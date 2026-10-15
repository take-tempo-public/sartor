<!-- provenance: schema=1 session=ddb9ad2f-5e2c-47d0-a71b-59c0776c68b0 branch=feat/confirm-before-overwriting-typed-edits commit=2be49f5 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-14 -->

# Agent handoff — Generate asks before it replaces a typed edit (`feat/confirm-before-overwriting-typed-edits`, item 170) → owner's next drawdown pick

**Branch to create:** none chosen. The owner picks the next item from `docs/dev/work/BOARD.md`
`## Open`; do not start one unprompted.
**Base branch:** `main`

> **This session closed item 170 on one branch (owner request, 2026-10-14).**
> - **The change:** `/api/generate`, `/api/generate/stream` and `/api/generate-cover-letter`
>   answer a pre-LLM `409 edits_would_be_discarded` when a *saved* typed edit would be lost,
>   unless the request carries `confirm_discard_edits: true`. The client asks with `cbConfirm`
>   ("Replace your typed edits?", Continue / Cancel) and re-sends once. Generate also runs the
>   unsaved-edit gate (`_gateEditsBeforeAction`), which was wired to Refine and Iterate only.
> - **Observed on `main` first:** all nine route arms were served as `200`, changed state, and
>   the seven with a letter spent one LLM call before the edit was dropped
>   (`docs/dev/work/items/0170-*.md` `## Updates`).
> - **A latent defect the new gate exposed, fixed at the helper by owner decision:**
>   `_readEditorText` lost the editor's line breaks whenever an ancestor tab was `display:none`.
>   `_detectEdits` then reported an edit nobody typed (the first full UX run was red on B7), and
>   `downloadResume()` posted line-break-less text (observed: 207 of 218 characters). Not caused
>   by this branch; the helper was untouched until this branch.
> - **Not reachable from the shipped UI:** cases 2 and 3 (a letter edit consumed by a new
>   letter). The client never requests a letter, and `#btnGenerateCover` is hidden once a letter
>   exists. The route arms cover all three cases; the browser tier drives cases 1 and 4.
> - **Two owner questions are open and nothing here decides them:** item 163's O5 (does the
>   frozen `carry_edits=True` path keep a typed letter edit over a new letter?) and whether a
>   cover letter should ever be regenerable from the shipped screens.

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
5. `docs/dev/architecture.md` — module map and LLM routing
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

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging
(owner's 2026-10-02 sequence on item 40).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157) · ~~`fix/console-run-lock-hardening`~~ ✓ (#158) ·
  ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (#159) · ~~`fix/python-direct-hooks-plan-gate`~~ ✓
  (#160) · ~~`fix/heredoc-escape-guard`~~ ✓ (#161) · ~~`fix/bash-tool-transport`~~ ✓ (#162) ·
  ~~`fix/test-reliability`~~ ✓ (#163) · ~~`test/assertion-strength`~~ ✓ (#164) ·
  ~~`fix/frozen-composition-staleness`~~ ✓ (#165) · ~~`fix/regenerate-persistence`~~ ✓ (#166) ·
  ~~`fix/regenerate-keeps-cover-letter`~~ ✓ (#167) · ~~`fix/recurrence-guardrails`~~ ✓ (#168) ·
  ~~`fix/run-row-letter-edit-shadow`~~ ✓ (#169): item 163 closed.
- ~~`feat/confirm-before-overwriting-typed-edits`~~ ✓ (PR #170; see the pointer's commit on
  `main`): item 170 closed.
- **Next: the owner's pick.** Open items, none started: 161 (`GET /composition` parses the
  context about eleven times per request; counted from the code, not measured, so the first
  step is a measurement); item 7 memory-consolidation apply (Deferred); item 30's C-7 probe
  branch; launcher items 145–147; the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`feat/confirm-before-overwriting-typed-edits`:

| Commit | What |
|---|---|
| `aaa1d2c` | **Dossier and instrument first** (C-10, C-7). `docs/dev/blast-radius/confirm-before-overwriting-typed-edits.md` (consumers re-derived by grep), `tests/test_confirm_overwrite_edits.py` (14 controls, 9 strict-xfail defect arms), this session's consumed-ledger file. Under `--runxfail` on `main` all 9 arms failed at `assert status == 409` (served `200`), 0 `ControlFailed`. |
| `75c1369` | **Server handshake.** `_pending_discards`, `_edits_would_be_discarded_response`, `_frozen_resume_md` in `blueprints/generation.py`; the check sits after the month block and before any LLM work on both routes; `_assemble_from_frozen_composition` takes an optional `resume_md` (one render). Seven existing drives gained `confirm_discard_edits=True`. Markers deleted from the instrument. |
| `9c46412` | **Client, the helper fix, UX tests, docs.** `runGeneration` over `_runGenerationOnce`, `runGenerateCoverLetter` over `_runGenerateCoverLetterOnce`; `_readEditorText` measures a rendered copy when the node has no layout; `tests/ux/regression/test_20261014_confirm_overwrite_edits.py` and `test_20261014_editor_text_hidden_tab.py`; additive `ui_pages/selectors.py` classes; user doc, architecture note, CHANGELOG. |
| `2be49f5` | Scoped `/wiki-self-update` (`route-surface`, `frontend-wizard`, `iteration-audit-chain`, `log.md`); item 170 closed with `verified_by`; board regenerated. |
| `f2230bd` | The correction to one item-170 sentence, and the first version of this handoff with its ledger rows (a `failed` then a `generated`). Docs only. |
| (this commit) | The PR #170 `ci_wait` exit-3 sample recorded in item 30's `## Updates`, and this handoff regenerated to carry the CI facts (another `generated` row). Docs only. |

**Verified, with the evidence:**
- **Routes:** 192 passed across the instrument and every suite that touches these routes.
- **Mutation checks, file restored and sha256 verified each time:** skipping the check on the
  stream route alone fails exactly its 4 arms; ignoring `carry_edits` in the predicate fails
  exactly the 2 carry controls; removing the case-4 gate and ignoring the 409 in `app.js` each
  fail the browser test where expected.
- **UX tier:** run 1 `1 failed, 171 passed` (B7, `PYTEST_EXIT=1`); after the helper fix,
  run 2 `173 passed, 2 xpassed in 489 s`, 0 `RERUN`.

**Gate:**
- `python -m scripts.gate --result`, run on `2be49f5`, the last commit that touched code or tests:
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-14T20:21:46-0700, HEAD 2be49f5`
- **That result is stale for the tip**, because the result binds to HEAD. Two docs-only commits
  sit on top of it (the handoff with the item-170 correction, then the item-30 CI-sample record
  and this regenerated handoff). Neither changes code or tests.
  `work_items check` and the doc checks were re-run by hand on the tip; the full gate was not.
- **What it ran:** `ruff check` and `ruff format --check` clean; `mypy` clean;
  `pytest -m "not ux" -n auto` **3396 passed, 8 skipped** (6 m 02 s; 3373 before this branch,
  the 23 new are `tests/test_confirm_overwrite_edits.py`); `pytest -m ux` **173 passed,
  2 xpassed** (11 m 02 s); `work_items check` OK (170). 0 `RERUN`, 0 `FAILED`/`ERROR`
  status lines. The 2 xpassed are the two deliberately non-strict xfails in
  `tests/ux/regression/test_20260708_busy_states_and_chip.py`, which this branch does not touch.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.
- **CI on the PR (#170), first run at head `f2230bd`:** all 8 required checks passed and
  `python -m scripts.ci_wait 170` exited **3**: one UX test, item 30's
  `test_keyboard_reorder_persists_and_reset_reverts`, failed 1 of 3 attempts (reach 9, nothing
  pending, `composeReady: True`, retry passed 3 s later). That is item 30's recorded signature
  and this branch touches no Compose reorder path. I recorded the sample in item 30's `## Updates`
  on this branch (a docs-only commit) **before** any merge, which pushed a new head and a second
  CI run. That second run's result is on the PR and is not in this frozen file.

**Wiki pass** (`docs/wiki/log.md`, 2026-10-14): scoped to this branch's diff; cite check 0
catches; my review 7 catches (run before the auditors); auditor (Sonnet 5) 1 UNSUPPORTED of 30
claims. `.last_ingest_sha` is unchanged (`3798e2d`); `wiki_freshness` OK at 38 < 75.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 22 / 10 ceiling -- OVER"**
(20 items below plus 2 open epics; this branch closed 170). The owner's drawdown direction
stands: down to 0 if possible, before alpha staging. That is well past the ~8–10
reduction-sprint threshold. Owner-decision items are marked *(owner)*.

`## Open`:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **128** *(owner)*: D1 close-out saw several python3.13 processes started 2026-09-18..25 (~0 MB), not that session's own.
- **129** *(owner)*: Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?
- **130**: Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty.
- **131**: Retire dialog cites a "Show retired" toggle Pipeline lacks; its query drops retired apps.
- **133** *(owner)*: No route, UI or script removes a user. Product decision: wanted, and when?
- **134**: Tuning smoke says ~$0.20 for TWO suite runs; Quality smoke says ~$0.35-0.40 for ONE. At most one is right.
- **135** *(owner)*: Template close-out step 1 says ruff+mypy+pytest (gate runs 6); charter:206 cites step 4 for a step-5 rule.
- **137**: Short review: are the pinned models and call settings (thinking, caching, routing) still the best performance/cost fit?
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Prompts hand bullets to the model as id="b{id}"; the model echoes the handle into prose. Letter date is ungrounded.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **146**: A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly.
- **147**: Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit.
- **161**: Each _read_* helper re-reads and re-parses the context JSON; one parse could serve them all.

`## Blocked` (4): **3**, **5**, **8**, **97**.
`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.
Plus `## Watching` (44) and `## Epics` (6) in `BOARD.md`. Items **168** and **169** are unchanged
(watching): 168 gained a datapoint, see below.

Declared, not filed. New this session, observed unless marked:
- **Cases 2 and 3 have no shipped client trigger** (read from `static/app.js`, not driven in a
  live session): `runGeneration` never sends `generate_cover_letter`, and `#btnGenerateCover` is
  hidden once a letter exists. The server floor and `runGenerateCoverLetter`'s handler protect
  direct API use and any later screen that reaches them. Whether a letter should be
  regenerable from the screens is an owner question.
- **`scripts/enforcement/blast_radius.py` says `ui_pages/selectors.py` has "14 non-test
  importers"; re-derived 2026-10-14 it is 15** (plus 51 test files). A stale count in the
  registry's own rationale. Not edited: it is the registry, and the number is prose.
- **Two UX tests hard-code the `#cbConfirm*` ids** (`test_20260612_corpus_affordance_polish.py`,
  `test_20260707_ux_w4_aesthetic.py`) instead of the new `ConfirmModal` selectors. They work;
  moving them is a refactor outside this item.
- **Refine and Iterate reaching the old hidden-tab false positive on `main` was read from the
  shared mechanism, not run there.** The new instrument observed it only through Generate.
- **The live-preview refresh (`_refreshLiveEditPreview`) from a hidden tab after the helper fix
  was not driven**; it is covered only by the existing live-preview UX tests passing in the
  full tier.
- **The wiki auditor result is not a measure of the scribes' accuracy this pass**: my review
  ran first and caught 7 (item 168's measurement should count review and auditor catches
  separately, as `docs/wiki/log.md` does). The auditor caught 1 of 30 claims. Six pages were
  checked by reading the cited passages, not by an auditor.
- **Two processes I did not start were left alone**: the `isidium` MCP server and a `spolia`
  podman-compose run. Neither is this session's.
- **This handoff's first validation FAILED** (`verbatim section does not match template`, the
  Documents-to-read section: my assembler dropped the template's blank line before its `---`).
  The ledger holds that `failed` row, then the `generated` row after the fix. The sections are
  sliced from the template by script, so this was the slice and not a retyped section.
- **`python scripts/check_docs_projection_fresh.py` reported STALE on a clean tree last
  session; not re-checked** (carried).

Carried from earlier handoffs, **not re-verified this session**:
- the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5): an owner question;
- the interrogative witness can pause the first `Edit` after a subagent hand-back (item 169's
  class); this session it paused the first `Write` after each prompt, which is the designed
  one-shot, and no new prompt shape was observed;
- `ruff` is not on the Git Bash PATH here (`python -m ruff` works); the IDE's Pyright reports
  unused-parameter hints for pytest fixtures and monkeypatch stubs, which `ruff` and `mypy` do not;
- the sibling window's gap is one sample (1.133 s; diagnosis O8), the 3 s default is a judgment;
- a trunk-time `compacted` row is no longer in `git log`; branch-time rows are (item 165);
- `plan_gate` reports a detached HEAD as `""`, so its `plan-archived` receipt stays in the
  tracked shard there (item 169);
- E1 sees a `lines N-M` reference only when a path is on the same or the preceding line, and E3
  is word-presence in the file (`scripts/wiki_cites.py` docstring);
- `ALLOWED_LINE_CITES` holds 25 line cites on 8 pages; converting one to a symbol forces the
  entry down;
- bash-run scripts edit files without the Edit|Write gates seeing them;
- a gap-fill retire, or a drag back to the same position, marks an approval stale without
  changing the résumé; approvals frozen before `fix/frozen-composition-staleness` carry no digest;
- the post-generate announcement still says "Resume and cover letter generated" when no cover
  letter was produced (`static/app.js`, `runGeneration`'s `_announce`);
- `lastCoverLetterPath` is assigned in seven places and read by none (`static/app.js`);
- a stale comment at `db/build_context.py:92`: fold it into any branch that touches that file;
- the doc-writing skill's evaluation plan has not been run (the owner's call when);
- 32 one-way wiki backlinks (WARN), as counted by an earlier `/wiki-lint`;
- `sartorEval.run()` returns no handle on its success path (`dashboard.html`);
- `docs/dev/diagnostics.md` cites code by line number, which rots on every edit;
- the derived-set test's `git ls-files` costs 1.8–5.2 s on this machine under 0.5–0.8 GB free;
- transitive wiki relevance is not modelled (`PERFORMANCE_HISTORY.md` → `scripts/perf_baseline.py`);
- `python3` resolution on hypha and the homelab is unchecked; without `python3` on PATH no hook
  starts and the gates fail open (`docs/governance/enforcement.md`);
- `tests/test_plan_approval_scoping.py` takes about 6 minutes locally: split it by `-k` class;
- pre-existing count drift, each deferred in `docs/dev/blast-radius/bash-tool-transport.md`:
  `docs/governance/enforcement.md:29-31` says "8 exist" (14 rules now); `TestBashDispatcher`'s
  docstring names four guards (there are seven); `blast_radius.py`'s `result.py` entry says "10
  non-test importers";
- item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry;
- the threaded UX `live_server` may expose route reads on Windows (inferred, not observed;
  `docs/dev/diagnosis/test-reliability.md` §Inferred);
- `tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt (run 30940947527), not investigated;
- the full local gate takes more than 25 minutes on this machine; this session's took 17 m 22 s
  (20:04 → 20:21) with a `spolia` job running alongside; run it in the background with a 35–40
  minute budget.

---

## Recurrences observed this session → guardrail authored

1. **A background task's "exit code 0" on a red run, and my mis-attribution of it** (the known
   class in the `reference-background-task-exit-code-unreliable` memory, now n=4; recognized
   because that note existed).
   - **The instance:** full `pytest -m ux` run 1 was `1 failed` (`PYTEST_EXIT=1` in the log) and
     the notification said exit 0. I called it a harness misreport and wrote that into item 170.
     The wrapper ended in `tail`, so exit 0 was the wrapper's own. Corrected in this branch's
     last commit and recorded in that memory with the verified cause.
   - **Mechanism authored: none, plainly.** The gate has `--result`, which is the mechanism for
     the gate; a general "re-raise the inner exit code" wrapper is possible and I did not build
     one. The hold was reading the log's own marker, which is discipline, not a gate. Surfaced
     here and to the user in the session.
2. **A claim written before it was checked, in a dossier** (C-12's class: a gap filled from
   plausibility). Row 19 of the blast-radius dossier said no suite stages a typed edit before a
   discarding generate, "read from the call sites", before I had read them. Caught by re-reading
   with grep, and a second over-claim in the corrected cell (`test_context_write_races.py` does
   call `save-edits`) was caught the same way.
   - **Mechanism authored: none, and none is possible deterministically** (whether a sentence
     was verified is not machine-checkable; C-0). The held mechanism is the order rule (C-10)
     plus the re-derive step; both are prose here.
3. **A silent false negative from Git Bash rewriting an argument that starts with `/`**
   (first sighting). `git grep -F "/api/generate"` returned nothing instead of an error; caught
   because the same string without the slash returned hits. Recorded in
   `reference-git-bash-leading-slash-arg-rewrite` (a memory, which is not a mechanism). **None
   authored:** a hook would have to guess whether a leading `/` is a path or a route, and C-0
   says that is not deterministic. Surfaced here.
4. **Wiring an existing gate into a new surface exposed a latent false positive** (first
   sighting as a class). **Mechanism authored:**
   `tests/ux/regression/test_20261014_editor_text_hidden_tab.py` fails closed if the editor
   text, the edit check or the download body depends on which tab is showing. The full UX tier
   is what found it; no unit test could have.
5. **The wiki scribes made reasoning errors about reachability and which branch a claim holds
   on** (the retune signal logged on three earlier passes; step 6 of the loop names this class).
   **Mechanism authored: none.** The cite check cannot see it and the auditor ran after my
   review; the held control is step 6, labeled unenforced in the command itself. Item 168 is
   the home for measuring the auditor; it needs a pass with review and auditor kept separate.
6. **Item 30's flake tripped `ci_wait` on this PR** (the third recorded failure since the
   2026-10-02 re-measurement, same test, same reach, same empty census; recognized from item
   30's own entries).
   - **The existing mechanism held:** `scripts/ci_wait.py` exit 3 made the absorbed retry
     visible (`gh pr checks` would have shown green), and I did not merge on it. I read the raw
     job log and compared it to the two earlier records before calling it the same signature.
   - **Mechanism authored: none, plainly.** The flake has been open since 2026-07-29 and its
     C-7 probe branch has not run; this branch's job was not to fix it. Recording the sample
     (item 30) is a record, not a mechanism (C-11). The cost is real and recurring: a
     re-push and a second CI run (about 7 minutes) before a merge that was otherwise ready.
     Surfaced here and to the user in the session.

---

## What this branch should build

**Nothing is queued.** The owner chooses the next drawdown item; this handoff does not pick one.
Scope for whatever is chosen is whatever the owner names, as filed in `docs/dev/work/items/`.
Do not expand beyond it.

If the owner asks what is cheapest to unblock: item 161 begins with a *measurement* (the
eleven-parse count is from the code, not measured), items 145–147 are the launch requirements,
and the *(owner)* items need a decision before any branch.

---

## First move

Run the pointer check, then `--event consumed` on this handoff, then confirm with the owner
that the PR for `feat/confirm-before-overwriting-typed-edits` has merged (this handoff's
pointer names that branch's commit on `main`). Then ask which item to take. Create that
branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to the user before
touching any code. **Do not code first.**

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
