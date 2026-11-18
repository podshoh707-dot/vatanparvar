"""Adminlar bilan ishlovchi repozitoriy."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.enums import AdminRole
from app.utils.timezone import now_utc


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        stmt = select(Admin).where(Admin.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        stmt = select(Admin).where(
            Admin.telegram_id == telegram_id,
            Admin.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, active_only: bool = True) -> list[Admin]:
        stmt = select(Admin).order_by(Admin.created_at.asc())
        if active_only:
            stmt = stmt.where(Admin.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_admin(
        self,
        telegram_id: int,
        role: AdminRole,
        added_by: Optional[int] = None,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Admin:
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            existing.role = role.value
            existing.is_active = True
            if username is not None:
                existing.username = username
            if full_name is not None:
                existing.full_name = full_name
            if added_by is not None:
                existing.added_by = added_by
            existing.updated_at = now_utc()
            await self.session.flush()
            return existing

        admin = Admin(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role.value,
            is_active=True,
            added_by=added_by,
        )
        self.session.add(admin)
        await self.session.flush()
        return admin

    async def update_profile(
        self,
        telegram_id: int,
        username: Optional[str],
        full_name: Optional[str],
    ) -> None:
        admin = await self.get_by_telegram_id(telegram_id)
        if admin:
            admin.username = username
            admin.full_name = full_name
            admin.updated_at = now_utc()
            await self.session.flush()

    async def deactivate(self, telegram_id: int) -> bool:
        admin = await self.get_by_telegram_id(telegram_id)
        if not admin:
            return False
        admin.is_active = False
        admin.updated_at = now_utc()
        await self.session.flush()
        return True

    async def update_role(self, telegram_id: int, role: AdminRole) -> Optional[Admin]:
        admin = await self.get_by_telegram_id(telegram_id)
        if not admin:
            return None
        admin.role = role.value
        admin.is_active = True
        admin.updated_at = now_utc()
        await self.session.flush()
        return admin
