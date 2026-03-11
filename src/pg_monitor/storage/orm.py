from __future__ import annotations

import datetime as dt  # noqa: TC003

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class QueryMetricSnapshotOrm(Base):
    __tablename__ = "query_metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "captured_at",
            "db_identifier",
            "queryid",
            "dbid",
            "userid",
            name="uq_query_metric_snapshot_point",
        ),
        Index(
            "ix_query_metric_snapshots_db_identifier_captured_at",
            "db_identifier",
            "captured_at",
        ),
        Index(
            "ix_query_metric_snapshots_queryid_captured_at",
            "queryid",
            "captured_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    db_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    queryid: Mapped[str] = mapped_column(String(128), nullable=False)
    dbid: Mapped[int] = mapped_column(Integer, nullable=False)
    userid: Mapped[int] = mapped_column(Integer, nullable=False)
    query: Mapped[str] = mapped_column(String, nullable=False)
    calls: Mapped[int] = mapped_column(Integer, nullable=False)
    total_exec_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    mean_exec_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_blks_hit: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_blks_read: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_blks_dirtied: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_blks_written: Mapped[int] = mapped_column(Integer, nullable=False)
