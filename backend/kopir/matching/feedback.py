"""Обратная связь «познакомились / не подошло» и личные веса критериев.

Причина «не подошло» говорит, какой критерий для человека важнее, чем считала
модель: «не тот уровень» → уровень. Каждая такая причина умножает вес этого
критерия на `STEP` (не больше `MAX_FACTOR`), а итог перенормируется, поэтому
балл остаётся в 0..1 и сравним с баллами без отзывов.

Отзыв меняет только сторону «чем этот человек полезен мне». Сторону «чем я полезен
ему» он не трогает: это предпочтения другого человека.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Literal

from kopir.matching.utility import Utility

Reason = Literal["level", "stack", "domain", "other"]
Verdict = Literal["met", "not_fit"]

# Какие критерии подбора усиливает причина «не подошло».
REASON_KINDS: dict[Reason, tuple[str, ...]] = {
    "level": ("level", "experience_gap"),
    "stack": ("stack", "topics"),
    "domain": ("domain",),
    "other": (),
}
STEP = 1.6
MAX_FACTOR = 4.0

Factors = Mapping[str, float]


def preference_factors(reasons: Iterable[Reason]) -> dict[str, float]:
    """Множители весов критериев из причин «не подошло»: {"level": 1.6, ...}."""
    counts = Counter(reasons)
    factors: dict[str, float] = {}
    for reason, n in counts.items():
        for kind in REASON_KINDS[reason]:
            factors[kind] = min(MAX_FACTOR, factors.get(kind, 1.0) * STEP**n)
    return factors


def personal_score(u: Utility, factors: Factors) -> float:
    """Балл полезности с личными весами; без множителей совпадает с `u.score`."""
    criteria = [f for f in u.facts if f.role == "criterion"]
    if not factors or not criteria:
        return u.score
    weights = [f.weight * factors.get(f.kind, 1.0) for f in criteria]
    total = sum(weights)
    return u.gate * sum(f.score * w for f, w in zip(criteria, weights)) / total
