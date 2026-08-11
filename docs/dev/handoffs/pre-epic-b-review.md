<!-- provenance: schema=1 session=c2b8b005-6cb9-4398-8dcd-1a5ddf011e86 branch=docs/pre-epic-b-review commit=a7e8eda actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-11 -->

# Handoff — pre-Epic-B robustness design pass complete; owner decision is the next move

> **This branch's own work is done.** It answered the handoff it consumed (`docs/dev/handoffs/pre-epic-b-intermediate-steps.md`)
> at a much larger scope than that document asked for, per the owner's own direction mid-session:
> not a checklist of §15.7 preconditions, but a full-lifecycle robustness design pass —
> handoff → orchestrator → subagents → gate → PR → CI — producing an evidenced friction map, a
> fully-specified proposed architecture, and explicit decision points **for the owner, not this
> branch, to resolve.** The single most important thing this handoff carries forward is: **the
> owner has not yet answered those decision points.** Nothing about Epic B, the chain envelope,
> or the proposed new architecture should be assumed resolved until they are.

**Branch to create:** none yet — the next branch depends on the owner's answer to §16.7 of
`docs/dev/epic-a-chain-design-corrections.md` (see "First move" below). Item 75's fix is the one
unconditional next branch, independent of that answer.
**Base branch:** `main`.

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

