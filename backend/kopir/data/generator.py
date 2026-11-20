"""Генератор синтетических анкет с управляемым покрытием.

Случайные анкеты от LLM дают перекос: много соискателей, мало нанимающих и
кофаундеров. Тогда любая нишевая анкета жюри получает плохую выдачу, как бы хорош
ни был алгоритм. Поэтому генератор работает по квотам и гарантирует встречную сторону:
- на каждую роль соискателей есть хотя бы одна вакансия;
- темы менти покрыты темами менторов;
- у технических кофаундеров есть бизнесовые с общими сферами, и наоборот.

Все имена, компании и контакты вымышлены. Генерация детерминирована (seed).
"""

import random
from collections import Counter

from kopir.data.texts import about_text
from kopir.models import Profile, Target
from kopir.taxonomy import LEVEL_YEARS, Goal, Level

GOAL_SHARE: dict[Goal, float] = {
    Goal.FIND_JOB: 0.24,
    Goal.HIRE: 0.13,
    Goal.FIND_MENTOR: 0.17,
    Goal.BE_MENTOR: 0.12,
    Goal.FIND_COFOUNDER: 0.16,
    Goal.SHARE_EXPERIENCE: 0.18,
}

# Роли тех, кто ищет работу, менторов или обмен опытом.
ROLE_WEIGHTS: dict[str, float] = {
    "backend": 0.18, "frontend": 0.12, "fullstack": 0.06, "mobile": 0.07, "ml": 0.08,
    "data_science": 0.05, "data_engineer": 0.04, "analyst": 0.07, "devops": 0.06,
    "qa": 0.06, "security": 0.03, "gamedev": 0.02, "embedded": 0.02, "product": 0.05,
    "project": 0.02, "designer": 0.05, "marketing": 0.02,
}

# Правдоподобные стеки: ядро семейства + возможные дополнения.
STACK_FAMILIES: dict[str, list[tuple[list[str], list[str]]]] = {
    "backend": [
        (["Python", "FastAPI", "PostgreSQL"], ["Django", "Redis", "Docker", "Kafka"]),
        (["Go", "PostgreSQL", "Docker"], ["Kafka", "Kubernetes", "Redis"]),
        (["Java", "Spring", "PostgreSQL"], ["Kafka", "Docker", "Kubernetes"]),
        (["C#", "PostgreSQL"], ["Docker", "Redis"]),
        (["Node.js", "TypeScript", "PostgreSQL"], ["MongoDB", "Redis", "Docker"]),
    ],
    "frontend": [
        (["JavaScript", "TypeScript", "React"], ["Next.js", "Figma"]),
        (["JavaScript", "Vue"], ["TypeScript", "Figma"]),
        (["TypeScript", "Angular"], ["JavaScript"]),
    ],
    "fullstack": [
        (["TypeScript", "React", "Node.js"], ["Next.js", "PostgreSQL", "Docker"]),
        (["Python", "Django", "React"], ["PostgreSQL", "Docker"]),
    ],
    "mobile": [
        (["Kotlin"], ["Java", "CI/CD"]),
        (["Swift"], ["CI/CD"]),
        (["Flutter"], ["Kotlin", "Swift"]),
        (["React Native", "TypeScript"], ["JavaScript"]),
    ],
    "ml": [
        (["Python", "PyTorch", "LLM"], ["NLP", "Docker", "Computer Vision"]),
        (["Python", "PyTorch", "Computer Vision"], ["TensorFlow", "Docker"]),
        (["Python", "TensorFlow", "NLP"], ["LLM", "Docker"]),
    ],
    "data_science": [(["Python", "scikit-learn", "SQL"], ["PyTorch", "NLP", "Excel"])],
    "data_engineer": [
        (["Python", "SQL", "Airflow"], ["Spark", "Kafka", "AWS"]),
        (["Spark", "SQL", "Kafka"], ["Python", "AWS"]),
    ],
    "analyst": [
        (["SQL", "Power BI"], ["Excel", "Python"]),
        (["SQL", "Python", "Tableau"], ["Excel"]),
    ],
    "devops": [
        (["Docker", "Kubernetes", "CI/CD"], ["Terraform", "AWS", "Linux"]),
        (["Linux", "Docker", "Terraform"], ["GCP", "AWS", "Kubernetes"]),
    ],
    "qa": [
        (["Selenium", "Java"], ["SQL"]),
        (["Playwright", "Python"], ["SQL"]),
    ],
    "security": [(["Pentest", "Linux"], ["Python", "Kubernetes"])],
    "gamedev": [(["Unity", "C#"], []), (["Unreal", "C++"], [])],
    "embedded": [(["C", "C++", "RTOS"], ["Rust", "Linux"])],
    "product": [(["Product Management", "UX Research"], ["Agile", "SQL", "Growth"])],
    "project": [(["Agile", "Product Management"], ["Excel"])],
    "designer": [(["Figma", "UX Research"], [])],
    "business": [(["Sales", "Fundraising"], ["Growth"])],
    "marketing": [(["Growth", "SMM"], ["SEO"])],
    "recruiter": [(["Recruiting", "Career"], [])],
}

