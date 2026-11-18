"""Postlar va reklamalar biznes servisi."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.enums import ContentType, JobType, PostStatus, PostType
from app.models.post import Post
from app.repositories.post_repo import PostRepository
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.system_repo import SystemRepository
from app.services.channel_service import ChannelService, explain_telegram_error
from app.utils.timezone import now_utc


class PostService:
    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        settings: Optional[Settings] = None,
    ) -> None:
        self.session = session
        self.bot = bot
        self.settings = settings or get_settings()
        self.post_repo = PostRepository(session)
        self.schedule_repo = ScheduleRepository(session)
        self.sys_repo = SystemRepository(session)
        self.channel = ChannelService(bot, self.settings)

    async def publish_now(
        self,
        *,
        created_by: int,
        post_type: PostType,
        content_type: ContentType,
        text: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[list[dict[str, Any]]] = None,
        title: Optional[str] = None,
    ) -> tuple[Optional[Post], str]:
        """Post yoki reklamani darhol kanalga joylashtiradi va bazaga saqlaydi."""
        has_rights, rights_msg, _ = await self.channel.check_bot_admin_rights()
        if not has_rights:
            return None, rights_msg

        post = await self.post_repo.create(
            created_by=created_by,
            post_type=post_type,
            content_type=content_type,
            title=title,
            text=text,
            media_file_id=media_file_id,
            buttons_json=buttons_json,
            status=PostStatus.DRAFT,
            channel_id=str(self.settings.channel_target),
        )

        ok, msg = await self.execute_publish_existing(post)
        if not ok:
            return None, msg

        await self.sys_repo.log_activity(
            admin_telegram_id=created_by,
            action=f"{post_type.value}_published",
            target_type=post_type.value,
            target_id=str(post.id),
            details={"message_id": post.channel_message_id},
        )
        return post, msg

    async def execute_publish_existing(self, post: Post) -> tuple[bool, str]:
        """Mavjud Post obyektini kanalga yuboradi (darhol yoki scheduler orqali)."""
        if post.status == PostStatus.PAUSED.value:
            return False, "Bu reklama/post to'xtatilgan holatda."
        if post.status == PostStatus.DELETED.value:
            return False, "Bu post o'chirilgan."

        target_channel: int | str = self.settings.channel_target
        if post.channel_id:
            raw = str(post.channel_id).strip()
            target_channel = int(raw) if raw.lstrip("-").isdigit() else raw

        try:
            sent = await self.channel.send_content(
                chat_id=target_channel,
                content_type=post.content_type,
                text=post.text,
                media_file_id=post.media_file_id,
                buttons_json=post.buttons_json,
            )
            await self.post_repo.mark_published(
                post,
                channel_id=str(target_channel),
                channel_message_id=sent.message_id,
            )
            return True, f"Muvaffaqiyatli kanalga joylashtirildi (Xabar ID: #{sent.message_id})."
        except Exception as exc:
            err = explain_telegram_error(exc)
            await self.post_repo.mark_failed(post, err)
            return False, err

    async def schedule_post(
        self,
        *,
        created_by: int,
        post_type: PostType,
        content_type: ContentType,
        run_at: datetime,
        text: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[list[dict[str, Any]]] = None,
        title: Optional[str] = None,
    ) -> tuple[Post, str]:
        """Post yoki reklamani PostgreSQL scheduled_jobs orqali rejalashtiradi."""
        post = await self.post_repo.create(
            created_by=created_by,
            post_type=post_type,
            content_type=content_type,
            title=title,
            text=text,
            media_file_id=media_file_id,
            buttons_json=buttons_json,
            status=PostStatus.SCHEDULED,
            channel_id=str(self.settings.channel_target),
            scheduled_at=run_at,
        )

        job_type = JobType.PUBLISH_AD if post_type == PostType.AD else JobType.PUBLISH_POST
        idem_key = f"{job_type.value}:{post.id}:{int(run_at.timestamp())}"
        await self.schedule_repo.enqueue(
            job_type=job_type,
            reference_id=post.id,
            idempotency_key=idem_key,
            run_at=run_at,
            payload_json={"post_id": post.id, "post_type": post_type.value},
        )
        await self.sys_repo.log_activity(
            admin_telegram_id=created_by,
            action=f"{post_type.value}_scheduled",
            target_type=post_type.value,
            target_id=str(post.id),
            details={"run_at": run_at.isoformat()},
        )
        return post, "Muvaffaqiyatli rejalashtirildi."

    async def edit_post(
        self,
        *,
        post_id: int,
        editor_id: int,
        new_text: str,
        new_buttons: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[bool, str]:
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            return False, "Post topilmadi."
        if post.status == PostStatus.DELETED.value:
            return False, "O'chirilgan postni tahrirlab bo'lmaydi."

        buttons_to_use = post.buttons_json if new_buttons is None else new_buttons

        if post.status == PostStatus.PUBLISHED.value and post.channel_message_id:
            target: int | str = self.settings.channel_target
            if post.channel_id:
                raw = str(post.channel_id).strip()
                target = int(raw) if raw.lstrip("-").isdigit() else raw

            ok, msg = await self.channel.edit_channel_message(
                channel_id=target,
                message_id=post.channel_message_id,
                content_type=post.content_type,
                new_text=new_text,
                buttons_json=buttons_to_use,
            )
            if not ok:
                return False, msg

        post.text = new_text
        post.buttons_json = buttons_to_use
        post.updated_by = editor_id
        post.updated_at = now_utc()
        await self.session.flush()

        await self.sys_repo.log_activity(
            admin_telegram_id=editor_id,
            action=f"{post.post_type}_edited",
            target_type=post.post_type,
            target_id=str(post.id),
        )
        return True, "Post muvaffaqiyatli tahrirlandi."

    async def delete_post(self, *, post_id: int, actor_id: int) -> tuple[bool, str]:
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            return False, "Post topilmadi."

        note = ""
        if post.status == PostStatus.PUBLISHED.value and post.channel_message_id:
            target: int | str = self.settings.channel_target
            if post.channel_id:
                raw = str(post.channel_id).strip()
                target = int(raw) if raw.lstrip("-").isdigit() else raw

            ok, msg = await self.channel.delete_channel_message(
                channel_id=target,
                message_id=post.channel_message_id,
            )
            if not ok:
                return False, msg
            note = " (kanaldan ham o'chirildi)"

        if post.status in {PostStatus.SCHEDULED.value, PostStatus.PAUSED.value}:
            jtype = JobType.PUBLISH_AD if post.post_type == PostType.AD.value else JobType.PUBLISH_POST
            await self.schedule_repo.cancel_by_reference(jtype, post.id)

        post.status = PostStatus.DELETED.value
        post.updated_by = actor_id
        post.updated_at = now_utc()
        await self.session.flush()

        await self.sys_repo.log_activity(
            admin_telegram_id=actor_id,
            action=f"{post.post_type}_deleted",
            target_type=post.post_type,
            target_id=str(post.id),
        )
        return True, f"Muvaffaqiyatli o'chirildi{note}."

    async def pause_or_resume_ad(self, *, post_id: int, actor_id: int) -> tuple[bool, str]:
        post = await self.post_repo.get_by_id(post_id)
        if not post or post.post_type != PostType.AD.value:
            return False, "Reklama topilmadi."

        if post.status == PostStatus.SCHEDULED.value:
            await self.schedule_repo.cancel_by_reference(JobType.PUBLISH_AD, post.id)
            post.status = PostStatus.PAUSED.value
            post.updated_by = actor_id
            post.updated_at = now_utc()
            await self.session.flush()
            await self.sys_repo.log_activity(
                admin_telegram_id=actor_id,
                action="ad_paused",
                target_type="ad",
                target_id=str(post.id),
            )
            return True, "Reklama vaqtincha to'xtatildi."

        if post.status == PostStatus.PAUSED.value:
            run_at = post.scheduled_at if (post.scheduled_at and post.scheduled_at > now_utc()) else now_utc()
            post.status = PostStatus.SCHEDULED.value
            post.scheduled_at = run_at
            post.updated_by = actor_id
            post.updated_at = now_utc()
            await self.schedule_repo.enqueue(
                job_type=JobType.PUBLISH_AD,
                reference_id=post.id,
                idempotency_key=f"publish_ad:resume:{post.id}:{int(now_utc().timestamp())}",
                run_at=run_at,
                payload_json={"post_id": post.id, "post_type": PostType.AD.value},
            )
            await self.session.flush()
            await self.sys_repo.log_activity(
                admin_telegram_id=actor_id,
                action="ad_resumed",
                target_type="ad",
                target_id=str(post.id),
            )
            return True, "Reklama qayta faollashtirildi."

        return False, "Faqat rejalashtirilgan yoki to'xtatilgan reklamani boshqarish mumkin."

    async def repost(self, *, post_id: int, actor_id: int) -> tuple[Optional[Post], str]:
        """Avvalgi postni kanalga yangi xabar sifatida qayta joylashtiradi."""
        original = await self.post_repo.get_by_id(post_id)
        if not original:
            return None, "Asl post topilmadi."

        return await self.publish_now(
            created_by=actor_id,
            post_type=PostType(original.post_type),
            content_type=ContentType(original.content_type),
            text=original.text,
            media_file_id=original.media_file_id,
            buttons_json=original.buttons_json,
            title=original.title,
        )
