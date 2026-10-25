LOCALES = {
    "uz": {
        "choose_language": "🌍 Iltimos, o'zingizga qulay tilni tanlang:",
        "enter_fullname": "👤 Iltimos, to'liq ism-sharifingizni (F.I.Sh.) kiriting:",
        "send_phone": "📞 Iltimos, telefon raqamingizni yuboring (yoki pastdagi tugmani bosing):",
        "btn_send_phone": "📱 Raqamni tasdiqlash",
        "reg_success": "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!\n\n🏠 Asosiy menyu:",
        "lang_changed": "✅ Til muvaffaqiyatli o'zgartirildi!\n\n🏠 Asosiy menyu:",
        "menu_test": "🚗 Test Ishlash (805 ta YHQ)",
        "menu_rules": "📚 YHQ Qoidalari",
        "menu_signs": "🚦 Yo'l belgilari",
        "menu_videos": "🎥 Video darslar",
        "menu_stats": "📊 Mening Natijam",
        "menu_rating": "👑 Liderlar Doskasi",
        "menu_news": "⚡️ So'nggi Yangiliklar",
        "menu_contact": "☎️ Adminga murojaat",
        "menu_language": "⚙️ Tilni o'zgartirish",
        "welcome": "Assalomu alaykum, {name}! 🚗\nAvtovatanparvar Premium botiga xush kelibsiz!\n\n👇 Quyidagi menyudan kerakli bo'limni tanlang:",
        "invalid_phone": "❌ Iltimos, telefon raqamingizni to'g'ri formatda kiriting (Masalan: +998901234567) yoki maxsus tugmadan foydalaning.",
    },
    "uz_cyr": {
        "choose_language": "🌍 Илтимос, ўзингизга қулай тилни танланг:",
        "enter_fullname": "👤 Илтимос, тўлиқ исм-шарифингизни (Ф.И.Ш.) киритинг:",
        "send_phone": "📞 Илтимос, телефон рақамингизни юборинг (ёки пастдаги тугмани босинг):",
        "btn_send_phone": "📱 Рақамни тасдиқлаш",
        "reg_success": "✅ Рўйхатдан ўтиш муваффақиятли якунланди!\n\n🏠 Асосий меню:",
        "lang_changed": "✅ Тил муваффақиятли ўзгартирилди!\n\n🏠 Асосий меню:",
        "menu_test": "🚗 Тест ишлаш (805 та ЙҲҚ)",
        "menu_rules": "📚 ЙҲҚ Қоидалари",
        "menu_signs": "🚦 Йўл белгилари",
        "menu_videos": "🎥 Видео дарслар",
        "menu_stats": "📈 Менинг Натижаларим",
        "menu_rating": "👑 Лидерлар Доскаси",
        "menu_news": "⚡️ Сўнгги Янгиликлар",
        "menu_contact": "☎️ Админга мурожаат",
        "menu_language": "⚙️ Тилни ўзгартириш",
        "welcome": "Ассалому алайкум, {name}! 🚗\nАвтоватанпарвар Премиум ботига хуш келибсиз!\n\n👇 Қуйидаги менюдан керакли бўлимни танланг:",
        "invalid_phone": "❌ Илтимос, телефон рақамингизни тўғри форматда киритинг (Масалан: +998901234567) ёки махсус тугмадан фойдаланинг.",
    },
    "ru": {
        "choose_language": "🌍 Пожалуйста, выберите удобный для вас язык:",
        "enter_fullname": "👤 Пожалуйста, введите ваше полное имя (Ф.И.О):",
        "send_phone": "📞 Пожалуйста, отправьте свой номер телефона (или нажмите кнопку ниже):",
        "btn_send_phone": "📱 Подтвердить номер",
        "reg_success": "✅ Регистрация успешно завершена!\n\n🏠 Главное меню:",
        "lang_changed": "✅ Язык успешно изменен!\n\n🏠 Главное меню:",
        "menu_test": "🚗 Тестирование (805 ПДД)",
        "menu_rules": "📚 Правила ПДД",
        "menu_signs": "🚦 Дорожные знаки",
        "menu_videos": "🎥 Видеоуроки",
        "menu_stats": "📈 Мои Результаты",
        "menu_rating": "👑 Доска Лидеров",
        "menu_news": "⚡️ Последние Новости",
        "menu_contact": "☎️ Связь с админом",
        "menu_language": "⚙️ Изменить язык",
        "welcome": "Здравствуйте, {name}! 🚗\nДобро пожаловать в Премиум бот Автошколы!\n\n👇 Выберите нужный раздел из меню ниже:",
        "invalid_phone": "❌ Пожалуйста, введите номер телефона в правильном формате (Например: +998901234567) или используйте специальную кнопку.",
    }
}

def get_text(lang: str, key: str, **kwargs) -> str:
    """Berilgan til va kalit bo'yicha matnni qaytaradi"""
    if lang not in LOCALES:
        lang = "uz"
    
    text = LOCALES[lang].get(key, f"[{key}]")
    if kwargs:
        text = text.format(**kwargs)
    return text
