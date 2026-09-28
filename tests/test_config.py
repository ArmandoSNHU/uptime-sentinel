"""Tests for configuration loading and validation."""

from pathlib import Path

import pytest

from sentinel.config import ConfigError, load_targets

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "targets.json"


def test_loads_example_targets():
    targets = load_targets(EXAMPLES)
    kinds = {t.kind for t in targets}
    assert len(targets) == 3
    assert kinds == {"http", "tcp", "dns"}
    names = {t.name for t in targets}
    assert "example-web" in names


def test_rejects_malformed_target(tmp_path):
    # http target missing its required 'url'.
    bad = tmp_path / "bad.json"
    bad.write_text('[{"name": "broken", "kind": "http"}]', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_targets(bad)


def test_rejects_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_targets(bad)


def test_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_targets(tmp_path / "does-not-exist.json")
