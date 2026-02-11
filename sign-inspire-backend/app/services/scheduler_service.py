# APScheduler 逻辑 (执行官)
import httpx
from datetime import datetime
import asyncio
from app.models.rule_storage import MOCK_DB

# 阿德莱德的经纬度 (Adelaide Uni)
ADELAIDE_LAT = -34.9285
ADELAIDE_LON = 138.6007

# 全局天气上下文，用于与前端共享
CURRENT_CONTEXT = {"weather": "unknown", "updated_at": None}

# 当前播放列表，存储最新的触发结果
CURRENT_PLAYLIST = "default"

# 锁，防止并发执行 check_rules_job
_check_rules_lock = None

def _ensure_lock():
    """确保锁已初始化"""
    global _check_rules_lock
    if _check_rules_lock is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        _check_rules_lock = asyncio.Lock()

async def get_real_weather():
    """
    调用 Open-Meteo 获取真实天气
    文档: https://open-meteo.com/en/docs
    """
    try:
        # 1. 构造 URL (请求当前天气代码)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={ADELAIDE_LAT}&longitude={ADELAIDE_LON}&current=weather_code,is_day"
        
        # 2. 发送请求 (不需要 API Key!)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            data = resp.json()
            
        # 3. 解析 WMO Weather Code
        # Open-Meteo 返回的是数字代码，我们需要转换成字符串
        # 参考代码表: https://open-meteo.com/en/docs
        code = data['current']['weather_code']
        is_day = data['current']['is_day'] # 1=白天, 0=晚上

        # --- 简单的天气映射逻辑 ---
        if code in [0, 1]:
            return "sunny"
        elif code in [2, 3]:
            return "cloudy"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: # 各种雨
            return "rain"
        elif code in [71, 73, 75, 85, 86]: # 雪
            return "snow"
        elif code in [95, 96, 99]: # 雷暴
            return "storm"
        else:
            return "cloudy" # 默认

    except Exception as e:
        print(f"❌ 获取天气失败: {e}")
        return "sunny" # 降级方案：获取失败就默认是大晴天

# 天气值中英文映射
WEATHER_MAP = {
    "sunny": ["sunny", "晴天", "晴"],
    "cloudy": ["cloudy", "多云", "阴"],
    "rain": ["rain", "雨天", "雨", "下雨"],
    "snow": ["snow", "雪天", "雪", "下雪"],
    "storm": ["storm", "雷暴", "雷雨"]
}

def normalize_weather_value(value: str) -> set:
    """
    将天气值（可能是中文或英文）标准化为英文值集合
    例如："多云" -> {"cloudy"}, "cloudy" -> {"cloudy"}
    """
    value_lower = value.lower().strip()
    result = set()
    
    # 检查是否直接匹配英文值
    for eng_value, aliases in WEATHER_MAP.items():
        if value_lower == eng_value:
            result.add(eng_value)
        # 检查是否在别名列表中（包括中文）
        for alias in aliases:
            if value_lower == alias.lower():
                result.add(eng_value)
                break
    
    # 如果没有匹配到，返回空集合
    return result

async def check_rules_job():
    """
    检查规则并触发匹配的规则
    """
    global CURRENT_PLAYLIST
    
    # 确保锁已初始化
    _ensure_lock()
    
    # 使用锁防止并发执行
    async with _check_rules_lock:
        # 1. 获取真实天气
        current_weather = await get_real_weather()
        
        # 更新全局天气上下文
        CURRENT_CONTEXT["weather"] = current_weather
        CURRENT_CONTEXT["updated_at"] = datetime.now().isoformat()
        
        # 获取当前时间并格式化
        current_time = datetime.now().strftime("%H:%M")
        
        # 打印当前时间和真实天气
        print(f"[Tick] {current_time} Weather: {current_weather}")
        print(f"🌍 [Real World] Adelaide Weather: {current_weather}")
        
        # 2. 遍历 MOCK_DB 里的所有规则，按优先级排序后选择匹配的规则
        # 按优先级排序（优先级数字越大，优先级越高）
        sorted_rules = sorted(MOCK_DB, key=lambda r: r.get("priority", 1), reverse=True)
        
        # 将当前天气标准化（也通过 normalize_weather_value 处理，确保一致性）
        current_weather_normalized = normalize_weather_value(current_weather)
        if not current_weather_normalized:
            # 如果标准化失败，使用原始值
            current_weather_normalized = {current_weather}
        print(f"🌤️  当前天气: '{current_weather}' -> 标准化后: {current_weather_normalized}")
        
        triggered = False
        print(f"📋 检查 {len(sorted_rules)} 条规则...")
        
        for rule in sorted_rules:
            rule_name = rule.get("name", "未知规则")
            conditions = rule.get("conditions", [])
            action = rule.get("action", {})
            
            print(f"  🔍 检查规则: {rule_name}")
            
            # 检查规则的 conditions 是否匹配当前天气
            matched = False
            for condition in conditions:
                # 如果条件类型是天气，且值匹配当前天气
                if condition.get("type") == "weather":
                    condition_value = condition.get("value", "")
                    operator = condition.get("operator", "==")
                    
                    print(f"    ⚙️  条件: weather {operator} '{condition_value}'")
                    
                    # 标准化条件值（支持中英文）
                    condition_normalized = normalize_weather_value(condition_value)
                    print(f"    📊 条件标准化后: {condition_normalized}")
                    print(f"    📊 当前天气标准化: {current_weather_normalized}")
                    
                    # 根据操作符进行匹配判断
                    if operator == "==":
                        # 检查是否有交集
                        intersection = current_weather_normalized & condition_normalized
                        print(f"    🔗 交集: {intersection}")
                        if intersection:
                            matched = True
                            print(f"    ✅ 匹配成功！")
                            break
                        else:
                            print(f"    ❌ 不匹配")
                    elif operator == "in":
                        # 如果 value 是逗号分隔的列表，检查当前天气是否在其中
                        values = [v.strip() for v in condition_value.split(",")]
                        for v in values:
                            v_normalized = normalize_weather_value(v)
                            if current_weather_normalized & v_normalized:
                                matched = True
                                break
                        if matched:
                            break
            
            # 如果匹配，触发规则（选择优先级最高的匹配规则）
            if matched:
                target_id = action.get("target_id", "未知播放列表")
                print(f"🚀 [Action] 触发规则 '{rule_name}' -> 切换播放列表为 '{target_id}'")
                # 存储到全局变量
                CURRENT_PLAYLIST = target_id
                print(f"✅ [State] CURRENT_PLAYLIST 已更新为: '{CURRENT_PLAYLIST}'")
                triggered = True
                break  # 找到优先级最高的匹配规则就停止
            else:
                print(f"  ⏭️  规则 '{rule_name}' 不匹配，跳过")
        
        # 如果没有规则匹配，设置为默认值
        if not triggered:
            print("💤 无规则触发，CURRENT_PLAYLIST 保持为: 'default'")
            CURRENT_PLAYLIST = "default"
            print(f"✅ [State] CURRENT_PLAYLIST = '{CURRENT_PLAYLIST}'")
        
        # 函数结束前再次确认值
        print(f"🔍 [Final] check_rules_job 执行完成，CURRENT_PLAYLIST = '{CURRENT_PLAYLIST}'")
