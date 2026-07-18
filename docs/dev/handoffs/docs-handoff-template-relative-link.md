<!-- provenance: schema=1 session=e64718a1-4bc8-4065-92c5-62d8212225df branch=docs/handoff-template-relative-link commit=fb7425c actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-18 -->

# Agent handoff: `docs/handoff-template-relative-link`

**Branch to create:** none — this branch is done; the next agent starts fresh per "First move" below.
**Base branch:** `main`

---

## Documents to read before any tool call (in this order)

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

**Stream:** this branch is **outside** `RELEASE_ARC.md`'s "v1.1.0 close-out —
reconciliation" numbered sequence — an ad-hoc fix triggered mid-session, same
precedent as `feat/handoff-integrity-kit` and `fix/handoff-pointer-verification`
(also both unlisted there). While consuming the `fix/compose-unawaited-reloads`
handoff pointer, this session's mandatory `verify_doc_template.py --event consumed`
check came back `BLOCKED` on a known, already-documented deviation (see "What just
landed" below); asked the user whether to accept-and-proceed or fix the root cause,
they chose fix it.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice) — unaffected by this branch's own
out-of-sequence status.
**Blocked until this stream tags:** nothing downstream is gated on this step.

- ~~`docs/v110-plan-reconciliation`~~ ✓ — step 1 of the numbered sequence
- ~~`fix/plan-approval-hook-scope`~~ ✓ — step 2 of the numbered sequence
- ~~`fix/handoff-pointer-verification`~~ ✓ — out-of-sequence, resolved the
  hand-typed-pointer-hash defect
- ~~`fix/compose-unawaited-reloads`~~ ✓ — step 3 of the numbered sequence
  (awaited 9 un-awaited Compose reload sites)
- **`docs/handoff-template-relative-link`** ← this branch, NOT numbered-sequence
  step 4
- `refactor/css-cascade-collapse` (PX-51) ← still the actual next
  numbered-sequence step — do not start it on this branch

Do not treat this handoff as authorizing `refactor/css-cascade-collapse` or any
other specific branch by default — the owner picks the next branch.

---

## What just landed on `main`

Commit `fb7425c` — merge of `fix/compose-unawaited-reloads` (step 3 of the
numbered sequence): `await` added to the 9 actually-open un-awaited
`loadComposition()` user-action reload sites in `static/app.js`, closing the
carry-forward item of the same name. 3 sites with a materially different call-path
shape were explicitly excluded and filed as their own carry-forward row (item 7
below).

