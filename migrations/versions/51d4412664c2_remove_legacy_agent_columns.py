"""remove_legacy_agent_columns

Revision ID: 51d4412664c2
Revises: 795422a9e2d8
Create Date: 2026-10-11 22:02:57.945117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51d4412664c2'
down_revision: Union[str, Sequence[str], None] = '795422a9e2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_column('kms_key_arn')
        batch_op.drop_column('working_hours')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('working_hours', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('kms_key_arn', sa.VARCHAR(length=512), nullable=True))

