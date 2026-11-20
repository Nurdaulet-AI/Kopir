"""Взаимный подбор: из двух направленных полезностей в ранжированный топ-K.

1. Взаимный балл пары — гармоническое среднее u(A→B) и u(B→A). Оно близко
   к меньшему из двух, поэтому односторонняя польза не поднимает пару наверх.
2. Анти-очередь: тех, кого уже часто рекомендовали за последний час, слегка
   опускаем, чтобы внимание зала не уходило трём «звёздам».
3. Разнообразие (MMR): пять рекомендаций не должны быть копиями одного профиля.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable

from kopir.matching.utility import Utility, utility
from kopir.models import Profile

# Ниже этого взаимного балла пара считается слабой и помечается в выдаче.
WEAK_MATCH = 0.4
# Доля смысловой близости текстов «о себе» в направленной полезности.
SEMANTIC_WEIGHT = 0.15
# Компромисс MMR: 1.0 — только релевантность, 0.0 — только разнообразие.
MMR_LAMBDA = 0.8

Similarity = Callable[[Profile, Profile], float]


@dataclass
class Match:
    profile: Profile
    score: float  # взаимный балл 0..1, его показываем как процент совпадения
    for_me: Utility  # чем этот человек полезен мне
    for_them: Utility  # чем я полезен ему
    weak: bool = False


def mutual_score(ab: float, ba: float) -> float:
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
        self._shown[profile_id].append(now if now is not None else time.time())

    def count(self, profile_id: str, now: float | None = None) -> int:
        now = now if now is not None else time.time()
        shown = self._shown[profile_id]
        while shown and now - shown[0] > self.window_s:
            shown.popleft()
        return len(shown)

    def penalty(self, profile_id: str) -> float:
        return 1.0 / (1.0 + self.strength * self.count(profile_id))


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def _redundancy(x: Profile, y: Profile) -> float:
    """Насколько два кандидата дублируют друг друга в выдаче."""
    return 0.5 * (x.role == y.role) + 0.5 * _jaccard(x.stack, y.stack)


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

    def _directional(self, a: Profile, b: Profile) -> Utility:
        u = utility(a, b)
        if self.similarity is not None and u.score > 0:
            u.score = (1 - SEMANTIC_WEIGHT) * u.score + SEMANTIC_WEIGHT * self.similarity(a, b)
        return u

    def score_all(self, me: Profile, exclude: set[str] = frozenset()) -> list[Match]:
        matches = []
        for other in self.profiles:
            if other.id == me.id or other.id in exclude:
                continue
            for_me = self._directional(me, other)
            if for_me.score <= 0:
                continue
            for_them = self._directional(other, me)
            score = mutual_score(for_me.score, for_them.score)
            if score > 0:
                matches.append(Match(other, score, for_me, for_them, weak=score < WEAK_MATCH))
        return matches

    def recommend(
        self, me: Profile, k: int = 5, exclude: set[str] = frozenset(), record: bool = True
    ) -> list[Match]:
        pool = self.score_all(me, exclude)
        ranked = {m.profile.id: m.score * self.exposure.penalty(m.profile.id) for m in pool}
        picked: list[Match] = []
        while pool and len(picked) < k:
            best = max(
                pool,
                key=lambda m: MMR_LAMBDA * ranked[m.profile.id]
                - (1 - MMR_LAMBDA) * max((_redundancy(m.profile, p.profile) for p in picked), default=0.0),
            )
            picked.append(best)
            pool.remove(best)
        if record:
            for m in picked:
                self.exposure.record(m.profile.id)
        return picked
