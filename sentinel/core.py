"""Pure evaluation and aggregation logic.

Nothing in this module performs I/O. Everything takes plain data in and
returns plain data out, which makes it exhaustively testable without a
network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

from .models import CheckResult, Target


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate(target: Target, raw: Mapping[str, Any]) -> CheckResult:
    """Turn a raw probe dict into a :class:`CheckResult`.

    Dispatch is by ``target.kind``. For HTTP checks the observed status is
    compared against ``target.expect_status``.
    """
    ms = float(raw.get("ms", 0.0))
    error = raw.get("error")
    ts = _now_iso()

    if error:
        return CheckResult(name=target.name, ok=False, ms=ms, detail=str(error), ts=ts)

    if target.kind == "http":
        status = raw.get("status")
        ok = status == target.expect_status
        if ok:
            detail = f"HTTP {status}"
        else:
            detail = f"HTTP {status} (expected {target.expect_status})"
        return CheckResult(name=target.name, ok=ok, ms=ms, detail=detail, ts=ts)

    if target.kind == "tcp":
        connected = bool(raw.get("connected"))
        detail = (
            f"connected to {target.host}:{target.port}"
            if connected
            else f"could not connect to {target.host}:{target.port}"
        )
        return CheckResult(name=target.name, ok=connected, ms=ms, detail=detail, ts=ts)

    if target.kind == "dns":
        addresses = raw.get("addresses") or []
        ok = len(addresses) > 0
        detail = (
            f"resolved {target.hostname} -> {', '.join(addresses)}"
            if ok
            else f"no addresses for {target.hostname}"
        )
        return CheckResult(name=target.name, ok=ok, ms=ms, detail=detail, ts=ts)

    # Should be unreachable given the Target validator, but stay defensive.
    return CheckResult(
        name=target.name, ok=False, ms=ms, detail=f"unknown kind {target.kind}", ts=ts
    )


def uptime_pct(results: List[CheckResult]) -> float:
    """Percentage (0-100) of results that were ``ok``.

    An empty list yields ``0.0``.
    """
    if not results:
        return 0.0
    ok = sum(1 for r in results if r.ok)
    return round(100.0 * ok / len(results), 2)


def summarize(results_by_target: Mapping[str, List[CheckResult]]) -> Dict[str, Any]:
    """Build a per-target summary: uptime%, last status, avg latency."""
    summary: Dict[str, Any] = {}
    for name, results in results_by_target.items():
        if results:
            last = results[-1]
            avg_ms = round(sum(r.ms for r in results) / len(results), 2)
            summary[name] = {
                "uptime_pct": uptime_pct(results),
                "last_ok": last.ok,
                "last_detail": last.detail,
                "last_ms": last.ms,
                "avg_ms": avg_ms,
                "checks": len(results),
            }
        else:
            summary[name] = {
                "uptime_pct": 0.0,
                "last_ok": None,
                "last_detail": "no data",
                "last_ms": 0.0,
                "avg_ms": 0.0,
                "checks": 0,
            }
    return summary
