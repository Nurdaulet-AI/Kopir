import itertools

import pytest

from conftest import make
from kopir.matching.utility import BY_GOAL, utility
from kopir.taxonomy import COMPATIBLE, Goal, Level

# Продуктовое требование, а не повтор формулы: человек, не выполняющий обязательное
# условие (не та роль, ментор не опытнее), получает не больше половины балла
# подходящего при прочих равных.
MAX_SHARE_WHEN_REQUIREMENT_MISSED = 0.5


@pytest.mark.parametrize("goal", list(Goal))
def test_criteria_weights_sum_to_one_for_every_goal(dataset, goal):
    """Иначе баллы разных целей несопоставимы между собой."""
    people = [p for p in dataset if p.goal == goal]
    partners = [p for p in dataset if p.goal in COMPATIBLE[goal]]
    for a, b in itertools.islice(itertools.product(people, partners), 50):
        if a.id == b.id:
            continue
        weights = [f.weight for f in BY_GOAL[goal](a, b).facts if f.role == "criterion"]
        assert sum(weights) == pytest.approx(1.0)


def test_scores_stay_within_unit_interval(dataset):
    for a, b in itertools.islice(itertools.permutations(dataset, 2), 5000):
        assert 0.0 <= utility(a, b).score <= 1.0


def test_incompatible_goals_give_zero():
    seeker = make(Goal.FIND_JOB)
    other_seeker = make(Goal.FIND_JOB)
    assert utility(seeker, other_seeker).score == 0


def test_self_is_never_useful():
    hirer = make(Goal.HIRE, target={"roles": ["backend"]})
    assert utility(hirer, hirer).score == 0


class TestJob:
    seeker = make(Goal.FIND_JOB, stack=["Python", "FastAPI", "PostgreSQL"], target={"roles": ["backend"]})

    def test_vacancy_for_other_role_is_penalised(self):
        right = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python"]})
        wrong = make(Goal.HIRE, target={"roles": ["frontend"], "skills": ["Python"]})
        assert utility(self.seeker, wrong).score <= utility(self.seeker, right).score * MAX_SHARE_WHEN_REQUIREMENT_MISSED

    def test_closer_stack_ranks_higher(self):
        exact = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python", "FastAPI"]})
        partial = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python", "Kafka"]})
        assert utility(self.seeker, exact).score > utility(self.seeker, partial).score

    def test_best_of_several_openings_is_used_and_named(self):
        """Компания с вакансиями на QA и на backend подходит backend-соискателю по второй."""
        single = make(Goal.HIRE, openings=[{"roles": ["backend"], "skills": ["Python"], "level": "middle"}])
        multi = make(Goal.HIRE, openings=[
            {"roles": ["qa"], "skills": ["Selenium"], "level": "junior"},
            {"roles": ["backend"], "skills": ["Python"], "level": "middle"},
        ])
        u = utility(self.seeker, multi)
        assert u.score == pytest.approx(utility(self.seeker, single).score)
        assert [f.value for f in u.facts if f.kind == "opening"] == [("backend", "middle")]

    def test_notes_do_not_change_the_score(self):
        hirer = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python"]})
        u = utility(self.seeker, hirer)
        assert u.score == pytest.approx(sum(f.score * f.weight for f in u.facts if f.role == "criterion"))

    def test_hirer_prefers_candidate_of_requested_level(self):
        hirer = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python"], "level": "middle"})
        middle = make(Goal.FIND_JOB, level=Level.MIDDLE, stack=["Python"])
        intern = make(Goal.FIND_JOB, level=Level.INTERN, stack=["Python"])
        assert utility(hirer, middle).score > utility(hirer, intern).score


