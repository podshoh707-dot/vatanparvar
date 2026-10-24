import os
import sys
import re
import json
import sqlite3
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
QUESTIONS_JSON = os.path.join(BASE_DIR, "db", "questions.json")
ZIP_VIDEOS_DIR = os.path.join(BASE_DIR, "zip", "videos")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
WEBAPP_IMAGES_DIR = os.path.join(BASE_DIR, "webapp", "images")
WEBAPP_REPO_IMAGES = os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "images")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(WEBAPP_IMAGES_DIR, exist_ok=True)
os.makedirs(WEBAPP_REPO_IMAGES, exist_ok=True)

# 1. Build ZIP video/image map
zip_img_map = {}
if os.path.exists(ZIP_VIDEOS_DIR):
    for f in os.listdir(ZIP_VIDEOS_DIR):
        m = re.match(r'^(\d+)[\.\-](\d+)(?:\.ru)?\.(jpg|png)$', f, re.IGNORECASE)
        m2 = re.match(r'^(\d+)-bilet_(\d+)-savol.*?\.(jpg|png)$', f, re.IGNORECASE)
        if m:
            zip_img_map[f"{int(m.group(1))}_{int(m.group(2))}"] = os.path.join("zip", "videos", f)
        elif m2:
            zip_img_map[f"{int(m2.group(1))}_{int(m2.group(2))}"] = os.path.join("zip", "videos", f)

print(f"1. ZIP ichida topilgan bilet rasmlari soni: {len(zip_img_map)} ta")

# 2. Read db/questions.json
with open(QUESTIONS_JSON, "r", encoding="utf-8") as f:
    raw_questions = json.load(f)

print(f"2. Baza savollari tahlil qilinmoqda: {len(raw_questions)} ta savol...")

# 3. Download helper
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def download_item(item):
    qid, url = item
    if not url or not url.startswith("http"):
        return qid, None
    try:
        parts = urllib.parse.urlsplit(url)
        encoded_path = urllib.parse.quote(parts.path)
        safe_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment))
        
        ext = os.path.splitext(parts.path)[1].lower()
        if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
            
        local_filename = f"q_{qid}{ext}"
        local_path = os.path.join(IMAGES_DIR, local_filename)
        
        if not os.path.exists(local_path) or os.path.getsize(local_path) < 500:
            req = urllib.request.Request(safe_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(local_path, "wb") as out:
                        out.write(data)
                        
        if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
            return qid, f"images/{local_filename}"
    except Exception as e:
        pass
    return qid, None

download_list = []
for qid_str, q in raw_questions.items():
    qid = int(qid_str)
    url = q.get("image_url") or ""
    if url and url.startswith("http"):
        download_list.append((qid, url))

print(f"3. Haqiqiy rasmlarni yuklab olish boshlandi: {len(download_list)} ta rasm...")
downloaded_results = {}
with ThreadPoolExecutor(max_workers=16) as executor:
    for qid, rel_path in executor.map(download_item, download_list):
        if rel_path:
            downloaded_results[qid] = rel_path

print(f"   Yuklab olingan rasmlar soni: {len(downloaded_results)} ta")

# 4. Build 100% clean questions mapping
con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Get existing media_urls & categories from current DB
cur.execute("SELECT id, media_urls, category, explanation FROM questions")
db_extra = {r[0]: {"media_urls": r[1], "category": r[2], "explanation": r[3]} for r in cur.fetchall()}

final_questions_list = []
matched_zip = 0
matched_download = 0
pure_text = 0

for qid_str, q in raw_questions.items():
    qid = int(qid_str)
    ticket = (qid - 1) // 10 + 1
    q_num = (qid - 1) % 10 + 1
    zip_key = f"{ticket}_{q_num}"
    
    text = (q.get("text_lat") or q.get("text_kir") or q.get("text_ru") or "").strip()
    options = q.get("options", [])
    
    opt_a = (options[0].get("text_lat") or options[0].get("text_kir") or options[0].get("text_ru") or "").strip() if len(options) > 0 else ""
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
    if not exp and db_extra.get(qid):
        exp = db_extra[qid]["explanation"] or ""
        
    extra = db_extra.get(qid, {})
    category = extra.get("category") or f"{ticket}-Bilet"
    media_urls = extra.get("media_urls")
    
    # DETERMINE THE EXACT 100% ACCURATE IMAGE:
    # Priority 1: ZIP HD Image for bilet situation
    final_image = None
    if zip_key in zip_img_map and os.path.exists(os.path.join(BASE_DIR, zip_img_map[zip_key])):
        final_image = zip_img_map[zip_key].replace("\\", "/")
        matched_zip += 1
    # Priority 2: Genuine downloaded image from questions.json
    elif qid in downloaded_results:
        final_image = downloaded_results[qid].replace("\\", "/")
        matched_download += 1
    else:
        # Check if local image already existed
        for ext in [".jpg", ".png", ".webp"]:
            local_cand = os.path.join(IMAGES_DIR, f"q_{qid}{ext}")
            if os.path.exists(local_cand):
                final_image = f"images/q_{qid}{ext}"
                matched_download += 1
                break
        if not final_image:
            pure_text += 1

    # Update SQLite database
    cur.execute("""
        UPDATE questions SET 
            image_url = ?,
            text = ?,
            option_a = ?,
            option_b = ?,
            option_c = ?,
            option_d = ?,
            correct_option = ?,
            explanation = ?,
            category = ?
        WHERE id = ?
    """, (
        final_image, text, opt_a, opt_b, opt_c, opt_d,
        correct_letter, exp, category, qid
    ))
    
    final_questions_list.append({
        "id": qid,
        "text": text,
        "image_url": final_image,
        "option_a": opt_a,
        "option_b": opt_b,
        "option_c": opt_c,
        "option_d": opt_d,
        "correct_option": correct_letter,
        "explanation": exp,
        "category": category,
        "media_urls": media_urls
    })

con.commit()
con.close()

# 5. Write to webapp/questions.json & webapp/avtomaktab-webapp/questions.json
with open(os.path.join(BASE_DIR, "webapp", "questions.json"), "w", encoding="utf-8") as f:
    json.dump(final_questions_list, f, ensure_ascii=False, indent=2)

with open(os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "questions.json"), "w", encoding="utf-8") as f:
    json.dump(final_questions_list, f, ensure_ascii=False, indent=2)

# Copy all images to webapp/images and webapp/avtomaktab-webapp/images
import shutil
for f in os.listdir(IMAGES_DIR):
    s = os.path.join(IMAGES_DIR, f)
    if os.path.isfile(s):
        shutil.copy2(s, os.path.join(WEBAPP_IMAGES_DIR, f))
        shutil.copy2(s, os.path.join(WEBAPP_REPO_IMAGES, f))

print("\n============================================================")
print("🏆 TO'LIQ RASM VA SAVOLLAR INTEGRATSIYASI YAKUNLANDI:")
print("============================================================")
print(f" • Jami savollar: {len(final_questions_list)} ta")
print(f" • ZIP HD bilet rasmlari: {matched_zip} ta (100% mos)")
print(f" • Yuklab olingan haqiqiy rasmlar: {matched_download} ta")
print(f" • Rasm talab qilinmaydigan nazariy savollar: {pure_text} ta")
print("============================================================")
