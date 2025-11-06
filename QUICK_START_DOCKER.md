# 🐳 Docker Quick Start - NODUS Backend

## 30 секунд до запуска!

### На сервере Ubuntu 22:

```bash
# 1. Установка Docker (одна команда!)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# ПЕРЕЛОГИНЬТЕСЬ после этого!

# 2. Клонирование и настройка
git clone https://github.com/your-username/NODUS_s.git
cd NODUS_s
cp .env.production .env
nano .env  # Измените пароли!

# 3. Запуск (одна команда!)
docker compose -f docker-compose.prod.yml up -d --build

# ✅ ГОТОВО! Проверьте:
curl http://localhost/health
```

---

## 🔧 Основные команды

```bash
# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f

# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Перезапуск
docker compose -f docker-compose.prod.yml restart

# Обновление кода
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Остановка
docker compose -f docker-compose.prod.yml stop

# Миграции (автоматически применяются при старте!)
docker compose exec backend alembic upgrade head
```

---

## 📊 Что внутри?

Docker автоматически запускает:
- ✅ **PostgreSQL** - база данных
- ✅ **Redis** - кэширование и WebSocket pub/sub
- ✅ **MinIO** - хранилище файлов (S3-совместимое)
- ✅ **Backend** - FastAPI приложение (4 workers)
- ✅ **Nginx** - reverse proxy

**Никаких ручных установок!**

---

## 🔒 SSL (Let's Encrypt)

```bash
# На хосте (не в Docker)
sudo apt install -y certbot
docker compose -f docker-compose.prod.yml stop nginx

sudo certbot certonly --standalone -d your-domain.com

mkdir -p deploy/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/*.pem deploy/ssl/
sudo chown $USER:$USER deploy/ssl/*

# Обновите deploy/nginx-docker.conf для HTTPS
docker compose -f docker-compose.prod.yml up -d nginx
```

---

## ⚠️ Важно!

В `.env` файле измените:
- `POSTGRES_PASSWORD` - пароль PostgreSQL
- `JWT_SECRET_KEY` - секретный ключ JWT (минимум 32 символа!)
- `JWT_REFRESH_SECRET_KEY` - секретный ключ refresh token
- `MINIO_ROOT_PASSWORD` - пароль MinIO

---

## 📖 Полная документация

Смотрите `DOCKER_DEPLOYMENT.md` для:
- SSL настройки
- Мониторинг
- Troubleshooting
- Production checklist
- Бэкапы БД

---

## 🎯 Доступ к API

- **API:** `http://your-server/api/`
- **WebSocket:** `ws://your-server/ws`
- **Health:** `http://your-server/health`

---

## 💡 Сравнение: Docker vs Нативная установка

| Действие | Docker | Нативно |
|----------|--------|---------|
| Установка Python | ❌ Не нужно | ✅ Нужно |
| Установка PostgreSQL | ❌ Не нужно | ✅ Нужно |
| Установка Redis | ❌ Не нужно | ✅ Нужно |
| Установка MinIO | ❌ Не нужно | ✅ Нужно |
| Настройка systemd | ❌ Не нужно | ✅ Нужно |
| **Время установки** | **5 минут** | **30-60 минут** |
| **Команд для установки** | **3 команды** | **50+ команд** |
| Обновление | `git pull && docker compose up -d --build` | 10+ команд |
| Откат | `docker compose down && git checkout old` | Сложно |

**Docker = Проще, Быстрее, Надежнее! 🚀**
