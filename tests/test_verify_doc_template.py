"""Tests for scripts/verify_doc_template.py's pure validation logic."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.verify_doc_template import (
    Heading,
    append_ledger_event,
    check_verbatim,
    fingerprint,
    heading_pattern,
    latest_generated_fingerprint,
    match_headings,
    parse_headings,
    read_ledger,
    required_headings,
    validate,
    verbatim_sections,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

_TEMPLATE = """# Template title

## Documents to read
<!-- verbatim -->
Read AGENTS.md first.
Read the failure patterns doc.

## What just landed on `<!-- base-branch -->`

<!-- fill in per branch -->

## Binding rules
<!-- verbatim -->
1. Evidence before mechanism.
2. Durable before deep.
"""

_WELL_FORMED_DOC = (
    "# B06 handoff\n\n"
    "## Documents to read\n"
    "Read AGENTS.md first.\n"
    "Read the failure patterns doc.\n\n"
    "## What just landed on `main`\n\ncommit abc123\n\n"
    "## Binding rules\n"
    "1. Evidence before mechanism.\n"
    "2. Durable before deep.\n"
)


class TestParseHeadings:
    def test_extracts_headings_with_level_and_text(self) -> None:
        headings = parse_headings(_TEMPLATE)
        assert headings[0] == Heading(level=1, text="Template title", line=0)
        assert headings[1].text == "Documents to read"
        assert headings[1].level == 2

    def test_skips_headings_inside_fenced_code_blocks(self) -> None:
        content = "# Real heading\n\n```\n# Not a heading\n```\n\n## Also real\n"
        headings = parse_headings(content)
        assert [h.text for h in headings] == ["Real heading", "Also real"]


class TestHeadingPattern:
    def test_literal_text_matches_itself_only(self) -> None:
        pattern = heading_pattern("Documents to read")
        assert pattern.match("Documents to read")
        assert not pattern.match("Documents to read more")

    def test_placeholder_span_matches_anything(self) -> None:
        pattern = heading_pattern("What just landed on `<!-- base-branch -->`")
        assert pattern.match("What just landed on `main`")
        assert pattern.match("What just landed on `b06-freshrss`")
        assert not pattern.match("What just landed on nothing at all")


class TestRequiredHeadings:
    def test_excludes_the_title_heading(self) -> None:
        required = required_headings(parse_headings(_TEMPLATE))
        assert all(h.level >= 2 for h in required)
        assert "Template title" not in [h.text for h in required]


class TestMatchHeadings:
    def test_matches_headings_present_in_order(self) -> None:
        template_headings = required_headings(parse_headings(_TEMPLATE))
        doc_headings = parse_headings(_WELL_FORMED_DOC)
        matches, errors = match_headings(template_headings, doc_headings)
        assert errors == []
        assert all(m is not None for m in matches)

    def test_reports_missing_headings(self) -> None:
        template_headings = required_headings(parse_headings(_TEMPLATE))
        doc = (
            "# B06 handoff\n\n## Documents to read\n"
            "Read AGENTS.md first.\nRead the failure patterns doc.\n"
        )
        doc_headings = parse_headings(doc)
        _matches, errors = match_headings(template_headings, doc_headings)
        assert len(errors) == 2
        assert any("What just landed" in e for e in errors)
        assert any("Binding rules" in e for e in errors)

    def test_reports_out_of_order_heading(self) -> None:
        template_headings = required_headings(parse_headings(_TEMPLATE))
        # "Binding rules" appears before "What just landed" -- out of order.
        doc = (
            "# B06 handoff\n\n"
            "## Documents to read\nRead AGENTS.md first.\nRead the failure patterns doc.\n\n"
            "## Binding rules\n1. Evidence before mechanism.\n2. Durable before deep.\n\n"
            "## What just landed on `main`\n\n"
        )
        doc_headings = parse_headings(doc)
        _matches, errors = match_headings(template_headings, doc_headings)
        assert any("Binding rules" in e for e in errors)


class TestVerbatimSections:
    def test_extracts_body_after_marker(self) -> None:
        headings = parse_headings(_TEMPLATE)
        sections = verbatim_sections(_TEMPLATE, headings)
        assert sections[1] == "Read AGENTS.md first.\nRead the failure patterns doc."

    def test_skips_sections_without_marker(self) -> None:
        headings = parse_headings(_TEMPLATE)
        sections = verbatim_sections(_TEMPLATE, headings)
        assert 2 not in sections


class TestCheckVerbatim:
    def test_byte_identical_section_passes(self) -> None:
        template_headings = required_headings(parse_headings(_TEMPLATE))
        doc_headings = parse_headings(_WELL_FORMED_DOC)
        matches, _errors = match_headings(template_headings, doc_headings)
        errors = check_verbatim(
            _WELL_FORMED_DOC, _TEMPLATE, template_headings, doc_headings, matches
        )
        assert errors == []

    def test_modified_verbatim_section_fails(self) -> None:
        template_headings = required_headings(parse_headings(_TEMPLATE))
        doc = (
            "# B06 handoff\n\n"
            "## Documents to read\n"
            "Read AGENTS.md first.\n\n"  # dropped the second line -- corruption
            "## What just landed on `main`\n\ncommit abc123\n\n"
            "## Binding rules\n"
            "1. Evidence before mechanism.\n"
            "2. Durable before deep.\n"
        )
        doc_headings = parse_headings(doc)
        matches, _errors = match_headings(template_headings, doc_headings)
        errors = check_verbatim(doc, _TEMPLATE, template_headings, doc_headings, matches)
        assert len(errors) == 1
        assert "Documents to read" in errors[0]

    def test_trailing_whitespace_is_ignored(self) -> None:
        template_headings = required_headings(parse_headings(_TEMPLATE))
        doc = _WELL_FORMED_DOC.replace("Read AGENTS.md first.", "Read AGENTS.md first.   ")
        doc_headings = parse_headings(doc)
        matches, _errors = match_headings(template_headings, doc_headings)
        errors = check_verbatim(doc, _TEMPLATE, template_headings, doc_headings, matches)
        assert errors == []


class TestValidate:
    def test_well_formed_doc_has_no_errors(self) -> None:
        assert validate(_WELL_FORMED_DOC, _TEMPLATE) == []

    def test_missing_sections_are_all_reported(self) -> None:
        # Two headings missing entirely, plus the present "Documents to read"
        # section is itself truncated (missing its second verbatim line) --
        # three independent errors, none masking another.
        doc = "# B06 handoff\n\n## Documents to read\nRead AGENTS.md first.\n"
        errors = validate(doc, _TEMPLATE)
        assert len(errors) == 3


class TestFingerprint:
    def test_returns_12_char_hex_and_is_stable(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("hello world", encoding="utf-8")
        fp = fingerprint(doc)
        assert len(fp) == 12
        assert fp == fingerprint(doc)

    def test_changes_when_content_changes(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("hello world", encoding="utf-8")
        before = fingerprint(doc)
        doc.write_text("hello world!", encoding="utf-8")
        assert fingerprint(doc) != before

    def test_crlf_and_lf_checkouts_of_the_same_content_match(self, tmp_path: Path) -> None:
        # Regression: a Windows checkout with core.autocrlf=true rewrites a git
        # blob's LF endings to CRLF on disk. The fingerprint must be blind to
        # that, or a doc validated at generation time on one checkout style
        # spuriously "changes" when read back on the other.
        lf_doc = tmp_path / "lf.md"
        crlf_doc = tmp_path / "crlf.md"
        lf_doc.write_bytes(b"line one\nline two\n")
        crlf_doc.write_bytes(b"line one\r\nline two\r\n")
        assert fingerprint(lf_doc) == fingerprint(crlf_doc)


class TestLedger:
    def test_append_then_read_round_trips(self, tmp_path: Path) -> None:
        ledger_dir = tmp_path / "ledger"
        record = {
            "event": "generated",
            "doc": "docs/dev/handoffs/b06.md",
            "session": "sess-1",
            "branch": "b06-freshrss",
            "commit": "abc1234",
            "actor": "Cooksey",
            "agent": "anthropic/claude-sonnet-5",
            "ts": "2026-07-18T00:00:00Z",
            "fingerprint": "deadbeef0000",
        }
        append_ledger_event(ledger_dir, "sess-1", record)
        assert read_ledger(ledger_dir) == [record]

    def test_shards_by_session(self, tmp_path: Path) -> None:
        ledger_dir = tmp_path / "ledger"
        append_ledger_event(ledger_dir, "sess-a", {"event": "generated", "doc": "x.md", "ts": "t"})
        append_ledger_event(ledger_dir, "sess-b", {"event": "consumed", "doc": "x.md", "ts": "t"})
        shard_names = sorted(p.name for p in ledger_dir.glob("*.jsonl"))
        assert shard_names == ["sess-a.jsonl", "sess-b.jsonl"]
        assert len(read_ledger(ledger_dir)) == 2

    def test_missing_ledger_dir_returns_empty(self, tmp_path: Path) -> None:
        assert read_ledger(tmp_path / "does-not-exist") == []

    def test_appended_shard_bytes_are_lf_only(self, tmp_path: Path) -> None:
        """**The RED for the CRLF ledger class (fix/n1-invoker-context-budget).**

        `append_ledger_event` opened the shard in text mode with no `newline=` argument,
        so on Windows every appended row's `\\n` was translated to CRLF in the WORKING
        TREE. Observed live: this very branch's session shard carried 1 CR byte written
        by `--event consumed` (dossier: docs/dev/diagnosis/n1-invoker-context-budget.md).
        """
        ledger_dir = tmp_path / "ledger"
        append_ledger_event(ledger_dir, "sess-lf", {"event": "generated", "doc": "x.md", "ts": "t"})
        raw = (ledger_dir / "sess-lf.jsonl").read_bytes()
        assert b"\r" not in raw, f"appended ledger row carries CR bytes: {raw!r}"


def _cr_offenders(paths: list[Path]) -> list[str]:
    """Return the ledger shards whose WORKING-TREE bytes contain a CR.

    Deliberately a local mirror of tests/test_n1_pipeline.py::_cr_offenders rather than a
    cross-test-module import — same two lines, no coupling between test modules.
    """
    return [p.name for p in paths if b"\r" in p.read_bytes()]


class TestLedgerWorkingTreeBytes:
    """fix/n1-invoker-context-budget: the CRLF class is a WORKING-TREE defect.

    Mirrors tests/test_n1_pipeline.py::TestWorkflowWorkingTreeBytes (S3), widened to the
    provenance-ledger shards: `.gitattributes` pins `*.jsonl` at CHECKOUT, but both
    ledger writers append AFTER checkout, and until this branch they emitted platform
    line endings — a shard carried CR bytes in the working tree on three separate
    sessions (2026-08-13 ×2, 2026-08-14) while every committed blob was clean. This
    sweep makes the class fail closed in the gate's pytest step instead of surfacing as
    unexplained working-tree drift during a pipeline run's step-6 assertion.
    """

    def test_checker_flags_synthetic_cr(self, tmp_path: Path) -> None:
        crlf = tmp_path / "crlf.jsonl"
        crlf.write_bytes(b'{"event": "compacted"}\r\n')
        clean = tmp_path / "clean.jsonl"
        clean.write_bytes(b'{"event": "compacted"}\n')
        assert _cr_offenders([crlf, clean]) == ["crlf.jsonl"], (
            "the checker itself must flag a CR byte -- if this fails, the "
            "real-tree assertion below proves nothing"
        )

    def test_ledger_shards_are_cr_free_in_the_working_tree(self) -> None:
        shards = sorted((_REPO_ROOT / "docs" / "dev" / "ledger").glob("*.jsonl"))
        assert shards, "no ledger shards found -- the glob itself is broken"
        offenders = _cr_offenders(shards)
        assert offenders == [], (
            f"CR bytes in working-tree ledger shard(s) {offenders}: a ledger writer is "
            "emitting platform line endings again (see "
            "docs/dev/diagnosis/n1-invoker-context-budget.md). Fix the writer, then "
            "re-normalize the shard bytes (\\r\\n -> \\n; content is unchanged)."
        )


_LEDGER_APPEND_WRITERS = {
    "scripts/enforcement/adapters/claude_context_hook.py",
    "scripts/verify_doc_template.py",
    "hooks/lib/retire-approved-plan.sh",
}


def _append_open_args(text: str) -> list[str]:
    """Arg text of every append-mode open() call in `text`.

    `[^)]*` spans newlines, so a call broken across lines is matched whole -- which
    matters, because the writer this check was authored for is formatted that way.
    """
    return [
        m.group(1)
        for m in re.finditer(r"\bopen\(([^)]*)\)", text)
        if re.search(r"""["']a["']""", m.group(1))
    ]


