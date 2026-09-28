"""Loading and validating target configuration from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Union

from pydantic import ValidationError

from .models import Target


class ConfigError(Exception):
    """Raised when a configuration file is missing or invalid."""


def load_targets(path: Union[str, Path]) -> List[Target]:
    """Load a list of :class:`Target` from a JSON file.

    The file may be either a top-level JSON array of target objects, or an
    object with a ``"targets"`` key holding that array. Any structural or
    validation problem is surfaced as a :class:`ConfigError` with a clear
    message.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config file {path}: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc

    if isinstance(data, dict):
        data = data.get("targets")
    if not isinstance(data, list):
        raise ConfigError(
            f"{path}: expected a JSON array of targets "
            "(or an object with a 'targets' array)"
        )

    targets: List[Target] = []
    for index, item in enumerate(data):
        try:
            targets.append(Target.model_validate(item))
        except ValidationError as exc:
            raise ConfigError(f"{path}: invalid target at index {index}: {exc}") from exc

    if not targets:
        raise ConfigError(f"{path}: no targets defined")

    return targets
