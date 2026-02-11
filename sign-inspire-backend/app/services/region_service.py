"""
文化圈层服务：国家/地区 -> Region_Cluster
用于全球天气+饮食推荐规则，不同文化圈 Comfort Food 不同
参考：Western(欧澳美)、East_Asia(中日韩)、Tropical(东南亚南亚)、UK(英伦)
"""
from typing import Optional

# 国家/地区 ISO 代码 -> 文化圈层
# western: 北美、西欧、澳洲 - 奶酪/面包/肉类主导
# east_asia: 中日韩 - 米饭/面条/热汤主导
# tropical: 东南亚、南亚 - 香料/酸辣/热食主导
# uk: 英伦 - Tea & Buns 特供
COUNTRY_TO_REGION: dict[str, str] = {
    # Western
    "US": "western", "CA": "western", "AU": "western", "NZ": "western",
    "DE": "western", "FR": "western", "IT": "western", "ES": "western",
    "NL": "western", "BE": "western", "AT": "western", "CH": "western",
    "PL": "western", "SE": "western", "NO": "western", "FI": "western",
    "PT": "western", "GR": "western", "IE": "western",  # IE 也可算 UK 相近
    # UK 单独
    "GB": "uk", "UK": "uk",
    # East Asia
    "CN": "east_asia", "JP": "east_asia", "KR": "east_asia",
    "TW": "east_asia", "HK": "east_asia", "MO": "east_asia",
    # Tropical / SE Asia / South Asia
    "SG": "tropical", "MY": "tropical", "TH": "tropical", "VN": "tropical",
    "ID": "tropical", "PH": "tropical", "MM": "tropical", "KH": "tropical",
    "LA": "tropical", "IN": "tropical", "PK": "tropical", "BD": "tropical",
    "LK": "tropical", "NP": "tropical",
    # 其他：中东、南美、非洲等归为 western 作为通用回退
}
DEFAULT_REGION = "western"


def get_region_from_country(country_code: Optional[str]) -> str:
    """
    根据国家代码返回文化圈层
    country_code: ISO 3166-1 alpha-2 如 "AU", "JP"
    """
    if not country_code:
        return DEFAULT_REGION
    key = str(country_code).strip().upper()
    return COUNTRY_TO_REGION.get(key, DEFAULT_REGION)
