"""
动态词汇服务 - 客户使用新词时自动创建，无需修改后端
"""
import re
import hashlib
from typing import Dict, Optional
from sqlalchemy.orm import Session

# 尝试使用 pypinyin 生成可读的 target_id，失败则用 hash
try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False


def _slugify_chinese(text: str) -> str:
    """
    将中文转换为 target_id，如 "雨衣广告" -> "yuyi_guanggao"
    或 "雨衣广告" -> "ad_a1b2c3d4e5" (无 pypinyin 时)
    """
    text = text.strip()
    if not text:
        return "default"

    if HAS_PYPINYIN:
        # 转换为拼音并拼接
        parts = lazy_pinyin(text, style=Style.NORMAL)
        slug = "_".join(parts).lower()
        # 只保留字母数字下划线
        slug = re.sub(r"[^a-z0-9_]", "", slug)
        if not slug:
            slug = "ad_" + hashlib.md5(text.encode()).hexdigest()[:10]
        return slug if len(slug) <= 50 else slug[:50]
    else:
        # 回退：用 hash 生成唯一 id
        return "ad_" + hashlib.md5(text.encode()).hexdigest()[:10]


# 内存缓存，减少 DB 查询
_vocab_cache: Dict[str, Dict[str, str]] = {"weather": {}, "action": {}}
_cache_dirty = True


def _get_db_session():
    """获取数据库会话（用于无依赖注入场景）"""
    from app.database import SessionLocal, USE_DATABASE
    if not USE_DATABASE or SessionLocal is None:
        return None
    return SessionLocal()


def _load_vocabulary(db: Optional[Session] = None) -> None:
    """从数据库加载词汇到缓存"""
    global _vocab_cache, _cache_dirty
    if not _cache_dirty:
        return

    try:
        from app.models.vocabulary_model import Vocabulary
        session = db or _get_db_session()
        if session is None:
            return
        try:
            rows = session.query(Vocabulary).all()
            _vocab_cache["weather"] = {}
            _vocab_cache["action"] = {}
            for row in rows:
                if row.type in _vocab_cache:
                    _vocab_cache[row.type][row.keyword] = row.mapped_value
            _cache_dirty = False
            try:
                print(f"[Vocab] Loaded {len(rows)} entries")
            except UnicodeEncodeError:
                pass
        finally:
            if db is None and session is not None:
                session.close()
    except Exception as e:
        try:
            print(f"[Vocab] Load failed, using builtin: {e}")
        except UnicodeEncodeError:
            pass


def invalidate_cache():
    """有新词添加时调用，使缓存失效"""
    global _cache_dirty
    _cache_dirty = True


def get_weather_mappings(db: Optional[Session] = None) -> Dict[str, str]:
    """获取天气关键词映射，包含内置默认 + 数据库动态词汇"""
    builtin = {
        "多云": "cloudy", "阴": "cloudy",
        "晴天": "sunny", "晴": "sunny",
        "雨天": "rain", "雨": "rain", "下雨": "rain",
        "雪天": "snow", "雪": "snow", "下雪": "snow",
        "雷暴": "storm", "雷雨": "storm",
        "雾天": "fog", "雾": "fog", "大雾": "fog",
    }
    _load_vocabulary(db)
    merged = dict(builtin)
    merged.update(_vocab_cache.get("weather", {}))
    return merged


def get_action_mappings(db: Optional[Session] = None) -> Dict[str, str]:
    """获取动作/广告关键词映射，包含内置默认 + 数据库动态词汇"""
    builtin = {
        "咖啡广告": "coffee_ad", "咖啡": "coffee_ad",
        "热饮广告": "hot_drink_ad", "热饮": "hot_drink_ad",
        "防晒霜": "sunscreen_ad", "防晒": "sunscreen_ad",
        "冰西瓜": "bingxigua_ad", "冰西瓜广告": "bingxigua_ad",
        "西瓜": "xigua_ad", "西瓜广告": "xigua_ad",
        "寿司": "sushi_ad", "寿司广告": "sushi_ad",
    }
    _load_vocabulary(db)
    merged = dict(builtin)
    merged.update(_vocab_cache.get("action", {}))
    return merged


def add_mapping(
    vocab_type: str,
    keyword: str,
    mapped_value: str,
    db: Optional[Session] = None
) -> bool:
    """添加或更新词汇映射"""
    global _cache_dirty
    keyword = keyword.strip()
    if not keyword:
        return False

    try:
        from app.models.vocabulary_model import Vocabulary
        session = db or _get_db_session()
        if session is None:
            # 无 DB 时只更新缓存
            _vocab_cache.get(vocab_type, {})[keyword] = mapped_value
            return True
        try:
            existing = session.query(Vocabulary).filter(
                Vocabulary.type == vocab_type,
                Vocabulary.keyword == keyword
            ).first()
            if existing:
                existing.mapped_value = mapped_value
            else:
                session.add(Vocabulary(type=vocab_type, keyword=keyword, mapped_value=mapped_value))
            session.commit()
            _cache_dirty = True
            try:
                print(f"[Vocab] New mapping: {vocab_type} '{keyword}' -> '{mapped_value}'")
            except UnicodeEncodeError:
                pass
            return True
        finally:
            if db is None and session is not None:
                session.close()
    except Exception as e:
        try:
            print(f"[Vocab] Add mapping failed: {e}")
        except UnicodeEncodeError:
            pass
        return False


def ensure_action_mapping(
    action_text: str,
    db: Optional[Session] = None
) -> str:
    """
    确保动作词汇存在：若已有映射则返回 target_id，
    否则根据文本生成 target_id、写入词汇表并返回。
    """
    action_text = action_text.strip()
    if not action_text:
        return "coffee_ad"

    mappings = get_action_mappings(db)
    # 按关键词长度降序匹配
    for kw, target_id in sorted(mappings.items(), key=lambda x: -len(x[0])):
        if kw in action_text:
            return target_id

    # 新词：生成 target_id 并保存
    target_id = _slugify_chinese(action_text)
    add_mapping("action", action_text, target_id, db)
    return target_id


def ensure_weather_mapping(
    weather_text: str,
    db: Optional[Session] = None
) -> str:
    """
    确保天气词汇存在：若已有映射则返回标准化值，
    否则尝试推断或默认 cloudy，并写入词汇表。
    """
    weather_text = weather_text.strip()
    if not weather_text:
        return "cloudy"

    mappings = get_weather_mappings(db)
    for kw, value in sorted(mappings.items(), key=lambda x: -len(x[0])):
        if kw in weather_text:
            return value

    # 新词：尝试根据常见字推断，否则默认 cloudy
    inferred = "cloudy"
    if "雾" in weather_text or "霾" in weather_text:
        inferred = "fog"
    elif "风" in weather_text and "龙" in weather_text:
        inferred = "storm"
    add_mapping("weather", weather_text, inferred, db)
    return inferred
