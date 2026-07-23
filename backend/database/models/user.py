
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship

from database.db import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String(100))
    role = Column(String(20), default="user", comment="角色标识（冗余字段，与 role_id 同步）")
    role_id = Column(Integer, ForeignKey("role.id"), nullable=True, comment="关联角色ID")
    phone = Column(String(20), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    openid = Column(String(100), unique=True, nullable=True)
    avatar = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, comment="账号状态：True=正常，False=已停用")
    deleted_at = Column(DateTime, nullable=True, comment="停用时间")
    created_at = Column(DateTime, server_default=func.now())

    # 角色关系（懒加载，按需查询）
    role_obj = relationship("Role", foreign_keys=[role_id], lazy="select")