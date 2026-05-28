from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SymbolEntry(BaseModel):
    symbol: str
    priority: int = 1


class SellPutRuleCreate(BaseModel):
    name: str
    enabled: bool = True
    symbols: list[SymbolEntry] = Field(default_factory=list)
    min_dte: int = 30
    max_dte: int = 45
    min_premium_mode: str = "pct"          # "pct" or "dollar"
    min_premium_pct: float = 1.0
    min_premium_dollar: float | None = None
    max_premium_pct: float | None = None
    min_daily_drop_pct: float | None = None
    max_daily_drop_pct: float | None = None
    profit_target_pct: float = 0.75
    profit_approach_pct: float | None = None
    stop_loss_pct: float | None = None
    max_open_positions: int = 5
    position_size_mode: str = "pct"        # "pct" or "contracts"
    position_size_pct: float = 0.05
    position_size_contracts: int | None = None
    max_position_size_usd: float | None = None
    min_delta: float | None = None
    max_delta: float | None = None
    min_iv_rank: float | None = None
    scan_interval_minutes: int = 15
    strategy_type: str = "SELL_PUT"
    min_strike_otm_pct: float | None = None
    itm_action: str = "let_assign"
    roll_when_dte: int = 7
    roll_target_weeks: int = 4
    # New filters
    strike_min: float | None = None
    strike_max: float | None = None
    max_premium_dollar: float | None = None
    bid_ask_fill_pct: float = 0.5
    min_iv_pct: float | None = None
    max_iv_pct: float | None = None


class SellPutRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    symbols: list[SymbolEntry] | None = None
    min_dte: int | None = None
    max_dte: int | None = None
    min_premium_mode: str | None = None
    min_premium_pct: float | None = None
    min_premium_dollar: float | None = None
    max_premium_pct: float | None = None
    min_daily_drop_pct: float | None = None
    max_daily_drop_pct: float | None = None
    profit_target_pct: float | None = None
    profit_approach_pct: float | None = None
    stop_loss_pct: float | None = None
    max_open_positions: int | None = None
    position_size_mode: str | None = None
    position_size_pct: float | None = None
    position_size_contracts: int | None = None
    max_position_size_usd: float | None = None
    min_delta: float | None = None
    max_delta: float | None = None
    min_iv_rank: float | None = None
    scan_interval_minutes: int | None = None
    strategy_type: str | None = None
    min_strike_otm_pct: float | None = None
    itm_action: str | None = None
    roll_when_dte: int | None = None
    roll_target_weeks: int | None = None
    # New filters
    strike_min: float | None = None
    strike_max: float | None = None
    max_premium_dollar: float | None = None
    bid_ask_fill_pct: float | None = None
    min_iv_pct: float | None = None
    max_iv_pct: float | None = None


class SellPutRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    enabled: bool
    symbols: list[dict[str, Any]]
    min_dte: int
    max_dte: int
    min_premium_mode: str
    min_premium_pct: float
    min_premium_dollar: float | None
    max_premium_pct: float | None
    min_daily_drop_pct: float | None
    max_daily_drop_pct: float | None
    profit_target_pct: float
    profit_approach_pct: float | None
    stop_loss_pct: float | None
    max_open_positions: int
    position_size_mode: str
    position_size_pct: float
    position_size_contracts: int | None
    max_position_size_usd: float | None
    min_delta: float | None
    max_delta: float | None
    min_iv_rank: float | None
    scan_interval_minutes: int
    strategy_type: str
    min_strike_otm_pct: float | None
    itm_action: str
    roll_when_dte: int
    roll_target_weeks: int
    strike_min: float | None
    strike_max: float | None
    max_premium_dollar: float | None
    bid_ask_fill_pct: float
    min_iv_pct: float | None
    max_iv_pct: float | None
    last_error: str | None
    last_error_at: datetime | None
    created_at: datetime
    updated_at: datetime
