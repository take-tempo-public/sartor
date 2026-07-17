# Agent handoff prompt template

> **Purpose:** enforces a consistent structure for the handoff FILE the
> closing agent writes at end of session, committed at
> `docs/dev/handoffs/<branch-slug>.md` (never chat-pasted text — see the
> transfer-by-reference note below). Fill in every `<!-- ... -->`
> placeholder. Do not delete any section. The fixed sections (Documents to
> read, Binding rules, Hard constraints, Close-out checklist) — each
> opening with a `<!-- verbatim -->` marker below — are copied verbatim —
> do not shorten or paraphrase them. `scripts/verify_doc_template.py`
> checks both things mechanically: every section below is present in
> order, and every `<!-- verbatim -->` section matches this file
> byte-for-byte.
>
> **Transfer by reference, not by value.** The instantiated file is a
> durable, frozen artifact, committed to git. The corruption this
> pipeline fixes was never "the user reads the handoff in chat" — it was
> a human drag-selecting rendered terminal text and pasting it into a
> *different* session as that session's literal instruction (a
> clipboard/terminal-grid copy silently drops mid-line content in
> transit; see
> [`handoff-integrity-design.md`](handoff-integrity-design.md) for
> the confirmed corruption evidence). So: the closing agent may show the
> file's content in chat for the user to read and approve — that display
> is not the lossy hop. What crosses INTO the next session as its
> operative instruction is a separate, single pointer line (path + branch
> + short commit hash) — never a drag-select of the printed content. See
> [`prov/SPEC.md`](prov/SPEC.md) and
> [`handoffs/README.md`](handoffs/README.md) for the stamp and the
> validator.
>
> **Companion:** AGENTS.md §"Branch close-out checklist" requires this
> template be used for every handoff. RELEASE_ARC.md is the authoritative
> source for the arc progress table.

---

<!-- provenance: schema=1 session=<SESSION> branch=<BRANCH> commit=<COMMIT> actor=<ACTOR> agent=<AGENT> generated_at=<DATE> -->

The line above, with its six bracketed tokens filled in (see
[`prov/SPEC.md`](prov/SPEC.md) §1 for what each means), is **line 1 of the
handoff file you write** — above that file's own `#` title, not above
this template's. Everything from here up to this point (this template's
own title and purpose note) is instructions; it is not part of the
output.

---

**Branch to create:** `<!-- branch-name -->` (branch off `<!-- base-branch -->`)
**Base branch:** `<!-- base-branch (usually main) -->`

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

**5. Corrupted input is a blocked gate.** Damaged, truncated, or
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
   observations` section above**; branches to prune identified. "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean)
3. Ask user to confirm merge to `main`; execute merge after confirmation
4. Prune merged branch(es) with the user's OK, then write the next-agent
   handoff at `docs/dev/handoffs/<branch-slug>.md` from this template
   (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`),
   stamped per `docs/dev/prov/SPEC.md` §1, then validate it:
   `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>`. A
   `failed` result is authoring corruption in the handoff itself — fix the
   file, don't silence the check. Commit the handoff file.
5. Give the user the one-line pointer to that file — path + branch + short
   commit hash — **as copyable chat text**, as the **last act** before
   closing the window. Never paste the handoff file's content into chat;
   that reintroduces the corruption channel this pipeline exists to remove.
