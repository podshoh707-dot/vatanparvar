"""
Mini App uchun PvP Duel REST API serveri (aiohttp)
Port: 3001
"""
from aiohttp import web
import json
import time
import uuid

# In-memory duel rooms: { room_id: {...} }
ROOMS = {}

# Umumiy savollar (bot.py dan import qilinmaydi, DB dan olindi)
QUESTIONS_CACHE = []


def set_questions(questions):
    """Bot ishga tushganda DB dan savollarni keshga o'tkazadi."""
    global QUESTIONS_CACHE
    QUESTIONS_CACHE = questions


def _room_to_dict(room):
    """Room state ni JSON ga o'tkazish."""
    return {
        "room_id": room["room_id"],
        "status": room["status"],      # waiting | active | finished
        "players": {
            pid: {
                "name": p["name"],
                "score": p["score"],
                "current_q": p["current_q"],
                "finished": p["finished"],
            }
            for pid, p in room["players"].items()
        },
        "total_q": room["total_q"],
        "created_at": room["created_at"],
    }


async def create_room(request):
    """POST /duel/create  { user_id, user_name }"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    user_id = str(data.get("user_id", ""))
    user_name = str(data.get("user_name", "Noma'lum"))

    if not user_id:
        return web.json_response({"error": "user_id required"}, status=400)

    # Eski kutayotgan xonani qidirish (matchmaking)
    for rid, room in list(ROOMS.items()):
        if room["status"] == "waiting" and user_id not in room["players"]:
            # Ikkinchi o'yinchi qo'shildi
            room["players"][user_id] = {
                "name": user_name, "score": 0,
                "current_q": 0, "finished": False,
                "answers": []
            }
            room["status"] = "active"
            room["started_at"] = time.time()
            return web.json_response({
                "room_id": rid,
                "status": "active",
                "joined": True,
                "questions": room["questions"]
            })

    # Yangi xona yaratish
    import random
    questions = random.sample(QUESTIONS_CACHE, min(10, len(QUESTIONS_CACHE)))
    q_data = [
        {
            "id": q["id"],
            "text": q["text"],
            "option_a": q["option_a"],
            "option_b": q.get("option_b", ""),
            "option_c": q.get("option_c", ""),
            "option_d": q.get("option_d", ""),
            "correct_option": q["correct_option"],
            "image_url": q.get("image_url", ""),
        }
        for q in questions
    ]

    room_id = uuid.uuid4().hex[:8].upper()
    ROOMS[room_id] = {
        "room_id": room_id,
        "status": "waiting",
        "players": {
            user_id: {
                "name": user_name, "score": 0,
                "current_q": 0, "finished": False,
                "answers": []
            }
        },
        "questions": q_data,
        "total_q": len(q_data),
        "created_at": time.time(),
    }

    return web.json_response({
        "room_id": room_id,
        "status": "waiting",
        "joined": False,
        "questions": q_data
    })


async def join_room(request):
    """POST /duel/join  { room_id, user_id, user_name }"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    room_id = str(data.get("room_id", "")).upper()
    user_id = str(data.get("user_id", ""))
    user_name = str(data.get("user_name", "Noma'lum"))

    room = ROOMS.get(room_id)
    if not room:
        return web.json_response({"error": "Xona topilmadi"}, status=404)
    if room["status"] == "finished":
        return web.json_response({"error": "Jang tugagan"}, status=400)
    if user_id in room["players"]:
        return web.json_response({"room_id": room_id, "status": room["status"],
                                   "questions": room["questions"]})
    if len(room["players"]) >= 2:
        return web.json_response({"error": "Xona to'la"}, status=400)

    room["players"][user_id] = {
        "name": user_name, "score": 0,
        "current_q": 0, "finished": False,
        "answers": []
    }
    room["status"] = "active"
    room["started_at"] = time.time()

    return web.json_response({
        "room_id": room_id,
        "status": "active",
        "questions": room["questions"]
    })


async def get_state(request):
    """GET /duel/state/{room_id}/{user_id}"""
    room_id = request.match_info["room_id"].upper()
    user_id = request.match_info["user_id"]

    room = ROOMS.get(room_id)
    if not room:
        return web.json_response({"error": "Xona topilmadi"}, status=404)

    # Expired xonalarni tozalash (30 daqiqadan eski)
    if time.time() - room["created_at"] > 1800:
        del ROOMS[room_id]
        return web.json_response({"error": "Xona muddati tugagan"}, status=404)

    return web.json_response(_room_to_dict(room))


