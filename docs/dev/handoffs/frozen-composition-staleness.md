<!-- provenance: schema=1 session=b504b487-00c5-4b0d-93dd-76b78dca6bd8 branch=fix/frozen-composition-staleness commit=6dc58c3 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-11 -->

# Agent handoff — frozen-composition staleness (`fix/frozen-composition-staleness`, items 106 + 132, folding in 66) → next drawdown branch (owner's pick)

**Branch to create:** none directed by this session. The owner picks the next drawdown item;
see "What this branch should build".
**Base branch:** `main`

> **This session closed items 106, 132 and 66, and filed 160 and 161.**
> - **The defect:** once Compose's Save and continue froze a composition, no later edit in that
>   application's Compose reached the preview, Generate or the download, and nothing said so.
>   Reproduced first, at `76f7a44`, by an HTTP-level instrument
>   (`docs/dev/diagnosis/frozen-composition-staleness.md`, O1–O8).
> - **The fix, per five owner decisions (2026-10-10):** a post-approval Compose edit marks the
>   approval **stale**, so Step 5 locks and both generate routes return 409 until Save and
>   continue re-approves. A Career Corpus panel edit never stales an approved application.
>   Item 132's button becomes "Save answers and revise in Compose". Typed edits are kept over
>   an unchanged regenerate and discarded with a notice after a re-approval. Compose's arrival
>   auto-fires don't run on an approved composition.
> - **Found, out of scope:** item 160. A second generate of the same run never persists; resume
>   shows the first résumé (diagnosis O9).

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
- ~~`fix/frozen-composition-staleness`~~ ✓ (PR pending): items 106, 132 and 66 closed; 160
  and 161 filed.
- **Next: the owner's pick.** Not started:
  - item 160 (a second generate never persists; observed, user-facing);
  - item 7 memory-consolidation apply (Deferred);
  - item 30's C-7 probe branch;
  - launcher items 145–147;
  - the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/frozen-composition-staleness`:

| Commit | What |
|---|---|
| `da967cf` | **The instrument** (C-7): `tests/test_frozen_composition_staleness.py` drives the real routes (analyzer stubbed) through analyze → Save and continue → one post-freeze edit → every surface, across eight edit arms and four controls. Defect invariants were `xfail(strict=True)`: 22 passed, 24 xfailed; with `--runxfail`, 24 failed, 22 passed. Plus the diagnosis dossier, this session's consumed-ledger file, and the previous session's `compacted` row found uncommitted on `main`. |
| `ca2a1f6` | **The fix.** `hardening`: `COMPOSITION_INPUT_KEYS`, `composition_inputs_digest`, `composition_is_stale`, `ContextSet.compose_corpus_edits`, `save_iteration_context(carry_edits=)`. The freeze stamps `meta.sartor.inputs_digest`. `POST /composition/touch` (new); `stale` / `composition_stale` on the composition and resume payloads; both generate routes 409 when stale; the refinement drafter reads the live doc when stale; typed edits carried or discarded. Client: one `_applyCompositionState` funnel, rail lock and reason, notices, touch-first `_composeCorpusFetch` / `_composeCorpusJson`, item 132's relabel, copy fixes. Four selectors (C-10 dossier first). Tests: the instrument's markers deleted (46 pass); `tests/test_composition_staleness.py` (21); `tests/ux/regression/test_20261010_compose_edit_after_freeze.py` (2, not run locally). |
| `7e778fa` | Items 66, 106, 132 closed with `verified_by`; 160, 161 filed; board **Open 23** (two closed, two filed); user docs (`walkthrough.md`, `iterating.md`); `architecture.md`; `CHANGELOG.md`. |
| `6dc58c3` | Scoped `/wiki-self-update` (owner-authorized): five pages; auditor catch-rate 4 on 5 pages, plus 3 misses caught in review (`docs/wiki/log.md`). |
| `d7590a9` | This handoff. |
| `8b0471b` | The six advisory CodeQL alerts this branch introduced on PR #165 (CI run 38174846179): `_read_freeze_state` now uses `resolve_within` (the modeled path-injection barrier) instead of `Path` + `_within`; two test-only shapes (`unnecessary-lambda`, `missing-equals`). Local re-run: 152 passed. |

**Tests run locally** (all `-p no:rerunfailures`):
- the instrument + regression module: 67 passed;
- 13 existing modules on the touched surfaces (composition, generate, preview, application
  routes, iteration, corpus-to-JSON, eval runner, telemetry, refinement, route containment, UX
  stub coverage, gap-fill decide, clarify): 319 passed;
- `test_openapi_spec`, `test_consumer_enumeration_gate`, `test_ux_toast_wait_gate`: 31 passed;
- the four doc test modules: 114 passed;
- `ruff check .` clean; `ruff format --check .` 398 files formatted; `mypy` clean on every
  changed module; `node --check static/app.js` OK; `work_items check` OK; `check_doc_links` OK
  (633); `doc_lints` 0 blocks.

**Gate:**
- **There is no local gate pass for this tree.** Run from Git Bash at `6dc58c3` with the
  owner's go-ahead, the gate refused at its own preflight:
  `gate: REFUSED -- 0.86 GB free, below the 1.00 GB floor.` / ``gate: FAILED at `memory preflight` (exit 1)``.
  Free memory read 1.7 GB a minute earlier and 0.5–1.1 GB for most of the session.
- **The owner's pre-approved fallback (2026-10-11): CI is the merge gate.** The two new UX
  tests get their first run there.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 23 / 10 ceiling -- OVER"**
(23 at this branch's start: 106 and 132 closed, 160 and 161 filed; 66 closed from Watching).
The owner's drawdown direction stands: down to 0 if possible, before alpha staging. That is well
past the ~8–10 reduction-sprint threshold.

`## Open` (21 items; the header also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. **Still true at this close:** six `python3.13` processes alive, none started by this session.
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
- **160** (new): Regenerate re-inserts the run's selected bullets, hits UNIQUE(run, bullet), rolls back; resume shows the FIRST résumé.
- **161** (new): Each _read_* helper re-reads and re-parses the context JSON; one parse could serve them all.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` (43) and `## Epics` in `BOARD.md`.

