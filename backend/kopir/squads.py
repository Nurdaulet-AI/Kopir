"""Мини-группы: знакомство не только парой.

Два вида — по тому, какие цели совместимы между собой:

- **Команда** (кофаундеры, обмен опытом): 3–4 человека, где *каждая* пара взаимно
  полезна. Собираем жадно: добавляем того, у кого худший балл с участниками группы
  максимален (max-min), — группа держится на самом слабом звене, а не на среднем.
  Кофаундеры — с разными ролями: две копии бэкендера стартап не собирают.
- **Круг ментора** (один ко многим): ментор и 2–3 менти, которым он полезен,
  с общей темой. Ментору — одна встреча вместо трёх, менти — общий разговор.

Для «работа ↔ найм» групп нет: нанимающему не нужен второй нанимающий.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from kopir.matching.engine import Matcher
from kopir.models import Profile
from kopir.taxonomy import Goal

Kind = Literal["team", "circle"]

TEAM_SIZE = 4
CIRCLE_MENTEES = 3
POOL = 25  # кандидаты — лучшие по взаимному баллу с «я»
MIN_PAIR = 0.3  # слабее — пара в группе бесполезна
TEAM_GOALS = {Goal.FIND_COFOUNDER, Goal.SHARE_EXPERIENCE}


@dataclass(frozen=True)
class Squad:
    kind: Kind
    members: list[Profile]  # без «я»; в круге первым идёт ментор
    cohesion: float  # худший взаимный балл среди пар группы (команда) или ментор–менти (круг)
    skills: list[str]  # общее у группы: что встречается у большинства
    domains: list[str]


def _shared(groups: list[list[str]], limit: int) -> list[str]:
    """Что есть хотя бы у половины группы (минимум у двоих), по убыванию частоты."""
    need = max(2, (len(groups) + 1) // 2)
    counts = Counter(x for g in groups for x in set(g))
    return [x for x, n in counts.most_common() if n >= need][:limit]


def _topics(p: Profile) -> list[str]:
    """Темы человека: чему хочет научиться менти (target.skills), иначе его стек."""
    return p.target.skills or p.stack


def _team(me: Profile, matcher: Matcher) -> Squad | None:
    pool = sorted(matcher.score_all(me), key=lambda m: -m.score)[:POOL]
    members: list[Profile] = []
    scores = {m.profile.id: m.score for m in pool}  # худший балл кандидата с группой
    candidates = [m.profile for m in pool]
    weakest = 1.0
    while candidates and len(members) < TEAM_SIZE - 1:
        best = max(candidates, key=lambda c: scores[c.id])
        if scores[best.id] < MIN_PAIR:
            break
        members.append(best)
        weakest = min(weakest, scores[best.id])
        candidates.remove(best)
        roles = {me.role, *(m.role for m in members)}
        for c in list(candidates):
            if me.goal is Goal.FIND_COFOUNDER and c.role in roles:
                candidates.remove(c)
                continue
            scores[c.id] = min(scores[c.id], matcher.pair(best, c))
    if len(members) < 2:
        return None
    group = [me, *members]
    return Squad("team", members, weakest, _shared([p.stack for p in group], 4), _shared([p.interests for p in group], 2))


def _circle(mentor: Profile, matcher: Matcher, me: Profile) -> Squad | None:
    """Ментор и менти с общей темой; `me` — сам ментор или один из менти."""
    mentees = sorted((m for m in matcher.score_all(mentor) if m.score >= MIN_PAIR), key=lambda m: -m.score)[:POOL]
    if me is not mentor:
        mentees = [m for m in mentees if m.profile.id != me.id]
    # Тема круга — самая частая среди сильных менти (и обязательно та, что нужна «я», если я менти).
    focus = me if me is not mentor else (mentees[0].profile if mentees else None)
    if focus is None:
        return None
    topics = set(_topics(focus))
    chosen = [m for m in mentees if topics & set(_topics(m.profile))]
    chosen = (chosen or mentees)[:CIRCLE_MENTEES if me is mentor else CIRCLE_MENTEES - 1]
    if len(chosen) < 2:
        return None
    members = [m.profile for m in chosen] if me is mentor else [mentor, *(m.profile for m in chosen)]
    group = [mentor, *(m.profile for m in chosen)] + ([] if me is mentor else [me])
    return Squad("circle", members, min(m.score for m in chosen),
                 _shared([_topics(p) for p in group], 4), _shared([p.interests for p in group], 2))


def squad(me: Profile, matcher: Matcher) -> Squad | None:
    if me.goal in TEAM_GOALS:
        return _team(me, matcher)
    if me.goal is Goal.BE_MENTOR:
        return _circle(me, matcher, me)
    if me.goal is Goal.FIND_MENTOR:
        mentors = sorted(matcher.score_all(me), key=lambda m: -m.score)
        return _circle(mentors[0].profile, matcher, me) if mentors else None
    return None
