"""Dependency versions are pinned, so URL keying (tldextract's suffix list) cannot change silently."""

import importlib.metadata
import re
import tomllib

from conftest import REPO


def _lock() -> dict[str, str]:
    pins = {}
    for line in (REPO / "requirements.lock").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].split(";", 1)[0].strip()
        if line:
            name, version = line.split("==")
            pins[re.sub(r"[-_.]+", "-", name).lower()] = version.strip()
    return pins


def _pyproject_pins() -> dict[str, str]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    specs = list(data["project"]["dependencies"]) + list(data["project"]["optional-dependencies"]["dev"])
    pins = {}
    for spec in specs:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", spec), f"not an exact pin: {spec!r}"
        name, version = spec.split("==")
        pins[re.sub(r"[-_.]+", "-", name).lower()] = version
    return pins


def test_every_direct_dependency_is_an_exact_pin_matching_the_lock() -> None:
    lock, direct = _lock(), _pyproject_pins()
    for name, version in direct.items():
        assert lock.get(name) == version, f"{name}: pyproject {version} vs lock {lock.get(name)}"


def test_tldextract_is_pinned_and_installed_at_the_pinned_version() -> None:
    lock = _lock()
    assert lock["tldextract"] == "5.4.0"
    assert importlib.metadata.version("tldextract") == lock["tldextract"], \
        "installed tldextract differs from requirements.lock: site keys could change"


def test_installed_packages_match_the_lock() -> None:
    lock = _lock()
    mismatched = {}
    for name, version in lock.items():
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            if name == "colorama":  # only on Windows (platform marker)
                continue
            installed = None
        if installed != version:
            mismatched[name] = (version, installed)
    assert not mismatched, f"lock vs installed: {mismatched} (run: pip install -r requirements.lock)"
