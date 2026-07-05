from sqlalchemy import Column, Integer, String
from database.db import Base


class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    module = Column(String(30), nullable=False)
    sort = Column(Integer, default=0)
