"""Haqiqiy statistika yig'ish va Matplotlib grafik yaratish servisi."""

from __future__ import annotations

import io
from collections import Counter
from datetime import timedelta
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.enums import PostStatus, PostType, TestStatus
from app.repositories.post_repo import PostRepository
from app.repositories.system_repo import SystemRepository
from app.repositories.test_repo import TestRepository
from app.repositories.user_repo import UserRepository
from app.services.channel_service import ChannelService
from app.utils.timezone import now_local, now_utc, to_local


class StatisticsService:
    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        settings: Optional[Settings] = None,
    ) -> None:
        self.session = session
        self.bot = bot
        self.settings = settings or get_settings()
        self.user_repo = UserRepository(session)
        self.post_repo = PostRepository(session)
        self.test_repo = TestRepository(session)
        self.sys_repo = SystemRepository(session)
        self.channel = ChannelService(bot, self.settings)

    async def collect(self) -> dict[str, Any]:
        """Faqat bazadagi va Telegram API orqali olingan real ma'lumotlarni yig'adi."""
        now = now_utc()
        tz = self.settings.TIMEZONE
        local_now = now_local(tz)

        start_today_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_today_utc = start_today_local.astimezone(now.tzinfo)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total_users = await self.user_repo.count_total()
        active_users = await self.user_repo.count_active()
        new_today = await self.user_repo.count_since(start_today_utc)
        new_week = await self.user_repo.count_since(week_ago)
        new_month = await self.user_repo.count_since(month_ago)

        channel_subscribers = await self.channel.get_channel_subscribers_count()

        posts_published = await self.post_repo.count_by_type_and_status(PostType.POST, PostStatus.PUBLISHED)
        posts_scheduled = await self.post_repo.count_by_type_and_status(PostType.POST, PostStatus.SCHEDULED)
        ads_published = await self.post_repo.count_by_type_and_status(PostType.AD, PostStatus.PUBLISHED)
        ads_scheduled = await self.post_repo.count_by_type_and_status(PostType.AD, PostStatus.SCHEDULED)

        tests_total = await self.test_repo.count_questions()
        tests_approved = await self.test_repo.count_questions(TestStatus.APPROVED)
        tests_pending = await self.test_repo.count_questions(TestStatus.PENDING)

        answers = await self.test_repo.get_answer_totals()
        admin_activity = await self.sys_repo.admin_activity_summary(limit=5)

        # Oxirgi 7 kunlik foydalanuvchi o'sishi
        created_dates = await self.user_repo.list_created_since(week_ago)
        day_counter: Counter[str] = Counter()
        for dt in created_dates:
            local_dt = to_local(dt, tz)
            if local_dt:
                day_counter[local_dt.strftime("%d.%m")] += 1

        daily_labels: list[str] = []
        daily_counts: list[int] = []
        for delta in range(6, -1, -1):
            day = local_now - timedelta(days=delta)
            label = day.strftime("%d.%m")
            daily_labels.append(label)
            daily_counts.append(day_counter.get(label, 0))

        return {
            "total_users": total_users,
            "active_users": active_users,
            "new_today": new_today,
            "new_week": new_week,
            "new_month": new_month,
            "channel_subscribers": channel_subscribers,
            "posts_published": posts_published,
            "posts_scheduled": posts_scheduled,
            "ads_published": ads_published,
            "ads_scheduled": ads_scheduled,
            "tests_total": tests_total,
            "tests_approved": tests_approved,
            "tests_pending": tests_pending,
            "answers": answers,
            "admin_activity": admin_activity,
            "daily_labels": daily_labels,
            "daily_counts": daily_counts,
        }

    def format_report(self, stats: dict[str, Any]) -> str:
        """Statistika hisobotini chiroyli o'zbek lotin matniga aylantiradi."""
        subs = (
            f"<b>{stats['channel_subscribers']}</b>"
            if stats["channel_subscribers"] is not None
            else "<i>(Telegram API orqali olinmadi — bot kanal admini ekanini tekshiring)</i>"
        )
        ans = stats["answers"]
        acc = round((ans["correct"] / ans["total"]) * 100, 1) if ans["total"] > 0 else 0.0

        admin_lines = []
        for aid, cnt in stats["admin_activity"]:
            admin_lines.append(f"  • ID <code>{aid}</code>: <b>{cnt}</b> ta amal")
        admin_block = "\n".join(admin_lines) if admin_lines else "  • Hali faoliyat qayd etilmagan"

        return (
            "📊 <b>AVTOVATANPARVAR TESTLARI — STATISTIKA</b>\n\n"
            f"📢 <b>Kanal ({self.settings.CHANNEL_USERNAME}):</b>\n"
            f"  • Obunachilar: {subs}\n\n"
            "👥 <b>Bot foydalanuvchilari:</b>\n"
            f"  • Jami: <b>{stats['total_users']}</b> (faol: {stats['active_users']})\n"
            f"  • Bugun qo'shilgan: <b>+{stats['new_today']}</b>\n"
            f"  • Oxirgi 7 kun: <b>+{stats['new_week']}</b>\n"
            f"  • Oxirgi 30 kun: <b>+{stats['new_month']}</b>\n\n"
            "📝 <b>Postlar va reklamalar:</b>\n"
            f"  • Joylangan postlar: <b>{stats['posts_published']}</b> | Rejalashtirilgan: <b>{stats['posts_scheduled']}</b>\n"
            f"  • Joylangan reklamalar: <b>{stats['ads_published']}</b> | Rejalashtirilgan: <b>{stats['ads_scheduled']}</b>\n\n"
            "🚦 <b>Testlar va natijalar:</b>\n"
            f"  • Jami testlar: <b>{stats['tests_total']}</b> (✅ {stats['tests_approved']} | ⏳ {stats['tests_pending']})\n"
            f"  • Jami javoblar: <b>{ans['total']}</b> (kanal: {ans['channel_total']}, bot: {ans['bot_total']})\n"
            f"  • To'g'ri javoblar: <b>{ans['correct']}</b> ({acc}%)\n"
            f"  • Noto'g'ri javoblar: <b>{ans['wrong']}</b>\n\n"
            "🛡 <b>Adminlar faoliyati (TOP-5):</b>\n"
            f"{admin_block}"
        )

    @staticmethod
    def build_chart_png(stats: dict[str, Any]) -> bytes:
        """7 kunlik o'sish va test natijalari bo'yicha 2 panelli PNG grafik yaratadi."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=130)
        fig.patch.set_facecolor("#F8FAFC")

        # 1-grafik: Oxirgi 7 kunlik yangi foydalanuvchilar
        labels = stats["daily_labels"]
        counts = stats["daily_counts"]
        ax1.bar(labels, counts, color="#2563EB", width=0.58)
        ax1.set_title("Oxirgi 7 kun: yangi foydalanuvchilar", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Soni")
        ax1.grid(axis="y", linestyle="--", alpha=0.35)
        ax1.set_facecolor("#FFFFFF")

        # 2-grafik: Test javoblari taqsimoti
        ans = stats["answers"]
        correct = ans["correct"]
        wrong = ans["wrong"]
        ax2.set_facecolor("#FFFFFF")
        if correct + wrong > 0:
            ax2.pie(
                [correct, wrong],
                labels=["To'g'ri", "Noto'g'ri"],
                colors=["#16A34A", "#DC2626"],
                autopct="%1.1f%%",
                startangle=90,
            )
            ax2.set_title("Test javoblari aniqligi", fontsize=11, fontweight="bold")
        else:
            ax2.text(0.5, 0.5, "Hali javoblar yo'q", ha="center", va="center", fontsize=11, color="#64748B")
            ax2.set_title("Test javoblari aniqligi", fontsize=11, fontweight="bold")
            ax2.axis("off")

        fig.suptitle("AVTOVATANPARVAR TESTLARI — Statistika", fontsize=13, fontweight="bold")
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()
