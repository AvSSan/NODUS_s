Write-Host "🚀 Инициализация проекта NODUS_s..." -ForegroundColor Green

# Проверка наличия .env файла
if (-not (Test-Path ".env")) {
    Write-Host "📝 Создание .env файла из .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Пожалуйста, отредактируйте .env файл и укажите правильные значения" -ForegroundColor Yellow
}

# Проверка Python
Write-Host "🐍 Проверка Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   Найден: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python не найден! Установите Python 3.12+ с https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Создание виртуального окружения
if (-not (Test-Path "venv")) {
    Write-Host "📦 Создание виртуального окружения..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка создания виртуального окружения" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Виртуальное окружение уже существует" -ForegroundColor Green
}

# Запуск инфраструктуры
Write-Host "🐳 Запуск Docker контейнеров..." -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка запуска Docker контейнеров" -ForegroundColor Red
    Write-Host "   Убедитесь, что Docker Desktop запущен" -ForegroundColor Yellow
    exit 1
}

# Ожидание готовности сервисов
Write-Host "⏳ Ожидание готовности сервисов..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# Активация виртуального окружения и установка зависимостей
Write-Host "📦 Установка зависимостей Python..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1
pip install --upgrade pip --quiet
pip install -e .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка установки зависимостей" -ForegroundColor Red
    exit 1
}

# Применение миграций
Write-Host "🗄️  Применение миграций базы данных..." -ForegroundColor Cyan
& .\venv\Scripts\python.exe -m alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка применения миграций" -ForegroundColor Red
    Write-Host "   Проверьте, что PostgreSQL запустился корректно" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "✅ Инициализация завершена!" -ForegroundColor Green
Write-Host ""
Write-Host "Для запуска приложения выполните:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "Или напрямую (без активации venv):" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "Для запуска RQ worker выполните (в новом терминале):" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  rq worker audio --url redis://localhost:6379/1" -ForegroundColor White
Write-Host ""
Write-Host "API документация будет доступна по адресу:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000/docs" -ForegroundColor White
