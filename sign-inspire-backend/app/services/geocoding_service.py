"""
地理编码：将城市名转为经纬度与 bbox
使用 OpenStreetMap Nominatim，免费无需 API Key
"""
import httpx
from typing import Optional, Tuple, Dict, Any
from time import time

# 地理编码缓存：Nominatim 国内访问慢，缓存 30 分钟
_GEO_CACHE: Dict[str, tuple] = {}
_GEO_CACHE_TTL = 1800

NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"

# 常用城市预设：(lat, lon, bbox, country_code, china_subregion?)
# china_subregion: south_china / east_china / north_china，仅 CN 有效
_CITY_PRESETS_RAW: Dict[str, tuple] = {
    "adelaide": (-34.9285, 138.6007, (-35.05, 138.45, -34.70, 138.75), "AU", None),
    "sydney": (-33.8688, 151.2093, (-34.10, 150.50, -33.50, 151.50), "AU", None),
    "melbourne": (-37.8136, 144.9631, (-38.10, 144.50, -37.50, 145.50), "AU", None),
    "brisbane": (-27.4698, 153.0251, (-27.80, 152.70, -27.20, 153.50), "AU", None),
    "perth": (-31.9505, 115.8605, (-32.30, 115.50, -31.50, 116.30), "AU", None),
    "london": (51.5074, -0.1278, (51.30, -0.50, 51.70, 0.20), "GB", None),
    "new york": (40.7128, -74.0060, (40.50, -74.30, 40.95, -73.70), "US", None),
    "paris": (48.8566, 2.3522, (48.65, 2.10, 49.05, 2.60), "FR", None),
    "tokyo": (35.6762, 139.6503, (35.40, 139.20, 35.95, 140.20), "JP", None),
    "singapore": (1.3521, 103.8198, (1.10, 103.50, 1.50, 104.20), "SG", None),
    "hong kong": (22.3193, 114.1694, (22.15, 113.80, 22.55, 114.40), "HK", "south_china"),
    "shanghai": (31.2304, 121.4737, (30.90, 121.00, 31.55, 122.00), "CN", "east_china"),
    "beijing": (39.9042, 116.4074, (39.70, 115.80, 40.20, 117.00), "CN", "north_china"),
    "guangzhou": (23.1291, 113.2644, (22.5, 112.9, 23.9, 114.0), "CN", "south_china"),
    "shenzhen": (22.5431, 114.0579, (22.4, 113.7, 22.8, 114.6), "CN", "south_china"),
    "hangzhou": (30.2741, 120.1551, (29.7, 119.2, 30.6, 120.6), "CN", "east_china"),
    "chengdu": (30.5728, 104.0668, (30.4, 103.7, 30.9, 104.5), "CN", "east_china"),
    "chongqing": (29.4316, 106.9123, (28.9, 106.2, 30.0, 107.0), "CN", "east_china"),
}
CITY_PRESETS = {k: (v[0], v[1], v[2]) for k, v in _CITY_PRESETS_RAW.items()}


def geocode_city(city: str) -> Optional[Dict[str, Any]]:
    """
    将城市名转为 { lat, lon, bbox, country_code?, china_subregion? }
    bbox = (south, west, north, east)
    """
    if not city or not city.strip():
        return None
    key = city.strip().lower()
    preset_raw = _CITY_PRESETS_RAW.get(key)
    if preset_raw:
        lat, lon, bbox, cc = preset_raw[:4]
        out = {"lat": lat, "lon": lon, "bbox": bbox, "city": city.strip(), "country_code": cc}
        if len(preset_raw) > 4 and preset_raw[4]:
            out["china_subregion"] = preset_raw[4]
        return out
    return geocode_city_sync(city)


def geocode_city_sync(city: str) -> Optional[Dict[str, Any]]:
    """将城市名转为经纬度与 bbox（含 country_code、china_subregion 若预设中有）"""
    if not city or not city.strip():
        return None
    key = city.strip().lower()
    # 缓存检查
    now = time()
    if key in _GEO_CACHE:
        cached, ts = _GEO_CACHE[key]
        if now - ts < _GEO_CACHE_TTL:
            return cached
    preset_raw = _CITY_PRESETS_RAW.get(key)
    if preset_raw:
        lat, lon, bbox, cc = preset_raw[:4]
        out = {"lat": lat, "lon": lon, "bbox": bbox, "city": city.strip(), "country_code": cc}
        if len(preset_raw) > 4 and preset_raw[4]:
            out["china_subregion"] = preset_raw[4]
        _GEO_CACHE[key] = (out, now)
        return out
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                NOMINATIM_SEARCH,
                params={"q": city, "format": "json", "limit": 1},
                headers={"User-Agent": "SignInspire/1.0"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            d = data[0]
            lat = float(d.get("lat", 0))
            lon = float(d.get("lon", 0))
            bbox_raw = d.get("boundingbox")
            if bbox_raw:
                s, n, w, e = [float(x) for x in bbox_raw]
                bbox = (s, w, n, e)
            else:
                delta = 0.15
                bbox = (lat - delta, lon - delta, lat + delta, lon + delta)
            addr = d.get("address", {}) or {}
            country_code = (addr.get("country_code") or "").upper()
            state = addr.get("state") or addr.get("province") or ""
            from app.services.china_region_service import get_china_subregion
            china_sub = get_china_subregion(d.get("name") or city, state, lat) if country_code == "CN" else None
            out = {"lat": lat, "lon": lon, "bbox": bbox, "city": d.get("display_name", city), "country_code": country_code}
            if china_sub:
                out["china_subregion"] = china_sub
            _GEO_CACHE[key] = (out, now)
            return out
    except Exception as e:
        print(f"⚠️ [Geocoding] {city} 解析失败: {e}")
        return None


def reverse_geocode_sync(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    逆地理编码：经纬度 -> 城市/地址
    用于用户定位后显示位置名称
    """
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                NOMINATIM_REVERSE,
                params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
                headers={"User-Agent": "SignInspire/1.0"},
            )
            if resp.status_code != 200:
                return None
            d = resp.json()
            addr = d.get("address", {})
            city = (
                addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or addr.get("municipality")
                or addr.get("county")
                or addr.get("state")
                or d.get("name", "")
            )
            display = d.get("display_name", str(city))
            country_code = (addr.get("country_code") or "").upper()
            state = addr.get("state") or addr.get("province") or ""
            delta = 0.08
            bbox = (lat - delta, lon - delta, lat + delta, lon + delta)
            from app.services.china_region_service import get_china_subregion
            china_sub = get_china_subregion(str(city), state, lat) if country_code == "CN" else None
            out = {"lat": lat, "lon": lon, "bbox": bbox, "city": str(city) or display[:50], "display_name": display, "country_code": country_code}
            if china_sub:
                out["china_subregion"] = china_sub
            return out
    except Exception as e:
        print(f"⚠️ [Geocoding] 逆解析 ({lat},{lon}) 失败: {e}")
        return None
