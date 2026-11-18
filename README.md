# 🚦 AVTOVATANPARVAR TESTLARI — Professional Telegram Kanal Boshqaruv Boti

**AVTOVATANPARVAR TESTLARI** — [@AvtoVatanparvar_testlari](https://t.me/AvtoVatanparvar_testlari) Telegram kanalini bitta qulay va xavfsiz admin paneldan to‘liq boshqarish, YHQ testlarini avtomatik va qo‘lda joylashtirish, statistika yuritish hamda foydalanuvchilar bilan ishlash uchun yaratilgan professional Python bot.

- **Til:** O‘zbek tili (lotin yozuvi)
- **Texnologiyalar:** Python 3.12 · aiogram 3 · FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL (Supabase/Render) · openpyxl · matplotlib
- **Vaqt mintaqasi:** `Asia/Tashkent`
- **Arxitektura:** Webhook + PostgreSQL asosidagi barqaror rejalashtiruvchi (`scheduled_jobs`)

---

## ✨ Asosiy imkoniyatlar

| Bo‘lim | Imkoniyatlar |
|---|---|
| 📝 **Postlarni boshqarish** | Matn, rasm, video, hujjat, HTML formatlash, inline URL tugmalar, oldindan ko‘rish, darhol joylash, vaqtga rejalashtirish, tahrirlash, o‘chirish (tasdiqlash bilan), tarix va qayta joylash |
| 🚦 **Testlarni boshqarish** | 10 qadamli qo‘shish, barcha/tasdiqlanmagan testlar, tahrirlash, o‘chirish, qidirish, mavzular bo‘yicha saralash, dublikatga qarshi himoya, **Excel (.xlsx) import/eksport**, namuna shablon |
| 📅 **Avtomatik joylashtirish** | Kunlik testlar soni, boshlash vaqti, oraliq, hafta kunlari, tasodifiy/ketma-ket tanlash, takroriy test himoyasi, **Quiz Poll** va **Inline Keyboard** rejimlari, javob va izohni avtomatik e’lon qilish |
| 📢 **Reklama boshqaruvi** | Matn/rasm/video/tugmali reklama yaratish, rejalashtirish, tahrirlash, to‘xtatish/qayta yoqish va o‘chirish |
| 👥 **Ko‘p adminli tizim** | 5 ta rol: `SUPER_ADMIN`, `ADMIN`, `TEST_MANAGER`, `EDITOR`, `STATISTIC_VIEWER`. Admin o‘chirilganda ruxsatlar darhol bekor qilinadi |
| 📊 **Statistika** | Real bazaviy ko‘rsatkichlar (kunlik/haftalik/oylik o‘sish, kanal obunachilari, post/test/javob/reklama/admin faoliyati) + **PNG grafik** |
| 📨 **Ommaviy xabar** | Barcha faol foydalanuvchilarga matn/media/tugmali xabar, jonli progress, Telegram flood limit himoyasi, bloklaganlarni avtomatik chiqarish |
| 👤 **Foydalanuvchi menyusi** | Test ishlash, mavzular bo‘yicha mashq, shaxsiy natijalar, majburiy kanal obunasini yoqish/o‘chirish |
| 💾 **Zaxira nusxa & Audit** | Barcha 12 jadvalni JSON + ZIP arxivda yuklab olish, barcha admin amallari tarixi (`activity_logs`) |
| 🛡 **Barqarorlik & Xavfsizlik** | Render Free uyqudan uyg‘onganda stale lock tiklash, o‘tib ketgan vazifalarni bajarish, 2 worker dublikat himoyasi, dual Webhook secret tekshiruvi, loglarda token yashirish |

---

## 📁 Loyiha tuzilishi

```text
avtovatanparvar_bot/
├── app/
│   ├── main.py              # FastAPI webhook serveri (/, /health, /webhook/{secret})
│   ├── config.py            # Pydantic Settings (Environment Variables + SSL/Supabase URL)
│   ├── database.py          # SQLAlchemy 2 async engine va session boshqaruvi
│   ├── models/              # 12 ta PostgreSQL jadval modellari
│   ├── repositories/        # Parametrizatsiyalangan DB so‘rovlar qatlami
│   ├── services/            # Post, Test, Excel, Statistika, Broadcast, Backup, Kanal servislari
│   ├── scheduler/           # PostgreSQL asosidagi idempotent rejalashtiruvchi
│   ├── middlewares/         # DB sessiya, RBAC auth, majburiy obuna, xatolik himoyasi
│   ├── keyboards/           # Barcha admin va foydalanuvchi klaviaturalari
│   ├── handlers/
│   │   ├── admin/           # Avto-test, reklama, adminlar, broadcast, sozlamalar, backup, loglar
│   │   ├── posts/           # Postlar CRUD va rejalashtirish
│   │   ├── tests/           # Testlar CRUD, Excel, kanaldagi inline/poll ovozlar
│   │   ├── statistics/      # Statistika hisoboti va PNG grafik
│   │   └── user/            # Oddiy foydalanuvchi menyusi va test yechish
│   └── utils/               # Vaqt mintaqasi, xavfsizlik, formatlash, logging, FSM
├── migrations/              # Alembic async PostgreSQL migratsiyalari
├── scripts/                 # init_db.py, run_polling.py, seed_sample_tests.py, generate_template.py
├── tests/                   # Pytest avtomatik testlar to‘plami (mock Telegram API bilan)
├── requirements.txt
├── .env.example
├── .gitignore
├── render.yaml
├── Procfile
├── runtime.txt
└── README.md
```

---

## 🤖 1. BotFather sozlamalari

1. Telegram’da [@BotFather](https://t.me/BotFather) ga kiring.
2. `/newbot` buyrug‘ini yuboring.
3. Bot nomi: `AvtoVatanparvar Testlari`
4. Bot username (oxiri `bot` bilan tugashi shart): masalan, `AvtoVatanparvarTestBot`.
5. Olingan **BOT_TOKEN** ni saqlab qo‘ying (uni hech qachon kodga yozmang!).
6. Foydalanuvchilar uchun buyruqlar ro‘yxatini o‘rnatish (`/setcommands`):
   ```text
   start - Botni ishga tushirish / Bosh menyu
   cancel - Joriy amalni bekor qilish
   ```
7. O‘zingizning Telegram ID raqamingizni bilish uchun [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring va `Id` raqamini `SUPERADMIN_ID` sifatida saqlang.

---

## 📢 2. Botni kanalga administrator qilish

1. [@AvtoVatanparvar_testlari](https://t.me/AvtoVatanparvar_testlari) kanalini oching.
2. **Kanal sozlamalari → Administratorlar → Administrator qo‘shish** bo‘limiga kiring.
3. Yangi yaratgan botingizni toping va qo‘shing.
4. Quyidagi ruxsatlarni yoqing:
   - ✅ **Post Messages** (Xabar joylash)
   - ✅ **Edit Messages of Others** / **Edit Messages** (Xabarlarni tahrirlash)
   - ✅ **Delete Messages** (Xabarlarni o‘chirish)
   - ✅ **Invite Users via Link** (ixtiyoriy, majburiy obuna va havolalar uchun foydali)
5. Kanal ID raqamini olish uchun kanaldan biror postni [@username_to_id_bot](https://t.me/username_to_id_bot) ga forward qiling (masalan: `-1001234567890`) yoki public kanal uchun `CHANNEL_ID=@AvtoVatanparvar_testlari` qilib ko‘rsating.
6. Bot ishga tushgach, Admin panel → **⚙️ SOZLAMALAR → 🛡 Kanal admin huquqlarini tekshirish** tugmasi orqali hamma huquqlar to‘g‘ri berilganini tekshiring.

---

## 🗄 3. PostgreSQL (Supabase Free) sozlash

1. [Supabase](https://supabase.com/) da bepul hisob oching va yangi loyiha yarating.
2. **Project Settings → Database → Connection string → URI** bo‘limiga kiring.
3. **Transaction pooler (port 6543)** yoki **Direct connection (port 5432)** manzilini nusxalang:
   ```text
   postgresql+asyncpg://postgres.XXXXXX:SIZNING_PAROL@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```
   > **Eslatma:** Bot avtomatik tarzda `postgres://` yoki `postgresql://` manzillarini `postgresql+asyncpg://` ga o‘giradi, `ssl=require` ni sozlaydi va Supabase PgBouncer (port 6543) uchun `statement_cache_size=0` ni yoqadi.

---

## 💻 4. Windows 10 da ishga tushirish qo‘llanmasi

### 4.1. Loyiha muhitini tayyorlash (PowerShell)

```powershell
cd E:\Botlarim\Avtomaktab\avtovatanparvar_bot

# Virtual muhit yaratish va faollashtirish
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Kutubxonalarni o'rnatish
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2. `.env` faylini yaratish

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` faylida kamida quyidagilarni to‘ldiring:
- `BOT_TOKEN`
- `SUPERADMIN_ID`
- `CHANNEL_ID` va `CHANNEL_USERNAME=@AvtoVatanparvar_testlari`
- `DATABASE_URL` (lokal sinov uchun `sqlite+aiosqlite:///./local_dev.db` yoki Supabase PostgreSQL URI)
- `WEBHOOK_SECRET` (kamida 32 belgili tasodifiy sirli satr)

### 4.3. Ma'lumotlar bazasi migratsiyasi va ishga tushirish

```powershell
# Alembic migratsiyalarini qo'llash
alembic upgrade head

# Super Admin va standart sozlamalarni tayyorlash
python scripts/init_db.py

# (Ixtiyoriy) 5 ta namuna YHQ testini qo'shish
python scripts/seed_sample_tests.py

# Lokal sinov uchun polling rejimida ishga tushirish:
python scripts/run_polling.py
```

Webhook serverini lokal tekshirish uchun:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 5. GitHub'ga joylashtirish ko‘rsatmasi

```powershell
cd E:\Botlarim\Avtomaktab\avtovatanparvar_bot

git init
git add .
git status   # .env fayli ro'yxatda YO'Q ekanligiga ishonch hosil qiling!
git commit -m "Initial commit: AVTOVATANPARVAR TESTLARI professional Telegram bot"
git branch -M main
git remote add origin https://github.com/<SIZNING_USERNAME>/avtovatanparvar-bot.git
git push -u origin main
```

---

## 🚀 6. Render Free Hosting qo‘llanmasi

1. [Render.com](https://render.com/) ga GitHub orqali kiring.
2. **New + → Web Service** tugmasini bosing va GitHub repozitoriyingizni tanlang (yoki `render.yaml` orqali **Blueprint** sifatida ulang).
3. Quyidagi sozlamalarni kiriting:
   - **Runtime:** `Python 3`
   - **Region:** `Frankfurt (EU Central)` (O‘zbekistonga eng yaqin)
   - **Instance Type:** `Free`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Health Check Path:** `/health`
4. **Environment Variables** bo‘limida quyidagilarni kiriting:
   - `PYTHON_VERSION` = `3.12.10`
   - `BOT_TOKEN` = *(BotFather tokeni)*
   - `SUPERADMIN_ID` = *(Telegram ID raqamingiz)*
   - `CHANNEL_ID` = `-100...` yoki `@AvtoVatanparvar_testlari`
   - `CHANNEL_USERNAME` = `@AvtoVatanparvar_testlari`
   - `DATABASE_URL` = *(Supabase PostgreSQL URI)*
   - `WEBHOOK_BASE_URL` = `https://<sizning-servisingiz>.onrender.com`
   - `WEBHOOK_SECRET` = *(32+ belgili maxfiy kalit, faqat harf/raqam/chiziqcha)*
   - `TIMEZONE` = `Asia/Tashkent`
   - `DB_SSL_REQUIRED` = `true`
5. **Deploy Web Service** tugmasini bosing.
6. Deploy tugagach, brauzerda tekshiring:
   - `https://<sizning-servisingiz>.onrender.com/`
   - `https://<sizning-servisingiz>.onrender.com/health` → `{"status":"ok","database":"connected",...}`

### ⚠️ Render Free va Supabase Free cheklovlari haqida muhim eslatma
- **Render Free** 15 daqiqa faolsizlikdan keyin serverni uxlash rejimiga o‘tkazadi. Buning oldini olish va rejalashtirilgan post/testlar o‘z vaqtida chiqishi uchun [UptimeRobot](https://uptimerobot.com/) yoki [cron-job.org](https://cron-job.org/) orqali har **5–10 daqiqada** `https://<sizning-servisingiz>.onrender.com/health` manziliga GET ping yuborib turing.
- Agar server uxlab qolsa ham, qayta uyg‘onishi bilan `PersistentScheduler` PostgreSQL `scheduled_jobs` jadvalidagi barcha o‘tib ketgan va osilib qolgan vazifalarni avtomatik aniqlab, dublikatsiz bajaradi.
- **Supabase Free** 7 kun davomida hech qanday so‘rov kelmasa bazani pauzaga qo‘yishi mumkin — `/health` endpointi har pingda `SELECT 1` bajargani uchun bazani ham doimiy faol saqlab turadi.

---

## 📥 7. Excel (.xlsx) test import formati

Admin panel → **🚦 TESTLARNI BOSHQARISH → 📥 Excel import** bo‘limidan tayyor namuna shablonni yuklab olishingiz mumkin. Majburiy ustunlar:

| savol | a | b | c | d | togri_javob | izoh | mavzu | qiyinlik |
|---|---|---|---|---|---|---|---|---|
| Aholi punktlarida maksimal tezlik? | 50 km/soat | 60 km/soat | 70 km/soat | 80 km/soat | B | YHQ bo'yicha 60 km/soat | Tezlik | easy |

- `togri_javob`: faqat `A`, `B`, `C` yoki `D`
- `qiyinlik`: `easy` (`oson`), `medium` (`o'rta`), `hard` (`qiyin`)

---

## 🧪 8. Testlarni ishga tushirish

```powershell
cd E:\Botlarim\Avtomaktab\avtovatanparvar_bot
python -m pytest
```
