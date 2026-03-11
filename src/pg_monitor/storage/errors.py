from __future__ import annotations


class StorageError(Exception):
    """Base exception for storage module errors."""


class StorageSchemaError(StorageError):
    """Raised when storage schema initialization fails."""


class StorageWriteError(StorageError):
    """Raised when snapshot write fails."""


class StorageReadError(StorageError):
    """Raised when snapshot read fails."""

