"""
高德地图 POI 服务：国内服务器替代 Google Places
需在 .env 中配置 AMAP_API_KEY，在 高德开放平台 申请 Web 服务 Key
https://lbs.amap.com/api/webservice/summary
"""
import os
from typing import List, Dict, Any, Optional
import httpx

API_KEY = os.getenv("AMAP_API_KEY")
BASE_URL = "https://restapi.amap.com/v3/place"

# target_id -> 高德搜索关键词
TARGET_TO_KEYWORDS: Dict[str, str] = {
    "coffee_ad": "咖啡",
    "coffee_ads": "咖啡",
    "hot_drink_ad": "咖啡馆 茶",
    "bingxigua_ad": "冰品 冰淇淋",
    "sushi_ad": "日料 寿司",
    "pizza_ad": "披萨",
    "bbq_ad": "烧烤",
    "asian_soup_ad": "越南粉 拉面 河粉",
    "green_bean_soup_ad": "糖水 绿豆沙",
    "herbal_tea_ad": "凉茶",
    "congee_ad": "砂锅粥 粥",
    "crayfish_ad": "小龙虾",
    "dumplings_ad": "饺子",
    "tangyuan_ad": "汤圆",
    "bubble_tea_ad": "奶茶",
    "cold_noodles_ad": "冷面",
    "lamb_hotpot_ad": "涮肉 羊汤",
    "iron_pot_stew_ad": "铁锅炖",
    "hairy_crab_ad": "大闸蟹",
    "vietnamese_ad": "越南菜",
    "burger_ad": "汉堡 炸鸡",
    "default": "咖啡馆",
}


def search_stores_amap(
    target_id: str,
    lat: float,
    lon: float,
    city: str,
    limit: int = 10,
    radius: int = 5000,
) -> List[Dict[str, Any]]:
    """
    高德周边搜索，返回与 Google Places 兼容格式
    """
    if not API_KEY:
        return []
    keywords = TARGET_TO_KEYWORDS.get(target_id) or TARGET_TO_KEYWORDS.get("default", "餐厅")
    kw = keywords.split()[0] if keywords else "餐厅"

    try:
        params = {
            "key": API_KEY,
            "location": f"{lon},{lat}",  # 高德：经度,纬度
            "keywords": kw,
            "radius": min(radius, 50000),
            "offset": min(limit, 25),
            "page": 1,
            "extensions": "all",
        }
        if city:
            params["city"] = city

        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{BASE_URL}/around", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if data.get("status") != "1":
                return []
            pois = data.get("pois") or []
    except Exception as e:
        print(f"⚠️ [Amap] 请求失败: {e}")
        return []

    out = []
    for p in pois[:limit]:
        loc = p.get("location", "")
        parts = loc.split(",") if loc else ["", ""]
        lon_s, lat_s = float(parts[0]) if len(parts) > 0 and parts[0] else lon, float(parts[1]) if len(parts) > 1 and parts[1] else lat
        photos = []
        for ph in (p.get("photos") or [])[:3]:
            if isinstance(ph, dict) and ph.get("url"):
                photos.append(ph["url"])
            elif isinstance(ph, str):
                photos.append(ph)
        out.append({
            "name": p.get("name") or "未知",
            "address": (p.get("address") or "").strip() or f"{p.get('pname','')}{p.get('cityname','')}{p.get('adname','')}",
            "latitude": lat_s,
            "longitude": lon_s,
            "type": p.get("type", ""),
            "photos": photos,
            "google_maps_uri": f"https://uri.amap.com/marker?position={lon_s},{lat_s}&name={p.get('name','')}",
        })
    return out
