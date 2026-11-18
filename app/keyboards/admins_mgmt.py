"""Adminlarni boshqarish klaviaturalari."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.common import inline_nav_row
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.utils.formatting import ROLE_LABELS


def admins_list_kb(admins: list[Admin], *, is_super_admin: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if is_super_admin:
        rows.append([InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="admins:add")])
    for adm in admins:
        role_txt = ROLE_LABELS.get(adm.role, adm.role)
        label = adm.full_name or (f"@{adm.username}" if adm.username else str(adm.telegram_id))
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{label} — {role_txt}",
                    callback_data=f"admins:view:{adm.telegram_id}",
                )
            ]
        )
    rows.append(inline_nav_row("nav:admin_home"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_role_picker_kb(prefix: str = "admins:pick_role") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=ROLE_LABELS[r.value], callback_data=f"{prefix}:{r.value}")]
        for r in AdminRole
    ]
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_detail_kb(target_tg_id: int, *, can_modify: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_modify:
        rows.append(
            [
                InlineKeyboardButton(text="🔄 Rolni o'zgartirish", callback_data=f"admins:chrole:{target_tg_id}"),
                InlineKeyboardButton(text="🗑 Adminni o'chirish", callback_data=f"admins:del_ask:{target_tg_id}"),
            ]
        )
    rows.append(inline_nav_row("admins:list"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_delete_confirm_kb(target_tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"admins:del_yes:{target_tg_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admins:view:{target_tg_id}"),
            ]
        ]
    )
