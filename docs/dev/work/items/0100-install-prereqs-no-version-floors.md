```toml
schema = 1
id = 100
kind = "item"
title = "Install docs state no OS or runtime version floors and offer no preflight check"
status = "closed"
decision_owner = "agent"
branches = [
  "feat/install-onboarding-preflight","docs/container-persistence-guidance"]
refs = [
  "docs/install.md:18-44",
  "pyproject.toml",
]
summary = "No OS/Python version floors or a preflight check; a macOS 12 user fails five times before the cause surfaces."
resolution = "Both halves built on feat/install-onboarding-preflight (2026-09-03). (1) The preflight command the item asked for: `sartor --doctor` reports the whole capability set -- Python vs floor, OS vs measured floor, API key presence, Chromium availability, recall index, container engine -- before anything is downloaded, in ~8ms, and exits nonzero only when Python itself is below the floor (an absent optional feature is not a failed install). (2) docs/install.md gains a version-floor table and a 'check your machine first' section. Deliberately narrow per C-0: ONLY floors this project has hit and traced are asserted -- the macOS 13 container floor (podman applehv) and the macOS 13 PDF floor (no Playwright Chromium build for macOS 12) -- and every other cell reads 'none measured' rather than implying support that was never tested. The observed `pip install --user` PATH trap on macOS is recorded too. preflight.os_capability() reports an unmeasured platform as unmeasured rather than inventing a plausible floor; a test asserts that."
verified_by = [
  "tests/test_preflight.py (57 tests, incl. TestOsCapability::test_no_floor_is_asserted_where_none_was_measured)",
  "tests/test_setup_api_key.py::TestDoctorFlag",
  "python app.py --doctor (live run, 2026-09-03, exit 0)",
]
```

**Observed on a real machine** (macOS 12.7.4 Monterey, build 21H1123, 2026-09-02). A user
following the recommended container path hit five consecutive failures before reaching an
error that revealed the path was never viable on their hardware:

1. `podman: command not found` — Podman Desktop was installed and updated, but Desktop
   ships only the GUI, not the engine. The user reasonably believed the prerequisite was met.
2. `podman machine list` showed a machine, so it looked configured. There is no state column;
   the machine was stopped. `podman info` was needed to learn that.
3. `podman machine start` failed on an SSH port conflict from stale `gvproxy`/`vfkit`
   processes left by earlier failed starts.
4. After a clean machine recreate, `vfkit exited unexpectedly with exit code 1` — a generic
   message with no cause.
5. Only under `--log-level=debug` did the real first line appear: **unsupported macOS
   version**. `applehv` requires macOS 13+.

The native path then hit its own undocumented floors: `pip install --user` console scripts
are not on macOS's PATH, and Playwright's current Chromium builds do not support macOS 12,
so PDF export is unavailable on this machine regardless of install method.

**What `docs/install.md` says today.** Prerequisites list Python 3.11+, an API key, and a
browser. There is **no** macOS version floor, no Windows WSL2 requirement, no statement that
the container path has hardware requirements the native path does not, and no command a user
can run to find out before downloading several GB.

**Proposed fix.** A prerequisites table with a hard floor per OS per path, and a preflight
`doctor` command that runs *before* anything is downloaded and reports the whole capability
set at once — container backend available or not, Python version, Chromium supportability —
rather than letting each floor surface separately as a runtime failure. This is the shape the
owner already specified for the planned launcher; today's session is the evidence for why the
`doctor` subcommand is the load-bearing part of it.

## Updates

### 2026-09-02 — filed from a live macOS install session

Sequence above is the actual failure order experienced, not a reconstruction. Total elapsed:
the entire session, with zero product commands run on the container path.
