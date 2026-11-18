"""Ko'p adminli tizim va rollarni boshqarish handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.admin import admin_main_menu_kb
from app.keyboards.admins_mgmt import (
    admin_delete_confirm_kb,
    admin_detail_kb,
    admin_role_picker_kb,
    admins_list_kb,
)
from app.keyboards.common import BTN_ADMIN_ADMINS, cancel_only_kb
from app.models.admin import Admin
from app.models.enums import AdminRole, Permission
from app.repositories.admin_repo import AdminRepository
from app.services.admin_service import AdminService
from app.utils.formatting import ROLE_LABELS
from app.utils.fsm import AdminManageState
from app.utils.security import escape_html

router = Router(name="admin_admins_mgmt")


async def _show_admins_list(
    target: Message | CallbackQuery,
    session: AsyncSession,
    admin: Admin,
) -> None:
    admins = await AdminService(session).list_active_admins()
    text = (
        "👥 <b>ADMINLAR RO'YXATI</b>\n\n"
        f"Faol adminlar soni: <b>{len(admins)}</b>\n"
        "<i>Admin qo'shish, rolini o'zgartirish va o'chirish faqat SUPER ADMIN tomonidan bajariladi.</i>"
    )
    kb = admins_list_kb(admins, is_super_admin=admin.is_super_admin)
    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_ADMIN_ADMINS)
async def open_admins_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADMINS):
        return
    assert admin is not None
    await state.clear()
    await _show_admins_list(message, session, admin)


@router.callback_query(F.data == "admins:list")
async def cb_admins_list(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    assert admin is not None
    await _show_admins_list(callback, session, admin)


@router.callback_query(F.data == "admins:add")
async def cb_start_add_admin(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    await state.set_state(AdminManageState.waiting_telegram_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "➕ <b>Yangi admin qo'shish</b>\n\n"
            "Yangi adminning <b>Telegram ID</b> raqamini yuboring (masalan: <code>554433221</code>).\n"
            "<i>ID ni bilish uchun @userinfobot dan foydalanish mumkin.</i>",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )


@router.message(AdminManageState.waiting_telegram_id)
async def receive_new_admin_id(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADMINS):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("⚠️ Telegram ID faqat musbat raqamlardan iborat bo'lishi kerak.")
        return
    await state.update_data(new_admin_tg_id=int(raw))
    await state.set_state(AdminManageState.waiting_role)
    await message.answer(
        f"🆔 Admin ID: <code>{raw}</code>\nEndi uning rolini tanlang:",
        parse_mode="HTML",
        reply_markup=admin_role_picker_kb("admins:pick_role"),
    )


@router.callback_query(AdminManageState.waiting_role, F.data.startswith("admins:pick_role:"))
async def receive_new_admin_role(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    assert admin is not None
    role_str = callback.data.split(":")[2]
    data = await state.get_data()
    target_id = int(data["new_admin_tg_id"])

    created, msg = await AdminService(session).add_admin(
        actor=admin,
        target_telegram_id=target_id,
        role=AdminRole(role_str),
    )
    await state.clear()
    await callback.answer()
    icon = "✅" if created else "⚠️"
    if callback.message:
        await callback.message.answer(
            f"{icon} {escape_html(msg)}\n🆔 ID: <code>{target_id}</code> | Rol: <b>{ROLE_LABELS.get(role_str, role_str)}</b>",
            parse_mode="HTML",
            reply_markup=admin_main_menu_kb(),
        )


@router.callback_query(F.data.startswith("admins:view:"))
async def cb_view_admin(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    assert admin is not None
    target_id = int(callback.data.split(":")[2])
    target = await AdminRepository(session).get_by_telegram_id(target_id)
    if not target:
        await callback.answer("Admin topilmadi.", show_alert=True)
        return

    cfg = get_settings()
    can_modify = admin.is_super_admin and target.telegram_id != cfg.SUPERADMIN_ID
    text = (
        f"👤 <b>Admin ma'lumotlari</b>\n\n"
        f"• Telegram ID: <code>{target.telegram_id}</code>\n"
        f"• Ism: <b>{escape_html(target.full_name or '—')}</b>\n"
        f"• Username: @{escape_html(target.username) if target.username else '—'}\n"
        f"• Rol: <b>{ROLE_LABELS.get(target.role, target.role)}</b>\n"
        f"• Holat: {'✅ Faol' if target.is_active else '❌ Nofaol'}"
    )
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_detail_kb(target.telegram_id, can_modify=can_modify),
        )


@router.callback_query(F.data.startswith("admins:chrole:"))
async def cb_start_change_role(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    target_id = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"🔄 Admin <code>{target_id}</code> uchun yangi rolni tanlang:",
            parse_mode="HTML",
            reply_markup=admin_role_picker_kb(f"admins:setrole:{target_id}"),
        )


@router.callback_query(F.data.startswith("admins:setrole:"))
async def cb_apply_role_change(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    assert admin is not None
    parts = callback.data.split(":")
    target_id = int(parts[2])
    new_role = AdminRole(parts[3])
    ok, msg = await AdminService(session).change_role(
        actor=admin,
        target_telegram_id=target_id,
        new_role=new_role,
    )
    await callback.answer(msg[:180], show_alert=not ok)
    await _show_admins_list(callback, session, admin)


@router.callback_query(F.data.startswith("admins:del_ask:"))
async def cb_ask_delete_admin(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    target_id = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"⚠️ Admin <code>{target_id}</code> ni o'chirishni tasdiqlaysizmi?\n"
            "Uning barcha admin huquqlari darhol bekor qilinadi.",
            parse_mode="HTML",
            reply_markup=admin_delete_confirm_kb(target_id),
        )


@router.callback_query(F.data.startswith("admins:del_yes:"))
async def cb_confirm_delete_admin(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADMINS):
        return
    assert admin is not None
    target_id = int(callback.data.split(":")[2])
    ok, msg = await AdminService(session).remove_admin(actor=admin, target_telegram_id=target_id)
    await callback.answer(msg[:180], show_alert=not ok)
    await _show_admins_list(callback, session, admin)
