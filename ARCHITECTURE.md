# Sign Inspire 架构设计

> 目标：Adelaide 试点 → 匹配引擎改造 → 未来 App 迁移

---

## 一、整体架构

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              前端 (现有 + 未来 App)                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ 管理后台 (Web)   │  │ 播放器 (Web/App) │  │ 商户 App (未来)   │              │
│  │ Dashboard       │  │ Player          │  │ React Native     │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│           └────────────────────┼────────────────────┘                        │
│                                │ 统一 API 客户端                               │
└────────────────────────────────┼──────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI 后端                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │ 规则 API    │ │ 门店 API    │ │ 匹配引擎    │ │ 媒体 API    │             │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────────────┘             │
│         │               │               │                                     │
│         └───────────────┼───────────────┘                                     │
│                        │                                                      │
│  ┌─────────────────────┼─────────────────────┐                              │
│  │          MySQL: rules, stores, vocabulary, media_cache                    │
│  └─────────────────────┴─────────────────────┘                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据模型设计

### 2.1 新增：门店表 `stores`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | varchar(36) | 主键 |
| name | varchar(100) | 门店名称 |
| city | varchar(50) | 城市（Adelaide 试点固定） |
| latitude | float | 纬度 |
| longitude | float | 经度 |
| sign_id | varchar(50) | 屏幕/标牌唯一标识（Player 轮询用） |
| opening_hours | json | 营业时间，如 `{"mon":"09:00-17:00",...}` |
| timezone | varchar(50) | 时区，默认 Australia/Adelaide |
| is_active | boolean | 是否启用 |
| created_at | datetime | |
| updated_at | datetime | |

### 2.2 现有：规则表 `rules` 扩展

| 现有字段 | 扩展说明 |
|----------|----------|
| store_id | 保持，关联门店；可支持 `*` 表示全部门店 |
| conditions | 增加 `city` 类型：`{"type":"city","operator":"==","value":"Adelaide"}` |
| action.target_id | 保持不变，播放内容 ID |

### 2.3 匹配引擎输入输出

**输入**：`{ city, weather, store_id, current_time }`  
**输出**：`{ target_id, priority }`（当前应播放的广告）

---

## 三、后端目录结构（建议）

```
sign-inspire-backend/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── rules.py      # 规则 CRUD（现有）
│   │   ├── stores.py     # 门店 CRUD（新增）
│   │   ├── matching.py   # 匹配引擎 API（新增）
│   │   └── media.py      # 媒体/图片（可独立）
│   ├── models/
│   │   ├── rule_model.py
│   │   ├── store_model.py    # 新增
│   │   ├── vocabulary_model.py
│   │   └── media_model.py
│   ├── services/
│   │   ├── matching_engine.py  # 核心：天气+城市+营业→广告（新增/改造）
│   │   ├── store_service.py    # 营业状态判断（新增）
│   │   ├── scheduler_service.py # 改造：按门店维度执行
│   │   ├── vocabulary_service.py
│   │   └── media_service.py
│   └── schemas/
│       ├── rule.py
│       ├── store.py       # 新增
│       └── matching.py    # 新增
```

---

## 四、核心 API 设计

### 4.1 门店（新增）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/cities` | 城市列表（Adelaide 试点仅 1 个） |
| GET | `/api/v1/cities/{city}/stores` | 某城市门店列表 |
| POST | `/api/v1/stores` | 创建门店 |
| GET | `/api/v1/stores/{store_id}` | 门店详情 |
| PATCH | `/api/v1/stores/{store_id}` | 更新门店 |
| DELETE | `/api/v1/stores/{store_id}` | 删除门店 |

### 4.2 匹配引擎（新增 / 改造）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/stores/{store_id}/current-content` | **改造**：按 store_id 返回该门店当前应播内容 |
| GET | `/api/v1/signs/{sign_id}/current-content` | **新增**：按屏幕 ID 获取（App/Player 用） |

**响应**：
```json
{
  "content": "sunscreen_ad",
  "city": "Adelaide",
  "weather": "sunny",
  "store_id": "store_001",
  "matched_rule_id": "xxx"
}
```

### 4.3 规则（现有，微调）

- 规则可关联 `store_id` 或 `city`
- 匹配时：先筛城市 → 再筛天气 → 再筛门店是否营业 → 按优先级取第一条

