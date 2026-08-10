"""Tests for scripts/work_items.py's pure parsing, validation, and board logic.

Vendored from spolia's tests/unit/test_work_items.py, plus a `depends_on`
class covering sartor's one schema addition (see docs/dev/work/SCHEMA.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import work_items as work_items_module
from scripts.work_items import (
    Item,
    check,
    check_with_deferral,
    main,
    parse_file,
    render_board,
    structural_errors,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _item_text(
    *,
    schema: int = 1,
    id: int = 1,
    kind: str = "item",
    title: str = "Example item",
    status: str = "open",
    decision_owner: str = "agent",
    summary: str = "An example item.",
    extra: str = "",
    fenced: bool = True,
    body: str = "\nBody prose.\n",
) -> str:
    frontmatter = (
        f"schema = {schema}\n"
        f"id = {id}\n"
        f'kind = "{kind}"\n'
        f'title = "{title}"\n'
        f'status = "{status}"\n'
        f'decision_owner = "{decision_owner}"\n'
        f'summary = "{summary}"\n'
        f"{extra}"
    )
    if not fenced:
        return frontmatter + body
    return f"```toml\n{frontmatter}```\n{body}"


def _write_item(tmp_path: Path, filename: str, text: str) -> Path:
    items_dir = tmp_path / "items"
    items_dir.mkdir(exist_ok=True)
    path = items_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


def _write_open_epic(tmp_path: Path, *, id: int = 36, branch: str = "epic/a-app-core") -> Path:
    """Write a `kind = "epic"`, `status = "open"` item whose `branches` include
    `branch` -- the same string `_write_deferral`'s default `epic` text names --
    so tests exercising the deferral's epic cross-check (`_find_deferral_epic`)
    have a real matching backlog item to point at without re-typing the
    frontmatter each time."""
    text = _item_text(id=id, kind="epic", extra=f'branches = ["{branch}"]\n')
    return _write_item(tmp_path, f"{id:04d}-epic.md", text)


def _write_deferral(
    tmp_path: Path,
    *,
    epic: str | None = "epic/a-app-core",
    declared: str | None = "2026-08-09",
    authorization: str | None = "docs/dev/epic-a-chain-design-corrections.md, section 15.2",
    filename: str = "BOARD_DEFERRAL.md",
    raw: str | None = None,
) -> Path:
    """Write a BOARD_DEFERRAL.md-shaped marker for tests. Passing `raw` writes it
    verbatim (for TOML-syntax/no-fence cases); otherwise a field set to `None` is
    OMITTED from the frontmatter (missing), and any other value is written as-is
    (an empty or whitespace-only string tests the "present but blank" case)."""
    path = tmp_path / filename
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
        return path
    lines = ["```toml"]
    if epic is not None:
        lines.append(f'epic = "{epic}"')
    if declared is not None:
        lines.append(f'declared = "{declared}"')
    if authorization is not None:
        lines.append(f'authorization = "{authorization}"')
    lines.append("```")
    lines.append("")
    lines.append("# Test deferral marker")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _mk_item(
    item_id: int,
    *,
    kind: str = "item",
    title: str = "Title",
    status: str = "open",
    decision_owner: str = "agent",
    summary: str = "summary",
    blocked_on: str | None = None,
    resolution: str | None = None,
    epic: int | None = None,
    depends_on: tuple[int, ...] = (),
    branches: tuple[str, ...] = (),
    refs: tuple[str, ...] = (),
) -> Item:
    return Item(
        path=Path(f"{item_id:04d}-x.md"),
        rel=f"{item_id:04d}-x.md",
        id=item_id,
        kind=kind,
        title=title,
        status=status,
        decision_owner=decision_owner,
        summary=summary,
        blocked_on=blocked_on,
        resolution=resolution,
        epic=epic,
        depends_on=depends_on,
        branches=branches,
        refs=refs,
    )


class TestParseFile:
    def test_valid_item_parses_with_no_errors(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1))
        parsed = parse_file(path)
        assert parsed.errors == []
        assert parsed.item is not None
        assert parsed.item.id == 1
        assert parsed.item.title == "Example item"

    def test_missing_frontmatter_fence_reports_error_and_no_item(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, fenced=False))
        parsed = parse_file(path)
        assert parsed.item is None
        assert any("```toml fenced" in e for e in parsed.errors)

    def test_invalid_toml_reports_error_and_no_item(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", "```toml\nnot = [valid\n```\n")
        parsed = parse_file(path)
        assert parsed.item is None
        assert any("invalid TOML" in e for e in parsed.errors)

    def test_missing_required_field_reports_error(self, tmp_path: Path) -> None:
        text = (
            "```toml\n"
            "schema = 1\n"
            "id = 1\n"
            'kind = "item"\n'
            'status = "open"\n'
            'decision_owner = "agent"\n'
            'summary = "missing title"\n'
            "```\n"
        )
        path = _write_item(tmp_path, "0001-example.md", text)
        parsed = parse_file(path)
        assert parsed.item is None
        assert any("`title`" in e for e in parsed.errors)

    def test_unknown_top_level_key_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(
            tmp_path, "0001-example.md", _item_text(id=1, extra='mystery_field = "x"\n')
        )
        parsed = parse_file(path)
        assert any("unrecognized frontmatter key" in e for e in parsed.errors)

    def test_x_table_is_allowed_and_ignored(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, extra="[x]\nfoo = 1\n"))
        parsed = parse_file(path)
        assert parsed.errors == []
        assert parsed.item is not None

    def test_filename_prefix_mismatch_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0002-example.md", _item_text(id=1))
        parsed = parse_file(path)
        assert any("filename prefix" in e for e in parsed.errors)

    def test_bad_kind_value_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, kind="feature"))
        parsed = parse_file(path)
        assert any("kind must be one of" in e for e in parsed.errors)

    def test_bad_status_value_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, status="paused"))
        parsed = parse_file(path)
        assert any("status must be one of" in e for e in parsed.errors)

    def test_bad_decision_owner_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, decision_owner="robot"))
        parsed = parse_file(path)
        assert any("decision_owner must be one of" in e for e in parsed.errors)

    def test_summary_over_120_chars_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, summary="x" * 121))
        parsed = parse_file(path)
        assert any("exceeds the 120-char cap" in e for e in parsed.errors)

    def test_blocked_status_without_blocked_on_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, status="blocked"))
        parsed = parse_file(path)
        assert any("requires a non-empty `blocked_on`" in e for e in parsed.errors)

    def test_blocked_status_with_blocked_on_passes(self, tmp_path: Path) -> None:
        text = _item_text(id=1, status="blocked", extra='blocked_on = "waiting on design"\n')
        path = _write_item(tmp_path, "0001-example.md", text)
        parsed = parse_file(path)
        assert parsed.errors == []

    def test_deferred_status_without_blocked_on_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, status="deferred"))
        parsed = parse_file(path)
        assert any("requires a non-empty `blocked_on`" in e for e in parsed.errors)

    def test_closed_status_without_resolution_reports_error(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, status="closed"))
        parsed = parse_file(path)
        assert any("requires a non-empty `resolution`" in e for e in parsed.errors)

    def test_watching_status_needs_neither_blocked_on_nor_resolution(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1, status="watching"))
        parsed = parse_file(path)
        assert parsed.errors == []

    def test_epic_must_not_set_epic_field(self, tmp_path: Path) -> None:
        text = _item_text(id=1, kind="epic", extra="epic = 5\n")
        path = _write_item(tmp_path, "0001-example.md", text)
        parsed = parse_file(path)
        assert any("nesting depth 1" in e for e in parsed.errors)

    def test_branches_must_be_a_string_list(self, tmp_path: Path) -> None:
        text = _item_text(id=1, extra="branches = [1, 2]\n")
        path = _write_item(tmp_path, "0001-example.md", text)
        parsed = parse_file(path)
        assert any("`branches` must be a list of strings" in e for e in parsed.errors)

    def test_branches_and_refs_are_captured(self, tmp_path: Path) -> None:
        text = _item_text(id=1, extra='branches = ["chore/example"]\nrefs = ["docs/foo.md"]\n')
        path = _write_item(tmp_path, "0001-example.md", text)
        parsed = parse_file(path)
        assert parsed.item is not None
        assert parsed.item.branches == ("chore/example",)
        assert parsed.item.refs == ("docs/foo.md",)


class TestDependsOn:
    """sartor's one schema addition beyond spolia's vendored shape."""

    def test_depends_on_is_captured(self, tmp_path: Path) -> None:
        path = _write_item(
            tmp_path, "0001-example.md", _item_text(id=1, extra="depends_on = [2, 3]\n")
        )
        parsed = parse_file(path)
        assert parsed.item is not None
        assert parsed.item.depends_on == (2, 3)

    def test_depends_on_defaults_to_empty(self, tmp_path: Path) -> None:
        path = _write_item(tmp_path, "0001-example.md", _item_text(id=1))
        parsed = parse_file(path)
        assert parsed.item is not None
        assert parsed.item.depends_on == ()

    def test_depends_on_must_be_an_integer_list(self, tmp_path: Path) -> None:
        text = _item_text(id=1, extra='depends_on = ["not-an-int"]\n')
        path = _write_item(tmp_path, "0001-example.md", text)
        parsed = parse_file(path)
        assert any("`depends_on` must be a list of integers" in e for e in parsed.errors)

    def test_dangling_depends_on_reports_error(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1, extra="depends_on = [99]\n"))
        _items, errors = structural_errors(tmp_path / "items")
        assert any("depends_on 99 not found" in e for e in errors)

    def test_depends_on_existing_item_passes(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_item(tmp_path, "0002-b.md", _item_text(id=2, extra="depends_on = [1]\n"))
        _items, errors = structural_errors(tmp_path / "items")
        assert errors == []

    def test_depends_on_does_not_gate_closing(self, tmp_path: Path) -> None:
        # depends_on is sequencing information, not a closure gate -- unlike
        # an epic's non-terminal-children rule, an item may close with an
        # unresolved dependency still open.
        _write_item(tmp_path, "0001-a.md", _item_text(id=1, status="open"))
        # `verified_by` satisfies the C-11 closure bar, which is a separate rule from the
        # `depends_on` behaviour under test here — see tests/test_work_items_closure_bar.py.
        text = _item_text(
            id=2,
            status="closed",
            extra='resolution = "done"\nverified_by = ["tests/x.py::test_y"]\ndepends_on = [1]\n',
        )
        _write_item(tmp_path, "0002-b.md", text)
        _items, errors = structural_errors(tmp_path / "items")
        assert errors == []

    def test_depends_on_renders_in_board_line(self) -> None:
        items = {
            1: _mk_item(1, status="open", title="Base"),
            2: _mk_item(2, status="open", title="Follow-on", depends_on=(1,)),
        }
        board = render_board(items)
        open_section = board.split("## Open")[1].split("## Blocked")[0]
        assert "[depends on: 1]" in open_section


class TestStructuralErrors:
    def test_clean_backlog_has_no_errors(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_item(tmp_path, "0002-b.md", _item_text(id=2))
        items, errors = structural_errors(tmp_path / "items")
        assert errors == []
        assert set(items) == {1, 2}

    def test_duplicate_id_reports_both_files(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_item(tmp_path, "0002-b.md", _item_text(id=1))
        _items, errors = structural_errors(tmp_path / "items")
        assert len(errors) >= 1
        assert any(
            "used by multiple files" in e and "0001-a.md" in e and "0002-b.md" in e for e in errors
        )

    def test_dangling_epic_reference_reports_error(self, tmp_path: Path) -> None:
        text = _item_text(id=1, status="deferred", extra='blocked_on = "x"\nepic = 99\n')
        _write_item(tmp_path, "0001-a.md", text)
        _items, errors = structural_errors(tmp_path / "items")
        assert any("epic 99 not found" in e for e in errors)

    def test_epic_pointing_at_non_epic_reports_error(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1, kind="item"))
        text = _item_text(id=2, status="deferred", extra='blocked_on = "x"\nepic = 1\n')
        _write_item(tmp_path, "0002-b.md", text)
        _items, errors = structural_errors(tmp_path / "items")
        assert any('epic 1 is not kind = "epic"' in e for e in errors)

    def test_closed_epic_with_open_child_reports_error(self, tmp_path: Path) -> None:
        text = _item_text(id=1, kind="epic", status="closed", extra='resolution = "done"\n')
        _write_item(tmp_path, "0001-epic.md", text)
        child = _item_text(id=2, status="open", extra="epic = 1\n")
        _write_item(tmp_path, "0002-child.md", child)
        _items, errors = structural_errors(tmp_path / "items")
        assert any("epic is closed but children" in e for e in errors)

    def test_closed_epic_with_all_closed_children_passes(self, tmp_path: Path) -> None:
        text = _item_text(id=1, kind="epic", status="closed", extra='resolution = "done"\n')
        _write_item(tmp_path, "0001-epic.md", text)
        child = _item_text(
            id=2,
            status="closed",
            extra='epic = 1\nresolution = "shipped"\nverified_by = ["tests/x.py::test_y"]\n',
        )
        _write_item(tmp_path, "0002-child.md", child)
        _items, errors = structural_errors(tmp_path / "items")
        assert errors == []


class TestRenderBoard:
    def test_groups_items_by_status(self) -> None:
        items = {
            1: _mk_item(1, status="open", title="Open one"),
            2: _mk_item(2, status="blocked", blocked_on="needs review", title="Blocked one"),
        }
        board = render_board(items)
        open_section = board.split("## Open")[1].split("## Blocked")[0]
        blocked_section = board.split("## Blocked")[1].split("## Deferred")[0]
        assert "Open one" in open_section
        assert "Blocked one" not in open_section
        assert "Blocked one" in blocked_section
        assert "needs review" in blocked_section

    def test_epic_lists_derived_children_not_top_level_groups(self) -> None:
        items = {
            36: _mk_item(36, kind="epic", status="deferred", title="Source epic"),
            89: _mk_item(89, status="deferred", blocked_on="x", epic=36, title="Child A"),
            90: _mk_item(90, status="deferred", blocked_on="x", epic=36, title="Child B"),
        }
        board = render_board(items)
        epics_section = board.split("## Epics")[1].split("## Closed")[0]
        assert "Child A" in epics_section
        assert "Child B" in epics_section
        deferred_section = board.split("## Deferred")[1].split("## Watching")[0]
        assert "Child A" not in deferred_section
        assert "Child B" not in deferred_section

    def test_closed_items_rendered_compactly_and_not_in_open(self) -> None:
        items = {1: _mk_item(1, status="closed", resolution="fixed in b06", title="Closed one")}
        board = render_board(items)
        closed_section = board.split("## Closed")[1]
        assert "Closed one" in closed_section
        assert "fixed in b06" in closed_section
        open_section = board.split("## Open")[1].split("## Blocked")[0]
        assert "Closed one" not in open_section

    def test_open_ceiling_flag_appears_only_when_exceeded(self) -> None:
        under = {i: _mk_item(i, status="open") for i in range(1, 4)}
        over = {i: _mk_item(i, status="open") for i in range(1, 12)}
        under_header = next(
            line for line in render_board(under).splitlines() if line.startswith("**Open")
        )
        over_header = next(
            line for line in render_board(over).splitlines() if line.startswith("**Open")
        )
        assert "OVER" not in under_header
        assert "OVER" in over_header
        assert "Open 11 / 10 ceiling" in over_header

    def test_same_input_produces_identical_output(self) -> None:
        items = {1: _mk_item(1), 2: _mk_item(2, status="closed", resolution="done")}
        assert render_board(items) == render_board(items)


class TestCheck:
    def test_missing_board_reports_error(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        errors = check(tmp_path / "items", tmp_path / "BOARD.md")
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_stale_board_reports_error(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        errors = check(tmp_path / "items", tmp_path / "BOARD.md")
        assert any("stale" in e for e in errors)

    def test_matching_board_passes(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        items, _errors = structural_errors(tmp_path / "items")
        (tmp_path / "BOARD.md").write_text(render_board(items), encoding="utf-8")
        assert check(tmp_path / "items", tmp_path / "BOARD.md") == []

    def test_crlf_board_on_disk_still_matches_lf_generated(self, tmp_path: Path) -> None:
        # Regression: this repo's markdown is CRLF on a Windows checkout
        # (core.autocrlf=true, no *.md rule in .gitattributes) and LF in CI --
        # the comparison must be blind to that, or the check is permanently
        # red in one of the two environments.
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        items, _errors = structural_errors(tmp_path / "items")
        generated = render_board(items)
        (tmp_path / "BOARD.md").write_bytes(generated.replace("\n", "\r\n").encode("utf-8"))
        assert check(tmp_path / "items", tmp_path / "BOARD.md") == []

    def test_structural_errors_short_circuit_the_board_check(self, tmp_path: Path) -> None:
        # A dangling epic reference -- one clean structural error, and nothing
        # about it implies anything about BOARD.md.
        text = _item_text(id=1, status="deferred", extra='blocked_on = "x"\nepic = 99\n')
        _write_item(tmp_path, "0001-a.md", text)
        # No BOARD.md is written at all -- if the board check ran anyway it
        # would pile a second, misleading error on top of the real one.
        errors = check(tmp_path / "items", tmp_path / "BOARD.md")
        assert len(errors) == 1
        assert "epic 99 not found" in errors[0]


class TestRealBacklog:
    def test_committed_backlog_validates_clean(self) -> None:
        """Bridge to the real committed backlog (docs/dev/work/items/), mirroring
        TestRealTemplate-style bridge tests elsewhere in this repo."""
        items, errors = structural_errors(_REPO_ROOT / "docs" / "dev" / "work" / "items")
        assert errors == []
        assert items, "expected the migrated backlog to be non-empty"

    def test_committed_board_is_up_to_date(self) -> None:
        # Mirrors the real CLI (`main()`'s `check` subcommand), which always passes
        # the real BOARD_DEFERRAL.md path -- so this bridge test reflects what
        # `python -m scripts.work_items check` actually does, deferral included.
        # When no deferral is active, this is byte-identical to passing no
        # deferral_path at all: see TestBoardDeferral for that guarantee in
        # isolation.
        errors = check(
            _REPO_ROOT / "docs" / "dev" / "work" / "items",
            _REPO_ROOT / "docs" / "dev" / "work" / "BOARD.md",
            work_items_module._BOARD_DEFERRAL_PATH,
        )
        assert errors == []


class TestBoardDeferral:
    """Charter C-11: a durable, committed, auditable exemption -- never an env var,
    never a second flag to also flip. See docs/dev/work/BOARD_DEFERRAL.md for the
    real, currently-active marker this mechanism was built to satisfy."""

    # --- (a) no-marker behavior is unchanged -- regression-critical ------------------

    def test_no_deferral_path_is_byte_identical_to_pre_deferral_check(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        # check()'s default (deferral_path omitted entirely) must reproduce EXACTLY
        # today's pre-deferral behavior: a stale board still fails, full stop.
        errors = check(tmp_path / "items", tmp_path / "BOARD.md")
        assert any("stale" in e for e in errors)

    def test_absent_marker_file_behaves_like_no_deferral(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        errors, deferral = check_with_deferral(
            tmp_path / "items", tmp_path / "BOARD.md", tmp_path / "does-not-exist.md"
        )
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_cli_check_output_is_plain_ok_without_a_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        items, _errors = structural_errors(tmp_path / "items")
        (tmp_path / "BOARD.md").write_text(render_board(items), encoding="utf-8")
        monkeypatch.setattr(work_items_module, "_ITEMS_DIR", tmp_path / "items")
        monkeypatch.setattr(work_items_module, "_BOARD_PATH", tmp_path / "BOARD.md")
        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", tmp_path / "no-marker.md")
        rc = main(["check"])
        out = capsys.readouterr().out
        assert rc == 0
        assert out.strip() == "work_items: OK (1 files)"

    # --- (b) a valid marker tolerates staleness AND names it unmissably --------------

    def test_valid_marker_tolerates_staleness_and_reports_it(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_open_epic(tmp_path)
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert errors == []
        assert deferral is not None
        assert deferral.epic == "epic/a-app-core"
        assert deferral.declared == "2026-08-09"
        assert "15.2" in deferral.authorization
        assert deferral.path == marker

    def test_check_wrapper_tolerates_with_valid_marker(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_open_epic(tmp_path)
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        assert check(tmp_path / "items", tmp_path / "BOARD.md", marker) == []

    def test_valid_marker_also_tolerates_a_missing_board_file(self, tmp_path: Path) -> None:
        # A missing BOARD.md and a mismatched BOARD.md are both `_board_status`
        # staleness outcomes -- the marker's job is to tolerate BOARD.md staleness
        # broadly, not just the "exists but wrong" sub-case.
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_open_epic(tmp_path)
        marker = _write_deferral(tmp_path)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert errors == []
        assert deferral is not None

    def test_valid_marker_never_tolerates_structural_errors(self, tmp_path: Path) -> None:
        # A dangling epic reference is a structural error -- the marker only ever
        # touches the BOARD.md-staleness rule, never the rules that keep the
        # backlog itself honest.
        text = _item_text(id=1, status="deferred", extra='blocked_on = "x"\nepic = 99\n')
        _write_item(tmp_path, "0001-a.md", text)
        marker = _write_deferral(tmp_path)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("epic 99 not found" in e for e in errors)

    def test_cli_check_output_names_the_deferral_unmissably(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_open_epic(tmp_path)
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        monkeypatch.setattr(work_items_module, "_ITEMS_DIR", tmp_path / "items")
        monkeypatch.setattr(work_items_module, "_BOARD_PATH", tmp_path / "BOARD.md")
        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", marker)
        rc = main(["check"])
        out = capsys.readouterr().out
        assert rc == 0
        # A green run under an active deferral must look visibly different from a
        # genuinely-clean run, in the same line a human or CI would actually read.
        assert "OK" in out
        assert "DEFERRED" in out
        assert "epic/a-app-core" in out
        assert "BOARD_DEFERRAL.md" in out
        assert "NOT actually current" in out

    # --- (c) a malformed/incomplete marker grants NOTHING -- fail closed -------------

    def test_marker_missing_epic_field_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, epic=None)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_marker_missing_authorization_field_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, authorization=None)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_marker_missing_declared_field_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, declared=None)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_empty_marker_file_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, raw="")
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_marker_with_blank_field_grants_nothing(self, tmp_path: Path) -> None:
        # A field present but whitespace-only is still "missing" once stripped --
        # same effective failure as never having set the key.
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, declared="   ")
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_marker_with_invalid_toml_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, raw="```toml\nepic = [unterminated\n```\n")
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_marker_without_toml_fence_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, raw='epic = "x"\ndeclared = "x"\nauthorization = "x"\n')
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)

    def test_malformed_marker_error_output_matches_no_marker_output_exactly(
        self, tmp_path: Path
    ) -> None:
        # The literal requirement: a malformed marker must fail EXACTLY as if no
        # marker existed at all -- not almost, not with extra noise appended.
        # Compare the two error lists for equality rather than substring-matching
        # each independently.
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        no_marker_errors, no_marker_deferral = check_with_deferral(
            tmp_path / "items", tmp_path / "BOARD.md", tmp_path / "absent.md"
        )
        malformed = _write_deferral(tmp_path, epic=None, filename="malformed.md")
        malformed_errors, malformed_deferral = check_with_deferral(
            tmp_path / "items", tmp_path / "BOARD.md", malformed
        )
        assert malformed_errors == no_marker_errors
        assert malformed_deferral is no_marker_deferral is None

    def test_cli_check_output_with_malformed_marker_matches_no_marker_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, authorization=None)
        monkeypatch.setattr(work_items_module, "_ITEMS_DIR", tmp_path / "items")
        monkeypatch.setattr(work_items_module, "_BOARD_PATH", tmp_path / "BOARD.md")
        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", marker)
        rc = main(["check"])
        out, err = capsys.readouterr()
        assert rc == 1
        assert out == ""
        assert "FAILED" in err
        assert "stale" in err
        assert "DEFERRED" not in err

    # --- (d) `board --write` is unaffected by the marker's presence ------------------

    def test_board_write_regenerates_correctly_regardless_of_marker_presence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        monkeypatch.setattr(work_items_module, "_ITEMS_DIR", tmp_path / "items")
        monkeypatch.setattr(work_items_module, "_BOARD_PATH", tmp_path / "BOARD.md")
        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", marker)
        rc = main(["board", "--write"])
        assert rc == 0
        items, _errors = structural_errors(tmp_path / "items")
        assert (tmp_path / "BOARD.md").read_text(encoding="utf-8") == render_board(items)
        # The write made the board genuinely current -- a plain check() with NO
        # deferral_path at all now passes too, independent of the marker's
        # continued presence on disk.
        assert check(tmp_path / "items", tmp_path / "BOARD.md") == []

    def test_board_write_output_unaffected_by_marker_presence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        monkeypatch.setattr(work_items_module, "_ITEMS_DIR", tmp_path / "items")
        monkeypatch.setattr(work_items_module, "_BOARD_PATH", tmp_path / "BOARD.md")

        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", tmp_path / "no-marker.md")
        rc_without_marker = main(["board", "--write"])
        out_without_marker = capsys.readouterr().out
        board_without_marker = (tmp_path / "BOARD.md").read_text(encoding="utf-8")

        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", marker)
        rc_with_marker = main(["board", "--write"])
        out_with_marker = capsys.readouterr().out
        board_with_marker = (tmp_path / "BOARD.md").read_text(encoding="utf-8")

        assert rc_without_marker == rc_with_marker == 0
        assert out_without_marker == out_with_marker
        assert board_without_marker == board_with_marker


class TestDeferralEpicCrossCheck:
    """A well-formed marker used to grant the exemption on prose alone -- `epic`
    is free text nobody verified against real backlog state, so a marker naming
    ANY string passed structurally. This closes that: the named epic must match
    a real `kind = "epic"` item with `status != "closed"` (`_find_deferral_epic`),
    or the marker grants nothing, same as a structurally malformed one -- see
    `TestBoardDeferral` group (c) for that half. Does NOT verify the current
    branch is actually part of the named epic -- deliberately out of scope,
    see the module docstring and docs/dev/work/BOARD_DEFERRAL.md."""

    def test_marker_naming_real_open_epic_grants_deferral(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_open_epic(tmp_path)
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        deferral = work_items_module._read_board_deferral(marker)
        assert deferral is not None
        items, errors = structural_errors(tmp_path / "items")
        assert errors == []
        matched, error = work_items_module._find_deferral_epic(deferral, items)
        assert error is None
        assert matched is not None
        assert matched.id == 36

    def test_marker_naming_real_closed_epic_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        text = _item_text(
            id=36,
            kind="epic",
            status="closed",
            extra=(
                'resolution = "done"\n'
                'verified_by = ["tests/x.py::test_y"]\n'
                'branches = ["epic/a-app-core"]\n'
            ),
        )
        _write_item(tmp_path, "0036-epic.md", text)
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)
        assert any("matches backlog item 36" in e and 'status = "closed"' in e for e in errors)
        # Distinct from the malformed-marker message -- a fixer needs to know
        # WHICH problem this is.
        assert not any("does not open with" in e or "invalid TOML" in e for e in errors)

    def test_marker_naming_nonexistent_epic_grants_nothing(self, tmp_path: Path) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        # No epic item at all in this backlog -- the marker's claim is unfounded.
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, epic="epic/does-not-exist-anywhere")
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("stale" in e for e in errors)
        assert any(
            'no `kind = "epic"` item' in e and "not a real backlog item" in e for e in errors
        )

    def test_marker_naming_epic_string_that_is_only_a_substring_of_a_real_branch_fails(
        self, tmp_path: Path
    ) -> None:
        # The match direction is branch-in-marker, not marker-in-branch -- a marker
        # cannot claim a shorter, vaguer string and have it match a longer real
        # branch name it merely happens to prefix.
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        _write_open_epic(tmp_path, branch="epic/a-app-core-and-then-some")
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path, epic="epic/a-app-core")
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("not a real backlog item" in e for e in errors)

    def test_structural_errors_still_short_circuit_before_the_epic_check(
        self, tmp_path: Path
    ) -> None:
        # A dangling epic reference on an unrelated item is a structural error --
        # it must fail there, never reach board staleness or the epic cross-check.
        text = _item_text(id=1, status="deferred", extra='blocked_on = "x"\nepic = 99\n')
        _write_item(tmp_path, "0001-a.md", text)
        marker = _write_deferral(tmp_path, epic="epic/does-not-exist-anywhere")
        errors, deferral = check_with_deferral(tmp_path / "items", tmp_path / "BOARD.md", marker)
        assert deferral is None
        assert any("epic 99 not found" in e for e in errors)
        assert not any("not a real backlog item" in e for e in errors)

    def test_cli_check_output_distinguishes_closed_epic_from_malformed_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_item(tmp_path, "0001-a.md", _item_text(id=1))
        text = _item_text(
            id=36,
            kind="epic",
            status="closed",
            extra=(
                'resolution = "done"\n'
                'verified_by = ["tests/x.py::test_y"]\n'
                'branches = ["epic/a-app-core"]\n'
            ),
        )
        _write_item(tmp_path, "0036-epic.md", text)
        (tmp_path / "BOARD.md").write_text("stale content", encoding="utf-8")
        marker = _write_deferral(tmp_path)
        monkeypatch.setattr(work_items_module, "_ITEMS_DIR", tmp_path / "items")
        monkeypatch.setattr(work_items_module, "_BOARD_PATH", tmp_path / "BOARD.md")
        monkeypatch.setattr(work_items_module, "_BOARD_DEFERRAL_PATH", marker)
        rc = main(["check"])
        out, err = capsys.readouterr()
        assert rc == 1
        assert out == ""
        assert "FAILED" in err
        assert "stale" in err
        assert 'status = "closed"' in err
        assert "DEFERRED" not in err


class TestRealBacklogDeferralEpic:
    """Bridge test: WHEN `BOARD_DEFERRAL.md` is active, confirm it names Epic A
    (item 36) as a real `kind = "epic"` item with a non-closed status, so the
    stronger check does not silently defeat the live deferral it was built to
    keep working. The marker is a deliberately temporary mechanism -- absent
    is this repo's normal steady state whenever no chain epic has declared a
    deferral -- so `test_real_deferral_marker_names_epic_a_and_verifies` skips
    when there is no marker to bridge-test; it never asserted "a marker must
    exist," only "IF one exists, it must be honest." `test_epic_a_item_is_a_real_open_epic`
    below is unconditional: it checks item 36's own state directly and never
    touches the marker file, so it is unaffected either way."""

    def test_epic_a_item_is_a_real_open_epic(self) -> None:
        items, errors = structural_errors(_REPO_ROOT / "docs" / "dev" / "work" / "items")
        assert errors == []
        epic_a = items[36]
        assert epic_a.kind == "epic"
        assert epic_a.status != "closed"

    def test_real_deferral_marker_names_epic_a_and_verifies(self) -> None:
        # This bridge test only ever validated "a *currently-active* marker is
        # well-formed and names a real, open epic" -- the mechanism's real
        # behavior (fixture-based malformed/missing/closed-epic/etc. cases) is
        # already covered by `TestBoardDeferral` and `TestDeferralEpicCrossCheck`
        # above, which don't touch the real filesystem. With no active marker
        # there is nothing here to validate: `BOARD_DEFERRAL.md` is expected to
        # be ABSENT whenever no chain epic has declared a deferral -- that is
        # this repo's normal steady state (see the marker's own "Removal"
        # section, and `docs/dev/epic-a-chain-design-corrections.md` §15.2 for
        # why it existed at all) -- so skip rather than fail when it's gone.
        if not work_items_module._BOARD_DEFERRAL_PATH.is_file():
            pytest.skip("no active BOARD_DEFERRAL.md marker -- nothing to bridge-test right now")
        items, errors = structural_errors(_REPO_ROOT / "docs" / "dev" / "work" / "items")
        assert errors == []
        deferral = work_items_module._read_board_deferral(work_items_module._BOARD_DEFERRAL_PATH)
        assert deferral is not None, "the real BOARD_DEFERRAL.md is expected to be well-formed"
        matched, error = work_items_module._find_deferral_epic(deferral, items)
        assert error is None
        assert matched is not None
        assert matched.id == 36
