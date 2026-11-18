"""PostgreSQL asosidagi scheduled_jobs repozitoriysi (atomik lock va idempotency)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobStatus, JobType
from app.models.schedule import ScheduledJob
from app.utils.timezone import now_utc


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
        self,
        *,
        job_type: JobType,
        run_at: datetime,
        idempotency_key: str,
        reference_id: Optional[int] = None,
        payload_json: Optional[dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> tuple[ScheduledJob, bool]:
        """
        Yangi vazifani qo'shadi. Agar idempotency_key allaqachon mavjud bo'lsa,
        dublikat yaratmaydi va mavjud vazifani qaytaradi.
        """
        existing_stmt = select(ScheduledJob).where(ScheduledJob.idempotency_key == idempotency_key)
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return existing, False

        job = ScheduledJob(
            job_type=job_type.value,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            payload_json=payload_json,
            run_at=run_at,
            status=JobStatus.PENDING.value,
            attempts=0,
            max_attempts=max_attempts,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(job)
                await self.session.flush()
            return job, True
        except IntegrityError:
            existing = (await self.session.execute(existing_stmt)).scalar_one()
            return existing, False

    async def recover_stale_locks(self, lock_timeout_seconds: int = 300) -> int:
        """Server uxlab qolgan yoki uzilgan bo'lsa, osilib qolgan running vazifalarni tiklaydi."""
        cutoff = now_utc() - timedelta(seconds=lock_timeout_seconds)
        stmt = (
            select(ScheduledJob)
            .where(
                ScheduledJob.status == JobStatus.RUNNING.value,
                ScheduledJob.locked_at < cutoff,
            )
        )
        stale_jobs = list((await self.session.execute(stmt)).scalars().all())
        recovered = 0
        for job in stale_jobs:
            if job.attempts >= job.max_attempts:
                job.status = JobStatus.FAILED.value
                job.last_error = "Worker lock muddati tugadi va maksimal urinishlar soniga yetdi."
            else:
                job.status = JobStatus.PENDING.value
                job.last_error = "Server qayta ishga tushgani sababli vazifa qayta navbatga qo'yildi."
            job.locked_at = None
            job.locked_by = None
            job.updated_at = now_utc()
            recovered += 1
        await self.session.flush()
        return recovered

    async def claim_due_jobs(
        self,
        *,
        worker_id: str,
        limit: int = 10,
        now: Optional[datetime] = None,
    ) -> list[ScheduledJob]:
        """
        Vaqti kelgan vazifalarni atomik ravishda bitta worker uchun band qiladi.
        PostgreSQL'da FOR UPDATE SKIP LOCKED ishlatadi; SQLite'da conditional UPDATE bilan himoyalanadi.
        """
        current_time = now or now_utc()
        dialect_name = self.session.bind.dialect.name if self.session.bind else ""

        stmt = (
            select(ScheduledJob)
            .where(
                ScheduledJob.status == JobStatus.PENDING.value,
                ScheduledJob.run_at <= current_time,
            )
            .order_by(ScheduledJob.run_at.asc(), ScheduledJob.id.asc())
            .limit(limit)
        )
        if dialect_name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        candidates = list((await self.session.execute(stmt)).scalars().all())
        claimed: list[ScheduledJob] = []

        for job in candidates:
            upd = (
                update(ScheduledJob)
                .where(
                    ScheduledJob.id == job.id,
                    ScheduledJob.status == JobStatus.PENDING.value,
                )
                .values(
                    status=JobStatus.RUNNING.value,
                    locked_at=current_time,
                    locked_by=worker_id,
                    attempts=job.attempts + 1,
                    updated_at=current_time,
                )
            )
            res = await self.session.execute(upd)
            if res.rowcount == 1:
                await self.session.refresh(job)
                claimed.append(job)

        await self.session.flush()
        return claimed

    async def mark_completed(self, job_id: int) -> None:
        now = now_utc()
        upd = (
            update(ScheduledJob)
            .where(ScheduledJob.id == job_id)
            .values(
                status=JobStatus.COMPLETED.value,
                completed_at=now,
                locked_at=None,
                locked_by=None,
                last_error=None,
                updated_at=now,
            )
        )
        await self.session.execute(upd)
        await self.session.flush()

    async def mark_failed_or_retry(
        self,
        job: ScheduledJob,
        error_message: str,
        retry_delay_seconds: int = 60,
    ) -> None:
        now = now_utc()
        if job.attempts < job.max_attempts:
            next_run = now + timedelta(seconds=retry_delay_seconds * job.attempts)
            status = JobStatus.PENDING.value
        else:
            next_run = job.run_at
            status = JobStatus.FAILED.value

        upd = (
            update(ScheduledJob)
            .where(ScheduledJob.id == job.id)
            .values(
                status=status,
                run_at=next_run,
                locked_at=None,
                locked_by=None,
                last_error=error_message[:1000],
                updated_at=now,
            )
        )
        await self.session.execute(upd)
        await self.session.flush()

    async def cancel_by_reference(self, job_type: JobType, reference_id: int) -> int:
        now = now_utc()
        upd = (
            update(ScheduledJob)
            .where(
                ScheduledJob.job_type == job_type.value,
                ScheduledJob.reference_id == reference_id,
                ScheduledJob.status == JobStatus.PENDING.value,
            )
            .values(
                status=JobStatus.CANCELLED.value,
                updated_at=now,
            )
        )
        res = await self.session.execute(upd)
        await self.session.flush()
        return int(res.rowcount or 0)

    async def cancel_pending_by_type(self, job_type: JobType) -> int:
        now = now_utc()
        upd = (
            update(ScheduledJob)
            .where(
                ScheduledJob.job_type == job_type.value,
                ScheduledJob.status == JobStatus.PENDING.value,
            )
            .values(
                status=JobStatus.CANCELLED.value,
                updated_at=now,
            )
        )
        res = await self.session.execute(upd)
        await self.session.flush()
        return int(res.rowcount or 0)

    async def list_upcoming(
        self,
        *,
        job_type: Optional[JobType] = None,
        limit: int = 15,
    ) -> list[ScheduledJob]:
        conditions = [ScheduledJob.status == JobStatus.PENDING.value]
        if job_type is not None:
            conditions.append(ScheduledJob.job_type == job_type.value)
        stmt = (
            select(ScheduledJob)
            .where(*conditions)
            .order_by(ScheduledJob.run_at.asc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
