# 🚀 Deployment Guide

## Развертывание NODUS_s в Production

---

## 📋 Предварительные требования

- Docker & Docker Compose 20.10+
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- MinIO или AWS S3
- Доменное имя с SSL сертификатом

---

## 🔧 Настройка окружения

### 1. Переменные окружения

Создайте `.env` файл на основе `.env.example`:

```bash
cp .env.example .env
```

**Обязательно измените следующие значения для production:**

```env
# Application
APP_NAME=NODUS_s
APP_VERSION=1.0.0

# Database (используйте сильный пароль!)
DATABASE_URL=postgresql+psycopg://nodus_user:STRONG_PASSWORD@postgres:5432/nodus_prod

# Redis
REDIS_URL=redis://redis:6379/0
RQ_REDIS_URL=redis://redis:6379/1

# JWT Settings (ОБЯЗАТЕЛЬНО поменяйте на случайные строки!)
JWT_SECRET_KEY=CHANGE_THIS_TO_RANDOM_STRING_32_CHARS_MIN
JWT_REFRESH_SECRET_KEY=CHANGE_THIS_TO_ANOTHER_RANDOM_STRING
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=15
REFRESH_TOKEN_EXPIRES_MINUTES=10080

# S3 / MinIO
S3_ENDPOINT_URL=https://s3.your-domain.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=nodus-attachments
```

**Генерация сильных секретов:**
```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🐳 Docker Production Setup

### 1. Production Docker Compose

Создайте `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: nodus_prod
      POSTGRES_USER: nodus_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    networks:
      - nodus_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nodus_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_prod_data:/data
    networks:
      - nodus_network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: always
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - nodus_network
    ports:
      - "8000:8000"

  worker:
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: always
    command: rq worker audio --url ${RQ_REDIS_URL}
    environment:
      - RQ_REDIS_URL=${RQ_REDIS_URL}
    depends_on:
      - redis
    networks:
      - nodus_network

  nginx:
    image: nginx:alpine
    restart: always
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    networks:
      - nodus_network

volumes:
  postgres_prod_data:
  redis_prod_data:

networks:
  nodus_network:
    driver: bridge
```

### 2. Dockerfile для Production

Создайте `Dockerfile.prod`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов проекта
COPY pyproject.toml .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Установка Python зависимостей
RUN pip install --no-cache-dir -e .

# Создание non-root пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3. Nginx конфигурация

Создайте `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name your-domain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security Headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # Logs
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;

        # API endpoints
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # WebSocket
        location /ws {
            proxy_pass http://app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_read_timeout 86400;
        }

        # Health check
        location /health {
            proxy_pass http://app;
            access_log off;
        }

        # Docs (опционально отключить в prod)
        location /docs {
            proxy_pass http://app;
        }
    }
}
```

---

## 🚀 Процесс развертывания

### 1. Подготовка сервера

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установить Docker Compose
sudo apt install docker-compose-plugin

# Создать пользователя для приложения
sudo useradd -m -s /bin/bash nodus
sudo usermod -aG docker nodus
```

### 2. Клонирование проекта

```bash
sudo su - nodus
git clone <repository-url> /home/nodus/nodus_s
cd /home/nodus/nodus_s
```

### 3. Настройка окружения

```bash
# Создать .env файл
cp .env.example .env
nano .env  # Отредактировать все значения

# Создать директорию для SSL
mkdir -p ssl
# Скопировать SSL сертификаты в ssl/
```

### 4. Применение миграций

```bash
# Запустить базу данных
docker-compose -f docker-compose.prod.yml up -d postgres redis

# Дождаться готовности
sleep 10

# Применить миграции
docker-compose -f docker-compose.prod.yml run --rm app alembic upgrade head
```

### 5. Запуск приложения

```bash
# Запустить все сервисы
docker-compose -f docker-compose.prod.yml up -d

# Проверить логи
docker-compose -f docker-compose.prod.yml logs -f

# Проверить статус
docker-compose -f docker-compose.prod.yml ps
```

### 6. Проверка работоспособности

```bash
# Health check
curl https://your-domain.com/health

# API test
curl https://your-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"email":"test@example.com","password":"test123","display_name":"Test User"}'
```

---

## 🔐 Безопасность

### 1. Firewall настройка

```bash
# UFW
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 2. SSL сертификаты (Let's Encrypt)

```bash
# Установить Certbot
sudo apt install certbot

# Получить сертификат
sudo certbot certonly --standalone -d your-domain.com

# Скопировать в проект
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/
sudo chown nodus:nodus ./ssl/*

# Автоматическое обновление (cron)
sudo crontab -e
# Добавить: 0 0 * * 0 certbot renew --quiet && docker-compose restart nginx
```

### 3. Database backup

```bash
# Создать скрипт backup.sh
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/nodus/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker-compose exec -T postgres pg_dump -U nodus_user nodus_prod | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Удалить старые backup'ы (старше 7 дней)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Добавить в cron (ежедневно в 2:00)
crontab -e
# Добавить: 0 2 * * * /home/nodus/nodus_s/backup.sh
```

---

## 📊 Мониторинг

### 1. Логи

```bash
# Просмотр логов приложения
docker-compose logs -f app

# Просмотр логов worker
docker-compose logs -f worker

# Логи Nginx
docker-compose logs -f nginx

# Все логи
docker-compose logs -f
```

### 2. Prometheus + Grafana (опционально)

Добавьте в `docker-compose.prod.yml`:

```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - nodus_network

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - nodus_network
```

---

## 🔄 Обновления

### Процесс обновления приложения

```bash
cd /home/nodus/nodus_s

# Получить последние изменения
git pull origin main

# Остановить приложение
docker-compose -f docker-compose.prod.yml down

# Применить миграции
docker-compose -f docker-compose.prod.yml run --rm app alembic upgrade head

# Пересобрать образы
docker-compose -f docker-compose.prod.yml build

# Запустить обновленное приложение
docker-compose -f docker-compose.prod.yml up -d

# Проверить логи
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🚨 Troubleshooting

### Проблема: Приложение не запускается

```bash
# Проверить логи
docker-compose logs app

# Проверить переменные окружения
docker-compose config

# Проверить подключение к БД
docker-compose exec postgres psql -U nodus_user -d nodus_prod -c "SELECT 1"
```

### Проблема: 502 Bad Gateway

```bash
# Проверить статус app
docker-compose ps app

# Перезапустить app
docker-compose restart app

# Проверить логи nginx
docker-compose logs nginx
```

### Проблема: WebSocket не работает

- Проверьте конфигурацию Nginx (upgrade headers)
- Проверьте firewall правила
- Проверьте SSL сертификаты

---

## ✅ Checklist для production

- [ ] Изменены все секретные ключи в `.env`
- [ ] Настроен SSL сертификат
- [ ] Настроен firewall
- [ ] Настроены автоматические backup'ы
- [ ] Настроен мониторинг и алерты
- [ ] Протестированы все endpoints
- [ ] Настроен CORS для конкретных доменов
- [ ] Отключен debug режим
- [ ] Настроен логирование
- [ ] Создан non-root пользователь в Docker
- [ ] Документация обновлена

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Проверьте документацию
3. Создайте issue в репозитории

---

**Version:** 1.0.0  
**Last Updated:** 2024-03-26
