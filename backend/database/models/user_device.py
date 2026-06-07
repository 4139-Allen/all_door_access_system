
from database.db import Base
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint

class UserDevice(Base):
    __tablename__ = "user_device"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))
    device_id = Column(Integer, ForeignKey("device.id", ondelete="CASCADE"), index=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'device_id', name='uq_user_device'),
    )

