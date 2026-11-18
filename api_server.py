"""
AVTOVATANPARVAR TESTLARI — FastAPI Webhook & Health Server.
Render.com Web Service va Health Check uchun ASGI ilovasi.
"""
from __future__ import annotations

from app.main import create_app

app = create_app()

__all__ = ["app"]
