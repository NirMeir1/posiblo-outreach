"""Mechanical checks from docs/validation.md (stdlib only).

Usage:
    python scripts/validate.py --step N        # "Always" checks + section for step N
    python scripts/validate.py --step N --log  # same, and record the result in docs/validation-log.md
    python scripts/validate.py --all           # "Always" checks + every implemented step section

Each check prints PASS, FAIL or MANUAL (MANUAL = needs a human/assistant to
look at the listed evidence). Exit code is 1 if any check FAILs.

Run it with the project's virtualenv interpreter so that A1 can run pytest,
e.g. `.venv\\Scripts\\python scripts/validate.py --step 0`.
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import importlib.metadata
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
LOG = ROOT / "docs" / "validation-log.md"
BUILD_PROMPTS = ROOT / "docs" / "build-prompts.md"

LATEST_IMPLEMENTED_STEP = 0

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


def check_a1(step: int, state: dict) -> Result:
    proc = _run([sys.executable, "-m", "pytest", "-q", "-rsx"])
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


ALWAYS: list[Callable[[int, dict], Result]] = [check_a1, check_a2, check_a3, check_a4, check_a5, check_a6]


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


STEPS: dict[int, list[Callable[[int, dict], Result]]] = {
    0: [p0_dirs, p0_gitignore, p0_pyproject, p0_claude_md, p0_scaffold_only, p0_script],
}


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
    sections = sorted(STEPS) if args.all else [step]

    state: dict = {}
    results = [c(step, state) for c in ALWAYS]
    for s in sections:
        results += [c(step, state) for c in STEPS[s]]

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
