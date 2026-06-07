from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from database.db import Base
from datetime import datetime


class DoorLog(Base):
    __tablename__ = "door_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"))
    device_id = Column(Integer, ForeignKey("device.id", ondelete="SET NULL"))
    action = Column(String(50))
    status = Column(String(50))
    ip = Column(String(50), nullable=True)  # 操作者IP，本地开门为NULL
    time = Column(DateTime, default=datetime.now)

    # 复合索引：用户 + 时间（覆盖非管理员查自己日志 + 时间排序）
    # 单列 time 索引：管理员全局时间范围查询
    __table_args__ = (
        Index("idx_door_log_user_time", "user_id", "time"),
        Index("idx_door_log_device_id", "device_id"),
        Index("idx_door_log_time", "time"),
    )
