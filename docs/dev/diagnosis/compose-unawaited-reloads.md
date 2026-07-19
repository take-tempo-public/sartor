# Diagnosis — Compose user-action reloads fire `loadComposition()` un-awaited

> **Status:** root cause PROVEN by direct code read (a static, deterministic
> code-symmetry defect, not an intermittent runtime mystery) — the falsification
> test below independently confirms it is observable at the settle-gate level, not
> merely a code-reading conclusion.
> **Branch:** `fix/compose-unawaited-reloads`

---

## Symptom

`RELEASE_CHECKLIST.md`'s Carry-forward ledger (open item, filed 2026-07-12,
`fix/ci-first-linux-run`): several Compose user-action handlers call
`loadComposition()` without `await`, unlike the 5 auto-arrival-cascade call sites
that `fix/ci-first-linux-run` (commit `be48fec`) fixed for exactly this reason.
No known live flake is currently attributed to these specific sites — the item
was separately investigated and **exonerated** as the cause of the one known
chronic flake (`compose-summary-draft-settle-hole`, see that dossier's finding
F-2). This is a latent settle-gate consistency defect, tracked as its own ledger
row, not an active symptom being chased.

---

## Observed

**Fact 1 — `loadComposition()`'s definition and the settle-gate mechanism it
participates in.** `static/app.js:7122`, `async function loadComposition()`.
It fetches `/api/applications/<id>/composition`, rebuilds `#composeList`, fires
up to 4 background context-writing calls, then re-sets `data-compose-ready` and
restores scroll. The settle gate the UX test suite waits on is
`#composeList[data-compose-ready]:not([data-compose-bg-pending])` — see
`tests/ux/regression/test_20260706_compose_settle_bg_reload.py`'s module
docstring, itself citing the `_markComposeBgReload` counter mechanism.

**Fact 2 — `be48fec` (2026-07-12, merged via `fix/ci-first-linux-run`) proved,
for 5 specific call sites, that calling `loadComposition()` without `await`
breaks this invariant.** Commit message (`git show be48fec`, verbatim): *"The
five auto-arrival Compose fires … called `loadComposition()` fire-and-forget, so
`_markComposeBgReload(-1)` fired the instant the reload hit its first await —
before the drafted value repainted … Awaiting each reload keeps the counter
raised until the repaint lands."* That commit reproduced the resulting flake
under 8-core CPU saturation and confirmed 3/3 green with the fix. `git show
--stat be48fec` confirms the diff touched exactly `static/app.js`, adding
`await` at 5 call sites: `static/app.js:7396` (`_fireRecommendSummary`),
`:7450` (`_fireDraftSummary`), `:7506` (`_fireDraftGapFill`), `:7890`
(`_fireRecommendSkills`), `:8215` (`_fireRecommendExperienceSummaries`).

**Fact 3 — direct read of current `static/app.js` on this branch (`git diff
main` is empty at this point, unmodified) finds 9 additional call sites that
still call bare `loadComposition();`, all reached only from an explicit user
click, none touched by `be48fec`:**

| # | file:line | Enclosing function (confirmed `async` via grep) | Click handler that reaches it |
|---|---|---|---|
| 1 | `static/app.js:2845` | `_acceptRefinementProposal` (fallback branch) | `accept.onclick` on loop-back banner, `static/app.js:2822-2826` |
| 2 | `static/app.js:2853` | `_acceptRefinementProposal` (success branch) | same |
| 3 | `static/app.js:2854` | `_acceptRefinementProposal` (failure branch) | same |
| 4 | `static/app.js:2857` | `_acceptRefinementProposal` (catch branch) | same |
| 5 | `static/app.js:7689` | `_togglePositioningPin` | `row.onclick`, `static/app.js:7662` |
| 6 | `static/app.js:7916` | `_fireSuggestSkills` | `suggestBtn.onclick`, `static/app.js:7731` |
| 7 | `static/app.js:7963` | `_reviewPendingSkill` | `approve.onclick`/`deny.onclick`, `static/app.js:7941,7944` |
| 8 | `static/app.js:8024` | `_decideGapFill` | `accept.onclick`/`retire.onclick`, `static/app.js:7993,7998` |
| 9 | `static/app.js:8246` | `_addComposeRoleIntro` | `addBtn.onclick`, `static/app.js:8131` |

