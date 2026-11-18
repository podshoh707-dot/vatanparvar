"""Barcha bot foydalanuvchilariga ommaviy xabar yuborish (broadcast) handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.common import require_permission
from app.keyboards.admin import admin_main_menu_kb
from app.keyboards.common import BTN_ADMIN_BROADCAST, BTN_SKIP, cancel_only_kb
from app.models.admin import Admin
from app.models.enums import ContentType, Permission
from app.repositories.user_repo import UserRepository
from app.services.broadcast_service import BroadcastService
from app.services.channel_service import ChannelService, explain_telegram_error
from app.utils.fsm import BroadcastState
from app.utils.security import escape_html, parse_inline_buttons_text

router = Router(name="admin_broadcast")


@router.message(F.text == BTN_ADMIN_BROADCAST)
async def start_broadcast(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.BROADCAST):
        return
    await state.clear()
    active_count = await UserRepository(session).count_active()
    await state.set_state(BroadcastState.waiting_content)
    await message.answer(
        "📨 <b>OMMAVIY XABAR YUBORISH</b>\n\n"
        f"👥 Faol auditoriya: <b>{active_count}</b> nafar foydalanuvchi.\n\n"
        "Yubormoqchi bo'lgan xabaringizni (matn, rasm, video yoki hujjat) yuboring:",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(),
    )


@router.message(BroadcastState.waiting_content)
async def receive_broadcast_content(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.BROADCAST):
        return

    if message.photo:
        ctype = ContentType.PHOTO
        media_id = message.photo[-1].file_id
        text = message.html_text if message.caption else ""
    elif message.video:
        ctype = ContentType.VIDEO
        media_id = message.video.file_id
        text = message.html_text if message.caption else ""
    elif message.document:
        ctype = ContentType.DOCUMENT
        media_id = message.document.file_id
        text = message.html_text if message.caption else ""
    elif message.text:
        ctype = ContentType.TEXT
        media_id = None
        text = message.html_text or message.text
    else:
        await message.answer("⚠️ Matn, rasm, video yoki hujjat yuboring.")
        return

    await state.update_data(content_type=ctype.value, text=text, media_file_id=media_id)
    await state.set_state(BroadcastState.waiting_buttons)
    await message.answer(
        "🔗 Inline tugmalar qo'shmoqchimisiz?\n"
        "Format: <code>Tugma matni | https://havola</code>\n"
        "Yoki <b>⏭ O'tkazib yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(allow_skip=True),
    )


@router.message(BroadcastState.waiting_buttons)
async def receive_broadcast_buttons(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.BROADCAST):
        return

    buttons_json: list[dict[str, str]] = []
    if message.text and message.text.strip() != BTN_SKIP:
        buttons_json, errors = parse_inline_buttons_text(message.text)
        if errors:
            await message.answer("⚠️ Xatolar:\n" + "\n".join(f"• {e}" for e in errors))
            return

    await state.update_data(buttons_json=buttons_json)
    d = await state.get_data()

    await message.answer("👁 <b>Xabar ko'rinishi:</b>", parse_mode="HTML")
    try:
        await ChannelService(bot).send_content(
            chat_id=message.chat.id,
            content_type=d["content_type"],
            text=d.get("text"),
            media_file_id=d.get("media_file_id"),
            buttons_json=buttons_json,
        )
    except Exception as exc:
        await message.answer(f"⚠️ Xatolik: {escape_html(explain_telegram_error(exc))}", parse_mode="HTML")
        await state.set_state(BroadcastState.waiting_content)
        return

    active_count = await UserRepository(session).count_active()
    await state.set_state(BroadcastState.confirm)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🚀 Ha, {active_count} kishiga yuborish", callback_data="broadcast:start")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")],
        ]
    )
    await message.answer(
        f"📨 Xabarni <b>{active_count}</b> nafar faol foydalanuvchiga yuborishni tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(BroadcastState.confirm, F.data == "broadcast:start")
async def execute_broadcast_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.BROADCAST):
        return
    assert admin is not None
    d = await state.get_data()
    await state.clear()
    await callback.answer("Yuborish boshlandi...")

    progress_msg = None
    if callback.message:
        progress_msg = await callback.message.answer("⏳ <b>Ommaviy xabar yuborish boshlandi...</b>", parse_mode="HTML")

    async def on_progress(done: int, total: int, sent: int, failed: int) -> None:
        if progress_msg:
            pct = round((done / total) * 100) if total else 100
            try:
                await progress_msg.edit_text(
                    f"📨 <b>Yuborish jarayoni: {pct}%</b>\n"
                    f"• Ko'rib chiqildi: {done}/{total}\n"
                    f"• ✅ Yuborildi: {sent}\n"
                    f"• ❌ Xato/Bloklangan: {failed}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    svc = BroadcastService(session, bot)
    result = await svc.execute_broadcast(
        created_by=admin.telegram_id,
        content_type=ContentType(d["content_type"]),
        text=d.get("text"),
        media_file_id=d.get("media_file_id"),
        buttons_json=d.get("buttons_json") or None,
        on_progress=on_progress,
    )

    summary = (
        "✅ <b>OMMAVIY XABAR YUBORISH YAKUNLANDI!</b>\n\n"
        f"👥 Jami maqsad: <b>{result.total_targets}</b>\n"
        f"✅ Muvaffaqiyatli yuborildi: <b>{result.sent_count}</b>\n"
        f"🚫 Botni bloklaganlar (chiqarildi): <b>{result.blocked_count}</b>\n"
        f"⚠️ Boshqa xatolar: <b>{result.failed_count}</b>"
    )
    if callback.message:
        await callback.message.answer(summary, parse_mode="HTML", reply_markup=admin_main_menu_kb())
