"""create query metric snapshots table

Revision ID: 20260310_01
Revises:
Create Date: 2026-03-10 22:00:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_metric_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("db_identifier", sa.String(length=255), nullable=False),
        sa.Column("queryid", sa.String(length=128), nullable=False),
        sa.Column("dbid", sa.Integer(), nullable=False),
        sa.Column("userid", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("total_exec_time_ms", sa.Float(), nullable=False),
        sa.Column("mean_exec_time_ms", sa.Float(), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("shared_blks_hit", sa.Integer(), nullable=False),
        sa.Column("shared_blks_read", sa.Integer(), nullable=False),
        sa.Column("shared_blks_dirtied", sa.Integer(), nullable=False),
        sa.Column("shared_blks_written", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "captured_at",
            "db_identifier",
            "queryid",
            "dbid",
            "userid",
            name="uq_query_metric_snapshot_point",
        ),
    )
    op.create_index(
        "ix_query_metric_snapshots_db_identifier_captured_at",
        "query_metric_snapshots",
        ["db_identifier", "captured_at"],
        unique=False,
    )
    op.create_index(
        "ix_query_metric_snapshots_queryid_captured_at",
        "query_metric_snapshots",
        ["queryid", "captured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_query_metric_snapshots_queryid_captured_at",
        table_name="query_metric_snapshots",
    )
    op.drop_index(
        "ix_query_metric_snapshots_db_identifier_captured_at",
        table_name="query_metric_snapshots",
    )
    op.drop_table("query_metric_snapshots")
