"""Oddiy foydalanuvchilar menyusi va test ishlash klaviaturalari."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.keyboards.common import (
    BTN_USER_ABOUT,
    BTN_USER_CHANNEL,
    BTN_USER_HOME,
    BTN_USER_RESULTS,
    BTN_USER_TEST,
    BTN_USER_TOPICS,
)


def user_main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_USER_TEST), KeyboardButton(text=BTN_USER_TOPICS)],
            [KeyboardButton(text=BTN_USER_RESULTS), KeyboardButton(text=BTN_USER_ABOUT)],
            [KeyboardButton(text=BTN_USER_CHANNEL), KeyboardButton(text=BTN_USER_HOME)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Bo'limni tanlang...",
    )


def user_quiz_options_kb(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🅰️ A", callback_data=f"uquiz:ans:{question_id}:A"),
                InlineKeyboardButton(text="🅱️ B", callback_data=f"uquiz:ans:{question_id}:B"),
            ],
            [
                InlineKeyboardButton(text="🇨 C", callback_data=f"uquiz:ans:{question_id}:C"),
                InlineKeyboardButton(text="🇩 D", callback_data=f"uquiz:ans:{question_id}:D"),
            ],
            [InlineKeyboardButton(text="⏹ Testni yakunlash", callback_data="uquiz:stop")],
        ]
    )


def user_topics_kb(topics: list[tuple[str, int]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, (topic, count) in enumerate(topics):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📚 {topic} ({count} ta)",
                    callback_data=f"uquiz:topic_idx:{idx}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="user:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
