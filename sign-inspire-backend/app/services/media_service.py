"""
媒体服务 - 根据广告/产品类型自动从互联网搜索相关图片
"""
import os
import httpx
from typing import Optional
from sqlalchemy.orm import Session

# 常见中文关键词 -> 英文搜索词（提升 Unsplash 搜索结果质量）
SEARCH_TERM_MAP = {
    "咖啡": "coffee", "咖啡广告": "coffee",
    "热饮": "hot drink", "热饮广告": "hot drink",
    "防晒霜": "sunscreen", "防晒": "sunscreen",
    "西瓜": "watermelon", "西瓜广告": "watermelon",
    "冰西瓜": "ice watermelon", "冰西瓜广告": "ice watermelon",
    "雨衣": "raincoat", "雨衣广告": "raincoat",
}


def _get_search_term(keyword: str) -> str:
    """将关键词转为 Unsplash 搜索词"""
    kw = (keyword or "").strip()
    return SEARCH_TERM_MAP.get(kw, kw) or keyword


def _search_unsplash(query: str) -> Optional[str]:
    """调用 Unsplash API 搜索图片"""
    key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": 1},
                headers={"Authorization": f"Client-ID {key}"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None
            urls = results[0].get("urls", {})
            # regular: 1080px 宽，适合展示
            return urls.get("regular") or urls.get("full") or urls.get("raw")
    except Exception as e:
        try:
            print(f"[Media] Unsplash search failed: {e}")
        except UnicodeEncodeError:
            pass
        return None


def _placeholder_url(target_id: str) -> str:
    """无 Unsplash 时使用 Picsum 占位图（按 target_id 固定）"""
    safe_id = (target_id or "default").replace(" ", "-")[:50]
    return f"https://picsum.photos/seed/{safe_id}/1920/1080"


def _get_keyword_for_target(target_id: str, db: Optional[Session] = None) -> Optional[str]:
    """从词汇表反向查找：target_id -> 关键词（用于搜索）"""
    try:
        from app.services.vocabulary_service import get_action_mappings
        action_map = get_action_mappings(db)
        for kw, val in action_map.items():
            if val == target_id:
                return kw
        return None
    except Exception as e:
        try:
            print(f"[Media] Vocab lookup failed: {e}")
        except UnicodeEncodeError:
            pass
        return None


def get_image_url(target_id: str, db: Optional[Session] = None) -> str:
    """
    获取 target_id 对应的图片 URL。
    1. 查缓存
    2. 无缓存则根据关键词搜索 Unsplash
    3. 无 Unsplash Key 或搜索失败则返回 Picsum 占位图
    """
    if not target_id or target_id == "default":
        return _placeholder_url("default")

    try:
        from app.models.media_model import MediaCache
        from app.database import SessionLocal, USE_DATABASE
        session = db
        own_session = False
        if session is None and USE_DATABASE and SessionLocal:
            session = SessionLocal()
            own_session = True

        if session:
            try:
                cached = session.query(MediaCache).filter(MediaCache.target_id == target_id).first()
                if cached:
                    return cached.image_url
            finally:
                if own_session and session:
                    session.close()
    except Exception as e:
        try:
            print(f"[Media] Cache query failed: {e}")
        except UnicodeEncodeError:
            pass

    # 未命中缓存：搜索
    keyword = _get_keyword_for_target(target_id, db)
    search_term = _get_search_term(keyword or target_id.replace("_ad", "").replace("_", " "))
    url = _search_unsplash(search_term)

    if url:
        # 写入缓存
        try:
            from app.models.media_model import MediaCache
            from app.database import SessionLocal, USE_DATABASE
            if USE_DATABASE and SessionLocal:
                session = SessionLocal()
                try:
                    session.merge(MediaCache(target_id=target_id, image_url=url, search_term=search_term))
                    session.commit()
                    try:
                        print(f"[Media] Cached: {target_id} <- {search_term}")
                    except UnicodeEncodeError:
                        pass
                finally:
                    session.close()
        except Exception as e:
            try:
                print(f"[Media] Cache write failed: {e}")
            except UnicodeEncodeError:
                pass
        return url

    return _placeholder_url(target_id)
