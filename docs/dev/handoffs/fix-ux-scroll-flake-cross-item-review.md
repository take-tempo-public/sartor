<!-- provenance: schema=1 session=f0e8666e-b8a7-4070-8135-1377773b9066 branch=fix/ux-scroll-flake-cross-item-review commit=3bf5527 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-30 -->

# Agent handoff: after `fix/ux-scroll-flake-cross-item-review` (item 29 corrected, not closed)

**Branch to create:** `fix/ux-restore-scroll-y-resource-contention` (branch off `main`) —
reusing this exact name is intentional, matching this repo's own established convention
(`fix/ux-scroll-wizard-rail-flake` was reused across rounds 3-7, PRs #67/#71/#72). Continue
item 29's own dossier (`docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md`) rather
than starting a new one — it already has a filled `## Observed` section (clears the
`require-evidence-before-fix` hook immediately) and the next step is a direct continuation of
its own `## Falsification` plan, now corrected by the cross-item review below.
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

**Read this branch's own cross-item review FIRST, then the dossier it corrects, in this
order** — the review supersedes part of the dossier's own `## Round 2`/`## Inferred`, and
reading the dossier first will plant the now-falsified explanation before you see why it's
wrong:

- `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md` — this session's own output. The
  core finding: item 29's `291`/`306`/`273` landing values cannot be explained by the
  document-level scroll-anchoring mechanism (item 27, fixed `27d349b`/`90e495d`, 2026-07-26) —
  every capture in the whole family post-dates that fix by 2-4 days, confirmed via
  `git merge-base --is-ancestor`, not just date-reading. Proposes a different, untested
  hypothesis instead (a transient max-scroll clamp hit while the corpus DOM is still
  mid-render, `## Inferred` + `## R-3` in that doc) and a concrete next instrument
  (`## Falsification`).
- `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` — item 29's own dossier,
  now carrying two `⚠ Corrected by the cross-item review` callouts (top banner + inline in
  `## Round 2`) pointing back at the review doc. Its own `## Falsification` section's original
  plan ("instrument the rAF callback's fire-time") is **superseded** — see the review doc's
  own `## Falsification` for what to run instead, and item 29's own work-item file
  (`docs/dev/work/items/0029-...md`) Updates for the same in board form.
- `docs/dev/diagnosis/ux-scroll-position-flake.md` — background only if needed: O-12/O-13/O-14
  are the source captures the cross-item review's timeline table draws from.

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
items 28-31 all close (27 is closed; 28-29 open with a corrected hypothesis;
30-31 untouched, sanity-checked again this session and confirmed still unrelated).

- ~~`fix/ux-mode-c-scroll-residual`~~ ✓ (merged, PR #80) — item 27 closed as
  already-resolved by a separate branch three days before it was filed; no code change.
- ~~`fix/ux-restore-scroll-y-resource-contention`~~ (merged, PR #81) — item 29 advanced with a
  dedicated contention campaign; no mechanism proven; the campaign's own `## Round 2` floated
  an anchoring-bleed-in explanation, later shown wrong (see below).
- **`fix/ux-scroll-flake-cross-item-review` (this branch, not yet merged) — cross-item review
  done, no fix, item 29 NOT closed.** Read all three scroll-family dossiers together per the
  prior handoff's own instruction. Falsified item 29's own anchoring-bleed-in inference with
  dated git evidence; proposed a sharper, untested hypothesis (transient max-scroll clamp) and
  a concrete next instrument. Full detail below and in the review doc itself.
- **`fix/ux-restore-scroll-y-resource-contention` (recommended next, reusing the name) —
  run the review's own `## Falsification` experiment: capture `documentElement.scrollHeight`
  at the moment of the final `after` read, re-run the confirmed `-n2`-within-suite vector until
  an `after != before` failure lands with it attached.**
- **After that, in priority order (unchanged from the prior handoff, still standing): item 29
  (resume/close depending on what the experiment shows), then item 28 (only if item 29's
  result plausibly extends to `loadComposition` — do not assume it does), then item 30, then
  item 31.**

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** `main` is currently at `3bf5527`
(the `fix/ux-restore-scroll-y-resource-contention` merge, PR #81, item 29's contention
campaign). This branch's own work, once merged, will be the next thing to land:

1. `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md` (new) — the full cross-item
   timeline table (14 captures across all three dossiers), the git-ancestry evidence that
   falsifies the anchoring-bleed-in inference, the height-clamp hypothesis with its supporting
   arithmetic, the item 28/30/31 cross-checks, and the concrete next instrument.
2. `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` (edited) — two `⚠
   Corrected by the cross-item review` callouts added; no other content changed.
3. `docs/dev/work/items/0019-ux-flake-solution-sprint.md` and
   `docs/dev/work/items/0029-o10-regression-test-resource-contention.md` (edited) — Updates
   entries recording the review's finding; `BOARD.md` regenerated (no table diff — only
   frontmatter-driven fields feed the table, and none changed).
4. This session's own `consumed`-event provenance-ledger file
   (`docs/dev/ledger/f0e8666e-b8a7-4070-8135-1377773b9066.jsonl`, for the incoming
   `fix-ux-restore-scroll-y-resource-contention` handoff pointer this session consumed) — to
   be committed with the above.

**What was found, in order:**

1. **Verified, not assumed, that the document-level scroll-anchoring fix (item 27) predates
   every post-Chip-3 capture in the whole scroll-flake family.** `git merge-base
   --is-ancestor 27d349b <commit>` returns true for the commits that added O-12/O-13
   (`6bb7d47`, 2026-07-28), O-14 (`23b916e`, 2026-07-29), and this branch's own predecessor's
   campaign (branched off `19d5532`, which already contains `27d349b`). Item 27's own closure
   text independently re-verified the fix effective on 2026-07-30, the same day as the
   predecessor branch's campaign.
2. **This falsifies, not just leaves-unconfirmed, item 29's own `## Round 2` inference** that
   its `291`/`306` landing values "look more like the already-documented mode-C/D
   scroll-anchoring shape... bleeding into this test." That mechanism was off for the entire
   window these values were captured in.
3. **Built a cross-item timeline table (14 rows) across all three dossiers**, converting every
   logged `before`/`after` pair with a known 900px viewport into an implied `scrollHeight`
   (`before + 900`). Found the `after=306` value recurs identically across two different tests
   and two different starting baselines, at two different times (once pre-fix, legitimately
   anchoring-explained; three times post-fix, not).
4. **Traced the implied heights back to exact values already logged elsewhere in the record**
   (`959` = the corpus tab's just-entered, nothing-rendered height per O-9's own spy dump;
   `1206` = the flat height of O-8's mode-B captures and doc2's isolated instrument) — proposed
   a transient max-scroll-clamp hypothesis (item 29's forced-ordering construction holds a
   fetch open specifically to block `_renderCorpusList()`, keeping the DOM small for most of
   the test, structurally similar to why doc2's isolated instrument saw the same clamp).
   **Labeled as inference, not fact** — no capture in the whole family has `scrollHeight`
   logged at the moment of an `after != before` read, so this is untested.
5. **Sanity-checked items 30/31** by reading their item files directly: neither mentions
   scroll/anchoring/`_captureScrollY` anywhere, distinct code paths, no reason to revise their
   "unrelated" classification.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) ·
`pytest -m "not ux" -n auto` — 2107 passed / 1 skipped (550s) ·
`pytest -m ux` — 129 passed / 1 xfailed / 1 xpassed, run in 4 chunks (a11y+flows: 11 passed,
101s; regression split 3-way via `split -n l/3 -d` on a file listing: 27 passed/132s, 40
passed/160s, 51 passed+1 xfailed+1 xpassed/211s) · `work_items check` ✓ (31 files) ·
`check_doc_links` ✓ (315 tracked files).** Genuinely clean, no reruns anywhere in the log,
matches the historical 131-total baseline exactly. This branch made no production-code
changes — docs and work-item files only — so the gate is a confirmation run, not a
regression check, but it was run in full per the Hard constraints below (no docs-only carve
out exists).

**Process note for whoever runs the gate next (unchanged from the predecessor's own note):**
this environment's Bash tool caps a single call's timeout at 600s: the full non-ux tier
(`-n auto`) fits in one background call (~550-590s); the full ux tier does not (~7-8 min this
run, historically up to ~20-23 min) and needs chunking — split `tests/ux/a11y` +
`tests/ux/flows` (one call), then `tests/ux/regression`'s ~50 files into 3 roughly-equal
groups via `split -n l/3 -d` on a file listing written to disk first (Git Bash's `split`
cannot determine stdin size if piped directly). **Never run two Playwright/pytest-ux
processes concurrently, including across your own chunks** — `scripts/gate.py`'s own
docstring documents this reproduces the exact CPU-saturation flake class this whole epic
investigates; wait for each chunk's own completion notification before starting the next,
do not poll or schedule a wakeup to check on it (see `feedback-schedulewakeup-not-for-
background-bash` — this session hit that exact mistake once, mid-gate, and self-corrected).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessor):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded.

**Open is still 12 / 10 ceiling — OVER, net 0 this session** (item 29 corrected but not
closed; no items closed, no new items filed — this session's finding was folded into item
29's and the epic's existing entries rather than filed as a new candidate). Still over
ceiling — a reduction sprint remains flagged, per charter W-1.

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
   item 29 corrected this session (new hypothesis, no fix), still open.
6. Item 20 — legacy `generate()` reachable via wizard rail without
   freezing Compose (`decision_owner=user`).
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
8. Item 22 — 4 call kinds never logged despite real call sites.
9. **Item 28** (epic 19 child) — O-13, one sample, untested
   `loadComposition` call site of the `_captureScrollY`/`_restoreScrollY`
   primitive (`before=400 after=796`). This session's review confirmed it also post-dates the
   anchoring fix (same commit as O-12, `6bb7d47`, 2026-07-28) — its "well above baseline"
   shape is also NOT anchoring-explained, but was not independently checked against the new
   height-clamp hypothesis (different call site, different tab/flow). Do not assume it shares
   item 29's mechanism without its own check.
10. **Item 29** (epic 19 child) — O-12/O-14, the O-10 regression test itself fails under
    resource contention. Corrected substantially this session (see above); still open, no
    mechanism proven, no fix. **The next branch's first move is the review doc's own
    `## Falsification` experiment — do not re-derive a new hypothesis first.**
11. **Item 30** (epic 19 child) — keyboard-reorder timeout, one sample, no
    diagnosis yet, re-confirmed this session as explicitly unrelated to the scroll-position
    mechanism (sanity check only, no new diagnosis work).
12. **Item 31** (epic 19 child) — network-retry assertion flake, one
    sample plus one clean isolated rerun, re-confirmed this session as explicitly unrelated to
    the scroll-position mechanism (sanity check only, no new diagnosis work).

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
handoff — item 29 corrected in place, nothing closed or newly filed). **New process
observation, not itself a ledger item:** this is the second consecutive session to find an
inference in this scroll-flake family that looked plausible from code/pattern inspection but
was wrong once checked against git history precisely (the first: item 27's own stale-filing
discovery, that the epic never cross-referenced an already-fixed dossier; this session's: an
inference stated as a labeled hypothesis, correctly, but not checked against commit ancestry
before being written down). Neither was a C-7 violation — both were correctly labeled as
unproven — but both show the value of `git merge-base --is-ancestor` as a cheap, mechanical
check before trusting a "this looks like X, already documented" read, worth reaching for by
default in this family going forward.

---

## What this branch should build

**N/A — this was a review branch, already closed out above.** For the NEXT branch
(`fix/ux-restore-scroll-y-resource-contention`, reused name): run the experiment specified in
`docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md`'s own `## Falsification` section —
add `documentElement.scrollHeight` (and `window.innerHeight`) to the value(s) captured at the
moment of the final `after` read in
`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`, re-run the confirmed
`-n2`-within-suite vector (`capture_contention_n2.sh`, referenced in item 29's own dossier)
until an `after != before` failure (not the `before=0` shape) is caught with height data
attached, and follow that doc's own stated decision tree for what each outcome means. Do not
extend to item 28's `loadComposition` call site without its own independent height-at-read
check — a different call site's `796` value was not verified against the same hypothesis this
session. Scope is bounded to item 29's own falsification experiment and whatever new,
evidence-backed next step it produces — not to items 9, 13, 14, 15, 20, 21, 22, 28, 30, or 31.

---

## First move

Create `fix/ux-restore-scroll-y-resource-contention` off `main` (reusing the name — see
"Branch to create" above for why). Read `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md`
and `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` together, in that order,
before writing any code. The `require-evidence-before-fix` hook will pass immediately (the
dossier already has a filled `## Observed`), but read it anyway — the corrected `## Round 2`
and the review's own hypothesis are what the next instrument targets. Build the
`scrollHeight`-at-read instrument as the FIRST commit (per C-7, this is still an instrument,
not a fix — no production code should change until the experiment's result is in hand and
points at something to fix).

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
