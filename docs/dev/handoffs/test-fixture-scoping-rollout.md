<!-- provenance: schema=1 session=8c233fda-e904-476d-9705-89e6dda50919 branch=test/fixture-scoping-rollout commit=c9ff442 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-27 -->

# Agent handoff: after `test/fixture-scoping-rollout` (PX-44 46-file rollout — DONE)

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

**Stream:** v1.1.0 endgame. This branch executed step 11b (PX-44's 46-file
fixture-scoping rollout), owner-directed this session from the carry-forward
ledger's efficiency-review row — **not** part of the RELEASE_ARC numbered
fork sequence's other owner-gated steps (12/13/15/16).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`fix/docs-site-badge-fetch-flake`~~ (merged, PR #73) — FIXED: ledger
  item 8 (docs-site badge-fetch build flake).
- **`test/fixture-scoping-rollout` (this branch, committed `c9ff442`, not
  yet merged) — DONE.** Step 11b resolved: the 46-file PX-44 rollout
  landed. Full record in `docs/dev/perf/TEST_SUITE_PERFORMANCE.md`
  "Rollout result" section.
- **No branch owner-directed next.** Per AGENTS.md "Do not pick a fork item
  on your own initiative," the owner must direct the next branch explicitly.
  The remaining fork (steps 12/13/15/16/17 + the undesigned exemplar-resume
  question) is unchanged in shape — see "Carried-forward observations"
  below for the current 7-item list.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** Six commits on
`test/fixture-scoping-rollout`, not yet pushed:

1. **Batch A** (`592df27`) — shared `_fresh_migrated_db` helper added to
   `tests/conftest.py`; 11 corpus/skills-route test files converted.
   Excluded `tests/test_bundled_templates.py` mid-batch (discovered, not
   planned): it directly tests `init_db()`'s own migration behavior.
2. **Batch B** (`2242a99`) — 13 applications/drafts/summaries files.
3. **Batch C** (`55ca42b`) — 9 recommend/proposal/pending-review files;
   2 of these (`identity_app`, `b4_app`) never called `init_db()`
   explicitly (implicit migration via first route touch) — converted the
   same way.
4. **Batch D** (`82bad1c`) — 9 DB-touching fixtures across 9 files;
   2 files (`test_app_iterate_clarify.py`, `test_assistant_route.py`) had
   no DB-touching fixture at all and stayed untouched.
5. **Special cases** (`cd016ed`, `5c7382b`) — `test_app_security.py`'s one
   DB-touching fixture (`config_route_db_app`); `test_context_write_races.py`'s
   `races_app` (concurrent-request races against the same DB file — got a
   dedicated 15-runs-each-side flake-rate check before converting, 0/30
   failures both ways).
6. **Docs + wiki** (`00c109a`, `c9ff442`) — updated
   `docs/dev/perf/TEST_SUITE_PERFORMANCE.md` (new "Rollout result"
   section), `RELEASE_ARC.md` (step 11b DONE), `RELEASE_CHECKLIST.md`
   (ledger entry + tally), `CHANGELOG.md`; ran `/wiki-self-update` +
   `/wiki-lint` to resolve the wiki-freshness merge gate this branch's own
   file-touch volume tripped (see below).

**Total: 44 mechanical targets + 2 special-cased files, all onto the
migrated-template-DB mechanism.** Zero test-body changes anywhere — only
fixture bodies changed.

**Verification, in order:**
- Batched (11/13/9/11-file groups): each batch run forward + explicit
  reversed file order (pass counts identical both ways every time — 191,
  248×2, 90×2, 164×2), plus each batch run together with the
  immediately-preceding batch as a cross-batch check (439, 338, 254 —
  all clean).
- `races_app` flake-rate check: 15 runs before conversion, 15 after —
  0/30 failures both sides.
- Full fast-lane, chunked (3 file-list groups, never one `pytest tests/`
  call, per the ~13-min-gate / 5–10-min-agent-kill constraint this
  rollout is a partial mitigation for — ledger item #1): **2055 passed, 1
  skipped, 1 failed.** The 1 failure was the wiki-freshness merge gate
  (this branch's own 46-file touch count pushed the cumulative
  changed-since-checkpoint count from 38 on `main` to 83, past the
  75-file block threshold) — resolved via `/wiki-self-update` (0 pages
  needed changes) + `/wiki-lint` (PASS) in the final two commits;
  `tests/test_wiki_freshness_gate.py` now passes (10/10).
- This session's own timing microbenchmark (not re-citing the pilot's
  numbers as this rollout's evidence): `init_db` 84.4ms → `copy2` 1.0ms
  median, N=8, 98.8% reduction — consistent with the pilot's ~99% figure.

**Gate: ruff ✓ · ruff format ✓ (3 files auto-fixed, folded into commits) ·
mypy ✓ (336 files, 0 errors) · pytest — full fast lane green after the
wiki-gate fix above.** 0 reruns anywhere in any gate invocation (checked
explicitly, chunked runs throughout — never one long unchunked call).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s
Carry-forward ledger (`#### Open`). **Rendered open count: 7 (unchanged
this session)** — PX-44 lived inside the efficiency-review aggregate row,
not as its own numbered Open bullet, so this rollout's completion doesn't
change the top-level count; it moves that aggregate row's internal tally
from 3-of-20-remaining to 2. Re-counted the actual `- [ ] **` bullets in
the ledger's Open subsection, not by arithmetic: 7, confirmed. One line
each, in ledger order:

1. The quality gate is unrunnable by an agent in one shot (~15-25 min,
   background-Bash kill risk around 5-10 min) — makes it unenforceable as
   a single command. This rollout is a partial, indirect mitigation
   (cuts the dominant per-test setup cost across 46 more files) but does
   not itself resolve the underlying "an agent's shell commands can't
   cleanly observe a 15-25 min run" problem — no new evidence on the
   orphaned-process-vs-per-command-ceiling question this session.
2. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic
   fold-in only, not a standalone branch.
3. PyPI wheel not installable — RESOLVED-PENDING-PUBLISH, owner-gated
   (PyPI/GHCR console access, blocked on the GitHub repo rename).
4. In-app rendered citation viewer — deferred, no friction signal yet.
5. Grounding / hallucination metric (calibrated layers B) — owner-gated
   (manual annotation + threshold-setting pass).
6. **2026-07 efficiency review (PX-37..56) — 2 of 20 rows remain (was 3),
   all owner-gated: PX-39 (real-corpus measurement — unblocked, not yet
   run), PX-46 (memory-review cleanup).** PX-44 (this branch) is the row
   that just resolved.
7. Compose-time rewrite latitude dial — [OWNER DECISION], evidence-gated on
   item 6's PX-39 run.

**Well within the ~8–10 ceiling; no reduction sprint needed.** None of the
remaining 7 are freely solo-closeable without further owner input (all are
either owner-gated or deferred pending a signal).

---

## What this branch should build

Nothing further — the rollout is landed and this handoff is the close-out.
The next agent's job is to get explicit owner direction on which ledger
item to pick up next, per "Where we are in the arc" above. All 7 remaining
open items are owner-gated or explicitly deferred (see the list above) —
there is currently no freely solo-closeable item on the ledger. Of the 2
remaining efficiency-review rows, PX-39 is the more actionable one if the
owner wants to unblock it (needs `.api_key` + access to the owner's E2E
corpus data; also gates ledger item 7's compose-rewrite-dial decision).

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
