"""Test savollari, e'lon qilingan testlar va javoblar repozitoriysi."""

from __future__ import annotations

import random
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import Difficulty, PublishedTestStatus, PublishMode, TestStatus
from app.models.test import PublishedTest, TestAnswer, TestAttempt, TestQuestion
from app.utils.security import compute_question_hash
from app.utils.timezone import now_utc


class TestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, question_id: int) -> Optional[TestQuestion]:
        return await self.session.get(TestQuestion, question_id)

    async def exists_by_hash(self, content_hash: str) -> bool:
        stmt = select(TestQuestion.id).where(TestQuestion.content_hash == content_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def create_question(
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
        status: TestStatus = TestStatus.PENDING,
    ) -> tuple[Optional[TestQuestion], bool]:
        """Yangi test qo'shadi. Qaytaradi: (question, created_bool). False bo'lsa dublikat."""
        content_hash = compute_question_hash(
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
        )
        if await self.exists_by_hash(content_hash):
            return None, False

        q = TestQuestion(
            question_text=question_text.strip(),
            option_a=option_a.strip(),
            option_b=option_b.strip(),
            option_c=option_c.strip(),
            option_d=option_d.strip(),
            correct_option=correct_option.strip().upper(),
            explanation=(explanation or "").strip() or None,
            topic=(topic or "Umumiy").strip(),
            difficulty=difficulty.value,
            image_file_id=image_file_id,
            status=status.value,
            content_hash=content_hash,
            created_by=created_by,
        )
        self.session.add(q)
        await self.session.flush()
        return q, True

    async def list_questions(
        self,
        *,
        status: Optional[TestStatus] = None,
        topic: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 8,
        offset: int = 0,
    ) -> tuple[list[TestQuestion], int]:
        conditions = []
        if status is not None:
            conditions.append(TestQuestion.status == status.value)
        if topic:
            conditions.append(TestQuestion.topic == topic)
        if search_query:
            pattern = f"%{search_query.strip()}%"
            conditions.append(
                or_(
                    TestQuestion.question_text.ilike(pattern),
                    TestQuestion.topic.ilike(pattern),
                    TestQuestion.option_a.ilike(pattern),
                    TestQuestion.option_b.ilike(pattern),
                    TestQuestion.option_c.ilike(pattern),
                    TestQuestion.option_d.ilike(pattern),
                )
            )

        count_stmt = select(func.count(TestQuestion.id)).where(*conditions)
        total = int((await self.session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(TestQuestion)
            .where(*conditions)
            .order_by(TestQuestion.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def list_all_for_export(self) -> list[TestQuestion]:
        stmt = select(TestQuestion).order_by(TestQuestion.id.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_topics(self, approved_only: bool = False) -> list[tuple[str, int]]:
        stmt = select(TestQuestion.topic, func.count(TestQuestion.id)).group_by(TestQuestion.topic)
        if approved_only:
            stmt = stmt.where(TestQuestion.status == TestStatus.APPROVED.value)
        stmt = stmt.order_by(TestQuestion.topic.asc())
        rows = (await self.session.execute(stmt)).all()
        return [(str(topic), int(cnt)) for topic, cnt in rows]

    async def approve(self, question_id: int, approved_by: int) -> Optional[TestQuestion]:
        q = await self.get_by_id(question_id)
        if not q:
            return None
        q.status = TestStatus.APPROVED.value
        q.approved_by = approved_by
        q.approved_at = now_utc()
        q.updated_at = now_utc()
        await self.session.flush()
        return q

    async def reject(self, question_id: int) -> Optional[TestQuestion]:
        q = await self.get_by_id(question_id)
        if not q:
            return None
        q.status = TestStatus.REJECTED.value
        q.updated_at = now_utc()
        await self.session.flush()
        return q

    async def delete_question(self, question_id: int) -> bool:
        q = await self.get_by_id(question_id)
        if not q:
            return False
        await self.session.delete(q)
        await self.session.flush()
        return True

    async def pick_next_approved_for_publish(
        self,
        *,
        selection_mode: str = "sequential",
        prevent_duplicates: bool = True,
    ) -> Optional[TestQuestion]:
        """Kanalga avtomatik chiqarish uchun faqat TASDIQLANGAN test tanlaydi."""
        base_cond = [TestQuestion.status == TestStatus.APPROVED.value]
        if prevent_duplicates:
            stmt = select(TestQuestion).where(*base_cond, TestQuestion.times_published == 0)
        else:
            stmt = select(TestQuestion).where(*base_cond)

        if selection_mode == "random":
            candidates = list((await self.session.execute(stmt)).scalars().all())
            if not candidates:
                return None
            return random.choice(candidates)

        # Sequential: eng kam chiqarilgan va ID si eng kichik savol
        stmt = stmt.order_by(TestQuestion.times_published.asc(), TestQuestion.id.asc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def pick_practice_questions(
        self,
        *,
        topic: Optional[str] = None,
        limit: int = 10,
    ) -> list[TestQuestion]:
        conditions = [TestQuestion.status == TestStatus.APPROVED.value]
        if topic:
            conditions.append(TestQuestion.topic == topic)
        stmt = select(TestQuestion).where(*conditions)
        all_items = list((await self.session.execute(stmt)).scalars().all())
        random.shuffle(all_items)
        return all_items[:limit]

    async def create_published_test(
        self,
        *,
        question: TestQuestion,
        channel_id: str,
        channel_message_id: int,
        mode: PublishMode,
        published_by: Optional[int] = None,
        poll_id: Optional[str] = None,
        reveal_at=None,
    ) -> PublishedTest:
        now = now_utc()
        pub = PublishedTest(
            question_id=question.id,
            channel_id=channel_id,
            channel_message_id=channel_message_id,
            poll_id=poll_id,
            mode=mode.value,
            status=PublishedTestStatus.ACTIVE.value,
            reveal_at=reveal_at,
            published_by=published_by,
            published_at=now,
        )
        question.times_published += 1
        question.last_published_at = now
        self.session.add(pub)
        await self.session.flush()
        return pub

    async def get_published_by_id(self, published_test_id: int) -> Optional[PublishedTest]:
        stmt = (
            select(PublishedTest)
            .options(selectinload(PublishedTest.question))
            .where(PublishedTest.id == published_test_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_published_by_poll_id(self, poll_id: str) -> Optional[PublishedTest]:
        stmt = (
            select(PublishedTest)
            .options(selectinload(PublishedTest.question))
            .where(PublishedTest.poll_id == poll_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def record_channel_inline_answer(
        self,
        *,
        published_test: PublishedTest,
        user_telegram_id: int,
        selected_option: str,
    ) -> tuple[bool, bool]:
        """
        Kanaldagi inline test javobini yozadi.
        Qaytaradi: (accepted_bool, is_correct_bool).
        Bir foydalanuvchi qayta javob bersa (False, False) qaytaradi.
        """
        existing_stmt = select(TestAnswer.id).where(
            TestAnswer.published_test_id == published_test.id,
            TestAnswer.user_telegram_id == user_telegram_id,
        )
        if (await self.session.execute(existing_stmt)).scalar_one_or_none() is not None:
            return False, False

        is_correct = selected_option.upper() == published_test.question.correct_option.upper()
        answer = TestAnswer(
            published_test_id=published_test.id,
            question_id=published_test.question_id,
            user_telegram_id=user_telegram_id,
            selected_option=selected_option.upper(),
            is_correct=is_correct,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(answer)
                await self.session.flush()
        except IntegrityError:
            return False, False

        published_test.total_votes += 1
        if is_correct:
            published_test.correct_votes += 1
        else:
            published_test.wrong_votes += 1
        await self.session.flush()
        return True, is_correct

    async def record_bot_attempt(
        self,
        *,
        user_id: int,
        question_id: int,
        selected_option: str,
        is_correct: bool,
        mode: str = "bot_practice",
    ) -> TestAttempt:
        attempt = TestAttempt(
            user_id=user_id,
            question_id=question_id,
            mode=mode,
            selected_option=selected_option.upper(),
            is_correct=is_correct,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def count_questions(self, status: Optional[TestStatus] = None) -> int:
        stmt = select(func.count(TestQuestion.id))
        if status is not None:
            stmt = stmt.where(TestQuestion.status == status.value)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def get_answer_totals(self) -> dict[str, int]:
        """Kanal (inline + quiz poll) va bot amaliyot javoblarining real yig'indisini qaytaradi."""
        pub_stmt = select(
            func.coalesce(func.sum(PublishedTest.total_votes), 0),
            func.coalesce(func.sum(PublishedTest.correct_votes), 0),
            func.coalesce(func.sum(PublishedTest.wrong_votes), 0),
        )
        pub_total, pub_correct, pub_wrong = (await self.session.execute(pub_stmt)).one()

        att_total_stmt = select(func.count(TestAttempt.id))
        att_correct_stmt = select(func.count(TestAttempt.id)).where(TestAttempt.is_correct.is_(True))
        att_total = int((await self.session.execute(att_total_stmt)).scalar_one() or 0)
        att_correct = int((await self.session.execute(att_correct_stmt)).scalar_one() or 0)
        att_wrong = att_total - att_correct

        return {
            "channel_total": int(pub_total or 0),
            "channel_correct": int(pub_correct or 0),
            "channel_wrong": int(pub_wrong or 0),
            "bot_total": att_total,
            "bot_correct": att_correct,
            "bot_wrong": att_wrong,
            "total": int(pub_total or 0) + att_total,
            "correct": int(pub_correct or 0) + att_correct,
            "wrong": int(pub_wrong or 0) + att_wrong,
        }
