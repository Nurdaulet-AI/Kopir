"""Рекомендатели для сравнения: типичные решения против Kópir.

`similar_people` — то, что делает большинство: ищет самых похожих по ролям,
навыкам, сферам и цели. На нетворкинге это даёт «соискателю — соискателей».
`similar_with_goal_filter` — то же, но с отсечением несовместимых целей.
"""

from collections.abc import Callable

from kopir.matching.engine import Matcher
from kopir.models import Profile
from kopir.taxonomy import COMPATIBLE

Recommender = Callable[[Profile, int], list[Profile]]


def _features(p: Profile) -> set[str]:
    return {
        f"goal:{p.goal}",
        f"role:{p.role}",
        *(f"role:{r}" for r in p.target.roles),
        *(f"skill:{s}" for s in p.stack + p.target.skills),
        *(f"domain:{d}" for d in p.interests + p.target.domains),
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _mutually_compatible(a: Profile, b: Profile) -> bool:
    return COMPATIBLE[a.goal].get(b.goal, 0) > 0 and COMPATIBLE[b.goal].get(a.goal, 0) > 0


def similar_people(pool: list[Profile]) -> Recommender:
    features = {p.id: _features(p) for p in pool}

    def recommend(me: Profile, k: int) -> list[Profile]:
        mine = _features(me)
        others = [p for p in pool if p.id != me.id]
        return sorted(others, key=lambda p: _jaccard(mine, features[p.id]), reverse=True)[:k]

    return recommend


def similar_with_goal_filter(pool: list[Profile]) -> Recommender:
    def recommend(me: Profile, k: int) -> list[Profile]:
        return similar_people([p for p in pool if _mutually_compatible(me, p)])(me, k)

    return recommend


def kopir(pool: list[Profile]) -> Recommender:
    matcher = Matcher(pool)

    def recommend(me: Profile, k: int) -> list[Profile]:
        return [m.profile for m in matcher.recommend(me, k=k, record=False)]

    return recommend


RECOMMENDERS: dict[str, Callable[[list[Profile]], Recommender]] = {
    "Похожие люди": similar_people,
    "Похожие + фильтр цели": similar_with_goal_filter,
    "Kópir": kopir,
}
