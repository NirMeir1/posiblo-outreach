"""approve <batch_id>: the human gate between dry-run and any live run.

Allowed only for a batch in state dry_run_done. Shows a summary and requires
the operator to type the batch id. On confirmation the `ready` sites are
frozen in approved_sites (database triggers forbid changing that list) and
the batch becomes `approved`. A later live run may only process that list.
"""

from __future__ import annotations

from typing import Callable

from .ledger import Ledger, LedgerError


class ApprovalRefused(RuntimeError):
    pass


def approval_summary(ledger: Ledger, batch_id: str) -> tuple[int, dict[str, int], list[str]]:
    results = ledger.dry_run_results(batch_id)
    ready = sum(1 for r in results if r["outcome"] == "ready")
    skipped: dict[str, int] = {}
    for r in results:
        if r["outcome"] != "ready":
            skipped[r["outcome"]] = skipped.get(r["outcome"], 0) + 1
    lines = [f"Batch {batch_id}: {len(results)} site(s) checked in the dry-run",
             f"  ready (will be approved): {ready}"]
    for outcome, n in sorted(skipped.items()):
        lines.append(f"  skipped, {outcome}: {n}")
    return ready, skipped, lines


def approve_batch(ledger: Ledger, batch_id: str, ask: Callable[[str], str] | None = None,
                  out: Callable[[str], None] = print) -> int:
    ask = ask or input  # looked up at call time
    batch = ledger.get_batch(batch_id)
    if batch is None:
        raise ApprovalRefused(f"no batch {batch_id!r}")
    if batch["state"] != "dry_run_done":
        raise ApprovalRefused(f"batch {batch_id} is {batch['state']}; run `python -m outreach dry-run {batch_id}` "
                              "to completion first")
    ready, _, lines = approval_summary(ledger, batch_id)
    for line in lines:
        out(line)
    if ready == 0:
        raise ApprovalRefused(f"batch {batch_id} has no ready sites; nothing to approve")
    typed = ask(f"Type the batch id ({batch_id}) to approve these {ready} site(s): ").strip()
    if typed != batch_id:
        ledger.add_event("info", f"approve {batch_id}: confirmation did not match; not approved")
        raise ApprovalRefused("confirmation did not match the batch id; nothing was approved")
    try:
        count = ledger.approve(batch_id)
    except LedgerError as e:
        raise ApprovalRefused(str(e)) from None
    ledger.add_event("info", f"approve {batch_id}: {count} site(s) frozen")
    out(f"Approved {batch_id}: {count} site(s) frozen. Live sending is still disabled.")
    return count
