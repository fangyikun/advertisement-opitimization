"""门店 Schema"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class StoreCreate(BaseModel):
    name: str
    city: str = "Adelaide"
    latitude: float = -34.9285
    longitude: float = 138.6007
    sign_id: Optional[str] = None
    opening_hours: Optional[Dict[str, str]] = None
    timezone: str = "Australia/Adelaide"
    is_active: bool = True


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sign_id: Optional[str] = None
    opening_hours: Optional[Dict[str, str]] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
