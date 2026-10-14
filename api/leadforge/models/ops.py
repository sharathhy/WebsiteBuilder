import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import ApiProvider, JobQueue, JobStatus


class Job(UUIDPk, Timestamps, Base):
    """Durable record of each unit of work: progress, retries and the dead-letter view."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_queue_status", "queue", "status"),)

    queue: Mapped[JobQueue] = mapped_column(str_enum(JobQueue, "job_queue"))
    kind: Mapped[str] = mapped_column(String(100))
    # Same key => same job. Enqueueing twice returns the existing row.
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus, "job_status"), default=JobStatus.QUEUED
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column()
    error: Mapped[str | None] = mapped_column(Text)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL"), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiUsage(UUIDPk, Timestamps, Base):
    """One row per billable external call, for quota tracking and the monthly budget cap."""

    __tablename__ = "api_usage"
    __table_args__ = (Index("ix_api_usage_provider_created", "provider", "created_at"),)

    provider: Mapped[ApiProvider] = mapped_column(str_enum(ApiProvider, "api_provider"))
    operation: Mapped[str] = mapped_column(String(100))
    units: Mapped[int] = mapped_column(Integer, default=1)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0))
    mocked: Mapped[bool] = mapped_column(default=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
