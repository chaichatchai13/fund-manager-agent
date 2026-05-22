"""
Stores the Schwab OAuth token (encrypted) in the database.
One row per app instance — we always upsert row id=1.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class SchwabToken(Base):
    __tablename__ = "schwab_tokens"

    id = Column(Integer, primary_key=True, default=1)
    token_encrypted = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
