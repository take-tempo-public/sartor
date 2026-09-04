"""scripts/gate.py's memory preflight (item 108).

Item 108 (docs/dev/work/items/0108-gate-preflight-resource-check.md): four
consecutive local `python -m scripts.gate` attempts died mid-run as an OOM'd
xdist worker rather than failing cleanly. This gate is the regression suite
for the fix -- a fail-closed preflight that reads free physical memory before
any of the six real steps run and refuses immediately, with a legible
message, below a measured floor (`gate._MEMORY_FLOOR_GB`).

Covers, in order:
  - the two pure text parsers (`/proc/meminfo`, macOS `vm_stat`) with real
    captured sample text, portable on any CI OS -- no platform mocking;
  - the two pure process-listing parsers (`tasklist /fo csv`, `ps -eo
    pid,rss,comm`), same approach, with real captured sample output;
  - `_available_memory_gb`'s platform dispatch: a REAL smoke test on
    whichever of Linux/Windows/macOS this test happens to run on (the
    other two platforms SKIP -- there is no portable way to fake an OS
    read without mocking away the exact code path under test), plus a
    fully portable test of the "unsupported platform" fail-open behavior
    via monkeypatching `os.name` and `sys.platform` together;
  - `_check_memory_preflight`'s three outcomes (proceed / refuse /
    unmeasurable-proceeds), fully portable via monkeypatching
    `gate._available_memory_gb` and `gate._top_memory_consumers` directly
    -- never touches a real OS memory read.

`tests/` is the one module tree the mypy --strict roster (pyproject.toml)
deliberately leaves un-ratcheted (Decision 7), so this file is typed loosely
where that is the path of least friction, matching the rest of tests/.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys

import pytest

from scripts import gate

# A trimmed but real /proc/meminfo (Linux). MemAvailable is what the parser
# reads -- Linux 3.14+, the kernel's own best estimate of what a new process
# could allocate without swapping, which is why it's the field this project
# reads rather than MemFree.
_PROC_MEMINFO_SAMPLE = """\
MemTotal:       16384000 kB
MemFree:         1048576 kB
MemAvailable:    2097152 kB
Buffers:          204800 kB
Cached:          3145728 kB
SwapTotal:              0 kB
SwapFree:               0 kB
"""

# A trimmed but real macOS `vm_stat` sample (Apple Silicon page size).
_VM_STAT_SAMPLE = """\
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                              32768.
Pages active:                           131072.
Pages inactive:                          65536.
Pages speculative:                        4096.
Pages wired down:                        98304.
"""

# Captured 2026-09-03 from a real `tasklist /fo csv` run on this project's
# Windows dev box (see docs/dev/work/items/0108-...md).
_TASKLIST_CSV_SAMPLE = (
    '"Image Name","PID","Session Name","Session#","Mem Usage"\r\n'
    '"python.exe","9660","Console","1","11,196 K"\r\n'
    '"python.exe","78736","Console","1","11,232 K"\r\n'
    '"chrome.exe","80556","Console","1","484,784 K"\r\n'
)

# A representative `ps -eo pid,rss,comm` sample (GNU/Linux and BSD/macOS both
# emit a header row in this shape; the parser tolerates it either way).
_PS_OUTPUT_SAMPLE = """  PID   RSS COMMAND
    1  2048 systemd
  842 65536 python3
  901 12345 pytest
