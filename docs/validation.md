# Validation protocol for the posiblo-outreach build

## How to use this file

After you finish each prompt from docs/build-prompts.md, and BEFORE you suggest a commit message, run this protocol: the "Always" checks plus the section for the prompt you just finished.

- Report a table: check id, PASS or FAIL, evidence (command output, file and line, test name). No check may be skipped or summarized as "looks fine".
- If anything fails: fix it, rerun the WHOLE protocol, and only then report. If you cannot fix it, stop and explain.
- Never edit this file. Never do work from a later prompt, with one exception: after Prompt 0, create `scripts/validate.py` (stdlib only) that automates the mechanical checks below (A2, A3, A4, A6 and the static scans such as "no POST in src"), runnable as `python scripts/validate.py --step N`. Extend it at each step.
- The environment is Windows PowerShell. Do not use grep or bash; use Python or PowerShell.
- Append one line per step to docs/validation-log.md: date, step number, pytest test count, PASS or FAIL.

## Always (after every prompt)

- A1. `python -m pytest -q` passes. Report the number of tests. No unexplained skipped or xfail tests. The count must not be lower than at the previous step (see the log).
- A2. `git ls-files` contains none of: data/* (except data/.gitkeep), *.db, *.db-wal, *.db-shm, backups/, logs/, reports/, .env, STOP.
- A3. pyproject.toml and src/ contain no LLM or AI SDK (anthropic, openai, google-generativeai, langchain, litellm, cohere, mistralai, transformers, or similar), in dependencies or imports.
- A4. CLAUDE.md exists and still contains all 10 hard rules, the status list and the conventions.
- A5. No test or code contacts a real website: tests use only 127.0.0.1/localhost servers; no real domain is ever fetched.
- A6. Scope: list the files added or changed in this step. Flag any file or module that belongs to a later prompt.
- A7. From Prompt 2 on: the sample CSV used by tests is byte-identical before and after any command that reads it.
- A8. From Prompt 2 on: `python -m outreach --help` runs and lists the commands that exist so far.

## After Prompt 0

- Directories exist: src/outreach/, tests/, tests/fixtures/, templates/, data/ (with .gitkeep), docs/.
- .gitignore contains every entry required by Prompt 0.
- pyproject.toml: python >= 3.11; runtime dependencies exactly httpx, beautifulsoup4, lxml, tldextract; pytest as dev dependency; nothing else.
- CLAUDE.md matches the Prompt 0 text (10 rules, statuses, conventions).
- src/ contains only package scaffolding, no functional code. README.md is a stub.
- scripts/validate.py was created and runs for step 0.

## After Prompt 1

- Normalizer: at least 30 table-driven cases, including Hebrew/IDN domains, .co.il, platform URLs (facebook, instagram, linktr.ee, wixsite, blogspot) and invalid input. www., trailing dot, ports, tracking params and fragments do not change the key. www.example.co.il, example.co.il and shop.example.co.il share one key; two different pages on facebook.com do not.
- tldextract is configured without network access (suffix_list_urls=() or equivalent). Show the line.
- Ledger opens with WAL and synchronous=FULL. Prove it by querying `PRAGMA journal_mode` and `PRAGMA synchronous` (expect wal and 2) in a test or in the script.
- claim() is a single INSERT that does nothing on conflict, returns True only for the call that created the row, and the commit is durable before it returns. Show the code.
- No code path updates or deletes a site row except finish() moving a `pending` row to a final status. Search src/ for UPDATE and DELETE statements and list them.
- Tests exist and pass for: second claim returns False; same site via different URL spellings returns False; concurrent claim (real threads or processes, at least 8 workers, repeated) has exactly one winner; crash after claim without finish leaves the row pending and it is not offered as work again; suppression blocks a suppressed domain.
- Mutation check, in a TEMPORARY COPY of the repo (never in the working tree): make claim() always return True, and separately remove its commit. At least one test must fail in each case. Delete the temporary copy afterwards and say so.

## After Prompt 2

- Every setting in config.py is documented in README. Sender address defaults to TODO.
- Backups use the sqlite3 backup API (show the call), never a raw file copy of the database. Test: the backup opens, passes integrity_check, and only the newest 30 are kept. The OFFSITE_BACKUP_DIR copy works and a failed copy raises.
- Send log: append-only JSONL, each write flushed and fsynced (show os.fsync).
- Preflight checks in the required order. A test proves it REFUSES to run when the ledger file is missing but a backup or the send log exists. Integrity check is included. TODO placeholders are rejected in live mode only.
- Breaker trips exactly at the threshold (test at N-1 and N).
- templates/consent_request_v1.txt matches character for character the Hebrew text in Prompt 2 of docs/build-prompts.md (compare programmatically). A docs note says the text is pending legal review.
- ingest: drops invalid URLs, duplicates inside the file, already-handled and suppressed sites; creates batches of the configured size in state `planned`; never modifies the CSV (A7). Commands ingest, status, backup, suppress add exist.
- No site fetching or form code exists yet.

## After Prompt 3

- No POST or form submission anywhere in src/: scan for `.post(`, `"POST"`, `method=` with POST in client calls, `.request("POST"`. Expect nothing.
- No Playwright, Selenium or similar in dependencies.
- Fetcher: User-Agent is exactly "PosibloOutreachBot/1.0 (+https://posiblo.com; posiblo.contact@gmail.com)"; robots.txt cached per host; a robots-disallowed page is NOT requested (test asserts the test server saw no request for it) and yields robots_blocked; per-host delay applied; 15s timeout; 2 MB body cap (test with a larger body); max 3 redirects, same registrable domain only; no retry logic.
- tests/fixtures/ has about 12 fixtures covering every case in Prompt 3. Report the list.
- Finder, classifier and detectors are tested against them: captcha, login_required, no_form, no_solicitation, newsletter-only and search forms excluded, honeypot field left empty, unknown REQUIRED field gives unclear_fields, cross-domain action gives unclear_fields, hidden tokens kept in the plan.
- At most 3 extra page fetches per site (test).

## After Prompt 4

- Test proves dry-run leaves the sites table with zero rows and never calls claim().
- dry_run_results is written; re-running dry-run on a batch replaces its results; batch state becomes dry_run_done.
- Report output includes the exact message text that would be sent.
- approve: refuses unless state is dry_run_done; requires typing the batch id; freezes the list of `ready` sites only (tests for each).
- export writes a NEW file under reports/ and never overwrites an existing file or the input CSV.
- Still no POST in src/ (repeat the scan).

## After Prompt 5 (most important)

- Exactly ONE place in src/ performs an HTTP POST. Show its location. It is reachable only through the send command.
- All gates run BEFORE any network call: ALLOW_LIVE equals exactly "1", batch approved, preflight passes, no STOP file, fresh backup created. Show the code.
- Per-site order is exactly: re-fetch and rebuild plan, compare with approved plan, claim, send-log "claimed" (fsync), POST, verify, finish, send-log "result" (fsync). Show the code and confirm the claim commit happens before the POST.
- No retry around the POST: the POST is not inside any retry loop and no retry library is used. An error or timeout during POST ends as sent_unconfirmed. Network errors BEFORE the claim leave the site unclaimed and log an event.
- Tests exist and pass, using a local server that counts POSTs: two runs of send on the same batch give exactly one POST per site; crash between claim and POST then rerun gives zero extra POSTs and the row stays pending; ALLOW_LIVE unset gives zero connections; unapproved batch refused; changed form action since approval is skipped; error during POST gives sent_unconfirmed with no retry; breaker trips after N consecutive failures.
- reopen: refused for sent, sent_unconfirmed and pending; allowed only for no_form, captcha, login_required, robots_blocked, unclear_fields; requires typing the site key; writes an event.
- Mutation check in a TEMPORARY COPY: (a) move the POST before the claim; (b) remove the ALLOW_LIVE check; (c) make claim() always return True. Each must make at least one test fail. Delete the copy afterwards.
- ALLOW_LIVE is not set in any committed file or .env. send was NOT run against any real website.

## After Prompt 6

- Dashboard binds to 127.0.0.1 only (show the line and a test).
- The ledger connection is read-only (SQLite URI mode=ro); a test proves a write attempt fails.
- STOP endpoint creates the STOP file and rejects a bad Origin (tests). No page endpoint clears STOP; `clear-stop` exists only in the CLI.
- No external assets: templates and static files reference no http(s) CDN URLs. Hebrew cells use dir="auto".
- The dashboard runs in its own process: the send code does not import the dashboard.
- The dashboard opens against a seeded ledger and shows counters, progress, events and pending rows.

## After Prompt 7

- Report: every POST path (must be one), the LLM/AI scan result, crash-window analysis, concurrency analysis, behavior if the ledger is deleted, power-loss analysis.
- Confirm no code path can clear or downgrade a pending, sent or sent_unconfirmed row.
- README has setup, the exact workflow (ingest, dry-run, approve, dashboard, send), all settings, backup and restore, and known limits.
- Run `python scripts/validate.py --all` and the full test suite; show both outputs.
- Any behavior change made during the audit was shown to the owner as a diff before being kept.
- End with a ranked list of residual risks.
