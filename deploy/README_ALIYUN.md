# 灵犀 · 阿里云部署指南

前后端一体部署到阿里云 ECS，Nginx + Uvicorn + MySQL。

---

## 一、服务器准备

### 1. 安装环境

**重要：Node.js 需 18+（推荐 20）**，Ubuntu 默认 12 无法构建前端。

```bash
# Node.js 20（Ubuntu）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v   # 应显示 v20.x

# 或 CentOS
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

# Python 3.10+
sudo yum install -y python3 python3-pip python3-venv

# Nginx
sudo yum install -y nginx

# MySQL 8
sudo yum install -y mysql-server
sudo systemctl start mysqld
sudo mysql_secure_installation
```

### 2. 创建数据库

```sql
CREATE DATABASE sign_inspire CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lingxi'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL ON sign_inspire.* TO 'lingxi'@'localhost';
FLUSH PRIVILEGES;
```

---

## 二、部署步骤

### 1. 上传代码到服务器

```bash
# 方式 A：Git 克隆（推荐）
cd /tmp
git clone https://github.com/fangyikun/advertisement-opitimization.git lingxi-src
cd lingxi-src

# 方式 B：本地打包后 SCP 上传
# 本地执行：tar czvf lingxi.tar.gz sign-inspire-frontend sign-inspire-backend deploy
# scp lingxi.tar.gz user@你的服务器IP:/tmp/
# 服务器上：cd /var/www && tar xzvf /tmp/lingxi.tar.gz -C lingxi-src
```

### 2. 准备 .env

```bash
# 在项目目录下
cp deploy/env.example sign-inspire-backend/.env
nano sign-inspire-backend/.env   # 填写 DB_PASSWORD、GOOGLE_PLACES_API_KEY、OPENAI_API_KEY 等
```

### 3. 执行部署脚本

```bash
cd /var/www/lingxi-src
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

### 4. 修改 Nginx 域名（可选）

若有域名，编辑 `/etc/nginx/conf.d/lingxi.conf`：

```nginx
server_name lingxi.你的域名.com;
```

重载 Nginx：`sudo systemctl reload nginx`

---

## 三、常用命令

| 操作         | 命令                                          |
|--------------|-----------------------------------------------|
| 查看后端日志 | `sudo journalctl -u lingxi-backend -f`        |
| 重启后端     | `sudo systemctl restart lingxi-backend`       |
| 重新部署     | 拉取最新代码后再次执行 `./deploy/deploy.sh`   |

---

## 四、目录结构（部署后）

```
/var/www/lingxi/
├── backend/      # FastAPI 后端
├── frontend/     # 前端静态文件（React build）
└── venv/         # Python 虚拟环境
```

---

## 五、注意事项

1. **安全组**：开放 80 端口（HTTP）
2. **HTTPS**：建议配置证书（Let's Encrypt），Nginx 增加 `listen 443 ssl`
3. **数据库**：也可用阿里云 RDS，修改 .env 中 `DB_HOST` 为 RDS 地址
