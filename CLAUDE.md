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
