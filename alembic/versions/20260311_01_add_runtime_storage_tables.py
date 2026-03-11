"""add runtime storage tables

Revision ID: 20260311_01
Revises: 20260310_01
Create Date: 2026-03-11 13:20:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260311_01"
down_revision = "20260310_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("db_identifier", sa.String(length=255), nullable=False),
        sa.Column("active_connections", sa.BigInteger(), nullable=False),
        sa.Column("blocked_sessions", sa.BigInteger(), nullable=False),
        sa.Column("longest_tx_duration_s", sa.Float(), nullable=True),
        sa.Column("waiting_locks", sa.BigInteger(), nullable=False),
        sa.Column("granted_locks", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_snapshots_db_identifier_captured_at",
        "runtime_snapshots",
        ["db_identifier", "captured_at"],
        unique=False,
    )

    op.create_table(
        "runtime_database_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("runtime_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("datid", sa.BigInteger(), nullable=False),
        sa.Column("datname", sa.String(length=255), nullable=False),
        sa.Column("numbackends", sa.BigInteger(), nullable=False),
        sa.Column("xact_commit", sa.BigInteger(), nullable=False),
        sa.Column("xact_rollback", sa.BigInteger(), nullable=False),
        sa.Column("blks_read", sa.BigInteger(), nullable=False),
        sa.Column("blks_hit", sa.BigInteger(), nullable=False),
        sa.Column("deadlocks", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["runtime_snapshot_id"],
            ["runtime_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_database_snapshots_runtime_snapshot_id_datname",
        "runtime_database_snapshots",
        ["runtime_snapshot_id", "datname"],
        unique=False,
    )

    op.create_table(
        "runtime_current",
        sa.Column("db_identifier", sa.String(length=255), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_connections", sa.BigInteger(), nullable=False),
        sa.Column("blocked_sessions", sa.BigInteger(), nullable=False),
        sa.Column("longest_tx_duration_s", sa.Float(), nullable=True),
        sa.Column("waiting_locks", sa.BigInteger(), nullable=False),
        sa.Column("granted_locks", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("db_identifier"),
    )

    op.create_table(
        "runtime_database_current",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("db_identifier", sa.String(length=255), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("datid", sa.BigInteger(), nullable=False),
        sa.Column("datname", sa.String(length=255), nullable=False),
        sa.Column("numbackends", sa.BigInteger(), nullable=False),
        sa.Column("xact_commit", sa.BigInteger(), nullable=False),
        sa.Column("xact_rollback", sa.BigInteger(), nullable=False),
        sa.Column("blks_read", sa.BigInteger(), nullable=False),
        sa.Column("blks_hit", sa.BigInteger(), nullable=False),
        sa.Column("deadlocks", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "db_identifier",
            "datname",
            name="uq_runtime_database_current_db_identifier_datname",
        ),
    )
    op.create_index(
        "ix_runtime_database_current_db_identifier",
        "runtime_database_current",
        ["db_identifier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_database_current_db_identifier",
        table_name="runtime_database_current",
    )
    op.drop_table("runtime_database_current")
    op.drop_table("runtime_current")
    op.drop_index(
        "ix_runtime_database_snapshots_runtime_snapshot_id_datname",
        table_name="runtime_database_snapshots",
    )
    op.drop_table("runtime_database_snapshots")
    op.drop_index(
        "ix_runtime_snapshots_db_identifier_captured_at",
        table_name="runtime_snapshots",
    )
    op.drop_table("runtime_snapshots")
