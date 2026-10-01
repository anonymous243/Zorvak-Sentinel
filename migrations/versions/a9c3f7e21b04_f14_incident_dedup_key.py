"""f14_incident_dedup_key

Revision ID: a9c3f7e21b04
Revises: f12b1b37632d
Create Date: 2026-09-22 12:15:00.000000

F-14: Incident Creation Race Condition — Migration Safety Hardened

WHAT THIS MIGRATION DOES
========================

1.  Adds incidents.dedup_key VARCHAR(64) (nullable initially).
2.  Backfills dedup_key for ALL existing incidents using the same
    deterministic formula as incident_detector.py:
        SHA-256("v1:INCIDENT_DEDUP:<tenant_id>:<rule_id>:<agent_id|''>")
3.  Detects logical duplicates among OPEN incidents BEFORE creating the
    unique index.  If any logical (tenant, rule, agent) triple has more
    than one OPEN incident, the migration raises MigrationError and
    leaves the schema unchanged so operators can investigate.
4.  Creates a partial unique index:
        CREATE UNIQUE INDEX uix_incidents_dedup_key_open
        ON incidents (dedup_key) WHERE status = 'OPEN';
5.  For PostgreSQL: adds a CHECK constraint enforcing NOT NULL dedup_key
    for OPEN incidents.  SQLite relies on the application layer.

MIGRATION SAFETY CONTRACT
==========================
- Pre-existing logical OPEN duplicates  -> MIGRATION FAILS (descriptive error)
- Pre-existing OPEN rows without dedup_key (legacy) -> backfilled safely
- Pre-existing RESOLVED/CLOSED rows -> backfilled for completeness
- Empty incidents table -> index created immediately
- No data is deleted, merged, or modified outside backfill

DOWNGRADE
=========
Drops CHECK constraint (PostgreSQL), partial unique index, and column.
Existing rows are not modified.
"""
import hashlib
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'a9c3f7e21b04'
down_revision: Union[str, Sequence[str], None] = 'f12b1b37632d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class MigrationError(Exception):
    """Raised when the migration cannot proceed safely."""


def _derive_dedup_key(tenant_id: str, rule_id: str, agent_id) -> str:
    """
    Deterministic incident dedup key — must exactly match
    incident_detector.derive_incident_dedup_key().
    Defined inline to keep the migration self-contained.
    """
    canonical = f"v1:INCIDENT_DEDUP:{tenant_id}:{rule_id}:{agent_id or ''}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Add nullable dedup_key column.
    # ------------------------------------------------------------------
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('dedup_key', sa.String(length=64), nullable=True)
        )

    # ------------------------------------------------------------------
    # Step 2: Backfill all existing rows deterministically.
    # ------------------------------------------------------------------
    rows = conn.execute(
        text("SELECT id, tenant_id, detection_rule_id, agent_id FROM incidents")
    ).fetchall()

    for row in rows:
        key = _derive_dedup_key(row.tenant_id, row.detection_rule_id, row.agent_id)
        conn.execute(
            text("UPDATE incidents SET dedup_key = :key WHERE id = :id"),
            {"key": key, "id": row.id},
        )

    # ------------------------------------------------------------------
    # Step 3: Detect pre-existing logical OPEN duplicates.
    # Fail loudly — do not silently merge, delete, or choose a winner.
    # ------------------------------------------------------------------
    duplicate_rows = conn.execute(text("""
        SELECT tenant_id, detection_rule_id, agent_id, dedup_key, COUNT(*) AS cnt
        FROM incidents
        WHERE status = 'OPEN'
        GROUP BY tenant_id, detection_rule_id, agent_id, dedup_key
        HAVING COUNT(*) > 1
    """)).fetchall()

    if duplicate_rows:
        details = "\n".join(
            f"  tenant={r.tenant_id} rule={r.detection_rule_id} "
            f"agent={r.agent_id!r} open_count={r.cnt}"
            for r in duplicate_rows
        )
        raise MigrationError(
            "F-14 migration cannot proceed safely.\n"
            "Pre-existing logical OPEN incident duplicates detected:\n"
            f"{details}\n\n"
            "Resolution: investigate each group, resolve to exactly one OPEN "
            "incident per logical identity, then re-run 'alembic upgrade'.\n"
            "DO NOT delete rows automatically without operator review."
        )

    # Sanity: confirm all rows are now populated (should always pass after backfill).
    null_count = conn.execute(
        text("SELECT COUNT(*) FROM incidents WHERE dedup_key IS NULL")
    ).scalar()
    if null_count:
        raise MigrationError(
            f"F-14 backfill incomplete: {null_count} row(s) still have NULL dedup_key."
        )

    # ------------------------------------------------------------------
    # Step 4: Create partial unique index (safe — no duplicates, all backfilled).
    # ------------------------------------------------------------------
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.create_index(
            'uix_incidents_dedup_key_open',
            ['dedup_key'],
            unique=True,
            sqlite_where=sa.text("status = 'OPEN'"),
            postgresql_where=sa.text("status = 'OPEN'"),
        )

    # ------------------------------------------------------------------
    # Step 5: PostgreSQL CHECK constraint — NOT NULL for OPEN incidents.
    # SQLite cannot add CHECK constraints via ALTER TABLE; the application
    # layer (incident_detector.py) enforces this invariant instead.
    # ------------------------------------------------------------------
    if conn.dialect.name == 'postgresql':
        conn.execute(text(
            "ALTER TABLE incidents "
            "ADD CONSTRAINT chk_open_incident_has_dedup_key "
            "CHECK (status <> 'OPEN' OR dedup_key IS NOT NULL)"
        ))


def downgrade() -> None:
    conn = op.get_bind()

    if conn.dialect.name == 'postgresql':
        conn.execute(text(
            "ALTER TABLE incidents "
            "DROP CONSTRAINT IF EXISTS chk_open_incident_has_dedup_key"
        ))

    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.drop_index('uix_incidents_dedup_key_open')
        batch_op.drop_column('dedup_key')
