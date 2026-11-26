"""Mechanical checks from docs/validation.md (stdlib only).

Usage:
    python scripts/validate.py --step N        # "Always" checks + section for step N
    python scripts/validate.py --step N --log  # same, and record the result in docs/validation-log.md
    python scripts/validate.py --all           # "Always" + the latest step's section + the
                                               # checks of earlier steps that must stay true

Each check prints PASS, FAIL or MANUAL (MANUAL = needs a human/assistant to
look at the listed evidence). Exit code is 1 if any check FAILs.

Run it with the project's virtualenv interpreter so that A1 can run pytest,
e.g. `.venv\\Scripts\\python scripts/validate.py --step 0`. Project code is
only ever run in a subprocess, so this script itself needs only the stdlib.
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
LOG = ROOT / "docs" / "validation-log.md"
BUILD_PROMPTS = ROOT / "docs" / "build-prompts.md"

LATEST_IMPLEMENTED_STEP = 7

# CLI commands that must exist (and no others) after each step (A8).
EXPECTED_COMMANDS: dict[int, list[str]] = {
    2: ["ingest", "status", "backup", "suppress"],
    3: ["ingest", "status", "backup", "suppress"],
    4: ["ingest", "status", "backup", "suppress", "dry-run", "approve", "export"],
    5: ["ingest", "status", "backup", "suppress", "dry-run", "approve", "export", "send", "reopen"],
    6: ["ingest", "status", "backup", "suppress", "dry-run", "approve", "export", "send", "reopen", "dashboard",
        "clear-stop"],
    7: ["ingest", "status", "backup", "suppress", "dry-run", "approve", "export", "send", "reopen", "dashboard",
        "clear-stop"],
}

# --- reference data -------------------------------------------------------

FORBIDDEN_AI = [
    "anthropic", "openai", "google-generativeai", "google.generativeai",
    "google-genai", "google.genai", "vertexai", "langchain", "langgraph",
    "litellm", "cohere", "mistralai", "transformers", "huggingface_hub",
    "huggingface-hub", "llama_index", "llama-index", "llama_cpp", "ollama",
    "groq", "sentence_transformers", "sentence-transformers", "tiktoken",
]
_AI_RE = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(t) for t in FORBIDDEN_AI) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

REQUIRED_GITIGNORE = [
    "data/*", "backups/", "logs/", "reports/", ".env", "*.db", "*.db-wal",
    "*.db-shm", "STOP", "__pycache__", ".venv",
]

# Files that are introduced by a specific prompt. Their presence at an earlier
# step is a scope violation (A6).
LATER_FILES: dict[str, int] = {
    "src/outreach/normalize.py": 1,
    "src/outreach/ledger.py": 1,
    "src/outreach/config.py": 2,
    "src/outreach/backup.py": 2,
    "src/outreach/sendlog.py": 2,
    "src/outreach/preflight.py": 2,
    "src/outreach/breaker.py": 2,
    "src/outreach/cli.py": 2,
    "src/outreach/__main__.py": 2,
    "src/outreach/ingest.py": 2,
    "templates/consent_request_v1.txt": 2,
    "src/outreach/fetch.py": 3,
    "src/outreach/finder.py": 3,
    "src/outreach/classify.py": 3,
    "src/outreach/detect.py": 3,
    "src/outreach/plan.py": 3,
    "src/outreach/dryrun.py": 4,
    "src/outreach/approve.py": 4,
    "src/outreach/export.py": 4,
    "src/outreach/send.py": 5,
    "src/outreach/verify.py": 5,
    "src/outreach/reopen.py": 5,
    "src/outreach/dashboard.py": 6,
}
LATER_DEPS: dict[str, int] = {
    "pytest-httpserver": 3,
    "flask": 6,
}
# Files the validation protocol itself allows at any step.
PROTOCOL_FILES = {"scripts/validate.py", "docs/validation-log.md", "docs/validation.md"}


# --- result plumbing --------------------------------------------------------

@dataclass
class Result:
    cid: str
    status: str  # PASS / FAIL / MANUAL
    evidence: list[str] = field(default_factory=list)


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def _git_ls_files() -> list[str]:
    return [p for p in _run(["git", "ls-files"]).stdout.splitlines() if p]


def _py_files(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _norm_ignore(entry: str) -> str:
    return entry.strip().rstrip("/")


# --- Always ---------------------------------------------------------------

def _previous_test_count(step: int) -> tuple[int | None, int | None]:
    """Return (step, count) of the most recent logged step lower than `step`."""
    if not LOG.exists():
        return None, None
    best: tuple[int | None, int | None] = (None, None)
    for line in LOG.read_text(encoding="utf-8-sig").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[1].isdigit() and cells[2].isdigit():
            s, n = int(cells[1]), int(cells[2])
            if s < step and (best[0] is None or s > best[0]):
                best = (s, n)
    return best


def _junit_outcomes(xml_path: Path) -> dict[str, str]:
    """Map 'tests/file.py::test_name[param]' -> passed/failed/error/skipped."""
    out: dict[str, str] = {}
    if not xml_path.exists():
        return out
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        mod = case.get("classname", "").replace(".", "/")
        name = f"{mod}.py::{case.get('name')}"
        outcome = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                outcome = {"failure": "failed"}.get(child.tag, child.tag)
        out[name] = outcome
    return out


def check_a1(step: int, state: dict) -> Result:
    with tempfile.TemporaryDirectory() as td:
        xml = Path(td) / "junit.xml"
        proc = _run([sys.executable, "-m", "pytest", "-q", "-rsx", f"--junitxml={xml}"])
        state["junit"] = _junit_outcomes(xml)
    tail = [l for l in proc.stdout.splitlines() if l.strip()][-3:]
    summary = tail[-1] if tail else "(no output)"
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", summary)) else 0
    bad = re.findall(r"(\d+) (failed|error|errors|skipped|xfailed|xpassed)", summary)
    state["test_count"] = passed
    ev = [f"interpreter: {sys.executable}", f"pytest summary: {summary.strip()}"]
    ok = proc.returncode == 0 and passed > 0 and not bad
    prev_step, prev_n = _previous_test_count(step)
    if prev_n is None:
        ev.append("no earlier step in docs/validation-log.md to compare with")
    else:
        ev.append(f"previous step {prev_step}: {prev_n} tests; now {passed}")
        if passed < prev_n:
            ok = False
            ev.append("test count went DOWN")
    if bad:
        ev.append(f"non-pass outcomes: {bad}")
    return Result("A1", "PASS" if ok else "FAIL", ev)


def check_a2(step: int, state: dict) -> Result:
    files = _git_ls_files()
    offenders = []
    for f in files:
        name = f.rsplit("/", 1)[-1]
        if (f.startswith("data/") and f != "data/.gitkeep") \
                or f.endswith((".db", ".db-wal", ".db-shm")) \
                or f.startswith(("backups/", "logs/", "reports/")) \
                or name == ".env" or name == "STOP":
            offenders.append(f)
    ev = [f"git ls-files: {len(files)} tracked files"]
    ev += [f"tracked sensitive file: {o}" for o in offenders] or ["no sensitive paths tracked"]
    # Also prove the ignore rules work on sample paths (covers untracked files too).
    probes = ["data/input.csv", "data/ledger.db", "x.db", "x.db-wal", "x.db-shm",
              "backups/b.db", "logs/send.jsonl", "reports/r.csv", ".env", "STOP"]
    ignored = set(_run(["git", "check-ignore", "--no-index", *probes]).stdout.split())
    not_ignored = [p for p in probes if p not in ignored]
    keep = _run(["git", "check-ignore", "--no-index", "-q", "data/.gitkeep"]).returncode
    ev.append(f"git check-ignore: {len(probes) - len(not_ignored)}/{len(probes)} sample sensitive paths ignored")
    if not_ignored:
        ev.append(f"NOT ignored: {not_ignored}")
    ev.append("data/.gitkeep is " + ("NOT ignored (kept)" if keep == 1 else "IGNORED (wrong)"))
    ok = not offenders and not not_ignored and keep == 1
    return Result("A2", "PASS" if ok else "FAIL", ev)


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8-sig"))


def _dep_name(spec: str) -> str:
    return re.split(r"[\s<>=!~;\[(]", spec.strip(), maxsplit=1)[0].lower()


def check_a3(step: int, state: dict) -> Result:
    hits: list[str] = []
    data = _pyproject()
    proj = data.get("project", {})
    all_specs = list(proj.get("dependencies", []))
    for group in proj.get("optional-dependencies", {}).values():
        all_specs += group
    for group in data.get("dependency-groups", {}).values():
        all_specs += [g for g in group if isinstance(g, str)]
    for spec in all_specs:
        if _AI_RE.search(spec):
            hits.append(f"pyproject.toml dependency: {spec}")
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8-sig")
    for i, line in enumerate(text.splitlines(), 1):
        if _AI_RE.search(line):
            hits.append(f"pyproject.toml:{i}: {line.strip()}")
    n_src = 0
    for p in _py_files(SRC):
        n_src += 1
        src = p.read_text(encoding="utf-8-sig")
        for node in ast.walk(ast.parse(src)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                if _AI_RE.search(m):
                    hits.append(f"{_rel(p)}:{node.lineno}: import {m}")
        for i, line in enumerate(src.splitlines(), 1):
            if _AI_RE.search(line):
                hits.append(f"{_rel(p)}:{i}: {line.strip()}")
    installed = sorted({(d.metadata["Name"] or "").lower() for d in importlib.metadata.distributions()})
    inst_hits = [n for n in installed if _AI_RE.fullmatch(n)]
    hits += [f"installed in environment: {n}" for n in inst_hits]
    ev = [f"scanned pyproject.toml ({len(all_specs)} dependency specs), {n_src} .py files in src/, "
          f"{len(installed)} installed distributions",
          f"forbidden names checked: {len(FORBIDDEN_AI)}"]
    ev += hits or ["no LLM/AI SDK names found"]
    return Result("A3", "FAIL" if hits else "PASS", ev)


def _expected_claude_md() -> str:
    """Extract the CLAUDE.md text from Prompt 0 in docs/build-prompts.md."""
    text = BUILD_PROMPTS.read_text(encoding="utf-8-sig")
    start = text.index("CLAUDE.md content:") + len("CLAUDE.md content:")
    end = text.index("When done: show the file tree", start)
    return text[start:end].strip()


def _norm_text(s: str) -> list[str]:
    return [l.rstrip() for l in s.strip().splitlines()]


def check_a4(step: int, state: dict) -> Result:
    path = ROOT / "CLAUDE.md"
    if not path.exists():
        return Result("A4", "FAIL", ["CLAUDE.md missing"])
    actual = path.read_text(encoding="utf-8-sig")
    lines = set(_norm_text(actual))
    expected = _norm_text(_expected_claude_md())
    missing = [l for l in expected if l and l not in lines]
    rules = [l for l in expected if re.match(r"^\d+\. ", l)]
    ev = [f"expected text extracted from {_rel(BUILD_PROMPTS)} (Prompt 0): {len(expected)} lines, "
          f"{len(rules)} numbered rules",
          f"rules present: {sum(r in lines for r in rules)}/{len(rules)}",
          "status list present: " + str(any(l.startswith("pending, sent, sent_unconfirmed") for l in lines)),
          "conventions present: " + str("## Conventions" in lines)]
    ev += [f"missing line: {m[:90]}" for m in missing]
    ok = not missing and len(rules) == 10
    return Result("A4", "PASS" if ok else "FAIL", ev)


NET_MODULES = ("httpx", "requests", "urllib.request", "urllib3", "http.client",
               "socket", "aiohttp", "pytest_httpserver")


def check_a5(step: int, state: dict) -> Result:
    """Static part of A5: which tests use a network client, and which hosts they mention."""
    users: list[str] = []
    for p in _py_files(TESTS):
        tree = ast.parse(p.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                if m.split(".")[0] in {n.split(".")[0] for n in NET_MODULES} and \
                        any(m == n or m.startswith(n + ".") or n.startswith(m + ".") or m == n.split(".")[0]
                            for n in NET_MODULES):
                    users.append(f"{_rel(p)}:{node.lineno}: imports {m}")
    ev = [f"scanned {len(_py_files(TESTS))} test files for network client imports"]
    if not users:
        ev.append("no test imports a network client; nothing can contact a website")
        return Result("A5", "PASS", ev)
    ev += users
    # Runtime guard: tests/conftest.py blocks every non-loopback connect/DNS lookup.
    conftest = TESTS / "conftest.py"
    guard = conftest.exists() and all(s in conftest.read_text(encoding="utf-8-sig") for s in
                                      ("autouse=True", "_block_real_network", "getaddrinfo", "connect_ex"))
    junit = state.get("junit", {})
    guard_tests = {k: v for k, v in junit.items() if k.startswith("tests/test_network_guard.py::")}
    guard_ok = guard and len(guard_tests) >= 3 and all(v == "passed" for v in guard_tests.values())
    ev.append(f"tests/conftest.py autouse guard (connect, connect_ex, getaddrinfo -> loopback only): "
              f"{'present' if guard else 'MISSING'}")
    ev.append(f"guard self-tests: {guard_tests or 'none found'}")
    subproc = []
    for p in _py_files(TESTS):
        txt = p.read_text(encoding="utf-8-sig")
        for i, line in enumerate(txt.splitlines(), 1):
            if re.search(r"\b(subprocess\.run|ctx\.Process|mp\.Process|Popen)\(", line):
                subproc.append(f"{_rel(p)}:{i}: {line.strip()[:80]}")
    if guard_ok:
        ev.append("in-process network use is limited to loopback by the guard")
        ev += [f"runs outside the guard (review by hand): {s}" for s in subproc] or ["no subprocess-based tests"]
        return Result("A5", "PASS", ev)
    ev.append("review: confirm every request in these files targets 127.0.0.1/localhost")
    return Result("A5", "MANUAL", ev)


def check_a6(step: int, state: dict) -> Result:
    out = _run(["git", "status", "--porcelain=v1", "-uall"]).stdout.splitlines()
    changed = []
    for line in out:
        code, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.append((code.strip() or "?", path))
    ev = [f"files added/changed since last commit: {len(changed)}"]
    ev += [f"{c:>2} {p}" + ("  (validation protocol file)" if p in PROTOCOL_FILES else "")
           for c, p in changed]
    flags = []
    tracked_and_new = set(_git_ls_files()) | {p for _, p in changed}
    for path, prompt in LATER_FILES.items():
        if prompt > step and (path in tracked_and_new or (ROOT / path).exists()):
            flags.append(f"{path} belongs to Prompt {prompt}")
    deps = [_dep_name(s) for s in _pyproject().get("project", {}).get("dependencies", [])]
    for group in _pyproject().get("project", {}).get("optional-dependencies", {}).values():
        deps += [_dep_name(s) for s in group]
    for dep, prompt in LATER_DEPS.items():
        if prompt > step and dep in deps:
            flags.append(f"dependency {dep} belongs to Prompt {prompt}")
    ev += [f"SCOPE FLAG: {f}" for f in flags] or [f"no files or dependencies from a prompt later than {step}"]
    return Result("A6", "FAIL" if flags else "PASS", ev)


def _csv_fingerprints() -> dict[str, tuple[str, int, int]]:
    import hashlib
    out = {}
    for p in sorted((TESTS / "fixtures").rglob("*.csv")):
        st = p.stat()
        out[_rel(p)] = (hashlib.sha256(p.read_bytes()).hexdigest(), st.st_size, st.st_mtime_ns)
    return out


def check_a7(step: int, state: dict) -> Result | None:
    if step < 2:
        return None
    before_tests = state.get("csv_before_tests", {})
    after_tests = _csv_fingerprints()
    ev = [f"fixture CSVs: {list(after_tests) or 'none'}"]
    ok = bool(after_tests) and before_tests == after_tests
    ev.append(f"sha256+size+mtime identical before and after the full pytest run (A1): {before_tests == after_tests}")
    # Run the real CLI against the fixture file itself (not a copy), from a throw-away project root.
    sample = TESTS / "fixtures" / "sample_sites.csv"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "templates").mkdir()
        shutil.copyfile(ROOT / "templates" / "consent_request_v1.txt", root / "templates" / "consent_request_v1.txt")
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("OUTREACH_", "SENDER_")) and k not in ("OFFSITE_BACKUP_DIR", "ALLOW_LIVE")}
        env.update(PYTHONPATH=str(SRC), PYTHONIOENCODING="utf-8")
        before = _csv_fingerprints()
        codes = []
        for args in (["ingest", str(sample)], ["ingest", str(sample)], ["status"]):
            proc = subprocess.run([sys.executable, "-m", "outreach", *args], cwd=root, env=env, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=120)
            codes.append(proc.returncode)
        after = _csv_fingerprints()
    ev.append(f"CLI ingest x2 + status on {_rel(sample)} from a temp project: exit codes {codes}; "
              f"CSV unchanged: {before == after}")
    ok = ok and before == after and codes == [0, 0, 0]
    return Result("A7", "PASS" if ok else "FAIL", ev)


def check_a8(step: int, state: dict) -> Result | None:
    if step < 2:
        return None
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-m", "outreach", "--help"], cwd=ROOT, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)
    found = re.findall(r"^\s{4}([a-z][a-z-]*)\s{2,}\S", proc.stdout, re.M)
    expected = EXPECTED_COMMANDS.get(step, EXPECTED_COMMANDS[max(k for k in EXPECTED_COMMANDS if k <= step)])
    ok = proc.returncode == 0 and sorted(found) == sorted(expected)
    ev = [f"`python -m outreach --help` exit code {proc.returncode}",
          f"commands listed: {found}",
          f"expected after Prompt {step}: {expected}"]
    extra = sorted(set(found) - set(expected))
    if extra:
        ev.append(f"commands from a later prompt: {extra}")
    return Result("A8", "PASS" if ok else "FAIL", ev)


ALWAYS: list[Callable[[int, dict], Result | None]] = [check_a1, check_a2, check_a3, check_a4, check_a5, check_a6,
                                                      check_a7, check_a8]


# --- After Prompt 0 -------------------------------------------------------

def p0_dirs(step: int, state: dict) -> Result:
    need = ["src/outreach", "tests", "tests/fixtures", "templates", "data", "docs"]
    missing = [d for d in need if not (ROOT / d).is_dir()]
    gitkeep = (ROOT / "data" / ".gitkeep").is_file()
    tracked_or_new = "data/.gitkeep" in _git_ls_files() or \
        "data/.gitkeep" in _run(["git", "status", "--porcelain", "-uall"]).stdout
    ev = [f"{d}/: {'exists' if d not in missing else 'MISSING'}" for d in need]
    ev.append(f"data/.gitkeep: {'exists' if gitkeep else 'MISSING'}, visible to git: {tracked_or_new}")
    return Result("P0.1", "PASS" if not missing and gitkeep and tracked_or_new else "FAIL", ev)


def p0_gitignore(step: int, state: dict) -> Result:
    entries = {_norm_ignore(l) for l in (ROOT / ".gitignore").read_text(encoding="utf-8-sig").splitlines()
               if l.strip() and not l.lstrip().startswith("#")}
    missing = [e for e in REQUIRED_GITIGNORE if _norm_ignore(e) not in entries]
    keep_rule = "!data/.gitkeep" in entries
    ev = [f"required entries present: {len(REQUIRED_GITIGNORE) - len(missing)}/{len(REQUIRED_GITIGNORE)}"]
    ev += [f"missing: {m}" for m in missing]
    ev.append(f"'!data/.gitkeep' rule present: {keep_rule}")
    extra = sorted(entries - {_norm_ignore(e) for e in REQUIRED_GITIGNORE} - {"!data/.gitkeep"})
    if extra:
        ev.append(f"additional entries (beyond Prompt 0): {extra}")
    return Result("P0.2", "PASS" if not missing and keep_rule else "FAIL", ev)


def p0_pyproject(step: int, state: dict) -> Result:
    data = _pyproject()
    proj = data["project"]
    req = proj.get("requires-python", "")
    runtime = sorted(_dep_name(d) for d in proj.get("dependencies", []))
    opt = {k: sorted(_dep_name(d) for d in v) for k, v in proj.get("optional-dependencies", {}).items()}
    groups = data.get("dependency-groups", {})
    ok = (
        req.replace(" ", "") == ">=3.11"
        and runtime == sorted(["httpx", "beautifulsoup4", "lxml", "tldextract"])
        and opt == {"dev": ["pytest"]}
        and not groups
    )
    ev = [f"requires-python = {req!r}",
          f"runtime dependencies = {runtime}",
          f"optional-dependencies = {opt}",
          f"dependency-groups = {groups or 'none'}",
          f"build-system.requires = {data.get('build-system', {}).get('requires')} (build backend, not a runtime dep)"]
    return Result("P0.3", "PASS" if ok else "FAIL", ev)


def p0_claude_md(step: int, state: dict) -> Result:
    actual = _norm_text((ROOT / "CLAUDE.md").read_text(encoding="utf-8-sig"))
    expected = _norm_text(_expected_claude_md())
    same = actual == expected
    ev = [f"CLAUDE.md: {len(actual)} lines; Prompt 0 text: {len(expected)} lines",
          "exact line-by-line match (trailing whitespace ignored): " + str(same)]
    if not same:
        for i, (a, e) in enumerate(zip(actual, expected), 1):
            if a != e:
                ev.append(f"first difference at line {i}: {a[:60]!r} vs {e[:60]!r}")
                break
    return Result("P0.4", "PASS" if same else "FAIL", ev)


def p0_scaffold_only(step: int, state: dict) -> Result:
    files = sorted(_rel(p) for p in SRC.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and ".egg-info" not in p.as_posix())
    functional = []
    for p in _py_files(SRC):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8-sig"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                functional.append(f"{_rel(p)}:{node.lineno}: {type(node).__name__} {node.name}")
    readme = [l for l in (ROOT / "README.md").read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    stub = len(readme) == 2 and readme[0].startswith("# ")
    ev = [f"files in src/ (excluding build metadata): {files}"]
    ev += functional or ["no functions or classes in src/"]
    ev.append(f"README.md non-empty lines: {len(readme)} (title + one line expected) -> {readme}")
    ok = files == ["src/outreach/__init__.py"] and not functional and stub
    return Result("P0.5", "PASS" if ok else "FAIL", ev)


def p0_script(step: int, state: dict) -> Result:
    return Result("P0.6", "PASS", [f"{_rel(Path(__file__).resolve())} is running for step {step} "
                                   f"(stdlib only: see imports)"])


# --- helpers for running project code (always in a subprocess) -------------

def _run_project_code(code: str, cwd: Path = ROOT, src: Path = SRC, timeout: int = 120) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(src), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=cwd, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


def _function_source(path: Path, qualname: str) -> tuple[str, int, int] | None:
    """Return (source, first_line, last_line) of Class.method or function."""
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    parts = qualname.split(".")
    nodes = tree.body
    found = None
    for part in parts:
        found = next((n for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                      and n.name == part), None)
        if found is None:
            return None
        nodes = found.body
    seg = ast.get_source_segment(text, found)
    return seg, found.lineno, found.end_lineno


def _sql_strings(path: Path) -> list[tuple[int, str, str]]:
    """All string constants in a file as (line, enclosing function, text)."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    out: list[tuple[int, str, str]] = []

    def visit(node: ast.AST, func: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = func
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                out.append((child.lineno, func, child.value))
            elif isinstance(child, ast.JoinedStr):
                txt = "".join(v.value for v in child.values
                              if isinstance(v, ast.Constant) and isinstance(v.value, str))
                out.append((child.lineno, func, txt))
                continue
            visit(child, name)

    visit(tree, "<module>")
    return out


def _test_names(prefix: str, state: dict) -> dict[str, str]:
    return {k: v for k, v in state.get("junit", {}).items() if k.startswith(prefix)}


@dataclass
class Mutation:
    label: str
    file: str
    old: str
    new: str
    more: tuple[tuple[str, str], ...] = ()   # further (old, new) edits in the same file, applied in order
    tests: tuple[str, ...] = ()               # test files to run (in this order); empty = whole suite

    def edits(self) -> list[tuple[str, str]]:
        return [(self.old, self.new), *self.more]


def _run_mutation(m: Mutation) -> tuple[bool, list[str]]:
    """Apply one mutation in a temporary copy of the repo and run pytest there.

    Returns (caught, evidence). caught = at least one test failed.
    The temporary copy is deleted afterwards (evidence says so).
    """
    ev: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="outreach-mutation-"))
    copy = tmp / "repo"
    try:
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".pytest_cache", "*.egg-info", "data", "backups", "logs", "reports"))
        target = copy / m.file
        text = target.read_text(encoding="utf-8")
        for old, new in m.edits():
            count = text.count(old)
            if count != 1:
                return False, [f"{m.label}: mutation text found {count} times in {m.file} (expected 1); "
                               f"not applied: {old.strip()[:70]!r}"]
            text = text.replace(old, new)
        target.write_text(text, encoding="utf-8")
        which = _run_project_code("import outreach, sys; print(outreach.__file__)", cwd=copy, src=copy / "src")
        imported = which.stdout.strip()
        if not imported.startswith(str(copy)):
            return False, [f"{m.label}: copy imported the wrong package: {imported or which.stderr[-200:]}"]
        env = {k: v for k, v in os.environ.items() if k != "ALLOW_LIVE"}
        env["PYTHONPATH"] = str(copy / "src")
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *m.tests],
                              cwd=copy, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=900)
        failed = [l for l in proc.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))]
        summary = [l for l in proc.stdout.splitlines() if l.strip()][-1:] or ["(no output)"]
        caught = proc.returncode not in (0, 5) and bool(failed)
        for old, new in m.edits():
            ev.append(f"{m.label}: {m.file}: {old.strip()[:70]!r} -> {new.strip()[:70]!r}")
        ev.append(f"  package under test: {imported}")
        ev.append(f"  pytest -x {' '.join(m.tests) or '(whole suite)'}: {summary[0].strip()}")
        ev += [f"  {l[:150]}" for l in failed[:3]]
        return caught, ev
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        ev.append(f"  temporary copy {tmp} deleted: {not tmp.exists()}")


