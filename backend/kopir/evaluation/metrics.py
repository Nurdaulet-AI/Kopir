"""Метрики качества выдачи и справедливости для зала."""

import json
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from kopir.evaluation.baselines import Recommender
from kopir.evaluation.judge import is_suitable
from kopir.matching.engine import Matcher
from kopir.models import Profile
from kopir.taxonomy import COMPATIBLE

K = 5
# Критерий жюри из ТЗ: на живой проверке подходящими должны быть минимум 3 из 5.
JURY_THRESHOLD = 3


@dataclass(frozen=True)
class QualityReport:
    queries: int
    jury_pass_rate: float  # доля анкет, где подходят ≥3 из 5
    precision_at_5: float  # среднее число подходящих / 5
    reciprocity_violations: float  # доля рекомендаций с несовместимой целью
    p95_ms: float
    failed: tuple[str, ...]  # id анкет, не прошедших критерий жюри


@dataclass(frozen=True)
class HallReport:
    profiles: int
    coverage: float  # доля участников, которых хоть раз рекомендовали
    max_impressions: int  # сколько раз показали самого популярного


def load_profiles(path: Path) -> list[Profile]:
    return [Profile.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def evaluate(recommend: Recommender, queries: list[Profile]) -> QualityReport:
    hits, violations, latencies, failed = [], 0, [], []
    for q in queries:
        start = time.perf_counter()
        recs = recommend(q, K)
        latencies.append((time.perf_counter() - start) * 1000)
        good = sum(is_suitable(q, r) for r in recs)
        violations += sum(COMPATIBLE[q.goal].get(r.goal, 0) == 0 for r in recs)
        hits.append(good)
        if good < JURY_THRESHOLD:
            failed.append(q.id)
    return QualityReport(
        queries=len(queries),
        jury_pass_rate=sum(h >= JURY_THRESHOLD for h in hits) / len(queries),
        precision_at_5=sum(hits) / (K * len(queries)),
        reciprocity_violations=violations / (K * len(queries)),
        p95_ms=statistics.quantiles(latencies, n=20)[-1] if len(latencies) > 1 else latencies[0],
        failed=tuple(failed),
    )


def data_ceiling(pool: list[Profile], queries: list[Profile]) -> tuple[float, tuple[str, ...]]:
    """Лучший возможный результат на этих данных: у скольких анкет в зале есть ≥3 подходящих.

    Отделяет ошибки ранжирования от нехватки людей: если подходящих меньше трёх,
    критерий жюри недостижим ни для какого алгоритма.
    """
    starved = tuple(q.id for q in queries if sum(is_suitable(q, p) for p in pool) < JURY_THRESHOLD)
    return 1 - len(starved) / len(queries), starved


def hall_fairness(pool: list[Profile], anti_queue: bool) -> HallReport:
    """Каждый участник зала запрашивает топ-5. Насколько равномерно распределено внимание?"""
    matcher = Matcher(pool)
    shown: Counter[str] = Counter()
    for t, me in enumerate(pool):
        # Время идёт, чтобы окно анти-очереди работало как в реальном зале.
        for m in matcher.recommend(me, k=K, record=anti_queue, now=float(t)):
            shown[m.profile.id] += 1
    return HallReport(
        profiles=len(pool),
        coverage=len(shown) / len(pool),
        max_impressions=max(shown.values(), default=0),
    )


def as_dict(report: QualityReport | HallReport) -> dict:
    return asdict(report)
