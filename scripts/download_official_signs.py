"""
O'zbekiston Yo'l Belgilarini (Wikipedia / Wikimedia Commons) HD Rasmlari Bilan
Yuklab Olish va Bazaga Yuklash Skripti
"""
import os
import sys
import re
import json
import sqlite3
import urllib.request
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
SIGNS_DIR = os.path.join(BASE_DIR, "webapp", "images", "signs")
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "images", "signs")

os.makedirs(SIGNS_DIR, exist_ok=True)
os.makedirs(WEBAPP_DIR, exist_ok=True)

WIKI_HTML_PATH = r"C:\Users\user\.gemini\antigravity-ide\brain\14475f2f-e975-4fab-96ae-9046a6f7ff05\.system_generated\steps\701\content.md"

# Kategoriya xaritasi
CATEGORY_MAP = {
    "1": "ogohlantiruvchi",
    "2": "imtiyozli",
    "3": "taqiqlovchi",
    "4": "buyuruvchi",
    "5": "axborot",
    "6": "servis",
    "7": "qushimcha"
}

# O'zbekcha nomlar va tushuntirishlar lug'ati
UZ_DESCRIPTIONS = {
    "ogohlantiruvchi": "Haydovchilarni yo'lning xavfli qismiga yaqinlashayotganligi haqida ogohlantiradi.",
    "imtiyozli": "Chorrahalar, qatnov qismlari kesishuvlari va yo'lning tor qismlarida harakatlanish navbatini belgilaydi.",
    "taqiqlovchi": "Harakatlanishga ma'lum cheklovlar kiritadi yoki ularni bekor qiladi.",
    "buyuruvchi": "Faqat ko'rsatilgan yo'nalishlarda yoki belgilangan tezlikda harakatlanishni buyuradi.",
    "axborot": "Harakatlanish rejimi xususiyatlari yoki aholi punktlari va boshqa ob'ektlar haqida axborot beradi.",
    "servis": "Tegishli xizmat ko'rsatish ob'ektlari (AYoQSh, oshxona, shifoxona va hk) haqida ma'lumot beradi.",
    "qushimcha": "Ular bilan birga qo'llanilgan belgilarga aniqlik kiritadi yoki ularning ta'sirini cheklaydi."
}

def parse_and_download_signs():
    print("1. Wikipedia maqolasidan yo'l belgilari tahlil qilinmoqda...")
    with open(WIKI_HTML_PATH, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    galleries = soup.find_all("ul", class_="gallery")
    
    signs_data = []
    
    for g in galleries:
        for li in g.find_all("li", class_="gallerybox"):
            img = li.find("img")
            caption = li.find("div", class_="gallerytext")
            if not img or not caption:
                continue
                
            src = img.get("src", "")
            raw_text = caption.get_text(strip=True)
            
            # Masalan: "1.1 Railway crossing with a barrier"
            m = re.match(r"^(\d+(?:\.\d+)*)\s*(.*)$", raw_text)
            if not m:
                continue
                
            sign_num = m.group(1)
            sign_en_name = m.group(2)
            
            # Wikimedia yuqori sifatli (HQ) rasm havolasini olish (thumb o'lchamini 240px ga oshirish)
            # URL: //upload.wikimedia.org/wikipedia/commons/thumb/4/4a/RU_road_sign_1.1.svg/120px-RU_road_sign_1.1.svg.png
            clean_url = src.split("?")[0]
            if not clean_url.startswith("http"):
                clean_url = "https:" + clean_url
            
            # Kattaroq rasm olish uchun /120px- ni /300px- ga almashtiramiz
            hd_url = re.sub(r'/\d+px-', '/300px-', clean_url)
            
            # Fayl nomi
            filename = f"sign_{sign_num}.png"
            local_path1 = os.path.join(SIGNS_DIR, filename)
            local_path2 = os.path.join(WEBAPP_DIR, filename)
            
            signs_data.append({
                "num": sign_num,
                "name": f"{sign_num} {sign_en_name}",
                "en_name": sign_en_name,
                "url": hd_url,
                "filename": filename,
                "rel_path": f"webapp/images/signs/{filename}",
                "local_path1": local_path1,
                "local_path2": local_path2
            })

    print(f"2. {len(signs_data)} ta yo'l belgilari topildi. Rasmlar yuklab olinmoqda...")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    downloaded = 0
    
    for s in signs_data:
        try:
            req = urllib.request.Request(s["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                with open(s["local_path1"], "wb") as f_out:
                    f_out.write(data)
                with open(s["local_path2"], "wb") as f_out:
                    f_out.write(data)
                downloaded += 1
        except Exception as e:
            # Fallback to direct url
            try:
                req = urllib.request.Request(s["url"].replace('/300px-', '/120px-'), headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    with open(s["local_path1"], "wb") as f_out:
                        f_out.write(data)
                    with open(s["local_path2"], "wb") as f_out:
                        f_out.write(data)
                    downloaded += 1
            except Exception as e2:
                print(f"Error downloading {s['num']}: {e2}")

    print(f"   Muvaffaqiyatli yuklab olindi: {downloaded} ta haqiqiy yo'l belgisi rasmi!")

    # 3. Bazadagi nomlarni o'zbekcha bilan boyitish
    print("3. SQLite bazasi va webapp/signs.json yangilanmoqda...")
    
    # O'zbekcha nomlar lug'atini webapp/signs.json dan yoki mavjud bazadan olamiz
    existing_uz_names = {}
    if os.path.exists("webapp/signs.json"):
        with open("webapp/signs.json", "r", encoding="utf-8") as f:
            ex_list = json.load(f)
            for ex in ex_list:
                m_ex = re.match(r"^(\d+(?:\.\d+)*)\s*(.*)$", ex.get("name", ""))
                if m_ex:
                    existing_uz_names[m_ex.group(1)] = m_ex.group(2)
                    if ex.get("description"):
                        existing_uz_names[f"{m_ex.group(1)}_desc"] = ex.get("description")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM signs")
    
    webapp_signs = []
    
    for idx, s in enumerate(signs_data, start=1):
        num = s["num"]
        prefix = num.split(".")[0]
        category = CATEGORY_MAP.get(prefix, "axborot")
        
        uz_name = existing_uz_names.get(num) or s["en_name"]
        full_name = f"{num} {uz_name}"
        desc = existing_uz_names.get(f"{num}_desc") or UZ_DESCRIPTIONS.get(category, "")
        
        rel_path = f"webapp/images/signs/{s['filename']}"
        
        cur.execute("""
            INSERT INTO signs (id, category, name, image_url, description, example)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (idx, category, full_name, rel_path, desc, "Yo'l harakati qoidalariga muvofiq amal qilinishi shart."))
        
        webapp_signs.append({
            "id": idx,
            "category": category,
            "name": full_name,
            "image_url": f"images/signs/{s['filename']}",
            "description": desc,
            "example": "Yo'l harakati qoidalariga muvofiq amal qilinishi shart."
        })

    con.commit()
    con.close()

    with open("webapp/signs.json", "w", encoding="utf-8") as f:
        json.dump(webapp_signs, f, ensure_ascii=False, indent=2)
    if os.path.exists("webapp/avtomaktab-webapp/signs.json"):
        with open("webapp/avtomaktab-webapp/signs.json", "w", encoding="utf-8") as f:
            json.dump(webapp_signs, f, ensure_ascii=False, indent=2)

    print(f"✅ BARCHA {len(webapp_signs)} TA YO'L BELGISI HD FORMATDA TO'LIQ O'RNATILDI!")

if __name__ == "__main__":
    parse_and_download_signs()
