---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# Area D findings — tests, CI & gates

> Surfaces: suite shape/runtime (1,453 tests measured at 308.9s), marker
> split, the 11 committed gate tests, CI matrix + docker + eval-smoke cost,
> interrogate/mypy/ruff ratchets. Finders: D1 suite-shape, D2 ci-cost.
>
> Area summary (D1): the full run is dominated by ~71 slow-tier tests (67
> Playwright ux + 4 pdf_render slow) — ~4.9% of tests consuming an estimated
> 95%+ of wall time. No fast inner-loop invocation is documented anywhere;
> CONTRIBUTING's checklist double-runs the ux tier. The governance-hooks-gate
> blocker count was spot-checked against the 10 wired hooks and found
> accurate (null result, not registered).
> Area summary (D2): matrix omits the requires-python floor; no concurrency
> cancellation; eval-smoke duplicates setup; arm64 rides QEMU unquantified.

## F-tci-01 — No documented fast test lane; default `pytest` silently re-pays the ~95% ux/slow cost when Chromium is installed

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** no
- **Metric:** measured: 77 non-ux tests run in 0.46s; 2 sampled ux tests took 18.3s (9.06s one-time Chromium setup + ~3s/test); extrapolation accounts for essentially all of the 308.9s full run. A `-m "not slow and not ux"` lane plausibly cuts the inner dev loop from ~309s to under ~15s (~20×).
- **Evidence:**
  - `pyproject.toml:285-297`: markers defined; no addopts deselects them by default.
  - `CONTRIBUTING.md:88-89`: checklist runs `pytest` AND `pytest -m ux` as separate steps — a redundant double-run when Chromium is present (confirmed installed on this machine).
  - `AGENTS.md:141-144`: "default pytest stays green everywhere" framed only around the skip-when-absent guard, not inner-loop cost when present.
  - Targeted runs: tests/ux/regression 2 tests → 18.27s; tests/test_hardening.py 77 tests → 0.46s.
- **Dedup:** dev-loop ergonomics; distinct from the pending PX-25 (UX tier in CI), which is about CI inclusion.

## F-tci-02 — `_imported_roots()` AST walker duplicated near-verbatim across three boundary-gate tests

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** 3 near-identical ~10-12 line bodies (~30 LOC); one shared helper (with a resolve-relative parameter for the recall variant) collapses 3 places a future import-walk bugfix must land into 1.
- **Evidence:** `tests/test_construction_boundary.py:40-51`; `tests/test_web_infra_is_leaf.py:21-31` (near byte-identical); `tests/test_recall_boundary.py:50-65` (one legitimate semantic variant).
- **Dedup:** the gate-primitive duplication itself — not any PX item about specific gates.

## F-tci-03 — UX tier repeats full app reload + SQLite init + threaded server + browser context on every one of 67 tests

- **Disposition:** WATCH · **Leverage:** P2 · **Simplification:** no
- **Metric:** ~0.6–9s setup + ~2.8–3.3s call + up to 1.9s teardown per test; only the Chromium process is session-scoped. Module-scoped app+server for read-mostly regression tests could shave a meaningful fraction of the tier's ~250–280s — but one personas-500 concurrency test deliberately needs per-test isolation, so which tests can share state is a human call.
- **Evidence:** `tests/ux/conftest.py:22-58` (ux_app function-scoped), `:61-79` (live_server function-scoped; docstring says threaded=True is load-bearing for ONE test), `:82-101` (_browser is the only session-scoped fixture).
- **Dedup:** internal fixture cost of the tier — not PX-25 (CI inclusion) or ledger #3 (owner E2E walkthrough).

## F-tci-04 — No CI concurrency group: force-push iterations run stale workflows to completion

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** YES
- **Metric:** one full matrix run (3 jobs) wasted per superseded push; a 3-line `concurrency:` block with cancel-in-progress eliminates it.
- **Evidence:** `.github/workflows/ci.yml:1-67` — no `concurrency:` block present.
- **Dedup:** new CI-efficiency gap; not in ledger or PX list.

