from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Default job configs seeded at startup
DEFAULT_JOBS = [
    {"job_id": "scan_job", "interval_minutes": 15, "max_runtime_minutes": None, "enabled": True},
    {"job_id": "profit_check_job", "interval_minutes": 2, "max_runtime_minutes": None, "enabled": True},
    {"job_id": "order_status_job", "interval_minutes": 5, "max_runtime_minutes": 60, "enabled": True},
    {"job_id": "daily_snapshot_job", "interval_minutes": None, "max_runtime_minutes": None, "enabled": True},
]


class SchedulerConfig(Base):
    __tablename__ = "scheduler_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
