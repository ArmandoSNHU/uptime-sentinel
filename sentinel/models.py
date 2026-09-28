"""Pydantic data models shared across the service."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Kind = Literal["http", "tcp", "dns"]


class Target(BaseModel):
    """A single monitored endpoint.

    The relevant connection fields depend on ``kind``:

    * ``http`` uses ``url`` (and ``expect_status``).
    * ``tcp`` uses ``host`` and ``port``.
    * ``dns`` uses ``hostname``.
    """

    name: str
    kind: Kind
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    hostname: Optional[str] = None
    expect_status: int = 200
    timeout: float = 5.0

    @model_validator(mode="after")
    def _check_kind_fields(self) -> "Target":
        if self.kind == "http" and not self.url:
            raise ValueError("http target requires 'url'")
        if self.kind == "tcp" and (not self.host or self.port is None):
            raise ValueError("tcp target requires 'host' and 'port'")
        if self.kind == "dns" and not self.hostname:
            raise ValueError("dns target requires 'hostname'")
        return self


class CheckResult(BaseModel):
    """The outcome of evaluating a single probe against a target."""

    name: str
    ok: bool
    ms: float
    detail: str
    ts: str
