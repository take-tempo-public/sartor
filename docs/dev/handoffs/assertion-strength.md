<!-- provenance: schema=1 session=c195419d-6716-4428-8548-155568c13083 branch=test/assertion-strength commit=8018d70 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-10 -->

# Agent handoff — assertion strength (`test/assertion-strength`, items 115 + 116 + 122) and the shared-toast wait gate (item 159) → next drawdown branch (owner's pick)

**Branch to create:** none directed by this session. The owner picks the next drawdown item;
see "What this branch should build".
**Base branch:** `main`

> **This session closed items 115, 116, 122 and 159. Every change is test-only.**
> - **115:** a UX test now measures the failing error count's computed color, both at rest and
>   on hover.
> - **116:** the annotation flow test now opens the help bubble that exists only after a
>   Collate.
> - **122:** three console-copy assertions now fail on the mutants filed against them.
> - **159** (filed and closed here, at the owner's direction): a new gate,
>   `tests/test_ux_toast_wait_gate.py`. It fails when any Python in the repo references the
>   shared `#_corpusToast` outside two allowlisted tests. That is item 155's class.
>
> Each change was verified by mutation. Every mutant passed the old test and fails the new one,
> and each run's control arm passed (`docs/dev/diagnosis/assertion-strength.md`).

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
- ~~`test/assertion-strength`~~ ✓ (PR pending): items 115, 116, 122 and 159 closed.
- **Next: the owner's pick.** Not started:
  - item 7 memory-consolidation apply (Deferred);
  - item 30's C-7 probe branch;
  - launcher items 145–147;
  - items 106 + 132 (frozen composition);
  - the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `test/assertion-strength`:

| Commit | What |
|---|---|
| `b8bebf1` | Item 159 filed. `docs/dev/diagnosis/assertion-strength.md` opens with the **before** arm (A1, A2): seven mutations, one per named regression. Each was applied (logged) and each passed the HEAD test it should have failed. Also this session's consumed-ledger file. |
| `d80f88d` | **Item 122:** `tests/test_dashboard_copy.py` and `tests/test_annotation_routes.py` (details below). |
| `7ee4d20` | **Item 115:** new `test_20260924_run_detail_modal.py::test_failing_error_count_keeps_danger_color_and_hover_affordance`. |
| `305a762` | **Item 116:** `test_annotation_tab.py::test_annotation_tab_save_and_collate` clicks the post-Collate "Run this fixture" (i), via `_assert_help_opens()`. |
| `7fd088d` | **Item 159:** `tests/test_ux_toast_wait_gate.py`. |
| `8018d70` | Items closed with `verified_by`; board **Open 26 → 23**; `CHANGELOG.md`; wiki relevance verified no-edit (`docs/wiki/log.md`). |
| this handoff's commit | |

**Item 122's three changes:**
- Raw names are matched by shape over space-joined tile text, with a used allowlist.
- Registry titles are bounded to their own entry.
- The Score-grounding help test asserts its specific claim.

**Mutation results** (`-p no:rerunfailures`, dossier A1–A5). The scratchpad plugin's source is
in the dossier. In every run the `none` control arm passed.

| Item | Mutant | Old test | New test |
|---|---|---|---|
| 115 | `dashboard.html:54` (F3 fix) removed from the served page | passed | failed: measured `rgb(96, 165, 250)` (`--info`) |
| 115 | `:55` (hover twin) removed | passed | failed: hover measured `rgb(248, 113, 113)` (`--danger`) |
| 116 | `window.sartorDashHelp` opener removed | passed | failed: help modal never opens |
| 116 | bubble opens `dashCollate` | passed | failed: title mismatch |
| 122 | the refuter's raw-name string injected into a Quality tile | passed | failed, tokens named |
| 122 | entry with no title; its bubble names the next entry's title | passed | failed, "has no title of its own" |
| 122 | help keeps the word "error" but drops the claim | passed | failed |
| 159 | allowlist entry dropped / stale entry / count raised / new toast wait | n/a (new) | all four failed |

**Item 159 against item 155's own history:** the gate flags the original wait as it ran in CI,
at `3cfb98d` in `test_card_company_editable_and_persists`.

**Other tests:**
- the touched modules pass: 85 in the two non-UX modules, 8 in the two UX modules, 2 in the
  gate;
- `ruff`, `ruff format --check` and `mypy` are clean on every changed file;
- `work_items check`: OK;
- `check_doc_links`: OK (628);
- `doc_lints`: 0 blocks.

**Gate:**
- **There is no local gate pass for this tree, and no local gate run at all.**
  - Under owner decision 5, a retry polled free memory for 12 minutes before starting the gate.
    It saw 0.61–1.04 GB and never cleared the 1.05 GB start mark (the gate's 1.00 GB floor plus
    a margin).
  - Claude Code then stopped the retry because the system was critically low on memory.
    The gate never started, and there is no `gate-result.json` for this tree.
  - Free memory was 0.50 GB afterwards.
- **The owner's direction (2026-10-10): CI is the merge gate.** The heavy local steps (`mypy .`,
  `pytest -m "not ux" -n auto`, `pytest -m ux`) were not run here.
