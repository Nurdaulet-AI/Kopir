"""Анкета участника.

Анкета состоит из двух частей:
- «кто я» — роль, уровень, опыт, стек, интересы;
- «кого/что ищу». Его смысл задаёт цель: ищущий ментора называет темы,
  кофаундер — нужные роли (`target`). Нанимающий перечисляет открытые
  вакансии (`openings`): на митап компании обычно приходят с несколькими.
Из этих двух частей подбор считает, полезен ли человек B человеку A и наоборот.
"""

from typing import Self
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from kopir.taxonomy import DOMAINS, ROLES, Goal, Lang, Level, normalize_skills


def new_profile_id() -> str:
    return f"u{uuid4().hex[:10]}"


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
    id: str = Field(default_factory=new_profile_id)
    name: str
    telegram: str | None = None
    lang: Lang = "ru"
    city: str = "Алматы"

    role: str
    level: Level
    years: float = Field(ge=0, le=50)
    stack: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    about: str = ""

    goal: Goal
    target: Target = Field(default_factory=Target)
    openings: list[Target] = Field(default_factory=list)  # вакансии нанимающего
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

    @model_validator(mode="after")
    def _openings_belong_to_hirers(self) -> Self:
        """У нанимающего есть хотя бы одна вакансия; у остальных вакансий нет.

        Короткая форма с одной вакансией в `target` переносится в `openings`,
        чтобы дальше по коду у нанимающего был один источник правды.
        """
        if self.goal != Goal.HIRE:
            if self.openings:
                raise ValueError("вакансии бывают только у нанимающих")
            return self
        if not self.openings and self.target.roles:
            self.openings = [self.target]
            self.target = Target()
        if not self.openings or not all(o.roles for o in self.openings):
            raise ValueError("у нанимающего должна быть хотя бы одна вакансия с ролью")
        return self
