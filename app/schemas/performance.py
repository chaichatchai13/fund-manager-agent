from datetime import date, datetime

from pydantic import BaseModel


class DailySnapshotResponse(BaseModel):
    model_config = {"from_attributes": True}

    snapshot_date: date
    total_portfolio_value: float | None
    buying_power: float | None
    open_positions_count: int
    total_unrealized_pnl: float
    daily_realized_pnl: float
    cumulative_realized_pnl: float
    created_at: datetime


class PerformanceSummary(BaseModel):
    period: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    pnl_pct: float | None  # % of portfolio value
    trades_closed: int
    win_rate: float | None  # % of profitable closed trades
    portfolio_value: float | None


class ClosedTradeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    position_id: str
    underlying_symbol: str
    option_symbol: str
    contracts: int
    premium_received: float
    exit_price: float
    realized_pnl: float
    holding_days: int
    close_reason: str
    closed_at: datetime
