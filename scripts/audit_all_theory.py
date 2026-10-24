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

# Regex for pure theory topics
pure_theory_patterns = [
    # Medical / First Aid
    r'tibbiy yordam', r'birinchi yordam', r'lat yeganda', r'singanda', r'jarohat',
    r'qon ketgand', r'jgut', r'bint', r'nafas', r'yurak', r'ko\'krak qafas',
    r'bosh suyagi', r'umurtqa', r'tos suyaklar', r'sonning yumshoq', r'tizzasi',
    r'reaksiya va diqqatni pasaytiruvchi dori',
    
    # Definitions
    r'kimlar\s+["\']?yo\'l harakati qatnashchisi["\']?',
    r'atamasi nimani bildiradi', r'atamasi qanday ma\'no', r'atamasi bilan nima tushuniladi',
    r'deganda nima tushuniladi', r'atamasi qoidalar', r'haydovchi hisoblanadimi\?',
    
    # Legal, Fines, Documents
    r'haydovchilik guvohnomas', r'ishonchnoma', r'sug\'urta', r'texnik ko\'rik',
    r'dyhxx ruxsatisiz', r'hujjatlar.*taqdim', r'ma\'muriy javobgarlik', r'jinoiy javobgarlik',
    r'jarima', r'yo\'l-transport hodisasiga daxldor', r'moddiy zarar esa ahamiyatsiz bo\'lsa',
    
    # Lighting & Signals Theory
    r'kunduzgi vaqtda yaqinni yorituvchi fara',
    r'ogohlantirish ishorasi bo\'ladimi',
    r'ogohlantiruvchi ishora.*berish.*shart',
    r'ogohlantirish ishorasini berishni talab qilmaydi',
    r'manyovr vaqtida haydovchi har doim ogohlantiruvchi',
    r'burilish ko\'rsatkichlari bilan yorug\'lik ishorasini har doim berishi kerakmi',
    r'qayta tizilish oldidan ogohlantiruvchi ishora qachon',
    r'haydovchi ko\'zi qamashgan taqdirda',
    r'tumanga qarshi chiroqlardan qanday hollarda',
    r'fara chiroqlarini.*almashtirish',
    r'tovushli ishora.*qaysi hollarda',
    r'shatakka olingan.*qanday tashqi yoritish',
    r'shatakka olingan transport vositasidagi yoritish asboblar',
    r'tunnelda harakatlanayotganda qanday yoritish',
    r'kunning qorong\'u vaqtida.*qaysi chiroqlari yoqilgan bo\'lishi kerak',
    r'temir yo\'l kesishmasida umumiy xatar ishorasi',
    r'poezdni to\'xtatish ishorasi bo\'lib xizmat qiladi',
    
    # Physics & Safety
    r'tortish kuchi yo\'l bilan tishlashish kuchidan',
    r'sirpanib ketishini to\'xtatish',
    r'sirpanish boshlanganida to\'xtatish',
    r'sirpanchiq yo\'lda.*xavfsiz to\'xtash',
    r'sirpanchiq yo\'lda.*drossel zaslonkasi',
    r'markazdan qochma kuch',
    r'tormozlanish yo\'li necha marta ortadi',
    r'tormoz masofasi',
    r'inersiya kuchi',
    r'yonilg\'i sarfini tejaydi',
    r'kuchli tuman.*masofa.*tuyuladi',
    
    # Towing Theory
    r'avtomagistralda shatakka olishga ruxsat beriladimi',
    r'mopedlarni shatakka olishga ruxsat etiladimi',
    r'egiluvchan ulagichda shatakka olinganda qanday yuqori tezlik',
    r'egiluvchan ulagich.*qanchadan ortiq bo\'lmagan masofani',
    r'qattiq ulagich transport vositalari orasida',
    r'shatakka olish taqiqlanadi\?',
    r'shatakka olingan avtomobilda odamlarni tashishga',
    r'haydovchisi bo\'lmagan transport vositalarini shatakka olish',
    
    # Numerical limits without signs
    r'aholi punktlaridan tashqarida yengil avtomobillarning qanday eng katta tezlik',
    r'aholi punktlaridan tashqarida yuk avtomobil yukxonasida odamlarni tashishda qanday eng yuqori tezlik',
    r'turar-joy dahalarida.*qanday eng yuqori tezlik',
    r'harakat tezligini tanlashda haydovchiga taqiqlanadi',
    r'transport vositasi texnik tavsifnomasida ko\'rsatilgan yuqori tezlikdan',
    r'tezligi texnik tavsifnomasiga yoki holatiga ko\'ra 40 km/s dan kam bo\'lganda avtomagistral',
    r'40 km/s ga teng yoki undan ortiq tezlik bilan balandlikka chiqa olmasa',
    r'sekinyurar transport vositalarining temir yo\'l kesishmasi.*kam bo\'lganda',
    r'davlat yhx xizmatining ruxsatisiz.*qanday yuqori o\'lchamdagi balandlik',
    r'davlat yhx xizmati ruxsatisiz.*qanday yuqori maksimal kenglik',
    r'bir tirkamali avtopoezdning qanday eng katta uzunligida',
    
    # Vehicle Equipment & Defects
    r'shina protektori naqshlarining balandligi',
    r'bitta o\'qiga har xil naqshli shinalarni',
    r'rul chambagi.*lyuft',
    r'tormoz tizimi.*nosoz bo\'lganda',
    r'tibbiyot qutichasi va o\'t o\'chirgich bo\'lmagan',
    r'boshqarishni o\'rgatishdagi transport vositasi qanday jihozlangan',
    r'pnevmatik tormoz yuritmasining manometri',
    r'qanday hollarda transport vositasidan foydalanishga ruxsat etiladi\?',
    r'qanday hollarda transport vositalaridan foydalanishga ruxsat etiladi\?',
    r'sanab o\'tilgan qaysi holatlarda transport vositasidan foydalanish taqiqlanadi\?',
    
    # Verbal rules & General prohibitions
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
    r'agar haydovchi transport vositasining eshigini ochishga va undan chiqishga qaror qilsa',
    r'qaysi joylarda orqa bilan harakatlanish taqiqlanadi',
    r'ajratuvchi mintaqa bo\'lganda piyodalarning o\'tishlariga ruxsat etiladimi',
    r'avtomagistralda ajratuvchi mintaqaning uzilishlariga kirishga ruxsat etiladimi',
    r'burilish vaqtida qatnov qismining kesishmasidan chiqishda transport vositasi qayerda bo\'lmasligi kerak',
    r'ko\'zi ojiz piyodalarni o\'tkazib yuborishi kerakmi',
    r'agar qatnov qismining kengligi chetki chap tasmadan qayrilish uchun yetarli bo\'lmasa',
    r'qayrilish taqiqlanadi:',
    r'aholi punktlarida ma\'lum harakat tezligiga rioya etayotgan yirik o\'lchamli',
    r'zanjirli bo\'lgan qishloq xo\'jalik.*temir yo\'l kesishmasidan o\'tishga',
    r'qanday hollarda quvib o\'tish taqiqlanadi\?'
]

