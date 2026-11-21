"""Схемы запросов и ответов API.

В карточку рекомендации не попадают контакты (Telegram) и приметы («как меня
узнать»): ими участники обмениваются только после взаимного согласия.
"""

from pydantic import BaseModel, Field

from kopir.models import Profile
from kopir.taxonomy import Lang


class RecommendRequest(BaseModel):
    profile: Profile
    lang: Lang | None = Field(None, description="язык объяснений; по умолчанию — язык анкеты")
    k: int = Field(5, ge=1, le=20)
    exclude: list[str] = Field(default_factory=list, description="id уже показанных людей («показать ещё»)")
    join: bool = Field(False, description="добавить анкету в зал, чтобы её рекомендовали другим")


class Option(BaseModel):
    value: str
    label: str


class OptionsResponse(BaseModel):
    goals: list[Option]
    roles: list[Option]
    levels: list[Option]
    domains: list[Option]
    skills: list[str]


class Candidate(BaseModel):
    id: str
    name: str
    goal: str
    goal_label: str
    role_label: str
    level_label: str
    years: float
    city: str
    company: str | None
    about: str


class ExplanationOut(BaseModel):
    label_you: str
    for_me: str
    label_them: str
    for_them: str
    shared: dict[str, list[str]]
    warnings: list[str]
    icebreaker: str


class Recommendation(BaseModel):
    candidate: Candidate
    score: int = Field(ge=0, le=100, description="взаимное совпадение, %")
    weak: bool
    explanation: ExplanationOut


class RecommendResponse(BaseModel):
    profile_id: str
    lang: Lang
    recommendations: list[Recommendation]
    elapsed_ms: float


class HealthResponse(BaseModel):
    status: str
    profiles: int
