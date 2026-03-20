from __future__ import annotations

import datetime as dt  # noqa: TC003

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
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
    calls: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_exec_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    mean_exec_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shared_blks_hit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shared_blks_read: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shared_blks_dirtied: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shared_blks_written: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RuntimeSnapshotOrm(Base):
    __tablename__ = "runtime_snapshots"
    __table_args__ = (
        Index(
            "ix_runtime_snapshots_db_identifier_captured_at",
            "db_identifier",
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
    active_connections: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blocked_sessions: Mapped[int] = mapped_column(BigInteger, nullable=False)
    longest_tx_duration_s: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    waiting_locks: Mapped[int] = mapped_column(BigInteger, nullable=False)
    granted_locks: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RuntimeDatabaseSnapshotOrm(Base):
    __tablename__ = "runtime_database_snapshots"
    __table_args__ = (
        Index(
            "ix_runtime_database_snapshots_runtime_snapshot_id_datname",
            "runtime_snapshot_id",
            "datname",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    runtime_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("runtime_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    datid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    datname: Mapped[str] = mapped_column(String(255), nullable=False)
    numbackends: Mapped[int] = mapped_column(BigInteger, nullable=False)
    xact_commit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    xact_rollback: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blks_read: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blks_hit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deadlocks: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RuntimeCurrentOrm(Base):
    __tablename__ = "runtime_current"

    db_identifier: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    active_connections: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blocked_sessions: Mapped[int] = mapped_column(BigInteger, nullable=False)
    longest_tx_duration_s: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    waiting_locks: Mapped[int] = mapped_column(BigInteger, nullable=False)
    granted_locks: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RuntimeDatabaseCurrentOrm(Base):
    __tablename__ = "runtime_database_current"
    __table_args__ = (
        UniqueConstraint(
            "db_identifier",
            "datname",
            name="uq_runtime_database_current_db_identifier_datname",
        ),
        Index(
            "ix_runtime_database_current_db_identifier",
            "db_identifier",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    db_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    datid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    datname: Mapped[str] = mapped_column(String(255), nullable=False)
    numbackends: Mapped[int] = mapped_column(BigInteger, nullable=False)
    xact_commit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    xact_rollback: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blks_read: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blks_hit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deadlocks: Mapped[int] = mapped_column(BigInteger, nullable=False)
