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
from dataclasses import dataclass, field, replace
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
    time: str  # слот встречи 1:1 («18:15»): выдаётся автоматически после согласия обоих
    slot: int = 0  # номер 15-минутного слота от START_MIN


@dataclass
class Intro:
    id: str
    from_id: str
    to_id: str
    status: Status = "pending"
    simulated: bool = False
    group: str | None = None  # общий id приглашения группы: одна зона, один код, одно время
    beacon: Beacon | None = None
    created: float = field(default_factory=time.time)
    accept_at: float | None = None  # когда вымышленный участник «ответит»


START_MIN = 18 * 60
SLOT_MIN = 15
SLOT_COUNT = 8  # запись на встречи: 18:00–19:45
SIM_DELAY_S = 4.0  # вымышленный участник «думает» несколько секунд — видно, что согласие двустороннее


def slot_time(slot: int) -> str:
    minutes = START_MIN + SLOT_MIN * slot
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


class Introductions:
    """Запросы на знакомство в памяти сервера (на время мероприятия).

    Записаться на встречу 1:1 = получить согласие второй стороны: тогда паре
    выдаётся маячок и ближайший слот, свободный у обоих (без двойных встреч).
    """

    def __init__(self, sim_delay: float = SIM_DELAY_S) -> None:
        self.sim_delay = sim_delay
        self._lock = threading.Lock()
        self._intros: dict[str, Intro] = {}
        self._ids = itertools.count(1)
        self._beacons = itertools.count(0)
        self._busy: dict[str, set[int]] = {}  # занятые слоты каждого участника
        self._groups: dict[str, Beacon] = {}

    def _slot(self, people: set[str]) -> int:
        taken = set().union(*(self._busy.get(p, set()) for p in people))
        slot = next(i for i in itertools.count() if i not in taken)
        for p in people:
            self._busy.setdefault(p, set()).add(slot)
        return slot

    def _new_beacon(self, people: set[str]) -> Beacon:
        n = next(self._beacons)
        letter = CODE_LETTERS[n % len(CODE_LETTERS)]
        slot = self._slot(people)
        return Beacon(color=BEACON_COLORS[n % len(BEACON_COLORS)], code=f"{letter}{n // len(CODE_LETTERS) + 1}",
                      zone=n % ZONES + 1, time=slot_time(slot), slot=slot)

    def _members(self, intro: Intro) -> set[str]:
        """Кто идёт на встречу: пара или вся группа приглашения."""
        if intro.group is None:
            return {intro.from_id, intro.to_id}
        same = [i for i in self._intros.values() if i.group == intro.group]
        return {i.from_id for i in same} | {i.to_id for i in same}

    def _meeting(self, intro_id: str, profile_id: str) -> Intro:
        intro = self._intros.get(intro_id)
        if intro is None or profile_id not in (intro.from_id, intro.to_id):
            raise KeyError("встреча не найдена")
        if intro.status != "accepted" or intro.beacon is None:
            raise ValueError("время выбирают после взаимного согласия")
        return intro

    def slots(self, intro_id: str, profile_id: str) -> list[tuple[int, str, bool]]:
        """Слоты записи: (номер, время, свободен ли у всех участников встречи). Текущий — свободен."""
        with self._lock:
            intro = self._meeting(intro_id, profile_id)
            current = intro.beacon.slot
            taken = set().union(*(self._busy.get(p, set()) for p in self._members(intro))) - {current}
            return [(i, slot_time(i), i not in taken) for i in range(SLOT_COUNT)]

    def reschedule(self, intro_id: str, profile_id: str, slot: int) -> Intro:
        """Перенести встречу на другое время — только на слот, свободный у всех её участников."""
        with self._lock:
            intro = self._meeting(intro_id, profile_id)
            old = intro.beacon.slot
            if not 0 <= slot < SLOT_COUNT:
                raise ValueError("такого слота нет")
            people = self._members(intro)
            taken = set().union(*(self._busy.get(p, set()) for p in people)) - {old}
            if slot in taken:
                raise ValueError("это время уже занято у одного из участников")
            for p in people:
                self._busy.setdefault(p, set()).discard(old)
                self._busy[p].add(slot)
            moved = replace(intro.beacon, slot=slot, time=slot_time(slot))
            for other in self._intros.values():  # у группы маячок общий — переносим всем
                if other.beacon is not None and other.beacon.code == intro.beacon.code and other is not intro:
                    other.beacon = moved
            intro.beacon = moved
            if intro.group is not None:
                self._groups[intro.group] = moved
            return intro

    def bookings(self, now: float | None = None) -> list[Intro]:
        """Все записи на встречи (по одной на маячок), по времени — для организатора."""
        with self._lock:
            self._settle(time.time() if now is None else now)
            seen: dict[str, Intro] = {}
            for i in self._intros.values():
                if i.status == "accepted" and i.beacon is not None:
                    seen.setdefault(i.beacon.code, i)
            return sorted(seen.values(), key=lambda i: (i.beacon.slot, i.beacon.zone))

    def members(self, intro: Intro) -> list[str]:
        with self._lock:
            return sorted(self._members(intro))

    def _accept(self, intro: Intro) -> None:
        intro.status = "accepted"
        if intro.beacon is not None:
            return
        if intro.group is None:
            intro.beacon = self._new_beacon({intro.from_id, intro.to_id})
            return
        # Группа встречается вместе: один маячок и одно время на всех участников приглашения.
        if intro.group not in self._groups:
            people = {i.from_id for i in self._intros.values() if i.group == intro.group}
            people |= {i.to_id for i in self._intros.values() if i.group == intro.group}
            self._groups[intro.group] = self._new_beacon(people | {intro.from_id, intro.to_id})
        intro.beacon = self._groups[intro.group]

    def _settle(self, now: float) -> None:
        for intro in self._intros.values():
            if intro.status == "pending" and intro.accept_at is not None and now >= intro.accept_at:
                self._accept(intro)

    def request(self, from_id: str, to_id: str, auto_accept: bool, group: str | None = None,
                now: float | None = None) -> Intro:
        if from_id == to_id:
            raise ValueError("нельзя познакомиться с самим собой")
        now = time.time() if now is None else now
        with self._lock:
            self._settle(now)
            for intro in self._intros.values():
                if (intro.from_id, intro.to_id) == (from_id, to_id):
                    return intro  # повторный запрос — тот же
            reverse = next((i for i in self._intros.values()
                            if (i.from_id, i.to_id) == (to_id, from_id) and i.status == "pending"), None)
            if reverse is not None:  # встречный интерес — это и есть двойное согласие
                self._accept(reverse)
                return reverse
            intro = Intro(id=f"i{next(self._ids)}", from_id=from_id, to_id=to_id, group=group)
            self._intros[intro.id] = intro
            if auto_accept:
                intro.simulated = True
                intro.accept_at = now + self.sim_delay
                self._settle(now)
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

    def of(self, profile_id: str, now: float | None = None) -> list[Intro]:
        with self._lock:
            self._settle(time.time() if now is None else now)
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
