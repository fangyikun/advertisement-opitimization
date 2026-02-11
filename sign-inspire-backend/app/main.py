# backend/app/main.py
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <--- 新增这行
from contextlib import asynccontextmanager
import asyncio
from app.api.v1.endpoints import rules
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
            print("⏰ [Background] 后台定时任务执行规则检查...")
            await check_rules_job()
        except Exception as e:
            print(f"❌ 天气检查任务出错: {e}")
        # 每60秒执行一次
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task
    print("⏰ [System] 智能排期调度器启动中...")
    
    # 初始化数据库（创建表）
    from app.database import init_db, USE_DATABASE
    if USE_DATABASE:
        try:
            init_db()
            print("✅ 数据库初始化完成")
        except Exception as e:
            print(f"⚠️ 数据库初始化警告: {e}")
            print("   如果表已存在，可以忽略此警告")
    else:
        print("ℹ️ 使用内存数据库模式（数据不会持久化）")
    
    # 启动时立即执行一次，获取初始天气
    try:
        await check_rules_job()
    except Exception as e:
        print(f"⚠️ 首次规则检查失败: {e}")
        print("   应用将继续运行，但规则检查可能无法正常工作")
    
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
    
    print("⏰ [System] 调度器关闭...")

app = FastAPI(lifespan=lifespan, title="Sign Inspire Backend")

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

@app.get("/")
def health_check():
    return {"status": "ok", "module": "smart_scheduler"}