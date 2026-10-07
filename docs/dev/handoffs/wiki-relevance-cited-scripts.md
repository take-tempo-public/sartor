<!-- provenance: schema=1 session=b6966e40-1ca3-47ed-a23e-a53d1858944f branch=fix/wiki-relevance-cited-scripts commit=f374b66 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-06 -->

# Agent handoff — wiki relevance (`fix/wiki-relevance-cited-scripts`) → hook group (items 152, 111, 154, 143)

**Branch to create:** `fix/python-direct-hooks-plan-gate` (branch off `main`)
**Base branch:** `main`

> **This session fixed item 153.** `RELEVANT_OVERRIDES` in `scripts/wiki_relevance.py` is now
> exactly the 23 `scripts/` and `docs/dev/perf/` files the wiki cites. A new test derives that
> set from `docs/wiki/` and asserts equality in both directions, so the list cannot drift
> silently again. Item 153 is closed. The branch merges through its PR.
>
> **The owner chose the next branch (2026-10-06): a GROUP fix of items 152, 111, 154 and 143.**
> This is an explicit owner override of the one-item-per-branch default: the four items share
> one surface (the Edit/Write hook wiring and the plan gate). Doing them apart would rework the
> same files four times.
>
> **CI is the gate, owner-directed (2026-10-05), and still is.** Free RAM was 0.5–0.8 GB all
> session. The full local gate passed ruff, format and mypy; its pytest step was killed by
> this session's own 120 s `timeout` wrapper, not by a failure. Targeted tests were run (below).

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

