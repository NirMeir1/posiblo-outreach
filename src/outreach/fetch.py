"""Polite, read-only HTTP fetcher. It only ever sends GET requests.

- Honest User-Agent (USER_AGENT).
- robots.txt fetched once per host (scheme + host + port) and cached; a
  disallowed URL is never requested and yields `robots_blocked`.
  robots.txt means "disallow everything" only on a network error, a 5xx
  answer or 429; any other 4xx (404/410 missing, 401/403, ...) means "allowed".
  A network error is reported as `fetch_error` (not `robots_blocked`): the
  site did not refuse anything, and the circuit breaker must see outages.
- Minimum delay between two requests to the same host (from config).
- Sequential: one request at a time per Fetcher (a lock), no concurrency.
- 15 s timeout, body capped at 2 MB (declared or streamed), at most 3
  redirects and only within the same registrable domain.
- No automatic retries anywhere: one attempt per URL, failures are reported.
- Hebrew pages decoded from the HTTP charset, a <meta> charset, or by trying
  UTF-8 then Windows-1255.
"""

from __future__ import annotations

import codecs
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import httpx

from .normalize import registrable_domain

USER_AGENT = "PosibloOutreachBot/1.0 (+https://posiblo.com; posiblo.contact@gmail.com)"
ROBOTS_AGENT = "PosibloOutreachBot"
TIMEOUT_SECONDS = 15.0
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3

OK = "ok"
ROBOTS_BLOCKED = "robots_blocked"
FETCH_ERROR = "fetch_error"

_REDIRECT_CODES = {301, 302, 303, 307, 308}
_HEBREW_ALIASES = {"iso-8859-8", "iso-8859-8-i", "iso-8859-8-e", "iso_8859-8", "hebrew", "windows-1255",
                   "cp1255", "x-cp1255"}


@dataclass
class FetchResult:
    requested_url: str
    url: str
    outcome: str
    status_code: int | None = None
    content_type: str | None = None
    text: str = ""
    detail: str = ""
    redirects: list[str] = field(default_factory=list)
    encoding: str = "utf-8"  # the codec the body was decoded with

    @property
    def ok(self) -> bool:
        return self.outcome == OK

    @property
    def is_html(self) -> bool:
        ct = (self.content_type or "").lower()
        return not ct or "html" in ct


class _Raw:
    def __init__(self, status: int, headers: httpx.Headers, body: bytes):
        self.status, self.headers, self.body = status, headers, body


class _RequestFailed(Exception):
    pass


@dataclass
class _RobotsPolicy:
    allow_all: bool = False
    disallow_all: bool = False
    parser: robotparser.RobotFileParser | None = None
    detail: str = ""
    network_error: bool = False  # robots.txt could not be fetched at all (DNS, connection, timeout)

    def allows(self, url: str) -> bool:
        if self.disallow_all:
            return False
        if self.allow_all or self.parser is None:
            return True
        return self.parser.can_fetch(ROBOTS_AGENT, url)


def decode_body(body: bytes, content_type: str | None) -> str:
    """Decode an HTML body, getting Hebrew legacy encodings right."""
    return decode_body_with_encoding(body, content_type)[0]


def normalize_charset(name: str | None) -> str | None:
    """Python codec name for an HTML/HTTP charset label, or None if unknown."""
    if not name:
        return None
    label = name.strip().strip("\"'").lower()
    if label in _HEBREW_ALIASES:
        return "cp1255"
    try:
        codec = codecs.lookup(label).name
    except LookupError:
        return None
    return "utf-8" if codec in ("utf-8-sig", "utf_8") else codec


def decode_body_with_encoding(body: bytes, content_type: str | None) -> tuple[str, str]:
    """(text, codec used). Same rules as decode_body."""
    candidates: list[str] = []
    m = re.search(r"charset=[\"']?([\w.:-]+)", content_type or "", re.I)
    if m:
        candidates.append(m.group(1))
    head = body[:4096].decode("ascii", "ignore")
    m = re.search(r"<meta[^>]+charset=[\"']?([\w.:-]+)", head, re.I)
    if m:
        candidates.append(m.group(1))
    if body.startswith(b"\xef\xbb\xbf"):
        candidates.insert(0, "utf-8-sig")
    for enc in candidates:
        codec = "utf-8-sig" if enc == "utf-8-sig" else normalize_charset(enc)
        if codec is None:
            continue
        try:
            return body.decode(codec), "utf-8" if codec == "utf-8-sig" else codec
        except (LookupError, UnicodeDecodeError):
            continue
    try:
        return body.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return body.decode("cp1255", errors="replace"), "cp1255"


def _host_key(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc.lower()}"


