"""Тексты «о себе» для синтетических анкет на русском, казахском и английском.

Это базовые шаблоны. Скрипт `scripts/rewrite_about.py` при доступной LLM
переписывает их живым языком; без LLM анкеты остаются с этими текстами.
"""

import random

from kopir.models import Profile
from kopir.taxonomy import DOMAIN_LABELS, LEVEL_LABELS, ROLE_LABELS, Goal


def years_ru(n: float) -> str:
    if n < 1:
        return "меньше года"
    if n != int(n):
        return f"{n:g} года"
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        word = "год"
    elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        word = "года"
    else:
        word = "лет"
    return f"{n} {word}"


def years_kk(n: float) -> str:
    return "бір жылдан аз" if n < 1 else f"{n:g} жыл"


def years_en(n: float) -> str:
    return "under a year" if n < 1 else f"{n:g} year{'s' if n != 1 else ''}"


def _join(items: list[str], lang: str) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    conj = {"ru": "и", "kk": "және", "en": "and"}[lang]
    return f"{', '.join(items[:-1])} {conj} {items[-1]}"


TEMPLATES: dict[Goal, dict[str, list[str]]] = {
    Goal.FIND_JOB: {
        "ru": [
            "Привет! Я {role} ({level}), опыт — {years}. Пишу на {stack}. Интересуюсь {domains}. Сейчас ищу работу и открыт к офферам.",
            "{level} {role} из города {city}. Основной стек: {stack}. Хочу в команду, которая делает продукт в сфере {domains}.",
        ],
        "kk": [
            "Сәлем! Мамандығым — {role} ({level}), тәжірибем {years}. Негізгі стек: {stack}. {domains} саласы қызықтырады. Жаңа жұмыс іздеймін.",
        ],
        "en": [
            "Hi! I'm a {level} {role} with {years} of experience. My stack: {stack}. Interested in {domains}. Open to job offers.",
            "{level} {role} based in {city}. I work with {stack} and want to join a team building in {domains}.",
        ],
    },
    Goal.HIRE: {
        "ru": [
            "Нанимаю в {company}: ищем {t_role} уровня {t_level}, стек {t_stack}. Делаем продукт в сфере {t_domains}.",
            "Я {role} в {company}. Открыта вакансия {t_role} ({t_level}), нужен опыт с {t_stack}.",
        ],
        "kk": [
            "{company} компаниясына {t_role} ({t_level}) іздейміз. Қажетті стек: {t_stack}. Біз {t_domains} саласында өнім жасаймыз.",
        ],
        "en": [
            "Hiring at {company}: looking for a {t_level} {t_role} with {t_stack}. We build products in {t_domains}.",
            "I'm a {role} at {company}. Open position: {t_role} ({t_level}), experience with {t_stack} required.",
        ],
    },
    Goal.FIND_MENTOR: {
        "ru": [
            "{level} {role}, опыт — {years}. Хочу прокачаться в темах: {topics}. Ищу ментора, который через это прошёл.",
            "Работаю как {role} ({level}). Чувствую потолок — нужен ментор по {topics}.",
        ],
        "kk": [
            "Мамандығым — {role} ({level}). {topics} бағытында өскім келеді, тәлімгер іздеймін.",
        ],
        "en": [
            "{level} {role} with {years} of experience. I want to grow in {topics} and I'm looking for a mentor.",
        ],
    },
    Goal.BE_MENTOR: {
        "ru": [
            "{role}, опыт — {years}. Могу помочь с темами: {topics}. Менторю тех, кто растёт в этом направлении.",
            "За плечами {years} в роли {role}. Готов делиться опытом: {topics}.",
        ],
        "kk": [
            "Мамандығым — {role}, тәжірибем {years}. {topics} бойынша көмектесе аламын, тәлімгер болуға дайынмын.",
        ],
        "en": [
            "{role} with {years} of experience. Happy to mentor on {topics}.",
        ],
    },
    Goal.FIND_COFOUNDER: {
        "ru": [
            "Хочу запустить стартап в сфере {domains}. Я {role}, ищу кофаундера: {t_roles}.",
            "Есть идея в {domains}, нужен партнёр. Сам(а) {role}, ищу {t_roles}.",
        ],
        "kk": [
            "{domains} саласында стартап бастағым келеді. Мамандығым — {role}. Серіктес-құрылтайшы іздеймін: {t_roles}.",
        ],
        "en": [
            "I want to start a company in {domains}. I'm a {role} looking for a co-founder: {t_roles}.",
        ],
    },
    Goal.SHARE_EXPERIENCE: {
        "ru": [
            "Работаю как {role} ({stack}). Интересно обменяться опытом про {topics} и {domains}.",
            "{level} {role}. Люблю обсуждать {topics} — давайте делиться опытом.",
        ],
        "kk": [
            "Мамандығым — {role} ({stack}). {topics} және {domains} туралы тәжірибе алмасқым келеді.",
        ],
        "en": [
            "{role} working with {stack}. Keen to swap experience on {topics} and {domains}.",
        ],
    },
}


def about_text(p: Profile, rng: random.Random) -> str:
    lang = p.lang
    years = {"ru": years_ru, "kk": years_kk, "en": years_en}[lang](p.years)
    t = p.target
    fields = {
        "role": ROLE_LABELS[p.role][lang],
        "level": LEVEL_LABELS[p.level][lang],
        "years": years,
        "city": p.city,
        "stack": _join(p.stack[:3], lang),
        "domains": _join([DOMAIN_LABELS[d][lang] for d in (p.interests or t.domains)], lang),
        "topics": _join(t.skills[:3], lang),
        "company": p.company or "",
        "t_role": _join([ROLE_LABELS[r][lang] for r in t.roles], lang),
        "t_roles": _join([ROLE_LABELS[r][lang] for r in t.roles], lang),
        "t_level": LEVEL_LABELS[t.level][lang] if t.level else "",
        "t_stack": _join(t.skills, lang),
        "t_domains": _join([DOMAIN_LABELS[d][lang] for d in t.domains], lang),
    }
    text = rng.choice(TEMPLATES[p.goal][lang]).format(**fields)
    return text[0].upper() + text[1:]
