# ========================================================
#    🚘 AVTOVATANPARVAR TESTLARI TELEGRAM BOT
# ========================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   🚘 AVTOVATANPARVAR TESTLARI TELEGRAM BOT" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

Write-Host "[*] Bot ishga tushirilmoqda ($py bot.py)..." -ForegroundColor Green
Write-Host "[*] To'xtatish uchun: Ctrl + C bosing" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

& $py bot.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[!] Bot to'xtadi yoki xatolik yuz berdi." -ForegroundColor Red
}

Read-Host "Oynani yopish uchun Enter bosing..."
