"""Направленная полезность: насколько участник B полезен участнику A.

Полезность несимметрична. Рекрутер полезен соискателю, если нанимает на его роль,
а соискатель полезен рекрутеру, если закрывает требования вакансии. Поэтому
`utility(a, b)` и `utility(b, a)` считаются разными функциями. Взаимный балл
пары собирается из обеих в `engine.py`.

Полезность складывается из двух видов фактов:
- **требования** (`require`): без них знакомство почти бессмысленно — не та роль
  для вакансии, ментор не опытнее менти. Невыполненное требование умножает итог
  на `REQUIREMENT_MISS`. Человек проваливается вниз, но не исчезает: если
  подходящих нет, лучше показать ближайших, чем пустой список;
- **критерии** (`add`): взвешенные компоненты, их веса для каждой цели дают 1.

Каждый факт хранит, что именно совпало. Из фактов строятся объяснения, поэтому
объяснение не может сказать того, чего не посчитала модель.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Literal

from kopir.models import Profile, Target
from kopir.taxonomy import COMPATIBLE, LEVEL_ORDER, SOFT_SKILLS, TECH_ROLES, Goal, Level

# Значение критерия, когда сравнивать не с чем (например, нанимающий не указал уровень).
NEUTRAL = 0.5
# Множитель за каждое невыполненное требование.
REQUIREMENT_MISS = 0.3
# Вес мягкой темы относительно технической при покрытии тем.
SOFT_SKILL_WEIGHT = 0.4
# Минимальный разрыв в опыте, при котором менторство имеет смысл, и комфортный разрыв.
MIN_MENTOR_GAP_YEARS = 1.5
GOOD_MENTOR_GAP_YEARS = 3.0


FactRole = Literal["criterion", "requirement", "note"]


@dataclass(frozen=True)
class Fact:
    """Одна причина полезности.

    - `criterion` — взвешенный критерий, вкладывает `score × weight`;
    - `requirement` — обязательное условие, при невыполнении умножает итог на `REQUIREMENT_MISS`;
    - `note` — сведение для объяснения (например, какая вакансия подошла), на балл не влияет.
    """

    kind: str
    value: tuple[str, ...]
    score: float
    weight: float = 0.0
    role: FactRole = "criterion"


@dataclass
class Utility:
    facts: list[Fact] = field(default_factory=list)
    gate: float = 1.0

    @property
    def score(self) -> float:
        return self.gate * sum(f.score * f.weight for f in self.facts if f.role == "criterion")

    def add(self, kind: str, value: Iterable[str], score: float, weight: float) -> None:
        self.facts.append(Fact(kind, tuple(value), score, weight))

    def require(self, kind: str, value: Iterable[str], ok: bool) -> None:
        self.facts.append(Fact(kind, tuple(value), 1.0 if ok else 0.0, role="requirement"))
        if not ok:
            self.gate *= REQUIREMENT_MISS

    def note(self, kind: str, value: Iterable[str]) -> None:
        self.facts.append(Fact(kind, tuple(value), 1.0, role="note"))


def _common(a: Iterable[str], b: Iterable[str]) -> tuple[str, ...]:
    """Пересечение с сохранением порядка `a`."""
    other = set(b)
    return tuple(dict.fromkeys(x for x in a if x in other))


def _skill_weight(skill: str) -> float:
    return SOFT_SKILL_WEIGHT if skill in SOFT_SKILLS else 1.0


def _coverage(required: list[str], have: list[str]) -> tuple[float, tuple[str, ...]]:
    """Взвешенная доля закрытых требований. Нет требований — нейтрально."""
    if not required:
        return NEUTRAL, ()
    hit = _common(required, have)
    total = sum(_skill_weight(s) for s in required)
    return sum(_skill_weight(s) for s in hit) / total, hit


def _overlap(a: list[str], b: list[str]) -> tuple[float, tuple[str, ...]]:
    """|A∩B| / min(|A|,|B|): не наказывает за длинный список.

    Если A пуст, у человека нет предпочтений — нейтрально. Если пуст только B,
    сравнивать не с чем, совпадения нет.
    """
    if not a:
        return NEUTRAL, ()
    if not b:
        return 0.0, ()
    hit = _common(a, b)
    return len(hit) / min(len(set(a)), len(set(b))), hit


def _level_fit(wanted: Level | None, actual: Level) -> float:
    if wanted is None:
        return NEUTRAL
    diff = abs(LEVEL_ORDER[wanted] - LEVEL_ORDER[actual])
    return {0: 1.0, 1: 0.5}.get(diff, 0.0)


def _level_closeness(a: Level, b: Level) -> float:
    diff = abs(LEVEL_ORDER[a] - LEVEL_ORDER[b])
    return {0: 1.0, 1: 1.0, 2: 0.5}.get(diff, 0.2)


def _wanted_domains(p: Profile) -> list[str]:
    return p.target.domains or p.interests


def _expertise(p: Profile) -> list[str]:
    return list(dict.fromkeys(p.stack + p.target.skills))


def _hard(skills: Iterable[str]) -> list[str]:
    return [s for s in skills if s not in SOFT_SKILLS]


def _mentoring(u: Utility, mentor: Profile, mentee: Profile) -> None:
    """Общая часть для обеих сторон менторства.

    Требования: ментор заметно опытнее и закрывает хотя бы одну тему менти.
    Если менти назвал технические темы, совпадение только по мягким («карьера») не засчитывается.
    """
    gap = mentor.years - mentee.years
    u.require("experience_gap", (f"{gap:g}",), gap >= MIN_MENTOR_GAP_YEARS)
    wanted = mentee.target.skills or mentee.stack
    score, hit = _coverage(wanted, _expertise(mentor))
    must_cover = _hard(wanted) or wanted
    u.require("topic_covered", _common(must_cover, hit), bool(_common(must_cover, hit)))
    u.add("topics", hit, score, 0.60)
    u.add("experience_gap", (f"{gap:g}",), 1.0 if gap >= GOOD_MENTOR_GAP_YEARS else 0.6, 0.20)


def _opening_label(opening: Target) -> tuple[str, ...]:
    return (*opening.roles[:1], opening.level or "")


def _best_opening(hirer: Profile, score_opening: Callable[[Target], Utility]) -> Utility:
    """Полезность лучшей из вакансий нанимающего; выбранная вакансия попадает в факты."""
    best_opening, best = max(
        ((o, score_opening(o)) for o in hirer.openings), key=lambda pair: pair[1].score
    )
    best.note("opening", _opening_label(best_opening))
    return best


def _find_job(a: Profile, b: Profile) -> Utility:
    """A ищет работу, B нанимает: подходит ли A хоть одна вакансия B."""

    def score(opening: Target) -> Utility:
        u = Utility()
        roles = _common(a.target.roles or [a.role], opening.roles)
        u.require("role", roles or opening.roles, bool(roles))
        stack, hit = _coverage(opening.skills, a.stack)
        u.add("stack", hit, stack, 0.45)
        u.add("level", [opening.level or a.level], _level_fit(opening.level, a.level), 0.30)
        domain, hit = _overlap(_wanted_domains(a), opening.domains)
        u.add("domain", hit, domain, 0.25)
        return u

    return _best_opening(b, score)


def _hire(a: Profile, b: Profile) -> Utility:
    """A нанимает, B ищет работу: закрывает ли B хоть одну вакансию A."""

    def score(opening: Target) -> Utility:
        u = Utility()
        roles = _common([b.role, *b.target.roles], opening.roles)
        u.require("role", roles or [b.role], bool(roles))
        stack, hit = _coverage(opening.skills, b.stack)
        u.add("stack", hit, stack, 0.55)
        u.add("level", [b.level], _level_fit(opening.level, b.level), 0.30)
        domain, hit = _overlap(opening.domains, b.interests)
        u.add("domain", hit, domain, 0.15)
        return u

    return _best_opening(a, score)


def _find_mentor(a: Profile, b: Profile) -> Utility:
    """A ищет ментора, B готов менторить: разбирается ли B в том, что нужно A."""
    u = Utility()
    _mentoring(u, mentor=b, mentee=a)
    score, hit = _overlap(_wanted_domains(a), b.interests)
    u.add("domain", hit, score, 0.20)
    return u


def _be_mentor(a: Profile, b: Profile) -> Utility:
    """A готов менторить, B ищет ментора: может ли A помочь именно B."""
    u = Utility()
    _mentoring(u, mentor=a, mentee=b)
    score, hit = _overlap(a.interests, _wanted_domains(b))
    u.add("domain", hit, score, 0.20)
    return u


def _find_cofounder(a: Profile, b: Profile) -> Utility:
    """Оба ищут кофаундера: нужна ли A роль B и горят ли они одним делом.

    Если A назвал нужные роли, это требование. Если нет, ценим взаимодополнение
    технаря и нетехнаря, но не требуем его.
    """
    u = Utility()
    domain_score, domain_hit = _overlap(_wanted_domains(a), _wanted_domains(b))
    level = _level_closeness(a.level, b.level)
    if a.target.roles:
        u.require("role", [b.role], b.role in a.target.roles)
        u.add("domain", domain_hit, domain_score, 0.70)
        u.add("level", [b.level], level, 0.30)
    else:
        complementary = (a.role in TECH_ROLES) != (b.role in TECH_ROLES)
        u.add("complement", [b.role], 1.0 if complementary else 0.0, 0.30)
        u.add("domain", domain_hit, domain_score, 0.50)
        u.add("level", [b.level], level, 0.20)
    return u


def _share_experience(a: Profile, b: Profile) -> Utility:
    """Оба хотят обменяться опытом: есть ли общий технический язык и общие темы.

    Требование: хотя бы один общий профессиональный навык. Одна общая сфера
    без общего ремесла — слабый повод для разговора.
    """
    u = Utility()
    common_craft = _common(_hard(_expertise(a)), _expertise(b))
    u.require("common_craft", common_craft, bool(common_craft))
    score, hit = _overlap(_expertise(a), _expertise(b))
    u.add("stack", hit, score, 0.45)
    score, hit = _overlap(_wanted_domains(a), _wanted_domains(b))
    u.add("domain", hit, score, 0.35)
    u.add("level", [b.level], _level_closeness(a.level, b.level), 0.20)
    return u


BY_GOAL: dict[Goal, Callable[[Profile, Profile], Utility]] = {
    Goal.FIND_JOB: _find_job,
    Goal.HIRE: _hire,
    Goal.FIND_MENTOR: _find_mentor,
    Goal.BE_MENTOR: _be_mentor,
    Goal.FIND_COFOUNDER: _find_cofounder,
    Goal.SHARE_EXPERIENCE: _share_experience,
}


def utility(a: Profile, b: Profile) -> Utility:
    """Насколько B полезен A с учётом цели A. Несовместимые цели и сам A дают ноль."""
    compat = COMPATIBLE[a.goal].get(b.goal, 0.0)
    if compat == 0.0 or a.id == b.id:
        return Utility(gate=0.0)
    u = BY_GOAL[a.goal](a, b)
    u.gate *= compat
    return u
