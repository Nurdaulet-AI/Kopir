"""Бот в режиме webhook внутри веб-сервера: один сервис на хостинге вместо двух.

Telegram сам присылает обновления на `/telegram/webhook`. Каждый запрос несёт
заголовок `X-Telegram-Bot-Api-Secret-Token`; секрет выводится из токена бота,
поэтому чужие запросы отклоняются без отдельной настройки.
"""

import hashlib
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request

from kopir.bot.app import build_dispatcher, configure, webapp_url_or_none

log = logging.getLogger(__name__)
WEBHOOK_PATH = "/telegram/webhook"


def webhook_secret(token: str) -> str:
    """Секрет для заголовка Telegram: производный от токена, допустимые символы, 64 знака."""
    return hashlib.sha256(f"kopir-webhook:{token}".encode()).hexdigest()


def attach_webhook(app: FastAPI, token: str, public_url: str) -> None:
    """Регистрирует маршрут webhook и при старте сервера сообщает Telegram адрес."""
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    webapp_url = webapp_url_or_none(public_url)
    dispatcher = build_dispatcher(webapp_url)
    secret = webhook_secret(token)

    @app.post(WEBHOOK_PATH, include_in_schema=False)
    async def telegram_webhook(request: Request) -> dict:
        given = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(given, secret):
            raise HTTPException(status_code=403)
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"ok": True}

    previous = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
        await bot.set_webhook(f"{public_url.rstrip('/')}{WEBHOOK_PATH}", secret_token=secret,
                              drop_pending_updates=True)
        await configure(bot, webapp_url)
        log.info("бот в режиме webhook: %s%s", public_url, WEBHOOK_PATH)
        try:
            async with previous(app_):
                yield
        finally:
            await bot.session.close()

    app.router.lifespan_context = lifespan
