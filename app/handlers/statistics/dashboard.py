"""Statistika hisobotlari va grafiklarini ko'rsatish handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.common import require_permission
from app.keyboards.common import BTN_ADMIN_STATS, inline_nav_row
from app.models.admin import Admin
from app.models.enums import Permission
from app.services.statistics_service import StatisticsService

router = Router(name="statistics_dashboard")


def _stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📈 Grafikni yuklash (PNG)", callback_data="stats:chart")],
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="stats:refresh")],
            inline_nav_row("nav:admin_home"),
        ]
    )


@router.message(F.text == BTN_ADMIN_STATS)
async def open_statistics(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.VIEW_STATS):
        return
    await state.clear()
    svc = StatisticsService(session, bot)
    stats = await svc.collect()
    await message.answer(
        svc.format_report(stats),
        parse_mode="HTML",
        reply_markup=_stats_kb(),
    )


@router.callback_query(F.data == "stats:refresh")
async def cb_refresh_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.VIEW_STATS):
        return
    svc = StatisticsService(session, bot)
    stats = await svc.collect()
    await callback.answer("Yangilandi")
    if callback.message:
        try:
            await callback.message.edit_text(
                svc.format_report(stats),
                parse_mode="HTML",
                reply_markup=_stats_kb(),
            )
        except Exception:
            pass


@router.callback_query(F.data == "stats:chart")
async def cb_send_stats_chart(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.VIEW_STATS):
        return
    await callback.answer("Grafik tayyorlanmoqda...")
    svc = StatisticsService(session, bot)
    stats = await svc.collect()
    png_bytes = svc.build_chart_png(stats)
    if callback.message:
        await callback.message.answer_photo(
            photo=BufferedInputFile(png_bytes, filename="avtovatanparvar_statistika.png"),
            caption="📈 <b>AVTOVATANPARVAR TESTLARI — Oxirgi 7 kunlik o'sish va test aniqligi grafigi</b>",
            parse_mode="HTML",
        )
