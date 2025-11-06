# 🚀 Инструкция по деплою NODUS Backend на Ubuntu 22.04

## 📋 Предварительные требования

- Ubuntu 22.04 LTS
- Минимум 2GB RAM
- 20GB свободного места на диске
- Root или sudo доступ
- Домен или IP адрес (опционально для SSL)

---

## 1️⃣ Обновление системы и установка базовых пакетов

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем необходимые пакеты
sudo apt install -y software-properties-common build-essential git curl nginx certbot python3-certbot-nginx
```

---

## 2️⃣ Установка Python 3.12

```bash
# Добавляем PPA для Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Устанавливаем Python 3.12 и зависимости
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Проверяем версию
python3.12 --version
```

---

## 3️⃣ Установка PostgreSQL

```bash
# Устанавливаем PostgreSQL 15
sudo apt install -y postgresql postgresql-contrib

# Запускаем и добавляем в автозагрузку
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создаем базу данных и пользователя
sudo -u postgres psql << EOF
CREATE DATABASE nodus;
CREATE USER nodus WITH ENCRYPTED PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE nodus TO nodus;
ALTER DATABASE nodus OWNER TO nodus;
\q
EOF

# Проверяем подключение
psql -U nodus -d nodus -h localhost -W
```

---

## 4️⃣ Установка Redis

```bash
# Устанавливаем Redis
sudo apt install -y redis-server

# Настраиваем Redis для production
sudo sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf

# Перезапускаем и добавляем в автозагрузку
sudo systemctl restart redis
sudo systemctl enable redis

# Проверяем работу
redis-cli ping
# Должно вернуть: PONG
```

---

## 5️⃣ Установка MinIO (для хранения файлов)

```bash
# Скачиваем MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
sudo chmod +x minio
sudo mv minio /usr/local/bin/

# Создаем пользователя и директории
sudo useradd -r minio-user -s /sbin/nologin
sudo mkdir -p /mnt/data/minio
sudo chown minio-user:minio-user /mnt/data/minio

# Создаем systemd service
sudo tee /etc/systemd/system/minio.service > /dev/null << 'EOF'
[Unit]
Description=MinIO
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
WorkingDirectory=/usr/local

User=minio-user
Group=minio-user

Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=minioadmin_password_change_me"

ExecStart=/usr/local/bin/minio server /mnt/data/minio --console-address ":9001"

Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Запускаем MinIO
sudo systemctl daemon-reload
sudo systemctl start minio
sudo systemctl enable minio

# Проверяем статус
sudo systemctl status minio

# MinIO Console доступна по адресу: http://your-server-ip:9001
```

---

## 6️⃣ Создание пользователя и настройка проекта

```bash
# Создаем пользователя для приложения
sudo useradd -m -s /bin/bash nodus
sudo usermod -aG sudo nodus

# Переключаемся на пользователя nodus
sudo su - nodus

# Клонируем репозиторий (замените URL на свой)
git clone https://github.com/your-username/NODUS_s.git
cd NODUS_s

# Создаем виртуальное окружение
python3.12 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip setuptools wheel
pip install -e .

# Создаем .env файл
cp .env.example .env
nano .env
```

### Пример `.env` файла:

```env
# Application
APP_NAME=NODUS_s
APP_VERSION=0.1.0

# Database
DATABASE_URL=postgresql+psycopg://nodus:your_secure_password_here@localhost:5432/nodus

# Redis
REDIS_URL=redis://localhost:6379/0
RQ_REDIS_URL=redis://localhost:6379/1

# JWT
JWT_SECRET_KEY=your_very_long_random_secret_key_here_min_32_chars
JWT_REFRESH_SECRET_KEY=your_very_long_random_refresh_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=15
REFRESH_TOKEN_EXPIRES_MINUTES=10080

# S3/MinIO
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin_password_change_me
S3_BUCKET=attachments
```

**Важно:** Замените все пароли и секретные ключи на свои!

---

## 7️⃣ Применение миграций базы данных

```bash
# Активируем виртуальное окружение (если не активно)
source venv/bin/activate

# Применяем миграции
alembic upgrade head

# Проверяем подключение к БД
python -c "from app.core.config import settings; print(settings.database_url)"
```

---

## 8️⃣ Настройка systemd service

```bash
# Выходим из пользователя nodus
exit

# Копируем service файл
sudo cp /home/nodus/NODUS_s/deploy/nodus-backend.service /etc/systemd/system/

# Создаем директорию для логов
sudo mkdir -p /var/log/nodus-backend
sudo chown nodus:nodus /var/log/nodus-backend

# Перезагружаем systemd и запускаем сервис
sudo systemctl daemon-reload
sudo systemctl start nodus-backend
sudo systemctl enable nodus-backend

# Проверяем статус
sudo systemctl status nodus-backend

# Смотрим логи в реальном времени
sudo journalctl -u nodus-backend -f
```

---

## 9️⃣ Настройка Nginx

```bash
# Копируем конфигурацию Nginx
sudo cp /home/nodus/NODUS_s/deploy/nginx.conf /etc/nginx/sites-available/nodus-backend

