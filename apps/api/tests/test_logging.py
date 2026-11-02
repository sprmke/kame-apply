import json

import structlog

from app.core.logging import configure_logging


def test_secrets_are_redacted(capsys):
    configure_logging("INFO", json=True)
    structlog.get_logger().info("login", password="hunter2", token="abc", user="u1")
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["password"] == "[redacted]"
    assert line["token"] == "[redacted]"
    assert line["user"] == "u1"


def test_nested_secrets_are_redacted(capsys):
    configure_logging("INFO", json=True)
    structlog.get_logger().info(
        "call",
        body={"api_key": "sk-live-123", "nested": {"refresh_token": "r1"}},
        items=[{"authorization": "Bearer x"}],
        keep={"email": "a@b.com"},
    )
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["body"]["api_key"] == "[redacted]"
    assert line["body"]["nested"]["refresh_token"] == "[redacted]"
    assert line["items"][0]["authorization"] == "[redacted]"
    assert line["keep"]["email"] == "a@b.com"
