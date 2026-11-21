import pytest
from fastapi.testclient import TestClient

from kopir.api.app import create_app
from kopir.bot.webhook import WEBHOOK_PATH, webhook_secret
from kopir.data.generator import generate
from kopir.hall import Hall

TOKEN = "123456789:" + "A" * 35  # не настоящий токен: Telegram в тестах не вызывается


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("KOPIR_BOT_MODE", "webhook")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("KOPIR_PUBLIC_URL", "https://kopir.example")
    # Без `with` TestClient не запускает lifespan, поэтому setWebhook в Telegram не уходит.
    return TestClient(create_app(Hall(generate(n=60, seed=1))))


def test_secret_is_stable_and_telegram_compatible():
    secret = webhook_secret(TOKEN)
    assert secret == webhook_secret(TOKEN) and len(secret) == 64 and secret.isalnum()
    assert secret != webhook_secret(TOKEN + "x")


def test_requests_without_valid_secret_are_rejected(client):
    assert client.post(WEBHOOK_PATH, json={"update_id": 1}).status_code == 403
    bad = {"X-Telegram-Bot-Api-Secret-Token": "guess"}
    assert client.post(WEBHOOK_PATH, json={"update_id": 1}, headers=bad).status_code == 403


def test_signed_update_is_accepted(client):
    good = {"X-Telegram-Bot-Api-Secret-Token": webhook_secret(TOKEN)}
    # Отредактированное сообщение: обработчика нет, бот пропускает его и не обращается к Telegram.
    update = {"update_id": 1, "edited_message": {"message_id": 1, "date": 0, "edit_date": 0,
                                                 "chat": {"id": 1, "type": "private"}, "text": "x"}}
    assert client.post(WEBHOOK_PATH, json=update, headers=good).json() == {"ok": True}


def test_webhook_is_off_by_default():
    client = TestClient(create_app(Hall(generate(n=60, seed=1))))
    assert client.post(WEBHOOK_PATH, json={"update_id": 1}).status_code in (404, 405)
