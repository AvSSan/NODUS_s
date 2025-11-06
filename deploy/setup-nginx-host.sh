#!/bin/bash
# Скрипт для настройки системного Nginx как reverse proxy для Docker backend

set -e

echo "🌐 Setting up Nginx on host..."

# Проверка что скрипт запущен от root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)" 
   exit 1
fi

# Спросить домен
read -p "Enter your domain name (or press Enter for IP-only setup): " DOMAIN

if [ -z "$DOMAIN" ]; then
    DOMAIN="_"
    echo "📍 Using IP-only configuration"
else
    echo "📍 Using domain: $DOMAIN"
fi

# Копируем конфигурацию
cp deploy/nginx-host.conf /etc/nginx/sites-available/nodus-backend

# Заменяем домен в конфигурации
sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/nodus-backend

# Создаем symlink
ln -sf /etc/nginx/sites-available/nodus-backend /etc/nginx/sites-enabled/

# Удаляем дефолтный конфиг если существует
rm -f /etc/nginx/sites-enabled/default

# Проверяем конфигурацию
echo "🔍 Testing Nginx configuration..."
nginx -t

# Перезагружаем Nginx
echo "🔄 Reloading Nginx..."
systemctl reload nginx

echo ""
echo "✅ Nginx configured successfully!"
echo ""
echo "📊 Status:"
systemctl status nginx --no-pager -l

echo ""
echo "🌐 Your API is now available at:"
if [ "$DOMAIN" = "_" ]; then
    echo "   http://YOUR_SERVER_IP/api/"
    echo "   ws://YOUR_SERVER_IP/ws"
else
    echo "   http://$DOMAIN/api/"
    echo "   ws://$DOMAIN/ws"
fi

echo ""
echo "🔒 To enable HTTPS with Let's Encrypt:"
echo "   sudo certbot --nginx -d $DOMAIN"
echo ""