- **Run locally on the branch tip `8018d70`:**
  - `ruff check .`: exit 0;
  - `ruff format --check .`: 395 files already formatted;
  - `work_items check`: OK;
  - plus the touched-module and per-file results listed above.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 23 / 10 ceiling -- OVER"**
(26 at this branch's start: 115, 116 and 122 closed; 159 filed and closed here). The owner's
drawdown direction stands: down to 0 if possible, before alpha staging. That is well past the
~8–10 reduction-sprint threshold.

`## Open` (21 items; the header also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **106**: Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. **Still true at this close:** seven `python3.13` processes started 2026-09-18 to 10-10 are alive, none of them this session's.
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

Declared, not filed. These are carried from the previous handoff unless marked new, and **not
re-verified this session** unless stated:
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
- **The interrogative-witness pause re-arms on events that aren't user prompts.**
  - `enforcement.md` names the subagent hand-back case.
  - The task-notification case (confirmed last session) is still not named there, and neither is
    the possible `AskUserQuestion` case.
  - This session's pauses:
    - The first fired on the first Write after the opening prompt, the designed case.
    - The second fired on the first Edit after a background-task notification and an
      `AskUserQuestion` answer arrived together. That's the same mixed case as before, so it
      still doesn't separate the two.
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
  `python -m scripts.gate` in a shorter `timeout`.
- **A fresh pytest start costs 9–47 s here, depending on free RAM.** Loop or mutate inside one
  process with the scratchpad plugins: `loop_plugin`
  (`docs/dev/diagnosis/test-reliability.md`) and `mut_plugin`
  (`docs/dev/diagnosis/assertion-strength.md`).
- **New: item 159's gate has two declared, unenforced limits** (in item 159 and the gate's
  docstring):
  - a wait on a toast message's text alone (`get_by_text("Notes saved")`) isn't caught;
  - neither is a selector built at runtime.
- **New: free memory sat at 0.50–1.08 GB all session** (the owner's own applications). See
  "Gate" above for what that cost. **Claude Code itself also stops idle background shells
  when system memory runs critically low**, and says not to restart them unasked. It stopped
  this session's gate retry that way (`CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` at
  startup turns that off; setting it from a shell has no effect).
- **New: the first, cold read of the repo's 410 `.py` files took 9.3 s; a warm read takes
  ~0.5 s.** The toast gate reads them twice (1.19 s measured warm), and a cold first run costs
  more.

---

## Recurrences observed this session → guardrail authored

1. **A UX test synchronizing on a signal another actor also writes** (item 155's class, the
   shared `#_corpusToast`).
   - **Recognized as a recurrence:** the previous handoff named this class (§Recurrences 1)
     and declared it unguarded.
   - **Mechanism authored, fails closed:** `tests/test_ux_toast_wait_gate.py` (item 159), at the
     owner's direction this session. It runs in `pytest -m "not ux"`, so the gate and CI enforce
     it for every agent.
   - **Proven by mutation:** four allowlist drifts and a new wait each fail it. Run on item 155's
     own history, it flags the original wait.
   - **Its two blind spots are declared:** a wait on toast text alone, and a runtime-built
     selector. Both are labelled unenforced in item 159.
2. **A doubled backslash in a Bash command, twice** (item 142's class).
   - **The two instances:** a Windows path in a `git commit -F` argument, and a `grep` pattern
     in the pre-push path scan.
   - **Mechanism:** the existing `block-doubled-backslash` guard refused both before they ran.
     They were rewritten with a `cygpath -m` path and with the PowerShell tool. No new mechanism
     needed.
3. **A bare tool name not on PATH** (`ruff`).
   - **Mechanism:** the existing `verify-binary-on-path` guard refused it and named
     `python -m ruff`. No new mechanism needed.
4. **A hand-transcribed handoff pointer.** I dropped the `Handoff: ` prefix when passing the
   owner's pointer line to the checker. That is a member of the hand-typed-pointer class
   (`docs/dev/diagnosis/handoff-pointer-verification.md`).
   - **Mechanism:** `check_handoff_pointer.py` refused the malformed line. The exact line then
     passed. No new mechanism needed.
5. **No local gate pass because of the owner's memory load** (the previous handoff's
   refusal, again).
   - **This time:** the gate never started. The preflight's floor was never cleared, and Claude
     Code stopped the retry for low memory.
   - **Mechanism:** the gate's own preflight, which fails closed. The memory reaper added
     nothing to it.
   - Memory `project-laptop-memory-pressure-is-transitional` records the owner's direction that
     the relief is hardware, not a repo workaround. No new mechanism.

---

## What this branch should build

**None directed by this session.** The next branch is the owner's pick from the Open list
above, under item 40's drawdown direction. The handoff that preceded this one listed what isn't
started (see "Where we are in the arc"). The owner chose this branch's items on 2026-10-09 and
added item 159 on 2026-10-10.

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
