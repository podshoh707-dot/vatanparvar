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
        
        if count < 1200 or is_corrupted:
            questions_file = os.path.join(os.path.dirname(__file__), "questions_data.json")
            if os.path.exists(questions_file):
                print(f"[init_db] Seeding questions from {questions_file}...")
                with open(questions_file, "r", encoding="utf-8") as f:
                    q_data = json.load(f)
                
                # Clear and insert fresh questions
                await session.execute(text("DELETE FROM questions"))
                for item in q_data:
                    q_obj = Question(
                        id=item.get("id"),
                        text=item.get("text"),
                        image_url=item.get("image_url"),
                        media_type=item.get("media_type", "image"),
                        media_urls=item.get("media_urls"),
                        option_a=item.get("option_a"),
                        option_b=item.get("option_b"),
                        option_c=item.get("option_c"),
                        option_d=item.get("option_d"),
                        correct_option=item.get("correct_option", "A"),
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

