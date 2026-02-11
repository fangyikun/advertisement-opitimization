from fastapi import APIRouter, HTTPException
from app.schemas.rule import RuleCreate
from app.services.llm_service import parse_rule_with_langchain # <--- 导入 Service
from app.services import scheduler_service  # 导入整个模块，而不是直接导入变量
from app.models.rule_storage import MOCK_DB
import uuid

router = APIRouter()

@router.post("/stores/{store_id}/rules:parse", response_model=RuleCreate)
async def parse_rule(store_id: str, text: str):
    """
    接收自然语言 -> 调用 LangChain -> 返回 JSON 规则
    """
    try:
        # 调用刚才写的真实 AI 服务
        rule_result = await parse_rule_with_langchain(text, store_id)
        return rule_result
    except Exception as e:
        print(f"❌ AI 解析失败: {e}")
        # 如果出错，返回 500 给前端
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stores/{store_id}/rules")
async def create_rule(store_id: str, rule: RuleCreate):
    """
    创建规则：生成随机ID，存入MOCK_DB，返回保存后的对象
    """
    # 生成随机ID
    rule_id = str(uuid.uuid4())
    
    # 将规则转换为字典并添加ID和store_id
    rule_dict = rule.model_dump()
    rule_dict["id"] = rule_id
    rule_dict["store_id"] = store_id
    
    # 存入MOCK_DB
    MOCK_DB.append(rule_dict)
    
    print(f"💾 [DB] 保存规则: {rule_dict}")
    print(f"📊 [DB] 当前 MOCK_DB 中共有 {len(MOCK_DB)} 条规则")
    return rule_dict

@router.get("/stores/{store_id}/rules")
async def get_rules(store_id: str):
    """
    获取指定门店的所有规则列表
    """
    # 过滤出该门店的规则
    store_rules = [rule for rule in MOCK_DB if rule.get("store_id") == store_id]
    return store_rules

@router.get("/debug/current-state")
async def debug_current_state():
    """
    调试接口：查看当前状态
    """
    return {
        "current_playlist": scheduler_service.CURRENT_PLAYLIST,
        "current_weather": scheduler_service.CURRENT_CONTEXT.get("weather"),
        "weather_updated_at": scheduler_service.CURRENT_CONTEXT.get("updated_at"),
        "total_rules": len(MOCK_DB),
        "rules": MOCK_DB,
        "store_001_rules": [rule for rule in MOCK_DB if rule.get("store_id") == "store_001"]
    }

@router.post("/debug/add-test-rule")
async def add_test_rule():
    """
    调试接口：添加一个测试规则（用于快速测试）
    """
    test_rule = {
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
    MOCK_DB.append(test_rule)
    print(f"🧪 [DEBUG] 添加测试规则: {test_rule}")
    print(f"📊 [DB] 当前 MOCK_DB 中共有 {len(MOCK_DB)} 条规则")
    return {"status": "success", "rule": test_rule}

@router.get("/weather")
async def get_weather():
    """
    获取当前天气状态
    """
    return scheduler_service.CURRENT_CONTEXT

@router.get("/stores/{store_id}/current-content")
async def get_current_content(store_id: str):
    """
    获取当前播放的内容
    """
    # 直接从模块读取最新值
    current_playlist = scheduler_service.CURRENT_PLAYLIST
    print(f"📡 [API] 获取当前内容请求，CURRENT_PLAYLIST = '{current_playlist}'")
    return {"content": current_playlist}

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