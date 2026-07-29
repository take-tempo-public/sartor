<!-- provenance: schema=1 session=92f86de5-e4ab-457c-9fb8-9f0cf077e98e branch=docs/pipeline-truth-and-era4-baseline commit=b226d04 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-29 -->

# Agent handoff: after `docs/pipeline-truth-and-era4-baseline` (pipeline docs truth pass + Era 4 real-corpus baseline — DONE)

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

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s
endgame-steps prose (both retained as historical narrative with inline
"MIGRATED to work item N" / "RESOLVED" pointers, not deleted).

**Stream:** v1.1.0 endgame.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`chore/work-item-tracking`~~ (merged) — built the work-item tracker; this
  branch's own predecessor.
- **`docs/pipeline-truth-and-era4-baseline` (this branch, not yet merged) — DONE.**
  Full detail below. Resumed item 6 (PX-39), found its filed method couldn't
  work, closed it with a different deliverable (Era 4 baseline), fixed
  `docs/architecture.md`'s three-diagram staleness this surfaced, closed item
  17 (doc contradiction) across 4 files, and filed 3 new items from what the
  pipeline trace found.
- **No branch owner-directed next.** Per AGENTS.md "Do not pick a fork item on
  your own initiative," the owner must direct the next branch explicitly.
  **Read `docs/dev/work/BOARD.md` for the current fork** — 10 open (at the
  W-1.4 reduction-sprint ceiling) / 4 blocked / 2 deferred / 3 watching, 5
  closed. **Two unresolved threads take priority over any board item** — see
  "Still-pending, unresolved thread" below; ask about those FIRST.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged; nothing has been
