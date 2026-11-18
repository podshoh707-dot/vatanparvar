"""Rejalashtirilgan vazifalarni bajaruvchi handlerlar."""

from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.enums import JobType, PostStatus
from app.models.schedule import ScheduledJob
from app.repositories.post_repo import PostRepository
from app.services.post_service import PostService
from app.services.settings_service import SettingsService
from app.services.test_service import TestService

logger = logging.getLogger(__name__)


async def execute_scheduled_job(
    *,
    job: ScheduledJob,
    session: AsyncSession,
    bot: Bot,
    settings: Optional[Settings] = None,
) -> tuple[bool, str]:
    """
    Band qilingan bitta vazifani bajaradi.
    Qaytaradi: (success_bool, message).
    """
    cfg = settings or get_settings()
    job_type = JobType(job.job_type)

    if job_type in {JobType.PUBLISH_POST, JobType.PUBLISH_AD}:
        post_id = job.reference_id or (job.payload_json or {}).get("post_id")
        if not post_id:
            return False, "Post ID topilmadi."

        post_repo = PostRepository(session)
        post = await post_repo.get_by_id(int(post_id))
        if not post:
            return True, "Post bazada topilmadi, vazifa yakunlandi."
        if post.status in {PostStatus.PUBLISHED.value, PostStatus.DELETED.value, PostStatus.PAUSED.value}:
            return True, f"Post holati '{post.status}', qayta yuborish talab etilmaydi."

        service = PostService(session, bot, cfg)
        ok, msg = await service.execute_publish_existing(post)
        return ok, msg

    if job_type == JobType.AUTO_TEST:
        settings_svc = SettingsService(session)
        auto_cfg = await settings_svc.get_auto_publish_config()
        if not auto_cfg["enabled"]:
            return True, "Avtomatik test joylashtirish o'chirilgan — vazifa o'tkazib yuborildi."

        test_svc = TestService(session, bot, cfg)
        pub, msg = await test_svc.publish_next_auto_test(published_by=None)
        if pub is None:
            # Agar mos tasdiqlangan test qolmagan bo'lsa, qayta-qayta xatoga tushmasdan yakunlaymiz
            if "topilmadi" in msg.lower():
                logger.info("Auto-test slot o'tkazildi: %s", msg)
                return True, msg
            return False, msg
        return True, msg

    if job_type == JobType.REVEAL_TEST_ANSWER:
        pub_id = job.reference_id or (job.payload_json or {}).get("published_test_id")
        if not pub_id:
            return False, "PublishedTest ID topilmadi."
        test_svc = TestService(session, bot, cfg)
        return await test_svc.reveal_published_test(int(pub_id))

    return False, f"Noma'lum vazifa turi: {job.job_type}"
