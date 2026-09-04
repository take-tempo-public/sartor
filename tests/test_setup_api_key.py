"""`sartor --setup`'s key prompt (item 104) and its failure summary (item 102).

Both were filed from the same live macOS install on 2026-09-02.

**Item 104** — every documented way to supply the Anthropic key wrote it into
plaintext shell history (`docker run -e ANTHROPIC_API_KEY=...`, `export ...`,
`echo ... > .api_key`). That install ended with a test key in `~/.zsh_history`
on hardware the key's owner did not control. `--setup` now offers a non-echoing
prompt and writes the file itself, owner-only.

**Item 102** — `_run_setup`'s summary named BOTH PDF export and semantic recall
whenever EITHER step failed, because the loop discarded per-step outcomes into
one boolean. The user had to be told to `ls db/vector_index/` to find out
whether their search was actually broken.

No fixture here is key-shaped: the `block-secrets` guard pattern-matches tool
input and correctly refused an earlier draft that used realistic placeholders.
These tests care about presence, permissions and echo, never about the value.

`tests/` is the one tree the mypy --strict roster leaves un-ratcheted
(Decision 7), so this file is typed loosely, matching the rest of tests/.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys

import pytest

import app as app_module
import preflight

#: Deliberately NOT key-shaped -- see the module docstring.
_FAKE_KEY = "placeholder-credential-value"


@pytest.fixture(autouse=True)
def _no_ambient_key(monkeypatch):
    """Never let the developer's real ANTHROPIC_API_KEY decide a test outcome."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


# --- the shared key path ------------------------------------------------------------


class TestKeyPathAgreement:
    def test_preflight_and_the_app_client_resolve_the_same_file(self):
        """The probe must not report 'missing' on a file the app happily reads.

        `web_infra.clients._get_client` falls back to `_REPO_ROOT / ".api_key"`.
        `preflight.api_key_path()` is the single resolution `--setup` writes to and
        `--doctor` reports on. If these two ever diverge, the preflight starts lying
        in one direction or the other -- so the agreement is asserted, not commented.
        """
        from web_infra import clients

        assert preflight.api_key_path() == clients._REPO_ROOT / ".api_key"

    def test_base_dir_override_is_honored(self, tmp_path):
        assert preflight.api_key_path(tmp_path) == tmp_path / ".api_key"


# --- writing the key ----------------------------------------------------------------


class TestWriteApiKey:
    def test_writes_the_key_with_a_trailing_newline(self, tmp_path):
        path = app_module._write_api_key(_FAKE_KEY, tmp_path)
        assert path.read_text(encoding="utf-8") == _FAKE_KEY + "\n"

    def test_surrounding_whitespace_is_stripped(self, tmp_path):
        """A pasted key routinely carries a trailing space or newline."""
        path = app_module._write_api_key(f"  {_FAKE_KEY}\n ", tmp_path)
        assert path.read_text(encoding="utf-8") == _FAKE_KEY + "\n"

    def test_the_probe_agrees_immediately_after_writing(self, tmp_path):
        app_module._write_api_key(_FAKE_KEY, tmp_path)
        assert preflight.api_key_capability(tmp_path).ok is True

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits; Windows uses ACLs")
    def test_file_is_owner_only(self, tmp_path):
        """0o600 at creation, not chmod-after -- there must be no world-readable window."""
        path = app_module._write_api_key(_FAKE_KEY, tmp_path)
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600, f"expected 0o600, got {mode:o}"

    def test_overwrites_rather_than_appends(self, tmp_path):
        app_module._write_api_key("first-value", tmp_path)
        path = app_module._write_api_key("second-value", tmp_path)
        assert path.read_text(encoding="utf-8") == "second-value\n"


# --- the prompt ---------------------------------------------------------------------


def _tty(monkeypatch, *, interactive: bool):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: interactive, raising=False)


