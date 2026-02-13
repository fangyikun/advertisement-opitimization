# 灵犀 · DigitalOcean 部署指南

在澳洲部署灵犀，使用 Google Places 等海外 API 无障碍。

---

## 一、注册与创建 Droplet

### 1. 领取学生福利（可选）
- 先申请 [GitHub Student Developer Pack](https://education.github.com/pack)
- 通过后领取 DigitalOcean $200 额度，可免费用很久

### 2. 创建 Droplet
1. 登录 [DigitalOcean](https://cloud.digitalocean.com/)
2. **Create** → **Droplets**
3. 选择：
   - **Image**: Ubuntu 22.04 LTS
   - **Region**: **Sydney**（澳洲用户延迟最低）
   - **Plan**: Basic $6/mo（1 GB RAM，足够开发/小规模）
   - **Authentication**: SSH Key（推荐）或 Password
4. 创建后记下 **IP 地址**

### 3. 开放防火墙端口
DigitalOcean 默认开放 22。若使用 8080，需在控制台：
- **Networking** → **Firewalls** → Create → 添加 **8080** (HTTP)
- 或改用 80 端口（见下方说明）

---

## 二、首次连接与安装环境

### 1. SSH 登录
```bash
ssh root@你的Droplet的IP
```

### 2. 一键安装依赖（复制整段执行）
```bash
# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt update && sudo apt install -y nodejs python3 python3-pip python3-venv nginx mysql-server

# MySQL 启动并安全设置
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql_secure_installation  # 按提示设置 root 密码
```

### 3. 创建数据库
```bash
sudo mysql -u root -p
```
```sql
CREATE DATABASE sign_inspire CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lingxi'@'localhost' IDENTIFIED BY '你的强密码';
GRANT ALL ON sign_inspire.* TO 'lingxi'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 三、部署灵犀

### 1. 克隆项目
```bash
cd /tmp
git clone https://github.com/fangyikun/advertisement-opitimization.git lingxi-src
cd lingxi-src
```
（若仓库为私有，需配置 deploy key 或 token）

### 2. 配置 .env
```bash
cp deploy/env.example sign-inspire-backend/.env
nano sign-inspire-backend/.env
```
填写：
```
DB_PASSWORD=刚才设置的lingxi用户密码
GOOGLE_PLACES_API_KEY=你的Google Places API Key   # 澳洲可直接用
OPENAI_API_KEY=你的OpenAI Key
# AMAP_API_KEY 可留空，澳洲不需要高德
```

### 3. 执行部署
```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

### 4. 访问
- 前端：`http://你的IP:8080/`
- 若 8080 被墙，改 Nginx 为 80：
  ```bash
  sudo sed -i 's/listen 8080/listen 80/' /etc/nginx/conf.d/lingxi.conf
  sudo nginx -t && sudo systemctl reload nginx
  ```
  然后访问 `http://你的IP/`

---

## 四、常用命令

| 操作       | 命令                                   |
|------------|----------------------------------------|
| 查看日志   | `sudo journalctl -u lingxi-backend -f` |
| 重启后端   | `sudo systemctl restart lingxi-backend` |
| 重新部署   | 拉代码后执行 `./deploy/deploy.sh`      |

---

## 五、与阿里云部署的区别

| 项目           | DigitalOcean（澳洲）     | 阿里云（国内）        |
|----------------|--------------------------|-------------------------|
| Google Places  | ✅ 正常使用              | ❌ 需用高德替代         |
| 字体/CDN       | ✅ 无限制                | 需换国内镜像            |
| 天气 API       | ✅ 稳定                  | 可能超时，需缓存        |
| 推荐配置       | GOOGLE_PLACES_API_KEY    | AMAP_API_KEY            |
