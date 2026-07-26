<!-- provenance: schema=1 session=41fae095-b4e4-454b-9668-c366cf5bc202 branch=fix/merge-suggestions-render-cap commit=6d893b7 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-25 -->

# Agent handoff: after `fix/merge-suggestions-render-cap` (carry-forward ledger item 11, RESOLVED)

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
ledger item (item 11, uncapped merge-suggestions render), **not** part of the
RELEASE_ARC numbered fork sequence (steps 11b-17) — same as its predecessors.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`fix/ux-scroll-wizard-rail-flake`~~ ✓ (merged, PR #67) — investigation, no
  fix; mode C established as Chromium scroll anchoring.
- ~~`chore/large-corpus-re-observation`~~ ✓ (merged, PR #68) — measurement
  only; established the real defect and split it into ledger items 10 and 11.
- ~~`fix/merge-suggestions-cost`~~ ✓ (merged, PR #69) — item 10 (server cost),
  30.8× real-corpus speedup, pure cost fix.
- ~~`fix/merge-suggestions-render-cap`~~ ✓ **this branch** — item 11 (client
  render), paginated the merge-suggestions render, resolved.
- **No branch owner-directed next.** Both halves of the large-corpus split
  (items 10 and 11) are now resolved. Ledger item 2 (mode-C scroll flake,
  still open, unfixed — see below) is a plausible next candidate on this same
  general surface, but per AGENTS.md "Do not pick a fork item on your own
  initiative" the owner must direct the next branch explicitly.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** Three commits on
`fix/merge-suggestions-render-cap`, not yet pushed:

- `27b461c` — instrument + falsification test (C-7 first commit): diagnosis
  dossier citing existing evidence (O-6: 1,086 cards/142,682px at 48
  duplicate-heavy roles; O-12: growth isolated to `#mergeSuggestionsList`)
  plus a new Playwright test confirming the defect on HEAD (28 rendered
  nodes for a 28-pair fixture, no cap). Also folds in this session's
  consumed-event provenance ledger file.
- `8f63b90` — the fix: `list_merge_suggestions` (`blueprints/corpus/curation.py`)
  now accepts `limit`/`offset` (default page size 25, clamped to 1000) and
  returns `total_count` + `has_more`; `refreshMergeSuggestions`
  (`static/app.js`) renders one page at a time and adds a "Show more"
  control. The existing scroll-flake regression test
  (`test_merge_suggestions_growth_shifts_scroll_deterministically`) was
  given an explicit `{ limit: 1000 }` override at both call sites so its
  single-call, full-growth reproduction of the *unrelated, still-open* mode-C
  flake (ledger item 2) is unaffected — confirmed by re-running it, both
  parametrized arms pass.
- `6d893b7` — ledger item 11 moved from Open to Resolved with the A/B
  numbers, `CHANGELOG.md` entry, and the new
  `docs/dev/perf/MERGE_SUGGESTIONS_RENDER_CAP_2026-07-25.md` results doc.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (336 source files) · pytest ✓**
— non-UX `2060 passed, 1 skipped, 129 deselected` in 362.92s; UX tier
`127 passed, 2061 deselected, 2 xfailed` in 477.02s. **0 reruns in both**
(checked explicitly). Run in two backgrounded stages, not as one
`python -m scripts.gate` call — known carry-forward ledger item 1, not new.

**The result:** `#mergeSuggestionsList` 142,682px/1,086 cards →
3,277px/25 cards (43.5×); document 146,798px → 7,438px (19.7×); settle
4,908ms → 2,471ms, all at the 48-role duplicate-heavy profile (O-6's worst
case). Suggestion computation/ranking unchanged — this is a pure render/
pagination fix, not a behavior change to which pairs surface.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s
Carry-forward ledger (`#### Open`). **Rendered open count: 9** (net −1 this
session: item 11 resolved, no new items filed). Re-counted the actual
`- [ ] **` bullets in the ledger's Open subsection, not by arithmetic: 9,
confirmed. One line each, in ledger order:

1. The quality gate is unrunnable by an agent in one shot (~15-25 min,
   background-Bash kill risk around 5-10 min) — makes it unenforceable as a
   single command. **Hit again this session** (ran in two backgrounded
   stages).
2. `test_corpus_reload_preserves_scroll_position` mode-C follow-on — mechanism
   directly observed (Chromium scroll anchoring); still no fix; round 6 arms
   B/C specified and not run. **This branch did not attempt this fix** — it
   only preserved this item's C-7 evidence test's exact behavior via an
   explicit override param while fixing the disjoint item 11.
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

**Well within the ~8–10 ceiling** (was 9 before this session too — item 11's
resolution was a straight −1 with no new filing). Freely solo-closeable
right now: item 9 (`docs-site` badge flake).

---

## What this branch should build

Nothing — no branch has been created or directed yet. The next agent's job
is to get explicit owner direction on which ledger item (or RELEASE_ARC fork
step) to pick up next, per "Where we are in the arc" above. Do not
self-select item 2 (mode-C flake) or any other item.

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
