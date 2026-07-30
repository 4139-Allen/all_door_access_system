"""drop_user_id_device_id_from_door_log

Revision ID: 12c2f4507704
Revises: 3505fa3650fd
Create Date: 2026-07-31 00:41:41.397849

Description: 从 door_log 表删除 user_id 和 device_id 列及相关外键和索引。
日志不再依赖 User/Device 表，改用 device_name/user_name 快照。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '12c2f4507704'
down_revision: Union[str, Sequence[str], None] = '3505fa3650fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除外键约束
    op.drop_constraint("door_log_ibfk_1", "door_log", type_="foreignkey")
    op.drop_constraint("door_log_ibfk_2", "door_log", type_="foreignkey")

    # 2. 删除索引
    op.drop_index("idx_door_log_device_id", table_name="door_log")
    op.drop_index("idx_door_log_user_time", table_name="door_log")

    # 3. 删除列
    op.drop_column("door_log", "user_id")
    op.drop_column("door_log", "device_id")


def downgrade() -> None:
    # 加回列
    op.add_column("door_log", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("door_log", sa.Column("device_id", sa.Integer(), nullable=True))

    # 加回索引
    op.create_index("idx_door_log_user_time", "door_log", ["user_id", "time"])
    op.create_index("idx_door_log_device_id", "door_log", ["device_id"])

    # 加回外键
    op.create_foreign_key("door_log_ibfk_1", "door_log", "user", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("door_log_ibfk_2", "door_log", "device", ["device_id"], ["id"], ondelete="SET NULL")
