"""Epic C C3 (`feat/dashboard-copy-discovery`) — lay copy + progressive discovery.

RELEASE_ARC §Epic C, C3: "every module on every tab gets an on-screen one-line lay
summary + a `_DASH_HELP` info bubble". The epic brief's acceptance check: "every
`.tile` / module has an on-screen lay line plus a `data-help` id that resolves in
`_DASH_HELP` (a test iterates `.tile`). No raw file or field name appears unglossed
in Quality tiles."

These tests render the **populated** console through a Flask test client (every
tile on every tab renders only when its data exists) and parse the HTML with the
stdlib parser. They pin the *structure* — every tile has copy, and every bubble
resolves — rather than any copy string, so rewording stays free while a tile
added later without copy fails here by construction. The in-browser counterpart
(each bubble actually opens `#helpModal`) is
`tests/ux/regression/test_20260925_dashboard_copy_discovery.py`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

import pytest

# --------------------------------------------------------------------------- fixtures

_EVAL_RECORDS: list[dict[str, Any]] = [
    {
        "schema_version": 3,
        "source": "eval",
        "fixture": "pm-senior",
        "rubric": "grounding",
        "score": 3.5,
        "status": "ok",
        "prompt_version": "v1",
        "run_id": "r1",
        "timestamp": "2026-06-06T12:00:00Z",
        "failed_rules": ["invented_metric"],
        "deterministic_metrics": {
            "groundedness": {
                "layers": ["L0"],
                "fabricated_specifics_rate": 0.1,
                "flagged_count": 1,
                "score": 4.2,
            },
            "fabricated_specifics": {
                "total_bullets": 4,
                "total_specifics": 10,
                "flagged": 1,
                "fabricated_specifics_rate": 0.1,
                "per_bullet": [
                    {"bullet": "Led a $5M migration", "n_specifics": 1, "flagged": ["$5M"]}
                ],
                "flagged_samples": ["$5M"],
            },
        },
    },
    # Two prompt versions of eval_composite so the Pareto summary renders.
    {
        "schema_version": 3,
        "source": "eval",
        "fixture": "pm-senior",
        "rubric": "eval_composite",
        "score": 4.0,
        "status": "ok",
        "prompt_version": "v1",
        "run_id": "r1",
        "timestamp": "2026-06-06T12:00:00Z",
        "latency_ms": 60000,
        "cost_usd": 0.1,
    },
    {
        "schema_version": 3,
        "source": "eval",
        "fixture": "pm-senior",
        "rubric": "eval_composite",
        "score": 4.3,
        "status": "ok",
        "prompt_version": "v2",
        "run_id": "r2",
        "timestamp": "2026-06-07T12:00:00Z",
        "latency_ms": 50000,
        "cost_usd": 0.09,
    },
]

_CALLS: list[dict[str, Any]] = [
    {
        "timestamp": "2026-06-06T12:00:01Z",
        "username": "eval:pm-senior",
        "run_id": "run-a",
        "call": "analyze_extraction",
        "model": "claude-haiku-4-5-20251001",
        "prompt_version": "v1",
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 1000,
        "stop_reason": "end_turn",
        "status": "ok",
    },
    {
        "timestamp": "2026-06-06T12:00:02Z",
        "username": "eval:pm-senior",
        "run_id": "run-a",
        "call": "generate",
        "model": "claude-sonnet-5",
        "prompt_version": "v1",
        "input_tokens": 200,
        "output_tokens": 80,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 3000,
        "stop_reason": None,
        "status": "error",
        "error_type": "APIStatusError",
        "error_message": "overloaded",
    },
]


@pytest.fixture
def populated_page(tmp_path, monkeypatch) -> str:
    """Render /dashboard/ with every tab's data present; return the HTML."""
    from flask import Flask

    from dashboard import routes as dashboard_routes

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "seed.jsonl").write_text(
        "\n".join(json.dumps(r) for r in _EVAL_RECORDS) + "\n", encoding="utf-8"
    )
    (results_dir / "baseline_v1.json").write_text(
        json.dumps(
            {
                "baseline_id": "v1-test",
                "prompt_version": "v1",
                "fixtures": {"pm-senior": {"grounding": {"mean": 4.6}}},
            }
        ),
        encoding="utf-8",
    )
    log = tmp_path / "llm_calls.jsonl"
    log.write_text("\n".join(json.dumps(c) for c in _CALLS) + "\n", encoding="utf-8")
    monkeypatch.setattr(dashboard_routes, "LLM_LOG", log)
    monkeypatch.setattr(dashboard_routes, "EVAL_RESULTS_DIR", results_dir)

    app = Flask(__name__)
    app.register_blueprint(dashboard_routes.dashboard_bp, url_prefix="/dashboard")
    with app.test_client() as client:
        resp = client.get("/dashboard/", headers={"Host": "127.0.0.1"})
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


# --------------------------------------------------------------------------- tiny DOM


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str]
    parent: _Node | None = None
    children: list[_Node] = field(default_factory=list)
    text: list[str] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def iter(self):
        yield self
        for c in self.children:
            yield from c.iter()

    def all_text(self) -> str:
        return "".join(self.text) + "".join(c.all_text() for c in self.children)


