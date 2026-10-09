<!-- provenance: schema=1 session=810882f3-b7f9-4c1c-829c-5da2989ed61d branch=fix/test-reliability commit=60d1af4 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-09 -->

# Agent handoff — test reliability (`fix/test-reliability`, items 155 + 156) → assertion strength (items 115 + 116 + 122)

**Branch to create:** `test/assertion-strength` (branch off `main`)
**Base branch:** `main`

> **This session closed items 155 and 156,** two test flakes. Both mechanisms were observed, not
> guessed.
> - **155: an app quirk and a test that read a shared signal.** The application modal opened
>   with focus on its notes field, so editing the company also saved the unchanged notes. When
>   that response landed second, `Notes saved` overwrote `Company saved` in the one shared
>   toast. Under load, response order alone decided pass or fail in all 30 runs.
>   - **Fixed on both sides,** by the owner's choice: notes now save only a change, and the test
>     waits on the company save's own response.
> - **156: the test's own threads crashed, not the product.** On Windows a plain read raises
>   `PermissionError` while another thread replaces the file. The harness's pre-reads died that
>   way, and the test called it a lost update. No failure in 700 runs was inside
>   `context_transaction`. Fixed in the test only.
>
> **The owner chose the next branch (2026-10-09): items 115, 116 and 122,** three
> test-strength items.

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
- ~~`fix/test-reliability`~~ ✓ (PR pending): items 155 and 156 closed.
- **`test/assertion-strength`** ← next (owner's pick, 2026-10-09): items 115, 116 and 122 only.
- Not started: item 7 memory-consolidation apply (Deferred), item 30's C-7 probe branch,
  launcher items 145–147, items 106 + 132 (frozen composition), and the owner-decision items
  (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold any other item into the 115/116/122
branch.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `fix/test-reliability`:
- **`a4bef7d`: the C-7 instruments.** No production code.
  - `docs/dev/diagnosis/test-reliability.md`, O1–O6:
    - O1: probe P-156 shows that plain reads and writers' replaces can each raise
      `PermissionError` on Windows;
    - O2–O3: the real test fails 8 of 400 idle and 18 of 300 under load, and every crash is
      in the harness;
    - O4: CI's rate for the 155 test is 1 of 113 attempts (a fresh `flake_rates collect`; the
      shard is committed);
    - O5: P-H1 reproduces the CI text 5 of 5;
    - O6: under load, 3 natural failures in 30, all with the meta response first.
  - The real tests were instrumented: writer-crash capture for 156, an in-page timeline for 155.
  - This session's consumed-ledger file.
- **`81b1500`: the fix.**
  - `static/app.js`: the notes blur saves only a change. The C-10 dossier
    `docs/dev/blast-radius/test-reliability.md` was written first.
  - `tests/ux/regression/test_20260611_prior_app_resume_robustness.py`:
    - the test waits on PUT `/meta` and reads the company back from the reopen's GET body;
    - it asserts that an unchanged notes field sends no PUT;
    - the new `test_company_save_survives_a_later_notes_response` forces the response order.
  - `tests/test_hardening.py`:
    - the pre-reads retry on `write_context_atomic`'s own budget;
    - a transactional writer that crashes fails the test by name;
    - the control counts only writers that finished.
  - `hardening.py` is unchanged.
- **`60d1af4`:** items 155 and 156 closed with `verified_by`. Board: Open went from 28 to 26.
  The wiki-relevance check came back verified no-edit (`docs/wiki/log.md`).
- **This handoff's commit,** with the `CHANGELOG.md` entry.
- **Results under the same load, same machine** (all with `-p no:rerunfailures`):

  | Test | Before | After |
  |---|---|---|
  | 156 real test (300 runs) | 18 failed | 0 failed |
  | 155 real test (30 runs) | 3 failed | 0 failed |
  | Forced response order | 5 of 5 failed | 3 of 3 passed |

  The three mutation checks behave as designed.
- **Other tests:** `tests/test_hardening.py`, the 155 UX module and
  `tests/test_application_routes.py`: 201 passed. `check_doc_links`: OK (625). `work_items
  check`: OK. `ruff`, `format` and `mypy` are clean on the changed files.
- **Gate:**
  - **First run (at `60d1af4`):** ruff ✓, format ✓, mypy ✓ (410 files), and
    `pytest -m "not ux"` 3173 passed, 8 skipped. Then this session's own `timeout 1500` wrapper
    killed `pytest -m ux` at 36% (`gate: FAILED at pytest -m ux (exit 143)`). It was the
    wrapper, not a test.
  - **Second run:** a full run on this handoff's commit. Its verdict is
    `python -m scripts.gate --result` at this commit, and the PR description records it.
  - **CI on the PR is the merge gate:** `python -m scripts.ci_wait <n>`, and exit 3 means stop.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 26 / 10 ceiling -- OVER"**
(28 at this branch's start; items 155 and 156 closed). The owner's drawdown direction stands:
down to 0 if possible, before alpha staging. Well past the ~8–10 reduction-sprint threshold.

`## Open` (24 items; the header also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **106**: Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **115**: Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring. ← **next branch**
- **116**: Post-Collate help circle is wired at runtime; C3's UX test never reaches it, only render-with-no-error is verified. ← **next branch**
- **122**: Three C3 assertions survive plausible mutants; tighten each to fail on the regression it names. ← **next branch**
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. **Still true at this close:** five python3.13 processes started 2026-09-18 to 10-06 are alive, none of them this session's.
- **129** *(owner)*: Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?
- **130**: Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty.
- **131**: Retire dialog cites a "Show retired" toggle Pipeline lacks; its query drops retired apps.
- **132**: Follow-up answers save, but regenerate re-assembles the frozen composition with no AI call. UNVERIFIED.
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

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` and `## Epics` in `BOARD.md`.

Declared, not filed (carried from the previous handoff unless marked new; **not re-verified this
session** unless stated):
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
  - `scripts/enforcement/blast_radius.py`'s `result.py` entry says "10 non-test importers"; the
    previous branch added one more.
- **The interrogative-witness pause re-arms on events that aren't user prompts.**
  - **Updated, observed this session:** it fired on the first `Edit` after an `AskUserQuestion`
    answer and a background-task notification arrived together. Which one re-armed it can't be
    told from that.
  - `enforcement.md` names the subagent hand-back case. The task-notification case and the
    `AskUserQuestion` case are still not named.
- **Item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry** (0 hits).
- **`test_enforcement_core.py`'s non-Bash half took 435 s locally** at about 1 GB free.
- **New: the threaded UX `live_server` may expose route reads on Windows.** A route's optimistic
  context read that runs outside `context_transaction` could raise the same `PermissionError`
  as item 156 while another request writes that file. Production is single-threaded and can't
  reach it. Inferred, not observed (`docs/dev/diagnosis/test-reliability.md` §Inferred).
- **New: `tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt.** That was run 30940947527 (`feat/consumer-enumeration-gate`, quality
  job, py3.13). Found in the flake-rate store this session; not investigated.
- **New: the full local gate takes more than 25 minutes on this machine.** `pytest -m "not ux"`
  alone took 980 s. Don't wrap `python -m scripts.gate` in a shorter `timeout`; this session's
  `timeout 1500` killed the UX tier with exit 143. The gate's result file wasn't written, and
  `--result` refused to certify the run, so the existing mechanism held.
- **New: a fresh pytest start costs 9–47 s here, depending on free RAM.** Repeated node ids are
  de-duplicated. Loop a test inside one process with the scratchpad plugin described in memory
  `reference-pytest-in-process-loop-and-mutation-plugins`; its source is in the diagnosis
  dossier.

---

## Recurrences observed this session → guardrail authored

1. **A test waited on a shared signal that another actor also writes** (item 155: the one
   `#_corpusToast`).
   - **Recognized as a member of a known class:** the epic-19 UX flake family, where a wait is
     satisfied, or defeated, by an event from something other than the action under test.
   - **Mechanism, fails closed for this test:**
     - it waits on the request's own response and reads the server's answer;
     - it asserts that an unchanged notes blur sends no PUT, which fails if the app half is
       reverted (checked);
     - `test_company_save_survives_a_later_notes_response` forces the response order, and ends
       on a check that the order really happened.
   - **No class-wide mechanism.** A guard that bans toast waits across the UX tier was
     considered and not built. The one other toast wait,
     `test_20260809_wizard_rail_frozen_gate.py:135`, waits on a synchronous refusal toast with
     no save in flight, and is 0/112 in CI. A ban would need an allowlist entry for it, and the
     owner bounded this branch to 155 and 156.
   - **Surfaced to the owner** in the close summary as a possible follow-up.
2. **A test misreported a harness crash as a product failure** (item 156; the same shape as the
   "plausible mechanism filed as fact" cost items 13, 15 and 31 under C-12).
   - **Mechanism, fails closed:** every writer's exception is captured, and a crashed
     transactional writer fails the test by name, never as "lost a delta". The control counts
     only writers that finished, so a crash can't satisfy it. Both behaviors were proven by
     mutation checks.
3. **A doubled backslash in a heredoc** (item 142's class).
   - **Mechanism:** the existing `block-doubled-backslash` guard refused the command before it
     ran. The script was rewritten with the Write tool and run by path. No new mechanism needed.
4. **A long run was killed by a wrapper, and the kill looked like a failure** (memory
   `reference-background-bash-kill-ceiling`'s class).
   - **Mechanism:** the gate's own result file. The killed run wrote no PASS, and
     `gate --result` kept reporting the earlier run. Recorded above as a declared observation.
     No new mechanism needed.
5. **The interrogative-witness pause re-armed after non-prompt events** (the previous handoff's
   observation, again).
   - **No new mechanism.** It is outside items 155 and 156, and each instance cost one re-run.
   - **Unenforced.** Surfaced to the owner in the close summary.

---

## What this branch should build

`test/assertion-strength`, items **115**, **116** and **122** only. This is the owner's pick
(2026-10-09), under item 40's drawdown direction. The filed items are
`docs/dev/work/items/0115-run-detail-err-link-computed-style-assertion.md`,
`docs/dev/work/items/0116-run-fixture-dynamic-help-bubble-unverified.md` and
`docs/dev/work/items/0122-c3-test-assertion-teeth.md`. Each says what is and isn't verified;
read it before planning.

1. **Item 115: measure the color, don't read the rule.**
   - **Where:** `tests/ux/regression/test_20260924_run_detail_modal.py`.
   - **What:** open a run's reliability detail, find a `.err-link` on a failing call kind, and
     assert its computed `color` is the resolved `--danger`, not `--info`.
   - **The hover state too:** the fix added a matching `:hover` rule, and a future edit can
     re-shadow it.
   - Memory `reference-css-cascade-per-property-not-per-rule` is the reason the measurement is
     required.
2. **Item 116: open the help bubble that only exists after a Collate.**
   - **The gap:** `renderCollateResult()` in `dashboard/templates/dashboard.html` builds the
     "Run this fixture" `.help-info` circle after a Collate. No test clicks it.
   - **What:** drive a real Collate, either from
     `tests/ux/regression/test_20260925_dashboard_copy_discovery.py` or from
     `tests/ux/flows/test_annotation_tab.py`, which already runs one. Find the circle by its
     `aria-label`, and reuse `_assert_help_opens()`.
3. **Item 122: give three assertions teeth.**
   - **`tests/test_dashboard_copy.py`, raw names:** match snake_case and `*.json(l)` tokens in
     tile text, with an explicit allowlist. This replaces a five-string denylist.
   - **`tests/test_dashboard_copy.py`, help titles:** bound the registry-title search to the
     entry's own `{…}`.
   - **`tests/test_annotation_routes.py:893`:** assert the specific message or status, not
     `"error" in body`.
4. **Verify each by mutation:** before closing an item, show that its new assertion fails on
   the regression it names. That was the method that closed 156 here (memory
   `reference-pytest-in-process-loop-and-mutation-plugins`).
5. **C-10:** these are test-only changes. If one turns out to need a `dashboard.html` or
   `ui_pages/` edit, enumerate its consumers into
   `docs/dev/blast-radius/assertion-strength.md` before the first edit.

Scope is bounded to items 115, 116 and 122 as filed in `docs/dev/work/items/`. Do not expand
beyond them.

---

## First move

Create branch `test/assertion-strength` off `main`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

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
