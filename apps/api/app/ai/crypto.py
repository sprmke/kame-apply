"""Envelope encryption for provider API keys.

  KEK (master key, env MASTER_KEK)  wraps  DEK (one random key per workspace, in workspace_keys)
  DEK encrypts each provider key with AES-256-GCM; the workspace id is bound as AAD, so a
  ciphertext copied into another workspace fails to decrypt.

Plaintext keys exist only in memory for the duration of a call. Never log them.

Rotating the KEK: set MASTER_KEK to the new key, MASTER_KEK_PREVIOUS to the old one, run the
rewrap script `python -m app.ops.rewrap_keks` (re-wraps every `workspace_keys.wrapped_dek`, bumps `kek_version`), then remove
MASTER_KEK_PREVIOUS. Provider keys themselves are not re-encrypted. See architecture/auth.md.
"""

import base64
import os
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.errors import AppError

NONCE_BYTES = 12


def parse_kek(b64: str) -> bytes:
    raw = base64.b64decode(b64)
    if len(raw) != 32:
        raise ValueError("MASTER_KEK must be 32 bytes, base64 encoded")
    return raw


def _seal(key: bytes, plaintext: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def _open(key: bytes, blob: bytes, aad: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], aad)
    except InvalidTag:
        raise AppError(
            "decryption_failed", "Stored credential could not be decrypted", 500
        ) from None


def new_wrapped_dek(kek: bytes, workspace_id: uuid.UUID) -> bytes:
    return _seal(kek, os.urandom(32), b"dek:" + workspace_id.bytes)


def wrap_dek(kek: bytes, dek: bytes, workspace_id: uuid.UUID) -> bytes:
    return _seal(kek, dek, b"dek:" + workspace_id.bytes)


def unwrap_dek(kek: bytes, wrapped: bytes, workspace_id: uuid.UUID) -> bytes:
    return _open(kek, wrapped, b"dek:" + workspace_id.bytes)


def encrypt_secret(dek: bytes, plaintext: str, workspace_id: uuid.UUID) -> bytes:
    return _seal(dek, plaintext.encode(), b"key:" + workspace_id.bytes)


def decrypt_secret(dek: bytes, blob: bytes, workspace_id: uuid.UUID) -> str:
    return _open(dek, blob, b"key:" + workspace_id.bytes).decode()
