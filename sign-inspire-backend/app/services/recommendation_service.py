"""
推荐服务：根据当前天气+规则，获取全球任意城市真实门店信息
使用 Overpass API (OpenStreetMap) 免费获取咖啡店等 POI
"""
import httpx
from typing import List, Dict, Any, Optional
from time import time

# 推荐结果缓存：减少重复请求，提升门店推送响应速度
_REC_CACHE: Dict[str, tuple] = {}
_REC_CACHE_TTL = 120  # 2 分钟

# target_id -> Overpass 查询条件 (amenity 或 shop 等)
TARGET_TO_OVERPASS = {
    "coffee_ad": [('amenity', 'cafe')],
    "coffee_ads": [('amenity', 'cafe')],
    "hot_drink_ad": [('amenity', 'cafe'), ('amenity', 'restaurant')],
    "sunscreen_ad": [('shop', 'cosmetics'), ('shop', 'chemist')],
    "xigua_ad": [('shop', 'greengrocer'), ('amenity', 'fast_food')],
    "bingxigua_ad": [('shop', 'greengrocer'), ('amenity', 'ice_cream')],
    # 寿司/日料（含拼音变体：寿司->shou_si, 寿司广告->shou_si_guang_gao 等）
    "sushi_ad": [('amenity', 'restaurant'), ('cuisine', 'japanese')],
    "shousi_ad": [('amenity', 'restaurant'), ('cuisine', 'japanese')],
    "shousi_guanggao": [('amenity', 'restaurant'), ('cuisine', 'japanese')],
    "shou_si": [('amenity', 'restaurant'), ('cuisine', 'japanese')],
    "shou_si_guang_gao": [('amenity', 'restaurant'), ('cuisine', 'japanese')],
    # 澳洲特色（Overpass 用 restaurant 兜底，Google Text Search 精准）
    "bbq_ad": [('amenity', 'restaurant')],
    "fish_chips_ad": [('amenity', 'fast_food'), ('amenity', 'restaurant')],
    "pizza_ad": [('amenity', 'restaurant')],
    "asian_soup_ad": [('amenity', 'restaurant')],
    # 中国特色
    "green_bean_soup_ad": [('amenity', 'restaurant')],
    "herbal_tea_ad": [('amenity', 'cafe'), ('shop', 'beverages')],
    "congee_ad": [('amenity', 'restaurant')],
    "crayfish_ad": [('amenity', 'restaurant')],
    "dumplings_ad": [('amenity', 'restaurant')],
    "tangyuan_ad": [('amenity', 'restaurant')],
    "bubble_tea_ad": [('amenity', 'cafe')],
    "cold_noodles_ad": [('amenity', 'restaurant')],
    "lamb_hotpot_ad": [('amenity', 'restaurant')],
    "iron_pot_stew_ad": [('amenity', 'restaurant')],
    "hairy_crab_ad": [('amenity', 'restaurant')],
    "vietnamese_ad": [('amenity', 'restaurant')],
    "burger_ad": [('amenity', 'restaurant')],
}
DEFAULT_OVERPASS = [('amenity', 'cafe')]

