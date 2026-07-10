"""Single-home (D5) heuristic gate — `ci/doc-merge-gate` merge=publish item 3.

WHY: `docs/dev/documentation-architecture.md` ("Gates — merge = publish") lists
"single-home (D5): a page restates a fact owned elsewhere instead of linking" as a
merge-blocking check — explicitly the hardest of the five to automate (verifying restatement
requires meaning, not grep). `scripts/check_doc_single_home.py` implements the documented,
deliberately-scoped-down heuristic instead: near-verbatim duplicated prose paragraphs across
the L1 `PUBLISHED_DOC_FILES` registry (see that module's docstring for the full rationale,
scope, and stated non-goals — this is a floor, not a fact-checker). This test (a) proves the
detector has real teeth on synthetic data (so a passing real-tree run is not a vacuous "the
matcher is broken" pass), then (b) re-runs the real gate as a subprocess, matching the
`tests/test_doc_links.py` pattern so it rides the existing `pytest` gate with no new CI job.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_doc_single_home.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_single_home as _checker_module  # noqa: E402 - path insert must precede this


def test_checker_script_exists() -> None:
    """Sanity teeth: a moved/deleted checker script fails loudly, not silently."""
    assert CHECKER.is_file(), f"{CHECKER} is missing — the single-home gate has nothing to run."


def test_detector_has_teeth_on_synthetic_duplication() -> None:
    """A genuinely duplicated long paragraph across two files must be flagged; distinct
    prose of the same length must not — proves the matcher works before trusting a green
    real-tree run."""
    shared = (
        "This is a long shared paragraph that should be detected as duplicated across two "
        "different files because it repeats the exact same wording word for word, sentence "
        "for sentence, with absolutely no changes made anywhere in the text at all whatsoever."
    )
    assert len(shared) >= _checker_module._MIN_PARAGRAPH_CHARS

    text_a = f"# Doc A\n\n{shared}\n\nSome A-only closing paragraph, long enough to not matter."
    text_b = f"# Doc B\n\n{shared}\n\nSome B-only closing paragraph, long enough to not matter."
    text_c = (
        "# Doc C\n\nAn entirely different paragraph with unrelated wording that shares no "
        "sentence at all with the other two synthetic documents used in this teeth test."
    )

    paras_a = [
        _checker_module._normalize(p) for p in _checker_module._iter_unfenced_paragraphs(text_a)
    ]
    paras_b = [
        _checker_module._normalize(p) for p in _checker_module._iter_unfenced_paragraphs(text_b)
    ]
    paras_c = [
        _checker_module._normalize(p) for p in _checker_module._iter_unfenced_paragraphs(text_c)
    ]

    shared_normalized = _checker_module._normalize(shared)
    assert shared_normalized in paras_a
    assert shared_normalized in paras_b
    assert shared_normalized not in paras_c
    assert set(paras_a) & set(paras_c) == set()


def test_fenced_code_is_excluded_from_matching() -> None:
    """A code block repeated across files (e.g. the same `pip install` snippet) must not
    trip the heuristic — only prose paragraphs outside fences are scanned."""
    code = (
        "```bash\n"
        "python -m pip install --upgrade pip\n"
        "pip install -e '.[dev]'\n"
        "python -m playwright install chromium\n"
        "```"
    )
    paragraphs = _checker_module._iter_unfenced_paragraphs(f"# Title\n\n{code}\n\nProse after.")
    assert all("pip install" not in p for p in paragraphs)


def test_no_duplicated_paragraph_across_published_docs() -> None:
    """Re-run the bare CLI exactly as a human would locally.

    Exit 0 = no near-verbatim paragraph duplicated across 2+ registered L1 docs; exit 1 = the
    script's own report (duplicated-pair listing) is surfaced below for a human to judge
    (link instead of restate, or add a reviewed exception if genuinely intentional).
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
        "scripts/check_doc_single_home.py found near-verbatim duplicated paragraph(s) across "
        "distinct L1 docs — link to the canonical home (D5) instead of restating, or review "
        "and add a documented exception if genuinely intentional:\n" + output
    )
