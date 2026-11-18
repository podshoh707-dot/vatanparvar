"""Aiogram Dispatcher integratsiya testlari: admin vs user /start, ruxsat himoyasi va FSM izolyatsiyasi."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from aiogram.types import Chat, Message, Update, User as TgUser

from app.keyboards.common import BTN_ADMIN_ADMINS
from app.keyboards.posts import BTN_POST_NEW
from app.main import build_dispatcher
from app.models.enums import AdminRole
from app.services.admin_service import AdminService


def _make_text_update(update_id: int, user_id: int, first_name: str, text: str) -> Update:
    msg = Message(
        message_id=update_id,
        date=datetime.now(timezone.utc),
        chat=Chat(id=user_id, type="private"),
        from_user=TgUser(id=user_id, is_bot=False, first_name=first_name),
        text=text,
    )
    return Update(update_id=update_id, message=msg)


@pytest.mark.asyncio
async def test_dispatcher_admin_vs_regular_user_routing_and_fsm_isolation(db, test_settings, mock_bot):
    # Ikkinchi admin qo'shamiz (FSM izolyatsiyasini tekshirish uchun)
    async with db.session_factory() as sess:
        svc = AdminService(sess, test_settings)
        superadmin = await svc.get_active_admin(test_settings.SUPERADMIN_ID)
        assert superadmin is not None
        await svc.add_admin(actor=superadmin, target_telegram_id=100002, role=AdminRole.ADMIN)
        await sess.commit()

    dp = build_dispatcher(db=db, settings=test_settings)
    sent_texts: list[tuple[int, str]] = []

    async def capture_call(method, request_timeout=None):
        text = getattr(method, "text", None)
        chat_id = getattr(method, "chat_id", 0)
        if text:
            sent_texts.append((int(chat_id), text))
        return True

    mock_bot.side_effect = capture_call

    # 1. SUPER_ADMIN /start -> Admin panel ochilishi kerak
    await dp.feed_update(mock_bot, _make_text_update(1, test_settings.SUPERADMIN_ID, "Super", "/start"))
    assert any(cid == test_settings.SUPERADMIN_ID and "ADMIN PANEL" in t for cid, t in sent_texts)

    # 2. Oddiy foydalanuvchi /start -> Foydalanuvchi menyusi
    sent_texts.clear()
    await dp.feed_update(mock_bot, _make_text_update(2, 555111, "Odil", "/start"))
    assert any(cid == 555111 and "xush kelibsiz" in t.lower() for cid, t in sent_texts)
    assert not any("ADMIN PANEL" in t for _, t in sent_texts)

    # 3. Oddiy foydalanuvchi admin tugmasini bosishga urinsa -> rad etiladi!
    sent_texts.clear()
    await dp.feed_update(mock_bot, _make_text_update(3, 555111, "Odil", BTN_ADMIN_ADMINS))
    assert any(cid == 555111 and "huquqlari mavjud emas" in t.lower() for cid, t in sent_texts)

    # 4. FSM izolyatsiyasi: Admin-1 post yaratishni boshlaydi, Admin-2 /start qiladi -> Admin-1 holati buzilmaydi!
    sent_texts.clear()
    await dp.feed_update(mock_bot, _make_text_update(4, test_settings.SUPERADMIN_ID, "Super", BTN_POST_NEW))
    await dp.feed_update(mock_bot, _make_text_update(5, 100002, "SecondAdmin", "/start"))

    state_admin1 = await dp.fsm.get_context(
        bot=mock_bot,
        chat_id=test_settings.SUPERADMIN_ID,
        user_id=test_settings.SUPERADMIN_ID,
    ).get_state()
    state_admin2 = await dp.fsm.get_context(
        bot=mock_bot,
        chat_id=100002,
        user_id=100002,
    ).get_state()
    assert state_admin1 == "PostCreateState:waiting_content"
    assert state_admin2 is None
