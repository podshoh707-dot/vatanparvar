# ========================================================
#    🚘 AVTOTEST / AVTOVATANPARVAR TELEGRAM BOT
# ========================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   🚘 AVTOTEST / AVTOVATANPARVAR TELEGRAM BOT" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[XATO] .venv muhiti topilmadi!" -ForegroundColor Red
    Read-Host "Davom etish uchun Enter bosing..."
    exit 1
}

Write-Host "[*] Bot ishga tushirilmoqda..." -ForegroundColor Green
Write-Host "[*] To'xtatish uchun: Ctrl + C bosing" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

& .venv\Scripts\python.exe bot.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[!] Bot to'xtadi yoki xatolik yuz berdi." -ForegroundColor Red
}

Read-Host "Oynani yopish uchun Enter bosing..."
