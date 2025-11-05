"""Тестовый скрипт для проверки подключения к БД"""
from app.core.config import settings

print("=" * 60)
print("Проверка настроек подключения к БД")
print("=" * 60)
print(f"DATABASE_URL: {settings.database_url}")
print(f"APP_NAME: {settings.app_name}")
print(f"APP_VERSION: {settings.app_version}")
print("=" * 60)

# Попытка синхронного подключения
import psycopg

try:
    # Парсим URL
    url = settings.database_url.replace("postgresql+psycopg://", "")
    
    print(f"\nПопытка подключения к: {url}")
    
    conn = psycopg.connect(
        "host=localhost port=5432 dbname=nodus user=postgres password=postgres"
    )
    print("✅ Успешное подключение!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL версия: {version[0]}")
    
    cursor.execute("SELECT current_database();")
    db = cursor.fetchone()
    print(f"Текущая база данных: {db[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    print(f"Тип ошибки: {type(e)}")
