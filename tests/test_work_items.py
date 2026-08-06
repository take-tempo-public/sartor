"""Tests for scripts/work_items.py's pure parsing, validation, and board logic.

Vendored from spolia's tests/unit/test_work_items.py, plus a `depends_on`
class covering sartor's one schema addition (see docs/dev/work/SCHEMA.md).
"""

from __future__ import annotations

from pathlib import Path

from scripts.work_items import (
    Item,
    check,
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
        errors = check(
            _REPO_ROOT / "docs" / "dev" / "work" / "items",
            _REPO_ROOT / "docs" / "dev" / "work" / "BOARD.md",
        )
        assert errors == []
