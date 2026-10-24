import json
import sqlite3
import re

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, image_url, option_a, option_b, option_c, option_d, correct_option, explanation, media_urls
    FROM questions 
    ORDER BY id
""")
rows = cur.fetchall()

questions = []
for r in rows:
    questions.append({
        "id": r[0],
        "category": r[1],
        "text": r[2],
        "image_url": r[3],
        "option_a": r[4],
        "option_b": r[5],
        "option_c": r[6],
        "option_d": r[7],
        "correct_option": r[8],
        "explanation": r[9],
        "media_urls": r[10]
    })

print(f"Total questions in database: {len(questions)}")

# Keywords that definitely prove a question is PURE TEXT and should NEVER have an image:
pure_text_patterns = [
    # 1. First Aid
    r'tibbiy yordam', r'birinchi yordam', r'lat yeganda', r'singanda', r'jarohatlangand',
    r'qon ketgand', r'jgut', r'bint', r'shina qo\'yish', r'nafas', r'yurak', r'ko\'krak qafas',
    r'bosh suyagi', r'umurtqa', r'tos suyaklar', r'sonning yumshoq', r'tizzasi',
    
    # 2. General definitions and concepts
    r'kimlar\s+["\']?yo\'l harakati qatnashchisi["\']?',
    r'atamasi nimani bildiradi', r'atamasi qanday ma\'no', r'atamasi bilan nima tushuniladi',
    r'ruxsat etilgan to\'la vazn atamasi', r'majburiy to\'xtash atamasi', r'yetarlicha ko\'rinmaslik atamasi',
    
    # 3. Documents, licenses, fines, responsibilities
    r'haydovchilik guvohnomas', r'ishonchnoma', r'sug\'urta', r'texnik ko\'rik',
    r'yo\'l-patrul xizmati xodimi talab qilgand', r'dyhxx ruxsatisiz', r'hujjatlar.*taqdim',
    r'ma\'muriy javobgarlik', r'jinoiy javobgarlik', r'jarima', r'yo\'l-transport hodisasiga daxldor',
    
    # 4. Lighting and warning signals rules (in words, without sign reference)
    r'kunduzgi vaqtda yaqinni yorituvchi fara',
    r'ogohlantirish ishorasi bo\'ladimi',
    r'ogohlantiruvchi ishora.*berish.*shart',
    r'ogohlantirish ishorasini berishni talab qilmaydi',
    r'manyovr vaqtida haydovchi har doim ogohlantiruvchi',
    r'burilish ko\'rsatkichlari bilan yorug\'lik ishorasini har doim berishi kerakmi',
    r'haydovchi ko\'zi qamashgan taqdirda',
    r'tumanga qarshi chiroqlardan qanday hollarda',
    r'fara chiroqlarini.*almashtirish',
    r'tovushli ishora.*qaysi hollarda',
    r'shatakka olingan.*qanday tashqi yoritish',
    r'shatakka olingan transport vositasidagi yoritish',
    r'tunnelda harakatlanayotganda qanday yoritish',
    r'kunning qorong\'u vaqtida.*qaysi chiroqlari yoqilgan bo\'lishi kerak',
    r'temir yo\'l kesishmasida umumiy xatar ishorasi',
    r'poezdni to\'xtatish ishorasi bo\'lib xizmat qiladi',
    
    # 5. Physics and driving safety theory
    r'tortish kuchi yo\'l bilan tishlashish kuchidan',
    r'sirpanib ketishini to\'xtatish',
    r'sirpanish boshlanganida to\'xtatish',
    r'sirpanchiq yo\'lda.*xavfsiz to\'xtash',
    r'markazdan qochma kuch',
    r'tormozlanish yo\'li necha marta ortadi',
    r'tormoz masofasi',
    r'inersiya kuchi',
    r'yonilg\'i sarfini tejaydi',
    r'kuchli tuman.*masofa.*tuyuladi',
    
    # 6. Towing rules (pure words, distance, speed)
    r'avtomagistralda shatakka olishga ruxsat beriladimi',
    r'egiluvchan ulagichda shatakka olinganda qanday yuqori tezlik',
    r'egiluvchan ulagich.*qanchadan ortiq bo\'lmagan masofani',
    r'qattiq ulagich transport vositalari orasida',
    r'shatakka olish taqiqlanadi\?',
    r'qanday hollarda haydovchisi bo\'lmagan transport vositalarini shatakka olish',
    
    # 7. Speed limits in words (pure numbers)
    r'aholi punktlaridan tashqarida yengil avtomobillarning qanday eng katta tezlik',
    r'aholi punktlaridan tashqarida yuk avtomobil yukxonasida odamlarni tashishda qanday eng yuqori tezlik',
    r'turar-joy dahalarida.*qanday eng yuqori tezlik',
    
    # 8. Vehicle equipment and technical defects
    r'shina protektori naqshlarining balandligi',
    r'bitta o\'qiga har xil naqshli shinalarni',
    r'rul chambagi.*lyuft',
    r'tormoz tizimi.*nosoz bo\'lganda',
    r'tibbiyot qutichasi va o\'t o\'chirgich bo\'lmagan',
    r'boshqarishni o\'rgatishdagi transport vositasi qanday jihozlangan',
    r'pnevmatik tormoz yuritmasining manometri',
    
    # 9. Pedestrian, cyclist and passenger rules (pure words)
    r'velosipedchilarga qatnov qismining o\'ng chekkasidan chiqishga yo\'l qo\'yiladi',
    r'velosipedchilarda trotuarda harakatlanishga ruxsat etiladimi',
    r'odamlarni tashishga moslashtirilmagan yuk avtomobili',
    r'bolalarni tashishga ruxsat etiladimi',
    r'haydovchi piyodalarga qachon yo\'l berishi kerak\?',
    r'transport vositasini orqaga harakatlantirish paytida haydovchi qanday talablarni',
    r'haydovchi harakatlanishni boshlashidan oldin qanday amallarni',
    r'transport vositasi qachon faqat o\'ng chetki tasmada harakatlanishi kerak',
    r'uchtadan kam tasmasi bo\'lgan yo\'lda to\'xtash va to\'xtab turish taqiqlanadi',
    r'agar transport vositasi o\'lchamlari kattaligidan.*chetga chiqqan holda burilishga',
    r'agar haydovchi transport vositasining eshigini ochishga va undan chiqishga qaror qilsa'
]

compiled_pure_regex = re.compile('|'.join(pure_text_patterns), re.IGNORECASE)

# Exceptions where visual is explicitly mentioned
visual_override = re.compile(r'ushbu belgi|mazkur belgi|bu belgi|qaysi belgi|chiziq|chorraha|rasmdagi|suratdagi|svetofor', re.IGNORECASE)

to_clear_image = []
to_keep_image = []

for q in questions:
    qid = q["id"]
    text = q["text"].strip()
    img = q["image_url"]
    
    if not img:
        continue
        
    # Check if this question is pure theory
    is_pure = bool(compiled_pure_regex.search(text))
    has_visual = bool(visual_override.search(text))
    
    # If pure text without visual override, must NOT have image
    if is_pure and not has_visual:
        to_clear_image.append(q)
    else:
        to_keep_image.append(q)

print(f"Questions with images: {len(to_clear_image) + len(to_keep_image)}")
print(f"Confirmed PURE THEORY with WRONG image (TO CLEAR): {len(to_clear_image)}")
print(f"Legitimate visual questions (TO KEEP/VERIFY): {len(to_keep_image)}")

print("\n--- DETAILED LIST OF PURE THEORY QUESTIONS WRONGLY SHOWING IMAGES ---")
for q in to_clear_image:
    print(f"ID {q['id']:3d} | {q['category']:8s} | WRONG IMG: {q['image_url']:25s} | TEXT: {q['text'][:70]}")

with open("scratch/to_clear_images.json", "w", encoding="utf-8") as f:
    json.dump(to_clear_image, f, ensure_ascii=False, indent=2)

con.close()
