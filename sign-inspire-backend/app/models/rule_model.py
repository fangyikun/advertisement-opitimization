"""
规则数据库模型
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Rule(Base):
    """
    规则表模型
    """
    __tablename__ = "rules"

    id = Column(String(36), primary_key=True, index=True)
    store_id = Column(String(50), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    conditions = Column(JSON, nullable=False)  # 存储条件列表
    action = Column(JSON, nullable=False)      # 存储动作对象
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        """
        转换为字典格式（兼容原有代码）
        """
        return {
            "id": self.id,
            "store_id": self.store_id,
            "name": self.name,
            "priority": self.priority,
            "conditions": self.conditions,
            "action": self.action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
