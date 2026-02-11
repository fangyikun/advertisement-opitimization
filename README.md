# Sign Inspire - 智能广告调度系统

一个基于规则引擎的智能数字标牌广告调度系统，通过 AI 解析自然语言规则，结合实时天气数据，自动切换播放内容。

## 🌟 特性

- 🤖 **AI 驱动**：使用 Google Gemini 将自然语言转换为结构化规则
- 🌤️ **实时天气**：集成 Open-Meteo API，根据天气自动切换广告
- 📊 **可视化 Dashboard**：直观的规则管理和实时状态监控
- 🎬 **Player 页面**：全屏播放界面，支持淡入淡出动画
- 🔄 **自动调度**：后台定时检查规则，自动触发内容切换

## 📁 项目结构

```
advertisement Optimization/
├── sign-inspire-backend/     # FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 路由
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # Pydantic 模式
│   │   ├── services/        # 业务逻辑
│   │   └── main.py          # 应用入口
│   └── requirements.txt     # Python 依赖
│
└── sign-inspire-frontend/    # React + TypeScript 前端
    ├── src/
    │   ├── components/      # React 组件
    │   ├── pages/           # 页面组件
    │   └── App.tsx          # 应用入口
    └── package.json         # Node.js 依赖
```

## 🚀 快速开始

### 后端设置

1. **安装依赖**
```bash
cd sign-inspire-backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
# 创建 .env 文件
GOOGLE_API_KEY=your_gemini_api_key_here
```

3. **启动后端服务**
```bash
cd sign-inspire-backend
fastapi dev app/main.py
```

后端将在 `http://127.0.0.1:8000` 启动

### 前端设置

1. **安装依赖**
```bash
cd sign-inspire-frontend
npm install
```

2. **启动开发服务器**
```bash
npm run dev
```

前端将在 `http://localhost:5173` 启动

## 📖 使用指南

### 创建规则

1. 在 Dashboard 页面输入自然语言，例如：
   - "如果当前多云，请播放咖啡广告"
   - "下雨时显示热饮广告"

2. 点击"生成规则"，AI 会自动解析并生成结构化规则

3. 确认规则后点击"确认并生效"，规则将保存并立即生效

### 查看播放内容

访问 `/player` 页面查看当前播放的内容。系统会根据天气自动切换广告。

## 🏗️ 架构说明

### 后端架构

- **FastAPI**：现代化的 Python Web 框架
- **LangChain + Gemini**：自然语言处理
- **Open-Meteo API**：免费天气数据服务
- **内存数据库**：使用 `MOCK_DB` 临时存储规则（生产环境建议使用真实数据库）

### 核心流程

1. **规则创建**：用户输入自然语言 → LLM 解析 → 保存到数据库
2. **规则执行**：定时任务获取天气 → 匹配规则条件 → 更新播放列表
3. **内容展示**：前端轮询获取当前播放内容 → 显示对应广告

### 数据流

```
用户输入自然语言
    ↓
POST /rules:parse → Gemini 解析
    ↓
POST /rules → 保存到 MOCK_DB
    ↓
后台定时任务（每60秒）
    ↓
获取天气 → 匹配规则 → 更新 CURRENT_PLAYLIST
    ↓
前端 GET /current-content → 显示广告
```

## 🔧 API 文档

启动后端后，访问 `http://127.0.0.1:8000/docs` 查看完整的 API 文档。

### 主要端点

- `POST /api/v1/stores/{store_id}/rules:parse` - 解析自然语言规则
- `POST /api/v1/stores/{store_id}/rules` - 创建规则
- `GET /api/v1/stores/{store_id}/rules` - 获取规则列表
- `GET /api/v1/weather` - 获取当前天气
- `GET /api/v1/stores/{store_id}/current-content` - 获取当前播放内容
- `POST /api/v1/stores/{store_id}/check-rules` - 手动触发规则检查

## 🛠️ 技术栈

### 后端
- FastAPI
- LangChain
- Google Gemini 2.5 Flash
- httpx (异步 HTTP 客户端)
- Pydantic (数据验证)

### 前端
- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios
- Lucide React (图标)

## 📝 开发计划

- [ ] 数据库持久化（SQLite/PostgreSQL）
- [ ] 多门店支持
- [ ] WebSocket 实时推送
- [ ] 规则触发历史记录
- [ ] 更多条件类型（时间、节假日等）
- [ ] 用户认证和权限管理

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
