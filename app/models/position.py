import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OptionPosition(Base):
    __tablename__ = "option_positions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    schwab_account_hash: Mapped[str] = mapped_column(String, nullable=False)

    underlying_symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    option_symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    strike: Mapped[float] = mapped_column(Float, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    dte_at_entry: Mapped[int] = mapped_column(Integer, nullable=False)

    # Greeks at entry
    delta_at_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    iv_rank_at_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    stock_price_at_entry: Mapped[float | None] = mapped_column(Float, nullable=True)

    contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    premium_received: Mapped[float] = mapped_column(Float, nullable=False)  # per contract
    total_credit: Mapped[float] = mapped_column(Float, nullable=False)      # premium × contracts × 100

    # Live-updated fields
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)

    # OPEN, CLOSING, CLOSED, EXPIRED, ASSIGNED
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)

    entry_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    exit_order_id: Mapped[str | None] = mapped_column(String, nullable=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
