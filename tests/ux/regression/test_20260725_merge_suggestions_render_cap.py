"""C-7 falsification test for carry-forward ledger item 11
(docs/dev/diagnosis/merge-suggestions-render-cap.md): the merge-suggestions
panel (`#mergeSuggestionsList`) renders every matching experience pair as a
flat DOM list with no cap, confirmed at 1,086 cards / 142,682px on a 48-role
duplicate-heavy corpus (docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md
O-6). This test seeds a smaller corpus that still exceeds the intended page
size and asserts the real production render path
(`refreshMergeSuggestions`, app.js:5212) bounds DOM node count to a fixed
ceiling rather than one node per match.

Must fail on HEAD (no cap exists yet) and pass once
`blueprints/corpus/curation.py::list_merge_suggestions` and
`static/app.js::refreshMergeSuggestions` paginate.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage

# 8 near-identical companies -> C(8,2) = 28 candidate pairs, all SIMILAR-band
# (same default title/dates/bullets; only the company suffix digit differs,
# same shape as the existing growth probe at
# tests/ux/regression/test_20260708_busy_states_and_chip.py:854-855) --
# comfortably over any reasonable page size (plan default: 25).
_NEAR_DUPLICATE_COMPANIES = 8
_EXPECTED_PAIRS = _NEAR_DUPLICATE_COMPANIES * (_NEAR_DUPLICATE_COMPANIES - 1) // 2
_MAX_INITIAL_CARDS = 25  # mirrors MERGE_SUGGESTIONS_PAGE_SIZE


@pytest.mark.ux
def test_merge_suggestions_render_is_capped(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    cid = seed_user(ux_app, "alice")
    for i in range(_NEAR_DUPLICATE_COMPANIES):
        seed_exp_with_bullets(cid, company=f"Company {i}")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open().wait_for_cards()

    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount > 0",
        timeout=15_000,
    )
    # Let the async refreshMergeSuggestions() render settle before counting.
    page.wait_for_timeout(200)

    rendered = page.evaluate(
        "() => document.getElementById('mergeSuggestionsList').childElementCount"
    )
    assert _EXPECTED_PAIRS > _MAX_INITIAL_CARDS, (
        f"fixture doesn't actually exceed the page size ({_EXPECTED_PAIRS} pairs "
        f"vs {_MAX_INITIAL_CARDS} cap) -- the test can't prove anything either way"
    )
    assert rendered <= _MAX_INITIAL_CARDS, (
        f"PROBE CONFIRMS THE DEFECT (expected on HEAD): a single "
        f"refreshMergeSuggestions() call rendered {rendered} DOM nodes into "
        f"#mergeSuggestionsList for {_EXPECTED_PAIRS} matching pairs -- one node "
        f"per match, no cap. Should be <= {_MAX_INITIAL_CARDS} once "
        f"list_merge_suggestions + refreshMergeSuggestions paginate."
    )
