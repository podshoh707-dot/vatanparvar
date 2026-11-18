"""
PostgreSQL asosidagi barqaror rejalashtirish dvigateli.

Render Free xususiyatlariga to'liq moslashtirilgan:
- Barcha vazifalar PostgreSQL scheduled_jobs jadvalida saqlanadi.
- Server uxlab qolsa va qayta uyg'onsa, osilib qolgan lock'larni tiklaydi va o'tib ketgan vazifalarni bajaradi.
- Bir vazifani ikki worker bajarishidan atomik DB lock bilan himoyalangan.
- Avtomatik test slotlari Asia/Tashkent vaqti bo'yicha idempotency_key bilan yaratiladi.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.models.enums import JobType
from app.repositories.schedule_repo import ScheduleRepository
from app.scheduler.handlers import execute_scheduled_job
from app.services.settings_service import SettingsService
from app.utils.timezone import get_tz, now_local, now_utc

logger = logging.getLogger(__name__)


def _parse_hhmm(raw: str) -> tuple[int, int]:
    try:
        parts = raw.strip().split(":")
        hour = max(0, min(23, int(parts[0])))
        minute = max(0, min(59, int(parts[1])))
        return hour, minute
    except Exception:
        return 9, 0


class PersistentScheduler:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        bot: Bot,
        settings: Optional[Settings] = None,
        worker_id: Optional[str] = None,
    ) -> None:
        self.session_factory = session_factory
        self.bot = bot
        self.settings = settings or get_settings()
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_tick_at: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_tick_at(self) -> Optional[datetime]:
        return self._last_tick_at

    async def start(self) -> None:
        """Scheduler fon jarayonini ishga tushiradi va stale lock'larni tiklaydi."""
        if self._running:
            return
        self._stop_event.clear()
        self._running = True

        # Startup tiklash
        try:
            async with self.session_factory() as session:
                repo = ScheduleRepository(session)
                recovered = await repo.recover_stale_locks(lock_timeout_seconds=180)
                await session.commit()
                if recovered:
                    logger.info("Startup tiklash: %s ta osilib qolgan vazifa navbatga qaytarildi.", recovered)
        except Exception as exc:
            logger.exception("Scheduler startup recovery xatoligi: %s", exc)

        self._task = asyncio.create_task(self._loop(), name="persistent-scheduler")
        logger.info("PersistentScheduler ishga tushdi (worker=%s)", self.worker_id)

    async def stop(self) -> None:
        """Joriy siklni xavfsiz yakunlab scheduler'ni to'xtatadi."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=15)
            except asyncio.TimeoutError:
                self._task.cancel()
            except Exception:
                pass
            self._task = None
        logger.info("PersistentScheduler xavfsiz to'xtatildi.")

    async def sync_auto_test_schedule(
        self,
        session: AsyncSession,
        *,
        days_ahead: int = 2,
        recreate_pending: bool = False,
    ) -> int:
        """
        Avtomatik test sozlamalari asosida kelgusi kunlar uchun Asia/Tashkent slotlarini
        scheduled_jobs jadvaliga idempotent tarzda yozadi.
        """
        settings_svc = SettingsService(session)
        repo = ScheduleRepository(session)
        cfg = await settings_svc.get_auto_publish_config()

        if recreate_pending:
            await repo.cancel_pending_by_type(JobType.AUTO_TEST)

        if not cfg["enabled"]:
            return 0

        tz = get_tz(self.settings.TIMEZONE)
        local_now = now_local(self.settings.TIMEZONE)
        per_day = max(1, min(24, int(cfg["per_day"])))
        interval_min = max(5, int(cfg["interval_minutes"]))
        hour, minute = _parse_hhmm(str(cfg["start_time"]))
        active_days = set(int(d) for d in (cfg["weekdays"] or []))

        created_count = 0
        for day_offset in range(days_ahead):
            target_date = (local_now + timedelta(days=day_offset)).date()
            if target_date.weekday() not in active_days:
                continue

            base_local = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour,
                minute,
                tzinfo=tz,
            )

            for slot_idx in range(1, per_day + 1):
                slot_local = base_local + timedelta(minutes=interval_min * (slot_idx - 1))
                # Ertangi kunga o'tib ketmasligi uchun
                if slot_local.date() != target_date:
                    break
                # O'tib ketgan slotlarni qayta yaratmaymiz (faqat kelajakdagilarni)
                if slot_local <= local_now - timedelta(minutes=1):
                    continue

                slot_utc = slot_local.astimezone(now_utc().tzinfo)
                idem_key = f"auto_test:{target_date.isoformat()}:slot_{slot_idx}:{hour:02d}{minute:02d}:{interval_min}"
                _, created = await repo.enqueue(
                    job_type=JobType.AUTO_TEST,
                    run_at=slot_utc,
                    idempotency_key=idem_key,
                    payload_json={
                        "date": target_date.isoformat(),
                        "slot": slot_idx,
                    },
                    max_attempts=3,
                )
                if created:
                    created_count += 1

        return created_count

    async def run_once(self) -> int:
        """Bitta tekshiruv siklini bajaradi: stale recovery, slot sync va due job ijrosi."""
        self._last_tick_at = now_utc()
        processed = 0

        async with self.session_factory() as session:
            repo = ScheduleRepository(session)
            await repo.recover_stale_locks(lock_timeout_seconds=300)
            await self.sync_auto_test_schedule(session, days_ahead=2)
            claimed_jobs = await repo.claim_due_jobs(worker_id=self.worker_id, limit=10)
            await session.commit()

        for job in claimed_jobs:
            async with self.session_factory() as job_session:
                repo = ScheduleRepository(job_session)
                try:
                    ok, msg = await execute_scheduled_job(
                        job=job,
                        session=job_session,
                        bot=self.bot,
                        settings=self.settings,
                    )
                    if ok:
                        await repo.mark_completed(job.id)
                        logger.info("Vazifa #%s (%s) bajarildi: %s", job.id, job.job_type, msg)
                    else:
                        await repo.mark_failed_or_retry(job, msg)
                        logger.warning("Vazifa #%s (%s) muvaffaqiyatsiz: %s", job.id, job.job_type, msg)
                    await job_session.commit()
                    processed += 1
                except Exception as exc:
                    await job_session.rollback()
                    async with self.session_factory() as err_session:
                        err_repo = ScheduleRepository(err_session)
                        await err_repo.mark_failed_or_retry(job, str(exc))
                        await err_session.commit()
                    logger.exception("Vazifa #%s bajarishda kutilmagan xato: %s", job.id, exc)

        return processed

    async def _loop(self) -> None:
        poll_interval = max(5, int(self.settings.SCHEDULER_POLL_SECONDS))
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception as exc:
                logger.exception("Scheduler siklida xatolik: %s", exc)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=poll_interval)
            except asyncio.TimeoutError:
                continue
