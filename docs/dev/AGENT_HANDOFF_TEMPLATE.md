# Agent handoff prompt template

> **Purpose:** enforces a consistent structure for the next-agent prompt
> every closing agent writes at end of session. Fill in every
> `<!-- ... -->` placeholder. Do not delete any section. Fixed sections
> (Documents to read, Hard constraints, Close-out checklist) are copied
> verbatim — do not shorten or paraphrase them.
>
> **Companion:** AGENTS.md §"Branch close-out checklist" requires this
> template be used for every handoff prompt. RELEASE_ARC.md is the
> authoritative source for the arc progress table.

---

**Branch to create:** `<!-- branch-name -->` (branch off `<!-- base-branch -->`)
**Base branch:** `<!-- base-branch (usually main) -->`

---

## Documents to read before any tool call (in this order)

1. [docs/RELEASE_ARC.md](RELEASE_ARC.md) — authoritative branch sequence,
   architectural decisions, and acceptance criteria for v1.0.2 → v1.1.0.
   The durable plan. Do not deviate without user sign-off.
2. [docs/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) — what is open, closed,
   and deferred per release. Before proposing anything, check here first.
3. [docs/dev/AGENT_FAILURE_PATTERNS.md](AGENT_FAILURE_PATTERNS.md) —
   failure patterns to avoid. Read in full before writing any code.
4. [docs/architecture.md](../architecture.md) — module map and LLM routing
   boundary. The deterministic / LLM split is load-bearing.
5. [evals/TUNING_LOG.md](../../evals/TUNING_LOG.md) — baseline floors and
   prompt change history.

---

## Where we are in the arc

<!-- Copy the current branch sequence from RELEASE_ARC.md for the active
     stream. Strike through completed items with ~~text~~ ✓ and bold the
     current branch. One-line summary after each completed item. -->

**Stream:** `<!-- e.g. "v1.0.2 eval apparatus (PATCH)" -->`
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** `<!-- e.g. "v1.0.3 R1 Phase 2" -->`

- `<!-- ~~completed-branch~~ ✓ — one-line summary -->`
- **`<!-- this-branch -->`** ← this branch
- `<!-- next-branch -->` ← next after this
- `<!-- further-branches -->` ← do not start these on this branch

<!-- Explicitly state what must NOT be started on this branch and why
     (e.g. "Do not begin pareto-dashboard — it is its own branch per
     RELEASE_ARC.md and must not be conflated with this one.").
     This prevents scope creep. -->

---

## What just landed on `<!-- base-branch -->`

<!-- Commit hash(es), merged branch name, and a 3–5 line summary:
     files touched, new routes / models / UI surface, test count,
     quality gate status. Be specific — the next agent orients from this.
     Example:
       Commit `abc1234`. Migration 0006 adds sent_at, outcome_at, notes to
       Application (idempotent). Status enum expanded. PUT /api/.../status
       auto-stamps timestamps. Outcome buttons on submitted cards.
       ruff ✓  mypy ✓  pytest 22/22 ✓ -->

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

<!-- REQUIRED — do not delete. Reproduce the FULL still-open subset of the one
     Carry-forward ledger in `RELEASE_CHECKLIST.md` — every open item, not just the ones
     this closing session surfaced — so nothing falls out of attention across handoffs
     (charter W-1 "carry-forward discipline"). For each: one line + its ledger home.
     Add any NEW "track this" item this session (flaky test, drift, process friction,
     follow-on flag, deferred sub-decision) to that ledger FIRST (the single authoritative
     home — not a memory/PX pointer in place of it), then it shows up here.
       - filed → `RELEASE_CHECKLIST.md` "Carry-forward ledger" › Open (a memory slug / PX-id
         may ALSO hold detail); OR
       - unfiled → "capture in your branch" — the next agent folds it into their pre-close
         sweep, NEVER a standalone post-merge branch.
     At ~8–10 open items, flag a reduction sprint. Empty is impossible while the ledger has
     open items; if the ledger's Open subset is genuinely empty, write "None — ledger Open
     is empty." This section mirrors the ledger; the close-out sweep (AGENTS.md step 0)
     requires it. -->

---

## What this branch should build

<!-- Numbered list of concrete deliverables. Each item must:
     - name the file(s) to create or modify
     - name any existing helper(s) to reuse (function name + file:line)
     - cite the RELEASE_ARC.md section or RELEASE_CHECKLIST.md item
       that authorizes the work

     End with:
     "Scope is bounded to [exact section] in RELEASE_ARC.md.
     Do not expand beyond what is listed there." -->

---

## First move

Create branch `<!-- branch-name -->` off `<!-- base-branch -->`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

---

## Hard constraints (copy verbatim — do not shorten)

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

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified. "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean)
3. Ask user to confirm merge to `main`; execute merge after confirmation
4. Prune merged branch(es) with the user's OK, then generate the next-agent
   handoff prompt using this template
   ([docs/dev/AGENT_HANDOFF_TEMPLATE.md](AGENT_HANDOFF_TEMPLATE.md)) **as
   copyable chat text (never a file in `output/`)** and give it to the user as
   the **last act** before closing the window
