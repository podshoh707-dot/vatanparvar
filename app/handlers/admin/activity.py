"""Admin faoliyat tarixi (audit log) va Yordam bo'limi handlerlari."""

from __future__ import annotations

import math
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.common import (
    BTN_ADMIN_HELP,
    BTN_ADMIN_LOGS,
    inline_nav_row,
    pagination_row,
)
from app.models.admin import Admin
from app.models.enums import Permission
from app.repositories.system_repo import SystemRepository
from app.utils.security import escape_html
from app.utils.timezone import format_local_dt

router = Router(name="admin_activity")
PAGE_SIZE = 10


async def _render_logs(
    target: Message | CallbackQuery,
    session: AsyncSession,
    page: int = 1,
) -> None:
    tz = get_settings().TIMEZONE
    offset = (page - 1) * PAGE_SIZE
    items, total = await SystemRepository(session).list_activity_logs(limit=PAGE_SIZE, offset=offset)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    lines = [f"📋 <b>FAOLIYAT TARIXI (AUDIT LOG)</b> — Jami: <b>{total}</b>", ""]
    if not items:
        lines.append("Hozircha faoliyat qayd etilmagan.")
    else:
        for item in items:
            t_str = format_local_dt(item.created_at, tz)
            tgt = f" [{item.target_type} #{item.target_id}]" if item.target_type else ""
            lines.append(
                f"• <code>{t_str}</code> | Admin <code>{item.admin_telegram_id}</code>: "
                f"<b>{escape_html(item.action)}</b>{escape_html(tgt)}"
            )

    rows = []
    if total_pages > 1:
        rows.append(pagination_row("logs:page", page, total_pages))
    rows.append(inline_nav_row("nav:admin_home"))
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    text = "\n".join(lines)

    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_ADMIN_LOGS)
async def open_activity_logs(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.VIEW_LOGS):
        return
    await state.clear()
    await _render_logs(message, session, page=1)


@router.callback_query(F.data.startswith("logs:page:"))
async def cb_logs_pagination(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.VIEW_LOGS):
        return
    page = max(1, int(callback.data.split(":")[2]))
    await _render_logs(callback, session, page=page)


@router.message(F.text == BTN_ADMIN_HELP)
async def open_admin_help(message: Message, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin):
        return
    cfg = get_settings()
    help_text = (
        "❓ <b>AVTOVATANPARVAR TESTLARI — ADMIN QO'LLANMASI</b>\n\n"
        "📝 <b>Postlarni boshqarish:</b> Matn, rasm, video va hujjatli postlar yaratish, "
        "inline tugma qo'shish, vaqtga rejalashtirish, tahrirlash, o'chirish va qayta joylash.\n\n"
        "🚦 <b>Testlarni boshqarish:</b> Savol qo'shish, Excel (.xlsx) import/eksport, "
        "mavzular bo'yicha saralash, qidirish va tasdiqlash. Faqat tasdiqlangan testlar avtomatik chiqariladi.\n\n"
        "📅 <b>Avtomatik joylashtirish:</b> Kunlik soni, boshlash vaqti, oraliq, hafta kunlari, "
        "Quiz Poll yoki Inline rejim hamda to'g'ri javob e'lon qilish kechikishini sozlash.\n\n"
        "👥 <b>Admin rollari:</b>\n"
        "• 👑 <b>SUPER ADMIN:</b> Barcha huquqlar + admin qo'shish/o'chirish.\n"
        "• 🛡 <b>ADMIN:</b> Post, test, reklama, broadcast, sozlamalar, zaxira.\n"
        "• 🚦 <b>TEST MANAGER:</b> Testlar va avtomatik joylashtirish.\n"
        "• ✏️ <b>EDITOR:</b> Postlar va reklamalar.\n"
        "• 📊 <b>STATISTIC VIEWER:</b> Faqat statistikani ko'rish.\n\n"
        f"📢 Kanal: <b>{cfg.CHANNEL_USERNAME}</b> | Vaqt: <b>{cfg.TIMEZONE}</b>\n"
        "💡 Istalgan jarayonni to'xtatish uchun <b>❌ Bekor qilish</b> tugmasini yoki /cancel buyrug'ini yuboring."
    )
    await message.answer(help_text, parse_mode="HTML")
