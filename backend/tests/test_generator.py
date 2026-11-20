from collections import Counter

from kopir.data.generator import GOAL_SHARE, generate
from kopir.taxonomy import TECH_ROLES, Goal


def test_generation_is_deterministic():
    assert generate(n=50, seed=7) == generate(n=50, seed=7)


def test_size_quotas_and_unique_ids(dataset):
    assert len(dataset) == 200
    assert len({p.id for p in dataset}) == 200
    counts = Counter(p.goal for p in dataset)
    for goal, share in GOAL_SHARE.items():
        assert abs(counts[goal] - 200 * share) <= 1


def test_every_seeker_role_has_a_vacancy(dataset):
    vacancies = {r for p in dataset if p.goal == Goal.HIRE for r in p.target.roles}
    seeker_roles = {p.role for p in dataset if p.goal == Goal.FIND_JOB}
    assert seeker_roles <= vacancies


def test_every_mentee_topic_is_covered_by_some_mentor(dataset):
    expertise = {s for p in dataset if p.goal == Goal.BE_MENTOR for s in p.stack + p.target.skills}
    for p in dataset:
        if p.goal == Goal.FIND_MENTOR:
            assert set(p.target.skills) & expertise, p.id


def test_cofounders_are_balanced_between_tech_and_business(dataset):
    founders = [p for p in dataset if p.goal == Goal.FIND_COFOUNDER]
    tech = sum(p.role in TECH_ROLES for p in founders)
    assert abs(tech - (len(founders) - tech)) <= 1


def test_all_languages_present_and_texts_filled(dataset):
    assert set(Counter(p.lang for p in dataset)) == {"ru", "kk", "en"}
    assert all(p.about and "{" not in p.about for p in dataset)
