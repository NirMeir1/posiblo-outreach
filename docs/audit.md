# Skeptical audit (Prompt 7)

Goal: try to break the send-once guarantee and the safety rules in CLAUDE.md.

- **Behavior:** the audit itself (commit `2154461`) changed no behavior. Its three proposals (A, B, C) were shown as diffs and approved by the owner afterwards, with one change to B. The owner also requested four more changes. All seven are listed in `docs/proposals/APPROVED.md` and in section 13. Sections 1–12 have been updated to the current code.
- **Line numbers** refer to the current code.

## 1. Every code path that performs an HTTP POST

| Where | What | Verdict |
|---|---|---|
| `src/outreach/send.py:173` in `_post_once()` | `client.stream("POST", plan.action_url, ...)` | **The only POST the tool makes.** |
| `src/outreach/dashboard.py`, route `/stop` | Flask route that *receives* a POST from the local dashboard page | Not a request the tool makes. Loopback only; Host and Origin are checked. |
| `src/outreach/dashboard.html` | Browser `fetch("/stop", {method: "POST"})` to the local dashboard | Browser to 127.0.0.1 only; creates the STOP file. |

- **One caller:** `_post_once()` is called once, at `send.py:270` in `_Run._send_one()`, and not inside any loop in that function. The per-site `try/except Exception` around it is not a loop and never calls it again.
- **One entry point:** `_send_one` ← `_Run.run` ← `run_send` ← `cli.cmd_send` ← `python -m outreach send`. Only `cli.py` imports `send.py`.
- **No other way out:**
  - `fetch.Fetcher` only calls `stream("GET", ...)`.
  - Both HTTP clients use `follow_redirects=False` (`fetch.py:164`, `send.py:359`), so a redirect can never be replayed as a second POST.
  - httpx is used without retries (its default), and no retry library is installed.
- **Claim first.** Before line 270 come the claim at `send.py:252` (`Ledger.claim()`, which runs `BEGIN IMMEDIATE`, `INSERT ... ON CONFLICT DO NOTHING`, then `COMMIT` before returning) and the send-log "claimed" line at `send.py:264`, which is fsynced. If `claim()` returns False, the function returns before the POST.
- **Proven by mutation:** in temporary copies, moving the POST before the claim, removing the ALLOW_LIVE check, or making `claim()` always return True each makes a test fail (validation P5.7).

## 2. LLM / AI SDK scan

- **Tracked files:** I scanned every tracked file for 23 SDK names plus "claude", "gpt-N", "chatgpt" and "gemini". The only matches are the word "Claude" in `docs/build-prompts.md`, and the forbidden-name lists in `docs/validation.md` and `scripts/validate.py`.
- **Code:** no imports, calls or dependency entries.
- **Installed packages** (32 in `.venv`): no AI/LLM package.
- **`requests`:** installed as a dependency of tldextract. tldextract runs with `suffix_list_urls=()` and `cache_dir=None` (no network, tested in a subprocess with sockets disabled), and nothing in `src/` imports `requests`.

## 3. Normalizer: can two spellings of one site get different keys?

**Same key (tested):**
- scheme, case, `www.`/`www2.`, trailing dot, port, path, query and tracking parameters, fragment;
- invisible right-to-left marks and zero-width characters, full-width letters;
- Hebrew IDN versus punycode, and uppercase punycode;
- facebook `m.`/`he-il.`/`fb.com` aliases;
- percent-encoded versus raw Hebrew in platform paths.

**Different keys for what may be one business:**

| Case | Effect | Backstop |
|---|---|---|
| `example.co.il` and `example.com` (two domains) | Two sites, so two messages are possible | None. Inherent to "one message per site". |
| `user.wixsite.com` (no path) and `user.wixsite.com/site` | Two keys | `sites.form_url` is UNIQUE: if both resolve to the same form URL, the second claim returns False. |
| Facebook vanity URL and `profile.php?id=` of the same page | Two keys | robots.txt blocks facebook and these pages have no usable form, so in practice nothing is sent. |
| A tldextract upgrade that changes the bundled public-suffix list | A previously sent site could get a new key | Fixed: all versions are pinned (`pyproject.toml`, `requirements.lock`), and `tests/test_dependencies.py` fails if the installed tldextract differs. `form_url` UNIQUE remains a second backstop. |

**The other direction (one key for two businesses):** shared hosts that are not in `PLATFORMS`, such as `x.myshopify.com` or `x.web.app`, get the host's registrable domain as their key. Different businesses then collide, and only the first is ever contacted. That is the safe direction: fewer messages, never more.

