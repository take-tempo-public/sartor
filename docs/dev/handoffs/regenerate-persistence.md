<!-- provenance: schema=1 session=0ad52715-d26a-43b8-875d-72ea47f81d66 branch=fix/regenerate-persistence commit=7f965bb actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-12 -->

# Agent handoff — a regenerate never persisted (`fix/regenerate-persistence`, item 160) → next drawdown branch (owner's pick)

**Branch to create:** none directed by this session. The owner picks the next drawdown item;
see "What this branch should build".
**Base branch:** `main`

> **This session closed item 160 and filed 162.**
> - **The defect:** every generate of an application reuses one `ApplicationRun`. The second
>   persist re-inserted `application_bullet` rows, hit `uq_application_bullet` and rolled
>   back, so resuming an application showed its first résumé. The route only logged it.
> - **The instrument first** (`7bcbc3a`): eight arms. They also showed that a duplicate
>   inside ONE result fails even a first persist (O5). A résumé-only regenerate blanks a
>   detached cover letter, with no rollback involved (O4); that corrected the plan's
>   inference. Proposals stack duplicates (O6), and the failure never reaches the response
>   (O7).
> - **The fix, per owner decisions (2026-10-12):**
>   - D1, replace in place: the run's bullet and title rows become the latest selection.
>   - D2: the letter is written only when present; a known proposal text isn't re-created;
>     `persist_failed` plus a Step 6 banner; batched lookups.

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
- ~~`fix/regenerate-persistence`~~ ✓ (PR pending): item 160 closed; 162 filed.
- **Next: the owner's pick.** Not started:
  - item 162 (the context-file half of the cover-letter clobber; observed, user effect inferred);
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
`fix/regenerate-persistence`:

| Commit | What |
|---|---|
| `7bcbc3a` | **The instrument** (C-7). `tests/test_regenerate_persistence.py` drives the real routes through the staleness rig and records each persist's outcome. On `main` @ `cfab8e0` with `--runxfail`: 8 failed, 2 passed (2 passed, 8 xfailed without it). Also the diagnosis dossier, this session's consumed-ledger file, and the previous session's uncommitted `compacted` row. |
| `75f4306` | **The fix.** `db/persist_run.py`: replace-then-insert of the run's `application_bullet` / `application_run_title` rows; duplicate skips (`duplicate_selections_skipped`); per-experience `position`; letter written only when non-empty; proposal-text dedupe (`proposed_bullets_already_present`); one `IN` query per kind (`_owned_experience_ids`). `blueprints/generation.py`: `persist_failed` on both routes. Client: the `persistFailedNotice` banner, toggled by `_renderOutput`. C-10 dossier first: `docs/dev/blast-radius/regenerate-persistence.md`. Tests: the instrument's markers deleted; `tests/test_persist_run.py::TestRegenerateSameRun` (7, including a SELECT-count test); `tests/test_composition_staleness.py`'s re-approval test now asserts the latest `resume_md`. |
| `5db5d75` | Item 160 closed with `verified_by`; item 162 filed; board **Open 23**; `CHANGELOG.md`. |
| `7f965bb` | Scoped `/wiki-self-update` (owner-authorized): `application-audit-chain`, `route-surface`, `frontend-wizard`. Auditor catch-rate 0 on 3 pages; 3 caught in review (`docs/wiki/log.md`). |
| (this commit) | This handoff. |

**Tests run locally** (all `-p no:rerunfailures`):
- the instrument + `test_persist_run.py` + `test_composition_staleness.py` +
  `test_frozen_composition_staleness.py`: 106 passed;
- the cover-letter, application-routes, merge/retire, OpenAPI, consumer-gate,
  deterministic-generate, iteration, regenerate-gap-fill and cover-letter-format modules: 191
  passed;
- `ruff check .` clean; `ruff format --check .` 399 files formatted; `mypy` clean on the two
  changed modules; `node --check static/app.js` OK; `work_items check` OK; `check_doc_links`
  OK (637); `doc_lints` 0 blocks.

**Gate:**
- **There is no local gate pass for this tree.** Run from Git Bash at `7f965bb` with the
  owner's go-ahead (1.04 GB free at start): the memory preflight passed and whole-tree `mypy`
  reported `Success: no issues found in 415 source files`. Then, during
  `=== gate: pytest -m "not ux" -n auto ===`, Claude Code stopped the background shell
  because the system was critically low on memory. Free memory afterwards read 0.67 GB, below
  the 1.00 GB floor. No orphaned workers were left.
- **The owner's fallback (2026-10-12): CI is the merge gate.**
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 23 / 10 ceiling -- OVER"**
(this branch closed 160 and filed 162). The owner's drawdown direction stands: down to 0 if
possible, before alpha staging. That is well past the ~8–10 reduction-sprint threshold.

