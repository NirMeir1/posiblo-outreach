"""Command line: python -m outreach <command> ...

Exit codes: 0 ok, 1 refused / failed (preflight, backup), 2 bad input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .approve import ApprovalRefused, approve_batch
from .backup import BackupError, create_backup, list_backups
from .config import ConfigError, load_config
from .dryrun import run_dry_run
from .export import export_batch
from .ingest import IngestError, ingest
from .ledger import SUPPRESSION_KINDS, Ledger, LedgerError, open_readonly, status_summary
from .message import MessageError
from .normalize import InvalidUrl
from .preflight import run_preflight
from .reopen import ReopenRefused, reopen_site
from .send import SendRefused, live_allowed, run_send

REPORTS_DIRNAME = "reports"


def _print_failures(failures: list[str]) -> None:
    print("Preflight failed:", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)


def cmd_ingest(args: argparse.Namespace) -> int:
    config = load_config()
    failures = run_preflight(config, live=False)
    if failures:
        _print_failures(failures)
        return 1
    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2
    with Ledger(config.ledger_path) as led:
        try:
            summary = ingest(csv_path, led, config.batch_size, column=args.column)
        except IngestError as e:
            print(f"ingest: {e}", file=sys.stderr)
            return 2
    print("\n".join(summary.lines()))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config()
    print(f"ledger: {config.ledger_path}")
    if config.stop_file.exists():
        print(f"STOP file present: {config.stop_file}")
    if not config.ledger_path.is_file():
        n = len(list_backups(config.backup_dir))
        print("no ledger yet" + (f" -- but {n} backup(s) exist; see preflight before running anything" if n else ""))
        return 0
    conn = open_readonly(config.ledger_path)
    try:
        s = status_summary(conn)
    finally:
        conn.close()
    print("sites by status:")
    for status, count in s["sites"].items():
        print(f"  {status:<17} {count}")
    print(f"batches: {len(s['batches'])}")
    for b in s["batches"]:
        print(f"  {b['batch_id']}  {b['state']:<13} size={b['size']}  created={b['created_at']}"
              + (f"  approved={b['approved_at']}" if b["approved_at"] else ""))
    print("suppression: " + ", ".join(f"{k}={v}" for k, v in s["suppression"].items()))
    print(f"backups: {len(list_backups(config.backup_dir))} in {config.backup_dir}")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    config = load_config()
    try:
        result = create_backup(config)
    except BackupError as e:
        print(f"BACKUP FAILED: {e}", file=sys.stderr)
        return 1
    print(f"backup written: {result.local}")
    if result.offsite:
        print(f"offsite backup written: {result.offsite}")
    if result.pruned:
        print(f"pruned {len(result.pruned)} old backup(s)")
    return 0


def cmd_suppress_add(args: argparse.Namespace) -> int:
    config = load_config()
    # A STOP file must not prevent recording an opt-out, so the STOP check is skipped here.
    failures = run_preflight(config, live=False, require_no_stop=False)
    if failures:
        _print_failures(failures)
        return 1
    with Ledger(config.ledger_path) as led:
        try:
            added = led.add_suppression(args.kind, args.value, reason=args.reason)
        except (ValueError, InvalidUrl) as e:
            print(f"suppress: {e}", file=sys.stderr)
            return 2
        led.add_event("info", f"suppress add {args.kind} ({'new' if added else 'already present'})")
    print(("added" if added else "already suppressed") + f": {args.kind} {args.value}")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    config = load_config()
    failures = run_preflight(config, live=False)
    if failures:
        _print_failures(failures)
        return 1
    with Ledger(config.ledger_path) as led:
        try:
            report = run_dry_run(config, led, args.batch_id)
        except (ValueError, LedgerError, MessageError) as e:
            print(f"dry-run: {e}", file=sys.stderr)
            return 2
    return 0 if report.completed else 1


def cmd_approve(args: argparse.Namespace) -> int:
    config = load_config()
    failures = run_preflight(config, live=False)
    if failures:
        _print_failures(failures)
        return 1
    with Ledger(config.ledger_path) as led:
        try:
            approve_batch(led, args.batch_id)
        except ApprovalRefused as e:
            print(f"approve: {e}", file=sys.stderr)
            return 1
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    config = load_config()
    if not config.ledger_path.is_file():
        print(f"no ledger at {config.ledger_path}", file=sys.stderr)
        return 1
    conn = open_readonly(config.ledger_path)
    try:
        path = export_batch(conn, args.batch_id, config.root / REPORTS_DIRNAME)
    except ValueError as e:
        print(f"export: {e}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(f"report written: {path}")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    import os
    # First thing, before reading config or opening anything: the ALLOW_LIVE gate.
    if not live_allowed(os.environ):
        print("Live sending is disabled (ALLOW_LIVE is not set to 1). Nothing was sent.", file=sys.stderr)
        return 1
    config = load_config()
    with Ledger(config.ledger_path) as led:
        try:
            report = run_send(config, led, args.batch_id, environ=os.environ)
        except SendRefused as e:
            print(f"send refused: {e}", file=sys.stderr)
            return 1
    return 1 if report.halted_reason else 0


def cmd_reopen(args: argparse.Namespace) -> int:
    config = load_config()
    failures = run_preflight(config, live=False, require_no_stop=False)
    if failures:
        _print_failures(failures)
        return 1
    with Ledger(config.ledger_path) as led:
        try:
            reopen_site(led, args.site_key)
        except ReopenRefused as e:
            print(f"reopen: {e}", file=sys.stderr)
            return 1
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    # Imported here, not at module top: send/dry-run never load Flask or the dashboard.
    from .dashboard import serve
    serve(load_config(), port=args.port)
    return 0


def cmd_clear_stop(args: argparse.Namespace) -> int:
    config = load_config()
    stop = config.stop_file
    if not stop.exists():
        print(f"no STOP file at {stop}")
        return 0
    typed = input(f"Remove {stop} and allow runs again? Type CLEAR to confirm: ").strip()
    if typed != "CLEAR":
        print("not cleared", file=sys.stderr)
        return 1
    stop.unlink()
    if config.ledger_path.is_file():
        with Ledger(config.ledger_path) as led:
            led.add_event("warning", "STOP file cleared from the command line")
    print(f"STOP file removed: {stop}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m outreach",
                                description="Posiblo outreach: one consent-request message per site, sent once.")
    sub = p.add_subparsers(dest="command", required=True, metavar="command")

    sp = sub.add_parser("ingest", help="read a CSV of website URLs and plan batches (CSV is never modified)")
    sp.add_argument("csv", help="path to the input CSV")
    sp.add_argument("--column", help="name of the URL column, if it cannot be detected")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("status", help="show counts per status, batches and suppression (read-only)")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("backup", help="back up the ledger (sqlite backup API), keep the newest 30")
    sp.set_defaults(func=cmd_backup)

    sp = sub.add_parser("suppress", help="manage the suppression list")
    ssub = sp.add_subparsers(dest="suppress_command", required=True, metavar="action")
    sa = ssub.add_parser("add", help="never contact this domain, email or phone")
    sa.add_argument("kind", choices=SUPPRESSION_KINDS)
    sa.add_argument("value")
    sa.add_argument("--reason", default=None)
    sa.set_defaults(func=cmd_suppress_add)

    sp = sub.add_parser("dry-run", help="visit each site of a batch and report what would be sent (sends nothing)")
    sp.add_argument("batch_id")
    sp.set_defaults(func=cmd_dry_run)

    sp = sub.add_parser("approve", help="approve a dry-run batch (type the batch id to confirm); freezes the list")
    sp.add_argument("batch_id")
    sp.set_defaults(func=cmd_approve)

    sp = sub.add_parser("export", help="write reports/<batch_id>-<timestamp>.csv (never overwrites)")
    sp.add_argument("batch_id")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("send", help="LIVE: send the approved batch (requires ALLOW_LIVE=1; disabled by default)")
    sp.add_argument("batch_id")
    sp.set_defaults(func=cmd_send)

    sp = sub.add_parser("reopen", help="make a site plannable again after no_form/captcha/login/robots/unclear")
    sp.add_argument("site_key")
    sp.set_defaults(func=cmd_reopen)

    sp = sub.add_parser("dashboard", help="read-only monitoring page on http://127.0.0.1 (with a STOP button)")
    sp.add_argument("--port", type=int, default=8765)
    sp.set_defaults(func=cmd_dashboard)

    sp = sub.add_parser("clear-stop", help="remove the STOP file (type CLEAR to confirm); only possible here")
    sp.set_defaults(func=cmd_clear_stop)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as e:
        print(f"configuration error: {e}", file=sys.stderr)
        return 2
