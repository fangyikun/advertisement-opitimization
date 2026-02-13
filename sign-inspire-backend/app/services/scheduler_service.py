# APScheduler 逻辑 (执行官)
import httpx
from datetime import datetime
from typing import Optional
import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.rule_model import Rule

# 阿德莱德的经纬度 (Adelaide Uni)
ADELAIDE_LAT = -34.9285
ADELAIDE_LON = 138.6007

# 全局天气上下文，用于与前端共享（含 temp_c、region 供全球规则）
CURRENT_CONTEXT = {"weather": "unknown", "temp_c": None, "region": "western", "updated_at": None}

# 当前播放列表，存储最新的触发结果（兼容单门店）
CURRENT_PLAYLIST = "default"
# 按门店存储：{store_id: target_id}，支持多门店
CURRENT_PLAYLIST_BY_STORE = {}

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

# 天气 + 温度上下文（全球规则用）
WeatherContext = dict  # {"weather": str, "temp_c": float, "is_day": int}

# 天气缓存：国内访问 Open-Meteo 可能较慢，缓存 5 分钟减少重复请求
_WEATHER_CACHE: dict = {}
_CACHE_TTL = 300  # 5 分钟


async def get_real_weather(lat: Optional[float] = None, lon: Optional[float] = None):
    """
    调用 Open-Meteo 获取真实天气，支持任意经纬度
    返回天气字符串 (向后兼容)
    文档: https://open-meteo.com/en/docs
    """
    ctx = await get_weather_context(lat, lon)
    return ctx.get("weather", "sunny")


# 星期映射：mon=0..sun=6（与 datetime.weekday() 一致，0=周一）
_DAY_ALIAS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


async def get_weather_context(lat: Optional[float] = None, lon: Optional[float] = None, timezone: str = "Australia/Adelaide") -> WeatherContext:
    """
    获取完整天气上下文：weather + temp_c + is_day + hour + weekday
    用于 Brunch、Barbie、Sunday Sesh 等时间场景规则
    缓存 5 分钟，减少国内访问 Open-Meteo 超时影响
    """
    _lat = lat if lat is not None else ADELAIDE_LAT
    _lon = lon if lon is not None else ADELAIDE_LON
    cache_key = (round(_lat, 2), round(_lon, 2))
    now_ts = datetime.now().timestamp()
    if cache_key in _WEATHER_CACHE:
        cached = _WEATHER_CACHE[cache_key]
        if now_ts - cached.get("_ts", 0) < _CACHE_TTL:
            out = {k: v for k, v in cached.items() if k != "_ts"}
            return out
    try:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(timezone))
        except ImportError:
            now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Mon, 6=Sun

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": _lat, "longitude": _lon,
            "current": "weather_code,is_day,temperature_2m",
        }
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if resp.status_code != 200 or "current" not in data:
            raise ValueError(f"Open-Meteo 返回异常: status={resp.status_code}, keys={list(data.keys())[:5] if isinstance(data, dict) else 'n/a'}")

        code = data["current"]["weather_code"]
        is_day = data["current"].get("is_day", 1)
        temp_c = float(data["current"].get("temperature_2m", 20))

        if code in [0, 1]:
            weather = "sunny"
        elif code in [2, 3]:
            weather = "cloudy"
        elif code in [45, 48]:
            weather = "fog"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            weather = "rain"
        elif code in [71, 73, 75, 85, 86]:
            weather = "snow"
        elif code in [95, 96, 99]:
            weather = "storm"
        else:
            weather = "cloudy"

        # 季节：南半球(lat<0)与北半球相反
        month = now.month
        if _lat is not None and _lat < 0:  # 南半球（澳洲等）
            season = "summer" if month in (12, 1, 2) else "autumn" if month in (3, 4, 5) else "winter" if month in (6, 7, 8) else "spring"
        else:  # 北半球
            season = "spring" if month in (3, 4, 5) else "summer" if month in (6, 7, 8) else "autumn" if month in (9, 10, 11) else "winter"
        result = {"weather": weather, "temp_c": temp_c, "is_day": is_day, "hour": hour, "weekday": weekday, "season": season}
        _WEATHER_CACHE[cache_key] = {**result, "_ts": now_ts}
        return result

    except Exception as e:
        print(f"⚠️ 天气 API 不可用，使用本地估算: {type(e).__name__}")
        now = datetime.now()
        month = now.month
        season = "summer" if month in (6, 7, 8) else "winter" if month in (12, 1, 2) else "spring" if month in (3, 4, 5) else "autumn"
        fallback = {"weather": "sunny", "temp_c": 20.0, "is_day": 1, "hour": now.hour, "weekday": now.weekday(), "season": season}
        _WEATHER_CACHE[cache_key] = {**fallback, "_ts": now_ts}
        return fallback

# 天气值中英文映射（内置 + 动态词汇表会合并）
WEATHER_MAP = {
    "sunny": ["sunny", "晴天", "晴"],
    "cloudy": ["cloudy", "多云", "阴"],
    "rain": ["rain", "雨天", "雨", "下雨"],
    "snow": ["snow", "雪天", "雪", "下雪"],
    "storm": ["storm", "雷暴", "雷雨"],
    "fog": ["fog", "雾天", "雾", "大雾"],
}

def normalize_weather_value(value: str) -> set:
    """
    将天气值（可能是中文或英文）标准化为英文值集合
    支持动态词汇表中的新词
    """
    from app.services.vocabulary_service import get_weather_mappings
    value_lower = value.lower().strip()
    result = set()

    # 使用动态词汇表（含内置 + DB 中客户添加的新词）
    vocab = get_weather_mappings()
    if value_lower in vocab:
        result.add(vocab[value_lower])
        return result
    # 反向查找：通过关键词匹配
    for kw, eng_value in vocab.items():
        if kw.lower() == value_lower or value_lower == eng_value:
            result.add(eng_value)
            return result
    # 回退：使用内置 WEATHER_MAP 的别名
    for eng_value, aliases in WEATHER_MAP.items():
        if value_lower == eng_value:
            result.add(eng_value)
            return result
        for alias in aliases:
            if value_lower == alias.lower():
                result.add(eng_value)
                return result
    return result

async def check_rules_job():
    """
    检查规则并触发匹配的规则（按门店维度）
    """
    global CURRENT_PLAYLIST, CURRENT_PLAYLIST_BY_STORE

    _ensure_lock()

    async with _check_rules_lock:
        from app.services.matching_engine import run_matching_for_all_stores

        by_store = await run_matching_for_all_stores(
            None, lat=ADELAIDE_LAT, lon=ADELAIDE_LON, city="Adelaide", country_code="AU"
        )
        CURRENT_PLAYLIST_BY_STORE = dict(by_store)
        CURRENT_PLAYLIST = by_store.get("store_001", "default")

        ctx = await get_weather_context(timezone="Australia/Adelaide")
        CURRENT_CONTEXT["weather"] = ctx.get("weather", "unknown")
        CURRENT_CONTEXT["temp_c"] = ctx.get("temp_c")
        CURRENT_CONTEXT["hour"] = ctx.get("hour")
        CURRENT_CONTEXT["weekday"] = ctx.get("weekday")
        CURRENT_CONTEXT["region"] = "western"
        CURRENT_CONTEXT["updated_at"] = datetime.now().isoformat()

        print(f"[Tick] Adelaide Weather: {CURRENT_CONTEXT['weather']} {CURRENT_CONTEXT.get('temp_c')}°C")
        print(f"📋 匹配结果: {by_store}")
        print(f"🔍 [Final] check_rules_job 完成, store_001 -> {CURRENT_PLAYLIST}")
