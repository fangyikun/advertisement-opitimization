"""
门店数据库模型
"""
from sqlalchemy import Column, String, Integer, Float, JSON, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Store(Base):
    """门店表"""
    __tablename__ = "stores"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False, default="Adelaide")
    latitude = Column(Float, default=-34.9285)
    longitude = Column(Float, default=138.6007)
    sign_id = Column(String(50), unique=True, index=True, nullable=True)
    opening_hours = Column(JSON, nullable=True)  # {"mon":"09:00-17:00","tue":"09:00-17:00",...}
    timezone = Column(String(50), default="Australia/Adelaide")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "sign_id": self.sign_id,
            "opening_hours": self.opening_hours,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
