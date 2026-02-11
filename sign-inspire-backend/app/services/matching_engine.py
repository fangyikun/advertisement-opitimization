"""
匹配引擎：天气 + 城市 + 门店营业状态 -> 应播放的广告
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.services.scheduler_service import normalize_weather_value
from app.services.store_service import is_store_open


def _parse_temp_range(value: str) -> Optional[tuple]:
    """解析温度范围: '0,15' -> (0,15) 闭区间; '>30' -> (30,999); '<=10' -> (-999,10)"""
    if not value or not str(value).strip():
        return None
    s = str(value).strip().replace(" ", "")
    if "," in s:
        parts = s.split(",")
        if len(parts) == 2:
            try:
                return (float(parts[0]), float(parts[1]))
            except ValueError:
                return None
    if s.startswith(">="):
        try:
            t = float(s[2:])
            return (t, 999)
        except ValueError:
            return None
    if s.startswith("<="):
        try:
            t = float(s[2:])
            return (-999, t)
        except ValueError:
            return None
    if s.startswith(">"):
        try:
            t = float(s[1:])
            return (t, 999)
        except ValueError:
            return None
    if s.startswith("<"):
        try:
            t = float(s[1:])
            return (-999, t)
        except ValueError:
            return None
    return None


def _parse_time_range(value: str) -> Optional[tuple]:
    """解析时段: '8,11' -> (8,11) 闭区间小时; '14,18' -> 下午2-6点"""
    if not value or not str(value).strip():
        return None
    s = str(value).strip().replace(" ", "")
    if "," in s:
        parts = s.split(",")
        if len(parts) == 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except ValueError:
                return None
    return None


def _parse_day_value(value: str) -> Optional[set]:
    """解析星期: '6'=周日; '4,5,6'=五/六/日; 'fri,sat,sun' 或 'sun'"""
    from app.services.scheduler_service import _DAY_ALIAS
    if not value or not str(value).strip():
        return None
    s = str(value).strip().lower()
    days = set()
    for part in s.split(","):
        part = part.strip()
        if part.isdigit():
            days.add(int(part))
        elif part in _DAY_ALIAS:
            days.add(_DAY_ALIAS[part])
    return days if days else None


def _conditions_match(
    conditions: List[Dict],
    weather: str,
    city: str = "Adelaide",
    temp_c: Optional[float] = None,
    region: str = "western",
    hour: Optional[int] = None,
    weekday: Optional[int] = None,
    china_subregion: Optional[str] = None,
    solar_terms: Optional[List[str]] = None,
) -> bool:
    """检查规则条件是否全部匹配（天气、温度、文化圈、城市、时段、星期）"""
    weather_normalized = normalize_weather_value(weather)
    if not weather_normalized:
        weather_normalized = {weather}

    for cond in conditions or []:
        ctype = cond.get("type")
        value = cond.get("value", "")
        op = cond.get("operator", "==")

        if ctype == "weather":
            cond_normalized = normalize_weather_value(str(value))
            matched = False
            if op == "==" and (weather_normalized & cond_normalized):
                matched = True
            elif op == "in":
                for v in [x.strip() for x in str(value).split(",")]:
                    if weather_normalized & normalize_weather_value(v):
                        matched = True
                        break
            if not matched:
                return False
        elif ctype == "city" and op == "==":
            if value and str(value).lower() != city.lower():
                return False
        elif ctype == "temp" and temp_c is not None:
            tr = _parse_temp_range(str(value))
            if tr:
                lo, hi = tr
                if not (lo <= temp_c <= hi):
                    return False
        elif ctype == "region" and op == "==":
            if value and str(value).lower() != region.lower():
                return False
        elif ctype == "time" and hour is not None:
            tr = _parse_time_range(str(value))
            if tr:
                lo, hi = tr
                if not (lo <= hour <= hi):
                    return False
        elif ctype == "day" and weekday is not None:
            days = _parse_day_value(str(value))
            if days and weekday not in days:
                return False
        elif ctype == "china_region":
            # 规则含 china_region 时：非中国地区（china_subregion 为空）必定不匹配
            if not china_subregion:
                return False
            if value and str(value).lower() != china_subregion.lower():
                return False
        elif ctype == "solar_term":
            # 规则含 solar_term 时：非节气日（solar_terms 为空）必定不匹配
            if not solar_terms:
                return False
            if value and str(value).strip() not in (solar_terms or []):
                return False
    return True


def match_content_for_store(
    store_id: str,
    store: Dict,
    rules: List[Dict],
    weather: str,
    city: str = "Adelaide",
    temp_c: Optional[float] = None,
    region: str = "western",
    hour: Optional[int] = None,
    weekday: Optional[int] = None,
    china_subregion: Optional[str] = None,
    solar_terms: Optional[List[str]] = None,
) -> str:
    """
    为指定门店匹配应播放的内容。
    返回 target_id 或 "default"
    """
    if not store.get("is_active", True):
        return "default"

    opening_hours = store.get("opening_hours")
    if not is_store_open(opening_hours, store.get("timezone", "Australia/Adelaide")):
        return "default"

    for rule in sorted(rules, key=lambda r: -(r.get("priority") or 1)):
        rule_store_id = rule.get("store_id", "")
        if rule_store_id and rule_store_id != "*" and rule_store_id != store_id:
            continue
        conditions = rule.get("conditions", [])
        if _conditions_match(conditions, weather, city, temp_c=temp_c, region=region, hour=hour, weekday=weekday,
                            china_subregion=china_subregion, solar_terms=solar_terms):
            return rule.get("action", {}).get("target_id", "default")

    return "default"


async def run_matching_for_all_stores(
    db: Optional[Session],
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    city: str = "Adelaide",
    country_code: Optional[str] = None,
    china_subregion: Optional[str] = None,
) -> Dict[str, str]:
    """
    为所有活跃门店执行匹配，返回 {store_id: target_id}
    支持传入 lat/lon 获取该位置天气+温度，country_code 获取文化圈层
    """
    from app.database import USE_DATABASE, SessionLocal
    from app.models.rule_model import Rule
    from app.models.store_model import Store
    from app.services.scheduler_service import get_weather_context
    from app.services.region_service import get_region_from_country

    from app.services.solar_term_service import get_active_solar_terms
    from datetime import date
    tz_map = {"AU": "Australia/Adelaide", "CN": "Asia/Shanghai", "JP": "Asia/Tokyo", "GB": "Europe/London", "US": "America/New_York", "SG": "Asia/Singapore"}
    tz = tz_map.get((country_code or "").upper(), "Australia/Adelaide")
    ctx = await get_weather_context(lat, lon, timezone=tz)
    weather = ctx.get("weather", "sunny")
    temp_c = ctx.get("temp_c")
    hour = ctx.get("hour")
    weekday = ctx.get("weekday")
    region = get_region_from_country(country_code)
    solar_terms = get_active_solar_terms(date.today()) if country_code in ("CN", "HK", "MO", "TW") else []

    session = db
    own = False
    if not session and USE_DATABASE and SessionLocal:
        session = SessionLocal()
        own = True

    result = {}
    try:
        if not session:
            return {"store_001": "default"}

        stores = session.query(Store).filter(Store.is_active == True).all()
        rules = session.query(Rule).order_by(Rule.priority.desc()).all()
        rules_list = [r.to_dict() for r in rules]

        for s in stores:
            store_dict = s.to_dict()
            target = match_content_for_store(
                s.id,
                store_dict,
                rules_list,
                weather,
                city,
                temp_c=temp_c,
                region=region,
                hour=hour,
                weekday=weekday,
                china_subregion=china_subregion if country_code in ("CN", "HK", "MO", "TW") else None,
                solar_terms=solar_terms,
            )
            result[s.id] = target
    finally:
        if own and session:
            session.close()

    return result if result else {"store_001": "default"}