# Куда хочет расти менти, помимо своего стека.
GROWTH_TOPICS: dict[str, list[str]] = {
    "backend": ["System Design", "Kubernetes", "Kafka"],
    "frontend": ["System Design", "TypeScript", "Next.js"],
    "fullstack": ["System Design", "Docker"],
    "mobile": ["System Design", "CI/CD"],
    "ml": ["LLM", "System Design", "Docker"],
    "data_science": ["PyTorch", "LLM"],
    "data_engineer": ["Kafka", "Spark", "System Design"],
    "analyst": ["Python", "SQL"],
    "devops": ["Kubernetes", "Terraform"],
    "qa": ["Playwright", "Python"],
    "security": ["Pentest", "Kubernetes"],
    "gamedev": ["Unreal", "C++"],
    "embedded": ["Rust", "RTOS"],
    "product": ["Growth", "UX Research"],
    "project": ["Product Management", "Agile"],
    "designer": ["UX Research", "Product Management"],
    "marketing": ["Growth", "SEO"],
}
SOFT_TOPICS = ["Career", "Public Speaking"]

HOT_DOMAINS = ["fintech", "edtech", "ai", "healthtech", "ecommerce", "agrotech", "logistics", "govtech", "greentech"]
ALL_DOMAINS = HOT_DOMAINS + ["gaming", "telecom", "media", "cybersecurity", "proptech"]

COFOUNDER_TECH = ["backend", "fullstack", "ml", "mobile", "frontend"]
COFOUNDER_BIZ = ["business", "product", "marketing", "designer"]

# (кириллица, латиница для вымышленного @handle)
FIRST_NAMES: list[tuple[str, str]] = [
    ("Айгерім", "aigerim"), ("Арман", "arman"), ("Дана", "dana"), ("Ерлан", "erlan"),
    ("Мадина", "madina"), ("Нұрлан", "nurlan"), ("Аружан", "aruzhan"), ("Данияр", "daniyar"),
    ("Әлия", "aliya"), ("Тимур", "timur"), ("Жанар", "zhanar"), ("Санжар", "sanzhar"),
    ("Әсел", "asel"), ("Бауыржан", "baurzhan"), ("Диана", "diana"), ("Әли", "ali"),
    ("Камила", "kamila"), ("Ернар", "ernar"), ("Томирис", "tomiris"), ("Алихан", "alikhan"),
    ("Дильназ", "dilnaz"), ("Мирас", "miras"), ("Інжу", "inzhu"), ("Ақжол", "akzhol"),
    ("Анна", "anna"), ("Дмитрий", "dmitry"), ("Екатерина", "ekaterina"), ("Максим", "maxim"),
    ("Ольга", "olga"), ("Игорь", "igor"), ("Виктория", "victoria"), ("Артём", "artem"),
    ("Alex", "alex"), ("Emma", "emma"), ("Daniel", "daniel"), ("Sofia", "sofia"),
]
INITIALS = "АБГДЕЖКМНОРСТШ"