# 每个 target_id 的默认推送语（用户点击标签时展示；格式：英文 / 中文，前端可取中文部分）
TARGET_TO_PUSH_MESSAGE: Dict[str, str] = {
    "coffee_ad": "Sunny day calls for a coffee. Take it outside. / 好天气，咖啡馆见。",
    "coffee_ads": "Sunny day calls for a coffee. Take it outside. / 好天气，咖啡馆见。",
    "hot_drink_ad": "Snowy day? Hot chocolate or a warming brew. / 雪天，热可可或热饮暖手又暖心。",
    "bingxigua_ad": "Scorcher! Time for gelato, icy poles. / 酷暑来袭，冰品冷饮救赎。",
    "sushi_ad": "Grey skies? Add some colour with a fresh Salmon Poke Bowl. 🌈 / 多云天心情修复剂：新鲜多彩的寿司卷。",
    "pizza_ad": "Sunday arvo? Pizza and cold ones. The Aussie way. / 周日午后，披萨配啤酒，澳式惬意。",
    "bbq_ad": "Sunny weekend? Fire up the barbie! Sausages and snags await. / 晴朗周末，后院 BBQ 走起！",
    "asian_soup_ad": "Chilly and wet? Warm up with laksa, pho, or ramen. / 湿冷天，来碗叻沙或拉面暖暖胃。",
    "green_bean_soup_ad": "天气这么热，来碗绿豆沙下下火吧！ / 湿热天，绿豆沙、龟苓膏祛湿解暑。",
    "herbal_tea_ad": "湿气重？喝凉茶还是吃龟苓膏？ / 夏日祛湿，王老吉、凉茶安排。",
    "congee_ad": "下雨天最适合喝砂锅粥，暖暖的超舒服。 / 雨天标配，海鲜粥、皮蛋瘦肉粥。",
    "crayfish_ad": "黄梅天闷热没胃口？小龙虾配啤酒，开胃！ / 深夜的麻辣烫小龙虾，是打工人的灵魂伴侣。",
    "dumplings_ad": "冬至不端饺子碗，冻掉耳朵没人管！ / 北方冬至，饺子安排。",
    "tangyuan_ad": "冬至大如年，南方吃汤圆，团团圆圆。 / 冬至吃汤圆，甜甜蜜蜜过冬。",
    "bubble_tea_ad": "周五了！奶茶炸鸡走起！ / TGIF，奶茶炸鸡犒劳自己。",
    "cold_noodles_ad": "大热天吃冷面，透心凉！ / 晚上出来撸串？啤酒我都冰好了。",
    "lamb_hotpot_ad": "下雪了！铜锅涮肉最治愈。 / 立秋贴秋膘，肉食者的节日。",
    "iron_pot_stew_ad": "下雪天，铁锅炖大鹅、排骨，暖到心窝。 / 雪天标配，铁锅炖走起。",
    "hairy_crab_ad": "秋风起，蟹脚痒。今晚大闸蟹安排上？ / 秋凉正是吃蟹时。",
    "vietnamese_ad": "Bit muggy? Cool down with a zesty Vietnamese Chicken Salad. / 外面有点闷？来份越南鸡肉沙拉清爽一下。",
    "burger_ad": "Classic Schnitty weather. Perfect for the beer garden. / 多云的周三？吃顿塔可大餐吧。",
    "sunscreen_ad": "Sun's out? Don't forget the SPF. / 晴天外出，记得防晒。",
    "xigua_ad": "Hot day? Chill with watermelon and cold drinks. / 天热来块冰西瓜，清凉解暑。",
    "fish_chips_ad": "Classic Aussie fish and chips. Can't go wrong. / 经典炸鱼薯条，澳式风味。",
    "shousi_ad": "Grey skies? Add some colour with a fresh Poke Bowl. / 多云天心情修复剂：新鲜寿司卷。",
    "shou_si": "Grey skies? Add some colour with a fresh Poke Bowl. / 多云天心情修复剂：新鲜寿司卷。",
}


def _build_overpass_query(key: str, value: str, bbox: tuple, limit: int = 10) -> str:
    """Overpass QL：指定 bbox 区域内指定类型的 POI，bbox=(south,west,north,east)"""
    s, w, n, e = bbox
    return f"""[out:json][timeout:15];
(
  node["{key}"="{value}"]({s},{w},{n},{e});
  way["{key}"="{value}"]({s},{w},{n},{e});
);
out center {limit};"""


