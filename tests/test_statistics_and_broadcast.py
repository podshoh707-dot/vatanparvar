"""Statistika, grafik yaratish, ommaviy xabar yuborish (broadcast) va ZIP zaxira testlari."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from app.models.enums import BroadcastStatus, ContentType
from app.repositories.user_repo import UserRepository
from app.services.backup_service import BackupService
from app.services.broadcast_service import BroadcastService
from app.services.statistics_service import StatisticsService


@pytest.mark.asyncio
async def test_statistics_collection_and_chart_generation(session, mock_bot, test_settings):
    user_repo = UserRepository(session)
    await user_repo.upsert_user(telegram_id=800001, first_name="Jasur")
    await user_repo.upsert_user(telegram_id=800002, first_name="Dilnoza")
    await session.commit()

    svc = StatisticsService(session, mock_bot, test_settings)
    stats = await svc.collect()
    assert stats["total_users"] == 2
    assert stats["channel_subscribers"] == 1450

    report = svc.format_report(stats)
    assert "AVTOVATANPARVAR TESTLARI" in report
    assert "1450" in report

    png = svc.build_chart_png(stats)
    # PNG sarlavha baytlari tekshiruvi
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 5000


@pytest.mark.asyncio
async def test_broadcast_handles_blocked_users_and_counts(session, mock_bot, test_settings):
    user_repo = UserRepository(session)
    await user_repo.upsert_user(telegram_id=900001, first_name="ActiveUser")
    await user_repo.upsert_user(telegram_id=900002, first_name="BlockedUser")
    await session.commit()

    async def fake_send_message(chat_id, **kwargs):
        if chat_id == 900002:
            raise TelegramForbiddenError(
                method=SendMessage(chat_id=chat_id, text="hi"),
                message="Forbidden: bot was blocked by the user",
            )
        return AsyncMock(message_id=501)

    mock_bot.send_message = AsyncMock(side_effect=fake_send_message)

    svc = BroadcastService(session, mock_bot)
    bc = await svc.execute_broadcast(
        created_by=test_settings.SUPERADMIN_ID,
        content_type=ContentType.TEXT,
        text="Muhim e'lon!",
        rate_delay_seconds=0.0,
    )
    assert bc.status == BroadcastStatus.COMPLETED.value
    assert bc.total_targets == 2
    assert bc.sent_count == 1
    assert bc.blocked_count == 1
    assert bc.failed_count == 0

    blocked_user = await user_repo.get_by_telegram_id(900002)
    assert blocked_user is not None
    assert blocked_user.is_blocked is True
    assert blocked_user.is_active is False


@pytest.mark.asyncio
async def test_backup_creates_valid_zip_with_all_tables(session, test_settings):
    svc = BackupService(session)
    filename, zip_bytes, record = await svc.create_zip_backup(created_by=test_settings.SUPERADMIN_ID)
    assert filename.endswith(".zip")
    assert record.tables_included == 12
    assert len(zip_bytes) > 200

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "admins.json" in names
        assert "test_questions.json" in names
        assert "scheduled_jobs.json" in names
