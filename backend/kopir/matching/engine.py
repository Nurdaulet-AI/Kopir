"""Взаимный подбор: из двух направленных полезностей в ранжированный топ-K.

1. Взаимный балл пары — гармоническое среднее u(A→B) и u(B→A). Оно тянется
   к меньшему из двух, поэтому односторонняя польза не поднимает пару наверх.
2. Анти-очередь: тех, кого часто показывали за последний час, слегка опускаем,
   чтобы внимание зала не уходило трём «звёздам». Влияет только на порядок,
   показанный процент совпадения не меняет.
3. Разнообразие (MMR): пять рекомендаций не должны дублировать друг друга.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable, Collection
from dataclasses import dataclass

from kopir.matching.utility import Utility, utility
from kopir.models import Profile
from kopir.taxonomy import Goal

# Ниже этого взаимного балла пара считается слабой и помечается в выдаче.
WEAK_MATCH = 0.4
# Доля смысловой близости текстов «о себе» в направленной полезности.
SEMANTIC_WEIGHT = 0.15
# Компромисс MMR. Штраф за дублирование не больше (1 - λ), поэтому кандидат
# обгоняет более сильного, только если тот сильнее меньше чем на (1 - λ) / λ ≈ 0.11.
MMR_LAMBDA = 0.9

Similarity = Callable[[Profile, Profile], float]


@dataclass(frozen=True)
class Match:
    profile: Profile
    score: float  # взаимный балл 0..1, показываем как процент совпадения
    for_me: Utility  # чем этот человек полезен мне
    for_them: Utility  # чем я полезен ему

    @property
    def weak(self) -> bool:
        return self.score < WEAK_MATCH


def mutual_score(ab: float, ba: float) -> float:
    """Гармоническое среднее: ноль, если хоть одной стороне знакомство бесполезно."""
    if ab <= 0 or ba <= 0:
        return 0.0
    return 2 * ab * ba / (ab + ba)


class Exposure:
    """Сколько раз человека показывали другим за скользящее окно."""

    def __init__(self, window_s: float = 3600, strength: float = 0.15) -> None:
        self.window_s = window_s
        self.strength = strength
        self._shown: dict[str, deque[float]] = defaultdict(deque)

    def record(self, profile_id: str, now: float | None = None) -> None:
        self._shown[profile_id].append(time.time() if now is None else now)

    def count(self, profile_id: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        shown = self._shown[profile_id]
        while shown and now - shown[0] > self.window_s:
            shown.popleft()
        return len(shown)

    def penalty(self, profile_id: str, now: float | None = None) -> float:
        return 1.0 / (1.0 + self.strength * self.count(profile_id, now))


def _jaccard(a: Collection[str], b: Collection[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def _offer(p: Profile) -> tuple[list[str], list[str]]:
    """Что человек предлагает: у нанимающего это его вакансии, у остальных — он сам."""
    if p.goal == Goal.HIRE:
        return [r for o in p.openings for r in o.roles], [s for o in p.openings for s in o.skills]
    return [p.role], p.stack


def redundancy(x: Profile, y: Profile) -> float:
    """Насколько два кандидата дублируют друг друга в выдаче, 0..1."""
    roles_x, skills_x = _offer(x)
    roles_y, skills_y = _offer(y)
    return 0.5 * bool(set(roles_x) & set(roles_y)) + 0.5 * _jaccard(skills_x, skills_y)


class Matcher:
    def __init__(
        self,
        profiles: list[Profile],
        similarity: Similarity | None = None,
        exposure: Exposure | None = None,
    ) -> None:
        self.profiles = profiles
        self.similarity = similarity
        self.exposure = exposure or Exposure()

    def _directional(self, a: Profile, b: Profile) -> tuple[Utility, float]:
        """Полезность B для A и её итоговый балл с учётом смысловой близости текстов."""
        u = utility(a, b)
        score = u.score
        if score > 0 and self.similarity is not None:
            score = (1 - SEMANTIC_WEIGHT) * score + SEMANTIC_WEIGHT * self.similarity(a, b)
        return u, score

    def score_all(self, me: Profile, exclude: Collection[str] = ()) -> list[Match]:
        """Все взаимно полезные кандидаты, без ранжирования."""
        matches = []
        for other in self.profiles:
            if other.id == me.id or other.id in exclude:
                continue
            for_me, ab = self._directional(me, other)
            if ab <= 0:
                continue
            for_them, ba = self._directional(other, me)
            score = mutual_score(ab, ba)
            if score > 0:
                matches.append(Match(other, score, for_me, for_them))
        return matches

    def recommend(
        self,
        me: Profile,
        k: int = 5,
        exclude: Collection[str] = (),
        record: bool = True,
        now: float | None = None,
    ) -> list[Match]:
        """Топ-K по взаимному баллу с анти-очередью и MMR-разнообразием."""
        pool = self.score_all(me, exclude)
        relevance = {m.profile.id: m.score * self.exposure.penalty(m.profile.id, now) for m in pool}
        picked: list[Match] = []
        while pool and len(picked) < k:
            best = max(
                pool,
                key=lambda m: MMR_LAMBDA * relevance[m.profile.id]
                - (1 - MMR_LAMBDA) * max((redundancy(m.profile, p.profile) for p in picked), default=0.0),
            )
            picked.append(best)
            pool.remove(best)
        if record:
            for m in picked:
                self.exposure.record(m.profile.id, now)
        return picked
