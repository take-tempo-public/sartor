"""preflight.py -- the capability probes behind items 100/102/103/104.

`docs/dev/diagnosis/install-onboarding-preflight.md` is the evidence record; this
file is the regression suite that keeps each observation from rotting back.

Two of these tests exist because the instrument REFUTED an earlier design, and
without them the refuted design is a plausible "simplification" a future session
would reach for:

  - `test_probe_checks_headless_shell_not_just_executable_path` pins O-2: the PDF
    path launches `chromium_headless_shell-<rev>`, NOT the `chromium-<rev>` binary
    `chromium.executable_path` names. A probe that stats only the headed artifact
    reports "available" for an install that cannot render a PDF.
  - `test_report_is_pure_ascii` pins O-7 and the module's own printed-output claim.
    A cp1252 console is what `docs/install.md` tells a Windows user to open, and a
    stray em-dash in a `remedy` string turns `--doctor` into a UnicodeEncodeError.
    This session hit exactly that, in this module, and fixed it -- the test is the
    mechanism so the next one cannot (C-11).

**Nothing in the default (`-m "not ux"`) tier launches a browser or starts the
Playwright driver**: the whole point of the module is that the answer costs ~8 ms,
and a suite that pays ~3 s to check it would quietly license the ~3 s
implementation. The single exception is `test_probe_agrees_with_a_real_chromium_launch`,
which is `ux`-marked and deselected here — it uses a real `launch()` as the oracle
because the presence arm cannot be checked against reality any other way, and it
guards itself inside the test body so collection never pays for it.

**No fixture in this file is key-shaped.** The `block-secrets` guard pattern-matches
tool input, and it correctly refused an earlier draft that used realistic-looking
placeholder keys. Key *presence* is all these probes report, so a plain sentinel
string exercises every branch just as well.

`tests/` is the one tree the mypy --strict roster (pyproject.toml) leaves
un-ratcheted (Decision 7), so this file is typed loosely, matching the rest of tests/.
"""

from __future__ import annotations

import json
import platform

import pytest

import preflight

#: Deliberately NOT key-shaped -- see the module docstring.
_FAKE_KEY = "placeholder-credential-value"

# A real `browsers.json` shape, captured 2026-09-03 from the installed
# playwright driver (package/driver/package/browsers.json). Trimmed to the
# entries that matter plus the two tip-of-tree decoys that make exact-name
# matching load-bearing.
_BROWSERS_JSON_SAMPLE = json.dumps(
    {
        "comment": "Do not edit by hand",
        "browsers": [
            {"name": "chromium", "revision": "1223"},
            {"name": "chromium-headless-shell", "revision": "1223"},
            {"name": "chromium-tip-of-tree", "revision": "1427"},
            {"name": "chromium-tip-of-tree-headless-shell", "revision": "1427"},
            {"name": "firefox", "revision": "1522"},
            {"name": "webkit", "revision": "2287"},
            {"name": "ffmpeg", "revision": "1011"},
        ],
    }
)


@pytest.fixture(autouse=True)
def _clear_pdf_cache():
    """`pdf_available` is lru_cached per process; a stale entry would leak between tests."""
    preflight.pdf_available.cache_clear()
    yield
    preflight.pdf_available.cache_clear()


# --- the pure manifest parser -------------------------------------------------------


