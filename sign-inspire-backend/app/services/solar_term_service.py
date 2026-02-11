"""
节气/时令服务：中国餐饮推荐灵魂变量
冬至、入伏、立秋、腊八 等 - 日历权重高于天气
"""
from datetime import date
from typing import Optional, List

# 节气名称 -> 公历日期范围 (月, 起始日, 结束日)，近似值
# 实际节气需天文计算，此处用常见公历范围
SOLAR_TERM_RANGES: dict[str, List[tuple]] = {
    "冬至": [(12, 20, 24)],          # 约 12/21-22
    "入伏": [(7, 11, 25)],           # 头伏通常 7/12 前后
    "立秋": [(8, 5, 12)],           # 约 8/7-8
    "腊八": [(1, 8, 28)],            # 腊八在 1 月，范围放宽
    "清明": [(4, 3, 6)],            # 约 4/4-5，青团时令
    "立夏": [(5, 3, 8)],
}


def is_solar_term(today: date, term: str) -> bool:
    """判断今日是否在指定节气范围内"""
    ranges = SOLAR_TERM_RANGES.get(term)
    if not ranges:
        return False
    m, d = today.month, today.day
    for (month, start, end) in ranges:
        if m == month and start <= d <= end:
            return True
    return False


def get_active_solar_terms(today: Optional[date] = None) -> List[str]:
    """返回今日匹配的所有节气"""
    d = today or date.today()
    return [t for t in SOLAR_TERM_RANGES if is_solar_term(d, t)]
