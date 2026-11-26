# Posiblo outreach tool: Claude Code build prompts

## Prompt 0: scaffold and rules

```
Create the skeleton of a Python 3.11+ project called posiblo-outreach in the current repo.

1. Layout: src/outreach/ (package), tests/, tests/fixtures/, templates/, data/ (empty, kept with .gitkeep), docs/. Use pyproject.toml with pytest as a dev dependency. Runtime dependencies for now: httpx, beautifulsoup4, lxml, tldextract. Do not add any LLM or AI SDK as a dependency, ever.
2. .gitignore must exclude: data/*, backups/, logs/, reports/, .env, *.db, *.db-wal, *.db-shm, STOP, __pycache__, .venv. Keep data/.gitkeep.
3. Create CLAUDE.md with the content below, verbatim.
4. Create a README.md stub (title and one line) and make an initial commit message suggestion (do not run git commit).

CLAUDE.md content:

# Posiblo outreach tool

Goal: read a CSV of business website URLs, find each site's contact form, and submit ONE fixed Hebrew written-consent-request message per site. Never send to the same site twice.

## Hard rules (never break these)
1. Send-once. A SQLite ledger has a unique key per site. A row is claimed (and committed to disk) BEFORE any POST. A row with status `pending` is never retried automatically.
2. Deterministic. No LLM calls anywhere in runtime code and no LLM SDKs in dependencies. Contact-page finding, field classification and success verification are rule-based.
3. Polite. Respect robots.txt, identify with an honest User-Agent, per-host delay, timeouts, response size cap, sequential requests (no parallel hits on one host).
4. Never bypass CAPTCHA, login, paywalls or any access control. Record a status and move on.
5. The input CSV is never modified. Output goes to new files.
6. Dry-run is the default. Live sending requires BOTH an approved batch AND the environment variable ALLOW_LIVE=1 (unset by default). Live sending stays disabled until the owner explicitly says the lawyer has answered.
7. No automatic retry after a POST was attempted. Ambiguous outcomes are recorded as `sent_unconfirmed`, never re-sent.
8. Personal data stays out of git: ledger, backups, logs, reports and data/ are git-ignored.
9. The message is one fixed template file with a version string. No personalization, no links beyond what the template contains. Refuse to send if a placeholder such as TODO remains in the sender details.
10. Safety stops: a circuit breaker halts the run after N consecutive failures; a file named STOP in the project root halts it immediately.

## Site statuses
pending, sent, sent_unconfirmed, no_form, captcha, login_required, robots_blocked, no_solicitation, unclear_fields, opted_out, invalid_url

## Conventions
Python 3.11+, src layout, type hints, small modules, argparse CLI (`python -m outreach ...`). Every step ships with pytest tests. Do not start work beyond the step you were asked to do.

When done: show the file tree and stop. Do not implement anything else.
```

---

## Prompt 1: ledger, normalizer, suppression list

```
Implement the heart of the tool: the ledger and the URL normalizer, with thorough tests. Follow CLAUDE.md. No network code in this step.

A. src/outreach/normalize.py
- normalize_url(raw) -> (site_key, domain) or raise InvalidUrl. Handle: missing scheme, uppercase, www., trailing dot, ports, paths, query strings and tracking params, fragments, IDN/punycode (Hebrew domains), whitespace, mailto:/javascript: junk.
- Normal business sites: site_key = registrable domain (via tldextract, configured to use the bundled suffix snapshot with no network access, e.g. suffix_list_urls=()). So www.example.co.il, example.co.il and shop.example.co.il share one key.
- Platform-aware keys: for shared hosts (facebook.com, instagram.com, linktr.ee, wixsite.com, blogspot.com, github.io, wordpress.com, business.site, and similar) the key includes the host and first path segment, so two different businesses on the same platform do not collide. Keep this list in one constant that is easy to extend.

B. src/outreach/ledger.py (SQLite, stdlib sqlite3)
- Open with WAL mode, synchronous=FULL, foreign_keys=ON, busy_timeout. Default path data/ledger.db, configurable.
- Tables: sites (site_key PRIMARY KEY, domain, input_url, form_url UNIQUE nullable, status, batch_id, message_version, source_url, collected_at, claimed_at, finished_at, detail), suppression (kind in domain/email/phone, value, reason, added_at, PRIMARY KEY(kind,value)), batches (batch_id, created_at, size, state, approved_at), dry_run_results (batch_id, site_key, outcome, form_url, fields_json, detail, created_at), events (id, ts, site_key, level, message).
- claim(site_key, ...) -> bool: a single INSERT that does nothing on conflict; returns True only if THIS call created the row (status `pending`), and the commit is durable before returning.
- finish(site_key, status, detail) updates a pending row to its final status.
- is_handled(site_key) and is_suppressed(domain/email/phone).
- pending rows are never touched by any automatic code path; add list_pending() for the dashboard and the preflight.

C. Tests (pytest), required:
- Table-driven normalizer tests with at least 30 cases, including Hebrew domains, .co.il, platform URLs, and invalid input.
- Second claim of the same key returns False. Claim of the same site via different URL spellings returns False.
- Two threads/processes claiming the same key at once: exactly one wins.
- Crash simulation: claim, then simulate a crash (do not call finish), reopen the ledger: the row is still `pending` and is not offered as work again.
- Suppression check blocks a suppressed domain.

When done: run pytest, show the full output, and stop. Do not start the next step.
```

