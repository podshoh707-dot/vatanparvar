import json
import sqlite3

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, image_url, option_a, option_b, option_c, option_d, correct_option, explanation, media_urls
    FROM questions 
    WHERE image_url IS NOT NULL 
    ORDER BY id
""")
rows = cur.fetchall()

questions = []
for r in rows:
    questions.append({
        "id": r[0],
        "category": r[1],
        "text": r[2],
        "image_url": r[3],
        "option_a": r[4],
        "option_b": r[5],
        "option_c": r[6],
        "option_d": r[7],
        "correct_option": r[8],
        "explanation": r[9],
        "media_urls": r[10]
    })

print(f"Total questions with images: {len(questions)}")

# Let's inspect rules that indicate a question is PURE TEXT and should NEVER have an image:
# 1. Speed limit questions with no sign mentioned in text:
#    e.g. "Aholi punktlaridan tashqarida yengil avtomobillarning qanday eng yuqori tezlikda..."
# 2. General rules:
#    e.g. "Avtomagistralda shatakka olishga ruxsat beriladimi?", "Qaysi holda qoidalar ogohlantirish ishorasini berishni talab qilmaydi?"
# 3. First aid, fines, documents, vehicle defects
# 4. Questions about pedestrians/cyclists with no reference to sign or diagram
# 5. Questions where text is a complete self-contained theoretical question:
#    "Kunduzgi vaqtda yaqinni yorituvchi fara...", "Agar g'ildiraklardagi tortish kuchi...", "Manyovr vaqtida haydovchi har doim..."

pure_text_ids = []
for q in questions:
    text = q["text"].strip()
    t_low = text.lower()
    exp = (q["explanation"] or "").lower()
    oa = (q["option_a"] or "").lower()
    ob = (q["option_b"] or "").lower()

    # Signals of pure text questions:
    # A) Headlights and warning signals
    if "kunduzgi vaqtda yaqinni yorituvchi" in t_low:
        pure_text_ids.append((q["id"], "Kunduzgi fara qoidasi (nazariya)"))
    elif "agar g'ildiraklardagi tortish kuchi" in t_low or "agar gʻildiraklardagi tortish kuchi" in t_low:
        pure_text_ids.append((q["id"], "Tortish kuchi fizikasi (nazariya)"))
    elif "birinchi tibbiy yordam" in t_low or "birinchi yordam" in t_low or "lat yeganda" in t_low or "singanda" in t_low:
        pure_text_ids.append((q["id"], "Tibbiy yordam (nazariya)"))
    elif "kimlar \"yo'l harakati qatnashchisi\"" in t_low:
        pure_text_ids.append((q["id"], "Ta'rif (nazariya)"))
    elif "avtomagistralda shatakka olishga ruxsat beriladimi" in t_low:
        pure_text_ids.append((q["id"], "Avtomagistralda shatakka olish (nazariya)"))
    elif "ogohlantirish ishorasini berishni talab qilmaydi" in t_low:
        pure_text_ids.append((q["id"], "Ishorani talab qilmaslik (nazariya)"))
    elif "manyovr vaqtida haydovchi har doim ogohlantiruvchi ishorasi berishi kerakmi" in t_low:
        pure_text_ids.append((q["id"], "Manyovrda ishora berish (nazariya)"))
    elif "odamlarni tashishga moslashtirilmagan yuk avtomobili" in t_low:
        pure_text_ids.append((q["id"], "Yukxonasida odam tashish (nazariya)"))
    elif "aholi punktlaridan tashqarida yuk avtomobil yukxonasida odamlarni tashishda qanday eng yuqori tezlikda" in t_low:
        pure_text_ids.append((q["id"], "Yukxonasida odam tashish tezligi (nazariya)"))
    elif "m2; m3 toifadagi avtotransport vositalarining shina protektori" in t_low:
        pure_text_ids.append((q["id"], "Shina protektori balandligi (nazariya)"))
    elif "egiluvchan ulagichda shatakka olinganda qanday yuqori tezlik" in t_low:
        pure_text_ids.append((q["id"], "Shatakka olish tezligi (nazariya)"))
    elif "velosipedchilarga qatnov qismining o'ng chekkasidan chiqishga yo'l qo'yiladi" in t_low:
        pure_text_ids.append((q["id"], "Velosipedchilar qoidasi (nazariya)"))
    elif "aholi punktlaridan tashqarida yengil avtomobillarning qanday eng yuqori tezlikda harakatlanishiga ruxsat etiladi" in t_low:
        pure_text_ids.append((q["id"], "Yengil avtomobil tezligi (nazariya)"))
    elif "haydovchi manyovrni bajarishda burilish ko'rsatkichlari bilan yorug'lik ishorasini har doim berishi kerakmi" in t_low:
        pure_text_ids.append((q["id"], "Burilish ishorasi (nazariya)"))
    elif "temir yo'l izlarini qayerda kesib o'tishga ruxsat beriladi" in t_low and not "belgi" in t_low:
        pure_text_ids.append((q["id"], "Temir yo'l izlarini kesib o'tish (nazariya)"))
    elif "temir yo'l kesishmasida umumiy xatar ishorasi sifatida" in t_low:
        pure_text_ids.append((q["id"], "Umumiy xatar ishorasi (nazariya)"))
    elif "poezdni to'xtatish ishorasi bo'lib xizmat qiladi" in t_low:
        pure_text_ids.append((q["id"], "Poezdni to'xtatish ishorasi (nazariya)"))
    elif "haydovchi ko'zi qamashgan taqdirda" in t_low:
        pure_text_ids.append((q["id"], "Ko'zi qamashganda (nazariya)"))
    elif "tumanga qarshi chiroqlardan qanday hollarda foydalanish mumkin" in t_low:
        pure_text_ids.append((q["id"], "Tumanga qarshi chiroqlar (nazariya)"))
    elif "shatakka olish taqiqlanadi" in t_low and not any(w in t_low for w in ['belgi', 'rasm', 'surat']):
        pure_text_ids.append((q["id"], "Shatakka olish taqiqlari (nazariya)"))
    elif "haydovchi piyodalarga qachon yo'l berishi kerak" in t_low and not any(w in t_low for w in ['belgi', 'chorraha', 'rasm']):
        pure_text_ids.append((q["id"], "Piyodalarga yo'l berish (nazariya)"))

print(f"Found {len(pure_text_ids)} specific pure text questions with wrong images:")
for qid, reason in pure_text_ids:
    q = next(x for x in questions if x["id"] == qid)
    print(f"ID {qid} ({q['category']}): {q['text'][:60]}... -> IMG: {q['image_url']} [{reason}]")

con.close()
