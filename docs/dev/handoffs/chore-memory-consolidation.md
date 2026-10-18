<!-- provenance: schema=1 session=f3b624bf-6d9e-4336-9278-d4b4d5441e47 branch=chore/memory-consolidation commit=e29db6a actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-18 -->

# Agent handoff — item 7 memory consolidation done to the owner's decisions (85 memory files deleted, 16 trimmed, 12 merged, `MEMORY.md` rebuilt); new `docs/dev/engineering-recipes.md`; items 176 and 177 filed; branch `chore/memory-consolidation` → owner's next pick (items 7, 137, 175, 176 and 177 stay open or deferred)

**Branch to create:** none chosen. The owner picks the next item. The candidates are under "What this branch should build"; the
order there is a recommendation, not a decision. Do not start one unprompted.
**Base branch:** `main`

> **This session (`f3b624bf`) took item 7 after the owner picked it from the previous handoff** (`model-pricing-rates.md`,
> pointer `@ main (de47905)`; the pointer first given to it, `model-55-eval-item.md @ dbc6f02`, was superseded: session
> `8603d643` had already consumed it, and the owner chose the newer one). It changed **no product code and no prompt**: the repo
> changes are docs, three small registry edits, one work-item board regeneration, and a consumer dossier for the one gated edit.
> It made **no paid API call**; the only network use was read-only `gh api` calls (Dependabot alerts).
> - **Memory (outside the repo, not committed):** 266 entries → 183; `.md` bytes 1,034,153 → 648,462; `MEMORY.md` 20,458 → 16,427
>   bytes; broken `[[links]]` 31 → 0. **85 files deleted** (16 batch A, 69 batch B), **16 trimmed**, **12 merged additively** (merged files
>   kept), 2 new memories written, 0 deleted for inaccuracy. The undo is the sibling directory `memory-backup-2026-10-18` (266 entries,
>   outside the repo); **the owner should delete it when satisfied**. Full record, with the per-file verdicts: item 7's `## Updates`.
> - **How it was checked:** seventeen independent agents, each allowed to write one output file (two Explore passes, five sweep agents, five adversarial
>   refuters, two accuracy auditors, three planners). Every quote an agent cited from a repo file was verified mechanically against that file (about
>   1,140: 844 from the refuters, 161 from the auditors, 123 from the trim planners, 10 from the merge preparer; 0 fabricated). About 36 auditor
>   evidence rows were command output, not file text, so a quote checker cannot parse them; I re-ran the three that mattered by hand. The
>   orchestrator also read every fact-to-quote pair for the 78 batch-B files. Quotes prove the text exists, not that it supports the fact, so that
>   read was the check that mattered. Agents' own tally lines were wrong twice; per-row labels were used.
> - **Found false in memory and fixed or removed:** e.g. `agent_id` "never observed", "exactly 8 egress files", a `hooks/` directory
>   that no longer exists, a note saying the docs-site build catches a broken diagram when it cannot.
> - **A possible product issue, NOT verified:** `hardening.py:1992-1993` says the app's server is not threaded (Werkzeug defaults to
>   `threaded=False`) and item 25 rests on it; the installed Flask 3.1.3's `run()` does `options.setdefault("threaded", True)`, and
>   `app.py:494` passes no `threaded`. **I only read Flask's source; I did not run two overlapping requests.** Filed as item 177 point 1;
>   reproduce first (charter C-7), then fix whichever of the docstring, item 25 and the dossier is wrong.
> - **New repo doc:** `docs/dev/engineering-recipes.md` (add or move a route; keep the typing and docstring floors green), registered,
>   indexed from `docs/dev/README.md`, classified in `scripts/wiki_relevance.py` (consumer dossier:
>   `docs/dev/blast-radius/chore-memory-consolidation.md`).
> - **Gate:** `python -m scripts.gate --result` read `PASSED on this tree -- exit 0, failed step None, finished 2026-10-18T14:12:02-0700, HEAD e29db6a` (non-UX 3581 passed, 8 skipped; ux 189 passed, 2 xpassed; a search of the log for `RERUN` found none). **This is the second run:** the first (at `58bd7ef`) was stopped by the harness under memory pressure at about 62% of the non-UX tier (`[gw0] node down: Not properly terminated`), recorded in item 7; it was not a code failure (the named test passes alone) and not a pass. The commit that adds this file comes after the gate and is docs only.
> - **Branch state:** commits on `chore/memory-consolidation` ahead of `main` (`de47905`), then the commit that adds this file.
>   **Nothing is pushed and no PR exists**; the push and every later step need the owner's confirmation. Check `gh pr list` and
>   `git branch -a` first.
> - **Model note:** this session began on Opus 5.5 (the plan) and ran on Sonnet 5.5; the consumed event and this file's stamp name
>   `claude-sonnet-5-5`.
> - **Not verified:** that the agents' per-fact cites for batch A are all correct (the first Explore pass's cites plus a sample; batch A
>   was not put through the adversarial read); the sweep's STALE flags on kept files (reported, not applied); the full-gate wall clock.

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

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging (owner's 2026-10-02 sequence on item 40).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- Everything through `fix/model-pricing-rates` ✓ (#185, merge `de47905`, MERGED): item 174, the price table. Record: `docs/dev/handoffs/model-pricing-rates.md`.
- **`chore/memory-consolidation`** ← this branch: item 7. Memory deletes, trims and merges (outside the repo), `docs/dev/engineering-recipes.md`,
  items 176 and 177, the wiki-log verified-no-edit entry. Not pushed.
- **Next: the owner's pick.** Item 175 (call provenance) before any item 137 model swap; item 177 point 1 (the threaded-server contradiction,
  instrument first); item 176 (the deferred fold-ins); the six remaining item 7 decisions below; item 145's branch 2 and 3 are not started; item 171
  waits on four owner answers.

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and on the owner's alpha approval.
**Do not build item 171's workflow before the owner answers its four questions.** **Do not start item 145's branch 2 or 3.** **Do not run a
paid eval or capture without the owner's spend approval** (includes item 137's candidate A/B; none is approved). **Do not delete any
further memory file** without the owner's approval of the specific rows (item 7). **Do not "fix" the threaded-server question by editing
`hardening.py` or item 25 before reproducing it.**