---

## Prompt 2: operations layer (preflight, backups, send log, ingest, batches)

```
Add the operations layer around the ledger. No site fetching or form code yet. Follow CLAUDE.md.

1. src/outreach/config.py: load settings from environment and an optional .env (document every setting in README): ledger path, backup dir (default backups/), OFFSITE_BACKUP_DIR (optional, e.g. a private cloud-synced folder), batch size (default 25), per-host delay seconds (default 5), circuit-breaker threshold (default 5 consecutive failures), sender details (name, email, phone, address) with the address defaulting to the string TODO.
2. src/outreach/backup.py: create_backup() using the sqlite3 backup API (never a raw file copy), timestamped file in the backup dir, keep the newest 30, and also copy to OFFSITE_BACKUP_DIR when set. Fail loudly if a copy fails.
3. src/outreach/sendlog.py: an append-only JSONL file in logs/ where each line is flushed and fsynced. Used later to record "claimed" and "result" events so the ledger can be rebuilt if it is lost.
4. src/outreach/preflight.py: run_preflight() checks, in this order: STOP file absent; PRAGMA integrity_check on the ledger is ok; if the ledger file is MISSING but backups or the send log exist, REFUSE to run and explain how to restore (this prevents silently starting from an empty ledger); templates/consent_request_v1.txt exists; in live mode only, no TODO placeholders in sender details. Return a clear list of failures.
5. src/outreach/breaker.py: a circuit breaker that counts consecutive failures and trips at the configured threshold.
6. Templates: create templates/consent_request_v1.txt with exactly this Hebrew text, where {address} is filled from config at send time:

פרסומת
שלום, אני ניר מאיר מ-Posiblo. האם תרצו שאשלח אליכם מידע על שירותי אוטומציה ו-AI לעסקים? אם כן, השיבו "כן". אם לא, אין צורך לענות ולא אפנה שוב.
פנייה בדיוור ישיר. הפרטים נלקחו מהאתר הציבורי של העסק. למחיקה מהרשימה השיבו "הסר".
Posiblo, {address}, 052-251-8189, posiblo.contact@gmail.com

   Add a short note in docs/ that this text is pending legal review and must not be changed without bumping the version in the file name.
7. CLI (python -m outreach ...): `ingest <csv>` reads the CSV (auto-detect the URL column; if ambiguous, ask via an error message listing columns), normalizes each URL, drops invalid URLs, duplicates inside the file, already-handled sites and suppressed sites, then splits the rest into batches of the configured size and stores them in the batches table (state `planned`) and prints a summary. It must never modify the CSV. Also: `status`, `backup`, `suppress add <domain|email|phone> <value> --reason ...`.

Tests: ingest on a sample CSV with duplicates, bad URLs, a handled site and a suppressed site; backup produces a valid, openable database and prunes to 30; preflight refuses when the ledger is missing but a backup exists; the breaker trips exactly at the threshold; the sample CSV is byte-identical after ingest.

When done: run pytest, show the output, and stop.
```

---

## Prompt 3: polite fetcher, contact-form finder, field classifier (read-only)

