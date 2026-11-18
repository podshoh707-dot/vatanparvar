"""Admin autentifikatsiyasi va foydalanuvchi profilini har so'rovda tekshiruvchi middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.admin_repo import AdminRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_service import AdminService


class AuthAndUserMiddleware(BaseMiddleware):
    def __init__(self, settings: Optional[Settings] = None) -> None:
        super().__init__()
        self.settings = settings or get_settings()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]
        tg_user = None
        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user

        data["admin"] = None
        data["db_user"] = None

        if tg_user is not None and not tg_user.is_bot:
            # Foydalanuvchini bazada saqlash / yangilash
            user_repo = UserRepository(session)
            db_user = await user_repo.upsert_user(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code,
            )
            data["db_user"] = db_user

            # Admin holatini har safar bazadan yangidan tekshirish
            admin_svc = AdminService(session, self.settings)
            admin = await admin_svc.get_active_admin(tg_user.id)
            if admin is not None:
                full_name = " ".join(p for p in [tg_user.first_name, tg_user.last_name] if p) or None
                if admin.username != tg_user.username or admin.full_name != full_name:
                    await AdminRepository(session).update_profile(
                        tg_user.id,
                        username=tg_user.username,
                        full_name=full_name,
                    )
                data["admin"] = admin

        return await handler(event, data)
