"""Telegram kanal bilan xavfsiz ishlash servisi (huquqlar, yuborish, tahrirlash, o'chirish)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import Settings, get_settings
from app.models.enums import ContentType
from app.utils.media import resolve_media_input

logger = logging.getLogger(__name__)


def build_url_keyboard(buttons_json: Optional[list[dict[str, Any]]]) -> Optional[InlineKeyboardMarkup]:
    """JSON ro'yxatdan Telegram inline URL tugmalarini yasaydi."""
    if not buttons_json:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    for btn in buttons_json:
        text = str(btn.get("text", "")).strip()
        url = str(btn.get("url", "")).strip()
        if text and url:
            rows.append([InlineKeyboardButton(text=text, url=url)])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def explain_telegram_error(exc: Exception) -> str:
    """Telegram API xatolarini admin uchun tushunarli o'zbek tiliga tarjima qiladi."""
    msg = str(exc).lower()
    if "not enough rights" in msg or "have no rights" in msg or "chat_admin_required" in msg:
        return (
            "Botda kanalda bu amalni bajarish uchun administrator huquqi yetarli emas. "
            "Botga 'Post joylash', 'Xabarlarni tahrirlash' va 'Xabarlarni o'chirish' huquqlarini bering."
        )
    if "message to edit not found" in msg or "message to delete not found" in msg:
        return "Kanalda bu xabar topilmadi (ehtimol u qo'lda o'chirilgan)."
    if "message can't be deleted" in msg:
        return (
            "Telegram API cheklovi sababli bu xabarni o'chirib bo'lmaydi "
            "(masalan, 48 soatdan oshgan yoki botda o'chirish huquqi yo'q)."
        )
    if "message can't be edited" in msg:
        return "Telegram API cheklovi sababli bu xabarni tahrirlab bo'lmaydi."
    if "message is not modified" in msg:
        return "Xabar matni avvalgi holat bilan bir xil, o'zgarish topilmadi."
    if "can't parse entities" in msg:
        return "HTML teglarida xatolik bor. Ochilgan teglar (<b>, <i>, <a>) to'g'ri yopilganini tekshiring."
    if "chat not found" in msg:
        return "Kanal topilmadi. .env faylidagi CHANNEL_ID va bot kanalga qo'shilganini tekshiring."
    if "bot was kicked" in msg or "forbidden" in msg:
        return "Bot kanaldan chiqarib yuborilgan yoki kanalga kirish ruxsati yo'q."
    return f"Telegram API xatoligi: {exc}"


class ChannelService:
    def __init__(self, bot: Bot, settings: Optional[Settings] = None) -> None:
        self.bot = bot
        self.settings = settings or get_settings()

    async def check_bot_admin_rights(self) -> tuple[bool, str, dict[str, bool]]:
        """Botning kanaldagi administratorlik huquqlarini tekshiradi."""
        rights = {
            "is_admin": False,
            "can_post_messages": False,
            "can_edit_messages": False,
            "can_delete_messages": False,
        }
        try:
            me = await self.bot.get_me()
            member = await self.bot.get_chat_member(
                chat_id=self.settings.channel_target,
                user_id=me.id,
            )
            status = getattr(member, "status", "")
            if status in {"creator", "administrator"}:
                rights["is_admin"] = True
                if status == "creator":
                    rights["can_post_messages"] = True
                    rights["can_edit_messages"] = True
                    rights["can_delete_messages"] = True
                else:
                    rights["can_post_messages"] = bool(getattr(member, "can_post_messages", False))
                    rights["can_edit_messages"] = bool(getattr(member, "can_edit_messages", False))
                    rights["can_delete_messages"] = bool(getattr(member, "can_delete_messages", False))

            if not rights["is_admin"]:
                return False, "Bot kanalda administrator emas.", rights
            if not rights["can_post_messages"]:
                return False, "Botda kanalga post joylash (can_post_messages) huquqi yo'q.", rights
            return True, "Bot kanal administratorlik huquqlariga ega.", rights
        except (TelegramAPIError, Exception) as exc:
            return False, explain_telegram_error(exc), rights

    async def send_content(
        self,
        *,
        chat_id: int | str,
        content_type: ContentType | str,
        text: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[list[dict[str, Any]]] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> Message:
        """Matn, rasm, video yoki hujjatni xavfsiz HTML formatda yuboradi."""
        ctype = ContentType(content_type)
        markup = reply_markup or build_url_keyboard(buttons_json)

        if ctype == ContentType.TEXT:
            return await self.bot.send_message(
                chat_id=chat_id,
                text=text or "",
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=False,
            )
        media_input = resolve_media_input(media_file_id) if media_file_id else ""
        if ctype == ContentType.PHOTO:
            return await self.bot.send_photo(
                chat_id=chat_id,
                photo=media_input,
                caption=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        if ctype == ContentType.VIDEO:
            return await self.bot.send_video(
                chat_id=chat_id,
                video=media_input,
                caption=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        if ctype == ContentType.DOCUMENT:
            return await self.bot.send_document(
                chat_id=chat_id,
                document=media_input,
                caption=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        raise ValueError(f"Qo'llab-quvvatlanmaydigan kontent turi: {content_type}")

    async def edit_channel_message(
        self,
        *,
        channel_id: int | str,
        message_id: int,
        content_type: ContentType | str,
        new_text: str,
        buttons_json: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[bool, str]:
        """Bot tomonidan joylangan kanal xabarini tahrirlaydi."""
        ctype = ContentType(content_type)
        markup = build_url_keyboard(buttons_json)
        try:
            if ctype == ContentType.TEXT:
                await self.bot.edit_message_text(
                    chat_id=channel_id,
                    message_id=message_id,
                    text=new_text,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            else:
                await self.bot.edit_message_caption(
                    chat_id=channel_id,
                    message_id=message_id,
                    caption=new_text,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            return True, "Kanaldagi xabar muvaffaqiyatli tahrirlandi."
        except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as exc:
            logger.warning("Kanal xabarini tahrirlashda xatolik: %s", exc)
            return False, explain_telegram_error(exc)

    async def delete_channel_message(
        self,
        *,
        channel_id: int | str,
        message_id: int,
    ) -> tuple[bool, str]:
        """Bot tomonidan joylangan kanal xabarini o'chiradi."""
        try:
            await self.bot.delete_message(chat_id=channel_id, message_id=message_id)
            return True, "Post kanaldan muvaffaqiyatli o'chirildi."
        except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as exc:
            logger.warning("Kanal xabarini o'chirishda xatolik: %s", exc)
            return False, explain_telegram_error(exc)

    async def get_channel_subscribers_count(self) -> Optional[int]:
        """Kanal obunachilari sonini Telegram API orqali oladi (real ma'lumot)."""
        try:
            return int(await self.bot.get_chat_member_count(chat_id=self.settings.channel_target))
        except Exception as exc:
            logger.warning("Kanal obunachilari sonini olib bo'lmadi: %s", exc)
            return None