class TestParseBrowsersJson:
    def test_extracts_both_chromium_revisions(self):
        assert preflight._parse_browsers_json(_BROWSERS_JSON_SAMPLE) == ("1223", "1223")

    def test_exact_name_match_ignores_tip_of_tree_decoys(self):
        """`chromium-tip-of-tree-headless-shell` must not be mistaken for the real one."""
        only_decoys = json.dumps(
            {
                "browsers": [
                    {"name": "chromium-tip-of-tree", "revision": "1427"},
                    {"name": "chromium-tip-of-tree-headless-shell", "revision": "1427"},
                ]
            }
        )
        assert preflight._parse_browsers_json(only_decoys) is None

    def test_integer_revisions_are_accepted(self):
        """Revisions are strings in the real manifest; an int must not silently drop it."""
        as_ints = json.dumps(
            {
                "browsers": [
                    {"name": "chromium", "revision": 1223},
                    {"name": "chromium-headless-shell", "revision": 1223},
                ]
            }
        )
        assert preflight._parse_browsers_json(as_ints) == ("1223", "1223")

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "not json at all",
            "[]",
            '{"browsers": "not a list"}',
            '{"browsers": [{"name": "chromium"}]}',
            '{"browsers": [{"name": "chromium", "revision": "1"}]}',
            '{"no_browsers_key": true}',
        ],
        ids=["empty", "garbage", "list", "browsers-not-list", "no-revision", "no-shell", "no-key"],
    )
    def test_malformed_input_returns_none_never_raises(self, text):
        """A layout change degrades to 'unknown', never to a crash at app startup."""
        assert preflight._parse_browsers_json(text) is None


# --- browsers root resolution -------------------------------------------------------


class TestBrowsersRoot:
    def test_env_var_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
        assert preflight._browsers_root() == tmp_path

    def test_zero_is_playwright_s_package_local_mode_not_a_directory(self, monkeypatch):
        """`PLAYWRIGHT_BROWSERS_PATH=0` means 'beside the package', not a dir named '0'."""
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "0")
        assert preflight._browsers_root() is None

    def test_windows_without_localappdata_is_unresolvable(self, monkeypatch):
        monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        assert preflight._browsers_root() is None

    def test_per_platform_defaults(self, monkeypatch):
        monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        assert preflight._browsers_root().as_posix().endswith("Library/Caches/ms-playwright")
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert preflight._browsers_root().as_posix().endswith(".cache/ms-playwright")


# --- the artifact marker ------------------------------------------------------------


class TestArtifactComplete:
    def test_marker_present(self, tmp_path):
        art = tmp_path / "chromium-1223"
        art.mkdir()
        (art / "INSTALLATION_COMPLETE").write_text("", encoding="utf-8")
        assert preflight._artifact_complete(tmp_path, "chromium-1223") is True

    def test_directory_without_marker_is_incomplete(self, tmp_path):
        """A half-extracted artifact dir must not read as installed (diagnosis O-3/O-4)."""
        (tmp_path / "chromium-1223").mkdir()
        assert preflight._artifact_complete(tmp_path, "chromium-1223") is False

    def test_missing_directory(self, tmp_path):
        assert preflight._artifact_complete(tmp_path, "chromium-1223") is False


# --- chromium capability ------------------------------------------------------------


def _fake_layout(monkeypatch, tmp_path, *, headed: bool, headless: bool):
    """Point the probe at a synthetic browsers root with the named artifacts present."""
    monkeypatch.setattr(preflight, "_chromium_revisions", lambda: ("1223", "1223"))
    monkeypatch.setattr(preflight, "_browsers_root", lambda: tmp_path)
    for present, name in ((headed, "chromium-1223"), (headless, "chromium_headless_shell-1223")):
        if present:
            art = tmp_path / name
            art.mkdir()
            (art / "INSTALLATION_COMPLETE").write_text("", encoding="utf-8")


