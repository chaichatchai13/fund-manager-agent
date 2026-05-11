"""
ScanService: orchestrates RulesEngine → OrderManager → PositionManager.
Called by the APScheduler scan_job.
"""
import structlog

from app.database import AsyncSessionLocal
from app.rules.engine import rules_engine
from app.schwab.client import schwab_client
from app.services.order_manager import order_manager
from app.services.position_manager import position_manager

logger = structlog.get_logger(__name__)


class ScanService:
    async def run_scan(self, rule_id: str | None = None) -> list[str]:
        """
        Run a full scan cycle. If rule_id is provided, scan only that rule.
        Returns a list of position IDs created.
        """
        async with AsyncSessionLocal() as db:
            if rule_id:
                from sqlalchemy import select
                from app.models.rule import SellPutRule
                result = await db.execute(select(SellPutRule).where(SellPutRule.id == rule_id))
                rule = result.scalar_one_or_none()
                if not rule or not rule.enabled:
                    logger.warning("Rule not found or disabled", rule_id=rule_id)
                    return []
                trade_candidates = await rules_engine.evaluate_rule(rule, db, schwab_client)
            else:
                trade_candidates = await rules_engine.scan_all_enabled_rules(db, schwab_client)

        if not trade_candidates:
            logger.info("Scan complete — no qualifying candidates found")
            return []

        created_position_ids: list[str] = []
        for candidate in trade_candidates:
            c = candidate.candidate
            try:
                import asyncio

                # Place sell-to-open order
                entry_order = await order_manager.place_sell_to_open(
                    option_symbol=c.symbol,
                    quantity=candidate.contracts,
                    limit_price=round(c.mid, 2),
                )

                # Poll Schwab once after a short delay to catch immediate rejections
                # before creating the position record.
                await asyncio.sleep(3)
                entry_order = await order_manager.poll_order_status(entry_order)

                if entry_order.status in ("REJECTED", "CANCELLED"):
                    logger.warning(
                        "Order rejected by Schwab — skipping position creation",
                        symbol=c.symbol,
                        schwab_order_id=entry_order.schwab_order_id,
                        status=entry_order.status,
                    )
                    continue

                # Order accepted (WORKING or FILLED) — create position record
                position = await position_manager.create_from_trade_candidate(candidate, entry_order)

                # Link order → position
                from app.database import AsyncSessionLocal as _db
                async with _db() as db2:
                    order = await db2.get(type(entry_order), entry_order.id)
                    if order:
                        order.position_id = position.id
                        await db2.commit()

                created_position_ids.append(position.id)
                logger.info(
                    "Trade placed",
                    symbol=c.symbol,
                    strike=c.strike,
                    contracts=candidate.contracts,
                    premium=c.mid,
                    order_status=entry_order.status,
                    position_id=position.id,
                )
            except Exception as exc:
                logger.error("Failed to place trade", symbol=c.symbol, error=str(exc))

        return created_position_ids


scan_service = ScanService()
