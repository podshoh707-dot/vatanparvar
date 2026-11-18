"""Postlarni boshqarish bo'limi klaviaturalari."""

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

BTN_POST_NEW = "➕ Yangi post"
BTN_POST_PHOTO = "📷 Rasmli post"
BTN_POST_VIDEO = "🎥 Videoli post"
BTN_POST_DOC = "📄 Hujjatli post"
BTN_POST_EDIT = "✏️ Postni tahrirlash"
BTN_POST_DELETE = "🗑 Postni o'chirish"
BTN_POST_SCHEDULED = "📅 Rejalashtirilgan postlar"
BTN_POST_HISTORY = "📚 Postlar tarixi"
BTN_POST_REPOST = "🔁 Postni qayta joylash"


def posts_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_POST_NEW), KeyboardButton(text=BTN_POST_PHOTO)],
            [KeyboardButton(text=BTN_POST_VIDEO), KeyboardButton(text=BTN_POST_DOC)],
            [KeyboardButton(text=BTN_POST_EDIT), KeyboardButton(text=BTN_POST_DELETE)],
            [KeyboardButton(text=BTN_POST_SCHEDULED), KeyboardButton(text=BTN_POST_HISTORY)],
            [KeyboardButton(text=BTN_POST_REPOST)],
            nav_reply_row(),
        ],
        resize_keyboard=True,
    )


def post_confirm_kb(is_ad: bool = False) -> InlineKeyboardMarkup:
    prefix = "ad" if is_ad else "post"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Hozir kanalga joylash", callback_data=f"{prefix}:confirm_now")],
            [InlineKeyboardButton(text="📅 Vaqtga rejalashtirish", callback_data=f"{prefix}:choose_schedule")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")],
        ]
    )


def post_schedule_confirm_kb(is_ad: bool = False) -> InlineKeyboardMarkup:
    prefix = "ad" if is_ad else "post"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Rejalashtirishni tasdiqlash", callback_data=f"{prefix}:confirm_sched")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")],
        ]
    )


def posts_list_kb(
    posts: list[Post],
    *,
    mode: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in posts:
        preview = truncate_text(p.text, 34)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{p.id} [{p.content_type}] {preview}",
                    callback_data=f"post:view:{p.id}:{mode}",
                )
            ]
        )
    if total_pages > 1:
        rows.append(pagination_row(f"post:list:{mode}", page, total_pages))
    rows.append(inline_nav_row("nav:posts_menu"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_detail_kb(post: Post) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if post.status != PostStatus.DELETED.value:
        rows.append(
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"post:edit:{post.id}"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"post:del_ask:{post.id}"),
            ]
        )
        rows.append([InlineKeyboardButton(text="🔁 Qayta joylash", callback_data=f"post:repost_ask:{post.id}")])
    rows.append(inline_nav_row("nav:posts_menu"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_delete_confirm_kb(post_id: int, is_ad: bool = False) -> InlineKeyboardMarkup:
    prefix = "ad" if is_ad else "post"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"{prefix}:del_yes:{post_id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"{prefix}:view:{post_id}:history"),
            ]
        ]
    )


def post_repost_confirm_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, qayta joylash", callback_data=f"post:repost_yes:{post_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"post:view:{post_id}:history"),
            ]
        ]
    )
