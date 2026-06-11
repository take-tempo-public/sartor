<!--
  SUPERSEDED HISTORICAL ARTIFACT — the fold-in promised below happened on
  2026-06-08: RELEASE_ARC.md §Phase 4.5 now carries the sprint decomposition
  (6.0–6.6 + WS-4) and is the single source of truth. This copy is preserved
  in excellence-walk/ as raw walkthrough source for the WS-4a wiki ingest;
  it may retire into the wiki's raw/ layer afterwards. Do not plan from it.
  (The original header claimed a gitignored output/ location — it was
  promoted into git with the rest of excellence-walk/ on 2026-06-08.)
-->

# callback. — v1.0.5 walk-through → sprint plan (working copy)

> **Status:** SUPERSEDED (2026-06-10). Folded into `RELEASE_ARC.md` §Phase 4.5 +
> `RELEASE_CHECKLIST.md` on 2026-06-08 — **plan from those, not this file.**
> Kept as preserved excellence-walk raw source (per the WS-4a ingest plan);
> the §2 24-item findings table remains the v1.0.5-walk numbering (#1–#24)
> that RELEASE_ARC references. Captured 2026-06-07.
> **Source:** the 24-item walk-through + RELEASE_ARC / RELEASE_CHECKLIST /
> V1_0_5_VERIFICATION reconciliation done this session.

## Context

The v1.0.5 UI/UX redesign stream landed all ten of its planned branches, after
which a real walk-through began. That walk-through has already produced four
merged fixes (`refactor/needs-onboarding-200-on-reads`,
`fix/retire-legacy-import-onboarding`, `feat/auto-open-browser`,
`feat/grounding-scorers-in-console`) and is now mid-way through the
**"finish the faceplate" arc**. The user did a first full walk-through, hit a
set of blockers we resolved, and has now handed over **24 UX findings** plus a
request to reconcile them against `RELEASE_ARC.md` / `RELEASE_CHECKLIST.md` /
`V1_0_5_VERIFICATION.md` so nothing was lost across the redesign sprints, then
decompose the result into topical sprints → sequential git-branch mini-sprints
(our "each agent does one branch, then writes the next-agent handoff" method).

**Cut-line decisions (user-confirmed):**
1. **v1.0.5 = finish the faceplate arc, then tag.** Items #14/#19 *are* that arc.
2. **#9 + #10 are v1.0.5 blockers** — they are regressions in features v1.0.5
   itself shipped (`feat/wysiwyg-option1`, `feat/step6-redesign`) and undercut the
   core value prop; fix before the tag.
3. **Education (#18/#22) = full sweep in one release** — every tab + every panel +
   diagnostics get plain-language, non-technical, a11y-safe summaries.
4. **All remaining walk-through items = one combined v1.0.6.** ("at most v1.0.7,
   more will surface before v1.1.0" — so v1.0.7 is the spill valve, not a
   pre-commitment.)
5. **Onboarding IA = corpus-first + smart landing.** Career corpus becomes **tab 1**
   and the landing tab for users with an **empty** corpus; **Tailor becomes tab 2**
   and the landing tab for users who **already have** a corpus. Finishing corpus
   review hands off forward with a "Start tailoring →" CTA. This is the domain-true
   model (corpus = source of truth; tailoring = consumer) and it fixes the #1
   dead-end by making the hand-off a *forward* step, not a "find your way back."
   The #7 Compose→corpus writeback (Sprint 6.1) is the orthogonal "tailor improves
   the corpus over time" half and rides on top of this IA. *(Chosen over
   import-into-Tailor, which would have revived the wizard corpus step B1
   deliberately retired and split import across two surfaces.)*

`V1_0_5_VERIFICATION.md` is the **unsigned** release-cut evidence checklist (empty
sign-off block). The walk-through is effectively the user executing its Part D;
several findings *contradict* its "should-work" checks (#9 ↔ D §3 WYSIWYG parity;
#10 ↔ D §2 "edit-raw modal edit → preview updates"). Running it end-to-end and
signing it off is therefore a **v1.0.5 tag gate**, and any further failures it
surfaces feed the same v1.0.6 buckets below.

---

## 1. What's left before v1.1.0 (macro view)

| Stage | Work | Owner / gate |
|---|---|---|
| **Finish v1.0.5** | Faceplate arc tail (3 branches) + #9/#10 blocker fixes + run & sign `V1_0_5_VERIFICATION.md` + version bump/tag | Sprints V5-A / V5-B |
| **v1.0.6** | The 24 walk-through items (minus #9/#10/#14/#19) as topical sprints | Sprints 6.1–6.5 |
| **v1.0.7 (pre-public hardening)** | Scheduled as **Sprint PV** below: (a) the never-run **v1.0.4 live shakedown** → real `annotations.json` labels; (b) grounding **calibrated layers (B)** — calibrate L0/L1/L2 against those labels + report it on the eval suite/tuning gate; (c) `generate_cover_letter` **opener tuning** (shares the corpus-rebuild prereq); (d) **type-annotation scan** of the whole post-v1.0.4 stream | `PRODUCT_SHAPE.md` §10 "Post-v1.0.5"; RELEASE_ARC v1.1.0 criteria |
| **v1.1.0 (public)** | `release/visual-assets` (screenshots/demo gif against the redesigned UI) → `release/fresh-clone-v1-1-0` (<5 min) → `chore/release-v1.1.0` (create GitHub repo, push, tag) | **user-owned tag**; RELEASE_ARC Phase 5 |

**Not blocking v1.1.0 (already deferred to v1.1/v2, leave parked):** master-résumé
operationalization + `PersonaTemplate.is_default` resolver (v1.1, PRODUCT_SHAPE
§9/§10); template field-filter chips (v1.1); `Dockerfile` (v1.1); paged.js
root-cause elimination (v2). The 5 `V1_0_5_VERIFICATION` "Known-deferred" items are
explicitly **not** regressions — do not re-open them.

---

## 2. The 24 walk-through items, mapped

Legend: **V5** = blocks the v1.0.5 tag · **6.x** = v1.0.6 sprint · **arc** = already
planned in RELEASE_ARC.

| # | Finding (short) | Bucket | Notes |
|---|---|---|---|
| 14 | Quality/Groundedness show a CLI script, not a button | **V5-A** (arc) | = `feat/run-eval-from-console` (NEXT). Not new. |
| 19 | Tuning interface is a dead-end | **V5-A** (arc) | = `feat/tuning-tab-ab`. Not new. |
| 17 | No instructions to install/prepare the tuning/grounding/eval stack | **V5-A** + **6.5** | discoverability doc in arc; install guide in 6.5. |
| 9 | Download formatting ≠ preview | **V5-B** | regression in `feat/wysiwyg-option1`. |
| 10 | Step-6 edit not reflected in preview | **V5-B** | regression in `feat/step6-redesign`. |
| 6 | "Continue to clarify" asks the same clarify/skip twice | **6.1** | feels broken; should initiate clarify directly. |
| 4 | JD analysis not resumable after exit | **6.1** | extends `feat/prior-app-resume` to non-Step-6 states. |
| 24 | Prior-app cards: one resumable/one not; "about the job" empty; "N pending" pill opaque | **6.1** | same prior-app/resumability branch as #4. |
| 7 | Step 3: add an alternative title, **sourced into corpus** | **6.1** | corpus-integrated, not a jump-out. |
| 8 | Step-4 copy "different typography and layout" — still true? | **6.1** | verify templates differ; correct copy if not. |
| 11 | Cost panel tooltip says "Total" but plots the mean | **6.2** | dashboard chart bug. |
| 12 | Calls panel needs to be wider (horizontal scroll) | **6.2** | dashboard layout. |
| 13 | Latest-trace bars look empty — scale needs fixing | **6.2** | dashboard chart scale. |
| 3 | ~150 form fields missing `id`/`name` (a11y/autofill) | **6.3** | + add the never-shipped axe a11y gate. |
| 21 | Required fields un-asterisked; auto-populatable inputs should be dropdowns | **6.3** | reusable form pattern. |
| 2 | Corpus "Add variant" referenced in copy but no affordance | **6.3** | `SummaryItem` exists (migration 0004); surface it. |
| 5 | Expand/collapse tick arrows ~imperceptible (+50%) | **6.3** | small CSS. |
| 16 | Move Career corpus to first tab; start onboarding there | **6.4** | corpus-first IA (decision #5). |
| 1 | First-time flow dead-ends after corpus import; wants per-tab hover summaries | **6.4** + **6.5** | dead-end fixed by the corpus-first hand-off in 6.4; hover summaries in 6.5. |
| 23 | Logo click should route to main page with no user chosen | **6.4** | small nav fix. |
| 15 | Annotate verdict drop-downs (fabricated/fix/omit) have no legend/explanation | **6.5** | education on the annotate surface. |
| 20 | Annotate: auto-expand bootstrap when none exist; username → dropdown; copy too technical | **6.3** (dropdown) + **6.5** (copy/auto-expand) | dropdown rides the 6.3 pattern. |
| 18 | Educate where/when needed; per-tab + per-panel, a11y-safe | **6.5** | the full-sweep driver. |
| 22 | Every tab + section needs a plain-language summary (incl. diagnostics) | **6.5** | the full-sweep driver. |

---

## 3. What's still open in the arc/checklist for v1.0.5 and earlier

**v1.0.5 (RELEASE_CHECKLIST "Discovered during the v1.0.5 stream"):**
- Faceplate arc — Step 1 shipped (`feat/grounding-scorers-in-console`); **remaining**
  `feat/run-eval-from-console` (NEXT) → `feat/tuning-tab-ab` →
  `docs/tuning-loop-discoverability`. → **Sprint V5-A.**
- Grounding **calibrated layers (B)** — intentionally deferred **pre-v1.1.0** (no
  labeled data exists; `evals/fixtures/real/` empty). → macro table, not v1.0.6.
- **Compose bullet-order reverts on reload** when an experience has *no* LLM
  recommendations (`_dropoffPick` re-sorts by score; persisted order is correct and
  `generate()` honors it). Tracked, small render-path fix. → **Sprint 6.1**
  (`fix/compose-order-no-recommendations`).

**Earlier versions (carryover):** the v1.0.1 "Should do" items all migrated into the
v1.0.5 stream and shipped (step6 redesign, playwright suite, prior-app resume,
template pagination, etc.). The only un-checked carryovers are **owner-v1.1.0**:
"Push to GitHub + verify URL" and "Visual assets" — both correctly parked for the
public release.

---

## 4. Sprint → branch decomposition

> Method (per `docs/dev/AGENT_HANDOFF_TEMPLATE.md` + AGENTS.md): **one branch per
> agent session**, strictly sequential. Each closing agent: gate green
> (`ruff` + `mypy` + `pytest` [+ `pytest -m ux`]) → commit → ask before merge to
> `main` → write the next-agent handoff prompt as the last act. Branch off `main`.
> Every new Flask route gets `_safe_username()` + `_within()` + `secure_filename()`.

### Sprint V5-A — Faceplate arc completion (tag-blocking; verbatim from RELEASE_ARC §Phase 4)
1. **`feat/run-eval-from-console`** *(NEXT — running now)* — extract a `run_suite(...)`
   core from `runner.main()` (optional `progress` cb; default path byte-identical) +
   a localhost SSE `POST /api/eval/run`; "Run eval" affordance on the Quality tab;
   replace collate's copy-the-command dead-end with a "Run this fixture" button.
   **Closes #14.** Files: `evals/runner.py`, `app.py`, `dashboard/templates/dashboard.html`.
2. **`feat/tuning-tab-ab`** — replace the Tuning stub with an in-browser A/B: pick an
   `analyzer._BASE_SYSTEM_PROMPTS` constant, draft/paste a candidate, run
   baseline+candidate evals (reuse `analyzer.prompt_overrides()` + `evals/tune.py`
   delta table). **Promote stays the agent's job** — no route edits `analyzer.py`.
   **Closes #19.** Depends on branch 1's `run_suite`.
3. **`docs/tuning-loop-discoverability`** — docs only; advertise the interactive loop
   in the diagnostics modal copy + `walkthrough.md` / `evals/README.md` /
   `GROUNDING_METRIC.md` "B (deferred)" note. (Partial #17.)

### Sprint V5-B — WYSIWYG/Step-6 correctness (tag-blocking; NEW)
4. **`fix/wysiwyg-download-parity`** — **#9**. Investigate the download↔preview
   divergence: `.pdf` should equal the paged.js preview; `.docx` should match the
   persona style. Surfaces: the `md_to_json_resume()` cache from
   `feat/wysiwyg-option1`, the preview route, `generator.py` `_write_docx()` (must
   open the template, never blank `docx.Document()`), `pdf_render.py`,
   `/api/download-edited`. Add a `tests/ux/regression/test_<date>_wysiwyg_parity.py`.
5. **`fix/step6-edit-reflects-preview`** — **#10**. Step-6 edit-raw modal edits must
   re-render the preview (refresh the cached JSON Resume + reload the iframe).
   Surfaces: `static/app.js` Step-6 edit/preview handlers; the same cache as #9.
   *(May share a root cause with #4's branch — the executing agent confirms during
   investigation and merges only if genuinely one fix; default is two branches.)*

   Then: **run `V1_0_5_VERIFICATION.md` Part A–D end-to-end on a real corpus, fill
   the sign-off block**, then **`chore/version-bump-v1.0.5`** (pyproject version,
   CHANGELOG `[Unreleased]` → `[1.0.5]`, tag). This is the v1.0.5 gate.

### Sprint 6.1 — Wizard flow correctness
6. **`fix/clarify-double-question`** — **#6**. Collapse the duplicate clarify/skip
   prompt; "Continue to clarify" initiates clarification directly. `static/app.js`
   Step-2 flow + the clarify route call sequence.
7. **`feat/prior-app-resume-robustness`** — **#4 + #24**. Resume an application from
   the most-advanced state with data even when generation never ran (today
   `feat/prior-app-resume` assumes Step 6); add JD **title/company** summary to
   prior-app cards (currently "about the job" is empty); relabel/explain the
   "N pending" pill (or remove if meaningless on that surface). `static/app.js`
   prior-apps panel + the application/runs read path.
8. **`feat/compose-add-title`** — **#7**. Add an alternative title in Step 3 that is
   **written into the corpus** (so it is sourced, not a context-only override).
   Reuse the corpus add-title write path; new affordance in the Compose card.
9. **`fix/compose-order-no-recommendations`** — tracked v1.0.5 deferred bug: honor
   the GET array order on the no-recommendations fallback in `_renderComposeCard`
   instead of re-sorting by score (`_dropoffPick`). Add a regression test.
10. **`fix/step4-template-copy`** — **#8**. Verify the four bundled templates
    actually differ in typography/layout; correct the Step-4 copy to match reality
    (and log a finding if they don't differ as claimed). Mostly `templates/index.html`.

### Sprint 6.2 — Diagnostics console correctness
11. **`fix/diagnostics-chart-corrections`** — **#11 + #12 + #13** (one branch, three
    small fixes on the same surface): cost tooltip "Total" must plot the sum not the
    mean (#11); calls panel widens / no horizontal scroll when expanded (#12);
    latest-trace bar chart axis rescaled so populated bars are visible (#13).
    `dashboard/routes.py` aggregators + `dashboard/templates/dashboard.html` +
    chart config.

### Sprint 6.3 — Forms, affordances & a11y
12. **`fix/form-field-labels-a11y`** — **#3**. Add `id`/`name` (+ associated
    `<label>` / `aria-label`) to the ~150 flagged fields across the redesigned
    surfaces; **add the never-shipped `tests/ux/a11y/test_axe_smoke.py`**
    (`@axe-core/playwright`, no serious/critical violations) so this can't regress.
    Land this **early** so the gate guards every later v1.0.6 branch.
13. **`feat/required-field-and-dropdown-pattern`** — **#21 + #20(dropdown)**. A
    reusable required-field marker (red asterisk + `aria-required`) and a convention
    for converting auto-populatable inputs to dropdowns; apply to the annotate
    **candidate username → dropdown of existing users** as the first consumer.
14. **`fix/corpus-affordance-polish`** — **#2 + #5**. Surface the corpus
    **Add-variant** control (the `SummaryItem` model exists; copy already promises
    it) and fix the misleading empty-state copy; enlarge the expand/collapse tick
    arrows ~50% (CSS). `static/app.js` corpus render + `static/style.css`.

### Sprint 6.4 — Information architecture + onboarding
15. **`fix/logo-home-route`** — **#23**. Logo click routes to the main page with no
    user selected. Small `static/app.js` + `templates/index.html`.
16. **`feat/corpus-first-tab-onboarding`** — **#16 + #1(deadend)**, decision #5
    (corpus-first + smart landing). Reorder the top tabs to **Career corpus (1) →
    Tailor (2) → Résumé templates → Candidate memory**. **Smart landing on
    user-select:** land on **Corpus** when the corpus is empty, on **Tailor** when it
    is non-empty (reuse the existing empty signal — `needs_onboarding` /
    pending-counts / experiences list read in `onUserSelect`). After résumé import +
    bullet/title review, show a **"Start tailoring →"** hand-off CTA into Tailor
    (replaces the dead-end). Keep the inverse "Go to Career corpus" CTA
    (`_renderCorpusEmptyCTA`) intact for the empty-Tailor edge case. Touches the
    top-tab order/handlers + default-tab logic (`templates/index.html`,
    `static/app.js` `switchTopTab` / `onUserSelect`, `ui_pages/selectors.py` tab
    registry). Add a UX regression test for the smart-landing + hand-off. Land
    **before** the education sweep (6.5) so per-tab summaries are written against the
    final order. *(Does NOT revive a wizard corpus step — import stays on the Corpus
    tab; this is the import-into-Tailor path we explicitly rejected.)*

### Sprint 6.5 — In-app education (full sweep) + install docs
17. **`feat/help-pattern-component`** — build the **reusable a11y-safe help primitive**
    once: a per-tab description + per-panel summary + contextual tooltip/inline help
    that is screen-reader-safe (no color-only meaning; real `aria` wiring). No content
    yet — just the mechanism + tokens, with one worked example.
18. **`feat/education-tailor-corpus-wizard`** — apply the pattern across Tailor,
    Career corpus, Résumé templates, Candidate memory, and each wizard step
    (incl. #1's per-tab hover summaries). Plain-language, assumes **no** technical
    background (the lay-person through-line: artist/retail/trades, not just engineers).
19. **`feat/education-diagnostics-annotate`** — apply the pattern across all
    diagnostics tabs **and** the annotate tab: the **verdict legend** + per-option
    tooltips (keep/fix/omit/fabricated and `failed_rules`) (#15), the annotate
    instructions rewritten for lay users + **auto-expand the bootstrap panel when no
    fixtures exist** (#20), and a summary on every diagnostics panel (#22).
20. **`docs/eval-stack-install-guide`** — **#17**. A user-facing install/prepare guide
    for the tuning/grounding/eval stack (lift the verified PowerShell steps from
    `V1_0_5_VERIFICATION.md` Setup) + an in-app pointer where the stack is needed.

    Then: **`chore/version-bump-v1.0.6`** (pyproject, CHANGELOG, tag) + re-check the
    RELEASE_CHECKLIST evergreen risk register.

### Sprint PV — Pre-v1.1.0 hardening + grounding calibration (→ v1.0.7)
> The pre-public obligations from `PRODUCT_SHAPE.md` §10 "Post-v1.0.5" + the
> RELEASE_ARC v1.1.0 tag criteria, scheduled as real branches. PV-1→PV-2→PV-3 share
> one human prerequisite and chain on real-data labels; PV-4 is independent.

**Shared prerequisite (human, not a branch):** a **clean-corpus rebuild from a real
git _clone_** — NOT a folder copy, which drags the gitignored `db/resume.sqlite` —
then regenerate the corpus from real JDs. Required by PV-1/PV-2/PV-3
(`PRODUCT_SHAPE.md` §10). The v1.0.5 faceplate arc makes the loop **browser-driven**,
so most of this is now done from the Annotate/Quality/Tuning tabs rather than the CLI.

21. **`eval/live-shakedown-labels`** — run the v1.0.4 loop **end-to-end on the real
    corpus** (the shakedown tagged-in-machinery-but-never-executed): Annotate-tab
    bootstrap **with grounding scorers** (the v1.0.5 `feat/grounding-scorers-in-console`
    path) → annotate verdicts → collate → `expected.json`. Deliverable: real
    `bootstrap.json` + `annotations.json` labels under `evals/fixtures/real/`
    (gitignored, PII) + a `evals/TUNING_LOG.md` entry recording the run. Mostly an
    operation (paid, human-in-the-loop), not new code. **Unblocks PV-2.**
22. **`eval/grounding-calibration`** — the **calibrated layers (B)**. Calibrate the
    L0 tolerance bands (`hardening.py`) + the eval-only L1/L2 NLI/MiniCheck thresholds
    (`evals/grounding_signals.py`) against the PV-1 labels; report **precision/recall
    per detector**; wire the calibrated cross-class groundedness score into
    `eval_composite` / score-over-time (`evals/runner.py`) and have the tuning gate
    consume it; update `docs/dev/GROUNDING_METRIC.md` (close the "B (deferred)" note)
    and the RELEASE_CHECKLIST grounding box. **L0 stays hot-path-safe; L1/L2 stay
    eval-only** (Key Decision #4). Depends on PV-1.
23. **`tune/cover-letter-opener`** — fix the throat-clearing/hedging opener that
    tripped `tone` in 1/5 v1.0.3 runs. Draft a `SYSTEM_PROMPT` worked-example
    candidate (OK / NOT-OK pair — the rule lives in the **non-overridable**
    `_COVER_LETTER_RULES_BLOCK`, so it must be a worked example, not a rules-block
    edit) via the in-browser A/B (`feat/tuning-tab-ab`), A/B against `--suite real`
    (n≥3); **user promotes** → edit `analyzer.py` SYSTEM_PROMPT + **bump
    `PROMPT_VERSION` in the same commit** + `TUNING_LOG.md` entry. Acceptance: `tone`
    holds at/above its floor. Depends on the corpus rebuild + the tuning loop; run
    after PV-2 so groundedness is calibrated when judging.
24. **`chore/type-annotation-scan`** — the explicit v1.1.0 tag criterion. Annotate
    Flask route returns with `flask.typing.ResponseReturnValue` (~15+ functions,
    lower-risk surgical path) **or** flip `check_untyped_defs = true` in the mypy
    config (broader — surfaces real new errors to fix first). **Scope to the whole
    post-v1.0.4 diff** (v1.0.5 **and** v1.0.6 added routes), not the pre-existing
    surface. Independent of the corpus rebuild — slot it last so it covers every new
    route. Closes the ~15 pre-existing `annotation-unchecked` notes.

    Then: **`chore/version-bump-v1.0.7`** (pyproject, CHANGELOG, tag).

### Sprint REL — v1.1.0 public release (user-owned tag)
> RELEASE_ARC Phase 5 — unchanged; listed here for completeness.
25. **`release/visual-assets`** — `docs/screenshots/*.png` (now against the
    redesigned UI) + optional `demo.gif`.
26. **`release/fresh-clone-v1-1-0`** — clean clone → install → one application
    < 5 min (risk-register D.4).
27. **`chore/release-v1.1.0`** — `version = "1.1.0"`; CHANGELOG; **create the GitHub
    repo, push `main` + tag, verify all doc URLs resolve** — executed **on the
    user's go**; the v1.1.0 tag is **user-owned**.

**Dependencies / ordering rationale.** V5-A → V5-B → v1.0.5 tag is fixed. Within
v1.0.6: branch 12 (a11y gate) lands first so it guards the rest; 6.2 is isolated;
6.1 branches are independent of each other (any order); branch 13's dropdown pattern
precedes branch 19's annotate-username consumer; branch 16 (IA reorder) precedes the
6.5 education content; branch 17 (help primitive) precedes 18/19. **Spill valve:** if
v1.0.6 runs long, Sprint 6.5 (branches 17–20, the education sweep) is the clean cut
to break out — it's self-contained and depends only on the IA reorder being done
(land it as its own point release ahead of v1.0.7, which is reserved for Sprint PV).
**Sprint PV (v1.0.7):** PV-1 → PV-2 → PV-3 chain on the shared corpus rebuild +
real-data labels; PV-4 (type scan) is independent and slots last so it covers
v1.0.6's new routes too. **Sprint REL (v1.1.0):** strictly after v1.0.7; tag
user-owned.

---

## 5. Versioning (honored)

v1.0.1–v1.0.4 tagged (local). **v1.0.5** = faceplate arc (V5-A) + #9/#10 blockers
(V5-B) + signed `V1_0_5_VERIFICATION.md`, then tag. **v1.0.6** = the combined
walk-through polish (Sprints 6.1–6.5). **v1.0.7** = pre-public hardening (Sprint PV:
live shakedown → grounding calibration B → cover-letter opener tuning →
type-annotation scan). **v1.1.0** = public release (Sprint REL), **user-owned tag**.
The education sweep (6.5) is the only floating piece — if v1.0.6 balloons it breaks
out as its own point release ahead of v1.0.7.
