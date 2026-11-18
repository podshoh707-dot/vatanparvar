"""Asosiy admin menyusi, sozlamalar va zaxira klaviaturalari."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.keyboards.common import (
    BTN_ADMIN_ADMINS,
    BTN_ADMIN_ADS,
    BTN_ADMIN_AUTO,
    BTN_ADMIN_BACKUP,
    BTN_ADMIN_BROADCAST,
    BTN_ADMIN_HELP,
    BTN_ADMIN_LOGS,
    BTN_ADMIN_POSTS,
    BTN_ADMIN_SETTINGS,
    BTN_ADMIN_STATS,
    BTN_ADMIN_TESTS,
    inline_nav_row,
)


def admin_main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADMIN_POSTS), KeyboardButton(text=BTN_ADMIN_TESTS)],
            [KeyboardButton(text=BTN_ADMIN_AUTO), KeyboardButton(text=BTN_ADMIN_STATS)],
            [KeyboardButton(text=BTN_ADMIN_ADS), KeyboardButton(text=BTN_ADMIN_ADMINS)],
            [KeyboardButton(text=BTN_ADMIN_BROADCAST), KeyboardButton(text=BTN_ADMIN_SETTINGS)],
            [KeyboardButton(text=BTN_ADMIN_BACKUP), KeyboardButton(text=BTN_ADMIN_LOGS)],
            [KeyboardButton(text=BTN_ADMIN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin panel bo'limini tanlang...",
    )


def settings_menu_kb(mandatory_sub: bool) -> InlineKeyboardMarkup:
    sub_label = "✅ Majburiy obuna: YOQILGAN" if mandatory_sub else "⭕ Majburiy obuna: O'CHIRILGAN"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=sub_label, callback_data="settings:toggle_sub")],
            [InlineKeyboardButton(text="🛡 Kanal admin huquqlarini tekshirish", callback_data="settings:check_channel")],
            [InlineKeyboardButton(text="✏️ Salomlashish matnini tahrirlash", callback_data="settings:edit_welcome")],
            [InlineKeyboardButton(text="ℹ️ 'Bot haqida' matnini tahrirlash", callback_data="settings:edit_about")],
            inline_nav_row("nav:admin_home"),
        ]
    )


def backup_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💾 Hozir zaxira nusxa yaratish (ZIP)", callback_data="backup:create")],
            [InlineKeyboardButton(text="📜 Zaxira nusxalar tarixi", callback_data="backup:history")],
            inline_nav_row("nav:admin_home"),
        ]
    )
