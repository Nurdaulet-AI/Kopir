import string
from pathlib import Path

import pytest

from conftest import make
from kopir.evaluation.metrics import load_profiles
from kopir.explain import explain
from kopir.explain.render import phrases
from kopir.matching.engine import Matcher
from kopir.taxonomy import DOMAIN_LABELS, LANGS, Goal, Level

EVAL = Path(__file__).resolve().parent.parent / "eval"
ALLOWED_FIELDS = {"name", "role", "level", "years", "my_role", "opening", "detail", "items", "item"}


def _keys(tree: dict, prefix: str = "") -> set[str]:
    out = set()
    for k, v in tree.items():
        out |= _keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {f"{prefix}{k}"}
    return out


def _leaves(tree: dict):
    for v in tree.values():
        yield from _leaves(v) if isinstance(v, dict) else [v]


def test_every_language_has_the_same_phrases():
    reference = _keys(phrases("ru"))
    for lang in LANGS:
        assert _keys(phrases(lang)) == reference, lang


@pytest.mark.parametrize("lang", LANGS)
def test_templates_use_only_known_fields(lang):
    for template in _leaves(phrases(lang)):
        fields = {name for _, name, _, _ in string.Formatter().parse(template) if name}
        assert fields <= ALLOWED_FIELDS, template


@pytest.fixture(scope="module")
def explained(dataset):
    """Объяснения для топ-5 каждой анкеты жюри на всех трёх языках."""
    matcher = Matcher(dataset)
    queries = load_profiles(EVAL / "queries.json") + load_profiles(EVAL / "holdout.json")
    return [(q, m, lang, explain(q, m, lang))
            for q in queries for m in matcher.recommend(q, record=False) for lang in LANGS]


def test_texts_are_complete_sentences_that_name_the_person(explained):
    for q, m, lang, e in explained:
        for text in (e.for_me, e.for_them, e.icebreaker):
            assert text and "{" not in text and "}" not in text, (q.id, lang, text)
            assert text[0].isupper() and text.rstrip()[-1] in ".?!", (q.id, lang, text)
        assert m.profile.name in e.for_me + e.for_them, (q.id, lang)


def test_vacancy_is_always_named_in_job_matches(explained):
    for q, m, lang, e in explained:
        if Goal.HIRE in (q.goal, m.profile.goal):
            assert "«»" not in e.for_me + e.for_them and "“”" not in e.for_me + e.for_them, (q.id, lang)


def test_every_chip_is_true_for_both_profiles(explained):
    """Чип — это то, что действительно есть у обоих, а не догадка."""
    for q, m, lang, e in explained:
        for kind, labels in e.shared.items():
            for label in labels:
                if kind == "domain":
                    keys = {k for k, names in DOMAIN_LABELS.items() if names[lang] == label}
                    owners = [set(p.interests + p.target.domains + [d for o in p.openings for d in o.domains])
                              for p in (q, m.profile)]
                    assert any(keys & owner for owner in owners), (q.id, label)
                else:
                    skills = [set(p.stack + p.target.skills + [s for o in p.openings for s in o.skills])
                              for p in (q, m.profile)]
                    assert all(label in s for s in skills), (q.id, kind, label)


def test_languages_actually_differ(dataset):
    me = make(Goal.FIND_JOB, stack=["Python"], target={"roles": ["backend"]})
    hirer = make(Goal.HIRE, name="Айгерім С.", target={"roles": ["backend"], "skills": ["Python"], "level": "middle"})
    match = Matcher([hirer]).recommend(me, record=False)[0]
    texts = {lang: explain(me, match, lang).for_me for lang in LANGS}
    assert len(set(texts.values())) == 3
    assert "Middle Backend-разработчик" in texts["ru"]
    assert "Python" in texts["kk"]


def test_missed_requirement_is_warned_about():
    mentee = make(Goal.FIND_MENTOR, level=Level.JUNIOR, years=1, target={"skills": ["Kafka"]})
    peer = make(Goal.BE_MENTOR, years=1.5, stack=["Kafka"])
    match = Matcher([peer]).recommend(mentee, record=False)[0]
    assert explain(mentee, match, "ru").warnings == ["разрыв в опыте слишком мал для менторства"]


def test_good_match_has_no_warnings():
    mentee = make(Goal.FIND_MENTOR, level=Level.JUNIOR, years=1, target={"skills": ["Kafka"]})
    mentor = make(Goal.BE_MENTOR, years=8, stack=["Kafka"])
    match = Matcher([mentor]).recommend(mentee, record=False)[0]
    e = explain(mentee, match, "en")
    assert e.warnings == []
    assert e.shared == {"topics": ["Kafka"]}
    assert "Kafka" in e.for_me and "Kafka" in e.icebreaker
