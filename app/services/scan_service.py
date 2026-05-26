"""
ScanService: orchestrates RulesEngine → OrderManager → PositionManager.
Called by the APScheduler scan_job.

Order placement retries: up to MAX_ORDER_ATTEMPTS per candidate.
If all attempts fail, the rejection reason is saved to the rule's last_error
field so it appears in the UI.
"""
import asyncio
from datetime import datetime

import structlog

from app.database import AsyncSessionLocal
from app.rules.engine import rules_engine
from app.schwab.client import schwab_client
from app.services.order_manager import order_manager
from app.services.position_manager import position_manager

logger = structlog.get_logger(__name__)

MAX_ORDER_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3  # pause between attempts


def _extract_rejection_reason(raw_response: dict | None) -> str:
    """
    Pull the most useful human-readable rejection reason out of a Schwab
    order status response dict.  Returns a non-empty string.
    """
    if not raw_response:
        return "Order rejected — no details returned by Schwab"

    # Fields Schwab may populate
    for key in ("statusDescription", "cancelType", "tag"):
        val = raw_response.get(key)
        if val:
            return str(val)

    # Fall back to the status itself
    status = raw_response.get("status", "REJECTED")
    return f"Order {status} by Schwab (no description provided)"


async def _save_rule_error(rule_id: str, error_msg: str) -> None:
    """Persist the last error message to the rule row."""
    try:
        from app.models.rule import SellPutRule
        async with AsyncSessionLocal() as db:
            rule = await db.get(SellPutRule, rule_id)
            if rule:
                rule.last_error = error_msg[:500]
                rule.last_error_at = datetime.utcnow()
                await db.commit()
    except Exception as exc:
        logger.warning("Could not save rule error to DB", rule_id=rule_id, error=str(exc))


async def _clear_rule_error(rule_id: str) -> None:
    """Clear any stale error once an order succeeds."""
    try:
        from app.models.rule import SellPutRule
        async with AsyncSessionLocal() as db:
            rule = await db.get(SellPutRule, rule_id)
            if rule and rule.last_error:
                rule.last_error = None
                rule.last_error_at = None
                await db.commit()
    except Exception as exc:
        logger.warning("Could not clear rule error in DB", rule_id=rule_id, error=str(exc))


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
            placed_rule_id = candidate.rule.id if hasattr(candidate, "rule") and candidate.rule else None

            try:
                entry_order = await self._place_with_retry(
                    option_symbol=c.symbol,
                    quantity=candidate.contracts,
                    limit_price=round(c.mid, 2),
                    rule_id=placed_rule_id,
                )

                if entry_order is None:
                    # All attempts exhausted — error already saved to rule
                    continue

                # Order accepted (WORKING or FILLED) — create position record
                position = await position_manager.create_from_trade_candidate(candidate, entry_order)

                # Link order → position
                async with AsyncSessionLocal() as db2:
                    order = await db2.get(type(entry_order), entry_order.id)
                    if order:
                        order.position_id = position.id
                        await db2.commit()

                # Clear any previous error from the rule
                if placed_rule_id:
                    await _clear_rule_error(placed_rule_id)

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
                if placed_rule_id:
                    await _save_rule_error(placed_rule_id, f"Unexpected error: {exc}")

        return created_position_ids

    async def _place_with_retry(
        self,
        option_symbol: str,
        quantity: int,
        limit_price: float,
        rule_id: str | None,
    ):
        """
        Attempt to place a sell-to-open order up to MAX_ORDER_ATTEMPTS times.
        Returns the accepted Order on success, or None after all attempts fail.
        The rejection reason is saved to the rule on final failure.
        """
        last_reason = "Unknown rejection"

        for attempt in range(1, MAX_ORDER_ATTEMPTS + 1):
            entry_order = await order_manager.place_sell_to_open(
                option_symbol=option_symbol,
                quantity=quantity,
                limit_price=limit_price,
            )

            # Poll Schwab after a short delay to catch immediate rejections
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            entry_order = await order_manager.poll_order_status(entry_order)

            if entry_order.status not in ("REJECTED", "CANCELLED"):
                # Success
                return entry_order

            # Rejected — extract why
            last_reason = _extract_rejection_reason(entry_order.raw_response)
            logger.warning(
                "Order rejected by Schwab",
                symbol=option_symbol,
                attempt=attempt,
                max_attempts=MAX_ORDER_ATTEMPTS,
                schwab_order_id=entry_order.schwab_order_id,
                status=entry_order.status,
                reason=last_reason,
            )

            if attempt < MAX_ORDER_ATTEMPTS:
                logger.info(
                    "Retrying order placement",
                    symbol=option_symbol,
                    next_attempt=attempt + 1,
                )
                await asyncio.sleep(2)  # brief pause before retry

        # All attempts exhausted
        error_msg = f"{option_symbol}: {last_reason} (failed after {MAX_ORDER_ATTEMPTS} attempts)"
        logger.error(
            "Order placement failed after all retry attempts",
            symbol=option_symbol,
            reason=last_reason,
        )
        if rule_id:
            await _save_rule_error(rule_id, error_msg)
        return None


scan_service = ScanService()
