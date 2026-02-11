from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- 定义“法律条款” (Schema) ---
class Condition(BaseModel):
    type: Literal["weather", "time", "holiday"]
    operator: Literal["==", "in", "between"]
    value: str

class Action(BaseModel):
    type: Literal["switch_playlist"]
    target_id: str

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
