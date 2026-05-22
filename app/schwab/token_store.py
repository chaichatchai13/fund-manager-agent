"""
Encrypted Schwab token persistence in PostgreSQL.

Encryption: Fernet symmetric key derived from SECRET_KEY via SHA-256.
DB row: always id=1 (one app instance, one token).
"""
import base64
import hashlib
import json
import time

import structlog
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.schwab_token import SchwabToken

logger = structlog.get_logger(__name__)


def _fernet() -> Fernet:
    """Derive a stable Fernet key from the app's SECRET_KEY."""
    from app.config import settings
    raw = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_token(token_json: str) -> str:
    return _fernet().encrypt(token_json.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


async def load_token_from_db() -> dict | None:
    """Return the decrypted token dict, or None if not stored."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SchwabToken).where(SchwabToken.id == 1))
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return json.loads(decrypt_token(row.token_encrypted))
    except Exception as exc:
        logger.warning("Failed to load Schwab token from DB", error=str(exc))
        return None


async def save_token_to_db(token_dict: dict) -> None:
    """Encrypt and upsert the token dict into the DB (always row id=1)."""
    from datetime import datetime, timezone
    encrypted = encrypt_token(json.dumps(token_dict))
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SchwabToken).where(SchwabToken.id == 1))
        row = result.scalar_one_or_none()
        if row:
            row.token_encrypted = encrypted
            row.updated_at = now
        else:
            db.add(SchwabToken(id=1, token_encrypted=encrypted, updated_at=now))
        await db.commit()
    logger.info("Schwab token saved to DB")


async def save_token_file_to_db(token_path: str) -> None:
    """Read an existing token file and store it in the DB."""
    import os
    if not os.path.exists(token_path):
        return
    with open(token_path) as f:
        token_dict = json.load(f)
    await save_token_to_db(token_dict)


async def write_token_db_to_file(token_path: str) -> bool:
    """Load token from DB and write to file so schwab-py can read it. Returns True if written."""
    token_dict = await load_token_from_db()
    if token_dict is None:
        return False
    with open(token_path, "w") as f:
        json.dump(token_dict, f)
    logger.info("Schwab token written from DB to file", path=token_path)
    return True


def build_token_dict(oauth_response: dict) -> dict:
    """
    Convert a raw Schwab OAuth token response into the format schwab-py expects:
      { "creation_timestamp": <unix>, "token": { ...oauth fields... } }
    """
    token = dict(oauth_response)
    # Add expires_at timestamp if not present
    if "expires_at" not in token:
        expires_in = int(token.get("expires_in", 1800))
        token["expires_at"] = time.time() + expires_in
    return {
        "creation_timestamp": int(time.time()),
        "token": token,
    }
