"""SSRF guard unit tests (Phase 14)."""

from unittest.mock import patch

import pytest

from app.core.errors import AppError
from app.core.ssrf import assert_public_http_url, is_safe_outbound_url


def test_rejects_non_http():
    with pytest.raises(AppError) as ei:
        assert_public_http_url("ftp://example.com/x")
    assert ei.value.code == "ssrf_blocked"


def test_rejects_odd_port():
    with pytest.raises(AppError):
        assert_public_http_url("https://example.com:22/")


def test_rejects_loopback_resolution():
    with patch(
        "app.core.ssrf.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("127.0.0.1", 443))]
    ):
        with pytest.raises(AppError) as ei:
            assert_public_http_url("https://evil.example/")
        assert ei.value.code == "ssrf_blocked"


def test_rejects_link_local_and_metadata():
    for ip in ("169.254.169.254", "10.0.0.5", "192.168.1.1", "::1"):
        with patch("app.core.ssrf.socket.getaddrinfo", return_value=[(0, 0, 0, "", (ip, 443))]):
            assert is_safe_outbound_url("https://meta.example/") is False


def test_allows_public_ip():
    with patch(
        "app.core.ssrf.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("93.184.216.34", 443))]
    ):
        assert assert_public_http_url("https://example.com/path") == "https://example.com/path"


def test_allow_private_bypass():
    with patch(
        "app.core.ssrf.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("10.0.0.2", 11434))]
    ):
        assert assert_public_http_url("http://ollama.local:11434", allow_private=True).startswith(
            "http://"
        )