## F-tci-05 — Python 3.10 floor untested: requires-python >=3.10 but matrix runs 3.11–3.13 only

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** no
- **Metric:** 0% CI coverage on the minimum version the package claims to support; either add 3.10 to the matrix (+1 job cost) or raise the floor to 3.11 (truer, cheaper — decision for the owner).
- **Evidence:** `pyproject.toml:11` (>=3.10) + `:18-21` (3.10 classifier) vs `.github/workflows/ci.yml:19` (["3.11","3.12","3.13"]).
- **Dedup:** E-2-adjacent coverage gap; not a ledger/PX item.

## F-tci-06 — eval-smoke job duplicates the quality job's pip-install boilerplate

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** duplicate dependency resolution (~30–60s) on every eval-labeled run + a DRY violation in the workflow.
- **Evidence:** `.github/workflows/ci.yml:24-28` (quality setup) vs `:52-56` (identical block; job already `needs: quality` at :48).
- **Dedup:** CI config DRY; not in ledger/PX.

## F-tci-07 — fail-fast disabled in the quality matrix

- **Disposition:** WATCH · **Leverage:** P2 · **Simplification:** YES
- **Metric:** all 3 matrix jobs run to completion even when the first fails (~10–30% cost multiplier when failures are common); likely intentional (see-all-failures) — trade-off to decide alongside F-tci-04.
- **Evidence:** `.github/workflows/ci.yml:16-17` (`fail-fast: false`).
- **Dedup:** pure CI-cost observation.

## F-tci-08 — arm64 docker builds ride QEMU with no measurement or deferral rationale recorded

- **Disposition:** WATCH · **Leverage:** P2 · **Simplification:** no
- **Metric:** arm64-under-QEMU is typically 3–5× slower than amd64; runs only on v-tags so the cost is bounded, but no stated strategy (native runner, defer-until-demand, or accept).
- **Evidence:** `.github/workflows/docker.yml:28-30,53` (setup-qemu + platforms with no conditional).
- **Dedup:** distribution-choice observation; not in ledger/PX.

## F-tci-09 — No dependency vulnerability scan (pip-audit) in CI

- **Disposition:** BOOST · **Leverage:** P2 · **Simplification:** no
- **Metric:** ~10–30s per run to add; catches transitive CVEs pre-merge. Overlaps the PX-26 badge set's Dependabot intent — cheapest form could land earlier.
- **Evidence:** `.github/workflows/ci.yml` (no audit step); `pyproject.toml:64-73` (dev deps unscanned).
- **Dedup:** adjacent to PX-26 (pending machine-badge set incl. Dependabot) — this is the minimal in-CI form; prescription should COORDINATE with PX-26 rather than duplicate it.

## F-tci-10 — Release artifacts default to 90-day retention with no policy

- **Disposition:** WATCH · **Leverage:** P3 · **Simplification:** no
- **Metric:** minor storage accumulation per release (wheel + sdist).
- **Evidence:** `.github/workflows/release.yml:53-56` (upload-artifact@v4, no retention-days).
- **Dedup:** not in ledger/PX.

## F-tci-11 — No Windows CI runner despite Windows being the primary dev machine

- **Disposition:** KEEP · **Leverage:** P3 · **Simplification:** no
- **Metric:** Windows runners cost 2–3× Linux; the known Windows-specific issues (cp1252 console encoding, path separators) have been caught locally so far (e.g. the EV-3 UnicodeEncodeError). KEEP the Linux-only matrix pre-public; revisit on public user feedback.
- **Evidence:** `.github/workflows/ci.yml:15` (ubuntu-latest only); `docs/dev/RELEASE_CHECKLIST.md` window-8.5 EV-3 note.
- **Dedup:** platform-coverage decision already implicitly made by the project; recorded as KEEP with a revisit trigger.
