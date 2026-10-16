<!-- provenance: schema=1 session=4308be07-40b0-46b2-81fa-e786f6d17f46 branch=chore/dependabot-triage-item commit=979f420 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-16 -->

# Agent handoff — items 171 (Dependabot merge policy) and 172 (gate scans linked worktrees) filed; docs-only branch `chore/dependabot-triage-item` → owner's next pick

**Branch to create:** none chosen. The owner picks the next item. The candidates, with an agent
recommendation (not a decision), are under "What this branch should build". Do not start one unprompted.
**Base branch:** `main`

> **This session was a read-only board review that turned into filing two work items and carrying the
> other agent's handoff forward. It changed no production code, no workflow and no test.** The branch holds
> three docs-only commits and is **not pushed and not merged**; the full gate has **not been run** on it.
> - **Board review (2026-10-16, `main` at `f01d29e` then `3a29b28`):** 19 open items plus 2 open epics
>   against a ceiling of 10 (board header "Open 21 / 10 ceiling -- OVER" with items 171 and 172 filed). The
>   count peaked at 43 on 2026-10-05 and fell to 19 by 2026-10-15; the board's Closed figure is 89 (items
>   and epics together). Item 10 (the 1.1.0 cut)
>   depends on 3, 6, 7, 9 and 19: 6 and 9 are closed, **3 and 7 are owner-gated, and epic 19 cannot close**
>   because its children 30 and 57 are `watching` and `SCHEMA.md` bars closing an epic while any child is
>   non-terminal. The handoff also says item 10 waits on the owner's alpha approval.
> - **Item 171** (`docs/dev/work/items/0171-dependabot-merge-policy-and-major-bumps.md`, owner-decided, open):
>   a design, not a build, for the 16 open Dependabot PRs (oldest 2026-07-13). It carries a per-class
>   policy table, a separate design for the four GitHub Actions majors, the cost of `strict: true`, and four
>   owner questions. **Two findings in it matter beyond Dependabot:** `release.yml` and `docker.yml` have
>   **no workflow runs at all** (`gh run list --workflow` returns nothing), so no PR check exercises them; and
>   `capture-smoke.yml` **failed its last three monthly schedules** (2026-08-01, 09-01, 10-01; latest run
>   `36858103525`), cause not examined, no item mentions it.
> - **Item 172** (`docs/dev/work/items/0172-gate-scans-linked-worktrees-under-claude.md`, agent-owned, open):
>   **this session caused it.** It used the harness's `EnterWorktree` so as not to disturb the other agent;
>   the worktree landed at `.claude/worktrees/dependabot-triage-item`, **inside** the repo, and per the other
>   agent's handoff it failed three whole-tree gate tests in the main checkout and coincided with
>   `core.hooksPath` turning absolute. Read in code: `tests/test_egress_allowlist.py:167-169` does not exclude
>   `.claude`. The worktree was **removed** (directory only; the branch and its commits are intact) before
>   this handoff was written. `git worktree list` now shows only `C:/Dev/sartor`; `core.hooksPath` reads
>   `.githooks`.
> - **Not verified by this session:** why PR #127 (ruff 0.17.0) fails; whether `release.yml` can publish when
>   dispatched by hand; whether Dependabot rebases a PR that is only `BEHIND`; whether mixed upload/download
>   artifact majors interoperate; the contents of the 23 open Dependabot alerts; the other two worktree-scan
>   tests' scan roots; the CI result of PR #178 beyond "it merged".
> - **Gate:** NOT RUN on this branch. `work_items check` read `OK (172 files)`; the handoff validator result is
>   in the commit that adds this file. Wiki: `wiki_freshness` read `OK -- 64 file(s) changed since the last
>   ingest (< 75-file block threshold)`; this branch's four changed paths all classify as **not**
>   wiki-relevant (`is_wiki_relevant()`), so no scoped wiki pass is owed by this branch.

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
- ~~`feat/confirm-before-overwriting-typed-edits`~~ ✓ (#170): item 170 closed.
- ~~`fix/reorder-networkidle-empty-census`~~ ✓ (#171) · ~~`fix/compose-single-context-parse`~~ ✓
  (#172): item 161 closed · ~~`fix/reorder-networkidle-bound`~~ ✓ (#173): item 30's Phase A;
  **item 30 stays `watching`**.
- ~~`feat/single-instance-and-quit`~~ ✓ (#174): items 146 and 147 closed.
- ~~`feat/data-root`~~ ✓ (#178, merged 2026-10-16T15:57Z, merge commit `3a29b28`): **item 145, branch 1 of 3**.
  Item 145 stays **open**.
- **`chore/dependabot-triage-item`** ← this branch: docs only, files items 171 and 172. Not pushed.
- **Next: the owner's pick.** Item 145's branch 2 (`feat/launcher`) and 3 (`feat/pushbuttons`) are not started.
  Other candidates are listed under "What this branch should build".

(The PR numbers in this list are GitHub PR numbers; they are unrelated to work-item ids such as 171 and 172.)

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and
on the owner's alpha approval. **Do not start item 145's branch 2 or 3 on this branch.** **Do not build item
171's workflow before the owner answers its four questions.** **Do not fix item 172 on this branch**: it is
its own `fix/*` branch and its first commit is a reproduction.

---

## What just landed on `main`

PR #178 (`feat/data-root`, item 145 branch 1 of 3) merged as `3a29b28` on 2026-10-16. The other agent's
handoff, `docs/dev/handoffs/data-root.md`, is the full record; this is a pointer plus what matters downstream.

- **The change:** `sartor_home.py` (a new stdlib-only leaf) is the one resolution of the user-data root
  (`SARTOR_HOME`, then the repo root in a checkout, then the per-user platform dir). Every user-data writer
  follows it. The `Dockerfile` sets `SARTOR_HOME=/data`, `VOLUME ["/data"]`, a stdlib `HEALTHCHECK` and
  `STOPSIGNAL SIGINT`. Bundled personas and the cover-letter shell resolve from the code root.
  `sartor_home.py` is now a **GATED** surface in `scripts/enforcement/blast_radius.py`.
- **Observed by that agent** (one run each unless stated; their dossier `docs/dev/blast-radius/data-root.md`
  `## Observed`, O1 to O13): 12 of 13 probed sites ignored `SARTOR_HOME` before and 13 of 13 follow it after;
  the container was built and run on **rootful** Podman 5.8.3 (healthy after 34 to 35 s, data survives
  recreate and an image update, `podman stop` 11 s with the default signal vs 1.3 to 1.7 s with SIGINT).
- **Their gate result:** `PASSED` in a clean detached checkout of `e31fd09` (3487 passed, 8 skipped; UX 189
  passed, 2 xpassed; 19 min 38 s) and `FAILED` in the repo directory on the same commit, for the three
  worktree-scan tests this session's item 172 records.
- **Not observed by that agent, declared:** rootless Podman, the CI-built GHCR image, Docker, the LLM path and
  `--setup` inside the image, a real wheel, and the template-preview route under `SARTOR_HOME`. **H2** (the
  image's recall index is not built: no `git` in the base image) is observed and **not fixed**. H3
  (`alembic.ini` not in the wheel) and H4 (`personas/cover_letter.html` not in the wheel) are hypotheses read
  from code.
- **This session did not re-run any of that.** The CI result of #178 was read only as "state MERGED"; the
  merge required the six branch-protection checks, so they passed at merge, but the final run was not opened.

**On this branch (not on `main`):** `bf646c2` items 171 and 172 plus the regenerated `BOARD.md`;
`979f420` this session's `consumed` ledger file for the data-root handoff; the commit that adds this file.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 21 / 10 ceiling -- OVER"** (19 items and
the 2 open epics, 19 and 36; this branch **added 2**: items 171 and 172). The owner's drawdown direction
stands: down to 0 if possible, before alpha staging. Still more than twice the ~8 to 10 reduction-sprint
threshold. Owner-decision items are marked *(owner)*. The lists below are **generated from the item files at
this commit**, not retyped. **Their counts differ from the board header by design:** the board prints an
epic's children under the epic, so item 10 (blocked, epic 40) and items 30, 34 and 57 (watching, epics 19
and 36) are counted here by status but sit under `## Epics` on the board. Here: Open 19, Blocked 5,
Deferred 9, Watching 47, plus 3 epics not closed (19 open, 36 open, 40 blocked). The board header reads
Blocked 4 and Watching 44 for the same data. That header-mixing is the subject of item 82.

`## Open` (19):
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
- **171** *(owner)*: 16 Dependabot PRs open, oldest 2026-07-13; nothing acts on green ones. Design the per-class merge policy.
- **172**: A harness worktree under .claude/worktrees fails 3 whole-tree gate tests in the main checkout; hooksPath also changed.

`## Epics` not closed (3):
- **19** (open): UX-suite flakiness solution sprint - mode-C residual + newly observed instances
- **36** (open): Final March epic A - main-app function + UX
- **40** (blocked) *(owner)*: Final March epic E - the public v1.1.0 cut

`## Blocked` (5):
- **3** *(owner)*: Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false. [blocked on: owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision]
- **5**: First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed. [blocked on: the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json]
- **8** *(owner)*: Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code. [blocked on: evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run] [depends on: 6]
- **10** *(owner)*: Bump pyproject.toml to 1.1.0, cut CHANGELOG [Unreleased] to [1.1.0], tag - last step, on the owner's go. [blocked on: everything else landing first, plus the owner's explicit go] [depends on: 3, 6, 7, 9, 19]
- **97** *(owner)*: Orchestration may belong outside the project; sartor's job becomes keeping ARC/CHECKLIST/ledger/BOARD in sync. [blocked on: owner design decision — this is a strategic redirect the owner raised; the tool choice and the scope of any sync layer are the owner's]

`## Deferred` (9):
- **4** *(owner)*: Avatar citations link out to GitHub; an in-app viewer needs a new route + sanitizer, deliberately not built yet. [blocked on: no friction signal yet; owner reaffirmed 2026-07-23, build only if friction warrants]
- **7** *(owner)*: Selective, not wholesale, memory consolidation - present the list, act only after explicit approval. [blocked on: owner sign-off on the keep/consolidate/delete list required first - judged irreversible if botched]
- **24** *(owner)*: In-app preview is single-column (python-docx limit); multi-column/paging fidelity needs a spike, never scheduled. [blocked on: not yet scheduled; needs a product-priority decision on investing in the spike before any code work starts]
- **25** *(owner)*: Single-threaded app.run() freezes the app during a diagnostics run; making it threaded is an owner-gated C-1 call. [blocked on: owner governance call not yet made; touches the C-1-sensitive loopback-bind area, deliberately kept out of the diagnostics epic and every branch since]
- **41** *(owner)*: Local lexicons (design, SWE, business, startup) so Compose drafting uses the JD domain's language and conventions. [blocked on: post-1.1.0 - owner scheduled this for 1.1.x investigation, not the Final March]
- **42** *(owner)*: Investigate dotx/mht as import formats and lock a small set of bullet-proof ATS templates with exact-preview fidelity. [blocked on: post-1.1.0 - owner scheduled a template epic for a 1.1.x sprint]
- **43** *(owner)*: v1.1.0 ships an approved-fonts list of Arial, Calibri, Georgia (sprint B2); verified additions considered later. [blocked on: post-1.1.0 - additions only after per-font ATS verification, owner-gated]
- **113** *(owner)*: 18 console UX findings outside Epic C (6 major, 12 minor) await triage; UX-22 is item 112; UX-24 joined C1b. [blocked on: owner triage after Epic C lands: which findings become items, which fold into a later epic, which are dropped]
- **114**: bench.md already summarizes error rows generically; naming error_message/error_type explicitly is a nice-to-have. [blocked on: low value until logs/llm_calls.jsonl accumulates real status="error" rows with the new fields; revisit once there is real data to summarize]

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

### Decisions the owner owes (collected; each is also in the item it belongs to)

- **Item 171, Q1:** may a bot enable auto-merge into `main` for the auto classes? (`maintainer-lane.md`
  step 4 says ask before a merge; it was written for agent branches.)
- **Item 171, Q2:** does the 2026-08-07 carve-out (the owner handles the docs-site Dependabot alerts
  personally) still stand, and does it cover version updates or only security alerts?
- **Item 171, Q3:** must the four Actions majors (PRs #10, #109, #51, #54) be resolved, or consciously pinned
  with a recorded reason, before the 1.1.0 tag? (The tag push is the first run of `release.yml` and
  `docker.yml`.)
- **Item 171, Q4:** a merge queue (a branch-protection change, owner's) or accept the squared CI cost under
  `strict: true`.
- **Item 172:** may agents use `EnterWorktree` in this repo before 172 is fixed, and if so only with a path
  outside the tree?
- **Item 145, branch 2's start:** the C-2 wording (`charter.md` names "the single-instance probe"; the
  launcher adds a loopback shutdown POST and a health read), the PEP 668 fallback for `pip install --user`,
  whether bare `sartor` with no runtime runs `up`, whether `sartor` is free on PyPI, separate native and
  container data. Its end-to-end waits on item 3 (nothing is published).
- **Item 10 and the alpha:** item 3 (GitHub toggles: repo rename, PyPI Trusted Publisher, GHCR visibility,
  `enforce_admins`), item 7 (the memory keep/consolidate/delete list), and the owner's alpha approval.
- **The *(owner)* items in `## Open`:** 50, 128, 129, 133, 135, 138. The *(owner)* items in Blocked, Deferred
  and Watching are flagged in the generated lists above.
- **Declared by the data-root agent as the owner's call:** whether `sartor --doctor` should print the key path;
  whether the simultaneous-launch race earns an item; whether to reopen item 164 (instrument first); whether
  the frozen `carry_edits=True` generate should keep a typed letter edit over a new letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5); whether a cover letter should be regenerable from
  the shipped screens (item 170's open question).

### Declared, not filed — carried from the data-root handoff, **not re-verified this session**

- The simultaneous-launch race: the one open limit of the single-instance guard (item 146's resolution).
- Wiki route and blueprint counts are prose, derived by whoever last edited the page; no check. **Unenforced.**
- Reported by subagents, not verified (leads): `blueprints/corpus/__init__.py`'s docstring sums its routes to
  50 where the files hold 54; `hardening.py:1780-1785` says the dev server "defaults to `threaded=False`" but
  Flask's `app.run` defaults `threaded=True`; `docs/dev/releasing.md:36-39` still describes a `GATE` step the
  publish job no longer has.
- **For item 145:** `platformdirs` has no runtime importer now (docstrings only; the parity test needs it), so
  it moves to the dev extra when branch 2 reorganises the dependencies. `evals/runner.py` writes results beside
  the code (`RESULTS_DIR = EVALS_DIR / "results"`) while the dashboard reads the data root; a mismatch only
  when `SARTOR_HOME` is set on a checkout; `evals/` is in neither the wheel nor the image.
  `preview_application_html` (`blueprints/templates.py`, the `BUNDLED_PERSONAS_DIR` reads near `:1075` and
  `:1441`) and the `generation.py` callers of the two persona resolvers were read, not run, under
  `SARTOR_HOME`. `sartor --doctor` prints only `found in .api_key` / `not found`, never a path.
- **Container (rootful only):** before any local build run `git ls-files --eol Dockerfile` (this machine's
  working copy is CRLF; build from a clean `git archive` with `--format docker`). `podman machine ssh` run
  from the repo drops a file named `NUL` there; run it from a scratch directory.
- A doc that paraphrases a code string has no check (`analyzer.py:_NO_CREDENTIAL_DETAIL` was fixed only
  because a wiki review compared a page to it). **Unenforced.**
- `maintainer-lane.md` step 2 still gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs
  `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.
- The IDE's Pyright reports stale "not defined / not accessed" hints between consecutive edits; `ruff` and
  `mypy` were clean.
- Older carry-forwards, as listed in `docs/dev/handoffs/data-root.md` under "Carried from earlier handoffs"
  (about 40 bullets: the P3/P4/P5 probe tests, the `isidium` MCP processes not being a session's to stop,
  `ruff` not on the Git Bash PATH, `plan_gate` and a detached HEAD, `ALLOWED_LINE_CITES`, the stale
  `db/build_context.py:92` comment, `tests/test_plan_approval_scoping.py` taking about 6 minutes, count drift
  in `enforcement.md:29-31`, and others). **Read that section there; it is not re-copied here, to avoid a
  second hand-maintained copy that rots** (the `maintained-classification-list` lesson). Not re-verified.

### New this session, declared (observed unless marked)

- **Dependabot state at 2026-10-16:** 16 open PRs (github-actions #10, #51, #54, #109, #147; pip #106, #127;
  npm `/docs-site` #132, #137, #146, #151, #152, #175, #176, #177); 23 open alerts (count only). Branch
  protection: six required checks, `strict: true`, `enforce_admins: false`, zero required reviews. Repo
  settings: `allow_auto_merge: true`, merge commit only, `delete_branch_on_merge: true`. `pyproject.toml:113`
  exact-pins `ruff==0.15.22` with a comment that bumping it is a deliberate one-commit action.
- **A stray empty directory** `.claude/worktrees/interesting-engelbart-27c56d` (dated May 6, no files,
  not a registered worktree, ignored by `.gitignore:108`). Not touched. Harmless to the scans as it holds no
  files; the owner may want it gone.
- **Hooks seen refusing, none bypassed:** `block-merge-to-main` refused `git merge --ff-only origin/main`
  run from a **feature** branch to update it (a rebase was used instead); the plan gate retired the previous
  approval when `feat/data-root` merged, so the first repo write of this session needed a new plan and
  `EnterPlanMode` then `ExitPlanMode`; the interrogative witness paused the first write after each user
  prompt and cleared on the identical re-run.

---

## Recurrences observed this session → guardrail authored

1. **A concurrent-session hazard came back, and this session was the cause** (the class the data-root
   handoff's #5 recorded from the other side: "a concurrent session changed shared git config"). Recognized
   as a recurrence of the "concurrent agents share one clone" class, which the memory
   `feedback-concurrent-agents-worktree` answers with "use separate worktrees". Following that guidance in
   the harness's default location (`.claude/worktrees/`) broke the other agent's gate. **No mechanism
   authored on this branch.** Item 172 records it and its first move is a reproduction; the mechanism that
   would fail closed is a derived-set test that every whole-tree scan excludes `.claude` (or reads
   `git ls-files`), which belongs on the `fix/*` branch. **Filed as a work item is not a mechanism:** this is
   **unenforced** until that branch lands, and it has been stated to the owner in chat.
2. **An unsourced assertion made before checking** (C-12; a recurrence of the data-root handoff's #3). In
   the answer about adding Dependabot fixes to CI this session said the **release and docker** workflows use
   the artifact actions; a grep afterwards showed `docker.yml` uses only `setup-qemu-action` and the artifact
   actions sit in `release.yml`, `capture-smoke.yml` and `docs-deploy.yml`. It was caught by grepping before
   item 171 was written, and item 171 carries the checked list. It was in chat, not in a committed doc.
   **No mechanism possible** for prose; the defence is checking each behavioural claim before writing it.
   **Unenforced.**
3. **A hook refused a legitimate-looking command** (a member of the false-block class `fix/hook-guard-false-blocks`
   (#157) addressed, and item 53 tracks for `verify-binary-on-path`): `block-merge-to-main` refused merging
   `origin/main` **into a feature branch**. Observed once; whether that is a false positive by design or
   intended (AGENTS says the flow is PR-only) was not established. **No mechanism authored, nothing filed:**
   it is the owner's call whether it is a defect. The hook was not bypassed and no escape hatch was used.
4. **The interrogative witness again paused edits after turns that were not questions** (item 164's class;
   see the data-root handoff's #4 and `single-instance-and-quit.md` "Recurrences" #5). Observed on this
   session's writes after prompts that were directives; each cleared on the identical re-run and no hook was
   bypassed. **No mechanism authored on this branch**, the same position as the previous two handoffs: the
   evaluation points to reopening item 164, instrument first, which is the owner's pick.

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses the next item; this handoff does not pick one. The
list below is the closing agent's **recommendation for order, not a decision**. Do not expand beyond what the
owner names.

1. **Land this branch first (if the owner agrees).** Docs only: items 171 and 172, one ledger file, this
   handoff. Steps, in order: `python -m scripts.gate` (about 20 minutes; **not yet run**, and it must be
   run from Git Bash in a tree with no linked worktree under `.claude/worktrees`), state to the owner what
   becomes public, get confirmation, `git push -u origin chore/dependabot-triage-item`, `gh pr create`,
   `python -m scripts.ci_wait <n>` (exit 0 only), `gh pr merge <n> --merge`, `git checkout main && git pull
   --ff-only`, regenerate the pointer with `print_handoff_pointer.py` and verify it with
   `check_handoff_pointer.py`, then `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Item 172's fix, `fix/gate-skips-linked-worktrees`** (agent-owned, small). First commit is the
   reproduction (C-7): create a linked worktree under `.claude/worktrees/`, run the three tests, record the
   failure in `docs/dev/diagnosis/gate-skips-linked-worktrees.md` `## Observed`. Enumerate every `rglob(` and
   `os.walk` under `tests/` and `scripts/` before choosing between the three candidate fixes in the item.
   Measure `git ls-files` before choosing it (the data-root handoff recorded 1.8 to 5.2 s under memory pressure).
   It removes the reason agents cannot safely work in parallel in this clone.
3. **Item 171, after the owner answers Q1 to Q4.** Instruments first: read the failing log of PR #127; trace
   whether `release.yml`'s `publish` job can run on `workflow_dispatch`; read the changelogs for the four
   Actions majors. Then the policy and the small `pull_request` workflow. Do the ruff bump on its own branch
   (`pyproject.toml:113`).
4. **File and look at `capture-smoke.yml`'s three failed scheduled runs** (cause not examined). Candidate for
   its own item, not part of 171.
5. **A checkpoint-advancing wiki pass.** The freshness gate reads 64 of 75; the data-root handoff says one is
   owed **before the next wiki-relevant branch** or `scripts/wiki_freshness.py` will trip the merge.
6. **Item 145's branch 2** (`feat/launcher`). Read item 0145's `## Updates` first. The first commit is an
   instrument (does a built wheel ship `alembic.ini` and `personas/cover_letter.html`? does the image's
   recall index build?). Ask the owner the questions listed above before any code.
7. **Open product bugs, agent-workable:** 140 (internal bullet ids leak into LLM output, and the cover letter
   invents its date; a grounding C-3 issue and the most serious), 130 (profile edits do not reach the AI),
   105 (no education from corpus import), 131 (a retired application cannot be found again), 107 (no
   account-naming step at first run), 134 (contradicting smoke-cost estimates), 139 (`capture_screenshots`
   leaves its demo user), 98 (wiki freshness measures checkpoint-staleness), 99 (`install.md` documents
   unpublished paths; depends on 3), 137 (a models and call-settings review).
8. **Remaining container checks and H2** (rootless Podman, the CI image, Docker, generation and `--setup`
   in the image; the no-git recall-index path) if the owner picks them; the method is in
   `docs/dev/blast-radius/data-root.md` O10 to O13.
9. **Reopening item 164** if the owner picks it: instrument first.
10. **The *(owner)* items**, which need a decision before any branch.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path:
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then confirm with the owner whether this branch was pushed and merged,
and that `git worktree list` shows no linked worktree under `.claude/worktrees` before running any gate in
`C:\Dev\sartor`. Then ask which item to take. Create that branch off `main`, write a plan at
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
