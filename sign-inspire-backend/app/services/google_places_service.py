"""
Google Places API 服务：获取门店完整地址、图片等
优先使用 Places API (New)，403 时回退到 Legacy Places API
需在 Google Cloud Console 启用 Places API
"""
import os
from typing import List, Dict, Any, Optional

import httpx

# 优先使用 Places 专用 key，否则用通用 Google API Key
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY")
PLACES_BASE = "https://places.googleapis.com/v1"
LEGACY_BASE = "https://maps.googleapis.com/maps/api/place"

# target_id -> Google Places includedTypes (New) / type (Legacy)
TARGET_TO_PLACES_TYPES = {
    "coffee_ad": ["cafe"],
    "coffee_ads": ["cafe"],
    "hot_drink_ad": ["cafe", "restaurant"],
    "sunscreen_ad": ["pharmacy", "store"],
    "xigua_ad": ["supermarket", "meal_takeaway"],
    "bingxigua_ad": ["ice_cream_shop", "cafe"],
    "sushi_ad": ["restaurant"],
    "shousi_ad": ["restaurant"],
    "shousi_guanggao": ["restaurant"],
    "shou_si": ["restaurant"],
    "shou_si_guang_gao": ["restaurant"],
    "bbq_ad": ["restaurant"],
    "fish_chips_ad": ["restaurant", "meal_takeaway"],
    "pizza_ad": ["restaurant"],
    "asian_soup_ad": ["restaurant"],
    "green_bean_soup_ad": ["restaurant", "cafe"],
    "herbal_tea_ad": ["cafe", "store"],
    "congee_ad": ["restaurant"],
    "crayfish_ad": ["restaurant"],
    "dumplings_ad": ["restaurant"],
    "tangyuan_ad": ["restaurant"],
    "bubble_tea_ad": ["cafe"],
    "cold_noodles_ad": ["restaurant"],
    "lamb_hotpot_ad": ["restaurant"],
    "iron_pot_stew_ad": ["restaurant"],
    "hairy_crab_ad": ["restaurant"],
    "vietnamese_ad": ["restaurant"],
    "burger_ad": ["restaurant"],
}
TARGET_TO_LEGACY_TYPE = {
    "coffee_ad": "cafe",
    "coffee_ads": "cafe",
    "hot_drink_ad": "cafe",
    "sunscreen_ad": "pharmacy",
    "xigua_ad": "meal_takeaway",
    "bingxigua_ad": "cafe",
    "sushi_ad": "restaurant",
    "shousi_ad": "restaurant",
    "shousi_guanggao": "restaurant",
    "shou_si": "restaurant",
    "shou_si_guang_gao": "restaurant",
    "bbq_ad": "restaurant",
    "fish_chips_ad": "restaurant",
    "pizza_ad": "restaurant",
    "asian_soup_ad": "restaurant",
    "green_bean_soup_ad": "restaurant",
    "herbal_tea_ad": "cafe",
    "congee_ad": "restaurant",
    "crayfish_ad": "restaurant",
    "dumplings_ad": "restaurant",
    "tangyuan_ad": "restaurant",
    "bubble_tea_ad": "cafe",
    "cold_noodles_ad": "restaurant",
    "lamb_hotpot_ad": "restaurant",
    "iron_pot_stew_ad": "restaurant",
    "hairy_crab_ad": "restaurant",
    "vietnamese_ad": "restaurant",
    "burger_ad": "restaurant",
}
# 使用 Text Search 的 target_id，query 模板含 {city}
TARGET_TO_LEGACY_QUERY = {
    "coffee_ad": "coffee shop cafe {city}",
    "coffee_ads": "coffee shop cafe {city}",
    "hot_drink_ad": "coffee cafe {city}",
    "bingxigua_ad": "ice cream cafe {city}",
    "sushi_ad": "sushi restaurant japanese {city}",
    "shousi_ad": "sushi restaurant japanese {city}",
    "shousi_guanggao": "sushi restaurant japanese {city}",
    "shou_si": "sushi restaurant japanese {city}",
    "shou_si_guang_gao": "sushi restaurant japanese {city}",
    "bbq_ad": "BBQ barbecue restaurant {city}",
    "fish_chips_ad": "fish and chips {city}",
    "pizza_ad": "pizza restaurant {city}",
    "asian_soup_ad": "laksa pho ramen {city}",
    "green_bean_soup_ad": "绿豆沙 糖水 甜品 {city}",
    "herbal_tea_ad": "凉茶 {city}",
    "congee_ad": "砂锅粥 海鲜粥 {city}",
    "crayfish_ad": "小龙虾 {city}",
    "dumplings_ad": "饺子 水饺 {city}",
    "tangyuan_ad": "汤圆 元宵 {city}",
    "bubble_tea_ad": "奶茶 茶饮 {city}",
    "cold_noodles_ad": "冷面 朝鲜冷面 {city}",
    "lamb_hotpot_ad": "铜锅涮肉 羊汤 {city}",
    "iron_pot_stew_ad": "铁锅炖 {city}",
    "hairy_crab_ad": "大闸蟹 {city}",
    "vietnamese_ad": "Vietnamese restaurant cold rolls {city}",
    "burger_ad": "schnitzel burger pub {city}",
}
# 需排除的 types（加油站、便利店、酒店等非咖啡主营）
EXCLUDE_TYPES_CAFE = {
    "gas_station", "convenience_store", "lodging", "travel_agency",
    "tourist_attraction",
}
DEFAULT_TYPES = ["cafe"]
DEFAULT_LEGACY_TYPE = "cafe"

