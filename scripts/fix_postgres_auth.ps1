#!/usr/bin/env pwsh
# Скрипт для исправления аутентификации PostgreSQL

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Fixing PostgreSQL authentication" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Current pg_hba.conf:" -ForegroundColor Yellow
docker exec nodus_postgres cat /var/lib/postgresql/data/pg_hba.conf
Write-Host ""

Write-Host "2. Adding host authentication rules..." -ForegroundColor Yellow
$newRule = @"
# Allow connections from host
host    all             all             0.0.0.0/0               md5
host    all             all             ::/0                    md5
"@

# Добавляем правила в pg_hba.conf
docker exec nodus_postgres sh -c "echo '$newRule' >> /var/lib/postgresql/data/pg_hba.conf"

Write-Host "3. Reloading PostgreSQL configuration..." -ForegroundColor Yellow
docker exec nodus_postgres psql -U postgres -c "SELECT pg_reload_conf();"
Write-Host ""

Write-Host "4. New pg_hba.conf:" -ForegroundColor Yellow
docker exec nodus_postgres cat /var/lib/postgresql/data/pg_hba.conf
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Done! Try migration again:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe -m alembic upgrade head" -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Cyan
