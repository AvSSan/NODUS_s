# 🔧 Быстрое исправление ошибки порта 443

## Проблема
Порт 443 уже занят системным Nginx на сервере.

## ✅ Решение
Используем системный Nginx вместо Docker Nginx.

---

## 📋 Шаги на сервере:

### 1. Обновите файлы проекта

```bash
cd ~/NODUS_s

# Если используете Git:
git pull origin main

# Или скопируйте файлы напрямую:
# scp docker-compose.prod.yml root@server:~/NODUS_s/
# scp deploy/nginx-host.conf root@server:~/NODUS_s/deploy/
# scp deploy/setup-nginx-host.sh root@server:~/NODUS_s/deploy/
```

### 2. Остановите старые контейнеры

```bash
docker compose -f docker-compose.prod.yml down
```

### 3. Запустите заново (без Nginx в Docker)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Настройте системный Nginx

```bash
# Сделайте скрипт исполняемым
chmod +x deploy/setup-nginx-host.sh

# Запустите скрипт
sudo bash deploy/setup-nginx-host.sh
```

Скрипт спросит ваш домен и автоматически настроит Nginx!

### 5. Проверьте работу

```bash
# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Статус Nginx
sudo systemctl status nginx

# Проверка API
curl http://localhost/health
# Ожидается: {"status":"ok"}
```

---

## 🔒 Настройка SSL (опционально)

После того как всё работает:

```bash
# Установите certbot если еще не установлен
sudo apt install -y certbot python3-certbot-nginx

# Получите SSL сертификат
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Certbot автоматически настроит HTTPS!
```

---

## 📊 Итоговая архитектура:

```
Internet
    ↓
Nginx (системный, порты 80/443)
    ↓
Docker Backend (порт 127.0.0.1:8000)
    ↓
PostgreSQL, Redis, MinIO (в Docker)
```

---

## 🎯 Теперь доступно:

- **API:** `http://your-domain.com/api/`
- **WebSocket:** `ws://your-domain.com/ws`
- **Health:** `http://your-domain.com/health`
- **После SSL:** `https://your-domain.com/...`

---

## 💡 Преимущества этого подхода:

✅ Использует существующий Nginx  
✅ Легче управлять SSL сертификатами  
✅ Меньше портов занято  
✅ Стандартный production setup  
✅ Backend изолирован (доступен только через Nginx)

---

## ⚠️ Troubleshooting

### Nginx не перезагружается

```bash
# Проверьте конфигурацию
sudo nginx -t

# Посмотрите логи
sudo tail -f /var/log/nginx/error.log
```

### Backend недоступен

```bash
# Проверьте что backend запущен
docker compose -f docker-compose.prod.yml ps

# Проверьте логи
docker compose -f docker-compose.prod.yml logs backend

# Проверьте что порт 8000 слушается
ss -tlnp | grep 8000
```

### Всё равно ошибка 443

```bash
# Найдите что занимает порт
sudo lsof -i :443

# Или
sudo ss -tlnp | grep :443

# Если там Apache или другой сервис - остановите его
sudo systemctl stop apache2
# или
sudo systemctl stop httpd
```

---

Готово! Теперь всё должно работать! 🎉
