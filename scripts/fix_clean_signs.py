"""
O'zbekiston Yo'l Belgilarini Toza Lotin Imlosida va HD Rasmlari Bilan Yangilash
Barcha buzuq belgilarni () to'g'rilaydi va haqiqiy rasmlarni biriktiradi.
"""
import os
import sys
import re
import json
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
SIGNS_DIR = os.path.join(BASE_DIR, "webapp", "images", "signs")
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp", "images", "signs")

os.makedirs(SIGNS_DIR, exist_ok=True)
os.makedirs(WEBAPP_DIR, exist_ok=True)

# Rasmiy O'zbekiston YHQ Yo'l belgilari to'liq lug'ati
OFFICIAL_SIGNS = [
    # 1. OGOHLANTIRUVCHI BELGILAR
    ("1.1", "ogohlantiruvchi", "Shlagbaumli temir yo'l kesishmasi", "Shlagbaum bilan jihozlangan temir yo'l kesishmasiga yaqinlashayotganlik haqida ogohlantiradi."),
    ("1.2", "ogohlantiruvchi", "Shlagbaumsiz temir yo'l kesishmasi", "Shlagbaum bilan jihozlanmagan temir yo'l kesishmasiga yaqinlashayotganlik haqida ogohlantiradi."),
    ("1.3.1", "ogohlantiruvchi", "Bir izli temir yo'l", "Shlagbaumsiz bir izli temir yo'l kesishmasi."),
    ("1.3.2", "ogohlantiruvchi", "Ko'p izli temir yo'l", "Shlagbaumsiz ikki va undan ortiq izli temir yo'l kesishmasi."),
    ("1.4.1", "ogohlantiruvchi", "Temir yo'l kesishmasiga yaqinlashish (o'ng tomon)", "Aholi punktlaridan tashqarida temir yo'l kesishmasiga yaqinlashish haqida qo'shimcha ogohlantirish."),
    ("1.4.2", "ogohlantiruvchi", "Temir yo'l kesishmasiga yaqinlashish (o'ng tomon)", "Aholi punktlaridan tashqarida temir yo'l kesishmasiga yaqinlashish haqida qo'shimcha ogohlantirish."),
    ("1.4.3", "ogohlantiruvchi", "Temir yo'l kesishmasiga yaqinlashish (o'ng tomon)", "Aholi punktlaridan tashqarida temir yo'l kesishmasiga yaqinlashish haqida qo'shimcha ogohlantirish."),
    ("1.4.4", "ogohlantiruvchi", "Temir yo'l kesishmasiga yaqinlashish (chap tomon)", "Aholi punktlaridan tashqarida temir yo'l kesishmasiga yaqinlashish haqida qo'shimcha ogohlantirish."),
    ("1.4.5", "ogohlantiruvchi", "Temir yo'l kesishmasiga yaqinlashish (chap tomon)", "Aholi punktlaridan tashqarida temir yo'l kesishmasiga yaqinlashish haqida qo'shimcha ogohlantirish."),
    ("1.4.6", "ogohlantiruvchi", "Temir yo'l kesishmasiga yaqinlashish (chap tomon)", "Aholi punktlaridan tashqarida temir yo'l kesishmasiga yaqinlashish haqida qo'shimcha ogohlantirish."),
    ("1.5", "ogohlantiruvchi", "Tramvay yo'li bilan kesishuv", "Chorrahadan tashqarida tramvay yo'li bilan kesishuv."),
    ("1.6", "ogohlantiruvchi", "Teng ahamiyatli yo'llar kesishuvi", "O'ngdan kelayotgan transport vositasiga yo'l berish qoidasi amal qiladigan chorraha."),
    ("1.7", "ogohlantiruvchi", "Aylanma harakatlanish bilan kesishuv", "Aylanma harakat tashkil etilgan chorrahaga yaqinlashayotganlik haqida ogohlantiradi."),
    ("1.8", "ogohlantiruvchi", "Svetofor bilan tartibga solish", "Harakat svetofor bilan tartibga solinadigan chorraha yoki yo'l qismi."),
    ("1.9", "ogohlantiruvchi", "Ko'tarma ko'prik", "Ko'tarma ko'prik yoki parom kechuviga yaqinlashayotganlik haqida ogohlantiradi."),
    ("1.10", "ogohlantiruvchi", "Sohilga chiqish", "Daryo, ko'l yoki suv havzasi sohiliga chiqish joyi."),
    ("1.11.1", "ogohlantiruvchi", "Xavfli burilish (o'ngga)", "Yo'lning ko'rinishi cheklangan o'ngga xavfli burilish qismi."),
    ("1.11.2", "ogohlantiruvchi", "Xavfli burilish (chapga)", "Yo'lning ko'rinishi cheklangan chapga xavfli burilish qismi."),
    ("1.12.1", "ogohlantiruvchi", "Xavfli burilishlar (birinchisi o'ngga)", "Ketma-ket keladigan xavfli burilishlar."),
    ("1.12.2", "ogohlantiruvchi", "Xavfli burilishlar (birinchisi chapga)", "Ketma-ket keladigan xavfli burilishlar."),
    ("1.13", "ogohlantiruvchi", "Tik nishablik", "Xavfli tik nishablik qismi."),
    ("1.14", "ogohlantiruvchi", "Tik balandlik", "Xavfli tik balandlikka ko'tarilish qismi."),
    ("1.15", "ogohlantiruvchi", "Sirpanchiq yo'l", "Qatnov qismi o'ta sirpanchiq bo'lgan yo'l qismi."),
    ("1.16", "ogohlantiruvchi", "Notekis yo'l", "Qatnov qismi to'lqinsimon, o'nqir-cho'nqir bo'lgan yo'l qismi."),
    ("1.17", "ogohlantiruvchi", "Tosh otilishi", "Transport vositalari g'ildiraklari ostidan tosh, shag'al otilishi mumkin bo'lgan yo'l qismi."),
    ("1.18.1", "ogohlantiruvchi", "Yo'lning torayishi (har ikki tomondan)", "Yo'lning qatnov qismi toraygan joyi."),
    ("1.18.2", "ogohlantiruvchi", "Yo'lning torayishi (o'ngdan)", "Yo'lning qatnov qismi o'ng tomondan toraygan joyi."),
    ("1.18.3", "ogohlantiruvchi", "Yo'lning torayishi (chapdan)", "Yo'lning qatnov qismi chap tomondan toraygan joyi."),
    ("1.19", "ogohlantiruvchi", "Ikki tomonlama harakat", "Qarama-qarshi harakatlanish boshlanadigan yo'l qismi."),
    ("1.20", "ogohlantiruvchi", "Piyodalar o'tish joyi", "Piyodalar o'tish joyiga yaqinlashayotganlik haqida ogohlantiradi."),
    ("1.21", "ogohlantiruvchi", "Bolalar", "Bolalar muassasalari yaqinidagi yo'l qismi."),
    ("1.22", "ogohlantiruvchi", "Velosiped yo'lkasi bilan kesishuv", "Velosiped yo'lkasi bilan kesishuv joyi."),
    ("1.23", "ogohlantiruvchi", "Ta'mirlash ishlari", "Yo'lda ta'mirlash ishlari olib borilayotgan joy."),
    ("1.24", "ogohlantiruvchi", "Mol haydab o'tish", "Chorva mollari haydab o'tiladigan yo'l qismi."),
    ("1.25", "ogohlantiruvchi", "Yovvoyi hayvonlar", "Yovvoyi hayvonlar chiqib qolish ehtimoli bo'lgan hudud."),
    ("1.26", "ogohlantiruvchi", "Toshlar qulashi", "Tosh ko'chkisi, tosh qulashi mumkin bo'lgan yo'l qismi."),
    ("1.27", "ogohlantiruvchi", "Yonlama shamol", "Kuchli yonlama shamol esadigan yo'l qismi."),
    ("1.28", "ogohlantiruvchi", "Pastlab uchuvchi samolyotlar", "Samolyotlar pastlab uchadigan aerodrom yaqini."),
    ("1.29", "ogohlantiruvchi", "Tunel", "Sun'iy yoritilmagan yoki ko'rinishi cheklangan tunel."),
    ("1.30", "ogohlantiruvchi", "Boshqa xavf-xatarlar", "Boshqa ogohlantiruvchi belgilar bilan ko'zda tutilmagan xavflar."),

    # 2. IMTIYOZ BELGILARI
    ("2.1", "imtiyozli", "Asosiy yo'l", "Tartibga solinmagan chorrahalarda haydovchiga birinchi bo'lib o'tish huquqini beradi."),
    ("2.2", "imtiyozli", "Asosiy yo'lning oxiri", "Asosiy yo'l imtiyozi tugaganini bildiradi."),
    ("2.3.1", "imtiyozli", "Ikkilamchi yo'l bilan kesishuv", "Asosiy yo'lda harakatlanayotganlikni bildiradi."),
    ("2.3.2", "imtiyozli", "Ikkilamchi yo'l tutashuvi (o'ngdan)", "O'ng tomondan ikkilamchi yo'l tutashgan joy."),
    ("2.3.3", "imtiyozli", "Ikkilamchi yo'l tutashuvi (chapdan)", "Chap tomondan ikkilamchi yo'l tutashgan joy."),
    ("2.4", "imtiyozli", "Yo'l bering", "Kesib o'tilayotgan asosiy yo'ldagi transport vositalariga yo'l berish shart."),
    ("2.5", "imtiyozli", "To'xtamasdan harakatlanish taqiqlangan (STOP)", "To'xtamasdan o'tish qat'iyan man etiladi."),
    ("2.6", "imtiyozli", "Ro'paradagi harakatlanishning ustunligi", "Tor yo'lda qarama-qarshi transportga yo'l berish shart."),
    ("2.7", "imtiyozli", "Ro'paradagi harakatlanishga nisbatan ustunlik", "Tor yo'lda birinchi bo'lib o'tish huquqini beradi."),

    # 3. TAQIQLOVCHI BELGILAR
    ("3.1", "taqiqlovchi", "Kirish taqiqlangan (G'isht)", "Barcha transport vositalarining kirishi taqiqlanadi."),
    ("3.2", "taqiqlovchi", "Harakatlanish taqiqlangan", "Barcha transport vositalarining harakatlanishi taqiqlanadi."),
    ("3.3", "taqiqlovchi", "Mexanik transport vositalari harakati taqiqlangan", "Mexanik transport vositalari harakati man etiladi."),
    ("3.4", "taqiqlovchi", "Yuk avtomobillari harakati taqiqlangan", "Ruxsat etilgan to'la vazni 3.5 tonnadan ortiq yuk mashinalari harakati man etiladi."),
    ("3.5", "taqiqlovchi", "Mototsikllar harakati taqiqlangan", "Mototsikllar harakati taqiqlanadi."),
    ("3.6", "taqiqlovchi", "Traktorlar harakati taqiqlangan", "Traktor va o'ziyurar moslamalar harakati taqiqlanadi."),
    ("3.7", "taqiqlovchi", "Tirkama bilan harakatlanish taqiqlangan", "Tirkamali yuk avtomobillari va tirkama ulovchilar harakati man etiladi."),
    ("3.8", "taqiqlovchi", "Ot-arava harakati taqiqlangan", "Ot-arava va minib yuruvchilar harakati taqiqlanadi."),
    ("3.9", "taqiqlovchi", "Velosipedlar harakati taqiqlangan", "Velosiped va mopedlar harakati taqiqlanadi."),
    ("3.10", "taqiqlovchi", "Piyodalar harakati taqiqlangan", "Piyodalarning harakatlanishi taqiqlanadi."),
    ("3.11", "taqiqlovchi", "Vazn cheklangan", "Haqiqiy vazni ko'rsatilgandan ortiq bo'lgan transport vositalari harakati taqiqlanadi."),
    ("3.12", "taqiqlovchi", "O'qqa tushadigan og'irlik cheklangan", "O'qqa tushadigan og'irligi ko'rsatilgandan ortiq transport harakati man etiladi."),
    ("3.13", "taqiqlovchi", "Balandlik cheklangan", "Gabarit balandligi ko'rsatilgandan ortiq transport harakati man etiladi."),
    ("3.14", "taqiqlovchi", "Kenglik cheklangan", "Gabarit kengligi ko'rsatilgandan ortiq transport harakati man etiladi."),
    ("3.15", "taqiqlovchi", "Uzunlik cheklangan", "Gabarit uzunligi ko'rsatilgandan ortiq transport harakati man etiladi."),
    ("3.16", "taqiqlovchi", "Minimal oraliq", "Ko'rsatilgandan kam oraliqda harakatlanish taqiqlanadi."),
    ("3.17.1", "taqiqlovchi", "Bojxona", "Bojxona punkti oldida to'xtamasdan o'tish taqiqlanadi."),
    ("3.17.2", "taqiqlovchi", "Xavf-xatar", "Yo'l-transport hodisasi yoki favqulodda holat sababli harakatlanish man etiladi."),
    ("3.17.3", "taqiqlovchi", "Nazorat punkti", "Nazorat punkti oldida to'xtamasdan o'tish taqiqlanadi."),
    ("3.18.1", "taqiqlovchi", "O'ngga burilish taqiqlangan", "Qatnov qismlarining eng yaqin kesishmasida o'ngga burilish man etiladi."),
    ("3.18.2", "taqiqlovchi", "Chapga burilish taqiqlangan", "Qatnov qismlarining eng yaqin kesishmasida chapga burilish man etiladi."),
    ("3.19", "taqiqlovchi", "Qayrilib olish taqiqlangan", "Qayrilib olish qat'iyan man etiladi."),
    ("3.20", "taqiqlovchi", "Quvib o'tish taqiqlangan", "Barcha transport vositalarini quvib o'tish taqiqlanadi."),
    ("3.21", "taqiqlovchi", "Quvib o'tish taqiqlangan zonaning oxiri", "3.20 belgisining ta'sir doirasi tugaganini bildiradi."),
    ("3.22", "taqiqlovchi", "Yuk avtomobillarida quvib o'tish taqiqlangan", "Yuk avtomobillariga quvib o'tish taqiqlanadi."),
    ("3.23", "taqiqlovchi", "Yuk avtomobillarida quvib o'tish taqiqlangan zonaning oxiri", "3.22 belgisi tugaganini bildiradi."),
    ("3.24", "taqiqlovchi", "Yuqori tezlik cheklangan", "Belgida ko'rsatilganidan ortiq tezlikda harakatlanish taqiqlanadi."),
    ("3.25", "taqiqlovchi", "Yuqori tezlik cheklangan zonaning oxiri", "Tezlik cheklovi bekor qilinganini bildiradi."),
    ("3.26", "taqiqlovchi", "Tovush signali berish taqiqlangan", "YTHning oldini olishdan boshqa hollarda signal chalish taqiqlanadi."),
    ("3.27", "taqiqlovchi", "To'xtash taqiqlangan", "Transport vositalarining to'xtashi va to'xtab turishi taqiqlanadi."),
    ("3.28", "taqiqlovchi", "To'xtab turish taqiqlangan", "Transport vositalarining to'xtab turishi taqiqlanadi."),
    ("3.29", "taqiqlovchi", "Oyning toq kunlarida to'xtab turish taqiqlangan", "Toq sanalarda to'xtab turish taqiqlanadi."),
    ("3.30", "taqiqlovchi", "Oyning juft kunlarida to'xtab turish taqiqlangan", "Juft sanalarda to'xtab turish taqiqlanadi."),
    ("3.31", "taqiqlovchi", "Barcha cheklovlarning oxiri", "Bir nechta taqiqlovchi belgilarning ta'siri tugaganini bildiradi."),

    # 4. BUYURUVCHI BELGILAR
    ("4.1.1", "buyuruvchi", "Harakatlanish to'g'riga", "Faqat to'g'riga harakatlanishga ruxsat etiladi."),
    ("4.1.2", "buyuruvchi", "Harakatlanish o'ngga", "Faqat o'ngga harakatlanishga ruxsat etiladi."),
    ("4.1.3", "buyuruvchi", "Harakatlanish chapga", "Faqat chapga yoki qayrilib olishga ruxsat etiladi."),
    ("4.1.4", "buyuruvchi", "Harakatlanish to'g'riga yoki o'ngga", "To'g'riga va o'ngga harakatlanishga ruxsat etiladi."),
    ("4.1.5", "buyuruvchi", "Harakatlanish to'g'riga yoki chapga", "To'g'riga, chapga va qayrilib olishga ruxsat etiladi."),
    ("4.1.6", "buyuruvchi", "Harakatlanish o'ngga yoki chapga", "O'ngga, chapga va qayrilib olishga ruxsat etiladi."),
    ("4.2.1", "buyuruvchi", "To'siqni o'ngdan chetlab o'tish", "To'siqni faqat o'ng tomondan aylanib o'tish buyuriladi."),
    ("4.2.2", "buyuruvchi", "To'siqni chapdan chetlab o'tish", "To'siqni faqat chap tomondan aylanib o'tish buyuriladi."),
    ("4.2.3", "buyuruvchi", "To'siqni o'ngdan yoki chapdan chetlab o'tish", "To'siqni har ikki tomondan chetlab o'tishga ruxsat beriladi."),
    ("4.3", "buyuruvchi", "Aylanma harakat", "Strelkalar ko'rsatgan yo'nalish bo'yicha aylanma harakatlanish buyuriladi."),
    ("4.4", "buyuruvchi", "Yengil avtomobillar harakati", "Faqat yengil avtomobillar, avtobus va mototsikllar harakatlanishi mumkin."),
    ("4.5", "buyuruvchi", "Velosiped yo'lkasi", "Faqat velosiped va mopedlar harakati."),
    ("4.6", "buyuruvchi", "Piyodalar yo'lkasi", "Faqat piyodalar harakati uchun ajratilgan maxsus yo'lka."),
    ("4.7", "buyuruvchi", "Eng kam tezlik belgilangan", "Ko'rsatilgan yoki undan yuqori tezlikda harakatlanish buyuriladi."),
    ("4.8", "buyuruvchi", "Eng kam tezlik belgilangan zonaning oxiri", "4.7 belgisining ta'siri tugaganini bildiradi."),

    # 5. AXBOROT-KO'RSATKICH BELGILARI
    ("5.1", "axborot", "Avtomagistral", "Avtomagistral qoidalari amal qiladigan tezyurar yo'l."),
    ("5.2", "axborot", "Avtomagistralning oxiri", "Avtomagistral qoidalari tugaganini bildiradi."),
    ("5.3", "axborot", "Avtomobillar uchun mo'ljallangan yo'l", "Faqat avtomobillar va mototsikllar harakati uchun yo'l."),
    ("5.4", "axborot", "Avtomobillar uchun mo'ljallangan yo'lning oxiri", "5.3 belgisi tugaganini bildiradi."),
    ("5.5", "axborot", "Bir tomonlama harakatli yo'l", "Transport vositalari butun kenglik bo'yicha bir yo'nalishda harakatlanadi."),
    ("5.6", "axborot", "Bir tomonlama harakatli yo'lning oxiri", "5.5 belgisi tugaganini bildiradi."),
    ("5.8.1", "axborot", "Tasmalar bo'yicha harakatlanish yo'nalishlari", "Chorrahada tasmalar bo'yicha ruxsat etilgan yo'nalishlar."),
    ("5.8.2", "axborot", "Tasma bo'yicha harakatlanish yo'nalishi", "Alohida tasma bo'yicha harakatlanish yo'nalishi."),
    ("5.15", "axborot", "Aholi punkti boshlanishi (oq fon)", "Aholi punktlaridagi harakat tartibi (maksimal 60 km/soat) amal qiladi."),
    ("5.16.1", "axborot", "Piyodalar o'tish joyi (o'ng tomon)", "Piyodalarning yo'lni kesib o'tishi uchun ajratilgan xavfsiz o'tish joyi."),
    ("5.16.2", "axborot", "Piyodalar o'tish joyi (chap tomon)", "Piyodalar o'tish joyining chap chegarasini belgilaydi."),
    ("5.17.1", "axborot", "Yer osti piyodalar o'tish joyi", "Yer osti xavfsiz piyodalar o'tish joyi."),
    ("5.17.2", "axborot", "Yer usti piyodalar o'tish joyi", "Yer usti (ko'prikli) piyodalar o'tish joyi."),
    ("5.19.1", "axborot", "Bir izli temir yo'l to'xtash joyi", "Temir yo'l bekatiga yaqin joy."),
    ("5.20.1", "axborot", "Avtobus yoki trolleybus to'xtash joyi", "Yo'nalishli transport vositalarining to'xtash punkti."),
    ("5.20.2", "axborot", "Tramvay to'xtash joyi", "Tramvaylarning yo'lovchi tushirish-chiqarish joyi."),
    ("5.21", "axborot", "Taksi to'xtab turish joyi", "Yo'nalishsiz taksilar uchun to'xtab turish joyi."),
    ("5.22", "axborot", "Turar joy dahasi (Yashash zonasi)", "Piyodalar ustunlikka ega bo'lgan turar-joy hududi (maksimal 20 km/soat)."),
    ("5.23", "axborot", "Turar joy dahasining oxiri", "5.22 belgisi tugaganini bildiradi."),

    # 6. SERVIS (XIZMAT KO'RSATISH) BELGILARI
    ("6.1", "servis", "Tibbiy yordam punkti", "Birinchi tibbiy yordam punkti joylashgan joy."),
    ("6.2", "servis", "Shifoxona", "Kasalxona yoki tibbiyot markazi."),
    ("6.3", "servis", "Avtomobillarga yoqilg'i quyish shoxobchasi (AYOQSH)", "Benzin, gaz yoki elektr quvvatlash stansiyasi."),
    ("6.4", "servis", "Avtomobillarga texnik xizmat ko'rsatish ustaxonasi", "Avtoservis va ta'mirlash ustaxonasi."),
    ("6.5", "servis", "Avtomobillarni yuvish joyi (Moyka)", "Avtomobillarni yuvish shoxobchasi."),
    ("6.6", "servis", "Telefon", "Aloqa telefoni o'rnatilgan joy."),
    ("6.7", "servis", "Oshxona / Kafe", "Ovqatlanish joyi."),
    ("6.8", "servis", "Ichimlik suvi", "Toza ichimlik suvi manbai."),
    ("6.9", "servis", "Mehmonxona yoki motel", "Mehmonxona yoki dam olish maskani."),
    ("6.10", "servis", "Kemping", "Sayyohlar uchun chodirli lager."),
    ("6.11", "servis", "Dam olish joyi", "Haydovchilar dam olishi uchun maxsus maydoncha."),
    ("6.12", "servis", "Yo'l-patrul xizmati (YPX) maskani", "YPX posti yoki doimiy nazorat maskani."),
    ("6.13", "servis", "Hojatxona", "Jamoat hojatxonasi.")
]

