"""Testlarni boshqarish bo'limi klaviaturalari."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.keyboards.common import inline_nav_row, nav_reply_row, pagination_row
from app.models.enums import TestStatus
from app.models.test import TestQuestion
from app.utils.formatting import truncate_text

BTN_TEST_ADD = "➕ Test qo'shish"
BTN_TEST_ALL = "📋 Barcha testlar"
BTN_TEST_EDIT = "✏️ Testni tahrirlash"
BTN_TEST_DELETE = "🗑 Testni o'chirish"
BTN_TEST_IMPORT = "📥 Excel import"
BTN_TEST_EXPORT = "📤 Excel eksport"
BTN_TEST_SEARCH = "🔎 Test qidirish"
BTN_TEST_TOPICS = "📚 Mavzular bo'yicha saralash"
BTN_TEST_APPROVE = "✅ Testni tasdiqlash"
BTN_TEST_PENDING = "⏳ Tasdiqlanmagan testlar"


def tests_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TEST_ADD), KeyboardButton(text=BTN_TEST_ALL)],
            [KeyboardButton(text=BTN_TEST_EDIT), KeyboardButton(text=BTN_TEST_DELETE)],
            [KeyboardButton(text=BTN_TEST_IMPORT), KeyboardButton(text=BTN_TEST_EXPORT)],
            [KeyboardButton(text=BTN_TEST_SEARCH), KeyboardButton(text=BTN_TEST_TOPICS)],
            [KeyboardButton(text=BTN_TEST_APPROVE), KeyboardButton(text=BTN_TEST_PENDING)],
            nav_reply_row(),
        ],
        resize_keyboard=True,
    )


def correct_option_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="A", callback_data="tcreate:corr:A"),
                InlineKeyboardButton(text="B", callback_data="tcreate:corr:B"),
                InlineKeyboardButton(text="C", callback_data="tcreate:corr:C"),
                InlineKeyboardButton(text="D", callback_data="tcreate:corr:D"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")],
        ]
    )


def difficulty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Oson", callback_data="tcreate:diff:easy"),
                InlineKeyboardButton(text="🟡 O'rta", callback_data="tcreate:diff:medium"),
                InlineKeyboardButton(text="🔴 Qiyin", callback_data="tcreate:diff:hard"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")],
        ]
    )


def test_create_confirm_kb(can_approve: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="💾 Saqlash (Tasdiqlash kutilmoqda)", callback_data="tcreate:save:pending")]
    ]
    if can_approve:
        rows.append(
            [InlineKeyboardButton(text="✅ Saqlash va darhol tasdiqlash", callback_data="tcreate:save:approved")]
        )
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tests_list_kb(
    questions: list[TestQuestion],
    *,
    scope: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for q in questions:
        icon = "✅" if q.status == TestStatus.APPROVED.value else "⏳"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{icon} #{q.id} {truncate_text(q.question_text, 34)}",
                    callback_data=f"test:view:{q.id}",
                )
            ]
        )
    if total_pages > 1:
        rows.append(pagination_row(f"test:list:{scope}", page, total_pages))
    rows.append(inline_nav_row("nav:tests_menu"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def test_detail_kb(q: TestQuestion, *, can_approve: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if q.status != TestStatus.APPROVED.value and can_approve:
        rows.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"test:approve:{q.id}")])
    if q.status == TestStatus.APPROVED.value:
        rows.append(
            [
                InlineKeyboardButton(text="📢 Kanalga chiqarish (Inline)", callback_data=f"test:pub:{q.id}:inline"),
                InlineKeyboardButton(text="🗳 Quiz Poll chiqarish", callback_data=f"test:pub:{q.id}:quiz_poll"),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"test:edit:{q.id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"test:del_ask:{q.id}"),
        ]
    )
    rows.append(inline_nav_row("nav:tests_menu"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def test_edit_fields_kb(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❓ Savol", callback_data=f"tedit:{question_id}:question_text"),
                InlineKeyboardButton(text="📚 Mavzu", callback_data=f"tedit:{question_id}:topic"),
            ],
            [
                InlineKeyboardButton(text="A javob", callback_data=f"tedit:{question_id}:option_a"),
                InlineKeyboardButton(text="B javob", callback_data=f"tedit:{question_id}:option_b"),
            ],
            [
                InlineKeyboardButton(text="C javob", callback_data=f"tedit:{question_id}:option_c"),
                InlineKeyboardButton(text="D javob", callback_data=f"tedit:{question_id}:option_d"),
            ],
            [
                InlineKeyboardButton(text="✅ To'g'ri javob", callback_data=f"tedit:{question_id}:correct_option"),
                InlineKeyboardButton(text="💡 Izoh", callback_data=f"tedit:{question_id}:explanation"),
            ],
            [
                InlineKeyboardButton(text="🎯 Qiyinlik", callback_data=f"tedit:{question_id}:difficulty"),
                InlineKeyboardButton(text="🖼 Rasm", callback_data=f"tedit:{question_id}:image_file_id"),
            ],
            [InlineKeyboardButton(text="⬅️ Testga qaytish", callback_data=f"test:view:{question_id}")],
        ]
    )


def test_delete_confirm_kb(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"test:del_yes:{question_id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"test:view:{question_id}"),
            ]
        ]
    )


def excel_import_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Namuna Excel shablonni yuklab olish", callback_data="test:excel_template")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nav:cancel")],
        ]
    )
