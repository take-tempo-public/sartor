"""Cross-document link + cite checker gate — Carry-forward ledger item #7 /
RELEASE_ARC §Phase 4.8 (ii) / `chore/doc-link-sweep`.

WHY: `wiki-lint` only checks `docs/wiki/` structural integrity ([[backlinks]],
`path:line` cite existence, index coherence). The extract-don't-restate move
that produced `docs/governance/` multiplied plain `[text](path)` pointers
across the contract docs (`AGENTS.md`/`CLAUDE.md`) and the rest of the doc
set with no gate checking them — pointer-rot risk with no periodic catch.
This test is that periodic catch: it re-runs `scripts/check_doc_links.py`
(deterministic, stdlib-only — no LLM, no network) so the check rides the
EXISTING `pytest` gate that already runs on every PR. Wiring it here IS the
"periodic" mechanism the ledger row asked for; no new CI job is needed.

HOW: `scripts/check_doc_links.py` is invoked as a subprocess (mirrors
`test_docstring_coverage_gate.py`'s pattern) so a failure prints the exact
`file:line -> broken-target` listing a human would see running it directly.
See that script's module docstring for the full scope (link check tree-wide,
cite-existence check scoped to `docs/governance/*.md` + `AGENTS.md` +
`CLAUDE.md`) and its documented exclusions (external URLs, fenced code,
literal backtick-quoted link syntax, gitignored targets, two narrow
documented (file, target) exclusions).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_doc_links.py"


def test_checker_script_exists() -> None:
    """Sanity teeth: a moved/deleted checker script fails loudly, not silently."""
    assert CHECKER.is_file(), f"{CHECKER} is missing — the doc-link gate has nothing to run."


def test_no_broken_cross_document_links_or_cites() -> None:
    """Every tracked `*.md` file's relative links + governance `path:line` cites resolve.

    Re-runs the bare CLI (`python scripts/check_doc_links.py`) exactly as a
    human would locally. Exit 0 = clean; exit 1 = the script's own report
    (a `file:line -> broken-target` listing) is surfaced in the assertion
    message.
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
        "scripts/check_doc_links.py found broken cross-document link(s)/cite(s) — "
        "fix the target (or, if the target is genuinely ambiguous, resolve it by hand "
        "and note the decision) rather than skipping this gate:\n" + output
    )
