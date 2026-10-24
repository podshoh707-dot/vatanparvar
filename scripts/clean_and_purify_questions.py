"""
OsonPrava testlarini butunlay o'chirish va faqat 100% toza E-Avtomaktab testlarini qoldirish skripti.
"""
import os
import sys
import json
import sqlite3
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = str(text)
    t = t.replace("â€™", "'").replace("â€œ", '"').replace("â€", '"').replace("\ufffd", "'")
    t = t.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return t.strip()

def clean_option(opt: str) -> str:
    if not opt:
        return ""
    t = clean_text(opt)
    # Remove leading option labels like "A) ", "1. ", "a. "
    t = re.sub(r'^(?:[A-Da-d1-4][\.\)]\s*)+', '', t).strip()
    return t

def main():
    print("=" * 60)
    print("🧹 OSONPRAVA TESTLARINI O'CHIRISH VA E-AVTOMAKTAB TESTLARINI SARALASH")
    print("=" * 60)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("SELECT id, text, image_url, option_images, media_type, media_urls, option_a, option_b, option_c, option_d, correct_option, explanation, category FROM questions ORDER BY id")
    rows = cur.fetchall()
    total_initial = len(rows)
    print(f"Boshlang'ich jami savollar: {total_initial} ta")

    clean_rows = []
    removed_osonprava = 0

    for r in rows:
        qid, text, image_url, option_images, media_type, media_urls, opt_a, opt_b, opt_c, opt_d, corr, expl, cat = r
        
        # Check if question belongs to Osonprava
        is_osonprava = (
            "osonprava" in str(image_url or "").lower() or
            "osonprava" in str(text or "").lower() or
            "osonprava" in str(expl or "").lower()
        )

        if is_osonprava:
            removed_osonprava += 1
            continue

        clean_rows.append({
            "old_id": qid,
            "text": clean_text(text),
            "image_url": str(image_url).strip() if image_url else None,
            "option_images": option_images,
            "media_type": media_type or "image",
            "media_urls": media_urls,
            "option_a": clean_option(opt_a),
            "option_b": clean_option(opt_b),
            "option_c": clean_option(opt_c) if opt_c else None,
            "option_d": clean_option(opt_d) if opt_d else None,
            "correct_option": str(corr or "A").strip().upper(),
            "explanation": clean_text(expl),
            "category": cat
        })

    print(f"❌ O'chirilgan OsonPrava savollari soni: {removed_osonprava} ta")
    print(f"✅ Qolgan toza E-Avtomaktab savollari soni: {len(clean_rows)} ta")

    # Check for exact duplicate questions (same text + same media)
    deduped = []
    seen = {}
    dups_removed = 0
    for q in clean_rows:
        media_k = str(q["image_url"] or "") + str(q["media_urls"] or "")
        key = f"{q['text'].lower()}__{media_k}"
        if key in seen:
            dups_removed += 1
            continue
        seen[key] = True
        deduped.append(q)

    print(f"🧹 O'chirilgan takroriy (dublikat) savollar soni: {dups_removed} ta")
    print(f"🎯 Yakuniy sof E-Avtomaktab savollari soni: {len(deduped)} ta")

    # Biletlarni tartib bilan 10 tadan savolga taqsimlash
    total_clean = len(deduped)
    final_questions = []

    for idx, q in enumerate(deduped, start=1):
        bilet_num = ((idx - 1) // 10) + 1
        q_num_in_bilet = ((idx - 1) % 10) + 1
        bilet_category = f"{bilet_num}-Bilet"

        q["id"] = idx
        q["category"] = bilet_category
        final_questions.append(q)

    total_bilets = ((total_clean - 1) // 10) + 1
    print(f"📂 Jami biletlar soni: {total_bilets} ta (Har bir biletda 10 tadan savol)")

    # Bazasini yangilash
    cur.execute("DELETE FROM questions")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='questions'")

    insert_sql = """
    INSERT INTO questions (id, text, image_url, option_images, media_type, media_urls, option_a, option_b, option_c, option_d, correct_option, explanation, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for q in final_questions:
        cur.execute(insert_sql, (
            q["id"],
            q["text"],
            q["image_url"],
            q["option_images"],
            q["media_type"],
            q["media_urls"],
            q["option_a"],
            q["option_b"],
            q["option_c"],
            q["option_d"],
            q["correct_option"],
            q["explanation"],
            q["category"]
        ))

    con.commit()
    con.close()
    print("💾 SQLite bazasi muvaffaqiyatli yangilandi!")

    # JSON fayllarni sinxronlashtirish
    json_export = []
    for q in final_questions:
        json_export.append({
            "id": q["id"],
            "text": q["text"],
            "image_url": q["image_url"] or "",
            "media_type": q["media_type"],
            "media_urls": q["media_urls"] or "",
            "option_a": q["option_a"],
            "option_b": q["option_b"],
            "option_c": q["option_c"] or "",
            "option_d": q["option_d"] or "",
            "correct_option": q["correct_option"],
            "explanation": q["explanation"] or "",
            "category": q["category"]
        })

    json_paths = [
        os.path.join(BASE_DIR, "db", "questions.json"),
        os.path.join(BASE_DIR, "database", "questions_data.json"),
        os.path.join(BASE_DIR, "webapp", "questions.json"),
        os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "questions.json")
    ]

    for p in json_paths:
        if os.path.exists(os.path.dirname(p)):
            with open(p, "w", encoding="utf-8") as f:
                json.dump(json_export, f, ensure_ascii=False, indent=2)
            print(f"✅ {os.path.relpath(p, BASE_DIR)} yangilandi!")

    print("\n" + "=" * 60)
    print("🏆 BARCHA OSONPRAVA TESTLARI BUTUNLAY O'CHIRILDI!")
    print(f"🏆 BAZADA FAQAT {total_clean} TA 100% RASMIY E-AVTOMAKTAB TESTLARI SAQLANDI!")
    print("=" * 60)

if __name__ == "__main__":
    main()
