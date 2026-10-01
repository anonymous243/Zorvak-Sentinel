"""add_check_constraint_to_ai_pending_high_risk_actions

Revision ID: f12b1b37632d
Revises: 091b181c3355
Create Date: 2026-09-22 09:42:47.680330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f12b1b37632d'
down_revision: Union[str, Sequence[str], None] = '091b181c3355'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ai_pending_high_risk_actions', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'ck_ai_pending_high_risk_actions_required_signatures',
            'required_signatures >= 1',
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ai_pending_high_risk_actions', schema=None) as batch_op:
        batch_op.drop_constraint(
            'ck_ai_pending_high_risk_actions_required_signatures',
            type_='check',
        )
