<!-- provenance: schema=1 session=58b9754e-6a84-4fa9-8103-bb18a81c617c branch=fix/ux-restore-scroll-y-resource-contention commit=19d5532 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-30 -->

# Agent handoff: after `fix/ux-restore-scroll-y-resource-contention` (item 29 advanced, not closed)

**Branch to create:** `fix/ux-scroll-flake-cross-item-review` (branch off `main`) — a
cross-referencing review pass across epic 19's scroll-position-family items (27, 28, 29) and
their three diagnosis docs, BEFORE narrowing back into item 29 alone. Owner-directed
(2026-07-30): the individual-item approach has now produced three overlapping diagnosis docs
and at least one new unexplained failure mode; a pattern pass across all of them, done once,
may answer gaps that chasing item 29 in isolation keeps re-discovering piecemeal.
**Base branch:** `main`

---

## Documents to read before any tool call (in this order)
<!-- verbatim -->

1. `docs/dev/RELEASE_ARC.md` — authoritative branch sequence,
   architectural decisions, and acceptance criteria for v1.0.2 → v1.1.0.
   The durable plan. Do not deviate without user sign-off.
2. `docs/dev/RELEASE_CHECKLIST.md` — what is open, closed,
   and deferred per release. Before proposing anything, check here first.
3. `docs/dev/AGENT_FAILURE_PATTERNS.md` —
   failure patterns to avoid. Read in full before writing any code.
   **§5f ("Guessing the mechanism") is the expensive one — it is why the
   Binding-rules block below exists.**
4. `docs/governance/charter.md` — the binding
   constitution. **C-7 (evidence before mechanism) and C-8 (durable before
   deep) are enforced by hooks, not by your judgment.**
5. `docs/architecture.md` — module map and LLM routing
   boundary. The deterministic / LLM split is load-bearing.
6. `evals/TUNING_LOG.md` — baseline floors and
   prompt change history.
7. **If this branch is a `fix/*`:** its diagnosis dossier at
   `docs/dev/diagnosis/<branch-slug>.md`, if one exists. It is the durable
   evidence record — what was **observed**, what was **falsified** (do not
   re-chase those; each one cost real money to kill), and what is still only
   **inferred**. The `restore-evidence` SessionStart hook replays it into your
   context automatically, including after a compaction.

---

## Documents to read next, specific to this handoff

**Read ALL THREE of these together, in this order, before forming any new hypothesis** — this
is the point of the cross-item review below: reading them separately across different
sessions is exactly what let overlapping mechanisms go unnoticed so far.

- `docs/dev/diagnosis/ux-scroll-position-flake.md` — the original dossier; O-1 through O-14,
  the four failure "modes" (A/B/C/D), and the fix that shipped (`_scrollCaptureOrdinal` +
  `_scrollInterruptGen`, `static/app.js:5601-5630`).
- `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md` — falsified the wizard-rail attribution
  for mode C entirely (F-7); root-caused it to Chromium scroll-anchoring on
  `refreshMergeSuggestions()`'s async growth; fixed via `overflow-anchor: none`
  (`static/style.css:122`).
- `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` — this branch's own dossier.
  Falsified "generic resource contention" as an explanation; found the `-n 2`-within-suite
  vector elevates the O-10 test's failure rate (25% un-instrumented); then, instrumenting it,
  caught a DIFFERENT, undocumented failure mode (`before == 0` at setup) instead, at a much
  lower rate (1/16) than the un-instrumented run (2/8) — an unresolved discrepancy that could
  be a probe effect, small-sample noise, or a sign that "the" mechanism isn't singular.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** v1.1.0 endgame — epic 19 (UX-suite flakiness solution sprint).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — item 19 is an epic that cannot close until
items 28-31 all close (27 is closed; 28-29 open with growing evidence; 30-31
untouched, and are explicitly filed as unrelated to the scroll-position mechanism).

