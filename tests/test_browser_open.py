"""Tests for the auto-open-browser guard (`app._should_open_browser`).

Regression coverage for the v1.0.7 "stray windows" bug: under Flask's debug
reloader, `main()` runs in a persistent supervisor (WERKZEUG_RUN_MAIN unset)
AND a serving child that is re-executed on every reload (WERKZEUG_RUN_MAIN ==
"true"). The browser must open exactly once — in the supervisor / single
process, never in the restart-prone child.
"""

from __future__ import annotations

from app import _should_open_browser


def test_supervisor_opens_once() -> None:
    # Debug-mode reloader supervisor: WERKZEUG_RUN_MAIN unset → opens (once,
    # the supervisor persists across child restarts).
    assert _should_open_browser(None, None) is True


def test_reload_child_does_not_open() -> None:
    # The serving child re-runs main() on every reload; it must NOT re-pop a
    # window. This is the stray-windows fix.
    assert _should_open_browser("true", None) is False


def test_non_debug_single_process_opens() -> None:
    # No reloader → single process, WERKZEUG_RUN_MAIN unset → opens once.
    assert _should_open_browser(None, None) is True


def test_no_browser_optout_never_opens() -> None:
    # CALLBACK_NO_BROWSER=1 wins regardless of process role.
    assert _should_open_browser(None, "1") is False
    assert _should_open_browser("true", "1") is False
