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
ALLOWED_FIELDS = {"name", "role", "level", "years", "my_role", "opening", "detail", "items", "item", "company"}


def _keys(tree: dict, prefix: str = "") -> set[str]:
    out = set()
    for k, v in tree.items():
        out |= _keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {f"{prefix}{k}"}
    return out


def _templates(tree: dict):
    """Все строки-шаблоны, включая тексты ступеней в лестницах первых фраз."""
    for v in tree.values():
        if isinstance(v, dict):
            yield from _templates(v)
        elif isinstance(v, list):
            yield from (step["text"] for step in v)
        else:
            yield v


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_every_language_has_the_same_phrases():
    reference = _keys(phrases("ru"))
    for lang in LANGS:
        assert _keys(phrases(lang)) == reference, lang


@pytest.mark.parametrize("lang", LANGS)
def test_templates_use_only_known_fields(lang):
    for template in _templates(phrases(lang)):
        assert _fields(template) <= ALLOWED_FIELDS, template


class TestIcebreakerLadders:
    def test_same_steps_in_every_language(self):
        ladders = {lang: phrases(lang)["icebreaker"] for lang in LANGS}
        for goal in Goal:
            steps = {lang: [s["needs"] for s in ladders[lang][goal]] for lang in LANGS}
            assert steps["ru"] == steps["kk"] == steps["en"], goal

    @pytest.mark.parametrize("lang", LANGS)
    def test_step_uses_exactly_what_it_needs_and_last_step_always_fits(self, lang):
        for goal, ladder in phrases(lang)["icebreaker"].items():
            for step in ladder:
                assert _fields(step["text"]) == set(step["needs"]), (lang, goal, step["text"])
            # «opening» есть у любой пары соискатель–нанимающий, поэтому последней ступени хватает.
            assert set(ladder[-1]["needs"]) <= {"opening"}, (lang, goal)

    seeker = make(Goal.FIND_JOB, stack=["Python", "FastAPI"], target={"roles": ["backend"]})

    def _icebreaker(self, hirer, rarity=None):
        match = Matcher([hirer]).recommend(self.seeker, record=False)[0]
        return explain(self.seeker, match, "ru", rarity=rarity).icebreaker

    def test_most_specific_step_is_chosen(self):
        hirer = make(Goal.HIRE, company="Dalafy", target={"roles": ["backend"], "skills": ["Python", "FastAPI"]})
        text = self._icebreaker(hirer, rarity={"Python": 90, "FastAPI": 12}.get)
        assert "Dalafy" in text and "FastAPI" in text and "Python" not in text

    def test_falls_back_when_company_is_unknown(self):
        hirer = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Python"], "level": "middle"})
        assert self._icebreaker(hirer) == ("Здравствуйте! Меня заинтересовала вакансия «Middle Backend-разработчик». "
                                           "Расскажете о команде?")

    def test_mentee_asks_about_the_mentors_strong_topic(self):
        mentee = make(Goal.FIND_MENTOR, years=1, target={"skills": ["Kafka"]})
        mentor = make(Goal.BE_MENTOR, years=8, stack=["Kafka"])
        match = Matcher([mentor]).recommend(mentee, record=False)[0]
        assert explain(mentee, match, "ru").icebreaker == (
            "Здравствуйте! Сейчас разбираюсь с Kafka — можно задать вам пару вопросов о вашем опыте?")


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


def test_second_sentence_does_not_repeat_the_first_detail(explained):
    for q, m, lang, e in explained:
        detail = e.for_me.split(" — ", 1)[1] if " — " in e.for_me else None
        if detail:
            assert detail.rstrip(".") not in e.for_them, (q.id, lang, e.for_me, e.for_them)
