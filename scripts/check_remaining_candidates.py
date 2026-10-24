import json

with open("scratch/to_clear_images.json", "r", encoding="utf-8") as f:
    cleared_ids = set(q["id"] for q in json.load(f))

with open("scratch/all_805_questions.json", "r", encoding="utf-8") as f:
    all_qs = json.load(f)

remaining_with_imgs = [q for q in all_qs if q["image_url"] and q["id"] not in cleared_ids]
print(f"Remaining questions with images: {len(remaining_with_imgs)}")

# Check questions that might still be pure text:
# e.g., questions with options like: "Ruxsat etiladi", "Taqiqlanadi", "Yo'l qo'yilmaydi"
# or questions that do NOT contain words:
# 'belgi', 'chiziq', 'svetofor', 'chorraha', 'avtomobil', 'transport', 'rasm', 'surat', 'yo\'nalish'
candidates = []
for q in remaining_with_imgs:
    t = q["text"].lower()
    img = q["image_url"]
    
    # Check if text does NOT mention any visual elements
    has_visual_element = any(w in t for w in [
        'belgi', 'chiziq', 'svetofor', 'chorraha', 'avtomobil', 'motosikl', 'tramvay',
        'avtobus', 'yo\'naltirgich', 'tartibga soluvchi', 'qaysi biri', 'tartibda',
        'o\'tadi', 'oʻtadi', 'o\'tadilar', 'oʻtadilar', 'yo\'l beradi', 'yoʻl beradi',
        'ustunlik', 'harakatlanish tartibi', 'quvib o\'tish', 'quvib o‘tish',
        'to\'xtash', 'toʻxtash', 'to\'xtab turish', 'toʻxtab turish',
        'rasm', 'surat', 'chiroq'
    ])
    if not has_visual_element:
        candidates.append(q)

print(f"Candidates with NO obvious visual elements: {len(candidates)}")
for q in candidates:
    print(f"ID {q['id']} ({q['category']}): {q['text']}")
    print(f"   IMG: {q['image_url']}\n")