class TestPromptForApiKey:
    def test_no_prompt_when_a_key_is_already_resolvable(self, monkeypatch, tmp_path):
        """`--setup` is documented idempotent; silently re-writing a working key is not."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", _FAKE_KEY)
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr(
            app_module.getpass, "getpass", lambda *a, **k: pytest.fail("prompted anyway")
        )
        app_module._prompt_for_api_key(tmp_path)
        assert not (tmp_path / ".api_key").exists()

    def test_no_prompt_when_a_key_file_already_exists(self, monkeypatch, tmp_path):
        (tmp_path / ".api_key").write_text(_FAKE_KEY + "\n", encoding="utf-8")
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr(
            app_module.getpass, "getpass", lambda *a, **k: pytest.fail("prompted anyway")
        )
        app_module._prompt_for_api_key(tmp_path)

    def test_never_prompts_on_a_non_interactive_stdin(self, monkeypatch, tmp_path, capsys):
        """A container build or CI step must not block forever on an unanswerable read."""
        _tty(monkeypatch, interactive=False)
        monkeypatch.setattr(
            app_module.getpass, "getpass", lambda *a, **k: pytest.fail("prompted with no tty")
        )
        app_module._prompt_for_api_key(tmp_path)
        assert "ANTHROPIC_API_KEY" in capsys.readouterr().err

    def test_writes_the_key_the_user_types(self, monkeypatch, tmp_path):
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr(app_module.getpass, "getpass", lambda *a, **k: _FAKE_KEY)
        app_module._prompt_for_api_key(tmp_path)
        assert (tmp_path / ".api_key").read_text(encoding="utf-8") == _FAKE_KEY + "\n"

    def test_empty_answer_skips_without_writing(self, monkeypatch, tmp_path, capsys):
        """Skipping is a legitimate answer -- demo mode needs no key at all."""
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr(app_module.getpass, "getpass", lambda *a, **k: "   ")
        app_module._prompt_for_api_key(tmp_path)
        assert not (tmp_path / ".api_key").exists()
        assert "Skipped" in capsys.readouterr().out

    @pytest.mark.parametrize("interrupt", [EOFError, KeyboardInterrupt])
    def test_ctrl_c_or_eof_skips_cleanly(self, monkeypatch, tmp_path, interrupt):
        _tty(monkeypatch, interactive=True)

        def _raise(*a, **k):
            raise interrupt

        monkeypatch.setattr(app_module.getpass, "getpass", _raise)
        app_module._prompt_for_api_key(tmp_path)  # must not propagate
        assert not (tmp_path / ".api_key").exists()

    def test_the_key_is_never_echoed_to_stdout_or_stderr(self, monkeypatch, tmp_path, capsys):
        """The whole point of item 104: the key must not reach any transcript."""
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr(app_module.getpass, "getpass", lambda *a, **k: _FAKE_KEY)
        app_module._prompt_for_api_key(tmp_path)
        captured = capsys.readouterr()
        assert _FAKE_KEY not in captured.out
        assert _FAKE_KEY not in captured.err

    def test_uses_getpass_not_input(self, monkeypatch, tmp_path):
        """`input()` echoes. Reaching for it here would silently undo the fix."""
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr("builtins.input", lambda *a, **k: pytest.fail("used echoing input()"))
        monkeypatch.setattr(app_module.getpass, "getpass", lambda *a, **k: "")
        app_module._prompt_for_api_key(tmp_path)

    def test_an_unwritable_target_is_reported_not_raised(self, monkeypatch, tmp_path, capsys):
        _tty(monkeypatch, interactive=True)
        monkeypatch.setattr(app_module.getpass, "getpass", lambda *a, **k: _FAKE_KEY)

        def _boom(*a, **k):
            raise OSError("read-only file system")

        monkeypatch.setattr(app_module, "_write_api_key", _boom)
        app_module._prompt_for_api_key(tmp_path)
        assert "could not write the key file" in capsys.readouterr().err


# --- item 102: the failure summary --------------------------------------------------


def _setup_with(monkeypatch, tmp_path, *, failing: set[str]):
    """Run `_run_setup` with the named steps failing. `failing` holds argv substrings."""
    monkeypatch.setattr(app_module, "_prompt_for_api_key", lambda *a, **k: None)

    # Patch the real `subprocess` module, not `app_module.subprocess`: `app.py` does a
    # plain `import subprocess` and calls `subprocess.run(...)`, so patching the module
    # object reaches it. Qualifying it as `app_module.subprocess` also works at runtime
    # but fails `mypy .` with "Module 'app' does not explicitly export attribute
    # 'subprocess'" (no-implicit-reexport) -- which the gate runs and a per-module mypy
    # does not, so it only surfaces in CI.
    def _fake_run(cmd, *a, **k):
        joined = " ".join(cmd)
        if any(token in joined for token in failing):
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    return app_module._run_setup(tmp_path)


class TestSetupFailureSummary:
    def test_both_steps_succeed(self, monkeypatch, tmp_path, capsys):
        assert _setup_with(monkeypatch, tmp_path, failing=set()) == 0
        assert "Setup complete" in capsys.readouterr().out

    def test_chromium_only_failure_does_not_impugn_recall(self, monkeypatch, tmp_path, capsys):
        """Item 102, exactly as observed: Chromium failed, the index built fine.

        The old summary said "PDF export / semantic recall may be degraded", so the
        user could not tell which -- landing on someone already five failures deep,
        an ambiguous second broken feature reads as an unsalvageable install.
        """
        assert _setup_with(monkeypatch, tmp_path, failing={"playwright"}) == 1
        err = capsys.readouterr().err
        assert "Degraded: PDF export." in err
        assert "Working: semantic recall." in err

    def test_recall_only_failure_does_not_impugn_pdf(self, monkeypatch, tmp_path, capsys):
        assert _setup_with(monkeypatch, tmp_path, failing={"build_vector_index"}) == 1
        err = capsys.readouterr().err
        assert "Degraded: semantic recall." in err
        assert "Working: PDF export." in err

    def test_both_failing_names_both_and_claims_nothing_works(self, monkeypatch, tmp_path, capsys):
        assert _setup_with(monkeypatch, tmp_path, failing={"playwright", "build_vector_index"}) == 1
        err = capsys.readouterr().err
        assert "Degraded: PDF export and semantic recall." in err
        assert "Working:" not in err

    def test_an_oserror_is_treated_as_a_step_failure_too(self, monkeypatch, tmp_path, capsys):
        """A missing interpreter/module raises OSError, not CalledProcessError."""
        monkeypatch.setattr(app_module, "_prompt_for_api_key", lambda *a, **k: None)

        def _fake_run(cmd, *a, **k):
            if "playwright" in " ".join(cmd):
                raise OSError("No such file or directory")
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert app_module._run_setup(tmp_path) == 1
        assert "Degraded: PDF export." in capsys.readouterr().err

    def test_the_key_prompt_runs_before_any_download(self, monkeypatch, tmp_path):
        """A user with no key should learn that in the first second, not after ~180 MB."""
        order: list[str] = []
        monkeypatch.setattr(
            app_module, "_prompt_for_api_key", lambda *a, **k: order.append("prompt")
        )

        def _fake_run(cmd, *a, **k):
            order.append("download")
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", _fake_run)
        app_module._run_setup(tmp_path)
        assert order[0] == "prompt", order


# --- the CLI surface ----------------------------------------------------------------


class TestDoctorFlag:
    def test_doctor_exits_without_starting_a_server(self, monkeypatch, capsys):
        monkeypatch.setattr(app_module.preflight, "run_doctor", lambda *a, **k: 0)
        monkeypatch.setattr(
            app_module.app, "run", lambda *a, **k: pytest.fail("--doctor started a server")
        )
        with pytest.raises(SystemExit) as excinfo:
            app_module.main(["--doctor"])
        assert excinfo.value.code == 0

    def test_doctor_propagates_a_fatal_exit_code(self, monkeypatch):
        monkeypatch.setattr(app_module.preflight, "run_doctor", lambda *a, **k: 1)
        with pytest.raises(SystemExit) as excinfo:
            app_module.main(["--doctor"])
        assert excinfo.value.code == 1

    def test_doctor_does_not_run_setup(self, monkeypatch):
        monkeypatch.setattr(app_module.preflight, "run_doctor", lambda *a, **k: 0)
        monkeypatch.setattr(
            app_module, "_run_setup", lambda *a, **k: pytest.fail("--doctor ran --setup")
        )
        with pytest.raises(SystemExit):
            app_module.main(["--doctor"])