def _parse_overpass_result(data: dict) -> List[Dict[str, Any]]:
    """解析 Overpass 返回为门店列表"""
    results = []
    for elem in data.get("elements", [])[:10]:
        tags = elem.get("tags", {})
        name = (tags.get("name") or tags.get("brand") or "未知").strip()
        addr = tags.get("addr:street") or tags.get("address") or ""
        if tags.get("addr:housenumber"):
            addr = f"{tags['addr:housenumber']} {addr}".strip()
        lat = elem.get("lat")
        lon = elem.get("lon")
        if lat is None and "center" in elem:
            lat = elem["center"].get("lat")
            lon = elem["center"].get("lon")
        results.append({
            "name": name or "未知门店",
            "address": addr.strip() or "-",
            "latitude": lat,
            "longitude": lon,
            "type": tags.get("amenity") or tags.get("shop") or "poi",
            "photos": [],
        })
    return results


def fetch_places_overpass(key: str, value: str, bbox: tuple, limit: int = 10) -> List[Dict[str, Any]]:
    """通过 Overpass API 获取 POI"""
    try:
        query = _build_overpass_query(key, value, bbox, limit)
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return _parse_overpass_result(data)
    except Exception as e:
        print(f"⚠️ [Recommendation] Overpass 请求失败: {e}")
        return []


def get_recommended_stores(
    target_id: str,
    lat: float,
    lon: float,
    city: str = "Adelaide",
    bbox: Optional[tuple] = None,
    limit: int = 10,
    radius: int = 15000,
) -> List[Dict[str, Any]]:
    """
    根据 target_id 获取指定城市对应类型的真实门店，支持全球
    优先 Google Places（含地址、图片），无 key 时回退 Overpass
    """
    if bbox is None:
        delta = 0.15
        bbox = (lat - delta, lon - delta, lat + delta, lon + delta)

    # 国内优先高德（无墙）；海外或无效时用 Google
    try:
        from app.services.amap_places_service import search_stores_amap
        stores = search_stores_amap(target_id, lat, lon, city, limit, radius)
        if stores:
            return stores
    except Exception as e:
        print(f"⚠️ [Recommendation] 高德跳过: {e}")

    try:
        from app.services.google_places_service import search_stores_google
        stores = search_stores_google(target_id, lat, lon, city, limit, radius)
        if stores:
            return stores
    except Exception as e:
        print(f"⚠️ [Recommendation] Google Places 跳过: {e}")

    # 未知 target_id 时用 restaurant 而非 cafe，避免总是显示咖啡店
    filters = TARGET_TO_OVERPASS.get(target_id)
    if not filters and target_id and target_id != "default":
        filters = [('amenity', 'restaurant')]  # 通用餐厅回退
    if not filters:
        filters = DEFAULT_OVERPASS
    all_results = []
    seen_names = set()

    for key, value in filters[:2]:
        places = fetch_places_overpass(key, value, bbox, limit=limit)
        for p in places:
            if p["name"] not in seen_names:
                seen_names.add(p["name"])
                all_results.append(p)
                if len(all_results) >= limit:
                    break
        if len(all_results) >= limit:
            break

    return all_results[:limit]


