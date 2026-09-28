"""Tests for the pure evaluation and aggregation logic."""

from sentinel.core import evaluate, summarize, uptime_pct
from sentinel.models import CheckResult, Target


def _http(name="web", expect=200):
    return Target(name=name, kind="http", url="https://example.com", expect_status=expect)


def _tcp(name="port"):
    return Target(name=name, kind="tcp", host="example.com", port=443)


def _dns(name="dns"):
    return Target(name=name, kind="dns", hostname="example.com")


def test_evaluate_http_good_status():
    result = evaluate(_http(), {"status": 200, "ms": 12.5, "error": None})
    assert result.ok is True
    assert result.ms == 12.5
    assert "200" in result.detail


def test_evaluate_http_bad_status():
    result = evaluate(_http(expect=200), {"status": 503, "ms": 8.0, "error": None})
    assert result.ok is False
    assert "503" in result.detail
    assert "expected 200" in result.detail


def test_evaluate_http_error():
    result = evaluate(_http(), {"status": None, "ms": 4.0, "error": "timed out"})
    assert result.ok is False
    assert result.detail == "timed out"


def test_evaluate_tcp_ok():
    result = evaluate(_tcp(), {"connected": True, "ms": 3.0, "error": None})
    assert result.ok is True
    assert "connected" in result.detail


def test_evaluate_tcp_fail():
    result = evaluate(_tcp(), {"connected": False, "ms": 5.0, "error": None})
    assert result.ok is False
    assert "could not connect" in result.detail


def test_evaluate_dns_ok():
    result = evaluate(_dns(), {"addresses": ["93.184.216.34"], "ms": 2.0, "error": None})
    assert result.ok is True
    assert "93.184.216.34" in result.detail


def test_evaluate_dns_fail():
    result = evaluate(_dns(), {"addresses": [], "ms": 2.0, "error": None})
    assert result.ok is False
    assert "no addresses" in result.detail


def _mk(name, ok):
    return CheckResult(name=name, ok=ok, ms=10.0, detail="x", ts="2026-01-01T00:00:00+00:00")


def test_uptime_pct_all_up():
    results = [_mk("a", True) for _ in range(4)]
    assert uptime_pct(results) == 100.0


def test_uptime_pct_mixed():
    results = [_mk("a", True), _mk("a", False), _mk("a", True), _mk("a", True)]
    assert uptime_pct(results) == 75.0


def test_uptime_pct_empty():
    assert uptime_pct([]) == 0.0


def test_summarize():
    by_target = {
        "a": [
            CheckResult(name="a", ok=True, ms=10.0, detail="HTTP 200", ts="t1"),
            CheckResult(name="a", ok=False, ms=20.0, detail="timeout", ts="t2"),
        ],
        "b": [],
    }
    summary = summarize(by_target)

    assert summary["a"]["uptime_pct"] == 50.0
    assert summary["a"]["last_ok"] is False
    assert summary["a"]["last_detail"] == "timeout"
    assert summary["a"]["last_ms"] == 20.0
    assert summary["a"]["avg_ms"] == 15.0
    assert summary["a"]["checks"] == 2

    assert summary["b"]["checks"] == 0
    assert summary["b"]["last_ok"] is None
    assert summary["b"]["uptime_pct"] == 0.0
