#!/usr/bin/env pwsh
# Скрипт для полного сброса базы данных

Write-Host "🔄 Остановка контейнеров..." -ForegroundColor Yellow
docker-compose down

Write-Host "🗑️  Удаление volumes..." -ForegroundColor Yellow
docker volume rm nodus_s_postgres_data -f

Write-Host "🚀 Запуск контейнеров..." -ForegroundColor Green
docker-compose up -d

Write-Host "⏳ Ожидание готовности PostgreSQL (20 секунд)..." -ForegroundColor Cyan
Start-Sleep -Seconds 20

Write-Host "✅ База данных сброшена!" -ForegroundColor Green
Write-Host ""
Write-Host "Теперь попробуйте:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\python.exe -m alembic upgrade head" -ForegroundColor White
