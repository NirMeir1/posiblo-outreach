import hashlib
import os
import shutil
from pathlib import Path

import pytest

from conftest import FIXTURES
from outreach.ingest import IngestError, detect_url_column, ingest, read_csv
from outreach.ledger import Ledger

SAMPLE = FIXTURES / "sample_sites.csv"


def _fingerprint(path: Path) -> tuple[str, int, float]:
    st = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), st.st_size, st.st_mtime


@pytest.fixture
def led(tmp_path: Path):
    with Ledger(tmp_path / "ledger.db") as ledger:
        # one handled site and one suppressed site, as required by the prompt
        ledger.claim("handled-example.co.il", domain="handled-example.co.il", input_url="https://handled-example.co.il")
        ledger.finish("handled-example.co.il", "sent")
        ledger.add_suppression("domain", "suppressed-example.co.il", reason="asked to be removed")
        yield ledger


def test_ingest_sample_counts_and_batches(led: Ledger) -> None:
    s = ingest(SAMPLE, led, batch_size=4)
    assert s.column == "אתר"
    assert s.rows == 17
    assert s.empty == 1
    assert s.invalid == 3            # mailto:, "not a url", javascript:
    assert s.duplicates == 2         # flowers (bare), lawyer (WWW + path)
    assert s.handled == 1
    assert s.suppressed == 1
    assert s.already_planned == 0
    assert s.planned == 9
    assert s.rows == s.empty + s.invalid + s.duplicates + s.handled + s.suppressed + s.planned
    assert s.batch_ids == ["B0001", "B0002", "B0003"]

    batches = led.list_batches()
    assert [(b["batch_id"], b["size"], b["state"]) for b in batches] == [
        ("B0001", 4, "planned"), ("B0002", 4, "planned"), ("B0003", 1, "planned")]
    keys = [r["site_key"] for b in s.batch_ids for r in led.batch_sites(b)]
    assert keys == ["flowers-example.co.il", "restaurant-example.co.il", "lawyer-example.co.il",
                    "garage-example.co.il", "beauty-example.co.il", "facebook.com/bakery.example",
                    "xn--6dbbec0c.co.il", "dentist-example.co.il", "yoga-example.co.il"]
    assert "handled-example.co.il" not in keys and "suppressed-example.co.il" not in keys
    first = led.batch_sites("B0001")[0]
    assert first["input_url"] == "https://www.flowers-example.co.il/" and first["source_row"] == 2


def test_ingest_never_claims_anything(led: Ledger) -> None:
    ingest(SAMPLE, led, batch_size=25)
    assert led.list_pending() == []
    assert led.get("flowers-example.co.il") is None


def test_ingest_leaves_csv_byte_identical(led: Ledger) -> None:
    before = _fingerprint(SAMPLE)
    ingest(SAMPLE, led, batch_size=3)
    ingest(SAMPLE, led, batch_size=3)
    assert _fingerprint(SAMPLE) == before


def test_second_ingest_plans_nothing_new(led: Ledger) -> None:
    first = ingest(SAMPLE, led, batch_size=25)
    second = ingest(SAMPLE, led, batch_size=25)
    assert first.planned == 9
    assert second.planned == 0 and second.already_planned == 9 and second.batch_ids == []
    assert len(led.list_batches()) == 1


def test_cp1255_encoded_csv(tmp_path: Path, led: Ledger) -> None:
    path = tmp_path / "hebrew.csv"
    path.write_bytes("שם,אתר\nמאפייה,https://bakery-example.co.il\n".encode("cp1255"))
    s = ingest(path, led, batch_size=25)
    assert s.column == "אתר" and s.planned == 1


def test_semicolon_csv_and_english_header(tmp_path: Path, led: Ledger) -> None:
    path = tmp_path / "sites.csv"
    path.write_text("Name;Website;Phone\nA;a-example.co.il;1\nB;b-example.co.il;2\n", encoding="utf-8")
    assert ingest(path, led, batch_size=25).planned == 2


def test_ambiguous_column_lists_columns(tmp_path: Path, led: Ledger) -> None:
    path = tmp_path / "two.csv"
    path.write_text("url,website\na.co.il,b.co.il\n", encoding="utf-8")
    with pytest.raises(IngestError) as e:
        ingest(path, led, batch_size=25)
    assert "'url'" in str(e.value) and "'website'" in str(e.value) and "--column" in str(e.value)
    assert ingest(path, led, batch_size=25, column="website").planned == 1


def test_undetectable_column_lists_columns(tmp_path: Path, led: Ledger) -> None:
    path = tmp_path / "none.csv"
    path.write_text("name,city\nא,תל אביב\n", encoding="utf-8")
    with pytest.raises(IngestError, match="Columns: 'name', 'city'"):
        ingest(path, led, batch_size=25)


def test_column_detected_from_content(tmp_path: Path) -> None:
    header, rows = ["name", "x", "phone"], [["a", "a-example.co.il", "1"], ["b", "https://b-example.co.il", "2"]]
    assert detect_url_column(header, rows) == 1


def test_unknown_explicit_column(tmp_path: Path, led: Ledger) -> None:
    with pytest.raises(IngestError, match="not found"):
        ingest(SAMPLE, led, batch_size=25, column="nope")


def test_read_csv_opens_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    modes = []
    real_open = open

    def spy(file, mode="r", *a, **k):
        modes.append(mode)
        return real_open(file, mode, *a, **k)

    monkeypatch.setattr("builtins.open", spy)
    read_csv(SAMPLE)
    assert modes == ["rb"]


def test_read_only_csv_file_can_be_ingested(tmp_path: Path, led: Ledger) -> None:
    path = tmp_path / "ro.csv"
    shutil.copyfile(SAMPLE, path)
    os.chmod(path, 0o444)
    try:
        assert ingest(path, led, batch_size=25).planned == 9
    finally:
        os.chmod(path, 0o666)
