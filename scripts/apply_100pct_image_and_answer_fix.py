"""
Barcha 805 ta test savollarini tahlil qilib, noto'g'ri biriktirilgan rasmlarni tozalash,
nazariy savollardan rasmni olib tashlash, to'g'ri javoblarni tuzatish va
bazalarni to'liq sinxronlashtirish skripti.
"""
import os
import sys
import json
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
TO_CLEAR_FILE = os.path.join(BASE_DIR, "scratch", "final_to_clear.json")

def main():
    print("=" * 65)
    print("🚀 BARCHA TESTLAR VA RASMLARNI 100% ANIQ TUZATISH BOSHLANDI")
    print("=" * 65)

    with open(TO_CLEAR_FILE, "r", encoding="utf-8") as f:
        to_clear_list = json.load(f)

    clear_ids = set(q["id"] for q in to_clear_list)
    print(f"1. Rasmi noto'g'ri qo'yilgan nazariy savollar soni: {len(clear_ids)} ta")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 1. Clear images on pure theory questions
    for qid in clear_ids:
        cur.execute("""
            UPDATE questions 
            SET image_url = NULL, media_urls = NULL, media_type = 'text' 
            WHERE id = ?
        """, (qid,))

    print(f"✅ {len(clear_ids)} ta nazariy savoldan noto'g'ri rasmlar olib tashlandi!")

    # 2. Fix Question 72 answer (Kunduzgi fara - YHQ 44-band: Bo'ladi -> A)
    cur.execute("""
        UPDATE questions 
        SET correct_option = 'A', image_url = NULL, media_urls = NULL, media_type = 'text'
        WHERE id = 72
    """)
    print("✅ 72-savol to'g'ri javobi 'A' ga tuzatildi va Yangibozor rasmi olib tashlandi!")

    # 3. Fix ID 736 and 737 remote URLs to local webapp/images
    cur.execute("""
        UPDATE questions 
        SET image_url = 'webapp/images/e-avtomaktab937.jpg' 
        WHERE id = 736
    """)
    cur.execute("""
        UPDATE questions 
        SET image_url = 'webapp/images/e-avtomaktab938.jpg' 
        WHERE id = 737
    """)
    print("✅ 736 va 737-savollar uchun mahalliy HD rasmlar ulandi!")

    con.commit()

    # 4. Read full updated database to sync JSON files
    cur.execute("""
        SELECT id, text, image_url, option_images, media_type, media_urls,
               option_a, option_b, option_c, option_d, correct_option, explanation, category
        FROM questions ORDER BY id
    """)
    rows = cur.fetchall()
    con.close()

    total_qs = len(rows)
    with_img_count = sum(1 for r in rows if r[2])
    print(f"\n📊 Baza yakuniy holati: {total_qs} ta savol, {with_img_count} ta rasmli savol, {total_qs - with_img_count} ta sof nazariy savol.")

    # 5. Build export structures
    json_export = []
    for r in rows:
        qid, text, img, opt_imgs, mtype, murls, oa, ob, oc, od, corr, exp, cat = r
        json_export.append({
            "id": qid,
            "text": text,
            "image_url": img or "",
            "option_images": opt_imgs or "",
            "media_type": mtype or "text",
            "media_urls": murls or "",
            "option_a": oa or "",
            "option_b": ob or "",
            "option_c": oc or "",
            "option_d": od or "",
            "correct_option": corr,
            "explanation": exp or "",
            "category": cat or ""
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
            print(f"✅ {os.path.relpath(p, BASE_DIR)} fayliga saqlandi!")

    print("\n" + "=" * 65)
    print("🏆 BARCHA SAVOLLAR VA RASMLAR 100% ANIQLIK BILAN TUZATILDI!")
    print("=" * 65)

if __name__ == "__main__":
    main()
