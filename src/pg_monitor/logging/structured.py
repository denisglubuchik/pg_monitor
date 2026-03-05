from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from .context import get_poll_cycle_id, get_queryid, get_request_id

SECRET_PATTERNS = (
    re.compile(r"(postgres(?:ql)?://[^:/\s]+:)([^@/\s]+)(@)", re.IGNORECASE),
    re.compile(
        r"((?:password|passwd|pwd|token|secret|api[_-]?key)\s*[=:]\s*)([^,\s]+)",
        re.IGNORECASE,
    ),
)


def _mask_secrets(value: str) -> str:
    masked = value
    masked = SECRET_PATTERNS[0].sub(r"\1***\3", masked)
    masked = SECRET_PATTERNS[1].sub(r"\1***", masked)
    return masked


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        message = _mask_secrets(record.getMessage())
        request_id = getattr(record, "request_id", get_request_id())
        poll_cycle_id = getattr(record, "poll_cycle_id", get_poll_cycle_id())
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "service": self._service,
            "env": self._environment,
            "component": getattr(record, "component", "app"),
            "request_id": request_id,
            "poll_cycle_id": poll_cycle_id,
            "queryid": getattr(record, "queryid", get_queryid()),
            "db_identifier": getattr(record, "db_identifier", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "error_type": getattr(record, "error_type", None),
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str, service: str, environment: str) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())

    stream_handler = logging.StreamHandler()
    formatter = JsonFormatter(service=service, environment=environment)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