- ~~`chore/flake-shard-slim`~~ ✓ (#155): item 144, the held flake shard slimmed and committed.
- ~~`chore/agent-doc-drift`~~ ✓ (#156): items 54/141 closed, 148–152 filed.
- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157): items 123/124/136/148–151 closed, 153 filed.
- ~~`fix/console-run-lock-hardening`~~ ✓ (#158): items 112/117–121 closed, 154 filed.
- ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (PR pending): item 153 closed.
- **`fix/python-direct-hooks-plan-gate`** ← next (owner's pick, 2026-10-06): items 152, 111, 154, 143 as one group.
- Item 7 memory-consolidation apply (Deferred); item 30 C-7 probe branch; launcher items
  145–147: not started.

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold the launcher items, item 142, item 50 or
any other item into the hook-group branch: the owner named exactly four.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `fix/wiki-relevance-cited-scripts`:
- `701278c`: the C-7 instrument. `test_relevant_overrides_equal_wiki_cited_mixed_files` derives,
  from every `docs/wiki/**/*.md` except `log.md`, the mixed-prefix files the wiki cites — by full
  path, relative link, bare name, or dotted `scripts.<mod>` — and asserts set equality both ways.
  It failed on `main` 542da4a: **20** cited files classified irrelevant (the item's grep found 9;
  it stopped at `/` and missed bare-name and dotted cites) and **2** overrides
  (`perf_baseline.py`, `export_corpus_seed.py`) that no wiki page ever cited.
- `6238fe8`: the fix. `RELEVANT_OVERRIDES` = the derived 23. The list stays explicit by the
  owner's choice: a call-time wiki scan measured 85–200 ms per process against a 7 ms import,
  and the post-commit reminder classifies on every commit. The reason and measurement sit at
  the site. C-10 dossier `docs/dev/blast-radius/wiki-relevance-cited-scripts.md`, written first.
  Item 153 closed; BOARD regenerated.
- `dad9101`: the post-fix evidence `6238fe8`'s message cites (see Recurrences, item 143).
- This handoff's commit: item 154 control data point; this handoff.
- **Tests:** `198 passed in 781.46s` with `-p no:rerunfailures` (`test_wiki_relevance_classification`,
  `test_wiki_freshness_gate`, `test_enforcement_core`, `test_blast_radius_classification`,
  `test_consumer_enumeration_gate`). Mutation check both ways: removing `scripts/gate.py` fails
  on MISSING; adding an uncited path fails on STALE.
- **Drift** at checkpoint `3798e2d1`: 8 → 9 (block 75, nudge 10).
- **Gate:** ruff, format and mypy steps green inside `python -m scripts.gate`; pytest step killed
  by this session's own `timeout 120` (exit 143), so **the full local gate has not passed**. CI on
  the PR is the gate: `python -m scripts.ci_wait <n>`; a result of 3 means stop, not merge.
- **PR #159's first CI run exited 3 (green with reruns).** Every required check passed, but
  `test_20260611_prior_app_resume_robustness.py::test_card_company_editable_and_persists` failed
  1 of 3 attempts (run 37569283583): the toast read `Notes saved` where the test waits for
  `Company saved`. This PR's diff cannot reach that path. It was untracked, so it was filed as
  **item 155** on this branch before merging, and CI was re-run on the new tip.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 32 / 10 ceiling -- OVER"**
(this branch's tip; it was 32 at this branch's start — item 153 closed, item 155 filed). The owner's drawdown
direction stands: down to 0 if possible, before alpha staging. Well past the ~8–10
reduction-sprint threshold.

`## Open` (30 items; the header also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **106**: Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **111**: Plan-approval hook: ~2 s per edit, 8-21 s per retire, from MSYS fork count. Item 110 fixed correctness, not speed.
- **115**: Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring.
- **116**: Post-Collate help circle is wired at runtime; C3's UX test never reaches it, only render-with-no-error is verified.
- **122**: Three C3 assertions survive plausible mutants; tighten each to fail on the regression it names.
- **128** *(owner)*: D1 close-out saw several python3.13 processes started 2026-09-18..25 (~0 MB), not that session's own.
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
- **142**: Heredoc python scripts with backslash escapes wrote a backspace char and a broken file; a Bash guard could refuse them.
- **143**: Witness paused the plan Write; ExitPlanMode in the same batch still ran, so the owner approved the old plan text.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **146**: A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly.
- **147**: Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit.
- **152**: A Bash with no grep/sleep made a Monitor spin. Owner chose Python-direct hooks (no .sh wrappers) + a shell probe.
- **154**: Approved on main, then checkout+rebase; next Edit hit NO EDIT APPROVAL. Item 110's class; cause unverified.
- **155**: A CI attempt saw 'Notes saved', never 'Company saved', for 5 s after the company blur. Retry passed; cause unverified.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` and `## Epics` in `BOARD.md`.

Declared, not filed (carried from the previous handoff unless marked new; **not re-verified this
session** unless stated):
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN), as counted by an earlier `/wiki-lint`.
- **Item 128 (owner):** stray stdin-reader hook helper processes from earlier sessions.
- **`sartorEval.run()` returns no handle on its success path** (`dashboard.html`); no caller reads
  it. Deferred in `docs/dev/blast-radius/console-run-lock-hardening.md`.
- **One UX test took 301 s alone** before the console fix, at about 1 GB free; not investigated.
- **`docs/dev/diagnostics.md` cites code by line number**, which rots on every edit.
- **New: the derived-set test's `git ls-files` costs 1.8–5.2 s on this machine** under 0.5–0.8 GB
  free (one subprocess, the minimum; the ambiguity check needs the whole tree). Measured, noisy;
  recorded in `docs/dev/diagnosis/wiki-relevance-cited-scripts.md`.
- **New: transitive wiki relevance is not modelled.** `docs/dev/perf/PERFORMANCE_HISTORY.md`
  (wiki-cited) mentions `scripts/perf_baseline.py`; the wiki does not, so it stays irrelevant.
  Deliberate; recorded under `## Deferred` in the blast-radius dossier.

---

## Recurrences observed this session → guardrail authored

1. **A hand-maintained classification list rotted** (C-10's "rots in both directions" class; the
   list missed 20 cited files and kept 2 never-cited ones). Recognized as a recurrence of the
   class item 35 / the 2026-07 relevance branch already fought at the top level.
   - **Mechanism, fails closed:** `tests/test_wiki_relevance_classification.py::test_relevant_overrides_equal_wiki_cited_mixed_files`
     — an exact-set test against a derivation from the wiki, run in the gate and CI.
2. **An unsourced claim became a premise** (C-12 class). The 2026-07 diagnosis said the two stale
   overrides were "genuinely cited"; `git log -S` shows no wiki page ever cited them. The item's
   own count (9) came from a grep narrower than the cite forms in use (20).
   - **Mechanism:** the same derived-set test now resolves every cite form, so the list's claim is
     checked rather than asserted. For counts written in item text, **no mechanism** (prose rule:
     re-derive, never copy) — **unenforced**.
3. **The witness paused a Write while a batched reader ran** (item 143, now **seven** instances,
   and the first that was not harmless). A background-task notification re-armed the witness —
   a new trigger shape — and its PAUSE refused the `## Observed` Edit while the batched
   `git commit` ran. Commit `6238fe8` cited evidence its tree did not hold; `dad9101` fixed it.
   - **No mechanism on this branch** (outside item 153's scope). **Surfaced to the owner**, who
     put item 143 into the next branch's group. Recorded on item 143.
4. **A UX test needed a CI retry** (a first sighting of this test, but a member of the known
   UX-flake class, epic 19). **Mechanism, fails closed, already existed and worked:**
   `scripts/ci_wait.py` exit 3 stopped the merge. The flake itself is filed as item 155 with its
   observed artifact; no fix on this branch (out of scope).
5. **Subagent / tool reports carrying facts:** none used this session (no subagents dispatched).

---

## What this branch should build

`fix/python-direct-hooks-plan-gate`, items **152, 111, 154 and 143** only — the owner's group pick (2026-10-06), item 40's
drawdown direction, and each item's file under `docs/dev/work/items/`.

1. **C-7 instrument first, for item 154** (the only one whose cause is unverified). Reproduce
   "approve on main → checkout → rebase → Edit" in a throwaway worktree (memory
   `reference-hook-manual-testing`). Control point from this session, recorded on item 154:
   approve on main → `checkout -b` with **no rebase** → Edit did **not** retire the approval.
   Write `docs/dev/diagnosis/python-direct-hooks-plan-gate.md` with `## Observed` before any
   production edit. Also measure item 111's baseline (fast path ~2 s, retire 8–21 s on
   2026-09-22) **before** changing anything, so the after-figure has a before.
2. **Item 152: Python-direct hooks.** Every `.claude/settings.json` hook entry calls the Python
   adapter directly, with no `hooks/*.sh` wrapper; plus a test that fails if a settings hook
   command invokes a `.sh` file or a shell interpreter; plus the warn-only `SessionStart` shell
   probe. **Unverified, check first:** how the hook runner resolves `python` vs `python3` per
   platform (item 152 "Before building").
3. **Item 111: port the plan-gate hooks** (`check-plan-approved.sh` and siblings — real logic,
   not wrappers) into Python, so the fast path stops forking. Re-measure; item 111 may close with
   152 per its own text.
4. **Item 143: the fail-closed half.** Item 143's candidate 1 — `ExitPlanMode`'s PreToolUse
   refuses when the plan file is older than the session's latest `Write` attempt on it — covers
   the high-stakes half. The general "batched reader" half cannot be blocked by a per-call hook;
   if no mechanism is possible, say so to the owner (C-11), don't paper over it.
5. **C-10, and the guard will enforce it.** `.claude/settings.json`, `hooks/` and the enforcement
   adapters are consumed by `CLAUDE.md`'s hook list, `docs/dev/tooling.md`,
   `docs/governance/enforcement.md`, `tests/test_enforcement_coverage.py`,
   `tests/test_enforcement_core.py::TestBashDispatcher` and `.githooks/` (item 152's own list — a
   snapshot). **Re-derive it yourself**, grep-complete, into
   `docs/dev/blast-radius/python-direct-hooks-plan-gate.md` before the first edit.

Scope is bounded to items 152, 111, 154 and 143 as filed in `docs/dev/work/items/`. Do not expand beyond it.

---

## First move

Create branch `fix/python-direct-hooks-plan-gate` off `main`, write a plan
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
