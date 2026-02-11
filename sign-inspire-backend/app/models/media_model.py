"""
媒体缓存模型 - 存储 target_id 自动搜索到的图片 URL
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class MediaCache(Base):
    """target_id -> 图片 URL 缓存"""
    __tablename__ = "media_cache"

    target_id = Column(String(100), primary_key=True)
    image_url = Column(String(500), nullable=False)
    search_term = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
