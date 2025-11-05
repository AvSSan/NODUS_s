#!/usr/bin/env pwsh
# Полный сброс PostgreSQL с удалением volume

Write-Host "==================================================" -ForegroundColor Red
Write-Host "COMPLETE RESET - All data will be lost!" -ForegroundColor Red
Write-Host "==================================================" -ForegroundColor Red
Write-Host ""

$confirmation = Read-Host "Continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "1. Stopping all containers..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "2. Removing postgres volume..." -ForegroundColor Yellow
docker volume rm nodus_s_postgres_data

Write-Host ""
Write-Host "3. Starting containers with new settings..." -ForegroundColor Green
docker-compose up -d

Write-Host ""
Write-Host "4. Waiting for PostgreSQL (20 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "5. Testing connection..." -ForegroundColor Cyan
docker exec nodus_postgres psql -U postgres -d nodus -c "SELECT version();"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Reset complete! Now try:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe test_db_connection.py" -ForegroundColor White
Write-Host "  .\venv\Scripts\python.exe -m alembic upgrade head" -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Green