def _discover_ledger_appenders() -> set[str]:
    found = set()
    for sub, patterns in (("scripts", ("*.py",)), ("hooks", ("*.sh", "*.py"))):
        for pattern in patterns:
            for path in (_REPO_ROOT / sub).rglob(pattern):
                text = path.read_text(encoding="utf-8", errors="replace")
                if "ledger" in text and _append_open_args(text):
                    found.add(path.relative_to(_REPO_ROOT).as_posix())
    return found


class TestLedgerWritersPinLf:
    """The WRITER-side half of the CRLF class -- fifth instance, run-6 preflight.

    TestLedgerWorkingTreeBytes above catches a shard that already carries CR bytes.
    It cannot stop a NEW writer from shipping without `newline="\\n"`, which is
    exactly how the class recurred: the fix that covered the two Python writers
    missed `hooks/lib/retire-approved-plan.sh`, whose `plan-archived` receipt put a
    CR byte in a fresh session's shard and would have failed gate #1 mid-run.

    Curated list + discovery scan, mirroring the egress-allowlist dual check: the
    list alone rots silently, the scan alone cannot say which writers are known.
    """

    def test_matcher_finds_a_synthetic_append_open(self) -> None:
        multiline = 'x.open(\n    "a", encoding="utf-8", newline="\\n"\n)'
        assert _append_open_args(multiline), (
            "the matcher must find a call broken across lines -- if this fails, the "
            "per-writer assertion below passes vacuously"
        )
        assert _append_open_args('x.open("r", encoding="utf-8")') == [], (
            "the matcher must ignore read-mode opens"
        )

    def test_every_known_ledger_writer_pins_lf(self) -> None:
        for rel in sorted(_LEDGER_APPEND_WRITERS):
            path = _REPO_ROOT / rel
            assert path.exists(), f"{rel} is on the ledger-writer list but does not exist"
            calls = _append_open_args(path.read_text(encoding="utf-8"))
            assert calls, (
                f"no append-mode open() found in {rel} -- either the writer moved or "
                "the matcher broke; a silent zero here is a vacuous pass"
            )
            for args in calls:
                assert 'newline="\\n"' in args, (
                    f'{rel} appends in text mode without newline="\\n": on Windows '
                    "that translates \\n to \\r\\n and puts CR bytes in the working "
                    "tree, which TestLedgerWorkingTreeBytes then fails the gate on."
                )

    def test_no_unregistered_ledger_appender(self) -> None:
        discovered = _discover_ledger_appenders()
        unregistered = discovered - _LEDGER_APPEND_WRITERS
        assert unregistered == set(), (
            f"new ledger-appending writer(s) {sorted(unregistered)} are not on "
            "_LEDGER_APPEND_WRITERS. Add them to the list AND confirm each passes "
            'newline="\\n" -- an unlisted writer is how this class reached a fifth '
            "instance."
        )