async def submit_answer(request):
    """POST /duel/answer  { room_id, user_id, q_idx, answer }"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    room_id = str(data.get("room_id", "")).upper()
    user_id = str(data.get("user_id", ""))
    q_idx = int(data.get("q_idx", -1))
    answer = str(data.get("answer", ""))

    room = ROOMS.get(room_id)
    if not room:
        return web.json_response({"error": "Xona topilmadi"}, status=404)

    player = room["players"].get(user_id)
    if not player:
        return web.json_response({"error": "O'yinchi topilmadi"}, status=404)

    # Faqat joriy savolga javob qabul qilamiz
    if player["current_q"] != q_idx:
        return web.json_response({"error": "Noto'g'ri savol indeksi"}, status=400)

    q = room["questions"][q_idx]
    is_correct = (str(answer).strip().upper() == str(q.get("correct_option", "")).strip().upper())
    if is_correct:
        player["score"] += 1


    player["answers"].append({"q_idx": q_idx, "answer": answer, "correct": is_correct})
    player["current_q"] += 1

    if player["current_q"] >= room["total_q"]:
        player["finished"] = True
        # Barcha o'yinchilar tugatdimi?
        if all(p["finished"] for p in room["players"].values()):
            room["status"] = "finished"

    return web.json_response({
        "correct": is_correct,
        "player_score": player["score"],
        "room_status": room["status"],
        "room_state": _room_to_dict(room)
    })


async def cleanup_old_rooms(request):
    """GET /duel/cleanup — eski xonalarni tozalash"""
    removed = 0
    for rid in list(ROOMS.keys()):
        if time.time() - ROOMS[rid]["created_at"] > 1800:
            del ROOMS[rid]
            removed += 1
    return web.json_response({"removed": removed})


async def health_check(request):
    return web.Response(text="Avtovatanparvar Bot is running!", content_type="text/plain")


async def api_register_user(request):
    """POST /api/register va POST /register - Mini Ilovadan ro'yxatdan o'tish"""
    # CORS options preflight
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    try:
        data = await request.json()
        telegram_id = int(data.get("telegram_id", 0))
        full_name = str(data.get("full_name", "")).strip()
        phone = str(data.get("phone", "")).strip()
        language = str(data.get("language", "uz")).strip()
        region = str(data.get("region", "Toshkent")).strip()

        if not full_name or not phone:
            return web.json_response(
                {"ok": False, "error": "full_name va phone kiritilishi shart"},
                status=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )

        from database import async_session, User, UserStat
        from datetime import datetime, timedelta
        from sqlalchemy import select

        async with async_session() as session:
            user = None
            if telegram_id > 0:
                result = await session.execute(select(User).where(User.telegram_id == telegram_id))
                user = result.scalars().first()

            if not user:
                user = User(
                    telegram_id=telegram_id if telegram_id > 0 else int(time.time()),
                    full_name=full_name,
                    phone=phone,
                    language=language,
                    region=region,
                    is_premium=True,
                    premium_expires_at=datetime.utcnow() + timedelta(days=5),
                    points=50
                )
                session.add(user)
                await session.flush()
                user_stat = UserStat(user_id=user.id)
                session.add(user_stat)
            else:
                user.full_name = full_name
                user.phone = phone
                user.language = language
                user.region = region
                if not user.is_premium or (user.premium_expires_at and user.premium_expires_at < datetime.utcnow()):
                    user.is_premium = True
                    user.premium_expires_at = datetime.utcnow() + timedelta(days=5)

            await session.commit()

        return web.json_response(
            {"ok": True, "message": "Ro'yxatdan muvaffaqiyatli o'tildi!", "user": {"full_name": full_name, "phone": phone, "language": language, "region": region}},
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return web.json_response(
            {"ok": False, "error": str(e)},
            status=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )


async def health_check(request):
    """Render.com Web Service Health Check & Status"""
    return web.json_response(
        {
            "status": "ok",
            "service": "Avtovatanparvar Bot & API",
            "version": "2.0",
            "uptime": "active"
        },
        headers={"Access-Control-Allow-Origin": "*"}
    )


def create_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_post("/api/register", api_register_user)
    app.router.add_options("/api/register", api_register_user)
    app.router.add_post("/register", api_register_user)
    app.router.add_options("/register", api_register_user)
    app.router.add_post("/duel/create", create_room)
    app.router.add_post("/duel/join", join_room)
    app.router.add_get("/duel/state/{room_id}/{user_id}", get_state)
    app.router.add_post("/duel/answer", submit_answer)
    app.router.add_get("/duel/cleanup", cleanup_old_rooms)
    return app


async def start_api_server(questions_list, host="0.0.0.0", port=3001):
    """Bot bilan parallel ishlaydigan API serverni ishga tushirish."""
    import os
    port = int(os.getenv("PORT", port))
    set_questions(questions_list)
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Duel API server ishga tushdi: http://{host}:{port}")
    return runner

