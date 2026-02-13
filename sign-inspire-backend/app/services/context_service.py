"""
环境感知服务：根据 location_id 获取天气、温度、时间等环境上下文
使用 Open-Meteo API（免费，无需 Key）或 OpenWeatherMap（可选）
"""
from datetime import datetime
from typing import Optional

from app.schemas.decide import EnvironmentContext


# 天气代码 -> 标准条件名（与 EnvironmentContext 兼容）
WEATHER_TO_CONDITION = {
    "sunny": "Sunny",
    "cloudy": "Cloudy",
    "rain": "Rainy",
    "snow": "Snowy",
    "storm": "Stormy",
    "fog": "Foggy",
}


async def get_current_context(location_id: str) -> Optional[EnvironmentContext]:
    """
    根据 location_id 获取当前环境上下文。
    location_id 支持：
    - store_001 等门店 ID：从数据库/预设获取经纬度
    - Adelaide、Sydney 等城市名：通过地理编码获取经纬度

    调用 Open-Meteo 获取实时天气、温度。
    返回标准化的 EnvironmentContext 对象。
    """
    lat, lon, location_name, timezone = _resolve_location(location_id)
    if lat is None or lon is None:
        return None

    # 获取天气上下文（复用 scheduler_service 的 Open-Meteo 逻辑）
    wx_ctx = await _get_weather_context(lat, lon, timezone)
    if not wx_ctx:
        return None

    weather_key = wx_ctx.get("weather", "sunny")
    weather_condition = WEATHER_TO_CONDITION.get(weather_key, weather_key.capitalize())
    temp = float(wx_ctx.get("temp_c", 20))

    try:
        from zoneinfo import ZoneInfo
        local_time = datetime.now(ZoneInfo(timezone))
    except ImportError:
        local_time = datetime.now()

    return EnvironmentContext(
        location=location_name or location_id,
        weather_condition=weather_condition,
        temperature=temp,
        local_time=local_time,
    )


def _resolve_location(location_id: str) -> tuple:
    """
    解析 location_id -> (lat, lon, location_name, timezone)
    返回 (None, None, None, "Australia/Adelaide") 表示解析失败
    """
    if not location_id or not location_id.strip():
        return (None, None, None, "Australia/Adelaide")

    lid = location_id.strip()

    # 1. 门店 ID：store_001 等，从数据库或预设获取
    if lid.startswith("store_"):
        store_info = _get_store_coords(lid)
        if store_info:
            return store_info

    # 2. 城市名：通过地理编码
    from app.services.geocoding_service import geocode_city_sync
    geo = geocode_city_sync(lid)
    if geo:
        lat = geo.get("lat")
        lon = geo.get("lon")
        city = geo.get("city", lid)
        cc = geo.get("country_code", "AU")
        tz = _country_to_timezone(cc)
        return (lat, lon, city, tz)

    return (None, None, None, "Australia/Adelaide")


def _get_store_coords(store_id: str) -> Optional[tuple]:
    """从数据库或预设获取门店经纬度"""
    # 预设门店（与 database.py 默认一致）
    PRESETS = {
        "store_001": (-34.9285, 138.6007, "Adelaide", "Australia/Adelaide"),
    }

    if store_id in PRESETS:
        return PRESETS[store_id]

    # 尝试从数据库查
    try:
        from app.database import USE_DATABASE, SessionLocal
        from app.models.store_model import Store
        if USE_DATABASE and SessionLocal:
            db = SessionLocal()
            try:
                store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
                if store:
                    tz = store.timezone or "Australia/Adelaide"
                    return (store.latitude, store.longitude, store.city or store.name, tz)
            finally:
                db.close()
    except Exception:
        pass

    return None


def _country_to_timezone(country_code: str) -> str:
    """国家代码 -> 时区"""
    tz_map = {
        "AU": "Australia/Adelaide", "CN": "Asia/Shanghai", "JP": "Asia/Tokyo",
        "GB": "Europe/London", "US": "America/New_York", "SG": "Asia/Singapore",
        "HK": "Asia/Hong_Kong", "TW": "Asia/Taipei",
    }
    return tz_map.get(country_code or "", "Australia/Adelaide")


async def _get_weather_context(lat: float, lon: float, timezone: str = "Australia/Adelaide") -> Optional[dict]:
    """调用 Open-Meteo 获取天气"""
    from app.services.scheduler_service import get_weather_context
    return await get_weather_context(lat, lon, timezone=timezone)
