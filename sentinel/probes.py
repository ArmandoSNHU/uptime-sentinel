"""Live network probes.

Each probe performs a single side-effecting check and returns a raw
dictionary describing what happened. No interpretation of "up vs down"
lives here -- that belongs to :mod:`sentinel.core.evaluate`, which keeps
these functions trivial to monkeypatch in tests.

Only the standard library is used (urllib / socket); no third-party HTTP
client is pulled in.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from .models import Target


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def probe_http(target: Target) -> Dict[str, Any]:
    """Issue an HTTP GET and report the status code and latency."""
    start = time.perf_counter()
    request = urllib.request.Request(target.url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=target.timeout) as response:
            status = response.status
        return {"status": status, "ms": _elapsed_ms(start), "error": None}
    except urllib.error.HTTPError as exc:
        # An HTTP error is still a valid status code we can compare against.
        return {"status": exc.code, "ms": _elapsed_ms(start), "error": None}
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        return {"status": None, "ms": _elapsed_ms(start), "error": str(exc)}


def probe_tcp(target: Target) -> Dict[str, Any]:
    """Attempt a TCP connection to ``host:port``."""
    start = time.perf_counter()
    try:
        with socket.create_connection((target.host, target.port), timeout=target.timeout):
            pass
        return {"connected": True, "ms": _elapsed_ms(start), "error": None}
    except (socket.timeout, OSError) as exc:
        return {"connected": False, "ms": _elapsed_ms(start), "error": str(exc)}


def probe_dns(target: Target) -> Dict[str, Any]:
    """Resolve ``hostname`` to a list of addresses."""
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(target.hostname, None)
        addresses = sorted({info[4][0] for info in infos})
        return {"addresses": addresses, "ms": _elapsed_ms(start), "error": None}
    except (socket.gaierror, OSError) as exc:
        return {"addresses": None, "ms": _elapsed_ms(start), "error": str(exc)}
