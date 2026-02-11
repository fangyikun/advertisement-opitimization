from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.rule import RuleCreate, RuleUpdate
from app.services.llm_service import parse_rule_with_langchain
from app.services import scheduler_service
from app.database import get_db, get_db_optional, USE_DATABASE
from app.models.rule_model import Rule
from app.models.rule_storage import MOCK_DB
import uuid
import asyncio

router = APIRouter()

@router.post("/stores/{store_id}/rules:parse", response_model=RuleCreate)
async def parse_rule(store_id: str, text: str, db: Optional[Session] = Depends(get_db_optional)):
    """
    接收自然语言 -> 使用动态词汇表解析（新词自动创建）-> 返回 JSON 规则
    """
    try:
        rule_result = await parse_rule_with_langchain(text, store_id, db)
        return rule_result
    except Exception as e:
        print(f"❌ 规则解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"规则解析失败: {str(e)}")

@router.post("/stores/{store_id}/rules")
async def create_rule(store_id: str, rule: RuleCreate, db: Optional[Session] = Depends(get_db_optional)):
    """
    创建规则：生成随机ID，存入数据库或内存，返回保存后的对象
    """
    # 生成随机ID
    rule_id = str(uuid.uuid4())
    
    # 将规则转换为字典
    rule_dict = rule.model_dump()
    rule_dict["id"] = rule_id
    rule_dict["store_id"] = store_id
    
    if USE_DATABASE and db is not None:
        try:
            # 检查是否已存在相同的规则（根据名称和条件判断）
            existing_rules = db.query(Rule).filter(
                Rule.store_id == store_id,
                Rule.name == rule.name
            ).all()
            
            # 检查条件是否相同
            conditions_dict = [c.model_dump() if hasattr(c, 'model_dump') else c for c in rule.conditions]
            action_dict = rule.action.model_dump() if hasattr(rule.action, 'model_dump') else rule.action
            
            for existing_rule in existing_rules:
                existing_conditions = existing_rule.conditions
                existing_action = existing_rule.action
                
                # 比较条件（转换为字典后比较）
                if (existing_conditions == conditions_dict and 
                    existing_action == action_dict):
                    print(f"⚠️ 规则已存在，跳过保存: {rule.name}")
                    return existing_rule.to_dict()
            
            # 将 Pydantic 模型转换为字典（用于 JSON 序列化）
            conditions_json = [c.model_dump() if hasattr(c, 'model_dump') else c for c in rule.conditions]
            action_json = rule.action.model_dump() if hasattr(rule.action, 'model_dump') else rule.action
            
            # 保存到数据库
            db_rule = Rule(
                id=rule_id,
                store_id=store_id,
                name=rule.name,
                priority=rule.priority,
                conditions=conditions_json,  # 使用字典而不是 Pydantic 对象
                action=action_json  # 使用字典而不是 Pydantic 对象
            )
            db.add(db_rule)
            db.commit()
            db.refresh(db_rule)
            rule_dict = db_rule.to_dict()
            print(f"💾 [DB] 保存规则到数据库: {rule_dict}")
            
            rule_count = db.query(Rule).filter(Rule.store_id == store_id).count()
            print(f"📊 [DB] 门店 {store_id} 共有 {rule_count} 条规则")
            
            # 保存后立即触发规则检查，无需等待后台任务
            asyncio.create_task(scheduler_service.check_rules_job())
            print("⚡ [API] 已触发立即规则检查")
        except Exception as e:
            import traceback
            print(f"⚠️ 数据库保存失败，使用内存数据库: {e}")
            print(traceback.format_exc())
            # 检查内存数据库中是否已存在
            existing_in_memory = [r for r in MOCK_DB 
                                 if r.get("store_id") == store_id 
                                 and r.get("name") == rule.name
                                 and r.get("conditions") == rule_dict.get("conditions")
                                 and r.get("action") == rule_dict.get("action")]
            if existing_in_memory:
                print(f"⚠️ 内存数据库中规则已存在，跳过保存")
                return existing_in_memory[0]
            MOCK_DB.append(rule_dict)
            print(f"💾 [Memory] 保存规则到内存: {rule_dict}")
            print(f"📊 [Memory] 当前 MOCK_DB 中共有 {len(MOCK_DB)} 条规则")
            
            # 保存后立即触发规则检查
            asyncio.create_task(scheduler_service.check_rules_job())
            print("⚡ [API] 已触发立即规则检查")
    else:
        # 降级到内存数据库
        # 检查是否已存在相同的规则
        existing_in_memory = [r for r in MOCK_DB 
                             if r.get("store_id") == store_id 
                             and r.get("name") == rule.name
                             and r.get("conditions") == rule_dict.get("conditions")
                             and r.get("action") == rule_dict.get("action")]
        if existing_in_memory:
            print(f"⚠️ 内存数据库中规则已存在，跳过保存")
            return existing_in_memory[0]
        
        MOCK_DB.append(rule_dict)
        print(f"💾 [Memory] 保存规则到内存: {rule_dict}")
        print(f"📊 [Memory] 当前 MOCK_DB 中共有 {len(MOCK_DB)} 条规则")
        
        # 保存后立即触发规则检查
        asyncio.create_task(scheduler_service.check_rules_job())
        print("⚡ [API] 已触发立即规则检查")
    
    return rule_dict

@router.patch("/stores/{store_id}/rules/{rule_id}")
async def update_rule(
    store_id: str,
    rule_id: str,
    update: RuleUpdate,
    db: Optional[Session] = Depends(get_db_optional),
):
    """
    更新规则（支持部分更新，如修改优先级）
    """
    if USE_DATABASE and db is not None:
        try:
            db_rule = db.query(Rule).filter(
                Rule.id == rule_id,
                Rule.store_id == store_id,
            ).first()
            if not db_rule:
                raise HTTPException(status_code=404, detail="规则不存在")
            update_data = update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(db_rule, key):
                    setattr(db_rule, key, value)
            db.commit()
            db.refresh(db_rule)
            print(f"✏️ [DB] 更新规则: {rule_id}, 更新内容: {update_data}")
            asyncio.create_task(scheduler_service.check_rules_job())
            return db_rule.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ 数据库更新失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 内存数据库
    idx = next((i for i, r in enumerate(MOCK_DB) if r.get("id") == rule_id and r.get("store_id") == store_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in MOCK_DB[idx]:
            MOCK_DB[idx][key] = value
    print(f"✏️ [Memory] 更新规则: {rule_id}")
    asyncio.create_task(scheduler_service.check_rules_job())
    return MOCK_DB[idx]


@router.post("/stores/{store_id}/rules:reset")
async def reset_rules(
    store_id: str,
    db: Optional[Session] = Depends(get_db_optional),
):
    """
    清空规则并恢复为默认全球规则种子（澳洲+中国城市）
    """
    if USE_DATABASE and db is not None:
        try:
            deleted = db.query(Rule).filter(Rule.store_id == store_id).delete()
            db.commit()
            from app.database import _seed_rules_if_empty, engine
            if engine:
                _seed_rules_if_empty(engine)
            print(f"🔄 [DB] 已重置规则，删除 {deleted} 条，并重新写入默认种子")
            asyncio.create_task(scheduler_service.check_rules_job())
            return {"status": "success", "message": "规则已恢复为默认"}
        except Exception as e:
            import traceback
            print(f"⚠️ 重置规则失败: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))

    # 内存模式：清空后写入默认种子
    before = len(MOCK_DB)
    for i in range(len(MOCK_DB) - 1, -1, -1):
        if MOCK_DB[i].get("store_id") == store_id:
            del MOCK_DB[i]
    from app.database import _seed_rules_to_mock_db
    _seed_rules_to_mock_db(store_id)
    print(f"🔄 [Memory] 已重置规则，清空 {before - len(MOCK_DB)} 条并写入默认种子")
    asyncio.create_task(scheduler_service.check_rules_job())
    return {"status": "success", "message": "规则已恢复为默认"}


@router.delete("/stores/{store_id}/rules/{rule_id}")
async def delete_rule(
    store_id: str,
    rule_id: str,
    db: Optional[Session] = Depends(get_db_optional),
):
    """
    删除规则
    """
    if USE_DATABASE and db is not None:
        try:
            db_rule = db.query(Rule).filter(
                Rule.id == rule_id,
                Rule.store_id == store_id,
            ).first()
            if not db_rule:
                raise HTTPException(status_code=404, detail="规则不存在")
            db.delete(db_rule)
            db.commit()
            print(f"🗑️ [DB] 删除规则: {rule_id}")
            asyncio.create_task(scheduler_service.check_rules_job())
            return {"status": "success", "deleted_id": rule_id}
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ 数据库删除失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 内存数据库
    idx = next((i for i, r in enumerate(MOCK_DB) if r.get("id") == rule_id and r.get("store_id") == store_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    del MOCK_DB[idx]
    print(f"🗑️ [Memory] 删除规则: {rule_id}")
    asyncio.create_task(scheduler_service.check_rules_job())
    return {"status": "success", "deleted_id": rule_id}


@router.get("/stores/{store_id}/rules")
async def get_rules(
    store_id: str,
    city: Optional[str] = None,
    db: Optional[Session] = Depends(get_db_optional),
):
    """
    获取指定门店的所有规则列表
    city: 可选，传入时根据该城市天气+文化圈计算每条规则是否适用当前上下文，返回 matches_current
    """
    raw_rules = []
    if USE_DATABASE and db is not None:
        try:
            rules = db.query(Rule).filter(Rule.store_id == store_id).all()
            raw_rules = [rule.to_dict() for rule in rules]
        except Exception as e:
            print(f"⚠️ 数据库查询失败，使用内存数据库: {e}")
            raw_rules = [r for r in MOCK_DB if r.get("store_id") == store_id]
    else:
        raw_rules = [r for r in MOCK_DB if r.get("store_id") == store_id]

    if not city or not raw_rules:
        return raw_rules if not city else {"rules": raw_rules, "context": None}

    # 根据 city 计算每条规则是否匹配当前上下文
    try:
        from app.services.geocoding_service import geocode_city_sync
        from app.services.scheduler_service import get_weather_context
        from app.services.region_service import get_region_from_country
        from app.services.matching_engine import _conditions_match
        geo = geocode_city_sync(city)
        if not geo:
            return raw_rules
        lat, lon = geo.get("lat"), geo.get("lon")
        country_code = geo.get("country_code")
        region = get_region_from_country(country_code)
        city_display = geo.get("city", city)
        china_subregion = geo.get("china_subregion")
        if not china_subregion and country_code in ("CN", "HK", "MO", "TW"):
            from app.services.china_region_service import get_china_subregion
            china_subregion = get_china_subregion(city_display, geo.get("state"), lat)
        from app.services.solar_term_service import get_active_solar_terms
        from datetime import date
        solar_terms = get_active_solar_terms(date.today()) if country_code in ("CN", "HK", "MO", "TW") else []

        tz_map = {"AU": "Australia/Adelaide", "CN": "Asia/Shanghai", "JP": "Asia/Tokyo", "GB": "Europe/London", "US": "America/New_York", "SG": "Asia/Singapore"}
        tz = tz_map.get(country_code or "", "Australia/Adelaide")
        ctx = await get_weather_context(lat, lon, timezone=tz) if lat is not None else None
        weather = ctx.get("weather", "sunny") if ctx else "sunny"
        temp_c = ctx.get("temp_c") if ctx else None
        hour = ctx.get("hour") if ctx else None
        weekday = ctx.get("weekday") if ctx else None
        season = ctx.get("season") if ctx else None

        result = []
        for r in raw_rules:
            d = dict(r)
            conds = r.get("conditions") or []
            d["matches_current"] = _conditions_match(conds, weather, city_display or city, temp_c=temp_c, region=region, hour=hour, weekday=weekday, china_subregion=china_subregion, solar_terms=solar_terms)
            result.append(d)
        return {"rules": result, "context": {"weather": weather, "temp_c": temp_c, "region": region, "city": city_display or city, "hour": hour, "weekday": weekday, "season": season, "china_subregion": china_subregion, "solar_terms": solar_terms}}
    except Exception as e:
        print(f"⚠️ 计算 matches_current 失败: {e}")
        return raw_rules

@router.get("/debug/current-state")
async def debug_current_state(db: Optional[Session] = Depends(get_db_optional)):
    """
    调试接口：查看当前状态
    """
    if USE_DATABASE and db is not None:
        try:
            total_rules = db.query(Rule).count()
            store_001_rules = db.query(Rule).filter(Rule.store_id == "store_001").all()
            all_rules = db.query(Rule).all()
            return {
                "current_playlist": scheduler_service.CURRENT_PLAYLIST,
                "current_weather": scheduler_service.CURRENT_CONTEXT.get("weather"),
                "weather_updated_at": scheduler_service.CURRENT_CONTEXT.get("updated_at"),
                "database_mode": "MySQL",
                "total_rules": total_rules,
                "rules": [rule.to_dict() for rule in all_rules],
                "store_001_rules": [rule.to_dict() for rule in store_001_rules]
            }
        except Exception as e:
            print(f"⚠️ 数据库查询失败: {e}")
            return {
                "current_playlist": scheduler_service.CURRENT_PLAYLIST,
                "current_weather": scheduler_service.CURRENT_CONTEXT.get("weather"),
                "weather_updated_at": scheduler_service.CURRENT_CONTEXT.get("updated_at"),
                "database_mode": "Memory (fallback)",
                "total_rules": len(MOCK_DB),
                "rules": MOCK_DB,
                "store_001_rules": [rule for rule in MOCK_DB if rule.get("store_id") == "store_001"]
            }
    else:
        return {
            "current_playlist": scheduler_service.CURRENT_PLAYLIST,
            "current_weather": scheduler_service.CURRENT_CONTEXT.get("weather"),
            "weather_updated_at": scheduler_service.CURRENT_CONTEXT.get("updated_at"),
            "database_mode": "Memory",
            "total_rules": len(MOCK_DB),
            "rules": MOCK_DB,
            "store_001_rules": [rule for rule in MOCK_DB if rule.get("store_id") == "store_001"]
        }

@router.post("/debug/add-test-rule")
async def add_test_rule(db: Optional[Session] = Depends(get_db_optional)):
    """
    调试接口：添加一个测试规则（用于快速测试）
    """
    rule_dict = {
        "id": str(uuid.uuid4()),
        "store_id": "store_001",
        "name": "播放咖啡广告 (多云)",
        "priority": 1,
        "conditions": [
            {
                "type": "weather",
                "operator": "==",
                "value": "多云"
            }
        ],
        "action": {
            "type": "switch_playlist",
            "target_id": "coffee_ads"
        }
    }
    
    if USE_DATABASE and db is not None:
        try:
            test_rule = Rule(**rule_dict)
            db.add(test_rule)
            db.commit()
            db.refresh(test_rule)
            rule_dict = test_rule.to_dict()
            print(f"🧪 [DEBUG] 添加测试规则到数据库: {rule_dict}")
            rule_count = db.query(Rule).count()
            print(f"📊 [DB] 数据库中共有 {rule_count} 条规则")
        except Exception as e:
            print(f"⚠️ 数据库保存失败，使用内存数据库: {e}")
            MOCK_DB.append(rule_dict)
            print(f"🧪 [DEBUG] 添加测试规则到内存: {rule_dict}")
            print(f"📊 [Memory] 当前 MOCK_DB 中共有 {len(MOCK_DB)} 条规则")
    else:
        MOCK_DB.append(rule_dict)
        print(f"🧪 [DEBUG] 添加测试规则到内存: {rule_dict}")
        print(f"📊 [Memory] 当前 MOCK_DB 中共有 {len(MOCK_DB)} 条规则")
    
    return {"status": "success", "rule": rule_dict}

@router.get("/weather")
async def get_weather():
    """
    获取当前天气状态
    """
    return scheduler_service.CURRENT_CONTEXT

@router.get("/stores/{store_id}/current-content")
async def get_current_content(store_id: str):
    """
    获取指定门店当前应播放的内容（支持多门店）
    """
    by_store = getattr(scheduler_service, "CURRENT_PLAYLIST_BY_STORE", {})
    content = by_store.get(store_id) if by_store else scheduler_service.CURRENT_PLAYLIST
    if content is None:
        content = scheduler_service.CURRENT_PLAYLIST if store_id == "store_001" else "default"
    print(f"📡 [API] current-content store={store_id} -> {content}")
    return {"content": content}


@router.get("/signs/{sign_id}/current-content")
async def get_current_content_by_sign(sign_id: str, db: Optional[Session] = Depends(get_db_optional)):
    """
    根据屏幕 ID 获取当前应播放的内容（App/Player 用）
    """
    if USE_DATABASE and db is not None:
        from app.models.store_model import Store
        store = db.query(Store).filter(Store.sign_id == sign_id, Store.is_active == True).first()
        if store:
            by_store = getattr(scheduler_service, "CURRENT_PLAYLIST_BY_STORE", {})
            content = by_store.get(store.id) or scheduler_service.CURRENT_PLAYLIST
            return {"content": content, "store_id": store.id}
    if sign_id == "sign_001":
        return {"content": scheduler_service.CURRENT_PLAYLIST, "store_id": "store_001"}
    return {"content": "default", "store_id": None}


@router.get("/stores/{store_id}/media/{target_id}")
async def get_media_for_target(store_id: str, target_id: str, db: Optional[Session] = Depends(get_db_optional)):
    """
    根据 target_id 获取对应图片 URL。
    自动从 Unsplash 搜索相关图片并缓存，无需手动维护 IMAGE_MAP。
    若未配置 UNSPLASH_ACCESS_KEY，则使用 Picsum 占位图。
    """
    from app.services.media_service import get_image_url
    url = get_image_url(target_id, db)
    return {"url": url}

@router.post("/stores/{store_id}/check-rules")
async def trigger_check_rules(store_id: str):
    """
    手动触发规则检查（用于测试和调试）
    """
    print(f"🔧 [API] 手动触发规则检查，当前 CURRENT_PLAYLIST = '{scheduler_service.CURRENT_PLAYLIST}'")
    
    # 执行规则检查
    await scheduler_service.check_rules_job()
    
    # 直接从模块读取最新值（避免导入缓存问题）
    result_playlist = scheduler_service.CURRENT_PLAYLIST
    result_weather = scheduler_service.CURRENT_CONTEXT.get("weather")
    
    print(f"🔧 [API] 规则检查完成，当前 CURRENT_PLAYLIST = '{result_playlist}'")
    return {
        "status": "success",
        "current_playlist": result_playlist,
        "current_weather": result_weather
    }