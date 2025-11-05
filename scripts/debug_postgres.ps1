#!/usr/bin/env pwsh
# Скрипт для диагностики проблем с PostgreSQL

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Diagnostika PostgreSQL" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Running containers:" -ForegroundColor Yellow
docker ps --filter name=nodus
Write-Host ""

Write-Host "2. Environment variables:" -ForegroundColor Yellow
docker exec nodus_postgres env | Select-String "POSTGRES"
Write-Host ""

Write-Host "3. Connect INSIDE container (no password):" -ForegroundColor Yellow
$cmd3 = 'psql -U postgres -c "SELECT version();"'
docker exec nodus_postgres sh -c $cmd3
Write-Host ""

Write-Host "4. Connect INSIDE container (with password):" -ForegroundColor Yellow
$cmd4 = 'PGPASSWORD=postgres psql -U postgres -c "SELECT current_database();"'
docker exec nodus_postgres sh -c $cmd4
Write-Host ""

Write-Host "5. Check pg_hba.conf:" -ForegroundColor Yellow
docker exec nodus_postgres cat /var/lib/postgresql/data/pg_hba.conf | Select-String -Pattern "host"
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Diagnostika complete" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
