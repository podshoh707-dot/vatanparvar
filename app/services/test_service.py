"""Testlarni boshqarish, kanalga chiqarish (Quiz Poll va Inline) hamda javoblarni hisoblash servisi."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Poll
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.enums import (
    Difficulty,
    JobType,
    PublishedTestStatus,
    PublishMode,
    TestStatus,
)
from app.models.test import PublishedTest, TestQuestion
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.system_repo import SystemRepository
from app.repositories.test_repo import TestRepository
from app.services.channel_service import ChannelService, explain_telegram_error
from app.services.settings_service import SettingsService
from app.utils.formatting import format_channel_inline_test, format_test_reveal_message
from app.utils.media import resolve_media_input
from app.utils.timezone import now_utc

logger = logging.getLogger(__name__)

OPTION_INDEX_MAP = {"A": 0, "B": 1, "C": 2, "D": 3}


def build_channel_inline_test_keyboard(published_test_id: int, options_count: int = 4) -> InlineKeyboardMarkup:
    """Kanaldagi inline test uchun dinamik variant tugmalari."""
    buttons = [
        InlineKeyboardButton(text="🅰️ A", callback_data=f"chtest:{published_test_id}:A"),
        InlineKeyboardButton(text="🅱️ B", callback_data=f"chtest:{published_test_id}:B"),
    ]
    rows: list[list[InlineKeyboardButton]] = [buttons]
    second_row: list[InlineKeyboardButton] = []
    if options_count >= 3:
        second_row.append(InlineKeyboardButton(text="🇨 C", callback_data=f"chtest:{published_test_id}:C"))
    if options_count >= 4:
        second_row.append(InlineKeyboardButton(text="🇩 D", callback_data=f"chtest:{published_test_id}:D"))
    if second_row:
        rows.append(second_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


class TestService:
    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        settings: Optional[Settings] = None,
    ) -> None:
        self.session = session
        self.bot = bot
        self.settings = settings or get_settings()
        self.test_repo = TestRepository(session)
        self.schedule_repo = ScheduleRepository(session)
        self.sys_repo = SystemRepository(session)
        self.settings_service = SettingsService(session)
        self.channel = ChannelService(bot, self.settings)

    async def create_test(
        self,
        *,
        question_text: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        correct_option: str,
        created_by: int,
        explanation: Optional[str] = None,
        topic: str = "Umumiy",
        difficulty: Difficulty = Difficulty.MEDIUM,
        image_file_id: Optional[str] = None,
        auto_approve: bool = False,
    ) -> tuple[Optional[TestQuestion], str]:
        corr = correct_option.strip().upper()
        if corr not in OPTION_INDEX_MAP:
            return None, "To'g'ri javob faqat A, B, C yoki D bo'lishi kerak."

        status = TestStatus.APPROVED if auto_approve else TestStatus.PENDING
        q, created = await self.test_repo.create_question(
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=corr,
            created_by=created_by,
            explanation=explanation,
            topic=topic,
            difficulty=difficulty,
            image_file_id=image_file_id,
            status=status,
        )
        if not created or q is None:
            return None, "Bu test bazada allaqachon mavjud (takroriy test rad etildi)."

        if auto_approve:
            q.approved_by = created_by
            q.approved_at = now_utc()
            await self.session.flush()

        await self.sys_repo.log_activity(
            admin_telegram_id=created_by,
            action="test_created",
            target_type="test_question",
            target_id=str(q.id),
            details={"topic": q.topic, "status": q.status},
        )
        return q, f"Test #{q.id} muvaffaqiyatli qo'shildi."

    async def approve_test(self, question_id: int, actor_id: int) -> tuple[bool, str]:
        q = await self.test_repo.approve(question_id, actor_id)
        if not q:
            return False, "Test topilmadi."
        await self.sys_repo.log_activity(
            admin_telegram_id=actor_id,
            action="test_approved",
            target_type="test_question",
            target_id=str(q.id),
        )
        return True, f"Test #{q.id} tasdiqlandi va avtomatik joylashtirishga tayyor."

    async def publish_test_to_channel(
        self,
        *,
        question: TestQuestion,
        mode: Optional[PublishMode] = None,
        published_by: Optional[int] = None,
        reveal_delay_minutes: Optional[int] = None,
    ) -> tuple[Optional[PublishedTest], str]:
        """Faqat TASDIQLANGAN testni kanalga Quiz Poll yoki Inline Keyboard rejimida joylashtiradi."""
        if question.status != TestStatus.APPROVED.value:
            return None, "Faqat admin tomonidan tasdiqlangan testlar kanalga joylashtirilishi mumkin."

        config = await self.settings_service.get_auto_publish_config()
        chosen_mode = mode or PublishMode(config["publish_mode"])
        delay = reveal_delay_minutes if reveal_delay_minutes is not None else int(config["reveal_delay_minutes"])

        target = self.settings.channel_target

        try:
            if chosen_mode == PublishMode.QUIZ_POLL:
                # Agar testda rasm bo'lsa, avval rasmni yuboramiz, keyin Quiz Poll
                if question.image_file_id:
                    await self.bot.send_photo(
                        chat_id=target,
                        photo=resolve_media_input(question.image_file_id),
                        caption=f"🚦 <b>AVTOVATANPARVAR TESTLARI</b>\n📚 Mavzu: <i>{question.topic}</i>",
                        parse_mode="HTML",
                    )

                poll_question = f"🚦 {question.question_text}"[:300]
                options = [
                    f"A) {question.option_a}"[:100],
                    f"B) {question.option_b}"[:100],
                ]
                if question.option_c and question.option_c.strip() not in ("", "-"):
                    options.append(f"C) {question.option_c}"[:100])
                if question.option_d and question.option_d.strip() not in ("", "-"):
                    options.append(f"D) {question.option_d}"[:100])

                correct_letter = question.correct_option.upper()
                correct_idx = OPTION_INDEX_MAP.get(correct_letter, 0)
                if correct_idx >= len(options):
                    correct_idx = 0

                explanation = (question.explanation or "")[:200] or None
                sent = await self.bot.send_poll(
                    chat_id=target,
                    question=poll_question,
                    options=options,
                    type="quiz",
                    correct_option_id=correct_idx,
                    explanation=explanation,
                    is_anonymous=True,
                )
                poll_id = sent.poll.id if sent.poll else None
                pub = await self.test_repo.create_published_test(
                    question=question,
                    channel_id=str(target),
                    channel_message_id=sent.message_id,
                    mode=PublishMode.QUIZ_POLL,
                    published_by=published_by,
                    poll_id=poll_id,
                )
            else:
                # Inline Keyboard rejimi
                text = format_channel_inline_test(question)
                # Avval vaqtinchalik PublishedTest yaratib real ID olamiz, so'ngra yuboramiz
                reveal_at = now_utc() + timedelta(minutes=max(1, delay)) if delay > 0 else None

                if question.image_file_id:
                    sent = await self.bot.send_photo(
                        chat_id=target,
                        photo=resolve_media_input(question.image_file_id),
                        caption=text,
                        parse_mode="HTML",
                    )
                else:
                    sent = await self.bot.send_message(
                        chat_id=target,
                        text=text,
                        parse_mode="HTML",
                    )

                pub = await self.test_repo.create_published_test(
                    question=question,
                    channel_id=str(target),
                    channel_message_id=sent.message_id,
                    mode=PublishMode.INLINE,
                    published_by=published_by,
                    reveal_at=reveal_at,
                )

                options_count = 2
                if question.option_c and question.option_c.strip() not in ("", "-"):
                    options_count = 3
                    if question.option_d and question.option_d.strip() not in ("", "-"):
                        options_count = 4

                # Inline tugmalarni real pub.id bilan biriktiramiz
                await self.bot.edit_message_reply_markup(
                    chat_id=target,
                    message_id=sent.message_id,
                    reply_markup=build_channel_inline_test_keyboard(pub.id, options_count=options_count),
                )

                if reveal_at is not None:
                    await self.schedule_repo.enqueue(
                        job_type=JobType.REVEAL_TEST_ANSWER,
                        reference_id=pub.id,
                        idempotency_key=f"reveal_test:{pub.id}",
                        run_at=reveal_at,
                        payload_json={"published_test_id": pub.id},
                    )

            if published_by:
                await self.sys_repo.log_activity(
                    admin_telegram_id=published_by,
                    action="test_published",
                    target_type="published_test",
                    target_id=str(pub.id),
                    details={"question_id": question.id, "mode": chosen_mode.value},
                )
            return pub, f"Test #{question.id} kanalga muvaffaqiyatli chiqarildi ({chosen_mode.value})."
        except Exception as exc:
            logger.exception("Testni kanalga chiqarishda xatolik: %s", exc)
            return None, explain_telegram_error(exc)

    async def publish_next_auto_test(self, published_by: Optional[int] = None) -> tuple[Optional[PublishedTest], str]:
        """Sozlamalar asosida navbatdagi tasdiqlangan testni tanlab kanalga chiqaradi."""
        config = await self.settings_service.get_auto_publish_config()
        question = await self.test_repo.pick_next_approved_for_publish(
            selection_mode=config["selection_mode"],
            prevent_duplicates=config["prevent_duplicates"],
        )
        if not question:
            return None, "Joylashtirish uchun mos tasdiqlangan test topilmadi."
        return await self.publish_test_to_channel(
            question=question,
            mode=PublishMode(config["publish_mode"]),
            published_by=published_by,
            reveal_delay_minutes=int(config["reveal_delay_minutes"]),
        )

    async def reveal_published_test(self, published_test_id: int) -> tuple[bool, str]:
        """Inline testning to'g'ri javobi, izohi va natijalarini kanalga e'lon qiladi."""
        pub = await self.test_repo.get_published_by_id(published_test_id)
        if not pub:
            return False, "E'lon qilingan test topilmadi."
        if pub.status == PublishedTestStatus.REVEALED.value:
            return True, "Bu testning javobi allaqachon e'lon qilingan."

        reveal_text = format_test_reveal_message(
            pub.question,
            total_votes=pub.total_votes,
            correct_votes=pub.correct_votes,
            wrong_votes=pub.wrong_votes,
        )
        target: int | str = int(pub.channel_id) if pub.channel_id.lstrip("-").isdigit() else pub.channel_id
        try:
            sent = await self.bot.send_message(
                chat_id=target,
                text=reveal_text,
                parse_mode="HTML",
                reply_to_message_id=pub.channel_message_id,
            )
            pub.status = PublishedTestStatus.REVEALED.value
            pub.revealed_at = now_utc()
            pub.reveal_message_id = sent.message_id
            await self.session.flush()
            return True, "To'g'ri javob va izoh kanalga e'lon qilindi."
        except Exception as exc:
            return False, explain_telegram_error(exc)

    async def sync_quiz_poll_update(self, poll: Poll) -> bool:
        """Telegram Quiz Poll natijalarini real vaqtda bazaga yangilaydi."""
        pub = await self.test_repo.get_published_by_poll_id(poll.id)
        if not pub:
            return False
        total = int(poll.total_voter_count or 0)
        correct_idx = poll.correct_option_id
        correct_votes = 0
        if correct_idx is not None and 0 <= correct_idx < len(poll.options):
            correct_votes = int(poll.options[correct_idx].voter_count or 0)
        wrong_votes = max(0, total - correct_votes)

        pub.total_votes = total
        pub.correct_votes = correct_votes
        pub.wrong_votes = wrong_votes
        await self.session.flush()
        return True
