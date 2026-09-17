"""add authorization decision records

Revision ID: b721d641a425
Revises: a8563b0d9533
Create Date: 2026-09-14 14:15:08.107899

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b721d641a425"
down_revision: Union[str, Sequence[str], None] = "a8563b0d9533"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the authorization decision audit store."""

    op.create_table(
        "authorization_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=False),
        sa.Column(
            "effect",
            sa.Enum("allow", "deny", name="decision_effect"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=36), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("evaluation_ms", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "effect IN ('allow', 'deny')",
            name="ck_authorization_decisions_effect",
        ),
        sa.CheckConstraint(
            "evaluation_ms >= 0",
            name="ck_authorization_decisions_evaluation_ms",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_authorization_decisions_request_id",
        "authorization_decisions",
        ["request_id"],
    )

    op.create_index(
        "ix_authorization_decisions_agent_id_evaluated_at",
        "authorization_decisions",
        ["agent_id", "evaluated_at"],
    )

    op.create_index(
        "ix_authorization_decisions_evaluated_at",
        "authorization_decisions",
        ["evaluated_at"],
    )


def downgrade() -> None:
    """Remove the authorization decision audit store."""

    op.drop_index(
        "ix_authorization_decisions_evaluated_at",
        table_name="authorization_decisions",
    )

    op.drop_index(
        "ix_authorization_decisions_agent_id_evaluated_at",
        table_name="authorization_decisions",
    )

    op.drop_index(
        "ix_authorization_decisions_request_id",
        table_name="authorization_decisions",
    )

    op.drop_table("authorization_decisions")