**Then, this session:** consuming that handoff's pointer, the mandatory
`scripts/verify_doc_template.py --event consumed` check came back `BLOCKED`.
Traced (not assumed): the prior session had already diagnosed and documented the
exact cause inline in its own handoff (a blockquote note at
`docs/dev/handoffs/fix-compose-unawaited-reloads.md:281-293`) and filed it as an
open carry-forward item — `docs/dev/AGENT_HANDOFF_TEMPLATE.md:286`'s "Branch
close-out checklist" verbatim block contained a markdown link
(`[...](diagnosis/handoff-pointer-verification.md)`) that resolves correctly from
the template's own location (`docs/dev/`) but 404s once copied verbatim into
`docs/dev/handoffs/<slug>.md` (one directory deeper). Every closing agent since
had been hand-patching their own copy to `../diagnosis/...`, which made every
handoff's "verbatim" section deliberately diverge from the template — exactly the
`BLOCKED` result hit this session. Independently verified (diffed the normalized
verbatim bodies via `verify_doc_template`'s own `_normalize`/`_sha256`
functions, and cross-checked the doc's fingerprint against the ledger) that there
was no OTHER drift beyond this one link and the prior session's explanatory note
— not new corruption.

**Fixed on this branch:** `docs/dev/AGENT_HANDOFF_TEMPLATE.md:286` now cites the
target as a plain-text, full-repo-relative-path (`` `docs/dev/diagnosis/handoff-pointer-verification.md` ``,
no markdown-link syntax at all) — matching the precedent already used one
directory over, in `docs/dev/handoffs/README.md:23`, to cite the same file. A
plain path citation has no relative-resolution step, so it survives being copied
to any directory depth by construction, and `scripts/check_doc_links.py`'s link
check doesn't even parse it (it only matches `[text](path)`) — nothing left to
break. Also moved the corresponding carry-forward item from Open to Resolved in
`docs/dev/RELEASE_CHECKLIST.md`, and corrected that file's `#### Open` header,
which had gone stale by one (`fix/compose-unawaited-reloads` filed the item
without updating the rendered count).

`python scripts/check_doc_links.py` — clean, 0 violations, both before and after.
Full `python -m scripts.gate` run in progress at the time this handoff was
written; see the commit this handoff ships with for the actual result (the
"quality gate is unrunnable by an agent in one shot" ledger item, below, is
exactly why this can't be asserted in one line with certainty ahead of time).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward
ledger (`#### Open`); this is the required one-line-each mirror. **14 open,
still over the ~8–10 ceiling** — this branch resolved the item numbered 7 in the
prior handoff (the template relative-link) and added no new item, so the true
count moved 15 → 14 (the prior handoff's header had understated it as 14 without
the +1 `fix/compose-unawaited-reloads` had actually filed — corrected as part of
this branch's own fix, see above).

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a chronically
   broken test (64% fail rate) for 11 CI runs. The underlying bug is fixed; the
   retry-policy question itself is deliberately left open pending a real post-fix
   CI sample.
2. The quality gate is unrunnable by an agent in one shot (~13 min vs. a
   per-command wall-clock ceiling around 5–10 min) — a governance hole, worked
   around by hand (batching) repeatedly, not yet resolved by tooling.
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` —
   admin-only Settings toggle, not automatable.
4. `test_corpus_reload_preserves_scroll_position` (and sibling scroll-restore
   tests) — modes B/D root-caused and FIXED (Chip 3); mode C (the wizard rail's
   `scrollIntoView` racing a scroll read/write, ~17% under saturation) is a
   separate, unfixed hazard tracked as its own follow-on.
5. `chore/scrub-local-eval-paths` parked branch — 2 commits, unmerged, gate
   re-verification incomplete (not failed); owner decision: leave parked.
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` (~107 files) —
   user-facing surface already swept; this remainder deliberately deferred,
   opportunistic only, do not schedule.
7. 3 `loadComposition()` sites excluded from the just-landed
   `compose-unawaited-reloads` fix (`static/app.js:6549`/`:6606`/`:6932`) —
   materially different call-path shapes (non-async intermediates, mixed
   click/chained-async/browser-Back-Forward triggers); needs its own scoped
   design pass, not a mechanical `await`.
8. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; open only for the
   still-blocked `[HUMAN]` Trusted Publisher / GHCR prerequisite (gated on the
   GitHub repo rename).
9. In-app rendered citation viewer — deliberately deferred; build only if real
   friction shows up (GitHub links suffice for now).
10. Grounding/hallucination metric calibrated layers (L1/L2) — labels + scorer
    persistence fixed; the calibration itself is still owner-gated (manual
    annotation + threshold-setting).
11. Agent-coding-practices kit-adoption staged commitments — mypy `--strict`
    ratchet, gate-hardness ratchet-then-block, skills/hooks packaging
    coherence — cross-cutting deferrals kept in one tracked home, in progress.
12. 2026-07 efficiency review PX-37..PX-56 aggregate — drains via
    per-PX-coordinated individual branches per `RELEASE_ARC.md`'s "v1.1.0
    close-out — reconciliation" sequence.
13. UX round-2 remediation — Wave A (six decision-free findings) landed; the
    design-heavy remainder (state-communication unification, skills redesign,
    design-system pass) is registered as the UX Cohesion Epic, unscheduled.
14. `docs/governance/enforcement.md` (and several memory files) cite "charter
    W-1" (parallel-session working model) as an existing clause — confirmed
    again this session (`grep` of `charter.md` for a `W-1` heading: none) that
    it still does not exist, only an intro-line mention. Needs an
    owner-directed amendment ceremony to write the actual clause.

**Reduction sprint is overdue, not merely due** — the ~8–10 ceiling has been
exceeded across multiple prior handoffs. This branch (correctly, per its own
scope) neither added a tracked item nor changed that fact — it resolved one item
that was already open. Strongly consider the reduction sprint as an upcoming
branch.

---

## What this branch should build

This handoff exists solely to record `docs/handoff-template-relative-link` and
hand off cleanly — it does not mandate a deliverable itself. Per
`RELEASE_ARC.md`'s ordered sequence, the next candidate is **step 4,
`refactor/css-cascade-collapse` (PX-51)**, unless the owner prefers to run the
overdue reduction sprint first (see the note above) or names something else
entirely.

Scope is bounded to whatever the owner confirms next — do not treat this
handoff as authorizing any specific branch by default.

---

## First move

Create branch `<!-- branch-name -->` off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code.
**Do not code first.**

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
   observations` section above**; branches to prune identified. "Done" is the output
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
4. Ask user to confirm merge to `main`; execute merge after confirmation
5. Prune merged branch(es) with the user's OK. Generate the one-line
   pointer with `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
