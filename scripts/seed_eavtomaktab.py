"""
e-Avtomaktab barcha test savollari, YHQ qoidalari, Yo'l belgilari va QA ma'lumotlarini
ma'lumotlar bazasiga (db/database.sqlite) sifatli va toza yuklash skripti.
"""
import os
import sys
import json
import sqlite3
import re
import html

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SCRIPTS_DIR)

DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
TAGGED_JSON = os.path.join(BASE_DIR, "db", "questions_tagged.json")
BLITS_JSON = os.path.join(BASE_DIR, "scratch", "eavtotalim_blits.json")

def clean_str(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('\xa0', ' ').replace('\u200b', '')
    text = text.replace('‘', "'").replace('’', "'").replace('`', "'")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_category(cat):
    if not cat:
        return "Umumiy YHQ qoidalari"
    c = clean_str(cat)
    if "belgi" in c.lower() or "chiziq" in c.lower():
        return "Yo'l belgilari va chiziqlari"
    elif "chorraha" in c.lower():
        return "Chorrahalardan o'tish qoidalari"
    elif "tezlik" in c.lower() or "to'xtash" in c.lower() or "toxtash" in c.lower():
        return "Tezlik va to'xtash qoidalari"
    elif "manevr" in c.lower() or "joylashuv" in c.lower() or "burilish" in c.lower():
        return "Manevr qilish va harakatlanish"
    elif "nosozlik" in c.lower() or "texnik" in c.lower():
        return "Texnik nosozliklar va xavfsizlik"
    elif "tibbiy" in c.lower() or "qonun" in c.lower() or "yordam" in c.lower():
        return "Birinchi tibbiy yordam va qonunchilik"
    elif "blits" in c.lower():
        return "Blits-test (Tezkor)"
    elif "piyoda" in c.lower() or "yo'lovchi" in c.lower():
        return "Piyodalar va yo'lovchilar"
    elif "quvib" in c.lower() or "quvib o'tish" in c.lower():
        return "Quvib o'tish qoidalari"
    elif "svetofor" in c.lower() or "tartibga" in c.lower():
        return "Svetofor va tartibga soluvchi"
    elif "temir" in c.lower() or "kesishma" in c.lower():
        return "Temir yo'l kesishmalari"
    elif "shatak" in c.lower() or "yuk" in c.lower() or "tashish" in c.lower():
        return "Yuk va odam tashish, shatakka olish"
    elif "boshqa" in c.lower() or "umumiy" in c.lower():
        return "Umumiy YHQ qoidalari"
    return c

def seed_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Questions jadvalini tozalash va to'ldirish
    print("--- 1. Questions jadvalini yangilash ---")
    c.execute("DELETE FROM questions")
    c.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
    conn.commit()

    saved_texts = set()
    total_added = 0

    # A) Tagged e-avtomaktab savollari
    if os.path.exists(TAGGED_JSON):
        with open(TAGGED_JSON, "r", encoding="utf-8") as f:
            tagged_data = json.load(f)

        for qid, q in tagged_data.items():
            text = clean_str(q.get("text", ""))
            if not text or text in saved_texts:
                continue

            options = q.get("options", [])
            if len(options) < 2:
                continue

            opt_a = clean_str(options[0].get("text", "")) if len(options) > 0 else ""
            opt_b = clean_str(options[1].get("text", "")) if len(options) > 1 else ""
            opt_c = clean_str(options[2].get("text", "")) if len(options) > 2 else None
            opt_d = clean_str(options[3].get("text", "")) if len(options) > 3 else None

            correct_letter = "A"
            explanation = ""
            letters = ["A", "B", "C", "D", "E"]
            for idx, opt in enumerate(options):
                if opt.get("is_correct"):
                    correct_letter = letters[idx] if idx < len(letters) else "A"
                    if opt.get("explanation"):
                        explanation = clean_str(opt.get("explanation"))
                    break

            if not explanation:
                for opt in options:
                    if opt.get("explanation"):
                        explanation = clean_str(opt.get("explanation"))
                        break

            image_url = q.get("image_url") or None
            category = normalize_category(q.get("category", "Yo'l belgilari va chiziqlari"))
            difficulty = "qiyin" if (image_url and len(options) >= 4) else "o'rta"

            c.execute("""
                INSERT INTO questions 
                (text, image_url, media_type, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (text, image_url, "image", opt_a, opt_b, opt_c, opt_d, correct_letter, explanation, difficulty, category))
            
            saved_texts.add(text)
            total_added += 1

        print(f"  Tagged e-avtomaktab savollari yuklandi: {total_added} ta")

    # B) seed_new_questions.py dagi mavzuli savollar
    try:
        sys.path.append(BASE_DIR)
        from seed_new_questions import QUESTIONS as NEW_QUESTIONS
        added_new = 0
        for q in NEW_QUESTIONS:
            text = clean_str(q.get("text", ""))
            if not text or text in saved_texts:
                continue

            opts = q.get("options", [])
            if len(opts) < 2:
                continue

            opt_a = clean_str(opts[0].get("text", "")) if len(opts) > 0 else ""
            opt_b = clean_str(opts[1].get("text", "")) if len(opts) > 1 else ""
            opt_c = clean_str(opts[2].get("text", "")) if len(opts) > 2 else None
            opt_d = clean_str(opts[3].get("text", "")) if len(opts) > 3 else None

            letters = ["A", "B", "C", "D"]
            correct_letter = "A"
            for idx, opt in enumerate(opts):
                if opt.get("correct"):
                    correct_letter = letters[idx] if idx < len(letters) else "A"
                    break

            exp = clean_str(q.get("explanation", ""))
            diff = q.get("difficulty", "o'rta")

            # Kategoriya aniqlash
            cat = "Umumiy YHQ qoidalari"
            t_lower = text.lower()
            if "tezlik" in t_lower or "km/soat" in t_lower:
                cat = "Tezlik va to'xtash qoidalari"
            elif "piyoda" in t_lower or "yo'lovchi" in t_lower:
                cat = "Piyodalar va yo'lovchilar"
            elif "quvib" in t_lower:
                cat = "Quvib o'tish qoidalari"
            elif "svetofor" in t_lower or "chiroq" in t_lower:
                cat = "Svetofor va tartibga soluvchi"
            elif "chorraha" in t_lower:
                cat = "Chorrahalardan o'tish qoidalari"
            elif "belgi" in t_lower or "chiziq" in t_lower:
                cat = "Yo'l belgilari va chiziqlari"
            elif "tibbiy" in t_lower or "yordam" in t_lower or "jarohat" in t_lower:
                cat = "Birinchi tibbiy yordam va qonunchilik"
            elif "tormoz" in t_lower or "shina" in t_lower or "chiroq" in t_lower or "nosozlik" in t_lower:
                cat = "Texnik nosozliklar va xavfsizlik"
            elif "temir yo'l" in t_lower or "shlagbaum" in t_lower:
                cat = "Temir yo'l kesishmalari"
            elif "shatak" in t_lower or "tirkama" in t_lower or "yuk" in t_lower:
                cat = "Yuk va odam tashish, shatakka olish"

            c.execute("""
                INSERT INTO questions 
                (text, image_url, media_type, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (text, None, "image", opt_a, opt_b, opt_c, opt_d, correct_letter, exp, diff, cat))

            saved_texts.add(text)
            added_new += 1
            total_added += 1

        print(f"  Mavzuli YHQ savollari yuklandi: {added_new} ta")
    except Exception as e:
        print(f"  seed_new_questions xatosi: {e}")

    # C) seed_image_questions.py dagi rasmli savollar
    try:
        from seed_image_questions import IMAGED_QUESTIONS
        added_img = 0
        for q in IMAGED_QUESTIONS:
            text = clean_str(q.get("text", ""))
            if not text or text in saved_texts:
                continue

            opts = q.get("options", [])
            if len(opts) < 2:
                continue

            opt_a = clean_str(opts[0].get("text", "")) if len(opts) > 0 else ""
            opt_b = clean_str(opts[1].get("text", "")) if len(opts) > 1 else ""
            opt_c = clean_str(opts[2].get("text", "")) if len(opts) > 2 else None
            opt_d = clean_str(opts[3].get("text", "")) if len(opts) > 3 else None

            letters = ["A", "B", "C", "D"]
            correct_letter = "A"
            for idx, opt in enumerate(opts):
                if opt.get("correct"):
                    correct_letter = letters[idx] if idx < len(letters) else "A"
                    break

            exp = clean_str(q.get("explanation", ""))
            diff = q.get("difficulty", "o'rta")
            img = q.get("image")

            cat = "Chorrahalardan o'tish qoidalari" if "chorraha" in text.lower() else "Yo'l belgilari va chiziqlari"

            c.execute("""
                INSERT INTO questions 
                (text, image_url, media_type, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (text, img, "image", opt_a, opt_b, opt_c, opt_d, correct_letter, exp, diff, cat))

            saved_texts.add(text)
            added_img += 1
            total_added += 1

        print(f"  Rasmli amaliy savollar yuklandi: {added_img} ta")
    except Exception as e:
        print(f"  seed_image_questions xatosi: {e}")

    # D) Blits savollari
    if os.path.exists(BLITS_JSON):
        with open(BLITS_JSON, "r", encoding="utf-8") as f:
            blits_data = json.load(f)
        added_blits = 0
        for item in blits_data:
            text = clean_str(item.get("text", ""))
            if not text or text in saved_texts:
                continue

            exp = clean_str(item.get("explanation", ""))
            img = item.get("image_url")
            correct = item.get("correct_option", "A")

            c.execute("""
                INSERT INTO questions 
                (text, image_url, media_type, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (text, img, "image", "Ha", "Yo'q", None, None, correct, exp, "oson", "Blits-test (Tezkor)"))

            saved_texts.add(text)
            added_blits += 1
            total_added += 1

        print(f"  Blits-test savollari yuklandi: {added_blits} ta")

    conn.commit()

    # 2. QA savol-javoblari (qa_items) to'ldirish
    print("\n--- 2. Savol-Javoblar (qa_items) to'ldirish ---")
    c.execute("DELETE FROM qa_items")
    qa_list = [
        ("Haydovchilik guvohnomasini olish uchun necha yoshdan o'qish mumkin?", 
         "O'zbekistonda 'B' va 'C' toifali haydovchilik guvohnomasini olish uchun 17 yoshdan avtomaktabda o'qishni boshlash va 18 yoshga to'lganda imtihon topshirib guvohnoma olish mumkin. 'A' toifasi (motosikl) uchun esa 16 yoshdan ruxsat beriladi."),
        ("Imtihon qanday bosqichlardan iborat?", 
         "Davlat YHQ imtihoni 2 ta bosqichdan iborat: 1) Nazariy imtihon (kompyuterda test savollari, 20 tadan kamida 18 tasiga to'g'ri javob berish kerak); 2) Amaliy imtihon (avtodromda va shaharda haydash ko'nikmasi)."),
        ("Aholi yashash punktlarida maksimal ruxsat etilgan tezlik qancha?", 
         "So'nggi YHQ tahririga binoan, aholi yashash punktlarida barcha yengil transport vositalari uchun ruxsat etilgan eng yuqori tezlik soatiga 60 km etib belgilangan (maktab va bog'chalar oldida 30 km/soat, turar joy dahalarida 20 km/soat)."),
        ("Avtomaktabda o'qish davomiyligi qancha?", 
         "'B' toifasi uchun o'rtacha o'qish muddati 2.5 oydan 3 oygacha davom etadi. Darslar nazariy va amaliy haydash mashg'ulotlarini o'z ichiga oladi."),
        ("Xavfsizlik kamari taqish majburiymi?", 
         "Ha, konstruksiyasida xavfsizlik kamarlari ko'zda tutilgan barcha transport vositalarida old va orqa o'rindiqdagi yo'lovchilar ham xavfsizlik kamarini taqishlari shart."),
        ("Svetoforning qizil va sariq chirog'i bir vaqtda yonsa nimani bildiradi?", 
         "Qizil va sariq chiroqning bir vaqtda yonishi harakatlanishni taqiqlaydi va tez orada yashil chiroq yonishidan ogohlantiradi."),
        ("Testlarda xatolar ustida qanday ishlash mumkin?", 
         "Botimizda '👑 Xatolar tahlili' bo'limi mavjud. Siz test jarayonida adashgan savollaringiz avtomatik tarzda ushbu bo'limga yig'iladi va ularni qayta ishlab to'liq o'zlashtirishingiz mumkin."),
        ("VIP Premium obunasi qanday imkoniyatlarni beradi?", 
         "VIP Premium orqali siz real imtihon simulyatori (70 ta savol), xatolar tahlili, cheksiz testlar, to'liq rasmiy YHQ izohlari va reklamasiz foydalanish imkoniyatiga ega bo'lasiz.")
    ]
    for q_text, ans_text in qa_list:
        c.execute("INSERT INTO qa_items (question, answer) VALUES (?, ?)", (q_text, ans_text))
    conn.commit()
    print(f"  qa_items to'ldirildi: {len(qa_list)} ta savol-javob.")

    # 3. Rules (YHQ qoidalari) tekshirish
    print("\n--- 3. Rules (YHQ Kitobi) tekshirish ---")
    c.execute("SELECT count(*) FROM rules")
    rules_count = c.fetchone()[0]
    if rules_count < 15:
        from seed_comprehensive import rules_data
        for title, text in rules_data:
            c.execute("SELECT id FROM rules WHERE title = ?", (title,))
            if not c.fetchone():
                c.execute("INSERT INTO rules (title, text) VALUES (?, ?)", (title, text))
        conn.commit()
        print("  YHQ qoidalari qo'shildi.")
    else:
        print(f"  YHQ qoidalari allaqachon mavjud: {rules_count} ta bob.")

    # 4. Signs (Yo'l belgilari) tekshirish
    print("\n--- 4. Signs (Yo'l belgilari) tekshirish ---")
    c.execute("SELECT count(*) FROM signs")
    signs_count = c.fetchone()[0]
    print(f"  Yo'l belgilari soni: {signs_count} ta.")

    # Statistika chiqarish
    c.execute("SELECT COUNT(*) FROM questions")
    total_q = c.fetchone()[0]
    print(f"\n==========================================")
    print(f"BAZA MUVAFFAQIYATLI YANGILANDI!")
    print(f"Jami savollar soni: {total_q} ta")
    print(f"Bo'limlar statistikasi:")
    c.execute("SELECT category, COUNT(*) FROM questions GROUP BY category ORDER BY COUNT(*) DESC")
    for cat, cnt in c.fetchall():
        print(f"  📌 {cat}: {cnt} ta")
    print(f"==========================================")

    conn.close()

if __name__ == "__main__":
    seed_database()
