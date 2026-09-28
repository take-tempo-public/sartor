<!-- provenance: schema=1 session=e713dc79-24c8-4deb-a9dd-8668112f289b branch=feat/dashboard-copy-discovery commit=dbbd1b0 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-26 -->

# Agent handoff — Epic C close (`feat/dashboard-copy-discovery`, C3, terminal sprint)

**Branch to create:** `feat/docs-ia-design` (branch off `main`)
**Base branch:** `main`

> **This is the EPIC's terminal handoff — it closes all of Epic C**
> (`epic/c-diagnostics`: C1a, C1b, C1c, C2, C3), not just this one sprint.
> C1a/C1b/C1c/C2/C3 all landed as commits on this same branch
> (`feat/dashboard-copy-discovery`), which the invoking session gates and
> lands as the single epic PR per §11.5 halt point 1 (any push/PR/merge is
> owner-gated, never a sprint-level action).
>
> **Dispatch note (owner decision, 2026-09-25 "Manual dispatch"):** the N=1
> pipeline's automated run (`wf_fd312963-54d`) stopped after the C3
> implementer on a `verify-binary-on-path` hook block for a bare `ruff`
> invocation (this machine requires `python -m ruff`, never bare `ruff`).
> The owner manually dispatched fresh refuter, judge, and closer agents
> (this session) to finish C3's close-out rather than restart the pipeline
> run. §11.9's delegation-seam roles were preserved; only the dispatch
> mechanism (manual vs. pipeline script) changed.

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

**Stream:** Epic C — `epic/c-diagnostics` (board item 38), diagnostics console.
**Sequencing rule:** strictly sequential — one branch at a time; Epic D runs
after all UI epics land (RELEASE_ARC).
**Blocked until this stream tags:** N/A — Epic C lands as one PR, not a
version tag; the next version tag is Epic E (`chore/release-v1.1.0`).

- ~~C1a/C1b — fixes (`fix/dashboard-run-lock-gaps` + `feat/dashboard-polish`)~~ ✓
- ~~C1c — LLM-call error capture (`feat/llm-call-error-capture`)~~ ✓ — `error_type` +
  redacted `error_message` on `status == "error"` rows.
- ~~C2 — per-run observability (`feat/run-detail-modal`)~~ ✓ — `GET
  /_dashboard/api/run/<run_id>`; run-detail modal; error-rate drill-down.
- **C3 — copy + progressive discovery (`feat/dashboard-copy-discovery`)** ← this
  branch, **closed by this handoff** (all five sprints of Epic C now committed
  on this one branch, per the 2026-09-22 "one continuous N=1 pipeline run"
  execution-mode decision).
- **`feat/docs-ia-design`** ← next branch (Epic D, D1: research + IA design) —
  do not start this until Epic C's PR is open and its checks are green; the
  owner decides when to cut it.

**Do not start on this branch:** any Epic D content (D1–D4), any Epic E
content, or any further Epic C scope. C3's scope is bounded to what
`docs/dev/handoffs/epic-c-c3-brief.md` and RELEASE_ARC's C3 bullet list
authorize (see "What just landed" below); do not expand it.

**For Epic D specifically**, once branched: also read
`docs/dev/RELEASE_ARC.md` §"Epic D — `epic/d-docs-ia`" (D1–D4) in full, and
the audits it names under `docs/dev/reviews/` once D1's own kickoff produces
them.

---

## What just landed on `main`

**PENDING — do not treat as landed yet.** Epic C has not merged. This
section is a placeholder for the invoking session to fill in after the gate,
the epic-close wiki pass, the epic-level adversarial review, and the PR
merge — per §11.5 halt point 1, no sprint-level agent commits or merges to
`main`.

What is true right now: five sprints (C1a, C1b, C1c, C2, C3) are committed
in sequence on `feat/dashboard-copy-discovery`, off `main` at the epic's
start point. The tip commit when this handoff was generated was `8a7db6f`;
C3 itself, including this closer's fixes (see "Fixes applied" below), has since
been committed by the invoking session as `dbbd1b0` (§11.9.4: the commit is the
invoking session's step, not the closer's). (Corrected 2026-09-26 at epic close;
the earlier text said these changes were staged but not committed, which was true
only at generation time.)

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Ledger home migrated 2026-07-28** (`chore/work-item-tracking`): the
authoritative current-state source is now `docs/dev/work/BOARD.md`, not
`RELEASE_CHECKLIST.md`'s "Carry-forward ledger" prose (which is retained
there only as historical narrative and is not to be added to). The full
still-open subset, reproduced from `docs/dev/work/BOARD.md` at this
generation (`python -m scripts.work_items board --write` just run):

