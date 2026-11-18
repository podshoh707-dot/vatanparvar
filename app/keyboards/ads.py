"""Reklama boshqaruvi klaviaturalari."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.keyboards.common import inline_nav_row, nav_reply_row, pagination_row
from app.models.enums import PostStatus
from app.models.post import Post
from app.utils.formatting import truncate_text

BTN_AD_CREATE = "➕ Reklama yaratish"
BTN_AD_SCHEDULE = "📅 Reklamani rejalashtirish"
BTN_AD_HISTORY = "📋 Reklamalar tarixi"
BTN_AD_EDIT = "✏️ Reklamani tahrirlash"
BTN_AD_DELETE = "🗑 Reklamani o'chirish"
BTN_AD_PAUSE = "⏸ Reklamani to'xtatish"


def ads_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_AD_CREATE), KeyboardButton(text=BTN_AD_SCHEDULE)],
            [KeyboardButton(text=BTN_AD_HISTORY), KeyboardButton(text=BTN_AD_EDIT)],
            [KeyboardButton(text=BTN_AD_DELETE), KeyboardButton(text=BTN_AD_PAUSE)],
            nav_reply_row(),
        ],
        resize_keyboard=True,
    )


def ads_list_kb(ads: list[Post], *, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ad in ads:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📢 #{ad.id} [{ad.status}] {truncate_text(ad.text, 30)}",
                    callback_data=f"ad:view:{ad.id}:history",
                )
            ]
        )
    if total_pages > 1:
        rows.append(pagination_row("ad:list", page, total_pages))
    rows.append(inline_nav_row("nav:ads_menu"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ad_detail_kb(ad: Post) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if ad.status != PostStatus.DELETED.value:
        rows.append(
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"ad:edit:{ad.id}"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ad:del_ask:{ad.id}"),
            ]
        )
    if ad.status == PostStatus.SCHEDULED.value:
        rows.append([InlineKeyboardButton(text="⏸ To'xtatish", callback_data=f"ad:toggle_pause:{ad.id}")])
    elif ad.status == PostStatus.PAUSED.value:
        rows.append([InlineKeyboardButton(text="▶️ Qayta yoqish", callback_data=f"ad:toggle_pause:{ad.id}")])
    rows.append(inline_nav_row("nav:ads_menu"))
    return InlineKeyboardMarkup(inline_keyboard=rows)