**Epic-specific reading, on top of the numbered list above** — read the sections named, not a
summary: `docs/dev/epic-a-chain-design-corrections.md` §16–§20 in full (this session's own
design pass — the friction evidence, the two tested hypotheses, the design evolution A→B→C→C+drift,
the proposed architecture, the §14.7 adversarial pass outcome, and the directive 2(a)/2(b)/3
write-ups). §16.7 is the decision list — read it before doing anything else.

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics, A→E, strictly
sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first (A–C), docs after (D),
release last (E). This branch's work is **not itself an epic** and carries no A/B/C/D/E label —
same as its predecessor, it is governance-interval work, not a march branch.
**Blocked until this stream lands on `main`:** unchanged — Epics C, D, E (board items 38/39/40)
stay `blocked` behind B regardless of this interval's outcome. What this interval gates is still
narrower: **Epic B's first code sprint (`B1`) must not start** until the owner has resolved §16.7
below — independent of whether Epic A has merged (it has: `162c1dc`, PR #117).

- ~~Epic A (`epic/a-app-core`, board 36)~~ — **confirmed merged this session**, `162c1dc`, PR
  #117. A separate `docs/post-epic-a-findings` branch (PR #121, `a7e8eda`) also merged since,
  filing items 77–80 (unrelated to this branch's scope — verified no overlap).
- ~~This handoff's predecessor~~ — the governance/design interval that first surfaced the
  owner's §12.0 directives.
- **This branch (`docs/pre-epic-b-review`)** ← the robustness design pass. Done.
- **Item 75's fix** ← unconditional next branch, own `fix/*`, independent of §16.7.
- **The design pass's own N=1 pipeline build (board item 84)** ← blocked on §16.7, not
  authorized by this handoff.
- Epic B (`epic/b-render-ats`, board 37) ← still blocked, now on a **better-informed** version of
  the same question this interval originally existed to resolve.
- Epics C, D, E (board 38/39/40) ← unchanged, still sequenced behind B.

**What must NOT be started on the next branch:** any Epic B code; any part of the proposed
pipeline (§16.4) built without the owner's explicit §16.7 authorization; the seam gate discussed
in §19 (recommended against, on this design, by the adversarial pass itself); editing
`AGENT_HANDOFF_TEMPLATE.md` (§16.5.1 — its own later, separately owner-gated decision).

---

## What just landed on `main`

Confirmed this session, not assumed from the incoming handoff's forward description (which was
written before the merge happened): `main` is at `a7e8eda`. Epic A merged as `162c1dc` (PR
#117, board item 36). A second branch, `docs/post-epic-a-findings` (PR #121), also merged since
— items 77–80, four findings from Epic A's own PR cycle (a UX-stub-coverage gap, an
unattributed billed API row, `ci_wait.py` crashing twice, and a Dependabot-staleness sequencing
cost). None overlap this branch's own scope; confirmed by reading each item's file, not assumed
from titles.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m scripts.work_items board
--write`). Reproduced from the board as regenerated at this branch's own close (85 files,
`check` OK).

**Open (4):** **9** (release/visual-assets refresh, nested under epic 39), **19** (UX-suite
flakiness epic — closed out, all 5 children resolved, unblocks item 10), **36** (Epic A itself —
now merged; the epic item's own `status` has not yet been flipped to `closed`, worth a follow-up
check), **50** (C-7/C-10 enforced by Claude Code hooks only — prose binds other agents).

**Blocked (4):** **3** ([HUMAN] GitHub toggles — repo rename, PyPI Trusted Publisher, GHCR
visibility), **5** (grounding-score persistence gap), **8** (Compose-time rewrite latitude,
evidence-gated on a PX-39 run), **84** (**new, this branch** — the N=1 pipeline build,
`blocked_on` the §16.7 decision below — this is the one item on the whole board whose resolution
is this handoff's actual point).

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — unchanged, all owner-gated or post-1.1.0, see
`BOARD.md` for one-line detail on each.

**Watching (41, up from 37 — this branch itself filed 4 of the +5 net growth: items 81–83, 85;
item 84 is `blocked`, not `watching`):** **2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56,
57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
81, 82, 83, 85** — 42 listed above by count text but the header itself now correctly reads 41;
**see item 82 below, this session's own finding, for why that arithmetic is worth re-deriving
rather than trusting either number blindly.**

- **Items 81–83, 85 are new this session**, filed alongside the design pass (see "What this
  branch built" below). **Item 84 is new and `blocked`.**
- **Item 82 (new) is a fifth instance of the "a number reads as one thing, is computed as
  another" class**, and it is the mechanism behind the incoming handoff's own unresolved
  watching-count discrepancy — `BOARD.md`'s header sums `open_count` over ALL items but
  `status_counts` (Blocked/Deferred/Watching) over top-level items only. Read the item file; it
  names the exact three epic-nested watching items (30, 34, 57) the incoming handoff could not
  fully reconcile.
- **Item 81 (new)** — `wiki_freshness.py` counts a **deleted** file as drift identically to a
  new one; the mechanical root cause behind this session's own case-9 false-drift finding
  (§17 of the design-corrections doc).
- **Item 75 is the fix-first defect and still needs its own `fix/*` branch** — unchanged from
  the incoming handoff, not touched by this branch per its own explicitly out-of-scope list.
- **The watching bucket is still the item to flag hardest.** Growth across Epic A: 16 → 22 → 25 →
  28 → 36; at the incoming handoff's writing, 37; **now 41, and this branch's own filings are
  four of that growth.** Naming this honestly rather than treating a governance-interval branch
  as exempt from the trend it keeps flagging. Still not the reduction-sprint trigger (that
  ceiling is on `open`, healthy at 4) — but a bucket that has only ever grown, across two
  consecutive governance-interval branches now, is overdue for the triage session both this
  branch and its predecessor recommended.

---

## Recurrences observed this session → guardrail authored

**Two recurrences recognized. One mechanism authored (the compaction-count notice). Two more
named and explicitly NOT built, per C-11's requirement to say so plainly rather than leave an
undeclared gap.**

1. **The compaction-ledger telemetry gap (D1/D2, §16.1.D of the design-corrections doc) — a
   RECURRENCE of "asserted-but-unverified precondition," now fixed with a mechanism, not just a
   note.** `record_compaction()`'s `session` field defaulted to `"unknown"` with no environment
   fallback, unlike the adjacent `_ledger_shard()` three lines above it — verified across all 52
   historical ledger rows, all `"unknown"`. **Guardrail authored:**
   `scripts/enforcement/adapters/claude_context_hook.py`'s `record_compaction()` now mirrors
   `_ledger_shard()`'s fallback, plus captures `agent_id`/`agent_type` when present (previously
   never captured at all, despite §14.7 already having proven they're available). 15 tests in
   `tests/test_c12_disclosure_gate.py::TestM3CompactionDisclosure`, all passing, cover both the
   RED (unfixed behavior) and GREEN (fixed behavior) shape per this repo's own standard.
2. **The self-assessed-context-limit failure (stop 3, already falsified) — recognized as a
   RECURRENCE of `feedback-dont-trust-self-context-judgment`'s own class, now with a second
   instance (this session's own compaction pattern, §16.1.B) confirming it generalizes beyond
   one incident.** **Guardrail authored:** `compaction_threshold_notice()`, wired into
   `restore_evidence()`, fires a deterministic, advisory notice once `compaction_count()` crosses
   5 within a branch/session — an external signal, not a self-assessment. Tested (4 new cases,
   passing).
3. **The `BOARD.md` header's dual-population count bug (item 82) is itself a RECURRENCE — a
   fifth instance of "a number that reads as one thing and is computed as another," the second
   inside `work_items.py` specifically.** **No mechanism authored.** Fixing `render_board()` is a
   production-code change to `scripts/work_items.py`, out of scope for this governance-interval
   branch. Filed as item 82 instead, `decision_owner = "user"`, with the concrete recommendation
   (unify the two populations, add a reconciliation test) already in the item file.
4. **The wiki-freshness deletion-as-drift bug (item 81) is a RECURRENCE of item 65's
   already-diagnosed class ("measures a proxy, not the target"), now with a third confirmed
   instance — the C-11 bar for "a class, not a first sighting."** **No mechanism authored** —
   same reasoning as #3, filed as item 81 instead.

---

## What this branch should build

<!-- This branch's own work is complete — see below for what it built. -->

**What this branch built** (facts, not proposals — see §16.6 of the design-corrections doc for
the canonical version):

1. `docs/dev/epic-a-chain-design-corrections.md` §16–§20: the full robustness design pass —
   evidence A–G, two hypotheses tested, four design shapes compared (A/B/C/C+drift), the
   proposed architecture in full (structure, staged rollout, audit trail), the §14.7 adversarial
   pass (three independent reviewers, one genuinely nuanced verdict — see below), and the
   directive 2(a)/2(b)/3 write-ups this branch owed from the incoming handoff.
2. `scripts/enforcement/adapters/claude_context_hook.py`: D1 fixed, D2 added, the
   `compaction_threshold_notice()` mechanism added — see "Recurrences" above.
3. `docs/dev/RELEASE_ARC.md`: the cadence section widened to require both close-out intervals
   AND coherence-drift checkpoints in one planning declaration, plus a sequencing norm (item 80)
   batching `main`-moving merges around a long-running epic PR.
4. Five new work items filed (81–85) and `BOARD.md` regenerated (`check` OK, 85 files).
5. `docs/wiki/log.md`: a verified-no-edit entry for the one wiki-relevant file this branch
   touched (`RELEASE_ARC.md`) — checked every page citing it; none needed an update, per
   §16 of the design-corrections doc.

**The §14.7 adversarial-pass outcome, worth restating here because it's the one place this
branch changed its own mind mid-session:** the pre-recorded read this branch inherited ("a seam
gate would have prevented none of the four stops") **did not survive intact** — one of three
independent reviewers found it materially false for stop 1 specifically (the orchestrator's own
16 `Edit`/8 `Write` calls are exactly what such a guard blocks, mechanically, independent of
whether anyone read the rule). The other two reviewers found the guard would break the single
most common workflow in this repo as specified, and risks displacing the proven Sonnet-refuter
check with false confidence when a run is already compromised. **Net recommendation: do not
build the gate — the proposed architecture (§16.4) makes the question moot by construction
instead**, since no persistent orchestrator exists in that design to degrade the way stop 1's
did. Read §19 in full before citing this outcome anywhere else; it is more nuanced than either
"prevented nothing" or "should be built" and deserves to be cited precisely.

---

## First move

1. If this handoff arrived via a pointer, run
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/pre-epic-b-review.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A
   `blocked` result is your **first output** — STOP (charter C-9).
2. Read `docs/dev/epic-a-chain-design-corrections.md` §16.7 — the three decision points — in
   full, not this handoff's summary of it.
3. **Put §16.7's decisions to the owner before doing anything else that depends on them.** Do
   not infer an answer, do not start building the N=1 pipeline (item 84), and do not assume
   silence means either "proceed" or "abandon" — per this whole document's own recurring rule,
   silence on a decision this consequential is a stop, not a licence.
4. **Independent of §16.7's answer:** item 75's fix is unconditionally the next piece of
   concrete work, and can start on its own `fix/*` branch without waiting on the owner's
   architecture decision — its own diagnosis dossier, C-7 evidence (a failing test demonstrating
   a retired role reaching the A3 prompt, written before the fix), per the incoming handoff's
   own filing of it (§ "What this branch should build" #5, `docs/dev/handoffs/pre-epic-b-intermediate-steps.md`).

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

**6. Enumerate consumers before changing a contract (charter C-10).** Before
implementing any change to a **schema, a shared contract, or a widely-consumed
helper**, enumerate its consumers **grep-complete** — the whole tree, and every
name the thing goes by (symbol, string form, re-export, raw-SQL column, template
selector) — and **decide-and-document each site before the first edit.**
- **The ordering is the mechanism.** An enumeration written afterwards is a
  description of what you did. Written first, it is the thing that tells you the
  change is bigger than you thought.
- **A site you skip deliberately gets a written reason** under `## Deferred`. The
  same site skipped silently is a defect the next person finds.
- **Treat any hand-maintained consumer list as stale until you re-derive it** — it
  rots in *both* directions, naming sites already fixed and omitting sites that
  are not.
- The `require-consumer-enumeration` hook blocks edits to a gated surface (registry:
  `scripts/enforcement/blast_radius.py`) until
  `docs/dev/blast-radius/<branch-slug>.md` has a `## Consumers` section naming that
  surface. There is no escape hatch. That dossier's directory and `tests/**` stay
  writable, so the way through is always open: **write down who consumes it.**

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
   `docs/dev/prov/SPEC.md` §5 step 3); **wiki-relevance check** — if this branch's
   own diff touches any path `scripts/wiki_relevance.py` (`is_wiki_relevant()`)
   classifies as wiki-relevant, run a scoped `/wiki-self-update` against just this
   branch's own diff and commit the wiki edit now, before opening the PR (same
   "committed before merge" discipline as memory/CHANGELOG, never a follow-up PR);
   if the touched file needed no page edit, say so explicitly rather than silently
   skipping the check; **any dev server or
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
   the user the URL) → **wait for the required checks with
   `python -m scripts.ci_wait <n>`** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **`scripts/ci_wait.py` is the single definition of "the PR is green" — never
   hand-roll a watcher, a poll loop, or a `gh pr checks … | jq` one-liner.** It
   exits **0** only when every required check passed *and* no test needed a
   retry; **3 = green-after-retries** (charter C-7 rule 3 — stop and look, do
   not merge on it reflexively), **1** a failing required check plus its log
   tail, **8** the deadline expiring, **2** a wrapper error. Two hand-rolled
   30-minute watches once ran to completion emitting *nothing* while a required
   check was already red — that silence is the failure this replaces.
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
