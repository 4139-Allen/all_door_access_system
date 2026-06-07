from sqlalchemy import Column, Integer, String, DateTime
from database.db import Base
from datetime import datetime

class Device(Base):
    __tablename__ = "device"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="offline")
    signal_strength = Column(Integer, nullable=True)  # WiFi RSSI (dBm)
    location = Column(String(200))
    last_online_at = Column(DateTime, nullable=True)  # 最后在线时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
