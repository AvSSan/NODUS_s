#!/usr/bin/env pwsh
# Проверка сетевых настроек Windows

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Network diagnostics" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Check if port 5432 is listening:" -ForegroundColor Yellow
netstat -ano | Select-String ":5432"
Write-Host ""

Write-Host "2. Check if local PostgreSQL is installed:" -ForegroundColor Yellow
Get-Service | Where-Object {$_.Name -like "*postgres*"}
Write-Host ""

Write-Host "3. Check Windows Firewall rules for port 5432:" -ForegroundColor Yellow
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*5432*" -or $_.DisplayName -like "*postgres*"} | Select-Object DisplayName, Enabled, Direction, Action
Write-Host ""

Write-Host "4. Try telnet to localhost:5432:" -ForegroundColor Yellow
Write-Host "   (Testing if port is reachable)" -ForegroundColor Gray
Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Detailed
Write-Host ""

Write-Host "5. Docker network info:" -ForegroundColor Yellow
docker network inspect bridge | Select-String "nodus_postgres" -Context 5
Write-Host ""

Write-Host "6. Container port mapping:" -ForegroundColor Yellow
docker port nodus_postgres
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Diagnostics complete" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