---

## What just landed on `main`

**Nothing from this branch is on `main`.** `main` is at `de47905` (PR #185, item 174: `MODEL_PRICING` now matches the pricing page for Sonnet 5 and
Haiku 4.5). Before it: #184 (`dbc6f02`, items 173 and 174 filed), #183 (`e490683`, item 140b), #182 (`7807c81`, the capture stall).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 23 / 10 ceiling -- OVER"** (21 items and the 2 open epics).
**Changes from the previous handoff's 19 items:** item 174 closed earlier; this branch **opened item 7** (it was deferred), **filed item 177** (open)
and **filed item 176** (deferred); the item 7 and item 169 files gained `## Updates` blocks. The owner's drawdown direction stands: down to 0 if
possible, before alpha staging. Still more than twice the ~8 to 10 reduction-sprint threshold. Owner-decision items are marked *(owner)*. The lists
below are **generated from the item files at this commit** (`structural_errors()` in `scripts/work_items.py`, run with `python -X utf8`; not
retyped). Generator output: `open_all=23 counts={'watching': 47, 'blocked': 5, 'deferred': 9, 'open': 21} epics_not_closed=3 closed_items_and_epics=92`.

`## Open` (21):
- **7** *(owner)*: Memory consolidation: 85 deleted, 16 trimmed, 12 merged, index rebuilt; further deletions await owner approval.
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
- **137**: Review pinned models and call settings, now including the Claude 5.5 candidate evaluation (absorbs item 173).
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Fix built, measured, screenshots recaptured; score drop not specific to the change; carrier hypothesis never reproduced.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **171** *(owner)*: 16 Dependabot PRs open, oldest 2026-07-13; nothing acts on green ones. Design the per-class merge policy.
- **175**: The call log keeps the model id asked for, not the answering version, settings or request id; judge calls log none.
- **177**: Sweep found a threaded-server contradiction, a wrong gate.py item path, README min_* claims and stale counts.

