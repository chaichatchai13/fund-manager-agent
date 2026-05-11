"""
RollManager: detects ITM positions that need rolling and executes the roll.

Roll logic:
  1. Detect: position is ITM AND DTE <= rule.roll_when_dte AND rule.itm_action == "roll"
  2. Buy-to-close the current position at market mid
  3. Scan the option chain for expiry closest to (today + roll_target_weeks * 7 days)
  4. Filter OTM strikes only
  5. Pick the strike whose mid premium is closest to the original entry premium
  6. Sell-to-open the new position → creates a new position record linked to same rule

ITM definition:
  - Short CALL (covered call): stock_price > strike  (call is in the money)
  - Short PUT:                  stock_price < strike  (put is in the money)
"""
from datetime import date, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.position import OptionPosition
from app.models.rule import SellPutRule
from app.schwab.option_chain import OptionCandidate, parse_option_chain

logger = structlog.get_logger(__name__)


class RollManager:

    async def check_and_roll_all(self, price_cache: dict) -> list[str]:
        """
        Check all OPEN positions against their rules.
        Returns list of new position IDs created by rolls.
        """
        from app.schwab.client import schwab_client

        new_position_ids: list[str] = []

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(OptionPosition).where(OptionPosition.status == "OPEN")
            )
            positions = result.scalars().all()

        for pos in positions:
            try:
                rolled_id = await self._maybe_roll(pos, price_cache)
                if rolled_id:
                    new_position_ids.append(rolled_id)
            except Exception as exc:
                logger.error("Roll check failed", position_id=pos.id, error=str(exc))

        return new_position_ids

    async def roll_position(self, position_id: str) -> str | None:
        """Manually roll a specific position. Returns new position ID or None."""
        async with AsyncSessionLocal() as db:
            pos = await db.get(OptionPosition, position_id)
            if not pos:
                raise ValueError(f"Position {position_id} not found")
            if pos.status not in ("OPEN", "CLOSING"):
                raise ValueError(f"Position status is {pos.status}, cannot roll")

        # Use current_price as live mark; fall back to last known
        price_cache: dict = {}
        return await self._maybe_roll(pos, price_cache, force=True)

    async def _maybe_roll(
        self,
        pos: OptionPosition,
        price_cache: dict,
        force: bool = False,
    ) -> str | None:
        from app.schwab.client import schwab_client

        # Load the rule
        async with AsyncSessionLocal() as db:
            rule = await db.get(SellPutRule, pos.rule_id) if pos.rule_id else None

        if not rule:
            return None

        itm_action = getattr(rule, "itm_action", "let_assign")
        roll_when_dte = getattr(rule, "roll_when_dte", 7)
        roll_target_weeks = getattr(rule, "roll_target_weeks", 4)

        if itm_action != "roll" and not force:
            return None

        # Check DTE
        today = date.today()
        dte = (pos.expiration_date - today).days
        if not force and dte > roll_when_dte:
            return None  # Too early to roll

        # Determine if position is ITM
        # Use price_cache for live price, fall back to stock_price_at_entry
        stock_price = price_cache.get(pos.option_symbol)
        if stock_price is None:
            quotes = await schwab_client.get_quotes([pos.underlying_symbol])
            q = quotes.get(pos.underlying_symbol, {}).get("quote", {})
            stock_price = float(q.get("lastPrice") or q.get("mark") or 0)

        is_call = "C" in pos.option_symbol.replace(pos.underlying_symbol, "").upper()
        itm = (is_call and stock_price > pos.strike) or (not is_call and stock_price < pos.strike)

        if not itm and not force:
            logger.debug("Position not ITM — skipping roll", symbol=pos.option_symbol, stock=stock_price, strike=pos.strike)
            return None

        logger.info(
            "Rolling position",
            symbol=pos.option_symbol,
            dte=dte,
            stock_price=stock_price,
            strike=pos.strike,
            is_call=is_call,
            forced=force,
        )

        # ── Step 1: Buy-to-close current position ─────────────────────────
        current_mark = pos.current_price or pos.premium_received * 0.5
        from app.services.order_manager import order_manager
        from app.services.position_manager import position_manager

        btc_order = await order_manager.place_buy_to_close(
            option_symbol=pos.option_symbol,
            quantity=pos.contracts,
            limit_price=round(float(current_mark), 2),
            position_id=pos.id,
        )

        # Mark existing position as CLOSING
        await position_manager.mark_closing(pos.id, btc_order.id)

        # ── Step 2: Find the new option to roll into ───────────────────────
        target_expiry = today + timedelta(weeks=roll_target_weeks)
        contract_type = "CALL" if is_call else "PUT"

        # Fetch chain with a window around the target expiry (±1 week)
        target_dte = (target_expiry - today).days
        raw_chain = await schwab_client.get_option_chain(
            pos.underlying_symbol,
            min_dte=max(1, target_dte - 7),
            max_dte=target_dte + 7,
            contract_type=contract_type,
        )

        from app.schwab.iv_rank import iv_rank_tracker
        iv_rank = iv_rank_tracker.get_iv_rank(pos.underlying_symbol)
        candidates = parse_option_chain(raw_chain, iv_rank=iv_rank, contract_type=contract_type)

        # Filter OTM only
        if is_call:
            otm_candidates = [c for c in candidates if c.strike > stock_price]
        else:
            otm_candidates = [c for c in candidates if c.strike < stock_price]

        if not otm_candidates:
            logger.warning("No OTM candidates found for roll", symbol=pos.underlying_symbol, target_expiry=str(target_expiry))
            return None

        # Pick strike with premium closest to original entry premium
        target_premium = pos.premium_received
        best = min(otm_candidates, key=lambda c: abs(c.mid - target_premium))

        logger.info(
            "Roll candidate selected",
            new_symbol=best.symbol,
            new_strike=best.strike,
            new_expiry=str(best.expiration_date),
            new_premium=best.mid,
            entry_premium=target_premium,
            premium_diff=round(best.mid - target_premium, 2),
        )

        # ── Step 3: Sell-to-open the new position ─────────────────────────
        sto_order = await order_manager.place_sell_to_open(
            option_symbol=best.symbol,
            quantity=pos.contracts,
            limit_price=round(best.mid, 2),
        )

        # Wait briefly and check if accepted
        import asyncio
        await asyncio.sleep(3)
        sto_order = await order_manager.poll_order_status(sto_order)

        if sto_order.status in ("REJECTED", "CANCELLED"):
            logger.warning("Roll STO order rejected", symbol=best.symbol, status=sto_order.status)
            return None

        # ── Step 4: Create new position record ────────────────────────────
        from app.models.position import OptionPosition as OPModel
        from datetime import datetime, timezone

        new_pos = OPModel(
            rule_id=pos.rule_id,
            schwab_account_hash=pos.schwab_account_hash,
            underlying_symbol=pos.underlying_symbol,
            option_symbol=best.symbol,
            strike=best.strike,
            expiration_date=best.expiration_date,
            dte_at_entry=(best.expiration_date - today).days,
            delta_at_entry=best.delta,
            iv_rank_at_entry=iv_rank,
            stock_price_at_entry=stock_price,
            contracts=pos.contracts,
            premium_received=best.mid,
            total_credit=round(best.mid * pos.contracts * 100, 2),
            current_price=best.mid,
            unrealized_pnl=0.0,
            status="OPEN",
            entry_order_id=sto_order.id,
        )

        async with AsyncSessionLocal() as db:
            db.add(new_pos)
            await db.commit()
            await db.refresh(new_pos)

            # Link STO order → new position
            sto_db = await db.get(type(sto_order), sto_order.id)
            if sto_db:
                sto_db.position_id = new_pos.id
                await db.commit()

        logger.info(
            "Roll complete",
            old_symbol=pos.option_symbol,
            new_symbol=best.symbol,
            new_position_id=new_pos.id,
        )
        return new_pos.id


# Singleton
roll_manager = RollManager()
