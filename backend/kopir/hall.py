"""Зал мероприятия: участники, подбор и анти-очередь в одном объекте.

Один `Hall` живёт всё время работы сервера и общий для всех запросов. Анти-очередь
меняет общее состояние (кого сколько раз показали), а сервер обрабатывает запросы
параллельно, поэтому изменения и подбор идут под блокировкой.
"""

import json
import os
import threading
from collections import Counter
from collections.abc import Collection
from pathlib import Path

from kopir.data.generator import generate
from kopir.matching.engine import Match, Matcher
from kopir.matching.feedback import Factors
from kopir.meet import Introductions
from kopir.models import Profile

# Сид зала по умолчанию: тот же, что у выгруженного data/profiles.json.
DEFAULT_SEED = 42
PROFILES_ENV = "KOPIR_PROFILES"


class Hall:
    def __init__(self, profiles: list[Profile]) -> None:
        ids = [p.id for p in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("в зале повторяются id анкет")
        self._lock = threading.Lock()
        self._by_id = {p.id: p for p in profiles}
        self._matcher = Matcher(list(profiles))
        self._skills: Counter[str] = Counter()
        self._joined: set[str] = set()  # живые участники, пришедшие через интерфейс
        self.introductions = Introductions()
        for p in profiles:
            self._count_skills(p)

    def _count_skills(self, p: Profile) -> None:
        self._skills.update(set(p.stack + p.target.skills + [s for o in p.openings for s in o.skills]))

    def skill_count(self, skill: str) -> int:
        """Сколько участников зала упоминают навык (свой стек, темы или вакансии)."""
        return self._skills[skill]

    @classmethod
    def from_file(cls, path: Path) -> "Hall":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls([Profile.model_validate(item) for item in data])

    @classmethod
    def default(cls) -> "Hall":
        """Зал из файла `$KOPIR_PROFILES`, а без него — синтетический зал с тем же сидом."""
        path = os.environ.get(PROFILES_ENV)
        return cls.from_file(Path(path)) if path else cls(generate(seed=DEFAULT_SEED))

    def profiles(self) -> list[Profile]:
        """Снимок участников зала (копия списка: зал может пополняться параллельно)."""
        with self._lock:
            return list(self._matcher.profiles)

    def is_live(self, profile_id: str) -> bool:
        """Живой ли это человек (а не вымышленная анкета демо-зала)."""
        return profile_id in self._joined

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, profile_id: str) -> Profile | None:
        return self._by_id.get(profile_id)

    def join(self, profile: Profile) -> None:
        """Добавляет участника в зал: теперь его тоже будут рекомендовать другим."""
        with self._lock:
            if profile.id in self._by_id:
                raise ValueError(f"анкета {profile.id} уже в зале")
            self._by_id[profile.id] = profile
            self._matcher.profiles.append(profile)
            self._count_skills(profile)
            self._joined.add(profile.id)

    def recommend(
        self, me: Profile, k: int = 5, exclude: Collection[str] = (), factors: Factors | None = None
    ) -> list[Match]:
        with self._lock:
            return self._matcher.recommend(me, k=k, exclude=exclude, factors=factors)
