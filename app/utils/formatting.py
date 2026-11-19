"""Xabar va test matnlarini chiroyli formatlash utilitalari."""

from __future__ import annotations

from typing import Any, Optional

from app.utils.security import escape_html

DIFFICULTY_LABELS = {
    "easy": "🟢 Oson",
    "medium": "🟡 O'rta",
    "hard": "🔴 Qiyin",
}

STATUS_LABELS = {
    "pending": "⏳ Tasdiqlanmagan",
    "approved": "✅ Tasdiqlangan",
    "rejected": "❌ Rad etilgan",
    "archived": "📦 Arxivlangan",
    "draft": "📝 Qoralama",
    "scheduled": "📅 Rejalashtirilgan",
    "published": "✅ Joylangan",
    "failed": "⚠️ Xatolik",
    "deleted": "🗑 O'chirilgan",
    "paused": "⏸ To'xtatilgan",
}

ROLE_LABELS = {
    "SUPER_ADMIN": "👑 Super Admin",
    "ADMIN": "🛡 Admin",
    "TEST_MANAGER": "🚦 Test menejeri",
    "EDITOR": "✏️ Muharrir",
    "STATISTIC_VIEWER": "📊 Statistika kuzatuvchisi",
}


def format_channel_inline_test(question: Any) -> str:
    """Kanal uchun inline test matni (Master Prompt standarti bo'yicha)."""
    options_lines = [
        f"A) {escape_html(question.option_a)}",
        f"B) {escape_html(question.option_b)}",
    ]
    if question.option_c and question.option_c.strip() not in ("", "-"):
        options_lines.append(f"C) {escape_html(question.option_c)}")
    if question.option_d and question.option_d.strip() not in ("", "-"):
        options_lines.append(f"D) {escape_html(question.option_d)}")
    opts_str = "\n".join(options_lines)
    return (
        "🚦 <b>AVTOVATANPARVAR TESTLARI</b>\n\n"
        f"❓ <b>{escape_html(question.question_text)}</b>\n\n"
        f"{opts_str}\n\n"
        f"📚 Mavzu: <i>{escape_html(question.topic)}</i>\n"
        "👇 <b>Javobingizni tanlang!</b>"
    )


def format_test_reveal_message(
    question: Any,
    total_votes: int = 0,
    correct_votes: int = 0,
    wrong_votes: int = 0,
) -> str:
    """Testning to'g'ri javobi va izohi e'loni."""
    correct_letter = question.correct_option.upper()
    correct_map = {
        "A": question.option_a,
        "B": question.option_b,
        "C": question.option_c,
        "D": question.option_d,
    }
    correct_text = correct_map.get(correct_letter, "")
    accuracy = round((correct_votes / total_votes) * 100, 1) if total_votes > 0 else 0.0

    lines = [
        "✅ <b>TO'G'RI JAVOB VA IZOH</b>",
        "",
        f"❓ <b>Savol:</b> {escape_html(question.question_text)}",
        f"🎯 <b>To'g'ri javob:</b> <b>{correct_letter})</b> {escape_html(correct_text)}",
    ]
    if question.explanation:
        lines.extend(["", f"💡 <b>Izoh:</b> {escape_html(question.explanation)}"])
    if total_votes > 0:
        lines.extend(
            [
                "",
                "📊 <b>Ishtirokchilar natijasi:</b>",
                f"👥 Jami javoblar: <b>{total_votes}</b>",
                f"✅ To'g'ri: <b>{correct_votes}</b> ({accuracy}%)",
                f"❌ Noto'g'ri: <b>{wrong_votes}</b>",
            ]
        )
    return "\n".join(lines)


def format_test_card_admin(question: Any) -> str:
    """Admin panelda bitta testning batafsil ko'rinishi."""
    diff = DIFFICULTY_LABELS.get(question.difficulty, question.difficulty)
    status = STATUS_LABELS.get(question.status, question.status)
    has_img = "Ha 🖼" if question.image_file_id else "Yo'q"
    options_lines = [
        f"A) {escape_html(question.option_a)}",
        f"B) {escape_html(question.option_b)}",
    ]
    if question.option_c and question.option_c.strip() not in ("", "-"):
        options_lines.append(f"C) {escape_html(question.option_c)}")
    if question.option_d and question.option_d.strip() not in ("", "-"):
        options_lines.append(f"D) {escape_html(question.option_d)}")
    opts_str = "\n".join(options_lines)
    return (
        f"🚦 <b>Test #{question.id}</b> | {status}\n"
        f"📚 Mavzu: <b>{escape_html(question.topic)}</b> | {diff}\n"
        f"🖼 Rasm: {has_img} | 📢 Chiqarilgan: {question.times_published} marta\n\n"
        f"❓ <b>{escape_html(question.question_text)}</b>\n\n"
        f"{opts_str}\n\n"
        f"✅ To'g'ri javob: <b>{question.correct_option}</b>\n"
        f"💡 Izoh: {escape_html(question.explanation or 'Kiritilmagan')}"
    )


def format_user_practice_question(question: Any, index: int, total: int) -> str:
    """Oddiy foydalanuvchi uchun test savoli ko'rinishi."""
    options_lines = [
        f"A) {escape_html(question.option_a)}",
        f"B) {escape_html(question.option_b)}",
    ]
    if question.option_c and question.option_c.strip() not in ("", "-"):
        options_lines.append(f"C) {escape_html(question.option_c)}")
    if question.option_d and question.option_d.strip() not in ("", "-"):
        options_lines.append(f"D) {escape_html(question.option_d)}")
    opts_str = "\n".join(options_lines)
    return (
        f"🚦 <b>Test {index}/{total}</b> — <i>{escape_html(question.topic)}</i>\n\n"
        f"❓ <b>{escape_html(question.question_text)}</b>\n\n"
        f"{opts_str}\n\n"
        "Javob variantini tanlang:"
    )


def truncate_text(text: Optional[str], max_len: int = 80) -> str:
    """Uzun matnlarni ro'yxatlar uchun qisqartiradi."""
    if not text:
        return "(matnsiz)"
    clean = " ".join(text.split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1] + "…"
