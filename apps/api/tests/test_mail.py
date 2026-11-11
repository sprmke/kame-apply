from typing import Any

import pytest

from app.core.config import Settings
from app.core.mail import Mail, Mailer


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "local",
        "smtp_host": "127.0.0.1",
        "smtp_port": 1125,
        "smtp_user": None,
        "smtp_password": None,
        "smtp_starttls": False,
        "smtp_ssl": False,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_smtp_uses_starttls_and_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_send(message: Any, **kwargs: Any) -> None:
        captured["message"] = message
        captured.update(kwargs)

    monkeypatch.setattr("app.core.mail.aiosmtplib.send", fake_send)

    settings = _settings(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="me@example.com",
        smtp_password="app-password",
        smtp_starttls=True,
    )
    await Mailer(settings).send(Mail(to="you@example.com", subject="Hi", text="Body"))

    assert captured["hostname"] == "smtp.gmail.com"
    assert captured["port"] == 587
    assert captured["username"] == "me@example.com"
    assert captured["password"] == "app-password"
    assert captured["start_tls"] is True
    assert "use_tls" not in captured


@pytest.mark.asyncio
async def test_smtp_without_auth_stays_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_send(message: Any, **kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("app.core.mail.aiosmtplib.send", fake_send)

    await Mailer(_settings()).send(Mail(to="you@example.com", subject="Hi", text="Body"))

    assert captured["hostname"] == "127.0.0.1"
    assert captured["port"] == 1125
    assert "username" not in captured
    assert "start_tls" not in captured
    assert "use_tls" not in captured
