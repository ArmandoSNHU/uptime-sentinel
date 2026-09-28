"""uptime-sentinel: a small self-hosted synthetic-monitoring service.

Checks a configured list of targets (HTTP status+latency, TCP port,
DNS resolution), records results, computes uptime, exposes Prometheus
metrics, and serves a minimal HTML status page.

The package keeps a strict separation between pure logic (``core``) and
side-effecting probes (``probes``) so the bulk of the behaviour can be
tested without touching the network.
"""

__version__ = "0.1.0"
