"""Судья: подходит ли рекомендация «по мнению разумного члена жюри».

Судья намеренно не переиспользует формулу ранжирования из `matching/`: если
оценивать выдачу той же функцией, что её строит, метрика всегда будет хорошей.
Здесь только явные условия «да/нет» без весов, которые легко прочитать
и оспорить. Условия строже ранжирования: рекомендация засчитывается, только
если знакомство очевидно осмысленно для обеих сторон.
"""

from kopir.models import Profile
from kopir.taxonomy import LEVEL_ORDER, SOFT_SKILLS, TECH_ROLES, Goal, Level

MIN_MENTOR_GAP_YEARS = 1.5


def _hard(skills: list[str]) -> set[str]:
    return {s for s in skills if s not in SOFT_SKILLS}


def _levels_close(a: Level | None, b: Level) -> bool:
    return a is None or abs(LEVEL_ORDER[a] - LEVEL_ORDER[b]) <= 1


def _domains(p: Profile) -> set[str]:
    return set(p.target.domains or p.interests)


def _job_fits(seeker: Profile, hirer: Profile) -> bool:
    wanted = set(seeker.target.roles or [seeker.role])
    if not wanted & set(hirer.target.roles):
        return False
    required = _hard(hirer.target.skills)
    if required and len(required & set(seeker.stack)) * 2 < len(required):
        return False
    return _levels_close(hirer.target.level, seeker.level)


def _mentoring_fits(mentor: Profile, mentee: Profile) -> bool:
    if mentor.years - mentee.years < MIN_MENTOR_GAP_YEARS:
        return False
    wanted = set(mentee.target.skills or mentee.stack)
    expertise = set(mentor.stack + mentor.target.skills)
    hard_wanted = _hard(list(wanted))
    # Если менти назвал технические темы, совпадение только по «карьере» не считается.
    return bool((hard_wanted or wanted) & expertise)


def _cofounders_fit(a: Profile, b: Profile) -> bool:
    for x, y in ((a, b), (b, a)):
        if x.target.roles and y.role not in x.target.roles:
            return False
    if not a.target.roles and not b.target.roles:
        if (a.role in TECH_ROLES) == (b.role in TECH_ROLES):
            return False
    return bool(_domains(a) & _domains(b))


def _exchange_fits(a: Profile, b: Profile) -> bool:
    shared_skills = _hard(a.stack + a.target.skills) & _hard(b.stack + b.target.skills)
    if not shared_skills:
        return False
    return bool(_domains(a) & _domains(b)) or _levels_close(a.level, b.level)


def is_suitable(query: Profile, candidate: Profile) -> bool:
    match query.goal, candidate.goal:
        case Goal.FIND_JOB, Goal.HIRE:
            return _job_fits(query, candidate)
        case Goal.HIRE, Goal.FIND_JOB:
            return _job_fits(candidate, query)
        case Goal.FIND_MENTOR, Goal.BE_MENTOR:
            return _mentoring_fits(candidate, query)
        case Goal.BE_MENTOR, Goal.FIND_MENTOR:
            return _mentoring_fits(query, candidate)
        case Goal.FIND_COFOUNDER, Goal.FIND_COFOUNDER:
            return _cofounders_fit(query, candidate)
        case Goal.SHARE_EXPERIENCE, Goal.SHARE_EXPERIENCE:
            return _exchange_fits(query, candidate)
    return False
