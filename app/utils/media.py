"""Media va rasmlarni xavfsiz yuklash (local fayllar va Telegram file_id) yordamchilari."""

from __future__ import annotations

import os
from typing import Any
from aiogram.types import FSInputFile


def resolve_media_input(media_val: Any) -> Any:
    """Agar media_val lokal diskdagi fayl yo'li bo'lsa, FSInputFile qaytaradi.
    Aks holda (file_id yoki URL) o'z holicha qaytaradi.
    """
    if not media_val or not isinstance(media_val, str):
        return media_val
    cleaned = media_val.strip()
    if os.path.isfile(cleaned):
        return FSInputFile(cleaned)
    # Loyiha ildiziga nisbatan tekshirish
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel_path = os.path.join(base_dir, cleaned.lstrip("/\\"))
    if os.path.isfile(rel_path):
        return FSInputFile(rel_path)
    return cleaned
