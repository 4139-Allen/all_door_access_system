"""add_is_builtin_to_user

新增 User.is_builtin 标记，标识系统内置账号（不可删除）。

Revision ID: 5c8d9e0f1a2b
Revises: 4a7b8c9d0e2f
Create Date: 2026-07-25 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5c8d9e0f1a2b"
down_revision: Union[str, Sequence[str], None] = "4a7b8c9d0e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 新增 is_builtin 列，默认 false
    op.add_column("user", sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False, comment="是否系统内置账号（不可删除）"))

    # 2. 将 admin 用户名对应的账号标记为内置（从 .env 读取可能不准确，统一标记所有 admin 角色）
    #    运行 python 代码来获取配置中的 ADMIN_USERNAME
    from core.config import ADMIN_USERNAME
    op.execute(
        f"UPDATE `user` SET `is_builtin` = TRUE WHERE `username` = '{ADMIN_USERNAME}'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "is_builtin")