# --- After Prompt 1 -------------------------------------------------------

def p1_normalizer(step: int, state: dict) -> Result:
    tests = TESTS / "test_normalize.py"
    text = tests.read_text(encoding="utf-8-sig")
    junit = state.get("junit", {})
    valid = {k: v for k, v in junit.items() if "::test_normalize_valid[" in k}
    invalid = {k: v for k, v in junit.items() if "::test_normalize_invalid[" in k}
    table_ok = len(valid) + len(invalid) >= 30 and all(v == "passed" for v in {**valid, **invalid}.values())
    needles = {"Hebrew characters": bool(re.search("[֐-׿]", text)), "punycode (xn--)": "xn--" in text,
               ".co.il": ".co.il" in text, "facebook": "facebook.com" in text, "instagram": "instagram.com" in text,
               "linktr.ee": "linktr.ee" in text, "wixsite": "wixsite.com" in text, "blogspot": "blogspot.com" in text,
               "invalid input table": "INVALID" in text}
    # Independent behavioural spot-checks, run against the real code.
    probe = _run_project_code("""
        from outreach.normalize import normalize_url as n
        k = lambda u: n(u).site_key
        base = k("https://example.co.il")
        checks = {
          "www. does not change key": k("https://www.example.co.il") == base,
          "trailing dot does not change key": k("https://example.co.il.") == base,
          "port does not change key": k("https://example.co.il:8443") == base,
          "tracking params do not change key": k("https://example.co.il/?utm_source=x&fbclid=y&gclid=z") == base,
          "fragment does not change key": k("https://example.co.il/#contact") == base,
          "www/bare/shop share one key": len({k("www.example.co.il"), k("example.co.il"), k("shop.example.co.il")}) == 1,
          "two facebook pages differ": k("https://facebook.com/biz-a") != k("https://facebook.com/biz-b"),
          "Hebrew IDN == punycode": k("https://דוגמה.co.il") == k("https://xn--6dbbec0c.co.il"),
        }
        for name, ok in checks.items():
            print(("OK  " if ok else "BAD ") + name)
        """)
    lines = probe.stdout.splitlines()
    probe_ok = probe.returncode == 0 and lines and all(l.startswith("OK") for l in lines)
    ev = [f"table-driven cases: {len(valid)} valid + {len(invalid)} invalid = {len(valid) + len(invalid)} "
          f"(all passed: {all(v == 'passed' for v in {**valid, **invalid}.values())})"]
    ev += [f"covers {k}: {v}" for k, v in needles.items()]
    ev += [f"probe: {l}" for l in lines] or [f"probe failed: {probe.stderr[-300:]}"]
    ok = table_ok and all(needles.values()) and probe_ok
    return Result("P1.1", "PASS" if ok else "FAIL", ev)


