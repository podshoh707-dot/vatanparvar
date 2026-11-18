"""Testlarni Excel (.xlsx) formatda import, eksport va shablon yaratish servisi."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Difficulty, TestStatus
from app.repositories.system_repo import SystemRepository
from app.repositories.test_repo import TestRepository

REQUIRED_COLUMNS = [
    "savol",
    "a",
    "b",
    "c",
    "d",
    "togri_javob",
]

ALL_EXPORT_HEADERS = [
    "ID",
    "savol",
    "a",
    "b",
    "c",
    "d",
    "togri_javob",
    "izoh",
    "mavzu",
    "qiyinlik",
    "holat",
]

HEADER_ALIASES = {
    "savol": "savol",
    "question": "savol",
    "question_text": "savol",
    "a": "a",
    "option_a": "a",
    "a_javob": "a",
    "b": "b",
    "option_b": "b",
    "b_javob": "b",
    "c": "c",
    "option_c": "c",
    "c_javob": "c",
    "d": "d",
    "option_d": "d",
    "d_javob": "d",
    "togri_javob": "togri_javob",
    "to'g'ri_javob": "togri_javob",
    "correct": "togri_javob",
    "correct_option": "togri_javob",
    "javob": "togri_javob",
    "izoh": "izoh",
    "explanation": "izoh",
    "mavzu": "mavzu",
    "topic": "mavzu",
    "qiyinlik": "qiyinlik",
    "difficulty": "qiyinlik",
}

DIFFICULTY_ALIASES = {
    "easy": Difficulty.EASY,
    "oson": Difficulty.EASY,
    "1": Difficulty.EASY,
    "medium": Difficulty.MEDIUM,
    "orta": Difficulty.MEDIUM,
    "o'rta": Difficulty.MEDIUM,
    "2": Difficulty.MEDIUM,
    "hard": Difficulty.HARD,
    "qiyin": Difficulty.HARD,
    "3": Difficulty.HARD,
}


@dataclass
class ExcelImportReport:
    total_rows: int = 0
    imported: int = 0
    duplicates: int = 0
    errors: list[str] = field(default_factory=list)


class ExcelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.test_repo = TestRepository(session)
        self.sys_repo = SystemRepository(session)

    @staticmethod
    def build_template_bytes() -> bytes:
        """Adminlar uchun tayyor namuna Excel shablonini yaratadi."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Testlar"

        headers = ["savol", "a", "b", "c", "d", "togri_javob", "izoh", "mavzu", "qiyinlik"]
        ws.append(headers)
        ws.append(
            [
                "Aholi punktlarida yengil avtomobillar uchun maksimal ruxsat etilgan tezlik qancha?",
                "50 km/soat",
                "60 km/soat",
                "70 km/soat",
                "80 km/soat",
                "B",
                "O'zbekiston YHQ ga muvofiq aholi punktlarida maksimal tezlik 60 km/soat.",
                "Tezlik chegaralari",
                "easy",
            ]
        )

        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[cell.column_letter].width = 22

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def export_tests_bytes(self) -> tuple[bytes, int]:
        """Barcha testlarni chiroyli Excel faylga eksport qiladi."""
        questions = await self.test_repo.list_all_for_export()
        wb = Workbook()
        ws = wb.active
        ws.title = "AvtoVatanparvar Testlar"

        ws.append(ALL_EXPORT_HEADERS)
        header_fill = PatternFill(start_color="0F4C81", end_color="0F4C81", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for col_idx in range(1, len(ALL_EXPORT_HEADERS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for q in questions:
            ws.append(
                [
                    q.id,
                    q.question_text,
                    q.option_a,
                    q.option_b,
                    q.option_c,
                    q.option_d,
                    q.correct_option,
                    q.explanation or "",
                    q.topic,
                    q.difficulty,
                    q.status,
                ]
            )

        widths = [8, 45, 25, 25, 25, 25, 14, 38, 22, 12, 14]
        for idx, width in enumerate(widths, start=1):
            col_letter = ws.cell(row=1, column=idx).column_letter
            ws.column_dimensions[col_letter].width = width

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), len(questions)

    async def import_tests_from_bytes(
        self,
        data: bytes,
        *,
        created_by: int,
        auto_approve: bool = False,
    ) -> ExcelImportReport:
        """
        Excel faylni to'liq tekshiruvdan o'tkazib import qiladi.
        Noto'g'ri formatdagi faylni rad etadi va barcha xatolar ro'yxatini qaytaradi.
        """
        report = ExcelImportReport()
        try:
            wb = load_workbook(filename=io.BytesIO(data), data_only=True)
        except Exception:
            report.errors.append("Fayl haqiqiy .xlsx Excel formatida emas yoki shikastlangan.")
            return report

        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            report.errors.append("Excel faylda sarlavha yoki test qatorlari topilmadi.")
            return report

        raw_headers = [str(c).strip().lower().replace(" ", "_") if c is not None else "" for c in rows[0]]
        col_map: dict[str, int] = {}
        for idx, h in enumerate(raw_headers):
            canonical = HEADER_ALIASES.get(h)
            if canonical and canonical not in col_map:
                col_map[canonical] = idx

        missing = [req for req in REQUIRED_COLUMNS if req not in col_map]
        if missing:
            report.errors.append(
                "Majburiy ustunlar yetishmayapti: "
                + ", ".join(missing)
                + ". Kerakli ustunlar: savol, a, b, c, d, togri_javob."
            )
            return report

        def _get(row: tuple, key: str) -> str:
            idx = col_map.get(key)
            if idx is None or idx >= len(row) or row[idx] is None:
                return ""
            return str(row[idx]).strip()

        status = TestStatus.APPROVED if auto_approve else TestStatus.PENDING

        for row_num, row in enumerate(rows[1:], start=2):
            if not any(cell is not None and str(cell).strip() for cell in row):
                continue

            report.total_rows += 1
            question = _get(row, "savol")
            opt_a = _get(row, "a")
            opt_b = _get(row, "b")
            opt_c = _get(row, "c")
            opt_d = _get(row, "d")
            correct = _get(row, "togri_javob").upper()
            explanation = _get(row, "izoh") or None
            topic = _get(row, "mavzu") or "Umumiy"
            diff_raw = (_get(row, "qiyinlik") or "medium").lower()

            row_errors: list[str] = []
            if len(question) < 5:
                row_errors.append("savol juda qisqa yoki bo'sh")
            if not all([opt_a, opt_b, opt_c, opt_d]):
                row_errors.append("A, B, C, D javoblarning barchasi to'ldirilishi shart")
            if correct not in {"A", "B", "C", "D"}:
                row_errors.append(f"togri_javob '{correct}' noto'g'ri (faqat A, B, C yoki D)")
            difficulty: Optional[Difficulty] = DIFFICULTY_ALIASES.get(diff_raw)
            if difficulty is None:
                row_errors.append(f"qiyinlik '{diff_raw}' noto'g'ri (easy/medium/hard)")

            if row_errors:
                report.errors.append(f"{row_num}-qator: " + "; ".join(row_errors))
                continue

            _, created = await self.test_repo.create_question(
                question_text=question,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=correct,
                explanation=explanation,
                topic=topic,
                difficulty=difficulty,
                status=status,
                created_by=created_by,
            )
            if created:
                report.imported += 1
            else:
                report.duplicates += 1

        await self.sys_repo.log_activity(
            admin_telegram_id=created_by,
            action="tests_excel_imported",
            target_type="test_question",
            details={
                "total_rows": report.total_rows,
                "imported": report.imported,
                "duplicates": report.duplicates,
                "errors_count": len(report.errors),
            },
        )
        return report
