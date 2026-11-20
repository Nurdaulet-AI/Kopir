import pytest

from conftest import make
from kopir.matching.engine import MMR_LAMBDA, Exposure, Matcher, mutual_score, redundancy
from kopir.taxonomy import COMPATIBLE, Goal


class TestMutualScore:
    @pytest.mark.parametrize(("ab", "ba"), [(0.9, 0.1), (0.5, 0.5), (0.2, 0.7)])
    def test_symmetric_and_between_min_and_max(self, ab, ba):
        s = mutual_score(ab, ba)
        assert s == mutual_score(ba, ab)
        assert min(ab, ba) <= s <= max(ab, ba)

    def test_one_sided_benefit_is_zero(self):
        assert mutual_score(0.9, 0.0) == 0.0

    def test_leans_towards_weaker_side(self):
        assert mutual_score(0.9, 0.1) < (0.9 + 0.1) / 2


def test_recommendations_are_always_reciprocal(dataset):
    """Главное требование ТЗ: ищущему работу — нанимающих, и так для всех целей."""
    matcher = Matcher(dataset)
    for me in dataset:
        for m in matcher.recommend(me, record=False):
            assert COMPATIBLE[me.goal].get(m.profile.goal, 0) > 0
            assert COMPATIBLE[m.profile.goal].get(me.goal, 0) > 0


def test_every_profile_gets_full_top5(dataset):
    """Покрытие датасета: у любой анкеты есть хотя бы пять взаимно полезных людей."""
    matcher = Matcher(dataset)
    short = [p.id for p in dataset if len(matcher.recommend(p, record=False)) < 5]
    assert not short


def test_never_recommends_self_or_excluded(dataset):
    matcher = Matcher(dataset)
    me = dataset[0]
    first = matcher.recommend(me, record=False)
    excluded = {m.profile.id for m in first}
    second = matcher.recommend(me, exclude=excluded, record=False)
    assert me.id not in {m.profile.id for m in first + second}
    assert not excluded & {m.profile.id for m in second}


@pytest.mark.parametrize(
    "bound",
    [
        pytest.param((1 - MMR_LAMBDA) / MMR_LAMBDA, id="mmr-invariant"),
        # Продуктовое требование: заметно более сильный кандидат (на 12+ п.п.)
        # никогда не стоит ниже слабого. Не зависит от выбранного λ.
        pytest.param(0.12, id="product-guarantee"),
    ],
)
def test_diversity_never_inverts_clearly_better_match(dataset, bound):
    matcher = Matcher(dataset)
    for me in dataset:
        scores = [m.score for m in matcher.recommend(me, record=False)]
        for i, earlier in enumerate(scores):
            assert all(later - earlier <= bound + 1e-9 for later in scores[i + 1:])


class TestExposure:
    def test_penalty_grows_with_impressions_and_expires(self):
        exposure = Exposure(window_s=60)
        for t in range(5):
            exposure.record("star", now=t)
        assert exposure.penalty("star", now=10) < exposure.penalty("newbie", now=10) == 1.0
        assert exposure.penalty("star", now=1000) == 1.0

    def test_popular_person_yields_to_equal_alternative(self):
        seeker = make(Goal.FIND_JOB, stack=["Python"], target={"roles": ["backend"]})
        star = make(Goal.HIRE, id="star", target={"roles": ["backend"], "skills": ["Python"]})
        twin = make(Goal.HIRE, id="twin", target={"roles": ["backend"], "skills": ["Python"]})
        matcher = Matcher([star, twin])
        for _ in range(10):
            matcher.exposure.record("star", now=0)
        assert matcher.recommend(seeker, k=1, record=False, now=1)[0].profile.id == "twin"


def test_redundancy_compares_vacancies_not_recruiters():
    backend_job = make(Goal.HIRE, role="recruiter", target={"roles": ["backend"], "skills": ["Go"]})
    design_job = make(Goal.HIRE, role="recruiter", target={"roles": ["designer"], "skills": ["Figma"]})
    assert redundancy(backend_job, design_job) == 0.0
