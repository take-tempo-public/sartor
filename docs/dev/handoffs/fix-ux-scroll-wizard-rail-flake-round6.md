<!-- provenance: schema=1 session=15449f40-e54a-402e-8a31-d175331b5dd6 branch=fix/ux-scroll-wizard-rail-flake commit=77c7843 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-26 -->

# Agent handoff: after round-6 `fix/ux-scroll-wizard-rail-flake` (carry-forward ledger item 2, STILL OPEN — investigation + two falsified fix attempts)

**Branch to create:** none directed yet — see "Where we are in the arc" below.
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

## Where we are in the arc

**Stream:** v1.1.0 endgame. This branch was a solo-closeable carry-forward
ledger item (item 2, mode-C scroll-anchoring flake, round 6), **not** part
of the RELEASE_ARC numbered fork sequence (steps 11b-17).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`fix/ux-scroll-wizard-rail-flake`~~ ✓ (merged, PR #67, rounds 3-4) —
  investigation, no fix; mode C established as Chromium scroll anchoring.
- ~~`chore/large-corpus-re-observation`~~ ✓ (merged, PR #68) — measurement
  only; established a real defect and split it into ledger items 10 and 11.
- ~~`fix/merge-suggestions-cost`~~ ✓ (merged, PR #69) — item 10 resolved.
- ~~`fix/merge-suggestions-render-cap`~~ ✓ (merged, PR #70) — item 11
  resolved.
- **`fix/ux-scroll-wizard-rail-flake` (this branch, reusing the historical
  slug — round 6, not merged)** — arms A/B/C run (all negative), two fresh
  wild captures (O-18) pinned the exact mechanism, two fix attempts built on
  it and **both falsified** (F-8) — see "What just landed" below. **Item 2
  is still open. No fix has ever landed on this defect, on any branch.**
- **No branch owner-directed next.** Per AGENTS.md "Do not pick a fork item
  on your own initiative," the owner must direct the next branch explicitly.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged, and unlike every
prior branch this session, it has no code change to merge.** Three commits
on `fix/ux-scroll-wizard-rail-flake`, not yet pushed:

- `6e3c95d` — round 6 arms B (no preceding shrink) and C (active
  `_restoreScrollY` settle loop): 20 armed runs combined, 0 shifts. Both
  refuted as the ~1-in-6 selector, joining arm A (already negative, prior
  session). New tests:
  `test_merge_suggestions_append_with_no_preceding_shrink_shifts_scroll`,
  `test_merge_suggestions_growth_during_active_restore_loop_shifts_scroll`.
- `e9a94f8` — **O-18**: CPU-saturation wild-capture (established 10-loader/
  8-core calibration produced only an unrelated, already-known
  `#panelCorpus` timeout — recalibrated to 6 loaders) surfaced 2 genuine
  `300 -> 369` mode-C captures in 14 runs. Both show the identical precise
  mechanism: `refreshCorpus()`'s fire-and-forget `refreshMergeSuggestions()`
  call (no capture/restore of its own) straggles past its own cycle's exit
  and lands unprotected between an external baseline read and a separate,
  later `refreshCorpus()` call.
- `77c7843` — **F-8**: two fix attempts built on O-18, both tested against
  the REAL target test (not just narrow falsification tests), both
  falsified and fully reverted. **Attempt 1** (independent capture right
  before `_loadMergeSuggestionsPage`'s DOM mutation): broke 3
  previously-passing tests — a nested capture, when its fetch resolves
  while the PARENT `refreshCorpus()` cycle is still mid-render, can read a
  transient value and illegitimately outrank its own parent's correct
  capture. **Attempt 2** (await `refreshMergeSuggestions()` + pass the
  parent's own capture down): fixed attempt 1's regression cleanly, but
  made each `refreshCorpus()` cycle take measurably longer to exit,
  widening a DIFFERENT window where a second, concurrent cycle can overlap
  the first. Measured directly: **4 failures in 10 runs with NO CPU
  saturation (40%)** — worse than the original defect's ~1-in-6 rate
  **under** saturation. Both attempts fully reverted
  (`git checkout HEAD -- static/app.js tests/...`) before this commit.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (336 source files) · pytest ✓** —
non-UX `2060 passed, 1 skipped, 131 deselected` in 361.57s; UX tier
`129 passed, 2 xfailed` in 350.81s. **0 reruns in both** (checked
explicitly).

**The result:** ledger item 2 is documented far more precisely than at
session start — the exact corrupting call, its mechanism, and why it's hard
to fix are now on record (O-18, F-8) — but the defect itself is **unfixed**,
and this session leaves it with **one more falsified path** than it found.
This is investigation-and-falsification work, not a shipped fix — same
shape as `chore/large-corpus-re-observation`'s prior session.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s
Carry-forward ledger (`#### Open`). **Rendered open count: 9** (net 0 this
session — no items resolved, none filed; item 2 stays open with more
evidence attached). Re-counted the actual `- [ ] **` bullets in the
ledger's Open subsection, not by arithmetic: 9, confirmed. One line each,
in ledger order:

1. The quality gate is unrunnable by an agent in one shot (~15-25 min,
   background-Bash kill risk around 5-10 min) — makes it unenforceable as a
   single command. **Hit again this session** (ran in two backgrounded
   stages, twice).
2. **Ledger item 2 itself** (`test_corpus_reload_preserves_scroll_position`
   mode-C) — this branch's own subject. Mechanism now precise (O-18); two
   fix attempts falsified (F-8); still open, still no fix. The one
   genuinely untested candidate remaining: reserve the merge-suggestions
   list's height before its second-stage layout lands, so the document
   never grows above the anchor at all (dossier `## The fix` #2).
3. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic
   fold-in only, not a standalone branch.
4. PyPI wheel not installable — RESOLVED-PENDING-PUBLISH, owner-gated
   (PyPI/GHCR console access, blocked on the GitHub repo rename).
5. In-app rendered citation viewer — deferred, no friction signal yet.
6. Grounding / hallucination metric (calibrated layers B) — owner-gated
   (manual annotation + threshold-setting pass).
7. 2026-07 efficiency review (PX-37..56) — 3 of 20 rows remain, all
   owner-gated (E2E corpus access / scope calls / irreversible-if-botched).
8. Compose-time rewrite latitude dial — [OWNER DECISION], evidence-gated on
   item 7's PX-39 run.
9. `docs-site/`'s shields.io badge-fetch build flake — solo-closeable, not
   merge-blocking, will recur on every future PR until fixed.

**Well within the ~8–10 ceiling.** Freely solo-closeable right now: item 9
(`docs-site` badge flake).

---

## What this branch should build

Nothing further — no branch has been created or directed for what comes
next. The next agent's job is to get explicit owner direction on which
ledger item to pick up, per "Where we are in the arc" above. **Do not
self-select a third attempt at item 2's fix** — the owner should decide
whether to try the one remaining untested candidate (reserve-height, dossier
`## The fix` #2), pursue a different mechanism entirely, or defer this item
further. Whoever attempts a THIRD fix must read F-8 in full first and design
explicitly for the overlapping-invocation problem it exposed, not just the
straggler-past-exit problem O-18 found — a fix that only reasons about one
`refreshCorpus()` cycle in isolation has now failed twice.

---

## First move

Do not create a branch yet. Confirm with the owner what to work on next.
Once directed, follow the same pattern: write a plan at
`~/.claude/plans/<slug>.md` and show it to the user before touching any
code. **Do not code first.**

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
