"""Аналитика зала для организатора: баланс спроса и предложения, карта, выводы.

Всё считается из анкет зала. Выводы — правила с порогами, а не догадки модели:
каждый можно проверить по цифрам рядом с ним.
"""

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from kopir.matching.engine import WEAK_MATCH, Matcher
from kopir.meet import schedule
from kopir.models import Profile
from kopir.taxonomy import DOMAIN_LABELS, GOAL_LABELS, GOAL_STATUS, ROLE_LABELS, SOFT_SKILLS, Goal, Lang

# Три «рынка» зала: на карте это три цвета (для точечной диаграммы проверены
# только три категориальных цвета), а сторона рынка — форма точки.
MARKET: dict[Goal, tuple[str, str]] = {
    Goal.FIND_JOB: ("jobs", "seeks"),
    Goal.HIRE: ("jobs", "offers"),
    Goal.FIND_MENTOR: ("mentoring", "seeks"),
    Goal.BE_MENTOR: ("mentoring", "offers"),
    Goal.FIND_COFOUNDER: ("startups", "seeks"),
    Goal.SHARE_EXPERIENCE: ("startups", "offers"),
}

# Расписание: слоты по 15 минут с начала нетворкинга.
SLOTS = 4
START_MIN = 18 * 60
SLOT_MIN = 15

# Пороги выводов: ниже MIN_SEEKERS людей роль не обсуждаем — выборка мала.
MIN_SEEKERS = 3
FEW_OPENINGS = 0.5  # вакансий на соискателя меньше — работодателей не хватает
FEW_CANDIDATES = 1.5  # вакансий на соискателя больше — кандидатов не хватает
MIN_TOPIC_DEMAND = 3
MAX_INSIGHTS = 5
TOP = 8

INSIGHTS: dict[Lang, dict[str, str]] = {
    "ru": {
        "few_openings": "Мало вакансий для роли «{role}»: соискателей — {seekers}, вакансий — {openings}. Стоит позвать компании, которые нанимают в эту роль.",
        "few_candidates": "Не хватает кандидатов на роль «{role}»: вакансий — {openings}, соискателей — {seekers}.",
        "mentor_gap": "Не хватает менторов по теме {topic}: запросов — {demand}, менторов — {supply}.",
        "top_domain": "Самая популярная сфера зала — {domain} (участников: {count}).",
    },
    "kk": {
        "few_openings": "«{role}» рөліне вакансиялар аз: {seekers} үміткерге {openings} вакансия. Осы рөлге қызметкер іздейтін компанияларды шақырған жөн.",
        "few_candidates": "«{role}» рөліне үміткерлер жетіспейді: {seekers} үміткерге {openings} вакансия.",
        "mentor_gap": "{topic} тақырыбы бойынша тәлімгерлер жетіспейді: {demand} сұраныс, {supply} тәлімгер.",
        "top_domain": "Залдағы ең танымал сала — {domain}: {count} қатысушы.",
    },
    "en": {
        "few_openings": "Few openings for “{role}”: job seekers — {seekers}, openings — {openings}. Invite companies hiring for this role.",
        "few_candidates": "Not enough candidates for “{role}”: openings — {openings}, job seekers — {seekers}.",
        "mentor_gap": "Not enough mentors for {topic}: requests — {demand}, mentors — {supply}.",
        "top_domain": "The hall's most popular domain is {domain} (participants: {count}).",
    },
}


@dataclass
class Dashboard:
    participants: int
    goals: list[dict]
    roles: list[dict]  # соискатели против вакансий по ролям
    skills: list[dict]  # востребованные навыки: спрос и предложение
    domains: list[dict]
    points: list[dict]  # карта зала
    insights: list[dict] = field(default_factory=list)
    hirers: int = 0
    openings: int = 0
    well_matched: float = 0.0  # доля участников с ≥3 сильными взаимными совпадениями
    slots: list[dict] = field(default_factory=list)  # расписание встреч 1:1
    scheduled: float = 0.0  # доля участников хотя бы с одной встречей


def _features(p: Profile) -> set[str]:
    skills = p.stack + p.target.skills + [s for o in p.openings for s in o.skills]
    roles = [p.role, *p.target.roles, *(r for o in p.openings for r in o.roles)]
    return {f"goal:{p.goal}", *(f"role:{r}" for r in roles), *(f"skill:{s}" for s in skills),
            *(f"domain:{d}" for d in p.interests + p.target.domains)}


def hall_map(profiles: list[Profile]) -> np.ndarray:
    """Координаты участников 0..1: две главные компоненты признаков анкеты.

    Похожие анкеты оказываются рядом. Знаки осей фиксированы (по нанимающим),
    чтобы карта не «переворачивалась» между запусками.
    """
    vocab = sorted({f for p in profiles for f in _features(p)})
    index = {f: i for i, f in enumerate(vocab)}
    x = np.zeros((len(profiles), len(vocab)))
    for row, p in enumerate(profiles):
        x[row, [index[f] for f in _features(p)]] = 1.0
    x -= x.mean(axis=0)
    u, s, _ = np.linalg.svd(x, full_matrices=False)
    coords = u[:, :2] * s[:2]
    hirers = np.array([p.goal == Goal.HIRE for p in profiles])
    for axis in range(2):
        if hirers.any() and coords[hirers, axis].mean() < 0:
            coords[:, axis] *= -1
    lo, hi = coords.min(axis=0), coords.max(axis=0)
    return 0.04 + 0.92 * (coords - lo) / np.where(hi > lo, hi - lo, 1)


