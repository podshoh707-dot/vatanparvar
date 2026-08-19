"""
e-avtomaktab.uz saytidan barcha testlar va video darslarni to'liq yuklab olish va tahlil qilish skripti.
"""
import urllib.request
import re
import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'uz,ru;q=0.9,en;q=0.8'
}

def fetch_url(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def inspect_site_endpoints():
    print("="*60)
    print("🌐 e-avtomaktab.uz SAYTI BO'LIMLARINI TEKSHIRISH")
    print("="*60)
    
    urls = [
        "https://e-avtomaktab.uz/",
        "https://e-avtomaktab.uz/Home/Test",
        "https://e-avtomaktab.uz/Home/IndexRU",
        "https://e-avtomaktab.uz/Home/CheckPayment"
    ]
    
    video_links = set()
    image_links = set()
    
    for u in urls:
        try:
            html = fetch_url(u)
            print(f"✅ {u} — yuklandi ({len(html)} bayt)")
            
            # YouTube yoki video havolalarni qidirish
            vids = re.findall(r'(?:https?://(?:www\.)?(?:youtube\.com|youtu\.be|vimeo\.com)[^\s"\'<>]+|\/videos\/[^\s"\'<>]+)', html)
            for v in vids:
                video_links.add(v)
                
            # Rasmlarni qidirish
            imgs = re.findall(r'src=["\']([^"\']+\.(?:png|jpg|jpeg|svg|webp|mp4))["\']', html)
            for img in imgs:
                image_links.add(img)
        except Exception as e:
            print(f"❌ {u} xato: {e}")
            
    print(f"\n🎬 Topilgan video havolalar: {len(video_links)} ta")
    for v in list(video_links)[:10]:
        print(f"   • {v}")
        
    print(f"\n🖼 Topilgan rasm va media fayllar: {len(image_links)} ta")
    for img in list(image_links)[:15]:
        print(f"   • {img}")

if __name__ == "__main__":
    inspect_site_endpoints()
