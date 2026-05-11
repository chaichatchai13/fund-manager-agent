import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    schwab_order_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    position_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # SELL_TO_OPEN or BUY_TO_CLOSE
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Schwab order status string (WORKING, FILLED, CANCELLED, etc.)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")

    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    limit_price: Mapped[float] = mapped_column(Float, nullable=False)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # GTC flag
    is_gtc: Mapped[bool] = mapped_column(default=False)

    filled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Full Schwab API response for debugging
    raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
