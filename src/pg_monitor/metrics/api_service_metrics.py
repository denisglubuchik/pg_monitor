from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    GCCollector,
    Histogram,
    PlatformCollector,
    ProcessCollector,
)


class ServiceMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        ProcessCollector(registry=self.registry)
        GCCollector(registry=self.registry)
        PlatformCollector(registry=self.registry)

        self.http_requests_total = Counter(
            "pg_monitor_http_requests_total",
            "Total HTTP requests served by API.",
            ["method", "path", "status_code"],
            registry=self.registry,
        )
        self.http_request_duration_seconds = Histogram(
            "pg_monitor_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            ["method", "path", "status_code"],
            registry=self.registry,
        )

    def observe_http_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        status_label = str(status_code)
        labels = {
            "method": method,
            "path": path,
            "status_code": status_label,
        }
        self.http_requests_total.labels(**labels).inc()
        self.http_request_duration_seconds.labels(**labels).observe(
            max(duration_seconds, 0.0)
        )
