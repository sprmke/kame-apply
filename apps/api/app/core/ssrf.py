"""SSRF guards for any outbound URL the server fetches (link resolver, crawlers, AI base URLs)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.errors import AppError

ALLOWED_PORTS = frozenset({80, 443, 8080, 11434})


def _blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    # not is_global covers CGNAT, link-local, loopback, private, reserved, multicast
    return not ip.is_global


def assert_public_http_url(url: str, *, allow_private: bool = False) -> str:
    """Refuse non-http(s), odd ports, and hosts that resolve to non-global addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise AppError("ssrf_blocked", "Enter a full http(s) URL", 422)
    if allow_private:
        return url
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise AppError("ssrf_blocked", "That port is not allowed", 422)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise AppError("ssrf_blocked", "Host could not be resolved", 422) from exc
    for info in infos:
        if _blocked(ipaddress.ip_address(info[4][0])):
            raise AppError("ssrf_blocked", "That address is not allowed", 422)
    return url


def is_safe_outbound_url(url: str, *, allow_private: bool = False) -> bool:
    try:
        assert_public_http_url(url, allow_private=allow_private)
        return True
    except AppError:
        return False
