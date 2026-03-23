from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

TOKEN_TYPE = "bearer"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padded = raw + "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _build_signature(secret: str, payload_b64: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(
    *,
    user_id: int,
    username: str,
    secret_key: str,
    expires_in_seconds: int,
) -> str:
    now = int(time.time())
    payload = {
        "uid": int(user_id),
        "usr": str(username),
        "iat": now,
        "exp": now + int(expires_in_seconds),
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_raw)
    signature = _build_signature(secret_key, payload_b64)
    return f"{payload_b64}.{signature}"


def parse_access_token(token: str, *, secret_key: str) -> dict[str, Any]:
    if "." not in token:
        raise ValueError("Invalid token format.")
    payload_b64, signature = token.split(".", 1)
    expected_signature = _build_signature(secret_key, payload_b64)
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid token signature.")

    try:
        payload_raw = _b64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_raw)
    except Exception as exc:
        raise ValueError("Invalid token payload.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid token payload.")
    exp_raw = payload.get("exp")
    if not isinstance(exp_raw, int):
        raise ValueError("Invalid token expiry.")
    if exp_raw < int(time.time()):
        raise ValueError("Token expired.")
    return payload
