"""Kanaldagi inline test javoblari va Telegram Quiz Poll yangilanishlarini qayta ishlash."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Poll
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.test_repo import TestRepository
from app.services.test_service import TestService

router = Router(name="channel_test_interaction")


@router.callback_query(F.data.startswith("chtest:"))
async def handle_channel_inline_test_vote(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Kanaldagi inline test tugmasi bosilganda:
    - Bir foydalanuvchining qayta-qayta ovoz berishini bloklaydi.
    - Javobni bazaga saqlaydi va statistikani yangilaydi.
    - Foydalanuvchiga darhol qisqa natija (toast/alert) ko'rsatadi.
    """
    if not callback.from_user or not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Noto'g'ri tugma ma'lumoti.", show_alert=True)
        return

    published_test_id = int(parts[1])
    selected_option = parts[2].upper()

    repo = TestRepository(session)
    pub = await repo.get_published_by_id(published_test_id)
    if not pub:
        await callback.answer("Bu test bazada topilmadi.", show_alert=True)
        return

    accepted, is_correct = await repo.record_channel_inline_answer(
        published_test=pub,
        user_telegram_id=callback.from_user.id,
        selected_option=selected_option,
    )
    if not accepted:
        await callback.answer(
            "⚠️ Siz bu testga allaqachon javob bergansiz! Qayta ovoz berish mumkin emas.",
            show_alert=True,
        )
        return

    if is_correct:
        await callback.answer(
            f"✅ Barakalla! {selected_option} — to'g'ri javob!",
            show_alert=True,
        )
    else:
        await callback.answer(
            f"❌ Siz {selected_option} variantini tanladingiz. To'g'ri javob belgilangan vaqtda e'lon qilinadi!",
            show_alert=True,
        )


@router.poll()
async def handle_telegram_quiz_poll_update(
    poll: Poll,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Telegram Quiz Poll ovozlari o'zgarganda real natijalarni bazaga sinxronlaydi."""
    svc = TestService(session, bot)
    await svc.sync_quiz_poll_update(poll)
