import pytest

from kopir.taxonomy import COMPATIBLE, GOAL_LABELS, LANGS, ROLE_LABELS, SKILLS, Goal, normalize_skill, normalize_skills


@pytest.mark.parametrize(
    ("raw", "canon"),
    [("golang", "Go"), ("  Python ", "Python"), ("питон", "Python"), ("k8s", "Kubernetes"), ("NestJS", "Node.js")],
)
def test_aliases_resolve_to_canonical_skill(raw, canon):
    assert normalize_skill(raw) == canon


def test_unknown_skill_is_dropped():
    assert normalize_skill("квантовая йога") is None


def test_normalize_skills_dedupes_and_keeps_order():
    assert normalize_skills(["go", "Python", "golang", "xyz", "py"]) == ["Go", "Python"]


def test_canonical_names_are_their_own_aliases():
    assert all(normalize_skill(s) == s for s in SKILLS)


def test_every_goal_and_role_is_labelled_in_all_languages():
    for labels in [*GOAL_LABELS.values(), *ROLE_LABELS.values()]:
        assert set(labels) == set(LANGS)


def test_goal_compatibility_is_symmetric():
    """Если B полезен A по цели, то и A полезен B — иначе взаимность невозможна."""
    for a in Goal:
        for b, weight in COMPATIBLE[a].items():
            assert COMPATIBLE[b].get(a) == weight