```
Build the read-only part that visits a site and works out what its contact form looks like. It must NEVER submit anything. Follow CLAUDE.md. No LLM, no Playwright in this step.

1. src/outreach/fetch.py: an httpx-based fetcher: User-Agent "PosibloOutreachBot/1.0 (+https://posiblo.com; posiblo.contact@gmail.com)"; robots.txt fetched once per host and cached (urllib.robotparser), a disallowed URL is not fetched and yields status robots_blocked; per-host minimum delay from config; sequential requests; 15s timeout; response body capped at 2 MB; at most 3 redirects and only within the same registrable domain; no automatic retries; Hebrew pages decoded correctly.
2. src/outreach/finder.py: given a site's homepage HTML, rank candidate contact links by rules: anchor text and href containing צור קשר, יצירת קשר, צרו קשר, contact, contact-us, contactus, get in touch; also try common paths (/contact, /contact-us, /צור-קשר, /he/contact) with at most 3 extra fetches per site. Look for the form on the homepage first. Choose the best form: one with a textarea or a text input plus an email input. Exclude search forms, login forms (password field), and newsletter-only forms (single email input with subscribe/newsletter/הרשמה/ניוזלטר).
3. Detect and report, without trying to get around them: CAPTCHA (g-recaptcha, h-captcha, cf-turnstile, data-sitekey, grecaptcha) -> captcha; login walls -> login_required; no usable form -> no_form; sites that state they do not want solicitation (phrases like "no solicitation", "אין לשלוח פרסומות", "אין לפנות לצרכי שיווק") -> no_solicitation.
4. src/outreach/classify.py: classify each form field by name, id, type, placeholder and label (Hebrew and English): name, email, phone, subject, message, consent checkbox, hidden. Keep hidden inputs (tokens) in the plan. Skip honeypot fields (CSS-hidden or tabindex=-1 text inputs) and leave them empty. If a REQUIRED field cannot be classified, return unclear_fields and do not guess.
5. Output a FormPlan dataclass: form_url, action URL, method, encoding, mapped fields, hidden fields, and a human-readable summary. Add a check that the action URL is on the same registrable domain, otherwise status unclear_fields with a detail.

Tests: create about 12 small HTML fixtures in tests/fixtures/ (Contact Form 7 in Hebrew, Elementor form, plain English form, form with reCAPTCHA, login page, newsletter-only page, page with no form, JS-only page with no static form, form with a honeypot, form with an unknown required field, no-solicitation notice, cross-domain action). Test finder and classifier against them. Fetcher tests use a local test HTTP server (pytest-httpserver), including a robots.txt that disallows the contact page and a body larger than the cap.

When done: run pytest, show the output, and stop.
```

---

## Prompt 4: dry-run and approval

```
Add the batch dry-run and the approval gate. Still no real sending. Follow CLAUDE.md.

1. `python -m outreach dry-run <batch_id>`: for each site in the batch, fetch, find the form and build the FormPlan (steps from the previous module), and store the outcome in dry_run_results (outcome is `ready` or one of the statuses: no_form, captcha, login_required, robots_blocked, no_solicitation, unclear_fields, or fetch_error). Dry-run must NOT write to the sites table and must NOT claim anything. Use the circuit breaker and the STOP file. Print a readable report: one line per site with the outcome, the form URL, and the fields that would be filled, plus the exact message text that would be sent. Set the batch state to dry_run_done.
2. `python -m outreach approve <batch_id>`: only allowed when the state is dry_run_done. Show a summary (how many ready, how many skipped and why) and require the user to type the batch id to confirm. On confirmation store approved_at and freeze the list of approved sites (those with outcome ready) so a later live run can only process exactly that list.
3. `python -m outreach export <batch_id>` writes reports/<batch_id>-<timestamp>.csv as a NEW file (never overwrite, never touch the input CSV).

Tests: dry-run leaves the sites table empty; approve refuses before a dry-run; approve requires the typed confirmation; the approved list contains only ready sites; re-running dry-run on a batch is allowed and replaces its dry_run_results; export never overwrites an existing file.

When done: run pytest, show the output, and stop.
```

---

## Prompt 5: live sending (locked by default)

