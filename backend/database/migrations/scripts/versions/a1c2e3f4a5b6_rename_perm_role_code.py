"""permission.code -> perm_code, role.code -> role_code

将权限标识与角色标识的列名从通用 code 改为语义明确的 perm_code / role_code，
避免与 API 统一响应格式中的业务码 code 混淆。

Revision ID: a1c2e3f4a5b6
Revises: 0bf6f7395ecb
Create Date: 2026-08-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '0bf6f7395ecb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # MySQL 的 ALTER TABLE CHANGE COLUMN 会保留列上的 unique 索引
    op.alter_column('permission', 'code', new_column_name='perm_code',
                    existing_type=sa.String(length=50), existing_nullable=False)
    op.alter_column('role', 'code', new_column_name='role_code',
                    existing_type=sa.String(length=30), existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('permission', 'perm_code', new_column_name='code',
                    existing_type=sa.String(length=50), existing_nullable=False)
    op.alter_column('role', 'role_code', new_column_name='code',
                    existing_type=sa.String(length=30), existing_nullable=False)