pure_regex = re.compile('|'.join(pure_theory_patterns), re.IGNORECASE)

# Check override:
# Explicit visual keywords:
# "ushbu yo'l belgisi", "mazkur belgi", "bu belgi", "qaysi belgi", "quyidagi belgilar", "ushbu chiziq",
# "mazkur chiziq", "ushbu svetofor", "chorrahadan birinchi", "chorrahada", "qizil avtomobil"
visual_phrases = [
    r'ushbu yo\'l belgisi', r'mazkur yo\'l belgisi', r'bu yo\'l belgisi', r'ushbu belgi',
    r'mazkur belgi', r'bu belgi', r'qaysi belgi', r'quyidagi belgilar', r'bunday belgi',
    r'ushbu chiziq', r'mazkur chiziq', r'bu chiziq', r'ushbu tik chiziq', r'bu tik yo\'l chizig\'i',
    r'ushbu svetofor', r'mazkur svetofor', r'chorrahadan birinchi', r'chorrahani birinchi',
    r'chorrahadan ikkinchi', r'chorrahadan oxirgi', r'tartibda o\'tadilar', r'tartibda o‘tadilar',
    r'suratdagi', r'rasmdagi', r'ushbu vaziyatda', r'mazkur vaziyatda', r'ko\'rsatilgan vaziyatda',
    r'koʻrsatilgan vaziyatda', r'ushbu holatda', r'mazkur holatda', r'ko\'rsatilgan holatda',
    r'koʻrsatilgan holatda', r'yo\'naltirgichlarning qaysilari', r'qaysi yo\'nalishda harakatlanishga ruxsat',
    r'qaysi yo\'nalishlarda harakatlanishga ruxsat', r'qaysi transport vositasiga harakatlanish ruxsat',
    r'harakatlanish kimga ruxsat etilgan\?', r'harakatlanish taqiqlanadi:',
    r'qizil avtomobil', r'sariq avtomobil', r'yashil avtomobil', r'ko\'k avtomobil', r'oq avtomobil'
]
visual_regex = re.compile('|'.join(visual_phrases), re.IGNORECASE)

audit_results = []
clear_count = 0

for q in questions:
    qid = q["id"]
    text = q["text"].strip()
    img = q["image_url"]
    
    is_pure = bool(pure_regex.search(text))
    has_visual = bool(visual_regex.search(text))
    
    action = "KEEP"
    reason = "Normal"
    
    if img:
        if is_pure and not has_visual:
            action = "CLEAR_IMAGE"
            reason = "Pure theory question wrongly assigned an image"
            clear_count += 1
        elif not is_pure and not has_visual:
            # Let's check further
            pass
            
    audit_results.append({
        "id": qid,
        "category": q["category"],
        "text": text,
        "image_url": img,
        "action": action,
        "reason": reason
    })

print(f"Total to clear images: {clear_count}")
with open("scratch/audit_results_clear.json", "w", encoding="utf-8") as f:
    json.dump([r for r in audit_results if r["action"] == "CLEAR_IMAGE"], f, ensure_ascii=False, indent=2)

con.close()