COMPANIES = [
    "Bürkit Systems", "Dalafy", "Shanyraq Cloud", "Steppewise", "Altynbit", "Nomadix Games",
    "Saryarqa MedTech", "Jibekline", "Aqqu Analytics", "Taldy Soft", "Kokzhiek Data", "Orda Logistics",
]

LANG_WEIGHTS = {"ru": 0.55, "kk": 0.25, "en": 0.20}
CITY_WEIGHTS = {"Алматы": 0.6, "Астана": 0.3, "Шымкент": 0.05, "Караганда": 0.05}

LOOKS_LIKE = {
    "ru": ["чёрное худи и очки", "белая футболка, рюкзак", "джинсовая куртка", "зелёный свитер",
           "кепка и наушники", "серый пиджак", "красная толстовка", "футболка с котом"],
    "kk": ["қара худи, көзілдірік", "ақ футболка, рюкзак", "джинсы куртка", "жасыл свитер",
           "кепка және құлаққап", "сұр пиджак", "қызыл толстовка"],
    "en": ["black hoodie and glasses", "white t-shirt, backpack", "denim jacket", "green sweater",
           "cap and headphones", "grey blazer", "red sweatshirt"],
}


def _pick(rng: random.Random, weights: dict) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


class Generator:
    def __init__(self, n: int = 200, seed: int = 42) -> None:
        self.n = n
        self.rng = random.Random(seed)
        self.profiles: list[Profile] = []

    # --- общие части анкеты ---

    def _years(self, level: Level) -> float:
        lo, hi = LEVEL_YEARS[level]
        return round(self.rng.uniform(lo, hi) * 2) / 2

    def _stack(self, role: str) -> tuple[list[str], list[str]]:
        """Стек участника и ядро его семейства (ядро = типичные требования вакансии)."""
        core, extras = self.rng.choice(STACK_FAMILIES[role])
        stack = core + self.rng.sample(extras, k=min(len(extras), self.rng.randint(0, 2)))
        return stack, core

    def _interests(self, k_max: int = 3, pool: list[str] = ALL_DOMAINS) -> list[str]:
        return self.rng.sample(pool, k=self.rng.randint(1, k_max))

    def _add(self, *, role: str, level: Level, goal: Goal, target: Target, stack: list[str] | None = None,
             interests: list[str] | None = None, company: str | None = None) -> Profile:
        idx = len(self.profiles) + 1
        first, latin = self.rng.choice(FIRST_NAMES)
        lang = _pick(self.rng, LANG_WEIGHTS)
        stack = stack if stack is not None else self._stack(role)[0]
        profile = Profile(
            id=f"p{idx:03d}",
            name=f"{first} {self.rng.choice(INITIALS)}.",
            telegram=f"@{latin}_{idx:03d}",
            lang=lang,
            city=_pick(self.rng, CITY_WEIGHTS),
            role=role,
            level=level,
            years=self._years(level),
            stack=stack,
            interests=interests if interests is not None else self._interests(),
            goal=goal,
            target=target,
            company=company,
            looks_like=self.rng.choice(LOOKS_LIKE[lang]),
        )
        profile.about = about_text(profile, self.rng)
        self.profiles.append(profile)
        return profile

    # --- цели ---

    def _job_seekers(self, count: int) -> None:
        levels = {Level.INTERN: 0.15, Level.JUNIOR: 0.35, Level.MIDDLE: 0.35, Level.SENIOR: 0.15}
        for _ in range(count):
            role = _pick(self.rng, ROLE_WEIGHTS)
            interests = self._interests()
            self._add(role=role, level=_pick(self.rng, levels), goal=Goal.FIND_JOB,
                      target=Target(roles=[role], domains=interests), interests=interests)

    def _hirers(self, count: int) -> None:
        """Вакансии повторяют распределение ролей соискателей: у каждой роли есть спрос."""
        seekers = [p for p in self.profiles if p.goal == Goal.FIND_JOB]
        demand = Counter(p.role for p in seekers)
        roles = [r for r, _ in demand.most_common()][:count]
        while len(roles) < count:
            roles.append(self.rng.choices(list(demand), weights=list(demand.values()))[0])
        for vacancy in roles:
            _, core = self._stack(vacancy)
            levels = Counter(p.level for p in seekers if p.role == vacancy) or Counter({Level.MIDDLE: 1})
            level = self.rng.choices(list(levels), weights=list(levels.values()))[0]
            domain = self.rng.choice(HOT_DOMAINS)
            who = self.rng.choice(["recruiter", "recruiter", vacancy, "business"])
            self._add(role=who, level=self.rng.choice([Level.SENIOR, Level.LEAD]), goal=Goal.HIRE,
                      target=Target(roles=[vacancy], skills=core, level=level, domains=[domain]),
                      interests=[domain], company=self.rng.choice(COMPANIES))

    def _mentors(self, count: int) -> None:
        for _ in range(count):
            role = _pick(self.rng, ROLE_WEIGHTS)
            stack, _ = self._stack(role)
            topics = stack[:2] + self.rng.sample(GROWTH_TOPICS[role], k=2) + self.rng.sample(SOFT_TOPICS, k=1)
            self._add(role=role, level=self.rng.choice([Level.SENIOR, Level.LEAD]), goal=Goal.BE_MENTOR,
                      stack=stack, target=Target(skills=list(dict.fromkeys(topics))))

    def _mentees(self, count: int) -> None:
        """Роли менти берём из ролей менторов, чтобы у каждого был кто-то по теме."""
        mentor_roles = [p.role for p in self.profiles if p.goal == Goal.BE_MENTOR]
        levels = {Level.INTERN: 0.25, Level.JUNIOR: 0.5, Level.MIDDLE: 0.25}
        for _ in range(count):
            role = self.rng.choice(mentor_roles)
            topics = self.rng.sample(GROWTH_TOPICS[role], k=self.rng.randint(1, 2))
            if self.rng.random() < 0.3:
                topics.append(self.rng.choice(SOFT_TOPICS))
            self._add(role=role, level=_pick(self.rng, levels), goal=Goal.FIND_MENTOR,
                      target=Target(skills=topics))

    def _cofounders(self, count: int) -> None:
        """Половина технари, половина бизнес; сферы из общего «горячего» набора."""
        for i in range(count):
            tech = i % 2 == 0
            role = self.rng.choice(COFOUNDER_TECH if tech else COFOUNDER_BIZ)
            need = self.rng.sample(COFOUNDER_BIZ if tech else COFOUNDER_TECH, k=2)
            domains = self.rng.sample(HOT_DOMAINS, k=self.rng.randint(1, 2))
            self._add(role=role, level=self.rng.choice([Level.MIDDLE, Level.SENIOR, Level.LEAD]),
                      goal=Goal.FIND_COFOUNDER, interests=domains, target=Target(roles=need, domains=domains))

    def _exchangers(self, count: int) -> None:
        levels = {Level.JUNIOR: 0.2, Level.MIDDLE: 0.4, Level.SENIOR: 0.3, Level.LEAD: 0.1}
        for _ in range(count):
            role = _pick(self.rng, ROLE_WEIGHTS)
            stack, _ = self._stack(role)
            interests = self._interests(k_max=2, pool=HOT_DOMAINS)
            topics = stack[:2] + self.rng.sample(GROWTH_TOPICS[role], k=1)
            self._add(role=role, level=_pick(self.rng, levels), goal=Goal.SHARE_EXPERIENCE, stack=stack,
                      interests=interests, target=Target(skills=list(dict.fromkeys(topics)), domains=interests))

    def run(self) -> list[Profile]:
        counts = {g: round(self.n * share) for g, share in GOAL_SHARE.items()}
        counts[Goal.FIND_JOB] += self.n - sum(counts.values())
        # Порядок важен: вакансии строятся по соискателям, менти — по менторам.
        self._job_seekers(counts[Goal.FIND_JOB])
        self._hirers(counts[Goal.HIRE])
        self._mentors(counts[Goal.BE_MENTOR])
        self._mentees(counts[Goal.FIND_MENTOR])
        self._cofounders(counts[Goal.FIND_COFOUNDER])
        self._exchangers(counts[Goal.SHARE_EXPERIENCE])
        return self.profiles


def generate(n: int = 200, seed: int = 42) -> list[Profile]:
    return Generator(n, seed).run()
