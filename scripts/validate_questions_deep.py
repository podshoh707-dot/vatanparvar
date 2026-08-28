"""
Barcha 1242 ta test savollarini chuqur tekshirish va xatolarni aniqlash skripti.
"""
import os
import sys
import json
import asyncio
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database import async_session, Question
from sqlalchemy import select

async def deep_audit_questions():
    print("="*60)
    print("🔍 1242 TA TEST SAVOLINI CHUQUR TEKSHIRISH VA XATOLAR AUDITI")
    print("="*60)

    errors = {
        "empty_text": [],
        "invalid_correct_option": [],
        "missing_correct_option_text": [],
        "less_than_two_options": [],
        "duplicate_options": [],
        "missing_images": [],
        "missing_videos": [],
        "encoding_issues": [],
        "duplicates": []
    }

    seen_texts = {}

    async with async_session() as session:
        result = await session.execute(select(Question).order_by(Question.id))
        questions = result.scalars().all()

        total = len(questions)
        print(f"Jami tekshirilayotgan savollar: {total} ta\n")

        for q in questions:
            qid = q.id
            text = (q.text or "").strip()
            
            # 1. Bo'sh savol matni
            if not text:
                errors["empty_text"].append(qid)

            # 2. To'g'ri javob harfi
            corr = (q.correct_option or "").strip().upper()
            if corr not in ["A", "B", "C", "D"]:
                errors["invalid_correct_option"].append((qid, corr))

            # 3. Variantlar mavjudligi
            opts = {
                "A": (q.option_a or "").strip(),
                "B": (q.option_b or "").strip(),
                "C": (q.option_c or "").strip(),
                "D": (q.option_d or "").strip()
            }

            non_empty_opts = [k for k, v in opts.items() if v]
            if len(non_empty_opts) < 2:
                errors["less_than_two_options"].append((qid, len(non_empty_opts)))

            if corr in opts and not opts[corr]:
                errors["missing_correct_option_text"].append((qid, corr))

            # 4. Bir xil variantlar (duplicate options)
            filled_vals = [v.lower() for k, v in opts.items() if v]
            if len(filled_vals) != len(set(filled_vals)):
                errors["duplicate_options"].append((qid, opts))

            # 5. Rasmlar mavjudligi
            if q.image_url:
                if not str(q.image_url).startswith("http"):
                    p1 = os.path.join(BASE_DIR, "webapp", str(q.image_url).replace("\\", "/"))
                    p2 = os.path.join(BASE_DIR, str(q.image_url).replace("\\", "/"))
                    if not os.path.exists(p1) and not os.path.exists(p2):
                        errors["missing_images"].append((qid, q.image_url))

            # 6. Videolar mavjudligi
            if q.media_urls:
                try:
                    m = json.loads(q.media_urls) if isinstance(q.media_urls, str) else q.media_urls
                    if isinstance(m, dict):
                        for k, v in m.items():
                            if v and not v.startswith("http"):
                                vp = os.path.join(BASE_DIR, v.replace("\\", "/"))
                                if not os.path.exists(vp):
                                    errors["missing_videos"].append((qid, v))
                except Exception as e:
                    errors["missing_videos"].append((qid, f"JSON xato: {e}"))

            # 7. Kodirovka xatolari (Mojibake)
            full_str = f"{text} {q.option_a} {q.option_b} {q.option_c} {q.option_d} {q.explanation}"
            if "\ufffd" in full_str or "â€™" in full_str or "â€œ" in full_str or "â€" in full_str:
                errors["encoding_issues"].append(qid)

            # 8. Takroriy savollar (matn va rasm/video bir xil bo'lgan)
            media_key = str(q.image_url or "") + str(q.media_urls or "")
            norm_key = f"{re.sub(r'\s+', ' ', text.lower())}___{media_key}"
            if norm_key in seen_texts:
                errors["duplicates"].append((qid, seen_texts[norm_key]))
            else:
                seen_texts[norm_key] = qid

    print("📊 TEKSHIRUV NATIJALARI:")
    print("-" * 50)
    print(f"1. Bo'sh matnli savollar: {len(errors['empty_text'])} ta")
    print(f"2. Noto'g'ri belgilangan to'g'ri javob (A/B/C/D): {len(errors['invalid_correct_option'])} ta")
    print(f"3. To'g'ri javob varianti matni bo'sh bo'lgan: {len(errors['missing_correct_option_text'])} ta")
    print(f"4. 2 tadan kam varianti bor savollar: {len(errors['less_than_two_options'])} ta")
    print(f"5. Bir xil takrorlangan variantli savollar: {len(errors['duplicate_options'])} ta")
    print(f"6. Diskda topilmagan chorraha rasmlari: {len(errors['missing_images'])} ta")
    print(f"7. Diskda topilmagan 3D videolar: {len(errors['missing_videos'])} ta")
    print(f"8. Kodirovka / Shrift buzilishlari (Mojibake): {len(errors['encoding_issues'])} ta")
    print(f"9. Aynan bir xil matnli takroriy savollar: {len(errors['duplicates'])} ta")
    print("-" * 50)

    total_issues = sum(len(v) for v in errors.values())
    if total_issues == 0:
        print("🏆 BARAKALLA! BARCHA 1242 TA TEST SAVOLLARI 100% XATOSIZ VA MUKAMMAL!")
    else:
        print(f"⚠️ Jami aniqlangan nuqsonlar: {total_issues} ta")
        for k, v in errors.items():
            if v:
                print(f"\n🔴 {k} ({len(v)} ta):")
                for item in v[:5]:
                    print(f"   • {item}")

if __name__ == "__main__":
    asyncio.run(deep_audit_questions())
