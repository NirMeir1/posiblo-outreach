"""Turn a raw website URL from the input CSV into a stable per-site key.

normalize_url(raw) -> NormalizedUrl(site_key, domain), or raises InvalidUrl.

- Normal sites: site_key is the registrable domain (eTLD+1, e.g. example.co.il),
  so www.example.co.il, example.co.il and shop.example.co.il share one key.
- Shared platforms (see PLATFORMS): the key also carries the part of the URL
  that identifies the business (host and/or leading path segments), so two
  businesses on one platform do not collide.
- Hosts are kept in ASCII/punycode form (one canonical spelling for IDN /
  Hebrew domains). Platform path segments are percent-decoded and lowercased.

No network access: tldextract uses only its bundled public-suffix snapshot.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import NamedTuple
from urllib.parse import parse_qs, unquote, urlsplit

import tldextract


class InvalidUrl(ValueError):
    """The input cannot be turned into a website key."""


class NormalizedUrl(NamedTuple):
    site_key: str
    domain: str  # normalized host to visit: lowercase, ASCII/punycode, no port, no leading "www."


@dataclass(frozen=True)
class Platform:
    """How a shared host identifies one business.

    key_host: canonical host for platforms where the account is in the PATH
        (facebook.com/biz). None means the account is in the SUBDOMAIN
        (biz.blogspot.com) and the visited host is kept in the key.
    path_segments: how many leading path segments belong to the key.
        For path platforms they are required (a bare facebook.com is not a
        business); for subdomain platforms they are added when present.
    """

    key_host: str | None
    path_segments: int


# One place to extend. Keyed by registrable domain (as tldextract reports it,
# without PSL private domains).
PLATFORMS: dict[str, Platform] = {
    # account in the path
    "facebook.com": Platform("facebook.com", 1),
    "fb.com": Platform("facebook.com", 1),
    "fb.me": Platform("facebook.com", 1),
    "instagram.com": Platform("instagram.com", 1),
    "linktr.ee": Platform("linktr.ee", 1),
    "tiktok.com": Platform("tiktok.com", 1),
    "x.com": Platform("x.com", 1),
    "twitter.com": Platform("x.com", 1),
    "youtube.com": Platform("youtube.com", 1),
    "linkedin.com": Platform("linkedin.com", 2),  # /company/<name>, /in/<name>
    "wa.me": Platform("wa.me", 1),
    # account in the subdomain (+ optional path segments)
    "wixsite.com": Platform(None, 1),  # <user>.wixsite.com/<site>
    "blogspot.com": Platform(None, 0),
    "blogspot.co.il": Platform(None, 0),
    "github.io": Platform(None, 0),
    "wordpress.com": Platform(None, 0),
    "business.site": Platform(None, 0),
    "netlify.app": Platform(None, 0),
    "vercel.app": Platform(None, 0),
    "webflow.io": Platform(None, 0),
    "weebly.com": Platform(None, 0),
    "mystrikingly.com": Platform(None, 0),
    "site123.me": Platform(None, 0),
}

_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

# Invisible characters that commonly sneak in when URLs are copied from Hebrew
# (RTL) text: bidi marks/embeddings/isolates, zero-width chars, BOM.
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁩﻿­]")
_SCHEME_LIKE = re.compile(r"^([a-z][a-z0-9+.-]*):(.*)$", re.DOTALL)
_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_WWW = re.compile(r"^www\d*\.")


def normalize_url(raw: object) -> NormalizedUrl:
    if not isinstance(raw, str):
        raise InvalidUrl(f"not a string: {raw!r}")
    s = _INVISIBLE.sub("", raw).strip().replace("\\", "/")
    if not s:
        raise InvalidUrl("empty")

    low = s.lower()
    if low.startswith("//"):
        s = "http:" + s
    elif "://" in low:
        scheme = low.split("://", 1)[0]
        if scheme not in ("http", "https"):
            raise InvalidUrl(f"unsupported scheme: {scheme}")
    else:
        m = _SCHEME_LIKE.match(low)
        # "example.co.il:8080/x" is host:port, "mailto:x" / "javascript:x" is junk.
        if m and not re.match(r"^\d+(?:[/?#]|$)", m.group(2)):
            raise InvalidUrl(f"unsupported scheme: {m.group(1)}")
        s = "http://" + s

    try:
        parts = urlsplit(s)
        parts.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError as e:
        raise InvalidUrl(f"unparseable: {e}") from None
    if "@" in parts.netloc:
        raise InvalidUrl("user info in URL (email address or obfuscated host)")

    host = _ascii_host(parts.hostname or "")
    ext = _EXTRACT(host)
    if not ext.suffix:
        raise InvalidUrl(f"unknown top-level domain: {host}")
    if not ext.domain:
        raise InvalidUrl(f"no registrable domain: {host}")
    registrable = f"{ext.domain}.{ext.suffix}"
    stripped = _WWW.sub("", host)
    # Drop a leading "www." only if it is not itself the registrable label
    # (www2.co.il is a site called "www2", not a www prefix).
    if stripped == registrable or stripped.endswith("." + registrable):
        host = stripped

    platform = PLATFORMS.get(registrable)
    if platform is None:
        return NormalizedUrl(registrable, host)
    return _platform_key(platform, registrable, host, parts.path, parts.query)


def registrable_domain(host: str) -> str:
    """eTLD+1 of a host, for same-site checks (redirects, form actions).

    IP addresses and hosts without a public suffix (e.g. localhost) are their
    own "registrable domain", so they only match themselves.
    """
    h = (host or "").strip().rstrip(".").lower()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    try:
        ipaddress.ip_address(h)
        return h
    except ValueError:
        pass
    try:
        h = h.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return h
    ext = _EXTRACT(h)
    if not ext.suffix or not ext.domain:
        return h
    return f"{ext.domain}.{ext.suffix}"


def _ascii_host(host: str) -> str:
    host = host.strip().rstrip(".").lower()
    if not host:
        raise InvalidUrl("no host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise InvalidUrl(f"IP address, not a domain: {host}")
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as e:
        raise InvalidUrl(f"invalid domain {host!r}: {e}") from None
    labels = ascii_host.split(".")
    if len(labels) < 2 or len(ascii_host) > 253 or not all(_LABEL.match(l) for l in labels):
        raise InvalidUrl(f"invalid domain: {host!r}")
    return ascii_host


def _segments(path: str) -> list[str]:
    return [unquote(p).strip().lower() for p in path.split("/") if unquote(p).strip()]


def _platform_key(platform: Platform, registrable: str, host: str, path: str, query: str) -> NormalizedUrl:
    segs = _segments(path)
    if platform.key_host is not None:
        # Account in the path: facebook.com/<account>
        if platform.key_host == "facebook.com" and segs[:1] == ["profile.php"]:
            ids = parse_qs(query).get("id", [])
            if not ids or not ids[0].isdigit():
                raise InvalidUrl("facebook profile.php without a numeric id")
            return NormalizedUrl(f"facebook.com/profile.php?id={ids[0]}", platform.key_host)
        if len(segs) < platform.path_segments:
            raise InvalidUrl(f"platform URL without an account: {registrable}")
        key = "/".join([platform.key_host, *segs[: platform.path_segments]])
        return NormalizedUrl(key, platform.key_host)
    # Account in the subdomain: <account>.blogspot.com
    if host in (registrable, f"www.{registrable}"):
        raise InvalidUrl(f"platform URL without an account: {registrable}")
    key = "/".join([host, *segs[: platform.path_segments]])
    return NormalizedUrl(key, host)
