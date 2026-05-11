"""
OrderManager: places orders on Schwab, persists to DB, polls for fills.
"""
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.order import Order
from app.schwab.client import schwab_client
from app.schwab.order_builder import (
    build_buy_to_close_limit,
    build_buy_to_close_market,
    build_sell_to_open_limit,
)

logger = structlog.get_logger(__name__)


class OrderManager:
    async def place_sell_to_open(
        self,
        option_symbol: str,
        quantity: int,
        limit_price: float,
        position_id: str | None = None,
    ) -> Order:
        order_spec = build_sell_to_open_limit(option_symbol, quantity, limit_price)
        response = await schwab_client.place_order(order_spec)
        schwab_order_id = str(response.get("orderId", ""))

        order = Order(
            schwab_order_id=schwab_order_id,
            position_id=position_id,
            order_type="SELL_TO_OPEN",
            status="WORKING",
            symbol=option_symbol,
            quantity=quantity,
            limit_price=limit_price,
            is_gtc=False,
            raw_response=response,
        )

        async with AsyncSessionLocal() as db:
            db.add(order)
            await db.commit()
            await db.refresh(order)

        logger.info("Sell-to-open order placed", symbol=option_symbol, qty=quantity, price=limit_price, schwab_id=schwab_order_id)
        return order

    async def place_buy_to_close(
        self,
        option_symbol: str,
        quantity: int,
        limit_price: float,
        position_id: str | None = None,
        gtc: bool = False,
    ) -> Order:
        order_spec = build_buy_to_close_limit(option_symbol, quantity, limit_price, gtc=gtc)
        response = await schwab_client.place_order(order_spec)
        schwab_order_id = str(response.get("orderId", ""))

        order = Order(
            schwab_order_id=schwab_order_id,
            position_id=position_id,
            order_type="BUY_TO_CLOSE",
            status="WORKING",
            symbol=option_symbol,
            quantity=quantity,
            limit_price=limit_price,
            is_gtc=gtc,
            raw_response=response,
        )

        async with AsyncSessionLocal() as db:
            db.add(order)
            await db.commit()
            await db.refresh(order)

        logger.info("Buy-to-close order placed", symbol=option_symbol, qty=quantity, price=limit_price, gtc=gtc, schwab_id=schwab_order_id)
        return order

    async def place_buy_to_close_market(
        self,
        option_symbol: str,
        quantity: int,
        position_id: str | None = None,
    ) -> Order:
        """Place a market BTC order (stop-loss scenario)."""
        order_spec = build_buy_to_close_market(option_symbol, quantity)
        response = await schwab_client.place_order(order_spec)
        schwab_order_id = str(response.get("orderId", ""))

        order = Order(
            schwab_order_id=schwab_order_id,
            position_id=position_id,
            order_type="BUY_TO_CLOSE",
            status="WORKING",
            symbol=option_symbol,
            quantity=quantity,
            limit_price=0.0,
            is_gtc=False,
            raw_response=response,
        )

        async with AsyncSessionLocal() as db:
            db.add(order)
            await db.commit()
            await db.refresh(order)

        logger.info("Buy-to-close market order placed", symbol=option_symbol, qty=quantity, schwab_id=schwab_order_id)
        return order

    async def poll_order_status(self, order: Order) -> Order:
        """Poll Schwab for current order status and update DB."""
        if not order.schwab_order_id:
            return order

        raw = await schwab_client.get_order(order.schwab_order_id)
        new_status = raw.get("status", order.status)
        fill_price = raw.get("price") or raw.get("filledPrice")

        async with AsyncSessionLocal() as db:
            db_order = await db.get(Order, order.id)
            if db_order:
                db_order.status = new_status
                db_order.raw_response = raw
                if new_status == "FILLED" and fill_price:
                    db_order.fill_price = float(fill_price)
                    db_order.filled_at = datetime.utcnow()
                await db.commit()
                await db.refresh(db_order)
                return db_order
        return order

    async def cancel_order(self, order: Order) -> bool:
        if not order.schwab_order_id:
            return False
        success = await schwab_client.cancel_order(order.schwab_order_id)
        if success:
            async with AsyncSessionLocal() as db:
                db_order = await db.get(Order, order.id)
                if db_order:
                    db_order.status = "CANCELLED"
                    await db.commit()
        return success


order_manager = OrderManager()
