"""send <batch_id>: live sending, locked behind several gates.

Gates, all checked BEFORE any network call (run_send):
  1. live_allowed(): the environment variable ALLOW_LIVE equals exactly "1";
  2. preflight in live mode passes (no STOP file, ledger healthy and present,
     template present, no TODO in the sender details);
  3. the batch is approved and has a frozen approved list;
  4. the message renders;
  5. a fresh backup was just created.
Without ALLOW_LIVE=1 nothing is opened, fetched or sent.

Per approved site, in this exact order (_send_one):
  1. re-fetch the form page and rebuild the FormPlan (fresh tokens); if the
     form differs from the approved plan, skip (event, not claimed);
  2. claim(site_key): committed to disk before anything is sent; False -> skip;
  3. send log "claimed" (fsync);
  4. build the message and POST it ONCE (_post_once, the only POST in src/);
  5. verify by rules -> finish(sent) or finish(sent_unconfirmed);
  6. send log "result" (fsync); update the circuit breaker.
No retry after a POST attempt. Problems BEFORE the claim leave the site
unclaimed (an event is logged), so it can be planned in a future batch.
Any unexpected error AFTER the claim (also inside verify or finish) is caught
per site: an event is logged, the row stays as it is (pending unless finish
already ran), the breaker counts a failure, and the run goes on to the next
site. Nothing is retried and there is never a second POST.
When the batch finishes (not halted), its dry-run outcomes no_form, captcha,
login_required, robots_blocked and unclear_fields are recorded in the ledger
with no POST (never a ready site), so `reopen` can release them later.
After the run (complete or halted) a backup is created.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable, Mapping
from urllib.parse import unquote, urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup

from .backup import BackupError, create_backup
from .breaker import CircuitBreaker
from .classify import READY, FormPlan, MappedField, build_plan
from .config import Config
from .fetch import MAX_BODY_BYTES, TIMEOUT_SECONDS, USER_AGENT, Fetcher, decode_body
from .finder import captcha_marker, choose_form, visible_text
from .ledger import SENDABLE_BATCH_STATES, Ledger
from .message import MessageError, message_version, render_message
from .preflight import run_preflight
from .runstatus import write_status
from .sendlog import EVENT_CLAIMED, EVENT_RESULT, SendLog

SUBJECT = "פרסומת - בקשת הסכמה"
SUCCESS_TEXTS = ("תודה", "ההודעה נשלחה", "נשלח בהצלחה", "thank you", "message sent", "we will get back to you")
SUCCESS_REDIRECT_HINTS = ("thank", "thanks", "success", "תודה")
_REDIRECT_CODES = {301, 302, 303, 307, 308}

SENT = "sent"
SENT_UNCONFIRMED = "sent_unconfirmed"
ERROR = "error"  # unexpected error after the claim; the ledger row is left as it is (normally pending)


def live_allowed(environ: Mapping[str, str]) -> bool:
    """The single ALLOW_LIVE gate: live sending only if ALLOW_LIVE is exactly "1"."""
    return environ.get("ALLOW_LIVE") == "1"


class SendRefused(RuntimeError):
    pass


@dataclass
class SiteSend:
    site_key: str
    result: str          # sent | sent_unconfirmed | skipped | fetch_error
    detail: str = ""
    posted: bool = False


@dataclass
class SendReport:
    batch_id: str
    sites: list[SiteSend] = field(default_factory=list)
    halted_reason: str | None = None
    backup: str | None = None
    recorded: list[tuple[str, str]] = field(default_factory=list)  # no-POST outcomes recorded at the end


@dataclass
class PostOutcome:
    status_code: int | None = None
    location: str | None = None
    text: str = ""
    error: str | None = None


# --- plan comparison ------------------------------------------------------

def plan_signature(plan: FormPlan | dict) -> dict:
    """What must not change between approval and sending. Hidden VALUES (tokens) may change."""
    d = plan.to_dict() if isinstance(plan, FormPlan) else plan
    return {
        "action_url": d["action_url"],
        "method": d["method"],
        "encoding": d["encoding"],
        "fields": sorted((f["name"], f["role"], f.get("part"), bool(f["required"])) for f in d["fields"]),
        "hidden": sorted(d.get("hidden_fields", {})),
        "honeypots": sorted(d.get("honeypots", [])),
        "charset": d.get("charset", "utf-8"),
    }


def plan_differences(fresh: FormPlan, approved: dict) -> list[str]:
    a, b = plan_signature(fresh), plan_signature(approved)
    return [k for k in a if a[k] != b[k]]


# --- message payload ------------------------------------------------------

def _name_value(f: MappedField, full_name: str) -> str:
    parts = full_name.split()
    if f.part == "first" and parts:
        return parts[0]
    if f.part == "last" and len(parts) > 1:
        return " ".join(parts[1:])
    return full_name


def build_payload(plan: FormPlan, config: Config, message: str) -> list[tuple[str, str]]:
    """Fields to submit: fresh hidden tokens, sender details, the message, empty honeypots.

    A consent checkbox is ticked only if the form requires it.
    """
    pairs: list[tuple[str, str]] = list(plan.hidden_fields.items())
    for f in plan.fields:
        if f.role == "name":
            pairs.append((f.name, _name_value(f, config.sender_name)))
        elif f.role == "email":
            pairs.append((f.name, config.sender_email))
        elif f.role == "phone":
            pairs.append((f.name, config.sender_phone))
        elif f.role == "subject":
            pairs.append((f.name, SUBJECT))
        elif f.role == "message":
            pairs.append((f.name, message))
        elif f.role == "consent" and f.required:
            pairs.append((f.name, f.value or "on"))
    pairs += [(name, "") for name in plan.honeypots]
    if plan.submit:
        pairs.append(plan.submit)
    return pairs


# --- the single POST --------------------------------------------------------

def _post_once(client: httpx.Client, plan: FormPlan, pairs: list[tuple[str, str]]) -> PostOutcome:
    """THE ONLY HTTP POST IN THIS CODEBASE. Exactly one attempt; never retried; never raises for HTTP errors.

    Values are encoded in the form's charset (accept-charset, else the page encoding, else UTF-8), like a
    browser; characters the charset cannot represent become HTML character references (&#NNNN;).
    """
    charset = plan.charset or "utf-8"
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(plan.form_url))
    headers = {"Referer": plan.form_url, "Origin": origin}
    if plan.encoding == "multipart/form-data":
        kwargs = {"files": [(k, (None, v.encode(charset, "xmlcharrefreplace"))) for k, v in pairs]}
    else:
        kwargs = {"content": urlencode(pairs, encoding=charset, errors="xmlcharrefreplace").encode("ascii")}
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with client.stream("POST", plan.action_url, headers=headers, **kwargs) as resp:
            body, total = [], 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > MAX_BODY_BYTES:
                    break
                body.append(chunk)
            text = decode_body(b"".join(body), resp.headers.get("content-type"))
            return PostOutcome(resp.status_code, resp.headers.get("location"), text)
    except httpx.HTTPError as e:
        return PostOutcome(error=f"{type(e).__name__}: {e}")


def verify(outcome: PostOutcome, before_html: str) -> tuple[str, str]:
    """Rule-based success check. A phrase counts only if it was NOT already on the form page."""
    if outcome.error:
        return SENT_UNCONFIRMED, f"error during POST: {outcome.error}"
    code = outcome.status_code or 0
    if code in _REDIRECT_CODES and outcome.location:
        loc = unquote(outcome.location).lower()
        hint = next((h for h in SUCCESS_REDIRECT_HINTS if h in loc), None)
        if hint:
            return SENT, f"HTTP {code} redirect to {outcome.location} ({hint!r})"
        return SENT_UNCONFIRMED, f"HTTP {code} redirect to {outcome.location} (no success hint)"
    if code >= 400:
        return SENT_UNCONFIRMED, f"HTTP {code} after POST"
    after = visible_text(BeautifulSoup(outcome.text, "lxml"))
    before = visible_text(BeautifulSoup(before_html, "lxml"))
    phrase = next((p for p in SUCCESS_TEXTS if p in after and p not in before), None)
    if phrase:
        return SENT, f"HTTP {code}, success text {phrase!r}"
    return SENT_UNCONFIRMED, f"HTTP {code}, no success text found"


# --- the run ----------------------------------------------------------------

class _Run:
    def __init__(self, config: Config, ledger: Ledger, batch_id: str, fetcher: Fetcher, client: httpx.Client,
                 out: Callable[[str], None]):
        self.config, self.ledger, self.batch_id = config, ledger, batch_id
        self.fetcher, self.client, self.out = fetcher, client, out
        self.sendlog = SendLog(config.send_log_path)
        self.message = render_message(config)
        self.version = message_version()

    def _skip(self, key: str, why: str, result: str = "skipped") -> SiteSend:
        self.ledger.add_event("warning", f"send {self.batch_id}: {result}: {why}", site_key=key)
        return SiteSend(key, result, why)

    def _send_one(self, site: dict) -> SiteSend:
        key = site["site_key"]
        if self.ledger.is_handled(key):
            return self._skip(key, f"already in the ledger ({self.ledger.get(key)['status']}); not sent again")
        if self.ledger.is_suppressed("domain", key):
            return self._skip(key, "on the suppression list")
        approved = json.loads(site["fields_json"])

        # Step 1: re-fetch the form page and rebuild the plan (fresh tokens). Nothing is claimed yet.
        page = self.fetcher.get(site["form_url"])
        if not page.ok:
            return self._skip(key, f"re-fetch failed: {page.outcome}: {page.detail}", result="fetch_error")
        form, _ = choose_form(BeautifulSoup(page.text, "lxml"))
        if form is None:
            return self._skip(key, "form no longer found on the page")
        marker = captcha_marker(page.text)
        if marker:
            return self._skip(key, f"form page now has a CAPTCHA ({marker})")
        rebuilt = build_plan(form, page.url, page.encoding)
        if rebuilt.status != READY or rebuilt.plan is None:
            return self._skip(key, f"form no longer usable: {rebuilt.detail}")
        plan = rebuilt.plan
        diffs = plan_differences(plan, approved)
        if diffs:
            return self._skip(key, f"form changed since approval ({', '.join(diffs)}); not sent")
        if not self.fetcher.robots_allows(plan.action_url):
            return self._skip(key, f"robots.txt does not allow the form target {plan.action_url}")
        payload = build_payload(plan, self.config, self.message)

        # Step 2: claim. Committed to disk before anything is sent.
        if not self.ledger.claim(key, domain=site["domain"], input_url=site["input_url"], batch_id=self.batch_id,
                                 form_url=site["form_url"], message_version=self.version,
                                 source_url=page.url):
            return self._skip(key, "claim refused: the site is already in the ledger")

        # From here on the site is claimed. Any unexpected error (before or after the POST, including in
        # verify or finish) leaves the row as it is (pending unless finish already ran), is logged as an
        # event, counts as a failure for the breaker, and the run continues with the next site.
        # There is no retry and no second POST: this block runs once per claimed site.
        post_attempted = False
        try:
            # Step 3: send log "claimed" (flushed + fsynced).
            self.sendlog.append(EVENT_CLAIMED, site_key=key, batch_id=self.batch_id, form_url=site["form_url"],
                                action_url=plan.action_url, message_version=self.version)

            # Step 4: the one POST. No retry, whatever happens.
            self.fetcher.wait_turn(plan.action_url)
            post_attempted = True
            outcome = _post_once(self.client, plan, payload)

            # Step 5: verify and finish.
            status, detail = verify(outcome, page.text)
            self.ledger.finish(key, status, detail)

            # Step 6: send log "result" (flushed + fsynced).
            self.sendlog.append(EVENT_RESULT, site_key=key, batch_id=self.batch_id, status=status, detail=detail)
            self.ledger.add_event("info" if status == SENT else "warning",
                                  f"send {self.batch_id}: {status}: {detail}", site_key=key)
            return SiteSend(key, status, detail, posted=True)
        except Exception as e:  # noqa: BLE001 - by design: one site's failure must not stop the batch
            try:
                row = self.ledger.get(key)
                state = row["status"] if row else "missing"
            except Exception:  # noqa: BLE001 - reporting only
                state = "unknown (ledger not readable)"
            detail = (f"unexpected error after the claim ({'POST was attempted' if post_attempted else 'no POST made'}"
                      f"): {type(e).__name__}: {e}; ledger row is {state}; not retried")
            try:
                self.ledger.add_event("error", f"send {self.batch_id}: error: {detail}", site_key=key)
            except Exception:  # noqa: BLE001 - the event is best effort; the row itself is what matters
                pass
            return SiteSend(key, ERROR, detail, posted=post_attempted)

    def _status(self, state: str, index: int, total: int, site_key: str | None, breaker: CircuitBreaker,
                halted_reason: str | None = None) -> None:
        write_status(self.config.log_dir, mode="send", batch_id=self.batch_id, state=state, index=index,
                     total=total, site_key=site_key, breaker=breaker.state(), halted_reason=halted_reason)

    def run(self, sites: list[dict], report: SendReport) -> None:
        breaker = CircuitBreaker(self.config.breaker_threshold)
        for i, site in enumerate(sites, 1):
            if self.config.stop_file.exists():
                report.halted_reason = f"STOP file found ({self.config.stop_file})"
                break
            self._status("running", i, len(sites), site["site_key"], breaker)
            r = self._send_one(site)
            report.sites.append(r)
            self.out(f"[{i}/{len(sites)}] {r.site_key}  {r.result.upper()}  {r.detail}")
            if r.result in (SENT_UNCONFIRMED, "fetch_error", ERROR):
                if breaker.record_failure():
                    report.halted_reason = (f"circuit breaker tripped after {breaker.consecutive_failures} "
                                            "consecutive failures")
                    break
            elif r.result == SENT:
                breaker.record_success()
        self._status("halted" if report.halted_reason else "finished", len(report.sites), len(sites), None,
                     breaker, report.halted_reason)


def run_send(config: Config, ledger: Ledger, batch_id: str, *, environ: Mapping[str, str] | None = None,
             fetcher: Fetcher | None = None, transport: httpx.BaseTransport | None = None,
             out: Callable[[str], None] = print) -> SendReport:
    environ = os.environ if environ is None else environ
    # Gate 1: ALLOW_LIVE, before anything else.
    if not live_allowed(environ):
        raise SendRefused("live sending is disabled: ALLOW_LIVE is not set to 1. Nothing was sent.")
    # Gate 2: preflight in live mode (STOP, ledger, template, no TODO sender details).
    failures = run_preflight(config, live=True)
    if failures:
        raise SendRefused("preflight failed: " + " | ".join(failures))
    # Gate 3: the batch is approved and has a frozen list.
    batch = ledger.get_batch(batch_id)
    if batch is None:
        raise SendRefused(f"no batch {batch_id!r}")
    if batch["state"] not in SENDABLE_BATCH_STATES:
        raise SendRefused(f"batch {batch_id} is {batch['state']}; only an approved batch can be sent")
    sites = ledger.approved_sites(batch_id)
    if not sites:
        raise SendRefused(f"batch {batch_id} has no approved sites")
    # Gate 4: the message renders.
    try:
        render_message(config)
    except MessageError as e:
        raise SendRefused(f"message: {e}") from None
    # Gate 5: a fresh backup, just now.
    try:
        before = create_backup(config)
    except BackupError as e:
        raise SendRefused(f"backup before sending failed: {e}") from None
    out(f"backup written: {before.local}")

    report = SendReport(batch_id)
    ledger.begin_send(batch_id)
    ledger.add_event("info", f"send {batch_id} started ({len(sites)} approved sites)")
    own_fetcher = fetcher is None
    fetcher = fetcher or Fetcher(delay_seconds=config.host_delay_seconds, transport=transport)
    client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(fetcher.timeout or TIMEOUT_SECONDS),
                          follow_redirects=False, trust_env=False, transport=transport)
    completed = False
    try:
        _Run(config, ledger, batch_id, fetcher, client, out).run(sites, report)
        completed = True
    finally:
        client.close()
        if own_fetcher:
            fetcher.close()
        if completed and not report.halted_reason:
            ledger.finish_send(batch_id)
            ledger.add_event("info", f"send {batch_id} finished")
            # The batch is finished: record its no-POST dry-run outcomes (never `ready` sites) so they are
            # not re-planned and re-fetched in later batches. `reopen` can release them again.
            try:
                report.recorded = ledger.record_no_post_outcomes(batch_id)
                if report.recorded:
                    ledger.add_event("info", f"send {batch_id}: recorded {len(report.recorded)} no-POST outcome(s) "
                                             f"from the dry-run: {report.recorded}")
                    out(f"recorded {len(report.recorded)} site(s) where nothing could be sent "
                        f"(no message): {', '.join(f'{k}={s}' for k, s in report.recorded)}")
            except Exception as e:  # noqa: BLE001 - must not prevent the closing backup
                ledger.add_event("error", f"send {batch_id}: recording no-POST outcomes failed: {e}")
                out(f"RECORDING NO-POST OUTCOMES FAILED: {e}")
        else:
            ledger.add_event("error", f"send {batch_id} halted: {report.halted_reason or 'unexpected error'}")
            if not completed:
                write_status(config.log_dir, mode="send", batch_id=batch_id, state="halted",
                             index=len(report.sites), total=len(sites), site_key=None, breaker=None,
                             halted_reason="unexpected error (see events)")
        try:
            after = create_backup(config)
            report.backup = str(after.local)
            out(f"backup written: {after.local}")
        except BackupError as e:  # never hide the run's own outcome or exception
            out(f"BACKUP AFTER SEND FAILED: {e}")
    if report.halted_reason:
        out(f"HALTED: {report.halted_reason}")
    return report
