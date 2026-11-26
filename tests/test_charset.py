"""Proposal A: the single POST uses the form's charset (accept-charset, else page encoding, else UTF-8)."""

from pathlib import Path
from urllib.parse import parse_qs

import pytest
from bs4 import BeautifulSoup
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

from outreach.approve import approve_batch
from outreach.classify import form_charset
from outreach.config import load_config
from outreach.dryrun import run_dry_run
from outreach.fetch import Fetcher
from outreach.ledger import Ledger
from outreach.message import render_message
from outreach.send import plan_signature, run_send

LIVE = {"ALLOW_LIVE": "1"}


def form(attrs: str = "") -> object:
    return BeautifulSoup(f"<form {attrs}></form>", "lxml").find("form")


@pytest.mark.parametrize(("attrs", "page", "expected"), [
    ('accept-charset="windows-1255"', "utf-8", "cp1255"),
    ('accept-charset="ISO-8859-8"', None, "cp1255"),
    ('accept-charset="UTF-8"', "cp1255", "utf-8"),
    ('accept-charset="bogus utf-8"', "cp1255", "utf-8"),     # first label the codec registry knows
    ('accept-charset="bogus"', "cp1255", "cp1255"),          # unknown label: page encoding
    ("", "cp1255", "cp1255"),
    ("", "windows-1255", "cp1255"),
    ("", None, "utf-8"),
    ("", "nonsense", "utf-8"),
])
def test_form_charset_rules(attrs: str, page, expected: str) -> None:
    assert form_charset(form(attrs), page) == expected


def test_fetcher_reports_the_encoding_it_used(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/robots.txt").respond_with_data("", status=404)
    httpserver.expect_request("/he").respond_with_data("<p>שלום</p>".encode("cp1255"),
                                                       content_type="text/html; charset=windows-1255")
    httpserver.expect_request("/u").respond_with_data("<p>שלום</p>".encode("utf-8"), content_type="text/html")
    with Fetcher(delay_seconds=0) as f:
        assert f.get(httpserver.url_for("/he")).encoding == "cp1255"
        assert f.get(httpserver.url_for("/u")).encoding == "utf-8"


def test_old_approved_plans_without_charset_compare_as_utf8() -> None:
    plan = {"action_url": "a", "method": "post", "encoding": "x", "fields": [], "hidden_fields": {}, "honeypots": []}
    assert plan_signature(plan)["charset"] == "utf-8"


def _page(charset_attr: str = "") -> bytes:
    html = f"""<html><head><meta charset="windows-1255"></head><body>
<form action="/send" method="post" {charset_attr}>
<label for="n">שם מלא</label><input id="n" name="name" required>
<label for="e">אימייל</label><input id="e" type="email" name="email" required>
<label for="m">הודעה</label><textarea id="m" name="message" required></textarea>
</form></body></html>"""
    return html.encode("cp1255")


@pytest.mark.parametrize(("charset_attr", "wire"), [("", "cp1255"), ('accept-charset="utf-8"', "utf-8")])
def test_post_body_is_encoded_in_the_form_charset(project: Path, httpserver: HTTPServer, charset_attr: str,
                                                  wire: str) -> None:
    httpserver.expect_request("/robots.txt").respond_with_data("", status=404)
    httpserver.expect_request("/", method="GET").respond_with_data(_page(charset_attr),
                                                                   content_type="text/html")  # charset only in <meta>
    httpserver.expect_request("/send", method="POST").respond_with_handler(
        lambda r: Response("<p>תודה! ההודעה נשלחה</p>".encode("utf-8"), content_type="text/html; charset=utf-8"))
    address = "רחוב הדוגמה 1 → קומה 2"  # "→" does not exist in windows-1255
    cfg = load_config(root=project, environ={"SENDER_ADDRESS": address, "OUTREACH_HOST_DELAY_SECONDS": "0"})
    with Ledger(cfg.ledger_path) as led:
        led.create_batches([[{"site_key": "he-site.co.il", "domain": "127.0.0.1", "input_url": httpserver.url_for("/")}]])
        with Fetcher(delay_seconds=0) as f:
            assert run_dry_run(cfg, led, "B0001", fetcher=f, out=lambda s: None).completed
        approve_batch(led, "B0001", ask=lambda p: "B0001", out=lambda s: None)
        report = run_send(cfg, led, "B0001", environ=LIVE, out=lambda s: None)
    assert report.sites[0].result == "sent"
    post = next(r for r, _ in httpserver.log if r.method == "POST")
    raw = post.get_data().decode("ascii")                       # urlencoded body is pure ASCII
    form_data = {k: v[0] for k, v in parse_qs(raw, encoding=wire).items()}
    expected = render_message(cfg)
    if wire == "cp1255":
        expected = expected.replace("→", "&#8594;")            # what a browser sends for unencodable chars
    assert form_data["message"] == expected
    assert form_data["name"] == cfg.sender_name
