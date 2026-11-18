"""Rejalashtiruvchi: takroriy vazifa himoyasi, 2 worker lock himoyasi, stale lock tiklash va o'tib ketgan vazifalar."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.enums import ContentType, JobStatus, JobType, PostStatus, PostType
from app.repositories.post_repo import PostRepository
from app.repositories.schedule_repo import ScheduleRepository
from app.scheduler.engine import PersistentScheduler
from app.services.post_service import PostService
from app.utils.timezone import now_utc


@pytest.mark.asyncio
async def test_idempotency_and_dual_worker_protection(db, mock_bot, test_settings):
    # 1. Bir xil idempotency_key bilan ikki marta vazifa qo'shilsa, dublikat yaratilmaydi
    async with db.session_factory() as sess:
        repo = ScheduleRepository(sess)
        run_at = now_utc() - timedelta(seconds=10)
        j1, created1 = await repo.enqueue(
            job_type=JobType.AUTO_TEST,
            run_at=run_at,
            idempotency_key="auto_test:2026-11-18:slot_1",
        )
        j2, created2 = await repo.enqueue(
            job_type=JobType.AUTO_TEST,
            run_at=run_at,
            idempotency_key="auto_test:2026-11-18:slot_1",
        )
        await sess.commit()
        assert created1 is True
        assert created2 is False
        assert j1.id == j2.id

    # 2. Ikki worker bir vaqtning o'zida band qilishga urinsa, faqat bittasi oladi
    async with db.session_factory() as s1:
        claimed1 = await ScheduleRepository(s1).claim_due_jobs(worker_id="worker-A", limit=5)
        await s1.commit()
    async with db.session_factory() as s2:
        claimed2 = await ScheduleRepository(s2).claim_due_jobs(worker_id="worker-B", limit=5)
        await s2.commit()

    assert len(claimed1) == 1
    assert len(claimed2) == 0


@pytest.mark.asyncio
async def test_scheduled_overdue_post_executes_and_recovers_stale_lock(db, mock_bot, test_settings):
    # 1. Server uxlab qolgandek o'tib ketgan vaqtga rejalashtirilgan post yaratamiz
    past_time = now_utc() - timedelta(minutes=5)
    async with db.session_factory() as sess:
        post_svc = PostService(sess, mock_bot, test_settings)
        post, _ = await post_svc.schedule_post(
            created_by=test_settings.SUPERADMIN_ID,
            post_type=PostType.POST,
            content_type=ContentType.TEXT,
            run_at=past_time,
            text="Rejalashtirilgan muhim post!",
        )
        post_id = post.id
        await sess.commit()

    # 2. Scheduler run_once() o'tib ketgan postni darhol kanalga chiqaradi
    scheduler = PersistentScheduler(
        session_factory=db.session_factory,
        bot=mock_bot,
        settings=test_settings,
        worker_id="test-worker-1",
    )
    processed = await scheduler.run_once()
    assert processed == 1

    async with db.session_factory() as sess:
        refreshed = await PostRepository(sess).get_by_id(post_id)
        assert refreshed is not None
        assert refreshed.status == PostStatus.PUBLISHED.value
        assert refreshed.channel_message_id is not None

    # 3. Stale lock recovery tekshiruvi (server o'rtada o'chib qolgan holat)
    async with db.session_factory() as sess:
        repo = ScheduleRepository(sess)
        job, _ = await repo.enqueue(
            job_type=JobType.AUTO_TEST,
            run_at=now_utc() - timedelta(minutes=20),
            idempotency_key="stale_lock_test_job",
        )
        job.status = JobStatus.RUNNING.value
        job.locked_at = now_utc() - timedelta(minutes=15)
        job.locked_by = "crashed-worker"
        job.attempts = 1
        await sess.commit()

    async with db.session_factory() as sess:
        recovered = await ScheduleRepository(sess).recover_stale_locks(lock_timeout_seconds=180)
        await sess.commit()
        assert recovered == 1
