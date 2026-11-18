@echo off
chcp 65001 > nul
title AVTOVATANPARVAR TESTLARI — Professional Telegram Bot
color 0A

echo ========================================================
echo    🚘 AVTOVATANPARVAR TESTLARI TELEGRAM BOT
echo ========================================================
echo.

set PY=.venv\Scripts\python.exe
if not exist %PY% (
    set PY=python
)

echo [*] Bot ishga tushirilmoqda (%PY% bot.py)...
echo [*] To'xtatish uchun: Ctrl + C bosing
echo ========================================================
echo.

%PY% bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Bot to'xtadi yoki xatolik yuz berdi.
)

pause