## 4. Crash windows around claim, POST and finish

| Crash point | State after restart | Can it cause a second message? |
|---|---|---|
| Before `claim()` | Nothing written; site unclaimed | No, nothing was sent. The site stays eligible. |
| Inside `claim()` before COMMIT | The transaction rolls back | No. |
| After the COMMIT, before the send-log "claimed" line | Row is `pending`; the send log doesn't know it | No: pending is never retried. Manual review. |
| After "claimed", before the POST | `pending` | No. Tested both in-process and with a real `os._exit`. |
| During the POST | `pending`; the message may have arrived | No. |
| After the POST, before `finish()` | `pending` | No. |
| After `finish()`, before the send-log "result" line | Ledger final; the send log has a claim with no result | No. |
| Unexpected exception (not a crash) anywhere after the claim, also inside verify or finish | Caught per site: event logged, row left `pending` (unless finish already ran), breaker failure, run continues | No. Tested after the POST, inside verify, and before the POST. |
| After the run, closing backup fails | Printed loudly | No. |

No window exists in which a POST can happen without a committed claim.

## 5. Concurrency (two terminals at once)

- **Two `send` runs on the same batch:**
  - Both may pass the `is_handled()` pre-check and both re-fetch the page (one extra GET).
  - `claim()` uses `BEGIN IMMEDIATE`, so SQLite serializes the two claims and exactly one wins. The loser skips without a POST.
  - Tested: `test_two_terminals_sending_the_same_batch_at_once` (2 threads, separate connections, one POST per site) and `test_claim_refused_means_no_post`.
  - Cosmetic effects only: both write `run-status.json`, and the first to finish marks the batch `send_done` while the other is still running.
- **`dry-run` during `send`:** refused (`start_dry_run` only accepts `planned` and `dry_run_done`).
- **Two `ingest` runs:** batch ids are allocated inside one `BEGIN IMMEDIATE` transaction, so no duplicate ids. The same site could land in two batches, but `claim()` still allows only one message.
- **Lock waits:** the busy timeout is 10 s.
  - If `claim()` gives up waiting, it raises; nothing has been sent and the run stops.
  - If `finish()` gives up waiting, the row stays `pending` (safe, but needs manual review).

## 6. If the ledger file is deleted

- **History exists:** if backups (local or offsite) or the send log exist, `ingest`, `dry-run`, `approve`, `suppress add`, `reopen` and `send` refuse to run and print the newest backup. Tested: `test_refuses_when_ledger_missing_but_backup_exists`, `..._offsite_backup_exists`, `..._send_log_exists`, and `test_send_refused_when_ledger_missing_but_send_log_exists`.
- **Read-only commands:** `status`, `export` and `dashboard` never create the ledger.
- **Restoring an old backup (fixed, proposal C).** Preflight now compares the send log with the ledger and refuses to run when claimed sites are missing (`test_refuses_when_send_log_claims_are_missing_from_a_restored_ledger`).
- **Gap: copying `ledger.db` without its `-wal` file.** This loses committed claims, and even the table definitions; `test_raw_copy_of_ledger_file_can_lose_claims_but_backup_does_not` proves it. The README now warns against it. The `backup` command is safe.
- **Everything lost:** if the ledger, every backup and the send log are all lost, the tool starts fresh and could contact everyone again. Offsite backups are the mitigation.

## 7. Power loss

- **Ledger:**
  - WAL mode with `synchronous=FULL`: every commit is synced to disk (FlushFileBuffers on Windows) before `claim()` returns.
  - A drive that acknowledges writes it hasn't made would break this; that's outside software control.
  - On restart SQLite recovers from the WAL, and preflight runs `PRAGMA integrity_check` before every write command.
- **Send log:** each line is flushed and fsynced. A line torn by power loss is skipped when the log is read (tested).
- **Backups:** written to a `.partial` file, integrity-checked, then renamed, but not fsynced before the rename. After power loss the newest backup file could be incomplete. Preflight only checks that backups exist, not that they're intact. Low risk.

## 8. Can any code path clear or downgrade a pending, sent or sent_unconfirmed row?

No.

