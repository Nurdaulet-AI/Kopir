import itertools
import statistics
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import make
from kopir.api.app import create_app
from kopir.data.generator import generate
from kopir.evaluation.metrics import load_profiles
from kopir.hall import Hall
from kopir.matching.engine import Matcher
from kopir.matching.feedback import MAX_FACTOR, STEP, personal_score, preference_factors
from kopir.matching.utility import utility
from kopir.taxonomy import Goal, Level

EVAL = Path(__file__).resolve().parent.parent / "eval"


class TestFactors:
    def test_no_feedback_no_factors(self):
        assert preference_factors([]) == {}
        assert preference_factors(["other"]) == {}

    def test_reason_strengthens_its_criteria(self):
        assert preference_factors(["level"]) == {"level": STEP, "experience_gap": STEP}
        assert preference_factors(["stack", "stack"]) == {"stack": STEP**2, "topics": STEP**2}

    def test_factor_is_capped(self):
        assert preference_factors(["domain"] * 10) == {"domain": MAX_FACTOR}


class TestPersonalScore:
    def test_without_factors_score_is_unchanged(self, dataset):
        for a, b in itertools.islice(itertools.permutations(dataset, 2), 2000):
            u = utility(a, b)
            assert personal_score(u, {}) == u.score

    def test_uniform_factor_changes_nothing(self, dataset):
        """Перенормировка: если усилить все критерии одинаково, балл тот же."""
        uniform = {kind: 2.5 for kind in ("stack", "level", "domain", "topics", "experience_gap", "complement")}
        for a, b in itertools.islice(itertools.permutations(dataset, 2), 2000):
            u = utility(a, b)
            assert personal_score(u, uniform) == pytest.approx(u.score)

    def test_level_feedback_lets_better_level_overtake_better_stack(self):
        seeker = make(Goal.FIND_JOB, level=Level.JUNIOR, stack=["Python", "FastAPI"], target={"roles": ["backend"]})
        exact_stack = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python", "FastAPI"], "level": "middle"})
        exact_level = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python", "Kafka"], "level": "junior"})
        a, b = utility(seeker, exact_stack), utility(seeker, exact_level)
        assert a.score > b.score
        factors = preference_factors(["level"])
        assert personal_score(b, factors) > personal_score(a, factors)


def test_level_feedback_raises_level_fit_across_jury_queries(dataset):
    """На анкетах жюри после «не тот уровень» уровень в топ-5 в среднем подходит лучше."""
    matcher = Matcher(dataset)
    factors = preference_factors(["level", "level"])

    def mean_level_fit(q, f):
        fits = [next(x.score for x in m.for_me.facts if x.kind == "level")
                for m in matcher.recommend(q, record=False, factors=f)]
        return statistics.mean(fits)

    queries = [q for q in load_profiles(EVAL / "queries.json") + load_profiles(EVAL / "holdout.json")
               if q.goal in (Goal.FIND_JOB, Goal.HIRE, Goal.SHARE_EXPERIENCE)]
    before = statistics.mean(mean_level_fit(q, None) for q in queries)
    after = statistics.mean(mean_level_fit(q, factors) for q in queries)
    assert after > before


class TestApi:
    SEEKER = {"name": "Тест", "lang": "ru", "role": "backend", "level": "junior", "years": 1.5,
              "stack": ["Python", "FastAPI"], "goal": "find_job", "target": {"roles": ["backend"]}}

    @pytest.fixture
    def client(self):
        return TestClient(create_app(Hall(generate(n=150, seed=5))))

    def _recommend(self, client, feedback):
        return client.post("/api/recommend", json={"profile": self.SEEKER, "feedback": feedback})

    def test_feedback_excludes_people_and_returns_factors(self, client):
        first = self._recommend(client, []).json()
        assert first["factors"] == {}
        met, rejected = (r["candidate"]["id"] for r in first["recommendations"][:2])
        body = self._recommend(client, [
            {"candidate_id": met, "verdict": "met"},
            {"candidate_id": rejected, "verdict": "not_fit", "reason": "level"},
        ]).json()
        assert not {met, rejected} & {r["candidate"]["id"] for r in body["recommendations"]}
        assert body["factors"] == {"level": STEP, "experience_gap": STEP}

    def test_met_with_reason_is_rejected(self, client):
        r = self._recommend(client, [{"candidate_id": "p001", "verdict": "met", "reason": "level"}])
        assert r.status_code == 422

    def test_unknown_reason_is_rejected(self, client):
        r = self._recommend(client, [{"candidate_id": "p001", "verdict": "not_fit", "reason": "vibes"}])
        assert r.status_code == 422
