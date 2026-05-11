import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClosedTrade(Base):
    """Immutable record written when a position closes. Source of truth for P&L history."""

    __tablename__ = "closed_trades"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    position_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    underlying_symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    option_symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    contracts: Mapped[int] = mapped_column(Integer, nullable=False)

    premium_received: Mapped[float] = mapped_column(Float, nullable=False)  # per contract at entry
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)         # per contract at close
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False)       # (premium - exit) × 100 × contracts

    holding_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # PROFIT_TARGET, STOP_LOSS, EXPIRED_WORTHLESS, MANUAL, ASSIGNED
    close_reason: Mapped[str] = mapped_column(String(30), nullable=False)

    closed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
