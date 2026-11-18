"""Ma'lumotlar bazasidan zaxira nusxa (backup) yaratish va tarixini ko'rish handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.admin import backup_menu_kb
from app.keyboards.common import BTN_ADMIN_BACKUP
from app.models.admin import Admin
from app.models.enums import Permission
from app.repositories.system_repo import SystemRepository
from app.services.backup_service import BackupService
from app.utils.timezone import format_local_dt

router = Router(name="admin_backup")


@router.message(F.text == BTN_ADMIN_BACKUP)
async def open_backup_menu(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.BACKUP):
        return
    await state.clear()
    await message.answer(
        "💾 <b>ZAXIRA NUSXA (BACKUP)</b>\n\n"
        "Ma'lumotlar bazasidagi barcha 12 ta jadvalni JSON + ZIP formatda yuklab olishingiz "
        "va oldingi zaxira nusxalar tarixini ko'rishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=backup_menu_kb(),
    )


@router.callback_query(F.data == "backup:create")
async def cb_create_backup(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.BACKUP):
        return
    assert admin is not None
    await callback.answer("Zaxira nusxa tayyorlanmoqda...")

    svc = BackupService(session)
    filename, zip_bytes, record = await svc.create_zip_backup(
        created_by=admin.telegram_id,
        backup_type="manual",
    )
    total_records = sum((record.record_counts_json or {}).values())
    size_kb = round(len(zip_bytes) / 1024, 1)

    if callback.message:
        await callback.message.answer_document(
            document=BufferedInputFile(zip_bytes, filename=filename),
            caption=(
                "✅ <b>Zaxira nusxa muvaffaqiyatli yaratildi!</b>\n\n"
                f"📁 Fayl: <code>{filename}</code>\n"
                f"📦 Hajmi: <b>{size_kb} KB</b>\n"
                f"🗂 Jadvallar: <b>{record.tables_included}</b> ta\n"
                f"📊 Jami yozuvlar: <b>{total_records}</b> ta"
            ),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "backup:history")
async def cb_backup_history(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.BACKUP):
        return
    tz = get_settings().TIMEZONE
    records = await SystemRepository(session).list_backups(limit=10)
    if not records:
        text = "📜 Hozircha zaxira nusxalar yaratilmagan."
    else:
        lines = ["📜 <b>Oxirgi zaxira nusxalar tarixi:</b>", ""]
        for r in records:
            kb = round(r.file_size_bytes / 1024, 1)
            lines.append(
                f"• <code>{r.file_name}</code> ({kb} KB) — {format_local_dt(r.created_at, tz)}"
            )
        text = "\n".join(lines)
    await callback.answer()
    if callback.message:
        await callback.message.answer(text, parse_mode="HTML")
