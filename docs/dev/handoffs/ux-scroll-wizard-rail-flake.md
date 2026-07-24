<!-- provenance: schema=1 session=612beff3-ccbf-4309-a44b-57d1ce04f0b5 branch=fix/ux-scroll-wizard-rail-flake commit=9a2ac10 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-07-24 -->

# Agent handoff: after `fix/ux-scroll-wizard-rail-flake` (investigation branch, merged with NO fix)

**Branch to create:** `<!-- OWNER PICKS — see "What this branch should build" -->`
(branch off `main`). The leading candidate is a **re-observation branch for
large-corpus scalability** (ledger item 10), because the owner raised it
directly this session — but it is **owner-gated** (needs their real corpus in
the E2E clone), so **do not start it, or anything else, without the owner
naming it.**
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

**Stream:** v1.1.0 endgame. The branch that just merged was a solo-closeable
carry-forward ledger item (mode C of the scroll-position flake), **not** part
of the RELEASE_ARC numbered fork sequence (steps 11b-17).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing was gated on that branch.

- ~~`feat/context-structure-review-skill`~~ ✓ (merged, PR #66) — imported the
  `context-structure-review` skill; closed the kit-adoption arc.
- ~~`fix/ux-scroll-wizard-rail-flake`~~ ✓ **merged as an INVESTIGATION, with
  NO FIX.** Five commits, all evidence: instrument, falsification, growth
  attribution, an on-demand probe, and the ledger. Ledger item 2 stays
  **open**; ledger item 10 (large-corpus scalability) was **newly filed**.
- next branch ← **not directed. The owner picks.**

**Do not pick any fork item (RELEASE_ARC steps 11b-17) on your own
initiative, and do not resume mode C on your own initiative either** — the
mode-C dossier's own round 6 says explicitly that the next move may be "stop
guessing and capture a second wild failure," which is a spend decision, not a
technical one.

---

## What just landed on `main`

**Commits `3b29716`, `7938997`, `5bfb93d`, `06f0127`, `9a2ac10`** (branch
`fix/ux-scroll-wizard-rail-flake`). **Zero production code changed** — the one
production edit attempted (`static/style.css`, `overflow-anchor: none`) was
A/B-refuted and reverted in the same session, so it is not in the tree. Files
touched: `tests/ux/regression/test_20260708_busy_states_and_chip.py` (three new
instruments + one probe), `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md`
(O-5…O-14, F-4…F-7), `docs/dev/RELEASE_CHECKLIST.md`, and this branch's
provenance ledger file.

Gate: **ruff ✓ · ruff format ✓ (319 files) · mypy ✓ (334 files) · pytest ✓**
(non-UX `2057 passed, 1 skipped, 0 RERUN`; UX tier run separately) — see the
"Quality gate" note at the end of this section for how it was run.

**One inherited red was resolved, and you should know how:**
`test_wizard_render_firing_after_baseline_creeps_it` was committed by the
prior session *asserting the bug* (correct under C-7 "instrument first"), so
this branch was never gate-green. **F-4 then established its subject is not
mode C at all.** It is now `xfail(strict=False)` citing F-4 — the assertion
itself is **untouched**; only its status as a gate signal changed, and only
because the evidence changed. It was a permanently-red entry asserting a
non-defect. If a later round re-establishes that ordering as load-bearing,
**remove the marker rather than editing the assert.**

**What the branch actually established about mode C** (read the dossier before
touching it — this is a summary, not the record):

- **Mechanism, directly observed:** `window.scrollY` shifts by **exactly** the
  document's height growth — `dy == dh`, verified at `+69` and `+25054` in the
  same run, with **no scroll event at all**. Chromium **scroll anchoring**.
- **What grows** (measured, not assumed): `#mergeSuggestionsList` (24956px).
  `#corpusExperienceList` is 1308px and **never grows**.
- **Seven framings are dead.** Do not rebuild on any: `prefers-reduced-motion`
  (F-3), a second/late `_wizardRender()` (F-4), the max-scroll clamp (F-5),
  list-scoped `overflow-anchor: none` (F-6), and — note — **the wizard rail
  itself** (F-7). The `300 -> 369` signature the branch is *named* after is a
  `+69`/`+69` height shift, not a scroll to `#panelJD`. **The branch name and
  dossier title are historical, not descriptive.**
- **The open question:** what *selects* the ~1-in-6 runs where it fires. The
  same growth lands in the same window in 5 of 6 control runs and shifts `y`
  in only 1. A probe that forces that ordering on demand never fires it (0
  shifts in 11 armed runs), and growth *timing* was isolated singly and ruled
  out. **No fix can be honestly measured until this is closed** — at a ~1-in-6
  rate, round 4's 1/6-vs-1/5 arms were evidence of neither improvement nor harm.

**Quality gate note (relevant to ledger item 1):** the gate was run in stages
(`ruff check` / `ruff format --check` / `mypy` / `pytest` split by tier) rather
than as one `python -m scripts.gate` call, because a single call exceeds the
agent's per-command wall-clock ceiling. This is the known ledger item 1, not a
new problem — but it means "gate green" here is an *assembled* result. Re-run
it whole if you need a single-command attestation.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s
Carry-forward ledger (`#### Open`). **Rendered open count: 10** (+1 this
session: item 10 filed; item 2 updated, not closed). One line each, in ledger
order:

1. The quality gate is unrunnable by an agent in one shot (~15-25min,
   background-Bash kill risk around 5-10min) — makes it unenforceable as a
   single command. **Hit again this session** (see the gate note above).
2. `test_corpus_reload_preserves_scroll_position` mode-C follow-on — **the
   branch that just merged.** Mechanism now directly observed; **still no
   fix**; round 6 arms B/C specified and not run.
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
10. **Large-corpus scalability — NEW this session, owner-raised.** *"We must be
    able to deal with large corpuses."* First hard data point: the
    possible-duplicate-roles panel renders its entire suggestion set with no
    cap/pagination/virtualization and appears to grow **superlinearly** — 20
    seeded roles → **~25000px**. **Owner-stated provenance caveat: their
    symptoms are ~a week old and have NOT been re-tested during that week of
    release work.** First action is to **re-observe, not optimize**;
    "probably fixed by X" is not a resolution.

**The ceiling is ~8-10 open items; this ledger is now at 10 — a reduction
sprint is DUE** (charter W-1). Freely solo-closeable right now: item 9, and
item 2 only once the round-6 spend decision is made.

---

## What this branch should build

**Nothing is directed. The owner picks the next branch.** Three candidates,
with what each actually needs — presented so the owner can choose, not as a
recommendation to act on unprompted:

1. **Large-corpus scalability re-observation** (ledger item 10) — the owner
   raised this directly and it is the only item with fresh owner energy behind
   it. **Owner-gated:** it needs their real corpus in the E2E clone
   (`project-e2e-instance-location` — that evidence lives in a *separate*
   clone, not this repo's `output/`). Deliverable would be a **per-surface
   cost table** (corpus list, merge suggestions, Compose, applications) at
   real scale, *before* any optimization is designed. Start points already
   measured: `refreshMergeSuggestions()` (`static/app.js:5212`) and
   `GET /api/users/<u>/corpus/merge-suggestions`. Target sizes and acceptance
   thresholds are an **[OWNER DECISION]**.
2. **A ledger reduction sprint** (charter W-1) — the ledger is at its ceiling.
   Item 9 (`docs-site` shields.io badge fetch) is solo-closeable and would take
   it to 9.
3. **Mode C round 6** (ledger item 2) — arms B (no preceding shrink) and C
   (active `_restoreScrollY` settle loop), each tested **singly**, per the
   dossier's `## Falsification`. **Read that section first:** it says if both
   come back negative, the next move is *not* a fourth guess but capturing a
   second wild failure. That is a spend decision the owner should make, since
   this branch already spent three rounds on refuted framings.

**Scope is bounded to whichever single item the owner names.** Do not expand
beyond it, and do not combine two of the above into one branch.

---

## First move

Create the branch the owner names off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

If the owner names candidate 1 or 3, note that **both are measurement-first**:
the first commit is an instrument or a measurement table, never a fix
(charter C-7). Candidate 3 additionally inherits an existing dossier — read
`docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md` in full, including
`## Falsified`, and do not re-chase F-3 through F-7.

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
