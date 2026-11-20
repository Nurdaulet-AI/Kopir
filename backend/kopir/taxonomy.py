"""Единый словарь Kópir: цели, роли, уровни, навыки и сферы.

Анкеты хранятся в канонических ключах (`backend`, `Python`, `fintech`),
поэтому анкету на казахском можно сравнить с анкетой на английском без перевода.
Подписи на трёх языках нужны только для интерфейса и объяснений.
"""

from enum import StrEnum

Lang = str  # "ru" | "kk" | "en"
LANGS: tuple[Lang, ...] = ("ru", "kk", "en")


class Goal(StrEnum):
    FIND_JOB = "find_job"
    HIRE = "hire"
    FIND_MENTOR = "find_mentor"
    BE_MENTOR = "be_mentor"
    FIND_COFOUNDER = "find_cofounder"
    SHARE_EXPERIENCE = "share_experience"


GOAL_LABELS: dict[Goal, dict[Lang, str]] = {
    Goal.FIND_JOB: {"ru": "Найти работу", "kk": "Жұмыс табу", "en": "Find a job"},
    Goal.HIRE: {"ru": "Нанять", "kk": "Қызметкер жалдау", "en": "Hire"},
    Goal.FIND_MENTOR: {"ru": "Найти ментора", "kk": "Тәлімгер табу", "en": "Find a mentor"},
    Goal.BE_MENTOR: {"ru": "Стать ментором", "kk": "Тәлімгер болу", "en": "Become a mentor"},
    Goal.FIND_COFOUNDER: {"ru": "Найти кофаундера", "kk": "Серіктес-құрылтайшы табу", "en": "Find a co-founder"},
    Goal.SHARE_EXPERIENCE: {"ru": "Обмен опытом", "kk": "Тәжірибе алмасу", "en": "Share experience"},
}

# Чья цель чьей полезна: COMPATIBLE[a][b] — насколько человек с целью b
# в принципе может дать то, за чем пришёл человек с целью a.
# Пары зеркальны: ищущему работу нужны нанимающие, а не другие соискатели.
COMPATIBLE: dict[Goal, dict[Goal, float]] = {
    Goal.FIND_JOB: {Goal.HIRE: 1.0},
    Goal.HIRE: {Goal.FIND_JOB: 1.0},
    Goal.FIND_MENTOR: {Goal.BE_MENTOR: 1.0},
    Goal.BE_MENTOR: {Goal.FIND_MENTOR: 1.0},
    Goal.FIND_COFOUNDER: {Goal.FIND_COFOUNDER: 1.0},
    Goal.SHARE_EXPERIENCE: {Goal.SHARE_EXPERIENCE: 1.0},
}


