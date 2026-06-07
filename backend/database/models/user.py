
from sqlalchemy import Column, Integer, String, DateTime
from database.db import Base
from datetime import datetime

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password = Column(String(100))
    role = Column(String(20), default="user")
    phone = Column(String(20), unique=True, nullable=True, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    openid = Column(String(100), unique=True, nullable=True, index=True)
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)