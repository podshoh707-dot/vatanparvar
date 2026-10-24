"""
Savol rasmlarini 100% tiniqlashtirish, kontrastini oshirish va HD formatga keltirish moduli.
"""
import os
import hashlib
from PIL import Image, ImageEnhance, ImageFilter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "images", "hd_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_enhanced_image_path(original_path: str) -> str:
    """
    Berilgan rasm yo'lini oladi, uni tiniqlashtirib, kontrastini kuchaytiradi
    va keshdan yuqori sifatli HD nusxasining yo'lini qaytaradi.
    """
    if not original_path or not os.path.exists(original_path):
        return original_path

    # Fayl nomiga qarab kesh kaliti yaratish
    file_stat = os.stat(original_path)
    cache_key = hashlib.md5(f"{original_path}_{file_stat.st_mtime}_{file_stat.st_size}".encode()).hexdigest()
    cached_file = os.path.join(CACHE_DIR, f"hd_{cache_key}.jpg")

    if os.path.exists(cached_file):
        return cached_file

    try:
        with Image.open(original_path) as img:
            # Agar RGBA bo'lsa, RGB ga o'tkazish
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            w, h = img.size

            # Agar rasm juda kichik bo'lsa (< 1000px), uni sifatli kattalashtirish (Lanczos)
            if w < 1000 or h < 600:
                scale = max(1000 / max(w, 1), 600 / max(h, 1))
                if scale > 1.0:
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 1. Kontrastni kuchaytirish (yo'l belgilari va chiziqlar aniq ajralishi uchun)
            enhancer_contrast = ImageEnhance.Contrast(img)
            img = enhancer_contrast.enhance(1.12)

            # 2. Rang to'yinganligini biroz oshirish (svetofor va yo'l belgilari yorqin chiqishi uchun)
            enhancer_color = ImageEnhance.Color(img)
            img = enhancer_color.enhance(1.10)

            # 3. Aniqlikni (Sharpness) oshirish
            enhancer_sharpness = ImageEnhance.Sharpness(img)
            img = enhancer_sharpness.enhance(1.35)

            # 4. UnsharpMask filtri (detallar, harflar va chiziqlarni o'tkir qilish)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.8, percent=150, threshold=2))

            # 5. Yuqori sifatli JPEG formatda saqlash (quality=95, subsampling=0)
            img.save(cached_file, "JPEG", quality=95, subsampling=0, optimize=True)

            return cached_file
    except Exception as e:
        print(f"[ImageEnhancer Error] {original_path}: {e}")
        return original_path
