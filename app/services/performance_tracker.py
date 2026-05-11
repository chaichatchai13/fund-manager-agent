"""
PerformanceTracker: aggregates P&L into daily snapshots and calculates summaries.
"""
from datetime import date, datetime, timedelta

import structlog
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models.performance import DailySnapshot
from app.models.position import OptionPosition
from app.models.trade import ClosedTrade
from app.schemas.performance import ClosedTradeResponse, DailySnapshotResponse, PerformanceSummary
from app.schwab.client import schwab_client

logger = structlog.get_logger(__name__)


class PerformanceTracker:
    async def take_snapshot(self) -> DailySnapshot:
        """Take end-of-day snapshot. Called nightly at 4:30 PM ET."""
        today = date.today()

        # Get account data
        account = await schwab_client.get_account()
        balances = account.get("securitiesAccount", {}).get("currentBalances", {})
        portfolio_value = float(balances.get("liquidationValue") or 0)
        buying_power = float(balances.get("buyingPower") or 0)

        async with AsyncSessionLocal() as db:
            # Count open positions
            open_count_result = await db.execute(
                select(func.count(OptionPosition.id)).where(OptionPosition.status == "OPEN")
            )
            open_count = open_count_result.scalar() or 0

            # Total unrealized P&L from open positions
            unrealized_result = await db.execute(
                select(func.sum(OptionPosition.unrealized_pnl)).where(
                    OptionPosition.status == "OPEN"
                )
            )
            total_unrealized = float(unrealized_result.scalar() or 0)

            # Today's realized P&L (closed trades today)
            daily_result = await db.execute(
                select(func.sum(ClosedTrade.realized_pnl)).where(
                    func.date(ClosedTrade.closed_at) == today
                )
            )
            daily_realized = float(daily_result.scalar() or 0)

            # Cumulative realized P&L (all time)
            cumulative_result = await db.execute(
                select(func.sum(ClosedTrade.realized_pnl))
            )
            cumulative = float(cumulative_result.scalar() or 0)

            # Upsert snapshot
            existing = await db.execute(
                select(DailySnapshot).where(DailySnapshot.snapshot_date == today)
            )
            snapshot = existing.scalar_one_or_none()
            if snapshot:
                snapshot.total_portfolio_value = portfolio_value
                snapshot.buying_power = buying_power
                snapshot.open_positions_count = open_count
                snapshot.total_unrealized_pnl = total_unrealized
                snapshot.daily_realized_pnl = daily_realized
                snapshot.cumulative_realized_pnl = cumulative
            else:
                snapshot = DailySnapshot(
                    snapshot_date=today,
                    total_portfolio_value=portfolio_value,
                    buying_power=buying_power,
                    open_positions_count=open_count,
                    total_unrealized_pnl=total_unrealized,
                    daily_realized_pnl=daily_realized,
                    cumulative_realized_pnl=cumulative,
                )
                db.add(snapshot)
            await db.commit()
            await db.refresh(snapshot)

        logger.info("Daily snapshot taken", date=today, portfolio_value=portfolio_value)
        return snapshot

    async def get_summary(self, period: str) -> PerformanceSummary:
        """
        period: "today" | "week" | "month" | "all_time"
        """
        today = date.today()
        if period == "today":
            start = today
        elif period == "week":
            start = today - timedelta(days=7)
        elif period == "month":
            start = today - timedelta(days=30)
        else:
            start = date(2000, 1, 1)

        async with AsyncSessionLocal() as db:
            trades_result = await db.execute(
                select(ClosedTrade).where(func.date(ClosedTrade.closed_at) >= start)
            )
            trades = trades_result.scalars().all()

            unrealized_result = await db.execute(
                select(func.sum(OptionPosition.unrealized_pnl)).where(
                    OptionPosition.status == "OPEN"
                )
            )
            total_unrealized = float(unrealized_result.scalar() or 0)

        realized = sum(t.realized_pnl for t in trades)
        total_pnl = realized + total_unrealized
        wins = sum(1 for t in trades if t.realized_pnl > 0)
        win_rate = (wins / len(trades) * 100) if trades else None

        # Get portfolio value from latest snapshot
        async with AsyncSessionLocal() as db:
            latest = await db.execute(
                select(DailySnapshot).order_by(DailySnapshot.snapshot_date.desc()).limit(1)
            )
            snap = latest.scalar_one_or_none()
        portfolio_value = snap.total_portfolio_value if snap else None
        pnl_pct = (total_pnl / portfolio_value * 100) if portfolio_value else None

        return PerformanceSummary(
            period=period,
            realized_pnl=round(realized, 2),
            unrealized_pnl=round(total_unrealized, 2),
            total_pnl=round(total_pnl, 2),
            pnl_pct=round(pnl_pct, 2) if pnl_pct is not None else None,
            trades_closed=len(trades),
            win_rate=round(win_rate, 1) if win_rate is not None else None,
            portfolio_value=portfolio_value,
        )

    async def get_daily_series(self, start: date, end: date) -> list[DailySnapshotResponse]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DailySnapshot)
                .where(DailySnapshot.snapshot_date >= start, DailySnapshot.snapshot_date <= end)
                .order_by(DailySnapshot.snapshot_date)
            )
            snapshots = result.scalars().all()
        return [DailySnapshotResponse.model_validate(s) for s in snapshots]

    async def get_trade_history(
        self, symbol: str | None = None, limit: int = 50
    ) -> list[ClosedTradeResponse]:
        async with AsyncSessionLocal() as db:
            query = select(ClosedTrade).order_by(ClosedTrade.closed_at.desc()).limit(limit)
            if symbol:
                query = query.where(ClosedTrade.underlying_symbol == symbol)
            result = await db.execute(query)
            trades = result.scalars().all()
        return [ClosedTradeResponse.model_validate(t) for t in trades]


performance_tracker = PerformanceTracker()
