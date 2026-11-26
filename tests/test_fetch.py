import time
from urllib.parse import quote

import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

from conftest import FIXTURES
from outreach.fetch import (FETCH_ERROR, MAX_BODY_BYTES, MAX_REDIRECTS, OK, ROBOTS_BLOCKED, TIMEOUT_SECONDS,
                            USER_AGENT, Fetcher, decode_body)
from outreach.finder import find_contact_form


def paths(server: HTTPServer) -> list[str]:
    return [req.path for req, _ in server.log]


def robots(server: HTTPServer, body: str = "User-agent: *\nAllow: /\n", status: int = 200) -> None:
    server.expect_request("/robots.txt").respond_with_data(body, status=status, content_type="text/plain")


@pytest.fixture
def fetcher():
    with Fetcher(delay_seconds=0) as f:
        yield f


def test_constants_match_the_prompt() -> None:
    assert USER_AGENT == "PosibloOutreachBot/1.0 (+https://posiblo.com; posiblo.contact@gmail.com)"
    assert TIMEOUT_SECONDS == 15
    assert MAX_BODY_BYTES == 2 * 1024 * 1024
    assert MAX_REDIRECTS == 3
    f = Fetcher()
    assert f.timeout == 15 and f.max_bytes == 2 * 1024 * 1024 and f.delay_seconds == 5
    f.close()


