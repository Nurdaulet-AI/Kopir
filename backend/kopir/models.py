"""Анкета участника.

Анкета состоит из двух частей:
- «кто я» — роль, уровень, опыт, стек, интересы;
- `target` — «кого/что ищу». Его смысл задаёт цель:
  нанимающий описывает вакансию, ищущий ментора — темы, кофаундер — нужные роли.
Из этих двух частей подбор считает, полезен ли человек B человеку A и наоборот.
"""

from pydantic import BaseModel, Field, field_validator

from kopir.taxonomy import DOMAINS, ROLES, Goal, Level, normalize_skills


class Target(BaseModel):
    """Кого или что ищет участник. Пустое поле означает «неважно»."""

    roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    level: Level | None = None
    domains: list[str] = Field(default_factory=list)

    @field_validator("roles")
    @classmethod
    def _known_roles(cls, v: list[str]) -> list[str]:
        return [r for r in v if r in ROLES]

    @field_validator("skills")
    @classmethod
    def _normalize(cls, v: list[str]) -> list[str]:
        return normalize_skills(v)

    @field_validator("domains")
    @classmethod
    def _known_domains(cls, v: list[str]) -> list[str]:
        return [d for d in v if d in DOMAINS]


class Profile(BaseModel):
    id: str
    name: str
    telegram: str | None = None
    lang: str = "ru"
    city: str = "Алматы"

    role: str
    level: Level
    years: float = Field(ge=0, le=50)
    stack: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    about: str = ""

    goal: Goal
    target: Target = Field(default_factory=Target)
    company: str | None = None  # для нанимающих: вымышленное название компании
    looks_like: str | None = None  # «как меня узнать в зале»

    @field_validator("role")
    @classmethod
    def _known_role(cls, v: str) -> str:
        if v not in ROLES:
            raise ValueError(f"неизвестная роль: {v}")
        return v

    @field_validator("stack")
    @classmethod
    def _normalize_stack(cls, v: list[str]) -> list[str]:
        return normalize_skills(v)

    @field_validator("interests")
    @classmethod
    def _known_interests(cls, v: list[str]) -> list[str]:
        return [d for d in v if d in DOMAINS]
