"""
动态词汇表模型 - 支持客户使用新词时自动创建，无需修改后端
"""
from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Vocabulary(Base):
    """
    词汇表：存储关键词到标准值的映射
    - type='weather': 天气关键词 -> 标准化值 (sunny, cloudy, rain, snow, storm, fog)
    - type='action': 广告/产品关键词 -> target_id (coffee_ad, sunscreen_ad, 等)
    """
    __tablename__ = "vocabulary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)  # 'weather' | 'action'
    keyword = Column(String(100), nullable=False)
    mapped_value = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('type', 'keyword', name='uq_vocab_type_keyword'),
    )
