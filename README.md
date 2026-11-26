# posiblo-outreach

Finds each business website's contact form and submits one fixed Hebrew consent-request message per site, exactly once.

The rules the code follows are in [CLAUDE.md](CLAUDE.md). The skeptical review of the code is in [docs/audit.md](docs/audit.md). The message and its legal status are in [docs/message-template.md](docs/message-template.md).

**Live sending is disabled.** It needs an approved batch *and* `ALLOW_LIVE=1` in the real environment. Leave `ALLOW_LIVE` unset until the owner confirms the lawyer has answered.

## Setup

Windows, Python 3.11 or newer. All package versions are pinned (`pyproject.toml` and `requirements.lock`), so how URLs become site keys cannot change by accident. To upgrade a package, change both files and re-run the tests and `python scripts/validate.py --all`.

```powershell
cd posiblo-outreach
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
python -m pip install -r requirements.lock   # exact, tested versions of every package
python -m pip install -e . --no-deps
python -m pytest -q                 # all tests use local servers only; nothing on the internet is contacted
python -m outreach --help
```

Optional: create a `.env` file in the project folder (it is git-ignored) with your settings, at least:

```
SENDER_ADDRESS=<your postal address>
OFFSITE_BACKUP_DIR=C:\Users\<you>\OneDrive\posiblo-backups
```

Run every command from the project folder: relative paths and the `STOP` file are resolved against it.

## Workflow

1. **Ingest** the CSV of website URLs. The CSV is opened read-only and never changed.
   ```powershell
   python -m outreach ingest leads.csv            # add --column NAME if the URL column is not detected
   ```
   Invalid URLs, duplicates in the file, sites already in the ledger, suppressed sites and sites already in an open batch are dropped. The rest becomes batches `B0001`, `B0002`, ... of `OUTREACH_BATCH_SIZE` sites, in state `planned`.

2. **Dry-run** a batch. It visits each site with GET requests only, respecting robots.txt, and records what would be filled. Nothing is sent and nothing is claimed.
   ```powershell
   python -m outreach dry-run B0001
   python -m outreach export B0001                # optional: reports\B0001-<timestamp>.csv for review
   ```
   Read the report: one line per site (outcome, form URL, fields), then the exact message text. If the dry-run halts (STOP file, circuit breaker), run it again; only a complete dry-run can be approved.

3. **Approve** the batch. You see how many sites are ready and why the others were skipped, and you must type the batch id. The list of ready sites is then frozen.
   ```powershell
   python -m outreach approve B0001
   ```

4. **Dashboard** (optional, a second terminal): a read-only page on `http://127.0.0.1:8765/`. It shows the current batch and progress, counters per status, the site being processed, the circuit breaker, pending rows that need review, and the latest events. Its STOP button halts any run before its next site.
   ```powershell
   python -m outreach dashboard
   ```

