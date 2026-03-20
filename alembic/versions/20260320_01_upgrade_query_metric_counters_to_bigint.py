"""upgrade query metric counters to bigint

Revision ID: 20260320_01
Revises: 20260311_01
Create Date: 2026-03-20 15:30:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260320_01"
down_revision = "20260311_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "query_metric_snapshots",
        "calls",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "rows",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_hit",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_read",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_dirtied",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_written",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_written",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_dirtied",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_read",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "shared_blks_hit",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "rows",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "query_metric_snapshots",
        "calls",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
