"""HTTP API Kópir и раздача собранного веб-интерфейса.

    uv run uvicorn kopir.api.app:create_app --factory --port 8000

Документация с примерами — на /docs. Если задан `$KOPIR_WEB_DIR` (папка со
сборкой web/dist), сервер отдаёт интерфейс с того же адреса.
"""

import os
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from kopir.api.schemas import (
    Candidate,
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
    dashboard_cache: dict[tuple[int, str], dict] = {}

    @app.get("/api/dashboard")
    def organizer_dashboard(request: Request, lang: Lang = "ru") -> dict:
        """Дашборд организатора: баланс ролей, востребованные навыки, карта зала, выводы."""
        hall = get_hall(request)
        key = (len(hall), lang)
        if key not in dashboard_cache:
            dashboard_cache.clear()
            dashboard_cache[key] = asdict(dashboard.build(hall.profiles(), lang))
        return dashboard_cache[key]

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
