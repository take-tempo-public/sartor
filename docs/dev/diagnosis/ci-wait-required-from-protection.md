# Diagnosis — `ci_wait` reported GREEN while 4 of 6 protected contexts were pending

> **Status:** root cause PROVEN — observed in the live watch log (item 109) and reproduced
> against the real `_run()` by a test that fails on HEAD.
> **Branch:** `fix/ci-wait-required-from-protection`

---

## Symptom

`python -m scripts.ci_wait 135` printed `ci-wait: GREEN (exit 0)` on PR #135 (head
`865f714`, 2026-09-22) while `Lint, type-check, test (py3.11/3.12/3.13)` and
`UX / a11y / PDF (Playwright, py3.12)`, all four required by branch protection, were still
pending. `ci_wait` is the sanctioned merge gate (AGENTS.md close-out step 4), so a false
exit 0 is a false merge authorization.

---

## Observed

- Item record `docs/dev/work/items/0109-ci-wait-required-set-from-registered-checks.md`
  (filed from the live PR #135 session): `gh pr checks 135 --watch --required` listed
  **only** the four `Analyze (…)` jobs on every refresh. Its final report put the four
  lint/UX jobs under "advisory (reported, never gating)" as `pending`. A minute later,
  `gh pr checks 135 --required` listed all six.
- The required set comes from registered checks only: `scripts/ci_wait.py:353`
  (`required = _gh_checks(pr_args, required=True)`), and `--required` itself is gh's
  view of *registered* check runs. Every non-required registered row is then reported
  as advisory (`scripts/ci_wait.py:355-356`).
- Branch protection lists six contexts, read 2026-09-22 with
  `gh api "repos/{owner}/{repo}/branches/main/protection/required_status_checks"`:

  ```
  {"strict":true,"contexts":["Lint, type-check, test (py3.11)","Lint, type-check, test (py3.12)",
   "Lint, type-check, test (py3.13)","UX / a11y / PDF (Playwright, py3.12)",
   "Analyze (javascript-typescript)","Analyze (python)"], ...}
  ```

- Reproduction on HEAD (`b48dc70`): `python -m pytest tests/test_ci_wait.py -k Protection`
  → `FAILED …::TestRunVerdictAgainstProtection::test_pr135_shape_is_not_green`. `_run`
  printed the same shape item 109 recorded (four `Analyze` rows under `required (final)`,
  four `pending` rows under `advisory`), then `no absorbed reruns found`, and returned
  `EXIT_GREEN`. The call phase took 0.03 s (`--durations`), so the fakes were in use. The
  ~10–16 s setup is the suite's first-test session setup, which existing tests like
  `TestClassify::test_all_pass_is_green` pay too (9.28 s).

- **After the fix, live and read-only** (2026-09-22,
  `python -m scripts.ci_wait 135 --no-rerun-scan --timeout-minutes 2`, merged PR #135):
  the first line was `ci-wait: 6 required context(s) from branch protection on PR #135`,
  followed by the six names. `required (final)` held all eight rows (6 contexts, the two
  `Analyze` names twice each), all `pass`. The verdict was `ci-wait: GREEN (exit 0)`. So
  the protection read works against the real API with the maintainer's token.
- **A side finding from the same run:** piped through `Select-Object`, the wrapper's own
  announce lines printed *after* `gh --watch`'s output. Python block-buffers a piped
  stdout, while the un-captured `gh` child writes directly. Fixed by `flush=True` on the
  pre-watch line. This is a readability issue, not a verdict issue.

---

## Falsified

_(Nothing — the mechanism was read off the live log, not guessed.)_

---

## Inferred

_(Nothing. No part of the mechanism rests on inference.)_

---

## Falsification

`TestRunVerdictAgainstProtection::test_pr135_shape_is_not_green` replays PR #135's
payloads through the real `_run()` and asserts the verdict is not `EXIT_GREEN`.

- **If it fails on HEAD:** confirmed. It did fail (see Observed); it is committed as
  `xfail(strict=True)` and the fix commit removes the marker.
- **If it passes on HEAD:** the mechanism is wrong. That is not what happened.

---

## The fix

"Required" becomes branch protection's context list for the PR's base branch, fetched
once per run. A protected context with no registered row counts as `pending`, and
`_run` re-enters `gh pr checks --watch` until every protected context has a verdict or
the deadline expires. If the protection rule can't be read, the result is `EXIT_ERROR`
("unknown"), never green. Exit codes are unchanged.

**Consumers of the exit-code contract** (unchanged, so none need an edit):
`scripts/flake_rates.py:139`, which imports only `scan_reruns` (untouched), and the
prose descriptions in AGENTS.md step 4, `docs/dev/AGENT_HANDOFF_TEMPLATE.md` and
`docs/governance/charter.md`.

### Deferred (with reason)

- **AGENTS.md step 4 and the TEMPLATE's verbatim close-out block were left unedited.**
  The plan proposed adding "required = branch protection's contexts" to both. On reading
  them, neither sentence ("exits 0 only when every required check passed") is false after
  the fix. The definition of "required" now lives in `scripts/ci_wait.py`'s module
  docstring, which the charter's extract-don't-restate rule makes its one canonical
  home. Editing the TEMPLATE's verbatim block would also force every future handoff's copy
  to change, a C-10-gated contract edit this fix doesn't need.

---

## Acceptance bar

- The reproduction passes with no `xfail` marker.
- New `_run` cases cover three paths: missing-then-registered → GREEN, still missing at
  the deadline → 8, protection unreadable → 2.
- A live read-only `python -m scripts.ci_wait 135` lists all six protected contexts as
  required.
- This branch's own PR is watched by the fixed tool, and the first announce line lists
  six required contexts.
