#!/bin/bash
# Быстрый скрипт установки NODUS Backend на Ubuntu 22.04
# Запуск: curl -sSL https://your-repo/deploy/quick-start.sh | bash

set -e

echo "🚀 NODUS Backend Quick Installation Script"
echo "==========================================="
echo ""

# Проверка root прав
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)" 
   exit 1
fi

# Запрос данных
read -p "Enter domain name or IP: " DOMAIN
read -p "Enter PostgreSQL password: " -s DB_PASSWORD
echo ""
read -p "Enter JWT secret key (min 32 chars): " -s JWT_SECRET
echo ""
read -p "Enter MinIO password: " -s MINIO_PASSWORD
echo ""

echo "📦 Installing system packages..."
apt update && apt upgrade -y
apt install -y software-properties-common build-essential git curl nginx postgresql redis-server

echo "🐍 Installing Python 3.12..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.12 python3.12-venv python3.12-dev

echo "🗄️ Setting up PostgreSQL..."
sudo -u postgres psql << EOF
CREATE DATABASE nodus;
CREATE USER nodus WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE nodus TO nodus;
ALTER DATABASE nodus OWNER TO nodus;
EOF

echo "📥 Installing MinIO..."
wget -q https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
mv minio /usr/local/bin/
useradd -r minio-user -s /sbin/nologin || true
mkdir -p /mnt/data/minio
chown minio-user:minio-user /mnt/data/minio

cat > /etc/systemd/system/minio.service << 'EOF'
[Unit]
Description=MinIO
After=network-online.target

[Service]
User=minio-user
Group=minio-user
Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}"
ExecStart=/usr/local/bin/minio server /mnt/data/minio --console-address ":9001"
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start minio
systemctl enable minio

echo "👤 Creating application user..."
useradd -m -s /bin/bash nodus || true

echo "📥 Cloning repository..."
cd /home/nodus
sudo -u nodus git clone https://github.com/your-username/NODUS_s.git || echo "Repository already exists"
cd NODUS_s

echo "🐍 Setting up Python environment..."
sudo -u nodus python3.12 -m venv venv
sudo -u nodus bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -e ."

echo "📝 Creating .env file..."
sudo -u nodus cat > .env << EOF
APP_NAME=NODUS_s
APP_VERSION=0.1.0
DATABASE_URL=postgresql+psycopg://nodus:${DB_PASSWORD}@localhost:5432/nodus
REDIS_URL=redis://localhost:6379/0
RQ_REDIS_URL=redis://localhost:6379/1
JWT_SECRET_KEY=${JWT_SECRET}
JWT_REFRESH_SECRET_KEY=${JWT_SECRET}_refresh
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=15
REFRESH_TOKEN_EXPIRES_MINUTES=10080
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=${MINIO_PASSWORD}
S3_BUCKET=attachments
EOF

echo "🗄️ Running database migrations..."
sudo -u nodus bash -c "source venv/bin/activate && alembic upgrade head"

echo "⚙️ Setting up systemd service..."
cp deploy/nodus-backend.service /etc/systemd/system/
mkdir -p /var/log/nodus-backend
chown nodus:nodus /var/log/nodus-backend

systemctl daemon-reload
systemctl start nodus-backend
systemctl enable nodus-backend

echo "🌐 Configuring Nginx..."
sed "s/your-domain.com/${DOMAIN}/g" deploy/nginx.conf > /etc/nginx/sites-available/nodus-backend
ln -sf /etc/nginx/sites-available/nodus-backend /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "✅ Installation completed!"
echo "========================="
echo ""
echo "🌐 API: http://${DOMAIN}/api/"
echo "🔌 WebSocket: ws://${DOMAIN}/ws"
echo "❤️ Health: http://${DOMAIN}/health"
echo ""
echo "📊 Check status: sudo systemctl status nodus-backend"
echo "📋 View logs: sudo journalctl -u nodus-backend -f"
echo ""
echo "🔒 To enable SSL, run: sudo certbot --nginx -d ${DOMAIN}"
echo ""
