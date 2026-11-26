"""ingest: read a CSV of website URLs and plan batches. The CSV is never modified.

The file is opened read-only in binary mode ("rb") and decoded in memory
(UTF-8, UTF-8 with BOM, or Windows-1255 Hebrew). Each URL is normalized; the
following are dropped and counted: invalid URLs, duplicates inside the file,
sites already in the ledger (any status), suppressed sites, and sites already
planned in an earlier batch. The rest is split into batches of the configured
size and stored with state `planned`. Ingest never claims a site.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from .ledger import Ledger
from .normalize import InvalidUrl, normalize_url

_URL_HEADER = re.compile(
    r"^(url|urls|website|web ?site|site|homepage|home ?page|domain|link|web|"
    r"אתר|אתרים|אתר אינטרנט|כתובת אתר|כתובת האתר|כתובת אינטרנט|קישור|לינק)$",
    re.IGNORECASE,
)
_URL_HEADER_LOOSE = re.compile(r"(url|website|אתר)", re.IGNORECASE)


class IngestError(ValueError):
    pass


@dataclass
class IngestSummary:
    csv_path: str
    column: str
    rows: int = 0
    empty: int = 0
    invalid: int = 0
    duplicates: int = 0
    handled: int = 0
    suppressed: int = 0
    already_planned: int = 0
    planned: int = 0
    batch_ids: list[str] = field(default_factory=list)
    invalid_examples: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [
            f"CSV: {self.csv_path} (not modified)",
            f"URL column: {self.column!r}",
            f"rows read:          {self.rows}",
            f"empty URL cells:    {self.empty}",
            f"invalid URLs:       {self.invalid}",
            f"duplicates in file: {self.duplicates}",
            f"already handled:    {self.handled}",
            f"suppressed:         {self.suppressed}",
            f"already planned:    {self.already_planned}",
            f"planned now:        {self.planned} site(s) in {len(self.batch_ids)} batch(es)"
            + (f": {', '.join(self.batch_ids)}" if self.batch_ids else ""),
        ]
        out += [f"  invalid: {e}" for e in self.invalid_examples]
        return out


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Return (header, rows). Opens the file read-only; never writes."""
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8-sig", "cp1255"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise IngestError(f"{path}: cannot decode as UTF-8 or Windows-1255")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]
    if not rows:
        raise IngestError(f"{path}: the file is empty")
    header = [h.strip() for h in rows[0]]
    return header, rows[1:]


def detect_url_column(header: list[str], rows: list[list[str]], explicit: str | None = None) -> int:
    listing = ", ".join(repr(h) for h in header)
    if explicit is not None:
        if explicit not in header:
            raise IngestError(f"column {explicit!r} not found. Columns: {listing}")
        return header.index(explicit)
    if len(header) == 1:
        return 0
    exact = [i for i, h in enumerate(header) if _URL_HEADER.match(h)]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise IngestError(f"more than one column looks like a URL column ({', '.join(repr(header[i]) for i in exact)}). "
                          f"Choose one with --column. Columns: {listing}")
    loose = [i for i, h in enumerate(header) if _URL_HEADER_LOOSE.search(h)]
    if len(loose) == 1:
        return loose[0]
    # Fall back to content: the one column where most non-empty cells are valid URLs.
    scores = []
    for i in range(len(header)):
        cells = [r[i] for r in rows[:200] if i < len(r) and r[i].strip()]
        ok = 0
        for c in cells:
            try:
                normalize_url(c)
                ok += 1
            except InvalidUrl:
                pass
        scores.append(ok / len(cells) if cells else 0.0)
    good = [i for i, s in enumerate(scores) if s >= 0.6]
    if len(good) == 1:
        return good[0]
    raise IngestError(f"cannot tell which column holds the website URLs. Choose one with --column. "
                      f"Columns: {listing}")


def ingest(csv_path: str | Path, ledger: Ledger, batch_size: int, column: str | None = None) -> IngestSummary:
    path = Path(csv_path)
    header, rows = read_csv(path)
    col = detect_url_column(header, rows, column)
    summary = IngestSummary(csv_path=str(path), column=header[col])
    seen: set[str] = set()
    keep: list[dict] = []
    for n, row in enumerate(rows, start=2):  # row 1 is the header
        summary.rows += 1
        raw = row[col] if col < len(row) else ""
        if not raw.strip():
            summary.empty += 1
            continue
        try:
            key, domain = normalize_url(raw)
        except InvalidUrl as e:
            summary.invalid += 1
            if len(summary.invalid_examples) < 10:
                summary.invalid_examples.append(f"row {n}: {raw.strip()[:80]!r} ({e})")
            continue
        if key in seen:
            summary.duplicates += 1
            continue
        seen.add(key)
        if ledger.is_handled(key):
            summary.handled += 1
            continue
        if ledger.is_suppressed("domain", key):
            summary.suppressed += 1
            continue
        if ledger.is_planned(key):
            summary.already_planned += 1
            continue
        keep.append({"site_key": key, "domain": domain, "input_url": raw.strip(), "source_row": n})

    groups = [keep[i:i + batch_size] for i in range(0, len(keep), batch_size)]
    summary.batch_ids = ledger.create_batches(groups, source_file=path.name)
    summary.planned = len(keep)
    ledger.add_event("info", f"ingest {path.name}: {summary.rows} rows, {summary.planned} planned in "
                             f"{len(summary.batch_ids)} batch(es) {summary.batch_ids}; dropped invalid={summary.invalid} "
                             f"duplicates={summary.duplicates} handled={summary.handled} "
                             f"suppressed={summary.suppressed} already_planned={summary.already_planned}")
    return summary
