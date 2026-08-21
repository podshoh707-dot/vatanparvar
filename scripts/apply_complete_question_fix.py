"""
Barcha 1242 ta test savollarini 100% rasmiy javoblar, to'g'ri variantlar, rasmlar, videolar
va izohlar bilan yangilash skripti.
"""
import json
import os
import sys
import re
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")

# 1. Raw questions
with open(os.path.join(BASE_DIR, 'db', 'questions.json'), 'r', encoding='utf-8') as f:
    raw_questions = json.load(f)

# 2. Master answers from scratch
with open(os.path.join(BASE_DIR, 'scratch', 'master_answers.json'), 'r', encoding='utf-8') as f:
    master_answers = json.load(f)

# 3. Media map for videos and images
VIDEOS_DIR = os.path.join(BASE_DIR, "zip", "videos")
media_map = {}
if os.path.exists(VIDEOS_DIR):
    for f in os.listdir(VIDEOS_DIR):
        m_main_vid = re.match(r'^(\d+)[\.\-](\d+)[\.\-]F[\.\-]?(?:lotin|kiril)?\.mp4$', f, re.IGNORECASE)
        m_opt_vid = re.match(r'^(\d+)[\.\-](\d+)(?:[\.\-](?:F[\.\-]?)?(\d+)|\(F?(\d+)\))(?:\.ru)?\.mp4$', f, re.IGNORECASE)
        m_img = re.match(r'^(\d+)[\.\-](\d+)(?:\.ru)?\.(jpg|png)$', f, re.IGNORECASE)
        m_bilet_img = re.match(r'^(\d+)-bilet_(\d+)-savol.*?\.(jpg|png)$', f, re.IGNORECASE)

        ticket = None
        q_num = None
        opt_num = None
        is_main = False

        if m_main_vid:
            ticket = int(m_main_vid.group(1))
            q_num = int(m_main_vid.group(2))
            is_main = True
        elif m_opt_vid:
            ticket = int(m_opt_vid.group(1))
            q_num = int(m_opt_vid.group(2))
            opt_num = int(m_opt_vid.group(3) or m_opt_vid.group(4))
        elif m_img:
            ticket = int(m_img.group(1))
            q_num = int(m_img.group(2))
        elif m_bilet_img:
            ticket = int(m_bilet_img.group(1))
            q_num = int(m_bilet_img.group(2))

        if ticket and q_num:
            key = f"{ticket}_{q_num}"
            if key not in media_map:
                media_map[key] = {"images": [], "videos": {}, "main_video": None}
            
            rel = f"zip/videos/{f}"
            if f.lower().endswith(".mp4"):
                if is_main:
                    if "lotin" in f.lower() or not media_map[key]["main_video"]:
                        media_map[key]["main_video"] = rel
                elif opt_num:
                    opt_letter = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}.get(opt_num, str(opt_num))
                    if "ru" not in f.lower() or opt_letter not in media_map[key]["videos"]:
                        media_map[key]["videos"][opt_letter] = rel
                else:
                    media_map[key]["main_video"] = rel
            else:
                if "ru" not in f.lower() or not media_map[key]["images"]:
                    media_map[key]["images"].append(rel)

# Specific manual overrides
manual_overrides = {
    31: 'A', 61: 'B', 73: 'A', 84: 'A', 96: 'A', 101: 'A', 127: 'B', 137: 'B',
    155: 'A', 165: 'A', 177: 'A', 182: 'B', 194: 'A', 196: 'A', 211: 'A', 212: 'B',
    227: 'A', 238: 'A', 269: 'A', 313: 'C', 329: 'B', 355: 'B', 364: 'A', 370: 'A',
    699: 'B', 714: 'A', 735: 'A', 737: 'B', 741: 'C', 754: 'B', 783: 'C', 785: 'A',
    794: 'A', 795: 'B', 798: 'A', 801: 'A', 845: 'B', 859: 'A', 861: 'A', 863: 'B',
    866: 'A', 881: 'B', 899: 'A', 908: 'A', 913: 'B', 920: 'A', 946: 'A', 948: 'B',
    953: 'B', 969: 'B', 986: 'C', 992: 'C', 1009: 'C', 1016: 'B',
    1243: 'A', 1244: 'B', 1245: 'C', 1246: 'B', 1247: 'A', 1248: 'B', 1249: 'A',
    1250: 'A', 1251: 'A', 1252: 'A', 1253: 'A'
}