def p1_tldextract_offline(step: int, state: dict) -> Result:
    hits = []
    for p in _py_files(SRC):
        for i, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
            if "TLDExtract(" in line or "tldextract.extract(" in line:
                hits.append((f"{_rel(p)}:{i}", line.strip()))
    ok = bool(hits) and all("suffix_list_urls=()" in l for _, l in hits)
    ev = [f"{loc}: {line}" for loc, line in hits] or ["no TLDExtract construction found"]
    guard = _test_names("tests/test_normalize.py::test_normalizer_works_with_network_disabled_from_import", state)
    ev.append(f"no-network subprocess test: {guard or 'not found'}")
    ok = ok and bool(guard) and all(v == "passed" for v in guard.values())
    return Result("P1.2", "PASS" if ok else "FAIL", ev)


def p1_pragmas(step: int, state: dict) -> Result:
    with tempfile.TemporaryDirectory() as td:
        proc = _run_project_code(f"""
            from outreach.ledger import Ledger
            with Ledger({str(Path(td) / 'probe.db')!r}) as led:
                print(led.pragma("journal_mode"), led.pragma("synchronous"),
                      led.pragma("foreign_keys"), led.pragma("busy_timeout"))
            """)
    vals = proc.stdout.split()
    ok = proc.returncode == 0 and vals[:2] == ["wal", "2"]
    ev = [f"opened a fresh Ledger: journal_mode={vals[0] if vals else '?'} synchronous={vals[1] if len(vals) > 1 else '?'} "
          f"foreign_keys={vals[2] if len(vals) > 2 else '?'} busy_timeout={vals[3] if len(vals) > 3 else '?'}"
          if vals else f"probe failed: {proc.stderr[-300:]}"]
    t = _test_names("tests/test_ledger.py::test_pragmas_wal_full_fk_busy", state)
    ev.append(f"test: {t or 'not found'}")
    return Result("P1.3", "PASS" if ok and t and all(v == 'passed' for v in t.values()) else "FAIL", ev)


def p1_claim_code(step: int, state: dict) -> Result:
    path = SRC / "outreach" / "ledger.py"
    found = _function_source(path, "Ledger.claim")
    if not found:
        return Result("P1.4", "FAIL", ["Ledger.claim not found"])
    src, first, last = found
    lines = src.splitlines()
    inserts = len(re.findall(r"\bINSERT\b", src))
    do_nothing = "ON CONFLICT DO NOTHING" in src
    other_writes = re.findall(r"\b(UPDATE|DELETE|REPLACE|DO UPDATE)\b", src)
    begin = next((i for i, l in enumerate(lines) if '"BEGIN IMMEDIATE"' in l), None)
    commit = next((i for i, l in enumerate(lines) if '"COMMIT"' in l), None)
    ret = next((i for i, l in enumerate(lines) if l.strip().startswith("return created")), None)
    rowcount = any("rowcount == 1" in l for l in lines)
    ok = (inserts == 1 and do_nothing and not other_writes and begin is not None and commit is not None
          and ret is not None and begin < commit < ret and rowcount)
    ev = [f"{_rel(path)}:{first}-{last} Ledger.claim",
          f"INSERT statements: {inserts}; 'ON CONFLICT DO NOTHING': {do_nothing}; other writes: {other_writes or 'none'}",
          f"BEGIN IMMEDIATE at line {first + begin if begin is not None else '?'}, "
          f"COMMIT at line {first + commit if commit is not None else '?'}, "
          f"'return created' at line {first + ret if ret is not None else '?'} (commit before return: "
          f"{commit is not None and ret is not None and commit < ret})",
          f"result is 'rowcount == 1' (True only when this call inserted): {rowcount}"]
    return Result("P1.4", "PASS" if ok else "FAIL", ev)


_WRITE_STMT = re.compile(
    r"\b(UPDATE\s+(\w+)\s+SET|DELETE\s+FROM\s+(\w+)|REPLACE\s+INTO\s+(\w+)|INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)"
    r"|DO\s+UPDATE|DROP\s+(?:TABLE|TRIGGER|INDEX)\b[^;]*)", re.I)
_TRIGGER = re.compile(r"CREATE\s+TRIGGER\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+BEFORE\s+(UPDATE|DELETE)\s+ON\s+(\w+)"
                      r"(.*?)\bEND\b", re.I | re.S)


def p1_update_delete_scan(step: int, state: dict) -> Result:
    """Every SQL statement in src/ that can modify or remove an existing row."""
    ev, bad = [], []
    for p in _py_files(SRC):
        for line, func, text in _sql_strings(p):
            flat = " ".join(text.split())
            for t in _TRIGGER.finditer(flat):
                body_writes = _WRITE_STMT.findall(t.group(4))
                verdict = ("protective trigger: body only RAISEs" if "RAISE(ABORT" in t.group(4) and not body_writes
                           else "TRIGGER WITH WRITES")
                if body_writes:
                    bad.append(f"{_rel(p)}:{line}")
                ev.append(f"{_rel(p)}:{line}: trigger {t.group(1)} BEFORE {t.group(2).upper()} ON {t.group(3)} -> {verdict}")
            for m in _WRITE_STMT.finditer(_TRIGGER.sub(" ", flat)):
                stmt = " ".join(m.group(0).split()[:3]).upper()
                table = next((g for g in m.groups()[1:] if g), "?")
                fin = re.fullmatch(r"\s*UPDATE sites SET (.*) WHERE site_key = \? AND status = 'pending'\s*", flat)
                reo = re.fullmatch(r"\s*DELETE FROM sites WHERE site_key = \? AND status IN \('no_form', 'captcha', "
                                   r"'login_required', 'robots_blocked', 'unclear_fields'\)\s*", flat)
                if stmt.startswith("UPDATE") and table == "sites" and func == "finish" \
                        and fin and "pending" not in fin.group(1):
                    verdict = "allowed: finish() moves a pending row to a final status"
                elif stmt.startswith("DELETE") and table == "sites" and func == "reopen" and reo:
                    verdict = ("allowed (Prompt 5 reopen): removes only no_form/captcha/login_required/"
                               "robots_blocked/unclear_fields rows, where no POST happened")
                elif table not in ("sites", "?"):
                    verdict = f"writes table {table} (not sites)"
                else:
                    verdict = "NOT ALLOWED (modifies or removes site rows / schema)"
                    bad.append(f"{_rel(p)}:{line}")
                ev.append(f"{_rel(p)}:{line} in {func}(): {flat[:90]!r} -> {verdict}")
    ev = ev or ["no UPDATE/DELETE statements in src/"]
    return Result("P1.5", "FAIL" if bad else "PASS", ev)


P1_REQUIRED_TESTS = {
    "second claim returns False": "tests/test_ledger.py::test_second_claim_of_same_key_returns_false",
    "different URL spellings return False": "tests/test_ledger.py::test_claim_via_different_url_spellings_returns_false",
    "concurrent claim (threads)": "tests/test_ledger.py::test_concurrent_claims_threads_exactly_one_winner",
    "concurrent claim (processes)": "tests/test_ledger.py::test_concurrent_claims_processes_exactly_one_winner",
    "crash after claim stays pending, not re-offered":
        "tests/test_ledger.py::test_crash_after_claim_leaves_row_pending_and_not_offered_again",
    "suppression blocks a domain": "tests/test_ledger.py::test_suppressed_domain_is_blocked_for_any_spelling",
}


def p1_required_tests(step: int, state: dict) -> Result:
    junit = state.get("junit", {})
    ev, ok = [], True
    for label, name in P1_REQUIRED_TESTS.items():
        outcome = junit.get(name, "MISSING")
        ok &= outcome == "passed"
        ev.append(f"{label}: {name} -> {outcome}")
    text = (TESTS / "test_ledger.py").read_text(encoding="utf-8-sig")
    sizes = re.findall(r"workers, rounds = (\d+), (\d+)", text)
    ev.append(f"concurrency sizes (workers, rounds): {sizes}")
    ok &= len(sizes) >= 2 and all(int(w) >= 8 and int(r) >= 2 for w, r in sizes)
    return Result("P1.6", "PASS" if ok else "FAIL", ev)


