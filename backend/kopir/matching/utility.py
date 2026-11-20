"""Направленная полезность: насколько участник B полезен участнику A.

Полезность несимметрична. Рекрутер полезен соискателю, если нанимает на его роль,
а соискатель полезен рекрутеру, если закрывает требования вакансии. Поэтому
`utility(a, b)` и `utility(b, a)` считаются разными функциями. Взаимный балл
пары собирается из обеих в `engine.py`.

Каждая функция возвращает не только число, но и факты, за которые оно начислено.
Из этих фактов строятся объяснения, поэтому объяснение не может сказать
того, чего не посчитала модель.
"""

from dataclasses import dataclass, field
from typing import Callable

from kopir.models import Profile
from kopir.taxonomy import COMPATIBLE, LEVEL_ORDER, TECH_ROLES, Goal, Level

# Значение компонента, когда сравнивать не с чем (например, нанимающий не указал уровень).
NEUTRAL = 0.5


@dataclass(frozen=True)
class Fact:
    """Одна причина, по которой B полезен A. `value` — то, что совпало."""

    kind: str
    value: tuple[str, ...]
    score: float
    weight: float


@dataclass
class Utility:
    score: float = 0.0
    facts: list[Fact] = field(default_factory=list)

    def add(self, kind: str, value: tuple[str, ...], score: float, weight: float) -> None:
        self.score += score * weight
        self.facts.append(Fact(kind, value, score, weight))


def _common(a: list[str], b: list[str]) -> tuple[str, ...]:
    other = set(b)
    return tuple(x for x in a if x in other)


def _coverage(required: list[str], have: list[str]) -> tuple[float, tuple[str, ...]]:
    """Какая доля требований закрыта. Нет требований — нейтрально."""
    if not required:
        return NEUTRAL, ()
    hit = _common(required, have)
    return len(hit) / len(required), hit


def _overlap(a: list[str], b: list[str]) -> tuple[float, tuple[str, ...]]:
    """Коэффициент перекрытия |A∩B| / min(|A|,|B|): не наказывает за длинный стек."""
    if not a or not b:
        return NEUTRAL if not a else 0.0, ()
    hit = _common(a, b)
    return len(hit) / min(len(a), len(b)), hit


def _level_fit(wanted: Level | None, actual: Level) -> float:
    if wanted is None:
        return NEUTRAL
    diff = abs(LEVEL_ORDER[wanted] - LEVEL_ORDER[actual])
    return {0: 1.0, 1: 0.5}.get(diff, 0.0)


def _experience_gap(mentor: Profile, mentee: Profile) -> float:
    """Ментор должен быть заметно опытнее: разрыв от 3 лет — идеально."""
    gap = mentor.years - mentee.years
    if gap >= 3:
        return 1.0
    if gap >= 1.5:
        return 0.6
    return 0.0


def _wanted_domains(p: Profile) -> list[str]:
    return p.target.domains or p.interests


def _expertise(p: Profile) -> list[str]:
    return list(dict.fromkeys(p.stack + p.target.skills))


def _find_job(a: Profile, b: Profile) -> Utility:
    """A ищет работу, B нанимает: подходит ли вакансия B под A."""
    u = Utility()
    wanted_roles = a.target.roles or [a.role]
    roles = _common(wanted_roles, b.target.roles)
    u.add("role", roles, 1.0 if roles else 0.0, 0.35)
    score, hit = _coverage(b.target.skills, a.stack)
    u.add("stack", hit, score, 0.30)
    u.add("level", (b.target.level or a.level,), _level_fit(b.target.level, a.level), 0.20)
    score, hit = _overlap(_wanted_domains(a), b.target.domains)
    u.add("domain", hit, score, 0.15)
    return u


def _hire(a: Profile, b: Profile) -> Utility:
    """A нанимает, B ищет работу: закрывает ли B вакансию A."""
    u = Utility()
    roles = _common([b.role, *b.target.roles], a.target.roles)
    u.add("role", roles[:1], 1.0 if roles else 0.0, 0.30)
    score, hit = _coverage(a.target.skills, b.stack)
    u.add("stack", hit, score, 0.40)
    u.add("level", (b.level,), _level_fit(a.target.level, b.level), 0.20)
    score, hit = _overlap(a.target.domains, b.interests)
    u.add("domain", hit, score, 0.10)
    return u


def _find_mentor(a: Profile, b: Profile) -> Utility:
    """A ищет ментора, B готов менторить: разбирается ли B в том, что нужно A."""
    u = Utility()
    score, hit = _coverage(a.target.skills or a.stack, _expertise(b))
    u.add("topics", hit, score, 0.50)
    u.add("experience_gap", (f"{b.years:g}",), _experience_gap(b, a), 0.30)
    score, hit = _overlap(_wanted_domains(a), b.interests)
    u.add("domain", hit, score, 0.20)
    return u


def _be_mentor(a: Profile, b: Profile) -> Utility:
    """A готов менторить, B ищет ментора: может ли A помочь именно B."""
    u = Utility()
    score, hit = _coverage(b.target.skills or b.stack, _expertise(a))
    u.add("topics", hit, score, 0.50)
    u.add("experience_gap", (f"{b.years:g}",), _experience_gap(a, b), 0.30)
    score, hit = _overlap(a.interests, _wanted_domains(b))
    u.add("domain", hit, score, 0.20)
    return u


def _find_cofounder(a: Profile, b: Profile) -> Utility:
    """Оба ищут кофаундера: закрывает ли B нужную A роль и горят ли они одним делом."""
    u = Utility()
    if a.target.roles:
        roles = _common([b.role], a.target.roles)
        u.add("role", roles, 1.0 if roles else 0.0, 0.40)
    else:
        complementary = (a.role in TECH_ROLES) != (b.role in TECH_ROLES)
        u.add("complement", (b.role,), 1.0 if complementary else 0.3, 0.40)
    score, hit = _overlap(_wanted_domains(a), _wanted_domains(b))
    u.add("domain", hit, score, 0.40)
    u.add("different_role", (b.role,), 1.0 if b.role != a.role else 0.0, 0.20)
    return u


def _share_experience(a: Profile, b: Profile) -> Utility:
    """Оба хотят обменяться опытом: есть ли общий технический язык и общие темы."""
    u = Utility()
    score, hit = _overlap(_expertise(a), _expertise(b))
    u.add("stack", hit, score, 0.45)
    score, hit = _overlap(_wanted_domains(a), _wanted_domains(b))
    u.add("domain", hit, score, 0.35)
    diff = abs(LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level])
    u.add("level", (b.level,), {0: 1.0, 1: 1.0, 2: 0.5}.get(diff, 0.2), 0.20)
    return u


_BY_GOAL: dict[Goal, Callable[[Profile, Profile], Utility]] = {
    Goal.FIND_JOB: _find_job,
    Goal.HIRE: _hire,
    Goal.FIND_MENTOR: _find_mentor,
    Goal.BE_MENTOR: _be_mentor,
    Goal.FIND_COFOUNDER: _find_cofounder,
    Goal.SHARE_EXPERIENCE: _share_experience,
}


def utility(a: Profile, b: Profile) -> Utility:
    """Насколько B полезен A с учётом цели A. Несовместимые цели дают ноль."""
    compat = COMPATIBLE[a.goal].get(b.goal, 0.0)
    if compat == 0.0 or a.id == b.id:
        return Utility()
    u = _BY_GOAL[a.goal](a, b)
    u.score *= compat
    return u
