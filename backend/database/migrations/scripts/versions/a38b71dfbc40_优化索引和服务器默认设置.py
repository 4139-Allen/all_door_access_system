"""优化索引和服务器默认设置

Revision ID: a38b71dfbc40
Revises:
Create Date: 2026-07-05 14:39:57.381130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38b71dfbc40'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ===== 1. 移除 id 列的冗余索引（PK 已是聚簇索引）=====
    # 使用 IF EXISTS 兼容 create_all 初始化的数据库
    op.execute("DROP INDEX IF EXISTS ix_device_id ON device")
    op.execute("DROP INDEX IF EXISTS ix_door_log_id ON door_log")
    op.execute("DROP INDEX IF EXISTS ix_permission_id ON permission")
    op.execute("DROP INDEX IF EXISTS ix_role_id ON role")
    op.execute("DROP INDEX IF EXISTS ix_role_permission_id ON role_permission")
    op.execute("DROP INDEX IF EXISTS ix_user_id ON user")
    op.execute("DROP INDEX IF EXISTS ix_user_device_id ON user_device")

    # ===== 2. device 表新增常用查询索引 =====
    op.create_index(op.f('ix_device_name'), 'device', ['name'], unique=False)
    op.create_index(op.f('ix_device_status'), 'device', ['status'], unique=False)

    # ===== 3. 添加 server_default（数据库层默认值）=====
    op.alter_column('user', 'created_at',
                    existing_type=sa.DateTime(),
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('device', 'created_at',
                    existing_type=sa.DateTime(),
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('device', 'updated_at',
                    existing_type=sa.DateTime(),
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('role', 'created_at',
                    existing_type=sa.DateTime(),
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('door_log', 'time',
                    existing_type=sa.DateTime(),
                    server_default=sa.text('CURRENT_TIMESTAMP'))


def downgrade() -> None:
    """Downgrade schema."""

    # ===== 回滚 server_default =====
    op.alter_column('user', 'created_at',
                    existing_type=sa.DateTime(),
                    server_default=None)
    op.alter_column('device', 'created_at',
                    existing_type=sa.DateTime(),
                    server_default=None)
    op.alter_column('device', 'updated_at',
                    existing_type=sa.DateTime(),
                    server_default=None)
    op.alter_column('role', 'created_at',
                    existing_type=sa.DateTime(),
                    server_default=None)
    op.alter_column('door_log', 'time',
                    existing_type=sa.DateTime(),
                    server_default=None)

    # ===== 回滚 device 索引 =====
    op.drop_index(op.f('ix_device_status'), table_name='device')
    op.drop_index(op.f('ix_device_name'), table_name='device')

    # ===== 回滚 id 冗余索引 =====
    op.create_index(op.f('ix_device_id'), 'device', ['id'], unique=False)
    op.create_index(op.f('ix_door_log_id'), 'door_log', ['id'], unique=False)
    op.create_index(op.f('ix_permission_id'), 'permission', ['id'], unique=False)
    op.create_index(op.f('ix_role_id'), 'role', ['id'], unique=False)
    op.create_index(op.f('ix_role_permission_id'), 'role_permission', ['id'], unique=False)
    op.create_index(op.f('ix_user_id'), 'user', ['id'], unique=False)
    op.create_index(op.f('ix_user_device_id'), 'user_device', ['id'], unique=False)