5. **Send**, only after the lawyer has answered and `SENDER_ADDRESS` is set:
   ```powershell
   $env:ALLOW_LIVE = "1"; python -m outreach send B0001; Remove-Item Env:ALLOW_LIVE
   ```
   `send` refuses unless all of these hold: `ALLOW_LIVE` is exactly `1`, the batch is approved, live preflight passes (no `STOP` file, ledger healthy and consistent with the send log, template present, no `TODO` in the sender details), and a fresh backup was just written. Then, for each approved site: it fetches the form again (fresh tokens), skips the site if the form changed since approval, claims the site in the ledger (committed to disk), writes "claimed" to the send log, POSTs **once** (in the form's own charset), checks for a success message, records `sent` or `sent_unconfirmed`, and writes "result" to the send log. Nothing is ever retried. If anything unexpected goes wrong after the claim, the site is left `pending`, an event is logged and the run moves on to the next site. When the batch finishes, sites whose dry-run showed `no_form`, `captcha`, `login_required`, `robots_blocked` or `unclear_fields` are recorded in the ledger (no message, no request), so later batches skip them. A backup is written again at the end.

6. **Review** afterwards: `python -m outreach status`, the dashboard, or `python -m outreach export B0001`.
   - `pending` rows: the run stopped between the claim and the result, so a message may or may not have been sent. They are never retried automatically. Check them by hand.
   - `sent_unconfirmed`: a message was submitted but success could not be confirmed. Never re-sent.

Other commands:

| Command | What it does |
|---|---|
| `python -m outreach status` | Read-only summary: sites per status, batches, suppression counts, backups. |
| `python -m outreach backup` | Backs up the ledger (SQLite backup API), keeps the newest 30, also writes to `OFFSITE_BACKUP_DIR`. |
| `python -m outreach suppress add <domain\|email\|phone> <value> [--reason TEXT]` | Never contact this domain, email or phone (works even while `STOP` exists). |
| `python -m outreach clear-stop` | Removes the `STOP` file (type `CLEAR`). The dashboard cannot clear STOP. |
| `python -m outreach reopen <site_key>` | Lets a site be planned again after `no_form`, `captcha`, `login_required`, `robots_blocked` or `unclear_fields` (recorded when its batch finished; no message was sent). Refused for every other status. Type the site key to confirm. |

## Settings

Settings come from environment variables or from `.env` in the project folder. A real environment variable wins over `.env`, and `.env` wins over the default. Relative paths are relative to the project folder.

| Variable | Default | Meaning |
|---|---|---|
| `OUTREACH_LEDGER_PATH` | `data/ledger.db` | SQLite ledger file (the record of every site ever handled). |
| `OUTREACH_BACKUP_DIR` | `backups` | Local backup folder; the newest 30 backups are kept. |
| `OFFSITE_BACKUP_DIR` | *(unset)* | Optional second backup folder, e.g. a private cloud-synced folder. It must already exist; if it is set but missing, or the copy fails, the backup fails loudly (and `send` refuses to start). |
| `OUTREACH_LOG_DIR` | `logs` | Folder for the append-only send log `send-log.jsonl` and the dashboard's `run-status.json`. |
| `OUTREACH_BATCH_SIZE` | `25` | Sites per batch created by `ingest`. |
| `OUTREACH_HOST_DELAY_SECONDS` | `5` | Minimum seconds between two requests to the same host. |
| `OUTREACH_BREAKER_THRESHOLD` | `5` | Consecutive failures after which a run halts (circuit breaker). |
| `SENDER_NAME` | `ניר מאיר` | Sender name filled into contact forms. |
| `SENDER_EMAIL` | `posiblo.contact@gmail.com` | Sender email filled into contact forms. |
| `SENDER_PHONE` | `052-251-8189` | Sender phone filled into contact forms. |
| `SENDER_ADDRESS` | `TODO` | Sender postal address, inserted into the message. Live sending refuses while any sender detail contains `TODO`. |

`ALLOW_LIVE` is not a setting. It is ignored if it appears in `.env`, and only the exact value `1` set in the real environment enables `send`.

## Files and safety stops

| Path | Content | In git? |
|---|---|---|
| `data/ledger.db` (+ `-wal`, `-shm`) | The ledger | no |
| `backups/ledger-<UTC time>.db` | Backups (newest 30) | no |
| `logs/send-log.jsonl` | Append-only record of every claim and result, each line fsynced | no |
| `logs/run-status.json` | What a running dry-run/send is doing (for the dashboard) | no |
| `reports/*.csv` | Exports | no |
| `STOP` | Halts any run before its next site; clear with `clear-stop` | no |
| `.env` | Your settings | no |

## Backup and restore

- **Backups are automatic** before and after every `send`. Make one any time with `python -m outreach backup`. Backups go through SQLite's backup API, so they include commits that are still only in `ledger.db-wal`. Each backup is integrity-checked and is a single self-contained file.
- **Never copy, move or replace `ledger.db` by hand while it may have a `-wal` file next to it.** A plain copy can miss committed claims (there is a test proving this: `test_raw_copy_of_ledger_file_can_lose_claims_but_backup_does_not`). Use the `backup` command.
- **If the ledger is missing** while backups or the send log exist, `ingest`, `dry-run`, `approve`, `suppress add`, `reopen` and `send` refuse to run and print the newest backup.
- **To restore:**
  1. Stop everything. Create `STOP` if anything might be running.
  2. Delete `data/ledger.db-wal` and `data/ledger.db-shm` if they exist.
  3. Copy the **newest** backup, from `backups\` or from `OFFSITE_BACKUP_DIR`, to `data\ledger.db`.
  4. Run `python -m outreach status`. Every write command now checks that every site with a `claimed` line in `logs\send-log.jsonl` is in the ledger. If you restored a backup older than the last send, they refuse and name the missing sites: restore a newer backup instead, or reconcile by hand.
  5. Run `python -m outreach clear-stop` when you are sure.
- If all backups and the send log are lost too, the tool cannot know what was sent. Do not ingest the same CSV again.

## Known limits

- **Only static HTML is read.** Sites that build their contact form with JavaScript are recorded as `no_form`. There is no browser automation.
- **No CAPTCHA, login or paywall handling**, by design. Those sites are recorded and skipped.
- **Success detection is rule-based.** It looks for a success phrase that was not already on the form page, or a redirect to a thank-you/success URL. Everything else is `sent_unconfirmed`, which is never re-sent even if the message did arrive.
- **robots.txt:** a missing file (404/410) or 401/403 means allowed; a network error, a 5xx answer or 429 means the whole site is skipped for this run.
- **Platform URLs** (facebook.com/x, instagram.com/x, ...) normally have no usable form and robots.txt usually blocks them.
- **One site key per registrable domain.** A business with two domains (e.g. `example.co.il` and `example.com`) counts as two sites.
- **Legal questions are unresolved.** The message text is pending legal review (docs/message-template.md). Live sending must stay disabled until the owner confirms the lawyer has answered.