Declared, not filed. These are carried from the previous handoff unless marked new, and **not
re-verified this session** unless stated:
- **New: the two UX tests this branch added have never run anywhere.** The local gate refused
  for memory and no Chromium fit alongside the owner's applications. CI is their first run.
- **New: Bash-run scripts edit files without the Edit|Write gates seeing them.** This session
  edited `static/app.js`, `templates/index.html` and the gated `ui_pages/selectors.py` through
  Python scripts run by Bash. The C-10 dossier already named the gated file, so its condition
  was met, but `require-consumer-enumeration`, `require-evidence-before-fix` and the plan gate
  never saw those writes. Only the `block-*` Bash guards run on that path.
- **New: the wiki scribe/auditor pair missed three wrong passages on one long page**
  (`frontend-wizard`). The auditor marked a mislocated section SUPPORTED. Recorded in
  `docs/wiki/log.md` as the retune signal the loop's design asks for.
- **New: a separately generated cover letter may be blanked by a résumé-only regenerate**
  (`hardening.py`, `last_generated_cover_letter = ""` in `save_iteration_context`). Inferred
  from code; not instrumented (diagnosis `## Inferred`).
- **New: a gap-fill retire, or a drag back to the same position, marks an approval stale
  without changing the résumé.** Both change `composition_overrides`, which is a digest input.
  Declared in the diagnosis's fix section.
- **New: approvals frozen before this branch carry no digest,** so they detect only Compose's
  corpus edits until approved again.
- **New: the post-generate announcement still says "Resume and cover letter generated"** when
  no cover letter was produced (`static/app.js`, `runGeneration`'s `_announce`).
- **The interrogative-witness pause re-arms on events that aren't user prompts. Now
  separated (new this session):** it fired on the first Edit/Write after every task-notification
  that arrived alone (at least eight times) and never after an `AskUserQuestion` answer (seven
  times). `docs/governance/enforcement.md` still names only the subagent hand-back case.
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN), as counted by an earlier `/wiki-lint`.
- **`sartorEval.run()` returns no handle on its success path** (`dashboard.html`); no caller reads
  it. Deferred in `docs/dev/blast-radius/console-run-lock-hardening.md`.
