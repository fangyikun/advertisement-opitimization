"""门店 API"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from app.database import get_db_optional, USE_DATABASE
from app.models.store_model import Store
from app.schemas.store import StoreCreate, StoreUpdate

router = APIRouter()


@router.get("/cities", response_model=List[str])
async def list_cities():
    """城市列表（Adelaide 试点）"""
    return ["Adelaide"]


@router.get("/cities/{city}/stores")
async def list_stores_by_city(city: str, db: Optional[Session] = Depends(get_db_optional)):
    """某城市门店列表"""
    if not USE_DATABASE or db is None:
        return []
    stores = db.query(Store).filter(Store.city == city, Store.is_active == True).all()
    return [s.to_dict() for s in stores]


@router.get("/stores")
async def list_all_stores(db: Optional[Session] = Depends(get_db_optional)):
    """全部门店"""
    if not USE_DATABASE or db is None:
        return []
    stores = db.query(Store).all()
    return [s.to_dict() for s in stores]


@router.get("/stores/{store_id}")
async def get_store(store_id: str, db: Optional[Session] = Depends(get_db_optional)):
    """门店详情"""
    if not USE_DATABASE or db is None:
        raise HTTPException(status_code=404, detail="门店不存在")
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    return store.to_dict()


@router.post("/stores")
async def create_store(store: StoreCreate, db: Optional[Session] = Depends(get_db_optional)):
    """创建门店"""
    if not USE_DATABASE or db is None:
        raise HTTPException(status_code=503, detail="数据库不可用")
    store_id = f"store_{uuid.uuid4().hex[:8]}"
    db_store = Store(
        id=store_id,
        name=store.name,
        city=store.city,
        latitude=store.latitude,
        longitude=store.longitude,
        sign_id=store.sign_id or f"sign_{store_id}",
        opening_hours=store.opening_hours,
        timezone=store.timezone,
        is_active=store.is_active,
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    print(f"🏪 [API] 创建门店: {store_id}")
    return db_store.to_dict()


@router.patch("/stores/{store_id}")
async def update_store(store_id: str, update: StoreUpdate, db: Optional[Session] = Depends(get_db_optional)):
    """更新门店"""
    if not USE_DATABASE or db is None:
        raise HTTPException(status_code=503, detail="数据库不可用")
    db_store = db.query(Store).filter(Store.id == store_id).first()
    if not db_store:
        raise HTTPException(status_code=404, detail="门店不存在")
    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(db_store, k, v)
    db.commit()
    db.refresh(db_store)
    print(f"🏪 [API] 更新门店: {store_id}")
    return db_store.to_dict()


@router.delete("/stores/{store_id}")
async def delete_store(store_id: str, db: Optional[Session] = Depends(get_db_optional)):
    """删除门店（软删除：is_active=False）"""
    if not USE_DATABASE or db is None:
        raise HTTPException(status_code=503, detail="数据库不可用")
    db_store = db.query(Store).filter(Store.id == store_id).first()
    if not db_store:
        raise HTTPException(status_code=404, detail="门店不存在")
    db_store.is_active = False
    db.commit()
    print(f"🏪 [API] 停用门店: {store_id}")
    return {"status": "success", "store_id": store_id}


@router.get("/recommendations")
async def get_recommendations(
    limit: int = 10,
    city: str = "Adelaide",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    target_id: Optional[str] = None,
):
    """
    根据当前天气+规则，获取应推送的门店推荐
    支持：1) city 城市名  2) lat,lon 用户当前位置  3) target_id 指定品类（如 bubble_tea_ad）
    """
    from app.services.recommendation_service import get_current_recommended_stores
    result = await get_current_recommended_stores(
        limit=min(limit, 20),
        city=city.strip(),
        lat=lat,
        lon=lon,
        target_id=target_id.strip() if target_id else None,
    )
    return result


@router.get("/signs/{sign_id}/store")
async def get_store_by_sign(sign_id: str, db: Optional[Session] = Depends(get_db_optional)):
    """根据 sign_id 获取门店"""
    if not USE_DATABASE or db is None:
        raise HTTPException(status_code=404, detail="门店不存在")
    store = db.query(Store).filter(Store.sign_id == sign_id, Store.is_active == True).first()
    if not store:
        raise HTTPException(status_code=404, detail="未找到该屏幕对应的门店")
    return store.to_dict()
