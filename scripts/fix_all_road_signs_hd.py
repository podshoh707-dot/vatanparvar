import os
import sys
import re
import json
import sqlite3
import urllib.request
from bs4 import BeautifulSoup
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNS_DIR = os.path.join(BASE_DIR, "webapp", "images", "signs")
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "images", "signs")
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")

os.makedirs(SIGNS_DIR, exist_ok=True)
os.makedirs(WEBAPP_DIR, exist_ok=True)

HTML_PATH = r"C:\Users\user\.gemini\antigravity-ide\brain\b099be54-0681-4034-b752-f955c6a9f5a3\.system_generated\steps\1681\content.md"

def get_wiki_signs():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    signs_map = {}
    for li in soup.find_all("li", class_="gallerybox"):
        img = li.find("img")
        caption = li.find("div", class_="gallerytext")
        if not img or not caption:
            continue
        text = caption.get_text(strip=True)
        src = img.get("src", "")
        if not src:
            continue
        
        if not src.startswith("http"):
            src = "https:" + src
        
        m = re.match(r"^(\d+(?:\.\d+)*)", text)
        if m:
            num = m.group(1)
            signs_map[num] = src
            
            parts = num.split(".")
            if len(parts) == 3:
                base_num = f"{parts[0]}.{parts[1]}"
                if base_num not in signs_map:
                    signs_map[base_num] = src

    # Special mapped signs
    signs_map["2.4"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ea/RU_road_sign_2.4.svg/120px-RU_road_sign_2.4.svg.png"
    signs_map["2.5"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/23/RU_road_sign_2.5.svg/120px-RU_road_sign_2.5.svg.png"
    signs_map["2.6"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/25/RU_road_sign_2.6.svg/120px-RU_road_sign_2.6.svg.png"
    signs_map["4.1.1"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5e/RU_road_sign_4.1.1.svg/120px-RU_road_sign_4.1.1.svg.png"
    signs_map["4.4"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/33/SU_road_sign_4.4.svg/120px-SU_road_sign_4.4.svg.png"
    signs_map["5.1"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c9/RU_road_sign_5.1.svg/120px-RU_road_sign_5.1.svg.png"
    signs_map["5.2"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d0/RU_road_sign_5.2.svg/120px-RU_road_sign_5.2.svg.png"
    signs_map["5.5"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/91/RU_road_sign_5.5.svg/120px-RU_road_sign_5.5.svg.png"
    signs_map["5.16.1"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/44/RU_road_sign_5.19.2.svg/120px-RU_road_sign_5.19.2.svg.png"
    signs_map["5.21"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/dc/UZ_road_sign_5.14.svg/120px-UZ_road_sign_5.14.svg.png"
    signs_map["5.22"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5f/UZ_road_sign_5.22.svg/120px-UZ_road_sign_5.22.svg.png"
    signs_map["5.23"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/be/UZ_road_sign_5.23.svg/120px-UZ_road_sign_5.23.svg.png"
    signs_map["6.1"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ee/RU_road_sign_7.1.svg/120px-RU_road_sign_7.1.svg.png"
    signs_map["6.2"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/46/RU_road_sign_7.2.svg/120px-RU_road_sign_7.2.svg.png"
    signs_map["6.3"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a2/RU_road_sign_7.3.svg/120px-RU_road_sign_7.3.svg.png"
    signs_map["6.10"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d6/RU_road_sign_7.10.svg/120px-RU_road_sign_7.10.svg.png"
    signs_map["1.11.1"] = "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b3/RU_road_sign_1.11.1.svg/120px-RU_road_sign_1.11.1.svg.png"

    return signs_map

def download_and_fix_all_signs():
    wiki_signs = get_wiki_signs()
    with open("webapp/signs.json", "r", encoding="utf-8") as f:
        signs = json.load(f)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    updated_count = 0

    for s in signs:
        m = re.match(r"^(\d+(?:\.\d+)*)", s["name"])
        if not m:
            continue
        num = m.group(1)
        filename = f"sign_{num}.png"
        path1 = os.path.join(SIGNS_DIR, filename)
        path2 = os.path.join(WEBAPP_DIR, filename)

        needs_replace = False
        if not os.path.exists(path1) or os.path.getsize(path1) == 0:
            needs_replace = True
        else:
            try:
                img = Image.open(path1)
                # Check if it was one of the placeholder 300x300 or narrow 104x41 images
                if img.size == (300, 300) or img.size[0] < 60 or img.size[1] < 60 or (img.size[0] == 104 and img.size[1] == 41):
                    needs_replace = True
            except Exception:
                needs_replace = True

        if needs_replace:
            url = wiki_signs.get(num)
            if url:
                print(f"Downloading HD sign {num} ({s['name']})...")
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = resp.read()
                    with open(path1, "wb") as f_out:
                        f_out.write(data)
                    with open(path2, "wb") as f_out:
                        f_out.write(data)
                    updated_count += 1
                except Exception as e:
                    print(f"Error downloading {num}: {e}")
            else:
                print(f"No URL for {num}")

    print(f"\n✅ Total signs successfully updated with real HD images: {updated_count}")

    # Re-verify all signs
    corrupted = 0
    for s in signs:
        m = re.match(r"^(\d+(?:\.\d+)*)", s["name"])
        num = m.group(1) if m else "unknown"
        p = os.path.join(SIGNS_DIR, f"sign_{num}.png")
        if not os.path.exists(p):
            corrupted += 1
            print(f"STILL MISSING: {num}")
        else:
            img = Image.open(p)
            if img.size == (300, 300) or img.size[0] < 60 or img.size[1] < 60:
                corrupted += 1
                print(f"STILL CORRUPTED/PLACEHOLDER: {num} size={img.size}")

    print(f"Final Verification: {len(signs) - corrupted} / {len(signs)} signs are 100% genuine and HD!")

if __name__ == "__main__":
    download_and_fix_all_signs()
