"""door_log_add_action_index

Revision ID: 0bf6f7395ecb
Revises: 9d7bcd1aed31
Create Date: 2026-08-03 00:04:56.114288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0bf6f7395ecb'
down_revision: Union[str, Sequence[str], None] = '9d7bcd1aed31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 door_log.action 加索引，加速开锁方式占比（GROUP BY action）聚合查询"""
    op.create_index('idx_door_log_action', 'door_log', ['action'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_door_log_action', table_name='door_log')
