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
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp", "questions.json"),
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

                    q_obj = Question(
                        id=item.get("id"),
                        text=item.get("text", ""),
                        image_url=item.get("image_url"),
                        media_type=item.get("media_type", "image"),
                        media_urls=item.get("media_urls"),
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

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