def _well_matched(profiles: list[Profile]) -> float:
    matcher = Matcher(profiles)
    good = sum(sum(m.score >= WEAK_MATCH for m in matcher.recommend(p, k=3, record=False)) == 3 for p in profiles)
    return good / len(profiles) if profiles else 0.0


def build(profiles: list[Profile], lang: Lang) -> Dashboard:
    goals = Counter(p.goal for p in profiles)
    seekers = Counter(p.role for p in profiles if p.goal == Goal.FIND_JOB)
    openings = Counter(o.roles[0] for p in profiles if p.goal == Goal.HIRE for o in p.openings)
    roles = sorted(set(seekers) | set(openings), key=lambda r: -(seekers[r] + openings[r]))[:10]

    demand = Counter(s for p in profiles if p.goal == Goal.HIRE for o in p.openings for s in o.skills)
    demand += Counter(s for p in profiles if p.goal == Goal.FIND_MENTOR for s in p.target.skills)
    supply = Counter(s for p in profiles if p.goal in (Goal.FIND_JOB, Goal.BE_MENTOR)
                     for s in set(p.stack + p.target.skills))
    skills = [s for s, _ in demand.most_common() if s not in SOFT_SKILLS][:TOP]

    domains = Counter(d for p in profiles for d in set(p.interests + p.target.domains))
    coords = hall_map(profiles)

    t = INSIGHTS[lang]
    insights: list[dict] = []
    for r in roles:
        if seekers[r] < MIN_SEEKERS:
            continue
        ratio = openings[r] / seekers[r]
        label = ROLE_LABELS[r][lang]
        if ratio < FEW_OPENINGS:
            insights.append({"kind": "few_openings", "severity": 1 - ratio,
                             "text": t["few_openings"].format(role=label, seekers=seekers[r], openings=openings[r])})
        elif ratio > FEW_CANDIDATES:
            insights.append({"kind": "few_candidates", "severity": min(1.0, ratio / 4),
                             "text": t["few_candidates"].format(role=label, seekers=seekers[r], openings=openings[r])})
    topic_demand = Counter(s for p in profiles if p.goal == Goal.FIND_MENTOR for s in p.target.skills
                           if s not in SOFT_SKILLS)
    mentors = Counter(s for p in profiles if p.goal == Goal.BE_MENTOR for s in set(p.stack + p.target.skills))
    for topic, n in topic_demand.most_common():
        if n >= MIN_TOPIC_DEMAND and mentors[topic] * 2 < n:
            insights.append({"kind": "mentor_gap", "severity": 1 - mentors[topic] / n,
                             "text": t["mentor_gap"].format(topic=topic, demand=n, supply=mentors[topic])})
    insights.sort(key=lambda i: -i["severity"])
    insights = insights[:MAX_INSIGHTS - 1]
    if domains:
        domain, count = domains.most_common(1)[0]
        insights.append({"kind": "top_domain", "severity": 0.0,
                         "text": t["top_domain"].format(domain=DOMAIN_LABELS[domain][lang], count=count)})

    plan = schedule(profiles, slots=SLOTS)
    met = {p.id for slot in plan for m in slot for p in (m.a, m.b)}
    slots = [{
        "time": f"{(START_MIN + i * SLOT_MIN) // 60:02d}:{(START_MIN + i * SLOT_MIN) % 60:02d}",
        "meetings": [{"a_id": m.a.id, "b_id": m.b.id, "a": m.a.name, "a_role": ROLE_LABELS[m.a.role][lang], "b": m.b.name,
                      "b_role": ROLE_LABELS[m.b.role][lang], "score": round(m.score * 100), "zone": m.zone}
                     for m in slot],
    } for i, slot in enumerate(plan)]

    return Dashboard(
        slots=slots,
        scheduled=round(len(met) / len(profiles), 3) if profiles else 0.0,
        participants=len(profiles),
        goals=[{"goal": g, "label": GOAL_LABELS[g][lang], "count": goals[g]} for g in Goal],
        roles=[{"role": r, "label": ROLE_LABELS[r][lang], "seekers": seekers[r], "openings": openings[r]}
               for r in roles],
        skills=[{"skill": s, "demand": demand[s], "supply": supply[s]} for s in skills],
        domains=[{"domain": d, "label": DOMAIN_LABELS[d][lang], "count": c} for d, c in domains.most_common(TOP)],
        points=[{"id": p.id, "name": p.name, "role": ROLE_LABELS[p.role][lang], "goal": p.goal,
                 "goal_label": GOAL_STATUS[p.goal][lang], "market": MARKET[p.goal][0], "side": MARKET[p.goal][1],
                 "x": round(float(x), 4), "y": round(float(y), 4)} for p, (x, y) in zip(profiles, coords)],
        insights=[{"kind": i["kind"], "text": i["text"]} for i in insights],
        hirers=goals[Goal.HIRE],
        openings=sum(openings.values()),
        well_matched=round(_well_matched(profiles), 3),
    )
