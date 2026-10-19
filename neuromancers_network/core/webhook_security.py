"""HMAC verification for inbound provider webhooks."""

from __future__ import annotations

import hashlib
import hmac


def verify_hmac_sha256(*, secret: str, body: bytes, signature: str) -> bool:
    """Verify a hex HMAC-SHA256 signature (optionally ``sha256=`` prefixed)."""
    if not secret or not signature:
        return False
    value = signature.strip()
    if value.startswith("sha256="):
        value = value[len("sha256=") :]
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, value.lower())
