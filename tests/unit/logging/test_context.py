from __future__ import annotations

import json
import logging

from pg_monitor.logging import (
    reset_poll_cycle_id,
    reset_queryid,
    reset_request_id,
    set_poll_cycle_id,
    set_queryid,
    set_request_id,
)
from pg_monitor.logging.structured import JsonFormatter


def test_formatter_includes_context_fields() -> None:
    request_token = set_request_id("req-001")
    poll_token = set_poll_cycle_id("poll-001")
    query_token = set_queryid("42")

    try:
        record = logging.makeLogRecord(
            {
                "name": "pg_monitor.test",
                "levelno": logging.INFO,
                "levelname": "INFO",
                "msg": "test event",
                "runtime_interval_s": 60,
                "query_interval_s": 900,
            }
        )
        formatter = JsonFormatter(service="pg-monitor", environment="dev")
        payload = json.loads(formatter.format(record))
    finally:
        reset_queryid(query_token)
        reset_poll_cycle_id(poll_token)
        reset_request_id(request_token)

    assert payload["service"] == "pg-monitor"
    assert payload["env"] == "dev"
    assert payload["request_id"] == "req-001"
    assert payload["poll_cycle_id"] == "poll-001"
    assert payload["queryid"] == "42"
    assert payload["runtime_interval_s"] == 60
    assert payload["query_interval_s"] == 900
