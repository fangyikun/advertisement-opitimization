#!/bin/bash
# 在服务器项目根目录执行，创建 deploy 所需文件（无需从 GitHub 拉取 deploy）
# 用法：bash deploy/server-setup.sh  或先上传此文件后执行

cd "$(dirname "$0")/.." || exit 1
mkdir -p deploy

# 创建 .env 模板（无密码，需手动编辑）
if [ ! -f sign-inspire-backend/.env ]; then
  cat > sign-inspire-backend/.env << 'EOF'
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=sign_inspire
GOOGLE_PLACES_API_KEY=
OPENAI_API_KEY=
EOF
  echo "已创建 sign-inspire-backend/.env，请编辑填写 DB_PASSWORD 等"
fi

# 创建 nginx.conf
cat > deploy/nginx.conf << 'EOF'
server {
    listen 80;
    server_name _;
    root /var/www/lingxi/frontend;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /health { proxy_pass http://127.0.0.1:8000/; }
}
EOF

# 创建 systemd 服务（User 用 root，因 deploy.sh 以当前用户运行）
cat > deploy/lingxi-backend.service << EOF
[Unit]
Description=Lingxi Backend (FastAPI)
After=network.target mysql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/var/www/lingxi/backend
Environment="PATH=/var/www/lingxi/venv/bin"
ExecStart=/var/www/lingxi/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "deploy 文件已创建。编辑 .env 后执行: ./deploy/deploy.sh"