`## Blocked` (5):
- **3** *(owner)*: Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false. [blocked on: owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision]
- **5**: First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed. [blocked on: the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json]
- **8** *(owner)*: Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code. [depends on: 6] [blocked on: evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run]
- **10** *(owner)*: Bump pyproject.toml to 1.1.0, cut CHANGELOG [Unreleased] to [1.1.0], tag - last step, on the owner's go. [depends on: 3, 6, 7, 9, 19] [blocked on: everything else landing first, plus the owner's explicit go]
- **97** *(owner)*: Orchestration may belong outside the project; sartor's job becomes keeping ARC/CHECKLIST/ledger/BOARD in sync. [blocked on: owner design decision — this is a strategic redirect the owner raised; the tool choice and the scope of any sync layer are the owner's]

`## Deferred` (9):
- **4** *(owner)*: Avatar citations link out to GitHub; an in-app viewer needs a new route + sanitizer, deliberately not built yet. [blocked on: no friction signal yet; owner reaffirmed 2026-07-23, build only if friction warrants]
- **24** *(owner)*: In-app preview is single-column (python-docx limit); multi-column/paging fidelity needs a spike, never scheduled. [blocked on: not yet scheduled; needs a product-priority decision on investing in the spike before any code work starts]
- **25** *(owner)*: Single-threaded app.run() freezes the app during a diagnostics run; making it threaded is an owner-gated C-1 call. [blocked on: owner governance call not yet made; touches the C-1-sensitive loopback-bind area, deliberately kept out of the diagnostics epic and every branch since]
- **41** *(owner)*: Local lexicons (design, SWE, business, startup) so Compose drafting uses the JD domain's language and conventions. [blocked on: post-1.1.0 - owner scheduled this for 1.1.x investigation, not the Final March]
- **42** *(owner)*: Investigate dotx/mht as import formats and lock a small set of bullet-proof ATS templates with exact-preview fidelity. [blocked on: post-1.1.0 - owner scheduled a template epic for a 1.1.x sprint]
- **43** *(owner)*: v1.1.0 ships an approved-fonts list of Arial, Calibri, Georgia (sprint B2); verified additions considered later. [blocked on: post-1.1.0 - additions only after per-font ATS verification, owner-gated]
- **113** *(owner)*: 18 console UX findings outside Epic C (6 major, 12 minor) await triage; UX-22 is item 112; UX-24 joined C1b. [blocked on: owner triage after Epic C lands: which findings become items, which fold into a later epic, which are dropped]
- **114**: bench.md already summarizes error rows generically; naming error_message/error_type explicitly is a nice-to-have. [blocked on: low value until logs/llm_calls.jsonl accumulates real status="error" rows with the new fields; revisit once there is real data to summarize]
- **176** *(owner)*: 44 memory files hold facts with no repo home, plus leftovers of 69 deleted ones; fold them into docs. [blocked on: owner chose on 2026-10-18 to defer these 44 fold-ins to a later session; nothing here is started]

