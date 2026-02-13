"""
广告库存管理服务：获取可用广告素材列表
对接 Media 服务与内置广告库，确保每个广告都有丰富的 tags/description 供 LLM 理解
"""
from typing import List, Optional

from app.schemas.decide import AdAsset


# 内置广告库：id -> (tags, description)，content_url 由 media_service 动态获取
AD_INVENTORY = [
    ("coffee_ad", ["热饮", "咖啡", "早餐", "Brunch"], "一杯冒着热气的拿铁，适合寒冷天气或早晨"),
    ("hot_drink_ad", ["热饮", "热可可", "热巧克力", "冬季"], "热巧克力/热可可，适合雨雪冷天"),
    ("sunscreen_ad", ["防晒", "防晒霜", "夏季", "晴天"], "防晒霜广告，适合晴天高温"),
    ("xigua_ad", ["西瓜", "水果", "夏季", "清凉"], "冰西瓜，适合炎热天气"),
    ("bingxigua_ad", ["冰品", "冰淇淋", "冷饮", "酷暑"], "冰淇淋冷饮，适合大热天"),
    ("sushi_ad", ["寿司", "日料", "轻食", "多云"], "寿司轻食，适合多云天心情提亮"),
    ("pizza_ad", ["披萨", "周末", "午后"], "披萨配啤酒，适合周日午后"),
    ("bbq_ad", ["烧烤", "BBQ", "周末", "晴天"], "烧烤广告，适合晴朗周末"),
    ("asian_soup_ad", ["热汤", "拉面", "叻沙", "雨天", "湿冷"], "亚洲热汤（拉面/叻沙），适合雨天湿冷"),
    ("green_bean_soup_ad", ["绿豆沙", "糖水", "祛湿", "华南", "湿热"], "绿豆沙糖水，适合华南湿热天"),
    ("herbal_tea_ad", ["凉茶", "王老吉", "祛湿", "华南"], "凉茶龟苓膏，适合夏日祛湿"),
    ("congee_ad", ["砂锅粥", "粥", "雨天", "华南"], "砂锅粥，适合下雨天"),
    ("crayfish_ad", ["小龙虾", "麻辣", "梅雨", "华东"], "小龙虾配啤酒，适合黄梅天"),
    ("dumplings_ad", ["饺子", "冬至", "北方"], "饺子，适合北方冬至"),
    ("tangyuan_ad", ["汤圆", "冬至", "南方"], "汤圆，适合南方冬至"),
    ("bubble_tea_ad", ["奶茶", "周五", "快乐"], "奶茶炸鸡，适合周五"),
    ("cold_noodles_ad", ["冷面", "撸串", "酷暑", "华北"], "冷面撸串，适合华北酷暑"),
    ("lamb_hotpot_ad", ["涮肉", "羊汤", "立秋", "贴秋膘"], "铜锅涮肉，适合立秋贴秋膘"),
    ("iron_pot_stew_ad", ["铁锅炖", "雪天", "华北"], "铁锅炖，适合雪天"),
    ("hairy_crab_ad", ["大闸蟹", "秋凉", "华东"], "大闸蟹，适合秋凉"),
    ("vietnamese_ad", ["越南", "米纸卷", "闷热"], "越南米纸卷，适合闷热天"),
    ("burger_ad", ["炸鸡排", "塔可", "周三"], "炸鸡排塔可，适合多云周三"),
    ("fish_chips_ad", ["炸鱼薯条", "澳式"], "炸鱼薯条，澳式经典"),
]


def fetch_available_ads(db=None) -> List[AdAsset]:
    """
    获取所有可用广告素材。
    1. 从内置广告库 + media_service 获取 content_url
    2. 返回 List[AdAsset]，每个广告都有 tags 和 description 供 LLM 理解
    """
    from app.services.media_service import get_image_url

    result = []
    for ad_id, tags, description in AD_INVENTORY:
        content_url = get_image_url(ad_id, db)
        result.append(AdAsset(
            id=ad_id,
            tags=tags,
            description=description,
            content_url=content_url or "",
        ))
    return result


def get_ad_by_id(ad_id: str, db=None) -> Optional[AdAsset]:
    """根据 ID 获取单个广告素材"""
    for item in AD_INVENTORY:
        if item[0] == ad_id:
            from app.services.media_service import get_image_url
            return AdAsset(
                id=item[0],
                tags=list(item[1]),
                description=item[2],
                content_url=get_image_url(ad_id, db) or "",
            )
    return None
