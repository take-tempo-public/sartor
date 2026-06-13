---
status: review-artifact
evidence_sha: c6e0437
drift_checked_against: a0a1cb2
graduation: docs/dev/reviews/2026-06-product-excellence/ (archived with the review)
---

# Honest final assessment - callback. product-excellence review

> The capstone of the eight-domain review (ask #7). Evidence pinned at
> `c6e0437`; drift checked against current `main` (`a0a1cb2`, 15 commits
> ahead - Sprint 6.4 + 6.6 + the WS-4b wiki cold-ingest). Severity anchor:
> the SIGNED Product Charter. Findings are cited by F-id, prescriptions by
> PX-id. Written under C-0: mechanism-and-effort language, no
> LLM-behavior absolutes, no marketing.

---

## Overall verdict

callback. is on a credible track to be both functionally serious and a
portfolio piece - but it is not there yet, and the gap is concentrated in
one place: the project makes categorical promises faster than it builds the
machines that keep them honest. The craft is real. The persistence spine,
the audit chain, the eval regression gate, the seven enforced governance
hooks, the route-containment density, and the zero-PII clone are
genuinely good and were verified adversarially (`F-arch-06`, `F-arch-07`,
`F-qe-rel-05`, `F-gov-04`, `F-sec-05`, `F-sec-06`). The wiki/memory
exhibit just demonstrated something rare under drift: the WS-4b code
cold-ingest ran for real between the pin and `main`, and its rot-detection
*fired* - catching the route count drifting 75->92, a second raw-LLM call
site bypassing the `_call_llm` funnel, a wrong telemetry JSON key, and two
diagram drifts (`F-docs-10`, now discharged). That is the A-4 "whoa, this
is robust" reaction earning itself.

The load-bearing risk is the inverse of that strength. The two highest-
severity findings are both P0 and both CONFIRMED: the no-egress promise is
asserted in prose but not machine-falsifiable (`F-qe-rel-02`), and the
CI a11y/UX/PDF tier silently skips when Chromium is absent, so "machine-
checked in CI, free forever" is maintainer-local today (`F-qe-rel-01`). At
`a0a1cb2` the Chart.js CDN tag is still live at `dashboard/templates/
dashboard.html:15` while `SECURITY.md:85` still reads "No external CDN is
loaded at runtime" - the egress contradiction (`F-vision-05`/`F-sec-03`/
`F-docs-02`, PX-01) persists, and the WS-4b ingest did *not* catch it (its
rot-detection is code-vs-code/doc-vs-symbol, not cross-document claim
consistency). That is the owner's S-1 fear - PII/egress leak first,
amateurish-miss second - made concrete: not because a leak exists, but
because the claims that there is none are unenforced. Nothing here blocks
the craft narrative; everything here blocks the public tag until the
claims earn machine backing.

---

## Per-domain synthesis

### 1. Product vision & definition
- **FIX:** Reconcile the no-invention absolutes ("The LLM cannot invent
  facts," vision.md:50; "No invention, ever," :151) to C-0 mechanism
  language - a live signed-charter violation on the highest-audience
  surface the owner already recanted (`F-vision-02`/`F-docs-03`, PX-09).
  Demote single-tenant-as-value, which contradicts "local and yours" while
  the code ships multi-profile (`F-vision-04`, PX-27).
- **KEEP:** The system-model self-portrait with visible honesty seams
  (`F-vision-08`) and the Corpus-Item asymmetry matrix as falsifiable
  diagnosis (`F-vision-09`).
- **WATCH:** A-2/A-3/A-5 audiences absent from public identity
  (`F-vision-10`).
- **DRIFT - PARTLY RESOLVED:** `F-vision-03` (outcome funnel shipped, docs
  say "(Future v2)") and `F-vision-06` (Corpus-Item ladder drift) were each
  half-addressed in PRODUCT_SHAPE on `main`, but vision.md is unchanged -
  the doc-to-doc gap narrowed, not closed. PX-11/PX-12 still owe the
  reconciliation in vision.md.

### 2. Architecture & code health
- **FIX:** The C-6 deterministic-LLM boundary holds by *behavior* but has
  no construction gate - no import-linter, no boundary test (`F-arch-01`/
  `F-qe-rel-04`, PX-20). Correct the stale v1.0.8 blast-radius numbers
  (6290/75/67 vs actual 6992/78/24 - ~2.8x overstated coupling) before the
  blueprint epic is argued on them (`F-arch-02`, PX-10).
- **KEEP:** Boundary holds at the pin (`F-arch-04`); per-edge cascade +
  CHECK constraints (`F-arch-06`); the timestamped-child audit chain
  (`F-arch-07`).
- **WATCH:** route-security-lint is app.py-scoped and dark on blueprints -
  WEAKENED to a latent gap that becomes load-bearing only when filesystem-
  touching routes migrate (`F-arch-03`, PX-21).

### 3. Product experience & accessibility
- **FIX (P0-adjacent):** The a11y taxonomy is not machine-checked in CI
  (`F-expa11y-01`, rolls into PX-25). A cold no-API-key first run dumps a
  bare 500/traceback mid-analyze instead of guiding (`F-expa11y-02`,
  PX-16). No ACCESSIBILITY.md honest-status page exists (`F-expa11y-03`,
  PX-18). Diagnostics legends are dev-register; the lay metrics legend -
  S-3, the owner's self-named weakest area - is unwritten (`F-expa11y-04`,
  PX-15).
