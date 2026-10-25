"""
Avtovatanparvar Server & Health Check
Render.com Web Service Port Binding va Status tekshiruvi uchun
"""
from aiohttp import web
import os

def set_questions(questions):
    """Xotira kompatibilligi uchun bo'sh qoldirildi."""
    pass

async def health_check(request):
    """Render.com Web Service Health Check & Status"""
    return web.json_response(
        {
            "status": "ok",
            "service": "Avtovatanparvar Bot",
            "version": "2.0",
            "uptime": "active"
        },
        headers={"Access-Control-Allow-Origin": "*"}
    )

def create_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    return app

async def start_api_server(questions_list=None, host="0.0.0.0", port=3001):
    """Render.com port detection uchun veb serverni ishga tushirish."""
    port = int(os.getenv("PORT", port))
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Server muvaffaqiyatli ishga tushdi: http://{host}:{port}")
    return runner
