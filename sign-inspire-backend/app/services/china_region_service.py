"""
中国地域细分：华南/华东/华北
南甜北咸东辣西酸 - 不同地域对同一天气的饮食反应不同
"""
from typing import Optional
from datetime import date

# 城市/省份 -> 中国子区域
# south_china: 华南/大湾区 - 粤港琼桂，湿热、祛湿、凉茶
# east_china: 华东/江浙沪 - 包邮区，四季分明、时令精致
# north_china: 华北/东北 - 京津冀晋东北，干燥寒冷、面食高热
CITY_TO_CHINA_SUBREGION: dict[str, str] = {
    # 华南
    "guangzhou": "south_china", "shenzhen": "south_china", "hong kong": "south_china",
    "zhuhai": "south_china", "foshan": "south_china", "dongguan": "south_china",
    "zhongshan": "south_china", "huizhou": "south_china", "jiangmen": "south_china",
    "haikou": "south_china", "sanya": "south_china", "nanning": "south_china",
    "macau": "south_china", "macao": "south_china",
    # 华东/江浙沪
    "shanghai": "east_china", "hangzhou": "east_china", "suzhou": "east_china",
    "nanjing": "east_china", "ningbo": "east_china", "wuxi": "east_china",
    "wenzhou": "east_china", "jiaxing": "east_china", "huzhou": "east_china",
    "shaoxing": "east_china", "jinhua": "east_china", "taizhou": "east_china",
    "hefei": "east_china", "wuhu": "east_china",
    # 华北/东北
    "beijing": "north_china", "tianjin": "north_china", "shijiazhuang": "north_china",
    "taiyuan": "north_china", "dalian": "north_china", "shenyang": "north_china",
    "changchun": "north_china", "harbin": "north_china", "jinan": "north_china",
    "qingdao": "north_china", "zhengzhou": "north_china", "xi'an": "north_china",
    "xian": "north_china", "lanzhou": "north_china",
    # 西南（川渝偏辣，暂归 east_china 或单独；这里归 east 因规则可复用）
    "chengdu": "east_china", "chongqing": "east_china",
}

# 纬度粗略分界：< 26 华南，26-34 华东，> 34 华北
LAT_SOUTH = 26  # 华南上限
LAT_EAST = 34   # 华北下限


def get_china_subregion(city: Optional[str], state: Optional[str], lat: Optional[float]) -> Optional[str]:
    """
    返回中国子区域：south_china / east_china / north_china
    仅当国家为中国时有效，否则返回 None
    """
    key = (city or "").strip().lower().replace(" ", "")
    if key and key in CITY_TO_CHINA_SUBREGION:
        return CITY_TO_CHINA_SUBREGION[key]
    if state:
        sk = state.strip().lower()
        if "广东" in state or "广东" in sk or "guangdong" in sk:
            return "south_china"
        if "香港" in state or "香港" in sk or "hong kong" in sk:
            return "south_china"
        if "海南" in state or "广西" in state:
            return "south_china"
        if "上海" in state or "浙江" in state or "江苏" in state or "安徽" in state:
            return "east_china"
        if "北京" in state or "天津" in state or "河北" in state or "山西" in state:
            return "north_china"
        if "辽宁" in state or "吉林" in state or "黑龙江" in state or "山东" in state:
            return "north_china"
    if lat is not None:
        if lat < LAT_SOUTH:
            return "south_china"
        if lat > LAT_EAST:
            return "north_china"
        return "east_china"
    return None
