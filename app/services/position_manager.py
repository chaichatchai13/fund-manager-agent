"""
PositionManager: creates/updates/closes OptionPosition records in the DB.
"""
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.order import Order
from app.models.position import OptionPosition
from app.models.trade import ClosedTrade
from app.rules.engine import TradeCandidate
from app.schwab.client import schwab_client

logger = structlog.get_logger(__name__)


class PositionManager:
    async def create_from_trade_candidate(
        self, candidate: TradeCandidate, entry_order: Order
    ) -> OptionPosition:
        c = candidate.candidate
        total_credit = round(c.mid * candidate.contracts * 100, 2)

        position = OptionPosition(
            rule_id=candidate.rule.id,
            schwab_account_hash=schwab_client.account_hash,
            underlying_symbol=c.underlying,
            option_symbol=c.symbol,
            strike=c.strike,
            expiration_date=c.expiration,
            dte_at_entry=c.dte,
            delta_at_entry=c.delta,
            iv_rank_at_entry=c.iv_rank,
            stock_price_at_entry=c.stock_price,
            contracts=candidate.contracts,
            premium_received=c.mid,
            total_credit=total_credit,
            current_price=c.mid,
            unrealized_pnl=0.0,
            status="OPEN",
            entry_order_id=entry_order.id,
        )

        async with AsyncSessionLocal() as db:
            db.add(position)
            await db.commit()
            await db.refresh(position)

        logger.info(
            "Position created",
            symbol=c.symbol,
            strike=c.strike,
            contracts=candidate.contracts,
            total_credit=total_credit,
        )
        # Notify all connected WebSocket clients of the new position
        try:
            from app.api.routes.websocket import broadcast_positions
            await broadcast_positions()
        except Exception:
            pass
        return position

    async def update_price(self, position_id: str, current_price: float) -> None:
        async with AsyncSessionLocal() as db:
            position = await db.get(OptionPosition, position_id)
            if position and position.status == "OPEN":
                position.current_price = current_price
                # Unrealized P&L: (premium received - current price) × 100 × contracts
                position.unrealized_pnl = round(
                    (position.premium_received - current_price) * 100 * position.contracts, 2
                )
                await db.commit()

    async def mark_closing(self, position_id: str, exit_order_id: str) -> None:
        async with AsyncSessionLocal() as db:
            position = await db.get(OptionPosition, position_id)
            if position:
                position.status = "CLOSING"
                position.exit_order_id = exit_order_id
                await db.commit()
        # Notify all connected WebSocket clients of the status change
        try:
            from app.api.routes.websocket import broadcast_positions
            await broadcast_positions()
        except Exception:
            pass

    async def close_position(
        self, position_id: str, exit_price: float, close_reason: str
    ) -> ClosedTrade | None:
        async with AsyncSessionLocal() as db:
            position = await db.get(OptionPosition, position_id)
            if not position:
                return None

            # Mark position closed
            position.status = "CLOSED"
            position.current_price = exit_price
            position.closed_at = datetime.utcnow()
            position.unrealized_pnl = 0.0

            realized_pnl = round(
                (position.premium_received - exit_price) * 100 * position.contracts, 2
            )
            holding_days = (datetime.utcnow().date() - position.opened_at.date()).days

            trade = ClosedTrade(
                position_id=position_id,
                underlying_symbol=position.underlying_symbol,
                option_symbol=position.option_symbol,
                contracts=position.contracts,
                premium_received=position.premium_received,
                exit_price=exit_price,
                realized_pnl=realized_pnl,
                holding_days=holding_days,
                close_reason=close_reason,
            )
            db.add(trade)
            await db.commit()
            await db.refresh(trade)

        logger.info(
            "Position closed",
            position_id=position_id,
            realized_pnl=realized_pnl,
            reason=close_reason,
        )
        # Notify all connected WebSocket clients that the position is gone
        try:
            from app.api.routes.websocket import broadcast_positions
            await broadcast_positions()
        except Exception:
            pass
        return trade


position_manager = PositionManager()
