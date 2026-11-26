import subprocess
import sys
from pathlib import Path

import pytest

from outreach import normalize
from outreach.normalize import InvalidUrl, NormalizedUrl, normalize_url

HEB = "xn--6dbbec0c"        # דוגמה
HEB_SHOP = "xn--9dbd1a4b"   # חנות
HEB_TLD = "xn--4dbrk0ce"    # ישראל

# (raw input, expected site_key, expected domain)
VALID = [
    # plain business sites
    ("example.co.il", "example.co.il", "example.co.il"),
    ("http://example.co.il", "example.co.il", "example.co.il"),
    ("https://www.example.co.il/", "example.co.il", "example.co.il"),
    ("HTTPS://WWW.EXAMPLE.CO.IL/About", "example.co.il", "example.co.il"),
    ("Http://Example.Co.Il", "example.co.il", "example.co.il"),
    ("  https://example.co.il  \n", "example.co.il", "example.co.il"),
    ("\thttps://example.co.il\t", "example.co.il", "example.co.il"),
    ("https://example.co.il./", "example.co.il", "example.co.il"),
    ("https://www.example.co.il.:443/", "example.co.il", "example.co.il"),
    ("https://example.co.il:8443/contact", "example.co.il", "example.co.il"),
    ("example.co.il:8080/contact", "example.co.il", "example.co.il"),
    ("https://example.co.il/contact?utm_source=fb&utm_medium=cpc&fbclid=abc", "example.co.il", "example.co.il"),
    ("https://example.co.il/?gclid=xyz#contact", "example.co.il", "example.co.il"),
    ("https://example.co.il/#/home", "example.co.il", "example.co.il"),
    ("https://shop.example.co.il/products", "example.co.il", "shop.example.co.il"),
    ("https://www2.example.co.il/", "example.co.il", "example.co.il"),
    ("www.example.co.il", "example.co.il", "example.co.il"),
    ("//example.co.il/path", "example.co.il", "example.co.il"),
    ("https:\\\\example.co.il\\contact", "example.co.il", "example.co.il"),
    ("example.co.il/צור-קשר", "example.co.il", "example.co.il"),
    ("https://www.example.com", "example.com", "example.com"),
    ("https://blog.example.org.il", "example.org.il", "blog.example.org.il"),
    ("https://dept.uni.ac.il/x", "uni.ac.il", "dept.uni.ac.il"),
    ("https://www2.co.il/", "www2.co.il", "www2.co.il"),
    ("https://ｅxample.co.il", "example.co.il", "example.co.il"),  # full-width letter
    # invisible characters copied from Hebrew (RTL) text
    ("\u200fhttps://example.co.il\u200f", "example.co.il", "example.co.il"),
    ("\u202bhttps://example.co.il/\u202c", "example.co.il", "example.co.il"),
    ("https://example.co.il\u200b", "example.co.il", "example.co.il"),
    ("\ufeffexample.co.il", "example.co.il", "example.co.il"),
    # Hebrew / IDN domains, Unicode and punycode spellings
    ("https://דוגמה.co.il", f"{HEB}.co.il", f"{HEB}.co.il"),
    ("https://www.דוגמה.co.il/צור-קשר", f"{HEB}.co.il", f"{HEB}.co.il"),
    (f"https://{HEB}.co.il/", f"{HEB}.co.il", f"{HEB}.co.il"),
    (f"HTTPS://XN--6DBBEC0C.CO.IL", f"{HEB}.co.il", f"{HEB}.co.il"),
    ("https://חנות.דוגמה.co.il", f"{HEB}.co.il", f"{HEB_SHOP}.{HEB}.co.il"),
    ("https://www.דוגמה.ישראל/", f"{HEB}.{HEB_TLD}", f"{HEB}.{HEB_TLD}"),
    (f"{HEB}.{HEB_TLD}", f"{HEB}.{HEB_TLD}", f"{HEB}.{HEB_TLD}"),
    # platforms: account in the path
    ("https://www.facebook.com/MyBiz", "facebook.com/mybiz", "facebook.com"),
    ("https://m.facebook.com/mybiz/about?ref=page_internal", "facebook.com/mybiz", "facebook.com"),
    ("https://he-il.facebook.com/MyBiz/", "facebook.com/mybiz", "facebook.com"),
    ("https://fb.com/mybiz", "facebook.com/mybiz", "facebook.com"),
    ("https://www.facebook.com/profile.php?id=100012345&ref=xyz", "facebook.com/profile.php?id=100012345", "facebook.com"),
    ("https://www.facebook.com/%D7%A2%D7%A1%D7%A7", "facebook.com/עסק", "facebook.com"),
    ("https://www.facebook.com/עסק", "facebook.com/עסק", "facebook.com"),
    ("https://instagram.com/my.biz/", "instagram.com/my.biz", "instagram.com"),
    ("https://www.instagram.com/my.biz?igsh=xyz", "instagram.com/my.biz", "instagram.com"),
    ("https://linktr.ee/MyBiz", "linktr.ee/mybiz", "linktr.ee"),
    ("https://www.tiktok.com/@mybiz?lang=he", "tiktok.com/@mybiz", "tiktok.com"),
    ("https://twitter.com/MyBiz", "x.com/mybiz", "x.com"),
    ("https://www.linkedin.com/company/my-biz/about/", "linkedin.com/company/my-biz", "linkedin.com"),
    # platforms: account in the subdomain
    ("http://user.wixsite.com/mybiz", "user.wixsite.com/mybiz", "user.wixsite.com"),
    ("https://user.wixsite.com/MyBiz/contact", "user.wixsite.com/mybiz", "user.wixsite.com"),
    ("https://user.wixsite.com/", "user.wixsite.com", "user.wixsite.com"),
    ("https://mybiz.blogspot.com/p/contact.html", "mybiz.blogspot.com", "mybiz.blogspot.com"),
    ("https://mybiz.blogspot.com/2023/05/post.html", "mybiz.blogspot.com", "mybiz.blogspot.com"),
    ("https://mybiz.blogspot.co.il/", "mybiz.blogspot.co.il", "mybiz.blogspot.co.il"),
    ("https://mybiz.github.io/site/", "mybiz.github.io", "mybiz.github.io"),
    ("https://mybiz.wordpress.com/contact/", "mybiz.wordpress.com", "mybiz.wordpress.com"),
    ("https://mybiz.business.site/?utm_source=gmb", "mybiz.business.site", "mybiz.business.site"),
]