- **KEEP:** Keyboard bullet-reorder pinned by a real regression test
  (`F-expa11y-07`); `_announce()` live-region discipline at every async
  completion (`F-expa11y-08`).
- **WATCH:** Modal focus-trap is implemented by static reading but not
  test-covered - WEAKENED (`F-expa11y-09`); browser Back exits the SPA and
  discards wizard state (`F-expa11y-06`, PX-22).

### 4. Quality engineering & release discipline
- **FIX (P0):** Commit a network-egress falsifiability test (`F-qe-rel-02`,
  PX-08) and run the UX/a11y/PDF tier in CI as a required check
  (`F-qe-rel-01`, PX-25). Land the E-2 machine badges, none of which exist
  at the pin (`F-qe-rel-03`, PX-26). Soften the two hard human SLAs to
  best-effort (`F-qe-rel-08`, PX-07).
- **KEEP:** The eval-quality regression gate genuinely blocks - exit-code 2
  fails eval-smoke on a grounding drop near/past 0.5 (grounding-rubric-only
  x3 synthetic fixtures in CI) (`F-qe-rel-05`, PX-13). CI matrix +
  least-privilege permissions (`F-qe-rel-10`).
- **WATCH:** T-D unclosed - gates run on synthetic/small inputs only;
  WEAKENED to drop the "silent" framing since it is already a sequenced
  release-blocking task (`F-qe-rel-07`). No automated perf gate
  (`F-qe-rel-06`, PX-35, trigger-deferred).

### 5. Eval / grounding / tuning as product
- **BOOST:** Paid eval/tune routes are cost- and consent-gated - localhost
  guard + cost-band confirm (`F-eval-07`).
- **FIX:** AL-1 over-suppression is uninstrumented and unfalsifiable from
  data - the suggested-bullet count never rides along (`F-eval-01`,
  PX-17). The committed synthetic suite exercises only the legacy generate
  path; corpus-mode is uncovered (`F-eval-10`, PX-30).
- **KEEP:** Non-polluting candidate A/B with byte-identical default path
  (`F-eval-05`); manual-promote, fail-closed, LLM-free annotation contract
  (`F-eval-06`); uncalibrated L1/L2 state surfaced and tracked, not
  silently trusted (`F-eval-08`).
- **DRIFT - STILL VALID:** `F-eval-02` (real loop never exercised; L1/L2
  uncalibrated, blocking M-2/T-D). TUNING_LOG gained a 2026-06-13 entry on
  `main`, but it is synthetic/legacy-mode work; `fixtures/real/` is still
  `.gitkeep`-only. The calibration gap is intact.

### 6. Open-source readiness, security & privacy
- **FIX (S-1 spine):** C-2 egress and C-1 loopback bind are both asserted
  in prose, not enforced by construction (`F-sec-01`/`F-sec-02`, PX-08/
  PX-19). SECURITY.md carries a false no-CDN claim and a phantom JD-URL
  egress class (`F-sec-03`/`F-sec-04`, PX-01/PX-03). The CODE_OF_CONDUCT
  routes vulnerability reports to the wrong repo (`F-sec-11`, PX-05).
- **KEEP:** Route containment dense, unit-tested, build-time-guarded (read
  the count as helper-usage density, not per-route proof) (`F-sec-05`); a
  fresh hostile clone carries zero real PII and zero secrets across full
  history (`F-sec-06`).
- **WATCH:** No E-2 machine gates committed (`F-sec-09`, PX-26); the HF
  eval-grounding download honors D-6 but rides an unpinned VCS dep
  (`F-sec-10`).

### 7. Documentation & wiki architecture
- **FIX:** SECURITY.md's egress enumeration disagrees with vision/README
  (3 classes vs 2, incl. the phantom JD-URL fetch) (`F-docs-01`, PX-03);
  public docs describe a live profile scrape that is dead code at the pin
  (`F-docs-04`, PX-02).
