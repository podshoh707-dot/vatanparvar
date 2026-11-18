"""Xavfsizlik utilitalari: HTML himoya, token yashirish, hash va webhook tekshiruvi."""

from __future__ import annotations

import hashlib
import hmac
import html
import re
from urllib.parse import urlparse


def escape_html(text: str | None) -> str:
    """Foydalanuvchi matnini Telegram HTML uchun xavfsiz qiladi."""
    if not text:
        return ""
    return html.escape(str(text), quote=False)


def verify_secret_token(provided: str | None, expected: str) -> bool:
    """Timing-attack'ga chidamli maxfiy kalit tekshiruvi."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def compute_question_hash(
    question: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
) -> str:
    """Takroriy testlarni aniqlash uchun normallashtirilgan SHA-256 hash."""

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    payload = "|".join(
        [
            _norm(question),
            _norm(option_a),
            _norm(option_b),
            _norm(option_c),
            _norm(option_d),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_valid_http_url(url: str) -> bool:
    """Inline tugma uchun faqat xavfsiz http/https/tg havolalarga ruxsat beradi."""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme in {"http", "https"} and bool(parsed.netloc):
            return True
        if parsed.scheme == "tg" and bool(parsed.netloc or parsed.path):
            return True
        return False
    except Exception:
        return False


def parse_inline_buttons_text(raw_text: str) -> tuple[list[dict[str, str]], list[str]]:
    """
    Har bir qatordan inline tugmalarni ajratib oladi.
    Format: Tugma matni | https://example.com
    Qaytaradi: (tugmalar ro'yxati, xatolar ro'yxati)
    """
    buttons: list[dict[str, str]] = []
    errors: list[str] = []

    for idx, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if "|" not in stripped:
            errors.append(f"{idx}-qator: '|' ajratuvchisi topilmadi.")
            continue
        label, url = [part.strip() for part in stripped.split("|", 1)]
        if not label or len(label) > 64:
            errors.append(f"{idx}-qator: tugma matni 1-64 belgi orasida bo'lishi kerak.")
            continue
        if not is_valid_http_url(url):
            errors.append(f"{idx}-qator: noto'g'ri havola ({url}). Faqat https://, http:// yoki tg://.")
            continue
        buttons.append({"text": label, "url": url})

    return buttons, errors


def mask_sensitive_text(message: str, secrets: list[str]) -> str:
    """Loglarda token, parol va webhook secret chiqib ketishini oldini oladi."""
    masked = message
    for secret in secrets:
        if secret and len(secret) >= 6:
            masked = masked.replace(secret, "***REDACTED***")
    # Telegram bot token patterni: 12345678:AA...
    masked = re.sub(r"\b\d{6,12}:[A-Za-z0-9_-]{25,}\b", "***BOT_TOKEN_REDACTED***", masked)
    # PostgreSQL parolini yashirish: ://user:pass@host
    masked = re.sub(r"(://[^:\s/]+:)([^@\s/]+)(@)", r"\1***REDACTED***\3", masked)
    return masked
