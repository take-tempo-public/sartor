<!-- provenance: schema=1 session=43e0e87c-9df9-4209-81bc-e3ead85b2813 branch=feat/handoff-integrity-kit commit=0daf6df actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-17 -->

# feat/handoff-integrity-kit handoff — 2026-07-17

This is the **first real exercise of the handoff-integrity kit this branch itself built** —
per `docs/dev/handoff-integrity-design.md` §7, this branch's own close-out was deliberately
chosen as the kit's first live test, mirroring how spolia's `b06-freshrss` became that
project's first live test of the same design. Read
[`docs/dev/handoff-integrity-design.md`](../handoff-integrity-design.md) first if you have not
— it is the full evidence + decision record this branch executes against.

---

**Branch to create:** `<!-- pick per whatever the owner wants next -->` (branch off `main`)
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

**Stream:** Not a `RELEASE_ARC.md` stream — `feat/handoff-integrity-kit` is a
process/governance change orthogonal to the v1.1.0 version stream, matching the
`docs/handoff-carryforward-rule` and `feat/governance-extraction` precedents (both
landed as their own small streams, not ARC phases). `RELEASE_ARC.md`'s v1.1.0
sequence is untouched by this branch.
**Sequencing rule:** N/A for this branch's own scope; whatever you pick up next
resumes `RELEASE_ARC.md`'s normal sequential rule.
**Blocked until this stream tags:** nothing — this branch does not gate any ARC
phase.

- **`feat/handoff-integrity-kit`** ← this branch (governance/process, not ARC-sequenced)
- `<!-- whatever the owner picks next -->` ← the v1.1.0 reduction sprint is
  overdue (14 open carry-forward items, over the ~8–10 ceiling) and is the
  strongest candidate; `RELEASE_ARC.md` "v1.1.0 close-out — reconciliation"
  already has the ordered individual-branch plan for it.

Do not start any v1.1.0 ARC-sequenced branch believing this branch was part of
that sequence — it deliberately was not.

---

## What just landed on `main`

This branch (`feat/handoff-integrity-kit`) executes
`docs/dev/handoff-integrity-design.md` §6 in full:

- **`docs/dev/prov/SPEC.md`** (new) — provenance-stamp vocabulary, privacy
  tiers, ledger event schema. Vendored from spolia (`c:/Dev/spolia`), paths
  adjusted for sartor.
- **`scripts/verify_doc_template.py`** (new) — the generic doc/template
  validator: structural-heading + `<!-- verbatim -->`-section checks, plus
  `--event generated|consumed` ledger logging. Vendored byte-for-byte from
  spolia's **post**-`fix/doc-fingerprint-crlf` version (commit `2be210f`) —
  `fingerprint()` hashes newline-normalized text, so a Windows
  `core.autocrlf` checkout can't spuriously "change" an unchanged doc. Fully
  `mypy --strict`-clean (`scripts.*` is already strict-rostered in
  `pyproject.toml`) and ruff-clean (one `# noqa: S603` added, matching the
  existing precedent in `scripts/gate.py`).
- **`docs/dev/ledger/`** and **`docs/dev/handoffs/`** (new dirs) — each with a
  `README.md` adapted from spolia's. This handoff file is the first real file
  in `docs/dev/handoffs/`; its own `--event generated` ledger record (below)
  is the first real shard in `docs/dev/ledger/`.
- **`docs/dev/AGENT_HANDOFF_TEMPLATE.md`** — extended, not replaced (sartor's
  richer structure stays): provenance-stamp instruction block added, the four
  fixed sections (Documents to read, Binding rules, Hard constraints,
  Close-out checklist) marked `<!-- verbatim -->`, a fifth binding rule added
  ("corrupted input is a blocked gate"), close-out checklist step 4 rewritten
  to the file-based flow (write → stamp → validate `--event generated` →
  commit → give the one-line pointer, never the full content, in chat).
