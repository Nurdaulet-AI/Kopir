"""Объяснение рекомендации с двух сторон: чем человек полезен вам и чем вы полезны ему.

Объяснение собирается только из фактов, которые посчитал подбор (`Utility.facts`),
поэтому в нём не может появиться совпадение, которого нет. Тексты лежат в
`locales/<lang>.json`: их можно вычитать и поправить носителем языка, не трогая код.
Фразы построены так, чтобы имя не нужно было склонять и род не нужно было угадывать.
"""

import json
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files

from kopir.i18n import join, years
from kopir.matching.engine import Match
from kopir.matching.utility import Fact, Utility
from kopir.models import Profile
from kopir.taxonomy import DOMAIN_LABELS, LANGS, LEVEL_LABELS, ROLE_LABELS, Goal, Lang, Level

# Какой факт уточняет главную фразу, в порядке предпочтения, для каждой цели.
DETAIL_PRIORITY: dict[Goal, tuple[str, ...]] = {
    Goal.FIND_JOB: ("stack", "domain"),
    Goal.HIRE: ("stack", "domain"),
    Goal.FIND_MENTOR: ("topics", "domain"),
    Goal.BE_MENTOR: ("topics", "domain"),
    Goal.FIND_COFOUNDER: ("domain",),
    Goal.SHARE_EXPERIENCE: ("stack", "domain"),
}
# Факты, которые показываем чипами под объяснением.
CHIP_KINDS = ("stack", "topics", "domain")
# Сколько элементов перечислять в одной фразе, чтобы она оставалась короткой.
MAX_ITEMS = 3


@dataclass(frozen=True)
class Explanation:
    for_me: str  # чем этот человек полезен вам
    for_them: str  # чем вы полезны ему
    label_you: str
    label_them: str
    shared: dict[str, list[str]] = field(default_factory=dict)  # чипы: вид факта → подписи
    warnings: list[str] = field(default_factory=list)
    icebreaker: str = ""


@cache
def phrases(lang: Lang) -> dict:
    if lang not in LANGS:
        raise ValueError(f"неизвестный язык: {lang}")
    return json.loads(files("kopir.explain").joinpath("locales", f"{lang}.json").read_text(encoding="utf-8"))


def _labels(fact: Fact, lang: Lang) -> list[str]:
    """Значения факта в виде подписей на нужном языке (сферы переводятся, навыки — нет)."""
    if fact.kind == "domain":
        return [DOMAIN_LABELS[d][lang] for d in fact.value]
    return list(fact.value)


def _matched(u: Utility, kind: str) -> Fact | None:
    """Совпавший критерий данного вида: с ненулевым баллом и непустым значением."""
    return next((f for f in u.facts if f.kind == kind and f.role == "criterion" and f.score > 0 and f.value), None)


def _opening(u: Utility, lang: Lang) -> str:
    """Подпись вакансии, которую выбрал подбор: «Middle Backend-разработчик»."""
    note = next((f for f in u.facts if f.kind == "opening"), None)
    if note is None:
        return ""
    role, level = note.value
    prefix = f"{LEVEL_LABELS[Level(level)][lang]} " if level else ""
    return prefix + ROLE_LABELS[role][lang]


def _detail(u: Utility, goal: Goal, lang: Lang) -> str:
    for kind in DETAIL_PRIORITY[goal]:
        fact = _matched(u, kind)
        if fact is not None:
            items = join(_labels(fact, lang)[:MAX_ITEMS], lang)
            return phrases(lang)["detail"][kind].format(items=items)
    return ""


def _first_item(u: Utility, lang: Lang, fallback: str) -> str:
    for kind in CHIP_KINDS:
        fact = _matched(u, kind)
        if fact is not None:
            return _labels(fact, lang)[0]
    return fallback


def _sentence(template: str, context: dict[str, str]) -> str:
    text = template.format(**context)
    return text[0].upper() + text[1:]


def explain(me: Profile, match: Match, lang: Lang | None = None) -> Explanation:
    """Объяснение для `me`, почему стоит познакомиться с `match.profile`."""
    lang = lang or me.lang
    other = match.profile
    p = phrases(lang)
    base = {
        "name": other.name,
        "role": ROLE_LABELS[other.role][lang],
        "level": LEVEL_LABELS[other.level][lang],
        "years": years(other.years, lang),
        "my_role": ROLE_LABELS[me.role][lang],
    }
    for_me = _sentence(p["for_me"][me.goal], base | {
        "opening": _opening(match.for_me, lang),
        "detail": _detail(match.for_me, me.goal, lang),
    })
    for_them = _sentence(p["for_them"][other.goal], base | {
        "opening": _opening(match.for_them, lang),
        "detail": _detail(match.for_them, other.goal, lang),
    })

    shared: dict[str, list[str]] = {}
    for kind in CHIP_KINDS:
        labels: dict[str, None] = {}
        for u in (match.for_me, match.for_them):
            fact = _matched(u, kind)
            if fact is not None:
                labels.update(dict.fromkeys(_labels(fact, lang)))
        if labels:
            shared[kind] = list(labels)

    missed = {f.kind for u in (match.for_me, match.for_them) for f in u.facts
              if f.role == "requirement" and f.score == 0}
    warnings = [p["warning"][kind] for kind in p["warning"] if kind in missed]

    icebreaker = _sentence(p["icebreaker"][me.goal], {
        "opening": _opening(match.for_me, lang),
        "item": _first_item(match.for_me, lang, fallback=base["role"]),
    })
    return Explanation(
        for_me=for_me,
        for_them=for_them,
        label_you=p["label_you"],
        label_them=p["label_them"],
        shared=shared,
        warnings=warnings,
        icebreaker=icebreaker,
    )