class TestLatestGeneratedFingerprint:
    def test_returns_none_when_no_generated_event(self) -> None:
        assert latest_generated_fingerprint([], "doc.md") is None

    def test_returns_most_recent_by_timestamp(self) -> None:
        records = [
            {
                "doc": "doc.md",
                "event": "generated",
                "ts": "2026-07-17T00:00:00Z",
                "fingerprint": "old",
            },
            {
                "doc": "doc.md",
                "event": "generated",
                "ts": "2026-07-18T00:00:00Z",
                "fingerprint": "new",
            },
            {
                "doc": "other.md",
                "event": "generated",
                "ts": "2026-07-19T00:00:00Z",
                "fingerprint": "irrelevant",
            },
        ]
        assert latest_generated_fingerprint(records, "doc.md") == "new"

    def test_ignores_non_generated_events(self) -> None:
        records = [
            {
                "doc": "doc.md",
                "event": "consumed",
                "ts": "2026-07-19T00:00:00Z",
                "fingerprint": "x",
            },
        ]
        assert latest_generated_fingerprint(records, "doc.md") is None


class TestRealTemplate:
    def test_agent_handoff_template_has_the_four_named_verbatim_sections(self) -> None:
        """Regression bridge to the real template: its own intro paragraph names
        exactly these four sections as copied verbatim into every handoff."""
        template_path = _REPO_ROOT / "docs" / "dev" / "AGENT_HANDOFF_TEMPLATE.md"
        content = template_path.read_text(encoding="utf-8")
        headings = parse_headings(content)
        sections = verbatim_sections(content, headings)
        verbatim_titles = {headings[i].text for i in sections}
        assert verbatim_titles == {
            "Documents to read before any tool call (in this order)",
            "Binding rules — no discretion (copy verbatim — MANDATORY in every handoff)",
            "Hard constraints (copy verbatim — do not shorten)",
            "Branch close-out checklist (do in this order before closing the window)",
        }

    def test_the_c11_recurrence_section_is_required_of_every_handoff(self) -> None:
        """Charter **C-11**'s enforcement (M4), and the reason it is not merely advice.

        `required_headings()` selects every `##`-or-deeper heading with no allowlist, and
        `match_headings()` demands each one be present *in relative order*. So the mere
        presence of this section in the template is what makes a handoff lacking it a hard
        `failed` — no code in `verify_doc_template.py` names it specially, and none needs to.

        Deliberately **not** a `<!-- verbatim -->` section: its content is per-session (what
        recurred, what mechanism was built), not boilerplate to reproduce byte-for-byte.
        What is enforced is that the question gets answered at all.

        **Stated limit (C-0):** this forces the question to be answered. It cannot check the
        answer is true, or that the named mechanism exists.
        """
        template_path = _REPO_ROOT / "docs" / "dev" / "AGENT_HANDOFF_TEMPLATE.md"
        content = template_path.read_text(encoding="utf-8")
        required = required_headings(parse_headings(content))
        titles = [h.text for h in required]
        assert "Recurrences observed this session → guardrail authored" in titles

    def test_a_handoff_missing_the_c11_section_is_rejected(self) -> None:
        """The teeth, asserted directly: strip the section, validation must fail.

        Without this, the test above would only prove the heading exists in the template —
        not that its absence from a handoff is actually caught.
        """
        template_path = _REPO_ROOT / "docs" / "dev" / "AGENT_HANDOFF_TEMPLATE.md"
        template = template_path.read_text(encoding="utf-8")
        # A "handoff" that reproduces the template exactly, minus the C-11 section.
        doc = template.replace("## Recurrences observed this session → guardrail authored", "")
        errors = validate(doc, template)
        assert any("Recurrences observed this session" in e for e in errors), errors
