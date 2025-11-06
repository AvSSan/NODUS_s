# 🐳 Деплой NODUS Backend с Docker

## Преимущества Docker

✅ **Не нужно устанавливать:** Python, PostgreSQL, Redis, MinIO  
✅ **Изоляция:** Все работает в контейнерах  
✅ **Легкое обновление:** Один команда для пересборки  
✅ **Портативность:** Работает одинаково на любой ОС  
✅ **Простое масштабирование:** Легко добавить реплики  

---

## 📋 Требования

На сервере Ubuntu 22 нужен только Docker:

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo apt install -y docker-compose-plugin

# Проверяем установку
docker --version
docker compose version
```

**Перелогиньтесь после установки!**

---

## 🚀 Деплой на Production

### 1. Клонируем репозиторий

```bash
# Создаем директорию для проекта
mkdir -p ~/projects
cd ~/projects

# Клонируем репозиторий
git clone https://github.com/your-username/NODUS_s.git
cd NODUS_s
```

### 2. Настраиваем переменные окружения

```bash
# Копируем шаблон
cp .env.production .env

# Редактируем файл
nano .env
```

**Важно! Измените все значения:**

```env
POSTGRES_PASSWORD=ваш_надежный_пароль_postgresql
JWT_SECRET_KEY=ваш_очень_длинный_случайный_секретный_ключ_минимум_32_символа
JWT_REFRESH_SECRET_KEY=другой_очень_длинный_секретный_ключ_для_refresh_токенов
MINIO_ROOT_PASSWORD=ваш_надежный_пароль_minio
```

### 3. Запускаем всё одной командой!

```bash
# Production деплой
docker compose -f docker-compose.prod.yml up -d --build
```

**Это всё! 🎉**

Docker автоматически:
- ✅ Скачает все образы (PostgreSQL, Redis, MinIO)
- ✅ Соберет ваше приложение
- ✅ Создаст сеть для контейнеров
- ✅ Применит миграции базы данных
- ✅ Настроит MinIO bucket
- ✅ Запустит Nginx как reverse proxy
- ✅ Запустит backend с 4 workers

### 4. Проверяем работу

```bash
# Смотрим статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Все контейнеры должны быть "Up" и "healthy"

# Проверяем логи
docker compose -f docker-compose.prod.yml logs -f backend

# Проверяем API
curl http://localhost/health
# Должно вернуть: {"status":"ok"}
```

---

## 📊 Управление контейнерами

### Просмотр логов

```bash
# Логи всех сервисов
docker compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f postgres
docker compose -f docker-compose.prod.yml logs -f redis
```

### Перезапуск сервисов

```bash
# Перезапустить всё
docker compose -f docker-compose.prod.yml restart

# Перезапустить только backend
docker compose -f docker-compose.prod.yml restart backend
```

### Остановка и запуск

```bash
# Остановить всё
docker compose -f docker-compose.prod.yml stop

# Запустить всё
docker compose -f docker-compose.prod.yml start

# Полностью удалить (с данными!)
docker compose -f docker-compose.prod.yml down -v
```

---

## 🔄 Обновление приложения

Когда вы внесли изменения в код:

```bash
cd ~/projects/NODUS_s

# Получаем последние изменения
git pull origin main

# Пересобираем и перезапускаем
docker compose -f docker-compose.prod.yml up -d --build

# Миграции применяются автоматически при старте!
```

**Готово! Обновление заняло 2 команды.** 🚀

---

## 🔧 Разработка (локально)

Для разработки используйте `docker-compose.yml` (не production):

```bash
# Запуск для разработки
docker compose up -d

# С автоматической перезагрузкой при изменении кода
docker compose up

# Остановка
docker compose down
```

Отличия от production:
- ✅ Hot reload при изменении кода
- ✅ Volume mapping для быстрой разработки
- ✅ 1 worker вместо 4
- ✅ Debug логирование
- ❌ Нет Nginx (напрямую к backend)

---

## 🗄️ Работа с базой данных

### Подключение к PostgreSQL

```bash
# Через psql
docker compose exec postgres psql -U postgres -d nodus

# Или используйте любой PostgreSQL клиент:
# Host: localhost
# Port: 5432 (прокинут наружу в dev режиме)
# User: postgres
# Password: (из .env)
# Database: nodus
```

### Миграции

```bash
# Применить миграции (автоматически при старте backend)
docker compose exec backend alembic upgrade head

# Откатить последнюю миграцию
docker compose exec backend alembic downgrade -1

# Создать новую миграцию
docker compose exec backend alembic revision --autogenerate -m "описание"
```

### Бэкап базы данных

```bash
# Создать бэкап
docker compose exec postgres pg_dump -U postgres nodus > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить бэкап
cat backup_20240101_120000.sql | docker compose exec -T postgres psql -U postgres nodus
```

---

## 📦 Работа с MinIO

### Доступ к MinIO Console

```bash
# В production режиме MinIO доступен только внутри Docker сети
# Для доступа снаружи временно добавьте порты в docker-compose.prod.yml:

# minio:
#   ports:
#     - "9000:9000"
#     - "9001:9001"