class Level(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"


LEVEL_ORDER: dict[Level, int] = {lvl: i for i, lvl in enumerate(Level)}

LEVEL_LABELS: dict[Level, dict[Lang, str]] = {
    Level.INTERN: {"ru": "Стажёр / студент", "kk": "Тағылымдамашы / студент", "en": "Intern / student"},
    Level.JUNIOR: {"ru": "Junior", "kk": "Junior", "en": "Junior"},
    Level.MIDDLE: {"ru": "Middle", "kk": "Middle", "en": "Middle"},
    Level.SENIOR: {"ru": "Senior", "kk": "Senior", "en": "Senior"},
    Level.LEAD: {"ru": "Lead / руководитель", "kk": "Lead / жетекші", "en": "Lead / head"},
}

# Типичный опыт в годах — для генератора и проверки «ментор опытнее менти».
LEVEL_YEARS: dict[Level, tuple[int, int]] = {
    Level.INTERN: (0, 1),
    Level.JUNIOR: (1, 2),
    Level.MIDDLE: (2, 5),
    Level.SENIOR: (5, 9),
    Level.LEAD: (7, 15),
}

ROLE_LABELS: dict[str, dict[Lang, str]] = {
    "backend": {"ru": "Backend-разработчик", "kk": "Backend-әзірлеуші", "en": "Backend developer"},
    "frontend": {"ru": "Frontend-разработчик", "kk": "Frontend-әзірлеуші", "en": "Frontend developer"},
    "fullstack": {"ru": "Fullstack-разработчик", "kk": "Fullstack-әзірлеуші", "en": "Fullstack developer"},
    "mobile": {"ru": "Мобильный разработчик", "kk": "Мобильді әзірлеуші", "en": "Mobile developer"},
    "ml": {"ru": "ML-инженер", "kk": "ML-инженер", "en": "ML engineer"},
    "data_science": {"ru": "Data Scientist", "kk": "Data Scientist", "en": "Data scientist"},
    "data_engineer": {"ru": "Data-инженер", "kk": "Data-инженер", "en": "Data engineer"},
    "analyst": {"ru": "Аналитик данных", "kk": "Деректер талдаушысы", "en": "Data analyst"},
    "devops": {"ru": "DevOps-инженер", "kk": "DevOps-инженер", "en": "DevOps engineer"},
    "qa": {"ru": "QA-инженер", "kk": "QA-инженер", "en": "QA engineer"},
    "security": {"ru": "Специалист по кибербезопасности", "kk": "Киберқауіпсіздік маманы", "en": "Security engineer"},
    "gamedev": {"ru": "Gamedev-разработчик", "kk": "Ойын әзірлеуші", "en": "Game developer"},
    "embedded": {"ru": "Embedded-разработчик", "kk": "Embedded-әзірлеуші", "en": "Embedded developer"},
    "product": {"ru": "Продакт-менеджер", "kk": "Өнім менеджері", "en": "Product manager"},
    "project": {"ru": "Проджект-менеджер", "kk": "Жоба менеджері", "en": "Project manager"},
    "designer": {"ru": "UX/UI-дизайнер", "kk": "UX/UI-дизайнер", "en": "UX/UI designer"},
    "business": {"ru": "Бизнес / BizDev", "kk": "Бизнес / BizDev", "en": "Business / BizDev"},
    "marketing": {"ru": "Маркетолог", "kk": "Маркетолог", "en": "Marketer"},
    "recruiter": {"ru": "IT-рекрутер / HR", "kk": "IT-рекрутер / HR", "en": "IT recruiter / HR"},
}
ROLES: tuple[str, ...] = tuple(ROLE_LABELS)

# Технические роли против нетехнических: для кофаундеров важна взаимодополняемость.
TECH_ROLES = frozenset(
    {"backend", "frontend", "fullstack", "mobile", "ml", "data_science", "data_engineer",
     "devops", "qa", "security", "gamedev", "embedded", "analyst"}
)

DOMAIN_LABELS: dict[str, dict[Lang, str]] = {
    "fintech": {"ru": "FinTech", "kk": "FinTech", "en": "FinTech"},
    "edtech": {"ru": "EdTech", "kk": "EdTech", "en": "EdTech"},
    "govtech": {"ru": "GovTech", "kk": "GovTech", "en": "GovTech"},
    "ecommerce": {"ru": "E-commerce", "kk": "E-commerce", "en": "E-commerce"},
    "healthtech": {"ru": "HealthTech", "kk": "HealthTech", "en": "HealthTech"},
    "agrotech": {"ru": "AgroTech", "kk": "AgroTech", "en": "AgroTech"},
    "logistics": {"ru": "Логистика", "kk": "Логистика", "en": "Logistics"},
    "gaming": {"ru": "Игры", "kk": "Ойындар", "en": "Gaming"},
    "telecom": {"ru": "Телеком", "kk": "Телеком", "en": "Telecom"},
    "media": {"ru": "Медиа", "kk": "Медиа", "en": "Media"},
    "ai": {"ru": "AI / LLM", "kk": "AI / LLM", "en": "AI / LLM"},
    "cybersecurity": {"ru": "Кибербезопасность", "kk": "Киберқауіпсіздік", "en": "Cybersecurity"},
    "greentech": {"ru": "GreenTech", "kk": "GreenTech", "en": "GreenTech"},
    "proptech": {"ru": "PropTech", "kk": "PropTech", "en": "PropTech"},
}
DOMAINS: tuple[str, ...] = tuple(DOMAIN_LABELS)

# Канонический навык → варианты написания, которые встречаются в анкетах.
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python", "py", "питон", "пайтон"),
    "Go": ("go", "golang", "гоу"),
    "Java": ("java", "джава"),
    "Kotlin": ("kotlin", "котлин"),
    "Swift": ("swift", "свифт"),
    "JavaScript": ("javascript", "js", "джаваскрипт"),
    "TypeScript": ("typescript", "ts"),
    "C#": ("c#", "csharp", ".net", "dotnet"),
    "C++": ("c++", "cpp"),
    "Rust": ("rust", "раст"),
    "PHP": ("php", "laravel"),
    "React": ("react", "reactjs", "реакт"),
    "Vue": ("vue", "vuejs", "nuxt"),
    "Angular": ("angular",),
    "Next.js": ("next.js", "nextjs", "next"),
    "Node.js": ("node.js", "nodejs", "node", "nestjs"),
    "FastAPI": ("fastapi",),
    "Django": ("django", "джанго"),
    "Spring": ("spring", "spring boot"),
    "Flutter": ("flutter", "dart", "флаттер"),
    "React Native": ("react native", "rn"),
    "PostgreSQL": ("postgresql", "postgres", "постгрес"),
    "MongoDB": ("mongodb", "mongo"),
    "Redis": ("redis",),
    "Kafka": ("kafka", "кафка"),
    "SQL": ("sql",),
    "Docker": ("docker", "докер"),
    "Kubernetes": ("kubernetes", "k8s", "кубернетес"),
    "AWS": ("aws",),
    "GCP": ("gcp", "google cloud"),
    "Terraform": ("terraform",),
    "Linux": ("linux", "линукс"),
    "CI/CD": ("ci/cd", "cicd", "gitlab ci", "github actions"),
    "PyTorch": ("pytorch", "torch"),
    "TensorFlow": ("tensorflow", "tf"),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "LLM": ("llm", "gpt", "rag", "langchain"),
    "NLP": ("nlp",),
    "Computer Vision": ("computer vision", "cv", "opencv"),
    "Spark": ("spark", "pyspark"),
    "Airflow": ("airflow",),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Excel": ("excel",),
    "Figma": ("figma", "фигма"),
    "UX Research": ("ux research", "ux-research", "custdev", "касдев"),
    "Unity": ("unity", "юнити"),
    "Unreal": ("unreal", "unreal engine"),
    "Selenium": ("selenium",),
    "Playwright": ("playwright",),
    "Pentest": ("pentest", "pentesting", "пентест"),
    "C": ("c",),
    "RTOS": ("rtos", "freertos"),
    "System Design": ("system design", "системный дизайн"),
    "Product Management": ("product management", "продакт-менеджмент"),
    "Agile": ("agile", "scrum", "kanban"),
    "Growth": ("growth", "growth hacking", "гроус"),
    "SEO": ("seo",),
    "SMM": ("smm",),
    "Sales": ("sales", "продажи", "b2b sales"),
    "Fundraising": ("fundraising", "фандрейзинг", "инвестиции"),
    "Recruiting": ("recruiting", "рекрутинг", "найм"),
    "Career": ("career", "карьера"),
    "Public Speaking": ("public speaking", "выступления"),
}
SKILLS: tuple[str, ...] = tuple(SKILL_ALIASES)

