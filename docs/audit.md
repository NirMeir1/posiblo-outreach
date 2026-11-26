# Skeptical audit (Prompt 7)

Goal: try to break the send-once guarantee and the safety rules in CLAUDE.md.

- **Behavior:** this audit changed no behavior in `src/`. Every behavior fix is a proposal (A, B, C below) waiting for the owner's approval.
- **What was committed:** new tests for gaps, the README, this report and the validation script.
- **Line numbers** refer to commit `5c5843e` plus this audit's commit.

## 1. Every code path that performs an HTTP POST

| Where | What | Verdict |
|---|---|---|
| `src/outreach/send.py:158` in `_post_once()` | `client.stream("POST", plan.action_url, ...)` | **The only POST the tool makes.** |
| `src/outreach/dashboard.py`, route `/stop` | Flask route that *receives* a POST from the local dashboard page | Not a request the tool makes. Loopback only; Host and Origin are checked. |
| `src/outreach/dashboard.html` | Browser `fetch("/stop", {method: "POST"})` to the local dashboard | Browser to 127.0.0.1 only; creates the STOP file. |

- **One caller:** `_post_once()` is called once, at `send.py:248` in `_Run._send_one()`, and not inside any loop in that function.
- **One entry point:** `_send_one` ← `_Run.run` ← `run_send` ← `cli.cmd_send` ← `python -m outreach send`. Only `cli.py` imports `send.py`.
- **No other way out:**
  - `fetch.Fetcher` only calls `stream("GET", ...)`.
  - Both HTTP clients use `follow_redirects=False` (`fetch.py:141`, `send.py:324`), so a redirect can never be replayed as a second POST.
  - httpx is used without retries (its default), and no retry library is installed.
- **Claim first.** Before line 248 come the claim at `send.py:237` (`Ledger.claim()`, which runs `BEGIN IMMEDIATE`, `INSERT ... ON CONFLICT DO NOTHING`, then `COMMIT` before returning) and the send-log "claimed" line at `send.py:243`, which is fsynced. If `claim()` returns False, the function returns before the POST.
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
| A tldextract upgrade that changes the bundled public-suffix list | A previously sent site could get a new key | `form_url` UNIQUE catches the common case. Residual risk 6: pin the dependency versions. |

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
- **Gap: restoring an old backup.** If the ledger is restored from a backup older than the last send, nothing notices that the send log has claims the ledger lacks. Sites sent after that backup could be contacted again. → **Proposal C.**
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

Current code (`src/outreach/fetch.py`, `_fetch_robots`, lines 249–273):

| robots.txt result | Today | Your rule | Test |
|---|---|---|---|
| 404 / 410 (missing) | **allowed** | allowed ✔ | `test_robots_404_means_allow_and_page_is_fetched`, `test_robots_status_handling[404-True]`, `[410-True]` |
| 5xx | **disallow** | disallow ✔ | `test_robots_status_handling[500-False]`, `[503-False]` |
| Network error (unreachable) | **disallow** | disallow ✔ | `test_robots_network_error_means_disallow` |
| Timeout | **disallow** | disallow ✔ | `test_robots_timeout_means_disallow` |
| 401 / 403 | disallow | allowed ✘ | `test_robots_status_handling[401-False]`, `[403-False]` |
| 429 | allowed | allowed ✔ | `test_robots_429_is_currently_treated_as_allow` |
| Redirect to another domain | disallow | allowed ✘ | none |
| More than 3 redirects | disallow | allowed ✘ | none |
| Body over 2 MB | disallow | allowed ✘ | none |

So 404 already means "allowed", and network errors and 5xx already mean "disallow". The four ✘ rows violate "only network errors and 5xx". **Proposal B** fixes them: any 4xx is allowed; robots redirects are followed up to 3 hops, including to another host, where only robots.txt is read; more hops count as "no robots.txt"; an oversized file is parsed up to the cap.

My recommendation, one exception to your rule: treat **429 Too Many Requests** like 5xx (disallow for this run). It means "slow down", not "no file". RFC 9309 groups it with other 4xx, but Google treats it as a server error. Proposal B follows your rule as written; tell me if you want the 429 exception.

### 10.2 POST encoding