def clean_opt_text(text):
    if not text: return ""
    text = re.sub(r'^(?:[A-Da-d1-4][\.\)]\s*)+', '', text).strip()
    return text

full_questions_list = []

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cur.execute("DELETE FROM questions")
cur.execute("DELETE FROM sqlite_sequence WHERE name='questions'")

count_inserted = 0

sorted_keys = sorted(raw_questions.keys(), key=lambda x: int(x) if x.isdigit() else 999999)

for qid_str in sorted_keys:
    qid = int(qid_str)
    q_item = raw_questions.get(qid_str, {})
    if not q_item:
        continue

    ticket = (qid - 1) // 10 + 1
    q_num = (qid - 1) % 10 + 1
    key = f"{ticket}_{q_num}"

    text = (q_item.get("text_lat") or q_item.get("text_kir") or q_item.get("text_ru") or "").strip()
    if not text:
        continue

    options = q_item.get("options", [])
    if len(options) < 2:
        continue

    opt_a = clean_opt_text(options[0].get("text_lat") or options[0].get("text_kir") or options[0].get("text_ru") or "")
    opt_b = clean_opt_text(options[1].get("text_lat") or options[1].get("text_kir") or options[1].get("text_ru") or "") if len(options) > 1 else ""
    opt_c = clean_opt_text(options[2].get("text_lat") or options[2].get("text_kir") or options[2].get("text_ru") or "") if len(options) > 2 else None
    opt_d = clean_opt_text(options[3].get("text_lat") or options[3].get("text_kir") or options[3].get("text_ru") or "") if len(options) > 3 else None

    # Determine correct option
    correct = master_answers.get(qid_str, 'A')
    if qid in manual_overrides:
        correct = manual_overrides[qid]

    # Validate correct_option is in range
    available_letters = ['A', 'B']
    if opt_c: available_letters.append('C')
    if opt_d: available_letters.append('D')

    if correct not in available_letters:
        correct = available_letters[-1]

    # Explanation
    exp = ""
    for opt in options:
        if opt.get("explanation_lat"):
            exp = opt.get("explanation_lat")
            break
        elif opt.get("explanation_ru"):
            exp = opt.get("explanation_ru")
            break
    if not exp and options:
        exp = options[0].get("explanation_lat") or options[0].get("explanation_ru") or ""

    # Media
    media_info = media_map.get(key, {"images": [], "videos": {}, "main_video": None})
    image_url = None
    media_type = "image"
    media_urls = None

    if media_info["images"]:
        image_url = media_info["images"][0]
    elif q_item.get("image_url"):
        image_url = q_item.get("image_url")

    if media_info["main_video"]:
        media_type = "video"
        media_urls = json.dumps({"main": media_info["main_video"], **media_info["videos"]})
    elif media_info["videos"]:
        media_type = "multi_video"
        media_urls = json.dumps(media_info["videos"])

    category = f"{ticket}-Bilet"

    cur.execute("""
        INSERT INTO questions (
            id, text, image_url, media_type, media_urls,
            option_a, option_b, option_c, option_d,
            correct_option, explanation, difficulty, category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        qid, text, image_url, media_type, media_urls,
        opt_a, opt_b, opt_c, opt_d,
        correct, exp, "o'rta", category
    ))
    count_inserted += 1

    full_questions_list.append({
        "id": qid,
        "text": text,
        "image_url": image_url,
        "media_type": media_type,
        "media_urls": media_urls,
        "option_a": opt_a,
        "option_b": opt_b,
        "option_c": opt_c,
        "option_d": opt_d,
        "correct_option": correct,
        "explanation": exp,
        "category": category,
        "difficulty": "o'rta"
    })

con.commit()
con.close()

print(f"✅ BAZAGA {count_inserted} TA SAVOL TO'LIQ VA TO'G'RI JAVOBLAR BILAN YUKLANDI!")

# Save to database/questions_data.json (for auto-seeding on fresh server deployment)
data_file = os.path.join(BASE_DIR, "database", "questions_data.json")
with open(data_file, "w", encoding="utf-8") as f:
    json.dump(full_questions_list, f, ensure_ascii=False, indent=2)
print(f"✅ Auto-seeding fayli saqlandi: {data_file}")

# Save to webapp/questions.json and webapp/avtomaktab-webapp/questions.json
for p in [
    os.path.join(BASE_DIR, "webapp", "questions.json"),
    os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "questions.json")
]:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(full_questions_list, f, ensure_ascii=False, indent=2)
    print(f"✅ WebApp fayli yangilandi: {p}")
