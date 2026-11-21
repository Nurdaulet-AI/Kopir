"""HTTP API Kópir и раздача собранного веб-интерфейса.

    uv run uvicorn kopir.api.app:create_app --factory --port 8000

Документация с примерами — на /docs. Если задан `$KOPIR_WEB_DIR` (папка со
сборкой web/dist), сервер отдаёт интерфейс с того же адреса.
"""

import os
import threading
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from kopir.api.schemas import (
    BeaconOut,
    Candidate,
    Contact,
    IntroAnswer,
    IntroRequest,
    IntroView,
    JoinRequest,
    JoinResponse,
    LivePerson,
    LiveResponse,
    ParseRequest,
    SquadOut,
    SquadRequest,
    ExplanationOut,
    HealthResponse,
    Option,
    OptionsResponse,
    Recommendation,
    RecommendRequest,
    RecommendResponse,
)
from kopir import dashboard
from kopir.explain import explain
from kopir.hall import Hall
from kopir.matching.engine import Match
from kopir.matching.feedback import preference_factors
from kopir.meet import Intro
from kopir.voice import parse as parse_text
from kopir.models import Profile, new_profile_id
from kopir.taxonomy import DOMAIN_LABELS, GOAL_LABELS, GOAL_STATUS, LEVEL_LABELS, ROLE_LABELS, SKILLS, Goal, Lang, Level


def _candidate(p: Profile, lang: Lang) -> Candidate:
    return Candidate(
        id=p.id,
        name=p.name,
        goal=p.goal,
        goal_label=GOAL_STATUS[p.goal][lang],
        role_label=ROLE_LABELS[p.role][lang],
        level_label=LEVEL_LABELS[p.level][lang],
        years=p.years,
        city=p.city,
        company=p.company,
        about=p.about,
    )


def _recommendation(me: Profile, m: Match, lang: Lang, hall: Hall) -> Recommendation:
    return Recommendation(
        candidate=_candidate(m.profile, lang),
        score=round(m.score * 100),
        weak=m.weak,
        explanation=ExplanationOut(**asdict(explain(me, m, lang, rarity=hall.skill_count))),
    )


WEB_DIR_ENV = "KOPIR_WEB_DIR"
DASHBOARD_TTL_S = 30
# Режим бота на хостинге: webhook внутри этого же сервера (см. kopir/bot/webhook.py).
BOT_MODE_ENV = "KOPIR_BOT_MODE"


def _public_url() -> str | None:
    """Публичный адрес сервиса: задан явно или выдан хостингом (Render — RENDER_EXTERNAL_URL)."""
    return os.environ.get("KOPIR_PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL")


