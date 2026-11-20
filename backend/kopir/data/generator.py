"""Генератор синтетического зала с управляемым покрытием.

Случайные анкеты дают перекос: много соискателей, мало нанимающих и кофаундеров,
вакансии не совпадают со стеками зала. Тогда анкета жюри получает слабую выдачу,
как бы хорош ни был алгоритм. Поэтому генератор моделирует реальное мероприятие:
- стеки взвешены по рынку (на Python пишут чаще, чем на C#);
- вакансии повторяют спрос зала: организатор зовёт компании, которым нужны эти люди;
- технари-кофаундеры чаще ищут бизнес и продакта, бизнес чаще ищет «любого технаря»;
- сферы взвешены по популярности.

Все имена, компании и контакты вымышлены. Генерация детерминирована (seed).
"""

import random
from collections import Counter
from typing import NamedTuple

from kopir.data.texts import about_text
from kopir.models import Profile, Target
from kopir.taxonomy import LEVEL_YEARS, Goal, Level

# Размер зала по умолчанию — из ТЗ: «на митапы приходит 300+ человек».
DEFAULT_SIZE = 300

GOAL_SHARE: dict[Goal, float] = {
    Goal.FIND_JOB: 0.22,
    Goal.HIRE: 0.16,
    Goal.FIND_MENTOR: 0.16,
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


class Family(NamedTuple):
    """Правдоподобный стек: ядро (оно же требования вакансии) и частые дополнения."""

    weight: float
    core: tuple[str, ...]
    extras: tuple[str, ...] = ()


STACK_FAMILIES: dict[str, tuple[Family, ...]] = {
    "backend": (
        Family(0.35, ("Python", "FastAPI", "PostgreSQL"), ("Django", "Redis", "Docker", "Kafka")),
        Family(0.20, ("Java", "Spring", "PostgreSQL"), ("Kafka", "Docker", "Kubernetes")),
        Family(0.20, ("Go", "PostgreSQL", "Docker"), ("Kafka", "Kubernetes", "Redis")),
        Family(0.15, ("Node.js", "TypeScript", "PostgreSQL"), ("MongoDB", "Redis", "Docker")),
        Family(0.10, ("C#", "PostgreSQL"), ("Docker", "Redis")),
    ),
    "frontend": (
        Family(0.65, ("JavaScript", "TypeScript", "React"), ("Next.js", "Figma")),
        Family(0.25, ("JavaScript", "Vue"), ("TypeScript", "Figma")),
        Family(0.10, ("TypeScript", "Angular"), ("JavaScript",)),
    ),
    "fullstack": (
        Family(0.6, ("TypeScript", "React", "Node.js"), ("Next.js", "PostgreSQL", "Docker")),
        Family(0.4, ("Python", "Django", "React"), ("PostgreSQL", "Docker")),
    ),
    "mobile": (
        Family(0.35, ("Flutter",), ("Kotlin", "Swift")),
        Family(0.30, ("Kotlin",), ("Java", "CI/CD")),
        Family(0.25, ("Swift",), ("CI/CD",)),
        Family(0.10, ("React Native", "TypeScript"), ("JavaScript",)),
    ),
    "ml": (
        Family(0.45, ("Python", "PyTorch", "LLM"), ("NLP", "Docker", "Computer Vision")),
        Family(0.30, ("Python", "PyTorch", "Computer Vision"), ("TensorFlow", "Docker")),
        Family(0.25, ("Python", "TensorFlow", "NLP"), ("LLM", "Docker")),
    ),
    "data_science": (Family(1.0, ("Python", "scikit-learn", "SQL"), ("PyTorch", "NLP", "Excel")),),
    "data_engineer": (
        Family(0.6, ("Python", "SQL", "Airflow"), ("Spark", "Kafka", "AWS")),
        Family(0.4, ("Spark", "SQL", "Kafka"), ("Python", "AWS")),
    ),
    "analyst": (
        Family(0.6, ("SQL", "Power BI"), ("Excel", "Python")),
        Family(0.4, ("SQL", "Python", "Tableau"), ("Excel",)),
    ),
    "devops": (
        Family(0.6, ("Docker", "Kubernetes", "CI/CD"), ("Terraform", "AWS", "Linux")),
        Family(0.4, ("Linux", "Docker", "Terraform"), ("GCP", "AWS", "Kubernetes")),
    ),
    "qa": (
        Family(0.5, ("Selenium", "Java"), ("SQL",)),
        Family(0.5, ("Playwright", "Python"), ("SQL",)),
    ),
    "security": (Family(1.0, ("Pentest", "Linux"), ("Python", "Kubernetes")),),
    "gamedev": (Family(0.7, ("Unity", "C#")), Family(0.3, ("Unreal", "C++"))),
    "embedded": (Family(1.0, ("C", "C++", "RTOS"), ("Rust", "Linux")),),
    "product": (Family(1.0, ("Product Management", "UX Research"), ("Agile", "SQL", "Growth")),),
    "project": (Family(1.0, ("Agile", "Product Management"), ("Excel",)),),
    "designer": (Family(1.0, ("Figma", "UX Research")),),
    "business": (Family(1.0, ("Sales", "Fundraising"), ("Growth",)),),
    "marketing": (Family(1.0, ("Growth", "SMM"), ("SEO",)),),
    "recruiter": (Family(1.0, ("Recruiting", "Career")),),
}

# Куда хочет расти менти, помимо своего стека.
GROWTH_TOPICS: dict[str, tuple[str, ...]] = {
    "backend": ("System Design", "Kubernetes", "Kafka"),
    "frontend": ("System Design", "TypeScript", "Next.js"),
    "fullstack": ("System Design", "Docker"),
    "mobile": ("System Design", "CI/CD"),
    "ml": ("LLM", "System Design", "Docker"),
    "data_science": ("PyTorch", "LLM"),
    "data_engineer": ("Kafka", "Spark", "System Design"),
    "analyst": ("Python", "SQL"),
    "devops": ("Kubernetes", "Terraform"),
    "qa": ("Playwright", "Python"),
    "security": ("Pentest", "Kubernetes"),
    "gamedev": ("Unreal", "C++"),
    "embedded": ("Rust", "RTOS"),
    "product": ("Growth", "UX Research"),
    "project": ("Product Management", "Agile"),
    "designer": ("UX Research", "Product Management"),
    "marketing": ("Growth", "SEO"),
}
SOFT_TOPICS = ("Career", "Public Speaking")

# Популярность сфер среди стартапов и IT-команд.
HOT_DOMAINS: dict[str, float] = {
    "ai": 0.20, "fintech": 0.18, "edtech": 0.14, "ecommerce": 0.12, "healthtech": 0.09,
    "govtech": 0.08, "logistics": 0.07, "agrotech": 0.06, "greentech": 0.06,
}
ALL_DOMAINS: dict[str, float] = HOT_DOMAINS | {
    "gaming": 0.04, "telecom": 0.04, "media": 0.04, "cybersecurity": 0.04, "proptech": 0.02,
}

COFOUNDER_TECH: dict[str, float] = {"backend": 0.30, "fullstack": 0.25, "ml": 0.20, "mobile": 0.15, "frontend": 0.10}
COFOUNDER_BIZ: dict[str, float] = {"business": 0.45, "product": 0.30, "designer": 0.15, "marketing": 0.10}
# Доля бизнесовых кофаундеров, которым подойдёт любой технический партнёр («ищу CTO»).
BIZ_WANTS_ANY_TECH = 0.6
# Вакансий на каждую роль, которую ищет хотя бы один соискатель.
MIN_VACANCIES_PER_ROLE = 2

# (кириллица, латиница для вымышленного @handle)
FIRST_NAMES: tuple[tuple[str, str], ...] = (
    ("Айгерім", "aigerim"), ("Арман", "arman"), ("Дана", "dana"), ("Ерлан", "erlan"),
    ("Мадина", "madina"), ("Нұрлан", "nurlan"), ("Аружан", "aruzhan"), ("Данияр", "daniyar"),
    ("Әлия", "aliya"), ("Тимур", "timur"), ("Жанар", "zhanar"), ("Санжар", "sanzhar"),
    ("Әсел", "asel"), ("Бауыржан", "baurzhan"), ("Диана", "diana"), ("Әли", "ali"),
    ("Камила", "kamila"), ("Ернар", "ernar"), ("Томирис", "tomiris"), ("Алихан", "alikhan"),
    ("Дильназ", "dilnaz"), ("Мирас", "miras"), ("Інжу", "inzhu"), ("Ақжол", "akzhol"),
    ("Анна", "anna"), ("Дмитрий", "dmitry"), ("Екатерина", "ekaterina"), ("Максим", "maxim"),
    ("Ольга", "olga"), ("Игорь", "igor"), ("Виктория", "victoria"), ("Артём", "artem"),
    ("Alex", "alex"), ("Emma", "emma"), ("Daniel", "daniel"), ("Sofia", "sofia"),
)
INITIALS = "АБГДЕЖКМНОРСТШ"

COMPANIES = (
    "Bürkit Systems", "Dalafy", "Shanyraq Cloud", "Steppewise", "Altynbit", "Nomadix Games",
    "Saryarqa MedTech", "Jibekline", "Aqqu Analytics", "Taldy Soft", "Kokzhiek Data", "Orda Logistics",
)

LANG_WEIGHTS = {"ru": 0.55, "kk": 0.25, "en": 0.20}
CITY_WEIGHTS = {"Алматы": 0.6, "Астана": 0.3, "Шымкент": 0.05, "Караганда": 0.05}

LOOKS_LIKE = {
    "ru": ("чёрное худи и очки", "белая футболка, рюкзак", "джинсовая куртка", "зелёный свитер",
           "кепка и наушники", "серый пиджак", "красная толстовка", "футболка с котом"),
    "kk": ("қара худи, көзілдірік", "ақ футболка, рюкзак", "джинсы куртка", "жасыл свитер",
           "кепка және құлаққап", "сұр пиджак", "қызыл толстовка"),
    "en": ("black hoodie and glasses", "white t-shirt, backpack", "denim jacket", "green sweater",
           "cap and headphones", "grey blazer", "red sweatshirt"),
}


class Demand(NamedTuple):
    """Кого ищут работу в зале: по этому спросу строятся вакансии."""

    role: str
    family: Family
    level: Level
    interests: list[str]


class Generator:
    def __init__(self, n: int = DEFAULT_SIZE, seed: int = 42) -> None:
        self.n = n
        self.rng = random.Random(seed)
        self.profiles: list[Profile] = []
        self.demand: list[Demand] = []

    # --- случайность с весами ---

    def _pick[T](self, weights: dict[T, float]) -> T:
        return self.rng.choices(list(weights), weights=list(weights.values()))[0]

    def _sample[T](self, weights: dict[T, float], k: int) -> list[T]:
        """Выборка k разных элементов с учётом весов."""
        pool = dict(weights)
        picked = []
        for _ in range(min(k, len(pool))):
            item = self._pick(pool)
            picked.append(item)
            del pool[item]
        return picked

    # --- общие части анкеты ---

    def _years(self, level: Level) -> float:
        lo, hi = LEVEL_YEARS[level]
        return round(self.rng.uniform(lo, hi) * 2) / 2

    def _family(self, role: str) -> Family:
        families = STACK_FAMILIES[role]
        return self.rng.choices(families, weights=[f.weight for f in families])[0]

    def _stack(self, family: Family) -> list[str]:
        extras = self.rng.sample(family.extras, k=min(len(family.extras), self.rng.randint(0, 2)))
        return [*family.core, *extras]

    def _interests(self, k_max: int = 3, weights: dict[str, float] = ALL_DOMAINS) -> list[str]:
        return self._sample(weights, self.rng.randint(1, k_max))

    def _add(self, *, role: str, level: Level, goal: Goal, target: Target, stack: list[str] | None = None,
             interests: list[str] | None = None, company: str | None = None) -> Profile:
        idx = len(self.profiles) + 1
        first, latin = self.rng.choice(FIRST_NAMES)
        lang = self._pick(LANG_WEIGHTS)
        profile = Profile(
            id=f"p{idx:03d}",
            name=f"{first} {self.rng.choice(INITIALS)}.",
            telegram=f"@{latin}_{idx:03d}",
            lang=lang,
            city=self._pick(CITY_WEIGHTS),
            role=role,
            level=level,
            years=self._years(level),
            stack=stack if stack is not None else self._stack(self._family(role)),
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
            role, level = self._pick(ROLE_WEIGHTS), self._pick(levels)
            family, interests = self._family(role), self._interests()
            self.demand.append(Demand(role, family, level, interests))
            self._add(role=role, level=level, goal=Goal.FIND_JOB, stack=self._stack(family),
                      interests=interests, target=Target(roles=[role], domains=interests))

    def _vacancy_level(self, wanted: Level) -> Level:
        """Чаще ровно нужный уровень, иначе соседний, но не выше Senior."""
        if self.rng.random() < 0.6:
            return wanted
        order = [Level.INTERN, Level.JUNIOR, Level.MIDDLE, Level.SENIOR]
        i = order.index(wanted) + self.rng.choice((-1, 1))
        return order[max(0, min(i, len(order) - 1))]

    def _hirers(self, count: int) -> None:
        """Каждая вакансия списана с реального соискателя в зале: роль, стек, уровень.

        Сначала каждая роль соискателей получает MIN_VACANCIES_PER_ROLE вакансий
        (от самых востребованных ролей к редким), остальные — пропорционально спросу.
        """
        by_role = Counter(d.role for d in self.demand)
        plan = [
            self.rng.choice([d for d in self.demand if d.role == role])
            for role, _ in by_role.most_common()
            for _ in range(MIN_VACANCIES_PER_ROLE)
        ][:count]
        plan += [self.rng.choice(self.demand) for _ in range(count - len(plan))]
        for d in plan:
            domain = self.rng.choice(d.interests) if self.rng.random() < 0.5 else self._pick(HOT_DOMAINS)
            who = self.rng.choice(("recruiter", "recruiter", d.role, "business"))
            self._add(role=who, level=self.rng.choice((Level.SENIOR, Level.LEAD)), goal=Goal.HIRE,
                      target=Target(roles=[d.role], skills=list(d.family.core),
                                    level=self._vacancy_level(d.level), domains=[domain]),
                      interests=[domain], company=self.rng.choice(COMPANIES))

    def _mentors(self, count: int) -> None:
        for _ in range(count):
            role = self._pick(ROLE_WEIGHTS)
            stack = self._stack(self._family(role))
            topics = [*stack[:2], *self.rng.sample(GROWTH_TOPICS[role], k=2), self.rng.choice(SOFT_TOPICS)]
            self._add(role=role, level=self.rng.choice((Level.SENIOR, Level.LEAD)), goal=Goal.BE_MENTOR,
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
            self._add(role=role, level=self._pick(levels), goal=Goal.FIND_MENTOR, target=Target(skills=topics))

    def _cofounder_needs(self, tech: bool) -> list[str]:
        if tech:
            optional = {"product": 0.6, "designer": 0.3, "marketing": 0.2}
            return ["business", *(r for r, p in optional.items() if self.rng.random() < p)]
        if self.rng.random() < BIZ_WANTS_ANY_TECH:
            return list(COFOUNDER_TECH)
        return self._sample(COFOUNDER_TECH, self.rng.randint(2, 3))

    def _cofounders(self, count: int) -> None:
        """Половина технари, половина бизнес; сферы взвешены по популярности."""
        for i in range(count):
            tech = i % 2 == 0
            role = self._pick(COFOUNDER_TECH if tech else COFOUNDER_BIZ)
            domains = self._interests(weights=HOT_DOMAINS)
            self._add(role=role, level=self.rng.choice((Level.MIDDLE, Level.SENIOR, Level.LEAD)),
                      goal=Goal.FIND_COFOUNDER, interests=domains,
                      target=Target(roles=self._cofounder_needs(tech), domains=domains))

    def _exchangers(self, count: int) -> None:
        levels = {Level.JUNIOR: 0.2, Level.MIDDLE: 0.4, Level.SENIOR: 0.3, Level.LEAD: 0.1}
        for _ in range(count):
            role = self._pick(ROLE_WEIGHTS)
            stack = self._stack(self._family(role))
            interests = self._interests(k_max=2, weights=HOT_DOMAINS)
            topics = [*stack[:2], self.rng.choice(GROWTH_TOPICS[role])]
            self._add(role=role, level=self._pick(levels), goal=Goal.SHARE_EXPERIENCE, stack=stack,
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


def generate(n: int = DEFAULT_SIZE, seed: int = 42) -> list[Profile]:
    return Generator(n, seed).run()
