import csv
import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from conftest import FIXTURES, FakeFetcher, fixture_html
from outreach.cli import main
from outreach.config import load_config
from outreach.dryrun import run_dry_run
from outreach.export import COLUMNS, export_batch
from outreach.ledger import Ledger, open_readonly

NOW = datetime(2026, 11, 26, 15, 30, 0)


@pytest.fixture
def db(project: Path):
    cfg = load_config(root=project, environ={})
    with Ledger(cfg.ledger_path) as led:
        led.create_batches([[{"site_key": "a-example.co.il", "domain": "a-example.co.il",
                              "input_url": "https://a-example.co.il/"},
                             {"site_key": "b-example.co.il", "domain": "b-example.co.il",
                              "input_url": "https://b-example.co.il/"}]])
        run_dry_run(cfg, led, "B0001", out=lambda s: None,
                    fetcher=FakeFetcher({"https://a-example.co.il/": fixture_html("cf7_hebrew.html")}))
    return cfg


def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_export_writes_a_new_report(db) -> None:
    conn = open_readonly(db.ledger_path)
    path = export_batch(conn, "B0001", db.root / "reports", now=NOW)
    conn.close()
    assert path == db.root / "reports" / "B0001-20261126-153000.csv"
    rows = read(path)
    assert list(rows[0]) == COLUMNS
    assert [(r["site_key"], r["dry_run_outcome"], r["approved"]) for r in rows] == [
        ("a-example.co.il", "ready", "no"), ("b-example.co.il", "fetch_error", "no")]


def test_export_never_overwrites(db) -> None:
    reports = db.root / "reports"
    reports.mkdir()
    existing = reports / "B0001-20261126-153000.csv"
    existing.write_text("do not touch", encoding="utf-8")
    conn = open_readonly(db.ledger_path)
    first = export_batch(conn, "B0001", reports, now=NOW)
    second = export_batch(conn, "B0001", reports, now=NOW)
    conn.close()
    assert existing.read_text(encoding="utf-8") == "do not touch"
    assert first.name == "B0001-20261126-153000-1.csv"
    assert second.name == "B0001-20261126-153000-2.csv"
    assert len(list(reports.iterdir())) == 3


def test_export_unknown_batch(db) -> None:
    conn = open_readonly(db.ledger_path)
    with pytest.raises(ValueError):
        export_batch(conn, "B9999", db.root / "reports", now=NOW)
    conn.close()


def test_cli_ingest_dry_run_export_never_touches_input_csv(project: Path, capsys: pytest.CaptureFixture) -> None:
    sample = FIXTURES / "sample_sites.csv"
    before = hashlib.sha256(sample.read_bytes()).hexdigest(), sample.stat().st_mtime_ns
    assert main(["ingest", str(sample)]) == 0
    assert main(["export", "B0001"]) == 0
    out = capsys.readouterr().out
    assert "report written:" in out
    reports = list((project / "reports").glob("B0001-*.csv"))
    assert len(reports) == 1 and len(read(reports[0])) == 11
    assert (hashlib.sha256(sample.read_bytes()).hexdigest(), sample.stat().st_mtime_ns) == before
