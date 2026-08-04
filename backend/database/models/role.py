from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

from database.db import Base


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False, unique=True)
    role_code = Column(String(30), nullable=False, unique=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
