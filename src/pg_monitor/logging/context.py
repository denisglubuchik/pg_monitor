from __future__ import annotations

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_poll_cycle_id: ContextVar[str | None] = ContextVar(
    "poll_cycle_id", default=None
)
_queryid: ContextVar[str | None] = ContextVar("queryid", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def get_poll_cycle_id() -> str | None:
    return _poll_cycle_id.get()


def get_queryid() -> str | None:
    return _queryid.get()


def set_request_id(value: str | None) -> Token[str | None]:
    return _request_id.set(value)


def set_poll_cycle_id(value: str | None) -> Token[str | None]:
    return _poll_cycle_id.set(value)


def set_queryid(value: str | None) -> Token[str | None]:
    return _queryid.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def reset_poll_cycle_id(token: Token[str | None]) -> None:
    _poll_cycle_id.reset(token)


def reset_queryid(token: Token[str | None]) -> None:
    _queryid.reset(token)
