"""dry-run <batch_id>: visit every site of a batch and record what WOULD be sent.

- Never claims and never writes the sites table. Writes only dry_run_results,
  the batch state and events.
- Read-only on the network: uses the GET-only Fetcher and the finder.
- Halts on the STOP file (checked before every site) and when the circuit
  breaker trips (consecutive fetch errors). A halted run leaves the batch in
  state `planned`, so it cannot be approved; a complete run sets
  `dry_run_done`.
- Re-running replaces the batch's previous dry-run results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

from .breaker import CircuitBreaker
from .config import PLACEHOLDER as TODO, Config
from .fetch import Fetcher
from .finder import FetcherLike, FindResult, find_contact_form
from .ledger import Ledger
from .message import message_version, render_message

READY = "ready"
FETCH_ERROR = "fetch_error"
OPTED_OUT = "opted_out"
ALREADY_HANDLED = "already_handled"
OUTCOMES = (READY, "no_form", "captcha", "login_required", "robots_blocked", "no_solicitation", "unclear_fields",
            FETCH_ERROR, OPTED_OUT, ALREADY_HANDLED)


@dataclass
class SiteOutcome:
    site_key: str
    input_url: str
    outcome: str
    form_url: str | None = None
    detail: str = ""
    plan: dict | None = None


@dataclass
class DryRunReport:
    batch_id: str
    total: int
    outcomes: list[SiteOutcome] = field(default_factory=list)
    completed: bool = False
    halted_reason: str | None = None
    message: str = ""


def start_url(input_url: str) -> str:
    """The URL the finder starts from: the input URL with a scheme and without a fragment."""
    raw = input_url.strip()
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")
    p = urlsplit(raw)
    return urlunsplit((p.scheme.lower(), p.netloc, p.path or "/", p.query, ""))


def fields_summary(plan: dict | None) -> str:
    if not plan:
        return ""
    parts = []
    for f in plan["fields"]:
        bits = f"{f['role']}{'/' + f['part'] if f.get('part') and f['part'] != 'full' else ''}->{f['name']}"
        if f["role"] == "consent":
            bits += " (required)" if f["required"] else " (optional)"
        parts.append(bits)
    if plan.get("hidden_fields"):
        parts.append(f"hidden: {', '.join(plan['hidden_fields'])}")
    if plan.get("honeypots"):
        parts.append(f"honeypot left empty: {', '.join(plan['honeypots'])}")
    return "; ".join(parts)


def format_line(i: int, n: int, so: SiteOutcome) -> str:
    line = f"[{i}/{n}] {so.site_key}  {so.outcome.upper()}  {so.form_url or '-'}"
    if so.outcome == READY:
        line += f"\n        fields: {fields_summary(so.plan)}"
    elif so.detail:
        line += f"\n        {so.detail}"
    return line


def _evaluate(site: dict, ledger: Ledger, fetcher: FetcherLike) -> SiteOutcome:
    key, url = site["site_key"], site["input_url"]
    if ledger.is_handled(key):
        status = ledger.get(key)["status"]
        return SiteOutcome(key, url, ALREADY_HANDLED, detail=f"already in the ledger with status {status}; not fetched")
    if ledger.is_suppressed("domain", key):
        return SiteOutcome(key, url, OPTED_OUT, detail="on the suppression list; not fetched")
    found: FindResult = find_contact_form(start_url(url), fetcher)
    plan = found.plan.to_dict() if found.plan is not None else None  # kept for unclear_fields too (for review)
    return SiteOutcome(key, url, found.status, found.form_url, found.detail, plan)


def run_dry_run(config: Config, ledger: Ledger, batch_id: str, *, fetcher: FetcherLike | None = None,
                out: Callable[[str], None] = print) -> DryRunReport:
    batch = ledger.get_batch(batch_id)
    if batch is None:
        raise ValueError(f"no batch {batch_id!r}")
    sites = ledger.batch_sites(batch_id)
    message = render_message(config)
    ledger.start_dry_run(batch_id)
    ledger.add_event("info", f"dry-run {batch_id} started ({len(sites)} sites)")
    report = DryRunReport(batch_id, len(sites), message=message)
    breaker = CircuitBreaker(config.breaker_threshold)
    own_fetcher = fetcher is None
    fetcher = fetcher or Fetcher(delay_seconds=config.host_delay_seconds)
    out(f"Dry-run {batch_id}: {len(sites)} site(s). Nothing is sent; nothing is claimed.")
    try:
        for i, site in enumerate(sites, 1):
            if config.stop_file.exists():
                report.halted_reason = f"STOP file found ({config.stop_file})"
                break
            so = _evaluate(site, ledger, fetcher)
            report.outcomes.append(so)
            ledger.add_dry_run_result(batch_id, so.site_key, so.outcome, so.form_url,
                                      json.dumps(so.plan, ensure_ascii=False) if so.plan else None, so.detail or None)
            out(format_line(i, len(sites), so))
            if so.outcome == FETCH_ERROR:
                if breaker.record_failure():
                    report.halted_reason = (f"circuit breaker tripped after {breaker.consecutive_failures} "
                                            f"consecutive fetch errors")
                    break
            else:
                breaker.record_success()
    finally:
        if own_fetcher:
            fetcher.close()  # type: ignore[union-attr]

    if report.halted_reason is None:
        ledger.finish_dry_run(batch_id)
        report.completed = True
        ledger.add_event("info", f"dry-run {batch_id} done")
    else:
        ledger.add_event("warning", f"dry-run {batch_id} halted: {report.halted_reason}")

    counts: dict[str, int] = {}
    for so in report.outcomes:
        counts[so.outcome] = counts.get(so.outcome, 0) + 1
    out("")
    out("Summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) +
        f"  ({len(report.outcomes)}/{len(sites)} visited)")
    if report.halted_reason:
        out(f"HALTED: {report.halted_reason}. Batch stays 'planned' and cannot be approved until a full dry-run.")
    else:
        out(f"Batch {batch_id} is now dry_run_done. Review, then: python -m outreach approve {batch_id}")
    out("")
    out(f"Message that would be sent ({message_version()}), exactly:")
    out("-" * 60)
    out(message)
    out("-" * 60)
    if TODO.lower() in config.sender_address.lower():
        out("NOTE: SENDER_ADDRESS is still TODO; live sending refuses to run until it is set.")
    return report
