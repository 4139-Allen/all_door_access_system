"""add_user_role_id_fk

新增 User.role_id 外键关联 Role 表，与现有的 role 字符串字段同步。

Revision ID: 2a8b5f7e9d10
Revises: c91c0fac2f85
Create Date: 2026-07-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2a8b5f7e9d10"
down_revision: Union[str, Sequence[str], None] = "c91c0fac2f85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 新增 role_id 列（先允许为空）
    op.add_column("user", sa.Column("role_id", sa.Integer(), nullable=True, comment="关联角色ID"))

    # 2. 数据迁移：根据现有的 role 字符串填充 role_id
    op.execute(
        """
        UPDATE `user` u
        JOIN `role` r ON u.`role` = r.`code`
        SET u.`role_id` = r.`id`
        WHERE u.`role_id` IS NULL
        """
    )

    # 3. 添加外键约束
    op.create_foreign_key(
        "fk_user_role_id",
        "user",
        "role",
        ["role_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. 删除外键约束
    op.drop_constraint("fk_user_role_id", "user", type_="foreignkey")

    # 2. 删除 role_id 列
    op.drop_column("user", "role_id")