DEFAULT_RADIUS_M = 15000  # 15km


def _search_text_legacy(
    query: str, lat: float, lon: float, radius: int = DEFAULT_RADIUS_M, limit: int = 10
) -> List[Dict[str, Any]]:
    """Legacy Text Search - 语义搜索，咖啡/咖啡馆更精准"""
    if not API_KEY:
        return []
    url = f"{LEGACY_BASE}/textsearch/json"
    params = {
        "query": query,
        "location": f"{lat},{lon}",
        "radius": radius,
        "key": API_KEY,
    }
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if data.get("status") != "OK":
                return []
            return data.get("results", [])[:limit * 2]  # 多取一些供过滤
    except Exception as e:
        print(f"⚠️ [Places] Text Search 失败: {e}")
        return []


def _search_nearby_legacy(
    lat: float, lon: float, place_type: str,
    radius: int = DEFAULT_RADIUS_M,
    keyword: Optional[str] = None, limit: int = 10
) -> List[Dict[str, Any]]:
    """Legacy Nearby Search - 使用 maps.googleapis.com"""
    if not API_KEY:
        return []
    url = f"{LEGACY_BASE}/nearbysearch/json"
    params = {
        "location": f"{lat},{lon}",
        "radius": radius,
        "type": place_type,
        "key": API_KEY,
    }
    if keyword:
        params["keyword"] = keyword
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if data.get("status") != "OK":
                return []
            return data.get("results", [])[:limit * 2]
    except Exception as e:
        print(f"⚠️ [Places] Legacy 请求失败: {e}")
        return []


def _legacy_photo_to_url(photo_ref: str, max_width: int = 800) -> Optional[str]:
    """Legacy: 获取 photo 重定向后的真实 URL，供前端直接加载"""
    if not API_KEY or not photo_ref:
        return None
    url = f"{LEGACY_BASE}/photo"
    params = {"maxwidth": max_width, "photo_reference": photo_ref, "key": API_KEY}
    try:
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return None
            return str(resp.url)
    except Exception:
        return None


def _should_exclude_cafe(place: Dict[str, Any]) -> bool:
    """排除加油站、酒店等非咖啡主营门店"""
    types = set(t.lower() for t in (place.get("types") or []))
    if types & EXCLUDE_TYPES_CAFE:
        return True
    name = (place.get("name") or "").lower()
    exclude_names = ("otr ", " otr", "bp ", " petrol", "gas station", "convention centre", "suites &")
    return any(x in name for x in exclude_names)


