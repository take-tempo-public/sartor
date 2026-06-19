# Release Checklist — callback.

> **Purpose:** the ship-list. What must be true before tagging a
> release, in what order, to what quality bar. The verify-before-
> ship gates for the next release.
> **Audience:** humans driving a release; LLM agents proposing
> version-bump work or release-blocking fixes.
> **Authoritative for:** the *active* release definition (v1.0.1
> at time of writing); the minimum-bar tests / ruff / mypy / eval
> gates; which items are shipping-blockers vs nice-to-haves.
>
> **Companion:** see
> [`docs/PRODUCT_SHAPE.md`](../PRODUCT_SHAPE.md) §10 for the full
> deferred-items table that drives the v1.0.1 / v1.1 / v2 ladder.

---

## Active release — v1.1.0 (public release — user-owned tag)

**Tag history (all local-only — no public release until the user-owned
v1.1.0 tag):** v1.0.1 tagged 2026-05-28, v1.0.2 tagged 2026-05-30,
v1.0.3 tagged 2026-06-02, v1.0.4 tagged 2026-06-02 (commit `072e290`, eval
tuning loop), v1.0.5 tagged 2026-06-07 (UI/UX redesign + diagnostics/tuning
console — **shipped**; all seven §Phase 4 tag criteria met, gate green incl.
`pytest -m ux`). **Versioning model (2026-06-08):** the **patch digit is an epic**
(a bounded set of one-branch sprints); the **minor digit is a tag marker** for a
public version (**1.1.0 = the public release**). Three internal epics now sit
between v1.0.5 and the public tag — **v1.0.6** (walkthrough polish + WS-4 wiki
substrate + corpus completion), **v1.0.7** (the app knows itself: self-documenting
wiki + doc-grounded assistant + governance extraction + pre-public hardening), and **v1.0.8** (monolith →
blueprints; absorbs the type scan) — folded into the arc on 2026-06-08 from the
v1.0.5 walk-through sprint plan + the excellence-walk workstreams + a backlog
grooming; see [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.5 / §4.7 / §4.8. Deferred
feature ideas live in [`nursery.md`](nursery.md). The immediate next epic is
**v1.0.6**, which **opens with a fresh end-to-end walkthrough**. The public
**v1.1.0** tag remains **owned by the user** — the public cut of the complete
product (assistant + self-documenting wiki + clean blueprints). The v1.0.5 items
below are reconciled in place (shipped → `[x]`); still-open items are carried into
v1.0.6 / v1.0.7 / v1.0.8 / v1.1.0 as noted.

### v1.0.7 → v1.0.8 — ordered sprint sequence (planned 2026-06-15)

> The two-epic plan from the 2026-06-15 release-planning session — **the ordered "what's
> next" between the v1.0.6 tag and the public cut.** Authoritative branch acceptance +
> rationale: [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7 / §4.8. **PX-item → branch
> authority** stays the prescriptions archive
> [`reviews/2026-06-product-excellence/03-prescriptions/`](reviews/2026-06-product-excellence/03-prescriptions/)
> + the PX rows in this file — the slots below are **indicative, not a re-authored PX
> map.** Each row is one branch / one session; quality gate green before every commit;
> ask before merge. **v1.0.6 is tagged**, so v1.0.7 opens off `main`.

**Owner decisions that shape the sequence:** (1) public **v1.1.0** stays the user-owned
promotion tag, but **all work lands by v1.0.8** (GitHub repo may be pushed early,
private/unpromoted; promote at v1.1.0 once integration issues resolve); (2) the
`app.py`→blueprints refactor **opens** the v1.0.8 cleanup window — issue-gathering runs on
the **decomposed** code; (3) feature-complete = the locked-in v1.0.7 set (R2
analyze-streaming is **already shipped** — a verify-the-wiring item, not a build); (4) the
post-feature test window is a **formal gate** (E2E walkthrough + first real-data eval loop
→ numbered findings backlog → correction sprint).

**Epic v1.0.7 — feature-complete ("the app knows itself").** Hard order 7.1 → 7.2 → {7.3, 7.7}; assistant after 7.3 design.

- [x] **7.1** `chore/plugin-activation` — make `.claude-plugin/` commands + agents load (not just hooks); fix `CLAUDE.md` "Skill catalog". Unblocks `/wiki-*` + compliance pilot. **Landed 2026-06-15:** local `callback-tools` marketplace + `enabledPlugins` committed in `.claude/settings.json`; `plugin.json` name→`callback` / version→`1.0.6`; the 10 command + 6 agent `.md` files moved out of the reserved `.claude-plugin/` to the plugin root (`commands/`, `agents/` — Claude Code skips components nested in `.claude-plugin/`), default root scan (no path-overrides); commands namespace as `/callback:…`, subagents `callback:…`. **Hooks deliberately left in `settings.json`** (enforcement-portability deferred to 7.2 — see tracked-deferred below). `CLAUDE.md` Skill+Subagent catalog and `README.md` plugin section corrected.
- [x] **7.2** `design/governance-extraction` → `feat/governance-extraction` — one canonical rules home; **preserve `@import`/pointer rule-access** (hard constraint). PX-23/24/27/28 ride here. **Design half DONE 2026-06-15** (`design/governance-extraction`): sub-decisions resolved (home=`docs/governance/`, AGENTS=inline-with-pointer, graduate all 4 draft files), drift-reconciled (cite-don't-refix), portability decided (split) — full spec in [`governance-extraction-design.md`](governance-extraction-design.md). **feat/ half DONE 2026-06-15** (`feat/governance-extraction`, merge `2b35551`): canonical rules graduated to `docs/governance/` — `charter.md` (signed; C-0…C-6 · D-1…D-6 · W-1/W-2 · amendment ceremony) + `enforcement.md` (gate/witness/tribal split) + `metrics.md`; PX-24 (`block-merge-to-main` HEAD==main check) + PX-28 (`check-plan-approved` hand-create-hint removal) + PX-27 (`vision.md` demotions) landed; `@import`/pointer rule-access preserved (`@AGENTS.md` chain intact). *(Row was left `[ ]`/"feat/ half pending" after the merge — surfaced as stale by the 7.7 compliance-witness pilot (CW-01, 2026-06-16) and corrected here.)*
- [x] **7.3** `design/self-documenting-loop` → `feat/self-documenting-wiki` — bounded, cost-aware Haiku diff-pass ingest + `/wiki-lint`/`/wiki-audit` backstop (PX-33). **Design half DONE 2026-06-16** (`design/self-documenting-loop`): trigger / cost / scope settled (bounded checkpoint + freshness-witness-hook escalation, no scheduler; Haiku diff-pass with warm-start exemplars by-reference + per-run page cap; `docs/wiki/`-only — the cross-document link/cite checker stays the separate follow-on, not absorbed), orchestration = new `/wiki-self-update` command + Haiku `wiki-scribe` subagent + separate read-only Haiku `wiki-grounding-auditor` subagent (author≠auditor) + `/wiki-lint` as the deterministic gate; **the loop never auto-commits** (always a reviewable diff). Full spec in [`self-documenting-loop-design.md`](self-documenting-loop-design.md). **feat/ half DONE 2026-06-16** (`feat/self-documenting-wiki`): built per the design §4 — `commands/wiki-self-update.md` orchestrator + `agents/wiki-scribe.md` (Haiku, `Read`/`Grep`/`Glob`/`Edit`) + `agents/wiki-grounding-auditor.md` (Haiku, read-only `Read`/`Grep`/`Glob`); freshness hook escalates at a 10-file threshold; default page cap 8 (`--cap N`); exemplars by-reference = `route-surface` + `deterministic-llm-boundary` + `using-callback`; **dev-harness only** (no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged). Owner-approved: the loop's **first real run landed on this branch** (the consolidated v1.0.7 wiki refresh — see [`docs/wiki/log.md`](../wiki/log.md)), so 7.9 inherits a current checkpoint.
- [x] **7.4** `feat/recall-skeleton` — Stage 0 `recall/` package (no LLM; never imports `app.py` → refactor-immune). **DONE 2026-06-16** (`feat/recall-skeleton`): new stdlib-only `recall/` package — the Stage 0 skeleton of the Memory substrate per [`memory-architecture.md`](memory-architecture.md) "Staged build." Public surface = `Unit`/`Source`/`Scope`/`Context` + `assemble()`; the two cross-cutting planes (provenance stamp enforced at construction; access/disclosure audience+tier gating); a working deterministic `assemble()` (RRF fusion + token-budget pack) proven end-to-end over a shipped `InMemorySource` reference; **no real source tier** (S1 wiki/S2 git → 7.5, S3 vector → 7.6) and **no LLM**. The hard dependency rule (never imports `app.py`/`analyzer.py`/DB/Flask/`anthropic`) is enforced by [`tests/test_recall_boundary.py`](../../tests/test_recall_boundary.py) (AST boundary-lint mirroring the PX-08 egress gate) — a test, **not a hook** (enforcement-portability stays the Sprint 8.7 work). **Dev-substrate only** — no route, no LLM call, no new dependency, no migration; `PROMPT_VERSION` unchanged; no user-facing behavior (nothing wired into the pipeline yet). Gate green (ruff · mypy · pytest). No new ledger item (open count stays 7).
- [x] **7.5** `feat/doc-assistant` — **the AI assistant** (Stage 1): wiki + `git grep` retrieval + Haiku avatar (user's key) + user/dev toggle; authored as its own `blueprints/assistant.py` module (blueprint-aware so the v1.0.8 split is a move, not a rewrite). **DONE 2026-06-16** (`feat/doc-assistant`): the three generic tiers in `recall/sources/` (`WikiSource` S1 / `GitGrepSource` S2 / `SessionSource` S5-P1 — roots+audience injected, kept project-agnostic by a new `test_recall_sources_no_hardcoded_roots` guard); the avatar `analyzer.avatar_answer_streaming` + `AVATAR_SYSTEM_PROMPT` (**honors C-6 — D1=A**) with its own `AVATAR_PROMPT_VERSION` (résumé `PROMPT_VERSION` unchanged); the SSE route `blueprints/assistant.py` (`POST /api/assistant/ask`, no `app.py` import) + the egress-allowlist add; a minimal collapsible in-shell panel (`templates/index.html` + `static/assistant.js`). Owner-confirmed: **D1=A** (avatar in `analyzer.py`), **D2=Y** (parameterized sources in `recall/sources/`), **UI** = minimal in-shell panel. **Zero new deps; no migration.** Gate green (ruff · mypy · pytest incl. the UX panel test). No new ledger item (open count stays 7).
- [x] **7.6** `feat/doc-assistant-vector` — Stage 2 vector tier. **DONE 2026-06-16** (`feat/doc-assistant-vector`): the S3 `VectorSource` semantic tier on the `recall/` `Source` protocol — static `model2vec` embeddings (`potion-base-8M`, dim 256) + brute-force cosine over a rebuildable `db/vector_index/` sidecar (gitignored; **NOT** `db/resume.sqlite`), incremental ($0-on-unchanged content-hash reuse), built offline by [`scripts/build_vector_index.py`](../../scripts/build_vector_index.py); wired into the assistant **"on when available"** (model + index present; no user-facing toggle). The substrate stays embedder-agnostic — the embedder is **injected**, so `recall/` never imports `model2vec` (it lives in `blueprints/assistant.py` + the build script); only `numpy` enters `recall/sources/` (the stdlib boundary test was deliberately relaxed for it). **Eval gate was an OWNER OVERRIDE** (was eval-gated/conditional): built ahead of the formal v1.0.8 labeled eval because the landed Stage-1 assistant tested *too literal / lacking semantic flexibility*; a probe ([`scripts/vector_index_probe.py`](../../scripts/vector_index_probe.py)) corroborates ([`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md)), the judge-scored before/after eval is owed at v1.0.8 (ledger). **New hard deps** `numpy` + `model2vec` (numpy + tokenizers + safetensors, no torch); CHANGELOG + RELEASE_ARC §4.7 + architecture + memory-architecture updated. No migration; résumé `PROMPT_VERSION` unchanged. Incidental fix folded in: `test_git_grep_source.py::test_no_match_returns_empty` was a pre-existing main failure (latent since 7.5: its hardcoded "absent" token self-matched the now-tracked test file via `git grep`) — fixed to a runtime-built token. Gate green (ruff · mypy 186 · pytest). Adds 1 ledger item (→ 8).
- [x] **7.7** `feat/compliance-agent-pilot` — `/compliance-witness` command + read-only subagent. **DONE 2026-06-16** (`feat/compliance-agent-pilot`): built per [`compliance-agent-design.md`](reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md) Appendix — `commands/compliance-witness.md` orchestrator (resolves a pinned sha via `--since`/last tag, delegates the read via `Task`, **caps flags default 12** `--cap N`, renders a findings-register table FLAG/WATCH/AFFIRM + a `/wiki-lint`-style gate verdict, appends a dated counts line to `docs/governance/compliance-log.md`) + `agents/compliance-witness.md` (**Sonnet**, read-only `Read`/`Grep`/`Glob`/`Bash` read-only-git — **no `Edit`/`Write`/`Task`**, the tool grant *is* the HARD-non-goal enforcement; pairwise-drift-only, ranks against the charter/C-0, cites-never-asserts, honest-silence). **Never edits, never blocks, never commits.** Both land at **repo-root** `commands/`+`agents/` — the design's `.claude-plugin/`-only Appendix path predates the 7.1 move (Claude Code skips components nested in `.claude-plugin/`). **Dev-harness only** (no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged). Owner-approved: one supervised **pilot run** against the freshly-graduated `docs/governance/` (born [`docs/governance/compliance-log.md`](../governance/compliance-log.md)) — window `e299ac8`→`1741ab1`, FLAG 1 / WATCH 2 / AFFIRM 3, verdict *needs attention*. **Pilot PASSES** the design's self-eval rubric: the one FLAG (CW-01 — this very checklist's 7.2 row left `[ ]`/"pending" after `feat/governance-extraction` merged) was owner-scored **true drift → flag-precision 1.0 ≥ 0.66**, and corrected here. Surfaces as `/callback:…` on the next Claude Code reload (in-session pilot reproduced the subagent as a Sonnet-pinned agent, per the 7.3 first-run precedent).
- [x] **7.8** `px/v107-band` — PX-18 `ACCESSIBILITY.md`, PX-31 Chromium reclassification, PX-32 KEEP/BOOST ledger; + fix the stale R2 deferred-listing in `PRODUCT_SHAPE.md`. **DONE 2026-06-16** (`px/v107-band`). **PX-18** (`F-expa11y-03`): new root [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) honest-status page per **E-2** (signed product charter, not the graduated `docs/governance/`) — the machine-checked taxonomy (axe serious/critical · keyboard a11y-floor · `_announce()` live-region · modal trap · `--fg-2/3` contrast) **vs known gaps** (UX tier not yet in CI → PX-25; serious/critical-only; Clarify/Output/cover-letter/modals + tab-order/reflow/history unscanned; NVDA not yet walked); **no conformance claim / tag gate / recurring-audit promise** (v1.1.0 WCAG-2.2-AA self-eval stated as intent only); + README doc-map pointer. **PX-31** (`F-docs-05`): Chromium ~150 MB reclassified **PDF-output-only** — lifted out of `docs/install.md` Prerequisites + the 3 OS sequences gated "optional — only for PDF output"; corrected the "renders every PDF and the live preview" conflation (the preview is browser-side paged.js, Chromium-free — `SECURITY.md` bundled-assets; verified `pdf_render.py` is the sole Playwright renderer); README quick-install + `pyproject.toml` playwright comment tightened. **PX-32**: new [`docs/dev/keep-ledger.md`](keep-ledger.md) eval/governance do-not-regress ledger — `F-eval-05/06/08` + `F-gov-06/09` + `F-docs-07/08/09` as KEEP notes, `F-eval-09` as a precision note, `F-eval-07` **BOOST** affirmed, `F-gov-08` + `F-gov-10` logged as **deferred design items (ledger-only)**; the security/PII KEEP set cross-referenced to PX-29 (8.4). **R2 fix**: `PRODUCT_SHAPE.md` §10 R2 entry marked **shipped v1.0.3** (was still listed v1.1-deferred, contradicting the §494 banner). **Docs-only** — no code/prompt/route/dep/migration; `PROMPT_VERSION` unchanged. Gate green (ruff · mypy · pytest). **No new ledger item (open count stays 8)** — the PX-32 deferred design items live in `keep-ledger.md`, not the carry-forward ledger (owner decision).
- [x] **7.8a** `feat/assistant-topbar-modal` — **assistant UI relocation** (first of a few small UI-polish sprints the owner flagged before the 7.9 tag). **DONE 2026-06-16** (`feat/assistant-topbar-modal`): the doc-grounded assistant's entry point moved from the always-visible in-shell collapsible `<details>` panel (`#panelAssistant`, parked below the wizard) to a **fixed top-bar magnifier icon** (`#assistantPill`, left of Diagnostics) opening a **floating, scrollable modal** (`#assistantModal`) — one stable, always-findable entry point. Reuses the existing `.cb-modal` skeleton (id-scoped to ~680px; `.cb-modal-body` internal scroll + 90vh cap unchanged) and the top-bar-pill-opens-overlay precedent (Diagnostics modal / Settings drawer). The control ids carry over, so `static/assistant.js` `askAssistant()`/SSE path is **unchanged**; one new `openAssistantModal()` adds focus-trap/Esc/backdrop/focus-restore/`aria-expanded` mirroring `openDiagnosticsModal()`. POM (`ui_pages/selectors.py` `Assistant`) re-pointed pill→modal; the assistant UX regression now drives pill → modal → streamed cited answer; the axe gate adds an open-state `#assistantModal` scan. **Front-end only** — no route, LLM, prompt, dep, or migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged. Gate green (ruff · mypy · pytest · `-m ux`). **No new ledger item (open count stays 8.)**
- [x] **7.8b** `fix/v107-ui-polish-trio` — **three small UI-polish fixes** (second of the few small sprints before 7.9). **DONE 2026-06-17** (`fix/v107-ui-polish-trio`): (#1) **stray browser windows** — `app.py` auto-opened a browser on every Flask debug-reloader restart because the open ran in the serving child (`WERKZEUG_RUN_MAIN == "true"`) the reloader re-executes per reload; a new pure `_should_open_browser()` opens **exactly once** (supervisor / non-debug single process, never the reload child; still honors `CALLBACK_NO_BROWSER=1`), covered by `tests/test_browser_open.py`. (#3) **slow application load** — `list_applications` ran `1+2N` queries (lazy `Application.runs` + per-app pending `ProposalReview` count); now `selectinload(Application.runs)` + one batched `group_by` pending-count → ~3 queries regardless of N, with a constant-query-count regression test. (#4) **new-user stale dropdown** — `showNewUserForm()` cleared the leftover `#userSelect` value (Cancel restores it) + a UX regression. **No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged.** Gate green (ruff · mypy 189 · pytest 1296 incl. `-m ux`). **Adds 1 ledger item** (assistant doc-coverage → open count 8 → 9). The remaining named UI-polish candidate is **#2 assistant voice softening** (own `feat/` branch — owner's "start with voice softening").
- [x] **7.8c** `fix/assistant-runs-without-user` — **let the doc-grounded assistant answer without a user selected** (third small UI-polish sprint before the 7.9 tag; follows #2 voice softening on `feat/avatar-voice-tone-tuning`). **Finding (2026-06-18):** the assistant gates on a chosen user (`static/assistant.js:24` "Pick a user first, then ask."; `blueprints/assistant.py:231` 400s on missing `username`, `:233` `_safe_username` 400s on unknown), but the answer is **project-global** — grounded in the committed wiki + code at HEAD, identical for every user. `username` does **not** feed retrieval (`_build_sources`/`assemble`), scope (`allow_dev` = the Dev-mode checkbox), or the answer; it is used only for (a) a `_safe_username` existence check applied **by discipline** (the route touches **no** user filesystem — its own docstring says `_within`/`secure_filename` is N/A) and (b) telemetry attribution, which `analyzer._call_llm_streaming` already supports anonymously (`username=""` default). So gating the avatar behind user-selection is an artifact of the per-user route pattern, not a need — and it blocks the assistant at exactly the first-run moment ("how does callback. work?") where a brand-new visitor benefits most, which reads as unfinished. **Fix:** make `username` optional in the assistant path — drop the client gate, relax the route's `if not username` 400, `_safe_username`-validate only when a username is provided, and stamp anonymous telemetry (`""`/`"anonymous"`). Retrieval + answer unchanged; add a route test for the no-user path. Small + contained (`blueprints/assistant.py` ~:225–235, `static/assistant.js:24`). **Pre-7.9-tag.** _(surfaced 2026-06-18 during `feat/avatar-voice-tone-tuning` close-out; capture only — its own branch.)_ **DONE 2026-06-19** (`fix/assistant-runs-without-user`): `username` made optional in the assistant path — the route requires only `question`, `_safe_username`-validates only when one is supplied (a provided-but-unknown user is still a `400`), and absent → anonymous (`""`); the client gate ("Pick a user first, then ask.") is dropped and the Ask button sends `currentUser || ''`; the no-user route test now asserts a streamed anonymous `200` (missing-question + unknown-user `400`s retained). Retrieval + answer unchanged; L3 microcopy needed no edit (the only "pick a user first" string was the removed JS gate). No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged. Gate green (ruff · mypy 189 · pytest 1303 — the lone full-run failure `test_compose_skills_card_drop_persists` is a pre-existing intermittent UX-tier race, passes clean in isolation, unrelated to this change). **Folded in (owner-directed):** the avatar citation/reference-format feedback surfaced this session is captured on this branch as [`avatar-citation-format-guidance.md`](avatar-citation-format-guidance.md) + a new carry-forward ledger item (open count 9 → 10; see the follow-up commit).
- [ ] **7.9** `chore/version-bump-v1.0.7` — tag. **Pre-tag: run `/wiki-self-update`** for the consolidated wiki refresh (the self-documenting loop now owns the diff-pass that `chore/version-bump-v1.0.6` did by hand), then confirm `/wiki-lint` is clean before tagging. (7.3 already advanced `.last_ingest_sha` to the v1.0.7 band, so this is a small top-up unless 7.4–7.8 changed cited code.)

**Epic v1.0.8 — refactor → gather → correct → public-prep ("all work done by 1.0.8").** Refactor opens the window; gather + first real-data eval loop run on the decomposed code.

- [ ] **8.1** `design/app-blueprints` — seams + shared-helpers home; 32 test imports; lint-hook compat.
- [ ] **8.2** `refactor/route-security-lint-widen` (PX-21) — widen the hook past `app.py` **before any route moves** (hook is app.py-only today).
- [ ] **8.3a–g** `refactor/app-blueprints-<seam>` — one seam/branch (analysis · generation/cover-letter · templates · corpus · user-config · dashboard · assistant move-only); folds `ResponseReturnValue` (PV-4) + the deterministic-LLM boundary gate (PX-20); back-nav (PX-22) rides templates; loopback bind (PX-19) rides user-config.
- [ ] **8.4** `test/keep-ledger-guards` (PX-29) — do-not-regress guards so the split can't weaken the KEEP ledger.
- [ ] **8.5** **gated test window (on decomposed code)** — E2E user+dev walkthrough (R2 verified live) + `eval/live-shakedown-labels` (PV-1, **first** real-data eval/tuning loop) → numbered findings backlog.
- [ ] **8.6** `fix/window-findings-*` — correction sprint: burn the backlog + PV-2 calibration + PV-3 cover-letter tone + `/wiki-ingest`. May spill to a v1.0.9 epic.
- [ ] **8.7** `release/public-prep` — `docs/screenshots`, fresh-clone < 5 min, badge set (E-2 / PX-26), UX/a11y/PDF required CI check (PX-25), doc-link sweep, **GitHub repo create + push (private/unpromoted)**.
- [ ] **8.8** `chore/version-bump-v1.0.8` — tag; all work done.

**v1.1.0 (owner-gated promotion):** flip the repo public + cut the tag once the v1.0.8 window's integration issues are resolved and the product is "working as expected"; final fresh-clone + doc-link re-verify at the cut.

### v1.0.6 — Walkthrough polish + knowledge substrate + corpus completion (SHIPPED 2026-06-15)

Authoritative branch sequence + acceptance: [`RELEASE_ARC.md`](RELEASE_ARC.md)
§Phase 4.5. Gates for the v1.0.6 tag:

- [x] **E2E walkthrough kickoff (Sprint 6.0)** — user drives the whole product
      (app + evals + tuning) on a real corpus to collect findings; decompose into
      the 6.x buckets (the v1.0.5 method). Doubles as **real-data capture**: the UX
      findings + the real corpus/annotation labels v1.0.7 calibration needs + the
      first outcome data (B.8). Also the signing / re-confirmation pass for the
      **unsigned** `V1_0_5_VERIFICATION.md` and the named-but-unlanded V5-B parity
      fixes (#9 download ≠ preview, #10 step-6 edit not reflected).
      **Progress (2026-06-10):** first pass completed end-to-end after the sprint-1
      blocker fixes (`fix/onboarding-e2e-blockers`); **11 findings (KW1–KW13)
      harvested + triaged into the 6.x buckets** — see RELEASE_ARC §Sprint 6.0
      "Kickoff-walk harvest". Still open before this gate checks: the lightweight
      eval/tuning pass on the re-walk, the `V1_0_5_VERIFICATION.md` signing run
      (#9/#10 re-confirmation), and the B.8 outcome-data verification (~~blocked on
      KW7~~ — **unblocked 2026-06-10** by `feat/outcome-capture-complete`: the
      re-walk should confirm the applications block updates live, the
      submit→outcome funnel works, and memory populates after clarify/interview).
      **Closed for the v1.0.6 tag (owner, 2026-06-15):** findings KW1–KW13 were triaged
      + fixed (the RELEASE_ARC tag criterion); the remaining re-walk verification pass
      (lightweight eval/tuning + `V1_0_5_VERIFICATION.md` signing + B.8 outcome-data
      confirmation) is **waived as non-blocking for this internal tag**, tracked forward to
      the v1.0.7 pre-public hardening pass.
- [x] **Sprints 6.1–6.6 merged** — 6.1 wizard-flow (incl. **B.8 Part 1** outcome
      capture) · 6.2 diagnostics-console · 6.3 forms + a11y (**the axe a11y gate
      lands first**) · 6.4 IA + onboarding (corpus-first) · 6.6 corpus-item completers
      (**B.4** ExperienceSummaryItem, **B.5** Skill-as-Corpus-Item) · 6.5 in-app education sweep.
      **Progress (2026-06-10):** first 6.1 branch `fix/generate-date-grounding` (KW6)
      landed — date-immutability prompt rules (PROMPT_VERSION `2026-06-10.1`) + a
      deterministic warn-only heading-date guard in both generate routes; smoke eval
      clean (see TUNING_LOG 2026-06-10 entry). Second 6.1 branch
      `feat/outcome-capture-complete` (B.8 Part 1 + KW7) landed — applications
      block syncs with the wizard, draft→submitted affordances (card button +
      Step-6 post-download nudge) open the previously unreachable outcome funnel,
      `?status=` query filter, and the candidate-memory write path goes live
      (answered clarifications → `clarification` rows; promote-to-bullet now
      reachable for wizard answers). Data model: lean single-status, `interview`
      terminal (user-approved 2026-06-10); no schema change, no prompt change.
      Third 6.1 branch `fix/clarify-generates-bullets` (KW4) landed 2026-06-11 —
      `/api/answer-clarifications` merges by id (default `merge:true`; skip path
      `merge:false`); two-round regression test. Fourth 6.1 branch
      `fix/clarify-double-question` (#6) landed 2026-06-11 — the "Continue to
      Clarify →" CTA now initiates clarification directly (one action) instead of
      re-showing the `#clarifyStartRow` "Get clarifying questions / Skip" prompt;
      rail-direct nav keeps that row; KW4 merge semantics untouched; UX-tier
      regression added. No prompt change, no new dep. Fifth 6.1 branch
      `feat/prior-app-resume-robustness` (#4 + #24) landed 2026-06-11 — prior
      applications now resume into the wizard at their **furthest** step
      (`_build_resume_state` classifies a `target_step` 1/2/3/6 from the iter-0
      context file; Steps 1–3 rehydrate with no `/api/clarify`/`/api/generate`
      re-spend), so analyze-/clarify-/compose-only apps are resumable (were dead
      cards). Card title + company are user-editable in the detail modal (new
      DB-only `PUT /api/applications/<id>/meta`; company was never captured) and
      the proposal pill reads "N to review". No prompt change, no new dep.
      Sixth 6.1 branch `feat/compose-add-title` (#7) landed 2026-06-11 — a
      Compose "+ Add title" affordance writes a sourced, immediately-eligible
      `ExperienceTitle` (`truthful_enough_to_use=1`, via the existing title
      route), and titles became a **per-JD radio** persisting
      `composition_overrides.pinned_title_ids`, honored in **both** the preview
      (`build_json_resume_from_corpus`: pin→official→first) and the generated
      download (chosen `<eligible_title pinned="true">` + new `<corpus_mode>`
      rule; `PROMPT_VERSION 2026-06-11.1`). The composition save re-syncs the
      frozen `career_corpus` eligible_titles for pinned experiences so a
      post-analyze title reaches generate. Per-JD pin was a user-approved scope
      extension of the #7 row; smoke eval clean (TUNING_LOG 2026-06-11). No new dep.
      Seventh 6.1 branch `fix/compose-order-no-recommendations` landed
      2026-06-11 (merge `c8b80e7`) — the no-recommendations Compose fallback now
      honors the saved GET order instead of re-sorting by score (render-only;
      detail in the "Discovered during the v1.0.5 stream" item below). Eighth
      6.1 branch `fix/step4-template-copy` (#8) landed 2026-06-11 — verified the
      four bundled templates **genuinely differ** in typography/layout (so the
      Step-4 "different typography and layout" line is accurate and unchanged)
      and corrected a stale **count**: migration 0005 curated the bundled set
      5 → 4 at v1.0.0, but the Résumé-templates settings copy still said "Five
      bundled" → "Four", and `docs/bundled_templates_LICENSE.md` inventory
      (which listed the nonexistent `compact.docx`/`hybrid_tech.docx`) was
      corrected to the curated four. Copy/doc only — no prompt change, no route,
      no new dep; canonical count of 4 pinned by `tests/test_bundled_templates.py`,
      copy↔rendered-set consistency guarded by a new UX regression. Ninth 6.1
      branch `fix/run-cover-letter-persistence` landed 2026-06-11 — the detached
      `POST /api/generate-cover-letter` route now persists
      `generated_cover_letter_md` onto the same run row the résumé wrote to
      (corpus-backed mode; best-effort), via a new surgical single-column
      write-back (`persist_cover_letter_md` + `_persist_cover_letter_to_db`) that
      deliberately avoids `persist_corpus_generation` (which would have nulled the
      saved résumé md). Captures the cover-letter signal B.8 Part 2 needs while
      real outcome data accrues. No prompt change, no route, no new dep, no
      migration; unit + route tests; pipeline/data-flow diagrams synced (detail in
      the "Discovered during the v1.0.5 stream" item below). Tenth 6.1 branch
      `fix/wizard-flow-polish` (KW5 + KW8) landed 2026-06-11 — **the final 6.1
      row, so Sprint 6.1 is complete.** KW5: `runIterateClarify()` now scrolls the
      rendered follow-up section (`#iterateClarifyArea`) into view in its success
      path, so the questions no longer generate below the fold. KW8: the button +
      divider were standardized on the clarify vocabulary (user-chosen "follow-up"
      framing) — "Get interview questions" → "Get follow-up questions", "Iteration
      interview" → "Follow-up clarification"; the `#btnIterateClarify` id and the
      tracker "Got interview" outcome status are untouched. Front-end only — no
      prompt change, no route, no new dep, no migration. UX regression
      (`test_20260611_wizard_flow_polish.py`) adds the first UX drive through the
      generate route, via two new offline stubs (`fake_generate_streaming` +
      `fake_clarify_iteration`).
      **Sprint 6.2** (`fix/diagnostics-chart-corrections`, #11 + #12 + #13 + KW13)
      landed 2026-06-11 — #11 verified **not a bug** (the cost-by-kind chart has
      always plotted the total; the fix is an explicit, unambiguous tooltip naming
      total + count + mean); the cramped 560px side drawer became a **full-width
      inline detail panel** (KW13, larger restructure, user-approved), which also
      fixes the #12 Calls horizontal scroll; and the latest-trace bars (a `<span>`
      left at `display:inline`, so their width never applied and they rendered at
      0px — fixed with `display:block` + a 2px min-width) now scale to the longest
      span (`dashboard/routes._run_trace.bar_pct`, max → 100%) so they render and
      short spans stay visible (#13). Front-end +
      deterministic aggregation only — no prompt change, no new route, no new dep;
      `bar_pct` unit test + UX regression
      `test_20260611_diagnostics_chart_corrections.py`; dashboard POM/selectors
      moved from `drawer` to `detail-panel` handles. **Sprint 6.3** opened
      2026-06-12 with `fix/form-field-labels-a11y` — **the never-shipped axe
      a11y gate landed** (`tests/ux/a11y/test_axe_smoke.py`; **vendored**
      axe-core 4.10.2, no pip dep; `a11y` marker, runs inside `pytest -m ux`),
      now guarding every later 6.x branch. Defect-vs-expected: the current
      markup had **zero** label/name serious/critical violations (the "~150"
      predated the redesign), so #3's labeling was already done — completed
      belt-and-suspenders (sr-only labels on the 3 hidden file inputs +
      `name`/`autocomplete` on the new-user & Settings personal fields). The
      gate's only serious finding was **pre-existing color-contrast** (muted
      text sub-AA on dark), fixed at the token level (user-approved scope add):
      `--fg-2`/`--fg-3` lightened to AA + `.edit-hint` drops `opacity:0.7`.
      Front-end + one test tier only — no prompt/route/dep/migration change;
      ruff/mypy ✓, pytest 1072/1072. Second 6.3 row
      `feat/required-field-and-dropdown-pattern` (#21 + #20-dropdown) landed
      2026-06-12 — two reusable conventions built on the new gate. **#21:** a
      `.required-marker` + `.form-required-legend` in `static/style.css`
      (shared) + the convention `required`/`aria-required` on the input,
      decorative `aria-hidden` asterisk on the label, applied across three
      render paths (new-user form, the `openFormModal` modals, and the console
      dropdown label). **#20:** `#bsUser`/`#tuneUser` converted from free-text
      inputs to `<select data-user-source>` auto-filled on load from the
      existing `GET /api/users` (reusable `populateUserSelects()`; no new route;
      `.value` reads unchanged) — `#bsUser` carries the required marker,
      `#tuneUser` (optional section) does not. Front-end + tests only — no
      prompt/route/dep/migration change; new regression
      `test_20260612_required_field_and_dropdown.py` + the dashboard axe scan
      now seeds a candidate so the populated dropdowns are scanned. Third 6.3
      row `fix/corpus-affordance-polish` (#2 + #5 + KW2) landed 2026-06-12.
      Defect-vs-expected: **#2** ("Add variant referenced in copy but no
      affordance") was **already resolved** by the β.6e summary-variants editor —
      regression-locked with a UX test rather than rebuilt; **#5** "tick arrows"
      resolved to the panel collapse chevron (`.panel-header::after`; a later
      redesign rule pinned the effective size to 10px → enlarged to 18px on the
      live rule, app-wide). Plus the misleading empty-state copy (dropped "automatically" —
      imports land pending review) and **KW2** corpus-wide "Accept all pending"
      (new banner button + DB-only `POST /api/users/<u>/accept-all-pending`,
      `_safe_username`, mirrors `accept_experience_all`; behind a sharp confirm
      since accepted items seed fit-analysis/bullet-generation/résumé-build).
      Front-end + one DB-only route + tests — no prompt/dep/migration change;
      new backend `TestAcceptAllPendingCorpus` + UX regression
      `test_20260612_corpus_affordance_polish.py`. **Sprint 6.4** opened
      2026-06-12 with `fix/logo-home-route` (#23) — the inert `.cb-wordmark`
      logo (`<a href="#">`, no handler) now routes home via a new public
      `goHome()` that reuses `onUserSelect()`'s no-user branch (deselect +
      `hideAllPanels()` + re-lock the picker open + `_resetIterationState()`) and
      `switchTopTab('tailor', …)` to restore the default landing tab; the anchor
      gains `onclick="goHome(); return false;"` + a clearer `aria-label`/`title`.
      Front-end only — no prompt/route/dep/migration change (pure SPA nav, so
      `route-security-lint` is N/A); new `Header` selector + UX regression
      `test_20260612_logo_home_route.py`; ruff/mypy ✓, pytest 1084/1084. Sprint
      6.4 second branch `feat/corpus-first-tab-onboarding` (#16 + #1 + KW1)
      **landed 2026-06-12** — tabs reordered to **Career corpus → Tailor →
      Résumé templates → Candidate memory** (button order only; Tailor keeps the
      default active state since the user picker lives in `#tab-tailor`); a new
      side-effect-free `_landingTab()` drives **smart landing** from
      `onUserSelect()` (empty corpus → Career corpus to onboard, fixing KW1;
      populated → Tailor) and `goHome()` (now routed through the same helper,
      single source of truth); a **"Start tailoring →"** hand-off CTA appears in
      the onboarding banner's ready state (non-empty corpus + 0 pending),
      replacing the dead-end. Front-end only — no prompt/route/dep/migration
      change. New UX regression `test_20260612_corpus_first_landing.py`;
      `test_20260612_logo_home_route.py` reseeded non-empty to match smart
      landing; new `Corpus.START_TAILORING_BUTTON` selector +
      `CorpusPage.start_tailoring_button()`.
      **Sprint 6.5 opened 2026-06-14** with `feat/help-pattern-component` (the
      reusable a11y-safe help **mechanism**; KW10/KW3) — **landed**. ONE shared
      `#helpModal` (cloned from the `.cb-modal` skeleton) + ONE generic
      `openHelpModal(blockId, triggerEl)` **factored from the duplicated per-modal
      pattern** (Esc / Tab focus-trap / backdrop click-away / focus-restore; the
      five existing modals left untouched); a `.help-info` (i)-circle injected per
      registered `.cb-panel` header (mirrors `.compose-order-info`) re-opens that
      block's modal, with real aria (`aria-haspopup=dialog`, `aria-controls`,
      `aria-expanded`) and **no color-only meaning** ("i" glyph + `aria-label`);
      an optional inline short-form line is injected + `aria-describedby`-linked.
      The welcome **first-view auto-modal** shows **once-ever** via a
      `cb_help_seen:<block>` **localStorage** flag (the app's first client-side
      storage — owner-approved; wrapped so a throwing store is non-fatal). A
      `_HELP_REGISTRY` keyed by block id is the **extension point** — the next 6.5
      branches add per-surface copy by adding keys, **no engine change**; this
      branch ships only one minimal demo entry (`panelUser`), **no per-surface
      education copy**. UX suite kept green by default-suppressing the welcome
      (autouse `_help_welcome_default_seen` fixture + `show_welcome` opt-in marker)
      so its full-screen backdrop never blocks other tests. New
      `test_20260614_help_pattern.py` (6 cases) + `#helpModal` added to the axe
      gate's scanned surfaces + a `Help` selector class. Front-end + help-component
      only — no route, no LLM, no prompt (`PROMPT_VERSION` unchanged), no dep, no
      migration. ruff/mypy ✓, pytest **1197/1197** incl. `-m ux`. Then
      `feat/education-tailor-corpus-wizard` (#1 + #18 — the per-surface education
      copy + KW3 first-run tour, authored INTO the WS-4 wiki user section) —
      **landed 2026-06-14.** Per-surface (i)-help on the user picker, prior
      applications, all six wizard steps, and the Corpus / Templates / Memory
      panels (registry keys, no engine change); the new-users-only KW3 tour
      (welcome → add-user → post-ingest → the six steps → generating →
      cover-letter), once-ever via `cb_help_seen:` + an in-memory armed flag, each
      stop (i)-re-openable, wizard stops visibility-guarded. Five new
      `audience: user` wiki guides (`using-callback` hub + tailoring / corpus /
      templates / memory) + index/SCHEMA/log/overview reconciled (content pass —
      `.last_ingest_sha` left at `93a34b9`; dev-tier `frontend-wizard.md` JS drift
      deferred to a later wiki refresh). New `test_20260614_education_help.py` (7)
      + an axe step-header-modal scan + the welcome-suppression fixture generalized
      to all tour stops (`show_tour` marker) + a scoped step-header icon CSS rule.
      Front-end + content only — no route, no LLM, no prompt (`PROMPT_VERSION`
      unchanged), no dep, no migration. ruff/mypy ✓ (161), pytest **1204/1204**
      incl. `-m ux` (the known `test_positioning_pin_preserves_title_pin` flake did
      not recur). Then `feat/education-diagnostics-annotate` (#15 + #20 + #22 —
      the diagnostics console) — **landed 2026-06-15.** The localhost `/_dashboard`
      console is self-contained (never loads `static/app.js`), so it got its own
      **port** of the help primitive in `dashboard/templates/dashboard.html`: the
      same `#helpModal` skeleton (id reused → the `Help` POM applies unchanged),
      a per-tab `_DASH_HELP` registry, an `openDashHelp`/`_maybeFireDashHelp`
      opener (Esc/Tab-trap/backdrop/focus-restore), a per-pane summary line + (i),
      and a per-tab first-expand explainer (Pipeline auto-opens on load, each
      other tab on its first click) — once-ever via the **shared** `cb_help_seen:`
      prefix, so adding the five `dash*` ids to `_TOUR_STOP_BLOCKS` suppresses them
      suite-wide. Annotate tab: plain-language verdict legend + scaffold-banner +
      ① copy, per-option `title` tooltips (suite/subset/grounding), and the
      bootstrap `<details>` auto-expands when no fixtures exist. Every empty-state
      rewritten to say what it is + what populates it (KW13). New
      `test_20260615_education_diagnostics_annotate.py` (8) + an axe open-`#helpModal`
      scan; the stale `No eval results yet` route-test copy assertion tightened to
      the new strings. Front-end + copy only — **no route, no LLM, no prompt
      (`PROMPT_VERSION` unchanged at `2026-06-13.1`), no dep, no migration.**
      ruff/mypy ✓ (162), pytest **1212/1212** incl. `-m ux` (flake did not recur).
      **Next: the v1.0.7 stream** ("The app knows itself" — governance extraction +
      self-documenting wiki + doc-grounded assistant + compliance pilot + plugin
      activation; see [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7). *(`chore/version-bump-v1.0.6`
      shipped 2026-06-15 — pyproject + CHANGELOG cut + tag `v1.0.6`, the PX-10 doc pass,
      and the dev-tier wiki diff-refresh.)*
- [x] **Corpus-item completers B.4/B.5** merged **before** the 6.5 sweep (so they're
      documented); **B.8 Part 1** outcome capture complete + verified end-to-end (the
      capture UI already exists — this *completes* it; unblocks the B.8-Part-2 +
      nursery learning layer).
      **Progress (2026-06-10):** the B.8 Part 1 half shipped via
      `feat/outcome-capture-complete` (see the Sprint 6.1 progress note above);
      end-to-end verification rides the Sprint 6.0 re-walk.
      **Progress (2026-06-12):** **B.4 landed** (`feat/experience-summary-item`) —
      per-role intro as a multi-variant `ExperienceSummaryItem` (migration `0008` +
      backfill), batched Haiku `recommend_experience_summaries`, Compose **opt-in
      "Add role intros"** toggle + per-role picker, full WYSIWYG into the generated
      résumé + JSON-resume preview, `PROMPT_VERSION → 2026-06-12.1`; also fixed an
      in-scope Compose-save clobber (`_togglePositioningPin` → canonical
      `_collectCompositionState()`). ruff/mypy ✓, pytest **1127/1127**. See
      RELEASE_ARC §Sprint 6.6 B.4 for the resolution note.
      **Progress (2026-06-13):** **B.5 landed** (`feat/skill-group-item`) —
      individual **`Skill` promoted to a Corpus Item** (the "skill clusters" framing
      dropped in an interactive clarification: no grouping). Migration `0009` (ALTER
      `skill` + `skill_tag` + backfill); **two** Haiku calls — `recommend_skills`
      (order/curate the approved set; auto-applied like bullets) + a user-authorized
      `suggest_skills` **grounded generator** (proposes corpus-evidenced JD skills as
      pending → approve/deny, human gate = grounding backstop); `composition_overrides`
      gains `pinned_skill_ids`/`excluded_skill_ids`/`skill_order`; reach **download +
      preview** via `_collect_skills` + `_apply_recommended_skills`;
      `PROMPT_VERSION → 2026-06-12.2`. Compose **Skills** card + Career-corpus **Skills**
      editor. Corpus-mode-only → unit + UX + byte-identity, no paid smoke. ruff/mypy ✓,
      pytest **1169/1169** incl. `-m ux`. **Closes Sprint 6.6.** See RELEASE_ARC
      §Sprint 6.6 B.5 for the resolution note. (Next: Sprint 6.5.)
- [x] **WS-4a landed early; WS-4b (after Sprint 6.6) before the 6.5 sweep** (the binding gate):
      `docs/system-model.md` (← seven-functions language) + the committed
      `docs/wiki/` skeleton + the `/wiki-*` skills exist; **the preserved
      excellence-walk source ([`excellence-walk/`](excellence-walk/)) is ingested
      into the wiki** (then may retire into its `raw/` layer); the code architecture
      is cold-ingested (`path:line`-grounded); a **user-facing wiki section is
      reserved so 6.5 authors INTO the wiki**. The code-ingest also **stamps
      `audience:` tags** + feeds the v1.0.7 doc-grounded assistant's memory
      substrate — design in [`memory-architecture.md`](memory-architecture.md).
      **✓ LANDED 2026-06-13** — WS-4b merged `a0a1cb2` (16 code pages cold-ingested,
      both tracked Mermaid drifts fixed); wiki diff-refreshed to HEAD on 2026-06-14
      (`chore/wiki-refresh-px-v106`).
- [x] **`audience:` tag convention authored** (the v1.0.6-retained slice of governance
      work) — the path→audience (`user`|`dev`) rules added to the wiki `SCHEMA.md` +
      stamped in WS-4b's cold-ingest, **before the 6.5 sweep**, since the assistant's
      access plane and the 6.5 user/dev split need it within this epic. **✓ done** —
      authored in `SCHEMA.md`; all content pages stamped (`overview.md`=`user`; the 24
      `pages/`=`dev`); user-education pages reserved for the 6.5 sweep. *(Full
      **governance extraction** — lifting the scattered canonical rules into one home —
      **moved to v1.0.7**, 2026-06-12: it depends on the wiki proving out, pairs with
      "the app knows itself," and is off v1.0.6's critical path. The ⚠ `@import`
      rule-access hard constraint + the 3 open sub-decisions move with it; see
      [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7.)*
- [x] **`docs/eval-stack-install-guide` (#17)** — the user-facing install/prepare
      guide authored from the excellence walk's **Q3** deliverable (preserved at
      [`excellence-walk/q3-downloads.md`](excellence-walk/q3-downloads.md)); all figures
      re-verified vs `pyproject.toml` + `install.md` + `CONTRIBUTING.md`. **Landed:** a
      plain-language **"What gets downloaded & why"** section in `docs/install.md`
      (Chromium ~150 MB to run the app; the optional grounding/eval stack ~3.2 GB flagged
      as a dev/power-user feature → links `CONTRIBUTING.md` "Grounding signal scorers", no
      dev commands inlined) + a README "what actually downloads" pointer beside "What gets
      saved" + a one-sentence in-app pointer on the dashboard `dashQuality` help body.
      The dev-tier provenance (`q3-downloads.md` + the `audience:dev` wiki page
      `non-dependency-downloads.md`) is unchanged. Docs + one help-copy line — no route,
      LLM, prompt, dep, or migration; `PROMPT_VERSION` unchanged.
- [x] **PX-02 — profile/website scrape re-wired** (`fix/profile-scrape-rewire`, now-v1.0.6
      PX band; `F-docs-04` / `AL-5`). The dead `scraper.fetch_profile_content` is wired to an
      explicit opt-in **"Fetch profile content"** action (`POST /api/users/<u>/profile/fetch`),
      caching to a **new** `Candidate.online_profile_text` column (alembic `0010`) surfaced via a
      `<candidate_web_presence>` prompt block (`PROMPT_VERSION 2026-06-13.1`). Kept **distinct**
      from the β.6 `profile_text` positioning summary so the résumé `basics.summary` can't be
      polluted (the prescription's literal `profile_text` cache target was already taken by β.6 —
      surfaced + re-scoped with the owner). Wiring pinned by a regression test
      (`tests/test_profile_fetch_route.py`). No new dep; `PROMPT_VERSION` bump. PX-03 egress-doc
      alignment stays for the later PX-03/05/07 doc batch. See CHANGELOG [Unreleased].
- [x] **PX-08 — network-egress falsifiability gate landed** (`test/egress-falsifiability`,
      now-v1.0.6 PX band; `F-qe-rel-02` P0 + `F-sec-01`). `tests/test_egress_allowlist.py`
      + the `pytest-socket` dev dep make charter **C-2** machine-falsifiable (gate **G-2**
      begins here — becomes a required CI check at v1.0.7) and keep **PX-01**'s Chart.js
      vendoring honest by construction. See CHANGELOG [Unreleased]; remaining band items per
      the review's `03-prescriptions/prescriptions.md` now-v1.0.6 list.
- [x] **PX-03/05/07 + stale-ref fold-in — disclosure-doc corrections** (`docs/disclosure-doc-corrections`,
      now-v1.0.6 PX band). Docs / metadata-only; no prompt/route/dep/migration. **PX-03** (`AL-7`; C-2):
      `SECURITY.md` egress enumeration corrected to the two real classes (Anthropic API; opt-in
      profile/website scrape), dropping the phantom "pasted-JD-URL fetch" class — `jd_url` is
      provenance-only, never fetched (verified against `scraper.py`; corroborated by the PX-08 gate);
      `vision.md` / `README.md` were already two-class-correct, left as-is. **PX-05** (`F-sec-11`, P1/S-1):
      the stale `Cooksey/resume` disclosure channel repointed to `amodal1/callback` in `CODE_OF_CONDUCT.md`
      + `.github/ISSUE_TEMPLATE/config.yml`. **PX-07** (`F-qe-rel-08` / `F-sec-07`; D-4 + P-3): the two
      hard human SLAs in `SECURITY.md` + `CODE_OF_CONDUCT.md` softened to best-effort. **Fold-in**
      (owner-authorized): the same stale `Cooksey/resume` target in `CONTRIBUTING.md` (`cd resume`),
      `.claude-plugin/plugin.json` (`homepage`), and `evals/schemas/context_set.schema.json` (`$id`)
      corrected in the same pass — **not** deferred to future one-file branches. Deliberately left: the
      plugin `author.name` (the maintainer, not a repo ref) and `name`/description (a v1.0.7
      project-rename concern). See CHANGELOG [Unreleased].
- [x] **PX-09 (+PX-14) — C-0 claims discipline (docs)** (`docs/c0-claims-discipline`, now-v1.0.6
      PX band; `F-vision-02` / `F-docs-03`, plus `F-eval-04` for PX-14). Docs-only; no
      prompt/route/dep/migration; `PROMPT_VERSION` unchanged. **PX-09**: reworded the absolute
      "The LLM cannot invent facts." / "No invention, ever" register on the highest-audience
      surfaces (`vision.md:50`/`:151`, `llms.txt:4`, `docs/wiki/overview.md`, `docs/system-model.md`)
      to mechanism-and-effort — a generation-prompt grounding check + the `grounding_overlap`
      *witness* metric that **measures**, best-effort not a categorical guarantee (C-0 bars
      LLM-behavior absolutes; owner recanted R2-4.2/R2-4.4). Consistency touch: each file's "Open
      revision points → point 4" self-reference no longer quotes the retired opening. **PX-14**
      (prescription: "rides PX-09's doc branch — COORDINATE"): corrected
      `docs/dev/GROUNDING_METRIC.md`'s four-part source union to the actual **three** sources
      (primary + supplementals + clarifications); typed edits are prompt-side, not a metric source
      element (doc follows `hardening.assemble_source_union`). See CHANGELOG [Unreleased].
- [x] **PX-13 — eval-smoke gate guard** (`test/eval-gate-guard`, now-v1.0.6 PX band;
      `F-qe-rel-05` KEEP/CONFIRMED; rides PX-08, done). Test + docs only; no behavior/prompt/
      route/dep/migration; `PROMPT_VERSION` unchanged. Affirms + guards the eval-quality
      regression gate so it can't silently rot. **Meta-test**: `tests/test_eval_runner.py::`
      `TestEvalGateGuard` pins **both** exit-`2` arms LLM-free (default `pytest`, no paid call) —
      a sub-`PASS_THRESHOLD` (4.0) score (`n_fail` path) **and** a threshold-passing score that
      drops past `REGRESSION_DELTA` (0.5) below a seeded baseline (`regressions` path, `n_fail==0`),
      matching `runner.py`'s `exit_code = 0 if (n_fail == 0 and not regressions) else 2`.
      **Do-not-regress note + CI scope**: reconciled `evals/README.md`, which had drifted — three
      spots (quick-start, exit-codes table, "Regression alerting") still claimed regressions were
      *informational* and didn't gate (true before commit `a60a008`'s "PR gate"; the narrative was
      never updated). Corrected to the real contract + a "machine-enforced" callout; recorded the
      CI scope (grounding-rubric-only ×3 synthetic fixtures, label-gated `eval`, no
      `continue-on-error`). See CHANGELOG [Unreleased].
- [x] `ruff + mypy + pytest + pytest -m ux` green; `chore/version-bump-v1.0.6` shipped 2026-06-15 (tagged `v1.0.6`).

> **Source preserved (no longer at-risk).** The excellence-walk drafts — the system-
> model/whys, the five-question deliverables (Q1–Q3), the sprint plan — were promoted
> from gitignored scratch into tracked **[`excellence-walk/`](excellence-walk/)** on
> 2026-06-08 and the originals deleted; git now holds them. WS-4a **ingests that
> folder into the wiki early** in this epic, after which the flat folder may retire
> into the wiki's `raw/` layer.

### Carry-forward ledger

> **One physical authoritative home** for tracked-deferred observations (charter
> [W-1](../governance/charter.md) "carry-forward discipline"). The **Open** subset is
> *cumulative* — every handoff renders it in full, not just the closing session's items,
> so nothing falls out of attention; at **~8–10 open items**, schedule a reduction sprint.
> **Resolved** items are kept with their resolution for the record (git holds the full
> diff); each keeps the stream it was discovered in. (Consolidated 2026-06-15 from the
> former per-stream "Discovered during the v1.0.x stream" sections — one home, not
> scattered subsections joined by pointers.)

#### Open

_Open count: 10 — at the top of the ~8–10 reduction-sprint threshold; the next stream should plan a reduction pass (the link-checker + CONTRIBUTING-drift items below are the natural pair to clear)._

- [ ] **S3 vector tier — labeled before/after eval (gate-override validation owed)** — the
      S3 `VectorSource` (Sprint 7.6, `feat/doc-assistant-vector`) was built **ahead of**
      RELEASE_ARC §4.7's formal eval gate at owner direction (the landed Stage-1 assistant
      tested *too literal / lacking semantic flexibility*). A coverage probe
      ([`scripts/vector_index_probe.py`](../../scripts/vector_index_probe.py)) corroborates
      qualitatively ([`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md): 1/12 hard lexical
      miss recovered; new semantic cites on 12/12), but the **judge-scored, labeled
      before/after relevance eval**
      (top-k with vs without S3) that confirms the tier earns its `numpy` + `model2vec`
      dependency footprint is **owed at the v1.0.8 test window** (Sprint 8.5, alongside
      `eval/live-shakedown-labels`). If it does not earn its keep it is cleanly removable —
      the embedder is injected and the tier is "on when available", so demote the deps to an
      optional extra or revert. Natural pair with the grounding-calibration item.
      _(discovered: v1.0.7 stream, 2026-06-16, `feat/doc-assistant-vector`.)_

- [ ] **Flaky UX test — `test_positioning_pin_preserves_title_pin`** — surfaced
      2026-06-13 on the docs-only `docs/flag-plugin-activation-v1.0.7` branch:
      [`tests/ux/regression/test_20260612_experience_summary_item.py`](../../tests/ux/regression/test_20260612_experience_summary_item.py)`::test_positioning_pin_preserves_title_pin`
      failed **once** in a full-suite run, then **passed on isolated re-run** — an
      intermittent UX-tier race (Playwright timing/selector), **pre-existing and not
      code-caused** (the same `main` code passed 1169/1169 twice the same day). Deferred:
      stabilize in a dedicated UX-tier pass (likely a missing settle/`to_be_visible`
      before the pin assertion); **not a release blocker.** _(discovered: v1.0.6 stream.)_
      **Update (2026-06-15):** did not recur across the v1.0.6 gate runs (1197/1197,
      1204/1204, 1212/1212) or the v1.0.7 governance-extraction gate; still deferred for a
      dedicated UX-tier stabilization pass.
      **Update (2026-06-16, `design/self-documenting-loop` gate):** a **second** UX-tier test of
      the **same intermittent-race class** surfaced —
      [`tests/ux/regression/test_20260613_skill_corpus_item.py`](../../tests/ux/regression/test_20260613_skill_corpus_item.py)`::test_compose_skills_card_drop_persists`
      failed **once** in the full suite (Playwright `wait_for_selector` timeout on
      `.compose-row.recommended`), then **passed on isolated re-run** (9.37s). The branch was
      **docs-only** (no `.py`/frontend touched — `git status` confirmed), so it is **not
      code-caused**. The deferred UX-tier stabilization pass now covers **≥2** flaky tests of this
      class (still one ledger item; not a release blocker).
      **Update (2026-06-16, `px/v107-band` gate):** neither recurred — the full suite ran
      clean (1290 passed) on the docs-only 7.8 branch; still deferred.
      **Update (2026-06-19, `fix/assistant-runs-without-user` gate):**
      `test_compose_skills_card_drop_persists` recurred **once** in the full suite (Playwright
      `wait_for_selector` timeout on `.compose-row.recommended`), then **passed clean on
      isolated re-run** (36s). The branch touched only the assistant route/client (unrelated to
      the Compose wizard), so **not code-caused**; still deferred for the UX-tier stabilization pass.

- [ ] **Grounding / hallucination metric — calibrated layers (B)** — the deterministic
      label-free **L0** slice shipped (`eval/grounding-metric-l0`:
      `hardening.compute_fabricated_specifics` + `hardening.assemble_source_union`, a
      `groundedness` composite riding every eval record). The **calibrated model-based
      layers (L1/L2)** + the never-run v1.0.4 live loop remain open — no labeled data
      exists yet (`evals/fixtures/real/` is empty). **Scheduled as v1.0.7 Sprint PV / PV-2**
      (`eval/grounding-calibration`; [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7). Detail:
      [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md); [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md)
      "calibrated layers (B)". _(discovered: v1.0.5 stream, 2026-06-05.)_

- [ ] **Portable-enforcement-core migration** — **DECIDED 2026-06-15: split** (the decision
      record is under Resolved below). The migration itself is pending: lift the portable
      guards (`require-feature-branch`, `block-merge-to-main`, `block-secrets`,
      `route-security-lint`, `ruff-changed`, `validate-context`) into a tool-agnostic shared
      core invoked by BOTH committed git-hooks (`core.hooksPath`/pre-commit) AND the Claude
      plugin, with CI as the server-side backstop. Follow-on **`feat/portable-enforcement-core`**
      clustered with the v1.0.8 gate epic when the git remote/CI activates (Sprint 8.7).
      Plan-mode lifecycle hooks stay Claude-only. _(discovered: v1.0.7 stream, 2026-06-15.)_

- [ ] **Periodic cross-document link / cite checker** — none exists or is planned. `wiki-lint`
      is `docs/wiki/`-scoped (`[[backlinks]]` + `path:line` existence only), so the
      `[text](path)` links across the contract docs **and the new `docs/governance/` pointers**
      are unchecked by any gate. The extract-don't-restate move multiplies those pointers →
      pointer-rot risk with no gate. Build a periodic link/cite gate (a CI step, or extend
      `wiki-lint` over `docs/governance/` + the contract docs); makes the §4.7 wiki-lint payoff
      actually true. Candidate reduction-sprint seed. _(surfaced 2026-06-15, `feat/governance-extraction`.)_
      **Confirmed out of scope for 7.3 (2026-06-16):** the `design/self-documenting-loop` design keeps the
      self-documenting loop **`docs/wiki/`-scoped** and explicitly does **not** absorb this cross-document
      link/cite checker — it stays this named separate follow-on (no new open item created;
      [`self-documenting-loop-design.md`](self-documenting-loop-design.md) §3 scope table).

- [ ] **`CONTRIBUTING.md` plugin-section drift** — "Working with the Claude Code plugin" still
      says "the `.claude-plugin/` directory holds the project's commands, agents, and hook
      scripts" and references "Step 5 / 8 / 9 of the OSS migration", but Sprint 7.1 **moved**
      commands/agents to the repo-root `commands/` / `agents/` (only hooks remain in
      `.claude-plugin/`). Same stale class as the `:87` fix landed this branch, but outside the
      governance-extraction scope — file, don't drive-by. _(surfaced 2026-06-15, `feat/governance-extraction`.)_

- [ ] **pytest-socket `UserWarning` ×2 (latent, benign)** — the egress-allowlist suite emits
      2 `UserWarning`s ("N passed, 2 warnings"); expected/benign (the autouse fn-scoped socket
      fixture), observed across recent gate runs. No action; surfaced here so it stops
      re-surprising future gates. _(filed in memory `reference-egress-allowlist-gate`.)_

- [ ] **Help-opener duplication** — the dashboard's `openDashHelp` ports `openHelpModal`
      (memory `reference-dashboard-education-ported-help`); deferred to a dedicated
      help-refactor branch. _(discovered: Sprint 6.5.)_

- [ ] **Assistant doc-coverage — author the how-to content the avatar draws on** — the
      doc-grounded assistant (Sprints 7.5/7.6) is grounded but **"woefully uninformed"**: only
      6 `audience: user` wiki pages exist (`overview` + the 5 Sprint-6.5 guides), so many
      "how do I…" questions (downloads, editing/refining, cover letters, multi-user, import
      mechanics, troubleshooting, the assistant itself) hit "I don't have that in my docs."
      The fix is **doc authoring** (user + dev how-to pages in `docs/wiki/`), distinct from the
      assistant **voice** prompt work (#2, its own `feat/` branch). Potentially multi-branch;
      the owner sequenced it "lastly," after voice softening. _(discovered: v1.0.7 stream,
      2026-06-17, `fix/v107-ui-polish-trio` scoping.)_

- [ ] **Avatar citation / reference formatting — consistency polish** — the doc-grounded
      assistant's voice/tone landed well (Sprint #2, `feat/avatar-voice-tone-tuning`), but owner
      testing (2026-06-19) found its **citations + references render inconsistently**: a Dev-mode
      answer mixed markdown links `[text](path)`, parentheticals, and numeric `[N]` markers in the
      same sentences, over a "Sources:" footer the `[N]` markers don't resolve to. A read-only
      trace pinned three server/prompt-side causes — **C1** the context renderer numbers units
      `[{i}]` (`analyzer.py:1538`) so the model mirrors `[N]` instead of the intended
      `[slug]`/`[path:line]`; **C2** the model invents markdown links (shown raw — the body is
      `textContent`), violating the prompt's no-bracketed-link rule; **C3** the footer ships
      **all** retrieved units (`analyzer.py:1595`), not the cited set, so the markers are
      unresolvable and grounding is overstated. Requirements + lever map + the scheme decision
      (A self-describing cites vs B numbered footnotes) are captured in
      [`avatar-citation-format-guidance.md`](avatar-citation-format-guidance.md). **Own branch,
      after the 7.9 tag** (v1.0.8-band; bumps `AVATAR_PROMPT_VERSION`); its R4 grounding check
      folds into the owed v1.0.8 labeled avatar eval (S3/grounding items above). _(surfaced
      2026-06-19 during `fix/assistant-runs-without-user`; capture only — its own branch.)_

#### Resolved

- [x] **Avatar voice/tone & behavior tuning — EXECUTION** — **DONE 2026-06-18 on
      `feat/avatar-voice-tone-tuning`.** Executed Part 4 of
      [`avatar-voice-tone-guidance.md`](avatar-voice-tone-guidance.md): friendly-guide
      `AVATAR_SYSTEM_PROMPT` (warmth via helpfulness, not instructed wit), near-mandatory cited
      refusal-as-doorway + the GitHub "report it" rung (URL only in L3 chrome, never model-emitted),
      calibrated middle, anti-sycophancy / anti-over-promise (ATS = parseability), connect-to-concern
      on reassurance-fishing; `AVATAR_PROMPT_VERSION 2026-06-16.1 → 2026-06-18.1` (same commit;
      `PROMPT_VERSION` untouched; avatar stays out of `_BASE_SYSTEM_PROMPTS`). **The bundled a11y
      defect is FIXED** — `#assistantAnswer` is no longer an `aria-live` region (was flooding screen
      readers per token); the single completion announcement rides `#assistantStatus`. Plus L3
      microcopy (plain intro, persistent empty state, blame-free errors, real GitHub link). Validated:
      ruff/mypy/pytest 1303 green incl. UX tier, new LLM-free deterministic tone checks, and a live
      Haiku §6.3 spot-check matrix (both modes × all scenario types; access plane held). Detail +
      the old-vs-new grounding-regression comparison in [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md)
      2026-06-18; memory [[project-avatar-voice-tone-guidance]]. **Tracked follow-on (NOT a new open
      item):** the live transcripts surfaced a *pre-existing* (present in the OLD prompt too, so not a
      regression) Haiku citation-format / line-number approximation fragility — the new cite-membership
      check is the mechanism to quantify it in the **v1.0.8 labeled avatar eval** (rides the test
      window / the grounding-metric ledger item below). _(surfaced: 2026-06-18, `docs/avatar-voice-tone-guidance`.)_

- [x] **Enforcement portability — security/quality hooks: tool-agnostic git-hooks/CI vs the
      Claude plugin** — **DECIDED 2026-06-15 on `design/governance-extraction` (7.2 design): SPLIT.**
      Fix PX-24/PX-28 hooks in place on `feat/governance-extraction`; migrate the portable rules
      (`require-feature-branch`, `block-merge-to-main`, `block-secrets`, `route-security-lint`,
      `ruff-changed`, `validate-context`) to a tool-agnostic **shared enforcement core** invoked by
      BOTH committed git-hooks (`core.hooksPath`/pre-commit) AND the Claude plugin, with CI as the
      server-side backstop — on a **follow-on branch clustered with the v1.0.8 gate epic** (PX-19/20/25)
      when the git remote/CI activates at Sprint 8.7. Plan-mode lifecycle hooks stay Claude-only.
      Full rationale + tradeoffs in [`governance-extraction-design.md`](governance-extraction-design.md) §5.
      Tracked follow-on: **`feat/portable-enforcement-core`** (or fold into the v1.0.8 gate epic).
      _Original framing (retained for the record):_ surfaced 2026-06-15 on `chore/plugin-activation`
      (Sprint 7.1) when deciding whether to migrate the 10 `.claude-plugin/hooks/` into the plugin
      manifest. The plugin surface (commands/agents/hooks) is
      Claude-Code-only, and the committed CI ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml))
      is **latent until the GitHub remote at sprint 8.7** — so today the Claude hooks are the
      only *active* mechanical enforcement; non-Claude agents (Codex/Cursor/Aider/llama.cpp)
      rely on `AGENTS.md` (read by any agent) alone. The **portable** rules' enforcement
      (`require-feature-branch`, `block-merge-to-main`, `ruff-changed`, `block-secrets`,
      `route-security-lint`) arguably belongs in tool-agnostic **git-hooks
      (`pre-commit`/`pre-push`) and/or CI** — which protect every agent *and* human — rather
      than a Claude-only plugin; only the inherently-Claude hooks (plan-mode lifecycle,
      `wiki-freshness-reminder`) clearly stay plugin-side. 7.1 deliberately left **all** hooks
      wired in `.claude/settings.json` (zero risk, no deeper Claude-coupling) pending this
      decision — the enforcement-side counterpart to governance's tool-agnostic *rule*
      consolidation. Fully reversible either way.

- [x] **`/api/answer-clarifications` overwrites the whole answers map — iterate
      submit drops analyze-round answers from the iterated context** — surfaced
      2026-06-10 while building `feat/outcome-capture-complete` (KW7 memory write
      path). `_collectIterateClarifyAnswers` ([app.js](../../static/app.js))
      collects **only** `#iterateClarifyQuestions` textareas, but the route does
      `context_set["clarifications"] = cleaned` (full replace, [app.py](../../app.py)
      `submit_clarifications`) — so after an iterate-round submit, the
      analyze-round answers vanish from the new context file and generate (iter≥1)
      loses them as ground truth. The JS comment at the iterate call site claims
      "merges by id — prior answers stay intact", which the route does not do.
      The candidate-memory mirror is unaffected (additive: DB rows persist even
      when the context map loses entries). **Scheduled** as load-bearing evidence
      on the `fix/clarify-generates-bullets` (KW4) row,
      [`RELEASE_ARC.md`](RELEASE_ARC.md) §Sprint 6.1 — investigate there, not as a
      drive-by. **Resolved 2026-06-11** on `fix/clarify-generates-bullets` (KW4):
      the route now merges by id (default `merge:true`), the skip path passes
      `merge:false`, and a two-round regression test guards it. See CHANGELOG
      [Unreleased].
- [x] **`application_run.generated_cover_letter_md` never populated** — observed
      2026-06-10 in the e2e walkthrough DB (run row has resume md + bullets +
      titles + ATS json, but cover-letter md is empty despite a generated +
      downloaded cover letter). Small run-persistence gap in the
      `persist_corpus_generation` write-back path; matters once the learning
      layer (B.8 Part 2) wants to correlate outcomes with cover letters.
      **Scheduled** as `fix/run-cover-letter-persistence` in
      [`RELEASE_ARC.md`](RELEASE_ARC.md) §Sprint 6.1 — land within v1.0.6 so the
      signal is captured while real outcome data accrues this epic (rows generated
      now without it can't be backfilled). **Resolved 2026-06-11** on
      `fix/run-cover-letter-persistence`: the gap was exclusively the detached
      `POST /api/generate-cover-letter` route (wrote the letter to disk + context
      but did **no** DB write; `/api/generate` with `with_cover_letter=True`
      already persisted). The route now writes `generated_cover_letter_md` onto
      the same run row the résumé wrote to (`context_set["application_run_id"]`)
      via a new surgical single-column write-back
      (`db.persist_run.persist_cover_letter_md` + `app._persist_cover_letter_to_db`)
      — deliberately **not** `persist_corpus_generation`, which would have nulled
      the already-saved résumé md. Best-effort, corpus-backed mode only; no prompt
      change, no route, no new dep, no migration. Unit no-clobber + route
      end-to-end tests; pipeline/data-flow diagrams synced. See CHANGELOG
      [Unreleased].

- [x] **Architecture Mermaid-diagram drift (two spots) — RESOLVED by WS-4b** _(discovered:
      v1.0.5 stream, 2026-06-11)_ — surfaced during `fix/wizard-flow-polish`
      (KW8) review. Both were pre-existing **doc-only** inaccuracies (no code/behavior
      bug), so deliberately **not** fixed on a feature branch:
      1. **Step-2 clarify action mislabeled** — `docs/diagrams/pipeline.mmd` (~L45)
         and the embedded copy in `docs/architecture.md` (~L89) read
         `U->>FE: click GET INTERVIEW QUESTIONS` under "Step 2 — Clarify"
         (`POST /api/clarify`), but the real Step-2 button (`#btnClarify`) is
         **"Get clarifying questions"** and always was — "interview" never matched
         it. Correct to `GET CLARIFYING QUESTIONS`. (The Step-6 iterate flow is
         labeled "ITERATE CLARIFY" + "follow-up questions" and is already accurate;
         KW8 renamed `#btnIterateClarify` to "Get follow-up questions" and needed no
         diagram change — which is *why* this Step-2 line is unrelated drift, not a
         KW8 leftover.)
      2. **Cover-letter artifact node out of sync between the two data-flow copies**
         — flagged in the 2026-06-10 `fix/run-cover-letter-persistence` handoff (was
         chat-only until now): the embedded data-flow diagram in
         `docs/architecture.md` lists `cover_TS.docx / .pdf / .md` for the
         cover-letter artifact while `docs/diagrams/data-flow.mmd` lists only
         `cover_TS.docx`. Harmless, pre-dates recent work.
      **RESOLVED — verified 2026-06-15:** `wiki/cold-ingest-code` (WS-4b, merge `a0a1cb2`)
      reconciled both spots while re-reading the architecture to cold-ingest it —
      `docs/diagrams/pipeline.mmd:45` now reads "GET CLARIFYING QUESTIONS" (matches
      `docs/architecture.md:89`) and `docs/diagrams/data-flow.mmd:77` now lists
      `cover_TS.docx / .pdf / .md` (matches `docs/architecture.md`); recorded in
      [`docs/wiki/log.md`](../wiki/log.md).

- [x] **Diagnostics console → interactive self-tuning loop (the "finish the
      faceplate" arc)** — sourced 2026-06-06 from a walkthrough finding
      (user-approved). The `feat/diagnostics-console-redesign` + `feat/annotation-tab`
      surfaces shipped but stop at CLI hand-offs (grounding only via the
      `--grounding-signals` flag, Tuning tab a stub, `collate` returns a paste-this
      `run_command`). This arc completes them into a browser-driven loop (produce →
      annotate → grounding-score → run eval → A/B → see deltas); the irreversible
      **promote** stays the agent's job. Authoritative sequence + acceptance:
      [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4 "Diagnostics console — interactive
      completion". **Status (2026-06-07):** Steps 1–2 shipped. Step 1
      `feat/grounding-scorers-in-console` (merged `bc29a07`) made the scorers reachable
      from the Annotate tab (opt-in bootstrap + "Score grounding" backfill) and browser
      bootstraps now capture a `seed.json`; Step 2 `feat/run-eval-from-console` extracted
      `evals.runner.run_suite` (the importable core `main()` is now a thin wrapper over)
      and added the localhost SSE `POST /api/eval/run`, a Quality-tab "Run eval" control,
      and an Annotate-tab "Run this fixture" button — the eval is now runnable from the
      browser; Step 3 `feat/tuning-tab-ab` (2026-06-07) replaced the Tuning stub with a
      real in-browser candidate-vs-baseline A/B — a dedicated localhost SSE
      `POST /api/tune/run` drives `run_suite` twice (baseline + candidate via
      `analyzer.prompt_overrides()`) and renders the `evals.tune` delta table; the
      irreversible **promote** stays the agent's job (no route edits `analyzer.py`).
      Step 4 `docs/tuning-loop-discoverability` (2026-06-07, docs only) closed the arc:
      the in-app diagnostics-modal/pill/settings copy now advertises the interactive
      loop, the end-to-end console walkthrough landed in [`evals/README.md`](../../evals/README.md)
      (the dev-doc home) with [`walkthrough.md`](../walkthrough.md) carrying a flag +
      link to it, and [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) was updated to note
      the label-producing loop is now browser-driven. **All four steps shipped — arc
      complete.**

- [x] **Standalone one-click corpus-seed export (`feat/seed-export-button`)** —
      flagged 2026-06-07 during the `docs/tuning-loop-discoverability` close-out.
      Generating a corpus `seed.json` should be a one-click, **LLM-free** unit, but
      today the only in-browser trigger is bundled inside the **paid** Annotate-tab
      bootstrap (`POST /api/annotation/bootstrap`); the deterministic
      `python -m scripts.export_corpus_seed --user <name>` CLI exists but is the only
      no-cost path. Proposed: a small **localhost** route + an Annotate-tab button
      calling `scripts.export_corpus_seed.export_seed` directly — deterministic, no
      paid call, reusing the existing write-guard (`_safe_username` + `_within(seed,
      ANNOTATION_ROOT)` + `secure_filename`, the same guard the bootstrap/score routes
      use). Separate functional unit from the docs arc; **next small `feat/` branch**
      after this docs branch (user-approved sequencing 2026-06-07).
      **Status (2026-06-07): shipped** via `feat/seed-export-button` (commit
      `3aa6a45`). Added the synchronous, localhost-only `POST /api/annotation/seed/export`
      (reads the live DB via `export_seed`, no model calls, no SSE) + an Annotate-tab
      "Export seed (no LLM)" button distinct from the paid "Run bootstrap"; factored a
      shared `_write_seed_json` writer out of the bootstrap route (bootstrap behavior
      byte-identical). Security trio enforced; unknown user → 400, config-only user with
      no corpus → 409. Tests in `TestSeedExport`; no `PROMPT_VERSION` bump, no new dep.

- [x] **Compose custom bullet order visually reverts on reload when an
      experience has no LLM recommendations** — surfaced 2026-06-04 while
      building the `feat/playwright-ux-suite` bullet-drag regression test. The
      saved `composition_overrides.bullet_order` round-trips correctly through
      `POST`/`GET /api/applications/<id>/composition`, and `generate()` still
      honors it (`_stable_user_prefix`), so the *persisted* order is intact.
      But [`_renderComposeCard`](../../static/app.js) routes
      no-recommendation experiences through `_dropoffPick`, which re-sorts the
      fallback bullets by **score** — so the *on-screen* order reverts after a
      Compose reload even though the data is correct. The common path
      (recommendations present → bullets land in the `visible` set → the GET
      array order is preserved) is unaffected, and the bullet-drag regression
      test covers that path. Fix belongs in a future Compose-render branch:
      honor the GET array order on the no-recommendations fallback path too,
      instead of re-sorting by score. **Now scheduled as v1.0.6 Sprint 6.1**
      (`fix/compose-order-no-recommendations`; [`RELEASE_ARC.md`](RELEASE_ARC.md)
      §Phase 4.5). **Resolved 2026-06-11** on
      `fix/compose-order-no-recommendations`: `_renderComposeCard` now honors the
      GET-returned order on the no-recommendations fallback (the `in_custom_order`
      bullets, already in saved sequence) when `has_custom_order`, instead of
      re-deriving a score sort via `_dropoffPick`. Render-only fix — no backend
      change, no `PROMPT_VERSION` bump, no new dep. UX regression
      `tests/ux/regression/test_20260611_compose_order_no_recommendations.py`; the
      common path stays guarded by `test_20260604_bullet_drag_reorder.py`. See
      CHANGELOG [Unreleased].

The v1.0.1 item list below was **reconciled in place at the v1.0.3 tag
(2026-06-02)**: completed items are checked; still-open items are flagged
`→ OPEN` with their current owning release. The v1.0.0 release landed in
commit `075d830` (with subsequent template curation, paged.js pagination,
and docs reworks landing on the same branch before tag); v1.0.1 was the
first follow-up release.

### Must do before tag (shipping blockers)

- [x] **~~Manual fresh-clone verification~~** — ✅ done (user-confirmed
      2026-06-02): clean-directory clone → `pip install -e .` +
      `python -m playwright install chromium` + `python app.py` → one
      application completed end-to-end. Evergreen — re-run at the v1.1.0
      public-release cut (risk register D.4 below).
- [x] **~~Eval baseline check~~** — ✅ verified 2026-05-26.
      `python evals/runner.py --suite synthetic --subset smoke`
      run twice (cost ~$0.79 across both); second run clean with
      all three synthetic fixtures at or within ±0.0 of
      `evals/results/baseline_v1.json` (data-scientist-junior 4.8
      = 4.8; pm-senior 4.8 = 4.8; sre-mid-level 4.7 = 4.7). First
      run surfaced a transient judge JSON parse failure on
      data-scientist-junior; see the "Judge JSON parse failures
      mis-categorized as `status=ok`" entry under "Should do" for
      the one-line `evals/runner.py:289` follow-up that would have
      prevented the false-positive regression alarm.
- [x] **~~Quality gate~~** — ✅ verified 2026-05-28. `ruff check .` +
      `mypy .` (81 files, no issues) + `pytest` (637 passed) all
      clean on branch `chore/quality-gate-version-bump-v1.0.1`.
- [x] **~~`pyproject.toml` version bump~~** — ✅ done 2026-05-28.
      `version = "1.0.1"` in [`pyproject.toml:7`](../../pyproject.toml).
      Landed in `chore/quality-gate-version-bump-v1.0.1`.
- [x] **~~`CHANGELOG.md` flip~~** — ✅ confirmed 2026-05-28. The
      `[1.0.1] — 2026-05-28` section was written ahead of time and is
      correct; `[Unreleased]` placeholder is clean. "Resume Optimizer"
      name in line 3 fixed to "callback." in this branch.
- [ ] **Push to GitHub + verify the `https://github.com/amodal1/callback`
      URL resolves** **→ OPEN, owner v1.1.0** — pushed **when the user is
      ready to push the v1.1.0 public-release tag**; the repo stays
      local-only until then (no `origin` remote configured). Action at the
      v1.1.0 cut: create the GitHub repo (public, name `callback`, under
      `amodal1`), `git remote add origin
      git@github.com:amodal1/callback.git`, push `main` and the
      release tag, then verify that `pyproject.toml` Homepage /
      Repository / Issues / Changelog URLs and `README.md`/
      `docs/install.md` clone instructions all resolve.

### Should do (v1.0.1 polish; document if skipped)

- [x] **Step 6 (Output) redesign** **✓ SHIPPED v1.0.5** (`feat/step6-redesign`,
      merged `43a60dc`; cover-letter styling landed with `feat/cover-letter-formats`
      `5fa186b`)
      (`feat/step6-redesign`, RELEASE_ARC §Phase 4) — surfaced during the
      v1.0.0 review: cut the obsolete tabs + raw/rendered toggle
      (replaced by paged.js preview); preview at the top of
      the step; edit-raw via modal; Changes → info-icon modal;
      cover letter → single "+ Generate" button until generated.
      **Cover-letter styling decisions (user-confirmed 2026-05-26
      for the B-phase work):**
      - **Header treatment:** terser than the résumé — business-
        letter style. No big name banner / contact bar repeat;
        use fonts appropriate to (i.e., matching) the chosen
        résumé template, but plain — nothing fancy.
      - **Body line spacing:** business-letter dense (single-
        spaced or near it), NOT breathy / generous line-height.
      - **Addressee block** (`Hiring Manager,` / company name /
        date): rendered **inline** with the body — no separately
        styled block, no boxed treatment.
- [x] **~~BACK / Continue spacing polish on Compose~~** — ✅ verified
      2026-05-28 (commit `8d59361`). Spacing confirmed correct; no
      visual change needed. Listed in PRODUCT_SHAPE §10 as deferred
      from v1.0.0.
- [x] **~~`docs/install.md` updated~~** — ✅ resolved 2026-05-28.
      Test count updated (`627+` → `637+`); Windows section now
      covers PowerShell `$env:` syntax for the API-key step, a
      `python -m pip` fallback for Windows Store Python installs,
      and the `sysdm.cpl` shortcut for setting a permanent env var.
- [x] **~~Accessibility scan of all user-facing documentation~~** —
      ✅ resolved 2026-05-28. Full audit of
      [`README.md`](../../README.md),
      [`docs/install.md`](../install.md),
      [`docs/walkthrough.md`](../walkthrough.md),
      [`docs/walkthrough_example.md`](../walkthrough_example.md),
      [`vision.md`](../../vision.md), and the 10 PNGs in
      [`docs/screenshots/`](../screenshots/).
      - **Alt text** — all 10 images have substantive, descriptive
        alt text. No "a screenshot" placeholders.
      - **Mermaid diagrams** — the second diagram already had
        "Read this top-down: …". Added an equivalent
        "Read this left-to-right: …" prose summary immediately
        after the first (user-flow) diagram in `walkthrough.md`.
      - **Heading hierarchy** — no skipped levels in any file.
      - **Link text** — no "click here" / "see this" patterns.
      - **Color-only meaning** — first diagram: explicit 4-class
        text legend. Second diagram: semantic subgraph labels
        encode meaning independently of color.
      - **Tables** — all use markdown `| Header |` syntax;
        no hand-rolled HTML tables found.
- [x] **~~Doc-vs-UI label drift on the corpus import button~~** —
      ✅ resolved 2026-05-26. Button renamed
      `+ Drop résumé (AI extract)` → `+ Import résumé` (cleaner
      action verb than "Drop" which conflated drag-and-drop with
      the action itself; the parenthetical leaked the AI-extract
      implementation detail into a button label). Live docs
      ([`docs/walkthrough.md`](../walkthrough.md),
      [`docs/install.md`](../install.md),
      [`docs/ux/screenshot_capture.md`](../ux/screenshot_capture.md))
      synced to the new label. The audit at
      [`docs/ux/onboarding_audit_2026-05-25.md`](../ux/onboarding_audit_2026-05-25.md)
      is left as the historical record (the audit accurately
      reports the doc/UI mismatch as it existed on 2026-05-25).
      The internal API route `/api/users/<user>/import-legacy`
      keeps its name — route rename is a separate cleanup, v1.1.
- [x] **~~Bullet-dedup gap in corpus re-import~~** — ✅ resolved
      2026-05-26. Changed `_merge_into_existing_experience` in
      [`onboarding/import_legacy.py`](../../onboarding/import_legacy.py)
      to dedup on **normalized bullet text** instead of
      `(source, text)`. The old key missed same-file re-imports
      because the source flips from `primary:<file>` to
      `supplemental:<file>` on the merge path, so the same text
      under two different sources slipped through as a "new"
      bullet. The new key matches regardless of source; different
      phrasings from different files still survive (they have
      different normalized text). Test
      `test_merge_dedupes_identical_bullet_text_across_sources`
      in [`tests/test_onboarding_import_legacy.py`](../../tests/test_onboarding_import_legacy.py)
      pins the new behavior; all 24 tests in that file pass.
- [x] **~~Wizard rail step buttons don't re-enable after prior step
      completes~~** — ✅ resolved 2026-05-26. Added a
      `_wizardRender()` call in `runAnalysis()`'s success path
      (after `lastContextPath` is set), so the rail picks up
      step 2 as `_wizardReachable` immediately. `runGeneration()`
      was already calling `_wizardAdvanceTo(6)` (which includes
      a `_wizardRender`), so the step-6 side of the bug was
      already covered — the bug only existed on the analyze →
      step 2 transition.
      [`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py)
      still navigates forward via the in-flow Continue buttons;
      that's fine and matches the real-user happy path, but rail
      clicks would now work too.
- [x] **Playwright UX clickthrough regression suite** **✓ SHIPPED v1.0.5**
      (`feat/playwright-ux-suite`, merged `aeb3e51`; `pytest -m ux` = 12 tests:
      happy-path-stubbed flows + the backfilled 2026-05-26/2026-06-04/2026-06-06
      regression tests, shared `ui_pages/` driver)
      (`feat/playwright-ux-suite`, RELEASE_ARC §Phase 4) —
      surfaced during the screenshot-capture pass (2026-05-26). The
      screenshot script at
      [`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py)
      drives the wizard end-to-end and incidentally exposed
      several UI bugs above (rail re-enable, corpus render,
      bullet-dedup gap, label drift) that the existing `pytest`
      unit suite doesn't catch because they live in JS render
      paths, not Python. Build a proper UX regression suite
      under `tests/ux/` so future PRs can't reintroduce these
      classes of bug. Structure (industry-standard
      Playwright + Page Object Model):
      - **`tests/ux/conftest.py`** — session Flask fixture on
        an ephemeral port; per-test browser context with a
        **console-error sentinel** (any `pageerror` or
        `console.error` fails the test — this alone would have
        caught the silent corpus-render failure); autouse
        fixture that isolates `configs/` / `resumes/` /
        `output/` + cleans demo-user DB rows on teardown.
      - **`tests/ux/pages/`** — one POM class per panel
        (`user_picker.py`, `corpus.py`, `wizard_step1_job.py`
        through `wizard_step6_output.py`, `cover_letter.py`).
        Mechanical refactor of the navigation already in
        [`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py).
      - **`tests/ux/fixtures/`** — `factories.py` (lift
        `write_priya_docx` + `PRIYA_JD` from the screenshot
        script); `api_stubs.py` (`page.route()` handlers
        returning canned LLM JSON for fast/free runs); a JD
        corpus with diverse shapes (Kafka backend, frontend,
        junior IC, exec).
      - **`tests/ux/flows/`** — full multi-step journeys:
        happy-path-stubbed, happy-path-real-llm, navigation
        (forward/back/jump/rail-disabled invariants),
        interruptions (reload mid-LLM, user-switch
        mid-wizard, close+reopen), state-reset, iteration
        loop (`parent_context_path` chain integrity).
      - **`tests/ux/error_handling/`** — stubbed API 5xx /
        timeout / offline / invalid input / concurrent-tab
        writeback. The category most likely to surface
        regressions.
      - **`tests/ux/regression/`** — one test per shipped
        bug, named `test_<YYYYMMDD>_<slug>.py`, never
        deleted. Backfill the five bugs from the 2026-05-26
        pass first (rail re-enable, corpus render, bullet
        dedup, doc-vs-UI label, plus any others the
        Playwright debug pass surfaces).
      - **`tests/ux/a11y/test_axe_smoke.py`** —
        `@axe-core/playwright` against each panel; no
        serious/critical violations.
      Two-tier execution via pytest markers (add `ux` +
      `real_llm` to `pyproject.toml`'s existing `markers`
      list):
      - `pytest -m "ux and not real_llm"` — stubbed, ~30s,
        $0; runs on every PR.
      - `pytest -m "ux and real_llm"` — one happy-path
        real-API smoke, ~$0.30 + ~6min; gated on `.api_key`
        presence (skip if absent so forks don't fail).
      Wire `pytest -m ux` into `.git/hooks/pre-push` (or a
      `make pre-pr` target) and document in
      [`CONTRIBUTING.md`](../../CONTRIBUTING.md) as the standard
      pre-PR ritual. **Defer if time-bound:** land the harness
      + `conftest.py` + one happy-path-stubbed test in v1.0.1;
      backfill the `regression/` + `error_handling/` +
      `flows/` tests across v1.0.1 and v1.1 as the screenshot-
      pass bugs get fixed (each fix lands with its regression
      test). **Prereq:** the screenshot script itself must
      stabilize first (currently being debugged) — the POMs
      lift directly from its navigation logic, so a moving
      script means churning POMs.
- [x] **~~Corpus tab render-after-refresh bug~~** —
      ✅ resolved 2026-05-27 (downstream of thread-race fix).
      Root cause confirmed: the `/personas` 500 thread-race
      (`fix/personas-500-thread-race`, commit `a32bc1b`) was
      corrupting upstream state on first user-select after restart,
      leaving `_corpusExperiences` in a bad state before
      `_renderCorpusList` ran. After the `threading.Lock()` fix
      landed, the corpus tab renders cards correctly on first load
      with no `console.error`. The try/catch instrumentation from
      `16d7ad4` stays in place as a safety net for future regressions.
- [x] **~~`/personas` 500 on first user-select after server restart~~** —
      ✅ resolved 2026-05-27. Added `threading.Lock()` around the
      check-and-init block in [`db/session.py`](../../db/session.py)
      `init_db()` (three lines: `import threading`, `_init_lock =
      threading.Lock()` at module level, `with _init_lock:` wrapping
      the entire check-then-`_initialized_paths.add()` sequence). The
      race: `onUserSelect` fires multiple concurrent requests on first
      user-select after restart; all threads saw an empty
      `_initialized_paths`, all attempted `command.upgrade()`
      simultaneously, corrupting alembic's module-level globals. The
      lock makes the check-and-add atomic — only the first thread runs
      `upgrade()`; the rest short-circuit once it completes. Branch
      `fix/personas-500-thread-race`.
- [x] **~~Judge JSON parse failures mis-categorized as `status=ok`~~** —
      ✅ resolved 2026-05-26.
      [`evals/runner.py:289`](../../evals/runner.py) now returns
      `{"score": 0, "reasons": [...], "raw": raw, "status": "judge_error"}`
      so the existing `judge_error` path in `_detect_regression` /
      summary logic skips these records correctly. New test
      `test_unparseable_json_marks_status_judge_error` in
      [`tests/test_eval_runner.py`](../../tests/test_eval_runner.py)
      pins the behavior; all 25 tests in that file pass. The
      false-positive WARN observed in
      [`evals/results/20260526_170400Z.jsonl`](../../evals/results/20260526_170400Z.jsonl)
      (`data-scientist-junior × grounding`, -4.8 delta) won't
      recur — re-running the smoke pass should produce a clean
      result.
- [x] **~~Re-baseline eval scores for v1.0.1~~** — ✅ superseded 2026-06-02
      by the **v1.0.2 schema-3 baseline** (`eval/baseline-v1-0-2`; TUNING_LOG
      "BASELINE — v1.0.2 — 2026-05-28"): five back-to-back synthetic runs at
      the shipping `PROMPT_VERSION 2026-05-24.4` replaced the stale
      `2026-05-12.1`-sourced baseline, resolving the apples-to-apples concern
      this item raised. Original detail retained below for the audit trail.
      [`evals/results/baseline_v1.json`](../../evals/results/baseline_v1.json)
      was sourced from
      [`evals/results/20260513_221926Z.jsonl`](../../evals/results/20260513_221926Z.jsonl)
      on `prompt_version=2026-05-12.1` (recorded 2026-05-25), but
      [`analyzer.py`](../../analyzer.py)'s current `PROMPT_VERSION`
      is `2026-05-24.4` — three prompt revisions shipped with
      v1.0.0 between the baseline source-run and tag. The
      baseline file's own `notes` field already calls this out
      ("a re-baseline is recommended early in v1.0.1 once the
      streaming/split-analyze changes from docs/dev/perf/PERF_ANALYZE.md
      land"). The smoke pass on 2026-05-26 showed the two
      successfully-graded fixtures essentially unchanged
      (`pm-senior`: 4.8 = 4.8; `sre-mid-level`: 4.8 vs 4.7,
      Δ=+0.1), so the drift appears benign — but the "Eval
      baseline check" Must-do at
      [`docs/RELEASE_CHECKLIST.md:32-35`](RELEASE_CHECKLIST.md)
      is comparing against scores no longer apples-to-apples
      with shipping code. Action: once the
      [`evals/runner.py:289`](../../evals/runner.py) judge-error
      fix lands AND the v1.0.1 prompt landscape is final (R2
      streaming work either in or explicitly deferred), run
      the full synthetic suite (`python evals/runner.py --suite
      synthetic`, ~$1.50, all five rubrics × three fixtures)
      and replace `baseline_v1.json` with a v1.0.1 baseline.
      Document the cut as a dated entry in
      [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md) per its
      four-question structure. **Defer:** v1.0.1 CAN ship
      against `baseline_v1` (smoke noise from the judge-error
      bug aside, the underlying scores are stable); the
      re-baseline is hygiene, not a blocker — slip to early
      v1.1 if v1.0.1 ships fast.
- [x] **Walkthrough documentation pass — three fixes** —
      ✅ resolved 2026-05-27.
      (a) Corpus→Application transition paragraph added to
      `docs/walkthrough.md` between Setup and Step 1 —
      instructs the reader to click the **Application** tab and
      select Step 1 in the wizard rail before pasting a JD.
      (b) `scripts/capture_screenshots.py` `run_step2()` now
      calls
      `page.locator("#clarifyQuestions").scroll_into_view_if_needed()`
      + `wait_quiet(page, 300)` before `cap()`, so re-running
      the script will produce a properly-scrolled PNG showing
      the actual questions.
      (c) `docs/walkthrough_example.md` confirmed intentional —
      purpose statement at lines 1–14 establishes it as the
      Priya companion to the abstract walkthrough; no file
      change needed.
- [x] **~~CSP `unsafe-eval` violation on script execution~~** —
      ✅ investigated 2026-05-28. Full grep of `static/app.js`,
      `static/vendor/paged.polyfill.js` (33 K lines), and
      `templates/index.html` found **zero** instances of `eval(`,
      dynamic-Function constructor, or string-form
      `setTimeout`/`setInterval`. The app sets **no**
      `Content-Security-Policy` response header; there is no
      server CSP to be violated. Root cause of the original
      dev-console message: Chrome surfaces sandbox-block events
      using CSP-style error text. Before the 2026-05-27 sandbox
      fix ("`Sandboxed iframe blocks script execution ×17`"
      item above), the preview iframes carried `sandbox` without
      `allow-scripts` — effectively `script-src 'none'` — which
      blocked paged.js and appeared as an `unsafe-eval` violation
      in the console. The sandbox fix (`allow-scripts
      allow-same-origin`) resolved it. The absence of a real
      `Content-Security-Policy` header is documented as an
      accepted-risk entry in [`SECURITY.md`](../../SECURITY.md)
      (appropriate for localhost-only v1.0.1; add before any
      networked deployment).
- [x] **~~Sandboxed iframe blocks script execution ×17~~** —
      ✅ resolved 2026-05-27. Both preview iframes (`#livePreviewFrame`
      in the Compose step and `#outputPreviewFrame` in Step 6) now
      use `sandbox="allow-scripts allow-same-origin"`, which lets
      paged.js polyfill execute inside the frame. `allow-same-origin`
      stays so `_updatePreviewPageCount` can read
      `frame.contentDocument` for the page-count chip; the two flags
      together effectively neutralize the sandbox per spec, but the
      iframe content is our own generated HTML (corpus + persona
      template + injected paged.js polyfill), not user-supplied
      markup — security posture is acceptable for v1.0.1 with a
      load-bearing comment at the call sites explaining the
      tradeoff. A future refactor could host paged.js outside the
      iframe and message-pass for true sandboxing (v1.0.2 or v1.1
      polish).
      **Downstream resolution:** this also closes the
      "Template preview pagination — blank pages between sections"
      tracked item below — paged.js is what handles intelligent
      `page-break-inside: avoid` layout; the blanks were the
      browser's naive fallback when paged.js couldn't run.
- [x] **~~Form fields without `id` or `name` attribute~~** —
      ✅ resolved 2026-05-28 (commit `b904a87`). Added `sr-only`
      `<label for="…">` elements for the six new-user form fields
      (`newUsername`, `newName`, `newEmail`, `newPhone`,
      `newLinkedin`, `newWebsite`) and the `memoryKindFilter`
      select in [`templates/index.html`](../../templates/index.html).
      All seven Chrome-flagged "violating nodes" now have
      associated labels; browser-autofill and screen-reader
      association restored. No functional change.
- [x] **~~Two `POST /api/analyze 409`s observed during Corpus-tab
      session~~** — ✅ investigated + logged 2026-05-28. Code
      audit confirmed:
      - **Single 409 trigger in `/api/analyze`:** both
        `_run_analysis_corpus_backed` and its streaming sibling
        return 409 only when `build_context_set_from_db` raises
        `ValueError` — i.e., the selected user has no `Candidate`
        row in the DB yet. Message: `"No candidate with
        username=..."`. No other 409 branches exist in these two
        functions.
      - **Corpus tab cannot implicitly call analyze:** `onUserSelect`
        fires `loadConfig`, `refreshApplications`,
        `_loadPersonaOptions`, `wizardInit` — none touch
        `/api/analyze`. The Corpus-tab 409 handler
        (`refreshCorpus`, `refreshMemory`, `refreshApplications`)
        is a *separate* set of routes, not analyze.
      - **Conclusion: expected behavior.** The two 409s were
        triggered by a user clicking Analyze for a user not yet
        onboarded (or by the post-onboarding-modal retry path).
        The JS correctly responds by opening the onboarding modal
        (`openOnboardingModal(runAnalysis)`); after successful
        import the analyze call retries and succeeds.
      - **Logging added** (commit on this branch): both 409
        branches now emit `logger.warning("[analyze 409] user=X
        needs_onboarding: ...")` so future occurrences are
        self-describing in the Flask log. Response payload
        unchanged.
      **Aside on console noise:** the bulk of the dev-console
      output during the original capture was
      `content.js:360 The kernel 'X' for backend 'webgl|cpu'
      is already registered` from a browser extension's content
      script (TensorFlow.js classifier running in `content.js`
      + `classifier.js`) — NOT our code.

- [x] **~~Template preview pagination — blank pages between
      sections~~** — ✅ resolved 2026-05-27 alongside the
      "Sandboxed iframe blocks script execution" entry above.
      Diagnosis was wrong in the original entry — the blanks
      were NOT caused by `page-break-inside: avoid` doing its
      job too aggressively; they were caused by paged.js (which
      handles intelligent break-vs-fit decisions for that CSS
      rule) being blocked from executing inside the
      `sandbox="allow-same-origin"` iframe. Once paged.js is
      allowed to run via `sandbox="allow-scripts allow-same-origin"`,
      it lays out content efficiently. If pagination quality is
      still imperfect after the sandbox fix (e.g., specific
      experience cards still push to new pages with blanks), the
      original fix paths remain valid for future polish:
      (a) tighten template densities, (b) drop
      `page-break-inside: avoid`, (c) add a "compact" mode.
      **Follow-up (2026-06-04, `feat/template-pagination`, v1.0.5):** path (b)
      landed — Modern/Spacious/Tech carried `section { page-break-inside: avoid }`
      (Classic did not), which forced paged.js to keep each whole section
      together and shoved oversize Experience sections onto blank/short pages.
      Dropped the section-level rule (kept the correct per-entry
      `article { page-break-inside: avoid }`) and added Classic's
      `h2 { page-break-after: avoid }`. Pinned by
      `tests/ux/regression/test_20260604_template_pagination.py` (no blank page
      across all four bundled templates). Closes the v1.0.5 tag criterion
      "Pagination fixed for all 4 bundled templates."

- [x] **~~Chrome "multiple downloads blocked" silently kills 2nd download~~** —
      ✅ resolved 2026-05-27 (UI hint). Added a one-line hint paragraph
      below the download button row in Step 6 (`templates/index.html`)
      pointing users to the Chrome address-bar ↓ icon → "Always allow
      downloads from this site". The underlying JS mechanism (programmatic
      anchor click) is unchanged; a server-side `Content-Disposition:
      attachment` redirect that avoids the per-page gesture requirement is
      tracked for v1.0.2. Branch `fix/chrome-multi-download-hint`.
- [x] **~~paged.js polyfill "Cannot read getBoundingClientRect of
      null"~~** — ✅ **console symptom contained** 2026-06-04
      (`feat/template-pagination`, v1.0.5), option (a). **Not** root-cause
      elimination — read this carefully so a future agent doesn't over-read
      "resolved": the throw still fires *inside* the vendored paged.js
      (`static/vendor/paged.polyfill.js` v0.4.3); we catch-and-ignore it. The
      polyfill's auto-run (~L33239) `await`s `previewer.preview()` with **no
      `.catch()`**, so a sparse-content layout throw escaped as an uncaught
      rejection. The injection in `app.py` (`_PAGED_PREVIEW_INJECTION`) now
      disables auto-run (`window.PagedConfig = { auto: false }`) and drives
      `new Paged.Previewer().preview()` itself inside `try/catch` + `.catch()`;
      the sibling `node.getAttribute is not a function` *sync* throw (fired off
      the awaited chain) stays covered by the paged-origin `window.error`
      swallow. The `tests/ux/conftest.py` `getBoundingClientRect` allowlist is
      **removed** — the sentinel is now unconditional, so a *new/different*
      paged.js error is not swallowed and WILL fail the suite — and
      `tests/ux/regression/test_20260604_template_pagination.py` asserts a clean
      console across all four bundled templates. Safe **only** because the
      render completes correctly despite the throws (that test also asserts no
      blank pages). **Root-cause elimination** = leave paged.js (option (c));
      tracked in [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) "paged.js
      preview-render fragility — contained, not eliminated".
- [x] **~~Cover-letter download honors the chosen output format~~** —
      ✅ resolved 2026-05-28 (path b, UI hint). Added a one-line hint
      paragraph below the download button row in
      [`templates/index.html`](../../templates/index.html):
      *"Cover letter downloads as .docx in v1.0.1. PDF and Markdown
      format support coming in v1.0.2."* The underlying
      `generator.generate_cover_letter` still hardcodes `.docx` (no
      change — path (a), full format support, is v1.0.2 alongside
      B3 persona styling work).
- [x] **Prior-application click resumes the wizard at that
      application's last state** **✓ SHIPPED v1.0.5** (`feat/prior-app-resume`,
      merged `cc74f90`)
      (`feat/prior-app-resume`, RELEASE_ARC §Phase 4) (user-surfaced
      2026-05-26 during round-6 smoke). Today, clicking a card in the "Prior
      applications" panel of Step 1 shows a one-line toast with
      title/status/iter-count and nothing else — that's an
      acknowledged placeholder per the comment at
      [`static/app.js:3404-3406`](../../static/app.js#L3404):
      *"Lightweight info display in the toast for now — resuming an
      application into the live editing flow ships in D.3.1."*
      Expected behavior (user-confirmed): clicking should load the
      application's context_path + selected persona + last-generated
      résumé/cover letter into the wizard and jump to the most
      advanced step that has data (typically Step 6 — Generated
      output). Implementation: the application row's runs[] already
      carries a `context_path` per iteration; the most recent run's
      context_path is the load target, the run's persona_template_id
      drives the template selection, and the run's resume_path /
      cover_letter_path hydrate the editors. Defer to v1.0.2; user
      can re-create from scratch in v1.0.1.

### Nice to have (defer to v1.1 if time-bound)

- [ ] **Visual assets** **→ OPEN, owner v1.1.0** (`release/visual-assets`,
      RELEASE_ARC §Phase 5) — screenshots, demo GIF, onboarding HTML
      page. PRODUCT_SHAPE §10 defers this to v1.0.1; if the
      planned UI redesign hasn't started, ship visual assets
      against the current UI rather than wait.
- [x] **~~R2 — stream `analyze()` output~~** — ✅ done in v1.0.1
      (CHANGELOG [1.0.1] "Added — Performance (R2 streaming)"):
      `/api/analyze/stream` + `/api/generate/stream` SSE routes shipped with
      spinner-default UX; the v1.0.3 two-pass split later layered the `phase`
      sentinel on top. (docs/dev/perf/PERF_ANALYZE.md, $0, perceived latency
      90s → 10-15s.)

### Pre-tag cleanup + review stage (do last, before v1.0.1 tag)

User-stated 2026-05-26: cull temporary exploration artifacts so
they don't continue to track. Run this as a focused stage AFTER
B1–B3 land and AFTER the fresh-clone verification, immediately
before the version-bump commit.

- [x] **~~Remove `docs/mockups/`~~** — ✅ resolved 2026-05-28.
      Grepped `templates/`, `scripts/`, `docs/` for `docs/mockups`
      — the only hit was a comment in `templates/index.html:126`
      (no live consumer). Deleted the directory (6 files including
      the undocumented `index.html`); stripped the comment
      reference. Branch `chore/pre-tag-cleanup-docs`.
- [x] **~~Audit `docs/archive/`~~** — ✅ resolved 2026-05-28.
      Only file: `docs/archive/2026-05-25_doc_audit.md` (pre-release
      v1.0.0 documentation audit). Confirmed not referenced anywhere
      outside itself. Deleted outright — all recommendations in that
      audit were implemented in v1.0.0 commits. Branch
      `chore/pre-tag-cleanup-docs`.
- [x] **~~Strip dead-link references from CHANGELOG history~~** —
      ✅ resolved 2026-05-28. Extracted all 17 relative-path links
      from `CHANGELOG.md`; all 17 resolve. No broken links found.
      Branch `chore/pre-tag-cleanup-docs`.
- [x] **~~`scripts/perf_baseline.py`~~** — ✅ resolved 2026-05-28.
      Added to `docs/architecture.md` module map as a release-cycle
      tool (p50/p90 latency snapshot before/after perf interventions).
      Branch `chore/pre-tag-cleanup-code`.
- [x] **~~`r1-attempted-2026-05-26` branch~~** — **DELETED 2026-06-02** (tip
      `09815a1`; reflog-recoverable ~90 days). Supersedes the earlier "KEPT as
      historical reference" decision. v1.0.3 R1 Phase 2 is complete; all R1
      branches (`structural-context-probe`, `hidden-qualities-schema`,
      `analyze-split-cache-reclaim`, `clarify-model-trial`) merged, and
      **all of its learnings are already incorporated on `main`** (verified
      via `git log`/`git diff`): the two-pass split was rebuilt fresh (the
      branch predated the Pydantic migration, so it was never cherry-picked),
      the `context_probe` wording + typed `hidden_qualities` redefinition
      landed in the two ✓ schema branches, and the failure diagnosis +
      recruiting consultation are preserved in `evals/TUNING_LOG.md`
      (2026-05-26 entries, on `main`). With nothing on it still needed, the
      museum snapshot was deleted at the v1.0.4 cut; the commit stays
      reachable via reflog (~90 days) if ever required.
- [x] **~~Retire `/api/users/<username>/import-legacy` route~~** —
      ✅ resolved 2026-05-28. (a) Confirmed only consumer was
      `scripts/capture_screenshots.py`, which already calls
      `run_import` directly, not via the Flask route. (b) Removed
      `import_legacy_user` route from `app.py`; `onboarding/import_legacy.py`
      kept — `ingest_one_resume` is still used by the live
      `/corpus/ingest-resume` route. (c) Updated comment in
      `scripts/capture_screenshots.py` that referenced the deleted
      route. (d) No references in `walkthrough.md` or `README.md`.
      Removed `tests/test_import_legacy_route.py`; updated
      `docs/architecture.md` route reference to the live
      `ingest-resume` route. Branch `chore/pre-tag-cleanup-code`.
- [x] **~~Grep for TODO / FIXME / XXX comments~~** — ✅ resolved
      2026-05-28. Grepped `*.py`, `*.html`, `static/app.js` — zero
      hits in our own code. All TODOs/FIXMEs are in the vendored
      `static/vendor/paged.polyfill.js` (not our code). No action
      needed. Branch `chore/pre-tag-cleanup-code`.
- [x] **~~`lcars-*` CSS class rename → `cb-*`~~** — ✅ resolved
      2026-05-26. After surfacing during the B1 smoke, the user
      reviewed the actual scope (the visual redesign had already
      landed in commits `dc062e4` Phase 1 → `3a3f891` Phase 2; only
      class NAMES were leftover) and chose to close the rename out
      in v1.0.1. Mechanical `lcars-` → `cb-` substitution across
      [`static/style.css`](../../static/style.css) (73 refs →  0),
      [`static/app.js`](../../static/app.js) (19 → 0), and
      [`templates/index.html`](../../templates/index.html) (147 → 0).
      Zero behavior change; class shape preserved
      (`lcars-btn` → `cb-btn`, `lcars-bg-*` → `cb-bg-*`, etc.).
      Historical CHANGELOG entries still describe the original
      `lcars-*` names as they existed at the time — those are
      not rewritten.

---

## Forward-looking — v1.1 and v2

v1.1 + v2 items are tracked in
[`docs/PRODUCT_SHAPE.md §10`](../PRODUCT_SHAPE.md). Don't duplicate
the list here — the strategy doc is the single source of truth
for the deferred table.

Highlights pulled from §10:

- **v1.0.2:** R1 (split analyze: Haiku-fast + Sonnet-deep)
  **— ATTEMPTED + REVERTED in v1.0.1, deferred to v1.0.2.**
  Three iterations attempted on 2026-05-26 (`2026-05-26.1`
  naive split, `2026-05-26.2` atomic extraction + context_probe
  clarify fix); each degraded `clarification_quality` further
  vs. the pre-R1 baseline (pm-senior went 4.2 → 3.2 → 2.1,
  ds-junior 4.2 → 4.2 → 3.2). Performance was a real win
  (analyze p50 103s → ~72s, ~30% reduction) but the
  "no quality loss" floor was hard-binding. The R1.2 attempt
  is preserved on the `r1-attempted-2026-05-26` branch as the
  starting point for v1.0.2; see `evals/TUNING_LOG.md` entries
  `2026-05-24.4 → 2026-05-26.1` and `2026-05-26.1 → 2026-05-26.2`
  for the full diagnosis and recruiting-specialist consultation.
  **v1.0.2 plan:** use the `/prompt-tune` skill for smaller
  iteration cycles (cheaper than full eval runs each change) +
  the new `.claude-plugin/agents/headhunter.md` agent for
  sharper diagnosis between attempts.
- **v1.1:** field-filter chips for templates by role tag,
  master résumé operationalization, Docker.
- **v2:** `recommend_template` Haiku call per JD class (gated
  on outcome data + an `ApplicationOutcome` table).

### v1.0.2 — Live preview = downloaded résumé (true WYSIWYG) (new 2026-05-26)

**The ask** (user-stated, 2026-05-26): *"the live preview should
be on the selected corpus and json produced in the JD specific
resume corpus and title selections. the user should see a live
preview of what will be produced."*

**Current state after v1.0.1.** The Step 6 iframe (preview route
`/api/applications/<id>/preview`) is now properly bounded — it
only renders when `llm_recommendations` exists; otherwise it
returns a placeholder HTML explaining that curation is needed.
This stops the misleading 3-page un-curated render. But the
preview is still **corpus-rendered**, while the downloaded file
is **LLM-rendered**. They can diverge:

- **Preview path**: `build_json_resume_from_corpus()` reads
  Candidate + Experience + Bullet rows from the DB, filters by
  `composition_overrides` (pin/exclude/added) and
  `llm_recommendations`, renders through the persona's HTML
  template via `pdf_render.render_html_string`.
- **Download path**: `analyzer.generate()` produces markdown the
  LLM wrote (informed by the same corpus + curation, but free to
  reword each bullet for sharpness / JD relevance). The markdown
  lands in `#resumePreview` (editable), then
  `/api/download-edited` renders it to `.docx`.

So the LLM rewrite can change bullet wording, ordering within an
experience, and sometimes the summary phrasing — the preview
doesn't see any of that.

**Implementation options for v1.0.2** (pick one when planning):

1. **Render preview from the LLM markdown when one exists.** The
   most recent generate's `last_generated_resume` (in the
   context_set) is the canonical "what the LLM wrote." Convert
   that markdown → JSON Resume via a deterministic parser, then
   render through the same template pipeline. Pre-generate
   (mid-wizard, before the user has clicked Generate), the
   preview falls back to the corpus-based render OR the v1.0.1
   placeholder. **Pro:** matches download exactly once Generate
   has run. **Con:** needs a robust markdown → JSON Resume
   parser; resume markdown has a lot of shape variation (sections,
   subsections, dash-vs-bullet, multiple title formats).
2. **Make the LLM produce structured JSON Resume directly.**
   Change the generate() prompt to emit JSON Resume instead of
   markdown. The download path renders that JSON through the
   template (same as preview). **Pro:** preview = download is
   trivially byte-identical. **Con:** large prompt change,
   PROMPT_VERSION bump, full eval re-run, AND the editor (a
   contenteditable markdown surface) needs replacement — users
   can't hand-edit raw JSON; needs a structured-edit UI or a
   JSON Resume → markdown → JSON Resume round-trip with parser
   on each save.
3. **Dual-render approach.** Keep the markdown path for the
   editor (humans edit markdown well), but also store a parallel
   JSON Resume artifact updated whenever the markdown changes
   (debounced server-side). Preview reads the JSON Resume; the
   editor / download read the markdown. **Pro:** preserves the
   markdown editor; gives the preview ground truth. **Con:**
   keeps two artifacts in sync, which is exactly the kind of
   "two sources of truth" the v1 architecture was designed to
   avoid.

**Recommendation when planning v1.0.2:** option 1 (markdown →
JSON Resume parser) is the lowest-risk path that preserves the
markdown editor. The parser is bounded scope (markdown shape is
known) and doesn't touch the generate prompt or the editor UX.
Option 2 is the long-term cleanest answer but bigger surface.

**Eval implication:** none of the three options changes the LLM
output by itself; preview shape is a rendering concern. No new
rubric needed unless option 2 is chosen.

### v1.1 — User-driven bullet ordering on Compose stage (new 2026-05-26)

**The ask** (user-stated, 2026-05-26): bullets in the Compose
stage should be ordered intentionally, with most-valuable
bullets at the top of each experience and least-valuable at the
bottom. The user should be able to click-and-drag to reorder
these. Functional change + documentation to support.

**Current state.** Bullets are already sorted server-side in
[`app.py:get_application_composition`](../../app.py) by
`(not (pinned or recommended or added), -score, id)` —
pinned / LLM-recommended / drawer-added bullets sink to the top,
then by descending `score_corpus_bullet()` (deterministic fit
score against JD keywords + analysis essentials), then by id
for a stable tiebreaker. **There is no explicit user
ordering today**; pin/exclude/add are the only user
affordances over order.

**Why this matters beyond UI polish.** The order influences the
final document in two ways the user may not see directly:

1. **Recruiter scan order.** Surveys consistently report
   recruiters initial-scan résumés top-down in 6–8 seconds.
   The first bullet under each role does the load-bearing
   work of selling that role's relevance. (The literature on
   exact scan times is messy — see the R1 researcher's note
   that the half-remembered "TheLadders eye-tracking" study
   wasn't verifiable in our session. Treat the 6–8s as
   directionally true, not citation-quality.)
2. **LLM prompt order shapes the generated bullets.** The
   `_corpus_block` in [`analyzer.py`](../../analyzer.py)
   iterates experiences and bullets in the order they appear
   in the corpus payload. The Sonnet generate prompt
   processes bullets in that order — when it picks which
   bullets to keep in a constrained-length résumé, the
   earlier-listed ones are weighted by sequence position,
   not just by score. So a user reordering on Compose isn't
   cosmetic; it's a prompt-engineering knob the user holds.

**Design notes (my own thoughts, deferred to v1.1
implementation):**

1. **Persistence shape.** Extend `composition_overrides` in the
   context file with `bullet_order: {[experience_id]:
   [bullet_id, ...]}`. When present, this is authoritative
   over the server-computed sort. Absent ⇒ fall back to the
   current `(not pinned, -score, id)` ordering. Same context
   file already carries `pinned` / `excluded` / `added` — the
   ordering data lives in the same place for the same lifecycle.
2. **Render impact in `_stable_user_prefix`.** Honor
   `bullet_order` when building the `<career_corpus>` block so
   the user's reordering propagates into the generate prompt.
   This is the load-bearing piece — without it, drag-and-drop
   is cosmetic and the LLM's output won't reflect the user's
   intent.
3. **UI.** HTML5 native drag-and-drop on bullet cards. No new
   dependency needed — the rest of the codebase avoids
   framework dependencies. Add a small grab-handle ("≡")
   on each card; whole card is the drop zone. Cursor
   changes to `grab` on the handle and `grabbing` while
   dragging so the affordance is discoverable without a
   tooltip.
4. **In-interface instructions (user-stated 2026-05-26).**
   Docs alone are insufficient — users in the wizard won't
   reread the walkthrough mid-flow. Add a short
   instructional line at the top of each experience's
   bullet list:

   > *"Bullets are ranked by callback's AI by fit to this job.
   > Drag to reorder — your order shapes the final résumé."*

   Two load-bearing words there: "AI" (sets expectation that
   the default order is already intentional, not random or
   chronological) and "shapes" (telegraphs that the order
   isn't cosmetic — see point 2). Keep it ONE sentence;
   anything longer gets skipped. Pair with an info "(i)"
   icon that reveals the longer "why ordering matters"
   explanation on hover/click, for the curious user who
   wants depth without forcing depth on everyone.
5. **Accessibility floor.** Keyboard-controlled reordering is
   non-negotiable (deprecated `aria-grabbed` / `aria-dropeffect`
   should NOT be used). Add Up/Down buttons on each row with
   `aria-label="Move bullet up"` etc. — these are the
   keyboard path; drag-and-drop is the pointer path. Both
   write to the same persistence layer.
6. **Persistence trigger.** Debounced (~300ms) POST to
   `/api/applications/<id>/composition/order` (new route, or
   extend the existing PATCH) with the full new order
   per-experience. Optimistic UI update; reconcile on response.
7. **Reset affordance.** "Reset to AI ranking" button
   per experience (matches the in-interface instruction's
   "ranked by callback's AI" framing — consistent vocabulary
   beats clever vocabulary). Clears `bullet_order` and falls
   back to the server sort. Disabled state when no custom
   order exists, so the user sees they're already on the
   default.
8. **Edge case — bullets added later.** If the user added a
   bullet via the drawer AFTER setting an explicit order,
   default to slotting it at the END of the list with a
   subtle "newly added — drag to reposition" hint. Don't
   silently re-sort, which would erase the user's other
   choices.
9. **Documentation impact.** Update
   [`docs/walkthrough.md`](../walkthrough.md) Step 3 (Compose) to
   teach the WHY of ordering (recruiter scan + LLM
   sequence-position bias), not just the HOW (drag to
   reorder). The educational depth is the differentiator vs.
   "click and drag" docs that just describe the affordance.
10. **Eval implication.** This is a UX change with prompt-
    structure side effects (point 2). After implementation,
    run a manual eval against synthetic fixtures with one
    reordered ⇄ one default-order condition to confirm the
    generated résumé honors the reorder. Not a full
    `PROMPT_VERSION` bump — the prompt template doesn't
    change, only the order of the data fed to it — but worth
    capturing in `evals/TUNING_LOG.md` as a behavior shift.

---

## Risk register — verify before every release

These are evergreen — re-check on every release cut.

1. **PII in fixtures.** Any `evals/fixtures/real/` files crept
   into the main suite? Run `pytest -k 'real'` separately,
   verify they're gitignored.
2. **Anthropic model availability.** Sonnet 4.6 + Haiku 4.5 IDs
   in `analyzer.py` — confirm still GA when the release cuts.
3. **Cross-platform path handling.** `_safe_username` + `_within`
   are POSIX-friendly; verify on Windows with users that have
   spaces / unicode in their username.
4. **First-run experience.** Time-to-first-generation < 5
   minutes from a clean clone, following `docs/install.md`.
5. **Eval baseline.** Diff against
   `evals/results/baseline_v1.json`; surface deltas in CHANGELOG
   if any rubric moved more than 0.3 points.

---

## Archive — v1.0.0 release completed items

Below: what shipped during the v1.0.0 release arc. Kept for the
audit trail; do NOT re-run on subsequent releases.

### A — Codebase hygiene (DONE)

- **A.1 PII scrub** — completed in the α-phase scaffolding pass.
  `configs/`, `resumes/`, `output/`, `evals/fixtures/real/`,
  `logs/` are all gitignored. Synthetic fixtures + testuser are
  the only fixtures in tree.
- **A.2 Stray-code sweep** — completed in
  `6f56461 chore(hygiene): retire dead LCARS chrome`.
- **A.3 Semantic naming consistency** — completed in
  `24dbc71 chore(naming): JS convention audit`.
- **A.4 CSS cleanup** — completed in
  `41a0a35 chore(css): migrate 220 alias refs to canonical
  callback. tokens`.

### B — Visual polish (DONE except v1.0.1 items)

- Wizard rail, top bar, panels, buttons → token-bound in Phase 1.
- Compose step `.exp-card` / `.bullet` mockup-staged; wiring
  to live UI deferred to v1.0.1 (see "Should do" above).

### C — Documentation pass (DONE)

- **C.1** README rewrite + `docs/install.md` — landed in
  `319ae1b` (initial) and `67ae017` (substantial body rewrite).
- **C.2** CLAUDE.md + `docs/architecture.md` — landed in
  `9d36761`. Four Mermaid diagrams in `docs/diagrams/`.
- **C.3** `docs/onboarding.html` — deferred per PRODUCT_SHAPE
  §10 (README + `docs/install.md` cover the same ground).
- **C.4** `SECURITY.md` threat model — refreshed in
  `e880451`.
- **C.5** `CHANGELOG.md` + version cut — `[1.0.0] —
  2026-05-25` entry written; version bumped to `1.0.0` in
  `075d830`.
- **C.6** Project-meta files — `LICENSE`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, issue/PR templates, `.editorconfig` all
  shipped. `FUNDING.yml`, `Dockerfile` deferred to v1.1.

### D — Risk register (CLEARED)

D.1–D.5 all verified before the v1.0.0 tag.

---

## When to revisit this file

After every release tag:

1. Move "Active release" items that shipped → "Archive — v1.X.Y
   release completed items" subsection.
2. Bump the "Active release" header to the next planned version.
3. Pull next release's items from PRODUCT_SHAPE §10 (move them
   in, don't duplicate them).
4. Re-check the Risk register evergreen items.

If a release cut surfaces a new "Forward-looking" item that
isn't in PRODUCT_SHAPE §10, add it there first, then reference
here.