- **Updates:** the only UPDATE on `sites` is `finish()`: `WHERE site_key = ? AND status = 'pending'`, and it is only called right after this run's own successful claim. A `pending` row left over from a crash is never finished automatically.
- **Deletes:** the only DELETE on `sites` is `reopen()`, restricted in code to the five no-POST statuses and refused for every other status (tested).
- **Inserts:** besides `claim()`, the only INSERT into `sites` is `record_no_post_outcomes()`. It runs for a finished batch and only for those five no-POST statuses. It uses `ON CONFLICT DO NOTHING`, so an existing row (pending, sent, ...) is never touched (tested).
- **Database triggers** independently refuse to:
  - delete `pending`, `sent`, `sent_unconfirmed` or `opted_out` rows;
  - move any row back to `pending`;
  - change a `sent`/`sent_unconfirmed` row to anything except `opted_out`;
  - change an `opted_out` row;
  - change a site's key.
- **Approved list:** a batch's approved list is protected by its own triggers.
- **Validation:** P1.5 lists every write statement and fails on any other.

## 9. Personal data and git

- **Ignored:** `.gitignore` excludes `data/*` (except `data/.gitkeep`), `backups/`, `logs/` (send log, run status), `reports/`, `.env`, `*.db`, `*.db-wal`, `*.db-shm` and `STOP`.
- **Tracked:** `git ls-files` contains none of these (validation A2, which also checks the ignore rules with `git check-ignore`).
- **Owner's details in code:** the sender name, email and phone defaults in `config.py` and the template are the owner's own business contact details, which the message itself contains. No third-party personal data is tracked.
- **Test data:** test fixtures use made-up `*-example.co.il` domains.

## 10. The owner's three extra questions

### 10.1 robots.txt: "404 must mean allowed; only network errors and 5xx may mean disallow"

The current code is `src/outreach/fetch.py`, `_fetch_robots`, from line 278. It is proposal B with the owner's change: 429 means disallow.