class TestMentoring:
    mentee = make(Goal.FIND_MENTOR, level=Level.JUNIOR, years=1, target={"skills": ["Kafka", "Career"]})

    def test_mentor_must_be_more_experienced(self):
        seasoned = make(Goal.BE_MENTOR, years=8, stack=["Kafka"])
        peer = make(Goal.BE_MENTOR, years=1.5, stack=["Kafka"])
        assert utility(self.mentee, peer).score <= utility(self.mentee, seasoned).score * MAX_SHARE_WHEN_REQUIREMENT_MISSED

    def test_mentor_must_cover_a_requested_technical_topic(self):
        kafka = make(Goal.BE_MENTOR, years=8, stack=["Kafka"])
        unrelated = make(Goal.BE_MENTOR, years=8, stack=["Figma"])
        career_only = make(Goal.BE_MENTOR, years=8, stack=["Recruiting"], target={"skills": ["Career"]})
        limit = utility(self.mentee, kafka).score * MAX_SHARE_WHEN_REQUIREMENT_MISSED
        assert utility(self.mentee, unrelated).score <= limit
        assert utility(self.mentee, career_only).score <= limit

    def test_technical_topic_adds_more_than_soft_topic(self):
        """При прочих равных вторая техническая тема ценнее «карьеры»."""
        mentee = make(Goal.FIND_MENTOR, years=1, target={"skills": ["Kafka", "Kubernetes", "Career"]})
        plus_soft = make(Goal.BE_MENTOR, years=8, stack=["Kafka"], target={"skills": ["Career"]})
        plus_hard = make(Goal.BE_MENTOR, years=8, stack=["Kafka", "Kubernetes"])
        assert utility(mentee, plus_hard).score > utility(mentee, plus_soft).score

    def test_both_directions_agree_on_topics(self):
        mentor = make(Goal.BE_MENTOR, years=8, stack=["Kafka"])
        topics = lambda u: next(f for f in u.facts if f.kind == "topics").value  # noqa: E731
        assert topics(utility(self.mentee, mentor)) == topics(utility(mentor, self.mentee)) == ("Kafka",)


class TestExchange:
    engineer = make(Goal.SHARE_EXPERIENCE, role="data_engineer", level=Level.SENIOR, stack=["Spark", "SQL"],
                    interests=["logistics"])

    def test_shared_domain_without_shared_craft_is_penalised(self):
        analyst = make(Goal.SHARE_EXPERIENCE, role="analyst", stack=["SQL"], interests=["logistics"])
        designer = make(Goal.SHARE_EXPERIENCE, role="designer", stack=["Figma"], interests=["logistics"])
        limit = utility(self.engineer, analyst).score * MAX_SHARE_WHEN_REQUIREMENT_MISSED
        assert utility(self.engineer, designer).score <= limit

    def test_shared_craft_beats_shared_domain(self):
        peer_other_domain = make(Goal.SHARE_EXPERIENCE, role="data_engineer", stack=["Spark", "SQL"],
                                 interests=["greentech"])
        designer_same_domain = make(Goal.SHARE_EXPERIENCE, role="designer", stack=["Figma"],
                                    interests=["logistics"])
        assert utility(self.engineer, peer_other_domain).score > utility(self.engineer, designer_same_domain).score


class TestCofounder:
    founder = make(Goal.FIND_COFOUNDER, role="frontend", interests=["agrotech"],
                   target={"roles": ["designer", "business"], "domains": ["agrotech"]})

    def test_requested_role_beats_unrequested_with_same_domain(self):
        designer = make(Goal.FIND_COFOUNDER, role="designer", interests=["agrotech"])
        ml = make(Goal.FIND_COFOUNDER, role="ml", interests=["agrotech"])
        assert utility(self.founder, ml).score <= utility(self.founder, designer).score * MAX_SHARE_WHEN_REQUIREMENT_MISSED

    def test_without_requested_roles_complement_is_preferred(self):
        open_founder = make(Goal.FIND_COFOUNDER, role="backend", interests=["fintech"])
        business = make(Goal.FIND_COFOUNDER, role="business", interests=["fintech"])
        backend = make(Goal.FIND_COFOUNDER, role="backend", interests=["fintech"])
        assert utility(open_founder, business).score > utility(open_founder, backend).score
