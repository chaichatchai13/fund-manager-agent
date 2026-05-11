"""
ProfitManager: runs on a schedule, checks all open positions against their rule's
profit target and stop loss. Places advance GTC orders or immediate BTC orders.
"""
import structlog
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.order import Order
from app.models.position import OptionPosition
from app.models.rule import SellPutRule
from app.services.order_manager import order_manager
from app.services.position_manager import position_manager

logger = structlog.get_logger(__name__)


class ProfitManager:
    async def check_all_positions(self, price_cache: dict[str, float]) -> None:
        """
        Check all OPEN positions. price_cache maps option_symbol → current price.
        Falls back to DB's last known current_price if symbol not in cache.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(OptionPosition).where(OptionPosition.status.in_(["OPEN", "CLOSING"]))
            )
            positions = result.scalars().all()

        for position in positions:
            try:
                await self._check_position(position, price_cache)
            except Exception as exc:
                logger.error("Error checking position", position_id=position.id, error=str(exc))

    async def _check_position(
        self, position: OptionPosition, price_cache: dict[str, float]
    ) -> None:
        # Get current price
        current_price = price_cache.get(position.option_symbol)
        if current_price is None:
            # Fall back to last known price in DB
            current_price = position.current_price
        if current_price is None:
            return

        # Update position price
        await position_manager.update_price(position.id, current_price)

        entry_price = position.premium_received
        if entry_price <= 0:
            return

        unrealized_profit_pct = (entry_price - current_price) / entry_price

        # Load rule
        async with AsyncSessionLocal() as db:
            rule = await db.get(SellPutRule, position.rule_id) if position.rule_id else None

        profit_target_pct = rule.profit_target_pct if rule else 0.75
        stop_loss_pct = rule.stop_loss_pct if rule else None
        profit_approach_pct = rule.profit_approach_pct if rule else None

        buy_back_price = round(entry_price * (1 - profit_target_pct), 2)

        # ── Stop loss ─────────────────────────────────────────────────────────
        if stop_loss_pct is not None and current_price >= entry_price * stop_loss_pct:
            logger.warning(
                "Stop loss triggered",
                position_id=position.id,
                symbol=position.option_symbol,
                entry=entry_price,
                current=current_price,
            )
            # Cancel any pending GTC BTC order first
            if position.exit_order_id and position.status == "CLOSING":
                async with AsyncSessionLocal() as db:
                    existing_order = await db.get(Order, position.exit_order_id)
                    if existing_order and existing_order.status == "WORKING":
                        await order_manager.cancel_order(existing_order)

            exit_order = await order_manager.place_buy_to_close_market(
                option_symbol=position.option_symbol,
                quantity=position.contracts,
                position_id=position.id,
            )
            await position_manager.mark_closing(position.id, exit_order.id)
            return

        # ── Already has a working GTC exit order ─────────────────────────────
        if position.status == "CLOSING" and position.exit_order_id:
            # Check if the GTC order has been filled
            async with AsyncSessionLocal() as db:
                existing_order = await db.get(Order, position.exit_order_id)
            if existing_order and existing_order.status == "FILLED":
                fill_price = existing_order.fill_price or buy_back_price
                await position_manager.close_position(position.id, fill_price, "PROFIT_TARGET")
            return

        # ── Advance GTC BTC order ─────────────────────────────────────────────
        if (
            profit_approach_pct is not None
            and unrealized_profit_pct >= profit_approach_pct
            and position.exit_order_id is None
            and position.status == "OPEN"
        ):
            logger.info(
                "Placing advance GTC BTC order",
                position_id=position.id,
                symbol=position.option_symbol,
                unrealized_profit_pct=round(unrealized_profit_pct * 100, 1),
                buy_back_price=buy_back_price,
            )
            gtc_order = await order_manager.place_buy_to_close(
                option_symbol=position.option_symbol,
                quantity=position.contracts,
                limit_price=buy_back_price,
                position_id=position.id,
                gtc=True,
            )
            await position_manager.mark_closing(position.id, gtc_order.id)
            return

        # ── Immediate profit target hit ───────────────────────────────────────
        if current_price <= buy_back_price and position.status == "OPEN":
            logger.info(
                "Profit target hit — placing immediate BTC",
                position_id=position.id,
                symbol=position.option_symbol,
                entry=entry_price,
                current=current_price,
                buy_back_price=buy_back_price,
            )
            exit_order = await order_manager.place_buy_to_close(
                option_symbol=position.option_symbol,
                quantity=position.contracts,
                limit_price=buy_back_price,
                position_id=position.id,
                gtc=False,
            )
            await position_manager.mark_closing(position.id, exit_order.id)


profit_manager = ProfitManager()