`## Watching` (47):
- **2**: ~107-file wiki + reviews-archive wordmark cleanup deliberately deferred to opportunistic fold-in, not a branch.
- **16** *(owner)*: No jd.txt/expected.json under evals/fixtures/real/ anywhere in this project - --suite real exits 1, zero LLM spend.
- **18**: Same fixture, 68s apart: tone 3.2->2.1, clarification_quality 3.2->3.8, composite 4.06->3.89 - n=2, uncharacterized.
- **23** *(owner)*: PX-52, WATCH: extract prompts.py/client.py when prompt work next opens the file, not a standalone refactor.
- **30**: test_keyboard_reorder_persists_and_reset_reverts: one Playwright 30s timeout; single sample.
- **34**: install_llm_stubs patches _get_client on 4 blueprints but not the corpus ones - real API risk if ever hit.
- **46**: Control assertion (`assert naive`) is itself a timing race; a quiet runner completes write_text between reader polls.
- **47**: Item 44's fix landed in one shared helper; other tests reasoning about spy events after a clear were not audited.
- **48**: ux job took 14m49s on PR #102 vs ~5m1s on PR #100 — zero reruns, so not a flake; the runtime is the anomaly.
- **49**: A suite run leaves personas/bundled/tmp*.html behind; `git add -A` swept one into a commit before it was caught.
- **51**: flake_rates.py is an instrument, not a gate; report --check against a committed budget is a named, unbuilt successor.
- **52** *(owner)*: The tree that lands is never the tree the gate examined; class study documents 6 instances + candidate mechanisms.
- **53**: Quote-parity tracker ignores heredoc semantics; prose quotes in a commit-message heredoc caused a live false-BLOCK.
- **56** *(owner)*: On main the reconciler dies mid-function: empty archive dir, all three pointers survive, stale approval stays live.
- **57**: 400 on a context file that exists: JSONDecodeError/OSError on read. Settle-hole dossier's O-3 had zero non-2xx.
- **58** *(owner)*: Handoff amended after its generated row; fingerprint and stamp both drift, and the next session hits a C-9 block.
- **59** *(owner)*: A role card offers two summary editors: the legacy Experience.summary cache and the canonical variants section.
- **60**: Count reports live roles; the empty hint branches on total rows, so they disagree when every role is retired.
- **61**: Stopping the chain at N-1 yields today's full schema, so the guard skips and the ADD path goes unexercised.
- **62**: Two gate runs over the same code gave `1 xfailed, 1 xpassed` then `2 xfailed` — the xfail is nondeterministic.
- **63** *(owner)*: `_setBusy` adds `body.cb-busy`, but no rule matches it — the busy banner is cosmetic, not blocking.
- **64**: A2 guarded a confirmed mechanism whose reachability was never established — the question, not a bug claim.
- **65** *(owner)*: Drift = files-since-checkpoint assumes periodic catch-up passes; under a per-branch workflow it self-perpetuates.
- **67** *(owner)*: The rail is the gate; the server fallback is the floor. Filed so the surface is tracked, not assumed closed.
- **68** *(owner)*: One lock message covers two refusal causes; telling them apart needs the server to say WHY, a payload change.
- **69**: Prompt-context bias only (no rendered-resume leak) -- lower severity than what A3 fixed, but the same root class.
- **70**: Every current blueprint uses the matched ImportFrom form; an attribute-access blueprint would escape the gate.
- **71** *(owner)*: Pointer + aggregated data for a future orchestrated-epic-execution design pass -- not a proposal.
- **72** *(owner)*: At-a-glance pending-review discoverability regressed -- count is still reachable in the detail modal, not on the row.
- **73** *(owner)*: open_detail() moved from DOM click to page.evaluate; four files still pass but now cover a direct-JS path, not a click.
- **74**: refreshApplications() (1 candidate) replaced by refreshPipeline() (whole roster) at 7 sites -- disclosed trade, no N+1.
- **76** *(owner)*: declared is checked for presence only, never as a date -- the staleness exemption never expires on its own.
- **77**: pytest -m ux is documented LLM-free; nothing gates that each LLM-reachable UX test calls install_llm_stubs.
- **78** *(owner)*: One alice/draft_summary billed row predates the fixed test and doesn't match its token shape -- source unresolved.
- **79**: ci_wait's verdict was right twice but delivery crashed on encoding + TLS faults, both requiring a manual re-run.
- **80**: Dependabot merges staled Epic A's open PR under strict:true, costing an update-branch cycle plus ~6 min CI.
- **81** *(owner)*: drift_count() has no change-status filter -- a deletion inflates drift exactly like new content needing ingestion.
- **82** *(owner)*: open_count sums ALL items; the other three counts sum top-level only -- one header line, two populations, undisclosed.
- **83** *(owner)*: F1/F2/F3/F5/F11/F13 each independently got a different piece of backgrounding wrong; codify the pattern once.
- **84** *(owner)*: implementer->refuter->judge->closer as a Workflow script, N=1; provably >= robust as today's process per the design.
- **85**: trigger is 'unknown' in all 52 ledger rows; the code round-trips it correctly when present -- the payload may lack it.
- **88**: The 3 preview routes + _render_pdf_from_json pass the refreshed companion; today only a manual grep verifies it.
- **90**: A first-field-less entry emits ambiguous markdown that misroutes on re-parse; the fix spans three entry kinds.
- **91** *(owner)*: Inconsistent GPA rendering between two bundled personas; no record of whether Spacious omits it deliberately.
- **92**: Bullets bypass the run-proto path, so no captured template typography (size/bold/font) applies to them.
- **168**: The auditor moved to Sonnet 5 on a measured miss rate, but its own catch rate and cost per pass are unmeasured.
- **169**: Only a <task-notification> prompt is exempt from arming; other injected turns, not yet observed, still arm it.

