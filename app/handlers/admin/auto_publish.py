"""Avtomatik test joylashtirish tizimi sozlamalari handlerlari."""

from __future__ import annotations

import re
from typing import Any, Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.admin import admin_main_menu_kb
from app.keyboards.auto_publish import auto_publish_menu_kb, weekdays_picker_kb
from app.keyboards.common import BTN_ADMIN_AUTO, cancel_only_kb
from app.models.admin import Admin
from app.models.enums import JobType, Permission, PublishMode
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.system_repo import SystemRepository
from app.scheduler.engine import PersistentScheduler
from app.services.settings_service import SettingsService
from app.services.test_service import TestService
from app.utils.fsm import AutoPublishConfigState
from app.utils.security import escape_html
from app.utils.timezone import WEEKDAY_UZ, format_local_dt

router = Router(name="admin_auto_publish")


def _format_auto_dashboard(cfg: dict[str, Any]) -> str:
    tz = get_settings().TIMEZONE
    status = "🟢 YOQILGAN" if cfg["enabled"] else "🔴 O'CHIRILGAN"
    days = ", ".join(WEEKDAY_UZ[d] for d in sorted(cfg["weekdays"]) if d in WEEKDAY_UZ) or "Tanlanmagan"
    mode = "🗳 Telegram Quiz Poll" if cfg["publish_mode"] == PublishMode.QUIZ_POLL.value else "🔘 Inline Tugmalar"
    sel = "🎲 Tasodifiy" if cfg["selection_mode"] == "random" else "🔢 Ketma-ket"
    dup = "✅ Himoyalangan" if cfg["prevent_duplicates"] else "⚠️ Ruxsat etilgan"

    return (
        "📅 <b>AVTOMATIK TEST JOYLASHTIRISH</b>\n\n"
        f"• Holat: <b>{status}</b>\n"
        f"• Vaqt mintaqasi: <b>{tz}</b>\n"
        f"• Kuniga testlar soni: <b>{cfg['per_day']} ta</b>\n"
        f"• Boshlash vaqti: <b>{cfg['start_time']}</b>\n"
        f"• Testlar oralig'i: <b>{cfg['interval_minutes']} daqiqa</b>\n"
        f"• Faol kunlar: <b>{days}</b>\n"
        f"• Tanlash tartibi: <b>{sel}</b>\n"
        f"• Takroriy test himoyasi: <b>{dup}</b>\n"
        f"• Joylashtirish rejimi: <b>{mode}</b>\n"
        f"• Inline javob e'loni kechikishi: <b>{cfg['reveal_delay_minutes']} daqiqa</b>\n\n"
        "<i>Faqat admin tasdiqlagan testlar avtomatik chiqariladi.</i>"
    )


async def _resync_schedule(
    session: AsyncSession,
    bot: Bot,
    scheduler: Optional[PersistentScheduler] = None,
) -> None:
    if scheduler is not None:
        await scheduler.sync_auto_test_schedule(session, days_ahead=2, recreate_pending=True)
    else:
        from app.database import db_manager

        temp = PersistentScheduler(session_factory=db_manager.session_factory, bot=bot)
        await temp.sync_auto_test_schedule(session, days_ahead=2, recreate_pending=True)


async def _render_dashboard(
    target: Message | CallbackQuery,
    session: AsyncSession,
) -> None:
    cfg = await SettingsService(session).get_auto_publish_config()
    text = _format_auto_dashboard(cfg)
    kb = auto_publish_menu_kb(cfg)
    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_ADMIN_AUTO)
async def open_auto_publish(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.AUTO_PUBLISH):
        return
    await state.clear()
    await _render_dashboard(message, session)


