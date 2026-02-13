# backend/app/main.py
import sys
from dotenv import load_dotenv
load_dotenv()
# Windows 控制台编码兼容
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <--- 新增这行
from contextlib import asynccontextmanager
import asyncio
from app.api.v1.endpoints import rules, stores, decide
from app.services.scheduler_service import check_rules_job

# 后台任务控制
background_task = None

async def weather_check_loop():
    """
    后台任务：定期检查天气并更新规则
    """
    # 等待一段时间，避免与启动时的检查冲突
    await asyncio.sleep(5)
    
    while True:
        try:
            print("[Background] Rules check...")
            await check_rules_job()
        except Exception as e:
            print(f"[Error] Weather check: {e}")
        # 每60秒执行一次
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task
    print("[System] Smart scheduler starting...")
    
    # 初始化数据库（创建表）
    from app.database import init_db, USE_DATABASE
    if USE_DATABASE:
        try:
            init_db()
            print("[OK] Database initialized")
        except Exception as e:
            print(f"[Warn] DB init: {e}")
    else:
        print("[Info] Using memory DB mode")
        from app.database import _seed_rules_to_mock_db
        from app.models.rule_storage import MOCK_DB
        if not any(r.get("store_id") == "store_001" for r in MOCK_DB):
            _seed_rules_to_mock_db("store_001")
            print("[OK] Seeded default rules")
    
    # 启动时立即执行一次，获取初始天气
    try:
        await check_rules_job()
    except Exception as e:
        print(f"[Warn] First rules check failed: {e}")
    
    # 启动后台任务，定期检查天气
    background_task = asyncio.create_task(weather_check_loop())
    
    yield
    
    # 关闭时取消后台任务
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    
    print("[System] Scheduler shutting down...")

app = FastAPI(lifespan=lifespan, title="Sign Inspire Backend")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获未处理异常，返回详细错误信息便于调试"""
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    if isinstance(exc, HTTPException):
        raise exc
    detail = str(exc).replace("\n", " ")[:500]
    return JSONResponse(status_code=500, content={"detail": detail, "type": type(exc).__name__})

# --- 新增：配置 CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源 (开发环境图省事，生产环境要改成前端域名)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------

app.include_router(rules.router, prefix="/api/v1")
app.include_router(stores.router, prefix="/api/v1")
app.include_router(decide.router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "ok", "module": "smart_scheduler"}