def create_app(hall: Hall | None = None, web_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Kópir API", version="0.1.0",
                  description="Взаимный подбор знакомств для IT-мероприятий.")
    app.state.hall = hall or Hall.default()

    def get_hall(request: Request) -> Hall:
        return request.app.state.hall

    @app.get("/api/health")
    def health(request: Request) -> HealthResponse:
        return HealthResponse(status="ok", profiles=len(get_hall(request)))

    @app.get("/api/options")
    def options(lang: Lang = "ru") -> OptionsResponse:
        """Справочники для формы анкеты с подписями на выбранном языке."""
        return OptionsResponse(
            goals=[Option(value=g, label=GOAL_LABELS[g][lang]) for g in Goal],
            roles=[Option(value=r, label=labels[lang]) for r, labels in ROLE_LABELS.items()],
            levels=[Option(value=lvl, label=LEVEL_LABELS[lvl][lang]) for lvl in Level],
            domains=[Option(value=d, label=labels[lang]) for d, labels in DOMAIN_LABELS.items()],
            skills=list(SKILLS),
        )

    # Аналитика зала: пересчитывается только при изменении состава зала.
    # Дашборд строится ~секунду (расписание на весь зал): кэш по языку, обновление не чаще раза в 30 с,
    # чтобы каждый новый участник не заставлял организатора ждать пересборки.
    dashboard_cache: dict[str, tuple[float, int, dict]] = {}

    def _dashboard(hall: Hall, lang: Lang) -> dict:
        cached = dashboard_cache.get(lang)
        if cached and (cached[1] == len(hall) or time.time() - cached[0] < DASHBOARD_TTL_S):
            return cached[2]
        data = asdict(dashboard.build(hall.profiles(), lang))
        dashboard_cache[lang] = (time.time(), len(hall), data)
        return data

    threading.Thread(target=lambda: _dashboard(app.state.hall, "ru"), daemon=True).start()

    @app.get("/api/dashboard")
    def organizer_dashboard(request: Request, lang: Lang = "ru") -> dict:
        """Дашборд организатора: баланс ролей, востребованные навыки, карта зала, выводы."""
        return _dashboard(get_hall(request), lang)

    def _intro_view(hall: Hall, intro: Intro, me: str, lang: Lang) -> IntroView:
        other = hall.get(intro.to_id if intro.from_id == me else intro.from_id)
        if other is None:
            raise HTTPException(status_code=404, detail="участник не найден")
        accepted = intro.status == "accepted"
        return IntroView(
            id=intro.id, status=intro.status, simulated=intro.simulated,
            direction="outgoing" if intro.from_id == me else "incoming",
            other=_candidate(other, lang),
            beacon=BeaconOut(**asdict(intro.beacon)) if accepted and intro.beacon else None,
            # Ник вымышленного участника может совпасть с чужим реальным аккаунтом — его не показываем.
            contact=Contact(telegram=other.telegram if hall.is_live(other.id) else None,
                            looks_like=other.looks_like) if accepted else None,
        )

    @app.post("/api/profiles")
    def join_hall(body: JoinRequest, request: Request) -> JoinResponse:
        """Войти в зал: анкету начнут рекомендовать другим, можно знакомиться."""
        profile = body.profile.model_copy(update={"id": new_profile_id()})
        get_hall(request).join(profile)
        return JoinResponse(profile_id=profile.id)

    @app.post("/api/intros")
    def request_intro(body: IntroRequest, request: Request, lang: Lang = "ru") -> IntroView:
        """«Хочу познакомиться». Вымышленные участники демо-зала соглашаются через несколько секунд (simulated)."""
        hall = get_hall(request)
        if not hall.is_live(body.from_id) or hall.get(body.to_id) is None:
            raise HTTPException(status_code=404, detail="участник не найден")
        try:
            intro = hall.introductions.request(body.from_id, body.to_id, auto_accept=not hall.is_live(body.to_id),
                                              group=body.group)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        return _intro_view(hall, intro, body.from_id, lang)

    @app.post("/api/intros/{intro_id}/respond")
    def respond_intro(intro_id: str, body: IntroAnswer, request: Request, lang: Lang = "ru") -> IntroView:
        hall = get_hall(request)
        try:
            intro = hall.introductions.respond(intro_id, body.profile_id, body.accept)
        except KeyError as e:
            raise HTTPException(status_code=404, detail="запрос не найден") from e
        return _intro_view(hall, intro, body.profile_id, lang)

    @app.get("/api/intros")
    def list_intros(profile_id: str, request: Request, lang: Lang = "ru") -> list[IntroView]:
        hall = get_hall(request)
        return [_intro_view(hall, i, profile_id, lang) for i in hall.introductions.of(profile_id)]

    @app.get("/api/live")
    def live_hall(request: Request, profile_id: str | None = None, lang: Lang = "ru") -> LiveResponse:
        """Реальные люди в зале прямо сейчас. Список виден тому, кто сам вошёл в зал."""
        hall = get_hall(request)
        me = hall.get(profile_id) if profile_id else None
        if profile_id and (me is None or not hall.is_live(profile_id)):
            raise HTTPException(status_code=404, detail="вы ещё не в зале")
        people, matches = hall.live(me)
        if me is None:
            return LiveResponse(count=len(people), people=[])
        ranked = sorted(people, key=lambda p: -(matches[p.id].score if p.id in matches else -1))
        return LiveResponse(count=len(people) + 1, people=[
            LivePerson(candidate=_candidate(p, lang),
                       match=_recommendation(me, matches[p.id], lang, hall) if p.id in matches else None)
            for p in ranked
        ])

    @app.post("/api/squad")
    def build_squad(body: SquadRequest, request: Request) -> SquadOut | None:
        """Мини-группа: команда, где каждый полезен каждому, или круг ментора. Нет группы — null."""
        s = get_hall(request).squad(body.profile)
        if s is None:
            return None
        return SquadOut(kind=s.kind, members=[_candidate(p, body.lang) for p in s.members], cohesion=round(s.cohesion, 3),
                        skills=s.skills, domains=[DOMAIN_LABELS[d][body.lang] for d in s.domains])

    @app.post("/api/parse")
    def parse_profile_text(body: ParseRequest) -> dict:
        """Рассказ о себе (голосом или текстом) → поля анкеты."""
        return asdict(parse_text(body.text))

    @app.post("/api/recommend")
    def recommend(body: RecommendRequest, request: Request) -> RecommendResponse:
        """Топ-K взаимно полезных знакомств с объяснениями с обеих сторон."""
        started = time.perf_counter()
        hall = get_hall(request)
        # id назначает сервер: клиент не может выдать себя за другую анкету.
        me = body.profile.model_copy(update={"id": new_profile_id()})
        lang = body.lang or me.lang
        if body.join:
            try:
                hall.join(me)
            except ValueError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
        factors = preference_factors(f.reason for f in body.feedback if f.verdict == "not_fit" and f.reason)
        exclude = {*body.exclude, *(f.candidate_id for f in body.feedback)}
        matches = hall.recommend(me, k=body.k, exclude=exclude, factors=factors)
        return RecommendResponse(
            profile_id=me.id,
            lang=lang,
            recommendations=[_recommendation(me, m, lang, hall) for m in matches],
            factors=factors,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if os.environ.get(BOT_MODE_ENV) == "webhook" and token and _public_url():
        from kopir.bot.webhook import attach_webhook  # aiogram нужен только в этом режиме

        attach_webhook(app, token, _public_url())

    # Статика монтируется последней: маршруты /api/* уже зарегистрированы и имеют приоритет.
    web_dir = web_dir or (Path(os.environ[WEB_DIR_ENV]) if WEB_DIR_ENV in os.environ else None)
    if web_dir is not None:
        if not (web_dir / "index.html").is_file():
            raise RuntimeError(f"в {web_dir} нет index.html — соберите web: npm run build")
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app