@router.callback_query(F.data == "auto:menu")
async def cb_auto_menu(callback: CallbackQuery, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    await _render_dashboard(callback, session)
    await callback.answer()


@router.callback_query(F.data == "auto:toggle_enabled")
async def cb_toggle_enabled(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
    scheduler: Optional[PersistentScheduler] = None,
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    svc = SettingsService(session)
    current = await svc.get_bool("auto_test_enabled", False)
    await svc.set_value("auto_test_enabled", not current, updated_by=admin.telegram_id)
    await _resync_schedule(session, bot, scheduler)
    await SystemRepository(session).log_activity(
        admin_telegram_id=admin.telegram_id,
        action="auto_test_toggled",
        details={"enabled": not current},
    )
    await _render_dashboard(callback, session)
    await callback.answer("Holat yangilandi")


@router.callback_query(F.data == "auto:toggle_publish_mode")
async def cb_toggle_publish_mode(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    svc = SettingsService(session)
    curr = await svc.get_raw("auto_test_publish_mode")
    new_mode = PublishMode.QUIZ_POLL.value if curr != PublishMode.QUIZ_POLL.value else PublishMode.INLINE.value
    await svc.set_value("auto_test_publish_mode", new_mode, updated_by=admin.telegram_id)
    await _render_dashboard(callback, session)
    await callback.answer("Joylashtirish rejimi o'zgartirildi")


@router.callback_query(F.data == "auto:toggle_selection")
async def cb_toggle_selection(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    svc = SettingsService(session)
    curr = await svc.get_raw("auto_test_selection_mode")
    new_val = "random" if curr != "random" else "sequential"
    await svc.set_value("auto_test_selection_mode", new_val, updated_by=admin.telegram_id)
    await _render_dashboard(callback, session)
    await callback.answer("Tanlash tartibi o'zgartirildi")


@router.callback_query(F.data == "auto:toggle_duplicates")
async def cb_toggle_duplicates(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    svc = SettingsService(session)
    curr = await svc.get_bool("auto_test_prevent_duplicates", True)
    await svc.set_value("auto_test_prevent_duplicates", not curr, updated_by=admin.telegram_id)
    await _render_dashboard(callback, session)
    await callback.answer("Takroriy test himoyasi yangilandi")


@router.callback_query(F.data == "auto:weekdays")
async def cb_open_weekdays(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    days = await SettingsService(session).get_json("auto_test_weekdays", [0, 1, 2, 3, 4, 5, 6])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "📆 <b>Avtomatik test chiqariladigan hafta kunlarini belgilang:</b>",
            parse_mode="HTML",
            reply_markup=weekdays_picker_kb(days),
        )


@router.callback_query(F.data.startswith("auto:wday:"))
async def cb_toggle_weekday(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
    scheduler: Optional[PersistentScheduler] = None,
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    day_idx = int(callback.data.split(":")[2])
    svc = SettingsService(session)
    days = set(int(d) for d in (await svc.get_json("auto_test_weekdays", [0, 1, 2, 3, 4, 5, 6])))
    if day_idx in days:
        days.remove(day_idx)
    else:
        days.add(day_idx)
    sorted_days = sorted(days)
    await svc.set_value("auto_test_weekdays", sorted_days, updated_by=admin.telegram_id)
    await _resync_schedule(session, bot, scheduler)
    await callback.answer("Saqlandi")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=weekdays_picker_kb(sorted_days))


@router.callback_query(F.data == "auto:set_per_day")
async def cb_ask_per_day(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    await state.set_state(AutoPublishConfigState.waiting_tests_per_day)
    await callback.answer()
    if callback.message:
        await callback.message.answer("🔢 Kuniga nechta test chiqarilsin? (1 dan 24 gacha son kiriting):", reply_markup=cancel_only_kb())


@router.message(AutoPublishConfigState.waiting_tests_per_day)
async def save_per_day(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
    scheduler: Optional[PersistentScheduler] = None,
) -> None:
    if not await require_permission(message, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 24):
        await message.answer("⚠️ Iltimos, 1 dan 24 gacha butun son kiriting.")
        return
    await SettingsService(session).set_value("auto_test_per_day", int(raw), updated_by=admin.telegram_id)
    await _resync_schedule(session, bot, scheduler)
    await state.clear()
    await message.answer("✅ Kunlik testlar soni yangilandi!", reply_markup=admin_main_menu_kb())
    await _render_dashboard(message, session)


@router.callback_query(F.data == "auto:set_start_time")
async def cb_ask_start_time(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    await state.set_state(AutoPublishConfigState.waiting_start_time)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "⏰ Birinchi test chiqarish vaqtini kiriting (Asia/Tashkent, <code>SS:DD</code> formatda, masalan <code>09:00</code>):",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )


@router.message(AutoPublishConfigState.waiting_start_time)
async def save_start_time(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
    scheduler: Optional[PersistentScheduler] = None,
) -> None:
    if not await require_permission(message, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    raw = (message.text or "").strip()
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", raw):
        await message.answer("⚠️ Noto'g'ri vaqt formati! Namuna: <code>09:00</code> yoki <code>14:30</code>", parse_mode="HTML")
        return
    await SettingsService(session).set_value("auto_test_start_time", raw, updated_by=admin.telegram_id)
    await _resync_schedule(session, bot, scheduler)
    await state.clear()
    await message.answer("✅ Boshlash vaqti saqlandi!", reply_markup=admin_main_menu_kb())
    await _render_dashboard(message, session)


@router.callback_query(F.data == "auto:set_interval")
async def cb_ask_interval(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    await state.set_state(AutoPublishConfigState.waiting_interval_minutes)
    await callback.answer()
    if callback.message:
        await callback.message.answer("⏱ Testlar orasidagi intervalni daqiqalarda kiriting (5 dan 720 gacha):", reply_markup=cancel_only_kb())


@router.message(AutoPublishConfigState.waiting_interval_minutes)
async def save_interval(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
    scheduler: Optional[PersistentScheduler] = None,
) -> None:
    if not await require_permission(message, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (5 <= int(raw) <= 720):
        await message.answer("⚠️ 5 dan 720 gacha daqiqa kiriting.")
        return
    await SettingsService(session).set_value("auto_test_interval_minutes", int(raw), updated_by=admin.telegram_id)
    await _resync_schedule(session, bot, scheduler)
    await state.clear()
    await message.answer("✅ Oraliq vaqt yangilandi!", reply_markup=admin_main_menu_kb())
    await _render_dashboard(message, session)


@router.callback_query(F.data == "auto:set_reveal_delay")
async def cb_ask_reveal_delay(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    await state.set_state(AutoPublishConfigState.waiting_reveal_delay)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "💡 Inline test chiqarilgandan necha daqiqa o'tgach to'g'ri javob va izoh e'lon qilinsin? (1 dan 1440 gacha):",
            reply_markup=cancel_only_kb(),
        )


@router.message(AutoPublishConfigState.waiting_reveal_delay)
async def save_reveal_delay(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 1440):
        await message.answer("⚠️ 1 dan 1440 gacha daqiqa kiriting.")
        return
    await SettingsService(session).set_value("auto_test_reveal_delay_minutes", int(raw), updated_by=admin.telegram_id)
    await state.clear()
    await message.answer("✅ Javob e'lon qilish vaqti yangilandi!", reply_markup=admin_main_menu_kb())
    await _render_dashboard(message, session)


@router.callback_query(F.data == "auto:publish_now")
async def cb_publish_one_now(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    assert admin is not None
    pub, msg = await TestService(session, bot).publish_next_auto_test(published_by=admin.telegram_id)
    await callback.answer()
    icon = "✅" if pub else "⚠️"
    if callback.message:
        await callback.message.answer(f"{icon} {escape_html(msg)}", parse_mode="HTML")


@router.callback_query(F.data == "auto:upcoming")
async def cb_show_upcoming_auto_jobs(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.AUTO_PUBLISH):
        return
    tz = get_settings().TIMEZONE
    jobs = await ScheduleRepository(session).list_upcoming(job_type=JobType.AUTO_TEST, limit=12)
    if not jobs:
        text = "📋 <b>Kelgusi avtomatik testlar navbati bo'sh.</b>\nAvto-tizimni yoqing."
    else:
        lines = [f"📋 <b>Kelgusi avtomatik testlar ({tz}):</b>", ""]
        for idx, job in enumerate(jobs, start=1):
            lines.append(f"{idx}. 🕒 <b>{format_local_dt(job.run_at, tz)}</b> (Job #{job.id})")
        text = "\n".join(lines)
    await callback.answer()
    if callback.message:
        await callback.message.answer(text, parse_mode="HTML")
