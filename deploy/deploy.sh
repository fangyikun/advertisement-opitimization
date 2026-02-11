#!/bin/bash
# 灵犀 · 阿里云一键部署脚本
# 在服务器上执行：bash deploy.sh
# 需提前：1) 安装 Node.js、Python3、nginx、MySQL  2) 创建数据库 sign_inspire

set -e
APP_DIR="/var/www/lingxi"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$APP_DIR/venv"

echo "==> 灵犀 部署开始"

# 0. 检查是否在项目根目录
[ ! -d sign-inspire-frontend ] || [ ! -d sign-inspire-backend ] && { echo "请在项目根目录执行此脚本"; exit 1; }

# 1. 创建目录
sudo mkdir -p "$APP_DIR" "$BACKEND_DIR" "$FRONTEND_DIR"
[ -w "$APP_DIR" ] || sudo chown -R $(whoami) "$APP_DIR"

# 2. 构建前端（在项目 sign-inspire-frontend 目录执行）
echo "==> 构建前端..."
cd sign-inspire-frontend
export VITE_BASE=/
export VITE_API_URL=/api/v1
npm ci
npm run build
cp -r dist/* "$FRONTEND_DIR/"
cd ..

# 3. 部署后端（完整复制，保持 app 包结构，不覆盖 .env）
echo "==> 部署后端..."
cp -r sign-inspire-backend/* "$BACKEND_DIR/"
rm -rf "$BACKEND_DIR/__pycache__" "$BACKEND_DIR/app/__pycache__" 2>/dev/null || true
[ -f sign-inspire-backend/.env ] && cp sign-inspire-backend/.env "$BACKEND_DIR/"

# 4. Python 虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q

# 5. 复制 .env（若存在）
if [ -f sign-inspire-backend/.env ]; then
    cp sign-inspire-backend/.env "$BACKEND_DIR/"
    echo "    已复制 .env"
else
    echo "    ⚠ 请手动创建 $BACKEND_DIR/.env，参考下方 README"
fi

# 6. 安装 nginx 配置
sudo cp deploy/nginx.conf /etc/nginx/conf.d/lingxi.conf
sudo nginx -t && sudo systemctl reload nginx

# 7. 安装 systemd 服务
sudo cp deploy/lingxi-backend.service /etc/systemd/system/
sudo sed -i "s|User=www-data|User=$(whoami)|g" /etc/systemd/system/lingxi-backend.service 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable lingxi-backend
sudo systemctl restart lingxi-backend

echo ""
echo "==> 部署完成！"
echo "    前端: http://$(hostname -I | awk '{print $1}')/"
echo "    后端: http://$(hostname -I | awk '{print $1}')/api/v1/"
echo ""
echo "    查看日志: sudo journalctl -u lingxi-backend -f"
