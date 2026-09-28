"""Tests for the Sentinel service and the FastAPI surface.

The three network probes are monkeypatched to canned raw dicts so the
whole suite runs offline.
"""

import pytest
from fastapi.testclient import TestClient

from sentinel import probes, server
from sentinel.models import Target
from sentinel.service import Sentinel

SAMPLE_TARGETS = [
    Target(name="web", kind="http", url="https://example.com", expect_status=200),
    Target(name="db-port", kind="tcp", host="example.com", port=5432),
    Target(name="name-lookup", kind="dns", hostname="example.com"),
]


@pytest.fixture
def canned_probes(monkeypatch):
    monkeypatch.setattr(
        probes, "probe_http", lambda t: {"status": 200, "ms": 11.0, "error": None}
    )
    monkeypatch.setattr(
        probes, "probe_tcp", lambda t: {"connected": True, "ms": 2.0, "error": None}
    )
    monkeypatch.setattr(
        probes,
        "probe_dns",
        lambda t: {"addresses": ["93.184.216.34"], "ms": 1.0, "error": None},
    )


def test_run_once_evaluates_all_targets(canned_probes):
    sentinel = Sentinel(SAMPLE_TARGETS)
    batch = sentinel.run_once()

    assert len(batch) == 3
    assert all(r.ok for r in batch)
    names = {r.name for r in batch}
    assert names == {"web", "db-port", "name-lookup"}
    # History was recorded.
    assert len(sentinel.store.history("web")) == 1


def test_run_once_marks_bad_http(monkeypatch):
    monkeypatch.setattr(
        probes, "probe_http", lambda t: {"status": 500, "ms": 9.0, "error": None}
    )
    sentinel = Sentinel([SAMPLE_TARGETS[0]])
    batch = sentinel.run_once()
    assert batch[0].ok is False
    assert "500" in batch[0].detail


@pytest.fixture
def client(canned_probes):
    app = server.create_app(Sentinel(SAMPLE_TARGETS))
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["targets"] == 3


def test_run_endpoint(client):
    resp = client.post("/run")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 3
    assert all(r["ok"] for r in results)


def test_status_endpoint(client):
    client.post("/run")
    resp = client.get("/status")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["web"]["uptime_pct"] == 100.0
    assert summary["web"]["checks"] == 1


def test_metrics_endpoint(client):
    client.post("/run")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "sentinel_up" in text
    assert "sentinel_check_duration_seconds" in text
    assert "sentinel_checks_total" in text


def test_index_html_lists_targets(client):
    client.post("/run")
    resp = client.get("/")
    assert resp.status_code == 200
    html_text = resp.text
    for target in SAMPLE_TARGETS:
        assert target.name in html_text
    assert "<table" in html_text