- **KEEP:** The one-grounding-rule + cite/backlink/synthesis convention is
  genuinely practiced - and the cold-ingest reaffirmed it at 24-page scale
  with a machine-parseable Audience-tag convention added (`F-docs-07`); the
  @import safety condition is recorded in SCHEMA D5 (`F-docs-09`).
- **DRIFT - SUPERSEDED (both discharged by execution):** `F-docs-08`
  (sentinel honesty) - the `.last_ingest_sha` advanced honestly from the
  "# no code ingest yet" sentinel to a real 40-char HEAD SHA
  (`9816b45...`); the honesty discipline held through the transition rather
  than a false advance. `F-docs-10` (untested-at-scale) - the pass produced
  16 path:line-grounded code pages, the grounding rule held at module
  scale, and rot-detection fired for the first time. These two are no
  longer open; PX-33 is largely delivered. **But** the ingest did not
  independently surface the egress/CDN/scraper spine: it documents
  `scraper.py` as a *live* module (flagging only a symbol-name drift, not
  the dead-code substance of `F-docs-04`) and records "Chart.js from CDN"
  neutrally, not as a contradiction with the no-CDN claim - that spine
  remains the product review's to carry.

### 8. Governance, memory & incubation
- **DEBUFF:** check-plan-approved prints a hand-create-the-marker hint that
  contradicts the never-hand-create rule (`F-gov-07`, PX-28).
- **FIX:** block-merge-to-main misses the dominant feature-merge direction -
  convention-only for the common path (`F-gov-01`, PX-24); the parallel-
  session isolation model is uncodified while two worktrees run daily
  (`F-gov-02`/`F-gov-03`, PX-23).
- **KEEP:** Seven enforced blocker hooks, honestly separated from witness
  rules (`F-gov-04`); governance-extraction design is register-grade
  (`F-gov-05`); read-only subagents as the compliance-agent precedent
  (`F-gov-09`).
- **DRIFT - STILL VALID / STRENGTHENED:** `F-gov-06` (witness-class
  freshness reminder + honest sentinel as a working amendment-ceremony
  precedent) is now demonstrated end-to-end - the sentinel honestly retired
  to a real SHA and log.md notes the commit-time freshness reminder "goes
  live." The KEEP holds, strengthened by a completed cycle.

---

## Cross-cutting (1): the two P0 public-tag blockers

Both P0 findings are CONFIRMED, and both are the same shape - a categorical
claim with no machine behind it:

1. **`F-qe-rel-02` -> PX-08 (now-v1.0.6).** C-2 says diagnostics/telemetry
   never "leave the machine, ever," and the charter records that egress was
   *audited* at `c6e0437` - but a one-time audit is not a committed gate.
   The fix is a `pytest-socket`-style test that disables sockets, allowlists
   exactly the two sanctioned destination classes (configured LLM provider;
   optional profile/website scrape), and fails on anything else. It would
   have caught the live Chart.js CDN fetch, and it keeps C-2 honest after
   PX-01 vendors. This is the construction C-0 prescribes for a "never"
   claim, and it answers the #1 S-1 fear directly.

2. **`F-qe-rel-01` -> PX-25 (v1.1.0-gate).** The CI quality job is
   ruff/mypy/pytest only; there is no `playwright install`, so on a fresh
   runner the UX/a11y/PDF tier *collects then skips* - "machine-checked in
   CI, free forever" (E-2, signed) is maintainer-local. The fix is a
   dedicated CI job that installs Chromium and runs `pytest -m ux` as a
   required check, plus reflow/tab-order/history axe assertions
   (`F-expa11y-05`).

Neither is a present leak or a present a11y regression - the egress *is*
clean at the audit, the a11y suite *does* pass on the maintainer's machine.
Both are honesty gaps: the public tag would claim enforcement the repo does
not yet perform unattended. That is precisely the "amateurish planning
visible to an A-4 reader" class the charter ranks second among release
fears, and an A-4 reader checks the CI, not the maintainer's laptop.

---

## Cross-cutting (2): the KEEP ledger - protect through the v1.0.8 split

The blueprint split (WS-1) and the v1.1.0 tag are the moments the
affirm-and-protect ledger is most likely to regress quietly. Three
exhibits and one spine must survive intact, and PX-29/PX-32 convert the
load-bearing ones into do-not-regress guard tests so they cannot be
weakened silently:

- **A-4 exhibit 1 - the eval/tuning loop.** The regression gate that forces
  exit-2 on a grounding drop (`F-qe-rel-05`), the cost/consent-gated paid
  routes (BOOST, `F-eval-07`), the non-polluting A/B primitive
  (`F-eval-05`), and the honest UNCALIBRATED stamp on L1/L2 (`F-eval-08`).
