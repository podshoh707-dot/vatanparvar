"""Bot sozlamalari va kanal administratorlik huquqlarini tekshirish handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.admin import admin_main_menu_kb, settings_menu_kb
from app.keyboards.common import BTN_ADMIN_SETTINGS, cancel_only_kb
from app.models.admin import Admin
from app.models.enums import Permission
from app.repositories.system_repo import SystemRepository
from app.services.channel_service import ChannelService
from app.services.settings_service import SettingsService
from app.utils.fsm import SettingsEditState
from app.utils.security import escape_html

router = Router(name="admin_settings")


async def _render_settings(target: Message | CallbackQuery, session: AsyncSession) -> None:
    cfg = get_settings()
    svc = SettingsService(session)
    mandatory_sub = await svc.get_bool("mandatory_subscription", False)
    text = (
        "⚙️ <b>BOT SOZLAMALARI</b>\n\n"
        f"📢 Asosiy kanal: <b>{cfg.CHANNEL_USERNAME}</b> (ID: <code>{cfg.CHANNEL_ID}</code>)\n"
        f"🕒 Vaqt mintaqasi: <b>{cfg.TIMEZONE}</b>\n"
        f"🔒 Majburiy obuna: <b>{'Yoqilgan ✅' if mandatory_sub else 'Ochirgan ⭕'}</b>\n\n"
        "Kerakli sozlamani tanlang:"
    )
    kb = settings_menu_kb(mandatory_sub)
    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_ADMIN_SETTINGS)
async def open_settings(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_SETTINGS):
        return
    await state.clear()
    await _render_settings(message, session)


@router.callback_query(F.data == "settings:toggle_sub")
async def cb_toggle_mandatory_sub(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_SETTINGS):
        return
    assert admin is not None
    svc = SettingsService(session)
    curr = await svc.get_bool("mandatory_subscription", False)
    await svc.set_value("mandatory_subscription", not curr, updated_by=admin.telegram_id)
    await SystemRepository(session).log_activity(
        admin_telegram_id=admin.telegram_id,
        action="settings_mandatory_sub_toggled",
        details={"enabled": not curr},
    )
    await _render_settings(callback, session)
    await callback.answer("Majburiy obuna holati o'zgartirildi")


@router.callback_query(F.data == "settings:check_channel")
async def cb_check_channel_rights(
    callback: CallbackQuery,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_SETTINGS):
        return
    ok, msg, rights = await ChannelService(bot).check_bot_admin_rights()
    report = (
        "🛡 <b>KANAL ADMINISTRATORLIK HUQUQLARI TEKSHIRUVI</b>\n\n"
        f"• Holat: {'✅ Tayyor' if ok else '⚠️ Muammo aniqlandi'}\n"
        f"• Kanal admini: {'✅' if rights['is_admin'] else '❌'}\n"
        f"• Post joylash: {'✅' if rights['can_post_messages'] else '❌'}\n"
        f"• Xabar tahrirlash: {'✅' if rights['can_edit_messages'] else '❌'}\n"
        f"• Xabar o'chirish: {'✅' if rights['can_delete_messages'] else '❌'}\n\n"
        f"💬 Izoh: {escape_html(msg)}"
    )
    await callback.answer()
    if callback.message:
        await callback.message.answer(report, parse_mode="HTML")


@router.callback_query(F.data == "settings:edit_welcome")
async def cb_edit_welcome(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_SETTINGS):
        return
    await state.set_state(SettingsEditState.waiting_welcome_text)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "✏️ Oddiy foydalanuvchilar uchun yangi salomlashish (/start) matnini yuboring (HTML qo'llab-quvvatlanadi):",
            reply_markup=cancel_only_kb(),
        )


@router.message(SettingsEditState.waiting_welcome_text)
async def save_welcome_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_SETTINGS):
        return
    assert admin is not None
    val = (message.html_text or message.text or "").strip()
    if not val:
        await message.answer("⚠️ Matn bo'sh bo'lishi mumkin emas.")
        return
    await SettingsService(session).set_value("bot_welcome_text", val, updated_by=admin.telegram_id)
    await state.clear()
    await message.answer("✅ Salomlashish matni yangilandi!", reply_markup=admin_main_menu_kb())


@router.callback_query(F.data == "settings:edit_about")
async def cb_edit_about(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_SETTINGS):
        return
    await state.set_state(SettingsEditState.waiting_about_text)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "ℹ️ 'Bot haqida' bo'limi uchun yangi matnni yuboring (HTML qo'llab-quvvatlanadi):",
            reply_markup=cancel_only_kb(),
        )


@router.message(SettingsEditState.waiting_about_text)
async def save_about_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_SETTINGS):
        return
    assert admin is not None
    val = (message.html_text or message.text or "").strip()
    if not val:
        await message.answer("⚠️ Matn bo'sh bo'lishi mumkin emas.")
        return
    await SettingsService(session).set_value("bot_about_text", val, updated_by=admin.telegram_id)
    await state.clear()
    await message.answer("✅ 'Bot haqida' matni yangilandi!", reply_markup=admin_main_menu_kb())
