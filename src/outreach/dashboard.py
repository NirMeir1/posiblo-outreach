"""python -m outreach dashboard: local, read-only monitoring page.

- Served by Flask on 127.0.0.1 only (never 0.0.0.0), as its own process:
  `send` and `dry-run` never import this module, so a dashboard problem
  cannot affect a run.
- Reads the ledger through a read-only SQLite connection (URI mode=ro),
  opened per request, plus logs/run-status.json. It cannot write the ledger.
- Every request must carry a loopback Host header (blocks DNS rebinding).
  The only write it can do is create the STOP file, via POST /stop, and only
  when the Origin is this dashboard itself. There is no way to clear STOP
  from the page: that is `python -m outreach clear-stop`.
- No external assets: one self-contained HTML page (dashboard.html).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from importlib import resources
from typing import Any

from flask import Flask, Response, abort, jsonify, request

from .config import Config
from .ledger import STATUSES, open_readonly
from .runstatus import read_status

BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK_NAMES = ("127.0.0.1", "localhost")
EVENTS_SHOWN = 50
STALE_SECONDS = 120


def open_db(config: Config) -> sqlite3.Connection:
    """The dashboard's only way to the ledger: read-only (mode=ro)."""
    return open_readonly(config.ledger_path)


def _host_ok(host: str | None, port: int) -> bool:
    if not host:
        return False
    name, _, p = host.rpartition(":") if ":" in host else (host, "", "")
    return name in LOOPBACK_NAMES and (p == "" or p == str(port))


def _origin_ok(origin: str | None, port: int) -> bool:
    return origin in {f"http://{n}:{port}" for n in LOOPBACK_NAMES}


def _current_batch(conn: sqlite3.Connection, run: dict | None) -> dict | None:
    if run and run.get("batch_id"):
        row = conn.execute("SELECT * FROM batches WHERE batch_id = ?", (run["batch_id"],)).fetchone()
        if row:
            return dict(row)
    row = conn.execute("SELECT * FROM batches ORDER BY batch_id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def snapshot(config: Config) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    run = read_status(config.log_dir)
    if run:
        try:
            age = (now - datetime.fromisoformat(run["updated_at"])).total_seconds()
        except (KeyError, ValueError):
            age = None
        run["stale"] = run.get("state") == "running" and (age is None or age > STALE_SECONDS)
    data: dict[str, Any] = {"now": now.isoformat(timespec="seconds"), "ledger_exists": config.ledger_path.is_file(),
                            "stop_file": config.stop_file.exists(), "run": run, "counters": {s: 0 for s in STATUSES},
                            "batch": None, "batches": [], "pending": [], "events": []}
    if not data["ledger_exists"]:
        return data
    conn = open_db(config)
    try:
        for status, n in conn.execute("SELECT status, COUNT(*) FROM sites GROUP BY status"):
            data["counters"][status] = n
        data["batches"] = [dict(r) for r in conn.execute(
            "SELECT batch_id, state, size, created_at, approved_at FROM batches ORDER BY batch_id DESC LIMIT 20")]
        batch = _current_batch(conn, run)
        if batch:
            bid = batch["batch_id"]
            approved = conn.execute("SELECT COUNT(*) FROM approved_sites WHERE batch_id = ?", (bid,)).fetchone()[0]
            if batch["state"] in ("approved", "sending", "send_done") and approved:
                done = conn.execute(
                    "SELECT COUNT(*) FROM approved_sites a JOIN sites s ON s.site_key = a.site_key "
                    "WHERE a.batch_id = ? AND s.status <> 'pending'", (bid,)).fetchone()[0]
                total, kind = approved, "approved sites finished (sent, sent_unconfirmed or other final status)"
            else:
                done = conn.execute("SELECT COUNT(*) FROM dry_run_results WHERE batch_id = ?", (bid,)).fetchone()[0]
                total, kind = batch["size"], "sites checked by the dry-run"
            batch.update(done=done, total=total, progress_kind=kind,
                         percent=round(100 * done / total) if total else 0)
            data["batch"] = batch
        data["pending"] = [dict(r) for r in conn.execute(
            "SELECT site_key, batch_id, form_url, claimed_at, detail FROM sites WHERE status = 'pending' "
            "ORDER BY claimed_at")]
        data["events"] = [dict(r) for r in conn.execute(
            "SELECT e.id, e.ts, e.level, e.site_key, e.message, s.status AS site_status FROM events e "
            "LEFT JOIN sites s ON s.site_key = e.site_key ORDER BY e.id DESC LIMIT ?", (EVENTS_SHOWN,))]
    finally:
        conn.close()
    return data


def create_app(config: Config, port: int = DEFAULT_PORT) -> Flask:
    app = Flask(__name__)
    page = resources.files("outreach").joinpath("dashboard.html").read_text(encoding="utf-8")

    @app.before_request
    def loopback_only() -> None:
        if not _host_ok(request.headers.get("Host"), port):
            abort(403, "Host header must be 127.0.0.1 or localhost")

    @app.get("/")
    def index() -> Response:
        return Response(page, mimetype="text/html; charset=utf-8",
                        headers={"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                                            "script-src 'self' 'unsafe-inline'; connect-src 'self'"})

    @app.get("/api/status")
    def status() -> Response:
        return jsonify(snapshot(config))

    @app.route("/stop", methods=["POST"])  # receives a POST from this page; it does not send one
    def stop() -> Response:
        if not _origin_ok(request.headers.get("Origin"), port):
            abort(403, "cross-origin request refused")
        config.stop_file.write_text(
            f"created from the dashboard at {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n",
            encoding="utf-8")
        return jsonify({"stop_file": True, "path": str(config.stop_file)})

    return app


def serve(config: Config, port: int = DEFAULT_PORT) -> None:
    app = create_app(config, port)
    print(f"dashboard: http://{BIND_HOST}:{port}/  (read-only; Ctrl+C to quit)")
    app.run(host=BIND_HOST, port=port, debug=False, use_reloader=False, threaded=True)