- ~~`fix/ux-mode-c-scroll-residual`~~ ✓ (merged, PR #80) — item 27 closed as
  already-resolved by a separate branch three days before it was filed; no code change.
- **`fix/ux-restore-scroll-y-resource-contention` (this branch, not yet merged) — item 29
  ADVANCED, not closed.** Ran three contention vectors; falsified "generic contention";
  confirmed a specific vector (`-n 2`-within-suite) elevates the failure rate; instrumented it
  and caught a different, unexplained failure mode instead. No fix — none proven yet. Full
  detail below and in the dossier.
- **`fix/ux-scroll-flake-cross-item-review` (recommended next, owner-directed 2026-07-30)** —
  NOT one of the original epic-19 child items. A deliberate pause on the per-item approach:
  read all three scroll-position diagnosis docs together, plus item 28's own single O-13
  sample, looking specifically for a pattern that explains gaps ACROSS items rather than
  within one — see "What this branch should build" below for concrete starting threads.
- **After that review, in priority order (evidence strength, from the ORIGINAL owner-confirmed
  sequencing, still standing unless the review changes it): item 29 (resume with whatever the
  review surfaces), then item 28, then item 30, then item 31.**

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** `main` is currently at `19d5532`
(the `fix/ux-mode-c-scroll-residual` merge, PR #80). This branch's own work, once merged, will
be the next thing to land:

Three commits' worth of work (not yet split/committed as of this handoff being written — see
"First move" for the closing agent's own remaining step 3):
1. `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` (new) — full campaign
   record across two rounds, three-then-four load vectors, ~48 total pytest invocations of the
   target test across all campaigns this session.
2. `tests/ux/regression/test_20260708_busy_states_and_chip.py` — added the file's existing
   scroll-mutation spy suite (`_SCROLL_SPY_JS`/`_SCROLL_SPY_NAMED_HOOKS_JS`/
   `_HEIGHT_ATTRIBUTION_JS`, already used by sibling tests) to
   `test_restore_scroll_y_stale_invocation_overwrites_later_scroll`, which previously had none.
   Verified passing cleanly under normal (uncontended) conditions as part of this session's
   gate run.
3. `docs/dev/work/items/0029-o10-regression-test-resource-contention.md` — two dated
   `## Updates` entries recording both rounds; `BOARD.md` regenerated.
4. This session's own `consumed`-event provenance-ledger file
   (`docs/dev/ledger/58b9754e-6a84-4fa9-8103-bb18a81c617c.jsonl`, for the incoming
   `fix-ux-mode-c-scroll-residual` handoff pointer this session consumed) — to be committed
   with the above.

**What was found, in order:**

1. **Three contention vectors tested, two falsified as sufficient alone.** A genuine external
   `pytest -m "not ux" -n auto` process and an idle orphaned same-project `python app.py`
   server both imposed real, measured slowdown (up to ~2.5-4x baseline test duration) but
   produced ZERO target-test failures across 8 runs each. An ambient-only control (no
   deliberate load — though NOT truly isolated; see the dossier's disclosed confound) had 1/8.
2. **The fourth vector — `pytest -n 2` WITHIN the ux suite itself (O-12 occurrence 1's actual,
   literal vector, never previously isolated) — reliably elevated the failure rate to 2/8
   (25%)**, including a landing value byte-identical to O-12's own historical capture. This
   falsifies "generic resource contention" and narrows the mechanism to something specific
   about a second concurrent Playwright/werkzeug pair in the same process tree.
3. **Hand-traced `_restoreScrollY`'s actual current implementation** (`static/app.js:5601-5630`)
   before building an instrument, rather than trusting the test's own docstring: the
   generation-mismatch abandon check has no fixed time budget, and this specific test's own
   `scrollTo(0,300)` bumps the generation counter BEFORE the stale restore is ever scheduled —
   so the docstring's implied "races a 150ms margin" framing does not hold up against the
   actual code. The observed failure values (`291`, `306` — well above `before=59`, not
   pulled toward the stale capture's near-0 value) look more consistent with the
   already-documented mode-C/D anchoring shape (this test seeds the same 20-near-identical-
   company corpus that triggers large merge-suggestion growth elsewhere in the file) than with
   a genuine regression of the generation-mismatch logic.
4. **Instrumented the test with the file's existing spy suite and re-ran the confirmed vector
   16x.** Did NOT catch the `after != before` shape this instrument was built to explain.
   Instead caught a THIRD, previously-undocumented failure mode: the test's own setup
   assertion (`before > 0`) failing, `before=0` — the page hadn't grown even its usual small
   scrollable amount by the time `scrollTo(0,300)` ran, earlier in the sequence than anything
   examined so far. Also: the instrumented failure rate (1/16) was well below the
   un-instrumented rate for the identical vector (2/8) — unresolved; possibly a probe effect
   from the spy's own overhead, possibly small-sample noise.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) ·
`pytest -m "not ux" -n auto` — 2107 passed / 1 skipped ·
`pytest -m ux` — 131 passed / 2 xpassed (run in 5 chunks: a11y+flows, and regression split
3-way, to stay under this environment's per-call wall-clock limits — see the closing agent's
own process notes if the next session needs to do this again) · `work_items check` ✓
(31 files).** Genuinely clean, no reruns anywhere in the log. The modified test
(`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`) passed cleanly with its new
instrumentation under normal conditions.

**Process note for whoever runs the gate next:** this environment's Bash tool caps a single
call's timeout at 600s: the full non-ux tier (`-n auto`) fits in one background call (~590s);
the full ux tier does not (historically ~20-23 min) and needs chunking — this session split it
`tests/ux/a11y + tests/ux/flows` (one call), then `tests/ux/regression`'s ~50 files into 3
roughly-equal groups via `split -n l/3 -d` on a file listing (NOT piped directly to `split` —
Git Bash's `split` cannot determine stdin size; write the listing to a file first).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessor):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded.

**Open is still 12 / 10 ceiling — OVER, net 0 this session** (item 29 advanced but not closed;
no items closed, no new items filed — this session's findings were folded into item 29's
existing entry rather than filed as new candidates, since they're the same underlying test).
Still over ceiling — a reduction sprint remains flagged, per charter W-1.

**Open (12 / 10 ceiling — OVER):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item
   10 (the v1.1.0 cut). Needs the dev server + visual review, not just code.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its own
   fixture's annotations. Needs a real heuristic decision in `pick_anchor_jd`.
3. Item 14 — no JD-identifying (name/company) metadata in bootstrap/eval
   artifacts.
4. Item 15 — suggested-skills rendering bug (comma-split inside
   parentheticals).
5. Item 19 (epic) — UX-suite flakiness solution sprint umbrella. Cannot
   close until items 28-31 (below) all close. Item 27 closed with no code change;
   item 29 advanced this session, still open.
6. Item 20 — legacy `generate()` reachable via wizard rail without
   freezing Compose (`decision_owner=user`).
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
8. Item 22 — 4 call kinds never logged despite real call sites.
9. **Item 28** (epic 19 child) — O-13, one sample, untested
   `loadComposition` call site of the `_captureScrollY`/`_restoreScrollY`
   primitive (`before=400 after=796`). Flagged this session as a likely thread for the
   cross-item review — same primitive, different call site, same "well above baseline"
   landing-value shape as this branch's own `291`/`306` captures.
10. **Item 29** (epic 19 child) — O-12/O-14, the O-10 regression test itself fails under
    resource contention. Advanced substantially this session (see above); still open, no
    mechanism proven, no fix. **Do not resume narrowly on this alone — see the recommended
    next branch above.**
11. **Item 30** (epic 19 child) — keyboard-reorder timeout, one sample, no
    diagnosis yet, explicitly unrelated to the scroll-position mechanism.
12. **Item 31** (epic 19 child) — network-retry assertion flake, one
    sample plus one clean isolated rerun, explicitly unrelated to the scroll-position
    mechanism, no diagnosis yet.

**Blocked (4):**
13. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR,
    `enforce_admins`).
14. Item 5 — grounding-score persistence gap.
15. Item 8 — compose-time rewrite dial, blocked pending owner direction.
16. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]`.

**Deferred (4):**
17. Item 4 — in-app citation viewer, no friction signal yet.
18. Item 7 — PX-46 memory consolidation, owner sign-off required first.
19. Item 24 — template-preview fidelity spike (T2), never scheduled.
20. Item 25 — `app.run(threaded=True)` governance decision, deliberately
    deferred.

**Watching (4):**
21. Item 2 — wordmark sweep, opportunistic only.
22. Item 16 — `evals/runner.py --suite real` non-functional.
23. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
24. Item 23 — PX-52 analyzer.py split, WATCH disposition.

24 total open+blocked+deferred+watching items (unchanged count from the predecessor
handoff — item 29 advanced in place, nothing closed or newly filed). **New process
observation, not itself a ledger item:** three rounds of per-item, per-session diagnosis on
the scroll-position family (items 27, 28, 29) have now produced three separate diagnosis
docs with plausible cross-references neither fully explored nor ruled out (mode-C anchoring
possibly bleeding into item 29's test; item 28's single O-13 sample sharing the "well above
baseline" landing shape with this session's own captures) — this is exactly the pattern the
recommended next branch exists to check before a fourth per-item round repeats the same gap.

---

## What this branch should build

**This is a review branch, not a fix branch — no production code edit is authorized on it
without a NEW C-7 finding of its own.** Concrete starting threads for the cross-item review,
each one a "does this pattern span items?" question, not a prescribed conclusion:

1. **Read all three scroll-position diagnosis docs back to back** (see the reading list
   above) and build a single timeline/table of every captured failure across all of them —
   test name, call site (`refreshCorpus` vs `loadComposition` vs `_wizardRender`), `before`/
   `after` values, load condition, and which of the four modes (A/B/C/D) or "new" it was
   classified as. Look specifically for landing-value clusters (this branch found `306`
   recurring exactly; item 28's `796` and this branch's `291` may or may not cluster with
   anything once laid out together) and for whether ANY call site of `_captureScrollY`/
   `_restoreScrollY` has ever been cleanly exonerated, or whether every one tested so far has
   shown at least one contention-adjacent failure.
2. **Item 28's O-13 sample** (`loadComposition` call site, `before=400 after=796`, one sample,
   never diagnosed) is a natural first cross-check: does instrumenting it the same way this
   branch instrumented the `refreshCorpus`/O-10 test reproduce something, and does whatever it
   shows share a mechanism with this branch's `before=0` finding or the `291`/`306` anchoring-
   shaped failures?
3. **The probe-effect question this branch left open** (instrumented failure rate 1/16 vs.
   un-instrumented 2/8 on the identical vector) is itself worth a dedicated few runs before
   trusting either rate — if real, it changes how much weight any spy-based finding in this
   whole family should carry going forward, not just for item 29.
4. **Items 30/31 are explicitly filed as unrelated** to this mechanism family (their own item
   text says so) — a quick sanity check that this still holds (rather than assuming it
   forever) is in scope, but do not invest deep diagnosis time there unless the sanity check
   finds something.

Scope is bounded to this cross-referencing review and whatever NEW, evidence-backed next step
it produces (which may be resuming item 29, starting item 28, or something the review itself
surfaces) — not to attempting a fix for any of items 28/29/30/31 without a proven mechanism,
and not to items 9, 13, 14, 15, 20, 21, or 22.

---

## First move

Create `fix/ux-scroll-flake-cross-item-review` off `main`. Read the three diagnosis docs
together per the reading-list note above before writing anything. This is explicitly a
reading/synthesis branch first — **do not code, and do not start a new load campaign, until
the cross-item read is done and written up** (a new section in whichever diagnosis doc it
belongs to, or a new short cross-reference doc if the finding doesn't fit any single existing
one — judgment call for that session, but write it down, per C-8, the turn it's found). If
that review lands on a concrete, testable hypothesis, `docs/dev/diagnosis/<new-branch-slug>.md`
(or continuing this branch's own dossier, if the finding is scoped to item 29 specifically)
still needs a filled-in `## Observed` before any production-code edit — the
`require-evidence-before-fix` hook enforces this exactly as it did on this branch.

---

## Binding rules — no discretion (copy verbatim — MANDATORY in every handoff)
<!-- verbatim -->

**These are not heuristics, and your judgment does not decide whether they apply
today.** Each one exists because an agent decided it did not apply, and was
expensively wrong. Read them as prohibitions, not as advice.

**1. Evidence before mechanism (charter C-7). If you did not SEE it, you did not
find it.**
- For a defect you cannot reproduce on demand, **the first commit on this branch
  is the instrument or the reproduction — never the fix.** The
  `require-evidence-before-fix` hook blocks production edits on a `fix/*` branch
  until `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section. There is no escape hatch. `docs/**`, `tests/**` and `*.md` stay
  writable, so the way through is always open: **write down what you saw.**
- **Reading code and finding a plausible mechanism is a HYPOTHESIS.** Put it under
  `## Inferred` and label it as unproven. A fix for a real defect that isn't
  **the** defect still leaves the bug — and plausibility is exactly what makes you
  skip the check.
- **Never scope an instrument to the theory you are testing.** It will confirm
  your theory by hiding its rivals. Capture wider than you think you need.
- **Green CI is not evidence if the test needed a retry.** `pytest-rerunfailures`
  reports a fail-fail-pass as a bare `PASSED` with **no traceback anywhere in the
  log**.
- If you are not certain **from evidence**, say **"I have not verified this"** and
  **stop**. That sentence is always cheaper than the alternative.

**2. Durable before deep (charter C-8). The context window is not a store.**
- Write a hard-won fact — a measurement, a falsified hypothesis, an observed
  artifact — to its durable home **in the turn you learn it.** Not at close-out.
  The pre-close sweep *reconciles*; it must not *discover*.
- **Compaction is an unannounced data-loss event.** After one, reconcile against
  the repo and git — never continue from a summary as though it were the evidence.
- **A thin context is a handoff trigger, not a push-harder trigger.**

**3. Hooks are not obstacles (see `feedback_hook_discipline`).**
- **NEVER** bypass a hook on your own initiative. Never hand-create the file a hook
  checks for. Never skip a step that has no escape hatch. Escape hatches
  (`CLAUDE_ALLOW_MAIN_EDITS=1`, `CLAUDE_CONFIRM_MERGE=1`) are legitimate **only when
  the user explicitly directs their use** — never on your own judgment.
- If a hook blocks you: **surface the hook name and its message, and STOP.**

**4. Do not declare done. Verify done.** "Done" is the *output* of the pre-close
sweep, not an announcement. See the close-out checklist below.

**5. Corrupted input is a blocked gate (charter C-9).** Damaged, truncated, or
fingerprint-mismatched input is a blocked gate — surface it as your **first
output** and **STOP**; never silently reconstruct, however confident the
reconstruction feels. A `blocked` result from
`scripts/verify_doc_template.py --event consumed` on a handoff you're
consuming is exactly this case — three of the four confirmed silent
handoff-corruption events this rule exists for were an agent reconstructing
damaged text instead of saying so (see
`docs/dev/handoff-integrity-design.md` §2).

---

## Hard constraints (copy verbatim — do not shorten)
<!-- verbatim -->

- Branch before any code edit (`require-feature-branch` hook enforces this)
- Quality gate before every commit: `ruff check .` + `mypy .` + `pytest`
- Every new Flask route: `_safe_username()` + `_within()` + `secure_filename()`
  — `route-security-lint` hook enforces this on `app.py` edits
- No LLM calls in `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, or `pdf_render.py`
- `PROMPT_VERSION` must bump in the same commit as any prompt change
- New dependency = `pyproject.toml` entry + `CHANGELOG.md` entry
- If a hook blocks you: surface the hook name + error, do not bypass,
  wait for authorization
- Do not merge to `main` without explicit user confirmation
- One branch per session — close, merge, hand off before starting the next
- Capture-before-merge: land ALL of this branch's docs / memory / CHANGELOG /
  RELEASE_ARC-CHECKLIST / tracked-deferred / flaky-test captures **before** the merge.
  Never merge then open a follow-up branch for a one-file doc/memory edit — it
  re-triggers the `--no-ff` `.approved` marker-wipe ceremony. If a small item surfaces
  after you'd otherwise merge, the sweep isn't finished: fold it in and re-gate.

---

## Branch close-out checklist (do in this order before closing the window)
<!-- verbatim -->

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified; **this session's
   own `consumed`-event provenance-ledger file** (`docs/dev/ledger/<session>.jsonl`,
   written on `main` at session start when the incoming handoff pointer was
   consumed) **committed on this branch** — folded into an early commit, never
   left untracked and never given its own dedicated branch/PR (see
   `docs/dev/prov/SPEC.md` §5 step 3); **any dev server or
   long-lived background process started this session terminated** before closing the
   window (check with `tasklist`/equivalent — an agent's own orphaned processes are
   exactly the failure mode carry-forward ledger item 20 documents). "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Write the next-agent handoff at `docs/dev/handoffs/<branch-slug>.md` from
   this template (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), stamped per
   `docs/dev/prov/SPEC.md` §1, then validate it:
   `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>`. A
   `failed` result is authoring corruption in the handoff itself — fix the
   file, don't silence the check. **Do this ON THIS BRANCH, BEFORE the
   merge** — this is exactly what the Capture-before-merge hard constraint
   above already requires (the handoff is one of this branch's own docs),
   and `require-feature-branch` blocks writing it on `main` once this
   branch is gone, so there is no compliant way to do this step after
   merging.
3. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean); the handoff file from step 2
   must be committed by this point too (its own commit or folded into this
   one — either way, both must exist before step 4)
4. **Land it through the PR channel — a local `git merge` to `main` is NEVER
   the flow.** `main` carries branch protection requiring a pull request plus
   six passing status checks (`strict: true`), so a local merge is rejected
   outright for a non-admin and, for an admin, silently bypasses those six
   checks. Squash and rebase merges are both disabled on the repo, leaving
   **merge commit** as the only method — deliberately: a squash rewrites SHAs
   and orphans the local commits it replaces (it already produced one zombie
   commit, `9f3c800`, before this was understood). Ask the user to confirm,
   then: `git push -u origin <branch>` → open the PR (`gh pr create`, or hand
   the user the URL) → **wait for all required checks to go green** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **Pushing is outward-facing on a public repo:** state what will become
   public — including any commits already on your local `main` that the remote
   does not have, since they ride along — and get explicit confirmation before
   the first push.
5. Prune the merged branch(es) with the user's OK — **but regenerate the
   pointer FIRST**, because it must cite `main`, and pruning a branch a
   pointer still names leaves the next session with an unresolvable
   reference (a correct C-9 halt, but a wasted first move). After the
   `pull --ff-only` in step 4: generate the one-line pointer with
   `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`). Then prune
   (`git branch -d <branch>`; the remote copy is auto-deleted on merge).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
