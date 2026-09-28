"""Prometheus metrics for the monitor.

Each :class:`Metrics` instance owns its own registry so multiple
``Sentinel`` instances (for example one per test) never collide on the
global default registry.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from .models import CheckResult


class Metrics:
    """Holds the gauge, histogram and counter for check outcomes."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()

        self.up = Gauge(
            "sentinel_up",
            "Whether the target was up (1) or down (0) at the last check.",
            ["target"],
            registry=self.registry,
        )
        self.duration = Histogram(
            "sentinel_check_duration_seconds",
            "Duration of each check in seconds.",
            ["target"],
            registry=self.registry,
        )
        self.checks = Counter(
            "sentinel_checks_total",
            "Total number of checks performed, labelled by outcome.",
            ["target", "outcome"],
            registry=self.registry,
        )

    def observe(self, result: CheckResult) -> None:
        """Update all metrics from a single check result."""
        self.up.labels(target=result.name).set(1 if result.ok else 0)
        self.duration.labels(target=result.name).observe(result.ms / 1000.0)
        outcome = "up" if result.ok else "down"
        self.checks.labels(target=result.name, outcome=outcome).inc()

    def render(self) -> bytes:
        """Render the registry in Prometheus text exposition format."""
        return generate_latest(self.registry)
