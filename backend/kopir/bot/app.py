"""Telegram-бот Kópir: приветствие, помощь и кнопка Mini App с нашим веб-интерфейсом.

Бот работает в режиме long polling — сам опрашивает Telegram, поэтому ему не нужен
публичный адрес. Публичный HTTPS-адрес нужен только Mini App (`KOPIR_WEBAPP_URL`):
без него бот работает, но вместо кнопки приложения пишет, что оно скоро будет.
"""

import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonDefault,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from kopir.bot.texts import TEXTS
from kopir.taxonomy import LANGS, Lang

log = logging.getLogger(__name__)


def user_lang(language_code: str | None) -> Lang:
    """Язык интерфейса Telegram → наш язык; всё незнакомое — русский."""
    code = (language_code or "").split("-")[0].lower()
    return code if code in LANGS else "ru"  # type: ignore[return-value]


def webapp_url_or_none(url: str | None) -> str | None:
    """Telegram открывает Mini App только по HTTPS; иное считаем «не настроено»."""
    if url and url.startswith("https://"):
        return url
    if url:
        log.warning("KOPIR_WEBAPP_URL должен начинаться с https:// — кнопка приложения отключена")
    return None


def start_keyboard(lang: Lang, webapp_url: str | None) -> InlineKeyboardMarkup | None:
    if webapp_url is None:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=TEXTS[lang]["open"], web_app=WebAppInfo(url=webapp_url)),
    ]])


def build_router(webapp_url: str | None) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        lang = user_lang(message.from_user.language_code if message.from_user else None)
        text = TEXTS[lang]["greeting"]
        if webapp_url is None:
            text += "\n\n" + TEXTS[lang]["no_app"]
        await message.answer(text, reply_markup=start_keyboard(lang, webapp_url))

    @router.message(Command("help"))
    async def help_(message: Message) -> None:
        lang = user_lang(message.from_user.language_code if message.from_user else None)
        await message.answer(TEXTS[lang]["help"])

    @router.message(F.text)
    async def fallback(message: Message) -> None:
        lang = user_lang(message.from_user.language_code if message.from_user else None)
        await message.answer(TEXTS[lang]["fallback"], reply_markup=start_keyboard(lang, webapp_url))

    return router


async def configure(bot: Bot, webapp_url: str | None) -> None:
    """Команды в меню на трёх языках и кнопка приложения слева от поля ввода."""
    for lang in LANGS:
        commands = [BotCommand(command="start", description=TEXTS[lang]["cmd_start"]),
                    BotCommand(command="help", description=TEXTS[lang]["cmd_help"])]
        await bot.set_my_commands(commands, language_code=None if lang == "ru" else lang)
    if webapp_url is None:
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Kópir", web_app=WebAppInfo(url=webapp_url)))


def build_dispatcher(webapp_url: str | None) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(webapp_url))
    return dispatcher
