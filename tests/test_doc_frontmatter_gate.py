"""Frontmatter + audience gate — `ci/doc-merge-gate` merge=publish item 2.

WHY: `docs/dev/documentation-architecture.md` ("Gates — merge = publish") lists
"frontmatter + audience" as a merge-blocking check: a published doc page lacking its
Purpose/Audience/Authoritative-for header. `scripts/check_doc_frontmatter.py` is the
deterministic (stdlib-only, no LLM, no network) implementation; see that script's module
docstring for the full scope rationale (`PUBLISHED_DOC_FILES` — the current L1 front-door
registry, deliberately narrower than "all of docs/dev/**"). This test re-runs it as a
subprocess (mirrors `tests/test_doc_links.py`/`tests/test_docstring_coverage_gate.py`) so it
rides the existing `pytest` gate that already runs on every PR — no new CI job needed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_doc_frontmatter.py"


def test_checker_script_exists() -> None:
    """Sanity teeth: a moved/deleted checker script fails loudly, not silently."""
    assert CHECKER.is_file(), f"{CHECKER} is missing — the frontmatter gate has nothing to run."


def test_every_published_doc_carries_the_header() -> None:
    """Re-run the bare CLI exactly as a human would locally.

    Exit 0 = every registered L1 doc carries Purpose/Audience/Authoritative-for near its top;
    exit 1 = the script's own report (a `path -> missing <fields>` listing) is surfaced below.
    """
    result = subprocess.run(  # noqa: S603 - static, trusted argv (sys.executable + a repo-relative path)
        [sys.executable, str(CHECKER)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        "scripts/check_doc_frontmatter.py found published doc(s) missing the "
        "Purpose/Audience/Authoritative-for header — add the missing field(s) rather than "
        "skipping this gate:\n" + output
    )
