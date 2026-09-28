"""The Sentinel service: ties config, probes, store and metrics together."""

from __future__ import annotations

from typing import Dict, List, Optional

from . import probes
from .core import evaluate, summarize
from .metrics import Metrics
from .models import CheckResult, Target
from .store import HistoryStore

# Dispatch table keyed by target kind. Probes are looked up on the module
# object at call time so tests can monkeypatch ``probes.probe_*``.
_PROBES = {
    "http": "probe_http",
    "tcp": "probe_tcp",
    "dns": "probe_dns",
}


class Sentinel:
    """Runs checks over a fixed set of targets and records the outcomes."""

    def __init__(
        self,
        targets: List[Target],
        store: Optional[HistoryStore] = None,
        metrics: Optional[Metrics] = None,
    ) -> None:
        self.targets = list(targets)
        self.store = store or HistoryStore()
        self.metrics = metrics or Metrics()

    def _probe(self, target: Target) -> dict:
        func_name = _PROBES.get(target.kind)
        if func_name is None:  # pragma: no cover - guarded by Target validator
            raise ValueError(f"unknown target kind: {target.kind}")
        probe = getattr(probes, func_name)
        return probe(target)

    def run_once(self) -> List[CheckResult]:
        """Probe every target once, evaluate, record and update metrics."""
        batch: List[CheckResult] = []
        for target in self.targets:
            raw = self._probe(target)
            result = evaluate(target, raw)
            self.store.record(result)
            self.metrics.observe(result)
            batch.append(result)
        return batch

    def status(self) -> Dict[str, dict]:
        """Return the per-target summary across all recorded history."""
        return summarize(self.store.all_history())
