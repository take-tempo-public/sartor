<!-- provenance: schema=1 session=d3fc1837-ade4-49d5-bca0-56a3674a3d07 branch=chore/large-corpus-re-observation commit=f151d69 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-07-24 -->

# Agent handoff: after `chore/large-corpus-re-observation` (measurement branch, no production code changed)

**Branch to create:** `fix/merge-suggestions-cost` (branch off `main`)
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
ledger item (large-corpus scalability), **not** part of the RELEASE_ARC numbered
fork sequence (steps 11b-17).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`fix/ux-scroll-wizard-rail-flake`~~ ✓ (merged, PR #67) — investigation, no
  fix; mode C established as Chromium scroll anchoring.
- ~~`chore/large-corpus-re-observation`~~ ✓ **this branch — measurement only.**
  Produced the per-surface cost table, refuted the ledger row's own framing,
  and split it into two open rows.
- **`fix/merge-suggestions-cost`** ← next, **owner-directed this session**
- further fork items (RELEASE_ARC steps 11b-17) ← do not start these

**Do not pick a fork item on your own initiative.** The owner directed the
merge-suggestions fix specifically, in the same session that produced the
evidence for it. **Do not also take the render-cap item** (the second new ledger
row) into the same branch — the owner deliberately filed them as two rows
because they are disjoint failure modes with different fixes.

---

## What just landed on `main`

**Commits `78532cc`, `4c8c1cc`, `b8c6d60`, `f151d69`** (branch
`chore/large-corpus-re-observation`). **Zero production code changed** — this was
a measurement branch by design. Files touched: `scripts/bench_corpus_scale.py`
(new instrument), `docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md` (new cost
table, O-1…O-6), `docs/dev/perf/data/large-corpus-curve.json` (raw results),
`docs/dev/RELEASE_CHECKLIST.md` (ledger), and this session's provenance ledger
file.

Gate: **ruff ✓ · ruff format ✓ (320 files) · mypy ✓ (335 files) · pytest ✓**
— non-UX `2057 passed, 1 skipped, 128 deselected` in 12:13; UX tier
`126 passed, 1 xfailed, 1 xpassed, 2058 deselected` in 7:59. **`0 RERUN` in
both** (checked explicitly — a rerun would mask a fail-fail-pass as a bare
`PASSED`). The single `xpassed` is one of the two `xfail(strict=False)`
wizard-render instruments the prior branch demoted; `strict=False` keeps its
xpass visible by design, and it is not a new signal.

Run in stages rather than as one `python -m scripts.gate` call, because a single
call exceeds the agent's per-command wall-clock ceiling. This is known
carry-forward ledger item 1, not a new problem — but it means "gate green" here
is an **assembled** result. Re-run it whole if you need a single-command
attestation.

**The headline, and it is not what the ledger row predicted.**
`GET /corpus/merge-suggestions` costs **~6.9 s** (4 701 / 9 127 ms min-max) on the
owner's **real, ordinary 8-role corpus** and returns a **29-byte empty list**. The
entire cost is deciding there is nothing to show. The row was filed as a
*large-corpus scalability* risk; it is a **live defect at ordinary size**. Corpus
growth makes it worse — it did not create it.

**The finding that explains why this went unseen for so long.** The
duplicate-heavy corpus (the shape the prior branch's instrument used) is **26×
FASTER on the server** than an ordinary one. `bullet_overlap` /
`shared_bullet_count` try an exact normalized-set membership test and only fall
through to `difflib.SequenceMatcher` when it misses
(`onboarding/experience_match.py:196-198`). Repeated bullets hit the fast path;
distinct bullets never do. **The fast path fires only for the corpora that need
the feature least.** An instrument built to be adversarial was exercising the
cheap path.

**Measured, in the committed table — do not re-derive any of this:**

- Curve (realistic profile): **647 ms / 10.2 s / 42 s / 97 s** at 8 / 24 / 48 / 96
  roles. Cost per pair is ~22–27 ms across a 163× range in pair count ⇒ **O(n²)
  in experiences**.
- **Bullet TEXT length dominates at real scale.** 222-char real bullets vs
  ~100-char synthetic explains a **10.7×** gap under `SequenceMatcher`'s O(L²).
- Tier 2 render: 6× realistic settles in **47.6 s** with a small DOM; 6×
  duplicate renders **142 682 px / 1 086 cards** with a fast server. **Two
  disjoint failure modes**, previously one ledger row.
- **`applications` is clean** — flat **3 queries** across a 12× range. The
  `1+2N → ~3` `selectinload` collapse is holding, no regression.
- **`corpus list` carries a latent ~2N+2 N+1** (18 / 50 / 98 / 194 queries).
  Harmless today at 271 ms.

**Honesty caveats stated in the table and repeated here, because they bound what
you may claim:** the medians are noisy (6× ranged 30.8–42.9 s; 12× is a single
sample), so the exponent is pinned to "tracks pair count within measurement
noise", **not** to a precise power. And the synthetic generator draws from a
14-company pool, so suggestion **counts** at ≥24 roles are inflated; the
**timings** are not, because the wasted work happens before the company gate.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s
Carry-forward ledger (`#### Open`). **Rendered open count: 11** (net +1 this
session: the large-corpus row resolved, two new rows filed). Re-counted by
counting the actual `- [ ] **` bullets, not by arithmetic. One line each, in
ledger order:

1. The quality gate is unrunnable by an agent in one shot (~15-25 min,
   background-Bash kill risk around 5-10 min) — makes it unenforceable as a
   single command. **Hit again this session** (see the gate note above).
2. `test_corpus_reload_preserves_scroll_position` mode-C follow-on — mechanism
   directly observed (Chromium scroll anchoring); **still no fix**; round 6 arms
   B/C specified and not run.
3. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic
   fold-in only, not a standalone branch.
4. PyPI wheel not installable — **RESOLVED-PENDING-PUBLISH**, owner-gated
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
10. **`GET /corpus/merge-suggestions` costs ~6.9 s on an ORDINARY 8-role corpus
    and returns an empty list — NEW this session.** O(n²) in roles; the
    quadratic term is `bullet_overlap`, computed unconditionally before the
    cheap company gate can reject the pair. **This is the next branch.**
11. **The merge-suggestion panel renders uncapped — 142 682 px at 48
    duplicate-heavy roles — NEW this session.** The client-side half. Separate
    row deliberately; **do not fold it into item 10's branch.**

**The ceiling is ~8-10 open items; this ledger is now at 11 — one ABOVE the
ceiling, so a reduction sprint is overdue, not merely due** (charter W-1). The
owner accepted the +1 knowingly, choosing two accurate rows over one convenient
one. Freely solo-closeable right now: item 9.

---

## What this branch should build

1. **Cut the merge-suggestions cost** — `onboarding/experience_match.py`
   `score_experiences()` (`:211-256`) currently computes `bullet_overlap(...)`
   at `:222` **unconditionally**, before the `comp < COMPANY_GATE` test at
   `:232` can reject the pair. Company similarity is cheap; bullet overlap is
   the quadratic term. Compute the gate first and short-circuit.
   **This is the filed direction, and it is UNVERIFIED** — the saving depends on
   what fraction of pairs the company gate rejects, which the cost table does
   **not** measure. Measure that fraction first; if it is small, this fix does
   little and you need a different one (memoizing `_normalized_bullets` per
   experience, or capping the pairwise scan, are the obvious rivals).
   Authorized by `RELEASE_CHECKLIST.md` Carry-forward ledger › Open item 10.
2. **A/B the fix against the committed numbers** using
   `scripts/bench_corpus_scale.py` — `--db <copy> --username <u>` for the real
   corpus (the 6 930 ms figure), `--size {1x,3x,6x} --profile realistic` for the
   curve. **Do not trust a fix measured only on the synthetic 1x point**; the
   real-corpus number is 10.7× larger and is the one that matters.
   `docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md` is the baseline to beat;
   record before/after with provenance to `docs/dev/perf/data/`.
3. **Add a regression test** that pins whatever invariant the fix establishes
   (e.g. company-gate rejection short-circuits before bullet scoring), so a
   later refactor cannot silently reintroduce the unconditional call.

**Scope is bounded to Carry-forward ledger item 10.** Do not expand beyond it —
in particular **do not** take ledger item 11 (the uncapped render), and **do
not** opportunistically fix the corpus-list N+1 noted inside item 10; both are
separate, deliberately.

---

## First move

Create branch `fix/merge-suggestions-cost` off `main`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

Note that this is a `fix/*` branch, so `require-evidence-before-fix` will block
production edits until `docs/dev/diagnosis/large-corpus-merge-suggestions.md`
has a filled-in `## Observed` section. **You already have the observations** —
they are in `docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md` and should be
cited into the dossier, not re-derived. What is **not** yet observed is the
company-gate rejection fraction; that measurement is the honest first commit.

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
