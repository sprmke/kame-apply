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
