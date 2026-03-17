from __future__ import annotations

import uuid

from pg_monitor.api import REQUEST_ID_HEADER


def test_healthz_endpoint_returns_ok(client) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert REQUEST_ID_HEADER in response.headers
    expected = response.headers[REQUEST_ID_HEADER]
    assert uuid.UUID(expected).hex == expected


def test_healthz_uses_incoming_request_id(client) -> None:
    response = client.get("/healthz", headers={REQUEST_ID_HEADER: "req-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-123"


def test_openapi_endpoint_is_available(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["openapi"].startswith("3.")
