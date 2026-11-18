"""Avtomatik test joylashtirish sozlamalari klaviaturalari."""

from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.common import inline_nav_row
from app.utils.timezone import WEEKDAY_UZ


def auto_publish_menu_kb(cfg: dict[str, Any]) -> InlineKeyboardMarkup:
    enabled_txt = "🟢 Avto-tizim: YOQILGAN (o'chirish)" if cfg["enabled"] else "🔴 Avto-tizim: O'CHIRILGAN (yoqish)"
    mode_txt = "🗳 Rejim: Quiz Poll" if cfg["publish_mode"] == "quiz_poll" else "🔘 Rejim: Inline Tugmalar"
    sel_txt = "🎲 Tanlash: Tasodifiy" if cfg["selection_mode"] == "random" else "🔢 Tanlash: Ketma-ket"
    dup_txt = "🛡 Takroriy test: TAQIQLANGAN" if cfg["prevent_duplicates"] else "🔁 Takroriy test: RUXSAT ETILGAN"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=enabled_txt, callback_data="auto:toggle_enabled")],
            [
                InlineKeyboardButton(text=f"🔢 Kuniga: {cfg['per_day']} ta", callback_data="auto:set_per_day"),
                InlineKeyboardButton(text=f"⏰ Boshlash: {cfg['start_time']}", callback_data="auto:set_start_time"),
            ],
            [
                InlineKeyboardButton(
                    text=f"⏱ Oraliq: {cfg['interval_minutes']} daq",
                    callback_data="auto:set_interval",
                ),
                InlineKeyboardButton(
                    text=f"💡 Javob e'loni: {cfg['reveal_delay_minutes']} daq",
                    callback_data="auto:set_reveal_delay",
                ),
            ],
            [InlineKeyboardButton(text="📆 Hafta kunlarini tanlash", callback_data="auto:weekdays")],
            [
                InlineKeyboardButton(text=mode_txt, callback_data="auto:toggle_publish_mode"),
                InlineKeyboardButton(text=sel_txt, callback_data="auto:toggle_selection"),
            ],
            [InlineKeyboardButton(text=dup_txt, callback_data="auto:toggle_duplicates")],
            [
                InlineKeyboardButton(text="🚀 Hozir 1 ta test chiqarish", callback_data="auto:publish_now"),
                InlineKeyboardButton(text="📋 Kelgusi navbat", callback_data="auto:upcoming"),
            ],
            inline_nav_row("nav:admin_home"),
        ]
    )


def weekdays_picker_kb(active_days: list[int]) -> InlineKeyboardMarkup:
    active_set = set(active_days)
    row1 = []
    row2 = []
    for day_idx in range(7):
        mark = "✅" if day_idx in active_set else "⬜"
        btn = InlineKeyboardButton(
            text=f"{mark} {WEEKDAY_UZ[day_idx]}",
            callback_data=f"auto:wday:{day_idx}",
        )
        if day_idx < 4:
            row1.append(btn)
        else:
            row2.append(btn)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            row1,
            row2,
            [InlineKeyboardButton(text="⬅️ Avto-sozlamalarga qaytish", callback_data="auto:menu")],
        ]
    )