class Fetcher:
    def __init__(
        self,
        delay_seconds: float = 5.0,
        *,
        timeout: float = TIMEOUT_SECONDS,
        max_bytes: int = MAX_BODY_BYTES,
        max_redirects: int = MAX_REDIRECTS,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self._clock, self._sleep = clock, sleep
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
                     "Accept-Language": "he,en;q=0.8"},
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )
        self._robots: dict[str, _RobotsPolicy] = {}
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()
        self.requested: list[str] = []  # every URL actually requested, in order (for tests and reports)

    # -- lifecycle -----------------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- public ------------------------------------------------------------
    def get(self, url: str) -> FetchResult:
        with self._lock:
            return self._get(url)

    def robots_allows(self, url: str) -> bool:
        with self._lock:
            return self._robots_policy(url).allows(url)

    def wait_turn(self, url: str) -> None:
        """Apply the per-host delay for a request made by another client (the single POST in send.py)."""
        with self._lock:
            self._wait_for_host(url)

    # -- internals -----------------------------------------------------------
    def _get(self, url: str) -> FetchResult:
        current = url
        redirects: list[str] = []
        origin = registrable_domain(urlsplit(url).hostname or "")
        for hop in range(self.max_redirects + 1):
            if urlsplit(current).scheme not in ("http", "https"):
                return FetchResult(url, current, FETCH_ERROR, detail=f"unsupported URL scheme: {current}",
                                   redirects=redirects)
            policy = self._robots_policy(current)
            if not policy.allows(current):
                if policy.network_error:
                    # Not a refusal by the site: the network failed. The page is still not requested,
                    # but it is reported as a fetch error so it counts for the circuit breaker.
                    return FetchResult(url, current, FETCH_ERROR, redirects=redirects,
                                       detail=f"network error, page not requested: {policy.detail}")
                return FetchResult(url, current, ROBOTS_BLOCKED, redirects=redirects,
                                   detail=f"robots.txt does not allow {current}" + (f" ({policy.detail})"
                                                                                    if policy.detail else ""))
            try:
                raw = self._request(current)
            except _RequestFailed as e:
                return FetchResult(url, current, FETCH_ERROR, detail=str(e), redirects=redirects)
            if raw.status in _REDIRECT_CODES and raw.headers.get("location"):
                nxt = urljoin(current, raw.headers["location"])
                if registrable_domain(urlsplit(nxt).hostname or "") != origin:
                    return FetchResult(url, current, FETCH_ERROR, raw.status, redirects=redirects,
                                       detail=f"redirect to another domain refused: {nxt}")
                if hop == self.max_redirects:
                    return FetchResult(url, current, FETCH_ERROR, raw.status, redirects=redirects,
                                       detail=f"more than {self.max_redirects} redirects")
                redirects.append(nxt)
                current = nxt
                continue
            ctype = raw.headers.get("content-type")
            if raw.status >= 400:
                return FetchResult(url, current, FETCH_ERROR, raw.status, ctype, redirects=redirects,
                                   detail=f"HTTP {raw.status}")
            text, encoding = decode_body_with_encoding(raw.body, ctype)
            return FetchResult(url, current, OK, raw.status, ctype, text, redirects=redirects, encoding=encoding)
        raise AssertionError("unreachable")

    def _wait_for_host(self, url: str) -> None:
        host = _host_key(url)
        last = self._last_request.get(host)
        if last is not None:
            wait = self.delay_seconds - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last_request[host] = self._clock()

    def _request(self, url: str, truncate: bool = False) -> _Raw:
        """Exactly one GET attempt. Raises _RequestFailed on any error.

        A body over the cap raises, or with truncate=True is cut at the cap (used for robots.txt).
        """
        self._wait_for_host(url)
        self.requested.append(url)
        try:
            with self._client.stream("GET", url) as resp:
                declared = resp.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > self.max_bytes and not truncate:
                    raise _RequestFailed(f"response too large: {declared} bytes declared (cap {self.max_bytes})")
                chunks, total = [], 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > self.max_bytes:
                        if not truncate:
                            raise _RequestFailed(f"response too large: more than {self.max_bytes} bytes")
                        chunks.append(chunk[: len(chunk) - (total - self.max_bytes)])
                        break
                    chunks.append(chunk)
                return _Raw(resp.status_code, resp.headers, b"".join(chunks))
        except httpx.TimeoutException:
            raise _RequestFailed(f"timeout after {self.timeout:g}s") from None
        except httpx.HTTPError as e:
            raise _RequestFailed(f"{type(e).__name__}: {e}") from None

    def _robots_policy(self, url: str) -> _RobotsPolicy:
        key = _host_key(url)
        if key in self._robots:
            return self._robots[key]
        policy = self._fetch_robots(key)
        self._robots[key] = policy
        return policy

    def _fetch_robots(self, host_key: str) -> _RobotsPolicy:
        """robots.txt policy for one host (RFC 9309).

        "Disallow everything" only for: a network error (unreachable, timeout), a 5xx answer, or
        429 Too Many Requests (a request to slow down, not a missing file). Every other 4xx
        (404/410 missing, 401/403, ...) means "no rules": allowed.
        Redirects are followed up to max_redirects hops, also to another host (only robots.txt is
        read there); more hops than that is treated as "no robots.txt" (allowed). A body larger
        than the cap is parsed up to the cap.
        """
        current = f"{host_key}/robots.txt"
        for _ in range(self.max_redirects + 1):
            if urlsplit(current).scheme not in ("http", "https"):
                return _RobotsPolicy(allow_all=True, detail=f"robots.txt redirects to a non-http URL: {current}")
            try:
                raw = self._request(current, truncate=True)
            except _RequestFailed as e:
                return _RobotsPolicy(disallow_all=True, network_error=True, detail=f"robots.txt not reachable: {e}")
            if raw.status in _REDIRECT_CODES and raw.headers.get("location"):
                current = urljoin(current, raw.headers["location"])
                continue
            if raw.status >= 500 or raw.status == 429:
                return _RobotsPolicy(disallow_all=True, detail=f"robots.txt answered HTTP {raw.status}")
            if 400 <= raw.status < 500:
                return _RobotsPolicy(allow_all=True, detail=f"robots.txt answered HTTP {raw.status}: no rules")
            parser = robotparser.RobotFileParser()
            parser.parse(raw.body.decode("utf-8", errors="replace").splitlines())
            parser.modified()  # can_fetch() answers False until the parser is marked as checked
            return _RobotsPolicy(parser=parser)
        return _RobotsPolicy(allow_all=True, detail="robots.txt: too many redirects, treated as missing")
