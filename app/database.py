"""SQLAlchemy 2 async ma'lumotlar bazasi ulanishi va sessiya boshqaruvi."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings


class DatabaseManager:
    """Async SQLAlchemy engine va session factory boshqaruvchisi."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self.init()
        assert self._engine is not None
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self.init()
        assert self._session_factory is not None
        return self._session_factory

    def init(self) -> None:
        """Engine va session factory yaratadi."""
        if self._engine is not None:
            return

        db_url, connect_args = self._settings.build_async_db_url_and_args()
        is_sqlite = db_url.startswith("sqlite")

        engine_kwargs: dict = {
            "echo": False,
            "future": True,
            "connect_args": connect_args,
        }

        if is_sqlite:
            engine_kwargs["poolclass"] = NullPool
        else:
            # Render Free + Supabase Free uchun tejamkor pool parametrlari
            engine_kwargs.update(
                {
                    "pool_pre_ping": True,
                    "pool_size": 5,
                    "max_overflow": 5,
                    "pool_recycle": 300,
                    "pool_timeout": 30,
                }
            )

        self._engine = create_async_engine(db_url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def is_postgres(self) -> bool:
        return self.engine.dialect.name == "postgresql"

    async def health_check(self) -> bool:
        """Bazaga ulanishni tekshiradi."""
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async sessiya generatori."""
        async with self.session_factory() as session:
            yield session

    async def close(self) -> None:
        """Barcha ulanishlarni xavfsiz yopadi."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


db_manager = DatabaseManager()
