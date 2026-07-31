"""door_log 加设备位置快照列

Revision ID: 9d7bcd1aed31
Revises: 46c280a24a6f
Create Date: 2026-07-31 22:05:09.231339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9d7bcd1aed31'
down_revision: Union[str, Sequence[str], None] = '46c280a24a6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 新增设备位置快照列（与 device_name/user_name 快照一致，保证设备改名/删除后位置仍保留）
    op.add_column('door_log', sa.Column('device_location', sa.String(length=200), nullable=True, comment='设备位置快照（开门时的设备位置）'))
    # 回填历史日志：按设备名匹配 device 表，把位置填进已存在的旧日志
    op.execute(
        """
        UPDATE door_log dl
        LEFT JOIN device d ON dl.device_name = d.name
        SET dl.device_location = d.location
        WHERE dl.device_name IS NOT NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('door_log', 'device_location')
