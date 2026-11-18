"""Global xatoliklardan himoya qiluvchi middleware."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            logger.exception("Update qayta ishlashda xatolik: %s", exc)
            err_msg = (
                "⚠️ <b>Kutilmagan texnik xatolik yuz berdi.</b>\n"
                "Iltimos, amalni qayta urinib ko'ring yoki 🏠 Bosh menyu tugmasini bosing."
            )
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer("Xatolik yuz berdi. Qayta urinib ko'ring.", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(err_msg, parse_mode="HTML")
            except Exception:
                pass
            return None
