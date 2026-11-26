"""reopen <site_key>: let a site be planned again after an outcome where no POST happened.

Allowed only for no_form, captcha, login_required, robots_blocked and
unclear_fields. Refused for sent, sent_unconfirmed, pending and every other
status. The operator must type the site key; an event is written.
"""

from __future__ import annotations

from typing import Callable

from .ledger import REOPENABLE_STATUSES, Ledger, LedgerError


class ReopenRefused(RuntimeError):
    pass


def reopen_site(ledger: Ledger, site_key: str, ask: Callable[[str], str] | None = None,
                out: Callable[[str], None] = print) -> str:
    ask = ask or input
    row = ledger.get(site_key)
    if row is None:
        raise ReopenRefused(f"no site {site_key!r} in the ledger")
    if row["status"] not in REOPENABLE_STATUSES:
        raise ReopenRefused(f"site {site_key} is {row['status']}; reopen is only allowed for "
                            f"{', '.join(REOPENABLE_STATUSES)} (no POST happened for those)")
    out(f"{site_key}: status {row['status']}, detail: {row['detail'] or '-'}")
    typed = ask(f"Type the site key ({site_key}) to reopen it: ").strip()
    if typed != site_key:
        ledger.add_event("info", "reopen: confirmation did not match; nothing changed", site_key=site_key)
        raise ReopenRefused("confirmation did not match the site key; nothing changed")
    try:
        old = ledger.reopen(site_key)
    except LedgerError as e:
        raise ReopenRefused(str(e)) from None
    out(f"reopened {site_key} (was {old}); it can be planned in a future batch")
    return old