# Редактируем конфигурацию (замените your-domain.com на свой домен)
sudo nano /etc/nginx/sites-available/nodus-backend

# Создаем символическую ссылку
sudo ln -s /etc/nginx/sites-available/nodus-backend /etc/nginx/sites-enabled/

# Удаляем дефолтный конфиг
sudo rm /etc/nginx/sites-enabled/default

# Проверяем конфигурацию
sudo nginx -t

# Перезапускаем Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 🔒 10. Настройка SSL (Let's Encrypt)

**Только для доменов! Не работает с IP адресами.**

```bash
# Устанавливаем SSL сертификат
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Certbot автоматически настроит Nginx для HTTPS

# Проверяем автообновление сертификата
sudo certbot renew --dry-run

# Сертификаты будут автоматически обновляться
```

---

## 🔍 11. Проверка работы

```bash
# Проверяем статус всех сервисов
sudo systemctl status nodus-backend
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis
sudo systemctl status minio

# Проверяем health endpoint
curl http://localhost:8000/health
# Должно вернуть: {"status":"ok"}

# Проверяем через Nginx
curl http://your-domain.com/health

# Проверяем логи
sudo journalctl -u nodus-backend -n 50
sudo tail -f /var/log/nodus-backend/error.log
sudo tail -f /var/log/nginx/error.log
```

---

## 🔄 12. Автоматический деплой при обновлениях

```bash
# Делаем скрипт деплоя исполняемым
chmod +x /home/nodus/NODUS_s/deploy/deploy.sh

# Настраиваем sudo без пароля для systemctl (опционально)
sudo visudo

# Добавьте строку:
# nodus ALL=(ALL) NOPASSWD: /bin/systemctl restart nodus-backend, /bin/systemctl status nodus-backend

# Теперь для деплоя новой версии просто запустите:
cd /home/nodus/NODUS_s
bash deploy/deploy.sh
```

---

## 🛡️ 13. Настройка firewall (опционально)

```bash
# Устанавливаем UFW
sudo apt install -y ufw

# Разрешаем необходимые порты
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Включаем firewall
sudo ufw enable

# Проверяем статус
sudo ufw status verbose
```

---

## 📊 14. Мониторинг и логи

### Просмотр логов приложения:
```bash
# Логи systemd
sudo journalctl -u nodus-backend -f

# Логи файлов
sudo tail -f /var/log/nodus-backend/access.log
sudo tail -f /var/log/nodus-backend/error.log

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Проверка ресурсов:
```bash
# Использование памяти и CPU
htop

# Дисковое пространство
df -h

# Активные подключения
ss -tulpn | grep :8000
```

---

## 🔧 15. Полезные команды

```bash
# Перезапуск бэкенда
sudo systemctl restart nodus-backend

# Остановка бэкенда
sudo systemctl stop nodus-backend

# Просмотр статуса
sudo systemctl status nodus-backend

# Применение новых миграций
sudo su - nodus
cd NODUS_s
source venv/bin/activate
alembic upgrade head

# Откат миграции
alembic downgrade -1

# Создание бэкапа базы данных
pg_dump -U nodus -h localhost nodus > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление базы данных
psql -U nodus -h localhost nodus < backup_20240101_120000.sql
```

---

## ⚠️ Troubleshooting

### Проблема: Ошибка подключения к БД
```bash
# Проверьте статус PostgreSQL
sudo systemctl status postgresql

# Проверьте строку подключения в .env
cat /home/nodus/NODUS_s/.env | grep DATABASE_URL

# Проверьте логи PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Проблема: WebSocket не работает
```bash
# Проверьте Nginx конфигурацию для /ws endpoint
sudo nginx -t

# Проверьте логи Nginx
sudo tail -f /var/log/nginx/error.log

# Убедитесь что proxy_pass настроен правильно
```

### Проблема: Высокое использование памяти
```bash
# Уменьшите количество workers в systemd service
sudo nano /etc/systemd/system/nodus-backend.service
# Измените --workers 4 на --workers 2

sudo systemctl daemon-reload
sudo systemctl restart nodus-backend
```

---

## 🎉 Готово!

Ваш NODUS Backend развернут и готов к использованию!

- **API:** `http://your-domain.com/api/`
- **WebSocket:** `ws://your-domain.com/ws`
- **Health Check:** `http://your-domain.com/health`
- **MinIO Console:** `http://your-domain.com:9001` (если открыли порт)

### Следующие шаги:
1. ✅ Настройте регулярные бэкапы базы данных
2. ✅ Настройте мониторинг (Grafana, Prometheus)
3. ✅ Настройте алерты о проблемах
4. ✅ Разверните фронтенд приложение
5. ✅ Настройте CI/CD для автоматического деплоя

---

## 📞 Поддержка

При возникновении проблем проверьте:
- Логи приложения: `sudo journalctl -u nodus-backend -f`
- Логи Nginx: `sudo tail -f /var/log/nginx/error.log`
- Статус сервисов: `sudo systemctl status nodus-backend postgresql redis nginx`