committed yet.** `main` is currently at `b226d04` (the `chore/work-item-tracking`
merge, PR #75 — the structured work-item tracker + real gate fix this
session's predecessor completed). This branch's own work, once committed,
will be the next thing to land:

1. **Item 6 (PX-39) closed — with a different deliverable than filed.** The
   filed plan (`analyze`+`generate` summed per `run_id`, matching Era 2's
   methodology) has no subject on 13 of 15 real Sonnet-5-era application runs:
   the frozen-composition path (Compose → deterministic assemble) never calls
   `generate()` at all. Defined a new **Era 4** in
   `docs/dev/perf/PERFORMANCE_HISTORY.md` instead — total LLM wall-clock +
   cost per completed application, summed per `run_id` — using zero-spend
   historical telemetry (128 records, owner's own real usage 2026-07-06 →
   2026-07-28, copied into this project's gitignored `logs/llm_calls.jsonl`):
   frozen path n=13, p50=109.3s, $0.2508/application; legacy path n=2, raw
   observations only (86.2s/163.9s), no p50 published at that sample size.
   Single-user traffic, pre-1.1-tag — flagged for re-measurement once real
   users arrive. The doc's own embedded reproduction snippet was run and
   verified to reproduce these exact numbers byte-for-byte.
2. **`docs/architecture.md` brought current.** Verifying PX-39 surfaced that
   all three Mermaid diagrams (pipeline sequence, LLM routing, context-set
   lifecycle) and the surrounding prose still described the pipeline shape
   from *before* `fix/compose-frozen-composition` (merged 2026-07-06) —
   missing the Compose-time Sonnet drafting calls (`draft_positioning_summary`,
   `draft_gap_fill_bullets`), the freeze step (`approved_composition`), and
   the frozen-vs-legacy branch at Generate. All three diagrams + prose fixed;
   `docs/wiki/pages/pipeline-stages.md` and `llm-call-catalog.md` were already
   accurate and served as the source. Also fixed a circular-staleness bug
   this same edit introduced and caught: `llm-call-catalog.md` pointed at
   `architecture.md`'s LLM routing diagram for "real p50 latencies" — a
   diagram this branch deliberately stripped of stale per-call latency
   numbers. Also corrected: `app.py` cited as route-map source (it has zero
   routes since Sprint 8.3h — should be `blueprints/`); a stale `$1.50`/full-run
   eval-cost figure (superseded by Sonnet-5 pricing, ~$0.30-0.40, already
   fixed elsewhere in the repo — same category of small unambiguous fix).
3. **Item 17 (doc contradiction) closed — wider than filed.** Filed as a
   two-file PERFORMANCE_HISTORY.md/RELEASE_ARC.md tension; actually four
   files: `PERFORMANCE_HISTORY.md`'s Open Item contradicted itself internally
   (line demanding non-`eval:*` traffic, next line offering the always-`eval:`-
   prefixed harness as a way to get it); `RELEASE_ARC.md` step 12 prescribed
   that harness anyway; `evals/runner.py` is structurally incapable of
   producing non-`eval:*` records (hardcodes the prefix at 5 sites, uses it as
   its own cost-attribution key); `COMPOSE_REWRITE_DIAL.md` assumed the same
   harness method would produce item 8's evidence. All four corrected. Also
   widened the traffic taxonomy: the log carries **three** population
   classes, not two — `eval:*` / `bootstrap:*` / bare (live) usernames — now
   documented in `PERFORMANCE_HISTORY.md`'s Era 4 caveats.
4. **Item 8 updated, kept blocked (owner directive).** `depends_on = [6]` and
   `status = blocked` preserved exactly as the owner directed — only
   `COMPOSE_REWRITE_DIAL.md`'s now-false "same paid runs yield both" premise
   was corrected (item 6 closed via zero-spend historical telemetry, so no
   fresh run happened and no side-by-side was produced, independent of the
   already-noted Microsoft-JD exclusion).
5. **3 new items filed** from what the pipeline trace surfaced: item 20 (a
   legacy `generate()` path still reachable by skipping Compose — the wizard
   rail gates Step 5 only on a context path, not on freeze; owner called this
   "not appropriate behavior" when told), item 21 (`check_refinement_scope`
   calls the API directly, bypassing `_call_llm` — no telemetry row, cost
   invisible), item 22 (4 call kinds with real call sites, zero rows ever
   logged — dead paths or an instrumentation gap, not yet distinguished).
6. **`SECURITY.md` corrected** — it described `logs/llm_calls.jsonl` as
   containing "request bodies + responses"; the file is 13 fields of
   metadata only (verified against `analyzer.py:_emit_call_log`), never
   prompt/response text.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 files) · `pytest -m "not ux" -n auto` ✓
(2104 passed / 1 skipped) · `pytest -m ux` ✓ (129 passed / 1 known xfail / 1 known
xpass, matching prior sessions exactly — not a regression) · `work_items check` ✓
(22 files).** No production code changed this branch — docs + work-item files only.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note, this handoff (same as predecessor):** `docs/dev/work/BOARD.md`'s
full Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded, per
"Where we are" above.

**Open (10 / 10 ceiling — AT the W-1.4 reduction-sprint threshold, flag this):**
1. Item 9 — release/visual-assets refresh, screenshots stale.
2. Item 11 — bootstrap overwrite destroys prior annotation work, no merge/versioning.
3. Item 12 — judge JSON-parse failure silently scores as 0.
4. Item 13 — fixture `jd.txt` doesn't match its own annotations (depends on 11).
5. Item 14 — no JD-identifying metadata in bootstrap/eval artifacts (depends on 11).
6. Item 15 — suggested-skills rendering bug (comma-split inside parentheticals).
7. Item 19 — UX-suite flakiness solution sprint (scheduled, not yet investigated).
8. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose (new this branch — `decision_owner=user`, needs a product-flow decision).
9. Item 21 — `check_refinement_scope` LLM call invisible to telemetry (new this branch).
10. Item 22 — 4 call kinds never logged despite real call sites (new this branch).

**Blocked (4):**
11. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
12. Item 5 — grounding-score persistence gap (blocks calibrated L1/L2 metric layers).
13. Item 8 — compose-time rewrite dial, evidence path corrected this branch (see above), still blocked pending owner direction on the real evidence channel (likely `/tune-from-annotations`, not decided).
14. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9]` (6 now satisfied).

**Deferred (2):**
15. Item 4 — in-app citation viewer, no friction signal yet.
16. Item 7 — PX-46 memory consolidation, owner sign-off required first.

**Watching (3):**
17. Item 2 — wordmark sweep, opportunistic only.
18. Item 16 — `evals/runner.py --suite real` non-functional, needs a real JD + owner data.
19. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.

**At the 10-item WIP ceiling as of this branch.** Charter W-1.4's own
reduction-sprint threshold is ~8-10 — worth folding a reduction pass into
whatever's directed next, or directing one explicitly.

**Still-pending, unresolved thread — surface at next session start, ask about
these BEFORE defaulting to a board item:** carried forward unresolved from the
predecessor handoff, still not addressed — this branch was directed to resume
PX-39 instead. The owner said mid-session (predecessor's session) "the fixes I
am still gathering" (implying more UX/annotation findings beyond that
session's 6, not yet filed) and separately asked for a documentation-only
investigation "next session." Neither scope was ever clarified and
**deliberately not filed as a work item** — filing it half-understood would
misrepresent scope. Ask the owner directly what each should cover.

---

## What this branch should build

Nothing further — this branch is closed out. The next agent's job is to get
explicit owner direction — starting with the two still-pending threads above,
not the board's own most-obvious candidate. All open items are either
`decision_owner = "user"` or, for the `agent`-owned ones, still require the
owner to pick which one to schedule next given the WIP ceiling — there is no
freely solo-closeable item this branch left behind that should be started
without that direction.

Scope is bounded to what's on `docs/dev/work/BOARD.md`. Do not expand beyond
it, and do not invent new items without owner direction beyond what this
session already filed.

---

## First move

Do not create a branch yet. Confirm with the owner what to work on next —
start by asking about the two still-pending unresolved threads above (the
"still-gathering" fixes and the documentation-only investigation), since both
were carried forward a second time now without being scoped, before defaulting
to the board's own candidates (e.g. a reduction sprint, given the 10/10
ceiling, or item 20's product-flow decision). Once directed, follow the same
pattern: write a plan at `~/.claude/plans/<slug>.md` and show it to the user
before touching any code. **Do not code first.**

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
