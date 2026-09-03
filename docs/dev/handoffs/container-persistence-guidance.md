<!-- provenance: schema=1 session=22550545-0af0-4805-96e3-895c7e5723cc branch=docs/container-persistence-guidance commit=4c27edf actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-09-02 -->

# Handoff — install-DX findings filed (7 items + a correction) plus one live bug report (item 106); the item-97 decision record is still owed

> **Where this sits (2026-09-02):** This branch started as answering an owner
> question about container persistence (item 101) and grew into a live macOS
> 12.7.4 (Monterey) install walkthrough that surfaced a chain of real
> blockers — filed as items **99–105** plus a verified correction to item 3
> (commit `4c27edf`, already on this branch, not yet on `main`). This
> session added one more: item **106**, a bug the owner reported directly
> (Compose bullet-text edits not reaching preview/generate/download),
> traced to a concrete code mechanism and filed with the trace, not yet
> reproduced live. **This branch is a deviation from the prior handoff's
> prescribed next branch** (`docs/item-97-decision-record`, off `main`) —
> that work is still owed, untouched, see "What must NOT be started" below
> for why it wasn't done here and "Carried-forward observations" for its
> current status.

**Branch to create:** `docs/item-97-decision-record` (branch off `main`) —
**still the standing prescription from the prior handoff**, never executed.
The owner may want to re-prioritize against the newly filed 99–106 install/
bug items first; that call belongs to the owner, not this handoff.
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

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md` §"v1.1.0 Final
March") — unchanged since the last handoff: Epic A and Epic B are both merged;
Epics C/D/E migrate to the external factory (item 97), not sartor branch
sessions.
**Sequencing rule:** one epic at a time; the factory design precedes any
further epic.
**Blocked until this stream tags:** the 1.1.x series (`RELEASE_ARC.md`
§"Post-public").

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — retired as a vehicle after run 6.
- ~~Epic B (`epic/b-render-ats`, board 37)~~ ✓ — merged `86dee5c` (PR #128).
- ~~`docs/item-97-decision-record`~~ — **prescribed as next by the prior
  handoff, still NOT done.** This branch (`docs/container-persistence-guidance`)
  ran instead, off the owner's live install testing — not a supersession, a
  genuine deviation. Nothing has resolved item 97's owner-amendment need.
- **`docs/container-persistence-guidance`** ← this branch, this handoff.
  Not yet merged to `main` (1 commit ahead, `4c27edf`, plus this session's
  additions below).
- Epics C (38), D (39), E (40) ← still do **NOT** start as branch sessions —
  unchanged from the last handoff.

**What must NOT be started by the next session:** any epic branch; any
`.claude/workflows/n1-baseline.mjs` invocation (retired); implementing item 98
or item 97's factory (both are factory-first-test cards, not branch-session
work); editing `docs/dev/work/SCHEMA.md` (gated surface).

---

## What just landed on `main`

**Nothing new since the last handoff.** `main` is still at the Epic B merge,
`86dee5c` (PR #128). This branch's commit (`4c27edf`, items 99–105 + the item-3
correction) and this session's additions (item 106, BOARD.md regen, a recovered
orphaned ledger file, this handoff) are **not yet on `main`** — see "First move
for the closing agent" below for what still needs to happen before that's true.

---

## This session's own contribution (on top of `4c27edf`, not yet committed at handoff-generation time)

- **Item 106 filed** (`docs/dev/work/items/0106-compose-bullet-edit-not-reflected-post-freeze.md`):
  owner reported that editing a bullet's text at Compose doesn't show up in
  preview, generate-preview, or the downloaded résumé. Traced by reading code
  (not yet reproduced live) to: `_editComposeBullet` (`static/app.js:9282-9346`)
  → `PUT /api/bullets/<id>` → `update_bullet` (`blueprints/corpus/experiences.py:499-555`),
  which writes only the corpus `Bullet.text` row. Once an application is frozen,
  preview (`blueprints/templates.py:1092-1095`), generate
  (`blueprints/generation.py:837-1119`), and download all serve the frozen
  `approved_composition` snapshot verbatim and never re-read the corpus — a
  documented-as-deliberate snapshot (`corpus_to_json_resume.py:376-380`), but
  the Edit-bullet modal's own copy gives no indication of that. Related to,
  but a distinct trigger from, existing item 66 (composition_overrides autosave
  going stale) — item 66's trigger is the debounced autosave; this one doesn't
  go through the autosave/save route at all. Flagged explicitly unverified
  where reasoning outran observation (whether the same failure reproduces on a
  never-frozen application; whether re-clicking "Save and continue" fixes it).
- **BOARD.md regenerated** — Open 11 → 12 top-level (`work_items check` OK,
  106 files).
- **Recovered an orphaned ledger file**, `docs/dev/ledger/93b12557-6085-47a9-b109-2a00151b3048.jsonl`
  — NOT this session's own ledger. Discovered untracked in the working tree,
  dated 2026-08-16T18:32:49Z (a different, unrelated session's `consumed`
  receipt for the `epic-b-render-ats-close.md` handoff, at commit `86dee5c`),
  never committed by whoever created it, sitting in the working tree
  uncommitted for ~2.5 weeks across every branch switch since. Committed here
  as a recovery, explicitly labeled as such in the commit message — not
  claimed as this session's own provenance event.
- **Memory written**: `reference-compose-bullet-edit-not-refrozen.md` (item
  106's mechanism, for recall on any future Compose/frozen-composition work).
- **MEMORY.md trimmed** (~20.3KB → ~19.9KB) in response to a size-approaching-limit
  hook nudge. Only prose shortened; every existing link and `(+ ...)` cluster
  preserved — no memory file dropped or merged. Did not reach the hook's
  17.1KB target: closing the remaining gap needs either renaming memory files
  (their long slugs are most of the remaining bytes) or actually merging/
  dropping clustered entries, and the latter is exactly what
  `project-plan-approved-marker`... — correction, what the **selective memory
  consolidation** standing preference (item 7 in the memory index) requires
  presenting as a list for explicit owner approval before acting on. Left
  as-is rather than force it unilaterally; flagged to the owner in this
  session's own chat, not acted on further here.
- **Quality gate**: green, assembled from verified pieces (this environment's
  background-task kill ceiling cut a straight `python -m scripts.gate` run
  short partway through the `pytest -m ux` step — see
  `reference-background-bash-kill-ceiling` memory for the known pattern).
  Confirmed individually: `ruff check .` ✓, `ruff format --check .` ✓,
  `mypy .` ✓, `pytest -m "not ux" -n auto` — 2654 passed, 2 skipped
  (1162.70s) ✓, `pytest -m ux` — run in 4 file-list chunks after the kill
  (24 + 45 + 33 + 46 tests), **146 passed, 2 xpassed, 0 failed** (the 2
  xpassed are `test_wizard_render_smooth_scroll_creeps_explicit_baseline` /
  `test_wizard_render_firing_after_baseline_creeps_it`, item 62's
  already-tracked non-strict-xfail flake, not a new finding) ✓,
  `python -m scripts.work_items check` — OK, 106 files ✓.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerated + `work_items check`
OK this session, 106 files). **Note the board header's own count is a known
undercount/overcount split (item 82: `open_count` sums ALL items including
epic children; the other three counts sum top-level only) — the lists below
are the top-level subsets, matching the prior handoff's convention.**

**Open — 12 top-level:** **50** (C-7/C-10 hooks don't travel to other agents);
**94** (item-87 witness kills N=1 pipeline runs — pipeline itself retired, item
watches on); **96** (sprint brief model args silently default); **98** (wiki
checkpoint coverage ledger — owner: "test with it and some open ledger items
before running the epics"); **99** (install.md documents unpublished GHCR/PyPI
paths); **100** (no OS/version floor, no preflight — the macOS 12 walkthrough
that produced 99–105); **101** (container quickstart defaults to data loss,
bind-mount trap); **102** (`--setup` failure summary hides which step broke);
**103** (PDF offered in UI with no Chromium graceful-degradation); **104** (no
safe API-key entry path — shell history); **105** (corpus import: education
rows missing, parse-vs-persist not yet distinguished); **106** (NEW — Compose
bullet-edit not reaching an already-frozen preview/generate/download).

**Blocked — 6:** **3** ([HUMAN] GitHub toggles — item 99 verified its "repo
rename" half is now stale, remote is already `take-tempo-public/sartor`); **5**
(grounding-score persistence gap); **8** (Compose rewrite latitude); **93**
(Epic-C invoker session shape — mooted by the factory); **95** (resume
pre-authorization names a broken remedy — owner amendment owed with 97); **97**
(external orchestration — direction given, design done in `the-factory`; the
sartor-side formal decision record — `docs/item-97-decision-record` — is
**still the next branch, still not started**). Plus epics 37, 38, 39, 40.

**Deferred (7):** 4, 7, 24, 25, 41, 42, 43.

**Watching — 45 top-level** (see `BOARD.md`; unchanged this session). **The
reduction-sprint flag stands — at least the SIXTEENTH handoff flagging it**
(Open alone is now 12, past the 10 ceiling and past the ~8–10 W-1.4 threshold
for real). Item 84 stays watching (pipeline retired; taxonomy = design input).

**Epics — 6, two still open with no owner action taken:** Epic A's item 36
still never flipped `closed` — **at least the SIXTEENTH handoff flagging
it.** Epic B's item 37 should be checked/closed by whoever takes
`docs/item-97-decision-record` next (its PR merged this window; nobody has
gone back to flip the item).

---

## Recurrences observed this session → guardrail authored

**1. The item-97-decision-record deviation.** The prior handoff prescribed a
specific next branch; this session (and apparently the session(s) before it
that produced `4c27edf`) ran a different branch instead, in response to live
owner activity (testing the install, then reporting a bug). This is not a
new failure class — RELEASE_ARC/RELEASE_CHECKLIST drift from actual branch
sequencing is exactly what the BOARD.md work-item system and the "Where we
are in the arc" handoff section already exist to keep visible. **Guardrail:**
none newly authored this session — the existing mechanism (this section,
required by C-11's own gate on every handoff) is what surfaced the drift
here; the fix is owner action on item 97, not a new tool. Stating this
plainly rather than inventing a mechanism that doesn't address an owner
-side decision gap.

**2. An orphaned, never-committed session ledger file surviving ~2.5 weeks
across branch switches.** This is the first time this specific failure has
been *observed* in this repo (a `docs/dev/ledger/<session>.jsonl` file
created on `main`, then never committed by the session that created it,
sitting untracked through multiple later branch checkouts) — not yet a
confirmed recurrence of a named class, so C-11's obligation to author a
fails-closed mechanism does not yet bind on this single instance. Flagging
it here rather than silently normalizing it: if this happens a second time,
that IS the recurrence, and the next session should author a mechanism
then (candidate: a pre-close-sweep check that greps `docs/dev/ledger/` for
untracked files, not just checks for "this session's own"). **No mechanism
authored this session** — recovered the one instance found, did not build a
detector for future ones, because one instance is not yet a pattern.

---

## What this branch should build

Nothing further — this branch's own work (items 99–106, the recovered
ledger file, this handoff) is complete as of this document. The **next**
branch's work is either:

1. `docs/item-97-decision-record` (off `main`) — the sartor-side formal
   decision record for item 97 (external orchestration factory), per the
   prior handoff's still-unexecuted prescription. Scope: read
   `C:\Dev\the-factory\docs\design\00-sync-record-2026-08-14.md` (canonical,
   per `project-item97-design-sprint-decisions` memory) and item 97's own
   entry in `docs/dev/work/items/`; write the decision record; do not touch
   `docs/dev/work/SCHEMA.md`.
2. OR triage/fixes against the newly filed items 99–106 — several are
   install-blocking for any non-maintainer (99, 100, 101) and one is a
   live user-facing bug (106) — **if the owner reprioritizes these ahead of
   item 97.**

**This is an owner decision, not this handoff's to make.** Ask before
starting either.

Scope is bounded to whichever of the two the owner selects. Do not expand
beyond it.

---

## First move

Create branch `docs/item-97-decision-record` (or the owner-selected
alternative above) off `main`, write a plan at `~/.claude/plans/<slug>.md`,
and show it to the user before touching any code. **Do not code first.**

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