`## Epics` not closed (3):
- **19** (open): UX-suite flakiness solution sprint - mode-C residual + newly observed instances
- **36** (open): Final March epic A - main-app function + UX
- **40** (blocked) *(owner)*: Final March epic E - the public v1.1.0 cut

### Decisions the owner owes (collected; each is also in the item it belongs to)

- **Item 7, six remaining decisions (new, the first four are deletions that were NOT approved):** (1) delete the **12 merged files** whose text now sits in
  survivors; (2) delete the **15 draft-list FOLD files** (the app-factory, seam and lint-ratchet records; the surviving how-to is `docs/dev/engineering-recipes.md`);
  (3) the **2 PARTIAL draft rows** (`excellence-walk-llm-wiki`, `project-v110-close-out-sequence`), each with one unhomed fact; (4) batches C and D stay (24 files,
  corrected where wrong); (5) whether to run a next pass applying the sweep's **STALE flags** to the other kept files (reported, not applied); (6) close
  item 7 (needs a falsifiable `verified_by` or an owner-named `closure_exception`) and delete the `memory-backup-2026-10-18` directory.
- **Item 176 (deferred by the owner):** the 44 fold-ins and the 26 unhomed leftover lines. Nothing started.
- **Item 177 (open, agent-workable):** eleven repo defects and gaps; **point 1 is the threaded-server contradiction** and needs a reproduction first.
- **Item 175, the design choices (carried):** how judge calls are recorded (eval record, or `llm_calls.jsonl` rows with their own `call` kind, which changes
  what eval `cost_usd` means) and whether to fix or only record the `max_tokens` retry drift. Both for that branch's plan. No code is written.
- **Item 137 (carries the 5.5 evaluation), spend approval for the candidate A/B (carried):** Sonnet 5.5 for the heavy calls and Haiku 5.5 for the structured calls,
  one swap per branch, judge held fixed, N per arm chosen in advance. The price table is correct for the two live pins (item 174); **no spend is approved.**
