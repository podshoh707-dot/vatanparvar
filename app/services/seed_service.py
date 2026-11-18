"""E-Avtomaktab 500 ta rasmiy testlarini bazaga avtomatik kiritish (seed) servisi."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.enums import Difficulty, TestStatus
from app.models.test import TestQuestion
from app.utils.security import compute_question_hash
from app.utils.timezone import now_utc

logger = logging.getLogger(__name__)


async def seed_eavtomaktab_questions(
    session: AsyncSession,
    settings: Optional[Settings] = None,
    force: bool = False,
) -> int:
    """database/questions_data.json yoki db/questions.json dan 500 ta E-Avtomaktab savollarini kiritadi."""
    cfg = settings or get_settings()

    res = await session.execute(select(func.count(TestQuestion.id)))
    current_count = res.scalar() or 0

    if current_count == 500 and not force:
        logger.info("[seed] Bazada 500 ta sof E-Avtomaktab savollari mavjud, seed talab qilinmaydi.")
        return 0

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        os.path.join(base_dir, "database", "questions_data.json"),
        os.path.join(base_dir, "db", "questions.json"),
    ]
    json_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not json_path:
        logger.warning("[seed] Savollar JSON fayli topilmadi!")
        return 0

    logger.info(f"[seed] {json_path} faylidan 500 ta E-Avtomaktab testlari yuklanmoqda...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if force or (current_count > 0 and current_count != 500):
        await session.execute(delete(TestQuestion))

    now = now_utc()
    created_count = 0
    for item in data:
        q_text = str(item.get("text", "")).strip()
        if not q_text:
            continue

        opts = item.get("options", [])
        opt_a, opt_b, opt_c, opt_d = "-", "-", "-", "-"
        if isinstance(opts, list):
            for i, opt in enumerate(opts):
                if isinstance(opt, dict):
                    letter = (opt.get("letter") or chr(65 + i)).strip().upper()
                    t = opt.get("text", "")
                    if letter == "A":
                        opt_a = t
                    elif letter == "B":
                        opt_b = t
                    elif letter == "C":
                        opt_c = t
                    elif letter == "D":
                        opt_d = t
                elif isinstance(opt, str):
                    if i == 0:
                        opt_a = opt
                    elif i == 1:
                        opt_b = opt
                    elif i == 2:
                        opt_c = opt
                    elif i == 3:
                        opt_d = opt

        corr = str(item.get("correct") or item.get("correct_option") or "A").strip().upper()
        if corr not in {"A", "B", "C", "D"}:
            corr = "A"

        h = compute_question_hash(q_text, opt_a, opt_b, opt_c, opt_d)
        q = TestQuestion(
            question_text=q_text,
            option_a=opt_a,
            option_b=opt_b,
            option_c=opt_c,
            option_d=opt_d,
            correct_option=corr,
            explanation=item.get("explanation"),
            topic=item.get("category") or "Umumiy",
            difficulty=Difficulty.MEDIUM.value,
            image_file_id=item.get("image_url"),
            status=TestStatus.APPROVED.value,
            content_hash=h,
            created_by=cfg.SUPERADMIN_ID,
            approved_by=cfg.SUPERADMIN_ID,
            approved_at=now,
            times_published=0,
        )
        session.add(q)
        created_count += 1

    await session.commit()
    logger.info(f"[seed] Muvaffaqiyatli {created_count} ta E-Avtomaktab savoli bazaga kiritildi!")
    return created_count
