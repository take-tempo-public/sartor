<!-- provenance: schema=1 session=5920836d-6147-426a-b384-1b778d423cf3 branch=fix/retired-roles-a3-prompt commit=7a6d8e7 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-11 -->

# Handoff — item 75 fixed; §16.7 RESOLVED: the N=1 baseline build (item 84) is the authorized next branch

> **The single most important thing this handoff carries forward:** the owner answered
> §16.7 of `docs/dev/epic-a-chain-design-corrections.md` this session — **(1) pursue the
> C+drift design; (2) the N=1 baseline build is authorized** (item 84, now `open`,
> decision recorded in its Updates). Decision point (3) is untouched: widening N past 1,
> retiring/merging `AGENT_HANDOFF_TEMPLATE.md`, the ledger extension (§16.5.2.2), and any
> Epic B chain under the old §11 envelope each remain their own later, owner-gated
> decisions. This branch's own work — item 75's fix, C-7 reproduction first — is done.

**Branch to create:** `feat/n1-baseline-pipeline` (branch off `main`) — item 84, the
authorized N=1 build. Building the pipeline is authorized; **running** it on a real
sprint is its own later, explicitly opted-into step (§16.5.2.3).
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

**Epic-specific reading, on top of the numbered list above:**
`docs/dev/epic-a-chain-design-corrections.md` §16 in full (the C+drift design the next
branch builds the N=1 baseline of — §16.4 structure, §16.5 staged rollout + audit trail,
§16.7 with the owner's decision now recorded in item 84), plus item 84's own file
(`docs/dev/work/items/0084-build-n1-baseline-pipeline.md`).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics, A→E,
strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first (A–C), docs
after (D), release last (E). This branch (item 75's fix) and the next (item 84's build)
are **not march epics** — governance-interval / infrastructure work between Epic A and
Epic B.
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B. Epic
B's first code sprint remains un-started; its execution mode is downstream of the N=1
baseline evidence, per the owner's §16.7 answer — do not resume any chain under the old
§11 envelope.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`docs/post-epic-a-findings`~~ ✓ — items 77–80 (PR #121).
- ~~`docs/pre-epic-b-review`~~ ✓ — the robustness design pass (PR #122, `7a6d8e7`).
- ~~**This branch (`fix/retired-roles-a3-prompt`)**~~ — item 75's fix. Done.
- `feat/n1-baseline-pipeline` ← next: item 84, the authorized N=1 build.
- Epic B (`epic/b-render-ats`, board 37) ← after that, owner-gated start.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on the next branch:** any Epic B code; *running* the built
pipeline on a real sprint (build-only is what §16.7's answer authorized); widening N past
1; editing `AGENT_HANDOFF_TEMPLATE.md` (§16.5.1 — its own later, owner-gated decision,
made only once N=1 evidence exists); the watching-bucket triage (recommended, but its own
session if the owner schedules it).

---

## What just landed on `main`

Nothing merged yet from this branch at writing time — this handoff is written pre-PR, per
the close-out checklist. This branch (`fix/retired-roles-a3-prompt`, item 75, one working
commit expected) contains: `blueprints/applications.py` —
`_build_experience_summary_targets` takes a live `active_exp_ids` set and drops
frozen-snapshot roles not in it; `evals/corpus_drafting_probe.py` — the probe stages the
identical live intersection (found as a second consumer by the gate's mypy step, not the
first grep — see the dossier's C-10 note); `tests/test_draft_experience_summaries.py` —
`test_retired_role_never_reaches_the_draft_prompt`, written and observed failing on HEAD
`7a6d8e7` BEFORE the fix ("retired role 2 reached the draft targets: [1, 2]");
`docs/dev/diagnosis/retired-roles-a3-prompt.md` — the C-7 dossier; item 75 closed with
`verified_by`; item 84 `blocked` → `open` with the §16.7 decision recorded; CHANGELOG +
BOARD regenerated; wiki `log.md` verified-no-edit entry (pages citing the changed symbols
checked by reading, none stale). `main` itself is at `7a6d8e7` (PR #122).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m scripts.work_items
board --write`). Reproduced from the board as regenerated at this branch's close (85
files, `check` OK). Item 82's caveat stands: the header's counts mix two populations
(all-items vs top-level) — re-derive, don't trust either number blindly.

**Open (top-level 2; header says 5 incl. epic-nested 9/19/36):** **50** (C-7/C-10
enforced by Claude Code hooks only — prose binds other agents), **84** (**the N=1
baseline build — now `open`, owner-authorized this session; the next branch**). Epic-
nested: **9** (visual-assets refresh, under epic 39), **19** (UX-flake epic close-out),
**36** (Epic A — merged; its item `status` still not flipped `closed`, worth the
follow-up check the last handoff already flagged).

**Blocked (3):** **3** ([HUMAN] GitHub toggles), **5** (grounding-score persistence gap),
**8** (Compose rewrite latitude, evidence-gated on the PX-39 run).

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — unchanged, all owner-gated or
post-1.1.0; see `BOARD.md` for one-line detail.

**Watching (40, down from 41 — this branch closed item 75):** **2, 16, 18, 23, 46, 47,
48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 85** (41 listed — the top-level/nested
population caveat above applies; item 57 is epic-nested).

- **The watching bucket shrank for the first time in its recorded history** (16 → 22 →
  25 → 28 → 36 → 37 → 41 → **40**) — by exactly one, because this branch existed to fix
  one watching item. The triage session two consecutive governance branches recommended
  is still owed; one-per-branch is not a reduction strategy.
- **Nothing new filed this session** — no new defects surfaced; the one new observation
  (the stale-plan-stamp retiring MID-branch rather than at the first production edit)
  landed in the memory that already tracks that class, and item 56 already tracks the
  hook's unproven mechanism.

---

## Recurrences observed this session → guardrail authored

**Two recurrences recognized. No new mechanism authored — both landed in existing
tracking, and the reason each time is stated plainly per C-11.**

1. **The gate's exit code masked by a pipe (`| tail -30`) — a RECURRENCE of the
   documented `| tee` trap** (memory `reference-background-bash-kill-ceiling`, 2026-07-21
   entry): the background notification said exit 0 while the log said `gate: FAILED at
   mypy (exit 1)`. Recognized immediately because the log tail carried the FAILED line;
   the second gate run used the documented redirect form (`> log 2>&1; echo "GATE EXIT:
   $?"`). **No mechanism authored:** the failure is in agent shell-invocation habit, not
   in repo code — `scripts/gate.py` already prints an unambiguous terminal verdict line;
   a wrapper that forbids piping an arbitrary command is not buildable as a fail-closed
   repo gate. Recurrence appended to the memory's own trap entry; surfaced here.
2. **A consumer missed by a single-file grep — a RECURRENCE of C-10's core class** (the
   `loadComposition()` 9-more-sites case in `docs/dev/diagnosis/compose-unawaited-reloads.md`):
   the first enumeration grepped `blueprints/applications.py` alone and called it "one
   caller"; the gate's mypy step caught `evals/corpus_drafting_probe.py:168`. **No NEW
   mechanism authored:** the arity change meant mypy already failed closed here — that
   existing gate is the mechanism, and it ran. Its limit is stated in the dossier: mypy
   cannot catch a same-arity behavioral consumer, so the grep-complete discipline (C-10)
   remains the binding rule, and the whole-tree grep was run and recorded before the
   second edit. The helper is single-module-private; adding it to the
   `blast_radius.py` registry would gate every `applications.py` edit on a dossier —
   disproportionate for a two-consumer private helper; declined explicitly rather than
   silently.

---

## What this branch should build

<!-- This branch's own work is complete — see "What just landed" above. The NEXT branch builds: -->

1. **Item 84 — the N=1 baseline pipeline** (`feat/n1-baseline-pipeline`): implementer →
   Sonnet refuter → judge → closer for ONE ordinary sprint, as a Workflow script, per
   `docs/dev/epic-a-chain-design-corrections.md` §16.4 (structure) and §16.5 (staged
   rollout; the Workflow-native capability argument in §16.5.2.3 — `journal.jsonl` +
   `resumeFromRunId` — bears on HOW to build, and does not authorize running). Authorized
   by the owner's §16.7 decision, recorded in item 84's Updates (2026-08-11).
2. Scope boundary: build + its own tests/verification only. The provenance-ledger event
   extension (§16.5.2.2) is explicitly NOT authorized. Running the pipeline on a real
   sprint is a separate owner opt-in.

Scope is bounded to item 84 and §16.4–§16.5 of the corrections doc. Do not expand beyond
what is listed there.

---

## First move

1. If this handoff arrived via a pointer, run
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/retired-roles-a3-prompt.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A
   `blocked` result is your **first output** — STOP (charter C-9).
2. Read `docs/dev/epic-a-chain-design-corrections.md` §16 in full and item 84's file —
   the owner's authorization and its exact scope live there, not in this summary.
3. Create branch `feat/n1-baseline-pipeline` off `main`, write a plan at
   `~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do
   not code first.** (Expect the stale-plan-stamp flush: one blocked edit on the branch,
   then the EnterPlanMode → ExitPlanMode ceremony — see memory
   `reference-flush-stale-plan-stamp-on-branch-not-main`; it can also fire mid-branch.)

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
