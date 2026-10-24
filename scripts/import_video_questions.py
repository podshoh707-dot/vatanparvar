"""
Video va Rasmli YHQ Testlarini To'g'ri Xaritalash va Bazaga Yuklash Skripti
Variantlar bo'yicha videolarni (A: 1.1.1.mp4, B: 1.1.2.mp4, ...) aniq bog'laydi.
"""
import os
import sys
import re
import json
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
VIDEOS_DIR = os.path.join(BASE_DIR, "zip", "videos")
QUESTIONS_JSON = os.path.join(BASE_DIR, "db", "questions.json")

def build_smart_media_map():
    media_map = {}
    if not os.path.exists(VIDEOS_DIR):
        print(f"Directory not found: {VIDEOS_DIR}")
        return media_map

    files = os.listdir(VIDEOS_DIR)
    for f in files:
        full_path = os.path.join(VIDEOS_DIR, f)
        if os.path.isdir(full_path):
            continue

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

    return media_map

def import_questions():
    print("1. Media xaritasi aniq tuzilmoqda...")
    media_map = build_smart_media_map()
    print(f"   Xaritalangan savollar soni: {len(media_map)}")

    if not os.path.exists(QUESTIONS_JSON):
        print(f"Questions json not found: {QUESTIONS_JSON}")
        return

    with open(QUESTIONS_JSON, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"2. {len(raw_data)} ta savol ma'lumotlari tahlil qilinmoqda...")
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM questions")
    
    inserted_count = 0
    with_images_count = 0
    with_videos_count = 0

    sorted_keys = sorted(raw_data.keys(), key=lambda x: int(x) if x.isdigit() else 999999)

    for q_id_str in sorted_keys:
        q_item = raw_data[q_id_str]
        try:
            q_id = int(q_id_str)
        except:
            continue

        ticket = (q_id - 1) // 10 + 1
        q_num = (q_id - 1) % 10 + 1
        key = f"{ticket}_{q_num}"

        text = (q_item.get("text_lat") or q_item.get("text_kir") or q_item.get("text_ru") or "").strip()
        if not text:
            continue

        options = q_item.get("options", [])
        if len(options) < 2:
            continue

        opt_a = (options[0].get("text_lat") or options[0].get("text_kir") or options[0].get("text_ru") or "").strip()
        opt_b = (options[1].get("text_lat") or options[1].get("text_kir") or options[1].get("text_ru") or "").strip() if len(options) > 1 else None
        opt_c = (options[2].get("text_lat") or options[2].get("text_kir") or options[2].get("text_ru") or "").strip() if len(options) > 2 else None
        opt_d = (options[3].get("text_lat") or options[3].get("text_kir") or options[3].get("text_ru") or "").strip() if len(options) > 3 else None

        correct_letter = "A"
        letters = ["A", "B", "C", "D"]
        for idx, opt in enumerate(options[:4]):
            if opt.get("is_correct"):
                correct_letter = letters[idx]
                break

        exp = ""
        for opt in options:
            if opt.get("is_correct"):
                exp = opt.get("explanation_lat") or opt.get("explanation_kir") or opt.get("explanation_ru") or ""
                break
        if not exp and options:
            exp = options[0].get("explanation_lat") or ""

        # Media fayllarni to'g'ri biriktirish
        media_info = media_map.get(key, {"images": [], "videos": {}, "main_video": None})
        
        image_url = None
        media_type = "image"
        media_urls = None

        if media_info["images"]:
            image_url = media_info["images"][0]
            with_images_count += 1
        elif q_item.get("image_url"):
            image_url = q_item.get("image_url")
            with_images_count += 1

        if media_info["main_video"]:
            media_type = "video"
            media_urls = json.dumps({"main": media_info["main_video"], **media_info["videos"]})
            with_videos_count += 1
        elif media_info["videos"]:
            media_type = "multi_video"
            media_urls = json.dumps(media_info["videos"])
            with_videos_count += 1

        category = f"{ticket}-Bilet"

        cur.execute("""
            INSERT INTO questions (
                id, text, image_url, media_type, media_urls,
                option_a, option_b, option_c, option_d,
                correct_option, explanation, difficulty, category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            q_id, text, image_url, media_type, media_urls,
            opt_a, opt_b, opt_c, opt_d,
            correct_letter, exp, "o'rta", category
        ))
        inserted_count += 1

    con.commit()
    con.close()

    print(f"\n✅ MUVAFFAQIYATLI YUKLANDI:")
    print(f"   📊 Jami savollar: {inserted_count} ta")
    print(f"   🖼 Rasmli savollar: {with_images_count} ta")
    print(f"   🎬 Video animatsiyali savollar: {with_videos_count} ta")

if __name__ == "__main__":
    import_questions()
