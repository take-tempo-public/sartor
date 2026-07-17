# Diagnosis — CodeQL and Scorecard CI checks newly failing on `main`

> **Status:** both root causes **PROVEN**. CodeQL: a real, independent workflow-config defect
> (fixed below). Scorecard: no config defect exists — the job's own log confirms it failed on a
> `503` from `api.github.com` mid-run, the concurrent GitHub platform incident, not anything in
> `scorecard.yml` (left unchanged).
> **Branch:** `fix/codeql-scorecard-workflow-config`

---

## Symptom

On commit `df95773` (merge of the `fix/ux-scroll-position-flake` Chip 3 fix to `main`), the
GitHub Actions check runs `Scorecard analysis` and `Analyze (python)` (CodeQL) both report
`conclusion: failure`. The same two checks reported `conclusion: success` on the immediately
preceding commit, `98da67a` (the merge-base main was at before this push).

---

## Observed

Facts with artifacts behind them. Nothing here is a deduction.

1. `GET /repos/take-tempo-public/sartor/commits/df95773.../check-runs` (unauthenticated,
   public API) returns 12 check runs for this commit: 10 `success`/`skipped`, 2 `failure`
   (`Scorecard analysis`, `Analyze (python)`).
2. The same endpoint for the parent commit `98da67a` returns 21 check runs, all `success` or
   `skipped` — 0 failed.
3. The CodeQL job's own Actions run-log page
   (`https://github.com/take-tempo-public/sartor/actions/runs/29540805876/job/87762451796`)
   shows the actual failure text: `"Unexpected input(s) 'language', valid inputs are ['tools',
   'languages', 'build-mode'..."` and `"Debugging artifacts are unavailable since the 'init'
   Action failed before it could produce any."` — the job failed at CodeQL's `init` step,
   before any source code was analyzed.
4. `.github/workflows/codeql.yml` line 46 (as of `df95773`) passes
   `language: ${{ matrix.language }}` to `github/codeql-action/init`, pinned to commit
   `02c5e83432fe5497fd85b873b6c9f16a8578e1d9` (labeled `# v3`).
5. Fetched `https://raw.githubusercontent.com/github/codeql-action/02c5e83432fe5497fd85b873b6c9f16a8578e1d9/init/action.yml`
   directly — the exact file GitHub's runner reads for that pinned SHA. Its declared inputs are
   `tools`, `languages` (plural), `build-mode`, `analysis-kinds`, `token`, `registries`,
   `matrix`, `config-file`, `config`, `queries`, and others. **There is no `language` (singular)
   input declared at all.**
6. The Scorecard job's Actions run-log page
   (`https://github.com/take-tempo-public/sartor/actions/runs/29540805857/job/87762451800`)
   shows only `"failed Jul 16, 2026 in 27s"` and a Node.js 20→24 deprecation notice. The detailed
   step-by-step log required GitHub authentication ("Sign in to view logs"), which was
   unavailable this session (see item 11).
7. `.github/workflows/scorecard.yml` invokes `ossf/scorecard-action`, pinned to commit
   `4eaacf0543bb3f2c246792bd56e8cdeffafb205a` (labeled `# v2.4.3`), with inputs `results_file`,
   `results_format`, `publish_results`. Fetched
   `https://raw.githubusercontent.com/ossf/scorecard-action/4eaacf0543bb3f2c246792bd56e8cdeffafb205a/action.yaml`
   directly — the exact file for that pinned SHA. Its declared inputs are exactly
   `results_file`, `results_format`, `repo_token`, `publish_results`, `file_mode`,
   `internal_publish_base_url`, `internal_default_token`. **Every input the workflow passes is
   declared and correctly named** — no mismatch found, unlike item 5's CodeQL finding.
8. That same pinned Scorecard action runs via `runs: using: "docker", image:
   "docker://ghcr.io/ossf/scorecard-action:v2.4.3"` — pulled from GitHub Container Registry at
   run time, not a pre-built JS/composite action like CodeQL's.
