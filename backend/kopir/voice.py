"""Разбор свободного рассказа о себе (голосом или текстом) в поля анкеты.

Распознавание речи делает браузер; здесь — только понимание текста: навыки по
словарю синонимов, роль, уровень, опыт, цель и сферы по ключевым словам на
RU / KK / EN. Правила прозрачны: человек видит заполненные поля и правит их.
"""

import re
from dataclasses import dataclass, field

from kopir.taxonomy import SKILL_ALIASES, Goal, Level

ROLE_WORDS: dict[str, tuple[str, ...]] = {
    "backend": ("бэкенд", "бекенд", "backend", "бэкендер"),
    "frontend": ("фронтенд", "frontend", "фронтендер"),
    "fullstack": ("фулстек", "fullstack", "full-stack"),
    "mobile": ("мобильн", "android", "ios", "flutter"),
    "ml": ("ml", "машинн", "нейросет", "machine learning"),
    "data_science": ("data scien", "дата сайент", "дата-сайент"),
    "data_engineer": ("data engineer", "дата-инженер", "дата инженер"),
    "analyst": ("аналитик", "analyst", "талдаушы"),
    "devops": ("devops", "девопс", "sre"),
    "qa": ("тестировщик", "qa", "тестер", "автотест"),
    "designer": ("дизайнер", "designer", "ux", "ui"),
    "product": ("продакт", "product manager", "өнім"),
    "business": ("бизнес", "предприниматель", "business", "founder"),
    "marketing": ("маркетолог", "marketing", "smm"),
    "recruiter": ("рекрутер", "hr", "recruiter"),
}
LEVEL_WORDS: dict[Level, tuple[str, ...]] = {
    Level.INTERN: ("стажёр", "стажер", "студент", "intern", "student", "студентпін"),
    Level.JUNIOR: ("джун", "junior"),
    Level.MIDDLE: ("мидл", "middle"),
    Level.SENIOR: ("сеньор", "синьор", "senior"),
    Level.LEAD: ("тимлид", "лид", "lead", "cto", "руковод"),
}
GOAL_WORDS: dict[Goal, tuple[str, ...]] = {
    Goal.HIRE: ("нанима", "ищем", "вакансия", "hiring", "hire", "жалда"),
    Goal.FIND_COFOUNDER: ("кофаундер", "co-founder", "cofounder", "партнёр", "партнер", "құрылтайшы"),
    Goal.BE_MENTOR: ("стать ментором", "могу менторить", "готов менторить", "mentor others", "тәлімгер боламын"),
    Goal.FIND_MENTOR: ("ищу ментора", "нужен ментор", "find a mentor", "тәлімгер іздеймін"),
    Goal.SHARE_EXPERIENCE: ("обменяться опытом", "обмен опытом", "swap experience", "тәжірибе алмас"),
    Goal.FIND_JOB: ("ищу работу", "работу", "job", "жұмыс"),
}
DOMAIN_WORDS: dict[str, tuple[str, ...]] = {
    "fintech": ("финтех", "fintech", "банк", "платеж"),
    "edtech": ("edtech", "образован", "школ", "білім"),
    "ai": (" ai", "ии ", "llm", "искусственн"),
    "healthtech": ("медицин", "health", "здоров"),
    "ecommerce": ("e-commerce", "ecommerce", "маркетплейс", "интернет-магазин"),
    "logistics": ("логистик", "logistics"),
    "govtech": ("govtech", "госуслуг", "государств"),
    "gaming": ("игр", "gamedev", "gaming"),
}


@dataclass
class Parsed:
    role: str | None = None
    level: Level | None = None
    years: float | None = None
    goal: Goal | None = None
    stack: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)


def _skills(text: str) -> list[str]:
    found: dict[str, int] = {}
    for canon, aliases in SKILL_ALIASES.items():
        for alias in {canon.lower(), *aliases}:
            if len(alias) < 2:
                continue
            # Кириллица склоняется («на питоне»): после основы допускаем окончание.
            tail = "" if re.search("[а-яёәіңғүұқөһ]", alias) else r"(?![\w+#])"
            m = re.search(rf"(?<![\w+#.]){re.escape(alias)}{tail}", text)
            if m and (canon not in found or m.start() < found[canon]):
                found[canon] = m.start()
    return sorted(found, key=found.get)


def _first(table: dict, text: str):
    hits = [(text.find(w), key) for key, words in table.items() for w in words if w in text]
    return min(hits)[1] if hits else None


def parse(text: str) -> Parsed:
    t = f" {text.lower()} "
    years = re.search(r"(\d+(?:[.,]\d)?)\s*(?:год|года|лет|жыл|years?|yrs?)", t)
    return Parsed(
        role=_first(ROLE_WORDS, t),
        level=_first(LEVEL_WORDS, t),
        years=float(years.group(1).replace(",", ".")) if years else None,
        goal=next((g for g, words in GOAL_WORDS.items() if any(w in t for w in words)), None),
        stack=_skills(t),
        interests=[d for d, words in DOMAIN_WORDS.items() if any(w in t for w in words)],
    )
