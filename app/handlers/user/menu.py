"""Oddiy foydalanuvchilar menyusi handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.common import (
    BTN_USER_ABOUT,
    BTN_USER_CHANNEL,
    BTN_USER_HOME,
    BTN_USER_RESULTS,
    BTN_USER_TOPICS,
)
from app.keyboards.users import user_main_menu_kb, user_topics_kb
from app.models.user import User
from app.repositories.test_repo import TestRepository
from app.services.settings_service import SettingsService
from app.services.subscription_service import SubscriptionService

router = Router(name="user_menu")


@router.message(F.text == BTN_USER_HOME)
async def user_home(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    welcome = await SettingsService(session).get_raw("bot_welcome_text")
    await message.answer(welcome, parse_mode="HTML", reply_markup=user_main_menu_kb())


@router.callback_query(F.data == "user:home")
async def cb_user_home(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await callback.answer()
    welcome = await SettingsService(session).get_raw("bot_welcome_text")
    if callback.message:
        await callback.message.answer(welcome, parse_mode="HTML", reply_markup=user_main_menu_kb())


@router.callback_query(F.data == "user:check_sub")
async def cb_user_check_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if not callback.from_user:
        await callback.answer()
        return
    is_sub = await SubscriptionService(session, bot).check_user_subscribed(callback.from_user.id)
    if is_sub:
        await callback.answer("✅ Obuna tasdiqlandi! Xush kelibsiz!", show_alert=True)
        if callback.message:
            await callback.message.answer(
                "✅ <b>Obunangiz tasdiqlandi!</b> Endi botdan to'liq foydalanishingiz mumkin.",
                parse_mode="HTML",
                reply_markup=user_main_menu_kb(),
            )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmagansiz!", show_alert=True)


@router.message(F.text == BTN_USER_TOPICS)
async def user_show_topics(message: Message, session: AsyncSession) -> None:
    topics = await TestRepository(session).list_topics(approved_only=True)
    if not topics:
        await message.answer(
            "📚 Hozircha tasdiqlangan test mavzulari qo'shilmagan. Tez orada yangi testlar joylanadi!",
            reply_markup=user_main_menu_kb(),
        )
        return
    await message.answer(
        "📚 <b>Test mavzulari</b>\nBilimingizni sinamoqchi bo'lgan mavzuni tanlang:",
        parse_mode="HTML",
        reply_markup=user_topics_kb(topics),
    )


@router.message(F.text == BTN_USER_RESULTS)
async def user_show_results(message: Message, db_user: Optional[User]) -> None:
    if not db_user:
        await message.answer("Natijalar topilmadi.", reply_markup=user_main_menu_kb())
        return
    total = db_user.total_answers
    correct = db_user.correct_answers
    wrong = max(0, total - correct)
    acc = round((correct / total) * 100, 1) if total > 0 else 0.0

    await message.answer(
        "📊 <b>MENING NATIJALARIM</b>\n\n"
        f"• Jami yechilgan testlar: <b>{total}</b>\n"
        f"• ✅ To'g'ri javoblar: <b>{correct}</b>\n"
        f"• ❌ Noto'g'ri javoblar: <b>{wrong}</b>\n"
        f"• 🎯 Aniqlik darajasi: <b>{acc}%</b>\n\n"
        "Bilimingizni oshirish uchun <b>🚦 Test ishlash</b> bo'limiga o'ting!",
        parse_mode="HTML",
        reply_markup=user_main_menu_kb(),
    )


@router.message(F.text == BTN_USER_ABOUT)
async def user_show_about(message: Message, session: AsyncSession) -> None:
    about = await SettingsService(session).get_raw("bot_about_text")
    await message.answer(about, parse_mode="HTML", reply_markup=user_main_menu_kb())


@router.message(F.text == BTN_USER_CHANNEL)
async def user_go_channel(message: Message) -> None:
    cfg = get_settings()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📢 {cfg.CHANNEL_USERNAME} kanaliga o'tish", url=cfg.channel_url)]
        ]
    )
    await message.answer(
        f"📢 Rasmiy Telegram kanalimiz: <b>{cfg.CHANNEL_USERNAME}</b>\n"
        "Har kuni yangi YHQ testlari va foydali ma'lumotlar uchun obuna bo'ling!",
        parse_mode="HTML",
        reply_markup=kb,
    )