# Нетехнические темы: полезны, но совпадение только по ним — слабый повод знакомиться.
SOFT_SKILLS = frozenset({"Career", "Public Speaking"})

_ALIAS_INDEX: dict[str, str] = {
    alias: canon for canon, aliases in SKILL_ALIASES.items() for alias in (canon.lower(), *aliases)
}


def normalize_skill(raw: str) -> str | None:
    """Приводит навык к каноническому виду: «golang» → «Go». Неизвестное → None."""
    return _ALIAS_INDEX.get(raw.strip().lower())


def normalize_skills(raw: list[str]) -> list[str]:
    """Нормализует список навыков, убирая неизвестные и дубликаты с сохранением порядка."""
    seen: dict[str, None] = {}
    for item in raw:
        canon = normalize_skill(item)
        if canon:
            seen.setdefault(canon, None)
    return list(seen)


# Типичный набор навыков для роли — основа генератора анкет.
ROLE_SKILLS: dict[str, tuple[str, ...]] = {
    "backend": ("Python", "Go", "Java", "C#", "Node.js", "FastAPI", "Django", "Spring",
                "PostgreSQL", "Redis", "Kafka", "Docker", "System Design"),
    "frontend": ("JavaScript", "TypeScript", "React", "Vue", "Angular", "Next.js", "Figma"),
    "fullstack": ("TypeScript", "React", "Next.js", "Node.js", "Python", "PostgreSQL", "Docker"),
    "mobile": ("Kotlin", "Swift", "Flutter", "React Native"),
    "ml": ("Python", "PyTorch", "TensorFlow", "LLM", "NLP", "Computer Vision", "Docker"),
    "data_science": ("Python", "scikit-learn", "SQL", "PyTorch", "NLP", "Excel"),
    "data_engineer": ("Python", "SQL", "Spark", "Airflow", "Kafka", "PostgreSQL", "AWS"),
    "analyst": ("SQL", "Python", "Power BI", "Tableau", "Excel"),
    "devops": ("Docker", "Kubernetes", "Terraform", "AWS", "GCP", "Linux", "CI/CD"),
    "qa": ("Selenium", "Playwright", "Python", "Java", "SQL"),
    "security": ("Pentest", "Linux", "Python", "Kubernetes"),
    "gamedev": ("Unity", "Unreal", "C#", "C++"),
    "embedded": ("C", "C++", "RTOS", "Rust", "Linux"),
    "product": ("Product Management", "UX Research", "Agile", "SQL", "Growth"),
    "project": ("Agile", "Product Management", "Excel"),
    "designer": ("Figma", "UX Research"),
    "business": ("Sales", "Fundraising", "Growth"),
    "marketing": ("Growth", "SEO", "SMM"),
    "recruiter": ("Recruiting", "Career"),
}
