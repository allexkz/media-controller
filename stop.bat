@echo off
rem Encerra o Media Controller (qualquer processo escutando na porta 8765)
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8765 -State Listen -EA 0; if ($c) { $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }; 'Media Controller encerrado.' } else { 'Media Controller nao esta rodando.' }"
timeout /t 2 >nul
