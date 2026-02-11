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
            ("action", "寿司", "sushi_ad"), ("action", "寿司广告", "sushi_ad"),
        ]
        for t, kw, val in defaults:
            session.add(Vocabulary(type=t, keyword=kw, mapped_value=val))
        session.commit()
        session.close()
        print("📚 词汇表种子数据已写入")
    except Exception as e:
        print(f"⚠️ 词汇表种子写入失败（可忽略）: {e}")


def _seed_stores_if_empty(eng):
    """若门店表为空，写入 Adelaide 默认门店 store_001"""
    try:
        from app.models.store_model import Store
        from sqlalchemy.orm import Session
        session = Session(bind=eng)
        if session.query(Store).count() > 0:
            session.close()
            return
        default_store = Store(
            id="store_001",
            name="Adelaide 试点门店",
            city="Adelaide",
            latitude=-34.9285,
            longitude=138.6007,
            sign_id="sign_001",
            timezone="Australia/Adelaide",
            is_active=True,
        )
        session.add(default_store)
        session.commit()
        session.close()
        print("🏪 门店种子数据已写入 (store_001)")
    except Exception as e:
        print(f"⚠️ 门店种子写入失败（可忽略）: {e}")


# 默认规则种子（DB 和内存模式共用）
DEFAULT_RULES = [
            # 澳洲五大特色场景 (western) - 按优先级匹配
            {"name": "澳洲 Sunday Sesh 推披萨", "priority": 6, "conditions": [{"type": "day", "operator": "==", "value": "sun"}, {"type": "time", "operator": "==", "value": "14,18"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "pizza_ad", "message": "Sunday arvo? Pizza and cold ones. The Aussie way. / 周日午后，披萨配啤酒，澳式惬意。"}},
            {"name": "澳洲 Barbie 推 BBQ 烧烤", "priority": 5, "conditions": [{"type": "day", "operator": "==", "value": "fri,sat,sun"}, {"type": "time", "operator": "==", "value": "12,18"}, {"type": "weather", "operator": "==", "value": "sunny"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "bbq_ad", "message": "Sunny weekend? Fire up the barbie! Sausages and snags await. / 晴朗周末，后院 BBQ 走起！"}},
            {"name": "澳洲 Brunch 推咖啡", "priority": 5, "conditions": [{"type": "time", "operator": "==", "value": "8,11"}, {"type": "weather", "operator": "in", "value": "sunny,cloudy"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "coffee_ad", "message": "Flat White o'clock. Kick off your morning the Aussie way. / 早晨来杯澳白，开启元气一天。"}},
            {"name": "澳洲 Scorcher 推冰品", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "sunny"}, {"type": "temp", "operator": "==", "value": ">30"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "bingxigua_ad", "message": "Scorcher! Time for gelato, icy poles, or a cold seafood platter. / 酷暑来袭，冰品冷饮救赎。"}},
            {"name": "澳洲湿冷推亚洲热汤", "priority": 4, "conditions": [{"type": "temp", "operator": "==", "value": "<15"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "asian_soup_ad", "message": "Chilly and wet? Warm up with laksa, pho, or ramen. / 湿冷天，来碗叻沙或拉面暖暖胃。"}},
            {"name": "澳洲雨天推亚洲热汤", "priority": 4, "conditions": [{"type": "weather", "operator": "==", "value": "rain"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "asian_soup_ad", "message": "Rainy day comfort: a steaming bowl of pho or laksa. / 雨天标配，热汤暖人心。"}},
            {"name": "澳洲晴天推咖啡", "priority": 1, "conditions": [{"type": "weather", "operator": "==", "value": "sunny"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "coffee_ad", "message": "Sunny day calls for a coffee. Take it outside. / 好天气，咖啡馆见。"}},
            {"name": "澳洲多云推咖啡", "priority": 1, "conditions": [{"type": "weather", "operator": "==", "value": "cloudy"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "coffee_ad", "message": "Cloudy but cosy. A flat white will hit the spot. / 多云天，一杯澳白刚刚好。"}},
            # 澳洲多云天气专项（Mood Booster / Muggy / Hump Day / Decision Fatigue）
            {"name": "多云心情提亮推 Poke/寿司", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "cloudy"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "sushi_ad", "message": "Grey skies? Add some colour to your dinner with a fresh Salmon Poke Bowl. 🌈 / 多云天心情修复剂：新鲜多彩的寿司卷。"}},
            {"name": "多云闷热推越南米纸卷", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "cloudy"}, {"type": "temp", "operator": "==", "value": "25,28"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "vietnamese_ad", "message": "Bit muggy out there? Cool down with a zesty Vietnamese Chicken Salad. / 外面有点闷？来份越南鸡肉沙拉清爽一下。"}},
            {"name": "多云周三推炸鸡排/塔可", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "cloudy"}, {"type": "day", "operator": "==", "value": "wed"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "burger_ad", "message": "Classic Schnitty weather. Not too hot, not too cold. Perfect for the beer garden. / 多云的周三？以此为借口吃顿塔可大餐吧。"}},
            {"name": "多云选择困难推披萨", "priority": 4, "conditions": [{"type": "weather", "operator": "==", "value": "cloudy"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "pizza_ad", "message": "Can't decide? You can't go wrong with a Woodfired Pizza. / 不知道吃啥？木火披萨永远没错。"}},
            {"name": "澳洲雪天推热饮", "priority": 2, "conditions": [{"type": "weather", "operator": "==", "value": "snow"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "hot_drink_ad", "message": "Snowy day? Hot chocolate or a warming brew. / 雪天，热可可或热饮暖手又暖心。"}},
            {"name": "澳洲雾天推咖啡", "priority": 1, "conditions": [{"type": "weather", "operator": "==", "value": "fog"}, {"type": "region", "operator": "==", "value": "western"}], "action": {"type": "switch_playlist", "target_id": "coffee_ad", "message": "Foggy morning? A good coffee cuts through. / 雾天清晨，一杯咖啡提神。"}},
            # 中国 - 节气优先 (时令>地域>天气)
            {"name": "冬至北方推饺子", "priority": 7, "conditions": [{"type": "solar_term", "operator": "==", "value": "冬至"}, {"type": "china_region", "operator": "==", "value": "north_china"}], "action": {"type": "switch_playlist", "target_id": "dumplings_ad", "message": "冬至不端饺子碗，冻掉耳朵没人管！ / 北方冬至，饺子安排。"}},
            {"name": "冬至南方推汤圆", "priority": 7, "conditions": [{"type": "solar_term", "operator": "==", "value": "冬至"}, {"type": "china_region", "operator": "==", "value": "south_china"}], "action": {"type": "switch_playlist", "target_id": "tangyuan_ad", "message": "冬至大如年，南方吃汤圆，团团圆圆。 / 冬至吃汤圆，甜甜蜜蜜过冬。"}},
            {"name": "冬至华东推汤圆", "priority": 7, "conditions": [{"type": "solar_term", "operator": "==", "value": "冬至"}, {"type": "china_region", "operator": "==", "value": "east_china"}], "action": {"type": "switch_playlist", "target_id": "tangyuan_ad", "message": "江南冬至，汤圆软糯，岁岁平安。 / 冬至汤圆，江南味道。"}},
            {"name": "入伏推饺子面条", "priority": 7, "conditions": [{"type": "solar_term", "operator": "==", "value": "入伏"}], "action": {"type": "switch_playlist", "target_id": "dumplings_ad", "message": "头伏饺子二伏面，入伏吃饺子，解馋又应景。 / 入伏了，饺子开吃！"}},
            {"name": "立秋贴秋膘", "priority": 7, "conditions": [{"type": "solar_term", "operator": "==", "value": "立秋"}], "action": {"type": "switch_playlist", "target_id": "lamb_hotpot_ad", "message": "立秋贴秋膘，红烧肉、羊汤涮锅，贴膘正当时。 / 秋风起，贴秋膘，肉食者的节日。"}},
            {"name": "腊八推腊八粥", "priority": 7, "conditions": [{"type": "solar_term", "operator": "==", "value": "腊八"}], "action": {"type": "switch_playlist", "target_id": "congee_ad", "message": "腊八腊八，冻掉下巴。喝碗腊八粥，暖胃又应景。 / 腊八粥，五谷丰登，福气满满。"}},
            # 中国 - 场景化
            {"name": "周五快乐推奶茶炸鸡", "priority": 5, "conditions": [{"type": "day", "operator": "==", "value": "fri"}, {"type": "region", "operator": "==", "value": "east_asia"}], "action": {"type": "switch_playlist", "target_id": "bubble_tea_ad", "message": "周五了！这点卡路里是对辛苦一周的奖励。奶茶炸鸡走起！ / TGIF，奶茶炸鸡犒劳自己。"}},
            {"name": "深夜修仙推小龙虾麻辣烫", "priority": 5, "conditions": [{"type": "time", "operator": "==", "value": "22,23"}, {"type": "region", "operator": "==", "value": "east_asia"}], "action": {"type": "switch_playlist", "target_id": "crayfish_ad", "message": "深夜的麻辣烫/小龙虾，是打工人的灵魂伴侣。 / 修仙夜宵，小龙虾配啤酒。"}},
            # 华南 (south_china) - 湿热祛湿
            {"name": "华南高温祛湿推绿豆沙", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "sunny"}, {"type": "temp", "operator": "==", "value": ">30"}, {"type": "china_region", "operator": "==", "value": "south_china"}], "action": {"type": "switch_playlist", "target_id": "green_bean_soup_ad", "message": "天气这么热，来碗绿豆沙下下火吧！ / 湿热天，绿豆沙、龟苓膏祛湿解暑。"}},
            {"name": "华南湿热推凉茶", "priority": 4, "conditions": [{"type": "temp", "operator": "==", "value": ">28"}, {"type": "china_region", "operator": "==", "value": "south_china"}], "action": {"type": "switch_playlist", "target_id": "herbal_tea_ad", "message": "湿气重？喝凉茶还是吃龟苓膏？ / 夏日祛湿，王老吉、凉茶安排。"}},
            {"name": "华南雨天推砂锅粥", "priority": 4, "conditions": [{"type": "weather", "operator": "==", "value": "rain"}, {"type": "china_region", "operator": "==", "value": "south_china"}], "action": {"type": "switch_playlist", "target_id": "congee_ad", "message": "下雨天最适合喝砂锅粥，暖暖的超舒服。 / 雨天标配，海鲜粥、皮蛋瘦肉粥。"}},
            # 华东 (east_china) - 梅雨小龙虾、秋凉大闸蟹
            {"name": "华东梅雨推小龙虾", "priority": 5, "conditions": [{"type": "weather", "operator": "in", "value": "rain,cloudy"}, {"type": "temp", "operator": "==", "value": "25,35"}, {"type": "china_region", "operator": "==", "value": "east_china"}], "action": {"type": "switch_playlist", "target_id": "crayfish_ad", "message": "黄梅天闷热没胃口？小龙虾配啤酒，开胃！ / 这种天气，只有小龙虾和啤酒能救我。"}},
            {"name": "华东秋凉推大闸蟹", "priority": 5, "conditions": [{"type": "temp", "operator": "==", "value": "10,25"}, {"type": "china_region", "operator": "==", "value": "east_china"}], "action": {"type": "switch_playlist", "target_id": "hairy_crab_ad", "message": "秋风起，蟹脚痒。今晚大闸蟹安排上？ / 秋凉正是吃蟹时，鲜肉月饼、糖炒栗子。"}},
            {"name": "华东晴好推寿司轻食", "priority": 2, "conditions": [{"type": "weather", "operator": "==", "value": "sunny"}, {"type": "china_region", "operator": "==", "value": "east_china"}], "action": {"type": "switch_playlist", "target_id": "sushi_ad", "message": "春暖花开，带上青团去野餐吧！晴好天，寿司轻食最惬意。 / 精致 Brunch，咖啡三明治走起。"}},
            # 华北 (north_china) - 酷暑冷面、严寒涮肉
            {"name": "华北酷暑推冷面撸串", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "sunny"}, {"type": "temp", "operator": "==", "value": ">30"}, {"type": "china_region", "operator": "==", "value": "north_china"}], "action": {"type": "switch_playlist", "target_id": "cold_noodles_ad", "message": "大热天吃冷面，透心凉！ / 晚上出来撸串？啤酒我都冰好了。"}},
            {"name": "华北严寒推铜锅涮肉", "priority": 5, "conditions": [{"type": "temp", "operator": "==", "value": "<0"}, {"type": "china_region", "operator": "==", "value": "north_china"}], "action": {"type": "switch_playlist", "target_id": "lamb_hotpot_ad", "message": "下雪了！还有什么比铜锅涮肉更治愈？ / 外面零下十几度，进屋吃羊汤暖和暖和。"}},
            {"name": "华北下雪推铁锅炖", "priority": 5, "conditions": [{"type": "weather", "operator": "==", "value": "snow"}, {"type": "china_region", "operator": "==", "value": "north_china"}], "action": {"type": "switch_playlist", "target_id": "iron_pot_stew_ad", "message": "下雪天，铁锅炖大鹅、排骨，暖到心窝。 / 雪天标配，铁锅炖走起。"}},
            {"name": "华北风沙推饺子润肺", "priority": 4, "conditions": [{"type": "weather", "operator": "==", "value": "fog"}, {"type": "china_region", "operator": "==", "value": "north_china"}], "action": {"type": "switch_playlist", "target_id": "dumplings_ad", "message": "风沙大别乱跑，吃顿饺子也是过节。 / 润肺止咳，雪梨汤、银耳羹安排。"}},
            # 中国通用
            {"name": "中国雾霾推热饮润肺", "priority": 4, "conditions": [{"type": "weather", "operator": "==", "value": "fog"}, {"type": "region", "operator": "==", "value": "east_asia"}], "action": {"type": "switch_playlist", "target_id": "hot_drink_ad", "message": "雾霾天，鸭血粉丝汤、雪梨汤润润肺。少出门，外卖免运费。 / 清肺热饮，宅家也能吃好。"}},
            {"name": "中国雨天推热饮", "priority": 2, "conditions": [{"type": "weather", "operator": "==", "value": "rain"}, {"type": "region", "operator": "==", "value": "east_asia"}], "action": {"type": "switch_playlist", "target_id": "hot_drink_ad", "message": "雨天一杯热饮，暖暖手也暖暖心。 / 下雨天，热饮、热汤最治愈。"}},
            {"name": "中国晴天推寿司", "priority": 1, "conditions": [{"type": "weather", "operator": "==", "value": "sunny"}, {"type": "region", "operator": "==", "value": "east_asia"}], "action": {"type": "switch_playlist", "target_id": "sushi_ad", "message": "好天气，寿司轻食走起。 / 晴天标配，精致日料。"}},
            {"name": "中国兜底推奶茶", "priority": 1, "conditions": [{"type": "region", "operator": "==", "value": "east_asia"}], "action": {"type": "switch_playlist", "target_id": "bubble_tea_ad", "message": "遇事不决推奶茶，在中国永远没错。 / 不知道喝啥？奶茶永远是最稳的选择。"}},
]


def _seed_rules_to_mock_db(store_id: str = "store_001"):
    """将默认规则写入 MOCK_DB（内存模式用）"""
    import uuid
    from app.models.rule_storage import MOCK_DB
    for d in DEFAULT_RULES:
        MOCK_DB.append({
            "id": str(uuid.uuid4()),
            "store_id": store_id,
            "name": d["name"],
            "priority": d["priority"],
            "conditions": d["conditions"],
            "action": d["action"],
        })
    print(f"📋 [Memory] 默认规则种子已写入 MOCK_DB")


def _seed_rules_if_empty(eng):
    """若规则表为空，写入澳洲+中国城市专用种子规则"""
    import uuid
    try:
        from app.models.rule_model import Rule
        from sqlalchemy.orm import Session
        session = Session(bind=eng)
        if session.query(Rule).count() > 0:
            session.close()
            return
        for d in DEFAULT_RULES:
            r = Rule(
                id=str(uuid.uuid4()),
                store_id="store_001",
                name=d["name"],
                priority=d["priority"],
                conditions=d["conditions"],
                action=d["action"],
            )
            session.add(r)
        session.commit()
        session.close()
        print("📋 全球规则种子数据已写入")
    except Exception as e:
        print(f"⚠️ 规则种子写入失败（可忽略）: {e}")


def get_db():
    """获取数据库会话（依赖注入）"""
    if not USE_DATABASE or SessionLocal is None:
        raise RuntimeError("数据库未启用，请检查数据库连接配置")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_optional():
    """可选的数据库会话（数据库未启用时返回 None）"""
    if USE_DATABASE and SessionLocal:
        try:
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ 获取数据库会话失败: {e}")
            yield None
    else:
        yield None


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
        from app.models.store_model import Store
        from app.models.vocabulary_model import Vocabulary
        from app.models.media_model import MediaCache
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        # 种子数据
        _seed_vocabulary_if_empty(engine)
        _seed_stores_if_empty(engine)
        _seed_rules_if_empty(engine)
        print("✅ 数据库表创建成功！")
        return True
    except Exception as e:
        print(f"⚠️ 创建数据库表失败: {e}")
        USE_DATABASE = False
        return False
