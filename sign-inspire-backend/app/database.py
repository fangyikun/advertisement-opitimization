"""
数据库配置和连接管理
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv

load_dotenv()

# 从环境变量读取数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "sign_inspire")

# 是否使用数据库（如果连接失败会自动设为 False）
USE_DATABASE = True

# 构建数据库 URL
# 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 创建数据库引擎
engine = None
SessionLocal = None
Base = declarative_base()

def test_connection():
    """
    测试数据库连接
    """
    global engine, SessionLocal, USE_DATABASE
    
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        # 尝试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # 创建会话工厂
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        USE_DATABASE = True
        print("✅ 数据库连接成功！")
        return True
    except Exception as e:
        USE_DATABASE = False
        print(f"⚠️ 数据库连接失败: {e}")
        print("   将使用内存数据库模式（数据不会持久化）")
        print("\n💡 解决方案：")
        print("   1. 检查 MySQL 服务是否启动")
        print("   2. 检查 .env 文件中的数据库配置是否正确")
        print("   3. 确认数据库是否存在：CREATE DATABASE sign_inspire;")
        print("   4. 确认用户名和密码是否正确")
        return False

# 初始化时测试连接
test_connection()


def _seed_vocabulary_if_empty(eng):
    """若词汇表为空，写入默认天气与动作映射"""
    try:
        from app.models.vocabulary_model import Vocabulary
        from sqlalchemy.orm import Session
        session = Session(bind=eng)
        if session.query(Vocabulary).count() > 0:
            session.close()
            return
        defaults = [
            # weather
            ("weather", "多云", "cloudy"), ("weather", "阴", "cloudy"),
            ("weather", "晴天", "sunny"), ("weather", "晴", "sunny"),
            ("weather", "雨天", "rain"), ("weather", "雨", "rain"), ("weather", "下雨", "rain"),
            ("weather", "雪天", "snow"), ("weather", "雪", "snow"), ("weather", "下雪", "snow"),
            ("weather", "雷暴", "storm"), ("weather", "雷雨", "storm"),
            ("weather", "雾天", "fog"), ("weather", "雾", "fog"),
            # action
            ("action", "咖啡广告", "coffee_ad"), ("action", "咖啡", "coffee_ad"),
            ("action", "热饮广告", "hot_drink_ad"), ("action", "热饮", "hot_drink_ad"),
            ("action", "防晒霜", "sunscreen_ad"), ("action", "防晒", "sunscreen_ad"),
            ("action", "冰西瓜", "bingxigua_ad"), ("action", "冰西瓜广告", "bingxigua_ad"),
            ("action", "西瓜", "xigua_ad"), ("action", "西瓜广告", "xigua_ad"),
        ]
        for t, kw, val in defaults:
            session.add(Vocabulary(type=t, keyword=kw, mapped_value=val))
        session.commit()
        session.close()
        print("📚 词汇表种子数据已写入")
    except Exception as e:
        print(f"⚠️ 词汇表种子写入失败（可忽略）: {e}")


def get_db():
    """
    获取数据库会话（依赖注入）
    """
    if not USE_DATABASE or SessionLocal is None:
        raise RuntimeError("数据库未启用，请检查数据库连接配置")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库（创建表）
    """
    global USE_DATABASE
    
    if not USE_DATABASE or engine is None:
        print("⚠️ 数据库未连接，跳过表创建")
        return False
    
    try:
        # 导入所有模型，确保它们被注册到 Base.metadata
        from app.models.rule_model import Rule
        from app.models.vocabulary_model import Vocabulary
        from app.models.media_model import MediaCache
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        # 种子数据：若词汇表为空则写入默认映射
        _seed_vocabulary_if_empty(engine)
        print("✅ 数据库表创建成功！")
        return True
    except Exception as e:
        print(f"⚠️ 创建数据库表失败: {e}")
        USE_DATABASE = False
        return False
