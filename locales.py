LOCALES = {
    "uz": {
        "choose_language": "🌍 Iltimos, o'zingizga qulay tilni tanlang:",
        "enter_fullname": "👤 Iltimos, to'liq ism-sharifingizni (F.I.Sh.) kiriting:",
        "send_phone": "📞 Iltimos, telefon raqamingizni yuboring (yoki pastdagi tugmani bosing):",
        "btn_send_phone": "📱 Raqamni tasdiqlash",
        "reg_success": "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!\n\n🏠 Asosiy menyu:",
        "lang_changed": "✅ Til muvaffaqiyatli o'zgartirildi!\n\n🏠 Asosiy menyu:",
        "menu_test": "🚗 Ishlash testi",
        "menu_rules": "📚 Yo'l harakati qoidalari",
        "menu_signs": "🚦 Yo'l belgilari",
        "menu_videos": "🎥 Video darslar",
        "menu_stats": "📈 Mening Natijalarim",
        "menu_rating": "👑 Liderlar Doskasi",
        "menu_news": "⚡️ So'nggi Yangiliklar",
        "menu_contact": "☎️ Adminga murojaat",
        "menu_language": "⚙️ Tilni o'zgartirish",
        "welcome": "Assalomu alaykum, {name}! 🚗\nAvtomaktab Premium botiga xush kelibsiz!\n\n👇 Quyidagi menyudan kerakli bo'limni tanlang:",
        "invalid_phone": "❌ Iltimos, telefon raqamingizni to'g'ri formatda kiriting (Masalan: +998901234567) yoki maxsus tugmadan foydalaning.",
    },
    "uz_cyr": {
        "choose_language": "🌍 Илтимос, ўзингизга қулай тилни танланг:",
        "enter_fullname": "👤 Илтимос, тўлиқ исм-шарифингизни (Ф.И.Ш.) киритинг:",
        "send_phone": "📞 Илтимос, телефон рақамингизни юборинг (ёки пастдаги тугмани босинг):",
        "btn_send_phone": "📱 Рақамни тасдиқлаш",
        "reg_success": "✅ Рўйхатдан ўтиш муваффақиятли якунланди!\n\n🏠 Асосий меню:",
        "lang_changed": "✅ Тил муваффақиятли ўзгартирилди!\n\n🏠 Асосий меню:",
        "menu_test": "🚗 Ishlash testi",
        "menu_rules": "📚 Yo'l harakati qoidalari",
        "menu_signs": "🚦 Yo'l belgilari",
        "menu_videos": "🎥 Video darslar",
        "menu_stats": "📈 Mening Natijalarim",
        "menu_rating": "👑 Liderlar Doskasi",
        "menu_news": "⚡️ So'nggi Yangiliklar",
        "menu_contact": "☎️ Adminga murojaat",
        "menu_language": "⚙️ Tilni o'zgartirish",
        "welcome": "Ассалому алайкум, {name}! 🚗\nАвтомактаб Premium ботига хуш келибсиз!\n\n👇 Қуйидаги менюдан керакли бўлимни танланг:",
        "invalid_phone": "❌ Илтимос, телефон рақамингизни тўғри форматда киритинг (Масалан: +998901234567) ёки махсус тугмадан фойдаланинг.",
    },
    "ru": {
        "choose_language": "🌍 Пожалуйста, выберите удобный для вас язык:",
        "enter_fullname": "👤 Пожалуйста, введите ваше полное имя (Ф.И.О):",
        "send_phone": "📞 Пожалуйста, отправьте свой номер телефона (или нажмите кнопку ниже):",
        "btn_send_phone": "📱 Подтвердить номер",
        "reg_success": "✅ Регистрация успешно завершена!\n\n🏠 Главное меню:",
        "lang_changed": "✅ Язык успешно изменен!\n\n🏠 Главное меню:",
        "menu_test": "🚗 Ishlash testi",
        "menu_rules": "📚 Yo'l harakati qoidalari",
        "menu_signs": "🚦 Yo'l belgilari",
        "menu_videos": "🎥 Video darslar",
        "menu_stats": "📈 Mening Natijalarim",
        "menu_rating": "👑 Liderlar Doskasi",
        "menu_news": "⚡️ So'nggi Yangiliklar",
        "menu_contact": "☎️ Adminga murojaat",
        "menu_language": "⚙️ Tilni o'zgartirish",
        "welcome": "Здравствуйте, {name}! 🚗\nДобро пожаловать в Premium бот Автошколы!\n\n👇 Выберите нужный раздел из меню ниже:",
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
