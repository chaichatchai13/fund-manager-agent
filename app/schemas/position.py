from datetime import date, datetime

from pydantic import BaseModel


class OptionPositionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    rule_id: str | None
    underlying_symbol: str
    option_symbol: str
    strike: float
    expiration_date: date
    dte_at_entry: int
    delta_at_entry: float | None
    iv_rank_at_entry: float | None
    stock_price_at_entry: float | None
    contracts: int
    premium_received: float
    total_credit: float
    current_price: float | None
    unrealized_pnl: float | None
    status: str
    entry_order_id: str | None
    exit_order_id: str | None
    opened_at: datetime
    closed_at: datetime | None