P1_MUTATIONS = [
    Mutation("claim() always returns True", "src/outreach/ledger.py",
             "            created = cur.rowcount == 1\n",
             "            created = True\n", tests=("tests/test_ledger.py",)),
    Mutation("claim() without COMMIT", "src/outreach/ledger.py",
             "            created = cur.rowcount == 1\n            conn.execute(\"COMMIT\")\n",
             "            created = cur.rowcount == 1\n", tests=("tests/test_ledger.py",)),
]


def p1_mutations(step: int, state: dict) -> Result:
    ev, ok = [], True
    for m in P1_MUTATIONS:
        caught, mev = _run_mutation(m)
        ok &= caught
        ev += mev + [f"  -> {'CAUGHT (a test failed)' if caught else 'NOT CAUGHT'}"]
    return Result("P1.7", "PASS" if ok else "FAIL", ev)


# --- After Prompt 2 -------------------------------------------------------

def _required(state: dict, names: dict[str, str]) -> tuple[bool, list[str]]:
    """Check that each named test (exact id, or prefix ending in '[' for all params) passed."""
    junit = state.get("junit", {})
    ok, ev = True, []
    for label, name in names.items():
        if name.endswith(("[", "-")):  # prefix: all parametrized cases (pytest escapes non-ASCII ids)
            hits = {k: v for k, v in junit.items() if k.startswith(name)}
            good = bool(hits) and all(v == "passed" for v in hits.values())
            ev.append(f"{label}: {name}*] -> {len(hits)} case(s), all passed: {good}")
        else:
            good = junit.get(name) == "passed"
            ev.append(f"{label}: {name} -> {junit.get(name, 'MISSING')}")
        ok &= good
    return ok, ev


def _lines_matching(path: Path, pattern: str) -> list[str]:
    return [f"{_rel(path)}:{i}: {l.strip()}" for i, l in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1)
            if re.search(pattern, l)]


def p2_settings_documented(step: int, state: dict) -> Result:
    with tempfile.TemporaryDirectory() as td:
        proc = _run_project_code(f"""
            from outreach.config import SETTINGS, load_config
            c = load_config(root={td!r}, environ={{}}, use_dotenv=False)
            print("ADDRESS=" + c.sender_address)
            for s in SETTINGS: print("ENV=" + s.env)
            """)
    envs = re.findall(r"^ENV=(\S+)", proc.stdout, re.M)
    address = re.search(r"^ADDRESS=(.*)$", proc.stdout, re.M)
    readme = (ROOT / "README.md").read_text(encoding="utf-8-sig")
    missing = [e for e in envs if f"`{e}`" not in readme]
    ev = [f"settings in config.SETTINGS: {envs}",
          f"documented in README.md: {len(envs) - len(missing)}/{len(envs)}" + (f"; missing {missing}" if missing else ""),
          f"sender address default: {address.group(1) if address else '?'!r}"]
    ok = proc.returncode == 0 and envs and not missing and address and address.group(1) == "TODO"
    return Result("P2.1", "PASS" if ok else "FAIL", ev)


def p2_backup(step: int, state: dict) -> Result:
    bk = SRC / "outreach" / "backup.py"
    api = _lines_matching(bk, r"\.backup\(")
    raw = []
    for p in _py_files(SRC):  # file-copy primitives anywhere in src/
        raw += _lines_matching(p, r"\bshutil\b|copyfile|copy2|copytree|os\.link\(")
    # raw byte reads/writes in the module that handles database files
    raw += _lines_matching(bk, r"\.read_bytes\(|\.write_bytes\(|\bopen\(")
    ok, ev = _required(state, {
        "backup opens + integrity ok": "tests/test_backup.py::test_backup_is_valid_openable_database",
        "WAL content included": "tests/test_backup.py::test_backup_includes_uncheckpointed_wal_content",
        "newest 30 kept": "tests/test_backup.py::test_backup_keeps_only_newest_30",
        "offsite copy works": "tests/test_backup.py::test_offsite_copy_is_written_and_valid",
        "offsite missing folder raises": "tests/test_backup.py::test_offsite_missing_folder_fails_loudly",
        "offsite copy error raises": "tests/test_backup.py::test_offsite_copy_error_fails_loudly",
        "only the backup API is used": "tests/test_backup.py::test_backup_uses_sqlite_backup_api",
    })
    ev = [f"backup API call: {a}" for a in api] + [f"raw file copy in src/: {raw or 'none'}"] + ev
    return Result("P2.2", "PASS" if ok and api and not raw else "FAIL", ev)


def p2_sendlog(step: int, state: dict) -> Result:
    sl = SRC / "outreach" / "sendlog.py"
    fsync = _lines_matching(sl, r"os\.fsync\(")
    flush = _lines_matching(sl, r"\.flush\(\)")
    opens = _lines_matching(sl, r"\bopen\(")
    append_only = opens and all(re.search(r"open\([^)]*[\"']a[\"']", o) for o in opens)
    ok, ev = _required(state, {
        "one JSON line per event": "tests/test_sendlog.py::test_append_writes_one_json_line_per_event",
        "each append flushed + fsynced": "tests/test_sendlog.py::test_each_append_is_flushed_and_fsynced",
        "never truncates": "tests/test_sendlog.py::test_append_only_never_truncates",
    })
    ev = fsync + flush + [f"open() calls: {opens}; all append mode: {bool(append_only)}"] + ev
    return Result("P2.3", "PASS" if ok and fsync and flush and append_only else "FAIL", ev)


def p2_preflight(step: int, state: dict) -> Result:
    pf = SRC / "outreach" / "preflight.py"
    order: list[str] = []
    for m in re.finditer(r'Check\("([a-z_]+)"', pf.read_text(encoding="utf-8-sig")):
        if m.group(1) not in order:
            order.append(m.group(1))
    expected = ["stop_file", "ledger_integrity", "ledger_missing", "template", "sender_details"]
    integrity = _lines_matching(pf, r"PRAGMA integrity_check")
    live_only = _lines_matching(pf, r"if live:")
    ok, ev = _required(state, {
        "order test": "tests/test_preflight.py::test_checks_run_in_required_order",
        "all failures in order": "tests/test_preflight.py::test_all_failures_reported_in_order",
        "REFUSES: ledger missing + backup": "tests/test_preflight.py::test_refuses_when_ledger_missing_but_backup_exists",
        "REFUSES: ledger missing + offsite backup":
            "tests/test_preflight.py::test_refuses_when_ledger_missing_but_offsite_backup_exists",
        "REFUSES: ledger missing + send log": "tests/test_preflight.py::test_refuses_when_ledger_missing_but_send_log_exists",
        "integrity: not SQLite": "tests/test_preflight.py::test_corrupt_ledger_fails_integrity",
        "integrity: damaged pages": "tests/test_preflight.py::test_damaged_ledger_pages_fail_integrity",
        "TODO rejected in live mode only": "tests/test_preflight.py::test_todo_sender_rejected_in_live_mode_only",
        "CLI ingest refused when ledger missing": "tests/test_cli.py::test_ingest_refused_when_ledger_missing_but_backup_exists",
    })
    ev = [f"check order in {_rel(pf)}: {order}", f"expected: {expected}"] + integrity + live_only + ev
    return Result("P2.4", "PASS" if ok and order == expected and integrity and live_only else "FAIL", ev)


def p2_breaker(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "N-1 not tripped, N tripped": "tests/test_breaker.py::test_trips_exactly_at_threshold[",
        "success resets": "tests/test_breaker.py::test_success_resets_the_consecutive_count",
    })
    txt = (TESTS / "test_breaker.py").read_text(encoding="utf-8-sig")
    asserts_n_minus_1 = "range(n - 1)" in txt and "n - 1" in txt
    ev.append(f"test asserts the N-1 state explicitly: {asserts_n_minus_1}")
    return Result("P2.5", "PASS" if ok and asserts_n_minus_1 else "FAIL", ev)


def p2_template(step: int, state: dict) -> Result:
    doc = BUILD_PROMPTS.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    marker = "filled from config at send time:\n\n"
    start = doc.index(marker) + len(marker)
    expected = doc[start:doc.index("\n\n   Add a short note", start)]
    path = ROOT / "templates" / "consent_request_v1.txt"
    raw = path.read_bytes() if path.exists() else b""
    actual = raw.decode("utf-8", "replace")
    same = actual == expected
    diff = next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), None)
    note_files = [p for p in (ROOT / "docs").glob("*.md") if p.name not in ("build-prompts.md", "validation.md")
                  and "pending legal review" in p.read_text(encoding="utf-8-sig").lower()]
    has_bom, cr_bytes = raw.startswith(b"\xef\xbb\xbf"), raw.count(b"\r")
    ev = [f"{_rel(path)}: {len(actual)} chars, {len(actual.splitlines())} lines; Prompt 2 text: {len(expected)} chars",
          f"character-for-character identical: {same}" + ("" if same else f" (first difference at char {diff})"),
          f"BOM: {has_bom}; CR bytes: {cr_bytes}",
          f"docs note saying 'pending legal review': {[_rel(p) for p in note_files] or 'none'}"]
    return Result("P2.6", "PASS" if same and note_files else "FAIL", ev)


def p2_ingest(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "drops invalid/dupes/handled/suppressed, batches planned": "tests/test_ingest.py::test_ingest_sample_counts_and_batches",
        "never claims": "tests/test_ingest.py::test_ingest_never_claims_anything",
        "CSV byte-identical": "tests/test_ingest.py::test_ingest_leaves_csv_byte_identical",
        "CSV opened 'rb' only": "tests/test_ingest.py::test_read_csv_opens_read_only",
        "second ingest plans nothing new": "tests/test_ingest.py::test_second_ingest_plans_nothing_new",
        "ambiguous column -> error listing columns": "tests/test_ingest.py::test_ambiguous_column_lists_columns",
        "CLI ingest + status": "tests/test_cli.py::test_ingest_then_status",
        "CLI suppress add": "tests/test_cli.py::test_suppress_add_then_ingest_skips_it",
        "CLI backup": "tests/test_cli.py::test_backup_command",
    })
    opens = _lines_matching(SRC / "outreach" / "ingest.py", r"\bopen\(")
    ev.append(f"open() calls in src/outreach/ingest.py (the CSV reader): {opens}")
    ok &= bool(opens) and all(re.search(r"open\([^)]*\"rb\"", o) for o in opens)
    return Result("P2.7", "PASS" if ok else "FAIL", ev)


def p2_no_fetch(step: int, state: dict) -> Result:
    hits = []
    pat = (r"^\s*(import|from)\s+(httpx|requests|urllib\.request|urllib3|http\.client|socket|aiohttp|bs4|lxml|"
           r"playwright|selenium)\b|\.post\(|\"POST\"|'POST'|<form|robotparser|robots\.txt")
    for p in _py_files(SRC):
        hits += _lines_matching(p, pat)
    ev = hits or ["no network client, HTML parser, form or robots code in src/"]
    return Result("P2.8", "FAIL" if hits else "PASS", ev)


# --- After Prompt 3 -------------------------------------------------------

# Case-sensitive where the protocol is ("POST"); case-insensitive only inside client calls.
_POST_SEND = re.compile(
    r"\.post\(|[\"']POST[\"']|(?i:\bmethod\s*=\s*[\"']post[\"'])|(?i:\.request\(\s*[\"']post)"
    r"|(?i:\.stream\(\s*[\"']post)|\.send\(|urlopen\(|\bhttp\.client\b"
    r"|\brequests\.(get|post|put|request|Session)\b|^\s*import requests\b")


def p3_no_post(step: int, state: dict) -> Result:
    sends, mentions = [], []
    for p in _py_files(SRC):
        for i, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
            loc = f"{_rel(p)}:{i}: {line.strip()[:110]}"
            if _POST_SEND.search(line):
                sends.append(loc)
            elif re.search(r"post", line, re.I):
                mentions.append(loc)
    client_calls = []
    for p in _py_files(SRC):
        client_calls += _lines_matching(p, r"_client\.\w+\(")
    get_only = client_calls and all(re.search(r"_client\.stream\(\"GET\"|_client\.close\(\)", c) for c in client_calls)
    ev = [f"request-sending patterns (.post(, \"POST\", method=post, .request/.stream(\"POST\"), .send(, urlopen, "
          f"http.client, requests.): {sends or 'none'}",
          f"HTTP client calls in src/: {client_calls}; GET only: {bool(get_only)}"]
    ev += [f"other 'post' text (not a request, listed for review): {m}" for m in mentions]
    return Result("P3.1", "PASS" if not sends and get_only else "FAIL", ev)