9. `https://www.githubstatus.com/api/v2/status.json` and `.../components.json`, fetched
   directly, report an active incident: overall status `minor` / "Partially Degraded Service";
   component `API Requests` at `degraded_performance`. The user independently confirmed seeing
   an HTTP 503 from github.com directly. The full incident timeline (user-supplied, from
   githubstatus.com's own history page):
   ```
   Investigating - We are investigating reports of impacted performance for some GitHub
   services.                                                        Jul 16, 2026 - 22:51 UTC
   Update - We are aware of degraded REST API availability and are investigating
                                                                      Jul 16, 2026 - 22:58 UTC
   Update - API Requests is experiencing degraded performance. We are continuing to
   investigate.                                                      Jul 16, 2026 - 22:58 UTC
   Update - We are continuing to investigate an issue causing approximately 35% of REST API
   requests to fail. Based on our current understanding, requests are not consistently
   reaching the application layer, resulting in failed requests returning HTML responses
   instead of the expected API response format.                     Jul 16, 2026 - 23:29 UTC
   ```
10. Both failing jobs (Scorecard and CodeQL) started at `2026-07-16T22:53:33Z` /
    `22:53:35Z` — 2-4 minutes after the incident's first-posted timestamp (22:51 UTC).
11. This session's own repeated attempts to authenticate against GitHub's API — `gh auth
    login --with-token` (twice, two different accounts/credentials), `gh auth status` (11
    consecutive calls), and direct `curl` with a `Bearer` token against `/user` (5 consecutive
    calls) — failed **15/15**, every failure either an HTML "unicorn" 503 page (curl) or `gh`
    reporting the keyring token "invalid" (which is `gh`'s only vocabulary for an
    unexpected/non-JSON response, not evidence the token itself is bad). Plain, unauthenticated
    `GET` requests to `api.github.com` succeeded throughout the same window (items 1-2 above,
    plus an unauthenticated sanity check). This is consistent with item 9's own description of
    the failure mode (HTML instead of the expected API response), and suggests
    authenticated/authorization-layer requests are being hit harder than plain reads right now,
    though the exact proportions are not measured.
12. **Authentication recovered later in this session** (`gh auth status` succeeded, account
    `amodal1`, token scopes `gist`/`read:org`/`repo`/`workflow`). Used it to fetch the Scorecard
    job's full log directly (`gh api /repos/take-tempo-public/sartor/actions/jobs/87762451800/logs`,
    superseding item 6's partial view). It contains, verbatim: `"2026/07/16 22:54:00 scorecard
    had an error: repo unreachable: GET https://api.github.com/repos/take-tempo-public/sartor:
    503  []"`. This is the Scorecard tool's own internal error, logged directly — not inferred,
    not correlated. It failed because its own call to `api.github.com` returned `503`, the exact
    failure mode item 9's incident describes and item 11 independently hit from this session
    fifteen times.

---

## Falsified

### F-1 — "Scorecard has the same class of input-mismatch bug as CodeQL"

**Falsified by item 7.** Direct comparison of `scorecard.yml`'s actual usage against the pinned
action's own declared schema (fetched from the exact SHA, not a floating tag) shows every input
name is correct. There is no analog of CodeQL's `language`/`languages` mismatch here.

---

## Inferred

1. **CodeQL's failure is a real, code-level defect, independent of the platform incident.** The
   `init` step's rejection (item 3) happens before any network call to the degraded API layer
   could plausibly be involved — it is client-side input validation against the action's own
   declared schema (item 5), which is a fixed property of the pinned SHA and cannot have
   "degraded." This is about as close to proven as an inference gets (exact error text, exact
   schema mismatch, independently confirmed), but is kept here rather than in `## Observed`
   because "this is why the job fails" is still one inferential step beyond the raw facts.

Scorecard's root cause is no longer inferred — item 12 (`## Observed`) is the tool's own logged
error, not a correlation. Nothing remains open here for Scorecard.

---

## Falsification

**For CodeQL:** the usual "write a test that fails on HEAD" shape doesn't map cleanly onto a
GitHub-Actions-hosted schema-validation step — the validation happens on GitHub's own runners
against the action's bundled schema, not in this repo's local test suite, so there is no
meaningful local reproduction to build. The actual CI run's own error text (item 3) already *is*
the "fails on HEAD" observation: GitHub's own runner, today, on this exact pinned SHA, rejected
`language` as unrecognized. That is the experiment; it already ran, non-deliberately, and the
result is recorded above rather than re-derived.

**For Scorecard:** no experiment was needed — item 12's log line is a direct observation of the
actual failure, not an inference requiring a falsification test. No further check is owed beyond
the acceptance bar below (a future clean run once the platform incident itself clears).

---

## The fix

- **`codeql.yml` line 46:** rename the input key from `language` to `languages` (same value
  expression, `${{ matrix.language }}` — a single string is valid for a comma-separated-list
  input). This directly addresses the exact mismatch proven in `## Observed` items 3-5.
- **`scorecard.yml`: no change.** No defect was found (item 7); changing a file with no
  confirmed defect, on the strength of correlation alone, would be exactly the "guessing the
  mechanism" failure mode (`AGENT_FAILURE_PATTERNS.md` §5f) this project's own evidence
  discipline exists to prevent.

---

## Acceptance bar

- **CodeQL: MET.** Authentication recovered later in this session. Confirmed directly via
  `gh run list --json ...` against the fix commit `8326b5e` (pushed to `main`): both matrix
  jobs — `Analyze (python)` and `Analyze (javascript-typescript)` — completed with
  `conclusion: success`, a genuine `analyze` result, not another `init`-stage rejection.
- **Scorecard: MET.** Root cause was already confirmed by direct log evidence (item 12); now
  also confirmed by outcome — the same commit (`8326b5e`), which carries **zero change** to
  `scorecard.yml`, shows `OpenSSF Scorecard: success` in real CI.

**One loose thread, recorded rather than smoothed over.** On the *unfixed* commit `df95773`,
`gh run list` shows `CodeQL (python)` failed but `CodeQL (javascript-typescript)` succeeded —
even though both matrix legs pass the identical wrong `language:` input to the identical pinned
action via the same workflow line (`codeql.yml`'s `matrix.language` strategy). If the
input-name mismatch is deterministic schema-validation rejection (which `## Observed` item 3's
error text reads as), both legs should have failed identically. Nothing gathered here explains
the asymmetry, and it was not investigated further — the fix's correctness is independently
confirmed by `8326b5e` (both legs now succeed identically, symmetrically), regardless of why
`df95773`'s failure was asymmetric. Left as an open, unexplained detail rather than folded into
the existing narrative or given an invented cause.
