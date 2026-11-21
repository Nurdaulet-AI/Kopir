from pathlib import Path

from conftest import make
from kopir.evaluation.judge import is_suitable
from kopir.evaluation.metrics import load_profiles
from kopir.taxonomy import Goal, Level

QUERIES = Path(__file__).resolve().parent.parent / "eval" / "queries.json"


def test_jury_queries_are_valid_and_cover_every_goal():
    queries = load_profiles(QUERIES)
    assert len({q.id for q in queries}) == len(queries) >= 30
    assert {q.goal for q in queries} == set(Goal)
    assert {q.lang for q in queries} == {"ru", "kk", "en"}


class TestJob:
    seeker = make(Goal.FIND_JOB, level=Level.JUNIOR, stack=["Python", "FastAPI"], target={"roles": ["backend"]})

    def test_matching_vacancy_is_suitable_both_ways(self):
        hirer = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python", "Kafka"], "level": "middle"})
        assert is_suitable(self.seeker, hirer) and is_suitable(hirer, self.seeker)

    def test_other_role_or_far_level_is_not(self):
        frontend = make(Goal.HIRE, target={"roles": ["frontend"], "skills": ["Python"]})
        lead = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python"], "level": "lead"})
        assert not is_suitable(self.seeker, frontend)
        assert not is_suitable(self.seeker, lead)

    def test_any_fitting_opening_is_enough(self):
        hirer = make(Goal.HIRE, openings=[
            {"roles": ["designer"], "skills": ["Figma"]},
            {"roles": ["backend"], "skills": ["Python"], "level": "junior"},
        ])
        assert is_suitable(self.seeker, hirer) and is_suitable(hirer, self.seeker)

    def test_another_seeker_is_never_suitable(self):
        assert not is_suitable(self.seeker, make(Goal.FIND_JOB, stack=["Python"]))


def test_mentor_matching_only_on_career_is_rejected_when_tech_topics_requested():
    mentee = make(Goal.FIND_MENTOR, years=1, target={"skills": ["Kafka", "Career"]})
    career_only = make(Goal.BE_MENTOR, years=8, stack=["Recruiting"], target={"skills": ["Career"]})
    kafka = make(Goal.BE_MENTOR, years=8, stack=["Kafka"])
    assert not is_suitable(mentee, career_only)
    assert is_suitable(mentee, kafka)


def test_cofounder_requirements_must_hold_for_both_sides():
    founder = make(Goal.FIND_COFOUNDER, role="backend", interests=["fintech"], target={"roles": ["business"]})
    wants_ml = make(Goal.FIND_COFOUNDER, role="business", interests=["fintech"], target={"roles": ["ml"]})
    wants_backend = make(Goal.FIND_COFOUNDER, role="business", interests=["fintech"], target={"roles": ["backend"]})
    assert not is_suitable(founder, wants_ml)
    assert is_suitable(founder, wants_backend)
