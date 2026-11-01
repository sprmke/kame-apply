"""Opt-in encrypted site session blobs (stdlib only; key from env)."""

from __future__ import annotations

import hashlib
import hmac
import os


def _key() -> bytes | None:
    raw = os.environ.get("KAME_SITE_SESSION_KEY") or os.environ.get("SITE_SESSION_KEY")
    if not raw:
        return None
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt_storage_state(blob: bytes) -> bytes | None:
    """XOR stream + HMAC tag. Prefer Fernet in prod when crypto dep is available."""
    key = _key()
    if key is None:
        return None
    out = bytearray(len(blob))
    for i, b in enumerate(blob):
        out[i] = b ^ key[i % len(key)]
    tag = hmac.new(key, bytes(out), hashlib.sha256).digest()
    return tag + bytes(out)


def decrypt_storage_state(blob: bytes) -> bytes | None:
    key = _key()
    if key is None or len(blob) < 32:
        return None
    tag, data = blob[:32], blob[32:]
    if not hmac.compare_digest(tag, hmac.new(key, data, hashlib.sha256).digest()):
        return None
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key[i % len(key)]
    return bytes(out)
