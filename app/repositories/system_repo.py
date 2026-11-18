"""Sozlamalar, faoliyat tarixi, broadcast va zaxira nusxa repozitoriysi."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import ActivityLog, BackupHistory, BotSetting, Broadcast
from app.utils.timezone import now_utc


class SystemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Settings ---
    async def get_setting(self, key: str) -> Optional[BotSetting]:
        stmt = select(BotSetting).where(BotSetting.key == key)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def set_setting(
        self,
        key: str,
        value: str,
        *,
        value_type: str = "str",
        description: Optional[str] = None,
        updated_by: Optional[int] = None,
    ) -> BotSetting:
        existing = await self.get_setting(key)
        if existing:
            existing.value = str(value)
            existing.value_type = value_type
            if description is not None:
                existing.description = description
            existing.updated_by = updated_by
            existing.updated_at = now_utc()
            await self.session.flush()
            return existing

        item = BotSetting(
            key=key,
            value=str(value),
            value_type=value_type,
            description=description,
            updated_by=updated_by,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_settings(self) -> list[BotSetting]:
        stmt = select(BotSetting).order_by(BotSetting.key.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    # --- Activity logs ---
    async def log_activity(
        self,
        *,
        admin_telegram_id: int,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            admin_telegram_id=admin_telegram_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details_json=details,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_activity_logs(
        self,
        *,
        limit: int = 12,
        offset: int = 0,
    ) -> tuple[list[ActivityLog], int]:
        total = int((await self.session.execute(select(func.count(ActivityLog.id)))).scalar_one() or 0)
        stmt = (
            select(ActivityLog)
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def admin_activity_summary(self, limit: int = 10) -> list[tuple[int, int]]:
        stmt = (
            select(ActivityLog.admin_telegram_id, func.count(ActivityLog.id))
            .group_by(ActivityLog.admin_telegram_id)
            .order_by(func.count(ActivityLog.id).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(int(aid), int(cnt)) for aid, cnt in rows]

    # --- Broadcasts ---
    async def create_broadcast(self, broadcast: Broadcast) -> Broadcast:
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def list_broadcasts(self, limit: int = 10) -> list[Broadcast]:
        stmt = select(Broadcast).order_by(Broadcast.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    # --- Backups ---
    async def record_backup(self, backup: BackupHistory) -> BackupHistory:
        self.session.add(backup)
        await self.session.flush()
        return backup

    async def list_backups(self, limit: int = 10) -> list[BackupHistory]:
        stmt = select(BackupHistory).order_by(BackupHistory.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
