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


# Шаблоны избегают конструкций, где название сферы или роли нужно склонять
# («интересуюсь Медиа»): без морфологии их не согласовать, поэтому списки
# стоят после двоеточия или в скобках.
TEMPLATES: dict[Goal, dict[str, list[str]]] = {
    Goal.FIND_JOB: {
        "ru": [
            "Привет! Я {role}, уровень {level}, опыт — {years}. Стек: {stack}. Интересные сферы: {domains}. Сейчас ищу работу.",
            "{role} ({level}), город {city}. Основной стек: {stack}. Хочу в продуктовую команду. Сферы: {domains}.",
        ],
        "kk": [
            "Сәлем! Мамандығым — {role} ({level}), тәжірибем {years}. Негізгі стек: {stack}. Қызықты салалар: {domains}. Жаңа жұмыс іздеймін.",
        ],
        "en": [
            "Hi! {role} ({level}), {years} of experience. Stack: {stack}. Interested in {domains}. Open to job offers.",
            "{role} ({level}) based in {city}. I work with {stack} and want to join a product team. Domains: {domains}.",
        ],
    },
    Goal.HIRE: {
        "ru": [
            "Нанимаю в {company}. Открытые вакансии: {openings}. Сфера компании: {company_domain}.",
            "Я {role} в {company}. Ищем людей в команду: {openings}.",
        ],
        "kk": [
            "{company} компаниясына қызметкерлер іздейміз. Ашық вакансиялар: {openings}. Сала: {company_domain}.",
        ],
        "en": [
            "Hiring at {company}. Open positions: {openings}. We work in {company_domain}.",
            "{role} at {company}. We're looking for: {openings}.",
        ],
    },
    Goal.FIND_MENTOR: {
        "ru": [
            "{role}, уровень {level}, опыт — {years}. Хочу прокачаться в темах: {topics}. Ищу ментора, который через это прошёл.",
            "Работаю как {role} ({level}). Упёрся в потолок, нужен ментор. Темы: {topics}.",
        ],
        "kk": [
            "Мамандығым — {role} ({level}). {topics} бағытында өскім келеді, тәлімгер іздеймін.",
        ],
        "en": [
            "{role} ({level}), {years} of experience. Looking for a mentor to grow in {topics}.",
        ],
    },
    Goal.BE_MENTOR: {
        "ru": [
            "{role}, опыт — {years}. Могу помочь с темами: {topics}.",
            "{years} в профессии, роль — {role}. Делюсь опытом, темы: {topics}.",
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
            "Хочу запустить стартап. Сферы: {domains}. Моя роль — {role}, ищу кофаундера: {t_roles}.",
            "Есть идея стартапа ({domains}), нужен партнёр. Моя роль — {role}, ищу: {t_roles}.",
        ],
        "kk": [
            "{domains} саласында стартап бастағым келеді. Мамандығым — {role}. Серіктес-құрылтайшы іздеймін: {t_roles}.",
        ],
        "en": [
            "Want to start a company in {domains}. My role: {role}. Looking for a co-founder: {t_roles}.",
        ],
    },
    Goal.SHARE_EXPERIENCE: {
        "ru": [
            "Работаю как {role} ({stack}). Интересно обменяться опытом. Темы: {topics}; сферы: {domains}.",
            "{role}, уровень {level}. Люблю обсуждать {topics} — давайте делиться опытом.",
        ],
        "kk": [
            "Мамандығым — {role} ({stack}). {topics} және {domains} туралы тәжірибе алмасқым келеді.",
        ],
        "en": [
            "{role} working with {stack}. Keen to swap experience on {topics} and {domains}.",
        ],
    },
}


def _domain_labels(domains: list[str], lang: str) -> str:
    return _join([DOMAIN_LABELS[d][lang] for d in domains], lang)


def _openings_text(p: Profile, lang: str) -> str:
    """«Middle Backend-разработчик (Python, FastAPI); Junior QA-инженер (Selenium)»."""
    parts = []
    for o in p.openings:
        level = f"{LEVEL_LABELS[o.level][lang]} " if o.level else ""
        stack = f" ({', '.join(o.skills)})" if o.skills else ""
        parts.append(f"{level}{ROLE_LABELS[o.roles[0]][lang]}{stack}")
    return "; ".join(parts)


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
        "domains": _domain_labels(p.interests or t.domains, lang),
        "topics": _join(t.skills[:3], lang),
        "company": p.company or "",
        "t_roles": _join([ROLE_LABELS[r][lang] for r in t.roles], lang),
        "openings": _openings_text(p, lang),
        "company_domain": _domain_labels(p.interests, lang),
    }
    text = rng.choice(TEMPLATES[p.goal][lang]).format(**fields)
    return text[0].upper() + text[1:]