_BROWSER_PKGS = {"playwright", "selenium", "pyppeteer", "splinter", "undetected-chromedriver", "seleniumbase",
                 "requests-html", "mechanize", "mechanicalsoup", "helium"}


def p3_no_browser(step: int, state: dict) -> Result:
    data = _pyproject()
    specs = list(data.get("project", {}).get("dependencies", []))
    for g in data.get("project", {}).get("optional-dependencies", {}).values():
        specs += g
    declared = sorted(_dep_name(s) for s in specs)
    installed = sorted({(d.metadata["Name"] or "").lower() for d in importlib.metadata.distributions()})
    bad = sorted((set(declared) | set(installed)) & _BROWSER_PKGS)
    imports = []
    for p in _py_files(SRC):
        imports += _lines_matching(p, r"^\s*(import|from)\s+(playwright|selenium|pyppeteer|splinter)\b")
    ev = [f"declared dependencies: {declared}", f"browser-automation packages declared or installed: {bad or 'none'}",
          f"browser imports in src/: {imports or 'none'}"]
    return Result("P3.2", "PASS" if not bad and not imports else "FAIL", ev)


def p3_fetcher(step: int, state: dict) -> Result:
    fp = SRC / "outreach" / "fetch.py"
    ua = _lines_matching(fp, r'^USER_AGENT = "PosibloOutreachBot/1\.0 \(\+https://posiblo\.com; posiblo\.contact@gmail\.com\)"$')
    consts = _lines_matching(fp, r"^(TIMEOUT_SECONDS|MAX_BODY_BYTES|MAX_REDIRECTS) = ")
    retry = _lines_matching(fp, r"retr(y|ies)\s*=|tenacity|backoff|for attempt|while True")
    retry = [r for r in retry if "No automatic retries" not in r]
    deps_retry = [l for l in (ROOT / "pyproject.toml").read_text(encoding="utf-8-sig").splitlines()
                  if re.search(r"tenacity|backoff|retrying|urllib3", l)]
    ok, ev = _required(state, {
        "UA sent, GET only": "tests/test_fetch.py::test_sends_honest_user_agent_and_only_get",
        "robots-disallowed page NOT requested": "tests/test_fetch.py::test_robots_disallowed_page_is_never_requested",
        "robots cached per host": "tests/test_fetch.py::test_robots_fetched_once_per_host",
        "robots status handling": "tests/test_fetch.py::test_robots_status_handling[",
        "per-host delay applied": "tests/test_fetch.py::test_per_host_delay_is_applied",
        "delay is per host": "tests/test_fetch.py::test_delay_is_per_host",
        "15 s timeout + no retry": "tests/test_fetch.py::test_timeout_and_no_retry",
        "2 MB cap (Content-Length)": "tests/test_fetch.py::test_body_cap_with_content_length",
        "2 MB cap (streamed)": "tests/test_fetch.py::test_body_cap_when_streamed_without_length",
        "3 redirects followed": "tests/test_fetch.py::test_up_to_three_redirects_followed",
        "4th redirect refused": "tests/test_fetch.py::test_fourth_redirect_is_refused",
        "cross-domain redirect refused": "tests/test_fetch.py::test_redirect_to_other_domain_is_refused",
        "5xx not retried": "tests/test_fetch.py::test_server_error_is_not_retried",
        "Hebrew decoding": "tests/test_fetch.py::test_hebrew_decoding[",
        "constants match prompt": "tests/test_fetch.py::test_constants_match_the_prompt",
    })
    ev = (ua or ["USER_AGENT line NOT exact"]) + consts + \
         [f"retry logic in fetch.py: {retry or 'none'}", f"retry libraries in pyproject: {deps_retry or 'none'}"] + ev
    return Result("P3.3", "PASS" if ok and ua and len(consts) == 3 and not retry and not deps_retry else "FAIL", ev)


P3_FIXTURE_CASES = {
    "Contact Form 7 in Hebrew": "cf7_hebrew.html",
    "Elementor form": "elementor.html",
    "plain English form": "plain_english.html",
    "form with reCAPTCHA": "recaptcha.html",
    "login page": "login.html",
    "newsletter-only page": "newsletter.html",
    "page with no form": "no_form.html",
    "JS-only page, no static form": "js_only.html",
    "form with a honeypot": "honeypot.html",
    "form with an unknown required field": "unknown_required.html",
    "no-solicitation notice": "no_solicitation.html",
    "cross-domain action": "cross_domain.html",
}


def p3_fixtures(step: int, state: dict) -> Result:
    present = sorted(p.name for p in (TESTS / "fixtures").glob("*.html"))
    missing = [f"{case} ({name})" for case, name in P3_FIXTURE_CASES.items() if name not in present]
    ev = [f"{len(present)} HTML fixtures: {present}"]
    ev += [f"{case}: {name} {'present' if name in present else 'MISSING'}" for case, name in P3_FIXTURE_CASES.items()]
    return Result("P3.4", "PASS" if not missing and len(present) >= 12 else "FAIL", ev)


def p3_finder_classifier(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "captcha": "tests/test_finder.py::test_contact_page_outcomes[recaptcha.html-captcha-recaptcha]",
        "login_required": "tests/test_finder.py::test_contact_page_outcomes[login.html-login_required-log]",
        "login_required via redirect": "tests/test_finder.py::test_redirect_to_login_is_login_required",
        "no_form": "tests/test_finder.py::test_contact_page_outcomes[no_form.html-no_form-no usable contact form]",
        "no_form (JS-only)": "tests/test_finder.py::test_contact_page_outcomes[js_only.html-no_form-JavaScript]",
        "no_solicitation": "tests/test_finder.py::test_contact_page_outcomes[no_solicitation.html-no_solicitation-",
        "no_solicitation on homepage": "tests/test_finder.py::test_no_solicitation_on_homepage_stops_immediately",
        "newsletter-only excluded": "tests/test_finder.py::test_contact_page_outcomes[newsletter.html-no_form-newsletter]",
        "search form excluded": "tests/test_classify.py::test_plain_english_form_and_search_form_excluded",
        "form kinds (search/login/newsletter)": "tests/test_finder.py::test_form_kinds[",
        "honeypot left empty": "tests/test_classify.py::test_honeypot_fields_left_empty_and_hidden_tokens_kept",
        "unknown REQUIRED -> unclear_fields": "tests/test_classify.py::test_unknown_required_field_gives_unclear_fields",
        "cross-domain action -> unclear_fields": "tests/test_classify.py::test_cross_domain_action_gives_unclear_fields",
        "hidden tokens kept (CF7)": "tests/test_classify.py::test_contact_form_7_hebrew",
        "Elementor": "tests/test_classify.py::test_elementor_form",
        "robots_blocked contact page": "tests/test_finder.py::test_robots_blocked_contact_page",
        "end-to-end on local server": "tests/test_fetch.py::test_finder_against_live_local_server",
    })
    return Result("P3.5", "PASS" if ok else "FAIL", ev)


def p3_extra_fetches(step: int, state: dict) -> Result:
    const = _lines_matching(SRC / "outreach" / "finder.py", r"^MAX_EXTRA_FETCHES = 3$")
    ok, ev = _required(state, {
        "fake fetcher: homepage + 3": "tests/test_finder.py::test_at_most_three_extra_fetches",
        "local server: homepage + 3": "tests/test_fetch.py::test_finder_extra_fetch_limit_on_live_server",
    })
    return Result("P3.6", "PASS" if ok and const else "FAIL", (const or ["MAX_EXTRA_FETCHES != 3"]) + ev)


# --- After Prompt 4 -------------------------------------------------------

def _calls_in(path: Path) -> list[tuple[int, str]]:
    """(line, attribute-or-function name) for every call in a module."""
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            out.append((node.lineno, name))
    return out


def p4_dry_run_no_claim(step: int, state: dict) -> Result:
    offenders = []
    for mod in ("dryrun.py", "approve.py", "export.py"):
        p = SRC / "outreach" / mod
        offenders += [f"{_rel(p)}:{ln}: {name}()" for ln, name in _calls_in(p) if name in ("claim", "finish")]
    ok, ev = _required(state, {
        "sites table stays empty, claim()/finish() never called":
            "tests/test_dryrun.py::test_dry_run_leaves_sites_table_empty_and_never_claims",
        "CLI dry-run on local server: GET only, sites table empty":
            "tests/test_dryrun.py::test_cli_dry_run_against_local_server",
        "approve does not touch sites": "tests/test_approve.py::test_approve_does_not_touch_sites_table",
    })
    ev.insert(0, f"claim()/finish() calls in dryrun.py, approve.py, export.py: {offenders or 'none'}")
    return Result("P4.1", "PASS" if ok and not offenders else "FAIL", ev)


def p4_dry_run_results(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "results written + state dry_run_done": "tests/test_dryrun.py::test_dry_run_records_outcomes_and_sets_state",
        "re-run replaces results": "tests/test_dryrun.py::test_rerun_replaces_previous_results",
        "STOP file halts (stays planned)": "tests/test_dryrun.py::test_stop_file_halts_and_batch_cannot_be_approved",
        "circuit breaker halts": "tests/test_dryrun.py::test_circuit_breaker_halts_after_consecutive_fetch_errors",
        "suppressed/handled not fetched": "tests/test_dryrun.py::test_suppressed_and_handled_sites_are_not_fetched",
    })
    delete = _lines_matching(SRC / "outreach" / "ledger.py", r"DELETE FROM dry_run_results")
    ev.append(f"replacement is done by: {delete}")
    return Result("P4.2", "PASS" if ok and delete else "FAIL", ev)


def p4_report_message(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "report has one line per site + the exact message":
            "tests/test_dryrun.py::test_report_shows_each_site_and_exact_message",
        "message uses the configured address": "tests/test_dryrun.py::test_message_uses_configured_address",
    })
    return Result("P4.3", "PASS" if ok else "FAIL", ev)


def p4_approve(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "refuses before dry-run": "tests/test_approve.py::test_approve_refuses_before_dry_run",
        "refuses after a halted dry-run": "tests/test_approve.py::test_approve_refuses_after_halted_dry_run",
        "requires typing the batch id": "tests/test_approve.py::test_approve_requires_typing_the_batch_id[",
        "approved list = ready sites only": "tests/test_approve.py::test_approved_list_contains_only_ready_sites",
        "approved list frozen (triggers)": "tests/test_approve.py::test_approved_list_is_frozen",
        "approve twice refused": "tests/test_approve.py::test_approve_twice_is_refused",
        "dry-run refused after approval": "tests/test_dryrun.py::test_dry_run_refused_after_approval",
        "CLI reads typed confirmation": "tests/test_approve.py::test_cli_approve_reads_typed_confirmation",
    })
    gate = _lines_matching(SRC / "outreach" / "ledger.py", r"if row\[0\] != \"dry_run_done\"")
    only_ready = _lines_matching(SRC / "outreach" / "ledger.py", r"d\.outcome = 'ready'")
    ev = gate + only_ready + ev
    return Result("P4.4", "PASS" if ok and gate and only_ready else "FAIL", ev)


def p4_export(step: int, state: dict) -> Result:
    ex = SRC / "outreach" / "export.py"
    opens = _lines_matching(ex, r"\bopen\(")
    x_only = bool(opens) and all(re.search(r"open\([^)]*\"x\"", o) for o in opens)
    ok, ev = _required(state, {
        "writes a new report under reports/": "tests/test_export.py::test_export_writes_a_new_report",
        "never overwrites": "tests/test_export.py::test_export_never_overwrites",
        "input CSV untouched": "tests/test_export.py::test_cli_ingest_dry_run_export_never_touches_input_csv",
    })
    reads_csv = _lines_matching(ex, r"read_csv|ingest")
    ev = [f"open() calls in export.py: {opens}; exclusive-create mode 'x' only: {x_only}",
          f"export.py reads the input CSV: {reads_csv or 'no'}"] + ev
    return Result("P4.5", "PASS" if ok and x_only and not reads_csv else "FAIL", ev)


# --- After Prompt 5 -------------------------------------------------------