`## Open` (21 items; the header also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. Not re-checked this session.
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
- **162** (new): After a detached cover letter, a résumé-only regenerate's child context carries last_generated_cover_letter = ''.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` (43) and `## Epics` in `BOARD.md`.

Declared, not filed. These are carried from the previous handoff unless marked new, and **not
re-verified this session** unless stated:
- **New: under D1, a bullet or title that only an earlier iteration selected loses its run
  reference.** A merge or delete of it is then no longer blocked by the
  `blueprints/corpus/experiences.py` merge guards. Accepted per the owner's decision;
  recorded in `docs/dev/blast-radius/regenerate-persistence.md` row 6.
- **New: `has_cover_letter` now reads False after a résumé-only first generate** (the column
  stays `None`, not `""`). This is more accurate; the Pipeline card stops saying "cover letter"
  when there isn't one (blast-radius row 7).
- **New: the A3 instrument showed the LLM path's stored résumé as just the header** (`"# Alice
  Rivera\nalice@example.com\n"`) even when the stub selected bullets. That's the corpus re-render
  of a stub result with no JSON résumé, so likely a stub artifact. Not investigated.
- **The two UX tests the previous branch added had never run locally.** CI ran them on #165.
- **Bash-run scripts edit files without the Edit|Write gates seeing them** (carried). This
  session made every repo edit through Edit/Write.
- **The wiki scribe/auditor pair keeps missing real problems.** This branch: 0 catches on 3
  pages, 3 in orchestrator review (`docs/wiki/log.md`), the third pass in a row. See
  Recurrences.
- **A gap-fill retire, or a drag back to the same position, marks an approval stale without
  changing the résumé** (carried).
- **Approvals frozen before `fix/frozen-composition-staleness` carry no digest** (carried).
- **The post-generate announcement still says "Resume and cover letter generated"** when no
  cover letter was produced (`static/app.js`, `runGeneration`'s `_announce`) (carried).
- **The interrogative-witness pause re-arms on events that aren't user prompts** (carried). This
  session it fired again after subagent hand-backs and task-notifications (at least 5 times).
  `docs/governance/enforcement.md` still names only the subagent hand-back case.
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
- **Free memory sat at 0.5–1.1 GB all session** (the owner's own applications). **Claude Code
  itself also stops idle background shells when system memory runs critically low**
  (`CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` at startup turns that off).
- **The first, cold read of the repo's 410 `.py` files took 9.3 s; a warm read takes
  ~0.5 s.** The toast gate reads them twice.

---

## Recurrences observed this session → guardrail authored

1. **A function-local import defeated a module-level test patch** (a known class: memory
   `reference-function-local-import-defeats-module-patch`).
   - **The instance:** the cover-letter route imports `generate_cover_letter_against_resume`
     inside the function, so the rig's patch on `blueprints.generation` never reached it. A4's
     first run called a real client.
   - **No mechanism authored.** The instrument now patches the source module, and the failure
     was loud (an `AttributeError`), not silent. A lint against function-local imports in
     routes would be a code-style rule the codebase uses on purpose (lazy imports). Surfaced to
     the owner here.
2. **A wiki scribe wrote what no source says, and the auditor passed it** (the third pass in a
   row; `docs/wiki/log.md`).
   - **The instances:** a line-number cite (`generation.py:1232`) that will rot, and an
     invented intent ("defined for future expansion") that the auditor marked SUPPORTED even
     when told to flag intent claims.
   - **No mechanism authored on this branch.** Possible: a `doc_lints` rule that refuses a
     `](….py:NNN)` link in `docs/wiki/pages/`, which mechanically closes the line-cite half.
     The invented-claim half has no deterministic check. Orchestrator review caught all three;
     recorded in memory (`reference-wiki-scribe-cannot-create-pages`). Surfaced to the owner
     here.
3. **The interrogative-witness pause re-arming on non-prompt events** (carried, at least 5 more
   instances).
   - **No mechanism authored.** The fix belongs in the witness (re-arm only on a real user
     prompt), a hook change outside this branch's scope. Surfaced again here.
4. **An inference treated as a premise until instrumented** (charter C-12's class).
   - **The instance:** the plan asserted the cover-letter clobber was hidden by the rollback.
     The instrument (A4) showed it was live today.
   - **Mechanism:** the existing one held. C-7's instrument-first ordering and the dossier's
     `## Inferred` / `## Falsified` split caught it before the fix built on it. No new
     mechanism needed.

---

## What this branch should build

**None directed by this session.** The next branch is the owner's pick from the Open list
above, under item 40's drawdown direction. Item 162 is the closest follow-on: the context-file
half of this branch's cover-letter finding, observed, with its user effect still inferred. It
needs an instrument before a fix, and the choice is the owner's.

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