Grep confirmation that all 6 enclosing functions are already `async` (so the fix
is a pure `loadComposition()` → `await loadComposition()` edit, no signature
change needed):
```
2844:async function _acceptRefinementProposal(proposal) {
7671:async function _togglePositioningPin(summaryId, alreadyPinned) {
7902:async function _fireSuggestSkills(btn) {
7955:async function _reviewPendingSkill(skillId, approve) {
8006:async function _decideGapFill(key, decision) {
8225:async function _addComposeRoleIntro(expId) {
```

**Fact 4 — `RELEASE_CHECKLIST.md:953-976`'s own enumeration of what's left is
stale against current `main`.** It names `_fireSuggestSkills`,
`_togglePositioningPin`, `_addComposeRoleIntro`, and "the add-title /
apply-change handlers." `git blame static/app.js` on the "add-title" site
(`_addComposeTitlePrompt`, `static/app.js:8551`) shows it has been `await
loadComposition();` since commit `c988db3` (2026-07-06) — **already fixed**,
predating even `be48fec`. The checklist also omits 2 sites this session found:
`_reviewPendingSkill` (#7 above) and `_decideGapFill` (#8 above).

**Fact 5 — 3 additional un-awaited sites exist but are excluded from this
branch's scope** (`static/app.js:6549,6606,6932` — `_resumeIntoStep6`,
`_resumeIntoPreGenerateStep`, `wizardGoTo`): reaching them requires making
multiple currently-non-`async` intermediate frames (`resumeApplicationIntoWizard`,
the `onResume` handler) async-aware, and `wizardGoTo`'s single call site
(`:6932`) is reachable from a chained-async cascade tail
(`_fireRecommendThenCompose`, `static/app.js:1520`) **and** browser Back/Forward
(`_onWizardPopState`, `static/app.js:7044-7048`), not only direct clicks. This is
a materially different, larger shape of change than "add `await` inside an
already-`async` function" — recorded as a separate, narrower carry-forward item
rather than folded into this "low priority, own small pass" branch.

---

## Falsified

Nothing chased and killed on this branch — the defect above is a direct code
read (grep + git blame + git show), not a hypothesis reached by guessing at an
intermittent runtime symptom. There is no live flake currently attributed to
these sites to chase in the first place (see Symptom section — `F-2` in
`compose-summary-draft-settle-hole.md` already exonerated this class of call
site for the one known chronic flake).

---

## Inferred

**Hypothesis:** the same settle-gate race `be48fec` proved for the 5
auto-cascade sites — `_markComposeBgReload(-1)` firing at `loadComposition()`'s
first internal `await` instead of at its actual completion, letting the settle
gate read terminal over a stale/mid-repaint `#composeList` — applies identically
to the 9 user-action sites in Fact 3, since every one of them calls the exact
same `loadComposition()` function through the exact same
`_markComposeBgReload` bracket.

This is *unproven for these specific sites* until demonstrated, not merely
inferred from the auto-cascade case being superficially similar — the
Falsification section below is the experiment that closes that gap.

---

## Falsification

**The experiment that settles it. Run this BEFORE writing any fix.**

New test: `tests/ux/regression/test_20260718_compose_unawaited_reloads.py::test_decide_gap_fill_retire_reload_is_awaited`,
targeting `_decideGapFill`'s Retire path (`static/app.js:8024`, call-site #8
above — Retire chosen over Accept as the representative case: simpler
server-side write, no Bullet-row creation, same `_markComposeBgReload`
bracket shape).

