"""Symmetric encryption for integration secrets stored in the database.

The key-encryption key (KEK) is derived from ``DJANGO_SECRET_KEY``; rotating
that value makes existing ciphertext unreadable, which is surfaced loudly rather
than silently returning an empty secret.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

PREFIX = "enc:v1:"


class SecretDecryptionError(ImproperlyConfigured):
    """A stored secret could not be decrypted with the configured key."""


def _fernet_key() -> bytes:
    secret = getattr(settings, "SECRET_KEY", "") or ""
    if not secret:
        message = "DJANGO_SECRET_KEY is required to encrypt stored secrets"
        raise ImproperlyConfigured(message)
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    return Fernet(_fernet_key())


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt(value: str | None) -> str | None:
    """Encrypt *value*; empty and already-encrypted values pass through."""
    if not value or is_encrypted(value):
        return value
    token = get_fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{PREFIX}{token}"


def decrypt(value: str | None) -> str | None:
    """Decrypt a prefixed value; legacy plaintext passes through."""
    if not value or not is_encrypted(value):
        return value
    token = value[len(PREFIX) :]
    try:
        return get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        message = (
            "Could not decrypt a stored integration secret. DJANGO_SECRET_KEY "
            "may have changed; re-enter the secret in the Wagtail admin."
        )
        raise SecretDecryptionError(message) from exc
