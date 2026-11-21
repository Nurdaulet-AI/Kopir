"""Запуск бота: `python -m kopir.bot`.

Переменные окружения:
- `TELEGRAM_BOT_TOKEN` — токен от @BotFather (без него бот не запускается);
- `KOPIR_WEBAPP_URL` — публичный HTTPS-адрес веб-интерфейса для Mini App (необязательно).
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from kopir.bot.app import build_dispatcher, configure, webapp_url_or_none

log = logging.getLogger("kopir.bot")


async def run(token: str, webapp_url: str | None) -> None:
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await bot.get_me()
        await configure(bot, webapp_url)
        log.info("бот @%s запущен; Mini App: %s", me.username, webapp_url or "не настроен")
        await build_dispatcher(webapp_url).start_polling(bot)
    finally:
        await bot.session.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        log.info("TELEGRAM_BOT_TOKEN не задан — бот не запускается (это нормально, если бот не нужен)")
        return 0
    asyncio.run(run(token, webapp_url_or_none(os.environ.get("KOPIR_WEBAPP_URL"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
