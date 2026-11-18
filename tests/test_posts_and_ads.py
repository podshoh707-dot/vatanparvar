"""Postlar va reklamalar tizimi: yaratish, tahrirlash, o'chirish, qayta joylash, to'xtatish."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.enums import ContentType, PostStatus, PostType
from app.services.post_service import PostService
from app.utils.timezone import now_utc


@pytest.mark.asyncio
async def test_post_create_edit_repost_and_delete(session, mock_bot, test_settings):
    svc = PostService(session, mock_bot, test_settings)

    # 1. Darhol post joylash
    post, msg = await svc.publish_now(
        created_by=test_settings.SUPERADMIN_ID,
        post_type=PostType.POST,
        content_type=ContentType.TEXT,
        text="<b>Assalomu alaykum!</b> Yangi YHQ darsi.",
        buttons_json=[{"text": "Kanal", "url": "https://t.me/AvtoVatanparvar_testlari"}],
    )
    assert post is not None
    assert post.status == PostStatus.PUBLISHED.value
    assert post.channel_message_id is not None

    # 2. Tahrirlash
    ok, _ = await svc.edit_post(
        post_id=post.id,
        editor_id=test_settings.SUPERADMIN_ID,
        new_text="<b>Yangilangan matn!</b>",
    )
    assert ok is True
    mock_bot.edit_message_text.assert_awaited_once()

    # 3. Qayta joylash
    reposted, _ = await svc.repost(post_id=post.id, actor_id=test_settings.SUPERADMIN_ID)
    assert reposted is not None
    assert reposted.id != post.id
    assert reposted.status == PostStatus.PUBLISHED.value

    # 4. O'chirish
    del_ok, _ = await svc.delete_post(post_id=post.id, actor_id=test_settings.SUPERADMIN_ID)
    assert del_ok is True
    assert post.status == PostStatus.DELETED.value
    mock_bot.delete_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_ad_schedule_pause_resume_and_delete(session, mock_bot, test_settings):
    svc = PostService(session, mock_bot, test_settings)
    future = now_utc() + timedelta(hours=2)

    ad, _ = await svc.schedule_post(
        created_by=test_settings.SUPERADMIN_ID,
        post_type=PostType.AD,
        content_type=ContentType.PHOTO,
        run_at=future,
        text="Avtomaktab chegirmasi!",
        media_file_id="AgACAgIAAxkBAAIB_fake_photo_id",
        buttons_json=[{"text": "Ro'yxatdan o'tish", "url": "https://t.me/AvtoVatanparvar_testlari"}],
    )
    assert ad.post_type == PostType.AD.value
    assert ad.status == PostStatus.SCHEDULED.value

    # To'xtatish (pause)
    ok_pause, _ = await svc.pause_or_resume_ad(post_id=ad.id, actor_id=test_settings.SUPERADMIN_ID)
    assert ok_pause is True
    assert ad.status == PostStatus.PAUSED.value

    # Qayta yoqish (resume)
    ok_resume, _ = await svc.pause_or_resume_ad(post_id=ad.id, actor_id=test_settings.SUPERADMIN_ID)
    assert ok_resume is True
    assert ad.status == PostStatus.SCHEDULED.value

    # O'chirish
    ok_del, _ = await svc.delete_post(post_id=ad.id, actor_id=test_settings.SUPERADMIN_ID)
    assert ok_del is True
    assert ad.status == PostStatus.DELETED.value