| robots.txt result | Behaviour | Test |
|---|---|---|
| 404 / 410 (missing) | allowed | `test_robots_404_means_allow_and_page_is_fetched`, `test_robots_status_handling[404-True]`, `[410-True]` |
| 401 / 403 / other 4xx | allowed | `test_robots_401_403_mean_allow_and_page_is_fetched[401]`, `[403]`, `test_robots_status_handling[400-True]` |
| 429 | **disallow** (owner's decision) | `test_robots_429_means_disallow_and_page_is_not_requested`, `test_robots_status_handling[429-False]` |
| 5xx | disallow | `test_robots_status_handling[500-False]`, `[502-False]`, `[503-False]` |
| Network error (unreachable, DNS failure) | page not requested; reported as **fetch_error** (counts for the circuit breaker) | `test_robots_network_error_means_disallow`, `test_dns_failure_is_a_fetch_error_not_robots_blocked` |
| Timeout | page not requested; reported as **fetch_error** | `test_robots_timeout_means_disallow` |
| Redirect, also to another host | followed (up to 3 hops) | `test_robots_redirect_to_another_host_is_followed` |
| More than 3 redirects | treated as missing: allowed | `test_robots_too_many_redirects_is_treated_as_missing` |
| Body over 2 MB | parsed up to 2 MB | `test_oversized_robots_is_parsed_up_to_the_cap` |

### 10.2 POST encoding

Fixed (proposal A). The plan takes the form's charset from `accept-charset` (the first label Python knows), else the encoding the page was decoded with, else UTF-8. `_post_once()` encodes with it, and characters the charset cannot represent become `&#NNNN;`. The charset is part of the approved-plan comparison; plans approved before the change compare as UTF-8.

Tests: `tests/test_charset.py`. One of them runs a full dry-run → approve → send against a local Windows-1255 page and checks the exact bytes received, including `→` arriving as `&#8594;`.

### 10.3 reopen: remove or wire up?

Wired up, per the owner's decision.
- **What happens:** when a `send` run finishes a batch (not halted), `ledger.record_no_post_outcomes()` records that batch's dry-run outcomes `no_form`, `captcha`, `login_required`, `robots_blocked` and `unclear_fields` in `sites`.
- **How:** one INSERT per site, with the final status, no `pending` state, no request and no send-log line. A ready site is never recorded, and existing rows are never touched.
- **Effect:** later ingests skip these sites as already handled. `reopen` (still limited to these five statuses) releases one, and it can then be planned again.
- **Tests:**
  - `test_finished_batch_records_no_post_outcomes_without_any_request`;
  - `test_recorded_outcome_can_be_reopened_and_planned_again`;
  - `test_halted_by_breaker_records_nothing`;
  - `test_ready_site_skipped_at_send_time_is_not_recorded`;
  - `test_record_no_post_outcomes_only_records_the_five_statuses`.

## 11. Proposals: shown, then approved and applied

The three diffs (in `docs/proposals/`) were shown to the owner before any change. The owner approved them on 2026-11-26, with 429 → disallow added to B. All three are now applied. `docs/proposals/APPROVED.md` records every decision. Validation P7.3 requires each decision to be listed there and proven by passing tests.

| | Change | State |
|---|---|---|
| A | POST uses the form's charset | applied |
| B | robots.txt: only network errors, 5xx and 429 disallow; follow redirects; parse oversized files up to the cap | applied, with the 429 change |
| C | Preflight refuses when send-log claims are missing from the ledger | applied |

## 12. Residual risks, ranked

1. **The legal basis is unresolved.** The message is pending legal review. *Mitigation:* `ALLOW_LIVE` gate, defaults off, docs.
2. **`sent_unconfirmed` may hide real sends, and `sent` may be a false positive.** Success detection is a heuristic: a new "תודה"/"thank you" text, or a thank/success redirect. Never retrying keeps send-once intact, but the counts can be wrong in either direction.
3. **`pending` rows need a human.** After an unexpected error or a crash between the claim and the result, the row stays `pending` and a message may or may not have been sent. The dashboard and `status` show them; nothing resolves them automatically.
4. **Losing everything at once.** If the ledger, every backup and the send log are all lost, the tool would start fresh and could contact everyone again. *Mitigation:* `OFFSITE_BACKUP_DIR`.
5. **Hand-copying `ledger.db` without its `-wal` file loses claims.** *Mitigation:* README warning, the `backup` command, the proving test, and the send-log consistency check (C), which now catches the result if the send log survived.
6. **One business with two domains** can get two messages. Inherent to per-site keys.
7. **Upgrading a pinned package** could still change site keys. Pins make this a deliberate act; the lock file comments tell you to re-run the tests and review section 3 first.
8. **Backups are not fsynced before the rename.** After power loss the newest backup could be incomplete. Low.
9. **Two concurrent `send` runs** cost one extra GET per site and confuse the dashboard's run status. Send-once still holds (tested).
10. **Sites recorded as `no_form`/`captcha`/... stay skipped** until someone runs `reopen`, even if the site later adds a usable form. That is the intended trade-off: politeness over reach.

## 13. Owner decisions applied after the audit

- **Proposals A, B (+429), C:** applied; see sections 10 and 11.
- **reopen wiring:** see section 10.3.
- **Per-site error guard** (`send.py`, `_Run._send_one`, `except Exception` at line 281):
  - What it covers: everything after a successful claim, from the send-log "claimed" line through the POST, verify, finish and the send-log "result" line.
  - On any unexpected `Exception`: an `error` event is logged (saying whether the POST was attempted), the row is left as it is (pending unless finish already ran), the site counts as a breaker failure, and the run continues with the next site.
  - It cannot re-enter the POST, and nothing is retried. `BaseException` (process kill, Ctrl+C) is not caught, so the crash tests behave as before.
  - Tests: `test_exception_after_the_post_leaves_row_pending_and_run_continues`, `test_exception_inside_verify_leaves_row_pending_and_run_continues`, `test_exception_after_claim_before_post_makes_no_post`, `test_unexpected_errors_count_for_the_breaker`.
- **Suppression lookup with platform-aware keys** (`ledger.is_suppressed`, line 297):
  - `_send_one`, `dry-run` and `ingest` all call it with the **site key**, never the bare `domain` column. For platform sites that column is `facebook.com`, which would have matched every page on facebook.
  - It was already correct for `facebook.com/<page>`, `profile.php?id=`, `*.blogspot.com` and normal domains.
  - **One gap was found and fixed:** suppressing a wix account host (`user.wixsite.com`) did not block that account's sites (`user.wixsite.com/shop`). For keys with a path, the host part is now checked too.
  - A bare platform such as `facebook.com` can never be suppressed, so one suppression can never block other businesses on the platform.
  - Tests: `test_suppression_with_platform_aware_keys`, `test_a_bare_platform_can_never_be_suppressed`, `test_suppressed_platform_account_is_not_sent`.
- **Pinned dependencies:** exact pins in `pyproject.toml`; every package (direct and transitive) pinned in `requirements.lock`. `tests/test_dependencies.py` fails if `pyproject.toml` and the lock disagree, or if the installed tldextract (whose bundled suffix list decides site keys) differs from the pin.
