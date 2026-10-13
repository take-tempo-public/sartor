
<!-- provenance: schema=1 session=321beaa0-cc3a-41bc-ac57-3c23c2a6b7da branch=fix/regenerate-keeps-cover-letter commit=3b84210 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-12 -->

# Agent handoff — a résumé regenerate blanked the cover letter (`fix/regenerate-keeps-cover-letter`, item 162) → next drawdown branch (owner's pick)

**Branch to create:** none directed by this session. The owner picks the next drawdown item;
see "What this branch should build".
**Base branch:** `main`

> **This session closed item 162 and filed 163.**
> - **The defect:** the client never sends `generate_cover_letter`, so every regenerate after a
>   detached cover letter produced none, and `save_iteration_context` overwrote
>   `last_generated_cover_letter` with `""` and popped the typed letter edit. In the wizard the
>   editor was empty, "+ Generate cover letter" replaced Download, the styled preview showed the
>   placeholder, and the iteration interview and the next cover letter had no draft. The DB row
>   kept the letter, so the wizard and the saved application disagreed.
> - **The instrument first** (`2097a40`, `41cac42`, `6e3d27e`): ten HTTP arms and a browser arm.
>   On `main` with `--runxfail` each failed at the defect assertion with its controls held.
>   The user effect item 162 had only inferred is now observed (diagnosis O1-O11).
> - **The fix, per owner decisions (2026-10-12):**
>   - D1: the rule lives in `hardening.resolve_cover_letter_after_generate`, which
>     `save_iteration_context` applies and both routes read;
>   - D2: a typed letter edit survives a résumé-only regenerate;
>   - D3: the browser arm ran before the fix;
>   - D4: decision 4's discard (`fix/frozen-composition-staleness`) is of the résumé edit only.
>     The C-10 enumeration found that conflict before the first edit.

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

- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157): items 123/124/136/148–151 closed, 153 filed.
- ~~`fix/console-run-lock-hardening`~~ ✓ (#158): items 112/117–121 closed, 154 filed.
- ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (#159): item 153 closed, 155 filed.
- ~~`fix/python-direct-hooks-plan-gate`~~ ✓ (#160): items 152/111/154/143 closed, 156 filed.
- ~~`fix/heredoc-escape-guard`~~ ✓ (#161): item 142 closed, items 157 and 158 filed.
- ~~`fix/bash-tool-transport`~~ ✓ (#162): items 157 (falsified) and 158 closed.
- ~~`fix/test-reliability`~~ ✓ (#163): items 155 and 156 closed.
- ~~`test/assertion-strength`~~ ✓ (#164): items 115, 116, 122 and 159 closed.
- ~~`fix/frozen-composition-staleness`~~ ✓ (#165): items 106, 132 and 66 closed; 160 and 161
  filed.
- ~~`fix/regenerate-persistence`~~ ✓ (#166): item 160 closed; 162 filed.
- ~~`fix/regenerate-keeps-cover-letter`~~ ✓ (PR pending): item 162 closed; 163 filed.
- **Next: the owner's pick.** Not started:
  - item 163 (the run row's typed letter edit shadows a newly generated letter in
    `resume_state`; observed for a with-letter generate, inferred for the cover-letter route);
  - item 161 (`GET /composition` parses the context about eleven times per request);
  - item 7 memory-consolidation apply (Deferred);
  - item 30's C-7 probe branch;
  - launcher items 145–147;
  - the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/regenerate-keeps-cover-letter`:

| Commit | What |
|---|---|
| `2097a40` | **The instrument** (C-7). `tests/test_regenerate_cover_letter.py` (HTTP arms B1-B6), `docs/dev/diagnosis/regenerate-keeps-cover-letter.md`, this session's consumed-ledger file, and the previous session's hook-written `compacted` row (uncommitted on `main` at session start). |
| `41cac42` | Browser arm B7 (`tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py`); controls that fail loudly (`ControlFailed`, markers `raises=AssertionError`); owner decisions D1-D3. |
| `77bd254` | **The C-10 dossier first:** `docs/dev/blast-radius/regenerate-keeps-cover-letter.md` (24 rows), and D4. |
| `6e3d27e` | B8 (the discard branch) and control C3, before the fix. |
| `eeb73ed` | **The fix.** `hardening.py` (`resolve_cover_letter_after_generate`, `save_iteration_context`); `blueprints/generation.py` (both routes, `_typed_edits_disposition`, `_clear_run_edits`, `_built_from_edited_baseline`); `static/app.js` `_renderOutput`; `templates/index.html` notice copy. The instrument's markers deleted; a 6-case resolver table and 4 helper tests; `tests/test_app_iteration.py::test_generate_consumes_edits_from_context` now asserts the letter edit stays (the one test that pinned the old contract). |
| `429ff43` | Item 162 closed with `verified_by`; item 163 filed; board **Open 23**; `CHANGELOG.md`. |
| `3b84210` | Scoped `/wiki-self-update` (owner-authorized): `context-set-contract`, `iteration-audit-chain`, `frontend-wizard`, `route-surface`. Auditor caught 1, review caught 5 more (`docs/wiki/log.md`). Plus 2 comment-only fixes. |
| (this commit) | This handoff. |

**Tests run locally** (all `-p no:rerunfailures`):
- the instrument + `test_hardening_iteration.py` + `test_app_iteration.py` +
  `test_composition_staleness.py`: 71 passed;
- the consumers the dossier names (persistence, frozen staleness, persist-run, detached cover
  letter, live preview, analyzer iteration, write races, deterministic generate, application
  routes, gap fill, OpenAPI): 282 passed;
- UX: B7 + the wizard-flow-polish generate drive + the happy path: 4 passed (78.6 s, about
  1.1 GB free);
- `ruff check .` clean; `ruff format --check .` 401 files formatted; `mypy` clean on the two
  changed modules; `node --check static/app.js` OK; `work_items check` OK; `check_doc_links`
  OK (641); `doc_lints` 0 blocks; `wiki_freshness` OK (36 files).

**Gate:**
- **There is no local gate pass for this tree.** `python -m scripts.gate` was not run: the
  owner chose CI as the merge gate (2026-10-12; the full gate takes more than 25 minutes and
  was killed by memory pressure last session).
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.
- **CI on PR #167 (run 38329364979, head `49df1ea`): `ci_wait` exit 0.** All eight required
  checks passed (Analyze ×4, Lint/type-check/test on py3.11, 3.12 and 3.13, UX / a11y / PDF
  on py3.12) and no required run log held an absorbed rerun. The docs-only commit that
  records this re-triggers the checks; the merge needs `ci_wait` exit 0 on that head too.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 23 / 10 ceiling -- OVER"** (this branch closed 162 and filed 163). The owner's
drawdown direction stands: down to 0 if possible, before alpha staging. That is well past
the ~8–10 reduction-sprint threshold.

`## Open` (21 items; the header also counts open epics). Generated from the
board; owner-decision items are marked *(owner)*:
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
- **163**: A with-letter generate consumes the letter edit in the context but not on the run row; resume shows the typed text.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` (43) and `## Epics` in `BOARD.md`.

Declared, not filed. These are carried from the previous handoff unless marked new, and **not
re-verified this session** unless stated:
- **New: `carry_edits=True` with a letter produced keeps the typed letter edit (existing,
  unobserved).** `carry` now needs a typed résumé edit, so this is the frozen, same-résumé,
  with-letter case where a résumé edit also exists: the helper pops nothing and the edit
  shadows the new letter in the preview. Recorded in the blast-radius dossier's Deferred.
- **New: The edit-detect diff (`summarize_recent_edits`) is unobserved against the fix.** It reads
  `last_generated_cover_letter`, which now survives a regenerate. Diagnosis I2.
- **New: `lastCoverLetterPath` is assigned in seven places and read by none** (`static/app.js`;
  diagnosis O8). Dead client state; not removed (out of scope).
- **New: Orphaned `chrome-headless-shell` processes from earlier today** (20 started 5:40 AM, about
  300 MB, plus older `chrome`/`node`/`python3.13`): not this session's, so not killed. Item 128
  is the stray-process item.
- **New: Edits made outside the Edit|Write gates this session:** `tests/test_hardening_iteration.py`
  (appended tests) and one `docs/wiki/pages/frontend-wizard.md` paragraph through a Python
  script run from Bash, and `docs/wiki/log.md` through a shell heredoc. None is a gated surface
  (`tests/**` and `docs/**` are exempt); declared because the carried item below says the gates
  can't see such writes.
- **Under D1 (item 160), a bullet or title that only an earlier iteration selected loses its
  run reference.** A merge or delete of it is then no longer blocked by the
  `blueprints/corpus/experiences.py` merge guards. Accepted per the owner's decision;
  recorded in `docs/dev/blast-radius/regenerate-persistence.md` row 6 (carried).
- **`has_cover_letter` reads False after a résumé-only first generate** (the column stays
  `None`, not `""`). This is more accurate; the Pipeline card stops saying "cover letter"
  when there isn't one (`regenerate-persistence` blast-radius row 7) (carried).
- **The item-160 A3 instrument showed the LLM path's stored résumé as just the header**
  (`"# Alice Rivera\nalice@example.com\n"`) even when the stub selected bullets. That's the
  corpus re-render of a stub result with no JSON résumé, so likely a stub artifact. Not
  investigated (carried).
- **The two UX tests `fix/frozen-composition-staleness` added ran on CI #165 only** (carried).
- **Bash-run scripts edit files without the Edit|Write gates seeing them** (carried). This session's own such writes are declared above.
- **The wiki scribe/auditor pair keeps missing real problems.** This branch: 1 caught by the auditor,
  5 in orchestrator review (`docs/wiki/log.md`), the fourth pass in a row. See Recurrences.
- **A gap-fill retire, or a drag back to the same position, marks an approval stale without
  changing the résumé** (carried).
- **Approvals frozen before `fix/frozen-composition-staleness` carry no digest** (carried).
- **The post-generate announcement still says "Resume and cover letter generated"** when no
  cover letter was produced (`static/app.js`, `runGeneration`'s `_announce`) (carried).
- **The interrogative-witness pause re-arms on events that aren't user prompts** (carried). This
  session it fired again after subagent hand-backs and task-notifications, at least 6 times, and on
  the first call of a parallel batch (the rest applied). `docs/governance/enforcement.md` still names
  only the subagent hand-back case.
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN), as counted by an earlier `/wiki-lint`.
- **`sartorEval.run()` returns no handle on its success path** (`dashboard.html`); no caller reads
  it. Deferred in `docs/dev/blast-radius/console-run-lock-hardening.md`.
- **One UX test took 301 s alone** before the console fix, at about 1 GB free; not investigated.
- **`docs/dev/diagnostics.md` cites code by line number**, which rots on every edit.
- **The derived-set test's `git ls-files` costs 1.8–5.2 s on this machine** under 0.5–0.8 GB
  free.
- **Transitive wiki relevance is not modelled** (`PERFORMANCE_HISTORY.md` →
  `scripts/perf_baseline.py`).
- **`python3` resolution on hypha and the homelab is unchecked.** On a machine without `python3`
  on PATH no hook starts and the gates fail open (`docs/governance/enforcement.md`).
- **`tests/test_plan_approval_scoping.py` takes about 6 minutes locally.** Split it by `-k`
  class.
- **Pre-existing count drift**, each deferred again in
  `docs/dev/blast-radius/bash-tool-transport.md`:
  - `docs/governance/enforcement.md:29-31` says "8 exist"; there are now 14 rules;
  - `tests/test_enforcement_core.py`'s `TestBashDispatcher` docstring names four guards (there
    are seven);
  - `scripts/enforcement/blast_radius.py`'s `result.py` entry says "10 non-test importers"; an
    earlier branch added one more.
- **Item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry** (0 hits).
- **`test_enforcement_core.py`'s non-Bash half took 435 s locally** at about 1 GB free.
- **The threaded UX `live_server` may expose route reads on Windows** (inferred, not observed;
  `docs/dev/diagnosis/test-reliability.md` §Inferred).
- **`tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt** (run 30940947527). Not investigated.
- **The full local gate takes more than 25 minutes on this machine.** Don't wrap
  `python -m scripts.gate` in a shorter `timeout`; run it in the background with 35–40 min.
- **A fresh pytest start costs 9–47 s here, depending on free RAM.** Loop or mutate inside one
  process with the scratchpad plugins: `loop_plugin`
  (`docs/dev/diagnosis/test-reliability.md`) and `mut_plugin`
  (`docs/dev/diagnosis/assertion-strength.md`).
- **Item 159's gate has two declared, unenforced limits** (in item 159 and the gate's
  docstring): a wait on a toast message's text alone isn't caught, and neither is a selector
  built at runtime.
- **Free memory sat at 0.5–1.1 GB through last session and read 1.08–1.56 GB this one** (the
  owner's own applications). **Claude Code itself also stops idle background shells when
  system memory runs critically low** (`CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` at
  startup turns that off).
- **The first, cold read of the repo's 410 `.py` files took 9.3 s; a warm read takes
  ~0.5 s.** The toast gate reads them twice.

---

## Recurrences observed this session → guardrail authored

1. **A hook-written `compacted` ledger row left a tracked file modified on `main`** (second
   instance; the previous handoff recorded the first).
   - **The instance:** at session start `docs/dev/ledger/0ad52715-d26a-43b8-875d-72ea47f81d66.jsonl`
     carried an uncommitted `compacted` row (`"branch": "main"`, `2026-10-12T22:52:48Z`),
     appended after that session's close-out.
   - **No mechanism authored.** The writer is the PreCompact hook, which appends to the
     session's own ledger file wherever the branch is. A fix means moving compaction rows out
     of tracked files, or exempting them in the provenance schema (`docs/dev/prov/SPEC.md`):
     a hook-contract change outside this branch's scope. Folded into this branch's first
     commit, as last time. Surfaced to the owner here.
2. **The wiki scribe/auditor pair again** (the fourth pass in a row; `docs/wiki/log.md`).
   - **The instances:** the auditor marked `route-surface`'s "the typed letter edit that
     generate did not consume" SUPPORTED on the evidence that "the LLM calls never receive
     `edited_cover_letter_text`", which is false (`analyzer._current_cover_letter_draft`
     reads it as the draft). Review caught 5 issues, the auditor 1.
   - **No mechanism authored.** A behavior claim on a branch the code can take (`carry_edits`)
     is not mechanically checkable (C-0). What helped: a brief naming the source facts and
     banning line cites and intent claims, and reading every diff against source. Surfaced to
     the owner here.
3. **The interrogative-witness pause re-arming on non-prompt events** (carried; at least 6
   more instances this session).
   - **New detail:** it fires on the first call of a *parallel batch*. The other calls in the
     batch apply, so related edits land partially until the paused call is re-run.
   - **No mechanism authored.** The fix belongs in the witness (re-arm only on a real user
     prompt), a hook change outside this branch's scope. Surfaced again here.
4. **An `xfail(strict=True)` arm whose controls are bare `assert`s reads a broken drive as the
   defect** (first instance; caught while writing the browser arm, by no mechanism).
   - **The instance:** `2097a40`'s HTTP arms had their controls inside strict-xfail tests.
   - **Guardrail authored, UNENFORCED:** a convention in both new test files (`ControlFailed`
     for every drive and control step, markers `raises=AssertionError`, and `--runxfail`
     must fail at the defect line). It is not a gate: "a bare assert before the invariant in
     an xfail test" is not mechanizable as a lint. Written to memory
     (`reference-xfail-strict-masks-broken-controls`). Surfaced to the owner here.
5. **A consumer enumeration found a conflict with an earlier owner decision before the first
   edit** (charter C-10, working as designed).
   - **The instance:** decision 4's discard of both typed edits against D2.
   - **Mechanism:** the existing one held (`77bd254` is the dossier, committed before the fix
     `eeb73ed`). No new mechanism needed.

---

## What this branch should build

**None directed by this session.** The next branch is the owner's pick from the Open list
above, under item 40's drawdown direction. Item 163 is the closest follow-on: observed for a
with-letter generate (control C3), inferred for `/api/generate-cover-letter`, and it needs an
instrument before a fix. The choice is the owner's.

Scope is whatever the owner names, as filed in `docs/dev/work/items/`. Do not expand beyond it.

---

## First move

Run the pointer check and `--event consumed`, then ask the owner which Open item comes next.
Then create that branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to
the user before touching any code. **Do not code first.**

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