- **A-4 exhibit 2 - grounding performance of generations.** The
  source-union metric that distinguishes asserted-beyond from
  synthesized-within (`F-eval-04`, WEAKENED to a three-source union - fix
  the doc's four-part overstatement, PX-14).
- **A-4 exhibit 3 - the wiki/memory + docs-with-git system.** The
  one-grounding-rule convention (`F-docs-07`), sentinel honesty (now
  discharged, `F-docs-08`), the @import safety condition (`F-docs-09`), and
  the freshness-reminder amendment precedent (`F-gov-06`). This exhibit
  *gained* evidence during the review window: the cold-ingest's rot-
  detection firing at module scale is the most concrete "robust" signal in
  the set.
- **The security/audit spine.** Route containment (`F-sec-05`), the
  zero-PII hostile clone (`F-sec-06`), the seven enforced hooks
  (`F-gov-04`), the audit chain (`F-arch-07`), keyboard-reorder and
  live-region a11y (`F-expa11y-07`/`F-expa11y-08`). Several of these are
  affirmed by static reading and have *no test today* - the split is exactly
  when an untested affirmation rots. PX-29 pins them.

The risk is not that any of these is wrong; it is that several have no
machine guarding them, so a refactor can quietly degrade them and the
review's "verified at the pin" goes stale. Guard tests are the cheap
insurance.

---

## Cross-cutting (3): the single highest-leverage theme

**C-0 claims discipline is the spine of the whole review.** Almost every
P0/P1 FIX reduces to the same defect: a categorical claim ("never," "only,"
"cannot," "always") standing on convention or a one-time audit instead of a
machine that fails by construction. The cluster:

- **Egress** - "never leave the machine" (`F-qe-rel-02`/`F-sec-01`) and the
  false no-CDN claim (`F-sec-03`/`F-docs-02`) -> PX-08 + PX-01.
- **Boundary** - the "Inviolable" deterministic-LLM boundary holds by
  behavior, no gate (`F-arch-01`/`F-qe-rel-04`) -> PX-20.
- **Loopback bind** - "binds to 127.0.0.1 only," implicit Flask default,
  unpinned (`F-sec-02`) -> PX-19.
- **CI a11y** - "machine-checked in CI, free forever," local-only
  (`F-qe-rel-01`/`F-expa11y-01`) -> PX-25.
- **No-invention** - "the LLM cannot invent facts," an LLM-behavior
  absolute C-0 expressly bars (`F-vision-02`/`F-docs-03`) -> PX-09.

The owner's S-1 fear is this theme made concrete. The fix pattern is
already correct in the charter: where a deterministic test *can* enforce a
categorical, build it and keep the categorical; where the claim depends on
LLM behavior, describe mechanism-and-effort and drop the absolute. The
prescriptions that matter most - PX-08 (egress), PX-20 (boundary gate),
PX-25 (CI a11y), PX-09 (no-invention rewording) - are each an instance of
that one move. The wiki cold-ingest is the proof the move *works*: its
rot-detection is a machine that fails on doc/code drift, and it caught five
real drifts the moment it ran. Extend that posture from doc-vs-code
consistency to claim-vs-code consistency and the categorical-claim risk
collapses.

---

## What this review could not determine

- **Real-data quality (T-D) is unmeasured.** Every grounding/eval gate runs
  on synthetic fixtures and small constructed inputs; `fixtures/real/` is
  empty at the pin and on `main` (`F-eval-02`/`F-qe-rel-07`). Whether
  generations are good at robert-scale on a real corpus - and whether AL-1
  over-suppression is actually happening - is unknowable from committed
  artifacts. M-2 exists to close exactly this before v1.1.0; the review can
  confirm the gap is named and sequenced, not that the machinery works on
  real data.
- **Live-main reconciliation is partial.** This assessment drift-checks
  against `a0a1cb2` for the items the drift pass flagged, but the full
  eight-domain evidence base is pinned at `c6e0437`. Sprint 6.4/6.6 landed
  UI and Corpus-Item work (corpus-first tabs, experience-summary and
  skill-group items) that was not re-assessed line-by-line; Phase 5 owns the
  full main reconciliation. Findings here are accurate at the pin and
  drift-adjusted where flagged, not re-verified against every `main` commit.
- **Anything pinned evidence cannot see.** Static git/grep/AST and
  sandboxed probes only - no paid eval runs, no live LLM behavior observed,
  no NVDA/screen-reader pass (the one bounded walkthrough is a v1.0.7
  deliverable, unbuilt). The modal focus-trap and several KEEP affirmations
  are static-reading only (`F-expa11y-09`); "implemented" here means "reads
  correct," not "test-verified." Network 404s (the wrong-repo disclosure
  channel, `F-sec-11`) were inferred from non-canonical provenance, not
  fetched.