```
Implement live sending, locked behind multiple gates. Follow CLAUDE.md strictly: this is the step where send-once must hold.

Gates for `python -m outreach send <batch_id>`: refuse unless ALL are true: environment variable ALLOW_LIVE=1; the batch is approved; preflight passes (including no TODO in sender details); no STOP file; a fresh backup was just created. Without ALLOW_LIVE=1 the command must print that live sending is disabled and exit before any network call.

Per site in the approved list, in this exact order:
1. Re-fetch the page and rebuild the FormPlan (tokens are fresh). If the form action or fields differ from the approved plan, skip with an event and do not send.
2. claim(site_key) in the ledger. If it returns False, skip. The claim is committed before anything is sent.
3. Append a "claimed" line to the send log (fsync).
4. Build the message from templates/consent_request_v1.txt and the sender details. If the form has a subject field, use: פרסומת - בקשת הסכמה. Fill name, email, phone and message; tick a consent checkbox only if it is required for submission. Submit once with httpx, including the hidden fields, to the same-registrable-domain action URL.
5. Verify with rules: success texts (תודה, ההודעה נשלחה, נשלח בהצלחה, thank you, message sent, we will get back to you) or a redirect to a URL containing thank/thanks/success/תודה. Match -> finish(sent). No match, or any error or timeout during the POST -> finish(sent_unconfirmed). NEVER retry after a POST attempt.
6. Append a "result" line to the send log (fsync). Update the circuit breaker; stop the run when it trips. After the batch finishes, create a backup.
Network errors BEFORE the claim (step 1) are logged as events and leave the site unclaimed, so it is eligible for a future batch.

Also add `python -m outreach reopen <site_key>`: allowed only for statuses where no POST happened (no_form, captcha, login_required, robots_blocked, unclear_fields); requires typing the site key to confirm; writes an event. It must refuse for sent, sent_unconfirmed and pending.

Do not add Playwright or any JavaScript rendering in this step.

Tests (use a local test server that counts POSTs): exactly one POST per site even when `send` runs twice on the same batch; crash simulated between claim and POST, then rerun: zero additional POSTs and the row stays pending; ALLOW_LIVE unset: zero network calls; unapproved batch refused; changed form action since approval: skipped; error during POST ends as sent_unconfirmed with no retry; breaker trips after N consecutive failures; reopen refuses sent/pending.

When done: run pytest, show the output, and stop. Do NOT run a live send against any real website.
```

---

## Prompt 6: live dashboard

```
Build the live monitoring dashboard. Follow CLAUDE.md.

1. `python -m outreach dashboard` starts a small Flask app (add flask as a dependency) bound to 127.0.0.1 only, in its own process, so a dashboard problem can never affect sending.
2. It reads the ledger and events READ-ONLY (SQLite URI mode=ro). One page that polls a JSON endpoint every 2 seconds and shows: current batch and state, a progress bar, counters per status, the site being processed, circuit-breaker state, a list of pending rows needing manual review, and a table of the latest events with colored statuses and failure reasons (failures stand out).
3. A big STOP button that creates the STOP file in the project root. Reject cross-origin POSTs (check the Origin/Host header). Clearing STOP is done only from the CLI (`python -m outreach clear-stop`), not from the page.
4. Hebrew must render correctly: use dir="auto" on text cells and a font stack with good Hebrew support. Keep the UI plain and clear, no external CDN assets (works offline).

Tests: the JSON endpoint returns the expected counters for a seeded ledger; the dashboard cannot write to the ledger; the STOP endpoint creates the file and rejects a bad Origin.

When done: run pytest, show the output, start the dashboard against a seeded sample ledger and describe what it shows, then stop.
```

---

## Prompt 7: skeptical audit

```
Act as a skeptical reviewer of this repo. Do not add features. Goal: try to break the send-once guarantee and the safety rules in CLAUDE.md.

1. List every code path that performs an HTTP POST. Confirm there is exactly one, that it is only reachable through the send command, and that it is always preceded by a committed claim.
2. Grep the repo and dependencies for any LLM or AI SDK usage. Report the result.
3. Review: the normalizer for ways two spellings of one site could get different keys, the crash windows around claim/POST/finish, concurrency (two terminals running at once), what happens if the ledger file is deleted, what happens on a power loss, and whether any path can clear or downgrade a pending/sent/sent_unconfirmed row.
4. Confirm .gitignore covers all personal data and that nothing sensitive is tracked.
5. Run the full test suite and add any missing tests for gaps you find. Show the output.
6. Write the README: setup, the exact step-by-step workflow (ingest, dry-run, approve, dashboard, send), all settings, backup and restore instructions, and a "known limits" section (JS-only sites are skipped, no CAPTCHA handling, unresolved legal questions).
7. Finish with a short list of residual risks, ranked. If you changed behavior anywhere, show me the diff before keeping it.
```
