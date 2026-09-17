"""add policy priority

Revision ID: a8563b0d9533
Revises: cf5c5e61af71
Create Date: 2026-09-14 14:04:03.764840

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8563b0d9533"
down_revision: Union[str, Sequence[str], None] = "cf5c5e61af71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add policy priority with a safe existing-row backfill."""

    op.add_column(
        "policies",
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            "UPDATE policies SET priority = 100 WHERE priority IS NULL"
        )
    )

    with op.batch_alter_table("policies") as batch_op:
        batch_op.alter_column(
            "priority",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    """Remove policy priority."""

    with op.batch_alter_table("policies") as batch_op:
        batch_op.drop_column("priority")
