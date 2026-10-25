@echo off
chcp 65001 > nul
title Vatanparvar - GitHubga Yuklash
color 0A

echo ========================================================
echo   🚀 VATANPARVAR LOYIHASINI GITHUB'GA YUKLASH
echo ========================================================
echo.

set GIT="C:\Users\user\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd\git.exe"
if not exist %GIT% (
    set GIT="C:\Users\user\AppData\Local\GitHubDesktop\app-3.6.5\resources\app\git\cmd\git.exe"
)
if not exist %GIT% (
    set GIT=git
)

echo [*] Fayllar qo'shilmoqda...
%GIT% add .

echo [*] Yangi o'zgarishlar commit qilinmoqda...
%GIT% commit -m "Vatanparvar Avtotest: HD rasmlar, toza E-Avtomaktab bazasi va yangi zamonaviy interfeys"

echo [*] GitHub omboriga (https://github.com/podshoh707-dot/Vatanparvar) yuborilmoqda...
%GIT% push origin main
if %ERRORLEVEL% NEQ 0 (
    %GIT% push vatanparvar main
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Agar konsolda parol so'ralsa yoki ruxsat berilmasa:
    echo     GitHub Desktop dasturida "Publish repository" yoki "Push origin" tugmasini bosing!
)

pause