def _search_stores_legacy(
    lat: float, lon: float, place_type: str,
    limit: int = 10, target_id: str = "",
    city: str = "Adelaide", radius: int = DEFAULT_RADIUS_M,
) -> List[Dict[str, Any]]:
    """Legacy Places API 结果转统一格式，咖啡用 Text Search 更精准"""
    query_tpl = TARGET_TO_LEGACY_QUERY.get(target_id) if target_id else None
    if query_tpl:
        query = query_tpl.format(city=city)
        raw = _search_text_legacy(query, lat, lon, radius, limit)
    else:
        # 未知 target_id 时按 target_id 构造 Text Search（如 shousi -> "shousi restaurant"）
        if target_id and target_id != "default":
            kw = target_id.replace("_ad", "").replace("_guanggao", "").replace("_", " ")
            if kw:
                query = f"{kw} restaurant {city}"
                raw = _search_text_legacy(query, lat, lon, radius, limit)
            else:
                keyword = "coffee cafe" if place_type == "cafe" else None
                raw = _search_nearby_legacy(lat, lon, place_type, radius, keyword=keyword, limit=limit)
        else:
            keyword = "coffee cafe" if place_type == "cafe" else None
            raw = _search_nearby_legacy(lat, lon, place_type, radius, keyword=keyword, limit=limit)
    results = []
    seen = set()
    for p in raw:
        if target_id in ("coffee_ad", "coffee_ads", "hot_drink_ad") and _should_exclude_cafe(p):
            continue
        name = (p.get("name") or "未知").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        loc = p.get("geometry", {}).get("location", {})
        lat_val = loc.get("lat")
        lon_val = loc.get("lng")
        vicinity = p.get("vicinity") or p.get("formatted_address") or ""
        place_id = p.get("place_id")
        google_maps_uri = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None
        photos_raw = p.get("photos") or []
        photo_urls: List[str] = []
        for ph in photos_raw[:5]:
            ref = ph.get("photo_reference")
            if ref:
                url = _legacy_photo_to_url(ref)
                if url:
                    photo_urls.append(url)
        results.append({
            "name": name,
            "address": vicinity.strip() or "-",
            "latitude": lat_val,
            "longitude": lon_val,
            "type": "place",
            "photos": photo_urls,
            "google_maps_uri": google_maps_uri,
        })
        if len(results) >= limit:
            break
    return results


def _search_nearby(
    lat: float, lon: float,
    included_types: List[str],
    limit: int = 10,
    radius: int = DEFAULT_RADIUS_M,
) -> List[Dict[str, Any]]:
    """Nearby Search (New) - 按位置和类型搜索"""
    if not API_KEY:
        return []
    url = f"{PLACES_BASE}/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.photos,places.googleMapsUri",
    }
    body = {
        "includedTypes": included_types[:5],
        "maxResultCount": min(limit, 20),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": float(radius),
            }
        },
        "rankPreference": "POPULARITY",
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=body, headers=headers)
            if resp.status_code == 403:
                print(f"⚠️ [Places] Nearby Search (New) 被限制，将使用 Legacy API")
                return None  # 触发 fallback
            if resp.status_code != 200:
                print(f"⚠️ [Places] Nearby Search 失败: {resp.status_code}")
                return []
            data = resp.json()
    except Exception as e:
        print(f"⚠️ [Places] 请求失败: {e}")
        return []
    places = data.get("places", [])
    return places


def _resolve_photo_uri(photo_name: str, max_size: int = 800) -> Optional[str]:
    """通过 Place Photos API 获取图片 CDN URL（skipHttpRedirect 返回 photoUri）"""
    if not API_KEY or not photo_name:
        return None
    url = f"{PLACES_BASE}/{photo_name}/media"
    params = {"maxWidthPx": max_size, "key": API_KEY, "skipHttpRedirect": "true"}
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return None
            j = resp.json()
            return j.get("photoUri")
    except Exception:
        return None


def search_stores_google(
    target_id: str,
    lat: float,
    lon: float,
    city: str = "Adelaide",
    limit: int = 10,
    radius: int = DEFAULT_RADIUS_M,
) -> List[Dict[str, Any]]:
    """
    使用 Google Places API 获取门店（含地址、图片）
    支持全球任意城市
    """
    if not API_KEY:
        return []
    types = TARGET_TO_PLACES_TYPES.get(target_id, DEFAULT_TYPES)
    places = _search_nearby(lat, lon, types, limit=limit, radius=radius)

    # 403 时使用 Legacy API
    if places is None:
        legacy_type = TARGET_TO_LEGACY_TYPE.get(target_id, DEFAULT_LEGACY_TYPE)
        return _search_stores_legacy(
            lat, lon, legacy_type, limit, target_id=target_id,
            city=city, radius=radius,
        )
    if not places:
        return []

    results = []
    seen = set()
    for p in places:
        name_obj = p.get("displayName") or {}
        name = (name_obj.get("text") or "未知").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        addr = p.get("formattedAddress") or ""
        loc = p.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        photos_raw = p.get("photos") or []
        photo_urls: List[str] = []
        for ph in photos_raw[:5]:  # 最多 5 张
            pname = ph.get("name")
            if pname:
                uri = _resolve_photo_uri(pname)
                if uri:
                    photo_urls.append(uri)
        results.append({
            "name": name,
            "address": addr.strip() or "-",
            "latitude": lat,
            "longitude": lon,
            "type": "place",
            "photos": photo_urls,
            "google_maps_uri": p.get("googleMapsUri"),
        })
        if len(results) >= limit:
            break
    return results
