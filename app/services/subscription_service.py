"""Majburiy kanal obunasini tekshirish servisi."""

from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.user_repo import UserRepository
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

SUBSCRIBED_STATUSES = {"creator", "administrator", "member", "restricted"}


class SubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        settings: Optional[Settings] = None,
    ) -> None:
        self.session = session
        self.bot = bot
        self.settings = settings or get_settings()
        self.settings_service = SettingsService(session)
        self.user_repo = UserRepository(session)

    async def is_mandatory_enabled(self) -> bool:
        return await self.settings_service.get_bool("mandatory_subscription", False)

    async def check_user_subscribed(self, user_telegram_id: int) -> bool:
        """Foydalanuvchi asosiy kanalga a'zo ekanligini tekshiradi."""
        try:
            member = await self.bot.get_chat_member(
                chat_id=self.settings.channel_target,
                user_id=user_telegram_id,
            )
            status = getattr(member, "status", "")
            is_sub = status in SUBSCRIBED_STATUSES
            await self.user_repo.set_subscription(user_telegram_id, is_sub)
            return is_sub
        except Exception as exc:
            logger.warning("Obuna tekshirishda xatolik (user=%s): %s", user_telegram_id, exc)
            # Agar bot kanalga ulana olmasa foydalanuvchini bloklab qo'ymaymiz, lekin logga yozamiz
            return True
