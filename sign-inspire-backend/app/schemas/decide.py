"""
AI 驱动广告牌推荐 - 核心数据结构
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AdAsset(BaseModel):
    """广告素材"""
    id: str = Field(..., description="唯一标识")
    tags: List[str] = Field(default_factory=list, description="标签，如热饮、咖啡、促销、早餐")
    description: str = Field(default="", description="描述，便于 LLM 理解")
    content_url: str = Field(default="", description="图片/视频地址")


class EnvironmentContext(BaseModel):
    """环境上下文"""
    location: str = Field(default="", description="地点，如 Adelaide")
    weather_condition: str = Field(default="", description="天气：Rainy, Sunny, Cloudy 等")
    temperature: float = Field(default=0.0, description="温度（摄氏度）")
    local_time: datetime = Field(default_factory=datetime.now, description="当地时间")


class UserRule(BaseModel):
    """用户策略（自然语言）"""
    natural_language_instruction: str = Field(
        ...,
        description="例如：如果下雨或者是早上，就给我推热咖啡；如果是大热天，就推冰可乐。"
    )


class DecideRequest(BaseModel):
    """决策接口请求体"""
    location_id: str = Field(..., description="门店ID或城市名，如 store_001 或 Adelaide")
    user_rule: UserRule = Field(..., description="用户自然语言规则")
    device_id: Optional[str] = Field(default=None, description="设备ID，传入时决策后自动推送")


class DecideResponse(BaseModel):
    """决策接口响应"""
    selected_ad_id: str = Field(..., description="选中的广告 ID")
    reason: str = Field(..., description="选择理由")
    ad_content: Optional[AdAsset] = Field(default=None, description="完整的广告素材")
    push_success: Optional[bool] = Field(default=None, description="若请求了推送，表示是否成功")
