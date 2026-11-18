"""Adminlar, rollar va faoliyat jurnali servisi."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.admin import Admin
from app.models.enums import AdminRole, Permission
from app.repositories.admin_repo import AdminRepository
from app.repositories.system_repo import SystemRepository


class AdminService:
    def __init__(self, session: AsyncSession, settings: Optional[Settings] = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.admin_repo = AdminRepository(session)
        self.sys_repo = SystemRepository(session)

    async def ensure_superadmin(self) -> Admin:
        """SUPERADMIN_ID va ADMIN_IDS dagi asosiy adminlarni bazada doimiy faol sifatida kafolatlaydi."""
        main_admin = await self.admin_repo.upsert_admin(
            telegram_id=self.settings.SUPERADMIN_ID,
            role=AdminRole.SUPER_ADMIN,
            added_by=self.settings.SUPERADMIN_ID,
        )
        for aid in self.settings.admin_id_list:
            if aid != self.settings.SUPERADMIN_ID:
                await self.admin_repo.upsert_admin(
                    telegram_id=aid,
                    role=AdminRole.ADMIN,
                    added_by=self.settings.SUPERADMIN_ID,
                )
        return main_admin

    async def get_active_admin(self, telegram_id: int) -> Optional[Admin]:
        """Har bir so'rovda bazadan admin holatini tekshiradi (o'chirilgan admin darhol bloklanadi)."""
        admin = await self.admin_repo.get_active_by_telegram_id(telegram_id)
        if admin is None and telegram_id in self.settings.admin_id_list:
            role = AdminRole.SUPER_ADMIN if telegram_id == self.settings.SUPERADMIN_ID else AdminRole.ADMIN
            admin = await self.admin_repo.upsert_admin(
                telegram_id=telegram_id,
                role=role,
                added_by=self.settings.SUPERADMIN_ID,
            )
        return admin

    async def add_admin(
        self,
        *,
        actor: Admin,
        target_telegram_id: int,
        role: AdminRole,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> tuple[Optional[Admin], str]:
        if not actor.is_super_admin:
            return None, "Faqat SUPER ADMIN yangi admin qo'sha oladi."

        if target_telegram_id == self.settings.SUPERADMIN_ID and role != AdminRole.SUPER_ADMIN:
            return None, "Asosiy SUPER ADMIN rolini pasaytirish mumkin emas."

        created = await self.admin_repo.upsert_admin(
            telegram_id=target_telegram_id,
            role=role,
            added_by=actor.telegram_id,
            username=username,
            full_name=full_name,
        )
        await self.log(
            actor.telegram_id,
            "admin_added",
            target_type="admin",
            target_id=str(target_telegram_id),
            details={"role": role.value},
        )
        return created, "Admin muvaffaqiyatli saqlandi."

    async def remove_admin(
        self,
        *,
        actor: Admin,
        target_telegram_id: int,
    ) -> tuple[bool, str]:
        if not actor.is_super_admin:
            return False, "Faqat SUPER ADMIN adminlarni o'chira oladi."

        if target_telegram_id == self.settings.SUPERADMIN_ID:
            return False, "Asosiy SUPER ADMIN ni o'chirish mumkin emas."

        if target_telegram_id == actor.telegram_id:
            return False, "O'zingizni o'zingiz adminlikdan olib tashlay olmaysiz."

        ok = await self.admin_repo.deactivate(target_telegram_id)
        if not ok:
            return False, "Admin topilmadi."

        await self.log(
            actor.telegram_id,
            "admin_removed",
            target_type="admin",
            target_id=str(target_telegram_id),
        )
        return True, "Admin ruxsatlari darhol bekor qilindi."

    async def change_role(
        self,
        *,
        actor: Admin,
        target_telegram_id: int,
        new_role: AdminRole,
    ) -> tuple[bool, str]:
        if not actor.is_super_admin:
            return False, "Faqat SUPER ADMIN rollarni o'zgartira oladi."
        if target_telegram_id == self.settings.SUPERADMIN_ID and new_role != AdminRole.SUPER_ADMIN:
            return False, "Asosiy SUPER ADMIN rolini o'zgartirish mumkin emas."

        updated = await self.admin_repo.update_role(target_telegram_id, new_role)
        if not updated:
            return False, "Admin topilmadi."

        await self.log(
            actor.telegram_id,
            "admin_role_changed",
            target_type="admin",
            target_id=str(target_telegram_id),
            details={"new_role": new_role.value},
        )
        return True, "Admin roli yangilandi."

    async def list_active_admins(self) -> list[Admin]:
        return await self.admin_repo.list_all(active_only=True)

    async def check_permission(self, admin: Optional[Admin], perm: Permission) -> bool:
        return bool(admin and admin.can(perm))

    async def log(
        self,
        admin_telegram_id: int,
        action: str,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.sys_repo.log_activity(
            admin_telegram_id=admin_telegram_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
