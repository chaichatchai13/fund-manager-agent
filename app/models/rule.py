import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SellPutRule(Base):
    __tablename__ = "sell_put_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # symbols: [{"symbol": "IREN", "priority": 1}, {"symbol": "TSLA", "priority": 2}]
    symbols: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # DTE filter
    min_dte: Mapped[int] = mapped_column(Integer, default=30)
    max_dte: Mapped[int] = mapped_column(Integer, default=45)

    # Premium filter — PRIMARY filter
    min_premium_mode: Mapped[str] = mapped_column(String(20), default="pct")  # "pct" or "dollar"
    min_premium_pct: Mapped[float] = mapped_column(Float, default=1.0)  # % of stock price (mode=pct)
    min_premium_dollar: Mapped[float | None] = mapped_column(Float, nullable=True)  # fixed $ amount (mode=dollar)
    max_premium_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Intraday drop trigger (optional — NULL = always scan)
    min_daily_drop_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_daily_drop_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Profit management
    profit_target_pct: Mapped[float] = mapped_column(Float, default=0.75)
    profit_approach_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # advance GTC trigger
    stop_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Position sizing
    max_open_positions: Mapped[int] = mapped_column(Integer, default=5)
    position_size_mode: Mapped[str] = mapped_column(String(20), default="pct")  # "pct" or "contracts"
    position_size_pct: Mapped[float] = mapped_column(Float, default=0.05)  # 5% of buying power (mode=pct)
    position_size_contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)  # fixed contract count (mode=contracts)
    max_position_size_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Optional secondary filters
    min_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_iv_rank: Mapped[float | None] = mapped_column(Float, nullable=True)

    scan_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)

    strategy_type: Mapped[str] = mapped_column(String(20), default="SELL_PUT")  # "SELL_PUT" or "SELL_COVERED_CALL"
    min_strike_otm_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # optional OTM % filter

    # ITM / expiry management
    itm_action: Mapped[str] = mapped_column(String(20), default="let_assign")  # "let_assign" or "roll"
    roll_when_dte: Mapped[int] = mapped_column(Integer, default=7)             # trigger roll when DTE ≤ this
    roll_target_weeks: Mapped[int] = mapped_column(Integer, default=4)         # roll to expiry ~N weeks out

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
