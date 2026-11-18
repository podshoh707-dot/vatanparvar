"""Oddiy foydalanuvchilar repozitoriysi."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.timezone import now_utc


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        now = now_utc()
        if user:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.is_active = True
            user.is_blocked = False
            user.last_active_at = now
            user.updated_at = now
            await self.session.flush()
            return user

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_active=True,
            is_blocked=False,
            last_active_at=now,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def mark_blocked(self, telegram_id: int) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_blocked = True
            user.is_active = False
            user.updated_at = now_utc()
            await self.session.flush()

    async def set_subscription(self, telegram_id: int, is_subscribed: bool) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_subscribed = is_subscribed
            user.updated_at = now_utc()
            await self.session.flush()

    async def increment_stats(self, user_id: int, is_correct: bool) -> None:
        user = await self.session.get(User, user_id)
        if user:
            user.total_answers += 1
            if is_correct:
                user.correct_answers += 1
            user.last_active_at = now_utc()
            await self.session.flush()

    async def list_active_telegram_ids(self) -> list[int]:
        stmt = (
            select(User.telegram_id)
            .where(User.is_active.is_(True), User.is_blocked.is_(False))
            .order_by(User.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_total(self) -> int:
        stmt = select(func.count(User.id))
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def count_active(self) -> int:
        stmt = select(func.count(User.id)).where(
            User.is_active.is_(True),
            User.is_blocked.is_(False),
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def count_since(self, since: datetime) -> int:
        stmt = select(func.count(User.id)).where(User.created_at >= since)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def list_created_since(self, since: datetime) -> list[datetime]:
        stmt = select(User.created_at).where(User.created_at >= since)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
