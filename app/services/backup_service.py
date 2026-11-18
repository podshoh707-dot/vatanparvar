"""Ma'lumotlar bazasini JSON + ZIP formatda zaxiralash servisi."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActivityLog,
    Admin,
    BackupHistory,
    BotSetting,
    Broadcast,
    Post,
    PublishedTest,
    ScheduledJob,
    TestAnswer,
    TestAttempt,
    TestQuestion,
    User,
)
from app.repositories.system_repo import SystemRepository
from app.utils.timezone import now_local

BACKUP_MODELS = [
    ("admins", Admin),
    ("users", User),
    ("posts", Post),
    ("test_questions", TestQuestion),
    ("published_tests", PublishedTest),
    ("test_answers", TestAnswer),
    ("test_attempts", TestAttempt),
    ("scheduled_jobs", ScheduledJob),
    ("settings", BotSetting),
    ("activity_logs", ActivityLog),
    ("broadcasts", Broadcast),
    ("backup_history", BackupHistory),
]


def _serialize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.isoformat()
    return val


class BackupService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sys_repo = SystemRepository(session)

    async def create_zip_backup(
        self,
        *,
        created_by: int,
        backup_type: str = "manual",
    ) -> tuple[str, bytes, BackupHistory]:
        """Barcha jadvallarni JSON ko'rinishida ZIP arxivga yig'adi va tarixga yozadi."""
        timestamp = now_local().strftime("%Y%m%d_%H%M%S")
        file_name = f"avtovatanparvar_backup_{timestamp}.zip"
        counts: dict[str, int] = {}

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for table_name, model in BACKUP_MODELS:
                rows = (await self.session.execute(select(model))).scalars().all()
                serialized_rows = []
                for row in rows:
                    row_dict = {
                        col.name: _serialize_value(getattr(row, col.name))
                        for col in model.__table__.columns
                    }
                    serialized_rows.append(row_dict)
                counts[table_name] = len(serialized_rows)
                zf.writestr(
                    f"{table_name}.json",
                    json.dumps(serialized_rows, ensure_ascii=False, indent=2),
                )

            manifest = {
                "project": "AVTOVATANPARVAR TESTLARI",
                "created_at": now_local().isoformat(),
                "created_by": created_by,
                "backup_type": backup_type,
                "tables": counts,
            }
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        zip_bytes = buf.getvalue()
        record = BackupHistory(
            backup_type=backup_type,
            file_name=file_name,
            file_size_bytes=len(zip_bytes),
            tables_included=len(BACKUP_MODELS),
            record_counts_json=counts,
            status="completed",
            created_by=created_by,
        )
        await self.sys_repo.record_backup(record)
        await self.sys_repo.log_activity(
            admin_telegram_id=created_by,
            action="backup_created",
            target_type="backup",
            target_id=str(record.id),
            details={"file_name": file_name, "size_bytes": len(zip_bytes)},
        )
        return file_name, zip_bytes, record