### 4.4 App 专用（未来）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 商户登录（JWT） |
| GET | `/api/v1/me/stores` | 当前商户门店列表 |
| GET | `/api/v1/me/stores/{id}/stats` | 播放统计 |

---

## 五、匹配引擎逻辑（核心改造）

```python
# 伪代码
def match_content(store_id: str, city: str, weather: str, current_time: datetime) -> str:
    store = get_store(store_id)
    if not store or not store.is_active:
        return "default"
    if not is_store_open(store, current_time):
        return "default"  # 或 "closed" 专用画面

    rules = get_rules_for_city(city)  # 可扩展 store_id 过滤
    for rule in sorted(rules, key=lambda r: -r.priority):
        if conditions_match(rule.conditions, weather=weather, city=city):
            return rule.action.target_id
    return "default"
```

**改造点**：
1. 从「全局单 playlist」改为「按 store_id 独立匹配」
2. 增加 `is_store_open()` 判断
3. `conditions` 支持 `city` 类型
4. 调度器：遍历所有 active 门店，分别执行 `match_content`，写入 `CURRENT_PLAYLIST_BY_STORE[store_id]`

---

## 六、前端设计（App 就绪）

### 6.1 目录结构建议

```
sign-inspire-frontend/
├── src/
│   ├── api/              # 统一 API 层（App 可复用）
│   │   ├── client.ts     # axios 实例、baseURL 配置
│   │   ├── rules.ts
│   │   ├── stores.ts     # 新增
│   │   └── content.ts    # current-content 等（新增）
│   ├── hooks/            # 业务逻辑（App 可复用）
│   │   ├── useRules.ts
│   │   ├── useStores.ts  # 新增
│   │   └── useCurrentContent.ts
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Stores.tsx    # 门店管理（新增）
│   │   └── Player.tsx
│   └── components/
```

### 6.2 配置抽离（App 迁移关键）

```typescript
// src/config.ts
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
  storeId: import.meta.env.VITE_STORE_ID || 'store_001',
  signId: import.meta.env.VITE_SIGN_ID || 'default',  // Player 用
};
```

- Web：`.env` 配置
- App：编译时注入或运行时从云端拉取

### 6.3 Player 改造

- 入参从「固定 store_001」改为「sign_id 或 store_id」
- URL：`/api/v1/signs/{sign_id}/current-content` 或 `/stores/{store_id}/current-content`
- 未来 App：同一套组件，传入不同 sign_id

---

## 七、实施顺序

| 阶段 | 任务 | 产出 |
|------|------|------|
| 1 | 新增 `stores` 表、Store 模型、stores API | 门店 CRUD |
| 2 | 改造 matching：`match_content(store_id, ...)` | 按门店匹配 |
| 3 | 改造 `current-content`：支持 store_id/sign_id | Player 可指定门店 |
| 4 | 新增 `store_service.is_open()` | 营业时间过滤 |
| 5 | 规则 conditions 支持 city | 按城市投放 |
| 6 | 前端 Stores 页面、Dashboard 支持多门店 | 管理多店 |
| 7 | 抽离 api、hooks、config | App 迁移就绪 |

---

## 八、已实现（2025-02）

- ✅ `stores` 表 + Store 模型 + CRUD API
- ✅ 匹配引擎 `matching_engine.py`：按 store_id 匹配
- ✅ `CURRENT_PLAYLIST_BY_STORE`：多门店结果
- ✅ `current-content` 支持 store_id、`/signs/{sign_id}/current-content` 支持 sign_id
- ✅ 前端门店管理页、Player 支持 `?sign=xxx`
- ✅ 配置抽离 `config.ts`

## 九、Adelaide 试点简化

- `city` 固定为 `"Adelaide"`，暂不做多城市 API
- 可先不做 `opening_hours`，所有门店默认营业
- 重点：**按 store_id 的匹配引擎 + current-content 改造**

完成以上设计后，后续扩展多城市、营业时间、App 时改动集中且清晰。

## 十、门店推荐（全球支持）

- **支持全球任意城市**：Adelaide、Sydney、London、Tokyo、Paris 等
- 地理编码：OpenStreetMap Nominatim（免费）将城市名转为经纬度
- 天气：Open-Meteo 按城市经纬度获取实时天气
- 门店数据：**Google Places API**（含地址、图片）优先，403 时回退 Legacy API，无 Key 时回退 Overpass
- API：`GET /recommendations?limit=10&city=Sydney`
