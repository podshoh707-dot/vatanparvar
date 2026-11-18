"""Database ulanishi, 12 jadval mavjudligi, admin autentifikatsiyasi va rollar testlari."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

from app.models.enums import AdminRole, Permission
from app.services.admin_service import AdminService


@pytest.mark.asyncio
async def test_database_connection_and_all_12_tables_exist(db):
    assert await db.health_check() is True

    async with db.engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))

    expected_tables = {
        "admins",
        "users",
        "posts",
        "test_questions",
        "test_answers",
        "test_attempts",
        "published_tests",
        "scheduled_jobs",
        "settings",
        "activity_logs",
        "broadcasts",
        "backup_history",
    }
    assert expected_tables.issubset(table_names)


@pytest.mark.asyncio
async def test_superadmin_bootstrap_and_roles_permissions(session, test_settings):
    svc = AdminService(session, test_settings)

    superadmin = await svc.get_active_admin(test_settings.SUPERADMIN_ID)
    assert superadmin is not None
    assert superadmin.is_super_admin
    assert superadmin.can(Permission.MANAGE_ADMINS)
    assert superadmin.can(Permission.MANAGE_POSTS)
    assert superadmin.can(Permission.APPROVE_TESTS)

    # SUPER_ADMIN yangi adminlarni qo'sha oladi
    tm, msg = await svc.add_admin(actor=superadmin, target_telegram_id=200001, role=AdminRole.TEST_MANAGER)
    assert tm is not None
    assert tm.can(Permission.MANAGE_TESTS)
    assert tm.can(Permission.APPROVE_TESTS)
    assert not tm.can(Permission.MANAGE_POSTS)
    assert not tm.can(Permission.MANAGE_ADMINS)

    editor, _ = await svc.add_admin(actor=superadmin, target_telegram_id=200002, role=AdminRole.EDITOR)
    assert editor is not None
    assert editor.can(Permission.MANAGE_POSTS)
    assert not editor.can(Permission.MANAGE_TESTS)
    assert not editor.can(Permission.BROADCAST)

    viewer, _ = await svc.add_admin(actor=superadmin, target_telegram_id=200003, role=AdminRole.STATISTIC_VIEWER)
    assert viewer is not None
    assert viewer.can(Permission.VIEW_STATS)
    assert not viewer.can(Permission.MANAGE_POSTS)
    assert not viewer.can(Permission.MANAGE_TESTS)

    # Oddiy admin yoki TEST_MANAGER yangi admin qo'sha olmaydi!
    denied, err = await svc.add_admin(actor=tm, target_telegram_id=200099, role=AdminRole.EDITOR)
    assert denied is None
    assert "SUPER ADMIN" in err

    # Admin o'chirilganda uning huquqlari darhol bekor qilinadi
    removed, _ = await svc.remove_admin(actor=superadmin, target_telegram_id=200002)
    assert removed is True
    assert await svc.get_active_admin(200002) is None

    # Asosiy SUPERADMIN_ID ni o'chirish taqiqlangan
    cannot_remove, _ = await svc.remove_admin(actor=superadmin, target_telegram_id=test_settings.SUPERADMIN_ID)
    assert cannot_remove is False
