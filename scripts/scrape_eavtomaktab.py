"""
e-avtomaktab.uz saytidan ma'lumotlarni tahlil qilish va kerakli materiallarni ko'chirib olish skripti.
"""
import urllib.request
import re
import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'uz,ru;q=0.9,en;q=0.8'
}

def fetch_url(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def parse_test_page():
    url = "https://e-avtomaktab.uz/Home/Test"
    print(f"📡 {url} sahifasi yuklanmoqda...")
    html = fetch_url(url)
    
    # Savollarni ajratib olish
    q_blocks = re.findall(r'<div class="allquestions" id="question_(\d+)">([\s\S]*?)</div>\s*</div>\s*</div>\s*</div>', html)
    print(f"✅ Ushbu test sessiyasida topilgan savollar soni: {len(q_blocks)} ta")
    
    # Rasmlarni aniqlash
    img_urls = re.findall(r'src=["\']([^"\']+\.(?:png|jpg|jpeg|gif|svg))["\']', html)
    print(f"🖼 Topilgan rasmlar soni: {len(set(img_urls))} ta")
    
    return len(q_blocks), len(set(img_urls))

if __name__ == "__main__":
    try:
        q_count, img_count = parse_test_page()
        print("\n🎉 e-avtomaktab.uz sayti bilan to'liq aloqa o'rnatildi va tahlil qilindi!")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
