"""remove_user_role_id_fk

删除 User.role_id 冗余外键（角色标识由 role 字符串字段承载）。

Revision ID: 3b9c6d8e1f20
Revises: 2a8b5f7e9d10
Create Date: 2026-07-25 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3b9c6d8e1f20"
down_revision: Union[str, Sequence[str], None] = "2a8b5f7e9d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 删除外键约束
    op.drop_constraint("fk_user_role_id", "user", type_="foreignkey")

    # 2. 删除 role_id 列
    op.drop_column("user", "role_id")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. 新增 role_id 列
    op.add_column("user", sa.Column("role_id", sa.Integer(), nullable=True, comment="关联角色ID"))

    # 2. 根据现有 role 字符串回填数据
    op.execute(
        """
        UPDATE `user` u
        JOIN `role` r ON u.`role` = r.`code`
        SET u.`role_id` = r.`id`
        WHERE u.`role_id` IS NULL
        """
    )

    # 3. 重新添加外键约束
    op.create_foreign_key(
        "fk_user_role_id",
        "user",
        "role",
        ["role_id"],
        ["id"],
    )
