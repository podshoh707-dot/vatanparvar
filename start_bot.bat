@echo off
chcp 65001 > nul
title AVTOVATANPARVAR - Avtotest Telegram Bot
color 0A

echo ========================================================
echo    🚘 AVTOTEST / AVTOVATANPARVAR TELEGRAM BOT
echo ========================================================
echo.

set PY=.venv\Scripts\python.exe
if not exist %PY% (
    set PY=py
)

echo [*] Bot ishga tushirilmoqda (%PY%)...
echo [*] To'xtatish uchun: Ctrl + C bosing
echo ========================================================
echo.

%PY% bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Bot to'xtadi yoki xatolik yuz berdi.
)

pause
