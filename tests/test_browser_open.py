"""Tests for the auto-open-browser guard (`app._should_open_browser`) and the
F-18 CI/container default detection (`app._is_ci_or_container`).

Regression coverage for the v1.0.7 "stray windows" bug: under Flask's debug
reloader, `main()` runs in a persistent supervisor (WERKZEUG_RUN_MAIN unset)
AND a serving child that is re-executed on every reload (WERKZEUG_RUN_MAIN ==
"true"). The browser must open exactly once — in the supervisor / single
process, never in the restart-prone child.
"""

from __future__ import annotations

import os

import pytest

from app import _is_ci_or_container, _should_open_browser


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
    # SARTOR_NO_BROWSER=1 wins regardless of process role.
    assert _should_open_browser(None, "1") is False
    assert _should_open_browser("true", "1") is False


# ---- F-18: _is_ci_or_container (the dev-default off-switch main() consults
# only when SARTOR_NO_BROWSER/FLASK_DEBUG are BOTH unset — see main()). ----


def test_ci_env_truthy_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(os.path, "exists", lambda _p: False)
    assert _is_ci_or_container() is True


def test_ci_env_numeric_truthy_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    # Some CI providers set CI=1 rather than CI=true.
    monkeypatch.setenv("CI", "1")
    monkeypatch.setattr(os.path, "exists", lambda _p: False)
    assert _is_ci_or_container() is True


def test_ci_env_explicit_false_not_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    # CI=false / CI=0 is a deliberate "no" some tools set — not a CI signal.
    monkeypatch.setenv("CI", "false")
    monkeypatch.setattr(os.path, "exists", lambda _p: False)
    assert _is_ci_or_container() is False


def test_no_signal_not_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(os.path, "exists", lambda _p: False)
    assert _is_ci_or_container() is False


def test_dockerenv_present_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/.dockerenv")
    assert _is_ci_or_container() is True
