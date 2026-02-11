from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- 定义“法律条款” (Schema) ---
class Condition(BaseModel):
    type: Literal["weather", "time", "holiday", "temp", "region", "city", "day", "china_region", "solar_term"]
    operator: Literal["==", "in", "between"]
    value: str  # china_region: south_china|east_china|north_china | solar_term: 冬至|入伏|立秋|腊八

class Action(BaseModel):
    type: Literal["switch_playlist"]
    target_id: str
    message: Optional[str] = None  # 推送文案，前端展示用

class RuleCreate(BaseModel):
    name: str
    priority: int = 1
    conditions: List[Condition]
    action: Action


class RuleUpdate(BaseModel):
    """部分更新（PATCH）用，所有字段可选"""
    name: Optional[str] = None
    priority: Optional[int] = None
    conditions: Optional[List[Condition]] = None
    action: Optional[Action] = None