It does **not** follow the form's charset today: `_post_once()` always encodes in UTF-8 (`send.py`, `urlencode(pairs, encoding="utf-8")`). **Proposal A** fixes this:
- The plan takes the charset from `accept-charset` (the first label Python knows), else the encoding the page was decoded with, else UTF-8.
- The POST encodes with it. Characters the charset cannot represent become `&#NNNN;`, as browsers do.
- The charset is part of the approved-plan comparison. Plans approved before the change compare as UTF-8.

### 10.3 reopen: remove or wire up?

**Recommendation: wire it up.**
- **The gap:** today no code ever writes `no_form`, `captcha`, `login_required`, `robots_blocked` or `unclear_fields` into `sites`. Dry-run must not write `sites`, and `send` only skips such sites (they stay unclaimed). So `reopen` works and is tested, but has nothing to act on.
- **Why wire it up rather than remove:**
  1. CLAUDE.md lists these as *site statuses*, so they are meant to be in the ledger.
  2. Without them, sites that cannot be contacted are re-planned after every finished batch. Each one is then fetched again in every later dry-run: repeated visits to sites that showed a CAPTCHA or a login wall, which is not polite.
  3. Once they are recorded, `reopen` becomes the deliberate, logged way to retry a site after it changes. It already refuses anything where a POST may have happened.
- **Suggested wiring (not implemented):** when a `send` run finishes a batch, record each non-ready dry-run outcome of that batch as a final status without any POST. That means a `claim()` immediately followed by `finish(<status>)`, plus a send-log line marked `posted: false`, so proposal C's consistency check stays exact.
- **Alternative:** if you'd rather keep the tool smaller, remove `reopen` and its tests. Nothing else depends on it.

## 11. Proposals waiting for approval (not applied)

Each one was made in a scratchpad copy of the repo and the full suite was run there. With A, B and C applied together, 435 tests pass. The patches are in `docs/proposals/` (`A-post-charset.patch`, `B-robots-status-rule.patch`, `C-sendlog-ledger-check.patch`). Each applies cleanly with `git apply docs/proposals/<file>`, on its own or after the others.

| | Change | Files | Tests in the copy |
|---|---|---|---|
| A | POST uses the form's charset (accept-charset → page encoding → UTF-8) | `fetch.py`, `classify.py`, `finder.py`, `send.py` + `tests/test_charset.py` | 429 pass |
| B | robots.txt: only network errors and 5xx disallow; follow redirects; parse oversized files up to the cap | `fetch.py` + `tests/test_fetch.py` | 421 pass |
| C | Preflight refuses when send-log claims are missing from the ledger (restored from an old backup) | `preflight.py` + `tests/test_preflight.py`; validation P2.4's expected check order gains `sendlog_consistency` | 417 pass |

## 12. Residual risks, ranked

1. **Restoring an older backup can lead to a second message.** Nothing compares the send log with the ledger. *Mitigation now:* the README's restore steps say to check by hand. *Fix:* proposal C.
2. **The legal basis is unresolved.** The message is pending legal review. *Mitigation:* `ALLOW_LIVE` gate, defaults off, docs.
3. **`sent_unconfirmed` may hide real sends, and `sent` may be a false positive.** Success detection is a heuristic: a new "תודה"/"thank you" text, or a thank/success redirect. Never retrying keeps send-once intact, but the counts can be wrong in either direction.
4. **Hebrew can arrive garbled** on Windows-1255 sites, because the POST is always UTF-8. *Fix:* proposal A.
5. **Hand-copying `ledger.db` without its `-wal` file loses claims.** *Mitigation:* README warning, the `backup` command, and the test that proves the risk.
6. **Dependency drift:** unpinned versions (for example a tldextract public-suffix update) could change site keys or behavior. *Suggestion:* pin exact versions (a lock file) before live use.
7. **One business with two domains** can get two messages. Inherent to per-site keys.
8. **The robots.txt policy is stricter than your rule** for 401/403, redirects and large files. That's polite but loses some sites. *Fix:* proposal B.
9. **Backups are not fsynced before the rename.** After power loss the newest backup could be incomplete. Low.
10. **Two concurrent `send` runs** cost one extra GET per site and confuse the dashboard's run status. Send-once still holds (tested).
11. **`reopen` has nothing to act on** until no-POST outcomes are recorded. See 10.3.
