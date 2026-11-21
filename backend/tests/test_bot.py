import pytest

from kopir.bot.app import start_keyboard, user_lang, webapp_url_or_none
from kopir.bot.texts import TEXTS
from kopir.taxonomy import LANGS


@pytest.mark.parametrize(
    ("code", "lang"),
    [("kk", "kk"), ("ru", "ru"), ("en", "en"), ("en-US", "en"), ("KK", "kk"), ("de", "ru"), (None, "ru"), ("", "ru")],
)
def test_user_language_maps_to_supported(code, lang):
    assert user_lang(code) == lang


def test_texts_exist_in_every_language():
    keys = set(TEXTS["ru"])
    for lang in LANGS:
        assert set(TEXTS[lang]) == keys, lang
        assert all(TEXTS[lang][k].strip() for k in keys), lang


@pytest.mark.parametrize("url", ["http://localhost:8000", "ftp://x", "localhost:8000"])
def test_mini_app_requires_https(url):
    assert webapp_url_or_none(url) is None


def test_open_button_launches_the_mini_app():
    assert start_keyboard("kk", None) is None
    keyboard = start_keyboard("kk", "https://kopir.example")
    button = keyboard.inline_keyboard[0][0]
    assert button.text == TEXTS["kk"]["open"]
    assert button.web_app.url == "https://kopir.example"