# Затем перезапустите:
docker compose -f docker-compose.prod.yml up -d minio
```

Откройте в браузере: `http://your-server-ip:9001`

**Логин:** `minioadmin` (или из .env)  
**Пароль:** из `MINIO_ROOT_PASSWORD` в .env

### Управление файлами через MinIO Client

```bash
# Запустить mc (MinIO Client)
docker compose exec backend sh

# Внутри контейнера:
mc alias set myminio http://minio:9000 minioadmin your-password
mc ls myminio/attachments
```

---

## 🌐 Настройка домена и SSL

### Вариант 1: Let's Encrypt с Certbot (рекомендуется)

```bash
# Установите certbot НА ХОСТЕ (не в Docker)
sudo apt install -y certbot

# Остановите Nginx контейнер
docker compose -f docker-compose.prod.yml stop nginx

# Получите сертификат
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Сертификаты будут в: /etc/letsencrypt/live/your-domain.com/

# Создайте директорию для SSL в проекте
mkdir -p deploy/ssl

# Скопируйте сертификаты
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/ssl/
sudo chown $USER:$USER deploy/ssl/*

# Обновите deploy/nginx-docker.conf для HTTPS:
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 100M;

    location / {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

```bash
# Перезапустите Nginx
docker compose -f docker-compose.prod.yml up -d nginx
```

### Автообновление SSL сертификатов

```bash
# Создайте скрипт обновления
sudo tee /usr/local/bin/renew-nodus-ssl.sh > /dev/null << 'EOF'
#!/bin/bash
certbot renew --quiet
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ~/projects/NODUS_s/deploy/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ~/projects/NODUS_s/deploy/ssl/
cd ~/projects/NODUS_s
docker compose -f docker-compose.prod.yml restart nginx
EOF

sudo chmod +x /usr/local/bin/renew-nodus-ssl.sh

# Добавьте в crontab (запуск каждый день в 3 утра)
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/renew-nodus-ssl.sh") | crontab -
```

---

## 🛡️ Firewall (опционально)

```bash
# Установите ufw
sudo apt install -y ufw

# Разрешите нужные порты
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Включите firewall
sudo ufw enable

# Проверьте статус
sudo ufw status verbose
```

---

## 🔍 Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Логи конкретного контейнера
docker logs -f nodus_backend

# Информация о контейнере
docker inspect nodus_backend

# Дисковое пространство Docker
docker system df

# Очистка неиспользуемых образов и контейнеров
docker system prune -a
```

---

## ⚠️ Troubleshooting

### Проблема: Контейнер не стартует

```bash
# Проверьте логи
docker compose -f docker-compose.prod.yml logs backend

# Проверьте статус
docker compose -f docker-compose.prod.yml ps

# Пересоздайте контейнеры
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### Проблема: База данных не подключается

```bash
# Проверьте что PostgreSQL запущен
docker compose -f docker-compose.prod.yml ps postgres

# Проверьте логи PostgreSQL
docker compose -f docker-compose.prod.yml logs postgres

# Проверьте подключение
docker compose exec postgres pg_isready -U postgres
```

### Проблема: WebSocket не работает

```bash
# Проверьте логи Nginx
docker compose -f docker-compose.prod.yml logs nginx

# Убедитесь что proxy_pass настроен
docker compose exec nginx cat /etc/nginx/conf.d/default.conf
```

### Проблема: Нехватка памяти

```bash
# Проверьте использование памяти
docker stats --no-stream

# Уменьшите количество workers в docker-compose.prod.yml:
# uvicorn app.main:app --workers 2  # вместо 4

# Перезапустите
docker compose -f docker-compose.prod.yml up -d backend
```

---

## 📈 Production Checklist

Перед запуском в production:

- [ ] Изменены все пароли в `.env`
- [ ] JWT секретные ключи случайные и длинные (32+ символа)
- [ ] Настроен SSL сертификат
- [ ] Настроен firewall (ufw)
- [ ] Настроены регулярные бэкапы базы данных
- [ ] Настроено автообновление SSL сертификатов
- [ ] Проверена работа WebSocket
- [ ] Настроен мониторинг (опционально)
- [ ] Проверена загрузка файлов (MinIO)
- [ ] Протестированы все API endpoints

---

## 🎉 Готово!

Ваше приложение запущено в Docker и готово к использованию!

**Доступ:**
- API: `http://your-domain.com/api/`
- WebSocket: `ws://your-domain.com/ws`
- Health: `http://your-domain.com/health`

**Полезные команды:**
```bash
# Быстрый рестарт
docker compose -f docker-compose.prod.yml restart

# Обновление
git pull && docker compose -f docker-compose.prod.yml up -d --build

# Логи
docker compose -f docker-compose.prod.yml logs -f

# Статус
docker compose -f docker-compose.prod.yml ps

# Остановка
docker compose -f docker-compose.prod.yml stop

# Полное удаление (осторожно!)
docker compose -f docker-compose.prod.yml down -v
```

---

## 📚 Дополнительные ресурсы

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI in Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)
- [MinIO Docker](https://min.io/docs/minio/container/index.html)
