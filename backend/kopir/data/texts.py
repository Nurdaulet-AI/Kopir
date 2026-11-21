"""Тексты «о себе» для синтетических анкет на русском, казахском и английском."""

import random

from kopir.i18n import join as _join
from kopir.i18n import years as _years
from kopir.models import Profile
from kopir.taxonomy import DOMAIN_LABELS, LEVEL_LABELS, ROLE_LABELS, Goal


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
            "Сәлем! Мамандығым — {role} ({level}), тәжірибем {years}. Негізгі стек: {stack}. Қызығатын салаларым: {domains}. Жаңа жұмыс іздеймін.",
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
            "{domains} саласында стартап бастағым келеді. Мамандығым — {role}. Тең құрылтайшы іздеймін: {t_roles}.",
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
            "Мамандығым — {role} ({stack}). Тәжірибе алмасқым келеді. Тақырыптар: {topics}. Салалар: {domains}.",
        ],
        "en": [
            "{role} working with {stack}. Keen to swap experience. Topics: {topics}. Domains: {domains}.",
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
    t = p.target
    fields = {
        "role": ROLE_LABELS[p.role][lang],
        "level": LEVEL_LABELS[p.level][lang],
        "years": _years(p.years, lang),
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
