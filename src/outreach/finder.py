"""Find a site's contact form and decide whether it can be used. Read-only.

find_contact_form(start_url, fetcher) -> FindResult

1. Fetch the homepage and look for a usable form there first.
2. Otherwise fetch at most MAX_EXTRA_FETCHES more pages: same-site links
   ranked by contact words in their text and href, then common paths.
3. Detect and report (never work around): no-solicitation notices,
   CAPTCHAs, login walls, missing forms. A usable form is turned into a
   FormPlan by classify.build_plan().

Outcomes: ready, no_form, captcha, login_required, robots_blocked,
no_solicitation, unclear_fields, fetch_error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from .classify import READY, UNCLEAR, FormPlan, build_plan
from .fetch import FETCH_ERROR, ROBOTS_BLOCKED, FetchResult
from .normalize import registrable_domain

MAX_EXTRA_FETCHES = 3

CONTACT_WORDS = ["צור קשר", "צרו קשר", "יצירת קשר", "contact us", "contact-us", "contactus", "get in touch",
                 "contact"]
COMMON_PATHS = ["/contact", "/contact-us", "/צור-קשר", "/he/contact"]
CAPTCHA_MARKERS = ["g-recaptcha", "h-captcha", "cf-turnstile", "data-sitekey", "grecaptcha",
                   "recaptcha/api.js", "hcaptcha.com/1/api.js", "challenges.cloudflare.com/turnstile"]
NO_SOLICITATION = ["no solicitation", "no solicitations", "no soliciting", "do not solicit",
                   "אין לשלוח פרסומות", "אין לפנות לצרכי שיווק", "אין לשלוח הצעות שיווקיות", "אין לשלוח דיוור"]
NEWSLETTER_WORDS = ["subscribe", "newsletter", "הרשמה", "ניוזלטר", "הירשמו", "להרשמה", "sign up", "signup",
                    "mailing list", "רשימת תפוצה", "דיוור"]
SEARCH_HINT = re.compile(r"search|חיפוש", re.I)
LOGIN_URL_HINT = re.compile(r"login|log-in|signin|sign-in|wp-login|התחברות|כניסה", re.I)

NO_FORM = "no_form"
CAPTCHA = "captcha"
LOGIN_REQUIRED = "login_required"
NO_SOLICITATION_STATUS = "no_solicitation"


class FetcherLike(Protocol):
    def get(self, url: str) -> FetchResult: ...


@dataclass
class FindResult:
    status: str
    start_url: str
    form_url: str | None = None
    plan: FormPlan | None = None
    detail: str = ""
    pages: list[str] = field(default_factory=list)  # pages fetched (not counting robots.txt)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _canon(url: str) -> str:
    p = urlsplit(url)
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme, p.netloc.lower(), unquote(path), p.query, ""))


def visible_text(soup: BeautifulSoup) -> str:
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    return " ".join(soup.get_text(" ").split()).lower()


def mentions_no_solicitation(html: str) -> str | None:
    text = visible_text(_soup(html))
    return next((p for p in NO_SOLICITATION if p in text), None)


def captcha_marker(html: str) -> str | None:
    low = html.lower()
    return next((m for m in CAPTCHA_MARKERS if m in low), None)


def _inputs(form: Tag) -> list[Tag]:
    return form.find_all(["input", "textarea", "select"])


def _type(el: Tag) -> str:
    return str(el.get("type", "text")).lower() if el.name == "input" else el.name


def _form_words(form: Tag) -> str:
    attrs = " ".join(str(form.get(a, "")) for a in ("id", "name", "action", "role", "aria-label"))
    attrs += " " + " ".join(form.get("class", []))
    for el in form.find_all(["input", "button"]):
        attrs += " " + " ".join(str(el.get(a, "")) for a in ("name", "id", "placeholder", "value", "aria-label"))
    return (attrs + " " + form.get_text(" ")).lower()


def form_kind(form: Tag) -> str:
    """'contact', 'search', 'login', 'newsletter' or 'other'."""
    fields = [el for el in _inputs(form) if _type(el) not in ("hidden", "submit", "button", "image", "reset")]
    types = [_type(el) for el in fields]
    words = _form_words(form)
    if "password" in types:
        return "login"
    if str(form.get("role", "")).lower() == "search" or "search" in types or \
            (len(fields) <= 2 and (SEARCH_HINT.search(words) or any(str(el.get("name", "")) in ("q", "s")
                                                                        for el in fields))):
        return "search"
    has_textarea = "textarea" in types
    emails = [el for el in fields if _type(el) == "email" or "mail" in str(el.get("name", "")).lower()]
    texts = [el for el in fields if _type(el) in ("text", "tel") and el not in emails]
    if not has_textarea and any(w in words for w in NEWSLETTER_WORDS):
        return "newsletter"
    if len(fields) == 1 and emails:
        return "newsletter"
    if has_textarea or (texts and emails):
        return "contact"
    return "other"


def choose_form(soup: BeautifulSoup) -> tuple[Tag | None, list[str]]:
    """Best usable contact form on the page, plus notes about excluded forms."""
    best, best_score, notes = None, -1, []
    for form in soup.find_all("form"):
        kind = form_kind(form)
        if kind != "contact":
            notes.append(kind)
            continue
        words = _form_words(form)
        score = 0
        score += 3 * len(form.find_all("textarea"))
        score += 2 * sum(1 for el in _inputs(form) if _type(el) == "email")
        score += sum(1 for el in _inputs(form) if _type(el) in ("text", "tel"))
        score += 2 * sum(1 for w in ("contact", "צור קשר", "wpcf7", "elementor-form") if w in words)
        if score > best_score:
            best, best_score = form, score
    return best, notes


def rank_contact_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    origin = registrable_domain(urlsplit(base_url).hostname or "")
    scored: dict[str, int] = {}
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "whatsapp:")):
            continue
        url = urljoin(base_url, href).split("#", 1)[0]
        p = urlsplit(url)
        if p.scheme not in ("http", "https") or registrable_domain(p.hostname or "") != origin:
            continue
        text = " ".join([a.get_text(" "), str(a.get("title", "")), str(a.get("aria-label", ""))]).lower()
        text = " ".join(text.split())
        path = unquote(p.path).lower().replace("_", "-")
        score = 0
        for i, w in enumerate(CONTACT_WORDS):
            weight = len(CONTACT_WORDS) - i
            if w in text:
                score = max(score, 10 + weight)
            if w.replace(" ", "-") in path:
                score = max(score, 5 + weight) if score < 10 else score + 2
        if score:
            score -= path.count("/")  # prefer short paths
            if scored.get(url, -999) < score:
                scored[url] = score
    return [u for u, _ in sorted(scored.items(), key=lambda kv: (-kv[1], len(kv[0])))]


def _js_only_hint(soup: BeautifulSoup) -> str:
    if soup.find(id=re.compile(r"^(root|app|__next|__nuxt)$")) or len(soup.find_all("script")) >= 5:
        return " (the page seems to build its content with JavaScript; only static HTML is read)"
    return ""


def _evaluate_form(form: Tag, html: str, page_url: str, start_url: str, pages: list[str],
                   page_encoding: str | None = None) -> FindResult:
    marker = captcha_marker(html)
    if marker:
        return FindResult(CAPTCHA, start_url, page_url, None, f"CAPTCHA on the form page ({marker}); skipped",
                          pages)
    result = build_plan(form, page_url, page_encoding)
    if result.status != READY:
        return FindResult(UNCLEAR, start_url, page_url, result.plan, result.detail, pages)
    return FindResult(READY, start_url, page_url, result.plan, "", pages)


def find_contact_form(start_url: str, fetcher: FetcherLike, max_extra_fetches: int = MAX_EXTRA_FETCHES) -> FindResult:
    pages: list[str] = []
    home = fetcher.get(start_url)
    pages.append(home.requested_url)
    if home.outcome == ROBOTS_BLOCKED:
        return FindResult(ROBOTS_BLOCKED, start_url, detail=home.detail, pages=pages)
    if not home.ok:
        return FindResult(FETCH_ERROR, start_url, detail=home.detail, pages=pages)
    if not home.is_html:
        return FindResult(NO_FORM, start_url, detail=f"homepage is not HTML ({home.content_type})", pages=pages)

    phrase = mentions_no_solicitation(home.text)
    if phrase:
        return FindResult(NO_SOLICITATION_STATUS, start_url, home.url, detail=f"site says: {phrase!r}", pages=pages)
    soup = _soup(home.text)
    form, notes = choose_form(soup)
    if form is not None:
        return _evaluate_form(form, home.text, home.url, start_url, pages, home.encoding)

    seen = {_canon(home.url), _canon(start_url)}
    root = urlunsplit(urlsplit(home.url)[:2] + ("", "", ""))
    candidates = rank_contact_links(soup, home.url) + [urljoin(root, p) for p in COMMON_PATHS]
    login_seen = robots_seen = False
    excluded: list[str] = list(notes)
    hint = _js_only_hint(_soup(home.text))
    extra = 0
    for url in candidates:
        if extra >= max_extra_fetches:
            break
        if _canon(url) in seen:
            continue
        seen.add(_canon(url))
        extra += 1
        page = fetcher.get(url)
        pages.append(page.requested_url)
        if page.outcome == ROBOTS_BLOCKED:
            robots_seen = True
            continue
        if not page.ok or not page.is_html:
            continue
        seen.add(_canon(page.url))
        if LOGIN_URL_HINT.search(unquote(urlsplit(page.url).path)) and page.redirects:
            login_seen = True
        phrase = mentions_no_solicitation(page.text)
        if phrase:
            return FindResult(NO_SOLICITATION_STATUS, start_url, page.url, detail=f"site says: {phrase!r}",
                              pages=pages)
        psoup = _soup(page.text)
        form, notes = choose_form(psoup)
        excluded += notes
        hint = hint or _js_only_hint(psoup)
        if form is not None:
            return _evaluate_form(form, page.text, page.url, start_url, pages, page.encoding)
        if "login" in notes:
            login_seen = True

    if login_seen:
        return FindResult(LOGIN_REQUIRED, start_url, detail="the contact page requires logging in", pages=pages)
    if robots_seen:
        return FindResult(ROBOTS_BLOCKED, start_url, detail="robots.txt does not allow the contact page", pages=pages)
    detail = "no usable contact form found"
    if excluded:
        detail += f" (forms ignored: {', '.join(sorted(set(excluded)))})"
    return FindResult(NO_FORM, start_url, detail=detail + hint, pages=pages)
