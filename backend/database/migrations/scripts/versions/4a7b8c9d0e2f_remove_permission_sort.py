"""remove_permission_sort

删除 permission.sort 字段（排序权重，无实际业务用途）。

Revision ID: 4a7b8c9d0e2f
Revises: 3b9c6d8e1f20
Create Date: 2026-07-25 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a7b8c9d0e2f"
down_revision: Union[str, Sequence[str], None] = "3b9c6d8e1f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("permission", "sort")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("permission", sa.Column("sort", sa.Integer(), nullable=False, server_default=sa.text("0")))
