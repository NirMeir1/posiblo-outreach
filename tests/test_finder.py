from urllib.parse import quote

import pytest
from bs4 import BeautifulSoup

from conftest import FIXTURES
from outreach.fetch import FETCH_ERROR, OK, ROBOTS_BLOCKED, FetchResult
from outreach.finder import (MAX_EXTRA_FETCHES, choose_form, find_contact_form, form_kind,
                             rank_contact_links)

BASE = "https://www.example.co.il"


def fx(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeFetcher:
    """Serves fixture HTML by URL. Unknown URLs are 404s. Records every page requested."""

    def __init__(self, pages: dict[str, str], blocked: set[str] = frozenset(), redirects=None):
        self.pages, self.blocked, self.redirects = pages, set(blocked), redirects or {}
        self.requested: list[str] = []

    def get(self, url: str) -> FetchResult:
        self.requested.append(url)
        if url in self.blocked:
            return FetchResult(url, url, ROBOTS_BLOCKED, detail="robots.txt does not allow it")
        final = self.redirects.get(url, url)
        if final in self.pages:
            return FetchResult(url, final, OK, 200, "text/html; charset=utf-8", self.pages[final],
                               redirects=[final] if final != url else [])
        return FetchResult(url, final, FETCH_ERROR, 404, detail="HTTP 404")


CONTACT = BASE + "/" + quote("צור-קשר") + "/"


def home_and_contact(contact_fixture: str) -> FakeFetcher:
    return FakeFetcher({BASE + "/": fx("home_with_contact_link.html"), CONTACT: fx(contact_fixture)})


def test_form_on_homepage_is_used_first() -> None:
    f = FakeFetcher({BASE + "/": fx("cf7_hebrew.html")})
    r = find_contact_form(BASE + "/", f)
    assert r.status == "ready" and r.form_url == BASE + "/"
    assert f.requested == [BASE + "/"]


def test_follows_hebrew_contact_link() -> None:
    f = home_and_contact("cf7_hebrew.html")
    r = find_contact_form(BASE + "/", f)
    assert r.status == "ready", r.detail
    assert r.form_url == CONTACT
    assert f.requested == [BASE + "/", CONTACT]


@pytest.mark.parametrize(("fixture", "status", "needle"), [
    ("elementor.html", "ready", ""),
    ("plain_english.html", "ready", ""),
    ("recaptcha.html", "captcha", "recaptcha"),
    ("login.html", "login_required", "log"),
    ("newsletter.html", "no_form", "newsletter"),
    ("no_form.html", "no_form", "no usable contact form"),
    ("js_only.html", "no_form", "JavaScript"),
    ("honeypot.html", "ready", ""),
    ("unknown_required.html", "unclear_fields", "id_number"),
    ("no_solicitation.html", "no_solicitation", "אין לשלוח פרסומות"),
    ("cross_domain.html", "unclear_fields", "another domain"),
])
def test_contact_page_outcomes(fixture: str, status: str, needle: str) -> None:
    r = find_contact_form(BASE + "/", home_and_contact(fixture))
    assert r.status == status, (r.status, r.detail)
    assert needle.lower() in r.detail.lower()


def test_honeypot_left_empty_in_found_plan() -> None:
    r = find_contact_form(BASE + "/", home_and_contact("honeypot.html"))
    assert set(r.plan.honeypots) == {"website", "company_hp", "url_check"}
    assert "website" not in {f.name for f in r.plan.fields}


def test_hidden_tokens_kept_in_found_plan() -> None:
    r = find_contact_form(BASE + "/", home_and_contact("cf7_hebrew.html"))
    assert r.plan.hidden_fields["_wpcf7"] == "42"


def test_no_solicitation_on_homepage_stops_immediately() -> None:
    f = FakeFetcher({BASE + "/": fx("no_solicitation.html")})
    r = find_contact_form(BASE + "/", f)
    assert r.status == "no_solicitation" and f.requested == [BASE + "/"]


def test_robots_blocked_homepage() -> None:
    f = FakeFetcher({}, blocked={BASE + "/"})
    assert find_contact_form(BASE + "/", f).status == "robots_blocked"


def test_robots_blocked_contact_page() -> None:
    f = FakeFetcher({BASE + "/": fx("home_with_contact_link.html")},
                    blocked={CONTACT, BASE + "/contact", BASE + "/contact-us"})
    r = find_contact_form(BASE + "/", f)
    assert r.status == "robots_blocked"


def test_homepage_fetch_error() -> None:
    r = find_contact_form(BASE + "/", FakeFetcher({}))
    assert r.status == "fetch_error"


def test_common_paths_tried_when_no_links() -> None:
    f = FakeFetcher({BASE + "/": fx("no_form.html"), BASE + "/contact-us": fx("plain_english.html")})
    r = find_contact_form(BASE + "/", f)
    assert r.status == "ready" and r.form_url == BASE + "/contact-us"
    assert f.requested == [BASE + "/", BASE + "/contact", BASE + "/contact-us"]


def test_at_most_three_extra_fetches() -> None:
    links = "".join(f'<a href="/contact-{i}">צור קשר {i}</a>' for i in range(10))
    f = FakeFetcher({BASE + "/": f"<html><body>{links}</body></html>"})
    r = find_contact_form(BASE + "/", f)
    assert r.status == "no_form"
    assert len(f.requested) == 1 + MAX_EXTRA_FETCHES == 4


def test_redirect_to_login_is_login_required() -> None:
    f = FakeFetcher({BASE + "/": fx("home_with_contact_link.html"), BASE + "/login?next=contact": fx("no_form.html")},
                    redirects={CONTACT: BASE + "/login?next=contact"})
    assert find_contact_form(BASE + "/", f).status == "login_required"


def test_rank_contact_links_prefers_contact_and_stays_on_site() -> None:
    html = ('<a href="/about">אודות</a><a href="https://other.example.com/contact">contact</a>'
            '<a href="/blog/how-to-contact-a-lawyer">מאמר</a><a href="/contact">צור קשר</a>'
            '<a href="mailto:a@b.co.il">צור קשר</a>')
    ranked = rank_contact_links(BeautifulSoup(html, "lxml"), BASE + "/")
    assert ranked[0] == BASE + "/contact"
    assert all(u.startswith(BASE) for u in ranked)
    assert BASE + "/about" not in ranked


@pytest.mark.parametrize(("html", "kind"), [
    ('<form role="search"><input name="s"></form>', "search"),
    ('<form action="/search"><input type="text" name="q"></form>', "search"),
    ('<form><input name="u"><input type="password" name="p"><textarea name="m"></textarea></form>', "login"),
    ('<form><input type="email" name="e"><button>הרשמה</button></form>', "newsletter"),
    ('<form><input type="email" name="e"></form>', "newsletter"),
    ('<form><input name="n"><input type="email" name="e"><button>Subscribe</button></form>', "newsletter"),
    ('<form><input name="n"><input type="email" name="e"></form>', "contact"),
    ('<form><textarea name="m"></textarea></form>', "contact"),
])
def test_form_kinds(html: str, kind: str) -> None:
    assert form_kind(BeautifulSoup(html, "lxml").find("form")) == kind


def test_choose_form_reports_excluded_forms() -> None:
    form, notes = choose_form(BeautifulSoup(fx("newsletter.html"), "lxml"))
    assert form is None and notes == ["newsletter", "newsletter"]


def test_finder_has_no_way_to_submit() -> None:
    """The finder only ever calls fetcher.get(); a fetcher without other methods is enough."""
    class GetOnly:
        def __init__(self): self.calls = []
        def get(self, url):
            self.calls.append(url)
            return FetchResult(url, url, OK, 200, "text/html", fx("cf7_hebrew.html"))
        def __getattr__(self, name):
            raise AssertionError(f"finder used fetcher.{name}")

    assert find_contact_form(BASE + "/", GetOnly()).status == "ready"
