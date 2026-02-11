# 全球天气+饮食规则设计

基于 Gemini 建议，支持**温度阈值**、**文化圈层**差异化推荐，适配全球用户。

## 一、核心变量

| 变量 | 来源 | 说明 |
|------|------|------|
| `weather` | Open-Meteo | sunny, cloudy, rain, snow, storm, fog |
| `temp_c` | Open-Meteo | 当前气温（摄氏度） |
| `region` | country_code → 映射 | western, east_asia, tropical, uk |
| `city` |  geocode / 用户输入 | 城市名 |

## 二、文化圈层 (Region_Cluster)

- **western**: 北美、西欧、澳洲 — 奶酪/面包/肉类
- **east_asia**: 中日韩 — 米饭/面条/热汤
- **tropical**: 东南亚、南亚 — 香料/酸辣
- **uk**: 英伦 — Tea & Buns

国家代码 → 文化圈见 `app/services/region_service.py`。

## 三、规则条件类型

| type | value 示例 | 说明 |
|------|------------|------|
| weather | "rain", "sunny" | 天气状态 |
| temp | "0,15", ">30", "<=10" | 温度范围（闭区间或阈值） |
| region | "east_asia", "western" | 文化圈层 |
| city | "Adelaide" | 城市 |

## 四、API 创建规则示例

```json
{
  "name": "东京酷热推冰沙",
  "priority": 2,
  "conditions": [
    {"type": "weather", "operator": "==", "value": "晴"},
    {"type": "temp", "operator": "==", "value": ">30"},
    {"type": "region", "operator": "==", "value": "east_asia"}
  ],
  "action": {"type": "switch_playlist", "target_id": "bingxigua_ad"}
}
```

```json
{
  "name": "伦敦下雨推炸鱼薯条",
  "priority": 1,
  "conditions": [
    {"type": "weather", "operator": "==", "value": "rain"},
    {"type": "region", "operator": "==", "value": "uk"}
  ],
  "action": {"type": "switch_playlist", "target_id": "hot_drink_ad"}
}
```

## 五、温度 value 格式

- `"0,15"` — 闭区间 0°C ≤ temp ≤ 15°C
- `">30"` — temp > 30°C
- `"<=10"` — temp ≤ 10°C
- `">=28"` — temp ≥ 28°C

## 六、推荐场景对应（参考 Gemini）

| 场景 | weather | temp | region | 推荐思路 |
|------|----------|------|--------|----------|
| 酷热 | sunny | >30 | east_asia | 冷面、刨冰、绿豆汤 |
| 酷热 | sunny | >30 | western | 沙拉、冰沙、冰咖啡 |
| 酷热 | sunny | >30 | tropical | 酸辣汤、椰子水 |
| 湿冷 | rain | <10 | east_asia | 拉面、火锅、咖喱 |
| 湿冷 | rain | <10 | western | 披萨、番茄汤 |
| 下雪 | snow | <5 | east_asia | 火锅、关东煮 |
| 下雪 | snow | <5 | western | 炖菜、热巧克力 |

## 七、实现文件

- `scheduler_service.py`: `get_weather_context()` 返回 weather + temp_c
- `region_service.py`: 国家 → 文化圈映射
- `geocoding_service.py`: 逆地理/城市解析返回 country_code
- `matching_engine.py`: `_conditions_match()` 支持 temp、region
- `recommendation_service.py`: 传递 lat, lon, country_code 做规则匹配