**First attempt (recorded because it's an instructive dead end, not because it
worked): a naive row-absence check passed on unmodified HEAD.** Checking
whether the retired `.gap-fill-row` was still in the DOM the instant
`data-compose-bg-pending` cleared turned out to be a broken instrument, not a
real falsification: `loadComposition()` (`static/app.js:7139-7140`) calls
`list.removeAttribute('data-compose-ready')` then `_setLoadingPlaceholder`
(→ `_clearChildren`) **synchronously, before its own first internal `await`**
— so the old row is wiped from the DOM the instant `loadComposition()` is
merely invoked, whether or not the caller awaits it. Row-absence is true in
both the buggy and the fixed case; it cannot distinguish them. Corrected by
checking the actual settle-gate CONTRACT instead
(`ui_pages/selectors.py::Compose.SETTLED` =
`#composeList[data-compose-ready]:not([data-compose-bg-pending])`): capture,
synchronously inside the SAME `MutationObserver` callback that first observes
`data-compose-bg-pending` clear (no Python/Playwright round-trip in the
critical window), whether `data-compose-ready` is already back. If
`loadComposition()` is awaited, the counter cannot clear until the whole
function — including the re-add of `data-compose-ready` — has finished, so it
must already be present. If fire-and-forget, the counter clears the instant
the reload is merely kicked off, long before the delayed fetch below resolves.

Setup: delay ONLY `loadComposition()`'s own internal composition GET
(`blueprints.applications._read_composition_overrides`, called exactly once
in the whole app, from `get_application_composition` — cannot leak into the
undelayed `/gap-fill-decide` POST or any other route) by 0.5s via
`monkeypatch.setattr`.

- **If it fails on HEAD:** the hypothesis is confirmed for this representative
  site (and, by the identical-mechanism argument in `## Inferred`, for the
  other 8) — proceed to add `await` at all 9 in-scope call sites.
- **If it passes on HEAD:** the hypothesis is dead for this site. Stop, do not
  fix, and re-examine whether `_decideGapFill`'s specific response-handling
  shape differs from the auto-cascade sites in a way that already avoids the
  race.

**Result — FAILED on HEAD, as predicted** (run on this branch, unmodified
`static/app.js`, 2026-07-18):
```
tests/ux/regression/test_20260718_compose_unawaited_reloads.py::test_decide_gap_fill_retire_reload_is_awaited FAILED
AssertionError: settle gate reported 'not pending' while data-compose-ready was
still absent — loadComposition() is not awaited in _decideGapFill, so the
bg-pending counter cleared before the reload actually finished
assert False is True
 +  where False = evaluate('() => window.__bgClearedReadyState')
============================= 1 failed in 19.09s ==============================
```
No `pytest-rerunfailures` retry involved — single run, deterministic fail, no
traceback ambiguity. The server access log for this run shows
`POST /api/applications/1/gap-fill-decide` returning 200, with the (delayed)
`GET /api/applications/1/composition` for the reload it triggers not landing
until AFTER the assertion had already failed (visible only in the teardown
log) — direct confirmation the settle gate cleared before that reload
completed. **Hypothesis confirmed by direct observation, not inference.**

---

## The fix

Add `await` before `loadComposition()` at all 9 in-scope call sites (Fact 3
table above), mirroring exactly the pattern `be48fec` already established for
the 5 auto-cascade sites (all 6 enclosing functions are already `async`, so
this is a pure `loadComposition();` → `await loadComposition();` edit, no
signature changes, no other logic changes).

---

## Acceptance bar

- The new falsification test fails on `main` pre-fix (observed, not assumed)
  and passes after `await` is added at all 9 in-scope call sites (Fact 3 table).
- No `pytest-rerunfailures` retry involved in either the fail-on-HEAD or the
  pass-after-fix result — a fail-fail-pass reported as a bare `PASSED` is not
  evidence.
- Full `pytest -m ux` regression/a11y/flows tiers stay green, aside from the
  already-characterized, unrelated scroll-restore flake (confirm clean on
  isolated re-run if it recurs; do not re-chase it here — see
  `docs/dev/diagnosis/ux-scroll-position-flake.md`).
- `python -m scripts.gate` green.
