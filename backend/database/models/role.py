from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database.db import Base
from datetime import datetime


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True, index=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
