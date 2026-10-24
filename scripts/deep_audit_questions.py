import json
import re

with open("scratch/all_805_questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

pure_theory_patterns = [
    r'tibbiy yordam', r'singanda', r'lat yeganda', r'qon ketgand', r'jgut', r'bint', r'nafas', r'shina.*protektor',
    r'hujjat.*talab', r'ishonchnoma', r'guvohnoma', r'sug\'urta', r'javobgarlik', r'jarima', r'tormoz yo\'li',
    r'inersiya', r'tortish kuchi', r'markazdan qochma', r'sirpanish', r'tishlashish kuch', r'kunning qorong\'i vaqtida.*fara',
    r'kunduzgi vaqtda.*fara', r'yaqinni yorituvchi fara', r'uzoqni yorituvchi', r'ko\'zi qamashgand',
    r'ogohlantirish ishorasi.*bo\'ladimi', r'ogohlantiruvchi ishora.*berish', r'tovushli ishora',
    r'kimlar.*yo\'l harakati qatnashchisi', r'atamasi nimani bildiradi', r'atamasi qanday ma\'no',
    r'qanday holatlarda.*shatakka olish taqiqlanadi', r'egiluvchan ulagichda.*shatakka',
    r'bolalarni tashish', r'odamlarni tashish', r'yo\'lovchilarning majburiyat', r'piyodalarning majburiyat',
    r'haydovchining majburiyat', r'boshqarish huquqini beruvchi', r'rul boshqaruvi.*lyuft',
    r'tormoz tizimi.*nosoz', r'tashqi yoritish asboblari.*nosoz', r'harakatlanish tezligi.*aholi punktlarida.*km/soat',
    r'turar-joy dahalarida.*km/soat', r'avtomagistralda.*km/soat.*tezlik'
]

pure_theory_regex = re.compile('|'.join(pure_theory_patterns), re.IGNORECASE)

needs_image_patterns = [
    r'\bushbu belgi\b', r'\bmazkur belgi\b', r'\bbu belgi\b', r'\bqaysi belgi\b', r'\bquyidagi belgi\b',
    r'\bbunday belgi\b', r'\bbelgilarning ta\'sir\b', r'\bushbu yo\'l belgisi\b', r'\bmazkur yo\'l belgisi\b',
    r'\bchiziq\b', r'\bchiziqlar\b', r'\byo\'naltirgichlarning qaysilari\b', r'\brasmdagi\b', r'\bsuratdagi\b',
    r'\bchorrahada\b', r'\bchorrahani\b', r'\bchorrahadan\b', r'\bchorraha\b', r'\bqaysi avtomobil\b',
    r'\bqaysi transport\b', r'\btransport vositalari.*tartibda\b', r'\bko\'rsatilgan holatda\b',
    r'\bko\'rsatilgan vaziyatda\b', r'\bkoʻrsatilgan vaziyatda\b', r'\bshu holatda\b', r'\bshu joyda to\'xtash\b'
]
needs_image_regex = re.compile('|'.join(needs_image_patterns), re.IGNORECASE)

cat_a_pure_theory_has_wrong_img = []
cat_b_visual_has_img = []
cat_c_visual_missing_img = []
cat_d_pure_theory_no_img = []
cat_e_other = []

for q in questions:
    qid = q["id"]
    text = q["text"]
    img = q["image_url"]
    
    is_pure_theory = bool(pure_theory_regex.search(text))
    references_visual = bool(needs_image_regex.search(text))
    
    # If text explicitly says "ushbu belgi" or "chorraha", visual overrides pure theory
    if references_visual:
        if img:
            cat_b_visual_has_img.append(q)
        else:
            cat_c_visual_missing_img.append(q)
    elif is_pure_theory:
        if img:
            cat_a_pure_theory_has_wrong_img.append(q)
        else:
            cat_d_pure_theory_no_img.append(q)
    else:
        cat_e_other.append(q)

print(f"Total questions: {len(questions)}")
print(f"Cat A: Pure theory questions that WRONGLY have an image: {len(cat_a_pure_theory_has_wrong_img)}")
print(f"Cat B: Visual questions that have an image: {len(cat_b_visual_has_img)}")
print(f"Cat C: Visual questions missing an image: {len(cat_c_visual_missing_img)}")
print(f"Cat D: Pure theory correctly without image: {len(cat_d_pure_theory_no_img)}")
print(f"Cat E: Other/ambiguous questions: {len(cat_e_other)}")

print("\n--- SAMPLE CAT A (PURE THEORY WITH WRONG IMAGE) ---")
for q in cat_a_pure_theory_has_wrong_img[:15]:
    print(f"ID {q['id']} ({q['category']}): {q['text']}")
    print(f"   -> WRONG IMG: {q['image_url']}\n")

print("\n--- SAMPLE CAT E (AMBIGUOUS - CHECKING IMAGES) ---")
for q in cat_e_other[:15]:
    print(f"ID {q['id']} ({q['category']}): {q['text']} -> IMG: {q['image_url']}")