async def get_current_recommended_stores(
    limit: int = 10,
    city: str = "Adelaide",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    target_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    根据当前天气匹配的规则，获取应推送的门店推荐
    支持：1) 城市名  2) 用户定位 lat,lon
    返回: { weather, target_id, category_label, stores: [...], city: str }
    """
    # 缓存：相同参数短时间重复请求直接返回
    cache_key = f"{city}|{lat or 0:.2f}|{lon or 0:.2f}|{target_id or ''}|{limit}"
    now = time()
    if cache_key in _REC_CACHE:
        cached, ts = _REC_CACHE[cache_key]
        if now - ts < _REC_CACHE_TTL:
            return cached

    from app.services.scheduler_service import get_weather_context
    from app.services.region_service import get_region_from_country
    from app.services.matching_engine import run_matching_for_all_stores
    from app.services.geocoding_service import geocode_city_sync, reverse_geocode_sync

    # 优先使用用户定位 (lat, lon)
    if lat is not None and lon is not None:
        geo = reverse_geocode_sync(lat, lon)
        if geo:
            bbox = geo.get("bbox")
            city_display = geo.get("city", f"{lat:.4f}, {lon:.4f}")
        else:
            delta = 0.08
            bbox = (lat - delta, lon - delta, lat + delta, lon + delta)
            city_display = f"当前位置 ({lat:.4f}, {lon:.4f})"
    else:
        # 地理编码：城市名 -> lat, lon, bbox
        geo = geocode_city_sync(city)
        if not geo:
            return {
                "weather": "unknown",
                "target_id": "default",
                "category_label": "门店",
                "stores": [],
                "city": city,
                "message": f"无法解析城市「{city}」，请尝试其他名称如 Sydney、London",
            }
        lat, lon = geo["lat"], geo["lon"]
        bbox = geo.get("bbox")
        city_display = geo.get("city", city)

    # 该位置的天气 + 温度 + 文化圈（用于全球规则）
    wx_ctx = await get_weather_context(lat, lon)
    weather = wx_ctx.get("weather", "sunny")
    temp_c = wx_ctx.get("temp_c")
    country_code = geo.get("country_code") if isinstance(geo, dict) else None
    china_subregion = geo.get("china_subregion") if isinstance(geo, dict) else None
    if not china_subregion and country_code in ("CN", "HK", "MO", "TW"):
        from app.services.china_region_service import get_china_subregion
        china_subregion = get_china_subregion(geo.get("city"), geo.get("state"), lat)
    region = get_region_from_country(country_code)
    if target_id is None or target_id == "":
        by_store = await run_matching_for_all_stores(
            None, lat=lat, lon=lon, city=city_display or city, country_code=country_code, china_subregion=china_subregion
        )
        target_id = by_store.get("store_001", "default")

    weather_labels = {"sunny": "晴天", "cloudy": "多云", "rain": "雨天", "snow": "雪天", "storm": "雷暴", "fog": "雾天"}
    weather_cn = weather_labels.get(weather, weather)

    category_labels = {
        "coffee_ad": "咖啡店",
        "coffee_ads": "咖啡店",
        "hot_drink_ad": "热饮/咖啡馆",
        "sunscreen_ad": "药妆/防晒",
        "xigua_ad": "果蔬/冷饮",
        "bingxigua_ad": "冰品店",
        "sushi_ad": "寿司/日料",
        "shousi_ad": "寿司/日料",
        "shousi_guanggao": "寿司/日料",
        "shou_si": "寿司/日料",
        "shou_si_guang_gao": "寿司/日料",
        "bbq_ad": "BBQ/烧烤",
        "fish_chips_ad": "炸鱼薯条",
        "pizza_ad": "披萨",
        "asian_soup_ad": "叻沙/拉面/河粉",
        "green_bean_soup_ad": "绿豆沙/糖水",
        "herbal_tea_ad": "凉茶",
        "congee_ad": "砂锅粥",
        "crayfish_ad": "小龙虾",
        "dumplings_ad": "饺子",
        "tangyuan_ad": "汤圆",
        "bubble_tea_ad": "奶茶",
        "cold_noodles_ad": "冷面",
        "lamb_hotpot_ad": "铜锅涮肉/羊汤",
        "iron_pot_stew_ad": "铁锅炖",
        "hairy_crab_ad": "大闸蟹",
        "vietnamese_ad": "越南米纸卷/檬粉",
        "burger_ad": "炸鸡排/汉堡/塔可",
        "default": "咖啡馆",
    }
    label = category_labels.get(target_id, "门店")

    stores = get_recommended_stores(target_id, lat, lon, city_display, bbox, limit)

    msg = f"当前 {weather_cn}"
    if temp_c is not None:
        msg += f" {temp_c:.0f}°C"
    msg += f"，优先推送{label}，为您精选 {city_display} {len(stores)} 家"

    push_message = TARGET_TO_PUSH_MESSAGE.get(target_id or "")
    result = {
        "weather": weather,
        "temp_c": temp_c,
        "region": region,
        "target_id": target_id,
        "category_label": label,
        "stores": stores,
        "city": city_display,
        "message": msg,
        "push_message": push_message or None,
    }
    _REC_CACHE[cache_key] = (result, now)
    return result