- **One UX test took 301 s alone** before the console fix, at about 1 GB free; not investigated.
- **`docs/dev/diagnostics.md` cites code by line number**, which rots on every edit. (This
  session re-anchored one such cite in `architecture.md` and two in the wiki to symbols.)
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
- **The threaded UX `live_server` may expose route reads on Windows.** A route's optimistic
  context read that runs outside `context_transaction` could raise the same `PermissionError`
  as item 156 while another request writes that file. Production is single-threaded and can't
  reach it. Inferred, not observed (`docs/dev/diagnosis/test-reliability.md` §Inferred).
- **`tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt.** That was run 30940947527 (`feat/consumer-enumeration-gate`, quality
  job, py3.13). Not investigated.
- **The full local gate takes more than 25 minutes on this machine.** Don't wrap
  `python -m scripts.gate` in a shorter `timeout`; run it in the background with 35–40 min.
- **A fresh pytest start costs 9–47 s here, depending on free RAM.** Loop or mutate inside one
  process with the scratchpad plugins: `loop_plugin`
  (`docs/dev/diagnosis/test-reliability.md`) and `mut_plugin`
  (`docs/dev/diagnosis/assertion-strength.md`).
- **Item 159's gate has two declared, unenforced limits** (in item 159 and the gate's
  docstring): a wait on a toast message's text alone isn't caught, and neither is a selector
  built at runtime.
- **Free memory sat at 0.5–1.7 GB all session** (the owner's own applications). It cost the
  local gate and every local UX run. **Claude Code itself also stops idle background shells
  when system memory runs critically low** (`CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` at
  startup turns that off).
- **The first, cold read of the repo's 410 `.py` files took 9.3 s; a warm read takes
  ~0.5 s.** The toast gate reads them twice.

---

## Recurrences observed this session → guardrail authored

1. **A doubled backslash in a Bash command** (item 142's class; a member of a known class).
   - **The instance:** a heredoc'd Python edit to a scratch script, with `\n` inside a string
     literal.
   - **Mechanism:** the existing `block-doubled-backslash` guard refused it before it ran. The
     edit was redone with the Edit tool. No new mechanism needed.
2. **The interrogative-witness pause re-arming on non-prompt events** (carried from the last two
   handoffs; at least eight instances here).
   - **No mechanism authored on this branch.** The fix belongs in the witness (re-arm only on a
     real user prompt). That is a hook change, outside this branch's scope. This session
     separated the cause (task-notifications re-arm; `AskUserQuestion` answers don't) and
     records it above and in memory. Surfaced to the owner in this handoff.
3. **A model's code-read treated as fact** (charter C-12's class: a subagent's report becoming a
   premise).
   - **The instances:** the wiki scribe wrote three wrong passages on `frontend-wizard`, and its
     auditor passed one of them. I caught all three by checking the source myself before
     accepting the pass.
   - **Mechanism:** the existing author ≠ auditor loop plus orchestrator review held. No new
     mechanism authored. A mechanical check for "this page's step labels match
     `data-wstep-body`" is possible but wasn't built. Surfaced here and in `docs/wiki/log.md`.
4. **A line-number cite that drifted** (the class `docs/dev/diagnostics.md` already carries).
   - **The instances:** `architecture.md`'s `static/app.js:7094` (already stale before this
     branch) and the wiki's `(line 2783)`, both re-anchored to symbol names.
   - **No new mechanism:** `check_doc_links.py` checks that a cited line exists, not that it
     still holds the cited code. Declared, not built.
5. **A silent tool false-negative** (a member of the `| tail`-masks-the-exit-code class,
   memory `reference-pytest-exit-through-pipe`).
   - **The instances:** `grep` dropped every matching line from cp1252 test output ("Binary
     file matches"); app loggers never reached pytest's log capture, which hid item 160's
     swallowed exception.
   - **No mechanism:** both are recorded in memory with the workaround (`grep -a`; wrap the
     function). Neither is a repo defect a gate could catch.
6. **Instrument errors caught by their own guard** (not a failure; recorded because the
   mechanism worked). Two first-run invariants passed on the base tip for instrument reasons
   (an echoed-field projection; a block that carries no skills). `xfail(strict=True)` turned
   both into failures before commit 1, so the dossier quotes only real defects.

---

## What this branch should build

**None directed by this session.** The next branch is the owner's pick from the Open list
above, under item 40's drawdown direction. Item 160 is a new, observed, user-facing defect found
here (resuming an application loads its first generated résumé, not the latest). It is the
closest follow-on, and the owner's call.

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
