import os

# 这是我们要生成的目录结构，完全对应之前的架构设计
structure = {
    "sign-inspire-backend": {  # 项目根目录
        "app": {
            "__init__.py": "",
            "main.py": """from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1.endpoints import rules

# 1. 模拟调度器生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⏰ [System] 智能排期调度器启动中...")
    # 这里未来会启动 APScheduler
    yield
    print("⏰ [System] 调度器关闭...")

app = FastAPI(lifespan=lifespan, title="Sign Inspire Backend")

# 2. 注册路由
app.include_router(rules.router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "ok", "module": "smart_scheduler"}
""",
            "api": {
                "__init__.py": "",
                "v1": {
                    "__init__.py": "",
                    "endpoints": {
                        "__init__.py": "",
                        "rules.py": """from fastapi import APIRouter, HTTPException
from app.schemas.rule import RuleCreate
# from app.services.llm_service import parse_rule_with_langchain

router = APIRouter()

@router.post("/stores/{store_id}/rules:parse")
async def parse_rule(store_id: str, text: str):
    # TODO: 这里接入 LangChain
    return {"msg": f"正在为门店 {store_id} 解析规则: {text}", "mock_result": "JSON结构待生成"}

@router.post("/stores/{store_id}/rules")
async def create_rule(store_id: str, rule: RuleCreate):
    # TODO: 存入数据库
    return {"status": "success", "rule_name": rule.name}
"""
                    }
                }
            },
            "schemas": {
                "__init__.py": "",
                "rule.py": """from pydantic import BaseModel, Field
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
"""
            },
            "services": {
                "__init__.py": "",
                "llm_service.py": """# LangChain 逻辑 (AI 翻译官)
from langchain_openai import ChatOpenAI
# 这里以后写 prompt template
""",
                "scheduler_service.py": """# APScheduler 逻辑 (执行官)
async def check_rules_job():
    print("Checking rules...")
"""
            }
        },
        ".env": "OPENAI_API_KEY=你的Key填在这里",
        "requirements.txt": """fastapi[standard]
uvicorn
apscheduler
langchain
langchain-openai
pydantic
"""
    }
}

def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)
        
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            print(f"📁 创建目录: {path}")
            create_structure(path, content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"📄 创建文件: {path}")

if __name__ == "__main__":
    print("🚀 开始自动生成 Sign Inspire 后端框架...")
    create_structure(".", structure)
    print("\n✅ 生成完成！")