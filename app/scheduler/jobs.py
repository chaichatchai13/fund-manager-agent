"""
APScheduler job definitions.
All jobs respect market hours and load their intervals from scheduler_config table.
"""
import asyncio
from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.order import Order
from app.models.scheduler import SchedulerConfig

logger = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None

# Track when orders were placed to implement max_runtime_minutes for order_status_job
_order_tracking_start: datetime | None = None


def is_market_open() -> bool:
    """Returns True during NYSE market hours (9:30 AM – 4:00 PM ET, Mon–Fri)."""
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now < market_close


async def scan_job() -> None:
    if not is_market_open():
        return
    logger.info("Running scan job")
    from app.services.scan_service import scan_service
    try:
        positions = await scan_service.run_scan()
        if positions:
            global _order_tracking_start
            _order_tracking_start = datetime.now(timezone.utc)
    except Exception as exc:
        logger.error("Scan job failed", error=str(exc))


async def profit_check_job() -> None:
    if not is_market_open():
        return
    from app.schwab.stream_manager import stream_manager
    from app.services.profit_manager import profit_manager
    try:
        await profit_manager.check_all_positions(stream_manager.price_cache)
    except Exception as exc:
        logger.error("Profit check job failed", error=str(exc))


async def order_status_job() -> None:
    """Poll working orders for fill status. Respects max_runtime_minutes window."""
    global _order_tracking_start

    # Check max_runtime window
    if _order_tracking_start is not None:
        async with AsyncSessionLocal() as db:
            config_result = await db.execute(
                select(SchedulerConfig).where(SchedulerConfig.job_id == "order_status_job")
            )
            config = config_result.scalar_one_or_none()
        max_min = config.max_runtime_minutes if config else 60
        elapsed = (datetime.now(timezone.utc) - _order_tracking_start).total_seconds() / 60
        if elapsed > max_min:
            _order_tracking_start = None
            return  # Stop polling until next scan places orders

    from app.services.order_manager import order_manager
    from app.services.position_manager import position_manager

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Order).where(Order.status == "WORKING")
        )
        working_orders = result.scalars().all()

    if not working_orders:
        return

    for order in working_orders:
        try:
            updated = await order_manager.poll_order_status(order)
            if updated.status == "FILLED" and updated.order_type == "BUY_TO_CLOSE":
                fill_price = updated.fill_price or 0.0
                if updated.position_id:
                    await position_manager.close_position(
                        updated.position_id, fill_price, "PROFIT_TARGET"
                    )
                    # Subscribe new positions to stream
                    await _refresh_stream_subscriptions()
        except Exception as exc:
            logger.error("Order status poll failed", order_id=order.id, error=str(exc))


async def roll_check_job() -> None:
    """
    Check all OPEN positions for ITM roll candidates.
    Runs every 15 min during market hours (rolling is only meaningful while the market is open).
    """
    if not is_market_open():
        return
    from app.schwab.stream_manager import stream_manager
    from app.services.roll_manager import roll_manager
    try:
        new_ids = await roll_manager.check_and_roll_all(stream_manager.price_cache)
        if new_ids:
            logger.info("Roll check: positions rolled", new_position_ids=new_ids)
    except Exception as exc:
        logger.error("Roll check job failed", error=str(exc))


async def reconcile_positions_job() -> None:
    """
    Sync DB positions against live Schwab account.
    Schwab is the single source of truth — positions missing from Schwab are
    automatically closed, expired, or deleted (if phantom).
    Runs every 15 min; does NOT require market to be open (assignments/expirations
    happen overnight too).
    """
    from app.services.position_reconciler import position_reconciler
    try:
        summary = await position_reconciler.reconcile()
        if any(v > 0 for k, v in summary.items() if k != "checked"):
            logger.info("Position reconciliation made changes", **summary)
    except Exception as exc:
        logger.error("Reconcile job failed", error=str(exc))


async def daily_snapshot_job() -> None:
    logger.info("Taking daily performance snapshot")
    from app.services.performance_tracker import performance_tracker
    try:
        await performance_tracker.take_snapshot()
    except Exception as exc:
        logger.error("Daily snapshot failed", error=str(exc))


async def iv_refresh_job() -> None:
    """Nightly IV rank refresh for all rule symbols."""
    from sqlalchemy import select
    from app.models.rule import SellPutRule
    from app.schwab.client import schwab_client
    from app.schwab.iv_rank import iv_rank_tracker

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SellPutRule).where(SellPutRule.enabled == True))
        rules = result.scalars().all()

    all_symbols = set()
    for rule in rules:
        for sym_entry in (rule.symbols or []):
            all_symbols.add(sym_entry["symbol"])

    if all_symbols:
        logger.info("Refreshing IV ranks", symbols=list(all_symbols))
        await iv_rank_tracker.refresh_all(list(all_symbols), schwab_client)


async def _refresh_stream_subscriptions() -> None:
    """Subscribe all open position option symbols to the live stream."""
    from app.models.position import OptionPosition
    from app.schwab.stream_manager import stream_manager
    from app.config import settings
    if settings.mock_schwab:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OptionPosition.option_symbol).where(OptionPosition.status == "OPEN")
        )
        symbols = [row[0] for row in result.fetchall()]

    if symbols:
        await stream_manager.subscribe(symbols)


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="America/New_York")

    # Load intervals from DB
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SchedulerConfig))
        configs = {c.job_id: c for c in result.scalars().all()}

    def get_interval(job_id: str, default: int) -> int:
        c = configs.get(job_id)
        return c.interval_minutes if (c and c.interval_minutes) else default

    scan_interval = get_interval("scan_job", 15)
    profit_interval = get_interval("profit_check_job", 2)
    order_interval = get_interval("order_status_job", 5)

    _scheduler.add_job(scan_job, IntervalTrigger(minutes=scan_interval), id="scan_job", replace_existing=True)
    _scheduler.add_job(profit_check_job, IntervalTrigger(minutes=profit_interval), id="profit_check_job", replace_existing=True)
    _scheduler.add_job(order_status_job, IntervalTrigger(minutes=order_interval), id="order_status_job", replace_existing=True)
    _scheduler.add_job(roll_check_job, IntervalTrigger(minutes=15), id="roll_check_job", replace_existing=True)
    _scheduler.add_job(reconcile_positions_job, IntervalTrigger(minutes=15), id="reconcile_positions_job", replace_existing=True)
    _scheduler.add_job(daily_snapshot_job, CronTrigger(hour=16, minute=30, timezone="America/New_York"), id="daily_snapshot_job", replace_existing=True)
    _scheduler.add_job(iv_refresh_job, CronTrigger(hour=17, minute=0, timezone="America/New_York"), id="iv_refresh_job", replace_existing=True)

    _scheduler.start()
    logger.info("Scheduler started", scan_interval=scan_interval, profit_interval=profit_interval)


async def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


async def reschedule_job(job_id: str, interval_minutes: int) -> None:
    """Reschedule a job with a new interval. Used by agent/UI."""
    if not _scheduler:
        return
    job_map = {
        "scan_job": scan_job,
        "profit_check_job": profit_check_job,
        "order_status_job": order_status_job,
    }
    if job_id in job_map:
        _scheduler.reschedule_job(
            job_id, trigger=IntervalTrigger(minutes=interval_minutes)
        )
        logger.info("Job rescheduled", job_id=job_id, interval_minutes=interval_minutes)
