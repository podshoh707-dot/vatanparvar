"""Majburiy kanal obunasini tekshiruvchi middleware (faqat oddiy foydalanuvchilar uchun)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.services.subscription_service import SubscriptionService


class MandatorySubscriptionMiddleware(BaseMiddleware):
    def __init__(self, settings: Optional[Settings] = None) -> None:
        super().__init__()
        self.settings = settings or get_settings()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Adminlar uchun majburiy obuna tekshirilmaydi
        if data.get("admin") is not None:
            return await handler(event, data)

        # Kanal ichidagi test tugmalari va obunani qayta tekshirish callback'i istisno
        if isinstance(event, CallbackQuery):
            cb_data = event.data or ""
            if cb_data.startswith("chtest:") or cb_data == "user:check_sub":
                return await handler(event, data)

        # Faqat shaxsiy chatdagi foydalanuvchilarga qo'llaniladi
        if isinstance(event, Message) and event.chat.type != "private":
            return await handler(event, data)

        tg_user = getattr(event, "from_user", None)
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        bot: Bot = data["bot"]
        sub_svc = SubscriptionService(session, bot, self.settings)

        if not await sub_svc.is_mandatory_enabled():
            return await handler(event, data)

        is_sub = await sub_svc.check_user_subscribed(tg_user.id)
        if is_sub:
            return await handler(event, data)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=self.settings.channel_url)],
                [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="user:check_sub")],
            ]
        )
        notice = (
            "🔒 <b>Botdan foydalanish uchun rasmiy kanalimizga obuna bo'ling!</b>\n\n"
            f"📢 Kanal: <b>{self.settings.CHANNEL_USERNAME}</b>\n\n"
            "Obuna bo'lgach, <b>✅ Obunani tekshirish</b> tugmasini bosing."
        )
        if isinstance(event, Message):
            await event.answer(notice, parse_mode="HTML", reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer("Avval kanalga obuna bo'ling!", show_alert=True)
            if event.message:
                await event.message.answer(notice, parse_mode="HTML", reply_markup=kb)
        return None