class TestChromiumCapability:
    def test_both_artifacts_present_is_available(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=True, headless=True)
        assert preflight.chromium_capability().ok is True

    def test_neither_present_is_unavailable(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=False, headless=False)
        cap = preflight.chromium_capability()
        assert cap.ok is False
        assert "sartor --setup" in cap.remedy

    def test_probe_checks_headless_shell_not_just_executable_path(self, monkeypatch, tmp_path):
        """O-2, the refutation this module exists around.

        Headed chromium present, headless shell absent. `render_pdf` calls
        `p.chromium.launch()` with no `headless` argument, so it needs the headless
        shell -- observed directly: `launch(headless=True)` failed on the
        `chromium_headless_shell-1223/...` path while `executable_path` pointed at the
        headed binary that WAS there. A probe that stats only `executable_path` calls
        this state available and ships item 103's bug back.
        """
        _fake_layout(monkeypatch, tmp_path, headed=True, headless=False)
        cap = preflight.chromium_capability()
        assert cap.ok is False
        assert "headless shell" in cap.detail

    def test_headed_missing_shell_present_is_also_unavailable(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=False, headless=True)
        cap = preflight.chromium_capability()
        assert cap.ok is False
        assert "chromium" in cap.detail

    def test_unresolvable_layout_is_unknown_not_false(self, monkeypatch):
        """Unknown must stay unknown -- `pdf_available` is what decides which way to lean."""
        monkeypatch.setattr(preflight, "_chromium_revisions", lambda: None)
        assert preflight.chromium_capability().ok is None

    def test_unresolvable_root_is_unknown_not_false(self, monkeypatch):
        monkeypatch.setattr(preflight, "_chromium_revisions", lambda: ("1223", "1223"))
        monkeypatch.setattr(preflight, "_browsers_root", lambda: None)
        assert preflight.chromium_capability().ok is None

    def test_macos_below_the_chromium_floor_is_not_told_to_rerun_the_failing_command(
        self, monkeypatch, tmp_path
    ):
        """Item 103's actual machine: `playwright install chromium` CANNOT succeed there.

        Current Playwright releases ship no Chromium build for macOS 12, so the generic
        remedy is advice that already failed for this user five times. The floor branch
        has to say PDF is unavailable and name the outputs that still work.
        """
        _fake_layout(monkeypatch, tmp_path, headed=False, headless=False)
        monkeypatch.setattr(platform, "mac_ver", lambda: ("12.7.4", ("", "", ""), "x86_64"))
        remedy = preflight.chromium_capability().remedy
        assert "playwright install chromium` cannot succeed" in remedy
        assert "DOCX" in remedy

    def test_off_macos_keeps_the_actionable_setup_remedy(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=False, headless=False)
        monkeypatch.setattr(platform, "mac_ver", lambda: ("", ("", "", ""), ""))
        assert "sartor --setup" in preflight.chromium_capability().remedy


class TestPdfAvailable:
    def test_available_when_probe_says_yes(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=True, headless=True)
        assert preflight.pdf_available() is True

    def test_unavailable_when_probe_says_no(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=False, headless=False)
        assert preflight.pdf_available() is False

    def test_unknown_leans_available(self, monkeypatch):
        """A Playwright layout change must degrade to today's behavior, not blank PDF out.

        The asymmetry is the argument: a false 'unavailable' hides a working feature with
        no way for the user to discover the button should be there; a false 'available'
        just restores the pre-fix behavior, where the attempt fails with an error the
        route already surfaces.
        """
        monkeypatch.setattr(preflight, "_chromium_revisions", lambda: None)
        assert preflight.chromium_capability().ok is None
        assert preflight.pdf_available() is True

    def test_result_is_cached_per_process(self, monkeypatch, tmp_path):
        _fake_layout(monkeypatch, tmp_path, headed=True, headless=True)
        assert preflight.pdf_available() is True
        # Flip the underlying answer; the cache must hold (no filesystem probe per call).
        monkeypatch.setattr(
            preflight, "chromium_capability", lambda: pytest.fail("re-probed after caching")
        )
        assert preflight.pdf_available() is True


# --- python / os --------------------------------------------------------------------


class TestPythonCapability:
    def test_current_interpreter_meets_the_floor(self):
        """The suite cannot run below the floor, so this is a real invariant, not a tautology."""
        assert preflight.python_capability().ok is True