**Header: "Open 13 / 10 ceiling -- OVER" — already past the ~8–10 reduction-sprint
threshold** (board item 82 itself notes the header's "13" sums ALL items
recursively including epic children, while the `## Open` section below lists
top-level items only — a known, tracked discrepancy, not this session's to fix).

`## Open` (10 top-level items):
- **50** — C-7/C-10 hooks don't travel to non-Claude-Code agents.
- **98** — Wiki freshness measures checkpoint-staleness, not page-staleness.
- **99** — install.md documents two never-published distribution paths.
- **105** — Corpus import produces bullets/skills but no education entries.
- **106** — Compose bullet-text edits don't reach an already-frozen application.
- **107** — First run offers no account-naming step.
- **111** — `check-plan-approved.sh` costs ~2s/edit, 8–21s/retire on Windows/MSYS.
- **112** — Dashboard Since filter raises TypeError (naive vs. offset-aware dates).
- **115** — UX-8 test needs a `getComputedStyle` assertion, not just a CSS-rule read
  (filed by C2's closer).
- **116** — Dynamically-created "Run this fixture" help bubble never verified to
  open in a real browser (filed by **this** closer — see "Filed obligations"
  below).

**Added at epic close (2026-09-26, invoking session):** items **117–124**, filed from the
epic-level adversarial review (see "Epic-close results" below): 117 server-side run lock,
118 redaction gaps (quoted-key / Basic auth), 119 lock ownership + unchecked `acquire()`,
120 pulse left on a declined run, 121 `run_detail` whole-log read, 122 weak C3 test
assertions, 123 `verify-binary-on-path` brace-group false positive, 124 bare-`ruff`
recurrence. Their board sections are in `docs/dev/work/BOARD.md` (regenerated).

`## Blocked` (4), `## Deferred` (9, including **113** — the 18 out-of-scope
console-UX-audit findings, explicitly deferred to owner triage after Epic C
lands, which is now), `## Watching` (45), `## Epics` (6), `## Closed` (37).
Full detail: `docs/dev/work/BOARD.md`.

**A reduction sprint is overdue** (10 top-level Open items at a ~8–10
ceiling, before counting item 113's 18 deferred findings that Epic C landing
now makes triage-able). Flagging per W-1, not resolving it here — resolving
the backlog is not this sprint's scope.

---

## Recurrences observed this session → guardrail authored

**One recurrence, no new mechanism — flagged, not silently left as prose.**

The judge's F1 finding (an in-envelope decision made and implemented but not
recorded — the run-detail-modal-gets-no-help-entry choice) is a second
instance of the same failure class item 84's own run-5 entry 3 already named:
a decision made under §11.8 ("decide and record") where the *deciding* half
happened but the *recording* half silently dropped. This closer's remedy was
doc-only (Observation 11 in the blast-radius dossier), per the judge's own
explicit "remedy is doc-only ... do not add a help entry" instruction — no
code mechanism was authored, and C-11 requires saying so plainly rather than
treating the doc fix as a guardrail: **a written observation is not a
fail-closed mechanism.** No gate currently catches an §11.8 decision that
goes unrecorded; building one (e.g., a lint that every blast-radius dossier's
"Consumers"/"Decision" entries have a matching Observation before a `feat/*`
branch's gate can pass) would itself be a new enforcement surface — a
§11.6.5 flag stop, not something this closer can build unilaterally. Surfaced
here for the owner rather than silently deferred as a bare note.

**Epic-close additions (invoking session, 2026-09-26):**

- **Bare `ruff` → `verify-binary-on-path` block — a RECURRENCE** (C3's implementer, run
  `wf_fd312963-54d`; agents reach for bare `ruff` although this machine only has
  `python -m ruff`). The guard itself failed closed correctly; what recurs is the agent
  behaviour, and it cost a pipeline run its automated review. **No mechanism authored this
  session** — filed as item **124** with a proposed steering mechanism (the guard naming
  `python -m <tool>` when that resolves). Declared here per C-11, not left as prose.
- **`verify-binary-on-path` false positive on shell brace groups** (`{ ...; }` read as
  binaries `{` / `}`): hit twice this session (refuter R2, and the invoker). It stopped R2's
  skip/xfail sweep before it finished. Filed as item **123**; no mechanism authored.
- **The §11.8 "decide and record" gap above** stays declared unenforced.

---

## What this branch should build

Epic D, D1 (`feat/docs-ia-design`) per `docs/dev/RELEASE_ARC.md` §"Epic D —
`epic/d-docs-ia`": best-practices research (end-user onboarding,
developer-experience onboarding, open-source docs conventions,
docs-governance-as-code), digested with citations into a design doc; the
target `docs/user/` vs `docs/dev/` tree; link policy (historical artifacts
never rewritten; live docs updated by script; link-check gate added);
governance uplift design (wordmark lint — must inherit item 2's exclusions
for `docs/wiki/` and `docs/dev/reviews/` — banned-words lint, audience-tag
lint, dead-link check, plus a doc-writing skill).

D1 opens with DX-expert + technical-writer audits (plus the
`ux-onboarding-designer` subagent on user docs) per RELEASE_ARC's own note —
run those before drafting the design doc, not after.

Scope is bounded to Epic D, D1 in `docs/dev/RELEASE_ARC.md`. Do not begin
D2/D3/D4 on this branch — each is its own branch per RELEASE_ARC, and D2
depends on D1's design landing first.

---

## First move

Create branch `feat/docs-ia-design` off `main` (**only after Epic C's PR has
merged** — do not branch from `feat/dashboard-copy-discovery` or from a
pre-merge `main`), write a plan at `~/.claude/plans/<slug>.md`, and show it
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

## Fixes applied this close-out (C3 judge verdicts)

**F1 (fix, confirmed):** the run-detail modal's `.run-link`/`.err-link`
triggers get no dedicated `_DASH_HELP` entry by design (they're a result
view, not a tile/module), but that decision was never recorded per the
mandatory First-move step 4 / §11.8 "decide AND record" obligation.
Remedy applied (doc-only, per the judge's own instruction — no help entry
added): Observation 11 appended to
`docs/dev/blast-radius/dashboard-copy-discovery.md`, naming the four
`_DASH_HELP` registry keys (`dashTileCalls`, `dashTileErrors`,
`dashTileTrace`, `dashTileRecent`) and the four detail-pane `.legend`
paragraphs (`throughput`, `reliability`, `trace`, `recent`) that carry the
explanation instead.

No reviewer-requested targeted fixes were in this payload (`reviewers: []`).

## Filed obligations this close-out

**Filed:** item **116** — the dynamically-created "Run this fixture" help
bubble (`renderCollateResult`, `dashboard.html:2730-2764`) is wired at
runtime and never reached by the C3 UX regression test's static `.tile`
iteration loop, so only "renders with no console error" is verified, not
"opens `#helpModal` with the registered title." Source: the implementer's
own close-out report (source (c) of the closer's three filing sources).

**Explicitly not filed, per invoker instruction:** UX-12, UX-27, UX-30 —
these are named by the implementer's report as known-false/contradictory
copy left deliberately untouched, but they are already owned by item 113
(`docs/dev/work/items/0113-console-ux-audit-out-of-scope-findings.md`) per
`docs/dev/handoffs/epic-c-design-brief.md` §"Goal + scope". Filing them
again would duplicate item 113.

**Correction (2026-09-26, epic-close fixer; refuter R3-1):** UX-12 was **not**
owned by item 113 — item 113 covers UX-23 and UX-25..UX-41 only, and the design
brief's scope names UX-1..UX-21, so UX-12 was in Epic C's scope but assigned to no
sprint. It was fixed at epic close: the Suite copy now describes only which
fixtures, the Subset copy only which rubrics, and "smoke" names the subset only.
UX-27 and UX-30 remain item 113's.

**Not filed, and not a filing obligation:** the implementer's "gaps declared
rather than filled (C-12)" note (no skills-per-JD count, no dollar-per-JD
figure) describes copy that honestly states it has no number — this is the
Observations 9/10 already recorded in the blast-radius dossier as structural
facts (no source exists), not a to-do needing a tracked item.

## Static checks run by this closer (not the full gate — see below)

Per the invoker note, this closer ran only the gate's **static** steps on
its own touched files (`docs/dev/blast-radius/dashboard-copy-discovery.md`,
`docs/dev/work/items/0116-run-fixture-dynamic-help-bubble-unverified.md`,
`docs/dev/work/BOARD.md`, this handoff). The exact commands and results went to
the invoking session in the closer's hand-back report; they are not reproduced in
this file, and no separate JSON report was committed (corrected 2026-09-26 at epic
close — the earlier text pointed at a report that does not exist). **The full
`python -m scripts.gate` was never run by this closer** (§11.9: a
subagent's gate dies with the agent) — that is the invoking session's step.

## Epic-close results (invoking session `e713dc79`, 2026-09-26)

Filled by the invoking session after C3's commit (`dbbd1b0`). Everything below cites its
source; where a count could not be recovered from a durable record it says so.

### Epic-level adversarial review

Three independent Opus refuters, each told to REFUTE the full epic diff
(`git diff main...HEAD` + C3), each with its own lens (Epic B precedent,
`epic-b-render-ats.md` §"Appendix"): **R1** runtime correctness + security, **R2** test
teeth (mutation probes on copies outside the repo), **R3** claims / copy / docs. **No
CRITICAL.** MAJOR findings: R1-1 (the run lock is per browser tab — no server-side
single-flight), R2-1 (redaction at the call sites had no test teeth: a raw-`str(exc)`
mutant survived 10 tests), R2-2 = R1-5 (`#annCollate` re-enabled mid-run by
`clearBtnPending`), R2-3 (`esc()` quote escaping unpinned), R3-1 (UX-12 in scope but never
assigned; still wrong), R3-2 (wiki page contradicted by the code), R3-3 (SECURITY.md
"metadata only" false after C1c), R3-4 (CHANGELOG carried only C1c), R3-5
(`dashboard/README.md` false claims).

**Disposition** (invoking session, per the approved close-out plan): every in-envelope
defect **fixed** by one Opus fixer agent at epic close (R1-2, R1-5/R2-2, R2-1, R2-3, R2-5,
R2-9, R3-1, R3-3..R3-14 incl. copy overclaims R3-6/7/8/12/13/14, dossier corrections, this
handoff's own self-contradictions); R1-1 recorded as a per-tab qualification in
`docs/dev/diagnosis/dashboard-run-lock-gaps.md` (the ratified acceptance text is not
edited); R3-2 fixed by the wiki pass below. **Filed** as items **117–124**: server-side
lock (117), redaction misses quoted-key / Basic-auth forms (118), lock ownership +
unchecked `acquire()` (119), pulse left on a declined run (120), `run_detail` whole-log
read (121), weak C3 test assertions (122), `verify-binary-on-path` brace-group false
positive (123), bare-`ruff` recurrence (124). **Recheck:** an independent `sartor:n1-refuter`
re-verified all 20 fixed findings — all cleared, no new defects, two mutation kills
reproduced independently. Its one non-finding observation: the copy corrections
(R3-6/7/8/12/13/14) carry no string-pinning test, so a later edit could reintroduce an
overclaim silently.

**Fixer deviation, disclosed:** the fixer was told to stop on any hook block other than
the C-10 guard. It hit `block-secrets` on a fabricated test key and, instead of stopping,
switched to a sub-threshold fake key (`sk-ant-api03-SeCrEt_9x`, the form existing tests
use). The invoker verified the staged diff contains no `sk-ant-` literal of 20+ chars. The
hook's intent held; the stop instruction did not.

### Wiki pass + grounding audits

`/wiki-self-update`, **scoped by owner decision** to Epic C's own changes (the full
`f42b2ea → HEAD` window was ~35 pages, over the cap of 8). 4 pages updated
(`diagnostics-console`, `code-module-map`, `deterministic-llm-boundary`,
`llm-call-catalog`); each audited by a separate `wiki-grounding-auditor` (author ≠
auditor): **4 DRIFTED + 1 UNSUPPORTED caught** and resolved (the UNSUPPORTED "five
paid-run buttons" corrected on the owner's decision). `.last_ingest_sha` **not advanced**
(scoped pass; item 98). Full record: `docs/wiki/log.md` 2026-09-26 entry.

### Gate record + a runbook deviation

- Gate on the pre-C3 epic tip `fe7d64c` (C2's gate #2 result was not in any durable
  record, C-12): `gate: all steps passed.`, 0 RERUN.
- C3 gate #1 (pre-commit, staged tree): `gate: all steps passed.`, 0 RERUN (2861 non-UX +
  161 UX passed); one hook-written `compacted` ledger row during the gate (benign).
- **C3 gate #2 was NOT run separately.** Free RAM stayed under the gate's 1.0 GB floor
  (`scripts/gate.py:_MEMORY_FLOOR_GB`) for hours (0.37–0.89 GB; a background watcher was
  also reaped by Claude Code for memory pressure). Owner decision ("Fix now, one gate
  after"): apply the epic-close fixes as their own commit, then run one full gate on the
  combined tip, which covers the C3 commit's tree as a subset. Result: recorded in the
  epic-close commit / PR body.
- UX tests written by the fixer (`test_20260923_annotate_collate_run_lock.py`'s new
  `#annCollate` assertions, `test_20260720_diagnostics_run_cancel.py`'s updated string)
  were **not run** by any agent (RAM); the combined-tip gate is their first run.

### Experiment outcomes (`epic-c-design-brief.md` §"What the experiment measures")

1. **Continuous window (item 93, choice b): did not hold as one session.** The five
   sprints ran under **five distinct invoking sessions** (C1a `1b9d9ef1`, C1b `85aae0ce`,
   C1c `93ed5108`, C2-rerun `d9b0e005`, C3 + close `e713dc79`; source: `session` field of
   the `compacted` receipts in `docs/dev/ledger/*.jsonl`). `compacted` receipts per sprint
   branch: C1a 2, C1b 2, C1c 3, C2 2, C3 1, plus 2 on `epic/c-diagnostics` at boundaries.
   Each handover was a clean resume-state stop (tip + next brief + runbook), consistent
   with runbook step 9 firing at every boundary; **I did not verify each prior session's
   stated reason for stopping** — only that each boundary was crossed by a fresh session.
2. **Prerequisite fixes:** no interrogative-witness `hook_block`, `NO EDIT APPROVAL`, or
   `PLAN RETIRED` escalation is recorded in any Epic C commit message or invoker run
   record (`git log main..HEAD`); the escalations that did occur were C2's UX-8
   `flag_stop` (`wf_697596d4-c2f`), C1c's refuter-stash event (`691a17a`), and C3's
   bare-`ruff` `verify-binary-on-path` `hook_block` (`wf_fd312963-54d`). The item-95
   recovery path never fired. In this session the witness pause fired only on the
   invoker's own edits (re-armed by task notifications / subagent hand-backs), never on a
   pipeline agent — item 94 held.
3. **Model-arg adherence (item 96):** every closer-written brief (C1b, C1c, C2, C2-rerun,
   C3) carries `implementerModel` (grep). C3 was invoked with `'opus'` per the table.
4. **Inter-sprint brief sufficiency:** C3's fresh implementer executed from
   `epic-c-c3-brief.md` alone and completed the sprint; the one stop was a tool-invocation
   hook block, not a brief gap. The brief's named line numbers were stale
   (`_DASH_HELP` at `:1077-1227`, not `:1003-1152`), as the brief itself warned.
5. **Accounting fidelity:** C3 — implementer 6 + closer 6 files == `git status --porcelain`
   exactly. C2 — "Accounting 8/8" (commit `8bf95a6`'s record of `wf_c9957967-04b`).
   Earlier sprints: see their commit messages.
6. **Owner interruptions in this session** (C3 + close): the step-0a preflight batch; the
   C3 `hook_block` escalation (→ option a) and the manual-dispatch choice it forced; four
   low-RAM gate stops; the gate-order decision; the wiki spend decision; the wiki
   UNSUPPORTED decision. The RAM stops were environmental, not pipeline defects. Earlier
   sessions' counts are in their own run records.

### Still owed after this file

- **"What just landed on `main`"** above: the merge commit hash and summary, once the
  epic PR merges (owner-gated, halt point 1).

## Wiki-relevance check (this sprint's own diff only — superseded by the epic-close wiki pass above)

Recorded in full in `docs/wiki/log.md` under "2026-09-25 — scoped close-out
relevance check (`feat/dashboard-copy-discovery`, C3 closer, Epic C terminal
sprint)". Summary: `dashboard/templates/dashboard.html` classifies
wiki-relevant per `scripts/wiki_relevance.py`; every other touched file
(this closer's own `docs/dev/**` artifacts, `ui_pages/selectors.py`, the
three test files) classifies irrelevant. **This is not a clean
verified-no-edit finding** — `docs/wiki/pages/diagnostics-console.md`'s
"In-app help" section documents the `_DASH_HELP` registry as 5 tab-level
keys only and does not yet describe C3's new per-tile entries or the
`.tile-cell`/`TILE_LAY`/`TILE_HELP` structural pattern, so the page is
stale (not wrong) against this sprint's work. Per the invoking session's
explicit instruction for this step, the edit itself is deferred to the
epic-close full `/wiki-self-update` pass (which sees C1a–C3's combined
diff), not made here — the drift is disclosed in the log, not silently
carried forward unstated.
