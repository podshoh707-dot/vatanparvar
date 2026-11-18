"""Maxfiy ma'lumotlarni yashiruvchi professional loglash konfiguratsiyasi."""

from __future__ import annotations

import logging
import sys

from app.utils.security import mask_sensitive_text


class SecretMaskingFilter(logging.Filter):
    """Log xabarlari va argumentlaridan maxfiy kalitlarni olib tashlaydi."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
            masked = mask_sensitive_text(rendered, self._secrets)
            record.msg = masked
            record.args = ()
            if record.exc_text:
                record.exc_text = mask_sensitive_text(record.exc_text, self._secrets)
        except Exception:
            pass
        return True


def setup_logging(level_name: str = "INFO", secrets: list[str] | None = None) -> None:
    """Strukturalangan va xavfsiz logging sozlaydi."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    secret_filter = SecretMaskingFilter(secrets or [])

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(secret_filter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Shovqinli kutubxonalarni kamaytirish
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
