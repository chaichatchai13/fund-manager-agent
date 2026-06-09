"""
PositionReconciler: keeps ThetaFlow's DB in sync with Schwab's actual account positions.

Schwab is the single source of truth for whether a position exists.
ThetaFlow's DB holds metadata Schwab doesn't know about:
  - which rule opened it
  - entry premium / total_credit for P&L tracking
  - profit target, status history

Reconciliation logic (runs every 15 min):
  For every DB position with status OPEN or CLOSING:
    - If found in Schwab → position is live; update current mark price
    - If NOT found in Schwab:
        - expiration_date <= today  → mark EXPIRED (or ASSIGNED if it was a short call/put)
        - expiration_date > today   → mark CLOSED (was closed externally / manually in Schwab)
        - entry_order_id is None    → was never real; delete outright (phantom)
"""
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.position import OptionPosition

logger = structlog.get_logger(__name__)


class PositionReconciler:

    async def reconcile(self) -> dict:
        """
        Fetch live Schwab positions and reconcile against DB.
        Returns a summary of actions taken.
        """
        from app.schwab.client import schwab_client

        # Fetch live account from Schwab
        try:
            account = await schwab_client.get_account()
        except Exception as exc:
            logger.error("Reconciler: failed to fetch Schwab account", error=str(exc))
            return {"error": str(exc)}

        schwab_positions = (
            account.get("securitiesAccount", {}).get("positions", [])
        )

        # Build a set of live option symbols in Schwab (normalised to uppercase, no spaces)
        schwab_option_symbols: set[str] = set()
        for pos in schwab_positions:
            inst = pos.get("instrument", {})
            if inst.get("assetType") == "OPTION":
                raw_sym = inst.get("symbol", "")
                # Schwab may use spaces; normalise to match our DB format
                normalised = raw_sym.replace(" ", "_").upper()
                schwab_option_symbols.add(normalised)
                schwab_option_symbols.add(raw_sym.upper())   # also keep original

        today = date.today()
        summary = {"checked": 0, "updated_price": 0, "closed": 0, "expired": 0, "deleted_phantom": 0}

        from app.models.order import Order

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(OptionPosition).where(
                    OptionPosition.status.in_(["OPEN", "CLOSING"])
                )
            )
            active_positions = result.scalars().all()
            summary["checked"] = len(active_positions)

            # Pre-load rejected/cancelled order IDs (orders placed but never filled)
            rejected_result = await db.execute(
                select(Order.id).where(
                    Order.status.in_(["REJECTED", "CANCELLED"]),
                    Order.fill_price.is_(None),
                )
            )
            rejected_order_ids = {row[0] for row in rejected_result.fetchall()}

            for pos in active_positions:
                sym_normalised = pos.option_symbol.replace(" ", "_").upper()

                if _symbol_in_schwab(sym_normalised, schwab_option_symbols):
                    # Still live — update mark price from Schwab if available
                    schwab_mark = _get_schwab_mark(pos.option_symbol, schwab_positions)
                    if schwab_mark is not None:
                        pos.current_price = schwab_mark
                        pos.unrealized_pnl = round(
                            (pos.premium_received - schwab_mark) * pos.contracts * 100, 2
                        )
                        summary["updated_price"] += 1
                else:
                    # Not in Schwab — phantom if order never filled
                    was_phantom = (
                        pos.entry_order_id is None
                        or pos.entry_order_id in rejected_order_ids
                    )

                    if was_phantom:
                        logger.info(
                            "Reconciler: deleting phantom position (order rejected or never placed)",
                            option_symbol=pos.option_symbol,
                            position_id=pos.id,
                            entry_order_id=pos.entry_order_id,
                        )
                        await db.delete(pos)
                        summary["deleted_phantom"] += 1

                    elif pos.expiration_date <= today:
                        pos.status = "EXPIRED"
                        pos.closed_at = datetime.now(timezone.utc)
                        logger.info("Reconciler: marking EXPIRED", option_symbol=pos.option_symbol)
                        summary["expired"] += 1

                    else:
                        pos.status = "CLOSED"
                        pos.closed_at = datetime.now(timezone.utc)
                        logger.info("Reconciler: marking CLOSED (removed from Schwab)", option_symbol=pos.option_symbol)
                        summary["closed"] += 1

            await db.commit()

        logger.info("Reconciler: done", **summary)

        # Notify all WebSocket clients if any positions changed status
        if summary.get("closed", 0) + summary.get("expired", 0) + summary.get("deleted_phantom", 0) + summary.get("updated_price", 0) > 0:
            try:
                from app.api.routes.websocket import broadcast_positions
                await broadcast_positions()
            except Exception as exc:
                logger.warning("Reconciler: failed to broadcast position update", error=str(exc))

        return summary


def _symbol_in_schwab(normalised_sym: str, schwab_symbols: set[str]) -> bool:
    """Fuzzy match: check if our DB symbol matches any Schwab symbol."""
    if normalised_sym in schwab_symbols:
        return True
    # Strip leading underlying ticker variance — compare just date+strike part
    # e.g. IREN_260515C00048000 vs IREN 260515C00048000
    for s in schwab_symbols:
        if s.replace(" ", "_") == normalised_sym:
            return True
    return False


def _get_schwab_mark(option_symbol: str, schwab_positions: list) -> float | None:
    """Find the current mark price for a symbol in the Schwab positions list."""
    normalised = option_symbol.replace(" ", "_").upper()
    for pos in schwab_positions:
        inst = pos.get("instrument", {})
        if inst.get("assetType") != "OPTION":
            continue
        raw = inst.get("symbol", "")
        if raw.replace(" ", "_").upper() == normalised:
            qty = abs(pos.get("shortQuantity", 0) or pos.get("longQuantity", 0))
            if qty > 0:
                market_value = pos.get("marketValue")
                if market_value is not None:
                    # market_value is negative for short options; mark = |value| / (qty * 100)
                    return round(abs(market_value) / (qty * 100), 4)
    return None


# Singleton
position_reconciler = PositionReconciler()
