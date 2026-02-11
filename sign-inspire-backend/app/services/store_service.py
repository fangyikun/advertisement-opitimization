"""门店服务：营业状态判断等"""
from datetime import datetime
from typing import Optional, Dict, Any


def is_store_open(opening_hours: Optional[Dict[str, str]], timezone: str = "Australia/Adelaide") -> bool:
    """
    根据 opening_hours 判断当前是否营业。
    格式: {"mon":"09:00-17:00", "tue":"09:00-17:00", ...}
    若 opening_hours 为空，默认视为营业中。
    """
    if not opening_hours:
        return True
    try:
        now = datetime.now()
        day_key = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        hours_str = opening_hours.get(day_key) or opening_hours.get(day_key.capitalize())
        if not hours_str:
            return True
        parts = hours_str.split("-")
        if len(parts) != 2:
            return True
        start = parts[0].strip()
        end = parts[1].strip()
        current = now.strftime("%H:%M")
        return start <= current <= end
    except Exception:
        return True
