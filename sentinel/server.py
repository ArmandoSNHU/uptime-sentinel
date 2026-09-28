"""FastAPI application exposing the monitor over HTTP.

Endpoints
---------
* ``GET /health``   -- liveness probe.
* ``GET /metrics``  -- Prometheus text exposition.
* ``POST /run``     -- trigger a single check pass and return the results.
* ``GET /status``   -- JSON per-target summary.
* ``GET /``         -- a minimal, dependency-free HTML status page.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse

from . import __version__
from .config import load_targets
from .service import Sentinel

CONTENT_TYPE_PROMETHEUS = "text/plain; version=0.0.4; charset=utf-8"

_DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "examples" / "targets.json"


def _config_path() -> Path:
    return Path(os.environ.get("SENTINEL_CONFIG", str(_DEFAULT_CONFIG)))


def create_app(sentinel: Sentinel | None = None) -> FastAPI:
    """Build the FastAPI app, wiring in a Sentinel instance."""
    if sentinel is None:
        sentinel = Sentinel(load_targets(_config_path()))

    app = FastAPI(title="uptime-sentinel", version=__version__)
    app.state.sentinel = sentinel

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__, "targets": len(sentinel.targets)}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(content=sentinel.metrics.render(), media_type=CONTENT_TYPE_PROMETHEUS)

    @app.post("/run")
    def run() -> JSONResponse:
        results = sentinel.run_once()
        return JSONResponse([r.model_dump() for r in results])

    @app.get("/status")
    def status() -> dict:
        return sentinel.status()

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(_render_page(sentinel))

    return app


def _render_page(sentinel: Sentinel) -> str:
    summary = sentinel.status()
    rows = []
    for target in sentinel.targets:
        info = summary.get(target.name)
        if info and info["checks"] > 0:
            up = bool(info["last_ok"])
            uptime = info["uptime_pct"]
            last_ms = info["last_ms"]
            detail = info["last_detail"]
        else:
            up = None
            uptime = 0.0
            last_ms = 0.0
            detail = "no data yet"

        if up is True:
            state_class, badge = "up", "UP"
        elif up is False:
            state_class, badge = "down", "DOWN"
        else:
            state_class, badge = "unknown", "?"

        rows.append(
            f"""      <tr class="{state_class}">
        <td class="name">{html.escape(target.name)}</td>
        <td class="kind">{html.escape(target.kind)}</td>
        <td><span class="badge {state_class}">{badge}</span></td>
        <td class="num">{uptime:.2f}%</td>
        <td class="num">{last_ms:.2f} ms</td>
        <td class="detail">{html.escape(str(detail))}</td>
      </tr>"""
        )

    table_body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>uptime-sentinel</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      margin: 0; padding: 2rem; background: #0f1420; color: #e6e9ef;
    }}
    h1 {{ margin: 0 0 .25rem; font-size: 1.4rem; }}
    p.sub {{ margin: 0 0 1.5rem; color: #9aa4b2; font-size: .9rem; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
    th, td {{ padding: .6rem .75rem; text-align: left; border-bottom: 1px solid #232a3a; }}
    th {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; color: #9aa4b2; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    td.detail {{ color: #9aa4b2; font-size: .85rem; }}
    .badge {{
      display: inline-block; padding: .15rem .55rem; border-radius: 999px;
      font-size: .75rem; font-weight: 600; color: #0f1420;
    }}
    .badge.up {{ background: #3fb950; }}
    .badge.down {{ background: #f85149; color: #fff; }}
    .badge.unknown {{ background: #6e7681; color: #fff; }}
    tr.up td.name {{ border-left: 3px solid #3fb950; }}
    tr.down td.name {{ border-left: 3px solid #f85149; }}
    tr.unknown td.name {{ border-left: 3px solid #6e7681; }}
    footer {{ margin-top: 1.5rem; color: #6e7681; font-size: .8rem; }}
  </style>
</head>
<body>
  <h1>uptime-sentinel</h1>
  <p class="sub">Synthetic monitoring &middot; version {html.escape(__version__)} &middot; {len(sentinel.targets)} targets</p>
  <table>
    <thead>
      <tr>
        <th>Target</th><th>Kind</th><th>State</th><th>Uptime</th><th>Last latency</th><th>Detail</th>
      </tr>
    </thead>
    <tbody>
{table_body}
    </tbody>
  </table>
  <footer>POST /run to refresh &middot; /status for JSON &middot; /metrics for Prometheus</footer>
</body>
</html>"""


app = create_app()


def main() -> None:  # pragma: no cover - thin CLI entry point
    import uvicorn

    uvicorn.run(
        "sentinel.server:app",
        host=os.environ.get("SENTINEL_HOST", "0.0.0.0"),
        port=int(os.environ.get("SENTINEL_PORT", "8000")),
    )


if __name__ == "__main__":  # pragma: no cover
    main()