_VOID = {"meta", "link", "input", "br", "img", "hr", "source", "col", "area", "wbr"}


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", {})
        self._cur = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, {k: (v or "") for k, v in attrs}, parent=self._cur)
        self._cur.children.append(node)
        if tag not in _VOID:
            self._cur = node

    def handle_endtag(self, tag: str) -> None:
        n: _Node | None = self._cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self._cur = n.parent

    def handle_data(self, data: str) -> None:
        if self._cur.tag not in ("script", "style"):
            self._cur.text.append(data)


def _parse(html: str) -> _Node:
    b = _TreeBuilder()
    b.feed(html)
    return b.root


def _registry_keys(html: str) -> set[str]:
    """Keys of the `_DASH_HELP` object literal, read from the rendered script."""
    start = html.index("var _DASH_HELP = {")
    end = html.index("\n  };", start)
    block = html[start:end]
    return set(re.findall(r"^    (\w+): \{$", block, flags=re.MULTILINE))


def _registry_body(html: str, key: str) -> str:
    """Concatenate the JS string literals of one `_DASH_HELP[key]` entry."""
    start = html.index(f"    {key}: {{")
    end = html.index("\n    },", start)
    lits = re.findall(r"'((?:[^'\\]|\\.)*)'", html[start:end])
    return "".join(lit.replace("\\'", "'") for lit in lits)


# --------------------------------------------------------------------------- tests


class TestEveryTileHasLayLineAndBubble:
    def test_every_tile_on_every_tab_renders(self, populated_page: str) -> None:
        """Guard the fixture itself: the assertion below is only as strong as
        the set of tiles that rendered. 5 Pipeline + 7 Quality + 2 Groundedness
        + 2 Tuning, per the audit's UX-9 count."""
        tiles = [n for n in _parse(populated_page).iter() if "tile" in n.classes]
        assert len(tiles) == 16, [t.attrs.get("data-detail") for t in tiles]

    def test_each_tile_has_lay_line_and_resolving_help(self, populated_page: str) -> None:
        keys = _registry_keys(populated_page)
        tiles = [n for n in _parse(populated_page).iter() if "tile" in n.classes]
        assert tiles
        for tile in tiles:
            name = tile.attrs.get("data-detail")
            lay = [n for n in tile.iter() if "lay" in n.classes]
            assert len(lay) == 1, f"tile {name!r} needs exactly one .lay line"
            assert lay[0].all_text().strip(), f"tile {name!r} has an empty .lay line"
            cell = tile.parent
            assert cell is not None and "tile-cell" in cell.classes, name
            helps = [
                c for c in cell.children if "help-info" in c.classes and c.attrs.get("data-help")
            ]
            assert len(helps) == 1, f"tile {name!r} needs one sibling (i)"
            assert helps[0].attrs["data-help"] in keys, (name, helps[0].attrs["data-help"])
            # Never nested inside the tile <button> (axe nested-interactive).
            assert not any("help-info" in n.classes for n in tile.iter()), name

    def test_every_data_help_on_the_page_resolves(self, populated_page: str) -> None:
        keys = _registry_keys(populated_page)
        used = {
            n.attrs["data-help"]
            for n in _parse(populated_page).iter()
            if n.attrs.get("data-help") and "help-info" in n.classes
        }
        assert used, "no help bubbles found"
        assert used <= keys, used - keys

    def test_help_icon_labels_match_registry_titles(self, populated_page: str) -> None:
        """The UX consistency check (the (i)'s accessible name == the modal title)
        holds for every static bubble, not just the five tab-level ones."""
        for n in _parse(populated_page).iter():
            key = n.attrs.get("data-help")
            if not key or "help-info" not in n.classes:
                continue
            start = populated_page.index(f"    {key}: {{")
            m = re.search(r"title: '((?:[^'\\]|\\.)*)'", populated_page[start:])
            assert m, key
            assert n.attrs.get("aria-label") == "Help: " + m.group(1), key


class TestModulesHaveBubbles:
    """Non-tile modules (UX-9 "every module"; UX-10/13/14..20/42)."""

    @pytest.mark.parametrize(
        "key",
        [
            "dashFilters",  # UX-13
            "dashPercentiles",  # UX-10
            "dashEvalRun",  # Quality's Run eval module
            "dashTuneRun",  # UX-42
            "dashFixtureSlug",  # UX-15
            "dashBootstrapRun",  # UX-14/20
            "dashFixturePicker",  # step ②
            "dashAnnFields",  # UX-17
            "dashCollate",  # UX-19
            "dashAnnScore",  # UX-18
            "dashGroundingSignals",  # UX-16
        ],
    )
    def test_module_bubble_present(self, populated_page: str, key: str) -> None:
        assert f'data-help="{key}"' in populated_page
        assert key in _registry_keys(populated_page)

    def test_collate_run_bubble_is_registered(self, populated_page: str) -> None:
        """'Run this fixture' is built by JS after a Collate, so its (i) is not in
        the static markup — but its entry must exist and its opener be exposed."""
        assert "dashCollateRun" in _registry_keys(populated_page)
        assert "window.sartorDashHelp = { open: openDashHelp };" in populated_page


