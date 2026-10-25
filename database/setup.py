import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models import Base

# SQLite bilan ishlash (lokal). Keyin PostgreSQL ga o'tkazish ham mumkin.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
DB_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# db/ papkani avtomatik yaratish (fresh deploy uchun)
if "sqlite" in DB_URL:
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    def _sync_schema(sync_conn):
        from sqlalchemy import inspect, text
        Base.metadata.create_all(sync_conn)
        inspector = inspect(sync_conn)
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        col_type = col.type.compile(sync_conn.dialect)
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                        try:
                            sync_conn.execute(text(sql))
                            print(f"Auto-migrated column: {table_name}.{col.name}")
                        except Exception as e:
                            print(f"Migration error ({table_name}.{col.name}): {e}")

    async with engine.begin() as conn:
        await conn.run_sync(_sync_schema)

    # Auto-seed questions if empty or missing
    from .models import Question
    from sqlalchemy import select, func, text
    import json
    async with async_session() as session:
        res = await session.execute(select(func.count(Question.id)))
        count = res.scalar() or 0
        
        # Check if corrupted (e.g. all 'A')
        res_sample = await session.execute(select(Question.correct_option).limit(30))
        sample_opts = res_sample.scalars().all()
        is_corrupted = len(sample_opts) > 0 and all(o == 'A' for o in sample_opts)
        
        if count == 0 or is_corrupted:
            candidate_files = [
                os.path.join(os.path.dirname(__file__), "questions_data.json"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "questions.json"),
            ]
            questions_file = next((cf for cf in candidate_files if os.path.exists(cf)), None)
            if questions_file:
                print(f"[init_db] Seeding questions from {questions_file}...")
                with open(questions_file, "r", encoding="utf-8") as f:
                    q_data = json.load(f)
                
                # Clear and insert fresh questions
                await session.execute(text("DELETE FROM questions"))
                for item in q_data:
                    opt_a, opt_b, opt_c, opt_d = None, None, None, None
                    opts = item.get("options", [])
                    if isinstance(opts, list):
                        for i, opt in enumerate(opts):
                            if isinstance(opt, dict):
                                letter = (opt.get("letter") or opt.get("label") or chr(65 + i)).strip().upper()
                                txt = opt.get("text", "")
                                if letter == "A": opt_a = txt
                                elif letter == "B": opt_b = txt
                                elif letter == "C": opt_c = txt
                                elif letter == "D": opt_d = txt
                            elif isinstance(opt, str):
                                if i == 0: opt_a = opt
                                elif i == 1: opt_b = opt
                                elif i == 2: opt_c = opt
                                elif i == 3: opt_d = opt
                    
                    # Direct key fallback
                    opt_a = opt_a or item.get("option_a") or "-"
                    opt_b = opt_b or item.get("option_b") or "-"
                    opt_c = opt_c or item.get("option_c")
                    opt_d = opt_d or item.get("option_d")
                    correct_opt = (item.get("correct") or item.get("correct_option") or "A").strip().upper()

                    # JSON field serialization for SQLite compatibility
                    media_urls_val = item.get("media_urls")
                    if isinstance(media_urls_val, (dict, list)):
                        media_urls_val = json.dumps(media_urls_val, ensure_ascii=False)
                    elif media_urls_val is not None and not isinstance(media_urls_val, str):
                        media_urls_val = str(media_urls_val)

                    option_images_val = item.get("option_images")
                    if isinstance(option_images_val, (dict, list)):
                        option_images_val = json.dumps(option_images_val, ensure_ascii=False)
                    elif option_images_val is not None and not isinstance(option_images_val, str):
                        option_images_val = str(option_images_val)

                    q_obj = Question(
                        id=item.get("id"),
                        text=item.get("text", ""),
                        image_url=item.get("image_url"),
                        option_images=option_images_val,
                        media_type=item.get("media_type", "image"),
                        media_urls=media_urls_val,
                        option_a=opt_a,
                        option_b=opt_b,
                        option_c=opt_c,
                        option_d=opt_d,
                        correct_option=correct_opt,
                        explanation=item.get("explanation"),
                        difficulty=item.get("difficulty", "o'rta"),
                        category=item.get("category", "Umumiy")
                    )
                    session.add(q_obj)
                await session.commit()
                print(f"[init_db] Successfully seeded {len(q_data)} questions!")

        # Auto-seed road signs if empty
        from .models import Sign
        res_signs = await session.execute(select(func.count(Sign.id)))
        count_signs = res_signs.scalar() or 0
        signs_file = os.path.join(os.path.dirname(__file__), "signs.json")
        if (count_signs < 279 or count_signs == 0) and os.path.exists(signs_file):
            print(f"[init_db] Seeding all 279 signs from {signs_file}...")
            with open(signs_file, "r", encoding="utf-8") as f:
                signs_data = json.load(f)
            await session.execute(text("DELETE FROM signs"))
            for s in signs_data:
                sign_obj = Sign(
                    id=s.get("id"),
                    category=s.get("category", "axborot"),
                    name=s.get("name", "Belgi"),
                    image_url=s.get("image_url"),
                    description=s.get("description"),
                    example=s.get("example")
                )
                session.add(sign_obj)
            await session.commit()
            print(f"[init_db] Successfully seeded {len(signs_data)} road signs!")

        # Auto-seed YHQ rules if empty
        from .models import Rule
        res_rules = await session.execute(select(func.count(Rule.id)))
        count_rules = res_rules.scalar() or 0
        if count_rules == 0:
            rules_file = os.path.join(os.path.dirname(__file__), "rules.json")
            if os.path.exists(rules_file):
                print(f"[init_db] Seeding rules from {rules_file}...")
                with open(rules_file, "r", encoding="utf-8") as f:
                    rules_data = json.load(f)
                for r in rules_data:
                    rule_obj = Rule(
                        id=r.get("id"),
                        title=r.get("title", ""),
                        text=r.get("text", ""),
                        image_url=r.get("image_url"),
                        video_url=r.get("video_url"),
                        pdf_url=r.get("pdf_url")
                    )
                    session.add(rule_obj)
                await session.commit()
                print(f"[init_db] Successfully seeded {len(rules_data)} YHQ rules!")

        # Auto-seed video lessons if empty or outdated
        from .models import VideoLesson
        res_videos = await session.execute(select(func.count(VideoLesson.id)))
        count_videos = res_videos.scalar() or 0
        first_video = (await session.execute(select(VideoLesson).limit(1))).scalars().first()
        is_corrupted = first_video and (first_video.topic.startswith("'") or "\ufffd" in first_video.topic)
        videos_file = os.path.join(os.path.dirname(__file__), "videos.json")
        if (count_videos < 133 or is_corrupted or count_videos == 0) and os.path.exists(videos_file):
            print(f"[init_db] Seeding video lessons from {videos_file}...")
            with open(videos_file, "r", encoding="utf-8") as f:
                videos_data = json.load(f)
            await session.execute(text("DELETE FROM video_lessons"))
            session.expunge_all()
            for v in videos_data:
                vid_obj = VideoLesson(
                    id=v.get("id"),
                    topic=v.get("topic", ""),
                    section=v.get("section", "Umumiy ta'lim"),
                    video_url=v.get("video_url"),
                    youtube_url=v.get("youtube_url") or v.get("video_url"),
                    telegram_video_id=v.get("telegram_video_id")
                )
                session.add(vid_obj)
            await session.commit()
            print(f"[init_db] Successfully seeded {len(videos_data)} video lessons!")

        # Auto-seed news if empty
        from .models import News
        res_news = await session.execute(select(func.count(News.id)))
        count_news = res_news.scalar() or 0
        news_file = os.path.join(os.path.dirname(__file__), "news.json")
        if (count_news < 3 or count_news == 0) and os.path.exists(news_file):
            print(f"[init_db] Seeding news from {news_file}...")
            with open(news_file, "r", encoding="utf-8") as f:
                news_data = json.load(f)
            await session.execute(text("DELETE FROM news"))
            for n in news_data:
                news_obj = News(
                    id=n.get("id"),
                    title=n.get("title", ""),
                    content=n.get("content", ""),
                    image_url=n.get("image_url"),
                    button_text=n.get("button_text"),
                    button_url=n.get("button_url")
                )
                session.add(news_obj)
            await session.commit()
            print(f"[init_db] Successfully seeded {len(news_data)} news items!")

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