def test_sends_honest_user_agent_and_only_get(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    httpserver.expect_request("/").respond_with_data("<html>hi</html>", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/"))
    assert r.outcome == OK and r.text == "<html>hi</html>"
    assert {req.headers["User-Agent"] for req, _ in httpserver.log} == {USER_AGENT}
    assert {req.method for req, _ in httpserver.log} == {"GET"}


def test_robots_disallowed_page_is_never_requested(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver, "User-agent: *\nDisallow: /contact\n")
    httpserver.expect_request("/contact").respond_with_data("SHOULD NOT BE FETCHED")
    httpserver.expect_request("/about").respond_with_data("<p>about</p>", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/contact"))
    assert r.outcome == ROBOTS_BLOCKED and "robots.txt" in r.detail
    assert fetcher.get(httpserver.url_for("/about")).outcome == OK
    assert "/contact" not in paths(httpserver)
    assert paths(httpserver) == ["/robots.txt", "/about"]


def test_robots_rules_for_our_agent(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver, "User-agent: PosibloOutreachBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n")
    assert fetcher.get(httpserver.url_for("/")).outcome == ROBOTS_BLOCKED
    assert paths(httpserver) == ["/robots.txt"]


def test_robots_fetched_once_per_host(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    for p in ("/a", "/b", "/c"):
        httpserver.expect_request(p).respond_with_data("ok", content_type="text/html")
        fetcher.get(httpserver.url_for(p))
    assert paths(httpserver).count("/robots.txt") == 1


@pytest.mark.parametrize(("status", "allowed"), [(404, True), (410, True), (401, True), (403, True), (400, True),
                                                 (429, False), (500, False), (502, False), (503, False)])
def test_robots_status_handling(httpserver: HTTPServer, fetcher: Fetcher, status: int, allowed: bool) -> None:
    robots(httpserver, "", status=status)
    httpserver.expect_request("/").respond_with_data("ok", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/"))
    assert (r.outcome == OK) is allowed
    assert ("/" in paths(httpserver)) is allowed


def test_hebrew_path_and_robots(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    contact = "/" + quote("צור-קשר") + "/"
    robots(httpserver, f"User-agent: *\nDisallow: {contact}\n")
    httpserver.expect_request("/צור-קשר/").respond_with_data("x")
    assert fetcher.get(httpserver.url_for(contact)).outcome == ROBOTS_BLOCKED
    assert paths(httpserver) == ["/robots.txt"]


def test_per_host_delay_is_applied(httpserver: HTTPServer) -> None:
    now = [100.0]
    sleeps: list[float] = []

    def sleep(s: float) -> None:
        sleeps.append(s)
        now[0] += s

    robots(httpserver)
    httpserver.expect_request("/p").respond_with_data("ok", content_type="text/html")
    with Fetcher(delay_seconds=5, clock=lambda: now[0], sleep=sleep) as f:
        f.get(httpserver.url_for("/p"))   # robots.txt at t=100, then /p must wait 5s
        f.get(httpserver.url_for("/p"))   # again 5s later
        assert sleeps == [5.0, 5.0]
        now[0] += 60                       # long pause: no wait needed
        f.get(httpserver.url_for("/p"))
        assert sleeps == [5.0, 5.0]


def test_delay_is_per_host(httpserver: HTTPServer) -> None:
    now = [0.0]
    sleeps: list[float] = []
    robots(httpserver)
    httpserver.expect_request("/p").respond_with_data("ok", content_type="text/html")
    other = httpserver.url_for("/p").replace("localhost", "127.0.0.1")
    with Fetcher(delay_seconds=5, clock=lambda: now[0], sleep=lambda s: sleeps.append(s)) as f:
        f.get(other)                                  # host A: robots, then page (waits once)
        assert len(sleeps) == 1
        f.get(httpserver.url_for("/p").replace("127.0.0.1", "localhost"))  # host B: its own robots, then page
        assert len(sleeps) == 2  # only the wait inside host B, nothing carried over from host A


def test_body_cap_with_content_length(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    httpserver.expect_request("/big").respond_with_data(b"x" * (MAX_BODY_BYTES + 1), content_type="text/html")
    httpserver.expect_request("/ok").respond_with_data(b"x" * MAX_BODY_BYTES, content_type="text/html")
    r = fetcher.get(httpserver.url_for("/big"))
    assert r.outcome == FETCH_ERROR and "too large" in r.detail
    assert fetcher.get(httpserver.url_for("/ok")).outcome == OK  # exactly 2 MB is allowed


def test_body_cap_when_streamed_without_length(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)

    def stream(_request):
        def gen():
            for _ in range(5):
                yield b"y" * (512 * 1024)  # 2.5 MB total, no Content-Length
        return Response(gen(), content_type="text/html", direct_passthrough=True)

    httpserver.expect_request("/stream").respond_with_handler(stream)
    r = fetcher.get(httpserver.url_for("/stream"))
    assert r.outcome == FETCH_ERROR and "too large" in r.detail


def test_up_to_three_redirects_followed(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    for a, b in (("/r1", "/r2"), ("/r2", "/r3"), ("/r3", "/final")):
        httpserver.expect_request(a).respond_with_data("", status=302, headers={"Location": b})
    httpserver.expect_request("/final").respond_with_data("done", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/r1"))
    assert r.outcome == OK and r.text == "done" and r.url.endswith("/final")
    assert len(r.redirects) == 3


def test_fourth_redirect_is_refused(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    chain = ["/s1", "/s2", "/s3", "/s4", "/final"]
    for a, b in zip(chain, chain[1:]):
        httpserver.expect_request(a).respond_with_data("", status=301, headers={"Location": b})
    httpserver.expect_request("/final").respond_with_data("never")
    r = fetcher.get(httpserver.url_for("/s1"))
    assert r.outcome == FETCH_ERROR and "redirects" in r.detail
    assert "/final" not in paths(httpserver)


def test_redirect_to_other_domain_is_refused(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    elsewhere = httpserver.url_for("/elsewhere").replace("127.0.0.1", "localhost")
    assert elsewhere != httpserver.url_for("/elsewhere")  # a different host name for the same machine
    httpserver.expect_request("/go").respond_with_data("", status=302, headers={"Location": elsewhere})
    httpserver.expect_request("/elsewhere").respond_with_data("never")
    r = fetcher.get(httpserver.url_for("/go"))
    assert r.outcome == FETCH_ERROR and "another domain" in r.detail
    assert "/elsewhere" not in paths(httpserver)


def test_timeout_and_no_retry(httpserver: HTTPServer) -> None:
    robots(httpserver)

    def slow(_request):
        time.sleep(1.5)
        return Response("late", content_type="text/html")

    httpserver.expect_request("/slow").respond_with_handler(slow)
    with Fetcher(delay_seconds=0, timeout=0.5) as f:
        r = f.get(httpserver.url_for("/slow"))
    assert r.outcome == FETCH_ERROR and "timeout" in r.detail
    time.sleep(1.2)  # let the server finish the slow handler before counting
    assert paths(httpserver).count("/slow") == 1


def test_server_error_is_not_retried(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    httpserver.expect_request("/err").respond_with_data("boom", status=500)
    r = fetcher.get(httpserver.url_for("/err"))
    assert r.outcome == FETCH_ERROR and r.status_code == 500 and r.detail == "HTTP 500"
    assert paths(httpserver).count("/err") == 1


def test_robots_network_error_means_disallow(fetcher: Fetcher) -> None:
    """robots.txt cannot be reached at all (connection refused): disallow, and the page is not requested."""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # nothing listens here now
    r = fetcher.get(f"http://127.0.0.1:{port}/")
    assert r.outcome == ROBOTS_BLOCKED and "not reachable" in r.detail
    assert fetcher.requested == [f"http://127.0.0.1:{port}/robots.txt"]


def test_robots_timeout_means_disallow(httpserver: HTTPServer) -> None:
    def slow(_request):
        time.sleep(1.5)
        return Response("User-agent: *\nAllow: /\n", content_type="text/plain")

    httpserver.expect_request("/robots.txt").respond_with_handler(slow)
    httpserver.expect_request("/").respond_with_data("page", content_type="text/html")
    with Fetcher(delay_seconds=0, timeout=0.5) as f:
        r = f.get(httpserver.url_for("/"))
    assert r.outcome == ROBOTS_BLOCKED and "timeout" in r.detail
    time.sleep(1.2)
    assert paths(httpserver) == ["/robots.txt"]


def test_robots_404_means_allow_and_page_is_fetched(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    httpserver.expect_request("/robots.txt").respond_with_data("Not Found", status=404)
    httpserver.expect_request("/contact").respond_with_data("<p>contact</p>", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/contact"))
    assert r.outcome == OK
    assert paths(httpserver) == ["/robots.txt", "/contact"]


def test_robots_429_means_disallow_and_page_is_not_requested(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    """429 Too Many Requests on robots.txt is a request to slow down: treated like 5xx (owner's decision)."""
    robots(httpserver, "slow down", status=429)
    httpserver.expect_request("/").respond_with_data("ok", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/"))
    assert r.outcome == ROBOTS_BLOCKED and "429" in r.detail
    assert paths(httpserver) == ["/robots.txt"]


@pytest.mark.parametrize("status", [401, 403])
def test_robots_401_403_mean_allow_and_page_is_fetched(httpserver: HTTPServer, fetcher: Fetcher, status: int) -> None:
    robots(httpserver, "forbidden", status=status)
    httpserver.expect_request("/").respond_with_data("ok", content_type="text/html")
    assert fetcher.get(httpserver.url_for("/")).outcome == OK
    assert paths(httpserver) == ["/robots.txt", "/"]


@pytest.mark.parametrize(("encoding", "content_type", "meta"), [
    ("cp1255", "text/html; charset=windows-1255", ""),
    ("cp1255", "text/html; charset=ISO-8859-8", ""),
    ("cp1255", "text/html", '<meta http-equiv="Content-Type" content="text/html; charset=windows-1255">'),
    ("cp1255", "text/html", ""),  # no declaration at all: UTF-8 fails, Windows-1255 fallback
    ("utf-8", "text/html", ""),
    ("utf-8", "text/html; charset=utf-8", '<meta charset="utf-8">'),
])
def test_hebrew_decoding(httpserver: HTTPServer, fetcher: Fetcher, encoding: str, content_type: str,
                         meta: str) -> None:
    robots(httpserver)
    html = f"<html><head>{meta}</head><body>צור קשר עם המספרה</body></html>"
    httpserver.expect_request("/he").respond_with_data(html.encode(encoding), content_type=content_type)
    r = fetcher.get(httpserver.url_for("/he"))
    assert r.outcome == OK
    assert "צור קשר עם המספרה" in r.text


def test_decode_body_unit() -> None:
    assert decode_body("שלום".encode("cp1255"), "text/html; charset=iso-8859-8-i") == "שלום"
    assert decode_body(b"\xef\xbb\xbf" + "שלום".encode("utf-8"), None) == "שלום"


def test_finder_against_live_local_server(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    """End-to-end on a local server: robots blocks /contact, the Hebrew contact page is used."""
    robots(httpserver, "User-agent: *\nDisallow: /contact\n")
    httpserver.expect_request("/").respond_with_data(
        (FIXTURES / "home_with_contact_link.html").read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
    httpserver.expect_request("/צור-קשר/").respond_with_data(
        (FIXTURES / "cf7_hebrew.html").read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
    r = find_contact_form(httpserver.url_for("/"), fetcher)
    assert r.status == "ready", r.detail
    assert r.plan.hidden_fields["_wpcf7"] == "42"
    got = paths(httpserver)
    assert got == ["/robots.txt", "/", "/צור-קשר/"]
    assert {req.method for req, _ in httpserver.log} == {"GET"}


def test_finder_extra_fetch_limit_on_live_server(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    robots(httpserver)
    links = "".join(f'<a href="/contact-{i}">צור קשר</a>' for i in range(8))
    httpserver.expect_request("/").respond_with_data(f"<html><body>{links}</body></html>", content_type="text/html")
    r = find_contact_form(httpserver.url_for("/"), fetcher)
    assert r.status == "no_form"
    pages = [p for p in paths(httpserver) if p != "/robots.txt"]
    assert len(pages) == 4  # homepage + at most 3 extra


def test_robots_redirect_to_another_host_is_followed(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    other = httpserver.url_for("/robots-elsewhere.txt").replace("127.0.0.1", "localhost")
    httpserver.expect_request("/robots.txt").respond_with_data("", status=301, headers={"Location": other})
    httpserver.expect_request("/robots-elsewhere.txt").respond_with_data("User-agent: *\nDisallow: /private\n")
    httpserver.expect_request("/public").respond_with_data("ok", content_type="text/html")
    assert fetcher.get(httpserver.url_for("/private")).outcome == ROBOTS_BLOCKED   # the target's rules apply
    assert fetcher.get(httpserver.url_for("/public")).outcome == OK


def test_robots_too_many_redirects_is_treated_as_missing(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    chain = ["/robots.txt", "/r1", "/r2", "/r3", "/r4"]
    for a, b in zip(chain, chain[1:]):
        httpserver.expect_request(a).respond_with_data("", status=302, headers={"Location": b})
    httpserver.expect_request("/page").respond_with_data("ok", content_type="text/html")
    r = fetcher.get(httpserver.url_for("/page"))
    assert r.outcome == OK
    assert "/r4" not in paths(httpserver)


def test_oversized_robots_is_parsed_up_to_the_cap(httpserver: HTTPServer, fetcher: Fetcher) -> None:
    body = "User-agent: *\nDisallow: /private\n" + "# padding\n" * (MAX_BODY_BYTES // 10 + 10)
    httpserver.expect_request("/robots.txt").respond_with_data(body, content_type="text/plain")
    httpserver.expect_request("/public").respond_with_data("ok", content_type="text/html")
    assert fetcher.get(httpserver.url_for("/private")).outcome == ROBOTS_BLOCKED
    assert fetcher.get(httpserver.url_for("/public")).outcome == OK