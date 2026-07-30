"""add_device_name_user_name_to_door_log

Revision ID: 3505fa3650fd
Revises: 5c8d9e0f1a2b
Create Date: 2026-07-31 00:39:02.782486

Description: 在 door_log 表中新增 device_name 和 user_name 字段，
用于存储开门时的设备名和用户名快照，使日志不依赖 Device/User 表的 JOIN。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import String

# revision identifiers, used by Alembic.
revision: str = '3505fa3650fd'
down_revision: Union[str, Sequence[str], None] = '5c8d9e0f1a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 新增字段（允许为空，因为已有数据）
    op.add_column('door_log', sa.Column('device_name', String(100), nullable=True,
                  comment='设备名快照（开门时的设备名）'))
    op.add_column('door_log', sa.Column('user_name', String(50), nullable=True,
                  comment='用户名快照（开门时的用户名）'))

    # 2. 回填已有数据
    op.execute("""
        UPDATE door_log dl
        LEFT JOIN device d ON dl.device_id = d.id
        LEFT JOIN `user` u ON dl.user_id = u.id
        SET
            dl.device_name = COALESCE(d.name, '未知设备'),
            dl.user_name = CASE
                WHEN dl.user_id IS NULL THEN '本地'
                ELSE COALESCE(u.username, '未知用户')
            END
    """)


def downgrade() -> None:
    op.drop_column('door_log', 'user_name')
    op.drop_column('door_log', 'device_name')
