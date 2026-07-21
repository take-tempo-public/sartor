"""Unit tests for the `ux` tier's rerun-rate alarm rendering (`tests/ux/rerun_report.py`).

Exercises the pure helpers directly with plain data — no pytest session, no browser, no
`tests/ux/conftest.py` fixtures. Deliberately placed at top level rather than under `tests/ux/`:
that directory's `_help_welcome_default_seen` fixture is `autouse=True` and requests the `page`
fixture (`_browser` -> a real Chromium launch), so any test collected there pays that cost
regardless of whether it uses a browser. A pure-function test earns none of that.
"""

from __future__ import annotations

from tests.ux.rerun_report import MAX_ATTEMPTS, render_annotations, render_step_summary


def test_no_reruns_renders_nothing() -> None:
    assert render_step_summary([]) == ""
    assert render_annotations([]) == []


def test_single_rerun_step_summary_has_test_and_count() -> None:
    summary = render_step_summary([("tests/ux/regression/test_x.py::test_add_title", 1)])
    assert "1 test needed a retry" in summary
    assert f"tests/ux/regression/test_x.py::test_add_title` | 1 of {MAX_ATTEMPTS} |" in summary


def test_multiple_reruns_step_summary_lists_every_test() -> None:
    reruns = [
        ("tests/ux/regression/test_a.py::test_one", 1),
        ("tests/ux/regression/test_b.py::test_two", 2),
    ]
    summary = render_step_summary(reruns)
    assert "2 tests needed a retry" in summary
    assert "test_a.py::test_one` | 1 of 3 |" in summary
    assert "test_b.py::test_two` | 2 of 3 |" in summary


def test_near_miss_two_of_three_is_reported_plainly() -> None:
    """Mirrors the real `8326b5e` near-miss from the step-14 CI investigation: 2 of the 3
    attempts failed and the test still passed overall (not silently, per this report's whole
    purpose) — `docs/dev/RELEASE_CHECKLIST.md` ledger item 1."""
    summary = render_step_summary(
        [("tests/ux/regression/test_scroll.py::test_corpus_reload_preserves_scroll_position", 2)]
    )
    assert "2 of 3 |" in summary


def test_annotations_one_warning_per_test() -> None:
    reruns = [
        ("tests/ux/regression/test_a.py::test_one", 1),
        ("tests/ux/regression/test_b.py::test_two", 2),
    ]
    annotations = render_annotations(reruns)
    assert len(annotations) == 2
    assert all(line.startswith("::warning title=UX rerun::") for line in annotations)
    assert "test_a.py::test_one" in annotations[0]
    assert "1 of 3 attempts failed" in annotations[0]
    assert "test_b.py::test_two" in annotations[1]
    assert "2 of 3 attempts failed" in annotations[1]


def test_annotation_never_a_github_error_command() -> None:
    """The alarm must never fail the build (option (a) is report-only, not option (b)) —
    a stray `::error::` would be interpreted by GitHub as a build-affecting annotation in
    spirit even though it doesn't touch exit status; assert we only ever emit `::warning::`."""
    annotations = render_annotations([("tests/ux/regression/test_a.py::test_one", 1)])
    assert all("::error::" not in line for line in annotations)


def test_nodeid_with_percent_is_escaped_in_annotation() -> None:
    """GitHub workflow-command data fields need `%` escaped first (before `\\r`/`\\n`) so a
    literal percent in a nodeid can't be misread as the start of another escape sequence."""
    annotations = render_annotations([("tests/ux/regression/test_a.py::test_100%_done", 1)])
    assert "%25_done" in annotations[0]