def _calls_with_func(path: Path) -> list[tuple[int, str, str, list[str]]]:
    """(line, callee name, enclosing function, enclosing loop kinds) for every call in a module."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    out: list[tuple[int, str, str, list[str]]] = []

    def visit(node: ast.AST, func: str, loops: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            f, lp = func, loops
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                f, lp = child.name, []
            elif isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                lp = loops + [type(child).__name__]
            if isinstance(child, ast.Call):
                fn = child.func
                name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
                out.append((child.lineno, name, func, loops))
            visit(child, f, lp)

    visit(tree, "<module>", [])
    return out


_SERVER_ROUTE = re.compile(r"^\s*@\w+\.(route\(.*methods\s*=\s*\[[^\]]*[\"']POST[\"']|post\()")


def p5_single_post(step: int, state: dict) -> Result:
    sends, routes = [], []
    for p in _py_files(SRC):
        for i, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
            if _SERVER_ROUTE.search(line):
                routes.append(f"{_rel(p)}:{i}: {line.strip()}")
            elif _POST_SEND.search(line):
                sends.append((p, i, line.strip()))
    ev = [f"request-sending lines in src/ (pattern of P3.1): {len(sends)}"]
    ev += [f"  {_rel(p)}:{i}: {l}" for p, i, l in sends]
    ev += [f"server route that RECEIVES a POST (not a request the tool makes): {r}" for r in routes]
    if any("dashboard.py" not in r for r in routes):
        return Result("P5.1", "FAIL", ev + ["a POST route outside dashboard.py"])
    send_py = SRC / "outreach" / "send.py"
    fn = _function_source(send_py, "_post_once")
    post_ok = (len(sends) == 1 and sends[0][0] == send_py and fn is not None and fn[1] <= sends[0][1] <= fn[2])
    ev.append(f"the POST is inside send.py:_post_once (lines {fn[1]}-{fn[2]}): {post_ok}" if fn else "_post_once missing")
    callers = [(f"{_rel(p)}:{ln}", func) for p in _py_files(SRC) for ln, name, func, _ in _calls_with_func(p)
               if name == "_post_once"]
    run_callers = [(f"{_rel(p)}:{ln}", func) for p in _py_files(SRC) for ln, name, func, _ in _calls_with_func(p)
                   if name == "run_send"]
    cli = (SRC / "outreach" / "cli.py").read_text(encoding="utf-8-sig")
    wired = re.search(r'add_parser\("send".*?\n\s*sp\.add_argument\("batch_id"\)\n\s*sp\.set_defaults\(func=cmd_send\)', cli)
    importers = [f"{_rel(p)}" for p in _py_files(SRC) if re.search(r"from \.send import|import outreach\.send|"
                                                                    r"from outreach\.send import",
                                                                    p.read_text(encoding="utf-8-sig"))]
    ev += [f"_post_once() called from: {callers}", f"run_send() called from: {run_callers}",
           f"`send` subcommand wired to cmd_send: {bool(wired)}", f"modules importing send.py: {importers}"]
    ok = (post_ok and [c[1] for c in callers] == ["_send_one"] and [c[1] for c in run_callers] == ["cmd_send"]
          and bool(wired) and importers == ["src/outreach/cli.py"])
    return Result("P5.1", "PASS" if ok else "FAIL", ev)


def _line_of(src: str, first: int, needle: str) -> int | None:
    for i, line in enumerate(src.splitlines()):
        if needle in line:
            return first + i
    return None


def p5_gates(step: int, state: dict) -> Result:
    send_py = SRC / "outreach" / "send.py"
    src, first, last = _function_source(send_py, "run_send")
    gates = [("ALLOW_LIVE (live_allowed)", "if not live_allowed(environ)"),
             ("preflight live=True (STOP, ledger, template, TODO)", "run_preflight(config, live=True)"),
             ("batch approved", "not in SENDABLE_BATCH_STATES"),
             ("frozen approved list", "ledger.approved_sites(batch_id)"),
             ("message renders", "render_message(config)"),
             ("fresh backup", "before = create_backup(config)")]
    network = [("Fetcher created", "Fetcher(delay_seconds"), ("POST client created", "httpx.Client(")]
    gl = [(label, _line_of(src, first, n)) for label, n in gates]
    nl = [(label, _line_of(src, first, n)) for label, n in network]
    ev = [f"{_rel(send_py)}:{first}-{last} run_send():"]
    ev += [f"  gate line {ln}: {label}" for label, ln in gl]
    ev += [f"  network line {ln}: {label}" for label, ln in nl]
    order_ok = all(ln for _, ln in gl + nl) and [ln for _, ln in gl] == sorted(ln for _, ln in gl) and \
        max(ln for _, ln in gl) < min(ln for _, ln in nl)
    gate_fn = _function_source(send_py, "live_allowed")
    ev.append(f"live_allowed(): {' '.join(gate_fn[0].split()) if gate_fn else 'missing'}")
    exact = bool(gate_fn) and 'return environ.get("ALLOW_LIVE") == "1"' in gate_fn[0]
    csrc, cfirst, _ = _function_source(SRC / "outreach" / "cli.py", "cmd_send")
    c_gate, c_cfg, c_led = (_line_of(csrc, cfirst, n) for n in ("if not live_allowed(os.environ)", "load_config()",
                                                                "Ledger(config.ledger_path)"))
    ev.append(f"cli.cmd_send(): ALLOW_LIVE gate line {c_gate} < load_config line {c_cfg} < Ledger line {c_led}")
    cli_ok = bool(c_gate and c_cfg and c_led and c_gate < c_cfg < c_led)
    ok, tev = _required(state, {
        "ALLOW_LIVE != '1' -> refused, no network, no backup":
            "tests/test_send.py::test_without_allow_live_nothing_happens[",
        "only exactly '1' enables": "tests/test_send.py::test_live_allowed_only_for_exactly_1",
        "CLI without ALLOW_LIVE: zero network, ledger not opened":
            "tests/test_send.py::test_cli_send_without_allow_live_makes_zero_network_calls",
        "unapproved batch refused": "tests/test_send.py::test_unapproved_batch_is_refused",
        "TODO sender refused": "tests/test_send.py::test_todo_sender_address_is_refused",
        "STOP refused before network": "tests/test_send.py::test_stop_file_refuses_before_any_network",
        "failed backup refused before network": "tests/test_send.py::test_failed_backup_refuses_before_any_network",
    })
    return Result("P5.2", "PASS" if ok and order_ok and exact and cli_ok else "FAIL", ev + tev)


def p5_order(step: int, state: dict) -> Result:
    send_py = SRC / "outreach" / "send.py"
    src, first, last = _function_source(send_py, "_Run._send_one")
    steps = [("re-fetch form page", "page = self.fetcher.get("), ("rebuild plan", "rebuilt = build_plan("),
             ("compare with approved plan", "diffs = plan_differences("), ("claim", "if not self.ledger.claim("),
             ("send-log 'claimed' (fsync)", "self.sendlog.append(EVENT_CLAIMED"),
             ("POST once", "outcome = _post_once("), ("verify", "status, detail = verify("),
             ("finish", "self.ledger.finish(key, status, detail)"),
             ("send-log 'result' (fsync)", "self.sendlog.append(EVENT_RESULT")]
    lines = [(label, _line_of(src, first, n)) for label, n in steps]
    ev = [f"{_rel(send_py)}:{first}-{last} _Run._send_one():"] + [f"  line {ln}: {label}" for label, ln in lines]
    nums = [ln for _, ln in lines]
    ascending = all(nums) and nums == sorted(nums) and len(set(nums)) == len(nums)
    ev.append(f"strictly in the required order: {ascending}")
    ev.append("claim() commits (BEGIN IMMEDIATE ... COMMIT) before it returns: see P1.4")
    ok, tev = _required(state, {
        "claim committed before POST (crash between them leaves pending, rerun sends nothing)":
            "tests/test_send.py::test_crash_between_claim_and_post_then_rerun_sends_nothing_more",
        "hard process crash between claim and POST": "tests/test_send.py::test_hard_process_crash_between_claim_and_post",
        "send log claimed/result per site": "tests/test_send.py::test_one_post_per_site_with_fresh_token_and_exact_message",
    })
    return Result("P5.3", "PASS" if ok and ascending else "FAIL", ev + tev)


def p5_no_retry(step: int, state: dict) -> Result:
    send_py = SRC / "outreach" / "send.py"
    calls = _calls_with_func(send_py)
    post_calls = [(ln, func, loops) for ln, name, func, loops in calls if name == "_post_once"]
    streams = [(ln, func, loops) for ln, name, func, loops in calls if name == "stream" and func == "_post_once"]
    retry_src = []
    for p in _py_files(SRC):
        retry_src += _lines_matching(p, r"\bretries\s*=|tenacity|backoff|retrying|Retry\(")
    retry_deps = [l.strip() for l in (ROOT / "pyproject.toml").read_text(encoding="utf-8-sig").splitlines()
                  if re.search(r"tenacity|backoff|retrying", l)]
    run_src = _function_source(send_py, "_Run.run")[0]
    ev = [f"_post_once() call sites: {post_calls} (loops inside the calling function: "
          f"{[l for _, _, l in post_calls]})",
          f"client.stream('POST') calls inside _post_once: {streams}",
          "the only loop around _send_one is `for i, site in enumerate(sites, 1)` in _Run.run: one pass per approved "
          f"site: {'for i, site in enumerate(sites, 1):' in run_src}",
          f"retry code in src/: {retry_src or 'none'}", f"retry libraries in pyproject: {retry_deps or 'none'}"]
    struct_ok = (len(post_calls) == 1 and post_calls[0][2] == [] and len(streams) == 1 and streams[0][2] == []
                 and not retry_src and not retry_deps)
    ok, tev = _required(state, {
        "HTTP error after POST -> sent_unconfirmed, 1 POST":
            "tests/test_send.py::test_http_error_after_post_is_sent_unconfirmed_without_retry",
        "timeout during POST -> sent_unconfirmed, 1 POST, rerun sends nothing":
            "tests/test_send.py::test_timeout_during_post_is_sent_unconfirmed_without_retry",
        "network error BEFORE claim -> unclaimed + event":
            "tests/test_send.py::test_network_error_before_claim_leaves_site_unclaimed_with_event",
        "static: one POST function, no retry wrapper": "tests/test_send.py::test_only_one_post_function_and_no_retry_wrapper",
    })
    return Result("P5.4", "PASS" if ok and struct_ok else "FAIL", ev + tev)


def p5_required_tests(step: int, state: dict) -> Result:
    ok, ev = _required(state, {
        "two runs -> exactly one POST per site": "tests/test_send.py::test_send_twice_gives_exactly_one_post_per_site",
        "crash between claim and POST, rerun -> 0 extra POSTs, row pending":
            "tests/test_send.py::test_crash_between_claim_and_post_then_rerun_sends_nothing_more",
        "ALLOW_LIVE unset -> zero connections": "tests/test_send.py::test_cli_send_without_allow_live_makes_zero_network_calls",
        "unapproved batch refused": "tests/test_send.py::test_unapproved_batch_is_refused",
        "changed form action since approval -> skipped":
            "tests/test_send.py::test_changed_form_action_is_skipped_and_not_claimed",
        "error during POST -> sent_unconfirmed, no retry":
            "tests/test_send.py::test_http_error_after_post_is_sent_unconfirmed_without_retry",
        "breaker trips after N consecutive failures": "tests/test_send.py::test_breaker_trips_after_n_consecutive_failures",
        "claim refused -> no POST": "tests/test_send.py::test_claim_refused_means_no_post",
    })
    counter = "posts(" in (TESTS / "test_send.py").read_text(encoding="utf-8-sig")
    ev.append(f"tests count POSTs received by a local server (LocalSites.posts): {counter}")
    return Result("P5.5", "PASS" if ok and counter else "FAIL", ev)


def p5_reopen(step: int, state: dict) -> Result:
    led = SRC / "outreach" / "ledger.py"
    allowed = _lines_matching(led, r"^REOPENABLE_STATUSES = ")
    ok, ev = _required(state, {
        "refused for sent/sent_unconfirmed/pending/...":
            "tests/test_reopen.py::test_reopen_refused_for_statuses_where_a_post_may_have_happened[",
        "allowed for the 5 no-POST statuses": "tests/test_reopen.py::test_reopen_allowed_statuses[",
        "exactly the prompt's list": "tests/test_reopen.py::test_reopenable_statuses_are_exactly_the_prompt_list",
        "requires typing the site key": "tests/test_reopen.py::test_reopen_requires_typing_the_site_key[",
        "ledger refuses directly too": "tests/test_reopen.py::test_ledger_reopen_refuses_directly_too",
        "CLI reopen": "tests/test_reopen.py::test_cli_reopen",
    })
    event = _lines_matching(led, r"reopened by operator")
    return Result("P5.6", "PASS" if ok and allowed and event else "FAIL", allowed + event + ev)


P5_MUTATIONS = [
    Mutation("(a) POST moved before the claim", "src/outreach/send.py",
             "        # Step 2: claim. Committed to disk before anything is sent.\n",
             "        outcome = _post_once(self.client, plan, payload)  # MUTATION: POST before claim\n"
             "        # Step 2: claim. Committed to disk before anything is sent.\n",
             more=(("        self.fetcher.wait_turn(plan.action_url)\n        outcome = _post_once(self.client, plan, payload)\n",
                    "        self.fetcher.wait_turn(plan.action_url)\n"),),
             tests=("tests/test_send.py",)),
    Mutation("(b) ALLOW_LIVE check removed", "src/outreach/send.py",
             '    return environ.get("ALLOW_LIVE") == "1"\n',
             "    return True  # MUTATION: ALLOW_LIVE check removed\n",
             tests=("tests/test_send.py",)),
    Mutation("(c) claim() always returns True", "src/outreach/ledger.py",
             "            created = cur.rowcount == 1\n",
             "            created = True\n",
             tests=("tests/test_send.py", "tests/test_ledger.py")),
]


def p5_mutations(step: int, state: dict) -> Result:
    ev, ok = [], True
    for m in P5_MUTATIONS:
        caught, mev = _run_mutation(m)
        ok &= caught
        ev += mev + [f"  -> {'CAUGHT (a test failed)' if caught else 'NOT CAUGHT'}"]
    return Result("P5.7", "PASS" if ok else "FAIL", ev)


_SET_ALLOW_LIVE = re.compile(
    r"^\s*(export\s+|set\s+|\$env:)?ALLOW_LIVE\s*=|environ\[\s*[\"']ALLOW_LIVE[\"']\s*\]\s*=|"
    r"setenv\(\s*[\"']ALLOW_LIVE|putenv\(\s*[\"']ALLOW_LIVE|environ\.update\([^)]*ALLOW_LIVE|"
    r"setdefault\(\s*[\"']ALLOW_LIVE", re.I)


def p5_allow_live_and_no_real_send(step: int, state: dict) -> Result:
    setters, mappings = [], []
    for f in _git_ls_files() + [p for _, p in [(None, l[3:].strip()) for l in
                                               _run(["git", "status", "--porcelain", "-uall"]).stdout.splitlines()]]:
        path = ROOT / f
        if not path.is_file() or path.suffix in (".db", ".png", ".jpg"):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if _SET_ALLOW_LIVE.search(line):
                setters.append(f"{f}:{i}: {line.strip()[:100]}")
            elif re.search(r"[\"']ALLOW_LIVE[\"']\s*:\s*[\"']1[\"']", line):
                mappings.append(f"{f}:{i}")
    setters = sorted(set(setters))
    # Markdown files only *describe* the command for the owner; they cannot set anything when the tool runs.
    docs = [s for s in setters if s.split(":", 1)[0].endswith(".md")]
    setters = [s for s in setters if s not in docs]
    dotenv = ROOT / ".env"
    dotenv_live = dotenv.exists() and "ALLOW_LIVE" in dotenv.read_text(encoding="utf-8-sig", errors="replace")
    in_env = "ALLOW_LIVE" in os.environ
    real_log = ROOT / "logs" / "send-log.jsonl"
    real_ledger = ROOT / "data" / "ledger.db"
    ev = [f"lines that SET ALLOW_LIVE as an environment variable (code, config, scripts): {setters or 'none'}",
          f"documentation that shows the owner the command (not executed by anything): {docs or 'none'}",
          f"test-only {{'ALLOW_LIVE': '1'}} mappings passed to run_send(environ=...), not environment variables: "
          f"{len(sorted(set(mappings)))} ({', '.join(sorted(set(mappings))[:4])}{', ...' if len(set(mappings)) > 4 else ''})",
          f".env exists: {dotenv.exists()}; .env mentions ALLOW_LIVE: {dotenv_live}",
          f"ALLOW_LIVE in this validation process's environment: {in_env}",
          f"project send log {_rel(real_log)} exists: {real_log.exists()}; project ledger {_rel(real_ledger)} "
          f"exists: {real_ledger.exists()} (no live run has ever written them)",
          "every send test talks to the 127.0.0.1 test server; the conftest guard blocks all other addresses (A5)"]
    ok = not setters and not dotenv_live and not in_env and not real_log.exists()
    return Result("P5.8", "PASS" if ok else "FAIL", ev)


# --- After Prompt 6 -------------------------------------------------------

DASH = SRC / "outreach" / "dashboard.py"
DASH_HTML = SRC / "outreach" / "dashboard.html"


def p6_bind(step: int, state: dict) -> Result:
    binds = _lines_matching(DASH, r"BIND_HOST\s*=|host\s*=")
    any_all = []
    for p in _py_files(SRC):
        any_all += _lines_matching(p, r"[\"']0\.0\.0\.0[\"']|host\s*=\s*[\"']\s*[\"']|[\"']::[\"']")
    cli_host = _lines_matching(SRC / "outreach" / "cli.py", r"--host")
    ok, ev = _required(state, {"serve() binds 127.0.0.1": "tests/test_dashboard.py::test_serve_binds_to_loopback_only",
                               "foreign Host header refused":
                                   "tests/test_dashboard.py::test_status_and_page_reject_foreign_host"})
    good = any('BIND_HOST = "127.0.0.1"' in b for b in binds) and any("host=BIND_HOST" in b for b in binds)
    ev = binds + [f"0.0.0.0 / wildcard binds in src/: {any_all or 'none'}", f"--host option in CLI: {cli_host or 'none'}"] + ev
    return Result("P6.1", "PASS" if ok and good and not any_all and not cli_host else "FAIL", ev)


def p6_read_only(step: int, state: dict) -> Result:
    opens = _lines_matching(DASH, r"open_readonly\(|sqlite3\.connect\(|Ledger\(")
    ro = _lines_matching(SRC / "outreach" / "ledger.py", r"\?mode=ro")
    writes = _lines_matching(DASH, r"\b(INSERT|UPDATE|DELETE|REPLACE)\b")
    ok, ev = _required(state, {
        "write attempts fail on the dashboard connection": "tests/test_dashboard.py::test_dashboard_connection_is_read_only",
        "every connection URI ends with ?mode=ro": "tests/test_dashboard.py::test_dashboard_uses_mode_ro",
        "ledger bytes unchanged by dashboard requests":
            "tests/test_dashboard.py::test_dashboard_requests_do_not_change_the_ledger",
    })
    only_ro = bool(opens) and all("open_readonly(" in o for o in opens)
    ev = [f"ledger access in dashboard.py: {opens}", f"open_readonly(): {ro}",
          f"SQL writes in dashboard.py: {writes or 'none'}"] + ev
    return Result("P6.2", "PASS" if ok and only_ro and ro and not writes else "FAIL", ev)


def p6_stop(step: int, state: dict) -> Result:
    clears = []
    for p in _py_files(SRC):
        for ln, name, func, _ in _calls_with_func(p):
            if name in ("unlink", "remove") and "stop" in (p.read_text(encoding="utf-8-sig").splitlines()[ln - 1]).lower():
                clears.append(f"{_rel(p)}:{ln} in {func}()")
    ok, ev = _required(state, {
        "STOP endpoint creates the file": "tests/test_dashboard.py::test_stop_creates_file",
        "bad Origin / Host rejected (6 cases)": "tests/test_dashboard.py::test_stop_rejects_bad_origin_or_host[",
        "no route clears STOP; routes are exactly GET /, GET /api/status, POST /stop":
            "tests/test_dashboard.py::test_stop_only_via_post_and_nothing_clears_it",
        "clear-stop is a CLI command": "tests/test_dashboard.py::test_clear_stop_is_a_cli_command",
    })
    origin = _lines_matching(DASH, r"_origin_ok\(request")
    ev = origin + [f"code that removes the STOP file: {clears}"] + ev
    only_cli = clears == ["src/outreach/cli.py:" + clears[0].split(":")[1].split(" ")[0] + " in cmd_clear_stop()"] \
        if len(clears) == 1 else False
    return Result("P6.3", "PASS" if ok and origin and only_cli else "FAIL", ev)


def p6_assets(step: int, state: dict) -> Result:
    html = DASH_HTML.read_text(encoding="utf-8-sig")
    urls = re.findall(r"https?://[^\s\"'<>)]+|//cdn[^\s\"']*", html)
    ext = re.findall(r"<(?:script|link|img)[^>]+(?:src|href)\s*=\s*[\"'](?!/|#)[^\"']+", html, re.I)
    dir_auto = len(re.findall(r'dir="auto"|\.dir = "auto"', html))
    font = re.search(r"--font:\s*([^;]+);", html)
    ok, ev = _required(state, {"page offline + Hebrew-ready": "tests/test_dashboard.py::test_page_is_offline_and_hebrew_ready"})
    ev = [f"http(s) URLs in dashboard.html: {urls or 'none'}", f"external script/link/img: {ext or 'none'}",
          f"dir=\"auto\" uses (markup + text cells built in JS): {dir_auto}",
          f"font stack: {font.group(1).strip() if font else 'missing'}"] + ev
    return Result("P6.4", "PASS" if ok and not urls and not ext and dir_auto >= 2 and font else "FAIL", ev)


def p6_own_process(step: int, state: dict) -> Result:
    importers = []
    for p in _py_files(SRC):
        tree = ast.parse(p.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and ("dashboard" in node.module or node.module == "flask"):
                importers.append(f"{_rel(p)}:{node.lineno}: from {node.module}")
            elif isinstance(node, ast.Import) and any("dashboard" in a.name or a.name == "flask" for a in node.names):
                importers.append(f"{_rel(p)}:{node.lineno}: import")
    lazy = _function_source(SRC / "outreach" / "cli.py", "cmd_dashboard")
    lazy_ok = bool(lazy) and "from .dashboard import serve" in lazy[0]
    proc = _run_project_code("""
        import sys, outreach.cli, outreach.send, outreach.dryrun
        print('flask' in sys.modules, 'outreach.dashboard' in sys.modules)
        """)
    loaded = proc.stdout.split()
    ok, ev = _required(state, {"send/dry-run never import the dashboard":
                               "tests/test_dashboard.py::test_send_and_dry_run_never_import_the_dashboard"})
    allowed = all(i.startswith(("src/outreach/dashboard.py", "src/outreach/cli.py")) for i in importers)
    ev = [f"imports of flask / dashboard in src/: {importers}",
          f"cli imports the dashboard only inside cmd_dashboard(): {lazy_ok}",
          f"after importing cli+send+dryrun: flask loaded={loaded[0] if loaded else '?'}, "
          f"dashboard loaded={loaded[1] if len(loaded) > 1 else '?'}"] + ev
    return Result("P6.5", "PASS" if ok and allowed and lazy_ok and loaded == ["False", "False"] else "FAIL", ev)


_SEED = """
from outreach.config import load_config
from outreach.ledger import Ledger
from outreach.runstatus import write_status
cfg = load_config(environ={})
with Ledger(cfg.ledger_path) as led:
    keys = ["mispara-example.co.il", "xn--6dbbec0c.co.il", "garage-example.co.il", "yoga-example.co.il"]
    led.create_batches([[{"site_key": k, "domain": k, "input_url": "https://" + k + "/"} for k in keys]])
    for k in keys:
        led.add_dry_run_result("B0001", k, "ready" if k != "yoga-example.co.il" else "captcha",
                               "https://" + k + "/contact", "{}", None)
    led.finish_dry_run("B0001"); led.approve("B0001"); led.begin_send("B0001")
    led.claim(keys[0], domain=keys[0], input_url="x", batch_id="B0001", form_url="https://" + keys[0] + "/contact")
    led.finish(keys[0], "sent", "HTTP 200, success text 'תודה'")
    led.claim(keys[1], domain=keys[1], input_url="x", batch_id="B0001", form_url="https://" + keys[1] + "/contact")
    led.finish(keys[1], "sent_unconfirmed", "HTTP 500 after POST")
    led.claim(keys[2], domain=keys[2], input_url="x", batch_id="B0001", form_url="https://" + keys[2] + "/contact")
    led.add_event("info", "send B0001: sent: HTTP 200, success text 'תודה'", site_key=keys[0])
    led.add_event("warning", "send B0001: sent_unconfirmed: HTTP 500 after POST", site_key=keys[1])
