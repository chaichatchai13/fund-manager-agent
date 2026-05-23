"""PWA push notification subscriptions."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, JSON
from app.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True)
    endpoint = Column(String(500), nullable=False, unique=True)
    keys = Column(JSON, nullable=False)   # {"p256dh": "...", "auth": "..."}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
