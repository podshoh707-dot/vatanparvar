"""PostgreSQL asosidagi barqaror rejalashtirilgan vazifalar (scheduled_jobs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import JobStatus


class ScheduledJob(Base, TimestampMixin):
    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    payload_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=JobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
