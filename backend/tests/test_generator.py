from collections import Counter

from kopir.data.generator import DEFAULT_SIZE, GOAL_SHARE, MIN_VACANCIES_PER_ROLE, OPENINGS_PER_HIRER, generate
from kopir.taxonomy import ROLE_LABELS, TECH_ROLES, Goal


def test_generation_is_deterministic():
    assert generate(n=50, seed=7) == generate(n=50, seed=7)


def test_size_quotas_and_unique_ids(dataset):
    assert len(dataset) == DEFAULT_SIZE
    assert len({p.id for p in dataset}) == DEFAULT_SIZE
    counts = Counter(p.goal for p in dataset)
    for goal, share in GOAL_SHARE.items():
        assert abs(counts[goal] - DEFAULT_SIZE * share) <= 1


def _hirers(dataset):
    return [p for p in dataset if p.goal == Goal.HIRE]


def test_every_seeker_role_has_enough_vacancies(dataset):
    vacancies = Counter(o.roles[0] for p in _hirers(dataset) for o in p.openings)
    for role in {p.role for p in dataset if p.goal == Goal.FIND_JOB}:
        assert vacancies[role] >= MIN_VACANCIES_PER_ROLE, role


def test_every_vacancy_matches_some_seeker_stack(dataset):
    """Вакансии списаны со спроса зала: требования вакансии есть у кого-то из соискателей."""
    seekers = [p for p in dataset if p.goal == Goal.FIND_JOB]
    for hirer in _hirers(dataset):
        for opening in hirer.openings:
            assert any(set(opening.skills) <= set(s.stack) for s in seekers), hirer.id


def test_companies_bring_several_distinct_openings(dataset):
    sizes = [len(p.openings) for p in _hirers(dataset)]
    assert min(sizes) >= 1
    assert max(sizes) <= max(OPENINGS_PER_HIRER) + 1  # +1: досадка отложенного дубля
    assert sum(sizes) / len(sizes) > 1.4
    for p in _hirers(dataset):
        keys = [(o.roles[0], tuple(o.skills)) for o in p.openings]
        assert len(keys) == len(set(keys)), p.id


def test_hirer_texts_mention_every_opening(dataset):
    for p in _hirers(dataset):
        for o in p.openings:
            assert ROLE_LABELS[o.roles[0]][p.lang] in p.about, p.id


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
