"""Zero-PII / zero-secret clone gate — PX-29 (F-sec-06 KEEP) / v1.0.8 item 8.4.

The 2026-06 product-excellence review affirmed (``F-sec-06``, KEEP) that a fresh
hostile clone carries zero real PII and zero secrets: ``.gitignore`` broadly
ignores the user-data surface, only auditably-synthetic fixtures are committed
(Casey Rivera, RFC-2606 domains), and a tree scan for API-key shapes is empty.
The finding's stated fear is that the allow-list lines get "tidied away" in a
future gitignore refactor.

This generalizes the existing ``configs/``-only check
(``tests/test_testuser_fixture.py::test_only_example_and_testuser_configs_are_tracked``)
to the WHOLE PII/secret surface, so the S-1 "#1 release fear" (a PII leak) is a
continuously-kept fact, not a one-time hand audit. It reuses that test's
``git ls-files`` + graceful-skip-when-not-a-git-tree pattern.

Scope note: this scans the tracked WORKING TREE (fast, deterministic). The
"zero key-shapes across full history" claim was verified once at the review pin;
a per-run full-``git log`` scan is slow and flaky in shallow CI clones, so it is
out of scope for this gate (a separate, deliberate audit if ever wanted).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Binary/opaque suffixes skipped by the key-shape text scan (a key cannot hide in
# a .docx the way it could in a tracked .py/.md/.json/.config).
_BINARY_SUFFIXES = frozenset(
    {".docx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
     ".ttf", ".otf", ".sqlite", ".pyc", ".zip", ".gz"}
)


def _git_ls_files(*paths: str) -> list[str]:
    """Tracked files under the given pathspecs (POSIX-separated). Skips the test
    if we're not inside a git working tree (CI quirk / detached snapshot)."""
    result = subprocess.run(  # noqa: S603 — trusted: literal git command + test-authored pathspecs
        ["git", "ls-files", *paths],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        pytest.skip("Not in a git working tree (CI quirk or detached snapshot)")
    return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())


# --------------------------------------------------------------------------- #
# 1. Each PII directory tracks ONLY its auditably-synthetic fixtures.
# --------------------------------------------------------------------------- #
def test_only_synthetic_configs_tracked() -> None:
    """configs/ tracks only the doc template + the synthetic dummy user."""
    allowed = {"configs/example.config", "configs/testuser.config"}
    leaked = [t for t in _git_ls_files("configs/") if t not in allowed]
    assert not leaked, f"Real-user config(s) leaked into git tracking: {leaked}"


def test_only_synthetic_resumes_tracked() -> None:
    """resumes/ tracks only the .gitkeep and the synthetic Casey Rivera fixture."""
    leaked = [
        t for t in _git_ls_files("resumes/")
        if t != "resumes/.gitkeep" and not t.startswith("resumes/testuser/")
    ]
    assert not leaked, f"Real résumé file(s) leaked into git tracking: {leaked}"


def test_output_dir_tracks_only_gitkeep() -> None:
    """output/ holds generated artifacts (often real PII) — only .gitkeep ships."""
    leaked = [t for t in _git_ls_files("output/") if t != "output/.gitkeep"]
    assert not leaked, f"Generated output leaked into git tracking: {leaked}"


def test_no_real_eval_fixtures_tracked() -> None:
    """evals/fixtures/real/ may hold real PII — only its .gitkeep ships; the
    synthetic/ fixtures are auditably synthetic and fine."""
    leaked = [
        t for t in _git_ls_files("evals/fixtures/")
        if t != "evals/fixtures/real/.gitkeep"
        and not t.startswith("evals/fixtures/synthetic/")
    ]
    assert not leaked, f"Non-synthetic eval fixture(s) leaked into git tracking: {leaked}"


def test_only_bundled_personas_tracked() -> None:
    """personas/ ships the bundled templates + the shared cover-letter shell;
    per-user personas/<username>/ are PII and stay gitignored."""
    leaked = [
        t for t in _git_ls_files("personas/")
        if t != "personas/cover_letter.html" and not t.startswith("personas/bundled/")
    ]
    assert not leaked, f"User persona file(s) leaked into git tracking: {leaked}"


def test_no_database_or_logs_tracked() -> None:
    """The SQLite corpus (candidate memory = PII) and LLM telemetry never ship."""
    db_leaked = [t for t in _git_ls_files("db/") if ".sqlite" in t]
    assert not db_leaked, f"SQLite database leaked into git tracking: {db_leaked}"
    assert not _git_ls_files("logs/"), "logs/ (LLM telemetry) must not be tracked"


# --------------------------------------------------------------------------- #
# 2. No secret-shaped FILE is tracked anywhere in the tree.
# --------------------------------------------------------------------------- #
def test_no_secret_files_tracked() -> None:
    """No tracked path matches the secret-file patterns block-secrets.sh guards
    (.api_key / .env* / *.pem / *.key / *.p12 / *.crt)."""
    secret_suffixes = (".pem", ".key", ".p12", ".crt")
    offenders = []
    for path in _git_ls_files():
        name = path.rsplit("/", 1)[-1]
        if name == ".api_key" or name == ".env" or name.startswith(".env."):
            offenders.append(path)
        elif name.endswith(secret_suffixes):
            offenders.append(path)
    assert not offenders, f"Secret-shaped file(s) tracked: {offenders}"


# --------------------------------------------------------------------------- #
# 3. No API-key SHAPE appears in any tracked text file.
# --------------------------------------------------------------------------- #
def test_no_api_key_shapes_in_tracked_files() -> None:
    """Scan tracked text files for the Anthropic key shape (block-secrets.sh:29).

    The pattern is assembled from fragments so this test file is not a self-match
    when it is itself one of the tracked files being scanned.
    """
    key_re = re.compile("sk-" + "ant-" + r"[A-Za-z0-9_-]{20,}")
    offenders: list[str] = []
    for rel in _git_ls_files():
        if Path(rel).suffix.lower() in _BINARY_SUFFIXES:
            continue
        try:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if key_re.search(text):
            offenders.append(rel)
    assert not offenders, (
        f"Anthropic API-key shape found in tracked file(s): {offenders}. "
        "Secrets must never be committed (charter C-1 / S-1; block-secrets.sh)."
    )


# --------------------------------------------------------------------------- #
# 4. The load-bearing .gitignore lines are present (not "tidied" away).
# --------------------------------------------------------------------------- #
def test_gitignore_pii_lines_present() -> None:
    """F-sec-06's stated fear: a gitignore refactor drops an allow-list line and a
    real user's data silently becomes trackable. Pin the load-bearing ignores."""
    lines = {
        ln.strip()
        for ln in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    required = {
        ".api_key", "*.key", "*.pem", "*.p12", "*.crt",
        "configs/*.config", "resumes/*", "output/*", "personas/*",
        "evals/fixtures/real/*", "db/*.sqlite", "logs/",
    }
    missing = sorted(required - lines)
    assert not missing, (
        f".gitignore is missing load-bearing PII/secret ignore line(s): {missing}. "
        "Restore them — do not 'tidy' the allow-list away (F-sec-06)."
    )
