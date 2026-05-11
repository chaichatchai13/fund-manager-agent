import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailySnapshot(Base):
    """Pre-aggregated nightly P&L snapshot for fast dashboard queries."""

    __tablename__ = "daily_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    total_portfolio_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    buying_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0)

    total_unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    daily_realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    cumulative_realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
