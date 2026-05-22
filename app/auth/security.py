"""
JWT creation/verification and password checking for ThetaFlow auth.

Password strategy:
  THETAFLOW_PASSWORD in .env can be:
    - Plain text:   "mysecretpassword"   (easy setup, fine behind HTTPS)
    - Bcrypt hash:  "$2b$12$..."         (generate with: python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('yourpassword'))")
"""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
COOKIE_NAME = "tf_token"
TOKEN_EXPIRE_DAYS = 7


def verify_password(plain: str) -> bool:
    """Check a plain-text password against the configured THETAFLOW_PASSWORD."""
    stored = settings.thetaflow_password
    if not stored:
        return False
    # Auto-detect bcrypt hash vs plain text
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        return _pwd_context.verify(plain, stored)
    return plain == stored


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": "owner", "exp": expire},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    """Return payload dict if token is valid, None otherwise."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def cookie_kwargs() -> dict:
    """
    Cookie settings.
    secure=True only when running on a real domain (not localhost) — requires HTTPS.
    samesite=lax works for normal navigation and API calls without blocking WebSocket cookies.
    """
    domain = getattr(settings, "thetaflow_domain", "localhost")
    is_real_domain = settings.environment == "production" and "localhost" not in domain
    return dict(
        key=COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=is_real_domain,
        max_age=TOKEN_EXPIRE_DAYS * 24 * 3600,
    )
