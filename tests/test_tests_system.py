"""Test tizimi: qo'shish, dublikat himoya, tasdiqlash, kanalga chiqarish, ovoz berish va Excel import/eksport."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from app.models.enums import Difficulty, PublishedTestStatus, PublishMode, TestStatus
from app.repositories.test_repo import TestRepository
from app.services.excel_service import ExcelService
from app.services.test_service import TestService


@pytest.mark.asyncio
async def test_test_creation_duplicate_prevention_approval_and_publish(session, mock_bot, test_settings):
    svc = TestService(session, mock_bot, test_settings)

    # 1. Test yaratish (pending holatda)
    q, msg = await svc.create_test(
        question_text="Aholi punktlarida maksimal tezlik qancha?",
        option_a="50 km/soat",
        option_b="60 km/soat",
        option_c="70 km/soat",
        option_d="80 km/soat",
        correct_option="B",
        explanation="YHQ bo'yicha 60 km/soat.",
        topic="Tezlik",
        difficulty=Difficulty.EASY,
        created_by=test_settings.SUPERADMIN_ID,
        auto_approve=False,
    )
    assert q is not None
    assert q.status == TestStatus.PENDING.value

    # 2. Dublikat test rad etilishi kerak
    dup, dup_msg = await svc.create_test(
        question_text="  aholi punktlarida maksimal tezlik qancha? ",
        option_a="50 km/soat",
        option_b="60 km/soat",
        option_c="70 km/soat",
        option_d="80 km/soat",
        correct_option="B",
        created_by=test_settings.SUPERADMIN_ID,
    )
    assert dup is None
    assert "takroriy" in dup_msg.lower() or "mavjud" in dup_msg.lower()

    # 3. Tasdiqlanmagan test kanalga chiqarilmasligi shart!
    pub_denied, deny_msg = await svc.publish_test_to_channel(question=q, mode=PublishMode.INLINE)
    assert pub_denied is None
    assert "tasdiqlangan" in deny_msg.lower()

    # 4. Tasdiqlash
    ok, _ = await svc.approve_test(q.id, actor_id=test_settings.SUPERADMIN_ID)
    assert ok is True

    # 5. Inline rejimda kanalga chiqarish
    pub, pub_msg = await svc.publish_test_to_channel(
        question=q,
        mode=PublishMode.INLINE,
        published_by=test_settings.SUPERADMIN_ID,
        reveal_delay_minutes=30,
    )
    assert pub is not None
    assert pub.mode == PublishMode.INLINE.value
    mock_bot.send_message.assert_awaited()
    mock_bot.edit_message_reply_markup.assert_awaited()

    # 6. Foydalanuvchi ovoz berishi va qayta ovoz berishga qarshi himoya
    repo = TestRepository(session)
    pub_loaded = await repo.get_published_by_id(pub.id)
    assert pub_loaded is not None

    accepted1, correct1 = await repo.record_channel_inline_answer(
        published_test=pub_loaded,
        user_telegram_id=777001,
        selected_option="B",
    )
    assert accepted1 is True
    assert correct1 is True

    # Xuddi shu foydalanuvchi qayta bosib statistikani buza olmaydi!
    accepted2, _ = await repo.record_channel_inline_answer(
        published_test=pub_loaded,
        user_telegram_id=777001,
        selected_option="A",
    )
    assert accepted2 is False

    # Boshqa foydalanuvchi noto'g'ri javob beradi
    accepted3, correct3 = await repo.record_channel_inline_answer(
        published_test=pub_loaded,
        user_telegram_id=777002,
        selected_option="C",
    )
    assert accepted3 is True
    assert correct3 is False
    assert pub_loaded.total_votes == 2
    assert pub_loaded.correct_votes == 1
    assert pub_loaded.wrong_votes == 1

    # 7. To'g'ri javob va izohni e'lon qilish
    rev_ok, _ = await svc.reveal_published_test(pub.id)
    assert rev_ok is True
    assert pub_loaded.status == PublishedTestStatus.REVEALED.value

    # 8. Quiz Poll rejimida chiqarish va Telegram Poll natijasini sinxronlash
    pub_poll, _ = await svc.publish_test_to_channel(
        question=q,
        mode=PublishMode.QUIZ_POLL,
        published_by=test_settings.SUPERADMIN_ID,
    )
    assert pub_poll is not None
    assert pub_poll.poll_id is not None

    fake_poll = SimpleNamespace(
        id=pub_poll.poll_id,
        total_voter_count=10,
        correct_option_id=1,
        options=[
            SimpleNamespace(voter_count=2),
            SimpleNamespace(voter_count=7),
            SimpleNamespace(voter_count=1),
            SimpleNamespace(voter_count=0),
        ],
    )
    synced = await svc.sync_quiz_poll_update(fake_poll)
    assert synced is True
    assert pub_poll.total_votes == 10
    assert pub_poll.correct_votes == 7
    assert pub_poll.wrong_votes == 3


@pytest.mark.asyncio
async def test_excel_import_validation_and_export(session, test_settings):
    excel = ExcelService(session)

    # 1. Yaroqsiz fayl rad etilishi kerak
    bad_report = await excel.import_tests_from_bytes(b"not an excel file", created_by=test_settings.SUPERADMIN_ID)
    assert bad_report.imported == 0
    assert len(bad_report.errors) == 1

    # 2. Yaxshi + xatoli + dublikat qatorli haqiqiy .xlsx
    wb = Workbook()
    ws = wb.active
    ws.append(["savol", "a", "b", "c", "d", "togri_javob", "izoh", "mavzu", "qiyinlik"])
    ws.append(["Svetofor qizil chirog'i nimani bildiradi?", "To'xtash", "Yurish", "Burilish", "Tezlashish", "A", "Qizil taqiqlaydi", "Svetofor", "easy"])
    ws.append(["Svetofor qizil chirog'i nimani bildiradi?", "To'xtash", "Yurish", "Burilish", "Tezlashish", "A", "Dublikat", "Svetofor", "easy"])
    ws.append(["Noto'g'ri javobli savol misoli", "1", "2", "3", "4", "Z", "", "Test", "medium"])
    buf = io.BytesIO()
    wb.save(buf)

    report = await excel.import_tests_from_bytes(buf.getvalue(), created_by=test_settings.SUPERADMIN_ID)
    assert report.total_rows == 3
    assert report.imported == 1
    assert report.duplicates == 1
    assert len(report.errors) == 1
    assert "4-qator" in report.errors[0]

    # 3. Eksport tekshiruvi
    export_bytes, count = await excel.export_tests_bytes()
    assert count >= 1
    assert len(export_bytes) > 500
