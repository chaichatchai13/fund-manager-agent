import structlog
from sqlalchemy import select

from app.core.logging import configure_logging
from app.database import AsyncSessionLocal, create_tables
from app.models.scheduler import DEFAULT_JOBS, SchedulerConfig

logger = structlog.get_logger(__name__)


async def on_startup() -> None:
    configure_logging()
    logger.info("Starting Fund Manager Agent")

    # Create DB tables
    await create_tables()
    logger.info("Database tables ready")

    # Seed default scheduler configs if missing
    await _seed_scheduler_config()

    # Initialize Schwab client (non-fatal — app starts in disconnected state if token expired)
    from app.schwab.client import schwab_client
    await schwab_client.initialize()
    if not schwab_client.is_connected:
        logger.warning(
            "Schwab not connected — scheduler and stream disabled until re-authenticated",
            error=schwab_client.auth_error,
        )

    # Start APScheduler
    from app.scheduler.jobs import start_scheduler
    await start_scheduler()

    # Start Schwab streaming only if connected (skip in mock mode or disconnected)
    from app.config import settings
    if not settings.mock_schwab and schwab_client.is_connected:
        from app.schwab.stream_manager import stream_manager
        await stream_manager.start()

    logger.info("Fund Manager Agent started")


async def on_shutdown() -> None:
    logger.info("Shutting down Fund Manager Agent")

    from app.scheduler.jobs import stop_scheduler
    await stop_scheduler()

    from app.config import settings
    if not settings.mock_schwab:
        from app.schwab.stream_manager import stream_manager
        await stream_manager.stop()

    logger.info("Shutdown complete")


async def _seed_scheduler_config() -> None:
    async with AsyncSessionLocal() as session:
        for job in DEFAULT_JOBS:
            result = await session.execute(
                select(SchedulerConfig).where(SchedulerConfig.job_id == job["job_id"])
            )
            if result.scalar_one_or_none() is None:
                session.add(SchedulerConfig(**job))
        await session.commit()
