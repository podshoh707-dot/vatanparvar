@echo off
chcp 65001 > nul
title AVTOVATANPARVAR - Avtotest Telegram Bot
color 0A

echo ========================================================
echo    🚘 AVTOTEST / AVTOVATANPARVAR TELEGRAM BOT
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [XATO] .venv muhiti topilmadi!
    pause
    exit /b 1
)

echo [*] Bot ishga tushirilmoqda...
echo [*] To'xtatish uchun: Ctrl + C bosing
echo ========================================================
echo.

.venv\Scripts\python.exe bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Bot to'xtadi yoki xatolik yuz berdi.
)

pause
