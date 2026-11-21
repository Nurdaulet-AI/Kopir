"""Знакомство в зале: двойное согласие, маячок и расписание встреч 1:1.

Двойное согласие: контакты открываются, только когда оба сказали «да». Встречный
запрос считается согласием — если B уже хотел познакомиться с A, запрос A сразу
подтверждает пару. Вымышленные участники демо-зала соглашаются автоматически
(`simulated`), чтобы весь путь можно было показать одному человеку.

Маячок помогает найти друг друга в зале на 300 человек: номер зоны (где), цвет
и крупный код на весь экран (кто именно) плюс приметы из анкеты.
"""

import itertools
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

from kopir.matching.engine import Matcher
from kopir.models import Profile

Status = Literal["pending", "accepted", "declined"]

# Яркие различимые цвета маячка и буквы кода: пара «цвет + код» уникальна в зале.
BEACON_COLORS = ("#00a3bf", "#f5b700", "#e8467c", "#6a4cff", "#18b26b", "#ff7a1a", "#1f6feb", "#c026d3")
CODE_LETTERS = "ABCDEFGHKMPRT"
ZONES = 8


@dataclass(frozen=True)
class Beacon:
    color: str
    code: str
    zone: int


@dataclass
class Intro:
    id: str
    from_id: str
    to_id: str
    status: Status = "pending"
    simulated: bool = False
    beacon: Beacon | None = None
    created: float = field(default_factory=time.time)


class Introductions:
    """Запросы на знакомство в памяти сервера (на время мероприятия)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._intros: dict[str, Intro] = {}
        self._ids = itertools.count(1)
        self._beacons = itertools.count(0)

    def _beacon(self) -> Beacon:
        n = next(self._beacons)
        letter = CODE_LETTERS[n % len(CODE_LETTERS)]
        return Beacon(color=BEACON_COLORS[n % len(BEACON_COLORS)], code=f"{letter}{n // len(CODE_LETTERS) + 1}",
                      zone=n % ZONES + 1)

    def _accept(self, intro: Intro) -> None:
        intro.status = "accepted"
        intro.beacon = intro.beacon or self._beacon()

    def request(self, from_id: str, to_id: str, auto_accept: bool) -> Intro:
        if from_id == to_id:
            raise ValueError("нельзя познакомиться с самим собой")
        with self._lock:
            for intro in self._intros.values():
                if (intro.from_id, intro.to_id) == (from_id, to_id):
                    return intro  # повторный запрос — тот же
            reverse = next((i for i in self._intros.values()
                            if (i.from_id, i.to_id) == (to_id, from_id) and i.status == "pending"), None)
            if reverse is not None:  # встречный интерес — это и есть двойное согласие
                self._accept(reverse)
                return reverse
            intro = Intro(id=f"i{next(self._ids)}", from_id=from_id, to_id=to_id)
            if auto_accept:
                intro.simulated = True
                self._accept(intro)
            self._intros[intro.id] = intro
            return intro

    def respond(self, intro_id: str, profile_id: str, accept: bool) -> Intro:
        with self._lock:
            intro = self._intros.get(intro_id)
            if intro is None or intro.to_id != profile_id:
                raise KeyError("запрос не найден")
            if intro.status == "pending":
                if accept:
                    self._accept(intro)
                else:
                    intro.status = "declined"
            return intro

    def of(self, profile_id: str) -> list[Intro]:
        with self._lock:
            return [i for i in self._intros.values() if profile_id in (i.from_id, i.to_id)]


# --- расписание встреч 1:1 ---

@dataclass(frozen=True)
class Meeting:
    a: Profile
    b: Profile
    score: float
    zone: int


def schedule(profiles: list[Profile], slots: int = 4, per_person: int = 5) -> list[list[Meeting]]:
    """Встречи 1:1 по слотам: каждый не больше одной встречи в слот, пары не повторяются.

    Кандидаты — взаимные топ-`per_person` каждого. В каждом слоте жадно берём самые
    сильные пары из ещё не встречавшихся (жадное паросочетание по убыванию балла).
    """
    matcher = Matcher(profiles)
    edges: dict[tuple[str, str], tuple[float, Profile, Profile]] = {}
    for p in profiles:
        for m in matcher.recommend(p, k=per_person, record=False):
            key = tuple(sorted((p.id, m.profile.id)))
            if key not in edges or edges[key][0] < m.score:
                edges[key] = (m.score, p, m.profile)
    ranked = sorted(edges.values(), key=lambda e: -e[0])
    used: set[tuple[str, str]] = set()
    plan: list[list[Meeting]] = []
    for _ in range(slots):
        busy: set[str] = set()
        slot: list[Meeting] = []
        for score, a, b in ranked:
            key = tuple(sorted((a.id, b.id)))
            if key in used or a.id in busy or b.id in busy:
                continue
            used.add(key)
            busy |= {a.id, b.id}
            slot.append(Meeting(a, b, score, zone=len(slot) % ZONES + 1))
        plan.append(slot)
    return plan
