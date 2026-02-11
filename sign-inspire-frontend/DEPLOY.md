# 灵犀前端部署指南

## 方式一：GitHub Pages（自动）

推送到 `main` 分支后，GitHub Actions 会自动构建并部署。

### 1. 开启 GitHub Pages

1. 打开仓库：https://github.com/fangyikun/advertisement-opitimization
2. 进入 **Settings** → **Pages**
3. **Source** 选择：**GitHub Actions**

### 2. （可选）配置后端 API 地址

若后端已上线，在仓库 **Settings** → **Secrets and variables** → **Actions** 中新增：

| 名称 | 值 |
|------|-----|
| `VITE_API_URL` | 如 `https://你的后端域名/api/v1` |

不配置则默认使用 `http://127.0.0.1:8000/api/v1`，仅本地调试有效。

### 3. 访问地址

部署完成后访问：

```
https://fangyikun.github.io/advertisement-opitimization/
```

---

## 方式二：本地手动部署

```bash
cd sign-inspire-frontend

# 设置 base 和 API（按需修改）
# Windows PowerShell:
$env:VITE_BASE = "/advertisement-opitimization/"
$env:VITE_API_URL = "https://你的后端/api/v1"  # 可选

npm run build
npx gh-pages -d dist
```

---

## 注意事项

- **CORS**：若后端在别的域名，需在后端配置允许前端域名的跨域请求
- **base 路径**：仓库名带连字符，访问路径为 `/advertisement-opitimization/`
