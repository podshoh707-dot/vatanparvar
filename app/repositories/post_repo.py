"""Postlar va reklamalar repozitoriysi."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ContentType, PostStatus, PostType
from app.models.post import Post
from app.utils.timezone import now_utc


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        created_by: int,
        post_type: PostType = PostType.POST,
        content_type: ContentType = ContentType.TEXT,
        title: Optional[str] = None,
        text: Optional[str] = None,
        media_file_id: Optional[str] = None,
        buttons_json: Optional[list[dict[str, Any]]] = None,
        status: PostStatus = PostStatus.DRAFT,
        channel_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Post:
        post = Post(
            post_type=post_type.value,
            content_type=content_type.value,
            title=title,
            text=text,
            media_file_id=media_file_id,
            buttons_json=buttons_json,
            status=status.value,
            channel_id=channel_id,
            scheduled_at=scheduled_at,
            created_by=created_by,
            updated_by=created_by,
        )
        self.session.add(post)
        await self.session.flush()
        return post

    async def get_by_id(self, post_id: int) -> Optional[Post]:
        return await self.session.get(Post, post_id)

    async def list_posts(
        self,
        *,
        post_type: Optional[PostType] = None,
        status: Optional[PostStatus] = None,
        statuses: Optional[list[PostStatus]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Post], int]:
        conditions = []
        if post_type is not None:
            conditions.append(Post.post_type == post_type.value)
        if status is not None:
            conditions.append(Post.status == status.value)
        if statuses:
            conditions.append(Post.status.in_([s.value for s in statuses]))

        count_stmt = select(func.count(Post.id)).where(*conditions)
        total = int((await self.session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(Post)
            .where(*conditions)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def mark_published(
        self,
        post: Post,
        *,
        channel_id: str,
        channel_message_id: int,
    ) -> Post:
        post.status = PostStatus.PUBLISHED.value
        post.channel_id = channel_id
        post.channel_message_id = channel_message_id
        post.published_at = now_utc()
        post.error_message = None
        post.updated_at = now_utc()
        await self.session.flush()
        return post

    async def mark_failed(self, post: Post, error: str) -> Post:
        post.status = PostStatus.FAILED.value
        post.error_message = error[:1000]
        post.updated_at = now_utc()
        await self.session.flush()
        return post

    async def count_by_type_and_status(
        self,
        post_type: PostType,
        status: Optional[PostStatus] = None,
    ) -> int:
        conditions = [Post.post_type == post_type.value]
        if status is not None:
            conditions.append(Post.status == status.value)
        stmt = select(func.count(Post.id)).where(*conditions)
        return int((await self.session.execute(stmt)).scalar_one() or 0)
