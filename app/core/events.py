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

    # Initialize Schwab client
    from app.schwab.client import schwab_client
    await schwab_client.initialize()

    # Start APScheduler
    from app.scheduler.jobs import start_scheduler
    await start_scheduler()

    # Start Schwab streaming (skip in mock mode)
    from app.config import settings
    if not settings.mock_schwab:
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
