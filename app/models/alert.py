"""Price alert rules — triggers SMS + push when condition is met."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from app.database import Base


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    condition = Column(String(20), nullable=False)  # "drop_pct", "rise_pct", "below_price", "above_price"
    threshold = Column(Float, nullable=False)        # e.g. 3.0 for 3%
    action = Column(String(30), nullable=False, default="notify_and_suggest")  # "notify_only", "notify_and_suggest"
    enabled = Column(Boolean, default=True, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    cooldown_minutes = Column(Integer, default=60, nullable=False)  # min time between triggers
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
