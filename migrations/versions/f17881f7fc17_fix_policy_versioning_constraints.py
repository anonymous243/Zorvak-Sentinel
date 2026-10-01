"""fix_policy_versioning_constraints

Revision ID: f17881f7fc17
Revises: cf4d079607c7
Create Date: 2026-09-14 14:53:49.877247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f17881f7fc17'
down_revision: Union[str, Sequence[str], None] = 'cf4d079607c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('policy_versions', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_policy_versions_policy_id_id', ['policy_id', 'id'])
        
    bind = op.get_bind()
    if bind.engine.name == 'sqlite':
        op.execute("""
        CREATE TRIGGER trg_policy_versions_immutable
        BEFORE UPDATE ON policy_versions
        FOR EACH ROW
        WHEN NEW.effect != OLD.effect OR NEW.priority != OLD.priority 
             OR NEW.action != OLD.action OR NEW.resource != OLD.resource
             OR NEW.policy_id != OLD.policy_id OR NEW.version != OLD.version
        BEGIN
            SELECT RAISE(ABORT, 'PolicyVersion fields are immutable');
        END;
        """)
    elif bind.engine.name == 'postgresql':
        op.execute("""
        CREATE OR REPLACE FUNCTION trg_policy_versions_immutable_func()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.effect != OLD.effect OR NEW.priority != OLD.priority 
               OR NEW.action != OLD.action OR NEW.resource != OLD.resource
               OR NEW.policy_id != OLD.policy_id OR NEW.version != OLD.version THEN
                RAISE EXCEPTION 'PolicyVersion fields are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
        op.execute("""
        CREATE TRIGGER trg_policy_versions_immutable
        BEFORE UPDATE ON policy_versions
        FOR EACH ROW
        EXECUTE FUNCTION trg_policy_versions_immutable_func();
        """)

    with op.batch_alter_table('authorization_decisions', schema=None) as batch_op:
        batch_op.drop_column('policy_version')
        batch_op.create_foreign_key('fk_authorization_decisions_policy_version_id', 'policy_versions', ['policy_version_id'], ['id'])
        batch_op.create_index('ix_authorization_decisions_policy_version_id', ['policy_version_id'], unique=False)
        
    with op.batch_alter_table('policies', schema=None) as batch_op:
        batch_op.drop_constraint('fk_policy_active_version', type_='foreignkey')
        batch_op.create_foreign_key('fk_policy_active_version_composite', 'policy_versions', ['id', 'active_version_id'], ['policy_id', 'id'])


def downgrade() -> None:
    with op.batch_alter_table('policies', schema=None) as batch_op:
        batch_op.drop_constraint('fk_policy_active_version_composite', type_='foreignkey')
        batch_op.create_foreign_key('fk_policy_active_version', 'policy_versions', ['active_version_id'], ['id'])

    with op.batch_alter_table('authorization_decisions', schema=None) as batch_op:
        batch_op.drop_index('ix_authorization_decisions_policy_version_id')
        batch_op.drop_constraint('fk_authorization_decisions_policy_version_id', type_='foreignkey')
        batch_op.add_column(sa.Column('policy_version', sa.INTEGER(), nullable=True))

    bind = op.get_bind()
    if bind.engine.name == 'sqlite':
        op.execute("DROP TRIGGER IF EXISTS trg_policy_versions_immutable")
    elif bind.engine.name == 'postgresql':
        op.execute("DROP TRIGGER IF EXISTS trg_policy_versions_immutable ON policy_versions")
        op.execute("DROP FUNCTION IF EXISTS trg_policy_versions_immutable_func")

    with op.batch_alter_table('policy_versions', schema=None) as batch_op:
        batch_op.drop_constraint('uq_policy_versions_policy_id_id', type_='unique')
