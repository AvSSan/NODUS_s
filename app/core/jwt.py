from __future__ import annotations

import base64
import json
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Any


class JWTError(Exception):
    """Raised when JWT decoding fails."""


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encode(payload: dict[str, Any], secret: str, algorithm: str = "HS256") -> str:
    if algorithm != "HS256":
        raise ValueError("Only HS256 algorithm is supported")
    header = {"alg": algorithm, "typ": "JWT"}
    header_segment = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _base64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode(token: str, secret: str, algorithms: list[str] | None = None) -> dict[str, Any]:
    algorithms = algorithms or ["HS256"]
    header_segment, payload_segment, signature_segment = token.split(".")
    header = json.loads(_base64url_decode(header_segment))
    if header.get("alg") not in algorithms:
        raise JWTError("Unsupported algorithm")
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _base64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise JWTError("Signature verification failed")
    payload = json.loads(_base64url_decode(payload_segment))
    exp = payload.get("exp")
    if exp is not None:
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(tz=timezone.utc) > exp_dt:
            raise JWTError("Token expired")
    return payload
