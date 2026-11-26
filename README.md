# posiblo-outreach

Finds each business website's contact form and submits one fixed Hebrew consent-request message per site, exactly once.

Run every command from the project folder (the folder that contains `pyproject.toml`); relative paths and the `STOP` file are resolved against it.

## Commands available so far

| Command | What it does |
|---|---|
| `python -m outreach ingest <csv> [--column NAME]` | Reads the CSV (never modifies it), normalizes the URLs, drops invalid URLs, duplicates, already-handled, suppressed and already-planned sites, and stores the rest as batches in state `planned`. |
| `python -m outreach status` | Read-only summary: sites per status, batches, suppression counts, backups. |
| `python -m outreach backup` | Backs up the ledger with the SQLite backup API; keeps the newest 30; also writes to `OFFSITE_BACKUP_DIR` when set. |
| `python -m outreach suppress add <domain\|email\|phone> <value> [--reason TEXT]` | Never contact this domain, email or phone. |
| `python -m outreach dry-run <batch_id>` | Visits every site of the batch (GET only, robots.txt respected), finds the contact form and records what would be filled. Sends nothing and claims nothing. Prints one line per site and the exact message text. |
| `python -m outreach approve <batch_id>` | Only after a complete dry-run. Shows ready/skipped counts and asks you to type the batch id. Freezes the list of `ready` sites. |
| `python -m outreach export <batch_id>` | Writes `reports/<batch_id>-<timestamp>.csv` as a new file (never overwrites, never touches the input CSV). |

## Settings

Settings come from environment variables, or from a `.env` file in the project folder (git-ignored). A real environment variable wins over `.env`; `.env` wins over the default. Relative paths are relative to the project folder.

| Variable | Default | Meaning |
|---|---|---|
| `OUTREACH_LEDGER_PATH` | `data/ledger.db` | SQLite ledger file (the record of every site ever handled). |
| `OUTREACH_BACKUP_DIR` | `backups` | Local backup folder; the newest 30 backups are kept. |
| `OFFSITE_BACKUP_DIR` | *(unset)* | Optional second backup folder, e.g. a private cloud-synced folder. It must already exist; if it is set but missing, or the copy fails, the backup command fails loudly. |
| `OUTREACH_LOG_DIR` | `logs` | Folder for the append-only send log `send-log.jsonl`. |
| `OUTREACH_BATCH_SIZE` | `25` | Sites per batch created by `ingest`. |
| `OUTREACH_HOST_DELAY_SECONDS` | `5` | Minimum seconds between two requests to the same host. |
| `OUTREACH_BREAKER_THRESHOLD` | `5` | Consecutive failures after which a run halts (circuit breaker). |
| `SENDER_NAME` | `ניר מאיר` | Sender name filled into contact forms. |
| `SENDER_EMAIL` | `posiblo.contact@gmail.com` | Sender email filled into contact forms. |
| `SENDER_PHONE` | `052-251-8189` | Sender phone filled into contact forms. |
| `SENDER_ADDRESS` | `TODO` | Sender postal address, inserted into the message. Live sending refuses to run while any sender detail contains `TODO`. |

`ALLOW_LIVE` is not a setting: it is ignored if it appears in `.env`, and can only be set in the real environment. Live sending is not implemented yet.

## Safety files

- `STOP` in the project folder halts any run immediately.
- If the ledger file is missing while backups or the send log exist, `ingest` and `suppress add` refuse to run and explain how to restore it.
- The message text and its rules: `templates/consent_request_v1.txt` and `docs/message-template.md` (pending legal review).
