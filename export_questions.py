"""
Bu skript bazadan savollarni olib database/questions_data.json va db/questions.json fayllariga yozadi.
Ishga tushirish: python export_questions.py
"""
import asyncio
import json
import os
import sys

# Loyiha papkasiga o'tamiz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import async_session, Question
from sqlalchemy import select

async def export():
    output_path1 = os.path.join(os.path.dirname(__file__), "database", "questions_data.json")
    output_path2 = os.path.join(os.path.dirname(__file__), "db", "questions.json")
    
    async with async_session() as session:
        result = await session.execute(select(Question))
        questions = result.scalars().all()
    
    data = []
    for q in questions:
        image_url = None
        if q.image_url:
            if str(q.image_url).startswith("http"):
                image_url = q.image_url
            else:
                base_name = os.path.basename(str(q.image_url))
                image_url = f"images/{base_name}"
        
        options = [
            {"letter": "A", "text": q.option_a},
        ]
        if q.option_b:
            options.append({"letter": "B", "text": q.option_b})
        if q.option_c:
            options.append({"letter": "C", "text": q.option_c})
        if q.option_d:
            options.append({"letter": "D", "text": q.option_d})
        
        m_urls = json.loads(q.media_urls) if isinstance(q.media_urls, str) else q.media_urls
        opt_imgs = json.loads(q.option_images) if isinstance(q.option_images, str) else q.option_images
        
        data.append({
            "id": q.id,
            "text": q.text,
            "image_url": image_url,
            "option_images": opt_imgs,
            "media_type": q.media_type or "image",
            "media_urls": m_urls,
            "options": options,
            "correct": q.correct_option,
            "explanation": q.explanation or "",
            "category": q.category or "Umumiy",
            "difficulty": q.difficulty or "o'rta"
        })
    
    with open(output_path1, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if os.path.exists(os.path.dirname(output_path2)):
        with open(output_path2, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    db_json = os.path.join(os.path.dirname(__file__), "db", "questions.json")
    if os.path.exists(os.path.dirname(db_json)):
        with open(db_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    data_json = os.path.join(os.path.dirname(__file__), "database", "questions_data.json")
    if os.path.exists(os.path.dirname(data_json)):
        with open(data_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"OK: {len(data)} ta savol barcha JSON fayllarga eksport qilindi!")

if __name__ == "__main__":
    asyncio.run(export())
