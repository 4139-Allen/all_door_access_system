from sqlalchemy import Column, Integer, String, DateTime, func

from database.db import Base

class Device(Base):
    __tablename__ = "device"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), default="offline", index=True)
    signal_strength = Column(Integer, nullable=True)  # WiFi RSSI (dBm)
    location = Column(String(200))
    last_online_at = Column(DateTime, nullable=True)  # 最后在线时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