- **`AGENTS.md`** — close-out checklist step 4 rewritten to match, plus the
  explicit binding rule that a `blocked` result from `--event consumed` is
  the consuming session's first output, surfaced and STOPPED on.
- **`tests/test_verify_doc_template.py`** (new, 25 tests — spolia's 24 plus
  the CRLF regression test, all present) — ported to sartor's flat `tests/`
  layout (no `tests/unit/` subdir here), `_REPO_ROOT` adjusted accordingly,
  and the real-template regression test updated to assert **sartor's** four
  actual verbatim heading texts. All 25 pass.
- **`CHANGELOG.md`** — `[Unreleased]` entry, docs/process change, no
  `PROMPT_VERSION` bump (no prompt touched).
- **`docs/dev/RELEASE_CHECKLIST.md`** — the "Handoff transfer channel..."
  Open ledger item moved to Resolved (open count 15 → 14); the
  charter-amendment question is called out explicitly as a
  **[HUMAN/OWNER] residual NOT resolved by this branch**.

`python -m scripts.gate` (ruff check + ruff format --check + mypy + pytest): **GREEN.**
`ruff check .` clean, `ruff format --check .` clean, `mypy .` clean (the vendored
`scripts/verify_doc_template.py` is fully `mypy --strict`-clean, matching sartor's
existing `scripts.*` strict roster), `pytest` **2130 passed, 1 skipped** in 27m45s
(the 1 skip is the pre-existing, unrelated `interrogate`-gated docstring-coverage
test, which skips when that dev-extra isn't installed). One real defect was caught
and fixed mid-branch by this exact gate: the first draft used `../handoff-integrity-design.md`
inside `AGENT_HANDOFF_TEMPLATE.md` itself (wrong — the template and the design doc
are both directly in `docs/dev/`, no `../` needed) and used clickable
`[text](path)` markdown links for `docs/dev/AGENT_HANDOFF_TEMPLATE.md` /
`docs/dev/prov/SPEC.md` inside two `<!-- verbatim -->` sections (wrong for a
different reason — the *canonical* text those sections carry gets copied
byte-for-byte into every handoff, which always lives one directory deeper at
`docs/dev/handoffs/`, so any relative link correct for the template's own location
is wrong for every instantiated handoff, and vice versa). Both fixed by switching
to plain-code-span paths inside the verbatim sections — no relative link at all,
matching spolia's own precedent for exactly this reason. **If you are adding new
prose to a `<!-- verbatim -->` section in the future, do not use a `[text](path)`
markdown link — use a plain backtick path instead**, or it will pass review but
fail `check_doc_links.py` (or worse, silently resolve to the wrong file) as soon
as it's copied into a handoff.

**The charter-amendment question was raised, not pre-decided, and the owner
answered it on this same branch:** at merge-confirmation the owner directed
running the amendment ceremony now. `docs/governance/charter.md` gained a new
clause, **C-9** ("corrupted or fingerprint-mismatched input is a blocked
gate"), honestly cited as **documented convention, not yet a blocking hook**
per that clause's own claims-discipline (C-0) — matching design decision (iv)'s
advisory-at-launch stance. `AGENTS.md`'s binding rule and
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`'s binding rule 5 (in the file you are
reading right now) both now cite C-9 by name. **`docs/dev/decisions.md` stays
untouched, deliberately** — its own header states its scope boundary
explicitly: "Binding rules → `docs/governance/charter.md` (with the amendment
ceremony). Not logged here." A charter clause is not itself a decisions.md row.

Also resolved this branch (research only, no code): the design doc's own §2
"reported but not independently re-verified" claim — that
`docs/dev/RELEASE_CHECKLIST.md` once had a ledger note "found truncated
mid-sentence" — is **CONFIRMED**, not dropped. Direct evidence:
`git log -p -- docs/dev/RELEASE_CHECKLIST.md`, commit `60a614a`
(`docs/v110-plan-reconciliation`, 2026-07-16): the "Lane UX progress note"
really was found truncated mid-sentence during a full audit against
`docs/dev/reviews/` and actual code, and was reconciled — nothing it
described was lost, verified independently against `CHANGELOG.md`.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward
ledger (`#### Open`); this is the required one-line-each mirror. **14 open, still
over the ~8–10 ceiling** — this branch neither added nor resolved a ledger item
other than the one below (this branch's own subject, now Resolved).

1. `--reruns 2` on the `ux` CI tier is a masking policy that hid a real
   64%-broken test for 11 runs — fix landed; the reruns-policy question
   itself is deliberately left open until a real post-fix CI sample exists.
2. The quality gate is unrunnable by an agent in one shot (~13 min vs. a
   10-command shell cap) — a governance hole: an agent will rationalize a
   partial-green as "probably fine."
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` —
   admin-only 30-second Settings toggle, not automatable.
4. `test_corpus_reload_preserves_scroll_position` — a real ~10–20% flake,
   measured not fixed; deterministic-looking values point at an async scroll
   race, not random jitter.
5. `chore/scrub-local-eval-paths` parked branch — 2 commits, unmerged, gate
   re-verification incomplete (not failed).
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` (~107 files,
   agent-regenerated) — user-facing surface already swept; this remainder
   deliberately deferred.
7. Compose user-action reloads still fire `loadComposition()` un-awaited —
   only the five auto-arrival cascade fires were awaited by
   `fix/ci-first-linux-run`.
8. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; left open only for the
   still-blocked `[HUMAN]` Trusted Publisher prerequisite.
9. In-app rendered citation viewer — deliberately deferred; build only if
   real friction shows up (GitHub links suffice for now).
10. Grounding/hallucination metric calibrated layers (L1/L2) — no labeled
    real data yet; scheduled as v1.0.7 Sprint PV-2.
11. Agent-coding-practices kit-adoption staged commitments — cross-cutting
    deferrals (mypy-strict ratchet exit, gate-hardness ratchet-then-block,
    etc.) kept in one tracked home.
12. 2026-07 efficiency review PX-37..PX-56 aggregate — drains via
    per-PX-coordinated individual branches per `RELEASE_ARC.md`
    "v1.1.0 close-out — reconciliation."
13. UX round-2 remediation — Wave A (six decision-free findings) landed on
    `fix/round2-quick-wins`; the design-heavy remainder (state-communication
    unification, etc.) is still open.
14. `check-plan-approved` hook has no per-project/session scope — a
    concurrent unrelated session can false-positive block this one; this
    session hit it live (see Context above) and worked around it per-instance,
    not a fix. Needs an actual scope-the-marker-per-project fix.

**Reduction sprint is overdue, not merely due** — the ~8–10 ceiling has been
exceeded since before this branch started, and this branch (correctly, per its
own design doc) did not touch it. Strongly consider making the reduction sprint
the very next branch rather than starting new feature work.

---

## What this branch should build

This handoff does not hand off a specific mandated deliverable — the branch
that produced it (`feat/handoff-integrity-kit`) was a self-contained
process/governance change, not a step in a sequenced arc. What comes next is
the owner's call. Two well-evidenced candidates, in the ledger above and in
`RELEASE_ARC.md`:

1. **The v1.1.0 reduction sprint** — 14 open carry-forward items, over
   ceiling; `RELEASE_ARC.md` "v1.1.0 close-out — reconciliation" already has
   an ordered, individual-branch plan for burning it down.
2. **Whatever `RELEASE_ARC.md`'s normal v1.1.0 sequence names next** if the
   owner prefers to keep moving forward on the version stream instead.

Do not treat this branch as authorizing a third option. If the owner names
something else entirely, that overrides both.

---

## First move

Create branch `<!-- branch-name -->` off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.** (This branch itself needed a fresh plan
approval for exactly this reason — the `check-plan-approved` marker is wiped
on every merge, including the one that lands this branch.)

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
