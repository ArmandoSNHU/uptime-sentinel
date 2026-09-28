"""In-memory, bounded history of check results keyed by target name."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

from .models import CheckResult


class HistoryStore:
    """Keep the most recent ``maxlen`` results for each target.

    The store is deliberately in-memory only; it is enough for a single
    process synthetic monitor and keeps the surface small.
    """

    def __init__(self, maxlen: int = 100) -> None:
        self.maxlen = maxlen
        self._history: Dict[str, Deque[CheckResult]] = defaultdict(
            lambda: deque(maxlen=maxlen)
        )

    def record(self, result: CheckResult) -> None:
        """Append a result to the target's ring buffer."""
        self._history[result.name].append(result)

    def history(self, name: str) -> List[CheckResult]:
        """Return the recorded results for ``name`` (oldest first)."""
        return list(self._history.get(name, ()))

    def latest(self, name: str) -> Optional[CheckResult]:
        """Return the most recent result for ``name``, or ``None``."""
        bucket = self._history.get(name)
        return bucket[-1] if bucket else None

    def all_latest(self) -> Dict[str, CheckResult]:
        """Return the most recent result for every known target."""
        return {name: bucket[-1] for name, bucket in self._history.items() if bucket}

    def all_history(self) -> Dict[str, List[CheckResult]]:
        """Return the full history for every known target."""
        return {name: list(bucket) for name, bucket in self._history.items()}
