"""Accessibility-floor guards — PX-29 (F-expa11y-07 + F-expa11y-08 KEEP) / item 8.4.

The 2026-06 product-excellence review affirmed two a11y floors as load-bearing:

* **F-expa11y-08** — the ``_announce()`` ARIA live-region discipline (a polite,
  atomic ``#srAnnounce`` region written at every meaningful async completion).
  The review flagged it "no test guards it" — this is that guard.
* **F-expa11y-07** — the keyboard bullet-reorder affordance (up/down buttons with
  aria-labels driving ``_moveBulletRow``). Its *behavioral* persistence already
  has a live UX test (``tests/ux/regression/test_20260604_bullet_drag_reorder.py``);
  this adds the always-runs static floor so the affordance can't be silently
  deleted even when Chromium is absent and the UX tier skips.

These are static source-scans (precedent: ``tests/test_construction_boundary.py``),
so they run in every environment — the reliable do-not-regress floor. The live
runtime check for the announcer lives in ``tests/ux/a11y/test_announce_live_region.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "templates" / "index.html"
APP_JS = REPO_ROOT / "static" / "app.js"


def _read(path: Path) -> str:
    assert path.is_file(), f"expected source file is missing: {path}"
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# F-expa11y-08 — the _announce() live region.
# --------------------------------------------------------------------------- #
def test_live_region_present_and_polite() -> None:
    """templates/index.html carries the #srAnnounce region, and it is a polite,
    atomic live region (so screen readers announce completions without interrupting)."""
    html = _read(INDEX_HTML)
    match = re.search(r"<[^>]*\bid=\"srAnnounce\"[^>]*>", html)
    assert match, 'The #srAnnounce live region is missing from templates/index.html (F-expa11y-08).'
    tag = match.group(0)
    assert 'aria-live="polite"' in tag, f'#srAnnounce must be aria-live="polite"; got: {tag}'
    assert 'aria-atomic="true"' in tag, f'#srAnnounce must be aria-atomic="true"; got: {tag}'


def test_announce_helper_defined_and_wired() -> None:
    """static/app.js defines _announce() and wires it to the #srAnnounce region."""
    js = _read(APP_JS)
    assert "function _announce(" in js, "_announce() helper is missing from static/app.js (F-expa11y-08)."
    assert "getElementById('srAnnounce')" in js, (
        "_announce() must write to the #srAnnounce region (getElementById('srAnnounce'))."
    )


def test_announce_called_at_success_sites() -> None:
    """_announce() is invoked at the meaningful async completions (analysis ready,
    questions ready, generation done, edits saved, refinement done, …). The review
    counted 7 success call sites + the definition; require at least that many so a
    refactor that quietly drops the announcements fails."""
    js = _read(APP_JS)
    occurrences = js.count("_announce(")  # 1 definition + >= 7 call sites
    assert occurrences >= 8, (
        f"Expected the _announce() definition + >=7 success call sites (>=8 total), "
        f"found {occurrences}. A dropped announcement weakens the F-expa11y-08 floor."
    )


# --------------------------------------------------------------------------- #
# F-expa11y-07 — the keyboard bullet-reorder affordance.
# --------------------------------------------------------------------------- #
def test_bullet_reorder_keyboard_affordance_present() -> None:
    """The keyboard reorder buttons (labelled up/down, driving _moveBulletRow) are
    the a11y alternative to drag. They must not be silently removed — the behavioral
    persistence check lives in the UX regression suite (which skips without Chromium)."""
    js = _read(APP_JS)
    for needed in ("_moveBulletRow", "reorder-btn", "Move bullet up", "Move bullet down"):
        assert needed in js, (
            f"Keyboard bullet-reorder affordance lost {needed!r} from static/app.js "
            "(F-expa11y-07 — the keyboard alternative to drag-reorder)."
        )
