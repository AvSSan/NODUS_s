#!/bin/bash

# Скрипт деплоя NODUS Backend
# Использование: bash deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Starting NODUS Backend deployment..."

# Переход в директорию проекта
cd /home/nodus/NODUS_s

# Получение последних изменений
echo "📥 Pulling latest changes from git..."
git pull origin main

# Активация виртуального окружения
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Установка/обновление зависимостей
echo "📦 Installing dependencies..."
pip install -e .

# Применение миграций базы данных
echo "🗄️ Running database migrations..."
alembic upgrade head

# Перезапуск сервиса
echo "🔄 Restarting backend service..."
sudo systemctl restart nodus-backend

# Проверка статуса
echo "✅ Checking service status..."
sudo systemctl status nodus-backend --no-pager

echo "🎉 Deployment completed!"
echo "📊 Check logs: sudo journalctl -u nodus-backend -f"
