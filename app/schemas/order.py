from datetime import datetime

from pydantic import BaseModel


class OrderResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    schwab_order_id: str | None
    position_id: str | None
    order_type: str
    status: str
    symbol: str
    quantity: int
    limit_price: float
    fill_price: float | None
    is_gtc: bool
    filled_at: datetime | None
    created_at: datetime
