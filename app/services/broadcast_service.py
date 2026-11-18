"""Telegram flood limitlariga rioya qiluvchi ommaviy xabar yuborish servisi."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import BroadcastStatus, ContentType
from app.models.system import Broadcast
from app.repositories.system_repo import SystemRepository
from app.repositories.user_repo import UserRepository
from app.services.channel_service import ChannelService
from app.utils.timezone import now_utc

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, int, int], Awaitable[None]]


class BroadcastService:
    def __init__(self, session: AsyncSession, bot: Bot) -> None:
        self.session = session
        self.bot = bot
        self.user_repo = UserRepository(session)
        self.sys_repo = SystemRepository(session)
        self.channel = ChannelService(bot)

    async def execute_broadcast(
        self,
        *,
        created_by: int,
        content_type: ContentType,
        text: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[list[dict[str, Any]]] = None,
        on_progress: Optional[ProgressCallback] = None,
        rate_delay_seconds: float = 0.04,
    ) -> Broadcast:
        """
        Barcha faol foydalanuvchilarga xabar yuboradi:
        - ~25 msg/sec tezlikda (flood limit himoyasi)
        - TelegramRetryAfter kelganda kerakli soniya kutib qayta urinadi
        - Botni bloklagan foydalanuvchilarni faol auditoriyadan chiqaradi
        """
        target_ids = await self.user_repo.list_active_telegram_ids()

        broadcast = Broadcast(
            content_type=content_type.value,
            text=text,
            media_file_id=media_file_id,
            buttons_json=buttons_json,
            status=BroadcastStatus.RUNNING.value,
            total_targets=len(target_ids),
            created_by=created_by,
            started_at=now_utc(),
        )
        await self.sys_repo.create_broadcast(broadcast)
        await self.session.commit()

        sent = 0
        failed = 0
        blocked = 0

        for idx, user_tg_id in enumerate(target_ids, start=1):
            delivered = False
            for attempt in range(2):
                try:
                    await self.channel.send_content(
                        chat_id=user_tg_id,
                        content_type=content_type,
                        text=text,
                        media_file_id=media_file_id,
                        buttons_json=buttons_json,
                    )
                    sent += 1
                    delivered = True
                    break
                except TelegramRetryAfter as exc:
                    wait_sec = float(getattr(exc, "retry_after", 1.0)) + 0.5
                    logger.warning("Flood limit: %.1f soniya kutilmoqda", wait_sec)
                    await asyncio.sleep(wait_sec)
                except TelegramForbiddenError:
                    blocked += 1
                    await self.user_repo.mark_blocked(user_tg_id)
                    delivered = True
                    break
                except TelegramBadRequest as exc:
                    if "chat not found" in str(exc).lower() or "user is deactivated" in str(exc).lower():
                        blocked += 1
                        await self.user_repo.mark_blocked(user_tg_id)
                    else:
                        failed += 1
                    delivered = True
                    break
                except Exception as exc:
                    logger.warning("Broadcast xatoligi (user=%s): %s", user_tg_id, exc)
                    if attempt == 1:
                        failed += 1

            if not delivered:
                failed += 1

            if on_progress and (idx % 20 == 0 or idx == len(target_ids)):
                try:
                    await on_progress(idx, len(target_ids), sent, failed + blocked)
                except Exception:
                    pass

            if rate_delay_seconds > 0:
                await asyncio.sleep(rate_delay_seconds)

        broadcast.sent_count = sent
        broadcast.failed_count = failed
        broadcast.blocked_count = blocked
        broadcast.status = BroadcastStatus.COMPLETED.value
        broadcast.completed_at = now_utc()

        await self.sys_repo.log_activity(
            admin_telegram_id=created_by,
            action="broadcast_completed",
            target_type="broadcast",
            target_id=str(broadcast.id),
            details={
                "total": len(target_ids),
                "sent": sent,
                "blocked": blocked,
                "failed": failed,
            },
        )
        await self.session.commit()
        return broadcast