- **Item 137, the `thinking` policy per model (carried):** Sonnet 5.5 must use `between_tools` (`disabled` is a `400`, item 173's Updates). For Haiku 5.5, hold today's
  behavior with an explicit `disabled`, or adopt `adaptive` as its own eval-gated change.
- **Item 137, how soon to move off Haiku 4.5 (carried):** Active but past its earliest retirement date, and the eval judge too; the owner's call.
- **Item 140, close or keep open (carried):** every build and measurement part is done; the original `b180` carrier (hypothesis B) has not reproduced in 31 letters
  and the guard covers it regardless. Needs `verified_by` or a `closure_exception`; not closed. Suggested wording: *"Hypothesis B (the `b180` letter carrier) never
  reproduced in 31 letters; the runtime guard hard-errors a handle in `cover_letter_content`; the score drop is not specific to the change
  (`docs/dev/diagnosis/ds-junior-score-drop.md`)."*
- **The app-side race (carried, not fixed):** a Save-and-continue during an in-flight arrival draft can lock Generate behind "You changed your composition after
  approving it". Confirmed at route level; not observed at realistic timing. `TestDraftLandingAfterTheFreeze` pins today's behavior; C-10 territory.
- **Item 171, Q1 to Q4 (carried):** auto-merge for the auto classes; whether the 2026-08-07 docs-site alert carve-out stands; the four Actions majors before the tag;
  a merge queue or the squared CI cost under `strict: true`.
- **The `EnterWorktree` question (carried):** may agents use the harness worktree location inside the repo? The scans were fixed by #180.
- **Item 145, branch 2's start (carried):** the C-2 wording, the PEP 668 fallback, whether bare `sartor` runs `up`, whether `sartor` is free on PyPI, separate native
  and container data. End-to-end waits on item 3.
- **Item 10 and the alpha (carried):** item 3 (GitHub toggles), item 7 (above), and the owner's alpha approval.
- **Whether to file a gate for the per-branch wiki obligation (carried, C-11):** possible, not built; it changes `scripts/gate.py`, a C-10 gated surface.
- **The *(owner)* items in `## Open`:** see the generated list above.

### Declared, not filed — carried, **not re-verified this session**

The full set is in `docs/dev/handoffs/gate-skips-linked-worktrees.md` and, behind it, `docs/dev/handoffs/dependabot-triage-item.md` and
`docs/dev/handoffs/data-root.md` "Carried from earlier handoffs" (about 40 bullets). Not re-copied, to avoid a second hand-maintained copy that rots. The ones
most likely to matter next:

- The simultaneous-launch race: the one open limit of the single-instance guard (item 146).
- `maintainer-lane.md` step 2 gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.
- `capture-smoke.yml` failed its last three monthly schedules (2026-08-01, 09-01, 10-01); cause not examined, no item mentions it. `release.yml` and `docker.yml`
  have no workflow runs at all (item 171).
- A stray empty directory `.claude/worktrees/interesting-engelbart-27c56d` (not a registered worktree). Not touched.
- A checkpoint-advancing wiki pass is owed: `wiki_freshness` read 67 files changed since the last ingest (under the 75 block threshold) after this branch's
  commits. This branch's wiki-relevance result is in `docs/wiki/log.md` (verified no-edit).
- A git stash `stash@{0}` ("On feat/run-detail-modal: epic-c C2 staged implementation … parked for C1c") belongs to another session. Not touched.

### New this session, declared (observed unless marked)

- **The memory directory is outside git.** All memory changes (deletes, trims, merges, two new notes, the rebuilt index) are undone only from
  `memory-backup-2026-10-18`. Nothing about them is in a commit except the record in item 7 and items 176 and 177.
- **Scratch tools, not committed (session scratchpad):** `memcheck.py` (integrity and link repair), `verify_quotes.py` (checks that an agent's
  cited quote appears in the cited file), the batch apply scripts, and the planner JSONL files. If the quote-verifier is wanted as a reusable tool,
  committing it under `scripts/` is an option; **not done** (scope).
- **Several agents (at least six) wrote helper scripts into the scratchpad** despite a one-output-file instruction (one deleted its own afterwards); the scripts are harmless and not in the repo.
- **Repo records still cite deleted memory files by stem** (about two dozen: dated handoffs, diagnosis files, work-item updates and `RELEASE_CHECKLIST.md`); they were
  left as frozen records, so they now name memory files that no longer exist.
- **Item 174's text still says `hardening.py` is a C-10 gated surface** (`docs/dev/work/items/0174-...md:80`); it is not. Recorded in item 177 point 4.
- **Past figures:** unchanged from the previous handoff (cost figures computed at the old model rates are dated records).
- **Process.** The ledger lists were generated from `structural_errors()` with `python -X utf8`. The gate ran once in the background from Git Bash with output
  redirected and the real exit code echoed. No dev server or other long-lived process was started; the sweep and audit agents were read-only.

---

## Recurrences observed this session → guardrail authored

1. **The interrogative witness paused `Write`/`Edit` calls after peer hand-backs arrived** (five times this session, plus two by-design pauses after the
   owner's own messages). Recognized as a recurrence of item 169 and the memory `reference-subagent-pretooluse-agent-id`. **No mechanism authored on
   this branch** (the witness is a fail-open one-shot by design; reopening is the owner's pick). Recorded as an observation in item 169's `## Updates`. **Unenforced.**
2. **`block-doubled-backslash` stopped two of my commands** (a heredoc with doubled backslashes). **Mechanism exists and held**; I took its way through (the Write tool,
   run by path). Nothing to add.
3. **Agents' own tally lines were wrong twice** (the first Explore pass said "15 safe, 3 partial" over 18 rows labelled 16 and 2; a refuter said "11 deletes" while
   listing 12). Recognized as the class in the memory `feedback-verify-rollup-claims-against-source`. **Mechanism for this session only:** I counted the per-row labels
   and ran a script over structured output. **Nothing in the repo enforces it** and I cannot see one that could: an agent's prose summary is not machine-checked
   data. Written into the new memory `feedback-bad-memory-is-worse-than-none`. **Unenforced.**
4. **A hand-maintained status list rotted again: the `MEMORY.md` index** carried "BUILT", "RESOLVED" and dated claims that had gone false (the C-10 "hand
   lists rot" class). I rebuilt it to state no current state. **No mechanism is possible in the repo**: the index is outside it, so no committed test can fail when
   it rots. **Surfaced to the owner here. Unenforced.**
5. **Memory files stating false facts (15 of the 24 audited, plus several in files marked for deletion)** and **the memory directory growing until a hook flagged it**
   (the previous handoff's row 7, now closed out by this work). Same limit as row 4: outside the repo, so no gate. The owner's principle is saved as
   `feedback-bad-memory-is-worse-than-none`. **Unenforced.**
6. **A wrong claim about what is gated survived in a work item** (item 174, line 80), after a memory already warned about exactly that. Recognized as the
   class in `reference-consumer-enumeration-gate-c10` (now deleted; its content is in `scripts/enforcement/blast_radius.py:198-209` and
   `docs/dev/diagnosis/model-pricing-rates.md:65`). **No mechanism authored** (a hook cannot judge a prose claim); filed as item 177 point 4, which is a record and not a
   mechanism. **Unenforced.**

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses the next item; this handoff does not pick one. The list is the closing agent's **recommendation for
order, not a decision.** Do not expand beyond what the owner names.

1. **Land this branch first (if the owner agrees).** Check `gh pr list` and `git branch -a`. Then, in order: ask the owner to confirm what becomes public (the
   branch is docs, three registry edits and a board regeneration; **state any commits already on local `main` that the remote lacks**), `git push -u origin
   chore/memory-consolidation`, open the PR, `python -m scripts.ci_wait <n>` (exit 0 only; 3 means green-after-retries, stop and look), `gh pr merge <n> --merge`,
   `git checkout main && git pull --ff-only`, regenerate the pointer with `print_handoff_pointer.py` and verify it with `check_handoff_pointer.py`, then
   `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Item 177 point 1: is the production server threaded?** The one item here with possible product impact. Instrument first (C-7): start the app, issue two
   overlapping requests (one slow), record the result; only then decide what to correct (`hardening.py:1992`, item 25's premise, or the dossier). Then the ten
   one-line corrections in item 177.
3. **Item 175, call provenance (the owner's stated requirement; carried).** First commit is the observation: one real call, read the logged row, show the missing
   fields. Then the design in the item. It makes any later item 137 A/B interpretable.
4. **The remaining item 7 decisions** (the owner's list above), then closing item 7.
5. **Item 176**, when the owner wants the 44 fold-ins done (re-verify each fact before writing it).
6. **Item 137 after 175:** the `thinking` policy, the 5.5 keys and Haiku 5.5's tiers in `compute_call_cost`, then the candidate A/B (**needs a new, explicit spend
   approval; none is given**).
7. **Carried, in the previous order:** item 140's closure; the wiki-obligation gate (C-11); the app-side race; item 171 after Q1 to Q4; `capture-smoke.yml`'s three
   failed scheduled runs; a checkpoint-advancing wiki pass; item 145's branch 2; the open product bugs 130, 105, 131, 107, 134, 139, 98, 99; the *(owner)* items.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path: `docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then check `gh pr list` and
`git branch -a` for this branch's PR and merge state (this file does not say). Then ask which item to take. Create that branch off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not code first.**

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