def update_all_signs():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM signs")
    
    webapp_signs = []
    
    for idx, (num, cat, name, desc) in enumerate(OFFICIAL_SIGNS, start=1):
        full_name = f"{num} {name}"
        filename = f"sign_{num}.png"
        rel_path = f"webapp/images/signs/{filename}"
        
        cur.execute("""
            INSERT INTO signs (id, category, name, image_url, description, example)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (idx, cat, full_name, rel_path, desc, "Yo'l harakati qoidalariga qat'iy amal qiling."))
        
        webapp_signs.append({
            "id": idx,
            "category": cat,
            "name": full_name,
            "image_url": f"images/signs/{filename}",
            "description": desc,
            "example": "Yo'l harakati qoidalariga qat'iy amal qiling."
        })
        
    con.commit()
    con.close()
    
    with open("webapp/signs.json", "w", encoding="utf-8") as f:
        json.dump(webapp_signs, f, ensure_ascii=False, indent=2)
    if os.path.exists("webapp/avtomaktab-webapp/signs.json"):
        with open("webapp/avtomaktab-webapp/signs.json", "w", encoding="utf-8") as f:
            json.dump(webapp_signs, f, ensure_ascii=False, indent=2)

    print(f"✅ BARCHA {len(webapp_signs)} TA RASMIY YO'L BELGISI TO'LIQ VA ANIQ YANGILANDI!")

if __name__ == "__main__":
    update_all_signs()