class TestOsCapability:
    def test_macos_below_floor_is_flagged_with_a_remedy(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "mac_ver", lambda: ("12.7.4", ("", "", ""), "x86_64"))
        cap = preflight.os_capability()
        assert cap.ok is False
        assert "12.7" in cap.detail
        assert "13.0" in cap.remedy

    def test_macos_at_floor_is_ok(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "mac_ver", lambda: ("13.0", ("", "", ""), "arm64"))
        assert preflight.os_capability().ok is True

    def test_unreadable_macos_version_is_unknown(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "mac_ver", lambda: ("", ("", "", ""), ""))
        assert preflight.os_capability().ok is None

    def test_non_numeric_macos_version_is_unknown(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "mac_ver", lambda: ("beta", ("", "", ""), ""))
        assert preflight._macos_version() is None

    @pytest.mark.parametrize("system", ["Windows", "Linux"])
    def test_no_floor_is_asserted_where_none_was_measured(self, monkeypatch, system):
        """C-0: an unmeasured floor is reported as unmeasured, never invented."""
        monkeypatch.setattr(platform, "system", lambda: system)
        cap = preflight.os_capability()
        assert cap.ok is True
        assert "no measured version floor" in cap.detail


# --- api key / recall / container ----------------------------------------------------


class TestApiKeyCapability:
    def test_env_var_found(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", _FAKE_KEY)
        assert preflight.api_key_capability(tmp_path).ok is True

    def test_blank_env_var_is_not_a_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        assert preflight.api_key_capability(tmp_path).ok is False

    def test_key_file_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        (tmp_path / ".api_key").write_text(_FAKE_KEY + "\n", encoding="utf-8")
        assert preflight.api_key_capability(tmp_path).ok is True

    def test_empty_key_file_is_not_a_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        (tmp_path / ".api_key").write_text("\n", encoding="utf-8")
        assert preflight.api_key_capability(tmp_path).ok is False

    def test_absent_offers_the_non_echoing_route_and_demo_mode(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cap = preflight.api_key_capability(tmp_path)
        assert cap.ok is False
        assert "SARTOR_DEMO=1" in cap.remedy

    def test_the_key_value_is_never_reported(self, monkeypatch, tmp_path):
        """Item 104 is about key exposure; a probe that echoed the key would be worse."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", _FAKE_KEY)
        cap = preflight.api_key_capability(tmp_path)
        rendered = preflight.format_report([cap])
        assert _FAKE_KEY not in cap.detail
        assert _FAKE_KEY not in cap.remedy
        assert _FAKE_KEY not in rendered


class TestVectorIndexCapability:
    def test_all_three_present_is_built(self, tmp_path):
        index = tmp_path / "db" / "vector_index"
        (index / "model").mkdir(parents=True)
        (index / "embeddings.npy").write_bytes(b"")
        (index / "chunks.json").write_text("[]", encoding="utf-8")
        assert preflight.vector_index_capability(tmp_path).ok is True

    def test_missing_model_dir_is_not_built(self, tmp_path):
        """Mirrors blueprints/assistant.py: BOTH the model and the index must be present."""
        index = tmp_path / "db" / "vector_index"
        index.mkdir(parents=True)
        (index / "embeddings.npy").write_bytes(b"")
        (index / "chunks.json").write_text("[]", encoding="utf-8")
        assert preflight.vector_index_capability(tmp_path).ok is False

    def test_absent_entirely(self, tmp_path):
        assert preflight.vector_index_capability(tmp_path).ok is False


class TestContainerCapability:
    def test_found_on_path(self, monkeypatch):
        monkeypatch.setattr(preflight.shutil, "which", lambda name: f"/usr/bin/{name}")
        cap = preflight.container_capability()
        assert cap.ok is True
        assert "podman" in cap.detail

    def test_neither_on_path_names_the_podman_desktop_trap(self, monkeypatch):
        """Item 100 step 1: Podman Desktop ships the GUI, not the engine."""
        monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
        cap = preflight.container_capability()
        assert cap.ok is False
        assert "Podman Desktop" in cap.remedy

    def test_nothing_is_executed_only_path_is_consulted(self, monkeypatch):
        """A hung `podman info` must never be reachable from a preflight probe."""
        import subprocess

        monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("preflight shelled out"))
        preflight.container_capability()


# --- report -------------------------------------------------------------------------


class TestReport:
    def test_report_is_pure_ascii(self):
        """O-7: a cp1252 console is what install.md tells a Windows user to open.

        This session put an em-dash into three `remedy`/`detail` strings and only caught
        it because the instrument had already crashed on the same class of character.
        The claim in the module docstring is only as good as this assertion.
        """
        report = preflight.format_report(preflight.probe_all())
        report.encode("ascii")  # raises UnicodeEncodeError if any glyph slipped in

    def test_every_probe_string_is_ascii(self, monkeypatch, tmp_path):
        """Cover the branches probe_all() does not hit on this machine."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "mac_ver", lambda: ("12.7.4", ("", "", ""), "x86_64"))
        monkeypatch.setattr(preflight, "_chromium_revisions", lambda: ("1223", "1223"))
        monkeypatch.setattr(preflight, "_browsers_root", lambda: tmp_path)
        monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        report = preflight.format_report(preflight.probe_all(tmp_path))
        report.encode("ascii")
        assert "MISSING" in report

    def test_report_names_every_probe(self):
        report = preflight.format_report(preflight.probe_all())
        for cap in preflight.probe_all():
            assert cap.label in report

    def test_optional_features_missing_is_not_a_fatal_exit(self, monkeypatch, tmp_path, capsys):
        """A macOS 12 user with no Chromium has a working Sartor minus PDF."""
        monkeypatch.setattr(preflight, "_chromium_revisions", lambda: ("1223", "1223"))
        monkeypatch.setattr(preflight, "_browsers_root", lambda: tmp_path)
        assert preflight.run_doctor(tmp_path) == 0
        assert "MISSING" in capsys.readouterr().out

    def test_python_below_floor_is_the_one_fatal_exit(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            preflight,
            "python_capability",
            lambda: preflight.Capability("python", "Python runtime", False, "3.9.0"),
        )
        assert preflight.run_doctor(tmp_path) == 1


class TestCapabilityMark:
    @pytest.mark.parametrize(
        ("ok", "expected"), [(True, "ok"), (False, "MISSING"), (None, "unknown")]
    )
    def test_mark_per_state(self, ok, expected):
        assert preflight.Capability("k", "L", ok, "d").mark.strip() == expected


# --- cross-check against the real machine -------------------------------------------


@pytest.mark.ux
def test_probe_agrees_with_a_real_chromium_launch():
    """The one test that checks the probe against reality rather than a fake layout.

    Every other chromium test here builds a synthetic browsers root, so the suite
    could agree perfectly with itself while being wrong about this machine. This one
    uses a **real `launch()` as the oracle** and asserts the ~8 ms probe agrees --
    the presence arm of the diagnosis' acceptance bar. (The absence arm is covered
    deterministically by the synthetic-layout tests above; reproducing it here would
    mean uninstalling Chromium.)

    **The skip guard is inside the test on purpose.** A module-level `skipif` calling
    a real `launch()` -- the pattern `tests/test_pdf_render.py:_chromium_available`
    uses -- is evaluated at COLLECTION, so it would launch a browser during the
    `pytest -m "not ux"` run too, where this module is still collected. That would
    put a multi-second browser launch in the default tier for a test that never runs
    there. An earlier draft of this test had no guard at all and would have FAILED
    (not skipped) in CI's `quality` job, which runs the full gate -- `pytest -m ux`
    included -- on a runner with no Chromium installed.
    """
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            browser.close()
    except Exception as exc:
        pytest.skip(f"Chromium not installed here ({type(exc).__name__}); no oracle to agree with")

    preflight.pdf_available.cache_clear()
    cap = preflight.chromium_capability()
    assert cap.ok is True, (
        "a real chromium.launch() just succeeded, so the probe must see it; "
        f"probe said: {cap.detail}"
    )