write_status(cfg.log_dir, mode="send", batch_id="B0001", state="running", index=3, total=3, site_key=keys[2],
             breaker={"threshold": 5, "consecutive_failures": 1, "tripped": False}, halted_reason=None)
print("seeded")
"""


def _free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def p6_live_dashboard(step: int, state: dict) -> Result:
    import json as _json
    import time as _time
    import urllib.request
    ev: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "templates").mkdir()
        shutil.copyfile(ROOT / "templates" / "consent_request_v1.txt", root / "templates" / "consent_request_v1.txt")
        seed = _run_project_code(_SEED, cwd=root)
        if "seeded" not in seed.stdout:
            return Result("P6.6", "FAIL", [f"seeding failed: {seed.stderr[-300:]}"])
        port = _free_port()
        env = {k: v for k, v in os.environ.items() if k != "ALLOW_LIVE"}
        env.update(PYTHONPATH=str(SRC), PYTHONIOENCODING="utf-8")
        server = subprocess.Popen([sys.executable, "-m", "outreach", "dashboard", "--port", str(port)], cwd=root,
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            data, page = None, ""
            for _ in range(50):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2) as r:
                        data = _json.loads(r.read().decode("utf-8"))
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as r:
                        page = r.read().decode("utf-8")
                    break
                except OSError:
                    _time.sleep(0.2)
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
    if data is None:
        return Result("P6.6", "FAIL", ["dashboard did not answer on 127.0.0.1"])
    b = data["batch"] or {}
    ev = [f"started `python -m outreach dashboard --port {port}` as its own process against a seeded temp ledger",
          f"counters: { {k: v for k, v in data['counters'].items() if v} }",
          f"progress: batch {b.get('batch_id')} {b.get('state')}: {b.get('done')}/{b.get('total')} ({b.get('percent')}%)",
          f"processing now: {(data['run'] or {}).get('site_key')}; breaker: {(data['run'] or {}).get('breaker')}",
          f"pending rows: {[p['site_key'] for p in data['pending']]}",
          f"events shown: {len(data['events'])} (levels {[e['level'] for e in data['events']]})",
          f"page served: {len(page)} bytes, has STOP button: {'id=\"stop\"' in page}, polls every 2 s: "
          f"{'setInterval(poll, 2000)' in page}",
          "server process terminated; temp project deleted"]
    ok = (data["counters"].get("sent") == 1 and data["counters"].get("sent_unconfirmed") == 1
          and data["counters"].get("pending") == 1 and b.get("done") == 2 and b.get("total") == 3
          and len(data["pending"]) == 1 and len(data["events"]) >= 2 and 'id="stop"' in page)
    return Result("P6.6", "PASS" if ok else "FAIL", ev)


# --- After Prompt 7 -------------------------------------------------------

AUDIT = ROOT / "docs" / "audit.md"
PROMPT6_COMMIT = "5c5843e"  # last commit before the audit; src/ must be unchanged since then


def p7_audit_report(step: int, state: dict) -> Result:
    text = AUDIT.read_text(encoding="utf-8-sig") if AUDIT.exists() else ""
    needed = {
        "every POST path": r"^## 1\. Every code path that performs an HTTP POST",
        "LLM/AI scan result": r"^## 2\. LLM / AI SDK scan",
        "normalizer review": r"^## 3\. Normalizer",
        "crash-window analysis": r"^## 4\. Crash windows",
        "concurrency analysis": r"^## 5\. Concurrency",
        "ledger deleted": r"^## 6\. If the ledger file is deleted",
        "power-loss analysis": r"^## 7\. Power loss",
        "no clear/downgrade of pending/sent/sent_unconfirmed": r"^## 8\. Can any code path clear or downgrade",
        "gitignore / tracked data": r"^## 9\. Personal data and git",
        "robots.txt question": r"^### 10\.1 robots\.txt",
        "POST encoding question": r"^### 10\.2 POST encoding",
        "reopen recommendation": r"^### 10\.3 reopen",
        "ranked residual risks": r"^## 12\. Residual risks, ranked",
    }
    ev, ok = [], bool(text)
    for label, pat in needed.items():
        found = bool(re.search(pat, text, re.M))
        ok &= found
        ev.append(f"{label}: {'present' if found else 'MISSING'}")
    risks = re.findall(r"^(\d+)\. \*\*", text.split("## 12.", 1)[-1], re.M) if "## 12." in text else []
    ev.append(f"ranked risks listed: {len(risks)} ({', '.join(risks)})")
    ok &= len(risks) >= 3 and risks == [str(i) for i in range(1, len(risks) + 1)]
    single = re.search(r"\*\*The only POST the tool makes\.\*\*", text)
    ev.append(f"report states exactly one POST path: {bool(single)}")
    return Result("P7.1", "PASS" if ok and single else "FAIL", ev)


def p7_readme(step: int, state: dict) -> Result:
    text = (ROOT / "README.md").read_text(encoding="utf-8-sig")
    sections = {s: bool(re.search(rf"^## {s}\b", text, re.M)) for s in ("Setup", "Workflow", "Settings",
                                                                        "Backup and restore", "Known limits")}
    wf = text.split("## Workflow", 1)[-1].split("\n## ", 1)[0]
    order = [wf.find(f"python -m outreach {c}") for c in ("ingest", "dry-run", "approve", "dashboard", "send")]
    order_ok = all(i >= 0 for i in order) and order == sorted(order)
    proc = _run_project_code("from outreach.config import SETTINGS\nfor s in SETTINGS: print(s.env)")
    envs = proc.stdout.split()
    missing = [e for e in envs if f"`{e}`" not in text]
    limits = text.split("## Known limits", 1)[-1]
    limit_ok = {"JS-only sites": "JavaScript" in limits, "no CAPTCHA handling": "CAPTCHA" in limits,
                "legal questions": "Legal" in limits or "legal" in limits}
    restore = "To restore" in text and "newest" in text
    ev = [f"sections: {sections}", f"workflow order ingest < dry-run < approve < dashboard < send: {order_ok} "
          f"(positions {order})", f"settings documented: {len(envs) - len(missing)}/{len(envs)}"
          + (f" missing {missing}" if missing else ""), f"known limits: {limit_ok}", f"restore steps present: {restore}"]
    ok = all(sections.values()) and order_ok and envs and not missing and all(limit_ok.values()) and restore
    return Result("P7.2", "PASS" if ok else "FAIL", ev)


def p7_no_behavior_change(step: int, state: dict) -> Result:
    diff = _run(["git", "diff", "--stat", PROMPT6_COMMIT, "--", "src"]).stdout.strip()
    untracked = [l for l in _run(["git", "status", "--porcelain", "-uall", "--", "src"]).stdout.splitlines()
                 if l.startswith("??")]
    patches = sorted((ROOT / "docs" / "proposals").glob("*.patch"))
    applies = {}
    for p in patches:
        applies[p.name] = _run(["git", "apply", "--check", str(p)]).returncode == 0
    ev = [f"`git diff {PROMPT6_COMMIT} -- src` (committed + working tree): {diff or 'empty'}",
          f"untracked files in src/: {untracked or 'none'}",
          f"behavior changes kept as proposals, not applied: {[p.name for p in patches]}",
          f"each proposal applies cleanly (git apply --check): {applies}"]
    ok = not diff and not untracked and len(patches) == 3 and all(applies.values())
    return Result("P7.3", "PASS" if ok else "FAIL", ev)


def p7_llm_scan_repo(step: int, state: dict) -> Result:
    pat = re.compile(_AI_RE.pattern + r"|(?<![A-Za-z0-9_])(gpt-[0-9]|chatgpt|gemini)(?![A-Za-z0-9_])", re.I)
    exempt = {"scripts/validate.py", "docs/validation.md", "docs/audit.md"}  # they list the forbidden names
    hits = []
    for f in _git_ls_files():
        if f in exempt:
            continue
        try:
            text = (ROOT / f).read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pat.search(line):
                hits.append(f"{f}:{i}")
    ev = [f"tracked files scanned (except {sorted(exempt)}, which list the forbidden names): "
          f"{len(_git_ls_files()) - len(exempt)}", f"matches: {hits or 'none'}"]
    return Result("P7.4", "FAIL" if hits else "PASS", ev)


STEPS: dict[int, list[Callable[[int, dict], Result]]] = {
    0: [p0_dirs, p0_gitignore, p0_pyproject, p0_claude_md, p0_scaffold_only, p0_script],
    1: [p1_normalizer, p1_tldextract_offline, p1_pragmas, p1_claim_code, p1_update_delete_scan,
        p1_required_tests, p1_mutations],
    2: [p2_settings_documented, p2_backup, p2_sendlog, p2_preflight, p2_breaker, p2_template, p2_ingest,
        p2_no_fetch],
    3: [p3_no_post, p3_no_browser, p3_fetcher, p3_fixtures, p3_finder_classifier, p3_extra_fetches],
    4: [p4_dry_run_no_claim, p4_dry_run_results, p4_report_message, p4_approve, p4_export, p3_no_post],
    5: [p5_single_post, p5_gates, p5_order, p5_no_retry, p5_required_tests, p5_reopen, p5_mutations,
        p5_allow_live_and_no_real_send],
    6: [p6_bind, p6_read_only, p6_stop, p6_assets, p6_own_process, p6_live_dashboard],
    7: [p7_audit_report, p7_readme, p7_no_behavior_change, p7_llm_scan_repo],
}
# Checks from earlier steps that must stay true at every later step (used by --all).
PERSISTENT = {p0_dirs, p0_gitignore, p0_claude_md, p1_normalizer, p1_tldextract_offline, p1_pragmas,
              p1_claim_code, p1_update_delete_scan, p1_required_tests, p1_mutations,
              p2_settings_documented, p2_backup, p2_sendlog, p2_preflight, p2_breaker, p2_template, p2_ingest,
              p3_no_browser, p3_fetcher, p3_fixtures, p3_finder_classifier, p3_extra_fetches,
              p4_dry_run_no_claim, p4_dry_run_results, p4_report_message, p4_approve, p4_export,
              p5_single_post, p5_gates, p5_order, p5_no_retry, p5_required_tests, p5_reopen, p5_mutations,
              p5_allow_live_and_no_real_send,
              p6_bind, p6_read_only, p6_stop, p6_assets, p6_own_process, p6_live_dashboard}


# --- driver ---------------------------------------------------------------

def write_log(step: int, count: int, verdict: str) -> None:
    header = "# Validation log\n\n| date | step | tests | result |\n|---|---|---|---|\n"
    rows: list[str] = []
    if LOG.exists():
        rows = [l for l in LOG.read_text(encoding="utf-8-sig").splitlines() if re.match(r"^\|\s*\d{4}-", l)]
    row = f"| {_dt.date.today().isoformat()} | {step} | {count} | {verdict} |"
    rows = [r for r in rows if r.split("|")[2].strip() != str(step)] + [row]
    LOG.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--step", type=int)
    g.add_argument("--all", action="store_true")
    ap.add_argument("--log", action="store_true", help="record result in docs/validation-log.md")
    args = ap.parse_args()

    step = LATEST_IMPLEMENTED_STEP if args.all else args.step
    if step not in STEPS:
        print(f"step {step} has no checks implemented yet (latest: {LATEST_IMPLEMENTED_STEP})")
        return 2
    state: dict = {"csv_before_tests": _csv_fingerprints()}
    results = [r for r in (c(step, state) for c in ALWAYS) if r is not None]
    if args.all:
        for s in sorted(STEPS):
            results += [c(step, state) for c in STEPS[s] if s == step or c in PERSISTENT]
    else:
        results += [c(step, state) for c in STEPS[step]]

    for r in results:
        print(f"[{r.status:6}] {r.cid}")
        for e in r.evidence:
            print(f"           {e}")
    fails = [r.cid for r in results if r.status == "FAIL"]
    manual = [r.cid for r in results if r.status == "MANUAL"]
    verdict = "FAIL" if fails else "PASS"
    print(f"\nRESULT: {verdict}  (fail: {fails or 'none'}; manual review: {manual or 'none'}; "
          f"tests: {state.get('test_count')})")
    if args.log:
        write_log(step, state.get("test_count", 0), verdict)
        print(f"logged to {_rel(LOG)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
