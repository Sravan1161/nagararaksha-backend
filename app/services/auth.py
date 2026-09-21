"""Minimal staff authentication.

This is intentionally simple for a pilot: one shared password for ward staff
(set via STAFF_PASSWORD), not individual accounts. It's enough to stop a
random citizen from tapping "Municipal" and reassigning or resolving other
people's reports -- it is NOT meant to survive serious attack. Move to
per-officer accounts before this handles real complaints at scale.
"""

from fastapi import Header, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.staff_token_secret, salt="staff-auth")


def issue_staff_token() -> str:
    return _serializer().dumps({"role": "staff"})


def verify_staff_token(token: str) -> bool:
    try:
        data = _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("role") == "staff"


def require_staff(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency: raises 401 unless a valid staff Bearer token is present."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Staff login required")
    token = authorization.removeprefix("Bearer ").strip()
    if not verify_staff_token(token):
        raise HTTPException(status_code=401, detail="Staff session invalid or expired")