INVALID = [
    "",
    "   ",
    "\u200f",
    "mailto:info@example.co.il",
    "MAILTO:info@example.co.il",
    "javascript:void(0)",
    "tel:+972522518189",
    "tel:0522518189",
    "info@example.co.il",
    "http://user:pw@example.co.il/",
    "http://good.co.il@evil.co.il/",
    "ftp://example.co.il",
    "file:///C:/sites.csv",
    "http://",
    "https:///path",
    "localhost",
    "http://localhost:8000/",
    "http://192.168.1.1/",
    "http://[::1]/",
    "N/A",
    "-",
    "example",
    "co.il",
    "example.invalidtld",
    "http://exa mple.co.il",
    "http://exa_mple.co.il",
    "http://-example.co.il",
    "http://example.co.il:99999/",
    "http://example.co.il:abc/",
    "https://www.facebook.com/",
    "https://facebook.com/profile.php",
    "https://linktr.ee",
    "https://www.linkedin.com/company/",
    "https://wixsite.com/mybiz",
    "https://www.blogspot.com/",
    None,
    123,
]


@pytest.mark.parametrize(("raw", "key", "domain"), VALID)
def test_normalize_valid(raw: str, key: str, domain: str) -> None:
    result = normalize_url(raw)
    assert isinstance(result, NormalizedUrl)
    assert result == (key, domain)


@pytest.mark.parametrize("raw", INVALID)
def test_normalize_invalid(raw: object) -> None:
    with pytest.raises(InvalidUrl):
        normalize_url(raw)


SAME_SITE = [
    ["www.example.co.il", "example.co.il", "shop.example.co.il", "https://EXAMPLE.co.il./x?utm_source=a#b",
     "http://example.co.il:8080", "\u200fhttps://www.example.co.il/\u200f"],
    ["https://דוגמה.co.il", f"http://www.{HEB}.co.il/", "https://חנות.דוגמה.co.il/צור-קשר"],
    ["https://www.facebook.com/MyBiz", "https://m.facebook.com/mybiz/", "fb.com/MYBIZ?ref=1"],
    ["https://user.wixsite.com/mybiz", "https://user.wixsite.com/MyBiz/contact-us"],
]

DIFFERENT_SITES = [
    ["https://www.facebook.com/biz-one", "https://www.facebook.com/biz-two",
     "https://www.facebook.com/profile.php?id=1", "https://www.facebook.com/profile.php?id=2"],
    ["https://instagram.com/a", "https://instagram.com/b", "https://linktr.ee/a"],
    ["https://user.wixsite.com/biz-a", "https://user.wixsite.com/biz-b", "https://other.wixsite.com/biz-a"],
    ["https://a.blogspot.com", "https://b.blogspot.com", "https://a.github.io", "https://a.wordpress.com"],
    ["example.co.il", "example.com", "example.org.il", "example2.co.il"],
]


@pytest.mark.parametrize("spellings", SAME_SITE)
def test_spellings_of_one_site_share_a_key(spellings: list[str]) -> None:
    keys = {normalize_url(s).site_key for s in spellings}
    assert len(keys) == 1, keys


@pytest.mark.parametrize("urls", DIFFERENT_SITES)
def test_different_businesses_get_different_keys(urls: list[str]) -> None:
    keys = [normalize_url(u).site_key for u in urls]
    assert len(set(keys)) == len(keys), keys


def test_case_count() -> None:
    assert len(VALID) + len(INVALID) >= 30


def test_platform_list_is_one_extendable_constant() -> None:
    assert "facebook.com" in normalize.PLATFORMS
    assert "wixsite.com" in normalize.PLATFORMS


def test_tldextract_is_configured_offline() -> None:
    assert tuple(normalize._EXTRACT.suffix_list_urls) == ()


def test_normalizer_works_with_network_disabled_from_import() -> None:
    """In a fresh interpreter, break sockets/DNS BEFORE importing the module."""
    src = Path(__file__).resolve().parent.parent / "src"
    code = (
        "import socket\n"
        "def boom(*a, **k): raise SystemExit('network attempted')\n"
        "socket.socket.connect = boom; socket.getaddrinfo = boom; socket.create_connection = boom\n"
        f"import sys; sys.path.insert(0, {str(src)!r})\n"
        "from outreach.normalize import normalize_url\n"
        "print(normalize_url('https://www.example.co.il').site_key)\n"
        "print(normalize_url('https://www.דוגמה.ישראל').site_key)\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["example.co.il", f"{HEB}.{HEB_TLD}"]
