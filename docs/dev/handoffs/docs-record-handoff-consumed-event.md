<!-- provenance: schema=1 session=aeb70086-9241-447c-a909-90a58741fe4f branch=docs/record-handoff-consumed-event commit=4bd1202 actor=amodal1 agent=claude-sonnet-5 generated_at=2026-07-22 -->

# Agent handoff: `docs/record-handoff-consumed-event`

**Branch to create:** none directed by this session — same as its predecessor
(`docs/record-orphaned-ledger-event`); this branch was a paperwork fix plus a process
fix, not a step in the release arc. See "What this branch should build" below for
candidates.
**Base branch:** `main` (once this branch has merged)

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

**Stream:** v1.1.0 endgame. This branch is NOT part of the Dependabot-backlog lineage —
it is a one-off provenance-hygiene fix plus the process fix that (should) retire this
whole class of fix.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`docs/record-orphaned-ledger-event`~~ ✓ (merged, PR #46) — landed one orphaned
  provenance file, one session late
- **`docs/record-handoff-consumed-event`** ← **this branch** — landed this session's
  own consumed-event ledger record, AND fixed the process gap that caused both of the
  last two branches to exist
- next branch ← **not directed**; see "What this branch should build" below

**Do not pick any fork item (RELEASE_ARC steps 11b-17, other than the #10/step-17 note in
`chore/dependabot-group-a`'s own handoff) on your own initiative.**

---

## What just landed on `main`

`main` is at `ac44145` (merge of `docs/record-orphaned-ledger-event`, PR #46). **This
branch has not merged yet** — pending the PR flow below.

**What this branch did — two things.**

1. **Landed the paperwork.** Committed `docs/dev/ledger/aeb70086-....jsonl`, this
   session's own `consumed`-event record for the handoff it read at session start
   (`docs/dev/handoffs/docs-record-orphaned-ledger-event.md @ main ac44145`). Same
   category of file as the previous two branches' fix — landed promptly this time,
   same session, instead of going untracked for a day first.

2. **Fixed why that keeps happening.** The user asked, mid-session, for a durable fix
   rather than a third repeat of this exact branch. Root cause, traced through
   `docs/dev/prov/SPEC.md` §5 and `docs/dev/handoffs/README.md`: the consumption
   workflow tells a session to run `--event consumed`, which writes a new untracked
   `docs/dev/ledger/<session>.jsonl` **on `main`, before any branch exists** — but
   never said who lands that file. A `generated` event's file rides along with the
   branch that produced the doc it describes; a `consumed` event's file has no branch
   yet. That gap fired twice (`feat-rerun-rate-alarm`'s orphaned record, then this
   session's own), each patched with a one-off dedicated branch+PR — itself a bad
   pattern to repeat every session.
   - Added an explicit landing rule to `docs/dev/prov/SPEC.md` §5 (new step 3) and
     `docs/dev/handoffs/README.md`'s Consumption bullet: fold the consumed-event
     ledger commit into the **first commit of the next branch** the session creates —
     no dedicated branch/PR needed going forward. If a session ends without creating
     any branch, it must name the stray file in `RELEASE_CHECKLIST.md`'s
     carry-forward ledger so the next session's first branch picks it up.
   - Mirrored the same obligation into the pre-close sweep (step 0) in both
     `AGENTS.md` and `docs/dev/AGENT_HANDOFF_TEMPLATE.md`'s verbatim block, so it's
     checked at every close, not just remembered.
   - **This branch itself does NOT test the new rule** — there was no "next branch"
     in-session to fold a ledger commit into; it used the old dedicated-branch pattern
     one last time. The new rule takes effect starting with whatever branch this
     session's successor creates.

**Gate:** ran the full `python -m scripts.gate` — docs-only change, but the
quality-gate rule has no carve-out for docs-only branches. `ruff check .` ✓ ·
`ruff format --check .` ✓ · `mypy .` ✓ (0 errors, pre-existing `annotation-unchecked`
notes only) · `pytest` **2180 passed, 1 skipped, 0 failed** in 856s (14m16s) —
`gate: all steps passed.`, exit 0.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Unchanged from `chore/dependabot-group-a`'s own handoff — this branch touched
provenance process docs, not a tracked ledger item. Full detail lives in
`docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`), confirmed still
**19 open** by re-reading that section this session (see
`docs/dev/handoffs/chore-dependabot-group-a.md` for the full one-line-each mirror —
not reproduced a third time here since nothing on this or the prior branch changed it).

---

## What this branch should build

Nothing is directed for a next branch by this session — same situation as this
branch's own predecessor. Candidates, in rough priority order per the open ledger,
still stand; **none of these is a standing authorization** — pick with the normal
plan-mode ceremony:

1. **The overdue reduction sprint** (19 open items, ceiling ~8-10) — several are
   owner-gated or owner-decision items that may need the owner's attention rather than
   more engineering.
2. **The docs-site `npm audit` finding** (its own dedicated `next`/`sharp` upgrade
   branch) — split out of the now-closed Dependabot backlog item on
   `chore/dependabot-group-a`.
3. **PX-39** — unblocked per a prior session's note, not yet run.

Scope for whichever is picked: bounded to that item alone. **Do not expand into the
fork items** (RELEASE_ARC steps 11b-17, except #10's own step-17 handling at release
time).

**Process note for whoever picks next:** per the new rule landed on this branch, when
you consume this handoff you will write your own `docs/dev/ledger/<session>.jsonl` on
`main` before creating any branch. Do not open a dedicated branch for it — fold its
commit into the first commit of whichever candidate branch above (or other directed
work) you create next.

---

## First move

Whatever branch is picked next: write a plan at `~/.claude/plans/<slug>.md` and show it
to the user before touching any code. **Do not code first.**

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
