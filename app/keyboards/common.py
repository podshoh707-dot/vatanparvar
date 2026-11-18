"""Umumiy tugma matnlari va navigatsiya klaviaturalari."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Umumiy navigatsiya tugmalari
BTN_BACK = "⬅️ Orqaga"
BTN_MAIN_MENU = "🏠 Bosh menyu"
BTN_CANCEL = "❌ Bekor qilish"
BTN_SKIP = "⏭ O'tkazib yuborish"

# Asosiy admin menyusi tugmalari (Master Prompt bo'yicha)
BTN_ADMIN_POSTS = "📝 POSTLARNI BOSHQARISH"
BTN_ADMIN_TESTS = "🚦 TESTLARNI BOSHQARISH"
BTN_ADMIN_AUTO = "📅 AVTOMATIK JOYLASHTIRISH"
BTN_ADMIN_STATS = "📊 STATISTIKA"
BTN_ADMIN_ADS = "📢 REKLAMA BOSHQARUVI"
BTN_ADMIN_ADMINS = "👥 ADMINLAR"
BTN_ADMIN_BROADCAST = "📨 XABAR YUBORISH"
BTN_ADMIN_SETTINGS = "⚙️ SOZLAMALAR"
BTN_ADMIN_BACKUP = "💾 ZAXIRA NUSXA"
BTN_ADMIN_LOGS = "📋 FAOLIYAT TARIXI"
BTN_ADMIN_HELP = "❓ YORDAM"

# Foydalanuvchi menyusi tugmalari (Master Prompt bo'yicha)
BTN_USER_HOME = "🏠 Bosh sahifa"
BTN_USER_TEST = "🚦 Test ishlash"
BTN_USER_TOPICS = "📚 Mavzular"
BTN_USER_RESULTS = "📊 Mening natijalarim"
BTN_USER_ABOUT = "ℹ️ Bot haqida"
BTN_USER_CHANNEL = "📢 Kanalga o'tish"


def nav_reply_row() -> list[KeyboardButton]:
    return [
        KeyboardButton(text=BTN_BACK),
        KeyboardButton(text=BTN_MAIN_MENU),
        KeyboardButton(text=BTN_CANCEL),
    ]


def cancel_only_kb(allow_skip: bool = False) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    if allow_skip:
        rows.append([KeyboardButton(text=BTN_SKIP)])
    rows.append([KeyboardButton(text=BTN_CANCEL), KeyboardButton(text=BTN_MAIN_MENU)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def inline_nav_row(back_callback: str = "nav:admin_home") -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text=BTN_BACK, callback_data=back_callback),
        InlineKeyboardButton(text=BTN_MAIN_MENU, callback_data="nav:admin_home"),
        InlineKeyboardButton(text=BTN_CANCEL, callback_data="nav:cancel"),
    ]


def pagination_row(
    prefix: str,
    page: int,
    total_pages: int,
) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if page > 1:
        row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"{prefix}:{page - 1}"))
    row.append(InlineKeyboardButton(text=f"{page}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"{prefix}:{page + 1}"))
    return row
