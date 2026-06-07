from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from database.db import Base


class RolePermission(Base):
    __tablename__ = "role_permission"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permission.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
