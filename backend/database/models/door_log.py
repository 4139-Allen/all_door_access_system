from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, func

from database.db import Base


class DoorLog(Base):
    __tablename__ = "door_log"

    id = Column(Integer, primary_key=True)
    device_name = Column(String(100), nullable=True, comment="设备名快照（开门时的设备名）")
    device_location = Column(String(200), nullable=True, comment="设备位置快照（开门时的设备位置）")
    user_name = Column(String(50), nullable=True, comment="用户名快照（开门时的用户名）")
    action = Column(String(50))
    status = Column(String(50))
    ip = Column(String(50), nullable=True)  # 操作者IP，本地开门为NULL
    time = Column(DateTime, default=datetime.now)

    # 单列 time 索引：管理员全局时间范围查询
    # action 索引：开锁方式占比（GROUP BY action）等聚合查询
    __table_args__ = (
        Index("idx_door_log_time", "time"),
        Index("idx_door_log_action", "action"),
    )