"""


class TestParseProcMeminfo:
    def test_extracts_mem_available_in_gb(self) -> None:
        # 2097152 kB / 1024**2 = 2.0 GB exactly.
        assert gate._parse_proc_meminfo(_PROC_MEMINFO_SAMPLE) == pytest.approx(2.0)

    def test_returns_none_when_mem_available_missing(self) -> None:
        text = "MemTotal:       16384000 kB\nMemFree:         1048576 kB\n"
        assert gate._parse_proc_meminfo(text) is None

    def test_returns_none_on_empty_text(self) -> None:
        assert gate._parse_proc_meminfo("") is None


class TestParseVmStat:
    def test_extracts_free_pages_in_gb(self) -> None:
        # 32768 pages * 16384 bytes = 536870912 bytes = 0.5 GB exactly.
        assert gate._parse_vm_stat(_VM_STAT_SAMPLE) == pytest.approx(0.5)

    def test_returns_none_when_page_size_missing(self) -> None:
        text = "Pages free:                              32768.\n"
        assert gate._parse_vm_stat(text) is None

    def test_returns_none_when_pages_free_missing(self) -> None:
        text = "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        assert gate._parse_vm_stat(text) is None


class TestParseTasklistCsv:
    def test_parses_real_sample(self) -> None:
        pairs = gate._parse_tasklist_csv(_TASKLIST_CSV_SAMPLE)
        assert ("python.exe (pid 9660)", 11196) in pairs
        assert ("chrome.exe (pid 80556)", 484784) in pairs
        assert len(pairs) == 3

    def test_returns_empty_list_for_empty_text(self) -> None:
        assert gate._parse_tasklist_csv("") == []

    def test_skips_rows_with_unparsable_mem_usage(self) -> None:
        text = (
            '"Image Name","PID","Session Name","Session#","Mem Usage"\r\n'
            '"weird.exe","123","Console","1","not-a-number"\r\n'
        )
        assert gate._parse_tasklist_csv(text) == []

    def test_returns_empty_list_when_header_missing_expected_columns(self) -> None:
        text = '"Foo","Bar"\r\n"1","2"\r\n'
        assert gate._parse_tasklist_csv(text) == []


class TestParsePsOutput:
    def test_parses_real_sample_and_skips_header(self) -> None:
        pairs = gate._parse_ps_output(_PS_OUTPUT_SAMPLE)
        assert ("systemd (pid 1)", 2048) in pairs
        assert ("python3 (pid 842)", 65536) in pairs
        assert ("pytest (pid 901)", 12345) in pairs
        assert len(pairs) == 3

    def test_returns_empty_list_for_empty_text(self) -> None:
        assert gate._parse_ps_output("") == []


class TestTopMemoryConsumers:
    def test_sorts_descending_and_formats_mb(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pairs = [("small (pid 1)", 1024), ("big (pid 2)", 1048576), ("medium (pid 3)", 102400)]
        monkeypatch.setattr(gate, "_parse_ps_output", lambda text: pairs)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: type(
                "R", (), {"returncode": 0, "stdout": "irrelevant, parser is mocked"}
            )(),
        )
        result = gate._top_memory_consumers(limit=8)
        assert result[0] == "big (pid 2) - 1024 MB"
        assert result[1] == "medium (pid 3) - 100 MB"
        assert result[2] == "small (pid 1) - 1 MB"

    def test_respects_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pairs = [(f"p{i} (pid {i})", i * 1000) for i in range(20)]
        monkeypatch.setattr(gate, "_parse_ps_output", lambda text: pairs)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: type("R", (), {"returncode": 0, "stdout": ""})(),
        )
        assert len(gate._top_memory_consumers(limit=3)) == 3

    def test_returns_empty_list_when_command_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: type("R", (), {"returncode": 1, "stdout": ""})(),
        )
        assert gate._top_memory_consumers() == []

    def test_returns_empty_list_when_command_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*args: object, **kwargs: object) -> None:
            raise OSError("no such command")

        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(subprocess, "run", _raise)
        assert gate._top_memory_consumers() == []

    # Deliberately NOT asserting non-empty: observed live on this project's own
    # dev box (2026-09-03, under the same memory pressure item 108 documents)
    # that a real `tasklist` call can itself time out under enough system
    # thrashing, correctly triggering the documented graceful-degrade-to-[]
    # path -- that is the mechanism working, not a bug. Asserting "non-empty"
    # here would make the test flaky on exactly the machine states this
    # feature exists to handle. The real, unmocked call is still exercised
    # for real dispatch/parsing coverage; only the "found something" claim is
    # relaxed to "returned a valid list, whatever its contents".

    @pytest.mark.skipif(sys.platform != "win32", reason="exercises the real Windows tasklist path")
    def test_real_windows_listing_returns_a_list(self) -> None:
        assert isinstance(gate._top_memory_consumers(), list)

    @pytest.mark.skipif(sys.platform == "win32", reason="exercises the real Unix ps path")
    def test_real_unix_listing_returns_a_list(self) -> None:
        assert isinstance(gate._top_memory_consumers(), list)


class TestWindowsAvailPhysGb:
    def test_returns_none_when_not_nt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "name", "posix")
        assert gate._windows_avail_phys_gb() is None

    @pytest.mark.skipif(os.name != "nt", reason="exercises the real GlobalMemoryStatusEx call")
    def test_real_read_on_windows_is_positive(self) -> None:
        result = gate._windows_avail_phys_gb()
        assert result is not None
        assert result > 0


class TestAvailableMemoryGb:
    def test_falls_open_on_unrecognized_platform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # gate._available_memory_gb dispatches on platform.system() (not
        # sys.platform -- see its own docstring for why), so that is what
        # this test patches. Not "Linux", not "Darwin" -> falls through to
        # the Windows reader, which itself declines (os.name != "nt") ->
        # None all the way out.
        monkeypatch.setattr(platform, "system", lambda: "FreeBSD")
        monkeypatch.setattr(os, "name", "posix")
        assert gate._available_memory_gb() is None

    @pytest.mark.skipif(
        not sys.platform.startswith("linux"), reason="real /proc/meminfo dispatch, Linux only"
    )
    def test_real_read_on_linux_is_positive(self) -> None:
        result = gate._available_memory_gb()
        assert result is not None
        assert result > 0

    @pytest.mark.skipif(sys.platform != "darwin", reason="real vm_stat dispatch, macOS only")
    def test_real_read_on_macos_is_positive(self) -> None:
        result = gate._available_memory_gb()
        assert result is not None
        assert result > 0

    @pytest.mark.skipif(
        sys.platform != "win32", reason="real GlobalMemoryStatusEx dispatch, Windows only"
    )
    def test_real_read_on_windows_is_positive(self) -> None:
        result = gate._available_memory_gb()
        assert result is not None
        assert result > 0


class TestCheckMemoryPreflight:
    def test_proceeds_when_available_meets_floor(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(gate, "_available_memory_gb", lambda: gate._MEMORY_FLOOR_GB)
        code = gate._check_memory_preflight()
        assert code == 0
        out = capsys.readouterr().out
        assert "proceeding" in out
        assert "REFUSED" not in out

    def test_proceeds_when_measurement_unavailable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(gate, "_available_memory_gb", lambda: None)
        code = gate._check_memory_preflight()
        assert code == 0
        out = capsys.readouterr().out
        assert "could not measure" in out

    def test_refuses_below_floor_and_names_consumers(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(gate, "_available_memory_gb", lambda: gate._MEMORY_FLOOR_GB - 0.5)
        monkeypatch.setattr(gate, "_top_memory_consumers", lambda: ["hog.exe (pid 1) - 900 MB"])
        code = gate._check_memory_preflight()
        assert code != 0
        err = capsys.readouterr().err
        assert "REFUSED" in err
        assert "hog.exe (pid 1) - 900 MB" in err

    def test_refuses_below_floor_even_with_no_named_consumers(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(gate, "_available_memory_gb", lambda: 0.0)
        monkeypatch.setattr(gate, "_top_memory_consumers", lambda: [])
        code = gate._check_memory_preflight()
        assert code != 0
        err = capsys.readouterr().err
        assert "REFUSED" in err

    def test_main_refuses_before_running_any_step(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The preflight must short-circuit main() -- no real step subprocess runs."""
        monkeypatch.setattr(gate, "_available_memory_gb", lambda: 0.0)
        monkeypatch.setattr(gate, "_top_memory_consumers", lambda: [])

        def _fail_if_called(name: str, cmd: list[str]) -> int:
            raise AssertionError(f"gate step {name!r} ran despite a refused preflight")

        monkeypatch.setattr(gate, "_run_step", _fail_if_called)
        assert gate.main([]) != 0
