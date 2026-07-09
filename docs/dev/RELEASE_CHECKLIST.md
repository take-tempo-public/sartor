# Release Checklist — sartor.

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

- [x] **7.1** `chore/plugin-activation` — make `.claude-plugin/` commands + agents load (not just hooks); fix `CLAUDE.md` "Skill catalog". Unblocks `/wiki-*` + compliance pilot. **Landed 2026-06-15:** local `sartor-tools` marketplace + `enabledPlugins` committed in `.claude/settings.json`; `plugin.json` name→`sartor` / version→`1.0.6`; the 10 command + 6 agent `.md` files moved out of the reserved `.claude-plugin/` to the plugin root (`commands/`, `agents/` — Claude Code skips components nested in `.claude-plugin/`), default root scan (no path-overrides); commands namespace as `/sartor:…`, subagents `sartor:…`. **Hooks deliberately left in `settings.json`** (enforcement-portability deferred to 7.2 — see tracked-deferred below). `CLAUDE.md` Skill+Subagent catalog and `README.md` plugin section corrected.
- [x] **7.2** `design/governance-extraction` → `feat/governance-extraction` — one canonical rules home; **preserve `@import`/pointer rule-access** (hard constraint). PX-23/24/27/28 ride here. **Design half DONE 2026-06-15** (`design/governance-extraction`): sub-decisions resolved (home=`docs/governance/`, AGENTS=inline-with-pointer, graduate all 4 draft files), drift-reconciled (cite-don't-refix), portability decided (split) — full spec in [`governance-extraction-design.md`](governance-extraction-design.md). **feat/ half DONE 2026-06-15** (`feat/governance-extraction`, merge `2b35551`): canonical rules graduated to `docs/governance/` — `charter.md` (signed; C-0…C-6 · D-1…D-6 · W-1/W-2 · amendment ceremony) + `enforcement.md` (gate/witness/tribal split) + `metrics.md`; PX-24 (`block-merge-to-main` HEAD==main check) + PX-28 (`check-plan-approved` hand-create-hint removal) + PX-27 (`vision.md` demotions) landed; `@import`/pointer rule-access preserved (`@AGENTS.md` chain intact). *(Row was left `[ ]`/"feat/ half pending" after the merge — surfaced as stale by the 7.7 compliance-witness pilot (CW-01, 2026-06-16) and corrected here.)*
- [x] **7.3** `design/self-documenting-loop` → `feat/self-documenting-wiki` — bounded, cost-aware Haiku diff-pass ingest + `/wiki-lint`/`/wiki-audit` backstop (PX-33). **Design half DONE 2026-06-16** (`design/self-documenting-loop`): trigger / cost / scope settled (bounded checkpoint + freshness-witness-hook escalation, no scheduler; Haiku diff-pass with warm-start exemplars by-reference + per-run page cap; `docs/wiki/`-only — the cross-document link/cite checker stays the separate follow-on, not absorbed), orchestration = new `/wiki-self-update` command + Haiku `wiki-scribe` subagent + separate read-only Haiku `wiki-grounding-auditor` subagent (author≠auditor) + `/wiki-lint` as the deterministic gate; **the loop never auto-commits** (always a reviewable diff). Full spec in [`self-documenting-loop-design.md`](self-documenting-loop-design.md). **feat/ half DONE 2026-06-16** (`feat/self-documenting-wiki`): built per the design §4 — `commands/wiki-self-update.md` orchestrator + `agents/wiki-scribe.md` (Haiku, `Read`/`Grep`/`Glob`/`Edit`) + `agents/wiki-grounding-auditor.md` (Haiku, read-only `Read`/`Grep`/`Glob`); freshness hook escalates at a 10-file threshold; default page cap 8 (`--cap N`); exemplars by-reference = `route-surface` + `deterministic-llm-boundary` + `using-sartor`; **dev-harness only** (no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged). Owner-approved: the loop's **first real run landed on this branch** (the consolidated v1.0.7 wiki refresh — see [`docs/wiki/log.md`](../wiki/log.md)), so 7.9 inherits a current checkpoint.
- [x] **7.4** `feat/recall-skeleton` — Stage 0 `recall/` package (no LLM; never imports `app.py` → refactor-immune). **DONE 2026-06-16** (`feat/recall-skeleton`): new stdlib-only `recall/` package — the Stage 0 skeleton of the Memory substrate per [`memory-architecture.md`](memory-architecture.md) "Staged build." Public surface = `Unit`/`Source`/`Scope`/`Context` + `assemble()`; the two cross-cutting planes (provenance stamp enforced at construction; access/disclosure audience+tier gating); a working deterministic `assemble()` (RRF fusion + token-budget pack) proven end-to-end over a shipped `InMemorySource` reference; **no real source tier** (S1 wiki/S2 git → 7.5, S3 vector → 7.6) and **no LLM**. The hard dependency rule (never imports `app.py`/`analyzer.py`/DB/Flask/`anthropic`) is enforced by [`tests/test_recall_boundary.py`](../../tests/test_recall_boundary.py) (AST boundary-lint mirroring the PX-08 egress gate) — a test, **not a hook** (enforcement-portability stays the Sprint 8.7 work). **Dev-substrate only** — no route, no LLM call, no new dependency, no migration; `PROMPT_VERSION` unchanged; no user-facing behavior (nothing wired into the pipeline yet). Gate green (ruff · mypy · pytest). No new ledger item (open count stays 7).
- [x] **7.5** `feat/doc-assistant` — **the AI assistant** (Stage 1): wiki + `git grep` retrieval + Haiku avatar (user's key) + user/dev toggle; authored as its own `blueprints/assistant.py` module (blueprint-aware so the v1.0.8 split is a move, not a rewrite). **DONE 2026-06-16** (`feat/doc-assistant`): the three generic tiers in `recall/sources/` (`WikiSource` S1 / `GitGrepSource` S2 / `SessionSource` S5-P1 — roots+audience injected, kept project-agnostic by a new `test_recall_sources_no_hardcoded_roots` guard); the avatar `analyzer.avatar_answer_streaming` + `AVATAR_SYSTEM_PROMPT` (**honors C-6 — D1=A**) with its own `AVATAR_PROMPT_VERSION` (résumé `PROMPT_VERSION` unchanged); the SSE route `blueprints/assistant.py` (`POST /api/assistant/ask`, no `app.py` import) + the egress-allowlist add; a minimal collapsible in-shell panel (`templates/index.html` + `static/assistant.js`). Owner-confirmed: **D1=A** (avatar in `analyzer.py`), **D2=Y** (parameterized sources in `recall/sources/`), **UI** = minimal in-shell panel. **Zero new deps; no migration.** Gate green (ruff · mypy · pytest incl. the UX panel test). No new ledger item (open count stays 7).
- [x] **7.6** `feat/doc-assistant-vector` — Stage 2 vector tier. **DONE 2026-06-16** (`feat/doc-assistant-vector`): the S3 `VectorSource` semantic tier on the `recall/` `Source` protocol — static `model2vec` embeddings (`potion-base-8M`, dim 256) + brute-force cosine over a rebuildable `db/vector_index/` sidecar (gitignored; **NOT** `db/resume.sqlite`), incremental ($0-on-unchanged content-hash reuse), built offline by [`scripts/build_vector_index.py`](../../scripts/build_vector_index.py); wired into the assistant **"on when available"** (model + index present; no user-facing toggle). The substrate stays embedder-agnostic — the embedder is **injected**, so `recall/` never imports `model2vec` (it lives in `blueprints/assistant.py` + the build script); only `numpy` enters `recall/sources/` (the stdlib boundary test was deliberately relaxed for it). **Eval gate was an OWNER OVERRIDE** (was eval-gated/conditional): built ahead of the formal v1.0.8 labeled eval because the landed Stage-1 assistant tested *too literal / lacking semantic flexibility*; a probe ([`scripts/vector_index_probe.py`](../../scripts/vector_index_probe.py)) corroborates ([`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md)), the judge-scored before/after eval is owed at v1.0.8 (ledger). **New hard deps** `numpy` + `model2vec` (numpy + tokenizers + safetensors, no torch); CHANGELOG + RELEASE_ARC §4.7 + architecture + memory-architecture updated. No migration; résumé `PROMPT_VERSION` unchanged. Incidental fix folded in: `test_git_grep_source.py::test_no_match_returns_empty` was a pre-existing main failure (latent since 7.5: its hardcoded "absent" token self-matched the now-tracked test file via `git grep`) — fixed to a runtime-built token. Gate green (ruff · mypy 186 · pytest). Adds 1 ledger item (→ 8).
- [x] **7.7** `feat/compliance-agent-pilot` — `/compliance-witness` command + read-only subagent. **DONE 2026-06-16** (`feat/compliance-agent-pilot`): built per [`compliance-agent-design.md`](reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md) Appendix — `commands/compliance-witness.md` orchestrator (resolves a pinned sha via `--since`/last tag, delegates the read via `Task`, **caps flags default 12** `--cap N`, renders a findings-register table FLAG/WATCH/AFFIRM + a `/wiki-lint`-style gate verdict, appends a dated counts line to `docs/governance/compliance-log.md`) + `agents/compliance-witness.md` (**Sonnet**, read-only `Read`/`Grep`/`Glob`/`Bash` read-only-git — **no `Edit`/`Write`/`Task`**, the tool grant *is* the HARD-non-goal enforcement; pairwise-drift-only, ranks against the charter/C-0, cites-never-asserts, honest-silence). **Never edits, never blocks, never commits.** Both land at **repo-root** `commands/`+`agents/` — the design's `.claude-plugin/`-only Appendix path predates the 7.1 move (Claude Code skips components nested in `.claude-plugin/`). **Dev-harness only** (no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged). Owner-approved: one supervised **pilot run** against the freshly-graduated `docs/governance/` (born [`docs/governance/compliance-log.md`](../governance/compliance-log.md)) — window `e299ac8`→`1741ab1`, FLAG 1 / WATCH 2 / AFFIRM 3, verdict *needs attention*. **Pilot PASSES** the design's self-eval rubric: the one FLAG (CW-01 — this very checklist's 7.2 row left `[ ]`/"pending" after `feat/governance-extraction` merged) was owner-scored **true drift → flag-precision 1.0 ≥ 0.66**, and corrected here. Surfaces as `/sartor:…` on the next Claude Code reload (in-session pilot reproduced the subagent as a Sonnet-pinned agent, per the 7.3 first-run precedent).
- [x] **7.8** `px/v107-band` — PX-18 `ACCESSIBILITY.md`, PX-31 Chromium reclassification, PX-32 KEEP/BOOST ledger; + fix the stale R2 deferred-listing in `PRODUCT_SHAPE.md`. **DONE 2026-06-16** (`px/v107-band`). **PX-18** (`F-expa11y-03`): new root [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) honest-status page per **E-2** (signed product charter, not the graduated `docs/governance/`) — the machine-checked taxonomy (axe serious/critical · keyboard a11y-floor · `_announce()` live-region · modal trap · `--fg-2/3` contrast) **vs known gaps** (UX tier not yet in CI → PX-25; serious/critical-only; Clarify/Output/cover-letter/modals + tab-order/reflow/history unscanned; NVDA not yet walked); **no conformance claim / tag gate / recurring-audit promise** (v1.1.0 WCAG-2.2-AA self-eval stated as intent only); + README doc-map pointer. **PX-31** (`F-docs-05`): Chromium ~150 MB reclassified **PDF-output-only** — lifted out of `docs/install.md` Prerequisites + the 3 OS sequences gated "optional — only for PDF output"; corrected the "renders every PDF and the live preview" conflation (the preview is browser-side paged.js, Chromium-free — `SECURITY.md` bundled-assets; verified `pdf_render.py` is the sole Playwright renderer); README quick-install + `pyproject.toml` playwright comment tightened. **PX-32**: new [`docs/dev/keep-ledger.md`](keep-ledger.md) eval/governance do-not-regress ledger — `F-eval-05/06/08` + `F-gov-06/09` + `F-docs-07/08/09` as KEEP notes, `F-eval-09` as a precision note, `F-eval-07` **BOOST** affirmed, `F-gov-08` + `F-gov-10` logged as **deferred design items (ledger-only)**; the security/PII KEEP set cross-referenced to PX-29 (8.4). **R2 fix**: `PRODUCT_SHAPE.md` §10 R2 entry marked **shipped v1.0.3** (was still listed v1.1-deferred, contradicting the §494 banner). **Docs-only** — no code/prompt/route/dep/migration; `PROMPT_VERSION` unchanged. Gate green (ruff · mypy · pytest). **No new ledger item (open count stays 8)** — the PX-32 deferred design items live in `keep-ledger.md`, not the carry-forward ledger (owner decision).
- [x] **7.8a** `feat/assistant-topbar-modal` — **assistant UI relocation** (first of a few small UI-polish sprints the owner flagged before the 7.9 tag). **DONE 2026-06-16** (`feat/assistant-topbar-modal`): the doc-grounded assistant's entry point moved from the always-visible in-shell collapsible `<details>` panel (`#panelAssistant`, parked below the wizard) to a **fixed top-bar magnifier icon** (`#assistantPill`, left of Diagnostics) opening a **floating, scrollable modal** (`#assistantModal`) — one stable, always-findable entry point. Reuses the existing `.cb-modal` skeleton (id-scoped to ~680px; `.cb-modal-body` internal scroll + 90vh cap unchanged) and the top-bar-pill-opens-overlay precedent (Diagnostics modal / Settings drawer). The control ids carry over, so `static/assistant.js` `askAssistant()`/SSE path is **unchanged**; one new `openAssistantModal()` adds focus-trap/Esc/backdrop/focus-restore/`aria-expanded` mirroring `openDiagnosticsModal()`. POM (`ui_pages/selectors.py` `Assistant`) re-pointed pill→modal; the assistant UX regression now drives pill → modal → streamed cited answer; the axe gate adds an open-state `#assistantModal` scan. **Front-end only** — no route, LLM, prompt, dep, or migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged. Gate green (ruff · mypy · pytest · `-m ux`). **No new ledger item (open count stays 8.)**
- [x] **7.8b** `fix/v107-ui-polish-trio` — **three small UI-polish fixes** (second of the few small sprints before 7.9). **DONE 2026-06-17** (`fix/v107-ui-polish-trio`): (#1) **stray browser windows** — `app.py` auto-opened a browser on every Flask debug-reloader restart because the open ran in the serving child (`WERKZEUG_RUN_MAIN == "true"`) the reloader re-executes per reload; a new pure `_should_open_browser()` opens **exactly once** (supervisor / non-debug single process, never the reload child; still honors `SARTOR_NO_BROWSER=1`), covered by `tests/test_browser_open.py`. (#3) **slow application load** — `list_applications` ran `1+2N` queries (lazy `Application.runs` + per-app pending `ProposalReview` count); now `selectinload(Application.runs)` + one batched `group_by` pending-count → ~3 queries regardless of N, with a constant-query-count regression test. (#4) **new-user stale dropdown** — `showNewUserForm()` cleared the leftover `#userSelect` value (Cancel restores it) + a UX regression. **No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged.** Gate green (ruff · mypy 189 · pytest 1296 incl. `-m ux`). **Adds 1 ledger item** (assistant doc-coverage → open count 8 → 9). The remaining named UI-polish candidate is **#2 assistant voice softening** (own `feat/` branch — owner's "start with voice softening").
- [x] **7.8c** `fix/assistant-runs-without-user` — **let the doc-grounded assistant answer without a user selected** (third small UI-polish sprint before the 7.9 tag; follows #2 voice softening on `feat/avatar-voice-tone-tuning`). **Finding (2026-06-18):** the assistant gates on a chosen user (`static/assistant.js:24` "Pick a user first, then ask."; `blueprints/assistant.py:231` 400s on missing `username`, `:233` `_safe_username` 400s on unknown), but the answer is **project-global** — grounded in the committed wiki + code at HEAD, identical for every user. `username` does **not** feed retrieval (`_build_sources`/`assemble`), scope (`allow_dev` = the Dev-mode checkbox), or the answer; it is used only for (a) a `_safe_username` existence check applied **by discipline** (the route touches **no** user filesystem — its own docstring says `_within`/`secure_filename` is N/A) and (b) telemetry attribution, which `analyzer._call_llm_streaming` already supports anonymously (`username=""` default). So gating the avatar behind user-selection is an artifact of the per-user route pattern, not a need — and it blocks the assistant at exactly the first-run moment ("how does sartor. work?") where a brand-new visitor benefits most, which reads as unfinished. **Fix:** make `username` optional in the assistant path — drop the client gate, relax the route's `if not username` 400, `_safe_username`-validate only when a username is provided, and stamp anonymous telemetry (`""`/`"anonymous"`). Retrieval + answer unchanged; add a route test for the no-user path. Small + contained (`blueprints/assistant.py` ~:225–235, `static/assistant.js:24`). **Pre-7.9-tag.** _(surfaced 2026-06-18 during `feat/avatar-voice-tone-tuning` close-out; capture only — its own branch.)_ **DONE 2026-06-19** (`fix/assistant-runs-without-user`): `username` made optional in the assistant path — the route requires only `question`, `_safe_username`-validates only when one is supplied (a provided-but-unknown user is still a `400`), and absent → anonymous (`""`); the client gate ("Pick a user first, then ask.") is dropped and the Ask button sends `currentUser || ''`; the no-user route test now asserts a streamed anonymous `200` (missing-question + unknown-user `400`s retained). Retrieval + answer unchanged; L3 microcopy needed no edit (the only "pick a user first" string was the removed JS gate). No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged. Gate green (ruff · mypy 189 · pytest 1304 incl. a new no-user UX regression — the lone full-run failure `test_compose_skills_card_drop_persists` is a pre-existing intermittent UX-tier race, passes clean in isolation, unrelated to this change). **Folded in (owner-directed):** the avatar citation/reference-format feedback surfaced this session is captured on this branch as [`avatar-citation-format-guidance.md`](avatar-citation-format-guidance.md); **per owner direction (2026-06-19) it is scheduled as `7.8d` below — a pre-7.9-tag sprint, not a v1.0.8 deferral** — so the carry-forward ledger is unchanged (stays 9).
- [x] **7.8d** `feat/avatar-citation-format` — **avatar citation / reference-format consistency** (fourth small UI-polish sprint before the 7.9 tag; **moved into the v1.0.7 band 2026-06-19 at owner direction — was a v1.0.8 deferral**). The friendly-guide voice landed well (#2, `feat/avatar-voice-tone-tuning`), but owner testing (2026-06-19) found the assistant's **citations + references render inconsistently** — markdown links `[text](path)`, parentheticals, and numeric `[N]` markers mixed in the same sentences, over a "Sources:" footer the `[N]` don't resolve to. Three server/prompt-side causes per [`avatar-citation-format-guidance.md`](avatar-citation-format-guidance.md): **C1** the context renderer numbers units `[{i}]` (`analyzer.py:1538`) so the model mirrors `[N]` not `[slug]`/`[path:line]` (the real lever — a prompt-only patch is fragile); **C2** model-invented markdown links shown raw (body is `textContent`); **C3** the "Sources:" footer ships **all** retrieved units (`analyzer.py:1595`), not the cited set, so markers are unresolvable + grounding is overstated. **Owner locks scheme A (self-describing cites) vs B (numbered footnotes) first.** Bumps `AVATAR_PROMPT_VERSION`; extends `tests/test_avatar_streaming.py` (no `[\d+]`, no `](`, cite↔footer resolution). **Pre-7.9-tag.** _(surfaced 2026-06-19 during `fix/assistant-runs-without-user`; its own branch.)_ **DONE 2026-06-19** (`feat/avatar-citation-format`): owner locked **scheme B** (numbered footnotes) + render a constrained inline-markdown subset + **clickable GitHub links** (in-app viewer deferred to the ledger). **C1** — the renderer keeps numbering units (the `[n]` is now the cite key) and `AVATAR_SYSTEM_PROMPT` (`analyzer.py`) instructs the avatar to cite with the bracketed **number** (worked OK/NOT-OK examples; never a slug, markdown link, or URL); `AVATAR_PROMPT_VERSION 2026-06-18.1 → 2026-06-19.1`. **C3** — new `_resolve_cited` makes the `done` payload's `citations` a **cited-only, consecutively-renumbered** `{n,label,href}` list (parses the emitted `[n]`, renumbers in first-appearance order, remaps the body); a refusal cites nothing. **C2** — `static/assistant.js` re-renders the answer once on completion as a tiny fixed markdown subset (`` `code` `` / `**bold**` / `[n]`→GitHub `<a>`), **XSS-safe by construction** (escape first, then only fixed tags + a re-validated `https://github.com/` href via `_citation_href`); the numbered "Sources" key renders into a new non-`aria-live` `#assistantSources` block. Deterministic tests extended (href construction, cited-only + renumber, out-of-range-literal, empty-refusal footer, every-`[n]`-resolves / no-`](` / no-URL); route + UX stubs moved to the new shape + assert the rendered links. `PROMPT_VERSION` untouched; avatar stays out of `_BASE_SYSTEM_PROMPTS`; no new route/dep/migration. **Adds 1 ledger item** (in-app citation viewer, deferred → open count 9 → 10). Gate green (ruff · mypy · pytest incl. `-m ux`).
- [x] **7.9** `chore/version-bump-v1.0.7` — tag. **Pre-tag: run `/wiki-self-update`** for the consolidated wiki refresh (the self-documenting loop now owns the diff-pass that `chore/version-bump-v1.0.6` did by hand), then confirm `/wiki-lint` is clean before tagging. (7.3 already advanced `.last_ingest_sha` to the v1.0.7 band, so this is a small top-up unless 7.4–7.8 changed cited code.) **DONE 2026-06-20** (`chore/version-bump-v1.0.7`): the **ledger-integration capture** (each of the 10 open carry-forward items now carries a **→ integrate at 8.x** target; the Open-count banner reconciled; the two pre-decided v1.0.8 items added — `chore/ledger-reduction` (8.0) + `docs/assistant-wiki-coverage` (8.6a), owner-confirmed slots, mirrored in `RELEASE_ARC.md` §4.8); `CHANGELOG.md` `[Unreleased]` cut to `## [1.0.7] — 2026-06-20`; `pyproject.toml` version `1.0.6 → 1.0.7` (`PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched); the consolidated `/wiki-self-update` refresh (diff `a008f86…`→HEAD) presented + committed wiki-only so `/wiki-lint` stays clean at the tag. **Docs/chore only** — no code/route/LLM-call/dep/migration. Gate green (ruff · mypy · pytest). Tagged **`v1.0.7`** — closes the v1.0.7 epic; unblocks v1.0.8 (8.0 / 8.1 onward, each its own branch).

**Epic v1.0.8 — refactor → gather → correct → public-prep ("all work done by 1.0.8").** Refactor opens the window; gather + first real-data eval loop run on the decomposed code.

- [x] **8.0** `chore/ledger-reduction` — reduction micro-branch run **before** the structural epic (ledger at 10/10): clear the **CONTRIBUTING.md plugin-section drift** (stale `.claude-plugin/` commands/agents description, post-7.1 move) + the **pytest-socket `UserWarning ×2`** (one `filterwarnings` entry) carry-forward items, dropping the open ledger 10→8. Docs/test hygiene only; zero coupling to the seams. _(PROPOSED 2026-06-20, 7.9 ledger capture — owner-confirmed slot; **DONE 2026-06-21** on `chore/ledger-reduction` — both items cleared, ledger 10→8.)_
- [x] **8.1** `design/app-blueprints` — seams + shared-helpers home; test imports; lint-hook compat. **DONE 2026-06-21** (`design/app-blueprints`): design doc [`app-blueprints-design.md`](app-blueprints-design.md) — read-only investigation, **no route moved**. **Owner decisions locked:** (1) **Crafted** architecture — `create_app(config)` application-factory (retained module-level `app = create_app()` WSGI handle) + a typed injected `Config` (ends the ~35-file monkeypatch-the-global test smell) + a shared web-infra package both `app.py` + all blueprints import (so `assistant.py` drops its duplicates); (2) **8 domain seams** (analysis · generation · corpus · templates/personas · applications · users/config · diagnostics · assistant) — splits the user-facing tracker from the dev diagnostics backend. The doc carries the full **93-route→seam map**, a **zero-tech-debt definition-of-done**, and the adversarial-audit fixes (incl. the `onboarding/corpus_import.py` **second** monkeypatch front + the `ensure_dirs` byte-identical pin). Owner directives: re-architecture moment · architectural-not-spot-fix · **absolute-minimum tech debt at the v1.1.0 tag**. Refines 8.3 (adds an 8.3a foundation branch). Docs-only; ledger stays 8.
- [x] **8.2** `refactor/route-security-lint-widen` (PX-21) — widen the hook past `app.py` **before any route moves** (hook is app.py-only today); also close the `_load_config`/`_save_config` `secure_filename` gap + route-traversal tests. **DONE 2026-06-21** (`refactor/route-security-lint-widen`): (1) **hook widened** — file matcher `(^|/)app\.py$` → `… | (^|/)blueprints/.*\.py$` (covers future sub-packages; `dashboard/` deliberately excluded — localhost-gated, no `<username>`); route grep `@app\.route\(` → `@<id>\.(route|get|post|put|delete|patch)\(` (the leading `@` keeps `data.get(` from false-matching); FS-marker set += `send_from_directory(`. (2) **helper gap closed** — `_load_config`/`_save_config` sanitize via `secure_filename` *at the helper* (containment holds for raw callers, not just call sites); `get_config`/`update_config` gain a `secure_filename`-non-empty→400 guard (the `create_user` pattern; no `_safe_username` existence check → no behavior change). (3) **SECURITY.md** scoped — the two route-residence claims now read `app.py` + `blueprints/` + a `secure_filename` filename-canonicalization note; the `app.debug` 5xx-gate passage left HEAD-accurate (its `current_app.debug` re-cite is 8.3a's, when `_error_detail_payload` moves). (4) **tests** — `tests/test_app_security.py` += `TestConfigHelperContainment` + `TestConfigRouteContainment` (helper-level containment is the real proof; the `..%2f..` route case is labeled "routing rejects it", since werkzeug 404s it before the handler). (5) **hand-tested** the widened hook across a 10-case exit-code matrix (byte-correct JSON via `python3 json.dumps`) — blueprint block, sub-package, dashboard-exclusion, `.get(`-false-positive, `send_from_directory` all verified. No prompt/dep/LLM-boundary change; `PROMPT_VERSION` untouched. Gate green (ruff · mypy 190 · pytest 1319 incl. `-m ux`). Ledger stays 8.
- [x] **8.3** `refactor/app-blueprints-*` — **8.3a `refactor/app-factory-and-infra`** (factory + typed `Config` + web-infra package + `assistant.py`/`dashboard` helper dedup + `corpus_import` second-front fold + canonical `create_app(TestConfig)` test fixture + the deterministic-LLM boundary gate **PX-20**; **no route moves**) → **8.3b–h** one **domain seam** per branch (analysis · generation · corpus · templates/personas · applications · users/config · diagnostics; assistant = move-only/verify, already a blueprint); folds `ResponseReturnValue` (PV-4) on every moved route; back-nav (PX-22) rides templates; loopback bind (PX-19) rides users/config (or 8.3a). _(8-seam set + 8.3a prelude resolved by the 8.1 design, owner-locked 2026-06-21 — see [`app-blueprints-design.md`](app-blueprints-design.md) §6.)_ **8.3a DONE 2026-06-21** (`refactor/app-factory-and-infra`): `create_app(config)` factory + retained module-level `app = create_app()` handle; new top-level typed `Config` (`config.py`) + new leaf `web_infra/` package (6 fixed groups); `assistant.py` drops its 3 duplicated helpers + `dashboard` consumes the shared `_is_localhost_request`; `corpus_import._safe_load_config`/`import_candidate_from_config` gain a defaulted `configs_dir` (CLI/legacy unaffected); canonical `app`/`client` conftest fixtures + `test_assistant_route` migrated; **PX-20** `tests/test_construction_boundary.py` + **PX-19** loopback bind landed here. **No route moves**; pure refactor (routes byte-identical), no prompt/dep/migration. **Option X** (the green path): `app.py` keeps its module-global path constants + the 4 config-dependent helper copies (`_safe_username`/`_load_config`/`_save_config`/`_get_or_provision_candidate`) for the not-yet-moved routes, so the ~29 module-global monkeypatch seam tests stay green untouched — they retire seam-by-seam in 8.3b–h (transitional, time-boxed; DoD measured at the v1.1.0 tag). Gate green (ruff · mypy · pytest incl. `-m ux`). **8.3b DONE 2026-06-21** (`refactor/app-blueprints-analysis`): first **domain seam** — the 5 analysis routes (`run_analysis` · `run_analysis_stream` SSE · `run_clarify` · `submit_clarifications` · `run_iterate_clarify`) + their 3 analysis-only helpers (`_run_analysis_corpus_backed[_streaming]`, `_persist_clarifications_to_memory`) moved to new `blueprints/analysis.py` (registered **no url_prefix** → full-path decorators keep every URL byte-identical). Bodies switched to the `web_infra` helpers + `current_app.config[...]` (the SSE helper captures `output_dir` as a local **before** the generator, so `stream()` never touches `current_app` — assistant.py's pattern; no `stream_with_context` needed). **PV-4** `ResponseReturnValue` on every moved route + the 2 corpus-backed helpers (this surfaced + fixed one latent `clarification_questions` TypedDict imprecision the untyped monolith body had skipped). `blueprints/analysis.py` added to the egress allowlist (catches `anthropic` errors). **Tests:** `test_app_clarify.py` + `test_app_corpus_backed.py` migrated onto the `create_app(Config(base_dir=tmp_path))` fixture (zero app-global monkeypatch; DB-path monkeypatch kept — distinct seam); `TestIterateClarifyRoute` relocated to a new `test_app_iterate_clarify.py` on the same fixture, seeding the iteration≥1 context directly so it no longer depends on the still-in-app `/api/generate`. UX harness updated (live-app `config[...]` injection for the moved routes + `install_llm_stubs` retargeted to `blueprints.analysis`). No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy · pytest incl. `-m ux`). **8.3c DONE 2026-06-22** (`refactor/app-blueprints-generation`): second **domain seam** — the 7 generation routes (`save_edits` · `run_generation` · `run_generation_stream` SSE · `validate_refinement` · `run_generate_cover_letter` · `download_file` · `download_edited`) + their generation-only helpers (`_check_date_grounding`, `_persist_run_persona`, `_persist_cover_letter_to_db`, `_persist_corpus_generation_to_db`, and the `_apply_chosen_summary`/`_apply_chosen_experience_summaries`/`_apply_recommended_skills` trio) moved to new `blueprints/generation.py` (registered **no url_prefix** → URLs byte-identical; verified all 7 resolve as `generation.*` with one endpoint each, total url-map rule count unchanged). Bodies switched to `web_infra` helpers + `current_app.config[...]`; the SSE route captures `output_dir` before `stream()`; `download_file`'s inline containment guard preserved byte-identically. **Owner-decided cross-seam bridge:** `_resolve_persona_template_path`/`_resolve_default_persona_template_path` (templates seam, 8.3e; still called by app.py preview routes) carried as a **transitional duplicate** in the blueprint (dedupe at 8.3e) — logged in the Carry-forward ledger. **PV-4** `ResponseReturnValue` on every moved route; the loose `_apply_*(dict)` calls bridged with a runtime-noop `cast(dict, context_set)`. `blueprints/generation.py` added to the egress allowlist. **Tests:** `test_app_iteration.py` + `test_cover_letter_detached.py` migrated onto `create_app(Config(base_dir=tmp_path))` (DB-path monkeypatch kept); the 3 `_apply_*` unit tests retargeted to `blueprints.generation`; `test_persona_routes.py` `/api/download-edited` case given live-app config injection (persona fixture migrates at 8.3e). UX `install_llm_stubs` retargeted (`generate_streaming` + `_get_client` → `blueprints.generation`). No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy · pytest 67 ux + full suite). Ledger 8→9 (added the `_resolve_*` transitional-duplicate item, → clears at 8.3e). **8.3d DONE 2026-06-22** (`refactor/app-blueprints-corpus`): third + largest **domain seam** — all **42 corpus routes** moved to a new `blueprints/corpus/` **sub-package** (owner-decided 6 route files + a shared layer: `experiences.py` 15 · `summaries.py` 4 · `skills.py` 4 · `tags.py` 7 + tag helpers · `curation.py` 9 + `_find_root` · `proposals.py` 3; one `corpus_bp` in `_bp.py`; cross-cutting serializers in `_shared.py`; registered **no url_prefix** → all 42 URLs byte-identical, verified by an `app.url_map` path+methods diff vs a pre-move baseline; `app.py` now carries **zero** corpus routes). Bodies switched to `web_infra` helpers + `current_app.config[...]`; **PV-4** `ResponseReturnValue` on every route (provision result bridged with `cast("Candidate", …)`). **Owner decision (shared serializers):** `_tag_list`/`_skill_to_dict` are corpus-domain but also called by 2 un-moved applications routes — corpus owns the **canonical** copy in `_shared.py` and `app.py` imports them (legal `app.py → blueprint` direction); **no transitional duplicate, no new ledger item** (inverse of 8.3c's `_resolve_*`; relocates to `blueprints/applications` at 8.3f). **Owner-authorized hook refinement:** `route-security-lint` dropped `CONFIGS_DIR` from its FS-indicator set (post-8.3a it's only ever reached via `_safe_username(configs_dir=…)`, itself the guard; raw construction removed in PX-21) so the FS-free corpus submodules aren't false-flagged for a missing `_within`; `OUTPUT_DIR`/`RESUMES_DIR`/`open(`/`Path(`/`send_file(` stay indicators (all 3 hook arms hand-verified). `blueprints/corpus/proposals.py` is the one corpus submodule on the egress allowlist (critique + promote catch `anthropic`; ingest delegates its Haiku call to `onboarding.corpus_import`); `app.py` dropped the now-unused top-level `LLMResponseError` import (kept `import anthropic` + its allowlist entry for the applications `recommend_*` routes). The `onboarding.corpus_import` **second monkeypatch front** retired for the migrated corpus tests (provisioning threads `configs_dir`). **Tests:** all 8 corpus test files migrated onto `create_app(Config(base_dir=tmp_path))` (DB-path monkeypatch kept); ingest/proposal `_get_client` patches retargeted to `blueprints.corpus.curation`/`.proposals`; analyzer-function patches unchanged. No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy · pytest 1353 incl. `-m ux`). Ledger 9→10 (the shared-serializer share added no item; owner chose to track the pre-existing `list_resumes` raw-username observation surfaced during the move, → clears at 8.3f). **8.3e DONE 2026-06-22** (`refactor/app-blueprints-templates`): fourth **domain seam** — the **11 templates/personas routes** (`list_bundled_personas` · `list_user_personas` · `upload_user_persona` · `get_persona` · `update_persona` · `delete_persona` · `download_persona` · `preview_persona_with_resume` · `preview_application_html` · `preview_cover_letter_html` · `preview_candidate_html`) + their persona-only helpers (`_persona_dict[s_safe]`, `_preview_placeholder_html`, `_json_resume_has_content`, `_cover_letter_placeholder_html`, `_latest_generated_resume_md`, `_inline_persona_css`, `_inject_paged_polyfill` + `_PAGED_PREVIEW_INJECTION`) moved to a new single-module `blueprints/templates.py` (registered **no url_prefix** → all 11 URLs byte-identical, verified by an `app.url_map` path+methods diff, 96 rules unchanged; `app.py` now has zero persona/preview routes). Bodies switched to `web_infra` helpers + `current_app.config[...]`; **LLM-free** so **not** on the egress allowlist (verified no `anthropic` reference); PV-4 `-> ResponseReturnValue` on every route (provision result bridged with `cast("Candidate", …)`). **Ledger item 2 RESOLVED:** `_resolve_persona_template_path`/`_resolve_default_persona_template_path` now live canonically in `blueprints/templates.py`; the app.py copies + the 8.3c transitional copy in `blueprints/generation.py` are deleted, and generation imports the pair from `blueprints.templates` (sibling import; no cycle). **Owner-decided cross-seam bridge (mirrors 8.3c):** `_load_application_owned` (applications seam, 8.3f; ~10 app.py callers) carried as a **transitional duplicate** in `blueprints/templates.py` (its one port: `_safe_username(configs_dir=…)`) → dedupes at 8.3f — **new ledger item; net ledger unchanged at 10** (item 2 out, this in). **PX-22 (owner-approved rider): browser Back/Forward traverse wizard steps** (`static/app.js`) — `wizardGoTo` pushes a `{wizardStep}` `history` entry (baseline `replaceState` at `wizardInit` + the resume-from-prior landings) + a `popstate` restorer; two correctness fixes were required for Back to actually step (skip the duplicate same-step push the Skip-to-Compose double-nav created; load preview iframes via `contentWindow.location.replace` so step-4/6 preview reloads don't pollute joint history); session-only scope (no `?step=N` / deep-link). **Tests:** the 3 persona/preview files migrated onto `create_app(Config(base_dir=tmp))` (drop the 8.3c `/api/download-edited` stopgap; resolvers invoked in an app context); new `-m ux` `test_20260622_wizard_back_nav.py`; UX harness keeps `BASE_DIR`/`PERSONAS_DIR` real (bundled personas resolve) while injecting tmp `CONFIGS_DIR`/`OUTPUT_DIR`. No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy 216 · pytest 1354 incl. `-m ux`). **8.3f DONE 2026-06-22** (`refactor/app-blueprints-applications`): fifth **domain seam** — all **13 application-tracker + per-application Compose routes** (`list_applications` · `get_application` · `update_application_status` · `update_application_notes` · `update_application_meta` · `get_application_composition` · `save_application_composition` · `recommend_application_bullets` · `recommend_application_summary` · `recommend_application_experience_summaries` · `recommend_application_skills` · `suggest_application_skills` · `list_clarifications` — the design's ‡ finalize-at-move-time route, owner-placed here) + their applications-only helpers (`_VALID_APP_STATUSES`, `_application_summary_dict`, `_build_resume_state`, `_parse_ats_status`, `_find_context_path_for_run`, `_latest_analysis_essentials`, the seven `_read_*` context-override readers) moved to a new single-module `blueprints/applications.py` (registered **no url_prefix** → all 13 URLs byte-identical, verified by an `app.url_map` path+methods diff: 96 rules unchanged, only the 13 endpoint names gained the `applications.` prefix). Bodies switched to `web_infra` helpers + `current_app.config[...]`; PV-4 `-> ResponseReturnValue` on every route; `_tag_list`/`_skill_to_dict` imported from `blueprints.corpus` (legal corpus→applications direction). **Egress:** the 5 recommend/suggest routes carry the last `anthropic` references in `app.py`, so `import anthropic` is dropped from `app.py`, `app.py` is **removed** from the egress allowlist (the gate asserts both directions), and `blueprints/applications.py` is added. **Ledger item 2 RESOLVED:** `_load_application_owned` is now canonical in `blueprints/applications.py`; the app.py copy + the 8.3e transitional copy in `blueprints/templates.py` are deleted, and templates imports it from `blueprints.applications` (sibling import; no cycle). **Ledger item 3 RESOLVED (owner-signed):** `list_resumes` (`blueprints/corpus/curation.py`) gains the `_safe_username(configs_dir=…)` guard (unknown user → 400, matching `list_corpus_duplicates`) — the one behavior tightening; valid users unaffected. **Tests:** the application/composition/clarifications/recommend/suggest files migrated onto `create_app(Config(base_dir=tmp_path))` (DB-path monkeypatch kept; recommend/suggest `_get_client` stubs retargeted to `blueprints.applications`); UX harness adds the `blueprints.applications._get_client` stub. No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy 217 · pytest incl. `-m ux`). **8.3g DONE 2026-06-22** (`refactor/app-blueprints-users-config`): sixth **domain seam** — all **6 users/config routes** (`index` the SPA shell · `list_users` · `create_user` · `get_config` · `update_config` · `fetch_profile` the PX-02 profile scrape) moved to a new single-module `blueprints/users.py` (registered **no url_prefix** → all 6 URLs byte-identical, verified by an `app.url_map` path+methods diff: 96 rules unchanged, only the 6 endpoint names gained the `users.` prefix). Bodies switched to the `web_infra` config-io/security/provisioning helpers (`_load_config`/`_save_config`/`_safe_username`/`_within`/`_get_or_provision_candidate`, all `configs_dir=current_app.config["CONFIGS_DIR"]`) + `current_app.config["RESUMES_DIR"]`; `db.session`/`scraper` imports stay lazy inside `fetch_profile`; PV-4 `-> ResponseReturnValue` on every route (provision result bridged with `cast("Candidate", …)`). **LLM-free** — `fetch_profile`'s only egress is inside `scraper.py` (already allowlisted), so `blueprints/users.py` is **not** added to the egress allowlist. **app.py:** the 6 route bodies removed + the now-unused `make_response`/`render_template`/`validate_config` imports pruned; the app.py-local helper copies (`_safe_username`/`_load_config`/`_save_config`/`_get_or_provision_candidate`) + the `CONFIGS_DIR`/`RESUMES_DIR` globals are **kept** (the still-resident diagnostics routes use `_safe_username` + the globals) → the whole local-helper block retires together at 8.3h when `app.py` has zero routes. **Second monkeypatch front retired for this seam:** `fetch_profile`'s provisioning chain is fully `configs_dir`-threaded, so `test_profile_fetch_route.py` drops its `onboarding.corpus_import.CONFIGS_DIR` monkeypatch (design §7). **Tests:** `test_profile_fetch_route.py` + the `TestConfigRouteContainment` class of `test_app_security.py` migrated onto `create_app(Config(base_dir=tmp_path))` (DB-path monkeypatch kept; the 3 helper-level classes `TestSafeUsername`/`TestWithin`/`TestConfigHelperContainment` stay on the `app_module` fixture — they exercise the kept app.py-local helpers); new `test_users_routes.py` adds the previously-absent `list_users`/`create_user` unit coverage (pins the `RESUMES_DIR` config-key swap); UX harness injects `RESUMES_DIR` so a new-user flow can't write the real `resumes/`. No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy · pytest incl. `-m ux`). **8.3h DONE 2026-06-22** (`refactor/app-blueprints-diagnostics`): seventh + **final** domain seam — the **9 diagnostics routes** (`annotation_fixtures` · `annotation_load` · `annotation_save` · `annotation_collate` · `annotation_score_grounding` SSE · `annotation_seed_export` · `annotation_bootstrap_stream` SSE · `eval_run_stream` SSE · `tune_run_stream` SSE) + their 4 domain helpers (`_annotation_fixture_path` — now **pure**, takes `annotation_root` explicitly — `_load_bootstrap_doc`, `_write_seed_json`, `_patch_annotation_scores`) moved to a new single-module `blueprints/diagnostics.py` (registered **no url_prefix** → all 9 URLs byte-identical; `app.url_map` path+methods diff: 96 rules unchanged, only the 9 endpoints gained the `diagnostics.` prefix). Bodies read `current_app.config["ANNOTATION_ROOT"]`/`["CONFIGS_DIR"]` + the `web_infra` helpers; PV-4 `-> ResponseReturnValue` on every route; the 5 SSE routes capture config locals before the `stream()` generator. **LLM-free at this layer** → **not** on the egress allowlist (paid work delegated to `evals.runner`/`evals.bootstrap`/`evals.grounding_signals` + `web_infra._get_client`; verified no `anthropic` import); `app.py` stays off the allowlist. **Zero-debt completion:** `app.py` now has **zero `@app.route`** handlers (thin factory + WSGI handle + `main()` + `_should_open_browser`); the transitional local-helper block (`_safe_username`/`_load_config`/`_save_config`/`_get_or_provision_candidate`) + path globals (`BASE_DIR`/`CONFIGS_DIR`/`RESUMES_DIR`/`OUTPUT_DIR`/`ANNOTATION_ROOT`/`ALLOWED_EXTENSIONS`) were deleted (orphaned imports pruned). **Tests:** `test_annotation_routes.py` migrated onto `create_app(Config(base_dir=tmp))` (SimpleNamespace shim → bodies unchanged; DB-path monkeypatch kept); `test_app_security.py`'s 3 helper classes (`TestSafeUsername`/`TestWithin`/`TestConfigHelperContainment`) retargeted to the canonical `web_infra` helpers; UX harness updated for the global removal (`conftest.py` drops the dead module-global monkeypatch + injects `ANNOTATION_ROOT`; `seeding.py`/`stubs.py`/`flows/test_annotation_tab.py`/the education-diagnostics regression read paths from `app.config` and stub `_get_client` on `blueprints.diagnostics`). **Help-opener (#7) reviewed + DEFERRED** (owner kept the last seam a pure route move → re-targeted to a dedicated help-refactor branch; ledger holds at 8). No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched. **DoD met:** all 93 routes on a domain blueprint, `app.py` zero routes / no path globals / no per-request helpers, zero module-global monkeypatch for any moved seam. Gate green (ruff · mypy 220 · pytest 1359 incl. `-m ux`). **All 7 seams done — the v1.0.8 `app.py`→blueprints decomposition is complete.**
- [x] **8.4** `test/keep-ledger-guards` (PX-29) — do-not-regress guards so the split can't weaken the KEEP ledger. **DONE 2026-06-23** (`test/keep-ledger-guards`): the security/PII/a11y/governance KEEP set (cross-referenced from [`keep-ledger.md`](keep-ledger.md) → the findings register) converted into committed guard tests asserting the **final post-split layout**, reusing the `tests/test_egress_allowlist.py` reviewed-allowlist + `tests/test_construction_boundary.py` AST-walk precedents. **What each guard pins:** **F-sec-05 route containment** — new `tests/test_route_containment_gate.py` AST-walks every `blueprints/**.py` route and asserts every FS-touching route carries `_within` (containment) + `_safe_username` (user-scoping), with two reviewed, reasoned exemption registries (`WITHIN_NOT_REQUIRED` = delegated/fixed/sanitized-only containment: `create_user`, `annotation_fixtures`, `preview_candidate_html`; `SAFE_USERNAME_NOT_REQUIRED` = no `<username>` to verify: `download_file`, `download_persona`, `delete_persona`, `create_user`, `annotation_fixtures`) — each waives exactly one guard so teeth hold; detection is docstring/comment-free (per-stmt `ast.unparse`) + call-form (`_within(`/`_safe_username(`) so a prose mention never trips it. **F-sec-06 zero-PII clone** — new `tests/test_zero_pii_clone.py` generalizes the `configs/`-only `git ls-files` check to the whole PII/secret surface (configs/resumes/output/personas/evals-fixtures-real/db/logs allow only synthetic fixtures), asserts no secret-shaped file is tracked, scans tracked text files for the `sk-ant-…` key shape (self-safe assembled pattern), and pins the load-bearing `.gitignore` lines against a "tidy". **F-expa11y-07/08 a11y floor** — new `tests/test_a11y_floor_guards.py` (always-runs static scan: the `#srAnnounce` polite/atomic live region + `_announce()` helper + ≥7 call sites; the keyboard reorder buttons/aria-labels/`_moveBulletRow`) + new Chromium-gated `tests/ux/a11y/test_announce_live_region.py` (drives analyze→asserts the live region receives "Analysis complete"; `LiveRegion.ANNOUNCER` added to `ui_pages/selectors.py`). **F-gov-04 hook split** — new `tests/test_governance_hooks_gate.py` pins 7 blockers (reachable `exit 2`) + 3 witnesses (no `exit 2`) as named frozensets and cross-checks the `.claude/settings.json` wiring (blockers→PreToolUse, witnesses→PostToolUse). **Drift closed (owner-approved, Q1 "harden then strict gate"):** 3 behavior-identical route hardenings restored the `_within` the gate requires — `upload_resume`/`list_resumes` (`blueprints/corpus/curation.py`) gain a redundant `_within(…, RESUMES_DIR)` (always-True today: parts already `secure_filename`/`_safe_username`-sanitized); `download_file` (`blueprints/generation.py`) replaces its inline `.resolve().relative_to()` with the canonical `_within(full_path, OUTPUT_DIR)` (literal extraction). Running the gate over the real tree surfaced **more** legitimate exemptions than the plan's estimate of 2 (the registries above) — each reviewed by reading the route; documented, not silenced. No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched. Gate green (ruff · mypy · pytest incl. `-m ux`). **No new ledger item** (the F-gov-04 "AGENTS.md:96 cite imprecision" logged as an observation, not fixed here — see Carry-forward ledger).
- [ ] **8.5** **gated test window (on decomposed code)** — E2E user+dev walkthrough (R2 verified live) + `eval/live-shakedown-labels` (PV-1, **first** real-data eval/tuning loop) → numbered findings backlog.
      **Progress (2026-06-23, `eval/live-shakedown-labels`) — the eval half ran.** Landed: the **flaky Compose-wizard UX stabilization** (ledger #3, test-only — `ui_pages/wizard_compose.py` waits on `.compose-experience-card` not `.compose-row.recommended`; 20/20 loop); the **S3 before/after labeled eval → KEEP** (Carry-forward #2 **resolved**; mean judge relevance 1.12→2.58, Δ+1.46; new `scripts/vector_before_after_eval.py`); and the **PV-1 real-data shakedown** (candidate `testuser`, 3 JDs) — which **proved the real corpus→context→generate path works** (3 pipelines OK) and produced the numbered findings backlog [`window-8.5-findings.md`](window-8.5-findings.md): **EV-1** minicheck unpinned-git-dep drift (HIGH, gates PV-2) · **EV-2** grounding-abort discards paid work (Med) · **EV-3** seed-export unicode crash (Low) · **S3-1** vector index stale post-split (Med). **Carried forward (owner-decided 2026-06-23):** (a) PV-1 **label production → 8.6** (blocked on EV-1 — fix minicheck first, then one full L0+L1+L2 annotation pass; see ledger #4); (b) the **E2E walkthrough + R2-live** verification → run against `main` (runbook [`window-8.5-walkthrough.md`](window-8.5-walkthrough.md); see ledger). No prompt/dep/migration; `PROMPT_VERSION` untouched. Gate green (ruff · mypy · pytest incl. `-m ux`).
      **8.5 remainder (owed — owner-manual; a v1.0.8 tag criterion):** the E2E user+dev walkthrough + R2-live verification against `main` (runbook [`window-8.5-walkthrough.md`](window-8.5-walkthrough.md)); KW findings append to [`window-8.5-findings.md`](window-8.5-findings.md) §1 and triage into the open sprint. Carry-forward ledger item #2. _(slotted explicitly 2026-06-23.)_
- [ ] **8.6** `fix/window-findings-*` — correction sprint: burn the backlog + PV-2 calibration + PV-3 cover-letter tone + `/wiki-ingest`. May spill to a v1.0.9 epic.
      **Progress (sub-branch 1, 2026-06-23, `fix/window-findings-grounding`):** grounding slice burned (EV-1/EV-2/EV-3 + S3-1); merge `cb8dc40`. Eval/dev tooling only; `PROMPT_VERSION` untouched.
      **Progress (sub-branch 2, 2026-06-23, `fix/window-findings-tone`) — PV-3 DONE.** Cover-letter tone tune: `_COVER_LETTER_RULES_BLOCK` gained a `WORKED EXAMPLES` OK/NOT-OK opener+close sub-block + de-cloned the single Para-3 close example the model was copying into the v1.0.3 lapse; **`PROMPT_VERSION 2026-06-13.1 → 2026-06-23.1`** (the only prompt bump in the v1.0.7/v1.0.8 epics; `AVATAR_PROMPT_VERSION` untouched, no new dep). Validated via paired before/after `--suite synthetic --subset full` n=3: **tone holds at the 4.2 floor, no regression on any rubric**; opener/close fix judge-confirmed adopted; the lone pm 3.2 was a scenario-specific gap-admission hedge (a different, untargeted tone failure mode — logged as a future-tuning learning). New deterministic test `TestCoverLetterWorkedExamples`. Detail: [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md) (2026-06-23 PV-3) + [`window-8.5-findings.md`](window-8.5-findings.md). Gate green (ruff · mypy 227 · pytest 1391 incl. `-m ux`). **Remaining for 8.6/8.6a:** PV-1/PV-2 (owner-gated, staged, may spill to v1.0.9 — now slotted as **8.6b** below); the `/wiki-ingest` re-anchor folds into 8.6a.
- [ ] **8.6b** `fix/window-findings-grounding-calibration` — **PV-1 label production + PV-2 grounding calibration** (the 3rd `fix/window-findings-*` sub-branch). **Owner-gated** (manual browser annotation): bootstrap (`--grounding-signals`) → owner annotate → collate → `runner.py --suite real --seed evals/fixtures/real/testuser/seed.json` → calibrate the L0 tolerance bands + the eval-only L1/L2 NLI/MiniCheck thresholds against the labels, wire the calibrated `groundedness` into the gate / score-over-time, and close [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) "(B) deferred". EV-1 is fixed and the L0+L1+L2 scorers are proven on CPU, so this is **unblocked but staged**; **may spill to a v1.0.9 epic**. Clears Carry-forward ledger item #4 (grounding/hallucination calibrated layers). _(slotted 2026-06-23 from the carry-forward ledger — re-homing, not a new item.)_
- [x] **8.6a** `docs/assistant-wiki-coverage` — author the user/dev how-to wiki pages the avatar draws on (downloads, editing/refining, cover letters, multi-user, import mechanics, troubleshooting, the assistant itself); clears the **Assistant doc-coverage** ledger item (only ~6 `audience: user` pages exist today, so the avatar is "woefully uninformed"). Content, not code — runs after 8.6 settles the post-split route surface, before the public cut (8.7) so v1.1.0 ships a well-informed avatar; pairs with the 8.6 `/wiki-ingest`. Possibly multi-branch. _(PROPOSED 2026-06-20, 7.9 ledger capture — owner-confirmed slot.)_ **DONE 2026-06-25** (`docs/assistant-wiki-coverage`): **7 `audience: user` how-to pages** authored (`downloading-your-documents` · `editing-and-refining` · `cover-letters` · `managing-users` · `importing-your-experience` · `troubleshooting` · `using-the-assistant`) — owner-chosen **all-7-topics** scope (dedicated deep-dive pages even where 3 topics were briefly covered before; the existing wizard/corpus pages gained reciprocal `[[backlinks]]`, **not** rewrites). Every page is `audience: user` (the avatar gates retrieval by audience — `blueprints/assistant.py`), grounded in the shipped UI (`templates/index.html` ids + `static/app.js`/`static/assistant.js`) + backend (`blueprints/*`, `analyzer.py`, `web_infra/clients.py`, `pdf_render.py`); no-fabrication defers to `overview.md` (D5). `index.md` lists all 7; hub `using-sartor` "The guides" + `tailoring-a-resume`/`career-corpus` splice the new backlinks. **Per-page adversarial grounding audit (author≠auditor): 6 CLEAN / 1 DRIFTED re-anchored** (`importing-your-experience` cited `analyzer.extract_experiences` → `onboarding.extract_experiences`; "deterministic ingest" mislabel corrected — the ingest delegates a Haiku extraction). **Content pass — `.last_ingest_sha` deliberately unchanged** (`3561657…`; tracks the last *code* ingest — the `/wiki-ingest` code-keyed re-anchor stays a later pass). Docs-only — no `.py`/route/prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched; per the CHANGELOG scope rule the pass is recorded in [`docs/wiki/log.md`](../wiki/log.md), not CHANGELOG. Gate: ruff ✓ · mypy ✓ (228 files) · manual `/wiki-lint` PASS (index↔pages parity, backlinks resolve, no orphans). Clears Carry-forward ledger **#8 (Assistant doc-coverage → Resolved)**, open count **9 → 8**.
- [ ] **8.7** `release/public-prep` — `docs/screenshots`, fresh-clone < 5 min, badge set (E-2 / PX-26), UX/a11y/PDF required CI check (PX-25), doc-link sweep, **GitHub repo create + push (private/unpromoted)**.
      **Also folds in here (slotted 2026-06-23 from the carry-forward ledger — re-homing, not new items):**
      (i) **`feat/portable-enforcement-core`** — lift the portable guards (`require-feature-branch`, `block-merge-to-main`, `block-secrets`, `route-security-lint`, `ruff-changed`, `validate-context`) into a tool-agnostic core invoked by BOTH committed git-hooks AND the plugin, with CI as the server-side backstop; activate when the git remote/CI lands (ledger item). **The agent-coding-practices kit-adoption arc folds in here** (2026-06-23, [`kit-adoption-design.md`](kit-adoption-design.md) §5): the kit's mechanizable gates (`ruff format`/`ERA`/`ANN`/`D`/`interrogate`/mypy `--strict` + `gitleaks`) become rules in this shared core (the local pre-commit half can land earlier; CI-blocking activates here when the remote lands), and the component packaging reaches its clean four-parallel end-state (root `skills/` for the `context-structure-review` skill + hooks re-homed out of `.claude-plugin/`).
      (ii) the **periodic cross-document link / cite checker** — the durable CI form of the doc-link sweep above (a CI step or `wiki-lint` extended over `docs/governance/` + the contract docs); without it the extract-don't-restate pointers across the contract + governance docs are ungated (ledger item).
      (iii) **resolve the flaky Compose-wizard UX class** — a **PX-25 prerequisite**: the UX tier can't become a *required* CI gate while a compose-load race (e.g. `test_20260604_bullet_drag_reorder`, `compose.bullet_texts()[0]` IndexError) intermittently fails; needs a broader compose-load wait or a retry policy. The `.compose-experience-card` stabilization (8.5) did not cover this second race; tally reset 2026-06-23 (ledger item #3).
      (iv) the **help-opener de-dup** (`openDashHelp` ports `openHelpModal`) as pre-public **UI polish** (owner-chosen home (a), 2026-06-23; ledger item).
      (v) **PX-25 DONE (CI job) — required-check flip PENDING.** `ci/ux-a11y-required-check` (2026-07-08) added a dedicated `ux` job to [`ci.yml`](../../.github/workflows/ci.yml) (`playwright install --with-deps chromium` → `pytest -m ux` → the PDF slice `pytest -m "slow and not ux"`, single Python 3.12, Playwright-browser caching), with a documented no-retry flake policy (the `(iii)` prerequisite above is resolved by `fix/compose-settle-bg-reload`, 2026-07-06 — see CHANGELOG) and an ACTIVATION NOTE comment in the workflow. **Still owed:** flipping "required status check" is a GitHub branch-protection setting, unavailable until the **GitHub repo create + push** step above actually runs — do that first, then mark the `ux` job's check + the `quality` matrix's 3 checks required (not `eval-smoke`, which is label-gated).
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
      _(Surgical note, `fix/review-surface-and-flows`, 2026-07-08: that "N to
      review" pill counted `ProposalReview.decision=='pending'`, but the corpus
      accept/retire routes — the only UI-reachable review path — never resolved
      those rows, so the badge over-counted indefinitely; bridged +
      backfilled. Title inference also moved off the raw-first-line contract this
      paragraph describes to a role-title-only extractor, owner-approved;
      company stays in its own column, unchanged. See CHANGELOG "Fix:
      review-surface unification, corpus skill suggestions, honest application
      titles".)_
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
      `audience: user` wiki guides (`using-sartor` hub + tailoring / corpus /
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
      the stale `Cooksey/resume` disclosure channel repointed to `amodal1/sartor` in `CODE_OF_CONDUCT.md`
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

_Open count: 12 — OVER the ~8–10 reduction-sprint threshold (reduction sprint IN PROGRESS; see the dated reconciliation at the end of this note). Most 2026-07 additions drain via already-scheduled coordinates (see the aggregate rows below), so the drain plan stands in lieu of a standalone reduction sprint — but treat 10 as the ceiling: clear before adding. **Triaged 2026-06-20 (7.9 ledger capture):** each item below carries a **→ integrate at 8.x** target mapping it to an already-scheduled v1.0.8 sprint, so the ledger drains without new standalone branches. **`chore/ledger-reduction` (8.0) ran 2026-06-21** and cleared the **CONTRIBUTING-drift + pytest-socket `UserWarning`** pair (both now under Resolved), dropping the open count 10→8. **`refactor/app-blueprints-generation` (8.3c) added one item** — the `_resolve_persona_*` transitional duplicate (→ clears at 8.3e) — bumping 8→9. **`refactor/app-blueprints-corpus` (8.3d) added one item** — the pre-existing `list_resumes` raw-username observation surfaced while moving the route (owner chose to track it 2026-06-22, → 8.3f); its shared `_tag_list`/`_skill_to_dict` used the legal `app.py → blueprint` import (no transitional duplicate) — bumping 9→10. **`refactor/app-blueprints-templates` (8.3e) ran 2026-06-22** — RESOLVED the `_resolve_persona_*` duplicate (now under Resolved) and ADDED the `_load_application_owned` transitional duplicate (→ clears at 8.3f); net open count unchanged at **10**. **`refactor/app-blueprints-applications` (8.3f) ran 2026-06-22** — RESOLVED both the `_load_application_owned` transitional duplicate and the `list_resumes` raw-username hardening (both now under Resolved), dropping the open count **10→8**. **`refactor/app-blueprints-users-config` (8.3g) ran 2026-06-22** — no ledger item added or cleared: the seam introduced **no transitional duplicate** (the `web_infra` config-io/provisioning helpers already existed) and **no new observation**; help-opener (#7) still targets 8.3h as scheduled. **`refactor/app-blueprints-diagnostics` (8.3h) ran 2026-06-22** — the **seventh and last** domain seam (`app.py` → zero routes; the transitional local-helper block + path globals retired): **no ledger item added or cleared** — no transitional duplicate, and help-opener (#7) was **reviewed and deferred** (owner kept the last seam a pure route move → #7 re-targeted to a dedicated help-refactor branch). Open count holds at **8**. **Re-evaluated at 8.3g (as the threshold note required): open count holds at 8** — the four remaining targeted items all drain on already-scheduled sprints (8.5 / 8.6a / 8.7) and the citation viewer stays deferred, so no standalone reduction sprint is needed. Net drain from here: 8.5 clears the S3-eval + grounding-metric pair · 8.7 clears portable-core + link-checker + flaky-UX · 8.3f clears the `list_resumes` raw-username hardening **and** the `_load_application_owned` duplicate · 8.3 clears help-opener · 8.6a clears assistant doc-coverage · the citation viewer stays deferred → by v1.1.0 the ledger is ~2 items. **`eval/live-shakedown-labels` (8.5) ran 2026-06-23** — RESOLVED the **S3 vector tier** item (judge-scored before/after → KEEP) and ADDED the **E2E walkthrough + R2-live remainder** (deferred at close-out, owner-decided, → runs against `main` before 8.6); net open count **unchanged at 8**. The **grounding-metric** item stays open but is now precisely blocked on **EV-1** (the minicheck unpinned-git-dep drift the shakedown surfaced) — its L1/L2 labels move to 8.6 PV-2 after that fix. The 8.5 window's other findings (EV-1/2/3 + S3-1) live in [`window-8.5-findings.md`](window-8.5-findings.md), which 8.6 (`fix/window-findings-*`) burns wholesale. **`fix/window-findings-grounding` (8.6, first sub-branch) ran 2026-06-23** — burned the grounding slice (EV-1/2/3 + S3-1, all window-doc findings, **not** ledger rows) and applied the 8.5 flaky-UX stabilization annotation (now **watch**-to-resolve). **No open ledger row cleared or added:** the **grounding-metric** item stays open (its PV-2 calibration is owner-gated — EV-1 is fixed but the manual annotation labels are still owed); the **flaky-UX** item stays open in watch. Open count holds at **8**. **`docs/kit-adoption-arc` (2026-06-23) ADDED one item** — the agent-coding-practices kit-adoption staged commitments (one consolidated home for the strict-ratchet exit criterion + gate-hardness ratchet-then-block + skills/hooks coherence; → [`kit-adoption-design.md`](kit-adoption-design.md)); open count **8 → 9**, still under the ~8–10 reduction threshold. **`chore/kit-phase1-pydantic-mypy` (2026-06-23)** — Phase 1's first kit-adoption branch (`pydantic.mypy` enabled; ERA + SQLAlchemy plugin evaluated-and-rejected); added/cleared no ledger row, so open count **holds at 9** (the subsequent kit Phase-1/Phase-2 branches likewise added/cleared no ledger row). **`docs/assistant-wiki-coverage` (8.6a) ran 2026-06-25** — RESOLVED the **Assistant doc-coverage** item (7 `audience: user` how-to pages authored — all-7-topics scope; `index.md` + bidirectional backlinks reconciled; per-page author≠auditor grounding audit = 6 CLEAN + 1 re-anchored; content pass, `.last_ingest_sha` unchanged), dropping the open count **9 → 8**. **`refactor/help-opener-dedup` (v1.0.8 reduction sprint) ran 2026-06-25** — RESOLVED the **Help-opener duplication** item (#7): the wizard/console help opener + `cb_help_seen:` seam extracted into the shared leaf `static/help-modal.js` (`window.cbOpenHelpModal` + seam globals); `openHelpModal`/`openDashHelp` become thin wrappers over their own (still-local) registries, so public names + DOM ids + localStorage keys are unchanged → zero test-code changes, and the console still never loads `app.js`. Dropping the open count **8 → 7**. **`fix/compose-ux-stabilization` (2026-06-26) ran** — RESOLVED the **Flaky Compose-UX race class** item (#3): the **test-infra** causes (5 members) via a `data-compose-ready` settle marker + settle-aware POM, AND **a real rare server-side title-pin race the 6th member was catching** — `save_application_composition` now self-heals a transient title-eligibility miss (rollback + fresh-snapshot re-read before 400), proven by a deterministic miss-then-hit unit test (the live race is unreproducible). Empirical support: positioning **400/400** with the fix (was ~0.37%), full `pytest` ✓ (1394). Dropping the open count **7 → 6**. **`fix/corpus-import-and-curation-ux` (2026-06-29) ADDED one item** — the merge-suggestion similarity-threshold calibration (first-pass scorer constants validated during e2e); open count **6 → 7**, still under the ~8–10 threshold. **`feat/packaging-publish` (2026-07-02) ADDED one item** — the PyPI-wheel data-files gap (its own bullet records **7 → 8**; this header missed that update, caught by the 2026-07 efficiency review as F-doc-02). **`review/2026-07-efficiency` ran 2026-07-03** — witness-only efficiency review ADDED one aggregate item (PX-37..56 → archive); open count **8 → 9**. The review's own PX-48 prescribes compressing this head-note to a current-state summary. **`chore/upgrade-sonnet-5-model` (v1.0.8 stream) ran 2026-07-05** — the Sonnet 4.6 → Sonnet 5 model upgrade (product LLM calls + 6 plugin subagents); ADDED one item (the eval-baseline stale-vs-Sonnet-5 refresh, deferred as bookkeeping after a controlled A/B cleared the model of material regression); open count **9 → 10** (its branch-time note said 7 → 8, inheriting the pre-correction header). **`chore/ruff-format-pin` (2026-07-06) ran** — the first reduction-sprint knock-down after the generation-experience re-architecture merge: RESOLVED the ruff-format-drift item AND reconciled this head-note to reality. The running per-item tally above had lagged — this note's headline said 10 and the flaky-Compose bullet said 11 — while **13** `- [ ]` items actually rendered; the authoritative rendered count is now **12** after this item. Treat the rendered `- [ ]` count as source-of-truth; compressing this whole head-note down to a current-state summary remains PX-48's job. **`fix/compose-settle-bg-reload` (2026-07-06) ran** — RESOLVED the flaky Compose-UX item via the **settle-marker** route: a `data-compose-bg-pending` in-flight-reload counter (set as the first synchronous statement of all 11 `loadComposition()`-on-success reload sites, cleared in a `finally`) makes `_wait_settled` gate deterministically on `#composeList[data-compose-ready]:not([data-compose-bg-pending])` instead of a networkidle + stability-poll heuristic; rendered open count **12 → 11**. Reduction sprint continues — next cheap candidate: the eval-baseline refresh. **`docs/ux-review-2026-07` (2026-07-07) ADDED one aggregate item** — the 3-persona UX-review remediation backlog (F-01..F-27, waves pre-planned in the review's `50-oss-polish-plan.md`); open count **11 → 12**, over the ceiling — the reduction sprint should burn the P0 wave next. **Trains 1+2 (2026-07-07)** RESOLVED the UX-review remediation aggregate (all 27 findings landed); rendered open count **12 → 11**. **Train 3 (2026-07-08)** RESOLVED the generation-experience LATER-branch remainder; rendered open count **11 → 10**. **Train 4 (2026-07-08)** RESOLVED portable-enforcement-core + the cross-document link checker; rendered open count **10 → 8**. **Train 5 (2026-07-08)** landed the four rebased repair lanes (eval-pipeline data-safety · output identity/dates · review-surface + corpus skill suggestions · UX busy-states + full hydration) and ADDED one aggregate item — the **Walkthrough residuals (post-Train-5)** row (six items the four lanes didn't cover: persona-preview style-fidelity, `preview_candidate_html` lazy-regen, silent persona-companion failures, `/api/download-edited` identity-override wiring, page-break preview/download parity, Workday extractor research); open count **8 → 9**. **`fix/persona-fidelity-and-residuals` (2026-07-09) ran** — RESOLVED the **Walkthrough residuals (post-Train-5)** row: 5 of its 6 items closed (persona-preview style-fidelity + honest date-column layout, `preview_candidate_html` lazy-regen, silent persona-companion-failure surfacing, `/api/download-edited` identity-override wiring, page-break-parity documentation); the 6th (Workday extractor research) re-points to its own already-tracked [`nursery.md`](nursery.md) item #7 instead of duplicating an open item under this row. Also landed on this branch (no ledger row added or cleared — governance-witness status corrections + a live-backfill extractor fix, not new tracked observations): CW-101/102/103/104 witness-FLAG reconciles and the `db.build_context._infer_role_title` extractor hardening. Dropping the rendered open count **9 → 8**. **`chore/eval-baseline-sonnet-5` (2026-07-09) ran** — RESOLVED the **Eval baseline stale vs production model (Sonnet 5)** item (bookkeeping refresh: `evals/results/baseline_v1.json` re-anchored to `claude-sonnet-5` / live `PROMPT_VERSION 2026-07-08.4`; `analyzer.py` untouched, no prompt change). Dropping the rendered open count **8 → 7**. **Merge-train capture (2026-07-09, `docs/badges-readme-prep` + `chore/eval-baseline-sonnet-5`, rebase-chained, + a capture commit) ran** — `docs/badges-readme-prep` landed PX-26 (E-2 machine badge set) + PX-54 (advisory pip-audit) as committed files (the **2026-07 efficiency review — PX-37..PX-56 aggregate** row stays open with a progress clause added: 2 of the row's 20 PX rows now land); `chore/eval-baseline-sonnet-5` RESOLVED the **Eval baseline stale vs production model (Sonnet 5)** row (already reflected above, 8 → 7); the capture commit additionally RESOLVED the **E2E walkthrough + R2-live verification (8.5 remainder)** and **Merge-suggestion similarity thresholds — first-pass, e2e-validated** rows on owner e2e round-2 confirmation (owner-confirmed facts: R2 analyze-streaming verified live; merge-suggestion constants held against a real multi-résumé import). Dropping the rendered open count **7 → 5**. **`fix/round2-quick-wins` (2026-07-09) ADDED one item** — the owner's e2e round-2 UX feedback ([`reviews/2026-07-ux-round2-findings.md`](reviews/2026-07-ux-round2-findings.md)): six decision-free findings (G6/C2/T1/Co2/Co4/O1a) landed as Wave A on this branch, the design-heavy remainder registered as the **UX Cohesion Epic** ([`RELEASE_ARC.md`](RELEASE_ARC.md) "UX Cohesion Epic", unscheduled, post-v1.0.8); open count **5 → 6**. **Pre-v1.0.8-tag capture (2026-07-09, `docs/diagnostics-round2-capture`)** — the diagnostics round-2 batch (17 items) + #14 run-health durably captured under `reviews/`; dates O1b RESOLVED (keep-status-quo, no code change); ADDED the wiki-refresh deferral (219-commit ingest drift → dedicated v1.0.9 branch). Rendered open count **6 → 7**._

- [ ] **PyPI wheel not installable — data files not packaged** — **RESOLVED-PENDING-PUBLISH
      2026-07-07 (`fix/packaging-install`); left open only for the still-blocked
      `[HUMAN]` publish prerequisite below.** `create_app()` did `Flask(__name__)`, so an
      installed (non-editable) wheel looked for `templates/` next to the `app.py` module in
      `site-packages`, and there was **no `MANIFEST.in` / `package-data` /
      `include-package-data`** — so `templates/` · `static/` · `personas/bundled/` ·
      `docs/wiki/` (recall) shipped in **neither** the sdist nor the wheel, and
      `pip install sartor` / `uvx sartor` 500'd on the first page load. **Fixed:** `app.py`
      now passes absolute `template_folder`/`static_folder` to `Flask(__name__, ...)`
      (resolved via the new `config._package_dir()`, import-based — correct under both
      editable and wheel installs); `templates/`, `static/`, `personas/bundled/`, and
      `docs/wiki/` each got a marker `__init__.py` + narrow `[tool.setuptools.package-data]`
      globs (no `sartor/` package restructure needed — the smaller fix sufficed).
      **Verified** with a real fresh-venv `pip install <wheel>` started from a directory
      OUTSIDE the repo, serving a real HTTP `GET /` → 200 with the shell HTML; the **GATE
      step** in `.github/workflows/release.yml` is deleted. `tests/test_packaging.py` pins
      the code-level contract as a regression guard. Bundled together with F-24/25/26 above
      per this ledger's own note. Still open: `[HUMAN]`, one-time, the PyPI **Trusted
      Publisher** config + GHCR package visibility, both **blocked on the GitHub repo rename
      to `take-tempo-public/sartor`** (image/publish namespaces + in-app URLs depend on it) —
      unrelated to the packaging fix, un-touched by this branch.
      _(discovered: v1.0.8 stream, 2026-07-02, `feat/packaging-publish`; open count 7 → 8.)_
      **→ Integrate as its own branch before the first PyPI tag** — the container +
      `sartor --setup` ship now; the wheel path is intentionally gated until this lands.
      **Residual follow-ups (2026-07-07, `fix/packaging-install` close-out):** (i)
      `[tool.ruff] target-version` + `[tool.mypy] python_version` still say py310 — bump to
      3.11 alongside the new `requires-python` floor in a dedicated pass (deferred to avoid an
      unplanned whole-tree UP-rule autofix diff); (ii) on a bare `pip install sartor && sartor`
      run, `Config.base_dir`'s default and `dashboard/routes.py`'s `PROJECT_ROOT` resolve into
      `site-packages/` (user data + telemetry would land there) — pre-existing characteristic,
      revisit before public docs advertise the bare-wheel path as a user journey.

- [ ] **In-app rendered citation viewer (deferred)** — the avatar's numbered citations
      (Sprint 7.8d, `feat/avatar-citation-format`) link to their source **on GitHub** (wiki
      pages on `main`, code lines pinned to the unit `sha`). An **in-app** viewer — a route
      serving the wiki/source rendered in-shell so a citation opens *inside* sartor. instead
      of navigating out to GitHub — was deliberately **not** built: it needs a new
      filesystem-serving Flask route + a vendored markdown renderer + a sanitizer (new deps + a
      security-gated render surface), out of scope for a contained citation-format polish. Build
      it **only if friction warrants** — the GitHub links suffice for now, and waiting tells us
      what shape the viewer actually needs (owner 2026-06-19). Known trade-off of the GitHub-link
      approach: a code citation on an unpushed local `sha` can 404 until pushed.
      _(discovered: v1.0.7 stream, 2026-06-19, `feat/avatar-citation-format`.)_
      **→ Triage (2026-06-20, 7.9 ledger capture):** leave deferred — conditional on real
      friction (external-tab annoyance or the unpushed-`sha`-404 biting). Do not schedule.

- [ ] **Grounding / hallucination metric — calibrated layers (B)** — the deterministic
      label-free **L0** slice shipped (`eval/grounding-metric-l0`:
      `hardening.compute_fabricated_specifics` + `hardening.assemble_source_union`, a
      `groundedness` composite riding every eval record). The **calibrated model-based
      layers (L1/L2)** + the never-run v1.0.4 live loop remain open — no labeled data
      exists yet (`evals/fixtures/real/` is empty). **Scheduled as v1.0.7 Sprint PV / PV-2**
      (`eval/grounding-calibration`; [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7). Detail:
      [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md); [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md)
      "calibrated layers (B)". _(discovered: v1.0.5 stream, 2026-06-05.)_
      **→ Integrate at 8.5→8.6 (2026-06-20, 7.9 ledger capture):** PV-2 calibration, blocked on
      the 8.5 real-data labels (`evals/fixtures/real/` is empty) — leave. Pairs with the
      **S3 vector tier** item.
      **→ Update (2026-06-23, `eval/live-shakedown-labels` 8.5 shakedown):** the first real-data
      loop run surfaced **EV-1** — the L2/MiniCheck scorer is broken by an **unpinned git dep**
      (`minicheck @ git+…`; a fresh install pulled a drifted incompatible major version that
      dropped `device`/`flan-t5-large`), and the installed `transformers` (5.10.2) violates the
      `<5.0` pin (see [`window-8.5-findings.md`](window-8.5-findings.md) EV-1, HIGH). So the L1/L2
      labels **cannot be produced until minicheck is reconciled.** Owner-decided sequencing: **8.6
      PV-2 fixes EV-1 first**, then runs the full bootstrap+annotate+eval in ONE pass (full
      L0+L1+L2, no double annotation). 8.5 proved the corpus→context→generate path works + exported
      the `testuser` seed; the labels + calibration are 8.6. Still pairs with EV-2/EV-3 + S3-1 in the
      window backlog.
      **→ Update (2026-06-23, `fix/window-findings-grounding` 8.6 — EV-1 RESOLVED, PV-2 staged):**
      the grounding slice of the window backlog burned — **EV-1 fixed** (`minicheck` pinned to
      `b58b9fa`; the real breaks were the dropped `device` kwarg + the needed `accelerate` +
      `punkt_tab` — NOT the dropped `flan-t5-large`/`score()`-shape the finding claimed) and the
      **L0+L1+L2 scorers re-validated end-to-end on CPU** (NLI 0.995, MiniCheck 0.973). EV-2/EV-3/S3-1
      also resolved (see [`window-8.5-findings.md`](window-8.5-findings.md) Resolution). The metric
      **calibration itself stays open**: it needs the owner's manual browser annotation pass, so PV-2
      is **staged, owner-gated** (may spill to v1.0.9 per RELEASE_ARC §4.8). Remains open until those
      labels + the calibration land.
      **→ Update (2026-07-09, `docs/diagnostics-round2-capture` / #14 run-health review):** the owner's
      manual annotation pass **did run** this session — 53 real annotations on
      `evals/fixtures/real/robert-bootstrap/annotations.json` (verdict + should_omit fully populated) —
      but surfaced a **different, more specific blocker than "awaiting the owner":** both automated
      grounding signals (NLI + MiniCheck) are **100% null**, an annotate-flow **persistence gap** (the
      scorer works in the eval *result* records; the scores never wrote back to the fixture). PV-2
      calibration is now blocked on **fixing that persistence seam + re-running grounding**, folded into
      the **v1.0.9** Diagnostics-DX thread. Detail:
      [`reviews/2026-07-e2e-run-health-review.md`](reviews/2026-07-e2e-run-health-review.md).

- [ ] **Agent-coding-practices kit-adoption — staged commitments (2026-06-23)** — the
      [`kit-adoption-design.md`](kit-adoption-design.md) arc's cross-cutting deferrals, kept in
      **one** tracked home so they can't silently half-migrate (the hooks split-home is the
      in-repo cautionary example): (1) the **mypy `--strict` ratchet to its finite exit
      criterion** — done = no module carries a strictness override except the named exempt set
      (`tests/`/`evals/`/`scripts/`/`db/migrations/versions`; design §6), backed by a per-module
      coverage surface; (2) **gate hardness = ratchet-then-block** — strict families flip
      warn→block per-module as each clears, noisy heuristics stay warn-only forever; (3)
      **skills/hooks packaging coherence** — root `skills/` lands with the skill install, hooks
      re-home out of `.claude-plugin/` with `feat/portable-enforcement-core` (8.7), reaching the
      clean four-parallel `commands/ agents/ skills/ hooks/` end-state. Detail in the design doc +
      [`decisions.md`](decisions.md) KIT-5/6/7; this row is the single ledger home so it renders in
      every handoff until done. _(captured 2026-06-23, `docs/kit-adoption-arc`.)_
      **→ Integrate across the kit-adoption phases:** (2)/(1) ride Phases 1–2 (pre-public-capable);
      (3)'s hook half rides 8.7 `feat/portable-enforcement-core`. Clears when the ratchet hits its
      exit criterion and the four component families are parallel.
      **Progress (2026-06-23, `chore/kit-phase1-pydantic-mypy`):** Phase 1 began — **`pydantic.mypy`
      enabled** (mypy green, no new dep). Commitment (2) exercised already: **ERA evaluated → 8/8
      false-positive on documentation prose → kept unenabled/warn-only** per design Decision 6, and the
      **SQLAlchemy mypy plugin dropped** (`db/models.py` 2.0 native `Mapped[]` typing). **`ruff format`
      landed next** (`chore/kit-phase1-ruff-format`, 2026-06-23): applied tree-wide (161 files),
      proven prompt-inert (byte-identical prompt constants → no `PROMPT_VERSION` bump, no eval run),
      and **hard-blocks day one** — gate wired in `ruff-changed.sh` + `[tool.ruff.format]`
      (Decision 6 / KIT-6). **Phase 1 COMPLETE (2026-06-24, `chore/kit-phase1-sim-ruf-triage`):** the
      `SIM`/`RUF` triage landed — `SIM`+`RUF` families enabled whole, 117 ambiguous-unicode + SIM905
      ignored (no prompt string edited → no `PROMPT_VERSION` bump), RUF059 carved out in `tests/**`, and
      the 110 real hits fixed (41 auto + 32 hand + 1 `# noqa`); all enabled families hard-block day one.
      ERA stays rejected (warn-only-forever). **Phase 2 began (2026-06-24, `chore/kit-phase2-ruff-ann`):**
      the **`ANN` (flake8-annotations) family enabled whole** — the production surface was small + even
      (60 hits / 18 files; `analyzer.py` 2, `applications.py` 5, neither deferred), so `ANN` landed
      **complete across the production tree in one branch**: 60 hits hand-fixed (0 safe autofixes), the
      Decision-7 exempt set carved (`tests/**`/`evals/*`/net-new `scripts/**`), `ANN401` (11) typed
      case-by-case + one targeted `# noqa` (the SQLAlchemy `connect`-event DBAPI boundary). ANN
      hard-blocks day one (Decision-6 — unambiguous) and now carries **no production override (the §6
      exit shape for this family)**. No prompt edited → no `PROMPT_VERSION` bump, no eval run; gate green
      (ruff/format/mypy/pytest 1391). **Phase 2 #2 (2026-06-24, `chore/kit-phase2-mypy-strict-leaves`):**
      commitment (1)'s **mypy `--strict` ratchet seeded** — a per-module `[[tool.mypy.overrides]]` block
      brings the first leaves (`scraper`/`json_resume`/`pdf_render`, the deterministic LLM-free
      P1-Hardening modules) to full `--strict` + `warn_unreachable`; `strict` isn't per-module-settable
      (`mypy.options.PER_MODULE_OPTIONS`) so the preset is enumerated as its component flags. One
      `disallow_any_generics` hit fixed (`scraper` `dict` → `dict[str, Any]`); the other two were already
      strict-clean. Establishes the per-module override pattern + tracking surface the larger modules
      reuse — **3 production modules at full strict, the rest permissive**; the committed `mypy .` gate is
      the per-module block. No prompt/dep/version change; gate green (ruff/format ✓, mypy 227 ✓, pytest
      1390 + the tracked Compose-load flaky — not code-caused, ledger #3 above). **Phase 2 #3
      (2026-06-24, `chore/kit-phase2-ruff-d`):** the **ruff `D` (pydocstyle/google) family enabled** —
      content rules (D205/D209/…) swept tree-wide so they block everywhere (105 safe autofix + 143 hand;
      D205 is 100% hand-fix in ruff 0.15.12), missing-docstring rules (D101/D102/D103/D105/D107) ratchet
      per-module via a new `per-file-ignores` block (ruff has no per-file `select`, so the block lists the
      **not-yet-done** modules — inverse of the mypy override — and shrinks toward the §6 exit). First
      documented module `hardening.py` (its 10 public TypedDict classes = the `context_set` contract).
      16 ratchet entries cover the 27 undocumented files (`ui_pages/**` = 53% of the debt, the big later
      branch). PROMPT-SAFE (analyzer prompt-constant sha256 byte-identical → no `PROMPT_VERSION` bump, no
      eval run); `D` hard-blocks day one (KIT-6); no dep/version/hook change; gate green (ruff/format ✓,
      mypy 227 ✓, pytest). Row **stays open** — the remaining `D` ratchet (drain the 27 modules),
      `interrogate` coverage gate, larger-module `--strict` (`analyzer.py`/`applications.py`), + (3)'s
      skills/hooks coherence (8.7) are the remaining work; no new ledger item.
      **Phase 2 #3 ratchet — unit 2 (2026-06-24, `chore/kit-phase2-ruff-d-recall`):** drained the
      **`recall/` batch** — documented the 6 `recall/` modules (`memory_source`/`models`/`sources/{git_grep,
      session,vector,wiki}_source`; all 6 hits were constructor docstrings, 5×`__init__` D107 + 1×
      `Unit.__post_init__` D105) and removed their six `per-file-ignores` entries (**ratchet 16 → 10**;
      `hardening.py` + 6 `recall/` modules now at full `D`, **21 modules still waived**). PROMPT-SAFE
      (no prompt constants in `recall/`); no dep/version/hook change; gate green (ruff/format ✓, mypy 227
      ✓, pytest 1390 + the tracked Compose-load flaky — title-add member `test_add_title_then_pin_persists`
      recurred, passed clean isolated, ledger #3). No new ledger item.
      **Phase 2 #3 ratchet — unit 3 (2026-06-24, `chore/kit-phase2-ruff-d-config`):** drained
      **`config.py`** — documented the typed `Config` frozen dataclass and removed its
      `per-file-ignores` entry (**ratchet 10 → 9**; `hardening.py` + 6 `recall/` modules + `config.py`
      now at full `D`, **20 modules still waived**). All 6 hits were **D102** on the six derived-root
      `@property` accessors (`configs_dir`/`resumes_dir`/`output_dir`/`annotation_root`/`personas_dir`/
      `bundled_personas_dir`), each given a single-line google-style docstring (the class/module
      docstrings + the two real methods were already documented). PROMPT-SAFE (no prompt constants in
      `config.py`); no dep/version/hook change; gate green (ruff/format ✓, mypy 227 ✓, pytest 1390 +
      the tracked Compose-load flaky — a **new member** `test_happy_path_through_template_preview`
      `experience_card_count()==0`, passed clean isolated, ledger #3). No new ledger item.
      **Phase 2 #3 ratchet — unit 4 (2026-06-25, `chore/kit-phase2-ruff-d-blueprints`):** drained the
      **small-blueprints trio** — documented `blueprints/users.py` (4) + `blueprints/generation.py` (1) +
      `blueprints/corpus/curation.py` (2) and removed their three `per-file-ignores` entries (**ratchet
      9 → 6**; `hardening.py` + 6 `recall/` modules + `config.py` + the trio now at full `D`, **17
      modules still waived**). All 7 hits were **D103** on **Flask route handlers** (`list_users`/
      `create_user`/`get_config`/`update_config` · `download_file` · `upload_resume`/`list_resumes`),
      each given a single-line google-style summary of the HTTP action (matching the already-documented
      siblings `fetch_profile`/`download_edited`/`list_corpus_duplicates`); the edits were anchored
      **inside** each body (not the `@…route` decorator) so `route-security-lint` saw no route in the
      diff and the guards stayed byte-identical. PROMPT-SAFE (no prompt constants in the three route
      modules); no dep/version/hook change; gate green (ruff/format ✓, mypy 227 ✓, pytest **1391
      passed** — the ledger #3 Compose load-race did **not** fire this run, clean full suite). No new
      ledger item. Remaining `D` ratchet units (smallest first): `onboarding/` (14) · `analyzer.py`
      (16) · `db/models.py` (20) · last `ui_pages/**` (89).
      **Phase 2 #3 ratchet — unit 5 (2026-06-25, `chore/kit-phase2-ruff-d-onboarding`):** drained the
      **`onboarding/` trio** — documented `onboarding/review_cli.py` (10) + `corpus_import.py` (2) +
      `extract_experiences.py` (2) and removed their three `per-file-ignores` entries (**ratchet 6 →
      3**; `hardening.py` + 6 `recall/` modules + `config.py` + the small-blueprints trio + the
      `onboarding/` trio now at full `D`, **14 modules still waived**). 14 hits spanning every prior
      genre at once (1 D107 `__init__` + 8 D102 `ReviewSession` methods + D102 `ImportReport.merge` +
      2 D103 `main`s + 2 D101 TypedDicts), each given a single-line google-style summary inserted as
      the first body line. **First ratchet unit where a documented module also holds an LLM prompt
      constant** — `EXTRACT_EXPERIENCES_SYSTEM_PROMPT` (`extract_experiences.py:69-90`); `onboarding/`
      is **not** in the deterministic-boundary exempt set, so it may legitimately hold LLM calls +
      prompts. None of the 14 symbols is the prompt string, and PROMPT-SAFE was **proven not
      asserted**: sha256 byte-identical pre/post (`268b76…ecd1aa2`, len 2553) + a `git diff` that
      never enters the 69-90 block → no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval run. No
      dep/version/hook change; gate green (ruff/format ✓, mypy 227 ✓, pytest **1390 passed / 1 flaky**
      — the ledger #3 Compose load-race fired this run, **bullet-load mode**
      `test_20260604_bullet_drag_reorder`, passed clean on isolated re-run → confirmed flake, ledger
      #3). No new ledger item. Remaining `D` ratchet units (smallest first): `analyzer.py` (16) ·
      `db/models.py` (20) · last `ui_pages/**` (89).
      **Phase 2 #3 ratchet — unit 6 (2026-06-25, `chore/kit-phase2-ruff-d-models`):** drained
      **`db/models.py`** — gave all **20 D101 undocumented ORM classes** (`Base` + `Candidate` …
      `Engagement`) a single-line google-style docstring (the prompt-free analogue of the unit-1
      `hardening.py` TypedDict pass; the 10 already-documented model classes set the house style) and
      removed its `per-file-ignores` entry (**ratchet 3 → 2**; `db/models.py` now at full `D`, **13
      modules still waived** — `analyzer.py` + the 12-file `ui_pages/**` glob). `Base`'s bare `pass`
      was replaced by the docstring (the only deleted line; PIE790 not in select, so lint-neutral
      either way). **PROMPT-SAFE the easy way** — `db/models.py` is pure SQLAlchemy: a grep for
      `(_PROMPT|_RULES_BLOCK|PROMPT_VERSION|SYSTEM_PROMPT|AVATAR_)` returned **0**, so no prompt
      constant exists to perturb → no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval run
      (GOTCHA-4 grep-first discipline; sha256 unneeded with 0 matches). No dep/version/hook change;
      gate green (ruff/format ✓, mypy 227 ✓, pytest **1389 passed / 2 flaky** — the ledger #3 Compose
      load-race fired its strongest datapoint yet, two members at once, both proven flaky and
      code-independent; see ledger #3). No new ledger item. Remaining `D` ratchet units (smallest
      first): `analyzer.py` (16, GOTCHA-4 — holds 16 prompt constants) · last `ui_pages/**` (89).
      **Phase 2 #3 ratchet — unit 7 (2026-06-25, `chore/kit-phase2-ruff-d-analyzer`):** drained
      **`analyzer.py`** — the GOTCHA-4 prompt-home unit. Documented its **16 D-flagged symbols**
      (**14 D101** Pydantic response-model classes + **1 D102** the `ClarifyResponse` composition
      validator + **1 D107** `LLMResponseError.__init__`) with single-line google summaries naming
      which call's `_parse_or_retry` shape each validates, and removed its `per-file-ignores` entry
      (**ratchet 2 → 1**; `analyzer.py` now at full `D`, **only the 12-file `ui_pages/**` glob
      waived**). The 16 D-flagged symbols are a DIFFERENT set from the module's prompt-string
      constants (schema/validation classes vs `NAME = """…"""` literals — docstrings never touch the
      latter). **PROMPT-SAFE proven the hard way** — `analyzer.py` IS the prompt home, so sha256'd
      every prompt constant (the 11 `_BASE_SYSTEM_PROMPTS` registry values + `AVATAR_SYSTEM_PROMPT` +
      `_COVER_LETTER_RULES_BLOCK`) + both version strings, HEAD vs branch → **byte-identical** → no
      `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval run. No dep/version/hook change; gate
      green (ruff/format ✓, mypy 227 ✓, pytest **1389 passed / 2 flaky** — a new ledger #3 member
      pair, both proven flaky and code-independent; see ledger #3). No new ledger item. **Remaining
      `D` ratchet: the single `ui_pages/**` unit (89) — the LAST/LARGEST, its own dedicated branch,
      which reaches the §6 exit (block empty → `D` blocks everywhere outside the KIT-7 exempt set).**
      **Phase 2 #3 ratchet — unit 8 (2026-06-25, `chore/kit-phase2-ruff-d-ui-pages`) — RATCHET
      COMPLETE / §6 EXIT for `D`:** drained the **LAST + LARGEST** unit, `ui_pages/**` — documented
      all **89 symbols across the 12-file Playwright POM** (20 D101 POM/registry classes + 68 D102
      page/selector methods + 1 D107 `BasePage.__init__`) with single-line google summaries, removed
      the sole `"ui_pages/**"` `per-file-ignores` line, and rewrote the ratchet-block comment to record
      the exit (**ratchet 1 → 0 — block empty**). The §6 exit criterion for the `D` family is now met:
      `D` (incl. the missing-docstring codes) blocks **everywhere outside the KIT-7 exempt set**
      (`tests/`/`evals/`/`scripts/`/`db/migrations/versions`); §6-exit proof = a
      cleared-`per-file-ignores` `--select D101..D107` over the whole tree = 1417 hits, all in
      `tests/`(1406)/`scripts/`(10)/`evals/`(1), zero in production or `ui_pages`. **Pure-mechanical,
      zero GOTCHA-4 risk** — `ui_pages/` is a test driver, prompt-constant grep = 0 (no sha256 needed).
      PROMPT-SAFE → no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval; no dep/version/hook
      change; gate green (ruff/format ✓, mypy 227 ✓, pytest **1390 passed / 1 flaky** — the ledger #3
      Compose bullet-load race `test_pointer_drag_reorders` (`bullet_texts()[0]` IndexError) fired in
      the full suite + **1/2 on isolated re-run** → confirmed flake, see ledger #3). **No new ledger
      item. ruff-`D` ratchet COMPLETE; remaining Phase 2 = `interrogate` coverage gate + larger-module
      `--strict` (`analyzer.py`/`applications.py`).**
      **Phase 2 #2 ratchet — rung 2 (2026-06-25, `chore/kit-phase2-mypy-strict-applications`):**
      commitment (1)'s mypy `--strict` ratchet took its **second rung** — added
      `blueprints.applications` (~2,100 LOC, the first **non-leaf route/seam** module) to the strict
      override roster (now `scraper`/`json_resume`/`pdf_render`/`blueprints.applications`). The feared
      "heavy" larger-module branch wasn't: Phase-2 #1 (`ANN`) had already typed its whole call graph,
      so `--strict` + `warn_unreachable` surfaced **no untyped-call cascade** — only **13 mechanical
      errors** (12 bare-generic `type-arg` → parametrized, mostly `dict[str, Any]`; 1 `no-any-return`
      → `cast`). `_load_application_owned` kept as `tuple[Any, Any]` (parametrized for
      `disallow_any_generics`; the precise typed tuple would force a None-narrowing change at its 9
      in-module callers — a deferred None-safety pass, out of scope for a typing rung; docstring
      records it). **4 production modules now at full strict, the rest permissive.** PROMPT-SAFE (no
      prompt constants in the module — grep-0, prompts live in `analyzer.py`); no dep/version/hook
      change; gate green (ruff/format ✓ 217, mypy 227 ✓, pytest **1389 passed / 2 flaky** — the
      ledger #3 Compose load-race fired a two-member pair, both passed clean isolated 2/2,
      code-independent). No new ledger item. **Remaining Phase 2: `interrogate` coverage gate +
      larger-module `--strict` (`analyzer.py`, the prompt home).**
      **Phase 2 #2 ratchet — rung 3 (2026-06-25, `chore/kit-phase2-mypy-strict-analyzer`):**
      commitment (1)'s mypy `--strict` ratchet took its **third rung** — added `analyzer.py` (~3,800
      LOC, the prompt-home module + sole LLM-call site) to the strict override roster (now
      `scraper`/`json_resume`/`pdf_render`/`blueprints.applications`/`analyzer`). **This COMPLETES the
      larger-module `--strict` commitment** (`analyzer.py` was the only large module left after rung 2's
      `applications.py`). Same story as rung 2 — `ANN` had pre-typed the call graph, so `--strict` +
      `warn_unreachable` surfaced **no untyped-call cascade** — only **47 errors, ~91% mechanical** (43
      bare-generic `type-arg` → `dict[str, Any]`/`list[dict[str, Any]]`; 2 `no-any-return` → `cast`).
      The 2 `warn_unreachable` were the only judgment calls: one local widened to `object` to keep a
      documented dict-or-list dispatch branch live (zero runtime change); one deliberate `or {}`
      malformed-JSON defense kept behind a scoped `# type: ignore[unreachable]` (TypedDict types it
      always-truthy, but persisted JSON can be partial — not removed on a typing-only branch). **5
      production modules now at full strict, the rest permissive.** **PROMPT-SAFE the GOTCHA-4 way
      (sha256, not grep-0 — `analyzer.py` IS the prompt home):** the 15 prompt constants
      sha256-byte-identical pre/post (re-verified after `ruff format`) → no `PROMPT_VERSION` bump, no
      eval. No dep/version/hook change; gate: ruff/format ✓ 217, mypy 227 ✓, pytest — the ledger #3
      Compose bullet-load race **fired on the pre-commit run** (**1389 passed / 2 failed**:
      `test_keyboard_reorder_persists_and_reset_reverts` + `test_pointer_drag_reorders`), both **passed
      clean isolated**; an earlier same-session full run on the **identical** code was clean (1391/0) —
      same-code fire-then-clean = code-independent (see ledger #3). No new ledger item. **Remaining
      Phase 2: only the `interrogate` coverage gate — the larger-module `--strict` commitment is now
      COMPLETE.**
      **Phase 2 #4 — `interrogate` docstring-coverage floor-lock gate (2026-06-25,
      `chore/kit-phase2-interrogate`):** the **final Phase 2 implementation sub-item** LANDED. New
      `interrogate>=1.7,<2.0` dev dep + `[tool.interrogate]` block (production scope = KIT-7 exempt set
      excluded, `ui_pages/**` in, single-underscore semiprivate helpers excluded for `D`-coherence;
      `fail-under = 99`) + `tests/test_docstring_coverage_gate.py` — a **pytest floor-lock ratchet**
      mirroring `test_route_containment_gate.py` (subprocess re-run of the bare interrogate CLI, single
      source of truth = `[tool.interrogate]`, skip-when-absent so default `pytest` stays green / teeth in
      CI, teeth = ≥250 of 417 symbols scanned). interrogate surfaced two undocumented public classes
      (`onboarding`'s `Color` + `ExtractResponse`) that google's `D101` blind-spots (attribute-only /
      pydantic); documenting them took public-API coverage 99.5% → **100%**, so `fail-under = 99` locks a
      fully-documented baseline with ~1 pt headroom (not a brittle exact 100). Owner-directed add-on: a
      docstring-only pass documented the **50** below-public-bar internals (`_`-helpers / nested
      SSE-worker closures / private methods, ~20 files; maximal-scope coverage now 100% too) + the 5
      empty `tests/**/__init__.py` markers — the gate stays public-API-scoped (KIT-7 keeps `tests/`
      D-exempt; no per-function test docstrings). `analyzer.py` re-verified PROMPT-SAFE (15 constants
      sha256-identical). No prompt/route/version change → no eval; teeth verified (floor 100 vs 99.5% →
      red, green again at 99); gate ruff/format ✓ 218, mypy 228 ✓, pytest. **Phase 2 of the kit-adoption arc is COMPLETE** (#1 `ANN` + #2 mypy
      `--strict` larger-module + #3 `D` + #4 `interrogate`). **Row STAYS OPEN** — the §6 `--strict`-family
      exit (`app.py`, the rest of `blueprints/**`, `db/`, `hardening.py`, `parser.py`, `generator.py`, …
      a longer post-public ratchet) + (3)'s skills/hooks-packaging coherence at 8.7
      `feat/portable-enforcement-core` are the remaining kit work; no new ledger item.

- [ ] **2026-07 efficiency review — PX-37..PX-56 aggregate** — witness-only
      four-area efficiency review (agent-process DX / runtime / docs-wiki /
      tests-CI) at pin `4196d0c`: 42 register findings (14 adversarially
      verified: 4 CONFIRMED / 9 WEAKENED / 1 REFUTED-dropped) → 20 banded
      prescriptions in
      [`reviews/2026-07-efficiency/prescriptions.md`](reviews/2026-07-efficiency/prescriptions.md).
      Drains via per-PX arc coordinates: **PX-42 rides the ledger-#1
      packaging branch** (Python-floor truth BEFORE the first PyPI tag — the
      floor is actively broken, not just untested); 5 rows ride the v1.0.9
      docs epic / scheduled 8.6 ingest; 13 land in the v1.1.0-gate hardening
      window; PX-52 defers post-public. This row closes when all 20 PX rows
      are landed or explicitly re-dispositioned.
      _(added: 2026-07-03, `review/2026-07-efficiency`; open count 8 → 9.)_
      **→ Update (2026-07-07, big-push Phase 0, `chore/px-staleness-reverify`):** the 7
      flagged-stale prescriptions (PX-38/39/43/45/47/51/55) were re-verified at HEAD — all 7
      PARTIALLY_STALE with revised scopes. These dispositions are now recorded in
      [`reviews/2026-07-efficiency/px-staleness-reverify-2026-07-07.md`](reviews/2026-07-efficiency/px-staleness-reverify-2026-07-07.md)
      and cross-linked from the affected rows in `prescriptions.md`. The gen-exp §6 marker
      reconcile (`6071478`) landed on this branch as well, and the Phase-0 remainder — the
      RELEASE_ARC scope brief (§Phase 4.8, "Big-push scope brief") — landed alongside it. Also
      noted: MEMORY.md index ~19.2KB vs the 17.1KB soft target — fold a completed-cluster
      consolidation into the PX-46 owner-gated memory review.
      **→ Update (2026-07-09, `docs/badges-readme-prep`):** PX-26 (E-2 machine badge set) +
      PX-54 (pip-audit) landed as committed files — README badges row, `.github/dependabot.yml`,
      the advisory `pip-audit` CI job, `.github/workflows/scorecard.yml`, and the `REUSE.toml` +
      `LICENSES/` manifest (`reuse lint` clean, 578/578 files). 2 of the row's 20 PX rows now
      land; row stays open. Owner-activation still owed: the `take-tempo-public/sartor` GitHub
      repo creation + public promotion + PyPI Trusted Publisher config ([HUMAN], out of scope
      here) — until then the CI/Scorecard/REUSE badges render unresolved. A pinned dependency
      lockfile is a separate, still-undecided owner call.
      **→ Update (2026-07-09, `docs/v109-epic-scope`):** the GitHub repo
      `take-tempo-public/sartor` is **created + `main` pushed** (private; the throwaway GitHub
      `LICENSE` init commit was force-pushed over with the real history, owner-directed). **All
      remaining CI / PyPI / GHCR / branch-protection activation is DEFERRED to the pre-v1.1.0
      checklist per owner (2026-07-09)** — the exact one-time steps live in the workflow files
      themselves: `.github/workflows/release.yml` (PyPI Trusted Publisher — project `sartor`,
      environment `pypi`), `docker.yml` (GHCR `ghcr.io/take-tempo-public/sartor` visibility),
      and `ci.yml`'s ACTIVATION NOTE (names the four required checks; NOT `eval-smoke`), plus
      `docs/install.md`. Public promotion (repo → public) + badge/citation-link resolution land
      at v1.1.0.

- [ ] **UX round-2 remediation (e2e feedback 2026-07-09)** — the owner's second
      end-to-end walkthrough surfaced a fresh UX friction set, captured + dispositioned in
      [`reviews/2026-07-ux-round2-findings.md`](reviews/2026-07-ux-round2-findings.md). Six
      decision-free findings (G6 clarify/more-Q busy-gap, C2 skills bounded-scroll, T1
      templates-card overflow, Co2 tailor-skills-state, Co4 wire the already-built
      corpus-wide skill-suggest endpoint, O1a docx blank-line spacing) landed as **Wave A**
      on `fix/round2-quick-wins`. The design-heavy remainder — state-communication
      unification (shape = strengthen the existing `_setBusy` banner, not a new modal),
      skills redesign (denial semantics + collapsible-toggle + icon unification + ATS-shape
      tuning), a design-system pass (caps-vs-sentence-case, iconography, modal-fade
      consistency), and prior-application compact cards — is registered as the **UX
      Cohesion Epic** ([`RELEASE_ARC.md`](RELEASE_ARC.md) "UX Cohesion Epic", unscheduled,
      post-v1.0.8, version slot TBD vs the v1.0.9 docs epic). **Dates (O1b) RESOLVED
      2026-07-09** — owner chose keep-status-quo: preview/download parity holds, and right
      tab-stops are ATS-safe, so the date-column lock was a non-constraint — no code change.
      The **diagnostics round-2 batch** (17 items) + the **#14 run-health** review are durably
      captured in [`reviews/2026-07-diagnostics-round2-findings.md`](reviews/2026-07-diagnostics-round2-findings.md)
      + [`reviews/2026-07-e2e-run-health-review.md`](reviews/2026-07-e2e-run-health-review.md) and
      bundle into the v1.0.9 epic (owner-decided; nothing pre-empts the v1.0.8 tag).
      _(discovered: 2026-07-09, `fix/round2-quick-wins`; open count 5 → 6.)_
      **→ Integrate:** Wave A is done on this branch; the epic itself needs owner slotting
      before it becomes a branch sequence.

- [ ] **Wiki ingest refresh — 219 commits stale at the v1.0.8 tag** — `docs/wiki/.last_ingest_sha`
      (`3561657`) predates the entire `app.py`→`blueprints/**` decomposition + kit-adoption +
      big-push, so most code cites in the wiki have drifted. A full `/wiki-self-update` pass is a
      **v1.0.9-sized refresh, not a pre-tag top-up**, so it was **deliberately deferred**: the
      v1.0.8 tag ships with the wiki stale — a conscious deviation from the v1.0.7 wiki-clean
      precedent, justified (internal dev-docs, not product; 219-commit drift). **→ Integrate as a
      dedicated v1.0.9 branch** (`docs/wiki-refresh-v1.0.9`): run `/wiki-self-update` to re-anchor
      `.last_ingest_sha` + confirm `/wiki-lint` clean. _(discovered: 2026-07-09,
      `docs/diagnostics-round2-capture`, pre-v1.0.8 tag prep; open count 6 → 7.)_

#### Resolved

- [x] **E2E walkthrough + R2-live verification (8.5 remainder)** — the gated test window's
      *walkthrough* half. 8.5 (`eval/live-shakedown-labels`) ran the *eval* half and produced
      the findings backlog, but the **owner-driven E2E user+dev walkthrough** (R2 streaming
      verified live; app + assistant + diagnostics on the decomposed code) was **deferred at
      close-out (owner, 2026-06-23)** rather than hold the branch open on a manual activity.
      Run it against `main` (the decomposed code is already there) using the ready runbook
      [`window-8.5-walkthrough.md`](window-8.5-walkthrough.md); append KW findings to
      [`window-8.5-findings.md`](window-8.5-findings.md) §1 and triage into 8.6.
      _(deferred: v1.0.8 stream, 2026-06-23, `eval/live-shakedown-labels`.)_
      **→ Integrate before/with 8.6:** the walkthrough generates findings the 8.6 correction
      sprint burns — run it before 8.6 planning settles the post-split route surface.
      **→ Update (2026-07-08, Train 5 merge-train capture):** the owner-driven E2E walkthrough
      **RAN 2026-07-07/2026-07-08** — findings triaged into the four Train-5 repair lanes
      (`fix/eval-pipeline-and-data-safety`, `fix/output-identity-and-dates`,
      `fix/review-surface-and-flows`, `feat/ux-busy-states-and-hydration`) plus the new
      **Walkthrough residuals (post-Train-5)** row for what those lanes didn't cover (RESOLVED
      2026-07-09, `fix/persona-fidelity-and-residuals` — see Resolved below). The
      **R2-live verification** remainder (R2 streaming verified live against a running server,
      not the stubbed UX tier) is still owed — this row **stays open** until that runs.
      **RESOLVED 2026-07-09 (owner e2e round-2):** R2 analyze-streaming verified working live
      against a running server during owner testing (owner-confirmed). The E2E walkthrough half
      already ran 2026-07-07/08 (triaged into Trains 1–5); this closes the R2-live remainder.

- [x] **Merge-suggestion similarity thresholds — first-pass, e2e-validated** — the
      deterministic role-similarity scorer (`onboarding/experience_match.py`,
      `fix/corpus-import-and-curation-ux`) ships with first-pass weights + bands
      (`COMPANY_GATE` 0.6, `SIMILAR_THRESHOLD` 0.55, weights 0.40/0.20/0.15/0.25,
      `ADJACENT_MONTHS` 3) locked by **unit fixtures**, not by real multi-résumé
      imports. e2e testing is the first real exercise: if it surfaces false
      positives (distinct roles flagged) or misses (the same job not flagged),
      tune the constants against the observed cases and extend
      `tests/test_experience_match.py`. Also deferred **by design**: post-application
      merge (the merge route refuses with `409` when a source role has
      `application_run_title` / `application_bullet` / `proposal_review` refs) and
      reworded-bullet overlap (the scorer counts exact-or-lightly-fuzzy bullets;
      heavily reworded shared bullets won't register).
      _(discovered: v1.0.x stream, 2026-06-29, `fix/corpus-import-and-curation-ux`.)_
      **RESOLVED 2026-07-09 (owner e2e round-2):** the first-pass role-similarity constants
      (`onboarding/experience_match.py`) were exercised against the owner's real multi-résumé
      import — no false positives (distinct roles wrongly flagged) or misses (same job
      unflagged); the constants hold (owner-confirmed). The two by-design deferrals
      (post-application-merge 409; heavily-reworded-bullet overlap) remain documented accepted
      limitations, not open work.

- [x] **Eval baseline stale vs production model (Sonnet 5)** — after the
      `chore/upgrade-sonnet-5-model` merge, production runs `claude-sonnet-5`
      (`analyzer.py:SONNET_MODEL`) but the tracked gate baseline
      `evals/results/baseline_v1.json` still records
      `model_snapshots.sonnet = "claude-sonnet-4-6"` on an older prompt, so the
      eval-smoke gate (exit 2 on regression > 0.5 vs `baseline_v1.json`, PX-13) and
      the full-suite regression report both compare Sonnet-5 output against a
      Sonnet-4.6 reference — a standing model/prompt confound that reads as phantom
      drift. A controlled single-variable A/B on 2026-07-05 (same `2026-07-01.1`
      prompt, 4.6 vs 5, both thinking-off) showed **no material regression**:
      composites flat/pass (pm 0.0, sre −0.08, ds −0.2, all > 4.0), grounding
      flat-to-better, and the one dramatic swing (`clarification_quality` −1.0) was
      on the **unchanged Haiku `clarify` path** — i.e. judge noise, not the model.
      So this is bookkeeping, not a quality risk. Refresh: capture a fresh
      Sonnet-5 / `2026-07-01.1` baseline (schema bump per the RELEASE_ARC
      `eval/baseline-*` procedure) so future regression checks have a same-model
      reference. _(discovered: v1.0.8 stream, 2026-07-05, `chore/upgrade-sonnet-5-model`.)_
      **`fix/eval-f11-frozen-assembly` (2026-07-07) landed the corpus-backed
      `--mode assemble` eval path this refresh was scheduled after — the fresh
      Sonnet-5 baseline capture is now UNBLOCKED** (still open: no capture run yet;
      when it runs, decide whether to seed a `generate`-mode-only baseline or a
      split baseline covering both `eval_mode` populations).
      **RESOLVED 2026-07-09 (`chore/eval-baseline-sonnet-5`):** `evals/results/baseline_v1.json`
      refreshed to `model_snapshots.sonnet = "claude-sonnet-5"` / `prompt_version
      "2026-07-08.4"` — the live `analyzer.py:PROMPT_VERSION` at HEAD, not the
      `2026-07-01.1` this row originally targeted (three more merge-train lanes bumped
      it since this row was written). Bookkeeping only — `analyzer.py` untouched, no
      prompt/`PROMPT_VERSION` change. One `python evals/runner.py --suite synthetic`
      run (generate-mode only: `--mode assemble` is a structurally separate population
      per `runner.py`'s F-11 docstring, and the comparison logic doesn't support a
      split baseline, so generate-mode-only matches this file's pre-existing scope)
      populated the refreshed cells, including the new `callback_likelihood` rubric
      (added `8640773`, no prior baseline entry) seeded fresh at 4.2–4.6 across
      fixtures. `pm-senior`'s first attempt hit a Haiku judge_error (invalid JSON) on
      that rubric; re-ran the fixture standalone and used the clean re-run for all six
      `pm-senior` cells. Every cell ≥ 4.0 except the two carried-forward
      known-fragile cells (`sre-mid-level × clarification_quality` 3.2 — Haiku judge
      noise on the unchanged `clarify` path; `sre-mid-level × iteration_quality` 3.8
      n=1 — known fixture fragility, consistent with the prior 3.73 n=3 reading) —
      neither new nor attributable to the model swap. The `--subset smoke`
      self-comparison was verified **offline** (calling `runner._load_baseline_scores`
      / `runner._detect_regression` — the actual PX-13 gate functions — directly
      against the committed file: every fixture's `grounding` cell reads back
      `delta=0.0`, `is_regression=False`, `score ≥ 4.0`) rather than as a second live
      paid eval run, because estimated spend (~$0.59–0.63 across the two pipeline runs
      + 28 Haiku judge gradings) was already at the session's $0.60 budget guardrail.
      Full per-cell before/after table + methodology: `evals/TUNING_LOG.md` "Eval
      baseline model-reference refresh — 2026-07-09".

- [x] **Walkthrough residuals (post-Train-5)** —
      **RESOLVED 2026-07-09 (`fix/persona-fidelity-and-residuals`):** 5 of the 6 items
      this row tracked are closed; the 6th (Workday extractor research) was never this
      branch's to resolve and re-points below instead of duplicating a still-open item.
      **Persona-preview style-fidelity** — `docx_to_persona_html.extract_persona_style`
      now captures per-role `space_before_pt`/`space_after_pt` (mirroring
      `generator._capture_template_styles`) and `_build_css` renders it, falling back to
      the historical hardcoded px literals when the source `.docx` never set it — no
      behavior change for documents without direct spacing overrides; verified against
      the owner's uploaded persona + before/after walkthrough artifacts (python-docx
      property analysis, not committed) and all 4 bundled `TypographyPreset`s
      round-tripping exactly. **Date-column layout reconciled to reality, not idealized**
      (owner-confirmed: dates stay single-tab, no right-alignment work in the docx
      writer) — the real artifacts examined had NO captured right tab stop on the
      job-title line, so the actual `.docx` download does not right-align the date
      either; `.job-header` now only flex-justifies flush-right (`space-between`) when
      the source `.docx` defines a right tab stop, else renders inline instead of
      showing a right-alignment the download doesn't produce. **`preview_candidate_html`
      lazy-regen fallback** — gained the same lazy-companion-generation fallback its two
      sibling preview routes (`preview_application_html` / `preview_edited_html`)
      already had. **Silent persona-companion-generation failure surfaced** —
      `upload_user_persona` no longer discards `generate_companion`'s return value: a
      failure now adds `companion_warning` to the 201 response and both frontend upload
      paths (`uploadPersonaFromInput` / `uploadTemplateFromTemplateStep`) toast it;
      upload still succeeds either way (degrade, don't block) — the underlying failure
      was already logged. **`/api/download-edited` identity-override wiring** — new
      `_resolve_candidate_identity_by_username` (same identity-dict shape as
      `_resolve_candidate_identity`, keyed by username since this route has no
      `context_set` in scope) closes the gap the row's follow-up note flagged: a
      hand-edited re-download can no longer resurrect a stale name/email/website.
      **Document page-break preview/download parity** — documented as an accepted
      limitation (preview/PDF paginate via CSS + paged.js; a `.docx` download
      page-breaks the same content through Word at open time instead — parity is
      content-level per D3, not pagination-level), noted in the Step 4 (Template)
      in-app help copy and `docs/PRODUCT_SHAPE.md` §5.5. **Workday extractor research**
      — untouched by this branch; re-points to [`nursery.md`](nursery.md) item #7
      ("ATS-provider ingest research + optimization"), which already tracks it (added
      the same day this row was, 2026-07-08) — one home, not two. Riding the same
      branch: three governance-witness FLAGs (CW-101 `docx_to_persona_html.py` added to
      the `DETERMINISTIC_MODULES` gate; CW-102/104 PX-19/PX-20/D-6-Chromium status cites
      reconciled in `docs/governance/charter.md` + `enforcement.md`, owner-approved
      factual reconciles, no clause meaning changed; CW-103's `docs/PRODUCT_SHAPE.md`
      slice — dangling `app.py` route citations repointed to `blueprints/templates.py`)
      and the live-backfill `db.build_context._infer_role_title` extractor fix (boilerplate
      role-segment extraction + a glued/mojibake-prose guard). Gate green (ruff · mypy ·
      pytest incl. `-m ux`). Dropping the open count **9 → 8**.
      _(discovered: v1.0.8/Train-5 stream, 2026-07-08, merge-train capture.)_

- [x] **Portable-enforcement-core migration** —
      **RESOLVED 2026-07-08 (Train 4, big-push Phase 4):** the six portable guards lifted into
      `scripts/enforcement/` (stdlib Python core; Claude/git/CI adapters; `.githooks/` via
      opt-in `core.hooksPath`); Claude-side behavior equivalence-proven (61-test OLD-vs-NEW
      matrix + 17/17 hand-tests + a real `core.hooksPath` end-to-end); both Train-1-filed
      `block-merge-to-main` defects fixed with regressions; CI backstop latent until the git
      remote exists. Detail retained below.
      **DECIDED 2026-06-15: split** (the decision
      record is under Resolved below). The migration itself is pending: lift the portable
      guards (`require-feature-branch`, `block-merge-to-main`, `block-secrets`,
      `route-security-lint`, `ruff-changed`, `validate-context`) into a tool-agnostic shared
      core invoked by BOTH committed git-hooks (`core.hooksPath`/pre-commit) AND the Claude
      plugin, with CI as the server-side backstop. Follow-on **`feat/portable-enforcement-core`**
      clustered with the v1.0.8 gate epic when the git remote/CI activates (Sprint 8.7).
      Plan-mode lifecycle hooks stay Claude-only. _(discovered: v1.0.7 stream, 2026-06-15.)_
      **→ Integrate at 8.7 (2026-06-20, 7.9 ledger capture):** `feat/portable-enforcement-core`,
      when the git remote/CI activates — leave. **Note (8.2, 2026-06-21):** the
      `route-security-lint` widen (PX-21) kept the hook a self-contained bash script with no new
      coupling, so it stays migration-friendly for this lift.
      **Note (Train 1, 2026-07-07):** `block-merge-to-main` false-positives on READ-ONLY
      `git merge-base` invocations (its `git merge` pattern lacks a boundary against
      `merge-base`) and resolves HEAD in the hook's own cwd rather than the caller's worktree,
      so it fires from any worktree while the main checkout sits on `main` — fix both when
      lifting it into the portable core.
      **DONE (Train 4, `feat/portable-enforcement-core`, 2026-07-08):** the migration itself
      landed. One implementation per guard in `scripts/enforcement/guards/`, three consumers —
      the Claude PreToolUse adapter (unchanged `.claude-plugin/hooks/*.sh` paths, now thin
      wrappers), the opt-in native git hooks at `.githooks/` (`git config core.hooksPath
      .githooks` — see `.githooks/README.md`; NOT auto-activated), and a CI backstop step
      (`scripts/enforcement/ci_backstop.py` in `.github/workflows/ci.yml`, itself still latent
      until the git remote activates, unchanged from the rest of that workflow). Both Train-1
      `block-merge-to-main` defects noted above are fixed — the `merge-base`/`merge-tree`
      false positive (a negative-lookahead regex tightening) and the cwd misresolution (the
      Claude adapter now reads the PreToolUse `cwd` field instead of the hook process's
      ambient cwd; the git-native `pre-merge-commit`/`pre-push` adapters never had the bug,
      since git itself supplies the operation and resolves HEAD in the invoking worktree) —
      each with a dedicated regression test proving OLD-blocks/NEW-allows against the
      pre-migration script. Equivalence proved by `tests/test_enforcement_core.py` (61 cases:
      a >=3-per-guard block/allow/edge unit matrix + OLD-vs-NEW subprocess equivalence through
      the real `.claude-plugin/hooks/*.sh` wrappers, byte-correct JSON via `json.dumps`); the
      PX-29 blocker/witness gate (`tests/test_governance_hooks_gate.py`) tightened in step —
      delegated blockers prove exit-2 structurally + behaviorally through the shared adapter
      instead of the literal-`exit 2` grep the thin wrappers no longer satisfy.
      Plan-mode lifecycle hooks + the wiki-freshness reminder stayed Claude-only, untouched.
      Row's final resolution (closing the ledger item) deferred to the train-time capture.

- [x] **Periodic cross-document link / cite checker** —
      **RESOLVED 2026-07-08 (Train 4, big-push Phase 4):** `scripts/check_doc_links.py` +
      `tests/test_doc_links.py` ride the standard pytest gate (the periodic mechanism,
      CI-covered via the pytest job); the one-time sweep fixed 48+ broken links/anchors incl.
      the systemic plugin-move depth bug. Detail retained below.
      **Originally:** none exists or is planned. `wiki-lint`
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
      **→ Integrate at 8.7 (2026-06-20, 7.9 ledger capture):** as the *durable CI form* of the
      planned doc-link sweep — don't build it standalone.
      **DONE (`chore/doc-link-sweep`, 2026-07-08, ledger #7 — Phase 4/TRAIN 4):** built
      [`scripts/check_doc_links.py`](../../scripts/check_doc_links.py) (deterministic,
      stdlib-only) — tree-wide `[text](path)`/`[text](path#anchor)` link resolution +
      GitHub-anchor verification across all 190 tracked `*.md` files (incl. `docs/wiki/*.md`,
      whose links use the identical convention — trivially covered, `[[backlinks]]`/`path:line`
      *drift* stay `wiki-lint`'s job), plus file-existence checking for `` `path:line` ``/
      `` `path:SYMBOL` `` cites scoped to `docs/governance/*.md` + `AGENTS.md` + `CLAUDE.md`
      (existence only, not drift). Wired into the existing gate via
      [`tests/test_doc_links.py`](../../tests/test_doc_links.py) — no new CI job, rides `pytest`
      on every PR — which **is** the periodic mechanism this row asked for. The one-time sweep
      fixed every hit: a systemic `../../` depth bug in 6 `commands/`/`agents/` files, 4 stale
      relative-depth links, 7 dangling `README.md` anchors (a removed heading + a never-landed
      one, both retargeted to the closest live section), and 3 historical entries (incl. this
      file's own two `onboarding/import_legacy.py` cites) de-linked rather than retargeted to
      keep the historical record accurate. Full findings in the branch close-out report.
      **Row toggle + the open-count header reconcile at Phase-4/TRAIN-4 capture** (per the
      cumulative-ledger discipline — multiple ledger items land in this train).

- [x] **Generation-experience re-architecture — LATER-branch remainder** —
      **RESOLVED 2026-07-08 (Train 3, big-push Phase 3b):** all four LATER-branch
      items landed — (a) `fix/surgical-refinement-and-loopback` · (d)
      `feat/regenerate-gap-fill` · (b) `feat/wysiwyg-source-of-truth` · (c)
      `feat/clarifications-to-corpus`. Per-item DONE clauses retained below; the
      design doc's as-built sections carry the full mechanics. The CORE
      re-architecture (the "unusable" remediation's deeper vision) SHIPPED on
      `fix/compose-frozen-composition` (2026-07-06, one cohesive branch, Phases 1–4):
      (1) Compose authors + FREEZES the approved composition — the resolved
      `approved_composition` JSON-Resume snapshot (Phase 1); (2) Compose authors the
      2-sentence positioning summary (Sonnet — Phase 2) + GROUNDED gap-fill bullets
      (Sonnet accept/retire + a resolver pending-leak guard — Phase 3); (3) **Generate =
      deterministic assembly** of the frozen composition — ZERO résumé-body LLM calls;
      cover letter stays LLM; legacy + `--suite synthetic` byte-identical (Phase 4);
      preview == assemble == download by construction; a corpus-mode Refine routes BACK
      to Compose (minimal loop-back with a banner). `PROMPT_VERSION 2026-07-06.1 → .3`.
      Durable design + as-built record:
      [`generation-experience-rearchitecture.md`](generation-experience-rearchitecture.md).
      **Per-item DONE clauses (each its own LATER branch, per that doc §4/§6):** (a) **surgical
      refinement** — a scoped single-item change / grounded re-phrasing (not the current
      route-to-Compose) + the richer loop-back-with-accept/retire banner —
      **(a) DONE 2026-07-08 (`fix/surgical-refinement-and-loopback`)**: new
      `analyzer.draft_surgical_refinement()` (Sonnet) proposes ONE bullet-supersede /
      new-bullet / summary change from a free-text note (or "none" for a broad ask,
      falling back to the prior plain banner); `/draft-refinement` (read-only) +
      `/accept-refinement` apply it via the EXISTING `accepted_generated_bullet_ids` /
      `excluded` / `summary_text` override keys (zero `corpus_to_json_resume.py`
      changes); the Compose loop-back banner renders the actual proposed change with
      Accept/Retire. `PROMPT_VERSION 2026-07-06.3 → 2026-07-08.1`; (b) **in-app
      WYSIWYG editing** as source of truth (D4 — edits ARE the document) —
      **(b) DONE 2026-07-08 (`feat/wysiwyg-source-of-truth`)**: new
      `POST /api/applications/<id>/preview-edited` (content in, styled HTML out,
      nothing persisted — the preview-side twin of `/api/download-edited`); a
      debounced `input` listener swaps the Step-6 iframe's `srcdoc` so the visible
      preview never lags the editor; the cover-letter preview route now honors a
      saved `edited_cover_letter_text` (it previously ignored it outright); a new
      `_persist_edited_text_to_db` mirrors a corpus-backed edit onto
      `ApplicationRun.edited_resume_text`/`edited_cover_letter_text` (columns that
      existed but were never written) so an edit survives a resumed application
      even if its context file is gone. No prompt touched — `analyzer.py`
      untouched, `PROMPT_VERSION` unchanged; (c) **clarifications persist to the
      corpus** for cross-JD reuse (D5) — **(c) DONE 2026-07-08
      (`feat/clarifications-to-corpus`)**: `db.build_context.build_context_set_from_db`
      stages `context_set["prior_clarifications"]` (every OTHER application's
      confirmed clarification, candidate-scoped, capped at 40); `draft_positioning_summary`
      + `suggest_skills` treat it as full grounding source material (same posture as
      `<clarifications>`), `draft_gap_fill_bullets` keeps it context-only (bullet
      evidence still must cite `<career_corpus>` — unchanged); `hardening.assemble_source_union`
      widened to match so the grounding metric scores the same union the prompts see.
      `PROMPT_VERSION 2026-07-08.1 → 2026-07-08.2`. Real-LLM validated end to end
      (sandbox candidate, temp DB): a JD-1 clarification surfaced in the JD-2 summary
      + 3 skill proposals (clarification-only evidence, `bullet_id`/`experience_id: null`),
      correctly did NOT leak into a fabricated gap-fill bullet (0 proposals — the
      corpus-evidence boundary held), and did not leak across candidates. 9 real
      calls, $0.1111. As-built record: `generation-experience-rearchitecture.md` §10;
      `evals/TUNING_LOG.md` "D5 clarifications-to-corpus" entry; (d) a "Regenerate
      gap-fill" affordance (needs a `retired_gap_fill_keys` set) — **(d) DONE
      2026-07-08 (`feat/regenerate-gap-fill`)**: durable
      `composition_overrides.retired_gap_fill_keys` (written by `/gap-fill-decide`
      retire, re-sent on every `/composition` save like every other override key) +
      an always-visible "Regenerate suggestions" control that re-calls
      `/draft-gap-fill` (a third context-writing firing path, serialized through
      `data-compose-bg-pending`); the route-level exclusion filter keeps a
      regenerated draft from resurfacing a retired OR already-accepted proposal —
      deterministic, no prompt change, no `PROMPT_VERSION` bump. Real-LLM validated
      (see `evals/TUNING_LOG.md`). **All four items (a)/(b)/(c)/(d) are now DONE.**
      _(added: 2026-07-06; **CORE DONE 2026-07-06 on `fix/compose-frozen-composition`**;
      re-scoped from "whole vision owed" to the LATER-branch remainder above; (a) DONE
      2026-07-08 on `fix/surgical-refinement-and-loopback`, (b) DONE 2026-07-08 on
      `feat/wysiwyg-source-of-truth`, (c) DONE 2026-07-08 on `feat/clarifications-to-corpus`,
      (d) DONE 2026-07-08 on `feat/regenerate-gap-fill`. All four LATER-branch items
      landed.)_

- [x] **UX-review remediation (aggregate) — F-01..F-27** —
      **RESOLVED 2026-07-07 (Trains 1+2, big-push Phases 1+3):** all 27 register
      findings (+F-06d) landed — Wave 0 via Train 1 (`fix/ux-review-wave0-keyword-score`
      · `fix/ux-f02-import-skill-rows` · `fix/eval-f11-frozen-assembly` ·
      `fix/packaging-install`) and Waves 1-4 via Train 2's seven lanes. Per-wave DONE
      clauses retained below for the record.
      The 2026-07-07 three-persona
      UX review ([`docs/dev/reviews/2026-07-ux-review/`](reviews/2026-07-ux-review/README.md))
      landed 27 code-verified findings with a pre-sequenced wave plan
      ([`50-oss-polish-plan.md`](reviews/2026-07-ux-review/50-oss-polish-plan.md)).
      **Wave 0 (P0, launch blockers):** F-01 keyword-score deflation — **DONE 2026-07-07**
      (`fix/ux-review-wave0-keyword-score`: boilerplate stoplist + forgive-absence
      company-term cleaning + coverage reframe) · F-02 résumé import
      creates no Skill rows — **F-02 DONE 2026-07-07 (`fix/ux-f02-import-skill-rows`)**
      · F-11 eval harness scores the fallback LLM `generate`
      path, not the frozen-composition assembly the UI ships — **DONE 2026-07-07**
      (`fix/eval-f11-frozen-assembly`: new `evals/runner.py --mode assemble` path
      drives the SAME Compose → freeze → assemble product path —
      `recommend_bullets`/`recommend_summaries` (Haiku) → `freeze_approved_composition`
      → the deterministic assembler, zero résumé-body LLM calls, cover letter stays a
      real Sonnet call — so corpus-backed runs score the shipped assembled document;
      every JSONL record carries `eval_mode`, assemble-mode scores are exempt from the
      `baseline_v1.json` regression gate (different population); legacy `--mode generate`
      path byte-identical/unchanged. Unblocks ledger row "Eval baseline stale vs
      production model (Sonnet 5)" below to proceed) · F-24/25/26
      install.md `[dev]`/`--setup` gaps + `pyproject.toml` `py-modules` omission
      (overlaps the PyPI-wheel item below — fix together). **F-24/25/26 DONE
      2026-07-07 (`fix/packaging-install`).**
      **Wave 1+:** **F-09/F-10 DONE 2026-07-07 (`feat/ux-w1-generate-surface`)**.
      **F-19 DONE 2026-07-07 (`feat/ux-w3-demo-mode`)** — offline/demo
      mode (`SARTOR_DEMO=1`): canned fixture-derived analyzer responses, zero
      Anthropic client construction, persistent banner, telemetry-clean by
      construction. **Wave 1 (first-run delight):** F-12 progressive-disclosure
      Analyze (verdict + top-3 deterministic actions, deep read behind "Show full
      analysis") · F-06 one-time corpus-landing transition modal · F-05
      display-name-first user form with live slug derivation · F-15 deterministic
      company capture onto applications — **F-12/F-06/F-05/F-15 DONE 2026-07-07
      (`feat/ux-w1-first-run-flow`).** F-03 two skills homes (flat Settings field
      goes inert after first corpus provisioning) + F-04 education/certifications
      have no corpus panel — **F-03/F-04 DONE 2026-07-07
      (`feat/ux-w1-skills-education`)**: one home per section —
      `GET /api/users/<u>/config` now returns `needs_onboarding` (Candidate DB
      row exists?); the Settings drawer's flat Skills/Certifications/Education
      fields show a labeled "Go to Career corpus →" pointer once a candidate is
      provisioned (corpus authoritative) and stay live, unchanged, pre-provision
      (the true legacy state — Phase C.4 already removed the file-based
      analyze/generate path for everyone, so this is a per-candidate lifecycle
      flag, not a permanent second mode); new candidate-level Education +
      Certification corpus editors (8 routes, `blueprints/corpus/career_assets.py`)
      mirror the Skills editor's add/edit/retire chrome, soft-retire only
      (never hard-deleted), with a swap-and-persist ↑/↓ reorder. No automatic
      data migration between the flat fields and the corpus rows (only the
      existing one-time `import_candidate_from_config` seed). **Wave 2 (recruiter
      tier):** F-08/F-17/F-16 DONE 2026-07-07 (`feat/ux-w2-recruiter`) —
      searchable candidate roster (F-08) layered above the existing
      `#userSelect`, a read-only cross-candidate Pipeline board grouped by
      canonical status (F-17), and a one-click persona COPY-TO-CANDIDATE for
      house templates (F-16); all three share one new query-count-guarded
      aggregate endpoint (`GET /api/candidates/roster`). Screenshot evidence
      (gitignored, local): `output/ux-review-2026-07-screenshots/` + its MANIFEST.md.
      _(discovered: 2026-07-07, `docs/ux-review-2026-07`; open count 11 → 12.)_
      **→ Integrate as `fix/ux-review-wave0-*` branches before any public tag;**
      waves 1–4 drain per the polish plan. **Wave 4 (P2, aesthetic/interaction
      polish) — F-07/F-23/F-13/F-14/F-18 DONE 2026-07-07 (`feat/ux-w4-aesthetic`):**
      native `confirm()` → app-native `cbConfirm()` modal (all 10 sites) ·
      Tailor-tab fold (wizard-first, persisted collapse) · gap-fill "Optional"
      framing · edit-gate modal plain-language copy · dev-default CI/container
      auto-detection (`app._is_ci_or_container()`). **Wave 3 (contributor
      on-ramp, partial):** F-21/F-22/F-20/F-27/F-06d — **DONE 2026-07-07
      (`docs/ux-w3-contributor`)**: README three-reader-paths front matter +
      Install prominence/`git` prereq/de-jargon/"formerly Callback" note,
      model-routing prose corrected repo-wide (verified against
      `analyzer.py:SONNET_MODEL`/`HAIKU_MODEL`, incl. a `clarify()` tier bug
      found along the way), eval-smoke cost restated ~$0.35-0.40 under Sonnet 5
      (AGENTS.md/README/evals/README.md/dashboard/diagnostics.py), dashboard
      reliability tile relabeled "error rate." F-19 (demo mode) DONE (listed
      above, `feat/ux-w3-demo-mode`) — Wave 3 fully drained.

- [x] **Recurring flaky Compose-UX under full-suite concurrency (settle-marker route)** —
      **DONE 2026-07-06 on `fix/compose-settle-bg-reload` (v1.1.0 reduction sprint).** The two
      newly-recurring members — `test_20260612_experience_summary_item.py::test_positioning_pin_preserves_title_pin`
      and `test_20260611_compose_order_no_recommendations.py::test_no_recommendations_order_persists_on_reload`
      — flaked because `_wait_settled` (`ui_pages/wizard_compose.py`) rode out the Compose
      auto-recommend cascade with a one-shot `networkidle` + a hand-rolled 3×50ms marker-stability
      poll: `loadComposition()` (`static/app.js`) re-sets `data-compose-ready` at the END of each
      synchronous render, but a background call's POST + reload (the Phase-3 deferred
      `/draft-gap-fill` most visibly) lands LATER, so the poll could observe a stably-present
      marker in the window between a firing pass and its reload and **return early** onto a
      non-terminal render (the positioning-pin clobber). **Fix (settle-marker, not serialize):** a
      `data-compose-bg-pending` counter attribute on `#composeList` — incremented as the FIRST
      synchronous statement of every `loadComposition()`-on-success reload site (the 5 auto-cascade
      `_fire*` **and** the 6 user-action pin/suggest/review/accept/add reloads) so it is present
      before the marker is re-set, and decremented in a `finally` so a failed POST still balances
      (no stuck attribute → no hang). `_wait_settled` now gates deterministically on
      `#composeList[data-compose-ready]:not([data-compose-bg-pending])` — the only state that is
      the true terminal render with no reload queued — replacing the stability poll with a single
      `wait_for_selector`. Pure test-observability: no product behavior change, no `PROMPT_VERSION`
      touch. Instrumenting all 11 sites (not just the auto-cascade) makes `_wait_settled` sound as
      the general gate the POM uses it as (adversarially verified). New deterministic regression
      test `tests/ux/regression/test_20260706_compose_settle_bg_reload.py` (slow-stub the gap-fill
      draft so its reload is in flight; assert the counter fires + the settle blocks until it
      drains). Gate green: ruff · `ruff format --check` · mypy (248) · pytest ✓ (1535, +1 new); the
      two flaky members + gap-fill passed **18/18** across 3 stability re-runs and the full
      `pytest -m ux` tier (77) is green. **Deferred (not taken, not separately ledger-tracked):**
      the alternative **approach-B server-side RMW serialization** (a per-application file lock +
      atomic write across the ~10 `cp.write_text(json.dumps(ctx))` sites in
      `blueprints/applications.py`) would additionally close a **latent, self-healing**
      concurrent-RMW clobber — summary-draft + skills-recommend can fire from the same compose pass
      and both read-modify-write the same context file (the `bgDraftFiring` deferral only holds
      back gap-fill); it re-converges on the next cascade pass, so it is low severity. Recorded in
      `reference-compose-settle-bg-reload-built` (memory); promote to a tracked row only if a real
      clobber is ever observed. _(discovered: 2026-07-06, generation-experience remediation;
      carried from the prior handoff.)_ Open count **12 → 11**.

- [x] **Local ruff-0.15.12 `ruff format --check` drift on 5 UNTOUCHED files** —
      **DONE 2026-07-06 on `chore/ruff-format-pin` (v1.1.0 reduction sprint).** A one-time
      `ruff format .` swept the 5 drifting files (`docx_to_persona_html.py` + the four `tests/`
      files) into agreement with the current formatter — **formatting-only** (f-string inner-quote
      normalization, single-line collapsing, string-concat re-wrapping), **no logic**.
      **Prompt-safe:** none of the 5 is `analyzer.py`, so no prompt bytes changed → **no
      `PROMPT_VERSION` bump / no eval** (same posture as the earlier
      `reference-kit-phase1-ruff-format-built` sweep). Root-cause fix so it can't silently recur:
      **ruff exact-pinned** `ruff>=0.6,<1.0` → `ruff==0.15.12` in `pyproject.toml` (ruff doesn't
      guarantee formatter-output stability even across patches, so a floating range let the drift
      accumulate), **and** a whole-tree **`ruff format --check .` step added to CI's `quality` job**
      (`.github/workflows/ci.yml`) — CI previously only ran `ruff check` (lint) and the commit hook
      only checks STAGED files, so committed format drift was invisible. Pin + gate are one
      inseparable fix (a gate without the pin would flake CI on unrelated PRs the day a newer ruff
      releases). Gate green: ruff check · `ruff format --check` (0 drift, 234 files) · mypy (247) ·
      pytest ✓ (1534). _(discovered: 2026-07-06, `fix/compose-frozen-composition`; carried from the
      prior handoff.)_ Open count **13 → 12**.

- [x] **Flaky Compose-UX race class — and a real server-side title-pin race it was catching** —
      **DONE 2026-06-26 on `fix/compose-ux-stabilization` (v1.0.8 reduction sprint).** The recurring
      Compose-wizard UX-test class (~25 logged recurrences) had **two distinct causes**, surfaced by
      chasing the last ~1%: **(1) test-timing (5 of 6 members)** — entering Compose runs
      `loadComposition()` (`static/app.js`), which fires up to 3 background `recommend-*` calls each
      re-running it (`_clearChildren(#composeList)` + rebuild); the `ui_pages/wizard_compose.py`
      read-helpers did raw queries with no wait and read `#composeList` mid-teardown → IndexError /
      `[]` / stale. **(2) a real, rare server-side race (the 6th member,
      `test_positioning_pin_preserves_title_pin`)** — the test was catching an actual bug: the client
      sends the title pin in every `/composition` POST, but `save_application_composition`'s
      title-eligibility validation could intermittently not see a just-added title (pooled SQLite +
      WAL read-snapshot visibility), 400, and drop the pin. **Fixes:** (server) self-heal a transient
      eligibility miss — `session.rollback()` + fresh-snapshot re-read before 400 (a genuinely
      stale/foreign id still 400s), covered by a deterministic miss-then-hit unit test
      `test_post_self_heals_transient_title_visibility_miss`; (test-infra) a `data-compose-ready`
      marker on `#composeList` (cleared at `loadComposition()` entry, set after the final synchronous
      append) + `_wait_settled()` (networkidle drain + marker-stable) gating every read/action POM
      helper + new `wait_skills_card()`/`drop_skill()`/`pin_positioning_variant()`.
      `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched; no new dependency. **Validation:** the
      server self-heal is proven by the deterministic unit test — the live race is **unreproducible**
      (it masked under three separate instrumentation attempts, a Heisenbug); empirical support:
      positioning **400/400** with the fix (was ~0.37% / 2-in-544), the other 5 members **30/30** +
      group **10/10**, full `pytest` ✓ (1394), ruff/format/mypy (228) ✓. _(discovered: v1.0.6
      stream; the 8.5 `.compose-experience-card` stabilization covered only the load-timeout mode;
      fully resolved here, incl. the underlying server race.)_ Open count **7 → 6**.

- [x] **Help-opener duplication** — **DONE 2026-06-25 on `refactor/help-opener-dedup` (v1.0.8
      reduction sprint).** Extracted the byte-identical help-modal opener + the `cb_help_seen:`
      localStorage seam — duplicated between the wizard's `openHelpModal` (`static/app.js`) and the
      self-contained console's ported `openDashHelp` (`dashboard/templates/dashboard.html`) — into a
      NEW shared **leaf** module `static/help-modal.js` (`window.cbOpenHelpModal` + `cbHelpSeen` /
      `cbMarkHelpSeen` / `CB_HELP_SEEN_PREFIX`; ES5 globals, no JS build step). `openHelpModal` /
      `openDashHelp` (and the `_helpSeen` / `_dashSeen` seams) become **thin wrappers** resolving
      their **own, still-local** registry (`_HELP_REGISTRY` / `_DASH_HELP`) and delegating. The
      console still **never loads `app.js`** — the shared file is a leaf both pages load (like
      `style.css` / the vendored chart bundle), so self-containment is preserved (the 8.3h blocking
      concern). Public function names, all DOM ids (`#helpModal` / `#help-icon-*`), and the
      `cb_help_seen:` keys are unchanged → **zero test-code changes**; the `_TOUR_STOP_BLOCKS`
      suppression contract still holds. Load order pinned: classic `<script>` (no `defer`) before
      `app.js` in `templates/index.html` and in `dashboard.html` `<head>` before the inline help
      IIFE. Frontend-only — no `.py`/route/prompt/dep/migration; `PROMPT_VERSION` /
      `AVATAR_PROMPT_VERSION` untouched (no eval owed). Gate: ruff ✓ · ruff format --check ✓ · mypy ✓
      (228) · pytest ✓ (1324) · UX help/dashboard + axe ✓ (25). _(discovered: Sprint 6.5;
      re-targeted to a dedicated help-refactor branch at 8.3h; cleared here.)_

- [x] **Assistant doc-coverage — author the how-to content the avatar draws on** — **DONE
      2026-06-25 on `docs/assistant-wiki-coverage` (8.6a).** Authored **7 `audience: user`
      how-to pages** in `docs/wiki/pages/` — `downloading-your-documents`, `editing-and-refining`,
      `cover-letters`, `managing-users`, `importing-your-experience`, `troubleshooting`,
      `using-the-assistant` (the owner-chosen **all-7-topics** scope: dedicated pages even for the
      3 topics already briefly covered → the new pages are the deep-dive homes, the existing
      wizard/corpus pages gained reciprocal `[[backlinks]]`, not rewrites). The avatar gates
      retrieval strictly by audience (`blueprints/assistant.py` `Scope`), so every new page is
      `audience: user`; each grounds in the shipped UI (`templates/index.html` ids +
      `static/app.js`/`static/assistant.js`) + the backend (`blueprints/*`, `analyzer.py`,
      `web_infra/clients.py`, `pdf_render.py`), the no-fabrication promise deferring to
      `overview.md` (D5). `index.md` lists all 7 (User-facing education); hub `using-sartor`
      "The guides" + `tailoring-a-resume`/`career-corpus` splice the new backlinks. **Per-page
      adversarial grounding audit (author≠auditor): 6 CLEAN, 1 DRIFTED re-anchored**
      (`importing-your-experience` cited `analyzer.extract_experiences` →
      `onboarding.extract_experiences`; the "deterministic ingest" mislabel corrected — the
      ingest delegates a Haiku extraction). **Content pass — `.last_ingest_sha` left at
      `3561657…`** (tracks the last *code* ingest; the `/wiki-ingest` code-keyed re-anchor stays a
      later pass). Docs-only — no `.py`/route/prompt/dep/migration; per the CHANGELOG scope rule
      the pass is recorded in [`docs/wiki/log.md`](../wiki/log.md), not CHANGELOG. _(discovered:
      v1.0.7 stream, 2026-06-17, `fix/v107-ui-polish-trio` scoping; cleared at 8.6a as scheduled.)_

- [x] **`evals/runner.py` cp1252 console crash (EV-3 class)** — **DONE 2026-06-23 on
      `fix/window-findings-tone` (PV-3), owner-directed fold-in.** `python evals/runner.py --help`
      (the `→` epilog) — and any `→`/non-cp1252 print — raised `UnicodeEncodeError` under a Windows
      cp1252 console: the EV-3 class, but the 8.6 grounding fix only reconfigured
      `scripts/export_corpus_seed.py` + `capture_screenshots.py`, **not** `runner.py` (correcting
      EV-3's "fixes the whole class"). Added the same
      `sys.stdout`/`sys.stderr.reconfigure(encoding="utf-8")` loop at the top of `runner.main()`.
      **Verified exit 0** — `--help` plain **and** under forced `PYTHONIOENCODING=cp1252`. Surfaced +
      filed during the PV-3 validation; the owner directed folding the 1-liner in **before the merge**
      (avoid a follow-up branch for a 1-file edit). Open ledger unchanged at 8 (added + resolved in the
      same close-out). _(surfaced 2026-06-23, PV-3 validation harness.)_

- [x] **S3 vector tier — labeled before/after eval (gate-override validation) → KEEP** — **DONE 2026-06-23 on `eval/live-shakedown-labels` (8.5).** The judge-scored before/after relevance eval the 7.6 gate-override owed: new [`scripts/vector_before_after_eval.py`](../../scripts/vector_before_after_eval.py) runs a 12-question dev-vocab set through `recall.assemble` with the lexical tiers (wiki+git+session) vs +S3, scoring each set's relevance with the Haiku eval-judge (retrieval corpus = committed wiki+code, no PII). **Result: mean relevance base 1.12 → +S3 2.58 (Δ +1.46, +130%); improved 8/12, regressed 1/12; S3 added a lexical-missed cite on 12/12 → KEEP.** S3 earns its `numpy`+`model2vec` footprint; **no demote.** The qualitative probe's "0/12 lexical misses" (git-grep hits on all) is not counter-evidence — the judge scores those lexical-only sets at 1.12/5 (many hits, little relevance). Full detail: [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md) (2026-06-23 entry §A) + [`window-8.5-findings.md`](window-8.5-findings.md) §3. _(One gotcha surfaced + → 8.6: the `db/vector_index/` was stale post-blueprint-split (cited moved `app.py` lines); a free rebuild re-anchored it, but it has no committed rebuild trigger — finding S3-1.)_ _(discovered: v1.0.7 stream, 2026-06-16, `feat/doc-assistant-vector`; retired at the 8.5 gated test window as scheduled.)_

- [x] **`_load_application_owned` transitional duplicate in `blueprints/templates.py`** — **DONE 2026-06-22 on `refactor/app-blueprints-applications` (8.3f).** The applications seam moved `_load_application_owned` into `blueprints/applications.py` as its **canonical** home (the `_safe_username(configs_dir=current_app.config[…])` signature the templates copy already used); the app.py copy and the 8.3e transitional copy in `blueprints/templates.py` were deleted, and templates now imports it from `blueprints.applications` (sibling blueprint→blueprint import; applications never imports templates, so no cycle). _(introduced 2026-06-22 by `refactor/app-blueprints-templates` (8.3e); cleared on the applications seam as scheduled.)_

- [x] **`list_resumes` built its path from a raw (un-`_safe_username`'d) username** — **DONE 2026-06-22 on `refactor/app-blueprints-applications` (8.3f), owner-signed.** `GET /api/users/<username>/resumes` (`blueprints/corpus/curation.py`) now calls `_safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])` and returns `400` for an unknown/unsafe user (matching its sibling `list_corpus_duplicates`), instead of building the listing path from the raw route `username`. A small, owner-approved behavior tightening: a real selected user is unaffected; an unknown username is now rejected rather than reading an empty directory. _(pre-existing, surfaced 2026-06-22 while moving the route in `refactor/app-blueprints-corpus` (8.3d); cleared on the applications seam as scheduled.)_

- [x] **`_resolve_persona_*` transitional duplicate in `blueprints/generation.py`** — **DONE
      2026-06-22 on `refactor/app-blueprints-templates` (8.3e).** The templates seam moved
      `_resolve_persona_template_path` / `_resolve_default_persona_template_path` into
      `blueprints/templates.py` as their **canonical** home (modeled on generation's already-blueprint-
      shaped copy — `current_app.config[...]`, lazy DB imports, `_within` from `web_infra`); the app.py
      copies and the 8.3c transitional copy in `blueprints/generation.py` were deleted, and generation
      now imports the pair from `blueprints.templates` (sibling blueprint→blueprint import; templates
      never imports generation, so no cycle). Grep confirms exactly one definition of each, in
      `blueprints/templates.py`. _(introduced 2026-06-22 by `refactor/app-blueprints-generation` (8.3c);
      cleared on the templates seam as scheduled — the only tech debt 8.3c introduced.)_

- [x] **`CONTRIBUTING.md` plugin-section drift** — **DONE 2026-06-21 on `chore/ledger-reduction`.**
      Rewrote [`CONTRIBUTING.md`](../../CONTRIBUTING.md) "Working with the Claude Code plugin" to the
      post-7.1 layout: commands/subagents live in the repo-root `commands/` / `agents/` (loaded as the
      `sartor` plugin via the local `sartor-tools` marketplace declared in `.claude/settings.json`);
      only the hooks + the manifest (`plugin.json`) + the marketplace (`marketplace.json`) remain in
      `.claude-plugin/`. Dropped the stale skill/subagent enumeration and the "Step 5 / 8 / 9 of the
      OSS migration" references; the section now points to
      [README → Architecture & developer reference](../../README.md#architecture--developer-reference) for the full catalog
      (cite-don't-restate, charter D5 — re-listing the entries inline is what drifted in the first
      place). _(surfaced 2026-06-15, `feat/governance-extraction`; cleared on the 8.0 reduction
      micro-branch.)_

- [x] **pytest-socket `UserWarning` ×2 (latent, benign)** — **DONE 2026-06-21 on
      `chore/ledger-reduction`.** Added one message-scoped `filterwarnings` ignore to
      `pyproject.toml` `[tool.pytest.ini_options]` — `"ignore:A test tried to use
      socket.:UserWarning"`. The egress-allowlist suite
      ([`tests/test_egress_allowlist.py`](../../tests/test_egress_allowlist.py)) deliberately trips
      `pytest_socket.SocketBlockedError` to prove the socket block has teeth, and each construction
      calls `warnings.warn(...)`. The two warnings turned out to be **distinct** messages
      (`...socket.socket.` and `...socket.getaddrinfo.`), so the filter matches their shared prefix
      `A test tried to use socket.` — start-anchored and specific enough that no unrelated
      `UserWarning` is masked, and the block itself is untouched (the `SocketBlockedError` still raises).
      _(filed in memory `reference-egress-allowlist-gate`; cleared on the 8.0 reduction micro-branch.)_

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
      name in line 3 fixed to "sartor." in this branch.
- [ ] **Push to GitHub + verify the `https://github.com/take-tempo-public/sartor`
      URL resolves** **→ OPEN, owner v1.1.0** — pushed **when the user is
      ready to push the v1.1.0 public-release tag**; the repo stays
      local-only until then (no `origin` remote configured). Action at the
      v1.1.0 cut: create the GitHub repo (public, name `sartor`, under
      `amodal1`), `git remote add origin
      git@github.com:amodal1/sartor.git`, push `main` and the
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
      `onboarding/import_legacy.py`
      to dedup on **normalized bullet text** instead of
      `(source, text)`. The old key missed same-file re-imports
      because the source flips from `primary:<file>` to
      `supplemental:<file>` on the merge path, so the same text
      under two different sources slipped through as a "new"
      bullet. The new key matches regardless of source; different
      phrasings from different files still survive (they have
      different normalized text). Test
      `test_merge_dedupes_identical_bullet_text_across_sources`
      in `tests/test_onboarding_import_legacy.py`
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

   > *"Bullets are ranked by sartor's AI by fit to this job.
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
   "ranked by sartor's AI" framing — consistent vocabulary
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
2. **Anthropic model availability.** Sonnet 5 + Haiku 4.5 IDs
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
  sartor. tokens`.

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