class TestCopyContent:
    def test_filters_say_what_they_scope(self, populated_page: str) -> None:
        """UX-13: the scope note sits next to the filters, and the blank option
        reads 'All' rather than an empty string."""
        root = _parse(populated_page)
        note = next(n for n in root.iter() if n.attrs.get("id") == "filterScope")
        assert "Pipeline" in note.all_text()
        blanks = [
            n.all_text().strip()
            for n in root.iter()
            if n.tag == "option"
            and n.attrs.get("value") == ""
            and n.parent is not None
            and n.parent.attrs.get("name") in ("user", "model")
        ]
        assert blanks == ["All users", "All models"]

    def test_quality_tiles_have_no_unglossed_raw_names(self, populated_page: str) -> None:
        """UX-11 acceptance: no raw file or schema field name in a Quality tile."""
        root = _parse(populated_page)
        pane = next(
            n for n in root.iter() if n.attrs.get("data-pane") == "quality" and n.tag == "section"
        )
        tiles = [n for n in pane.iter() if "tile" in n.classes]
        assert len(tiles) == 7
        for tile in tiles:
            text = tile.all_text()
            for raw in (
                "baseline_v1.json",
                "failed_rules",
                "prompt_version",
                "eval_composite",
                "≥2",
            ):
                assert raw not in text, (tile.attrs.get("data-detail"), raw)

    def test_groundedness_copy_has_no_metric_internal_terms(self, populated_page: str) -> None:
        """UX-21: no 'grounding box', 'source union' or bare 'L0' jargon on the tab
        or in its explainer."""
        root = _parse(populated_page)
        pane = next(
            n
            for n in root.iter()
            if n.attrs.get("data-pane") == "groundedness" and n.tag == "section"
        )
        detail = next(
            n
            for n in root.iter()
            if n.attrs.get("data-detail") == "groundedness" and "detail" in n.classes
        )
        body = _registry_body(populated_page, "dashGroundedness")
        for text in (pane.all_text(), detail.all_text(), body):
            assert "grounding box" not in text
            assert "source union" not in text
            assert not re.search(r"\bL0\b", text)

    def test_bootstrap_states_no_confirm_and_has_live_estimate(self, populated_page: str) -> None:
        """UX-14: the no-cost-confirm warning is on screen, and the live estimate
        element exists (its JS fills it from the filled JD rows)."""
        root = _parse(populated_page)
        warn = next(n for n in root.iter() if n.attrs.get("id") == "bsNoConfirm")
        text = warn.all_text().lower()
        assert "no confirmation" in text
        assert "only spend control" in text
        assert any(n.attrs.get("id") == "bsSpend" for n in root.iter())
        assert "function updateBsSpend()" in populated_page

    def test_slug_copy_no_longer_claims_reuse_adds_jds(self, populated_page: str) -> None:
        """UX-15: the old hover copy said reusing a slug adds JDs to the fixture;
        each run actually writes its own bootstrap-<ts>.json (diagnostics.py
        _new_bootstrap_path). The false claim is gone and the real one is on screen."""
        root = _parse(populated_page)
        slug = next(n for n in root.iter() if n.attrs.get("id") == "bsSlug")
        assert "add more JDs" not in slug.attrs.get("title", "")
        assert "does not add JDs" in slug.attrs.get("title", "")
        guide = next(n for n in root.iter() if n.attrs.get("id") == "bsSlugGuide")
        assert "new, separate" in guide.all_text()

    def test_forbidden_pattern_guide_has_worked_regex_examples(self, populated_page: str) -> None:
        """UX-17: at least one worked regex example, and each on-screen example
        compiles (validate_annotations would refuse one that doesn't)."""
        root = _parse(populated_page)
        guide = next(n for n in root.iter() if n.attrs.get("id") == "annFieldGuide")
        examples = [
            n.all_text()
            for n in guide.iter()
            if n.tag == "code" and any(ch in n.all_text() for ch in "[]|\\")
        ]
        assert len(examples) >= 3, examples
        for ex in examples:
            re.compile(ex)


class TestEscHelper:
    def test_esc_escapes_both_quote_characters(self, populated_page: str) -> None:
        """Epic-close fix (R2-3): `esc()` feeds attribute values (the waterfall row's
        `title="..."`), where textContent->innerHTML alone leaves quotes raw and a
        quote-bearing call_kind/error_message would break out of the attribute. No
        JS engine runs here, so this pins the escaping in the helper's own source:
        deleting either `.replace(...)` fails it."""
        match = re.search(r"function esc\(s\) \{(.*?)\n  \}", populated_page, re.S)
        assert match, "esc() helper not found in the rendered console"
        body = match.group(1)
        assert ".replace(/\"/g, '&quot;')" in body
        assert ".replace(/'/g, '&#39;')" in body
        assert "d.textContent =" in body and "d.innerHTML" in body
