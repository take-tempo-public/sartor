# Changelog

All notable changes to sartor. are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope:** this file tracks product/code changes. Wiki ingest/refresh passes
> (`docs/wiki/`) are recorded in [`docs/wiki/log.md`](docs/wiki/log.md) — the wiki's
> own changelog — not here.

---

## [Unreleased]

### Fix: eval-run resilience + annotate flow + migration data-safety (`fix/eval-pipeline-and-data-safety`, 2026-07-08)

Four pre-existing bugs surfaced by the owner's E2E walkthrough triage (root-caused by a
read-only investigation, not new regressions from any recent branch — in particular, not
F-11): a scorer failure could abort a whole paid eval run, the pinned MiniCheck loader could
hard-crash on low-RAM hosts, the Annotate tab's bootstrap-complete handler could leave the
editor stuck hidden, and two 2026-05-29 migrations could silently cascade-delete a real user's
entire application/generation history on upgrade. All four fixed; each had zero prior test
coverage for the specific failure path (confirmed by reverting each fix in isolation and
re-running its new test, which then fails exactly as described below).

- **Eval run degrades, not aborts, on grounding-scorer failure**
  (`evals/runner.py`) — `run_grounding_signals(...)` sat outside the per-fixture
  `try/except` (which closes before the metrics/grounding block), so any scorer
  exception propagated out of `run_suite()` and hit the worker-thread `except Exception`
  handler in `blueprints/diagnostics.py`'s `/api/eval/run` SSE route, turning one scorer
  hiccup into a failed run — discarding the already-completed, already-paid
  analyze/clarify/generate/judge work for every fixture. Now wrapped per-fixture: a scorer
  exception degrades `grounding_signals_data` to `None` (skips `_enrich_groundedness`,
  records still write with `status: "ok"`), emits an `_emit("warning", ...)` progress event,
  and the loop continues — the same contract `evals/bootstrap.py`'s
  `build_bootstrap_document()` already uses (EV-2, window-8.5-findings). The dashboard's
  Quality-tab streamer (`dashboard/templates/dashboard.html`) gained a `warning` case in
  `describe()` mirroring the bootstrap-wrapper JS's existing `⚠` rendering.
- **MiniCheck loader hardening** (`evals/grounding_signals.py`) — the pinned minicheck
  commit's `Inferencer` hardcodes `device_map="auto"` on
  `AutoModelForSeq2SeqLM.from_pretrained` for `flan-t5-large` with no `offload_folder` or
  `device` kwarg exposed through `MiniCheck.__init__` (verified against the installed
  package's actual source, not assumed) — on a RAM-constrained host, accelerate's auto
  device-map planning can raise before the model even loads. `_load_minicheck_scorer()` now
  runs inside `_hardened_device_placement()`, a scoped monkeypatch of that one
  `from_pretrained` classmethod that forces `device_map="cpu"` (skips the GPU+CPU+disk
  auto-plan entirely) and sets an `offload_folder` fallback for genuinely constrained hosts —
  a no-op on hosts with enough RAM, always restored on exit (success or exception). The EV-1
  pin is untouched.
- **Annotate tab: bootstrap-complete now loads the editor** (`dashboard/templates/dashboard.html`)
  — the bootstrap-`done` and seed-export handlers set `$('fixtureSelect').value = slug`
  directly, which never fires `change` (and re-picking the same value manually can't fire it
  either), so the editor stayed hidden until an unrelated interaction happened to trigger a
  reload. Both handlers now call `loadFixture(slug, user)` directly after setting the select.
- **Migration data-loss fix (forward-protection P0)** (`db/migrations/versions/0006_*.py`,
  `0007_*.py`) — both used `op.batch_alter_table("application", recreate="always")` to add
  columns / swap the `status` CHECK constraint. `application` is a CASCADE parent of
  `application_run`; with the app's `PRAGMA foreign_keys=ON` connect-time default active
  during migrations too (the listener is registered on the `Engine` class, so Alembic's engine
  gets it too), the recreate's internal `DROP TABLE application` cascade-deleted every run +
  its audit trail on any DB that already had them — reproduced end-to-end (downgrade → seed
  app+run → upgrade → run count 1→0). Column adds now go through native `op.add_column` (no
  batch — the PX-02 precedent already used in migrations 0010/0011/0013). The CHECK-constraint
  swap can't go through native `ALTER TABLE` at all (SQLite has none for CHECK) and disabling
  `PRAGMA foreign_keys` around the batch recreate does NOT work either — empirically confirmed
  the pragma is a no-op once Alembic's `env.py` has opened its single wrapping transaction for
  the whole migration run. New `db/migrations/_sqlite_check_constraint.py` rewrites the CHECK
  clause by editing `sqlite_master.sql` in place (`PRAGMA writable_schema` + a
  `PRAGMA schema_version` bump) instead of rebuilding the table — no `DROP TABLE` is ever
  issued against the parent, so there's nothing for the cascade to fire on, and the chain
  reaches `head` successfully even on a DB with existing run history (verified: children
  survive, `PRAGMA integrity_check` and `PRAGMA foreign_key_check` stay clean, for a fresh
  empty DB, a pre-0006 DB with seeded history, and an already-at-head DB re-run).

### Chore: cross-document link checker + repo-wide link sweep (`chore/doc-link-sweep`, 2026-07-08)

Carry-forward ledger item #7 / RELEASE_ARC §Phase 4.8 (ii): `wiki-lint` only checks
`docs/wiki/` structural integrity, so the plain `[text](path)` links the extract-don't-restate
move multiplied across the contract docs + `docs/governance/` (and the rest of the doc set)
were ungated pointer-rot risk. **Deterministic, stdlib-only — no new dependency.**

- **New checker** — [`scripts/check_doc_links.py`](scripts/check_doc_links.py): resolves every
  relative `[text](path)` / `[text](path#anchor)` markdown link in all 190 tracked `*.md` files
  (repo-wide, including `docs/wiki/*.md` — it uses the identical relative-link convention as
  every other doc) against its containing file, verifies the target exists, and — for `.md`
  targets with a `#fragment` — verifies a matching heading via a conservative GitHub-anchor
  slugger (handles the repo's real double-hyphen cases from stripped `&`/`—`/`→`). Separately,
  scoped to `docs/governance/*.md` + `AGENTS.md` + `CLAUDE.md`, verifies the **file** named by
  each `` `path:SYMBOL` ``/`` `path:LINE` `` cite exists (existence only — line-drift checking
  stays `wiki-lint`'s job). Skips external URLs, fenced code, literal backtick-quoted link
  syntax examples, and gitignored targets; two narrow documented `(file, target)` exclusions
  cover a generic `[text](path)` prose idiom and a destination-relative insertion-template doc.
- **Wired into the existing gate, not a new CI job** —
  [`tests/test_doc_links.py`](tests/test_doc_links.py) re-runs the checker as a subprocess and
  asserts exit 0, so it rides `pytest` on every PR (already CI-covered).
- **The sweep** — fixed every link/cite the checker found: a systemic `../../` depth bug in 6
  `commands/`/`agents/` files (pre-dated the plugin-activation move to repo root), 4 stale
  relative-depth links (`docs/dev/RELEASE_ARC.md`'s `excellence-walk/` refs, a design doc's
  nested review-directory refs, a stale `.claude-plugin/agents/` path), 3 dangling `README.md`
  anchors from a since-removed "Claude Code Plugin" heading (retargeted to the current
  `#architecture--developer-reference` section) and 4 from a never-landed `#cost` anchor
  (retargeted to `#install`, the closest live section), and 3 historical entries in
  `CHANGELOG.md`/`RELEASE_CHECKLIST.md`/an archived UX audit that named a since-renamed file —
  de-linked (kept as plain text) rather than retargeted, so the historical record stays accurate.

### CI: UX/a11y tier as a CI job, required-check ready (`ci/ux-a11y-required-check`, 2026-07-08)

PX-25 (2026-06 product-excellence review, `F-qe-rel-01` P0): the browser-driven
UX/a11y/PDF tier (`pytest -m ux` + the axe a11y gate + the PDF end-to-end
renders) ran on the maintainer's laptop only — `ci.yml` had no `playwright
install`, so the tier was silently collected-then-skipped in CI (documented as
a known gap in `ACCESSIBILITY.md`). This lands the CI job the tier needed; the
GitHub "required status check" flip is a separate, owner-gated repo setting
that cannot be configured until the `[HUMAN]` GitHub-repo-creation step
(RELEASE_ARC Phase 4) — see the activation note below.

- **New `ux` job in `.github/workflows/ci.yml`**, separate from the `quality`
  matrix so the fast py3.11–3.13 lint/type/unit gate isn't slowed by a
  Chromium install: `pip install -e '.[dev]'` → `python -m playwright install
  --with-deps chromium` → `pytest -m ux`. Single Python version (3.12, the
  middle of the `quality` matrix's 3.11–3.13 range) — Playwright/browser
  behavior isn't Python-version-sensitive, so matrixing would ~triple runtime
  for no coverage gain. `needs`/concurrency wiring between jobs is
  deliberately left undecided (PX-43, Phase 7 — out of scope here).
- **Caching:** `actions/setup-python`'s built-in `cache: pip` (same as
  `quality`) plus a new `actions/cache` step keyed on the installed
  Playwright version, caching `~/.cache/ms-playwright` (the ~150MB Chromium
  binary) — the slowest step in the job on a cache hit. `actions/cache` is
  GitHub-maintained, the same trust tier as `actions/checkout`/
  `actions/setup-python` already used in this file. OS-level Playwright deps
  (`install-deps`) still run every time — ephemeral runner VMs don't preserve
  apt packages regardless of the browser-binary cache.
- **Flake policy (HONEST, not masking) — no automatic retry.** The suite's
  known flake class (a Compose-wizard settle race under heavy LOCAL
  multi-suite concurrency) was root-caused and fixed 2026-07-06
  (`fix/compose-settle-bg-reload` — see that entry below); every recurrence
  since has reproduced ONLY under that concurrent-load condition, always
  green in isolation. A single dedicated CI job running one `pytest -m ux`
  invocation with no sibling suite contending for the same server cannot
  reproduce that precondition, so a retry step here would not be absorbing a
  *known* flake — it would silently re-run under an uncharacterized failure
  mode and report green, which is exactly the masking this policy avoids. If
  the `ux` job fails in CI, treat it as a real signal and investigate first;
  a genuinely new CI-only flake class would need its own scoped, documented
  retry, not a pre-emptive blanket one. Full rationale recorded as a comment
  block in the workflow itself.
- **PDF slice included.** RELEASE_ARC/RELEASE_CHECKLIST call this the
  "UX/a11y/PDF tier", but `pytest -m ux` alone doesn't cover the PDF
  end-to-end tests — the 4 tests in `tests/test_pdf_render.py` are marked
  `slow` only. The job's last step runs `pytest -m "slow and not ux"` too,
  reusing the Chromium install already done for the `ux` step rather than
  standing up a second job for 4 tests — so the tier's name is now accurate
  in CI, not just on the maintainer's machine.
- **Activation note (owed at the `[HUMAN]` GitHub-repo-creation step):** a CI
  job existing does not make it a "required check" — that's a GitHub repo
  setting (Settings → Branches → branch protection rule for `main` →
  "Require status checks to pass before merging"), unavailable until the
  repo exists. When it does: mark the `ux` job's check ("UX / a11y / PDF
  (Playwright, py3.12)") AND the `quality` matrix's 3 checks required. Do
  NOT mark `eval-smoke` required — it's label-gated (`eval` label only), so
  a required-but-conditional check would block every unlabeled PR forever.
- **Docs/workflow only** — no dependency change (`playwright` is already a
  pinned hard dep; `actions/cache` is a workflow-file action, not a Python
  package), no route/prompt/migration; `PROMPT_VERSION` unchanged.

### Feat: portable enforcement core — one guard implementation, three consumers (`feat/portable-enforcement-core`, 2026-07-08)

Lifts the six portable dev-loop guards (`require-feature-branch`, `block-merge-to-main`,
`block-secrets`, `route-security-lint`, `ruff-changed`, `validate-context`) out of
standalone `.claude-plugin/hooks/*.sh` bash and into a tool-agnostic shared core, so the
rules hold for plain `git commit`/`git merge`/`git push` too, not only inside a Claude
Code session (RELEASE_ARC §Phase 4.8 public-prep item (i); `docs/governance/
enforcement.md` "gate" side of the gate/witness/tribal split).

- **One implementation per guard** in `scripts/enforcement/guards/` (pure `decide()`
  functions, stdlib-only). **Three consumers**: the Claude Code PreToolUse adapter
  (`scripts/enforcement/adapters/claude_hook.py`, invoked by thin wrappers left at the
  same `.claude-plugin/hooks/*.sh` paths — `.claude/settings.json` wiring untouched); the
  native git hooks at `.githooks/` (`pre-commit`, `pre-merge-commit`, `pre-push`), opt-in
  per clone via `git config core.hooksPath .githooks` (see `.githooks/README.md` — **not**
  activated automatically); and a CI backstop step (`scripts/enforcement/ci_backstop.py`,
  a repo-wide secrets scan wired into `.github/workflows/ci.yml`, itself still latent
  until the git remote activates, same as the rest of that workflow).
- **Fixes both defects filed against `block-merge-to-main`** (RELEASE_CHECKLIST.md
  "Portable-enforcement-core migration" ledger row, Train-1 note, 2026-07-07): (i) the
  `\bgit merge\b` pattern false-positived on read-only `git merge-base`/`git merge-tree`
  (the `\b` boundary is satisfied at the `e`→`-` transition) — fixed with a negative
  lookahead; (ii) the dominant-direction check resolved HEAD via a bare
  `git rev-parse --abbrev-ref HEAD`, which runs in the hook *process's* ambient cwd —
  under parallel-worktree sessions (charter W-1) that isn't guaranteed to be the invoking
  agent's own worktree. Fixed by resolving against the PreToolUse hook-input `cwd` field
  instead. The native `pre-merge-commit`/`pre-push` git hooks never had either bug — git
  itself supplies the real operation and resolves HEAD in the invoking worktree.
- **Plan-mode lifecycle hooks** (`check-plan-approved`, `mark-plan-approved`,
  `cleanup-plan-on-merge`) and the wiki-freshness reminder stay Claude-only, untouched.
- Proven with `tests/test_enforcement_core.py`: a >=3-case-per-guard block/allow/edge unit
  matrix over the pure `decide()` functions, plus an OLD-vs-NEW equivalence harness that
  runs the pre-migration standalone scripts (extracted from git history) side-by-side with
  the migrated wrappers against byte-correct PreToolUse JSON, asserting matching exit
  codes and block-message substance — including two dedicated regression cases proving
  each `block-merge-to-main` defect existed pre-fix and is gone post-fix.
- The PX-29 blocker/witness governance gate (`tests/test_governance_hooks_gate.py`)
  tightened to the new architecture: the six core-delegated blockers now prove their
  reachable exit-2 structurally (the wrapper execs the shared adapter, naming its own
  guard) + behaviorally (the adapter's blocked path returns 2, asserted in-process),
  replacing the literal-`exit 2` grep those wrappers no longer satisfy;
  `check-plan-approved` keeps the literal-text check. Blocker/witness counts and the
  `settings.json` wiring pins are unchanged.

### Feat: clarifications persist to the corpus for cross-JD reuse (`feat/clarifications-to-corpus`, 2026-07-08)

Generation-experience re-architecture — item (c) of the LATER-branch remainder
(D5: [`docs/dev/generation-experience-rearchitecture.md`](docs/dev/generation-experience-rearchitecture.md)
§2 Stage 3 / §3.5 point 3). A clarification the candidate confirms while
working one JD now informs Compose content drafting for every LATER JD, not
just the one it was answered under.

- **`db.build_context.build_context_set_from_db`** stages a new
  `context_set["prior_clarifications"]` field — every `clarification` DB row
  for the candidate (cross-application by design; see `Clarification`'s
  docstring) EXCEPT the just-created application's own (which can't own any
  yet at build time, so no origin filter is needed), most-recent-first, capped
  at 40. Corpus-mode only; legacy (file-based) contexts are unaffected.
- **The three Compose CONTENT DRAFTING calls** (`analyzer.draft_positioning_summary`,
  `draft_gap_fill_bullets`, `suggest_skills`) each read
  `context_set["prior_clarifications"]` and render it as a `<prior_clarifications>`
  prompt block, distinct from the existing THIS-application `<clarifications>`
  block. `draft_positioning_summary` and `suggest_skills` treat it as full
  grounding source material (same posture as `<clarifications>`) — a confirmed
  fact from an earlier application is real evidence for this one too.
  `draft_gap_fill_bullets` keeps it CONTEXT-only: a proposed bullet's cited
  evidence must still come from `<career_corpus>`, unchanged.
- **Grounding widened, surgically.** `hardening.assemble_source_union` (the
  deterministic 3-source grounding metric) now also folds in
  `prior_clarifications` answers, so it scores against the same source union
  the Compose prompts are shown — it no longer over-reports legitimately
  cross-JD-sourced content as fabrication. The legacy `generate()` prompt is
  byte-identical; the widened carve-out is scoped to the three drafting calls
  only (AGENTS.md "LLM prompts").
- `PROMPT_VERSION` bumped `2026-07-08.1 → 2026-07-08.2` (the three drafting
  system prompts changed text; the legacy résumé-body `generate()` prompt is
  untouched).
- Real-LLM validated end to end on a throwaway sandbox candidate + temp DB
  (never touched `configs/`/`output/`/`resumes/`): answered a clarification
  under a Platform Engineer JD, then ran an SRE JD for the same candidate —
  the drafted summary wove in the cross-JD fact, `suggest-skills` proposed
  3 new skills evidenced ONLY by the clarification (corpus-evidenced skills
  still cite a bullet id), `draft-gap-fill` correctly proposed ZERO bullets
  from the clarification alone (its evidence-must-be-corpus rule held), and a
  second unrelated candidate saw zero prior_clarifications (candidate-scoped).
  9 real calls, $0.11 total. See `evals/TUNING_LOG.md` for the full record.

### Feat: WYSIWYG as source of truth — in-app edits are the document (`feat/wysiwyg-source-of-truth`, 2026-07-08)

Generation-experience re-architecture item (b) (D4, the LATER-branch remainder
tracked in the carry-forward ledger): closes the "preview != download" window
that existed between typing an edit into `#resumePreview` / `#coverLetterPreview`
and the next unrelated action (refine/iterate) that happened to persist it.

- **`POST /api/applications/<id>/preview-edited` (new route, `blueprints/templates.py`).**
  The preview-side twin of the existing `/api/download-edited`: content in,
  rendered HTML out, NOTHING persisted (no context write, no DB write). Renders
  résumé markdown through the same `md_to_json_resume` → `render_html_string`
  pipeline `save_edits` already uses to recompute its cache, and cover-letter
  markdown through `render_cover_letter_html` — the identical deterministic
  pipelines the cached preview routes use, just applied to live POSTed text
  instead of a stored snapshot.
- **`static/app.js`** wires a debounced (300ms, matching Compose's autosave
  cadence) `input` listener on both editors (`_wireLiveEditPreview` /
  `_refreshLiveEditPreview`) that POSTs the live text to the new route and
  swaps the styled iframe's `srcdoc` — so the visible Step-6 preview never lags
  behind what Download would produce. The existing "Use edits as baseline"
  edit-detection modal and `/api/save-edits` persistence path are UNCHANGED —
  this is a pure display refresh, not a new autosave.
- **Cover-letter preview precedence fix** (`preview_cover_letter_html`): the
  route now prefers a saved `edited_cover_letter_text` over the un-edited
  `last_generated_cover_letter`, mirroring the résumé preview's existing
  `edited_resume_text` precedence (D6(a)). Previously the cover-letter preview
  ignored a saved edit entirely — `/api/save-edits` persisted it but the
  styled iframe kept showing the pre-edit AI text forever.
- **DB durability fix** (`_persist_edited_text_to_db`, `blueprints/generation.py`):
  `save_edits` now mirrors a corpus-backed edit onto
  `ApplicationRun.edited_resume_text` / `edited_cover_letter_text` — columns
  the model already documents as "every generated and edited artifact" and
  `_build_resume_state` / `get_application`'s `has_edits` already READ, but
  that were never written. Without this, an edit survived only in the
  context_*.json sidecar: resuming an application after that file was cleaned
  up silently reverted Step 6 to the un-edited AI text. Best-effort (mirrors
  the sibling `_persist_run_persona`) — a DB hiccup never fails the save.
- Tests: `tests/test_live_preview_route.py::TestPreviewEditedRoute` (renders
  résumé/cover-letter content matching the editor, matches the persisted
  WYSIWYG preview for the same content — the transitive download==preview
  proof, nothing persisted, validation/ownership/404s) +
  `::TestCoverLetterPreview::test_edited_text_wins_over_last_generated` +
  `tests/test_app_iteration.py::TestSaveEditsRoute` (DB row persists, missing
  run row doesn't fail the save, legacy contexts skip the DB write).
- No prompt text changed — `analyzer.py` untouched; `PROMPT_VERSION` stays at
  `2026-07-08.1`.

### Feat: regenerate gap-fill + durable retirals (`feat/regenerate-gap-fill`, 2026-07-08)

Generation-experience re-architecture LATER-branch remainder item (d) (see
[`docs/dev/generation-experience-rearchitecture.md`](docs/dev/generation-experience-rearchitecture.md)
§4/§6 and the RELEASE_CHECKLIST carry-forward ledger). Phase 3
(`fix/compose-frozen-composition`) shipped Compose gap-fill drafting +
accept/retire, but retire was TRANSIENT — a re-draft could resurface a proposal
the user had just rejected, and there was no explicit way to ask for a fresh
draft at all.

- **`composition_overrides.retired_gap_fill_keys`** — a durable set of retired
  proposal keys (the existing `sha256(eid|text)[:12]` stable key), written
  directly by `/gap-fill-decide` (retire) alongside dropping the transient
  proposal. Rides `_collectCompositionState()`'s wholesale rebuild like every
  other override key (`accepted_generated_bullet_ids`, `summary_text`, …), so
  it survives a subsequent `/composition` save instead of being silently
  dropped.
- **"Regenerate suggestions"** — an always-visible control above the per-role
  gap-fill lanes (once experiences exist), calling the SAME `/draft-gap-fill`
  route the auto-fire uses. It's a THIRD context-writing firing path
  (alongside the summary draft + skills recommend) and serializes through the
  same `data-compose-bg-pending` counter.
- **Route-level exclusion filter** (`draft_application_gap_fill`, deterministic
  — no prompt change, no `PROMPT_VERSION` bump): a fresh draft filters out any
  proposal whose stable key is in `retired_gap_fill_keys`, OR matches an
  existing accepted `Bullet.source` (`llm_proposed:<key>`) for this candidate
  — so a Regenerate never resurfaces a proposal the user already decided on,
  either way.
- Tests: `tests/test_regenerate_gap_fill.py` (draft-side exclusion filter +
  decide-side durable write + `/composition` GET/POST round-trip, incl. the
  clobber-invariant regression), `tests/ux/regression/test_20260708_compose_gap_fill_regenerate.py`
  (the button + durability across Regenerate + reload + Save-and-continue),
  plus a `retired_gap_fill_keys` case folded into the existing
  `TestGapFillPromptInvariance` byte-identity guard.

### Fix: surgical single-item refinement + richer loop-back (`fix/surgical-refinement-and-loopback`, 2026-07-08)

Generation-experience re-architecture item (a) (the LATER-branch remainder tracked
in the carry-forward ledger, off `fix/compose-frozen-composition`'s minimal interim
loop-back): a corpus-mode refinement note now drafts ONE scoped, grounded change
instead of just pointing the user back at Compose to redo it themselves.

- **`analyzer.draft_surgical_refinement()` (Sonnet, new `DRAFT_SURGICAL_REFINEMENT_SYSTEM_PROMPT`).**
  Reads the CURRENT frozen `approved_composition` (with numeric bullet/role ids)
  and the free-text note, and proposes exactly ONE of: sharpen an EXISTING bullet
  in place (`supersedes_bullet_id`), a genuinely stronger NEW bullet where the
  corpus is silent, a rewritten positioning summary, or — for a broad "rewrite
  everything" ask with no single scoped target — nothing (`target_kind: "none"`,
  falling back to the plain loop-back). Grounded (no invention beyond
  `<current_resume>`/`<clarifications>`, the same posture as `draft_gap_fill_bullets`).
  `PROMPT_VERSION 2026-07-06.3 → 2026-07-08.1` (a new per-call template; the
  generate prompt is unchanged, so legacy + `--suite synthetic` stay byte-identical).
- **Two new routes** (`blueprints/applications.py`): `POST /api/applications/<id>/draft-refinement`
  (a pure read — stages the note + JD, re-validates any id the model returns against
  the candidate's own corpus, never writes to the context file) and
  `POST /api/applications/<id>/accept-refinement` (applies an accepted proposal:
  a pending Bullet + `accepted_generated_bullet_ids`, and — when the proposal named
  a superseded bullet — that bullet folds into `composition_overrides.excluded` too,
  so the composition gains exactly ONE net item; a summary proposal persists into
  `composition_overrides.summary_text`). Both reuse the EXISTING override keys the
  frozen-composition resolver already honors — zero changes to
  `corpus_to_json_resume.py`. Retire never reaches the server (nothing was written
  for a proposal the user hasn't accepted) — the banner dismisses it client-side.
- **The Compose loop-back banner is richer** (`static/app.js`, `.compose-loopback-*`
  in `static/style.css`): `submitRefinement()`'s corpus-mode path now runs the
  existing fact-scope check (`/api/validate-refinement` + `_showRefinementScopeModal`
  — previously skipped in corpus mode), drafts the scoped proposal, and routes to
  Compose with it stashed. `_renderComposeLoopbackBanner()` renders the ACTUAL
  proposed change (old text struck through when superseding, then the new text,
  plus the model's rationale) with Accept/Retire, falling back to the prior plain
  "adjust it yourself" copy when no proposal came back.
- Tests: `tests/test_draft_surgical_refinement.py` (short-circuit + route
  normalization/ownership-revalidation), `tests/test_accept_refinement.py` (bullet
  accept with/without supersede, idempotency, summary accept, validation),
  `tests/test_demo_mode.py::test_draft_surgical_refinement` (demo mode proposes
  nothing — same grounding-safety posture as `draft_gap_fill_bullets`).
- Real-LLM validation: one scoped refinement drafted against a live sandbox
  application (see `evals/TUNING_LOG.md` "surgical-refinement-and-loopback" entry
  for the transcript + telemetry cost).

### Feat: aesthetic coherence — app-native confirms, wizard-first Tailor, optional gap-fill framing, clearer edit gate, honest dev defaults (`feat/ux-w4-aesthetic`, 2026-07-07)

UX-review Wave 4 (P2, aesthetic/interaction polish — `50-oss-polish-plan.md`):
F-07, F-23, F-13, F-14, F-18.

- **F-07 — every native `confirm()` replaced by the app's own modal.** A new
  reusable `cbConfirm(message, opts)` helper (`static/app.js`) + a generic
  `#cbConfirmModal` skeleton (`templates/index.html`) mirror the existing
  `_showEditModal`/`_showRefinementScopeModal` a11y posture (focus trap, Esc,
  backdrop dismiss, focus restored to the trigger); call sites read
  `if (await cbConfirm(...))`. All 10 sites migrated (corpus summary-variant/
  skill/role-intro/title/bullet/experience retire, role merge, corpus-wide
  accept-all, application retire, persona delete). Destructive actions keep a
  destructive-styled confirm button (new `.cb-bg-danger` variant); the
  non-destructive accept-all keeps its confirm (a KW2 high-stakes guard) but
  drops the danger styling. Dialog-handler-dependent tests updated: the KW2
  accept-all UX test no longer needs a `page.on("dialog", ...)` auto-accept —
  it clicks the in-page modal instead.
- **F-23 — the Tailor tab folds the ambient panels behind the wizard.** User
  selection + Prior applications default to a compact/collapsible summary
  (reusing the existing `.cb-panel` collapse mechanism) once a user is
  selected, so the wizard rail is the primary surface instead of sitting below
  a full account switcher + untruncated applications list. The expand/collapse
  choice persists per panel via `localStorage` (`cb_panel_collapsed:<id>`), so
  a returning visitor's own preference sticks. Every existing id/selector is
  unchanged; `PriorAppsPage.open_detail()` (`ui_pages/prior_apps.py`) expands
  the panel first if it's collapsed.
- **F-13 — the Compose gap-fill lane reads as optional.** A subdued "Optional"
  badge on the lane title + a "Optional — add only what fits" lead-in on the
  hint copy. Presentation only — the gap-fill data flow, `bgDraftFiring`
  serialization, and the Compose settle markers are untouched.
- **F-14 — the edit-detection modal uses plain language.** "You edited the
  preview" → "Your edits aren't saved yet"; the body now names each choice's
  effect directly instead of the denser "ground truth" phrasing. Same ids,
  same three choices, same timing (`_gateEditsBeforeAction` already fires it
  at the moment the user acts on a stale preview, not on a delay) — the
  typed-edits-feed-grounding function is untouched.
- **F-18 — honest dev defaults.** `python app.py` still auto-opens a browser
  and runs Flask's debug reloader by default for a local desktop run. A new
  `app._is_ci_or_container()` (checks the `CI` env var and `/.dockerenv`) now
  fills in the off default (no browser open, `FLASK_DEBUG=0`) when NEITHER
  `SARTOR_NO_BROWSER` nor `FLASK_DEBUG` is set explicitly, so a bare
  `python app.py` in a CI job or an ad-hoc devcontainer/Codespace no longer
  surprises with a hung browser-open or a debug traceback. An explicit env var
  always wins over the auto-detection; the shipped `Dockerfile` already sets
  both explicitly, so this only covers runs outside that image.
  `_should_open_browser`'s existing tested 2-arg contract is unchanged — the
  detection only changes what `main()` passes in. Documented in
  `docs/install.md` ("Local development: headless / container / CI runs") and
  the README install section.

No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched.

### Feat: honest Generate surface — deterministic-assembly copy + reliable server-side download (`feat/ux-w1-generate-surface`, 2026-07-07)

UX-review Wave 1 items F-09 + F-10 (`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`).

- **F-09 — the deterministic Generate is finally said out loud.** On the primary
  corpus-mode path the final Generate is a deterministic assemble of the frozen
  `approved_composition` (`blueprints/generation.py:_frozen_composition` — LLM cost
  front-loaded into Analyze/Compose), but Step 5's copy still read as "another AI
  step". Step 5 now carries a state-aware copy pair (`#generateStepCopyFrozen` /
  `#generateStepCopyLegacy` in `templates/index.html`, toggled by
  `_renderGenerateStepCopy()` on every entry to the step): after Compose's
  Save-and-continue freeze actually lands (`_compositionFrozen` in `static/app.js`,
  set from the freeze POST's success and reset on fresh analysis / new-tailoring /
  prior-app resume — mirroring the server gate's own predicate), the step says
  "Assembled instantly from your approved composition — same input, same résumé,
  no AI variation"; the legacy/fallback LLM path keeps the original ~30–60s framing
  and NEVER gets the determinism claim. The `_HELP_REGISTRY.panelGenerate` (i) entry
  carries the longer both-paths explanation. No prompt or backend behavior change;
  no `PROMPT_VERSION` bump.
- **F-10 — the download can no longer silently fail.** `downloadResume()` /
  `downloadCoverLetter()` used to pull the bytes into a blob and click a synthetic
  `<a>` — the pattern Chrome's multiple-automatic-downloads heuristic could silently
  block on a second download without a fresh gesture, which the Step-6 panel
  *documented in-app* as a known caveat. `POST /api/download-edited` now returns
  JSON `{download_url, filename}` pointing at the existing containment-gated
  `GET /api/download/<path>` (`send_file(as_attachment=True)`), and the client
  follows it as a plain navigation the browser's download manager owns. The
  `download_url` is OUTPUT_DIR-relative (an absolute POSIX path would double-slash
  the URL; Windows paths carry a drive colon); `download_file` re-anchors a relative
  path under OUTPUT_DIR *before* its unchanged `_within` containment gate (traversal
  still 403s — new `TestDownloadFileContainment` cases pin it). Failures surface in
  the shared error modal (`reportError`) — never a silent no-op — and the retired
  Chrome caveat copy is REMOVED from `templates/index.html`. The 2026-05-26
  round-6 diagnostic `console.log`s in the download path retire with the bug they
  were instrumenting.
- **Tests.** `tests/ux/regression/test_20260707_generate_surface_download.py` — the
  deterministic copy shows on the frozen path and is absent on the legacy path (both
  driven through the stubbed wizard), the download is a server-served attachment
  (`download.url` is `/api/download/…`, not a `blob:`), and a forced failure opens
  the error modal. `tests/test_persona_routes.py` — download-edited's new JSON
  contract + the four `download_file` containment cases (relative serve, relative
  traversal 403, legacy absolute serve, absolute escape 403).

### Feat: recruiter tier — candidate roster, cross-candidate pipeline, house templates (`feat/ux-w2-recruiter`, 2026-07-07)

UX-review Wave 2 (`docs/dev/reviews/2026-07-ux-review/50-oss-polish-plan.md`) —
F-08 / F-17 / F-16. The multi-candidate data model already supported all of
this; this branch is presentation only, layered on the existing per-user
model without breaking any existing route contract.

- **F-08 — candidate roster.** The flat username `<select>` (`#userSelect`)
  is still the mechanism every flow keys off of, but it now has a searchable
  roster surface above it (`#candidateRoster`): each candidate's display
  name, latest target role/company, and a per-status application-count
  summary. Clicking a card just sets the `<select>` and fires the same
  `onUserSelect()` every other selection path uses — `currentUser` semantics
  are unchanged. Hidden for single-candidate installs (shows once 2+
  candidates exist) so the job-seeker experience is undisturbed.
- **F-17 — cross-candidate pipeline board.** A new read-only **Pipeline**
  top-level tab: every candidate's applications grouped into the five
  canonical lifecycle-status columns (draft / submitted / interview /
  rejected / withdrawn). Clicking a row switches the selected candidate and
  hands off to the Tailor tab on that application.
- **F-16 — house templates.** Personas stay per-candidate (no account-level
  scope, no schema change) — the smallest honest fix is a one-click
  **COPY TO CANDIDATE** action on an owned persona card
  (`POST /api/personas/<id>/copy`) that copies the `.docx` + regenerates its
  HTML/CSS preview companion into the target candidate's own template list,
  instead of re-uploading by hand for every candidate.
- **New aggregate endpoint** — `GET /api/candidates/roster`
  (`blueprints/users.py:candidate_roster`) backs both F-08 and F-17 in ONE
  response: exactly two DB queries regardless of candidate/application count
  (one `Candidate` `IN`-query, one `Application` `IN`-query), guarded by a
  constant-query-count regression test
  (`tests/test_users_routes.py::TestCandidateRoster::test_avoids_n_plus_1_query_growth`),
  mirroring the `list_applications` selectinload + grouped-count discipline.
- `copy_persona_to_candidate` carries the full `_safe_username` +
  `secure_filename` + `_within` guard sequence (containment + traversal
  tests in `tests/test_persona_routes.py::TestCopyPersonaToCandidate`); the
  committed route-containment gate (`tests/test_route_containment_gate.py`)
  stays green.

### Feat: one home per section — corpus skills/education/certifications editors + honest Settings fields (`feat/ux-w1-skills-education`, 2026-07-07)

UX-review Wave 1, F-03 + F-04 (`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`).
Both findings were SHARPENED during the review's verification pass, and the
F-02 skills-import fix that just merged to `main` changed the F-03 landscape
further (résumé import now also feeds the corpus Skill rows), so this branch
re-verified both against current code before designing a fix.

- **F-03 — one home for Skills.** The Settings drawer's flat Skills field
  is a ONE-TIME seed into the corpus (`onboarding/corpus_import.py`), not a
  permanent "legacy mode": `blueprints/analysis.py` confirms Phase C.4 already
  removed the file-based analyze/generate path for every user — everyone is
  corpus-backed once `_get_or_provision_candidate` has run once (on the first
  Analyze, or any Career-corpus write). So the real per-candidate state is
  pre-provision (flat field is still the only source of truth — nothing to
  point at yet) vs. post-provision (corpus Skill rows are authoritative, and
  the flat field silently does nothing). `GET /api/users/<u>/config` now
  returns `needs_onboarding` (does a Candidate DB row exist yet — the same
  flag `/api/users/<u>/experiences` etc. already expose) so the frontend can
  tell the two states apart. Chose the smallest honest fix: pre-provision, the
  live input renders unchanged; post-provision, it's replaced by a labeled
  "Managed in your Career corpus now… Go to Career corpus →" pointer that
  switches to the Corpus tab. No live mirror (extra fetch, staleness risk for
  no real benefit over a link) and no automatic data migration between the two
  homes — only the existing one-time config-seed import.
- **F-04 — a real corpus editor for Education + Certifications.** The
  `Education`/`Certification` DB tables already existed and were already
  consumed (`db/build_context.py` reads both, ordered by `display_order`, into
  the synthesized corpus-mode résumé the analyze/generate prompts see) — the
  gap was UI-only. Added 8 routes (`blueprints/corpus/career_assets.py`, list/
  create/update/delete × 2 entities, candidate-scoped via `_safe_username`,
  DB-only so no filesystem containment applies) and a matching Career-corpus
  editor section for each, reusing the Skills editor's row chrome
  (`.summary-variant-row` / `.corpus-action-btn`) rather than inventing a new
  component family. Neither entity gets a pending-review/LLM-proposal
  lifecycle (the DB models carry no `source`/`is_pending_review` column — a
  human types these directly). Delete always soft-retires (`is_active=0`,
  already on both models) — never hard-deleted, matching the project's
  "nothing hard-deleted" promise. Reorder: since neither the Skills nor
  Summary-variant editors have visible reorder controls to copy, added a small
  swap-with-neighbor ↑/↓ affordance (`.reorder-controls`/`.reorder-btn`,
  reused from the Compose bullet-list's keyboard-reorder styling) that PUTs
  both affected rows' `display_order` immediately. The Settings drawer's flat
  Certifications/Education fields get the exact same F-03 pointer treatment.
- No data migration: the flat config fields and the corpus rows stay two
  independent homes, reconciled only by the existing one-time import — never
  synced automatically, per the review's explicit scope.

### Feat: first-run flow — calm Analyze + guided landing + display-name-first + application company capture (`feat/ux-w1-first-run-flow`, 2026-07-07)

UX-review Wave 1 "first-run delight" slice — F-12 / F-06 / F-05 / F-15 from
`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`.

- **F-12 — the Analyze screen leads calm.** `_renderAnalysis` (static/app.js) now
  opens with the F-01 coverage block (heading, score bar, `.score-note` explainer —
  preserved verbatim), then a **"Where to Focus"** verdict line + up to three actions
  derived **deterministically from the payload** (top missing keywords + top
  comparison gaps, backfilled from the analyzer's own suggestions — no new LLM call,
  no prompt change, no `PROMPT_VERSION` bump). Everything else (skill chip clouds,
  hidden qualities, matched/could-add keyword lists incl. the verbatim "Keywords You
  Could Add" heading, comparison, suggestions, placement, strategy) folds into a
  native `<details id="analysisDetails">` "Show full analysis" disclosure, collapsed
  by default. ATS warnings (legacy path only) stay above the fold.
- **F-06 — the post-create tab jump is explained.** Smart-landing an empty-corpus
  user onto Career corpus now fires a one-time `tourCorpusLanding` help modal
  ("Let's build your corpus first") via the existing `_HELP_REGISTRY` +
  `cb_help_seen:` primitive — no new modal machinery; suppressed by default in the
  UX suite like every other auto-firing stop (`_TOUR_STOP_BLOCKS`).
- **F-05 — display-name-first new-user form.** Full name is the first field and gets
  focus; typing it live-derives a username slug (lowercased, hyphenated, diacritics
  stripped — `_slugify`) into the still-visible, still-editable username field with a
  "this is your storage key" hint. A manual username edit stops the auto-derive for
  that form session. Username remains the storage key; `POST /api/users` payload and
  validation (`secure_filename`, required markers) are unchanged.
- **F-15 — applications capture company at creation.** `build_context_set_from_db`
  (db/build_context.py) stamps `Application.company` via the new
  `_infer_application_company` — `hardening.extract_company_terms(jd_text)` (the
  deterministic, fail-open F-01 detector), longest term wins deterministically,
  title-cased for display; `None` on a miss (prior behavior). The applications card,
  detail modal, and editable save path (#24 `PUT /api/applications/<id>/meta`)
  already surfaced company — no migration needed either: `Application.company` has
  existed since migration 0001.
- Tests: `tests/ux/regression/test_20260707_first_run_flow.py` (progressive
  disclosure collapsed/expandable + F-01 preservation; one-time transition modal via
  the name-first create path; slug derivation/manual-edit-wins/re-arm; application
  card shows the captured company) + `TestInferApplicationCompany` and two
  capture-wiring cases in `tests/test_build_context_db.py`.

### Feat: demo mode — run without an API key (`feat/ux-w3-demo-mode`, 2026-07-07)

UX review F-19 (`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`): a
technical evaluator had no way to see the product without a billed Anthropic key.

- **Activation.** `SARTOR_DEMO=1` (env) is the single source of truth
  (`demo_fixtures.is_demo_mode()`); `config.Config.demo_mode` reads it as a
  `field(default_factory=...)` so `create_app()` surfaces it to Flask config
  (`DEMO_MODE`, for the banner) with no extra wiring, while `analyzer.py` checks
  the same env var directly so it keeps working outside a Flask request context
  (evals, onboarding scripts, tests). Demo mode never activates implicitly — a
  missing/blank key alone is unchanged (still fails at the first live API call,
  same as always); a real key present alongside the flag still means demo (checked
  before any key lookup, so a demo run can never accidentally spend).
- **Mechanism.** `web_infra.clients._get_client()` returns a `_DemoClient`
  sentinel instead of constructing `anthropic.Anthropic` when the flag is set —
  no key read, no client built. Every one of `analyzer.py`'s 18 public LLM call
  kinds (`analyze`, `analyze_streaming`, `avatar_answer_streaming`, `clarify`,
  `clarify_iteration`, `generate`, `generate_streaming`,
  `generate_cover_letter_against_resume`, `check_refinement_scope`,
  `critique_proposal`, `recommend_bullets`, `recommend_summaries`,
  `recommend_experience_summaries`, `recommend_skills`, `suggest_skills`,
  `promote_clarification_to_bullet`, `draft_positioning_summary`,
  `draft_gap_fill_bullets`) independently short-circuits to a canned response
  before it would ever touch the client, so the sentinel is never dereferenced.
  New product-side module `demo_fixtures.py` (LLM-free, like `hardening.py`)
  holds the canned payloads: the analysis/clarify/résumé/cover-letter story is
  adapted from `evals/fixtures/synthetic/sre-mid-level/` (a coherent JD +
  candidate + analysis, not disconnected scraps); the `recommend_*` family
  selects deterministically from whatever the caller staged on `context_set`
  (never fixture-fixed ids that wouldn't exist in a real corpus); calls needing
  genuine grounded judgment (`suggest_skills`, `draft_gap_fill_bullets`,
  `critique_proposal`, `promote_clarification_to_bullet`,
  `draft_positioning_summary`) return conservative, clearly-labeled no-ops
  rather than fabricated content.
- **Honesty.** A persistent, always-visible banner ("Demo mode — canned AI
  responses, no API calls") renders at the very top of every page while
  `DEMO_MODE` is set (`templates/index.html`, `.demo-mode-banner` in
  `static/style.css`) — never a dismissible toast. Telemetry is suppressed by
  construction, not filtered after the fact: every demo call kind returns
  before it would ever call `analyzer._call_llm`/`_call_llm_streaming`, so
  `logs/llm_calls.jsonl` and the `/_dashboard` cost/latency/reliability stats
  never see a demo row.
- Zero new dependencies; no `PROMPT_VERSION` change (no prompt touched); the
  deterministic modules stay LLM-free.
- Docs: README quickstart + `docs/install.md` gain a "Try it without an API
  key" section.

### Docs: contributor-facing truth pass — reader paths, model routing, eval costs, README polish, dashboard label (`docs/ux-w3-contributor`, 2026-07-07)

UX-review Wave 3 (contributor on-ramp): F-21, F-22, F-20, F-27, F-06d. Doc/copy-level
only — no code-behavior change.

- **F-21 — un-conflate using/developing/extending.** Added a "Three ways to meet
  Sartor" section to `README.md` (front matter, before "What Sartor does") with three
  explicitly labeled reader paths — Use it / Develop on it / Extend it — each pointing
  into the existing doc set; the "Extend it" path scopes the tuning slash commands
  (`/prompt-tune`, `/tune-from-annotations`, …) as Claude-Code-specific (they need the
  `sartor` plugin), distinct from the plugin-independent eval harness CLI.
- **F-22 — model-routing drift (Sonnet 4.6 → Sonnet 5).** Verified current routing
  against `analyzer.py:SONNET_MODEL`/`HAIKU_MODEL` and corrected drifted prose in:
  `AGENTS.md`, `docs/architecture.md` (prose only — the four fenced/linked diagrams
  are known-drifted, scheduled for full replacement in the v1.0.9 docs epic; added a
  one-line staleness note instead of reworking them), `README.md` (also fixed a
  pre-existing tier bug — `clarify()` was listed under "Sonnet"; it runs on Haiku
  4.5), `vision.md`, `docs/PRODUCT_SHAPE.md` (same `clarify()` tier fix),
  `docs/walkthrough.md`, `docs/walkthrough_example.md`, `evals/README.md`,
  `templates/index.html`, `scripts/capture_screenshots.py`, `blueprints/analysis.py`,
  `blueprints/generation.py`, `docs/dev/RELEASE_CHECKLIST.md` (risk-register item).
  Historical/dated artifacts (CHANGELOG entries, `evals/TUNING_LOG.md`,
  `docs/dev/perf/*`, `docs/dev/reviews/**`, `evals/results/baseline_v1.json`,
  `hardening.py`'s intentionally-retained `claude-sonnet-4-6` pricing entry) were
  left untouched — they're point-in-time records, not current-state claims.
- **F-20 — stale eval smoke cost.** The documented "~$0.10" smoke estimate was
  ~3.7× stale post-Sonnet-5 (measured ~$0.37 total / ~$0.12 per fixture in the
  2026-07-07 UX review). Restated as "~$0.35–0.40 under Sonnet 5" in `AGENTS.md`,
  `README.md`, `evals/README.md` (Quick start + Cost considerations table + the
  Tuning-tab 2×-cost gate estimate), the dashboard Quality-tab copy
  (`dashboard/templates/dashboard.html`: help text, `updateCost()`, the `confirm()`
  estimate string), and `blueprints/diagnostics.py`'s route docstring.
- **F-27 — README polish bundle.** Added a `git` prerequisite line to Install; moved
  the `## Install` section up (right after "How it works", before the audience
  sections) for prominence; expanded "ATS" on first use in "What Sartor does";
  softened `docs/architecture.md`'s "read in 5 minutes" claim (no such claim existed
  in the current README — the closest survivor was this one); added a brief
  "formerly Callback" note under the title.
- **F-06d — dashboard "RELIABILITY 0%" tile.** Relabeled the Pipeline-tab tile from
  "reliability" to "error rate" (`dashboard/templates/dashboard.html`) — the tile
  always rendered `error_rate * 100`, so the old label read as catastrophic at a
  glance. No metric/computation change. Updated the tile's `data-title` and the
  `_DASH_HELP.dashPipeline` body text to match.

No test asserted the old copy in any touched file (verified via grep), so no test
changes were needed.

### Fix: installable wheel + python floor + install-doc truth (`fix/packaging-install`, 2026-07-07)

Carry-forward ledger "PyPI wheel not installable" + UX-review Wave 0 F-24/25/26 +
2026-07-efficiency-review PX-42, bundled together per the ledger's own note
("F-24/25/26 ... overlaps the PyPI-wheel item below — fix together").

- **The wheel is now installable.** `create_app()`'s `Flask(__name__)` used to resolve
  `templates/`/`static/` relative to `app.py`'s own directory — correct only when they
  happened to be co-located on disk (a source checkout or `pip install -e .`), and there
  was no `package-data`/`MANIFEST.in`, so a real (non-editable) `pip install sartor` 500'd
  on the first page load. Fixed with the smallest change that makes a real wheel serve,
  not a `sartor/` package restructure:
  - `templates/`, `static/`, `personas/bundled/`, and `docs/wiki/` each got a marker
    `__init__.py` (see each file's own docstring) turning them into tiny data-only Python
    packages, shipped via new `[tool.setuptools.package-data]` globs — narrow and
    explicit (never `**/*`), so `personas/robert/` (a real gitignored per-user upload dir
    sitting right next to `personas/bundled/`) can never leak into a build.
  - `config.py` gains `_package_dir()` (import-based resolution — correct in both
    editable and wheel installs) and exports `TEMPLATES_DIR`/`STATIC_DIR`; `app.py`
    passes them explicitly to `Flask(__name__, template_folder=..., static_folder=...)`
    instead of relying on the implicit default. `blueprints/assistant.py`'s `_WIKI_DIR`
    (the doc-grounded assistant's S1 tier) gets the same `_package_dir`-style treatment,
    locally (matching the file's existing "re-derived locally, never imports app.py"
    precedent). `Config.bundled_personas_dir` is DELIBERATELY left untouched
    (`base_dir`-relative, as before) — many existing tests fabricate an isolated
    fake-bundled fixture under `Config(base_dir=tmp_path)`, and routing it through
    `_package_dir` instead redirected those test writes onto the real, tracked
    `personas/bundled/` files (caught by the fast test lane before landing). No code
    change was needed there anyway: the default `base_dir` is `_PROJECT_ROOT`
    (`config.py`'s own directory), which in an installed wheel IS `site-packages/`, and
    `personas.bundled`'s new package-data ships to `site-packages/personas/bundled/` —
    exactly where the existing `base_dir`-relative arithmetic already looks. The
    dev/editable path for `templates`/`static`/`docs.wiki` is byte-identical (same
    directories, resolved via import instead of `Path(__file__)` arithmetic).
  - Verified end-to-end: `python -m build` → fresh venv → `pip install <wheel>` → app
    started from a directory OUTSIDE the repo with a temp base dir → a real HTTP
    `GET /` returns 200 with the shell HTML (and `/static/style.css` serves), proving both
    halves (path resolution + packaging) together, not just in isolation. The `GATE` step
    in `.github/workflows/release.yml` (added specifically to block publishing until this
    landed) is removed. Publishing itself stays `[HUMAN]`-blocked on an unrelated
    prerequisite (PyPI Trusted Publisher + GHCR, gated on the GitHub repo rename) — see
    `docs/dev/RELEASE_CHECKLIST.md`.
  - New regression test `tests/test_packaging.py` pins the code-level contract (absolute,
    existing Flask folders; the four packages resolve; `py-modules` matches the repo's
    actual root `.py` files; the `requires-python` floor) so a future edit can't silently
    re-break the wheel between the (necessarily manual/scripted) fresh-venv verifies.
- **PX-42 — the python floor tells the truth.** `requires-python` was `>=3.10`, but CI
  (`ci.yml`) only ever tested 3.11–3.13, and `tests/test_docstring_coverage_gate.py` (dev
  tooling) already used `tomllib` (3.11+ stdlib) — a real 3.10 install was untested and
  would fail at *runtime*, not at `pip install` time. Raised to `requires-python = ">=3.11"`
  and dropped the `Python :: 3.10` classifier; `docs/install.md` "Python 3.10 or newer"
  corrected to 3.11.
- **F-26 — `py-modules` omission fixed.** `[tool.setuptools] py-modules` listed 7 of the
  repo's 11 root-level `.py` modules; `corpus_to_json_resume`, `docx_to_persona_html`,
  `json_resume`, and `pdf_render` were missing (all four are imported at runtime) and would
  have been absent from an installed wheel. Now lists all 11; `tests/test_packaging.py`
  pins the roster against a live glob of the repo root so this can't silently drift again.
- **F-24 — `docs/install.md` "Verifying the install" needs `[dev]`.** The verify steps ran
  `pytest`/`ruff`, but the install steps only ever ran `pip install -e .` — neither tool is
  a runtime dependency, so a clean install failed the very verification steps meant to
  confirm it. Added `pip install -e '.[dev]'` as the first step of "Verifying the install".
- **F-25 — `sartor --setup` added to every OS walkthrough.** The per-OS Windows/macOS/Linux
  steps only ever documented the raw `python -m playwright install chromium` call, never the
  documented one-time bootstrap (`sartor --setup`, which does that AND builds the assistant's
  semantic-recall index) — a reader following an OS section got PDF export working but the
  recall index unbuilt (silent lexical/wiki-tier fallback). Each OS section's Chromium step
  now runs `sartor --setup` instead, documented as covering both.

### Fix: eval harness scores the shipped frozen-assembly path (`fix/eval-f11-frozen-assembly`, 2026-07-07)

UX-review Wave 0, F-11 ([`40-friction-register.md`](docs/dev/reviews/2026-07-ux-review/40-friction-register.md)) —
on the UI happy path corpus-mode `/api/generate` assembles the résumé body **deterministically**
from the frozen `approved_composition` (`blueprints/generation.py`'s `_frozen_composition` gate,
zero résumé-body LLM calls), but `evals/runner.py` always ran `analyze → clarify → generate`,
where `generate()` is a real ~27s Sonnet call — the harness was scoring the fallback/legacy path,
not the assembled document users actually download.

- **New `evals/runner.py --mode {generate,assemble}` flag** (default `generate`, byte-identical to
  before). `assemble` REQUIRES `--seed` (frozen-composition assembly needs a real corpus) and
  drives the SAME Compose → freeze → assemble path the product uses instead of calling
  `analyzer.generate()`: `analyzer.recommend_bullets` / `recommend_summaries` (Haiku — the exact
  functions the `/recommend` + `/recommend-summary` routes call) populate
  `llm_recommendations` / `llm_summary_recommendation` on the context, then
  `corpus_to_json_resume.freeze_approved_composition` (the exact function Compose's
  Save-and-continue calls) resolves + freezes the composition, and
  `blueprints.generation._assemble_from_frozen_composition` (the exact function `/api/generate`
  calls once frozen) assembles it — zero résumé-body LLM calls. The cover letter stays a real
  Sonnet call (`generate_cover_letter_against_resume`) for tone-rubric parity with the legacy
  path's own default. Skill curation is left at its documented product default (no
  `recommend-skills` call → all active, approved skills), not an eval shortcut.
- **`eval_mode` rides every JSONL record** (`"generate"` or `"assemble"`), mirroring how
  `prompt_version` / `suite` attribute records — so the dashboard/baseline tooling can tell the
  two content-generation populations apart.
- **Baseline-gating scoped away from the new mode** — `assemble`-mode scores are never compared
  against `baseline_v1.json` (measured on the `generate`-mode population): `baseline_comparison`
  is always `null` and assemble-mode scores never feed the regression-gate `exit_code` (a
  sub-threshold score still counts via `n_fail`). No `PROMPT_VERSION` bump — no prompt changed.
- Unblocks the "Eval baseline stale vs production model (Sonnet 5)" carry-forward ledger row
  (`docs/dev/RELEASE_CHECKLIST.md`), scheduled to run after this landed.
- Tests: `tests/test_eval_runner.py::TestAssembleMode` — proves the graded résumé text is
  byte-identical to an independently re-derived `freeze_approved_composition(...) →
  json_resume_to_markdown(...)` call (not an LLM-authored stand-in), `analyzer.generate()` is
  never invoked in `assemble` mode (patched to raise), every record carries `eval_mode`, and the
  default `generate` mode never touches `recommend_bullets`/`recommend_summaries`/
  `freeze_approved_composition` (patched to raise) — proving the legacy path is unchanged.

### Fix: résumé import creates pending skills (`fix/ux-f02-import-skill-rows`, 2026-07-07)

UX-review Wave 0, F-02 ([`40-friction-register.md`](docs/dev/reviews/2026-07-ux-review/40-friction-register.md)) —
résumé import created Experiences, ExperienceTitles, Bullets, and role-intro summary variants,
but never Skill rows: a freshly imported candidate had an empty Skills section, the Compose
skills card never appeared, and skills silently dropped out of every tailored output.

- **One Haiku call, two outputs** (`onboarding/extract_experiences.py`) — the résumé-extraction
  system prompt now also asks for a flat `"skills"` array (verbatim names from an explicit
  Skills/Technologies section only; no invention, no pulling terms out of bullet prose). New
  `extract_experiences_and_skills()` returns `(experiences, skill_names)` from that single call;
  `extract_experiences()` becomes a thin backward-compatible wrapper over it, so every existing
  caller/test keeps working unchanged. No second API round trip, no cost increase.
- **`onboarding/corpus_import._insert_pending_skills`** — inserts the extracted names as
  `is_pending_review=1, is_active=1, source="imported"` Skill rows (`source` is DB-CHECK-limited
  to `manual|imported|llm_proposed` — `ck_skill_source` — so it reuses the same value the
  config-seeded importer and the legacy-row backfill already use). Deduped case-insensitively
  against **every** existing Skill row for the candidate (active, retired, or already pending),
  both within one extraction batch and across re-imports/re-uploads, so re-running an import is
  always safe. Wired into `ingest_one_resume`, so both the CLI importer (`--with-llm`) and the
  live `POST /api/users/<u>/corpus/ingest-resume` route pick it up with no route changes.
- Reuses the existing review surface end to end — no new UI. The Career Corpus tab's
  "AI-suggested skills" lane and the existing approve/deny routes (`blueprints/corpus/skills.py`)
  already list any `is_pending_review=1` Skill row regardless of source, and `refreshCorpus()`
  already re-fetches skills after an ingest. `static/app.js`'s post-upload status line and the
  route's JSON payload now also report `skills_created` alongside the existing experience/bullet
  counts.
- No `PROMPT_VERSION` bump — the changed prompt lives in `onboarding/extract_experiences.py`,
  which the project does not version-stamp (unlike `analyzer.py`'s persona prompts).
- Tests: pending-skill creation with the `imported` source, case-insensitive dedup against
  pre-existing rows and within one extraction batch, re-import idempotence, dry-run counting,
  and an end-to-end check that an approved skill flows through to
  `corpus_to_json_resume._collect_skills` (the deterministic JSON-Resume/frozen-composition
  skills source) while still-pending ones do not.

### Fix: keyword score no longer graded on the company name + JD boilerplate (`fix/ux-review-wave0-keyword-score`, 2026-07-07)

UX-review Wave 0, F-01 ([`40-friction-register.md`](docs/dev/reviews/2026-07-ux-review/40-friction-register.md)) —
the highest-leverage P0: a strong SRE-to-SRE match scored **18%** because the hiring company's
own name ("lattice cloud") and hiring boilerplate ("hiring", "serving") counted as keywords
missing from the résumé. Deterministic fix (`hardening.py` — charter C-6, no LLM, no
`PROMPT_VERSION` bump, no new dependency):

- **`JD_BOILERPLATE_WORDS`** — hiring-administrivia (process / qualifier / package /
  arrangement words) is dropped from the JD keyword universe inside `compute_keyword_overlap`:
  matching "hiring" is not signal, missing it is not a deficit.
- **`extract_company_terms(jd_text)`** — conservative deterministic company detection
  (header-zone "X — location" lines + "About X" / "at X" / "X is|runs|builds…" patterns);
  job-title vocabulary disqualifies a candidate term, so duty-bullet proper nouns
  (Kubernetes, Prometheus) are never captured; fail-open on any miss.
- **Forgive-absence scoring** — a company term absent from the résumé leaves both the missing
  list and the denominator; when present it still counts as matched (a Databricks engineer
  applying to Databricks keeps the credit). New `excluded_terms` key reports what was cleaned
  (also added to `evals/schemas/context_set.schema.json`).
- Company terms are passed at the two overlap call sites — `db/build_context.py` (corpus mode)
  and `evals/runner.py` (the eval harness stays on the live code path). Compose bullet ordering
  and corpus-snapshot selection intentionally keep the raw JD keywords (`extract_keywords`
  unchanged).
- **Analyze-screen reframe** (`static/app.js`): "Keyword Match Score" → "JD Keyword Coverage"
  plus a one-line explainer; "Keywords Missing From Resume" → "Keywords You Could Add".
- Tests: company-term detection, cleaning semantics, and a fixture regression asserting the
  SRE fixture's company/boilerplate never appear in the missing list and the cleaned score
  strictly exceeds the raw-overlap before-state.

### Fix: deterministic Compose settle gate — stop the flaky-UX class (`fix/compose-settle-bg-reload`, 2026-07-06)

A reduction-sprint knock-down of the carry-forward "recurring flaky Compose-UX" ledger item.
**Test-observability only** — no product behavior change, no prompt bytes, no `PROMPT_VERSION` bump.

- **Root cause** — the Compose (Step 3) auto-recommend/draft cascade fires background POSTs that
  each re-run `loadComposition()` on success; the `data-compose-ready` settle marker is re-set at
  the END of each synchronous render, but a background reload (the Phase-3 deferred
  `/draft-gap-fill` most visibly) lands *later*, so the POM's `_wait_settled` — a one-shot
  `networkidle` + a hand-rolled 3×50 ms marker-stability poll — could settle on a non-terminal
  render and race the re-render (the positioning-pin clobber).
- **Fix (settle-marker, not serialize)** — a `data-compose-bg-pending` counter attribute on
  `#composeList` ([`static/app.js`](static/app.js)), incremented as the first synchronous statement
  of every `loadComposition()`-on-success reload site (the 5 auto-cascade `_fire*` **and** the 6
  user-action pin/suggest/review/accept/add reloads) so it is present before the marker is re-set,
  and decremented in a `finally` so a failed POST still balances (no stuck attribute → no hang).
- **Deterministic gate** — `_wait_settled` ([`ui_pages/wizard_compose.py`](ui_pages/wizard_compose.py))
  now waits on `#composeList[data-compose-ready]:not([data-compose-bg-pending])`
  ([`Compose.SETTLED`](ui_pages/selectors.py)) — the only state that is the true terminal render
  with no reload queued — replacing the stability poll with a single `wait_for_selector`.
- **Regression test** — `tests/ux/regression/test_20260706_compose_settle_bg_reload.py` slow-stubs
  the gap-fill draft so its reload is reliably in flight, then asserts the counter fires and the
  settle blocks until it drains. The two previously-flaky members + the gap-fill tests passed
  **18/18** across 3 stability re-runs; full `pytest -m ux` (77) and the whole suite (1535) green.

### Chore: pin ruff + add a whole-tree `ruff format --check` CI gate (`chore/ruff-format-pin`, 2026-07-06)

A reduction-sprint knock-down of the carry-forward "ruff-format-drift" ledger item.
**Formatting-only and prompt-safe** — no logic, no prompt bytes, no `PROMPT_VERSION` bump.

- **One-time `ruff format .` sweep** — 5 files that predated the current formatter re-formatted
  under ruff 0.15.12 though no branch touched them (`docx_to_persona_html.py` + four `tests/`
  files): f-string inner-quote normalization, single-line collapsing, string-concat re-wrapping.
  None is `analyzer.py`, so no prompt changed.
- **Ruff exact-pinned** — [`pyproject.toml`](pyproject.toml) dev extra: `ruff>=0.6,<1.0` →
  `ruff==0.15.12`. Ruff does not guarantee formatter-output stability even across patch releases,
  so a floating range let the drift accumulate; the exact pin makes local + CI format identically.
- **New CI format gate** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml) `quality` job now
  runs `ruff format --check .`, which CI previously never did (it only ran `ruff check`, and the
  commit hook only checks *staged* files). Pin + gate are one inseparable fix: a gate without the
  pin would flake CI on unrelated PRs the day a new ruff releases. Bumping ruff is now a deliberate
  one-commit action (upgrade + `ruff format .` + re-pin).

### Feature: Compose authors + freezes the composition; Generate becomes deterministic (`fix/compose-frozen-composition`, 2026-07-06)

The generation-experience re-architecture (Option B — one cohesive branch). North
star: **NO SURPRISES** — content is authored + approved ONCE at Compose, frozen, then
rendered deterministically by every downstream surface. What you see is what you
download. `PROMPT_VERSION 2026-07-06.1 → 2026-07-06.3`. Full design + decision record:
[`docs/dev/generation-experience-rearchitecture.md`](docs/dev/generation-experience-rearchitecture.md).

- **Frozen `approved_composition` contract (Phase 1)** — `corpus_to_json_resume` is the
  sole producer of a resolved JSON-Resume snapshot (honors `bullet_order`, folds
  `accepted_generated_bullet_ids`, resolves `summary_text`, emits `meta.sartor`
  provenance); `freeze_approved_composition()` stamps it on Compose "Save and continue".
- **Compose authors the 2-sentence positioning summary (Phase 2)** — a dedicated Sonnet
  `draft_positioning_summary` (grounded, editable, retire-able) fires once on Compose
  arrival, replacing the summary the résumé LLM used to write.
- **Compose authors gap-fill bullets (Phase 3)** — a Sonnet `draft_gap_fill_bullets`
  proposes GROUNDED bullets for JD requirements the corpus doesn't cover, shown as a
  per-role "Suggested for this JD" accept/retire lane; ACCEPT creates a pending `Bullet`
  folded into this application's composition, RETIRE drops it. A resolver **pending-leak
  guard** keeps a pending+active bullet from rendering in other applications (mirrors the
  skills guard); this also stops any pre-existing pending+active bullet (e.g. a
  promoted-clarification bullet) from leaking into every all-active render.
- **Generate becomes deterministic (Phase 4)** — in corpus mode, `/api/generate`
  (+ streaming) ASSEMBLE the frozen `approved_composition` (ZERO résumé-body LLM calls)
  instead of calling `generate()`; the résumé renders directly from the doc, so
  **preview == assemble == download** by construction. The **cover letter stays an LLM
  call**; **legacy (file-based) mode is byte-identical**, so `--suite synthetic` is
  unchanged. A corpus-mode Refine now routes BACK to Compose (minimal loop-back) with an
  explaining banner instead of an LLM full-regenerate. New deterministic helpers:
  `json_resume.json_resume_to_markdown`, `generator.generate_resume_from_json_resume`.
- **Also folded in** (two pre-existing branch bugs, confirmed on clean HEAD): a
  `ui_pages/wizard_compose.reset_order` helper fix (used `EXPERIENCE_CARD.first`, which now
  resolves to the always-present positioning card) and an `aria-label` on
  `#composeSummaryDraft` (axe "form elements must have labels").
- **Deferred to LATER branches:** surgical (non-rewrite) refinement + the richer
  loop-back-with-accept/retire banner; WYSIWYG-as-source (D4); clarifications→corpus
  persistence (D5); a "Regenerate gap-fill" affordance.

### Fix: refinement scope warning is an in-app modal, not a native browser confirm (`fix/refinement-and-loopback`, 2026-07-06)

Preview #3: when a refinement looked like it might change facts (via
`/api/validate-refinement`), `submitRefinement()` fired a browser-native
`confirm()` — an OS dialog in a different visual format from every other modal in
the app, which read as jarring and untrustworthy.

- **`templates/index.html` + `static/app.js`** — new `refinementScopeModal` using
  the same `.cb-modal` shell as `editModal`, driven by a promise-based
  `_showRefinementScopeModal()` helper that mirrors `_showEditModal`'s a11y posture
  (focus trap, Esc-to-cancel, backdrop dismiss, focus restored to the trigger).
  `submitRefinement()` now awaits it instead of `confirm()`. Still FLAGS-not-BLOCKS
  (correcting a fabricated fact is a legitimate refinement), and reminds the user
  that changed claims stay grounded in their corpus + clarifications.
- **Tests** — `tests/ux/regression/test_20260706_refinement_scope_modal.py` drives
  the modal helper directly (LLM-free): reason shown in-modal, Cancel → `'cancel'`,
  Proceed → `'proceed'`.
- Deterministic UI-only change; no LLM/prompt changes, `PROMPT_VERSION` unchanged.

> **Note on scope.** The deeper items from the same plan — surgical (non-rewrite)
> refinement, deterministic assembly at Generate, and the loop-back-to-Compose for
> newly-generated content — are a larger, coupled re-architecture that depends on a
> Compose-authored *frozen composition* object (not yet built). They are deferred to
> a dedicated effort; the app is fully usable after the render-fidelity + richness
> branches.

### Fix: generation richness — rich bullets across every role, metrics surfaced, real Summary + Skills (`fix/generation-richness`, 2026-07-06)

Second branch of the remediation, targeting "weak first-generation bullets/summaries."
Corpus generation was collapsing most roles to a title-only "weak summary," dropping
metric bullets, and emitting no Summary/Skills.

- **`analyzer.py` — code-side anti-starvation floor.** `_stable_user_prefix`'s
  recommendation narrowing is now PER-ROLE: a role the user or `recommend_bullets`
  curated still narrows to that set, but a role with **no** curation signal keeps its
  active bullets instead of being filtered to empty. Previously any role
  `recommend_bullets` under-picked or omitted reached generate with **zero** bullets —
  so the v1.0.8 COVERAGE rule ("every role keeps its bullets") was moot because the
  bullets were already stripped. This also makes generate agree with the Compose
  preview (`corpus_to_json_resume` already kept all active bullets for un-recommended
  roles). On the owner's `robert` corpus: roles reaching generate with bullets **3/8 →
  8/8**, total bullets **11 → 24**.
- **`analyzer.py` — generous, metric-first RECOMMEND.** `RECOMMEND_SYSTEM_PROMPT` now
  targets 3-6 bullets/role, STRONGLY prefers `has_outcome` metric bullets, and never
  zeroes out a role — replacing the old "down to 1 / soft ceiling" stinginess that
  starved the Compose card.
- **`analyzer.py` — first-class Summary + Skills.** Resume rule #1 asks for a
  two-sentence positioning Summary (was one sentence); new rule #9 requires a `## Skills`
  section; and the corpus-mode grounding now explicitly declares the Summary paragraph +
  Skills list as EXPECTED non-bullet sections, so the verbatim-bullet rule no longer
  suppresses them.
- `PROMPT_VERSION` `2026-07-01.1` → `2026-07-06.1`.
- **Validation.** Grounding smoke (`--suite synthetic --subset smoke`): 3 pass / 0 fail,
  grounding 4.6, `fabricated_specifics` ≤ 0.13 — the Summary/Skills carve-out did not
  loosen grounding. Real `generate()` on `robert`: 8/8 roles, 24 bullets (16 with
  metrics), 2-sentence Summary, Skills section. New corpus-mode unit tests pin the
  anti-starvation floor + the generous-RECOMMEND + Summary/Skills prompt rules.

### Fix: single render engine — download == preview, and section titles never silently drop (`fix/single-render-engine`, 2026-07-06)

First branch of the preview/download-fidelity remediation. The `.docx` download
was a **second, divergent renderer**: it parsed the résumé markdown itself and
emitted any `## heading` verbatim, while the on-screen preview + PDF render the
`md_to_json_resume()` structured document through the persona HTML template. The
two disagreed on both styling and *content* — a résumé titled "Professional
Summary" / "Core Competencies" (what plain Word imports produce) rendered those
sections in the `.docx` but dropped them from the preview (they fell to
`meta.sartor.unparsed`).

- **`generator.py`** — replaced the markdown-walking `_write_docx()` with
  `_write_docx_from_json_resume()`, which consumes the SAME `json_doc` the
  preview/PDF use and walks it in `personas/bundled/classic.html`'s section order
  (header → summary → experience → skills → certifications → education →
  projects). Persona typography capture (`_capture_template_styles`, list
  numbering, per-role protos) is unchanged — only the content *source* moved from
  a raw markdown parse to the structured document. Result: **download == preview
  by construction**; a non-canonically-titled section can no longer appear in one
  surface and vanish from the other.
- **`json_resume.py`** — widened `_SECTION_MAP` with the common heading aliases
  ("Professional Summary", "Summary of Qualifications", "Professional
  Experience", "Work History", "Technical Skills", "Core Competencies", "Areas of
  Expertise", …) so those sections land in the canonical JSON Resume fields
  instead of `meta.sartor.unparsed`. Purely widening — can only rescue a title
  that would otherwise be dropped.
- **`db/ats_roundtrip.py`** — the round-trip section-presence check now compares
  on the canonical `_SECTION_MAP` key, so the audit agrees with the
  now-canonicalizing writer instead of flagging equivalent headings as "missing."
- **UI** — added a **"↻ Start new tailoring"** action under the wizard rail
  (`startNewTailoring()` in `static/app.js`, revealed by `wizardInit()`): clears
  the in-flight run (JD, analysis, clarify, composition, generated docs, preview)
  and returns to Step 1 for the same user without a browser refresh. The next
  ANALYZE opens a fresh application. Corpus untouched.
- **Tests** — `tests/test_render_parity.py` pins both invariants: the JSON Resume
  sidecar (download's source) equals `md_to_json_resume()` (preview's source),
  every preview bullet/summary/skill appears in the generated `.docx`, and the
  writer emits canonical headings regardless of the source's titles.
- Deterministic-only change (no LLM calls touched); `PROMPT_VERSION` unchanged.

### Model upgrade: Sonnet 4.6 → Sonnet 5 for the heavy-reasoning calls (`chore/upgrade-sonnet-5-model`, 2026-07-05)

Upgraded the Sonnet-tier LLM calls (analyze/synthesis, generate, cover letter,
clarify_iteration) from `claude-sonnet-4-6` to `claude-sonnet-5`. The Haiku-tier
calls are unchanged — **Haiku 4.5 (`claude-haiku-4-5-20251001`) is still the
latest Haiku; there is no Haiku 5.**

- **`analyzer.py`** — `SONNET_MODEL = "claude-sonnet-5"`. The streaming call now
  sends `thinking={"type": "disabled"}` on the Sonnet path. Sonnet 5 turns
  **adaptive thinking on by default** when `thinking` is omitted (4.6 ran
  thinking-off); left implicit, that would spend part of the 8192-token
  `MAX_TOKENS` budget on reasoning (risking a `max_tokens` truncation of the
  JSON payload), add latency before the streamed resume, and drift eval scores.
  Behavior is thus held identical to 4.6. Adopting adaptive thinking is a
  separate, eval-gated change. Haiku calls are untouched.
- **`hardening.py`** — added a `claude-sonnet-5` entry to `MODEL_PRICING`
  ($3/$15 in/out, standard rate — identical to 4.6; an intro discount of
  $2/$10 runs through 2026-08-31 but the durable rate is used to keep cost
  tracking stable). The `claude-sonnet-4-6` entry is **retained** so historical
  `llm_calls.jsonl` records keep costing correctly.
- **Eval + config provenance** — `evals/runner.py` `MODEL_SNAPSHOTS["sonnet"]`
  and the `promptfooconfig.yaml` provider now name `claude-sonnet-5`.
- **Docs** — `docs/architecture.md` and the two `docs/wiki/` cite lines
  (`deterministic-llm-boundary`, `llm-call-catalog`) updated to the new string.
- **Plugin subagents** — the six Sonnet-pinned `agents/*.md` frontmatter
  entries (`compliance-witness`, `git-flow`, `prompt-archaeologist`,
  `tune-drafter`, `headhunter`, `ux-onboarding-designer`) bumped to
  `claude-sonnet-5`, closing the model-version-drift the 2026-07 efficiency
  review flagged. The three Haiku-pinned subagents are unchanged.

`PROMPT_VERSION` is **not** bumped: no prompt text changed, and the model is an
independent telemetry axis already recorded per call (`model` in
`llm_calls.jsonl`, `MODEL_SNAPSHOTS` in eval results). Tests: added a
`claude-sonnet-5` case to `TestCallCost`. No new dependency. Recommended before
release: run `python evals/runner.py --suite synthetic` to confirm no rubric
regression on the new model.

### 2026-07 efficiency review — witness-only archive (`review/2026-07-efficiency`, 2026-07-03)

Four-area efficiency/optimization review (agent-process & governance DX ·
runtime performance & reliability · docs & wiki processes · tests/CI &
gates), pinned at `4196d0c`, mirroring the 2026-06 excellence-review
formats. Report-and-prescribe only — no code, hook, config, or prompt
changes ride this branch.

- **Archive:** `docs/dev/reviews/2026-07-efficiency/` — 42-row findings
  register (every P0/P1 adversarially verified: 4 CONFIRMED, 9 WEAKENED,
  1 REFUTED-and-dropped), per-area findings files with a measured
  LLM-telemetry appendix (2,955 calls, $35.14 tracked), a verification log
  (incl. an idle re-measurement that resolved a contested test-lane
  number), and 20 banded prescriptions (PX-37..PX-56; 2-judge panel +
  orchestrator tiebreak; 0 CONTESTED).
- **Headliners:** Edit/Write hook process-spawn tax measured ~3.5–4s per
  call (consolidation → PX-37); the Python 3.10 floor is actively broken
  (`import tomllib` fails collection) — PX-42 banded before the first PyPI
  tag; wiki 119 commits behind its checkpoint (PX-41 rides the scheduled
  8.6 ingest); a documented fast test lane halves the inner loop
  (309s → 163s, measured idle).
- **Ledger:** one aggregate carry-forward row; the stale "Open count: 7"
  header corrected per F-doc-02 (post-merge count: 10 — see the ledger head-note).

### Packaging: container image + `sartor --setup` + PyPI workflow (`feat/packaging-publish`, 2026-07-02)

Distribution surface for shipping Sartor beyond a git clone.

- **`sartor --setup`** — one-time post-install bootstrap in `app.py:main()` (now
  argparse-driven): installs Chromium for PDF (`python -m playwright install
  chromium`, `--with-deps` on Linux) and builds the semantic-recall vector index
  (`python -m scripts.build_vector_index`), then exits. Also adds `--host` / `--port`
  (so the container can bind `0.0.0.0` while the default stays loopback-only per
  PX-19) and `--no-browser`. Default (no-flag) behavior is unchanged.
- **Container** — `Dockerfile` (Docker- and Podman-compatible) + `.dockerignore`.
  `python:3.13-slim`, editable install so Flask resolves `templates/` · `static/` ·
  `personas/` under `/app`, Chromium + the vector index **baked in**, non-root user,
  `CMD ["sartor","--host","0.0.0.0"]`. `.github/workflows/docker.yml` builds + pushes
  a multi-arch (amd64 + arm64) image to `ghcr.io/take-tempo-public/sartor` on a tag.
- **PyPI** — `.github/workflows/release.yml` builds the wheel + publishes via OIDC
  **Trusted Publishing** (no stored token), with a tag↔version guard and a wheel
  smoke. The `publish` job is **intentionally gated (fails fast)**: the wheel does
  not yet ship the app's data dirs (`templates/` · `static/` · `personas/` ·
  `docs/wiki`), so `pip install sartor` would 500 at runtime — the fix is a tracked
  follow-up (see `RELEASE_CHECKLIST.md`), and the gate is removed once a fresh-venv
  wheel install actually serves a page.
- **Packaging fix:** added `scripts*` to the wheel's packaged modules — it is
  imported at runtime (`blueprints/diagnostics.py` → `scripts.export_corpus_seed`;
  `sartor --setup` → `scripts.build_vector_index`) but was previously omitted, so it
  only worked from an editable clone.

Docs: install paths (source + container + `sartor --setup`) in `README.md` +
`docs/install.md`, incl. the one-time `[HUMAN]` PyPI Trusted-Publisher + GHCR setup.
Tests: `tests/test_cli_setup.py`. No new runtime dependency.

### Product rename: Callback → Sartor (`rename/callback-to-sartor`, 2026-07-02)

Renamed the product from **Callback** to **Sartor** across the whole repo — brand
mark (the lowercase `sartor.` wordmark, incl. the letter-split masthead spans),
package/CLI name (`pyproject.toml`), the Claude Code plugin + namespace
(`/callback:*` → `/sartor:*`, `.claude-plugin/*`, `.claude/settings.json`, agents +
commands), the JSON Resume `meta.callback.*` → `meta.sartor.*` extension key, UI help
text, docs, wiki (`using-callback.md` → `using-sartor.md`), governance, and the
`AVATAR_SYSTEM_PROMPT` brand mark (`AVATAR_PROMPT_VERSION` → `2026-07-02.1`).

**Guarded false positives — "callback" is also a recruiting term** (the product name
is a pun on getting a call-back/interview). Left untouched: `callback_likelihood` /
`callback_weights` (eval), "generate a callback", "the callback signal/funnel",
"callbacks", `callback-worthy`, and Chart.js's `callback:` tick formatter — all the
recruiting/generic-JS uses. GitHub URLs point to `github.com/take-tempo-public/sartor`
(the résumé `PROMPT_VERSION` was untouched — the main personas carry no brand mark).

`[HUMAN]` follow-ups (not done here): rename the GitHub repo + registries + trademark
clearance (in-app URLs 404 until the repo rename); rename the working directory
`Dev/callback` → `Dev/sartor` (the code is path-agnostic, so no in-repo change needed);
and reload + re-trust the Claude Code marketplace to pick up the `sartor:*` namespace.

### v1.0.8 walkthrough remediation — Branch 8: generation quality (`fix/generation-quality`, 2026-07-01)

The hardest slice — generation correctness. `PROMPT_VERSION` → `2026-07-01.1`.

Deterministic / frontend (no eval):
- **C3 — cover-letter text leaking into the résumé.** A new deterministic
  `hardening.strip_cover_letter_block` drops any block starting at a "Dear …" /
  "To Whom It May Concern" salutation from `resume_content` (a résumé body never
  contains one), applied right after `generate()` in `run_generation`. This stops
  the stray cover letter that appeared at the bottom of the résumé editor + download
  and inflated length past two pages.
- **E4 — user blocked from correcting a hallucination.** The Haiku refinement
  scope-check flagged corrections as "changing facts" and the frontend *blocked*
  them. Now it **flags but never blocks**: the concern is surfaced as a
  confirm-to-proceed prompt, and the user can always proceed.

Prompt changes (`PROMPT_VERSION` bump; each conditional so the iteration-0 /
no-clarification path is unchanged):
- **C1/C2 — older roles came out with no bullets.** The corpus payload carries every
  role's bullets and `md_to_json_resume` parses them fine, so the LLM was dropping
  them. Added a **COVERAGE rule**: every experience that has corpus bullets must
  contribute at least one to `resume_content` — never leave a role title-only when
  bullets exist.
- **E2 — refine clobbered manual fixes.** In corpus mode `_stable_user_prefix` never
  emitted the current draft, so a refine re-derived from the corpus and discarded
  edits. A conditional `<current_resume_draft>` block (iteration>0 + edits) now feeds
  the edited draft in with an evolve-don't-rebuild instruction.
- **E5 — invented "10 years of…" tenure re-appearing.** Added a grounding-check
  worked example forbidding fabricated years-of-experience/ownership figures in the
  summary and making a prior removal binding.
- **H1 — a multi-role clarification answer mashed into one bullet.** The
  clarifications block now instructs the model to attribute each role's content to
  its own experience and never merge two roles into one bullet.

Tests: prompt-structure assertions (`tests/test_corpus_mode_prompt.py`), the C3
stripper (`tests/test_hardening.py`), and a grounding eval run (see
`evals/TUNING_LOG.md`). C1/E2 are corpus-mode-only (not exercised by the synthetic
suite) — validated structurally + owner E2E.

### v1.0.8 walkthrough remediation — Branch 7: retire / restore prior applications (`feat/prior-applications-retire`, 2026-07-01)

The Prior Applications list grew unbounded with no way to hide poor examples or
abandoned drafts (walkthrough J1 / E3 cleanup half). Added a soft-retire flag,
mirroring the corpus `ExperienceTitle.is_active` pattern (migration 0011):

- **`application.is_active`** column (migration `0013`, native `ADD COLUMN` — no
  batch recreate, since `application` is a parent of `application_run`; no backfill,
  everything starts active).
- **Routes:** `DELETE /api/applications/<id>` soft-retires (kept, not hard-deleted —
  runs + audit survive); `POST /api/applications/<id>/restore` reverses it. Both are
  DB-only with an ownership guard (`_safe_username`).
- **List:** `list_applications` hides retired rows by default; `?include_retired=1`
  returns them; the summary payload carries `is_active`.
- **UI:** a "Show retired" toggle in the Prior Applications tab, a `Retire` action on
  each card (`Restore` on retired cards), a `RETIRED` chip, and dimmed retired cards.
  The native checkbox gets the same `appearance:auto` override as the corpus one.

This also closes the deferred cleanup half of E3 (deserted résumés/applications).
Note: collapsing *resolved* applications (interview/rejected/withdrawn) into a
grouped section was considered but deferred — retire + the existing status filter
already tame the "too many to see" problem. Tests: `tests/test_application_routes.py`
(`TestRetireApplication`: retire hides + `include_retired` surfaces, restore, summary
`is_active`, 404).

### v1.0.8 walkthrough remediation — Branch 6: no legacy ATS advice in corpus mode (`fix/analyze-corpus-advice`, 2026-07-01)

Analyze (Step 1) showed "No standard ATS section headings detected…" and "Resume is
quite long (N words). Consider trimming to 1-2 pages…" even though there is no
uploaded résumé — the content is synthesized from the corpus (walkthrough G1).
`db.build_context` ran `check_ats_format` on the corpus synthesis with an always-empty
`sections` list (so the heading warning always fired) against the *whole* corpus (so
the length warning always fired) — both legacy artifacts of the old uploaded-résumé
flow. The corpus synthesis is a structured projection, not the final deliverable, so
those warnings are suppressed in corpus mode; the meaningful JD keyword-overlap signal
is unchanged, and ATS formatting is still judged on the rendered output
(preview/download). Test: `tests/test_build_context_db.py` asserts corpus-mode
`ats_warnings == []`.

### v1.0.8 walkthrough remediation — Branch 5: corpus import — year-only dates + role summaries (`fix/corpus-import`, 2026-07-01)

- **Year-only work dates accepted (F3 → also fixes much of F1).** The extractor and
  the manual add/edit-experience routes required `YYYY-MM` and **dropped** any role
  whose date was a bare year. Résumés that list years only lost those roles — and
  because the extraction prompt was told to omit undated roles, the model tended to
  lump their bullets under the one role it could date ("every bullet in one job").
  A bare `YYYY` is now valid across the extraction normalizer (`_DATE_RE`), the
  extraction prompt, both backend validations (create + update), and the frontend
  patterns. Year-only dates are stored **verbatim** (JSON Resume renders the date
  string as-is; nothing parses it as `%Y-%m`).
- **Role summaries import as role intros, not bullets (F2).** A résumé's role
  intro/scope paragraph was extracted as a bullet. Extraction now has a dedicated
  `summary` field (with a prompt rule separating an intro paragraph from achievement
  bullets), and import turns it into a pending-review **`ExperienceSummaryItem`** —
  the live role-intro path the Compose "Add role intros" picker and the résumé
  render actually read — plus the denormalized `Experience.summary` column for
  parity with the manual add route. Deduped across re-imports/merges.
- **F1 residual.** True LLM mis-grouping on unusually formatted résumés isn't fully
  deterministic; the existing post-import similar-role merge suggestions remain the
  cleanup path for that.

The extraction prompt lives in `onboarding/` (not the `PROMPT_VERSION`-tracked
generation personas) and isn't eval-gated, so no version bump / eval run. Tests:
`tests/test_extract_experiences.py` (year-only accepted; summary captured separately
from bullets) and `tests/test_corpus_import.py` (import summary → `ExperienceSummaryItem`,
not a bullet; year-only kept verbatim).

### v1.0.8 walkthrough remediation — Branch 4: inline bullet edit/approve + Compose UX (`feat/compose-inline-approve`, 2026-07-01)

Frontend-only (CSS/JS); no `PROMPT_VERSION` change, no new dependency:

- **Edit + approve a proposed bullet inline (D3).** A pending-review bullet in the
  Compose step now carries **EDIT** and **APPROVE** actions next to its `PENDING`
  flag. EDIT opens the bullet for editing and `PUT`s the new text to the corpus;
  APPROVE clears the pending flag via `POST /api/bullets/<id>/accept` — both the
  same routes the Career Corpus tab uses. The user no longer has to leave the
  tailor flow, edit in the Corpus tab, and come back for a proposed change to stick.
- **Role-intros checkbox alignment (I1).** The "Add role intros" native checkbox
  was hit by the global `input { flex:1; padding }` rule and stretched across the
  row (label wrapping asymmetrically). Added the `appearance:auto; flex:0 0 auto`
  override (mirrors `.corpus-show-retired input`).
- **Pending banner fades at zero (I2).** Retiring the last pending bullet/title
  now refreshes the corpus pending-review banner (accept already did; retire
  didn't), so it correctly transitions to the "ready" state instead of lingering
  on stale "Accept all pending" copy.

### v1.0.8 walkthrough remediation — Branch 3: edits reach the preview + refine overlay + back-nav (`fix/edit-backprop`, 2026-07-01)

Deterministic (no LLM, no `PROMPT_VERSION` change, no eval):

- **Edits now show in the styled preview (D1/D2).** The Step-6 preview iframe serves
  the cached `last_generated_json_resume` (WYSIWYG). `/api/save-edits` now recomputes
  that cache from the edited résumé markdown via the same deterministic path the
  download uses (`_normalize_markdown` → `md_to_json_resume`), and the frontend
  refreshes the preview iframe after a successful save — so a typed edit appears in
  the styled preview immediately, with zero LLM cost. Cover-letter-only edits leave
  the résumé cache untouched.
- **Refine shows the working overlay (E1).** `submitRefinement` now raises the
  persistent `_setBusy` banner while the refine regenerates (mirrors `runGeneration`),
  instead of only flipping a status label — no more dead-looking ~30-60s wait.
- **Back-navigation is discoverable (E3).** The wizard step rail read as a passive
  progress bar; reachable steps now carry a "Go to step N: <label>" tooltip so users
  find the click-to-go-back affordance. (The deserted-résumé cleanup half of E3 lands
  with the Prior-Applications retire work.)

Tests: `tests/test_app_iteration.py` — `/api/save-edits` recomputes
`last_generated_json_resume` (equals `md_to_json_resume(_normalize_markdown(edit))`,
carries the edit's name) and a cover-only edit leaves it untouched.

### v1.0.8 walkthrough remediation — Branch 2: faithful preview for uploaded templates (`feat/docx-html-companion`, 2026-07-01)

The live preview renders a résumé through a persona's `.html` + `.css` **companion**
(the sibling of the `.docx`). Only the 4 bundled personas shipped companions, so an
uploaded `.docx` template silently fell back to Classic — every uploaded template
previewed as Classic 1-column even though the `.docx` **download** was faithful
(walkthrough B2 / B3 / Step-6 #4).

- **New deterministic module `docx_to_persona_html.py`** (charter C-6, no LLM,
  no new dependency): reads an uploaded `.docx` with python-docx and reconstructs
  the same typography knobs the bundled templates are built from
  (`TypographyPreset` — font family/size, margins, name/heading/job sizes, heading
  treatment: uppercase / small-caps / underline / color, line spacing), then emits
  a companion `.html` (a byte-for-byte copy of the `classic.html` Jinja2 skeleton
  with only the CSS `href` swapped) + a `.css` (Classic's ATS-safe single-column
  structure, re-typed with the uploaded template's own typography) + a
  `<stem>.persona.json` fidelity sidecar.
- **Honest fidelity ceiling.** python-docx can't represent multi-column sections,
  tables, text boxes, or floating images; those sources are marked
  `layout_fidelity: "typography_only"` and rendered single-column with the source's
  fonts/colors/margins — which is exactly what the `.docx` download's `_write_docx`
  produces, so preview and download stay mutually consistent. Never fabricates a
  layout it can't deliver.
- **Wiring.** Companions are generated eagerly on upload (`upload_user_persona`,
  best-effort — a failure logs and still 201s, falling back to Classic as before)
  and lazily on first preview / PDF render for personas uploaded before this shipped
  (`preview_application_html`, `generator._render_pdf_from_json`). Idempotent
  (mtime-cached).
- **Spacious page-break.** Added `page-break-after: avoid` to the Spacious
  letterhead so paged.js stops occasionally orphaning the header on page 1
  (walkthrough Preview #2). Pagination of long résumés should be confirmed visually.

Tests: `tests/test_docx_to_persona_html.py` (round-trip extraction vs each
`TypographyPreset`; emit + skeleton-contract parity; fidelity fallback on tables;
`html_template_path_for` now resolves the companion so the preview stops falling
back to Classic). `PROMPT_VERSION` untouched; no new dependency.

### v1.0.8 walkthrough remediation — Branch 1: Step-4 template picker polish (`fix/preview-template-bugs`, 2026-07-01)

First slice of the pre-tag walkthrough-remediation epic. Two Step-4 template-picker fixes:

1. **Template-card badge overflow (B1).** A long owned-template filename pushed the
   `ATS` / `MINE` badges outside the card and triggered a horizontal scrollbar. The
   template name now truncates with an ellipsis (`.template-mini-label`: `flex:1;
   min-width:0`) and the two badges are pinned non-shrinking (`flex:0 0 auto`), so they
   always stay inside the row.
2. **Confusing picker copy (B4).** The Step-4 hint ("…the preview shows pages just as
   they'll print. Same content, different typography and layout.") read ambiguously.
   Reworded to state plainly that the résumé content stays the same and the template
   only changes how it looks (fonts, spacing, layout).

Frontend-only (CSS/HTML/JS); `PROMPT_VERSION` untouched; no new dependency. Full suite
green (1418 passed). Remaining walkthrough items (preview fidelity, edit-backprop,
generation quality, corpus import, prior-apps retire, Sartor rename, …) follow as
their own branches per the epic plan.

### Corpus import: similar-role merge suggestions + retire-hidden-by-default + persistent busy cue (`fix/corpus-import-and-curation-ux`, 2026-06-29)

Four corpus-building UX problems surfaced during e2e testing:

1. **Duplicate roles on import (P1).** The importer matched existing roles on an
   exact `(company, start_date)` key, so any date/company drift forked the same
   job into a new experience and split its bullets. Added a deterministic
   similarity scorer (company/title/dates/bullets → EXACT/SIMILAR/DISTINCT — pure
   stdlib, no LLM, inside the C-6 hardening boundary) and a post-import "possible
   duplicate roles" review card: the user **merges** (the extra title becomes an
   alternate, bullets combine + dedup, the **corpus dates are kept**) or **keeps
   separate** (persisted, so it stops re-surfacing). The importer's exact-match
   auto-merge is unchanged — only fuzzy matches ask.
2. **No persistent busy cue (P2).** Long actions (ingest / analyze / generate /
   cover letter) now raise a persistent flashing "working…" banner (vs the 2.4s
   toast) and disable the in-progress control, so the user doesn't click around
   mid-call.
3. **Couldn't truly remove an alternate title (P3) + retired clutter (P4).**
   "Delete" on a title was a soft-retire that left it visible as an `ALT` row.
   Retired titles **and** bullets are now hidden by default and shown only when
   the new "Show retired" checkbox is ticked (each with a RESTORE action);
   generation hard-excludes retired items. Soft-retire is kept (no hard-delete) —
   `application_run_title` / `proposal_review` FKs reference the rows for audit.

`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched; no new dependency (stdlib
`difflib` only). Two migrations, both FK-cascade-safe (plain `add_column` /
`create_table`, never a batch recreate of a parent table).

**Added**
- `onboarding/experience_match.py` — deterministic experience-similarity scorer.
- `ExperienceTitle.is_active` (migration `0011`) + the `merge_dismissal` table
  (migration `0012`).
- Routes: `GET /api/users/<u>/corpus/merge-suggestions`,
  `POST /api/experiences/<id>/merge`,
  `POST /api/users/<u>/corpus/merge-suggestions/dismiss`.
- Frontend: "possible duplicate roles" review card, global "Show retired"
  toggle + RESTORE actions, persistent busy banner (`_setBusy`).
- Tests: `tests/test_experience_match.py`, `tests/test_corpus_merge_and_retire.py`,
  `tests/ux/regression/test_20260629_corpus_retire_and_busy.py`.

**Changed**
- `blueprints/corpus/experiences.py` — title `DELETE` soft-retires via `is_active`;
  title/bullet `PUT` accept `is_active` for restore; the experience detail route
  honors `?include_retired=1`.
- `blueprints/corpus/_shared.py` — `_experience_detail_dict` hides retired rows by
  default; `title_count` is active-only.
- `db/build_context.py` — `eligible_titles_for` hard-gates on `is_active` so a
  retired title can never reach a generated résumé.
- `static/app.js` / `static/style.css` / `templates/index.html` — corpus UX, busy
  banner, import summary now surfaces `alternate_titles_created`.

**Fixed**
- Import no longer silently forks the same role across drifted dates/titles.
- Retired titles/bullets no longer linger in the corpus view.

### README rebuilt as a three-audience front door (`docs/readme-icp-ladder`, 2026-06-29)

The README is restructured around a cumulative three-audience ladder — job seeker →
coach/headhunter → developer (`one → many → extend`) — and brought under the project's
doc disciplines: a `Purpose / Audience / Authoritative-for` header, a documentation map,
and single-home / cite-don't-restate (it owns the pitch + the ladder; everything else
links to its canonical doc, with volatile facts linked out so the auto-published front
door can't drift). Two C-0 honesty corrections fold in: the governance status is flagged
as having two boundary gates owed (scheduled v1.0.8), and the egress claim is upgraded to
"machine-verified" by `tests/test_egress_allowlist.py`. No new dependency; `PROMPT_VERSION`
/ `AVATAR_PROMPT_VERSION` untouched.

**Changed**
- `README.md` — full rewrite as the product front door; clone URL corrected to
  `github.com/take-tempo-public/sartor`; `DOC-STATUS` freshness markers added.

**Added**
- `docs/dev/documentation-architecture.md` — the documentation publishing strategy that
  the README front door embodies (the layered L0–L3 source chain, Fumadocs-as-projection,
  the merge=publish gate, the `DOC-STATUS` convention). Dev-internal.

### Compose UX flaky-test class stabilized + a real server-side title-pin race fixed (`fix/compose-ux-stabilization`, 2026-06-26)

A v1.0.8 reduction-sprint branch closing carry-forward ledger #3 — the recurring flaky Compose-wizard
UX-test class (~25 logged recurrences). Chasing the last ~1% surfaced **two distinct causes**:

1. **Test-timing (5 of the 6 members).** Entering Compose runs `loadComposition()`, which fires up to 3
   background `recommend-*` calls, each re-running `loadComposition()` (a full `#composeList` teardown +
   rebuild); the Playwright page-object read-helpers did raw queries with no wait and read the DOM
   mid-rebuild. The 8.5 partial fix (waiting on `.compose-experience-card`) only proved the *initial*
   render, not the terminal one.
2. **A real, rare server-side race (the 6th member, `test_positioning_pin_preserves_title_pin`).** The
   flaky test was catching an actual bug, not a harness artifact: the client sends the title pin
   correctly in every `/composition` POST, but the save's title-eligibility validation could
   intermittently not see a just-added title (pooled SQLite + WAL read-snapshot visibility), return
   400, and drop the pin — so a user pinning a title then quickly pinning a positioning variant could
   rarely lose the title pin. The race resists reproduction (it vanished under every instrumentation
   attempt — a Heisenbug), so it's fixed defensively and validated by a deterministic unit test rather
   than an end-to-end repro.

`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched; no new dependency.

**Fixed**
- **Server-side (real bug):** `blueprints/applications.py` `save_application_composition` now self-heals
  a transient title-eligibility miss — on a miss it ends the read transaction (`session.rollback()`)
  and re-reads with a fresh snapshot before returning 400, so a momentarily-invisible just-added title
  is no longer dropped; a genuinely stale/foreign id still 400s. Covered by a deterministic
  miss-then-hit unit test (`test_post_self_heals_transient_title_visibility_miss`).
- **Test-infra (the flaky class):** all 6 members —
  `test_positioning_pin_preserves_title_pin`, `test_keyboard_reorder_persists_and_reset_reverts` /
  `test_pointer_drag_reorders`, `test_add_title_then_pin_persists`,
  `test_no_recommendations_order_persists_on_reload`, `test_compose_skills_card_drop_persists`,
  `test_happy_path_through_template_preview`.

**Changed**
- `static/app.js`: `loadComposition()` clears a `data-compose-ready` attribute on `#composeList` at
  entry (before its `/composition` fetch) and sets it after the final synchronous append — a *stably
  present* marker proves the auto-recommend re-render cascade reached its terminal render. Two
  non-behavioral lines (a `data-` attribute no code/CSS reads → byte-identical render/save/prompt).
- `ui_pages/wizard_compose.py`: new `_wait_settled()` (drains in-flight recommend POSTs via
  `networkidle`, then waits for the marker present + stable across 3×50ms samples); `_wait_loaded()`
  delegates to it; the read-helpers (`bullet_texts` / `title_texts` / `title_is_selected` /
  `experience_card_count` / `chosen_intro_texts`) and action helpers (`reset_order` / `add_title` /
  `drag_below` / `move_*` / `select_title` / `enable_role_intros`, via the `_first_card` /
  `_bullet_list` anchors or explicit calls) settle first; new `wait_skills_card()` / `drop_skill()` /
  `pin_positioning_variant()`.
- `ui_pages/selectors.py`: add `Compose.SKILLS_CARD` / `SKILL_ROW` / `SKILL_DROP` / `READY` /
  `POSITIONING_VARIANT` / `POSITIONING_CHOSEN`.
- `tests/ux/regression/test_20260613_skill_corpus_item.py` + `…/test_20260612_experience_summary_item.py`:
  use the new POM helpers (close the resolve-then-click + raw-positioning-click windows).

**Validation:** the server self-heal is proven by a deterministic miss-then-hit unit test (the live
race is unreproducible — it masked under three separate instrumentation attempts). Supporting empirical
evidence: the previously-flaky positioning test ran **400/400** with the fix (it was ~0.37%, 2-in-544,
before); the other 5 members **30/30** each + group **10/10**; full `pytest -m ux` ✓ (69) and full
`pytest` ✓ (1394). Gate: ruff ✓ · ruff format --check ✓ · mypy ✓ (228). Carry-forward ledger #3 →
Resolved (open count 7 → 6).

### Help-opener de-duplication — shared `static/help-modal.js` leaf (`refactor/help-opener-dedup`, 2026-06-25)

A v1.0.8 reduction-sprint branch closing carry-forward ledger #7. The wizard's help-modal opener
`openHelpModal` (`static/app.js`) and the self-contained diagnostics console's ported `openDashHelp`
(`dashboard/templates/dashboard.html`) were byte-identical logic plus a duplicated `cb_help_seen:`
localStorage seam. Extracted the single implementation into a NEW shared **leaf** module both pages
load — which does **not** make the console load `app.js` (the leaf is loaded like `style.css` / the
vendored chart bundle it already pulls), so the console's self-containment is preserved. **No
product behavior, prompt, route, dep, or version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`
untouched (frontend-only → no eval run owed).

**Changed**
- `static/help-modal.js` (new): the shared primitive — `window.cbOpenHelpModal(entry, triggerEl)`
  (opens the shared `#helpModal` for an already-resolved `{title, body}`; Esc / Tab focus-trap /
  `[data-help-dismiss]` click-away / `aria-expanded` toggle / focus-restore, all null-trigger safe)
  plus the `cb_help_seen:` seam (`cbHelpSeen` / `cbMarkHelpSeen` / `CB_HELP_SEEN_PREFIX`). ES5,
  exposed as `window` globals (no JS build step in the repo; the dashboard inline JS is not an ES
  module).
- `static/app.js`: `openHelpModal` / `_helpSeen` / `_markHelpSeen` reduced to thin wrappers that
  resolve `_HELP_REGISTRY` (kept local) and delegate to the shared globals. Signatures, callers,
  `_HELP_REGISTRY`, `_initHelp`, and all tour logic unchanged.
- `dashboard/templates/dashboard.html`: `openDashHelp` / `_dashSeen` / `_markDashSeen` reduced to
  thin wrappers over `_DASH_HELP` (kept local); the stale "opener lives here" comment refreshed to
  reflect the shared leaf (registry stays local; console still never loads `app.js`).
- `templates/index.html` + `dashboard/templates/dashboard.html`: load the leaf as a classic
  `<script>` (no `defer`) **before** `app.js` (index) and in the dashboard `<head>` **before** the
  inline help IIFE, so the shared globals exist at parse time.

**Gate:** ruff check ✓ · ruff format --check ✓ · mypy ✓ (228) · pytest ✓ (1324) · UX help/dashboard
+ axe tiers ✓ (25). Public function names, DOM ids (`#helpModal` / `#help-icon-*`), and the
`cb_help_seen:` keys are all unchanged → zero test-code changes (the `_TOUR_STOP_BLOCKS` suppression
contract still holds). Carry-forward ledger #7 → Resolved (open count 8 → 7).

### Kit-adoption Phase 2 #4 — `interrogate` docstring-coverage floor-lock gate (`chore/kit-phase2-interrogate`, 2026-06-25)

Fourth and final implementation sub-item of the agent-coding-practices kit-adoption arc **Phase 2**
(the strictness ratchet — kit-adoption-design.md §4/§6; Decision KIT-6 "measured-current /
warn-start" + KIT-7 named-exempt scope). Adds a docstring-**coverage** gate via **interrogate** (a
NEW dev dependency), shaped as a **pytest floor-lock ratchet** mirroring
`tests/test_route_containment_gate.py`: today's measured production coverage is recorded as
`[tool.interrogate].fail-under` and the gate asserts `coverage >= floor` — green today (forces no
new docstrings; KIT-6 "lock the gain, don't force new work"), red only on a regression below the
floor. It is the aggregate-% companion to the ruff-`D` family (which gates per-symbol docstring
*presence*) and runs inside the standard `pytest` gate — no new hook, no `.claude/settings.json`
change, no governance-hooks-gate change. **No product behavior, prompt, route, or version change**;
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (no prompt constant touched → no eval run owed).

**Changed**
- `pyproject.toml`: new `interrogate>=1.7,<2.0` dev dependency in `[project.optional-dependencies].dev`;
  new `[tool.interrogate]` block recording the floor (`fail-under = 99`), the production-only scope
  (`exclude` = the KIT-7 exempt set `tests`/`evals`/`scripts`/`db/migrations` + data/build dirs), and
  the ignore flags chosen to keep the metric coherent with the ruff-`D` google scope
  (`ignore-module`/`ignore-magic`/`ignore-private`/`ignore-semiprivate`/`ignore-nested-functions`/
  `ignore-overloaded-functions`/`ignore-init-method`; `@property` accessors COUNT —
  `ignore-property-decorators = false` — to match the D102 treatment of `config.py`'s derived-root
  properties). Single-underscore helpers are semiprivate and excluded, so a helper-only module like
  `web_infra/` contributes zero counted symbols by design.
- `tests/test_docstring_coverage_gate.py` (new): the floor-lock gate. Re-runs the bare interrogate
  CLI via subprocess (single source of truth = `[tool.interrogate]`; no `import interrogate`, so no
  mypy/stub coupling and robust to interrogate API drift) and asserts exit 0. Skips gracefully when
  interrogate is not installed (mirrors the `tests/ux/conftest.py` Chromium skip-guard) so default
  `pytest` stays green without dev-extras; has teeth in CI. Teeth assertions: the scan names core
  production modules and covers a non-trivial symbol surface (≥ 250 of the current 417). `ui_pages/**`
  is IN scope (matching the surface the ruff-`D` family covers, its ratchet unit 8).
- `onboarding/review_cli.py`, `onboarding/extract_experiences.py` (docstrings only): documented the two
  public classes `Color` and `ExtractResponse` that interrogate surfaced at adoption — genuine gaps
  that ruff-`D`/google's D101 does not flag (attribute-only / pydantic-model classes). Documenting them
  took public-API production coverage from 99.5% to **100%**, so the recorded floor (`fail-under = 99`)
  locks a fully-documented baseline with ~1 pt of headroom against incidental churn (not a brittle 100).
- Owner-directed documentation pass (docstrings only, no behavior change): documented the **50**
  below-public-bar internal symbols interrogate surfaces at *maximal* scope (single-underscore helpers,
  nested SSE/worker closures, and private methods across ~20 production files — `analyzer.py`,
  `blueprints/**`, `parser.py`, `json_resume.py`, `corpus_to_json_resume.py`, `dashboard/`, `recall/`,
  `web_infra/`, `onboarding/`, `ui_pages/`), taking *maximal*-scope production coverage (all ignore
  flags off) to **100%** as well. The interrogate **gate stays public-API-scoped** (ignore flags
  unchanged, coherent with ruff-`D`) — these docstrings are a quality pass, not a gate-scope change.
  `analyzer.py` re-verified **PROMPT-SAFE** (all 15 prompt constants sha256 byte-identical vs HEAD).
  Also added module docstrings to the 5 empty `tests/**/__init__.py` package markers; KIT-7 keeps
  `tests/` D-exempt, so no per-function test docstrings were added.

**Gate:** ruff check ✓ · ruff format --check (218) ✓ · mypy (228) ✓ · pytest. New dependency
(interrogate) added → CHANGELOG updated (charter D-1 / AGENTS.md "What NOT to do"). No version bump
(tooling config + one test + a docstring-only pass: 2 public-class fixes + 50 internal helpers + 5 test
`__init__` modules); the `ruff-changed` hook needs no edit (the gate is the standard `pytest` arm).
Teeth verified: with `fail-under` temporarily at 100 vs 99.5% actual the
floor-lock test went red, then green again at the locked floor. KIT-6 "warn-start": the floor locks
today's coverage; "ratchet up later" = raise `fail-under` in a future branch. **Phase 2 of the
kit-adoption arc is now COMPLETE** (only the 8.7 skills/hooks-coherence remainder rides on).

### Kit-adoption Phase 2 #3 — ruff `D` (pydocstyle/google) enabled + first ratchet rung (`chore/kit-phase2-ruff-d`, 2026-06-24)

Third implementation branch of the agent-coding-practices kit-adoption arc **Phase 2** (the
strictness ratchet — kit-adoption-design.md §4; Decision KIT-6 "ratchet-then-block" + KIT-7
named-exempt end-state). Enables the ruff `D` (pydocstyle) family with the **google** convention.
The docstring-**content** rules block tree-wide; the **missing-docstring** rules ratchet per-module
(first documented module: `hardening.py`). Tooling-config + docstrings only — **no product behavior,
dependency, prompt, route, or version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched
(docstrings are not prompt constants — the analyzer prompt-constant sha256 dump is byte-identical
pre/post, so no eval run is owed).

**Changed**
- `pyproject.toml`: `select += "D"`; new `[tool.ruff.lint.pydocstyle] convention = "google"` (narrows
  D to google's subset + silences the D203/D211 + D212/D213 conflicts). `per-file-ignores`: `"D"`
  added to the three exempt entries (`tests/**`, `evals/*`, `scripts/**`); a new **D missing-docstring
  ratchet block** waives only `D101/D102/D103/D105/D107` on the 27 not-yet-documented production
  modules (16 entries; `ui_pages/**` is the 12-file POM glob) — the content rules still apply to them.
  The list shrinks branch-by-branch toward the §6 exit criterion (empty → D blocks everywhere outside
  the exempt set).
- Docstring-content sweep across the production tree (39 files, docstrings only): 105 safe autofixes
  (D209/D411/D412) + 143 hand fixes (D205 blank-line-after-summary ×139, D301 raw-string ×3, D415
  terminal-period ×1) so the content rules pass tree-wide. `D205` has no safe autofix in ruff 0.15.12.
- `hardening.py`: documented its 10 public TypedDict classes (`CandidateInfo` … `ContextSet` — the
  `context_set` JSON contract between pipeline stages) → the module is now fully `D`-clean and the
  google-style reference for later ratchet branches.
- `.git-blame-ignore-revs`: the mechanical content-sweep commit (`6ee0be1`) added so blame skips it.
- **Ratchet COMPLETE — §6 exit for `D`** (`chore/kit-phase2-ruff-d-ui-pages`, 2026-06-25): units 2–8
  drained the remaining production modules branch-by-branch (`recall/` · `config.py` ·
  small-blueprints trio · `onboarding/` trio · `db/models.py` · `analyzer.py` · `ui_pages/**`), so the
  missing-docstring ratchet block is now **empty**. `D` (incl. `D101/D102/D103/D105/D107`) blocks
  **everywhere outside the KIT-7 exempt set** (`tests/**` · `evals/*` · `scripts/**` ·
  `db/migrations/versions`). `ui_pages/**` — the 12-file Playwright Page-Object-Model, 89 symbols —
  was the last + largest unit; docstrings only across every unit (no dependency/version/prompt change).

**Gate:** ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest. No new dependency
(ruff already present); no version bump (lint config only); the `ruff-changed` hook needs no edit
(`ruff check` inherits `select`). `D` hard-blocks day one (KIT-6 — unambiguous, not warn→block).

### Kit-adoption Phase 2 #2 — mypy `--strict` on leaf modules (`chore/kit-phase2-mypy-strict-leaves`, 2026-06-24)

Second implementation branch of the agent-coding-practices kit-adoption arc **Phase 2** (the
strictness ratchet — kit-adoption-design.md §4; Decision KIT-6 "ratchet-then-block" + KIT-7
named-exempt end-state). Brings the first three modules to full mypy `--strict` + `warn_unreachable`
via a per-module override — the **first rung** of the module-by-module `--strict` ratchet toward the
§6 exit criterion. Tooling-config + one type-annotation only — **no product behavior, dependency,
prompt, route, or version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

**Changed**
- `pyproject.toml` `[[tool.mypy.overrides]]`: new per-module block tightening `scraper`,
  `json_resume`, `pdf_render` (the deterministic, LLM-free P1-Hardening leaves) to the `--strict`
  preset + `warn_unreachable`. `strict` is **not** a per-module-settable option
  (`mypy.options.PER_MODULE_OPTIONS`), so the preset is spelled out as its per-module-capable
  component flags (`disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_untyped_calls`,
  `disallow_untyped_decorators`, `disallow_any_generics`, `disallow_subclassing_any`,
  `check_untyped_defs`, `warn_return_any`, `strict_equality`, `extra_checks`) + `warn_unreachable`.
  The global mypy config stays permissive; these three modules now block.
- `scraper.py`: `fetch_profile_content(config: dict)` → `dict[str, Any]` (the one
  `disallow_any_generics` hit — keys are `str`, values heterogeneous, so `dict[str, Any]` is the
  honest minimal type; not bare `Any`, so `ANN401` does not flag it) + `from typing import Any`.
  `json_resume.py` and `pdf_render.py` were already `--strict`-clean (0 changes). The three leaves
  are pure (stdlib / 3rd-party imports only, no intra-project calls) → strict treatment surfaced no
  cross-module cascade.

**Verification** — `ruff check .` clean tree-wide · `ruff format --check` (217 files) ok ·
`mypy .` (227 files) ok · `pytest` **1390 passed / 1 known-flaky** (the tracked Compose-load UX race
`test_20260604_bullet_drag_reorder::test_pointer_drag_reorders` — intermittent on both this branch
and the clean tree, **not code-caused**: this branch touches no Compose/`app.js` code; see
RELEASE_CHECKLIST carry-forward ledger #3). No eval run (no prompt change). Per-module tracking:
3 production modules now at full strict; the rest remain permissive (no override = permissive).
Remaining Phase 2: `D` + google pydocstyle, `interrogate` coverage gate, larger-module `--strict`
(`analyzer.py` / `applications.py`) — each its own later branch.

- **Rung 2 — `blueprints.applications`** (`chore/kit-phase2-mypy-strict-applications`, 2026-06-25):
  the next rung adds `blueprints.applications` (~2,100 LOC — the first **non-leaf route/seam**
  module) to the same strict override roster. Clean for a different reason than the pure leaves:
  Phase-2 #1 (`ANN`) had already annotated its whole call graph, so `--strict` + `warn_unreachable`
  surfaced **no `disallow_untyped_calls` cascade** — only **13 errors**, all mechanical (12
  bare-generic `type-arg` → parametrized, predominantly `dict[str, Any]`; 1 `no-any-return` →
  `cast("str | None", …)`, a runtime no-op). `_load_application_owned` stays `tuple[Any, Any]`
  (parametrized for `disallow_any_generics`; the precise `tuple[Application|None, Candidate|None]`
  would force a None-narrowing change at its 9 in-module callers — a deferred None-safety pass, out
  of scope for a typing rung; the docstring records this). The strict roster is now
  `scraper`/`json_resume`/`pdf_render`/`blueprints.applications`. PROMPT-SAFE (no prompt constants
  in the module — grep-0; the `anthropic` refs are exception types). No prompt/dep/version change;
  gate green (ruff/format ✓ 217, mypy ✓ 227, pytest **1389 passed / 2 known-flaky** — both the
  ledger #3 Compose load-race, passed clean isolated 2/2). Remaining Phase 2: `interrogate`
  coverage gate + larger-module `--strict` (`analyzer.py`).

- **Rung 3 — `analyzer.py`** (`chore/kit-phase2-mypy-strict-analyzer`, 2026-06-25): the final
  *larger-module* rung adds `analyzer.py` (~3,800 LOC — the prompt-home module and the sole LLM-call
  site) to the strict override roster, **completing the larger-module `--strict` commitment** (the
  three leaves landed rung 1, `applications.py` rung 2). Clean for the same reason as rung 2: Phase-2
  #1 (`ANN`) had pre-typed the whole call graph, so `--strict` + `warn_unreachable` surfaced **no
  `disallow_untyped_calls` cascade** — only **47 errors**, ~91% mechanical: 43 bare-generic `type-arg`
  → parametrized (`dict[str, Any]` / `list[dict[str, Any]]`), 2 `no-any-return` →
  `cast("dict[str, Any]", …)` (runtime no-ops), and 2 `warn_unreachable` — one a `ContextSet`-TypedDict
  always-truthy artifact on a deliberate `or {}` persisted-JSON defense (kept behind a scoped
  `# type: ignore[unreachable]`), the other fixed by widening one local to `object` so a documented
  dict-or-list branch stays live (no runtime change). The strict roster is now
  `scraper`/`json_resume`/`pdf_render`/`blueprints.applications`/`analyzer`. **PROMPT-SAFE the GOTCHA-4
  way** (analyzer.py is the prompt home, so the module's grep-0 shortcut doesn't apply): the 15 prompt
  constants (11 `_BASE_SYSTEM_PROMPTS` values + `AVATAR_SYSTEM_PROMPT` + `_COVER_LETTER_RULES_BLOCK` +
  `PROMPT_VERSION` + `AVATAR_PROMPT_VERSION`) were sha256-proven byte-identical pre/post → no
  `PROMPT_VERSION` bump, no eval. Gate: ruff ✓ · ruff format --check ✓ 217 · mypy ✓ 227 · pytest — the
  ledger #3 Compose bullet-load race **fired on the pre-commit run** (**1389 passed / 2 failed**:
  `test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts` +
  `::test_pointer_drag_reorders`), both **passed clean isolated** (1/1, 2/2); an earlier same-session
  full run on the **identical** code was clean (1391/0) — the same-code fire-then-clean alternation is
  itself proof the branch (annotations + config + docs, runtime-inert for Compose) is **not
  code-caused**. Remaining Phase 2: the `interrogate` coverage gate (the larger-module `--strict`
  commitment is now complete).

### Kit-adoption Phase 2 #1 — enable ruff `ANN` (`chore/kit-phase2-ruff-ann`, 2026-06-24)

First implementation branch of the agent-coding-practices kit-adoption arc **Phase 2** (the
strictness ratchet — kit-adoption-design.md §4; Decision KIT-6 "ratchet-then-block" + KIT-7
exempt set). Enables the `flake8-annotations` (`ANN`) lint family whole across the production
tree, fixes every real hit by hand, and carves the Decision-7 exempt set. Tooling-config +
type-annotation only — **no product behavior, dependency, prompt, route, or version change**;
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (no prompt string was edited; annotations
are runtime-inert, so generation output is byte-identical).

**Changed**
- `pyproject.toml` `[tool.ruff.lint]`: `select += ["ANN"]` (whole-family, forward-protective —
  ANN is unambiguous, so it hard-blocks day one via `ruff-changed.sh`, not warn→block
  ratcheted). `per-file-ignores += "ANN"` for the Decision-7 strictness-exempt set:
  `tests/**`, `evals/*`, and a net-new `scripts/**` entry (`db/migrations/versions` is already
  fully `extend-exclude`d). Production carries **no** ANN override — the §6 exit-criterion shape
  for this rule family.
- Hand-annotated **60 production violations across 18 files** (ruff's ANN autofix is
  `--unsafe-fixes`-only — none used, per Phase-1 discipline): SSE `stream`/`worker` inner-fns
  → `Iterator[str]` / `None` (`blueprints/diagnostics|analysis|generation|assistant.py`); route
  handlers → `ResponseReturnValue`; serializers/loaders → the `db.models` row types + `Session`
  (via `TYPE_CHECKING` blocks); docx plumbing → `Paragraph` / `Run` / `CT_NumPr`
  (`generator.py`, `parser.py`).
- **`ANN401`** (11 any-type hits) handled case-by-case (no blanket family ignore): typed the
  typeable (`session: Session`, `client: Anthropic`, `exp: Experience`, `raw: object`,
  `val: str | int | float | None`, `parent: Document | _Cell`); one **targeted `# noqa: ANN401`**
  on `db/session.py`'s SQLAlchemy `connect`-event listener (DBAPI / pool objects are dynamically
  typed at that boundary by design).
- Minor typing-driven, behavior-preserving body touches surfaced by the now-checked bodies:
  `_load_application_owned` / `_tag_link_target` return a bare `tuple` (their slots are
  correlated/polymorphic — precise typing would force an out-of-scope None-narrowing pass at the
  call sites); `_tag_link_target` uses a distinct `skill` local so `subject` is a clean
  `Bullet | ExperienceTitle` union; `blueprints/assistant.ask()` keeps `safe_user` a plain `str`
  via a `resolved` temp (a latent `str | None` surfaced once `ask()` gained a return type).

**Verification** — `ruff check .` clean tree-wide · `ruff format --check` (217 files) ok ·
`mypy .` (227 files) ok · `pytest` **1391 passed** (the tracked Compose-wizard load-race class
passed clean this run). No eval run (no prompt change). Phase 2 sub-items `D` / `interrogate` /
mypy `--strict` remain (each its own later branch).

### Kit-adoption Phase 1 — SIM/RUF ruff triage (`chore/kit-phase1-sim-ruf-triage`, 2026-06-24)

Final implementation branch of the agent-coding-practices kit-adoption arc Phase 1
(kit-adoption-design.md §4; Decision-6 "ratchet-then-block"). Enables the `flake8-simplify` (`SIM`)
+ `ruff`-specific (`RUF`) lint families whole, fixes the real hits, and ignores the documented noise.
Tooling-config + mechanical-cleanup only — **no product behavior, dependency, prompt, route, or
version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (no prompt string was edited —
the ambiguous-unicode hits inside prompt text are *ignored*, not rewritten).

**Changed**
- `pyproject.toml` `[tool.ruff.lint]`: `select += ["SIM", "RUF"]` (whole-family, forward-protective);
  `ignore += ["RUF001", "RUF002", "RUF003"]` (117 ambiguous-unicode false-positives — em-dashes /
  smart-quotes in prompt + UI copy, the documented Decision-6 noise) `+ ["SIM905"]` (the
  `hardening.STOP_WORDS` compact `.split()` constant — the fix explodes it into a ~110-element literal);
  `per-file-ignores["tests/**"] += ["RUF059"]` (idiomatic unused-tuple-unpack in tests, matching the
  existing S-family test carve-outs).
- Auto-fixed 41 hits via `ruff check --fix` (no `--unsafe-fixes`): **RUF100** unused-noqa ×33, **SIM300**
  yoda-conditions ×3, **RUF022** unsorted-`__all__` ×3, **RUF023** unsorted-`__slots__` ×1
  (`analyzer._StreamDone` — prompt-inert), **SIM114** if-with-same-arms ×1.
- Hand-fixed 32 real hits: **SIM115** open-without-context-manager ×16 → `Path(...).read_text/write_text`
  (all in tests); **RUF012** mutable-class-default ×7 → `ClassVar[...]` (6 test data tables + one
  `ui_pages` lookup dict); **SIM117** nested-`with` ×4 → combined; **SIM105** suppressible-exception ×4 →
  `contextlib.suppress`; **RUF022** ×1 → `# noqa: RUF022` on `db/models.py` `__all__` (preserves the
  curated domain grouping a flat sort would scatter).

**Verification** — `ruff check .` clean tree-wide · `ruff format --check` (217 files) ok · `mypy .`
(227 files) ok · `pytest` **1390 passed / 1 flaky** (`test_add_title_then_pin_persists`, the tracked
Compose-wizard load-race class — passed clean on isolated re-run; diff touches no Compose/frontend code).
No eval run (no prompt change). **Closes kit-adoption Phase 1.**

### Kit-adoption Phase 1 — ruff format (`chore/kit-phase1-ruff-format`, 2026-06-23)

Second implementation branch of the agent-coding-practices kit-adoption arc (kit-adoption-design.md
§4 Phase 1). Applies the `ruff format` auto-formatter tree-wide and wires it as a commit-time gate.
Style/tooling only — **no product code, dependency, prompt, route, or version change**;
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (proven byte-identical).

**Changed**
- Applied `python -m ruff format .` across the tree — **161 of 217 files** reformatted (56 already
  clean). Pure formatter output: hand-packed collection literals (`frozenset({...})`) exploded one
  item per line, type annotations / comprehensions reflowed, blank-line normalization. No hand edits.
- `.claude-plugin/hooks/ruff-changed.sh` — the pre-commit `ruff` hook now also runs
  `ruff format --check` on staged Python and blocks an unformatted commit (KIT-6 "hard-block
  unambiguous gates day one"), alongside the existing `ruff check`.
- `pyproject.toml` `[tool.ruff.format]` — declares the adopted formatter style
  (`quote-style = "double"`, `indent-style = "space"`; matches ruff defaults, so reformat output is
  unchanged) so the gate is deterministic across machines + ruff versions.

**Added**
- `.git-blame-ignore-revs` — lists the reformat commit so `git blame` (and GitHub) skip the
  mass-formatting noise.

**Verification** — prompt constants proven byte-identical via a sha256 dump-diff (31 entries: every
`*_SYSTEM_PROMPT`, the `_BASE_SYSTEM_PROMPTS` registry, `_COVER_LETTER_RULES_BLOCK`, both version
strings — zero differences); gate green: `ruff check .` ok · `mypy .` (227 files) ok · `pytest` 1391
passed. No eval run (provably prompt-inert).

### Kit-adoption Phase 1 — Pydantic-aware mypy (`chore/kit-phase1-pydantic-mypy`, 2026-06-23)

First implementation branch of the agent-coding-practices kit-adoption arc (kit-adoption-design.md §4
Phase 1; owner-selected "lint+typing wins, defer format" subset). Tooling-config only — **no product
code, dependency, prompt, route, or version change**; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched.

**Changed**
- `pyproject.toml` `[tool.mypy]`: enabled the `pydantic.mypy` plugin so mypy understands the analyzer
  Pydantic response models' generated `__init__`/validator signatures. The plugin ships inside the
  already-present `pydantic` dependency — **no new dependency**. mypy stays green ("no issues found in
  227 source files").

**Notes — two Phase-1 items evaluated and rejected for this codebase (recorded in
`docs/dev/kit-adoption-design.md` §4):**
- **ruff `ERA` (commented-out-code) NOT enabled** — all 8 `ERA001` hits are false positives on
  legitimate documentation prose (JSON-shape examples, TypedDict shape docs, `# Section (name)`
  dividers). This is the case Decision 6 (KIT-6) marks *warn-only forever*; enabling it blocking would
  clutter docs and block future prose comments, with no advisory lane until the 8.7 pre-commit core.
- **SQLAlchemy mypy plugin NOT enabled** — `db/models.py` uses native SQLAlchemy 2.0 typing
  (`DeclarativeBase` + `Mapped[...]` + `mapped_column`), for which `sqlalchemy.ext.mypy.plugin` is
  deprecated/unneeded.

Deferred to their own Phase-1 branches: `ruff format` (161-file restyle) and `SIM`/`RUF` per-family triage.

### Agent-coding-practices kit-adoption — evaluation + planning record (`docs/kit-adoption-arc`, 2026-06-23)

Docs-only. Persisted the settled evaluation of the lichen `agent-coding-practices-kit` handoff
(8 decisions; full faithful adoption, "implement + flag promotable") so it doesn't live only in
the session. **No code, config, dependency, or version change** — this is the planning record;
the implementation phases are scheduled separately and thread `feat/portable-enforcement-core`
(8.7) + WS-2-full.

**Added**
- `docs/dev/kit-adoption-design.md` — canonical evaluation, the 8 decisions + rationale, the
  5-phase sequenced arc, the temporal map, and the strict-ratchet exit criterion.
- `docs/dev/decisions.md` — a thin architectural-decision index (one line + pointer per
  decision), seeded with the 8 kit decisions + the enforcement-portability SPLIT backfill.

**Changed**
- `docs/dev/RELEASE_ARC.md` — recurring workstreams: tied WS-2-full to the arc + added the
  kit-adoption workstream bullet.
- `docs/dev/RELEASE_CHECKLIST.md` — folded the kit's gates + skills/hooks coherence into the 8.7
  `feat/portable-enforcement-core` item; added one Carry-forward ledger row for the staged
  commitments (open count 8 → 9).

### v1.0.8 correction sprint — cover-letter tone (`fix/window-findings-tone`, Sprint 8.6, PV-3)

The second 8.6 sub-branch: **PV-3 cover-letter tone tune** — the only `PROMPT_VERSION`-bumping
change in the v1.0.7/v1.0.8 epics. Reinforces the existing throat-clearing/hedging bans (the
v1.0.3 `tone` lapse was an *adherence* slip, not a missing rule) via the project's standard
mechanism — a worked OK/NOT-OK example. `AVATAR_PROMPT_VERSION` untouched; no new dependency.

**Changed**
- `analyzer.py` `_COVER_LETTER_RULES_BLOCK`: de-cloned the single STRUCTURE-Para-3 close example
  (the model was copying `"I'd welcome a direct conversation about what this team is building."`
  near-verbatim into the documented lapse) — replaced with a functional description of the close's
  job (concrete topic / timing signal / scheduling line; implies initiative, never polite waiting).
- `PROMPT_VERSION` `2026-06-13.1` → `2026-06-23.1` (same commit).

**Added**
- `analyzer.py` `_COVER_LETTER_RULES_BLOCK`: a `WORKED EXAMPLES` sub-block — OK / NOT-OK pairs for
  the cover-letter **opener** and **close**, the two surfaces the v1.0.3 lapse hit.
- `tests/test_corpus_mode_prompt.py::TestCoverLetterWorkedExamples` — deterministic ($0) assertions
  that the worked-example scaffold is present and wired into the generate prompt when
  `with_cover_letter=True`, absent when `False`.

**Fixed**
- `evals/runner.py`: the **EV-3-class cp1252 console crash** the 8.6 grounding fix didn't cover —
  `--help` (the `→` epilog) and any `→` print raised `UnicodeEncodeError` under a Windows cp1252
  console. Added the same `sys.stdout`/`sys.stderr.reconfigure(encoding="utf-8")` loop at
  `runner.main()` entry (mirrors `scripts/export_corpus_seed.py` + `capture_screenshots.py`); verified
  exit 0 plain and under forced `PYTHONIOENCODING=cp1252`. Surfaced during the PV-3 validation;
  owner-directed fold-in before the merge.

**Validation** — paired before/after `--suite synthetic --subset full`, n=3 each side: **tone holds
at the 4.2 floor with no regression on any rubric**; the opener/close fix is judge-confirmed adopted
(substance-first opener + concrete close). One sub-4.0 after-sample (pm 3.2) was a scenario-specific
gap-admission hedge, a *different* tone failure mode than PV-3 targeted. Detail + tables:
[`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) (2026-06-23 PV-3 entry). Gate: ruff · mypy (227) ·
pytest **1391** incl. `-m ux`.

### v1.0.8 correction sprint — grounding slice (`fix/window-findings-grounding`, Sprint 8.6)

The first 8.6 sub-branch burns the **grounding slice** of the
[`window-8.5-findings.md`](docs/dev/window-8.5-findings.md) backlog (EV-1/EV-2/EV-3 + S3-1).
**Eval/dev tooling only — no product-behavior change**; `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched. PV-3 cover-letter tone is a sibling branch; the
`/wiki-ingest` re-anchor folds into 8.6a. PV-1 labels + PV-2 calibration are staged
(owner-gated, may spill to v1.0.9).

**Changed**
- `pyproject.toml` (`eval-grounding` extra): **pinned `minicheck`** to commit
  `b58b9fa69acbd1015ec970fa65dd752413a053d2` (was an unpinned `git+` ref that drifted to a
  vLLM/Bespoke-7B rewrite — EV-1, HIGH) and **widened the `transformers` cap** `>=4.40,<5.0`
  → `>=4.40,<6.0` (the `<5.0` pin was already being violated by a fresh install; validated on
  5.10.2). The CPU `flan-t5-large` scorer was re-validated end-to-end (NLI mean 0.995,
  MiniCheck mean 0.973).

**Added**
- `pyproject.toml` (`eval-grounding` extra): **`accelerate>=1.0`** (required by
  `transformers>=5` for the `device_map="auto"` the MiniCheck loader uses) and **`nltk>=3.9`**
  (declared directly — `evals/grounding_signals.py` now ensures its `punkt_tab` data).
- `scripts/build_vector_index.py`: a `manifest.json` (`built_at_sha`) written on build + a
  `--check` staleness mode (manifest sha vs HEAD) so the gitignored vector index can no longer
  silently stale after a refactor moves code (S3-1). Local `--full` rebuild re-anchored the
  index onto `blueprints/**`.

**Fixed**
- **EV-1** — the L2/MiniCheck grounding scorer no longer crashes: dropped the removed `device`
  kwarg in `evals/grounding_signals.py` and auto-ensure NLTK `punkt_tab` before scoring. (The
  finding's "dropped `flan-t5-large`/`score()`-shape" root cause was inaccurate — corrected in
  the findings doc; the real breaks were `device` + the `accelerate`/`punkt_tab` deps.)
- **EV-2** — `evals/bootstrap.py:build_bootstrap_document` wraps the optional `grounding_fn`
  call in `try/except` (log + `grounding=None` + still return the doc), so a grounding scorer
  failure never discards the completed (paid) analyze/clarify/generate work. The browser
  bootstrap route (`blueprints/diagnostics.py`) reconciled to a single outcome-derived note.
- **EV-3** — `scripts/export_corpus_seed.py` + `scripts/capture_screenshots.py` reconfigure
  `stdout`/`stderr` to UTF-8 at entry, so the unicode in their progress output and `--help`
  text no longer `UnicodeEncodeError`s on a Windows cp1252 console (the export previously
  exited non-zero *after* the seed had written).

### v1.0.8 gated test window — eval half (`eval/live-shakedown-labels`, Sprint 8.5)

The first run of the real-data eval/tuning loop on the decomposed code, plus the S3
gate-override validation owed since v1.0.7. **No product-behavior change** — the only new
code is eval/test apparatus; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched, no
dependency or migration. The window's *purpose* — surfacing so-far-unexercised
integration issues — is met; the issues themselves are triaged into a findings backlog
that the 8.6 correction sprint burns.

**Added**
- `scripts/vector_before_after_eval.py` — a judge-scored **before/after relevance eval**
  for the S3 vector tier (the gate-override validation the 7.6 override owed). Runs a
  dev-vocab question set through `recall.assemble` with the lexical tiers vs +S3 and scores
  each set's relevance with the Haiku eval-judge (reuses `evals.runner._grade`, so no
  egress-allowlist change; retrieval corpus = committed wiki+code, no PII). **Verdict:
  KEEP** — mean relevance 1.12 → 2.58 (+1.46); the `numpy`+`model2vec` footprint earns its
  keep. See `evals/TUNING_LOG.md` (2026-06-23) + `docs/dev/window-8.5-findings.md`.
- `docs/dev/window-8.5-findings.md` — the one numbered findings backlog (EV-1 minicheck
  unpinned-git-dep drift · EV-2 grounding-abort discards work · EV-3 seed-export unicode
  crash · S3-1 stale vector index) the 8.6 sprint consumes.
- `docs/dev/window-8.5-walkthrough.md` — the E2E walkthrough runbook (R2-live + post-split
  route surface + assistant + diagnostics) for the deferred walkthrough half.

**Fixed**
- The recurring flaky Compose-wizard UX race (Carry-forward ledger #3, ≥3 members) —
  **test-only**: `ui_pages/wizard_compose.py:_wait_loaded()` now settles on
  `.compose-experience-card` (always rendered) instead of `.compose-row.recommended`
  (absent on no-recommendations fixtures = the race). 20/20 loop, zero flakes.

**Deferred to 8.6 (owner-decided 2026-06-23)** — PV-1 label production (blocked on EV-1:
fix minicheck first, then one full L0+L1+L2 annotation pass) and the E2E walkthrough +
R2-live verification (run against `main`).

### Added — KEEP-ledger do-not-regress guard tests (`test/keep-ledger-guards`, Sprint 8.4, PX-29)

The load-bearing security / PII / accessibility / governance KEEP affirmations from
the 2026-06 product-excellence review (cross-referenced from
[`docs/dev/keep-ledger.md`](docs/dev/keep-ledger.md) → the findings register) are now
committed **guard tests** asserting the **final post-blueprint-split layout**, so
neither the split nor the v1.1.0 public tag can quietly weaken them. They reuse the
existing AST-gate precedents (`tests/test_egress_allowlist.py` reviewed-allowlist +
`tests/test_construction_boundary.py` AST-walk). **No prompt / dependency / migration**
— `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

- **F-sec-05 route containment** — `tests/test_route_containment_gate.py` AST-walks
  every `blueprints/**.py` route and asserts every filesystem-touching route carries
  `_within` (containment) + `_safe_username` (user-scoping), with two reviewed,
  reasoned exemption registries: `WITHIN_NOT_REQUIRED` (containment delegated to a
  sanitizing helper, or a fixed / sanitized-only path) and `SAFE_USERNAME_NOT_REQUIRED`
  (no `<username>` to verify). Each registry waives exactly one guard, so a no-username
  download that loses `_within`, or an exemption that later gains its guard, still
  fails. Detection is docstring/comment-free (per-statement `ast.unparse`) and
  call-form (`_within(` / `_safe_username(`), so a guard named only in prose never trips
  it. This commits the `route-security-lint` hook's intent over the **whole** tree (the
  hook scans only the Edit diff), closing the WATCH rider the review flagged.
- **F-sec-06 zero-PII clone** — `tests/test_zero_pii_clone.py` generalizes the
  `configs/`-only `git ls-files` check to the whole PII/secret surface (configs /
  resumes / output / personas / `evals/fixtures/real` / db / logs track only synthetic
  fixtures), asserts no secret-shaped file is tracked, scans tracked text files for the
  `sk-ant-…` API-key shape (self-safe assembled pattern), and pins the load-bearing
  `.gitignore` lines so a future "tidy" can't silently un-ignore real data.
- **F-expa11y-07 / F-expa11y-08 a11y floor** — `tests/test_a11y_floor_guards.py`
  (always-runs static scan: the `#srAnnounce` polite/atomic live region + the
  `_announce()` helper + its ≥7 success call sites; the keyboard reorder
  buttons/aria-labels/`_moveBulletRow`) + `tests/ux/a11y/test_announce_live_region.py`
  (Chromium-gated: drives analyze→completion and asserts the live region receives the
  announcement). The review had flagged `_announce()` as "no test guards it."
- **F-gov-04 hook witness/blocker split** — `tests/test_governance_hooks_gate.py` pins
  the 7 enforced blockers (reachable `exit 2`) and 3 witnesses (never `exit 2`) as named
  frozensets and cross-checks the `.claude/settings.json` wiring (blockers → PreToolUse,
  witnesses → PostToolUse).

### Changed — route-containment drift closed (3 behavior-identical hardenings, Sprint 8.4)

Restoring the `_within` containment guard the route-containment gate requires, after
the 8.3 blueprint split's body-only move-edits had silently dropped it from two routes
(the F-sec-05 WATCH rider). **All three are behavior-identical** (verified green under
the existing route tests):

- `upload_resume` / `list_resumes` (`blueprints/corpus/curation.py`) gain a redundant
  `_within(…, RESUMES_DIR)` — always-True today because the path is built only from
  `secure_filename` / `_safe_username`-sanitized parts (belt-and-suspenders).
- `download_file` (`blueprints/generation.py`) replaces its inline
  `full_path.resolve().relative_to(OUTPUT_DIR.resolve())` containment check with the
  canonical `_within(full_path, OUTPUT_DIR)` (a literal extraction — `_within`'s body
  *is* that check).
- Doc accuracy: `AGENTS.md` now states `route-security-lint` covers `app.py` +
  `blueprints/**.py` (the PX-21 widen) and names the committed gate.

### Changed — diagnostics blueprint seam — the last seam, app.py → zero routes (`refactor/app-blueprints-diagnostics`, Sprint 8.3h)

The seventh and **final** domain seam of the v1.0.8 `app.py`→blueprints
decomposition. The 9 diagnostics routes (annotation / bootstrap / eval / tune — the
localhost dev-console write/SSE backend) moved out of `app.py` to a new single-module
`blueprints/diagnostics.py`, after which **`app.py` carries zero `@app.route`
handlers** and is the thin composition root (factory + WSGI handle + `main()`). **No
behavior change** — every URL / method / request / response is byte-identical; **no
prompt / dependency / migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`
untouched.

- **9 routes → `blueprints/diagnostics.py`** (registered with **no `url_prefix`** →
  all 9 URLs byte-identical, verified by an `app.url_map` path+methods diff: 96 rules
  unchanged, only the 9 endpoints gain a `diagnostics.` prefix): `annotation_fixtures`
  · `annotation_load` · `annotation_save` · `annotation_collate` ·
  `annotation_score_grounding` (SSE) · `annotation_seed_export` ·
  `annotation_bootstrap_stream` (SSE) · `eval_run_stream` (SSE) · `tune_run_stream`
  (SSE). The 4 diagnostics-only domain helpers moved with them
  (`_annotation_fixture_path`, `_load_bootstrap_doc`, `_write_seed_json`,
  `_patch_annotation_scores`); `_annotation_fixture_path` is now **pure** (takes its
  `annotation_root` explicitly rather than reading a module global). Bodies read
  `current_app.config["ANNOTATION_ROOT"]` / `["CONFIGS_DIR"]` and import the shared
  `web_infra` helpers; PV-4 `-> ResponseReturnValue` on every route. The 5 SSE routes
  keep the established pattern (config captured as a local **before** the `stream()`
  generator, which never touches `current_app`).
- **The transitional `app.py`-local block retired (zero-debt completion).** With the
  last routes gone, the local helper copies (`_safe_username` / `_load_config` /
  `_save_config` / `_get_or_provision_candidate`) and the module path globals
  (`BASE_DIR` / `CONFIGS_DIR` / `RESUMES_DIR` / `OUTPUT_DIR` / `ANNOTATION_ROOT` /
  `ALLOWED_EXTENSIONS`) — kept since 8.3a's "Option X" for the not-yet-moved routes —
  were deleted; the orphaned imports were pruned. `_should_open_browser` stays
  (`tests/test_browser_open.py` imports it; `main()` calls it).
- **Egress unchanged.** `blueprints/diagnostics.py` imports no `anthropic` — the routes
  catch only generic `Exception` and delegate the paid work to `evals.runner` /
  `evals.bootstrap` / `evals.grounding_signals` (already allowlisted) and the
  `web_infra` client factory — so it is **not** added to the egress allowlist, and
  `app.py` stays off it.
- **Tests migrated, no module-global monkeypatch left for the seam.**
  `tests/test_annotation_routes.py` builds a `create_app(Config(base_dir=tmp))` app
  (DB-path monkeypatch kept; the containment helpers exposed via a `SimpleNamespace` so
  the bodies are unchanged). `tests/test_app_security.py`'s three helper-test classes
  (`TestSafeUsername` / `TestWithin` / `TestConfigHelperContainment`) retarget to the
  canonical `web_infra` helpers. The UX harness drops the now-dead module-global
  monkeypatch and injects `ANNOTATION_ROOT` onto the live app config; `tests/ux/`
  (`conftest.py` / `seeding.py` / `stubs.py` / `flows/test_annotation_tab.py` / the
  education-diagnostics regression) read paths from `app.config` and stub
  `_get_client` on `blueprints.diagnostics`.
- **Definition-of-done:** the v1.0.8 `app.py`→blueprints decomposition is **complete**
  — all 93 routes live on a domain blueprint, `app.py` has zero routes / no path
  globals / no per-request helpers, and no moved seam relies on a module-global
  monkeypatch.

### Fixed — docs/test hygiene (`chore/ledger-reduction`, Sprint 8.0)

The v1.0.8 epic opens with a contained reduction micro-branch (run before the blueprint
refactor) that clears two carry-forward ledger items. **No code/prompt change** —
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched, no new dependency, no migration.

- **`CONTRIBUTING.md` plugin-section drift corrected.** "Working with the Claude Code plugin"
  described the pre-Sprint-7.1 layout (`.claude-plugin/` "holds the project's commands, agents,
  and hook scripts", plus stale "Step 5 / 8 / 9 of the OSS migration" references). It now
  documents the actual layout — commands/subagents in the repo-root `commands/` / `agents/`
  loading namespaced via the local `sartor-tools` marketplace; only hooks + manifest +
  marketplace in `.claude-plugin/` — and points to README → Claude Code Plugin for the full
  catalog instead of re-listing entries.
- **pytest-socket `UserWarning ×2` silenced.** Added one message-scoped `filterwarnings` ignore
  (`pyproject.toml` `[tool.pytest.ini_options]`) for the egress-allowlist suite's expected
  socket-block warning, so gate runs no longer report 2 benign warnings. Scoped to the exact
  message; the socket block itself is unchanged.

### Added — blueprint-decomposition design (`design/app-blueprints`, Sprint 8.1)

The design session that resolves the v1.0.8 `app.py`→blueprints architecture **with the
owner**, before any route moves. Read-only investigation of the monolith; **no code/route/
prompt change** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched, no dependency, no
migration.

- **New design doc [`docs/dev/app-blueprints-design.md`](docs/dev/app-blueprints-design.md)** —
  records the locked decisions, the full 93-route→8-seam map, the SSE handling, the
  test-harness migration, the hook/gate sequencing (PX-19/20/21/22/29, PV-4), and an explicit
  **zero-tech-debt definition-of-done** for the epic (owner bar: minimum tech debt at v1.1.0).
- **Owner decisions locked (2026-06-21):** *Crafted* architecture — a `create_app(config)`
  application-factory (retained module-level `app = create_app()` WSGI handle) + a typed
  injected `Config` + a shared web-infra package both `app.py` and every blueprint import; and
  **8 domain seams** (analysis · generation · corpus · templates/personas · applications ·
  users/config · diagnostics · assistant), splitting the user-facing tracker from the dev
  diagnostics backend.
- `RELEASE_ARC.md` §Phase 4.8 + `RELEASE_CHECKLIST.md` items 8.1/8.2/8.3 updated to record the
  resolution and the refined branch sequence (an 8.3a `refactor/app-factory-and-infra`
  foundation branch precedes the seam moves).

### Security — route-security-lint widen + config-helper containment (`refactor/route-security-lint-widen`, Sprint 8.2)

The hardening branch that **leads** the v1.0.8 blueprint refactor (PX-21): the route-security
lint hook is widened to cover blueprint route modules *before* any route leaves `app.py`, and
the two config helpers' path-traversal gap is closed at the helper. **No behavior change for
valid users; no prompt/dependency/migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`
untouched.

- **`route-security-lint` hook widened past `app.py`.** The file matcher now also covers
  `blueprints/**.py` (any depth — a future `blueprints/corpus/*.py` sub-package is included);
  the route detector catches blueprint decorators (`@<bp>.route/.get/.post/.put/.delete/.patch`,
  the leading `@` keeping ordinary `data.get(` from false-matching); and `send_from_directory(`
  joins the filesystem-access markers. The read-only localhost `dashboard/` surface is
  **deliberately excluded** (its routes take no `<username>` and read fixed diagnostic dirs).
  Hand-verified across a 10-case exit-code matrix. The hook stays a self-contained bash script
  (migration-friendly for the 8.7 portable-enforcement-core lift).
- **`_load_config` / `_save_config` containment closed at the helper.** Both now sanitize the
  username via `secure_filename` *inside* the helper, so containment to `CONFIGS_DIR` holds even
  for a raw caller — not only at the call site (PX-21). `get_config` / `update_config` (the two
  raw-input routes) gain a `secure_filename`-non-empty → `400` guard (the `create_user` pattern),
  so a nonsense username is rejected cleanly instead of 500-ing. `secure_filename` is idempotent
  on already-safe names → existing users resolve to the same file.
- **`SECURITY.md` scoped** to the post-split layout — the hook-coverage claims now read `app.py`
  + `blueprints/` (with the `dashboard/` exclusion noted), plus a note that config filenames are
  canonicalized through `secure_filename` (`josé` → `jose`). The `app.debug` 5xx-gate passage is
  left HEAD-accurate (its `current_app.debug` re-cite lands in 8.3a, when `_error_detail_payload`
  moves to the web-infra package).
- **Tests.** `tests/test_app_security.py` gains `TestConfigHelperContainment` +
  `TestConfigRouteContainment`; the helper-level cases are the real proof — an encoded-slash
  route request is werkzeug-404'd before the handler, so that case asserts *routing* rejection,
  not helper containment.

### Changed — application factory + shared web-infra package (`refactor/app-factory-and-infra`, Sprint 8.3a)

The **foundation** branch of the `app.py`→blueprints decomposition (no route moves; the 8
domain seams are 8.3b–h). `app.py` becomes a `create_app(config)` factory over a typed
injected `Config`, and the cross-cutting helpers move to a shared leaf `web_infra/` package
both `app.py` and the blueprints import. **Pure refactor — every route's URL/method/request/
response is byte-identical; no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **Application factory.** New `create_app(config: Config | None = None)` is the composition
  root: it pushes the config, runs the directory-creation (the old import-time `mkdir` loop),
  and registers the blueprints. The module-level `app = create_app()` WSGI / console-script
  handle is retained. `main()` + `_should_open_browser` stay in `app.py`.
- **Typed `Config` (new top-level `config.py`).** Replaces the eight module-global path
  constants + `ALLOWED_EXTENSIONS` + the bind host; `Config(base_dir=...)` re-points every
  derived directory off one root. `ensure_dirs()` is byte-identical to the retired loop
  (configs/resumes/output only — annotation_root/personas stay lazily created).
- **Shared `web_infra/` package (new).** Six fixed groups — `security` (`_safe_username` /
  `_within`), `http` (`_sse` / `_error_detail_payload`), `clients` (`_get_client`), `config_io`
  (`_load_config` / `_save_config`), `provisioning` (`_get_or_provision_candidate`),
  `request_gates` (`_is_localhost_request`). It is leaf infrastructure — it never imports
  `app.py`, a blueprint, or `config.py` (enforced by `tests/test_web_infra_is_leaf.py`).
  `_error_detail_payload` now reads `current_app.debug` (same flag, behavior-identical).
- **Dedup.** `blueprints/assistant.py` deletes its duplicated `_safe_username` / `_get_client`
  / `_sse` and imports them from `web_infra/`; `dashboard/routes.py` consumes the shared
  `_is_localhost_request` rather than a third loopback copy.
- **`onboarding/corpus_import.py` second front folded in.** `_safe_load_config` /
  `import_candidate_from_config` take an explicit, defaulted `configs_dir` (additive — the CLI
  + legacy tests are unaffected); the app reaches them via `web_infra._get_or_provision_candidate`,
  which threads `current_app.config["CONFIGS_DIR"]`.
- **PX-19 — loopback bind.** `app.run(...)` now binds `host="127.0.0.1"` from `Config.host`;
  `SERVER_NAME` noted as a third silent-flip vector.
- **PX-20 — construction boundary gate.** New `tests/test_construction_boundary.py` fails if any
  deterministic module (`hardening` / `parser` / `generator` / `scraper` / `json_resume` /
  `corpus_to_json_resume` / `pdf_render`) imports `analyzer` or `anthropic` (charter C-6, by
  construction not review).
- **Tests.** New `tests/test_config.py`, `tests/test_web_infra.py`, `tests/test_web_infra_is_leaf.py`;
  `tests/conftest.py` gains the canonical `app` / `client` factory fixtures; `tests/test_assistant_route.py`
  migrates onto them; `web_infra/clients.py` added to the egress allowlist. The remaining
  module-global monkeypatch test pattern is **intentionally retained** — those seam tests migrate
  with their routes in 8.3b–h (the zero-tech-debt DoD is measured at the v1.1.0 tag).

### Changed — analysis blueprint seam (`refactor/app-blueprints-analysis`, Sprint 8.3b)

The **first domain seam** moved out of the `app.py` monolith. The five analysis routes leave
`app.py` for a new `blueprints/analysis.py`. **Pure refactor — every route's URL/method/request/
response is byte-identical; no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/analysis.py`.** `POST /api/analyze`, `POST /api/analyze/stream` (SSE),
  `POST /api/clarify`, `POST /api/answer-clarifications`, `POST /api/iterate-clarify` — plus
  their three analysis-only domain helpers (`_run_analysis_corpus_backed`,
  `_run_analysis_corpus_backed_streaming`, `_persist_clarifications_to_memory`). Registered with
  **no `url_prefix`** (full-path decorators) so the URLs stay identical; the blueprint never
  imports `app.py`.
- **Reads config via `current_app`.** Route/helper bodies take their paths from
  `current_app.config["OUTPUT_DIR"]` / `["CONFIGS_DIR"]` and use the shared `web_infra` helpers
  (`_safe_username` / `_within` / `_get_client` / `_sse` / `_get_or_provision_candidate`,
  threading `configs_dir=current_app.config["CONFIGS_DIR"]`). The SSE helper captures the output
  dir as a local **before** the generator, so `stream()` never touches `current_app` (no
  `stream_with_context` needed — matches `blueprints/assistant.py`).
- **PV-4 typing.** Every moved route and the two corpus-backed helpers are annotated
  `-> ResponseReturnValue` (which also fixed one latent `clarification_questions` TypedDict
  imprecision the untyped monolith body had skipped). `blueprints/analysis.py` added to the
  egress allowlist (it catches `anthropic` error types).
- **Tests migrate onto the factory fixture.** `tests/test_app_clarify.py` and
  `tests/test_app_corpus_backed.py` drop the module-global monkeypatch + `importlib.reload` for
  `create_app(Config(base_dir=tmp_path))`, stubbing the analyzer functions on the blueprint
  module; the iterate-clarify tests relocate to a new `tests/test_app_iterate_clarify.py` on the
  same fixture (seeding the iteration≥1 context directly, so they no longer depend on the
  still-in-`app.py` `/api/generate`). The UX harness injects the moved routes' config onto the
  live app and retargets `install_llm_stubs` to `blueprints.analysis`. `app.py` keeps its
  module-global constants + config-dependent helper copies for the un-moved seams (they retire in
  8.3c–h).

### Changed — generation blueprint seam (`refactor/app-blueprints-generation`, Sprint 8.3c)

The **second domain seam** moved out of the `app.py` monolith. The seven generation routes leave
`app.py` for a new `blueprints/generation.py`. **Pure refactor — every route's URL/method/request/
response is byte-identical; no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/generation.py`.** `POST /api/save-edits`, `POST /api/generate`,
  `POST /api/generate/stream` (SSE), `POST /api/validate-refinement`,
  `POST /api/generate-cover-letter`, `GET /api/download/<path:filepath>`,
  `POST /api/download-edited` — plus their generation-only domain helpers
  (`_check_date_grounding`, `_persist_run_persona`, `_persist_cover_letter_to_db`,
  `_persist_corpus_generation_to_db`, and the composition-application trio
  `_apply_chosen_summary` / `_apply_chosen_experience_summaries` / `_apply_recommended_skills`).
  Registered with **no `url_prefix`** (full-path decorators) so the URLs stay identical; the
  blueprint never imports `app.py`.
- **Cross-seam helper bridge (owner decision).** Three generation routes resolve a persona
  template via `_resolve_persona_template_path` / `_resolve_default_persona_template_path`, which
  belong to the **templates/personas** seam (8.3e) and are still called by the persona-preview
  routes in `app.py`. Since a blueprint cannot import `app.py`, this pair is carried in
  `blueprints/generation.py` as a clearly-commented **transitional duplicate** (canonical copies
  stay in `app.py`); it is deduplicated when the templates seam lands at 8.3e (generation will then
  import it). Tracked in the Carry-forward ledger. The `_apply_*` trio — generation's sole callers
  today, grouped with the applications seam by the 8.1 design — moves here outright (no dead code);
  revisited at 8.3f if an applications route grows a caller.
- **Reads config via `current_app`.** Route/helper bodies take paths from
  `current_app.config["OUTPUT_DIR"]` / `["CONFIGS_DIR"]` / `["RESUMES_DIR"]` / `["BASE_DIR"]` /
  `["PERSONAS_DIR"]` and use the shared `web_infra` helpers (`_safe_username` / `_within` /
  `_get_client` / `_sse`, threading `configs_dir=current_app.config["CONFIGS_DIR"]`). The streaming
  route captures `output_dir` as a local **before** the generator, so `stream()` never touches
  `current_app`. `download_file`'s inline containment guard is preserved byte-identically.
- **PV-4 typing.** Every moved route is annotated `-> ResponseReturnValue`. The loose
  `_apply_*(context_set: dict)` helpers (which read/write keys outside the `ContextSet` schema) are
  bridged at the call site with a runtime-noop `cast(dict, context_set)` so mypy's TypedDict→dict
  variance check passes without copying (the in-place mutations still land on the same object).
  `blueprints/generation.py` added to the egress allowlist (it catches `anthropic` error types).
- **Tests migrate onto the factory fixture.** `tests/test_app_iteration.py` and
  `tests/test_cover_letter_detached.py` drop the module-global monkeypatch + `importlib.reload` for
  `create_app(Config(base_dir=tmp_path))`, stubbing the generate functions on the blueprint module
  (keeping the distinct `db.session.DEFAULT_DB_PATH` monkeypatch + the lazy-imported
  `analyzer.generate_cover_letter_against_resume` stub). The three `_apply_*` unit tests
  (`test_apply_chosen_summary` / `test_experience_summary_composition` / `test_skill_composition`)
  retarget the moved helper to `blueprints.generation`. `test_persona_routes.py`'s `/api/download-edited`
  case gets live-app config injection (the persona seam's own fixture migrates at 8.3e). The UX
  harness retargets `install_llm_stubs` `generate_streaming` + `_get_client` to
  `blueprints.generation`. `app.py` keeps its module-global constants + config-dependent helper
  copies for the un-moved seams (they retire in 8.3d–h).

### Changed — corpus blueprint seam (`refactor/app-blueprints-corpus`, Sprint 8.3d)

The **third and largest domain seam** moved out of the `app.py` monolith: all **42 corpus
routes** leave `app.py` for a new `blueprints/corpus/` **sub-package**. **Pure refactor — every
route's URL/method/request/response is byte-identical (verified by an `app.url_map` path+methods
diff vs a pre-move baseline); no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/corpus/` sub-package (owner decision: 6 route files + shared layer).** One
  `corpus_bp = Blueprint("corpus", __name__)` (in `_bp.py`) with the route families split by
  entity: `experiences.py` (15 — experiences/bullets/titles/experience-summaries),
  `summaries.py` (4), `skills.py` (4), `tags.py` (7 + tag-mutation helpers), `curation.py`
  (9 — upload/resumes/duplicates/ingest/accept/pending + `_find_root`), `proposals.py`
  (3 — critique/decide/promote). Cross-cutting serializers live in `_shared.py`. Registered with
  **no `url_prefix`** (full-path decorators) so the URLs stay identical; the package never imports
  `app.py`.
- **Shared serializers `_tag_list` / `_skill_to_dict` (owner decision).** Both are corpus-domain
  serializers (design §3.4) but are also called by two still-resident *applications* routes
  (`get_application_composition`, `suggest_application_skills`, 8.3f). Since `app.py → blueprint`
  is the legal import direction, corpus owns the **canonical** copy in `_shared.py` and `app.py`
  imports them — **no transitional duplicate, no new carry-forward ledger item** (the inverse of
  8.3c's `_resolve_*` case, where the owning seam was in the future). The import relocates to
  `blueprints/applications` at 8.3f.
- **Reads config via `current_app`.** Every route/helper takes paths from
  `current_app.config["CONFIGS_DIR"]` / `["RESUMES_DIR"]` / `["OUTPUT_DIR"]` / `["ALLOWED_EXTENSIONS"]`
  and uses the shared `web_infra` helpers (`_safe_username` / `_within` / `_get_client` /
  `_get_or_provision_candidate` / `_load_config` / `_save_config`), threading
  `configs_dir=current_app.config["CONFIGS_DIR"]`. The `onboarding.corpus_import` "second
  monkeypatch front" retires for the migrated corpus tests: provisioning threads `configs_dir`
  through `web_infra._get_or_provision_candidate`, so the `corpus_import.CONFIGS_DIR` monkeypatch
  is gone.
- **PV-4 typing.** All 42 moved routes are annotated `-> ResponseReturnValue`; the
  `_get_or_provision_candidate` result is bridged with `cast("Candidate", …)` where `.id` is
  accessed, preserving byte-identical runtime behavior. `blueprints/corpus/proposals.py` is the one
  corpus submodule added to the egress allowlist (critique + promote catch `anthropic` error types);
  ingest delegates its Haiku call to `onboarding.corpus_import`, so `curation.py` imports no
  `anthropic`. `app.py` drops the now-unused top-level `from analyzer import LLMResponseError` (the
  remaining applications `recommend_*` routes import it locally); it keeps `import anthropic` and its
  allowlist entry (those routes still use it).
- **route-security-lint refinement (owner-authorized).** The hook's filesystem-indicator heuristic
  dropped `CONFIGS_DIR` from its match set: post-8.3a a route body only ever reaches `CONFIGS_DIR`
  via `_safe_username(configs_dir=…)` — which IS the containment guard — and the raw
  `CONFIGS_DIR / f"{u}.config"` construction `_within` protected was removed in PX-21. The
  FS-free corpus submodules (which reference `CONFIGS_DIR` only as that argument) were otherwise
  false-flagged for a missing `_within`. `OUTPUT_DIR`/`RESUMES_DIR`/`open(`/`Path(`/`send_file(`
  remain indicators, so upload/ingest/download still require `_within` (all three hook arms
  hand-verified).
- **Tests migrate onto the factory fixture.** The eight corpus test files drop the module-global
  monkeypatch + `importlib.reload` for `create_app(Config(base_dir=tmp_path))` (keeping the distinct
  `db.session.DEFAULT_DB_PATH` monkeypatch); the ingest/proposal `_get_client` patches retarget to
  `blueprints.corpus.curation` / `.proposals`; the analyzer-function patches are unchanged (the
  routes import them lazily from `analyzer`). `app.py` keeps its module-global constants +
  config-dependent helper copies for the remaining un-moved seams (templates/personas,
  applications, users/config, diagnostics — they retire in 8.3e–h).

### Changed — templates/personas blueprint seam + PX-22 wizard back-nav (`refactor/app-blueprints-templates`, Sprint 8.3e)

The **fourth domain seam** moved out of the `app.py` monolith: all **11 persona-template +
live-preview routes** leave `app.py` for a new `blueprints/templates.py`, the
`_resolve_persona_*` transitional duplicate 8.3c left in `blueprints/generation.py` is cleared,
and (owner-approved) the wizard gains browser Back/Forward navigation (PX-22). The route move is
a **pure refactor — every URL/method/request/response is byte-identical** (verified by an
`app.url_map` path+methods diff vs a pre-move baseline, 96 rules unchanged); **no
prompt/dependency/migration**, `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched. PX-22 is a
front-end behavior change only.

- **New `blueprints/templates.py` (single module, 11 routes).** `templates_bp =
  Blueprint("templates", __name__)`, registered with **no `url_prefix`** (full-path decorators):
  `list_bundled_personas` · `list_user_personas` · `upload_user_persona` · `get_persona` ·
  `update_persona` · `delete_persona` · `download_persona` · `preview_persona_with_resume` ·
  `preview_application_html` · `preview_cover_letter_html` · `preview_candidate_html`. The
  persona-only helpers move with the seam (`_persona_dict`/`_persona_dicts_safe`,
  `_preview_placeholder_html`, `_json_resume_has_content`, `_cover_letter_placeholder_html`,
  `_latest_generated_resume_md`, `_inline_persona_css`, `_inject_paged_polyfill` +
  `_PAGED_PREVIEW_INJECTION`). Reads paths from `current_app.config["PERSONAS_DIR"]` /
  `["BUNDLED_PERSONAS_DIR"]` / `["BASE_DIR"]` / `["OUTPUT_DIR"]` and the shared `web_infra` helpers
  (`_safe_username(configs_dir=…)` / `_within` / `_error_detail_payload` /
  `_get_or_provision_candidate`); the package never imports `app.py`. **LLM-free** — no
  `anthropic` reference, so the module is deliberately **not** on the egress allowlist. PV-4:
  every route annotated `-> ResponseReturnValue`; the provision result is bridged with
  `cast("Candidate", …)` where `.id` is read (byte-identical runtime behavior). The now-unused
  `PERSONAS_DIR` / `BUNDLED_PERSONAS_DIR` module globals + the `send_file` / `generate_resume`
  imports are dropped from `app.py` (`config.py` is the canonical home).
- **`_resolve_persona_*` duplicate cleared (carry-forward ledger item Resolved).**
  `_resolve_persona_template_path` / `_resolve_default_persona_template_path` now live **canonically**
  in `blueprints/templates.py`; the app.py copies and the 8.3c transitional copy in
  `blueprints/generation.py` are deleted, and `generation.py` imports the pair from
  `blueprints.templates` (sibling blueprint→blueprint import; templates never imports generation, so
  no cycle).
- **`_load_application_owned` transitional duplicate (new carry-forward ledger item).** The two
  application-preview routes need it, but it is owned by the *applications* seam (8.3f, still in
  `app.py` with ~10 callers). Mirroring the 8.3c decision, a clearly-commented transitional copy
  rides `blueprints/templates.py` (its one port: `_safe_username(configs_dir=current_app.config[…])`);
  it dedupes when the applications seam lands. Net ledger: item 2 Resolved, this added → unchanged.
- **PX-22 — browser Back/Forward traverse wizard steps (`static/app.js`).** `wizardGoTo` pushes a
  `{wizardStep}` `history` entry on each step change (`wizardInit` + the resume-from-prior landings
  stamp a `replaceState` baseline); a `popstate` listener restores the step (re-running its
  side-effects, never re-pushing). Two correctness fixes were required for Back to actually step the
  wizard rather than feel dead: (a) `_wizardPushHistory` **skips a duplicate** entry for the
  step already current (the Skip-to-Compose path navigates to step 3 twice); (b) the live-preview
  iframes load history-neutrally via `contentWindow.location.replace()` (a new `_loadPreviewFrame`
  helper) instead of `frame.src =`, so preview reloads on steps 4/6 don't pollute the joint session
  history. Scope is session-only (no address-bar `?step=N`, no deep-link-on-load).
- **Tests migrate onto the factory fixture.** `test_persona_routes.py`,
  `test_default_template_resolver.py`, and `test_live_preview_route.py` drop the module-global
  monkeypatch + `importlib.reload` (and the 8.3c `/api/download-edited` config-injection stopgap) for
  `create_app(Config(base_dir=tmp_path))` (keeping the `db.session.DEFAULT_DB_PATH` monkeypatch); the
  moved resolvers are invoked inside an app context. A new `pytest -m ux` regression
  (`test_20260622_wizard_back_nav.py`) drives the wizard forward, then asserts browser Back steps it
  backward and Forward restores it. The UX harness leaves `BASE_DIR`/`PERSONAS_DIR` at the real repo
  root (so bundled personas resolve) while injecting the tmp `CONFIGS_DIR`/`OUTPUT_DIR`.

### Changed — applications blueprint seam (`refactor/app-blueprints-applications`, Sprint 8.3f)

The **fifth domain seam** moved out of the `app.py` monolith: all **13 application-tracker +
per-application Compose routes** leave `app.py` for a new `blueprints/applications.py`. The route
move is a **pure refactor — every URL/method/request/response is byte-identical** (verified by an
`app.url_map` path+methods diff vs a pre-move baseline: 96 rules unchanged, only the 13 endpoint
*names* gained the `applications.` blueprint prefix). Two **owner-signed** clean-ups ride along
(below). **No prompt/dependency/migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/applications.py` (single module, 13 routes).** `applications_bp =
  Blueprint("applications", __name__)`, registered with **no `url_prefix`** (full-path decorators):
  `list_applications` · `get_application` · `update_application_status` · `update_application_notes` ·
  `update_application_meta` · `get_application_composition` · `save_application_composition` ·
  `recommend_application_bullets` · `recommend_application_summary` ·
  `recommend_application_experience_summaries` · `recommend_application_skills` ·
  `suggest_application_skills` · `list_clarifications` (the candidate-memory list — the design's
  ‡ "finalize at move time" route, owner-placed here). The applications-only helpers move with the
  seam (`_VALID_APP_STATUSES`, `_application_summary_dict`, `_build_resume_state`, `_parse_ats_status`,
  `_find_context_path_for_run`, `_latest_analysis_essentials`, and the seven `_read_*` context-override
  readers). Reads paths from `current_app.config["OUTPUT_DIR"]` / `["CONFIGS_DIR"]` and the shared
  `web_infra` helpers (`_safe_username(configs_dir=…)` / `_within` / `_error_detail_payload` /
  `_get_client`); the corpus serializers `_tag_list` / `_skill_to_dict` are imported from
  `blueprints.corpus` (the legal corpus→applications direction); the module never imports `app.py`.
  PV-4: every route annotated `-> ResponseReturnValue`.
- **Egress allowlist: `app.py` out, `blueprints/applications.py` in.** The five recommend/suggest
  routes carry the last `anthropic` error-type references in `app.py`; with them moved, `app.py` no
  longer imports `anthropic`, so its `import anthropic` is dropped and `app.py` is **removed** from
  `tests/test_egress_allowlist.py` (the gate asserts both directions — a listed non-importer is
  "allowlist rot"). `blueprints/applications.py` is added in its place.
- **`_load_application_owned` transitional duplicate cleared (carry-forward ledger item Resolved).**
  The helper is now **canonical** in `blueprints/applications.py`; the `app.py` copy and the 8.3e
  transitional copy in `blueprints/templates.py` are deleted, and `templates.py` imports it from
  `blueprints.applications` (sibling blueprint→blueprint import; applications never imports templates,
  so no cycle).
- **`list_resumes` raw-username hardening (owner-signed behavior tightening; carry-forward ledger item
  Resolved).** `GET /api/users/<username>/resumes` (in `blueprints/corpus/curation.py`) built its
  directory path from the **raw** route `username` without the `_safe_username` guard its sibling
  corpus routes use. It now calls `_safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])`
  and returns `400` for an unknown/unsafe user (matching `list_corpus_duplicates`). The only behavior
  change in the branch: a real selected user is unaffected; an unknown username is now rejected rather
  than reading an empty directory.
- **Tests migrate onto the factory fixture.** The application / composition / clarifications / recommend /
  suggest test files drop the module-global monkeypatch + `importlib.reload` for
  `create_app(Config(base_dir=tmp_path))` (keeping the `db.session.DEFAULT_DB_PATH` monkeypatch); the
  recommend/suggest `_get_client` stubs retarget to `blueprints.applications` (the analyzer
  `recommend_*`/`suggest_*` stubs stay on `analyzer`). The UX harness adds the
  `blueprints.applications._get_client` stub for the Compose recommend/suggest steps.

### Changed — users/config blueprint seam (`refactor/app-blueprints-users-config`, Sprint 8.3g)

The **sixth domain seam** moved out of the `app.py` monolith: all **6 users/config routes** leave
`app.py` for a new `blueprints/users.py`. The move is a **pure refactor — every URL/method/request/
response is byte-identical** (verified by an `app.url_map` path+methods diff vs a pre-move baseline:
96 rules unchanged, only the 6 endpoint *names* gained the `users.` blueprint prefix). **No prompt/
dependency/migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/users.py` (single module, 6 routes).** `users_bp = Blueprint("users", __name__)`,
  registered with **no `url_prefix`** (full-path decorators): `index` (the SPA shell) · `list_users` ·
  `create_user` · `get_config` · `update_config` · `fetch_profile` (the PX-02 opt-in profile scrape).
  Reads paths from `current_app.config["CONFIGS_DIR"]` / `["RESUMES_DIR"]` and the shared `web_infra`
  config-io / security / provisioning helpers (`_load_config(configs_dir=…)` / `_save_config(configs_dir=…)`
  / `_safe_username(configs_dir=…)` / `_within` / `_get_or_provision_candidate(configs_dir=…)`); the
  `db.session` + `scraper` imports stay lazy inside `fetch_profile`; the module never imports `app.py`.
  PV-4: every route annotated `-> ResponseReturnValue`. **LLM-free** — `fetch_profile`'s only egress is
  inside `scraper.py` (already allowlisted), so `blueprints/users.py` is **not** on the egress allowlist.
- **app.py.** `users_bp` registered in `register_blueprints()`; the 6 route bodies removed; the
  now-unused `make_response` / `render_template` / `validate_config` imports pruned. The app.py-local
  helper copies (`_safe_username` / `_load_config` / `_save_config` / `_get_or_provision_candidate`) and
  the `CONFIGS_DIR` / `RESUMES_DIR` globals are **kept** — the still-resident diagnostics routes use
  `_safe_username` + the globals; the whole local-helper block retires together at 8.3h when `app.py`
  has zero routes.
- **Second monkeypatch front retired for this seam.** `fetch_profile`'s provisioning chain
  (`_get_or_provision_candidate` → `import_candidate_from_config` → `_safe_load_config`) is fully
  `configs_dir`-parameterized in `web_infra/`, so the blueprint passes
  `current_app.config["CONFIGS_DIR"]` end-to-end and `tests/test_profile_fetch_route.py` **drops** its
  `onboarding.corpus_import.CONFIGS_DIR` monkeypatch (design §7 zero-debt).
- **Tests.** `test_profile_fetch_route.py` and the `TestConfigRouteContainment` class of
  `test_app_security.py` migrate from module-global monkeypatch + `importlib.reload` to
  `create_app(Config(base_dir=tmp_path))` (keeping the `db.session.DEFAULT_DB_PATH` monkeypatch; the
  `scraper.fetch_url_content` stub is unchanged). The helper-level classes (`TestSafeUsername` /
  `TestWithin` / `TestConfigHelperContainment`) stay on the `app_module` fixture — they test the
  app.py-local helpers that remain. New `tests/test_users_routes.py` adds the previously-absent
  `list_users` / `create_user` unit coverage (pinning the `RESUMES_DIR` config-key swap). The UX harness
  injects `RESUMES_DIR` onto the live app config so a new-user flow can't write into the real `resumes/`.

## [1.0.7] — 2026-06-20

### Changed — avatar citation/reference-format consistency (`feat/avatar-citation-format`, Sprint 7.8d)

Owner testing (2026-06-19) found the doc-grounded assistant's citations rendering
inconsistently — markdown links `[text](path)`, parentheticals, and numeric `[N]` markers
colliding in the same sentences, over a "Sources:" footer the `[N]` never resolved to. This
makes every reference **numbered, resolvable, and clickable**, and the footer **honest** (it
lists only what the answer actually cited). Tunes the **avatar only** — `AVATAR_PROMPT_VERSION`
bumps `2026-06-18.1` → `2026-06-19.1`; **`PROMPT_VERSION` is unchanged**. No new route, no new
dependency, no migration.

- **Numbered footnote citations (Scheme B).** `AVATAR_SYSTEM_PROMPT` (`analyzer.py`) now
  instructs the avatar to cite a claim with the **bracketed number** of the unit it rests on
  (`[1]`, `[2]`) at the end of the sentence — never a slug, a markdown link, or a URL — with
  worked OK/NOT-OK examples. The per-turn closer and the `<recalled_context>` renderer docstring
  match.
- **Cited-only, renumbered, resolving footer.** `avatar_answer_streaming`'s `done` payload now
  carries `citations` as a list of `{n, label, href}` for **only the units the answer cited**
  (a new `_resolve_cited` parses the emitted `[n]`, renumbers them consecutively in
  first-appearance order, and remaps the body) — so the footer can no longer overstate grounding
  and every marker resolves. A refusal that cites nothing shows "no sources cited." A stray
  `[[slug]]` the model occasionally mirrors into prose is normalized to plain text (never a real
  numbered cite, so it can't show as raw bracket-soup).
- **Clickable GitHub links.** Each citation links to its source on GitHub — wiki pages on `main`,
  code lines pinned to the unit's provenance `sha` (`_citation_href`). The model still never emits
  a URL (the no-URL invariant holds); the client builds the anchor from the citation.
- **Constrained inline markdown (`static/assistant.js`).** On completion the answer re-renders a
  tiny fixed subset — `` `inline code` ``, `**bold**`, and the `[n]` links — **XSS-safe by
  construction** (escape first, then introduce only fixed tags + a re-validated GitHub href). The
  numbered "Sources" key renders into a dedicated non-`aria-live` `#assistantSources` block; the
  polite status region keeps a short "Answer ready."
- **Tests (`tests/test_avatar_streaming.py`):** the deterministic LLM-free layer now covers href
  construction, cited-only + consecutive renumbering, out-of-range markers left literal, the
  empty refusal footer, and "every body `[n]` resolves / no `](` / no URL." Route + UX stubs move
  to the new `citations` shape and assert the rendered links.
- **Deferred (ledger):** an in-app rendered citation viewer — clickable links go to GitHub for
  now; an in-app viewer waits until friction warrants it (owner 2026-06-19).

### Fixed — assistant answers without a user selected (`fix/assistant-runs-without-user`, Sprint 7.8c)

The doc-grounded assistant no longer requires a user to be selected before it will
answer. Its answer is **project-global** — grounded in the committed wiki + code at
HEAD, identical for every user — so gating it behind user-selection was an artifact
of the per-user route pattern, and it blocked the assistant at exactly the first-run
moment ("how does sartor. work?") a brand-new visitor benefits from it most. Route +
client behavior only; no prompt, dependency, or migration change; `PROMPT_VERSION` and
`AVATAR_PROMPT_VERSION` unchanged.

- **Route (`blueprints/assistant.py`):** `POST /api/assistant/ask` now requires only a
  `question`. `username` is optional — `_safe_username`-validated only when supplied (a
  provided-but-unknown user is still a `400`), and absent → anonymous telemetry (`""`,
  already the `_call_llm_streaming` default). Retrieval and the answer are unchanged.
- **Client (`static/assistant.js`):** dropped the "Pick a user first, then ask." gate; the
  Ask button works with no user selected and sends an empty username.
- **Tests (`tests/test_assistant_route.py`):** the missing-username case now asserts a
  streamed anonymous `200` instead of a `400`; the missing-question and unknown-user `400`s
  are retained.
- **UX regression (`tests/ux/regression/test_20260619_assistant_no_user.py`):** drives the
  top-bar magnifier modal with **no user selected** and asserts the streamed cited answer
  renders end-to-end — the path the route test can't cover (the real `static/assistant.js`
  sending an empty username).

### Changed — avatar voice/tone & behavior tuning (`feat/avatar-voice-tone-tuning`)

Executes the voice/tone/behavior guidance package ([`docs/dev/avatar-voice-tone-guidance.md`](docs/dev/avatar-voice-tone-guidance.md))
against the live doc-grounded assistant. Tunes the **avatar only** — `AVATAR_PROMPT_VERSION`
bumps `2026-06-16.1` → `2026-06-18.1`; **`PROMPT_VERSION` is unchanged** (the avatar carries
its own version and is deliberately not in the résumé `_BASE_SYSTEM_PROMPTS` eval registry).
No new dependency, no migration.

- **Persona (`AVATAR_SYSTEM_PROMPT`, `analyzer.py`)** is now a *friendly, encouraging guide*
  — warmth delivered through helpfulness and a real next step, never cheer, flattery, or
  instructed wit. The prime directive is unchanged and made explicit: when voice and grounding
  conflict, grounding wins.
- **The refusal is now a doorway, not a dead end.** The exact string `"I don't have that in my
  docs."` is byte-unchanged, but the redirect to the nearest *cited* covered topic is now
  near-mandatory, and an in-domain-but-undocumented question is invited to be reported on the
  project's GitHub (the model states the behavior; the real link lives only in the UI).
- **New behavioral guardrails:** a calibrated-middle (answer the covered part, mark the gap),
  explicit anti-sycophancy / anti-over-promise (ATS-safety is described as *parseability*,
  never "reaches a human" or "improves your chances"), no performed honesty/empathy, and a
  connect-the-capability-to-the-concern move on reassurance-fishing instead of predicting outcomes.
- **Readable citations:** answers now read as natural sentences with the source in clean
  single square brackets at the end of the sentence (`[using-sartor]`, `[analyzer.py:49]`),
  rather than `[[…]]` mid-sentence — easier for non-technical readers. The "Sources:" footer
  strips the double brackets to match.
- **Microcopy (`templates/index.html`, `static/assistant.js`):** plain-languaged intro ("I show
  my sources"); a persistent empty state (scope/boundary line + verified example prompts) replacing
  the vanishing placeholder; blame-free transport-error copy kept distinct from the grounded
  refusal; and a real "report it on the project's GitHub" link.
- **Accessibility fix:** `#assistantAnswer` is no longer an `aria-live` region — streaming
  tokens into it announced the whole answer to screen readers on every chunk. It is now
  `aria-busy`-toggled and silent; the single completion announcement rides the `#assistantStatus`
  polite region.
- **Tests:** added LLM-free deterministic tone checks (`tests/test_avatar_streaming.py`) —
  refusal byte-sync across the two locations, the locked voice clauses, banned-phrase /
  over-promise / no-URL-in-output scanners, a cite-membership checker, the brand-mark sweep, and
  the answer-node-not-a-live-region assertion. Validated live against a Haiku spot-check matrix
  (the guide's §6.3); see [`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) 2026-06-18.

### Fixed — UI-polish trio (`fix/v107-ui-polish-trio`, Sprint 7.8b)

Three small, independent fixes from the v1.0.7 UI-polish band. No prompt,
dependency, or migration change; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION`
unchanged.

- **Stray browser windows (#1):** `python app.py` re-opened a browser window on
  every Flask debug-reloader restart, because the auto-open ran inside the
  serving child (`WERKZEUG_RUN_MAIN == "true"`) that the reloader re-executes on
  each reload — so editing files popped a new window each time ("5–6 windows per
  session"). A new pure `app._should_open_browser()` opens **exactly once** — in
  the persistent supervisor / non-debug single process, never in the reload
  child — and still honors `SARTOR_NO_BROWSER=1`.
- **Slow application load (#3):** selecting a user loaded the prior-applications
  list with `1 + 2N` SQL queries (lazy `Application.runs` per row + a per-app
  pending `ProposalReview` count), so it slowed as a user accrued applications.
  `GET /api/users/<u>/applications` now eager-loads runs with `selectinload` and
  batches the pending counts into one grouped query (~3 queries regardless of
  N). Output JSON and ordering unchanged; a regression test asserts the query
  count stays constant as the application count grows.
- **New-user form stale heading (#4):** with a user selected, clicking "New
  user" left the previous username in the `#userSelect` dropdown directly above
  the new-profile fields. `showNewUserForm()` now clears the dropdown (Cancel
  restores it). Front-end label fix only.

### Changed — assistant moved to a fixed top-bar icon + floating modal (`feat/assistant-topbar-modal`, Sprint 7.x)

A **front-end-only** relocation of the doc-grounded assistant so it is always findable in
the same place. No route, LLM, prompt, dependency, or migration change; `PROMPT_VERSION`
and `AVATAR_PROMPT_VERSION` unchanged.

- **Entry point** is now a fixed **magnifier icon** in the floating top bar (`#assistantPill`,
  left of Diagnostics) instead of an always-visible collapsible `<details>` panel parked
  below the wizard. The panel (`#panelAssistant`) is **removed** — one stable, discoverable
  entry point.
- **Presentation** is a **floating, scrollable modal** (`#assistantModal`) built on the
  existing `.cb-modal` skeleton (widened to ~680px; the `.cb-modal-body` internal scroll +
  90vh cap keep a long streamed answer scrollable under a pinned title + Close). The
  question box, Dev-mode toggle, streamed answer, and cited-sources line keep their element
  ids, so the SSE client (`static/assistant.js` `askAssistant()`) is unchanged; a new
  `openAssistantModal()` adds the open/close mechanics (focus-trap, Esc, backdrop,
  focus-restore, `aria-expanded`) mirroring `openDiagnosticsModal()`.
- **a11y:** `role="dialog"`/`aria-modal`, a static dialog title, `aria-haspopup`/
  `aria-controls`/`aria-expanded` on the icon button (explicit `aria-label`, since it has no
  visible text). Covered by the relocated UX regression (pill → modal → streamed cited
  answer) and a new open-state scan in the axe a11y gate.

### Documentation — accessibility status, Chromium reclassification, KEEP/BOOST ledger (`px/v107-band`, Sprint 7.8)

A docs-only PX band (no code, prompts, routes, deps, or migrations; `PROMPT_VERSION`
unchanged) clearing four v1.0.7 review prescriptions:

- **`ACCESSIBILITY.md`** (PX-18, `F-expa11y-03`): a new root-level **honest-status page**
  per the signed charter's E-2 — what is machine-checked (the vendored axe-core
  serious/critical gate, the keyboard "a11y floor" regression, the `_announce()`
  live-region, modal focus-trap/Escape/focus-return, the `--fg-2/3` WCAG-AA contrast
  retune) versus the **known gaps** (the UX/a11y tier isn't yet run in CI → PX-25;
  serious/critical-only; the Clarify/Output/cover-letter steps + modals + tab-order/
  reflow/history are unscanned; the bounded pre-public NVDA walkthrough hasn't run).
  **No conformance claim, no tag gate, no recurring-audit promise**; the v1.1.0 WCAG 2.2
  AA self-evaluation is stated as intent, not a present claim. Linked from the README doc map.
- **Chromium reclassified as PDF-output-only** (PX-31, `F-docs-05`): `docs/install.md`
  lifts the ~150 MB `playwright install chromium` step out of the base **Prerequisites**
  and gates it "optional — only for PDF output" in all three OS sequences; corrects the
  "renders every PDF and the live preview" claim — the in-browser preview is browser-side
  paged.js, **Chromium-free**; only PDF output needs the binary (`pdf_render.py` is the
  sole Playwright renderer; cf. `SECURITY.md` bundled-assets). README quick-install and the
  `pyproject.toml` playwright comment tightened to match.
- **`docs/dev/keep-ledger.md`** (PX-32): a new **eval/governance KEEP/BOOST do-not-regress
  ledger** — the non-polluting prompt-override A/B, the manual-promote/fail-closed
  annotation contract, the surfaced-uncalibrated L1/L2 state, the cost/consent-gated paid
  routes (**BOOST**), the witness-class hooks + read-only subagents, and the wiki
  grounding/sentinel/`@import` disciplines, each with its regression risk. `F-gov-08`
  (W-4 maturity signal) and `F-gov-10` (governance→assistant interface) logged as deferred
  design items. The **affirmation** half of the set the v1.0.8 split guards (PX-29) will test.
- **`docs/PRODUCT_SHAPE.md` R2 reconciled** (§10): the "stream `analyze()` output" entry,
  still listed as a v1.1 deferral, marked **shipped in v1.0.3** — consistent with the §10
  banner and the live `/api/analyze/stream` route.

### Added — the S3 vector tier for the assistant (`feat/doc-assistant-vector`, Sprint 7.6)

**Stage 2** of the Memory substrate: a static-embedding **semantic retrieval tier** that
finds the right code/doc when the question's words don't match the source's words — the
*vocabulary bridge* the lexical `git grep` (S2) tier misses. Built ahead of the formal
v1.0.8 labeled-eval gate **at owner direction** (the Stage-1 assistant tested too literal /
lacking semantic flexibility); the dependency add + the boundary-test relaxation are a
deliberate, documented gate-override (`docs/dev/RELEASE_ARC.md` §Phase 4.7).

- **`VectorSource` on the `recall/` `Source` protocol** ([`recall/sources/vector_source.py`](recall/sources/vector_source.py)):
  brute-force cosine over a rebuildable embedding sidecar. **Project-agnostic by
  construction** — the index dir, the **embedder** (`Callable[[Sequence[str]], ndarray]`),
  the audience resolver, and the document provider are all injected; the substrate never
  imports `model2vec`, so it stays embedder-agnostic + extractable. Build (`refresh`) and
  search are split: `refresh` re-embeds only chunks whose content changed (content-hash
  reuse → incremental, $0-on-unchanged); `search` loads the process-cached sidecar, embeds
  the query, returns top-k `path:line`-cited Units. No index → `[]` (graceful degradation).
  Re-exported from `recall`.
- **Wiring** ([`blueprints/assistant.py`](blueprints/assistant.py)): the `model2vec`
  embedder is built lazily + process-cached here (confined to the project layer); the
  vector tier joins the source list + `Tier.VECTOR` joins the scope **only when the model +
  index are both present** ("on when available"; no user-facing toggle). Runtime retrieval
  is fully local — no network.
- **Build step** ([`scripts/build_vector_index.py`](scripts/build_vector_index.py)):
  downloads the static model ONCE (~30MB — the single deliberate network step, like
  `playwright install chromium`) into the gitignored sidecar `db/vector_index/`, enumerates
  tracked code + docs, chunks + embeds, writes the index. `--full` cold-rebuilds. A probe
  ([`scripts/vector_index_probe.py`](scripts/vector_index_probe.py)) measures what the tier
  recovers over the lexical tiers (the gate-override evidence; logged in `evals/TUNING_LOG.md`).
- **New dependencies (hard):** `numpy` (the source's cosine + the `.npy` sidecar) and
  `model2vec` (the static embedder: numpy + tokenizers + safetensors — **no torch /
  onnxruntime**, the lightest semantic path). The `recall/` stdlib-only boundary test
  ([`tests/test_recall_boundary.py`](tests/test_recall_boundary.py)) is deliberately
  relaxed to admit **`numpy` in `recall/sources/` only** (core `recall/` stays stdlib-only;
  `model2vec` stays forbidden anywhere in `recall/`).
- **No migration; the vector index is a derived, rebuildable sidecar** (`db/vector_index/`,
  gitignored) — never `db/resume.sqlite` (it would inherit migrations + the corpus PII).
  Résumé `PROMPT_VERSION` unchanged (no prompt change). Unit tests use a fake numpy
  embedder, so the default `pytest` stays green with no model download.

### Added — the doc-grounded assistant (`feat/doc-assistant`, Sprint 7.5)

The **Stage 1** Memory capability: a working, **cited** chat over the committed
`docs/wiki/` + the code at HEAD — *"a product that knows itself."* It turns the Stage-0
`recall/` skeleton into a real assistant by adding the two free retrieval tiers, the
Haiku **avatar** (the only LLM in the stack, reusing the user's existing Anthropic key —
**no new credential, no new dependency**), a **user/dev audience toggle** + model-detected
disclosure, and an S5-P1 session buffer. Built per
[`docs/dev/memory-architecture.md`](docs/dev/memory-architecture.md) "Stage 1"; the S3
vector tier stays out (Sprint 7.6, eval-gated).

- **Two real source tiers on the `recall/` `Source` protocol** ([`recall/sources/`](recall/sources/),
  generic + stdlib-only, roots/audience injected): `WikiSource` (S1 — `docs/wiki/pages/*.md`
  → `[[slug]]`-cited Units, audience from each page's `**Audience:**` tag, sha from
  `.last_ingest_sha`); `GitGrepSource` (S2 — `git grep` over **tracked** files → `path:line`
  Units, audience from the SCHEMA path rules; ignored user data is structurally excluded);
  `SessionSource` (S5-P1 — the in-memory session buffer). Re-exported from `recall`.
- **The avatar** ([`analyzer.py`](analyzer.py) — honoring charter C-6 "all LLM calls live in
  `analyzer.py`"): `avatar_answer_streaming()` + `AVATAR_SYSTEM_PROMPT`, a grounded Haiku
  call over an assembled `recall.Context` that cites what it claims and refuses what the
  context doesn't support. Carries its **own** `AVATAR_PROMPT_VERSION` (= `2026-06-16.1`)
  so persona tweaks never bump the résumé-pipeline `PROMPT_VERSION`; intentionally **not**
  in the résumé-scoped `_BASE_SYSTEM_PROMPTS` eval registry.
- **The SSE chat route**, authored as the first module in a new `blueprints/` package
  ([`blueprints/assistant.py`](blueprints/assistant.py), `assistant_bp`,
  `POST /api/assistant/ask`) — blueprint-shaped so the v1.0.8 `app.py`→blueprints split is
  a *move*, not a rewrite. It is the project-wiring layer (the callback roots + the SCHEMA
  audience rules injected into the generic tiers); it does **not** import `app.py` (the
  `dashboard/` precedent). The `_safe_username` security gate applies; `_within` is N/A
  (no user-supplied path is resolved).
- **A minimal in-app assistant panel** ([`templates/index.html`](templates/index.html) +
  [`static/assistant.js`](static/assistant.js)) — an always-available collapsible
  `<details>` with a dev-mode toggle, reusing the existing `_consumeSSE` SSE helper.
- **Guards:** the `recall/sources/` tiers stay project-agnostic — a new
  `test_recall_sources_no_hardcoded_roots` guard in
  [`tests/test_recall_boundary.py`](tests/test_recall_boundary.py) rejects sartor-specific
  path literals (the import-boundary test can't see string literals). `blueprints/assistant.py`
  is added to the PX-08 egress allowlist (it constructs the Anthropic client). `subprocess`
  in `GitGrepSource` carries justified `# noqa: S603, S607` (fixed argv, no shell, local git).
- **Tests:** unit suites for all three tiers + the avatar (LLM-free), a Flask `test_client`
  route suite, and a Playwright UX panel test (avatar stubbed). **`PROMPT_VERSION` unchanged
  at `2026-06-13.1`; zero new dependencies.**

### Added — the Memory substrate skeleton (`feat/recall-skeleton`, Sprint 7.4)

The first piece of sartor's **Memory** function as a first-class subsystem: a new
deterministic `recall/` Python package — the **Stage 0 skeleton** of the reusable
retrieval/assembly substrate the doc-grounded avatar (7.5) and the self-documenting wiki
loop build on. It defines the *seams* only — the public types + the two cross-cutting
planes + a working `assemble()` orchestration — and ships **no real source tier and no
LLM** (the S1 wiki + S2 `git grep` tiers are 7.5; the S3 vector tier is 7.6). **No route,
no LLM call, no new dependency (stdlib-only), no migration; `PROMPT_VERSION` unchanged at
`2026-06-13.1`; no user-facing behavior change** (nothing is wired into the pipeline yet).

- **New `recall/` package** ([`recall/README.md`](recall/README.md) is the contract):
  `Unit` / `Tier` / `Audience` / `Scope` / `Context` value types ([`recall/models.py`](recall/models.py)),
  the `Source` protocol ([`recall/source.py`](recall/source.py)), the access/disclosure
  plane ([`recall/planes.py`](recall/planes.py)), and `assemble(query, scope, sources)
  -> Context` — search → RRF fusion → access-filter → token-budget pack
  ([`recall/assemble.py`](recall/assemble.py)). The whole public API is those four types +
  one entry point.
- **Two cross-cutting planes.** *Provenance/grounding* — every `Unit` carries its stamp
  (`tier · source_id · citation · audience · sha`), enforced at construction; `assemble()`
  only filters/reorders/truncates, never rewrites text, so the stamp survives into the feed.
  *Access/disclosure* — `Scope` resolves the user/dev toggle into an allowed-audience set and
  drops units that exceed it. Design: [`docs/dev/memory-architecture.md`](docs/dev/memory-architecture.md).
- **Shipped reference `Source`** ([`recall/memory_source.py`](recall/memory_source.py)):
  `InMemorySource`, a minimal deterministic source — the worked example a 7.5 tier author
  copies, and the shape the future S5-P1 session buffer takes.
- **The refactor-immune boundary, enforced by test.** `recall/` must never import `app.py`,
  `analyzer.py`, the DB models, Flask, or an LLM client — the rule that makes the v1.0.8
  blueprint split a *move*, not a rewrite. [`tests/test_recall_boundary.py`](tests/test_recall_boundary.py)
  is the AST boundary-lint (mirrors the PX-08 egress gate); no new hook
  (enforcement-portability is the Sprint 8.7 work).

### Added — the compliance-agent pilot (`feat/compliance-agent-pilot`, Sprint 7.7)

Governance gains a witness for the Regulation function — a read-only periodic read of
whole-repo coherence that emits a **ranked, capped drift report**: places where what the
charter / release arc / changelog / code / wiki provenance *say* has drifted from what the
repo *is* at a pinned sha. It cautions and suggests; it **never edits, never blocks, never
files issues** — the [`/wiki-lint`](commands/wiki-lint.md) witness posture turned on the
governance surface, composing the read-only-subagent pattern + the witness-command pattern.
**Dev-harness only — no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged at
`2026-06-13.1`; no migration.**

- **New [`/sartor:compliance-witness`](commands/compliance-witness.md)** — the
  orchestrator command: resolves the pinned sha (`--since <sha>` or the last release tag),
  delegates the read to the model-pinned `compliance-witness` subagent via `Task`, applies a
  **flag cap (default 12, `--cap N`)**, renders the findings-register table (stable id ·
  one-line claim · ≥2 disagreeing sources cited `path:line @ <sha>` · disposition verb
  FLAG / WATCH / AFFIRM · a suggested direction), prints a `/wiki-lint`-style gate verdict
  (clean / needs attention), and **appends a dated counts-per-tier line to
  [`docs/governance/compliance-log.md`](docs/governance/compliance-log.md)**. Its only writes
  are the report surface + that log append — it **never commits, never blocks**.
- **New [`sartor:compliance-witness`](agents/compliance-witness.md)** (Sonnet, read-only
  `Read`/`Grep`/`Glob`/`Bash` — `Bash` is read-only git only) — re-derives every cited line
  at the pinned sha, finds **pairwise drift** (two named sources disagree, or one C-0
  categorical lacks the by-construction enforcement the charter requires), ranks against the
  charter + leverage tier, and returns FLAG / WATCH / AFFIRM flags. The tool grant (**no
  `Edit`, no `Write`, no `Task`**) *is* the enforcement of every HARD non-goal — it cites,
  it never asserts; zero drift is a valid honest-silence verdict.
- **Pilot run (v1.0.7) — PASSES.** One supervised run against the freshly-graduated
  [`docs/governance/`](docs/governance/) surface (born
  [`docs/governance/compliance-log.md`](docs/governance/compliance-log.md); window
  `e299ac8`→`1741ab1`, FLAG 1 / WATCH 2 / AFFIRM 3). The one FLAG (CW-01 — the
  `RELEASE_CHECKLIST` 7.2 row left `[ ]`/"pending" after `feat/governance-extraction`
  merged) was owner-scored **true drift → flag-precision 1.0 ≥ 0.66** and corrected, so the
  witness graduates toward the standing pre-tag companion (v1.1.x). The amendment
  ceremony's "a flag in the compliance agent's next drift report — witness, not approver"
  step is now satisfiable. Full design in
  [`compliance-agent-design.md`](docs/dev/reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md).

### Added — the self-documenting wiki loop (`feat/self-documenting-wiki`, Sprint 7.3)

The `docs/wiki/` knowledge layer now refreshes itself against the code through a bounded,
cost-aware Claude Code dev-harness loop — "the docs track the code without a human author,"
while a human stays at the spend boundary and the commit boundary. **Dev-harness only — no
product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged at `2026-06-13.1`; no migration.**

- **New [`/sartor:wiki-self-update`](commands/wiki-self-update.md)** — the orchestrator
  command: resolves the `.last_ingest_sha`→HEAD diff, **surfaces cost before spending** and
  enforces a per-run page cap (default 8, `--cap N`), delegates per-page synthesis to the
  `wiki-scribe` subagent and per-page grounding audit to the separate `wiki-grounding-auditor`
  subagent (author ≠ auditor), runs [`/sartor:wiki-lint`](commands/wiki-lint.md) as the
  deterministic gate, advances the checkpoint, logs, and **presents a reviewable diff — it
  never auto-commits.**
- **New [`sartor:wiki-scribe`](agents/wiki-scribe.md)** (Haiku, `Read`/`Grep`/`Glob`/`Edit`)
  — minimal SCHEMA-conformant per-page synthesis from the source at HEAD + named exemplar pages.
- **New [`sartor:wiki-grounding-auditor`](agents/wiki-grounding-auditor.md)** (Haiku,
  read-only `Read`/`Grep`/`Glob`) — adversarial quote-match of each cite/`[synthesis]` claim
  against source at HEAD → SUPPORTED / DRIFTED / UNSUPPORTED; the read-only tool grant *is* the
  "never silently rewrite committed history" enforcement.
- **Freshness hook escalation** — [`wiki-freshness-reminder.sh`](.claude-plugin/hooks/wiki-freshness-reminder.sh)
  now escalates its message to `/wiki-self-update` past a 10-file drift threshold (below it, the
  existing `/wiki-ingest` nudge). It **stays a witness** (always exit 0, silent under the
  sentinel and when nothing changed) — only the wording tiers.
- **Trigger = bounded checkpoint** (branch close-out / pre-tag — a `RELEASE_CHECKLIST` line on
  the version-bump), **no scheduler**; the loop is invoked, never self-firing. Scope is
  `docs/wiki/`-only — the cross-document link/cite checker stays a separate tracked follow-on.

### Added — governance extraction: one canonical rules home (`feat/governance-extraction`, Sprint 7.2)

Lifts sartor.'s *binding* governance rules out of the six descriptive docs they were tangled
into and into **one canonical home**, `docs/governance/` — the "extract, don't register-in-place"
decision of record (F-gov-05). Each rule is now stated **once**; each source doc keeps its prose
and gains a pointer back. Docs + hook-script only: **no product code, route, or LLM call;
`PROMPT_VERSION` unchanged at `2026-06-13.1`; no dependency; no migration.**

- **New [`docs/governance/`](docs/governance/)** — `charter.md` (the constitution: C-0…C-6,
  D-1…D-6, the W-1/W-2 working model, the amendment ceremony, the frozen 10-Principles backbone),
  `enforcement.md` (gate vs witness vs tribal, with each item's ship state), `metrics.md` (the
  v1.1.0 tag checklist SC-1..SC-5, the eval ride-along contract, the reusable review rubric).
  Graduated from the 2026-06 product-excellence review's four-file governance-draft;
  **drift-reconciled to HEAD** — the ~8 corrections that already landed in v1.0.6 (PX-01/02/03/05/
  07/08/09/13/14) are cited as corrected, not re-fixed; only the C-1 bind and C-6 boundary gates
  stay forward-sequenced to v1.0.8.
- **New [`docs/dev/EXTRACTION.md`](docs/dev/EXTRACTION.md)** — the incubant-maturity extraction
  playbook (when an in-repo system graduates to a product).
- **Source-doc pointers** — `vision.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `docs/PRODUCT_SHAPE.md`, `docs/dev/RELEASE_ARC.md` each gain a canonical-governance pointer and
  keep their descriptive content. **`AGENTS.md` stays inline-with-pointer** (non-Claude agents read
  it raw — a pure `@import` shell would strip their guardrails); `CLAUDE.md` carries the home
  transitively via `@AGENTS.md`.
- **PX-23** — the stale serial-session framing in `RELEASE_ARC.md` is reframed to the charter W-1
  worktree-per-session parallelism model.
- **PX-27** — `vision.md` gains the ATS escape hatch (goal 2), names the admitted audiences
  (A-2/A-3/A-5), and demotes "single-tenant **by design**" to a threat-model statement.
- **PX-24** — `block-merge-to-main.sh` now also blocks the dominant `git merge feature --no-ff`
  path issued while `HEAD` is `main`/`master` (via worktree-local `git rev-parse --abbrev-ref HEAD`).
- **PX-28** — `check-plan-approved.sh` no longer prints the `New-Item … .approved` hand-create hint
  (it contradicted the never-hand-create rule); the no-marker message is now just "Write a plan and
  call ExitPlanMode."
- **Carry-forward ledger** — the three scattered per-stream "Discovered…(tracked, deferred)"
  sections in `RELEASE_CHECKLIST.md` are consolidated into ONE physical authoritative ledger
  (Open / Resolved); `AGENTS.md` close-out step 0 + `AGENT_HANDOFF_TEMPLATE.md` + charter W-1 now
  require every handoff to render the full *cumulative* still-open subset, with a ~8–10 reduction-
  sprint threshold.
- **Drift fixes folded in:** `AGENTS.md` "Frontend config persistence" (dropped the absent
  `_savePrimaryResume`/`_saveIncludedResumes` names → cite the live `saveConfig()` path);
  `RELEASE_ARC.md` version map ("B.5 SkillGroupItem" → "Skill-as-Corpus-Item") + the §4.7 wiki-lint
  overclaim softened (wiki-lint is `docs/wiki/`-scoped today); `CONTRIBUTING.md` stale OSS-migration
  step reference; `CLAUDE.md` stale `.claude/hooks/` path → `.claude-plugin/hooks/`.

### Changed — plugin activation: `.claude-plugin/` commands + subagents now load (`chore/plugin-activation`, Sprint 7.1)

Makes the dormant Claude Code plugin's **10 commands + 6 subagents** invocable — previously
only the 10 hooks loaded (hand-wired in `.claude/settings.json`), while the commands/agents
were never registered (no marketplace, no install). Dev-harness only — no product code,
route, LLM call, prompt (`PROMPT_VERSION` unchanged at `2026-06-13.1`), dependency, or
migration. Unblocks the v1.0.7 self-documenting loop (`/sartor:wiki-*`) and compliance
pilot.

- **New [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)** — a local
  `sartor-tools` marketplace listing the `sartor` plugin (`source: "."`).
- **[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)** — `name`
  `resume-optimizer → sartor`; `version` `0.1.0 → 1.0.6` (lockstep with `pyproject.toml`).
  The 10 command + 6 agent `.md` files **moved out of `.claude-plugin/` to the plugin root**
  (`commands/`, `agents/`): Claude Code reserves `.claude-plugin/` for
  `plugin.json`/`marketplace.json` and **silently skips any components nested inside it**, so
  the manifest relies on the default root-level scan (no `commands`/`agents` path-overrides).
  No `hooks` key.
- **`.claude/settings.json`** — added `extraKnownMarketplaces` (`sartor-tools`, directory
  source) + `enabledPlugins` (`sartor@sartor-tools`). The existing **hooks block is
  untouched** — the security/quality hooks stay wired here, deliberately *not* migrated into
  the plugin manifest. The tool-agnostic-enforcement question (git-hooks/CI vs Claude
  plugin) is an explicit agenda item deferred to the v1.0.7 governance pass (see
  [`RELEASE_CHECKLIST.md`](docs/dev/RELEASE_CHECKLIST.md) tracked-deferred).
- Commands now load **namespaced** as `/sartor:<name>`; subagents as `sartor:<name>`.
- **Docs corrected to match reality:** command/agent path references repointed from
  `.claude-plugin/commands|agents/` to the root-level `commands/`/`agents/` across `CLAUDE.md`
  (Skill catalog + a new Subagent catalog, namespaced names), `README.md` (plugin section +
  activation line; added the omitted `headhunter` agent + `require-feature-branch` hook),
  `CONTRIBUTING.md`, `docs/system-model.md`, `docs/walkthrough.md`, `evals/README.md`, and the
  `llm-wiki-design` wiki page. Historical CHANGELOG/review/benchmark entries left as-is.

## [1.0.6] — 2026-06-15

### Changed — v1.0.6 release cut: PX-10 blast-radius correction + install test-count fix (`chore/version-bump-v1.0.6`)

Cuts the v1.0.6 release (`pyproject` `1.0.5 → 1.0.6`) and closes the durable-doc loops
that ride the version bump. v1.0.6 is an **internal** tag (public ships at v1.1.0).

- **PX-10 — stale v1.0.8 blast-radius numbers corrected** (`F-arch-02`; 2026-06 product-
  excellence review). The v1.0.8 monolith-decomposition epic's coupling rationale in
  [`docs/dev/RELEASE_ARC.md`](docs/dev/RELEASE_ARC.md) cited a `6,290-LOC / 75-route`
  `app.py` with `67 test files` importing it. Corrected to the **current-accurate**
  `8,251-LOC / 93-route` `app.py` with `32 test files` importing `app`. The prescription's
  literal targets (`6992 / 78 / 24`) were accurate only at the review-era commit `93ecc95`
  and had since drifted as B.4/B.5/PX-02 landed; writing them would have re-introduced the
  inaccuracy PX-10 exists to fix, so the numbers were re-verified against HEAD and the
  current figures used (owner-approved deviation, 2026-06-15). The historical prescription
  is annotated with the deviation, not rewritten.
- **`docs/install.md` — stale test-count floor corrected.** The "Verifying the install"
  step claimed `637+ passed`; the suite is now `1212`, so the floor is updated to
  `1200+ passed`.
- **Dev-tier wiki diff-refresh.** The deferred consolidated `docs/wiki/` refresh of the
  two drifted `audience: dev` pages (`diagnostics-console.md` + `frontend-wizard.md`,
  advancing `.last_ingest_sha` `93a34b9 → 7d8f427`) is recorded in
  [`docs/wiki/log.md`](docs/wiki/log.md) — wiki passes are tracked there, not here (see the
  Scope note at the top of this file).
- **Boundary.** Docs + version metadata only — no route, LLM call, prompt change
  (`PROMPT_VERSION` unchanged at `2026-06-13.1`), new dependency, or migration.

### Added — user-facing "what gets downloaded & why" + in-app eval-stack pointer (`docs/eval-stack-install-guide`, Sprint 6.5 #17)

The user-facing half of the downloads story. The dev-tier provenance already lives in
`docs/dev/excellence-walk/q3-downloads.md` + the `audience:dev` wiki page
`non-dependency-downloads.md`, and `CONTRIBUTING.md` owns the exact eval-stack install
commands — this adds the *user* layer. Authored from the excellence walk's Q3 deliverable;
every figure re-verified against `pyproject.toml`, `docs/install.md`, and `CONTRIBUTING.md`.

- **`docs/install.md` — new "What gets downloaded & why" section** (after Prerequisites,
  with a `what-gets-downloaded` anchor). Plain-language: the only sizeable non-pip download
  to run the app is the Chromium binary (~150 MB, OS user cache, not the repo); the optional
  grounding/eval stack (~3.2 GB of model weights) is flagged as a dev / power-user feature
  that runs only in the eval harness, with a link to `CONTRIBUTING.md` → "Grounding signal
  scorers" for the exact steps — no dev install commands inlined.
- **`README.md` — a "what actually downloads" pointer** beside the existing "What gets saved
  on your machine" section, linking the new install.md section.
- **`dashboard/templates/dashboard.html` — in-app pointer.** One sentence appended to the
  Quality-tab `dashQuality` help body (where the "grounding signals" checkbox is described):
  the offline scorers need the optional `[eval-grounding]` extras (~3.2 GB, dev-only), with
  the CONTRIBUTING.md / install.md references. Plain prose (the help body renders via
  `textContent`).
- **Boundary.** Docs + one dashboard help-copy line — no route, LLM, prompt, dependency, or
  migration; `PROMPT_VERSION` unchanged. Eval-stack install commands stay solely in
  `CONTRIBUTING.md` (single source).

### Added — in-app education for the diagnostics console (`feat/education-diagnostics-annotate`, Sprint 6.5)

Finishes the Sprint 6.5 education sweep on the one surface still left raw: the
localhost-only `/_dashboard` diagnostics console (KW9 + KW13). Plain-language,
a11y-safe, aimed at a first-time (technical) visitor.

- **Ported help mechanism.** The console is self-contained — it never loads
  `static/app.js`, and the wizard's `_initHelp` targets `.cb-panel` headers the
  dashboard doesn't have — so it carries its **own port** of the help primitive in
  `dashboard/templates/dashboard.html`: the same `#helpModal` skeleton (ids reused,
  so the `Help` POM applies unchanged), a per-tab `_DASH_HELP` registry, and an
  `openDashHelp` opener faithful to `app.js` `openHelpModal` (Esc / Tab focus-trap /
  backdrop click-away / `aria-expanded` toggle / focus-restore; the keydown listener
  is removed in cleanup so it never leaks a trap across tab switches).
- **Per-tab summary + first-expand explainer (KW9).** Every diagnostics tab opens
  with a one-line summary + an (i)-circle, and a once-ever explainer modal: the
  Pipeline explainer auto-opens on first visit (the welcome-equivalent), each other
  tab's auto-opens on its first click. Re-openable anytime via the (i). Once-ever via
  the **shared** `cb_help_seen:` localStorage prefix — so the explainers ride the
  same suppression seam as the wizard tour (the five `dash*` ids were added to the UX
  suite's `_TOUR_STOP_BLOCKS`).
- **Annotate tab rewritten for lay readers.** The verdict legend keeps the contract
  codes (`keep`/`fix`/`omit`/`fabricated`) but glosses each plainly; the read-write
  scaffold-banner + ① bootstrap copy are reframed; and the bootstrap `<details>`
  **auto-expands when there are no fixtures to annotate** so the path forward is
  obvious. Per-option `title` tooltips on the suite / subset / grounding controls
  (KW13 "grounding box" / "synthetic-vs-smoke options").
- **"Why empty" everywhere (KW13).** The Pipeline / Quality / Groundedness empty-states
  now say what the panel is, why it's empty, and what populates it.
- **Tests.** New `tests/ux/regression/test_20260615_education_diagnostics_annotate.py`
  (8 cases: per-pane (i) aria; modal open/close/focus-restore; per-tab auto-fire +
  once-ever under `show_tour`; plain-language verdict legend; bootstrap auto-expand on
  empty; "why empty" copy). The `test_axe_dashboard_console` gate now also scans the
  ported `#helpModal` in its **open** state. The stale `No eval results yet`
  route-test copy assertion was tightened to the new strings.
- **Boundary.** Front-end + copy only — **no route, no LLM call, no `PROMPT_VERSION`
  change, no new dependency, no migration.** The diagnostics console is a dev surface,
  so the education is dev content; no user-facing wiki page is authored here.

### Added — in-app education sweep: per-surface help + KW3 new-user tour (`feat/education-tailor-corpus-wizard`, Sprint 6.5)

The per-surface education **content** the help primitive was built for — plain-language,
assumes no technical background. Applies the pattern across every user-facing surface and
authors the new-user first-run tour, mirrored INTO the WS-4 wiki's reserved user section.

- **Per-surface help** — `_HELP_REGISTRY` entries (no engine change) add an (i)-circle +
  plain-language explainer to the user picker, prior applications, all six wizard-step
  panels, and the Career corpus / Résumé templates / Candidate memory panels.
- **KW3 new-user first-run tour** — a small once-ever sequence layered on the primitive:
  a welcome, an add-user tip, a post-ingest corpus explainer, a per-step modal across the
  six wizard steps, and generating / cover-letter tips. **New-users-only** via an in-memory
  "armed" flag (set on user creation / empty-corpus landing); returning users are never
  walked through onboarding. Each stop fires once (reusing the `cb_help_seen:` localStorage
  seam) and is re-openable from the nearest section's (i); wizard stops fire only when the
  panel is actually on screen (visibility-guarded).
- **Wiki** — five new `audience: user` guides under `docs/wiki/pages/` (`using-sartor`
  hub + tailoring / corpus / templates / memory), mirrored by the in-app copy. Recorded in
  [`docs/wiki/log.md`](docs/wiki/log.md) (a content pass — `.last_ingest_sha` unchanged).
- **Tests** — new `tests/ux/regression/test_20260614_education_help.py` (every panel's icon
  + aria; open/close/focus for regular and wizard-step headers; tour arming, once-ever, and
  the visibility guard); the vendored axe a11y gate gains a help-modal-from-step-header scan;
  the autouse welcome-suppression fixture generalized to all tour stops + a new `show_tour`
  marker. A scoped `.cb-step-header.has-help-icon .help-info` rule centres the (i) on the
  baseline-aligned step headers.

Front-end + content only — no Flask route, no LLM call, no prompt change (no `PROMPT_VERSION`
bump), no new dependency, no migration.

### Added — reusable in-app help primitive (`feat/help-pattern-component`, Sprint 6.5)

The mechanism the Sprint 6.5 in-app education sweep hangs its copy on — built once,
a11y-safe, reusable. **No per-surface education copy is authored here** (that is the
next branch); this ships the engine plus a single demo entry so it is exercised and
gated.

- **One shared `#helpModal`** (cloned from the existing `.cb-modal` skeleton) whose
  title/body are swapped per block; the stable `#helpModalTitle`/`#helpModalBody` ids
  keep `aria-labelledby`/`aria-describedby` valid without per-open rewiring.
- **One generic `openHelpModal(blockId, triggerEl)`** factored from the existing
  per-modal pattern (Esc, Tab focus-trap, backdrop click-away, focus restored to the
  trigger) — the reusable opener the five existing modals each re-implemented. They are
  left untouched.
- **A `.help-info` (i)-circle** injected into each registered `.cb-panel` header
  (mirrors `.compose-order-info`) re-opens that block's modal. **No color-only meaning:**
  the literal "i" glyph + an `aria-label` ("Help: <title>") + `aria-haspopup="dialog"`/
  `aria-expanded` carry the semantics; colour is decorative hover only. An optional inline
  short-form line is injected atop the panel body and associated via `aria-describedby`.
- **First-view welcome auto-modal** (graceful fade-in via the existing `cb-modal-in`
  keyframe + `prefers-reduced-motion`), shown **once-ever** via a `cb_help_seen:<block>`
  **localStorage** flag — the app's first client-side storage usage (wrapped so a
  disabled/throwing store is non-fatal).
- **Tests:** new `tests/ux/regression/test_20260614_help_pattern.py` (auto-open,
  click-away, once-ever, icon re-open, focus restore, aria wiring); `#helpModal` added to
  the vendored axe a11y gate's scanned surfaces; a `Help` selector class in `ui_pages/`.
  The welcome is default-suppressed for the rest of the UX suite by an autouse fixture +
  the new `show_welcome` marker, so its full-screen backdrop never blocks other tests.

Front-end + help-component only — no Flask route, no LLM call, no prompt change (no
`PROMPT_VERSION` bump), no new dependency, no migration.

### Added — eval-smoke gate guard + README exit-code reconciliation (`test/eval-gate-guard`, PX-13)

Affirms and guards the eval-quality regression gate so it can't silently rot (2026-06
product-excellence review: `F-qe-rel-05`, KEEP/CONFIRMED; rides the PX-08 egress gate). The
eval-smoke gate is a real machine gate: `evals/runner.py` returns process exit-code `2`
(failing the label-gated CI check) on **either** a sub-`PASS_THRESHOLD` (4.0) rubric score
**or** a regression past `REGRESSION_DELTA` (0.5) vs the committed `baseline_v1.json`
(`exit_code = 0 if (n_fail == 0 and not regressions) else 2`).

- **Meta-test** — new `tests/test_eval_runner.py::TestEvalGateGuard` pins **both** exit-`2`
  arms with an LLM-free stub (runs in the default `pytest`, no paid Anthropic call): a
  grounding score below the threshold (`n_fail` path), and a grounding score that passes the
  threshold but drops past `REGRESSION_DELTA` below a seeded baseline (`regressions` path,
  `n_fail == 0`). If a future change softens the gate (drops `not regressions`, loosens a
  threshold, adds `continue-on-error`), the test goes red.
- **Do-not-regress note + CI scope** — reconciled `evals/README.md`, which had drifted: three
  spots (quick-start, the exit-codes table, the "Regression alerting" section) still claimed
  regressions were *informational* and didn't affect the exit code. That was true before commit
  `a60a008` ("PR gate") made regressions gate; the narrative was never updated. Corrected to the
  actual contract, added a "Do-not-regress: the gate is machine-enforced" callout, and recorded
  the CI scope explicitly — grounding-rubric-only across the 3 synthetic fixtures, label-gated
  (`eval`), no `continue-on-error`.

Test + docs only — no change to the gate's behavior, no prompt, route, dependency, or
migration; `PROMPT_VERSION` unchanged.

### Changed — C-0 claims discipline: no-invention absolutes reworded (`docs/c0-claims-discipline`, PX-09 + PX-14)

Documentation-only corrections from the 2026-06 product-excellence review's PX band, reconciling
the absolute "no invention" register on the highest-audience surfaces with what the system
actually enforces. C-0 bars LLM-behavior absolutes; the owner recanted the exact strings in the
review interview (R2-4.2 "'LLM cannot invent' is a bold claim … we do our best"; R2-4.4 "no
invention ever is over-stated").

- **PX-09 — no-invention absolutes → mechanism-and-effort** (`F-vision-02` / `F-docs-03`; charter
  C-0, A-4). Reworded the categorical "The LLM cannot invent facts." and the "No invention, ever"
  heading (`vision.md`), and the "without inventing anything about you" / "may not fabricate"
  taglines (`llms.txt`, `docs/wiki/overview.md`, `docs/system-model.md`), to describe the actual
  mechanism — a grounding check in the generation prompt plus the `grounding_overlap` *witness*
  metric that **measures** rather than enforces-by-construction — and to say plainly it is
  best-effort, **not** a categorical guarantee. The two near-identical product taglines (overview /
  system-model) now read identically; each file's "Open revision points → point 4" self-reference
  was updated so it no longer quotes the retired opening.
- **PX-14 — `GROUNDING_METRIC.md` union correction** (`F-eval-04`; rides PX-09's branch per the
  prescription). The metric design note claimed a **four-part** source union (incl. first-person
  typed edits); corrected to the actual **three-source** deterministic union (`original primary
  résumé + supplemental résumés + clarification answers`). Typed edits remain prompt-side ground
  truth for the *model* — they widen the generation grounding check — but are not a member of the
  *metric's* source set. Doc now follows code (`hardening.assemble_source_union`); no code change.

Docs only — no code, prompt, route, dependency, or migration; `PROMPT_VERSION` unchanged.

### Changed — disclosure-doc corrections (`docs/disclosure-doc-corrections`, PX-03/05/07)

Documentation-only corrections from the 2026-06 product-excellence review's PX band, aligning
the public-facing security / governance docs with what the tool actually does.

- **PX-03 — two-class egress enumeration** (`AL-7`; charter C-2). `SECURITY.md` listed a third
  "any URL you explicitly paste as a job description" HTTP-egress class that has never existed:
  `jd_url` is provenance metadata, never fetched (the only network fetch is
  `scraper.fetch_url_content`, called solely for profile / portfolio URLs). Corrected to the two
  real classes — the Anthropic API and the opt-in profile/website scrape — with an explicit "JDs
  are always pasted text" note. `vision.md` / `README.md` already enumerated two classes; left
  unchanged. Corroborated by the PX-08 egress allowlist gate.
- **PX-05 — disclosure channel repointed** (`F-sec-11`, P1 / S-1). Conduct / vulnerability
  reports routed to a stale `Cooksey/resume` GitHub advisories inbox; corrected to the canonical
  `amodal1/sartor` in `CODE_OF_CONDUCT.md` and `.github/ISSUE_TEMPLATE/config.yml`.
- **PX-07 — human SLAs softened** (`F-qe-rel-08` / `F-sec-07`; charter D-4 + P-3). The hard
  "5 business days / 30 days" promises in `SECURITY.md` and `CODE_OF_CONDUCT.md` are reworded to
  best-effort intent (no guaranteed timeline) for a solo project. Machine gates unchanged.
- **Stale-ref fold-in** (owner-authorized). The same stale `Cooksey/resume` repo target in
  `CONTRIBUTING.md` (`cd resume`), `.claude-plugin/plugin.json` (`homepage`), and
  `evals/schemas/context_set.schema.json` (`$id` — cosmetic; resolved only by file path) was
  corrected in the same pass to avoid future one-file branches. The plugin's `author.name` (the
  maintainer) and `name` / description (a project-rename concern for v1.0.7) were left untouched.

Docs / metadata only — no code, prompt, route, dependency, or migration; `PROMPT_VERSION`
unchanged.

### Added — profile/website scrape re-wired into the runtime path (`fix/profile-scrape-rewire`, PX-02)

The opt-in LinkedIn / website / portfolio scrape (`scraper.fetch_profile_content`) had been
**dead code** — no runtime caller since the corpus/DB refactor — so the docs' "live profile
scrape" claim was false (2026-06 product-excellence review: `F-docs-04` / `AL-5`). It is now
wired to an explicit, opt-in user action so the claim is honest.

- **New route** `POST /api/users/<u>/profile/fetch` — reads the saved config's `linkedin_url` /
  `website_url` / `portfolio_urls`, runs the deterministic best-effort scraper, and caches the
  combined text. Triggered by a **"Fetch profile content"** button in the Settings drawer (saves
  config first, then fetches). Guarded by `_safe_username` + `_within`; the network egress stays
  inside the already-sanctioned `scraper.py` (PX-08 allowlist unchanged — no new egress site).
- **Dedicated storage** — cached in a new `Candidate.online_profile_text` column (alembic `0010`)
  and surfaced to the LLM via a new `<candidate_web_presence>` prompt block (`PROMPT_VERSION` →
  `2026-06-13.1`). Deliberately **distinct** from `profile_text`, which β.6 repurposed as the
  positioning summary (résumé `basics.summary` fallback) — so the scrape can never clobber a
  candidate's summary.
- Opt-in + graceful: nothing fetches until the user clicks; unreachable URLs are swallowed to
  empty; a config with no URLs is a valid opt-out. No new dependency (`requests` + `beautifulsoup4`
  already shipped for `scraper.py`). The runtime wiring is pinned by a regression test so it can't
  silently die again. (PX-03 egress-doc alignment is a separate later branch.)

### Added — network-egress falsifiability gate (`test/egress-falsifiability`, PX-08 / G-2)

A committed test (`tests/test_egress_allowlist.py`) now makes charter claim **C-2**
machine-falsifiable instead of a one-time hand audit (2026-06 product-excellence review:
`F-qe-rel-02` P0 + `F-sec-01`; gate **G-2**, release-pass-plan.md §2). It fails if anything
opens an outbound socket outside the **two** sanctioned destination classes — the configured
LLM provider (`api.anthropic.com` via the `anthropic` SDK) and the opt-in profile/website
scrape of arbitrary user URLs (`requests` in `scraper.py`) — or if any Jinja template loads an
off-box CDN resource. This is the construction that keeps **PX-01**'s Chart.js vendoring honest:
it would have caught the prior `cdn.jsdelivr.net` `<script>` by construction.

- **Static egress allowlist** (the core gate) — an AST scan asserts the set of production
  modules importing a network-egress library is *exactly* the sanctioned eight (anthropic in
  `analyzer.py` / `app.py` / `evals/runner.py` / `evals/bootstrap.py` /
  `onboarding/extract_experiences.py` / `onboarding/corpus_import.py` / `scripts/smoke_phase_b1.py`;
  `requests` in `scraper.py`). A new egress site anywhere — or allowlist rot — fails. Walks the
  whole AST so lazy / `TYPE_CHECKING` imports are caught; `urllib.parse` (string parsing) is not
  flagged.
- **Runtime checks** (pytest-socket) — the provider `base_url` is pinned to `api.anthropic.com`;
  the seven deterministic modules open no socket at call time; and the scrape path is proven a
  real, blockable egress (IP-literal so the block fires before DNS, not swallowed to `""`).
- **Template scan** — generalizes the rendered-output assertion at
  `tests/test_dashboard_routes.py:377-379` to a static scan of every template source
  (`templates/`, `dashboard/templates/`, `personas/`), flagging any off-box `<script>`/`<link>`/
  media/`url()` resource load or known CDN host.

New dev dependency `pytest-socket` (`[dev]` extras only; inert until invoked — no global
`--disable-socket`, so the default suite and the `-m ux` live-server tier are untouched). G-2
becomes a required CI check at **v1.0.7**; this lands the committed test + dependency it enforces.

### Changed — vendored Chart.js; declared vendored-asset licenses (`fix/vendor-chartjs`, PX-01 + PX-06)

Chart.js 4.4.0 (MIT) is now **vendored** at `static/vendor/chart.umd.min.js` instead of
loaded from `cdn.jsdelivr.net` at runtime — closing the runtime-CDN contradiction with
SECURITY.md / vision.md's "no external CDN / no third-party fetch at runtime" promise
(2026-06 product-excellence review: `F-sec-03` / `F-vision-05` / `F-docs-02`; charter
C-2(i)). The downloaded bytes were verified byte-for-byte against the prior `integrity`
SHA-384 before the CDN `integrity`/`crossorigin` attributes were dropped. SECURITY.md now
inventories both vendored assets' licenses — Chart.js (MIT) and the test-tier axe-core
4.10.2 (**MPL-2.0**) (`F-sec-08`, PX-06). No new Python dependency (vendored static asset,
like `paged.polyfill.js`).

### Added — individual skills as a Corpus Item (`feat/skill-group-item`, Sprint 6.6 B.5)

The flat `Skill` row is promoted to a full Corpus Item — the same lifecycle every
other corpus type already has (mirrors **Bullet**): taggable, recommend-curated,
pin/drop/reorder per JD, with a suggested → approved/denied review flow. Maps to
JSON Resume `skills[]`. New migration `0009` (ALTER `skill` + new `skill_tag` join
+ backfill) and **two** new Haiku calls; **`PROMPT_VERSION` bumped to `2026-06-12.2`**
(two new system prompts registered). No new dependency. (Settled interactively with
the owner: this replaces the original "skill clusters" framing — individual skills,
no grouping — and the grounded-suggestion generator is a **user-authorized** scope
addition beyond the literal RELEASE_ARC row.)

- **`Skill` promoted to a Corpus Item.** Gains `is_active` / `is_pending_review` /
  `source` / `display_order` / timestamps + a `SkillTag` join (mirrors `BulletTag`).
  Migration `0009` backfills every legacy row as `source='imported'`, active,
  approved, with `display_order` preserving the prior name-sorted order — so the
  no-curation output is unchanged.
- **`recommend_skills` (Haiku) — order + curate.** Given the candidate's active,
  approved skills (+ tags) and the JD, returns the relevance-ordered set the Compose
  card seeds as the default. Selects only from the approved set, so it can never
  invent a skill. Auto-applied like bullets; the user pins / drops / reorders on top.
- **`suggest_skills` (Haiku) — grounded generator.** Proposes skills the JD wants
  **and** the candidate's corpus evidences (evidence-or-nothing; never JD-only).
  Proposals land as **pending** (`source='llm_proposed'`) for the user to approve or
  deny — the human gate is the grounding backstop: a pending skill never reaches the
  recommend set, the preview `skills[]`, or the generate prompt until approved.
- **Per-application curation.** `composition_overrides` gains `pinned_skill_ids` /
  `excluded_skill_ids` / `skill_order` (each persisted only when non-empty, so the
  default path stays byte-identical). The recommend output rides on
  `llm_skill_recommendations`. All save paths route through the canonical
  `_collectCompositionState()`, so a skill save never clobbers sibling overrides.
- **Reach: download + preview.** `_collect_skills` (deterministic) applies the
  recommend ∪ pinned − excluded selection (ordered) to the preview `skills[]`; at
  generate time `_apply_recommended_skills` patches the candidate's skills list so
  the **LLM-authored download** surfaces the same curated/ordered set. No-op (and
  byte-identical) when there's no recommendation and no overrides.
- **Surfaces.** Compose gets a candidate-level **Skills** card (Tailor / Suggest +
  pin/drop/reorder + a pending review lane); the Career-corpus tab gets a **Skills**
  editor (add / retire / tag + approve/deny suggestions).
- **5 route families** — skill CRUD (`GET`/`POST /api/users/<u>/skills`,
  `PUT`/`DELETE /api/skills/<id>`), skill tag link/unlink, and per-application
  `POST .../recommend-skills` + `POST .../suggest-skills`, plus the `/composition`
  extension. Eval: corpus-mode-only; the legacy generate path is byte-identical, so
  the paid smoke is skipped (covered by unit + UX); see `evals/TUNING_LOG.md`.

### Added — per-role intro as a multi-variant Corpus Item (`feat/experience-summary-item`, Sprint 6.6 B.4)

The per-role intro paragraph — the line a recruiter reads first under each job —
becomes a first-class, multi-variant Corpus Item, mirroring the candidate-level
`SummaryItem` but scoped per-`Experience`. Maps to JSON Resume `work[].summary`.
New migration `0008` + a new Haiku `recommend_experience_summaries`; **`PROMPT_VERSION`
bumped to `2026-06-12.1`** (the generate prompt gained a conditional `<summary>`
element + guide). No new dependency.

- **Opt-in, not auto-applied.** Unlike `SummaryItem` (which auto-lands on the
  recommendation → first-active → profile_text), a role intro appears **only when
  the user turns on the Compose-step "Add role intros" toggle for that application
  AND a variant is chosen** (`composition_overrides.use_experience_summaries` +
  `chosen_experience_summary_ids`). Toggle off (the default) is a full no-op — the
  generate prompt is **byte-identical**, so the analyze→generate cache is untouched
  for anyone who doesn't opt in. The sentinel `0` records an explicitly-cleared role.
- **WYSIWYG into the real résumé.** A chosen intro is injected into the frozen
  `career_corpus` snapshot at generate time by `_apply_chosen_experience_summaries`
  (mirroring `_apply_chosen_summary`), so it reaches **both** the LLM-tailored output
  **and** the deterministic JSON-resume/PDF preview (`work[].summary`). The legacy
  single `Experience.summary` column is now a denormalized cache — migration `0008`
  backfills it into one `imported` variant; it is no longer auto-emitted.
- **Model + migration.** New `ExperienceSummaryItem` (+ `ExperienceSummaryItemTag`)
  tables (FK → `experience.id`, CASCADE), mirroring `SummaryItem`. Idempotent Alembic
  `0008` with a backfill from non-empty `Experience.summary`.
- **Routes.** Experience-scoped CRUD (`GET`/`POST /api/experiences/<id>/summaries`,
  `PUT`/`DELETE /api/experience-summaries/<id>`) with the bullet routes' ownership
  pattern (experience → candidate → `_safe_username`); a batched
  `POST /api/applications/<id>/recommend-experience-summaries` (one Haiku call keyed
  by `experience_id`, mirroring `recommend_application_summary`).
- **UI.** A per-role intro picker inside each Compose experience card (sits between
  the title and the bullets); the application-level **Add role intros** toggle (seeds
  each role from the AI recommendation on enable); a per-experience intro-variants
  editor in the Career-corpus tab (add / rename / retire). Composition GET surfaces a
  per-experience `summary` block + the toggle state; the per-role picks ride the
  canonical composition autosave so bullet/title saves never clobber them.
- **Tests.** New `tests/test_experience_summary_item_routes.py` (CRUD + ownership +
  soft-delete + real migration backfill), `tests/test_recommend_experience_summaries.py`
  (batch short-circuit + dedup + route), `tests/test_experience_summary_composition.py`
  (GET/POST + generate-path injection + a **byte-identity** guard on the default
  prompt), an opt-in mapping suite in `tests/test_corpus_to_json_resume.py`, and a UX
  regression `tests/ux/regression/test_20260612_experience_summary_item.py`. New
  `ui_pages` selectors + Corpus/Compose page-object methods; the UX stub gains
  `fake_recommend_experience_summaries`.
- **Fixed (in-scope, user-authorized): Compose save no longer clobbers sibling
  overrides.** `_togglePositioningPin` (the candidate positioning-summary pin) used
  to hand-gather only bullets, so pinning a summary silently wiped `bullet_order` +
  `pinned_title_ids` (and the bullet autosave wiped `pinned_summary_id`). All save
  paths now route through the canonical `_collectCompositionState()`, so every
  override family — bullets, order, title pins, **and** the new role intros —
  survives any single save. Regression-locked (`test_positioning_pin_preserves_title_pin`).
  Also fixed the `fake_recommend_summaries` UX stub's shape (it never set
  `has_recommendation`, looping the positioning card's auto-fire once 2+ candidate
  variants existed). ruff ✓ · mypy ✓ (149 files) · pytest **1127/1127** incl. `-m ux`.

### Added / Changed — corpus-first IA + smart landing (`feat/corpus-first-tab-onboarding`, Sprint 6.4 #16 + #1 + KW1)

Front-end only — SPA tab routing over one existing read endpoint
(`GET /api/users/<u>/experiences`). No new route, no LLM call, no
`PROMPT_VERSION` bump, no new dependency, no migration.

- **Tabs reordered to corpus-first.** The top tabs now read **Career corpus →
  Tailor → Résumé templates → Candidate memory**. Only the `<nav>` button order
  changes; **Tailor keeps the default active state** because the user picker
  (`#panelUser`) lives in the Tailor tab and the no-user landing must show it.
- **Smart landing on user select (KW1).** `onUserSelect()` now routes through a
  new side-effect-free `_landingTab()` helper instead of unconditionally showing
  the applications panel: an **empty corpus lands on Career corpus** (onboard —
  import a résumé), a **populated corpus lands on Tailor** (straight to the
  workflow). Fixes the dead-end where a brand-new user landed on JD entry with
  nothing to tailor from.
- **`goHome()` honors smart landing.** The wordmark route now goes through the
  same `_landingTab()` (single source of truth for "which tab is home") rather
  than a hardcoded `'tailor'`. Because it deselects the user first, it still
  resolves to the picker's home (Tailor).
- **"Start tailoring →" hand-off CTA.** When corpus review is finished — a
  non-empty corpus with **0 items pending** — the onboarding banner flips to a
  success (`is-ready`) state offering **Start tailoring →**, which switches to
  the Tailor tab. Replaces the old dead-end (the banner used to just disappear).
  The banner refresh in `refreshCorpus()` was relocated to fire after the list
  renders so its ready/empty decision reads fresh `_corpusExperiences`.
- **Tests.** New UX regression
  `tests/ux/regression/test_20260612_corpus_first_landing.py` (empty→Corpus,
  populated→Tailor, ready→CTA→Tailor). `test_20260612_logo_home_route.py` now
  seeds a non-empty user so its select-then-home flow still lands on Tailor under
  smart landing. New `Corpus.START_TAILORING_BUTTON` selector +
  `CorpusPage.start_tailoring_button()` POM accessor.

### Fixed — logo routes home (`fix/logo-home-route`, Sprint 6.4 #23)

Front-end only — no LLM call, no `PROMPT_VERSION` bump, no new dependency, no
route (pure client-side SPA navigation), no migration.

- **The `sartor.` wordmark now routes home.** It was an inert `<a href="#">`
  with no handler — once a user was selected (and the wizard or another tab
  engaged) there was no way back to the landing state. A new public `goHome()`
  clears the selected user via `onUserSelect()`'s no-user branch (hides the flow
  panels, re-locks the user picker open, resets iteration state) and restores the
  default **Tailor** landing tab via `switchTopTab('tailor', …)`. The wordmark
  anchor gains `onclick="goHome(); return false;"` (cancels the bare `#`
  navigation) plus a clearer `aria-label`/`title`. Which tab counts as "home"
  stays the current default — the smart-landing reorder is the separate next
  6.4 branch (`feat/corpus-first-tab-onboarding`).
- **Tests.** New UX regression
  `tests/ux/regression/test_20260612_logo_home_route.py` (select user → off-tab →
  wordmark click → asserts the Tailor tab restored, user deselected, picker
  re-locked open, flow panel hidden). New `Header` selector in
  `ui_pages/selectors.py`. Axe a11y gate stays green.

### Fixed — internal tooling (`fix/require-feature-branch-worktree-aware`)

- **`require-feature-branch` hook is now worktree-aware.** It resolves the
  branch of the repo containing the *target file* (`git -C`) instead of the
  hook's cwd, so edits to a feature branch in a separate worktree/clone are no
  longer falsely blocked by the launch clone being on `main`. Hook-only change;
  no LLM call, no `PROMPT_VERSION` bump, no new dependency, no route, no migration.

### Added / Changed — corpus affordance polish (`fix/corpus-affordance-polish`, Sprint 6.3 #2 + #5 + KW2)

Front-end polish + one DB-only route on the Career Corpus tab. No LLM call, no
`PROMPT_VERSION` bump, no new dependency, no migration.

- **KW2 — corpus-wide "Accept all pending."** A new `Accept all pending` button
  in the onboarding banner clears `is_pending_review` across **every** role in
  one click (senior résumés have many roles, previously accepted one-by-one). New
  DB-only route `POST /api/users/<username>/accept-all-pending` (`_safe_username`
  guard; mirrors `accept_experience_all` candidate-scoped, reusing the `exp_ids`
  query from `pending-counts`). The existing per-experience `ACCEPT ALL PENDING`
  still covers the by-role case. The control guards behind a **sharp confirm**:
  accepted items become source-of-truth the system scores for fit, generates new
  bullets from, and builds résumés on — one bad seed poisons everything
  downstream.
- **Empty-state copy — dropped the "automatically" overpromise.** Imported
  résumé items land *pending review*, so the empty-corpus copy (`static/app.js`)
  and the static corpus hint (`templates/index.html`) now say the import is
  extracted "for you to review" rather than built "automatically."
- **#5 — enlarged the panel collapse chevron.** `.panel-header::after` (`▾`)
  10px → 18px; it was near-imperceptible. (A later redesign rule had pinned the
  *effective* size to 10px, overriding the legacy 12px rule — sized on the live
  rule, with a comment so the next editor doesn't hit the same trap.)
- **#2 — regression-locked the "Add variant" affordance.** The finding ("Add
  variant referenced in copy but no affordance") was already resolved by the
  β.6e summary-variants editor; a new UX test now asserts the `+ Add variant`
  control is present so it can't regress.
- **Tests.** New backend `TestAcceptAllPendingCorpus`
  (`tests/test_pending_review_routes.py`) + new UX regression
  `tests/ux/regression/test_20260612_corpus_affordance_polish.py` (affordance
  present · review-honest empty copy · accept-all clears + hides the banner ·
  chevron size). New `Corpus` selectors in `ui_pages/selectors.py` +
  `CorpusPage` helpers. Axe a11y gate stays green.

### Added — reusable required-field marker + auto-populatable username dropdown (`feat/required-field-and-dropdown-pattern`)

Two reusable front-end conventions (Sprint 6.3, findings #21 + #20-dropdown),
built on the axe a11y gate that the prior branch landed. Front-end + tests only —
no LLM call, no `PROMPT_VERSION` bump, no new route (reuses `GET /api/users`),
no new dependency, no migration.

- **#21 — reusable required-field marker.** A new convention: a required input
  carries `required` + `aria-required="true"`; its visible label carries a
  decorative `<span class="required-marker" aria-hidden="true">*</span>`; a field
  cluster gets one `<p class="form-required-legend">` line. The two classes live
  in `static/style.css` (shared — the dashboard loads it too), documented by a
  load-bearing comment. `aria-required` is the real signal assistive tech
  announces; the asterisk is purely visual (`aria-hidden`). Proven across **three
  render paths**: the static new-user form (`templates/index.html` —
  username/name/email; the optional contact fields stay unmarked), the
  JS-rendered `openFormModal` modals (`static/app.js` — every `required:true`
  field gets the marker + `aria-required` for free, covering add-title /
  add-bullet / add-experience), and the console dropdown label (below).
- **#20 (dropdown) — auto-populatable input → `<select>`.** The diagnostics
  console's candidate-username fields (`#bsUser` on the Annotate tab, `#tuneUser`
  on the Tuning tab) were free-text `<input>`s that should pick from the known
  set of candidates. They are now `<select data-user-source>` auto-filled on load
  by a small reusable `populateUserSelects()` helper that fetches the existing
  `GET /api/users` (mirrors `loadUsers()` in `app.js`) — any select opting in via
  `data-user-source` is filled, with the placeholder `<option value="">`
  preserved so the existing `.value` reads + "provide a username" guards still
  work. `#bsUser` (genuinely required) carries the required marker; `#tuneUser`
  does not — its "Real-corpus seed (optional)" section is optional.
- **Tests.** New regression
  `tests/ux/regression/test_20260612_required_field_and_dropdown.py` (the marker
  across all three render paths + dropdown populate/select round-trip); the
  dashboard axe scan now seeds a candidate and opens the collapsed sub-panels so
  the **populated** dropdowns are scanned, not just empty placeholders. Selector
  registry gains a shared `Forms` class + the Tuning username handles.

### Added — axe-core accessibility smoke gate + a11y fixes (`fix/form-field-labels-a11y`)

The never-shipped a11y gate (Sprint 6.3, finding #3) — the arbiter that guards
every later v1.0.6 branch — plus the violations it surfaced. Front-end + one new
test tier only; no LLM call, no `PROMPT_VERSION` bump, no route, no migration,
**no new pip dependency** (axe-core is vendored, not installed).

- **New a11y gate — `tests/ux/a11y/test_axe_smoke.py`.** Injects the **vendored**
  axe-core engine (`tests/ux/a11y/vendor/axe.min.js`, axe-core `4.10.2`, MPL-2.0)
  into each reachable panel — landing, new-user form, the four top tabs, the
  Settings drawer, a stubbed Compose/Template drive, and every `/_dashboard` tab
  — and asserts **no `serious`/`critical` violations**. Vendored (not a pip dep)
  so it runs wherever the UX-tier Chromium runs and can never silently skip from
  a missing extra; rides the existing `tests/ux/conftest.py` harness (Chromium
  graceful-skip + console/5xx sentinel). New `a11y` pytest marker — the tests are
  also `ux`, so they run inside `pytest -m ux`; `pytest -m a11y` runs them alone.
- **Form-field labels were already clean** (defect-vs-expected: the "~150 flagged
  fields" predated the v1.0.5/v1.0.6 redesign). The gate found **zero** label/name
  `serious`/`critical` violations. Belt-and-suspenders completion of #3 anyway:
  `sr-only` labels on the three hidden file inputs (`templateUploadInput`,
  `corpusIngestFile`, `personaUploadInput`) and `name` + `autocomplete` on the
  new-user form + Settings-drawer personal fields (the "missing autofill" half).
- **Fixed — color-contrast (the only `serious` violations the gate found).** The
  muted-text tokens were sub-WCAG-AA on the dark surfaces: `--fg-2` (`#6c6c7a`,
  down to 3.19:1) and `--fg-3` (`#4a4a56`, down to 1.72:1) are lightened to
  `#9b9ba7` / `#8f8f9b` (≥4.5:1 on the darkest surface, including the warm
  selected template-row bg), and `.edit-hint` drops its `opacity: 0.7` (which
  composited `--fg-1` to a sub-AA `#7c7d88`) for a solid `--fg-2`. Token-level fix
  in `static/style.css`, so it clears the Settings hints, the Step-4 template
  chips/sub-labels, and the `/_dashboard` meta/cost/link text in one place
  (user-approved scope addition — design-system color change).

### Fixed — diagnostics-console chart + layout corrections (`fix/diagnostics-chart-corrections`)

Three `/_dashboard` defects from the v1.0.6 kickoff walkthrough harvest (Sprint
6.2; findings #11 + #12 + #13), plus the KW13 space-usage restructure. Front-end
+ deterministic-aggregation only — no LLM call, no `PROMPT_VERSION` bump, no new
route, no new dependency, no migration.

- **KW13 + #12 — panels now use the page width; the Calls table no longer
  horizontal-scrolls.** The detail surface was a cramped 560px right-hand side
  drawer, so the 10-column **Calls** (throughput) table overflowed with a
  horizontal scrollbar (#12). The drawer is replaced by a **full-width inline
  detail panel** rendered in the page flow beneath the tabs: the selected tile's
  detail block is moved into it from `#detailStore` (reusing the existing
  move-the-node + lazy-`initCharts` machinery — only the destination changed) and
  scrolled into view. Every detail (Calls, heatmap, health, reliability, pareto,
  trace, all charts) now renders at full width (KW13), and the Calls table fits
  with no scroll (a defensive `word-break` on its cells guards narrow viewports).
- **#13 — latest-trace bars now render and scale to the longest span.** Two
  problems compounded into "bars look empty": the `.wf-bar` was a `<span>` left
  at `display:inline`, so its `width` never applied and **every bar rendered at
  0px**; and the width was each span's share of the run *total*, so even once
  visible a short span (e.g. a 4s `clarify` beside a 60s `analyze_synthesis`) was
  a sliver. Fix: `.wf-bar` is now `display:block` with a 2px `min-width` floor,
  and `dashboard/routes._run_trace` emits `bar_pct` scaled to the **longest
  span** (max → 100%); the template binds bar width to `bar_pct`, keeps the
  share-of-total `pct` on hover, and keeps `latency_ms` as the absolute truth.
- **#11 — cost-by-kind chart tooltip is now unambiguous.** The walkthrough read
  the cost chart's tooltip as "Total" but plotting the mean. It always plotted
  the **total** (`total_cost_usd = sum`, unchanged since the console was built);
  the confusion was an unlabeled default tooltip beside a `mean $` table column.
  The chart now carries an explicit tooltip naming the value as the total with
  count + mean for context (e.g. `generate — total $0.02340 · 12 calls · mean
  $0.00195`). Data unchanged.
- Covered by a deterministic unit test for `bar_pct`
  (`tests/test_dashboard_routes.py::TestRunTrace`) and a UX-tier regression
  (`tests/ux/regression/test_20260611_diagnostics_chart_corrections.py`): the
  detail panel uses the page width with no horizontal overflow on Calls, the
  trace bars scale to the longest span, and the cost tooltip names total + mean.
  The dashboard POM + selectors moved from `drawer` to `detail-panel` handles.

### Fixed — wizard-flow polish: follow-up-question auto-scroll + copy alignment (`fix/wizard-flow-polish`)

Two small Output-panel polish fixes from the v1.0.5 walkthrough harvest
(Sprint 6.1, final row; findings KW5 + KW8):

- **KW5 — auto-scroll.** Clicking the post-generation **"Get follow-up
  questions"** button rendered the iteration questions *below the fold*, so it
  looked like nothing happened. `runIterateClarify()` now scrolls the revealed
  `#iterateClarifyArea` section into view in its success path (reusing the
  existing `scrollIntoView({behavior:'smooth',block:'start'})` idiom), covering
  both the questions and the "no follow-up questions surfaced" branches.
- **KW8 — copy alignment.** The button label and section divider used
  "interview" wording inconsistent with the clarify vocabulary (the button's own
  tooltip already said "clarifying questions"). They now read **"Get follow-up
  questions"** and **"Follow-up clarification"**. The `#btnIterateClarify` id is
  unchanged, so selectors / page objects are unaffected. The tracker "Got
  interview" outcome status is a different concept and was left untouched.
- Front-end only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new
  dependency, no migration. Covered by a UX-tier regression
  (`tests/ux/regression/test_20260611_wizard_flow_polish.py`): a cheap static
  copy guard plus a full analyze→generate→follow-up drive that verifies the
  scroll deterministically by spying on `scrollIntoView`. That drive needed two
  new UX stubs (`fake_generate_streaming` + `fake_clarify_iteration` in
  `tests/ux/stubs.py`) — the first UX test to exercise the generate route.

### Fixed — a detached cover letter is now persisted to its run row (`fix/run-cover-letter-persistence`)

Generating a cover letter via the Step-6 "+ Generate cover letter" button left
**no DB trace**: `ApplicationRun.generated_cover_letter_md` stayed empty even
after the letter was generated and downloaded (confirmed against the e2e
walkthrough run row, which had résumé md + bullets + titles + ATS json but no
cover-letter md). The detached route `POST /api/generate-cover-letter` wrote the
letter to disk and into the context file but never touched the database. (The
*other* path — `/api/generate` with `with_cover_letter=True` — already persisted
it; the gap was exclusively the detached, common-case route.)

- **Fix.** After writing the letter, the route now persists
  `generated_cover_letter_md` onto the **same** run row the résumé generation
  wrote to (identified by `context_set["application_run_id"]`), via a new
  surgical single-column write-back (`db.persist_run.persist_cover_letter_md` +
  the `app._persist_cover_letter_to_db` wrapper, mirroring
  `_persist_corpus_generation_to_db`). Corpus-backed mode only (legacy contexts
  without a run id skip it, as `/api/generate` does), and best-effort — a DB
  hiccup logs but never fails a letter the user already downloaded.
- **Why a dedicated helper, not `persist_corpus_generation`.** That function
  unconditionally writes `generated_resume_md = result.get("resume_content")`;
  a cover-letter result carries no résumé content, so reusing it would have
  *nulled out the already-saved résumé md*. The new helper writes one column and
  leaves the résumé md untouched.
- **Why now.** B.8 Part 2 (post-public, outcome-weighted recommend) will
  correlate interviews with the cover letters that earned them; rows generated
  now without the write-back can't be backfilled, so the signal is captured
  during v1.0.6 while real outcome data accrues.
- No LLM call (the persist module stays deterministic), no `PROMPT_VERSION` bump,
  no new route, no new dependency, no migration (the column already exists).
  Covered by a unit test (no-clobber surgical write,
  `tests/test_persist_run.py`) and a route test (run-row populated end-to-end,
  `tests/test_cover_letter_detached.py`). The architecture pipeline + data-flow
  diagrams were synced to show the new write-back.

### Fixed — Step-4 / Résumé-templates copy now matches the real bundled set (`fix/step4-template-copy`, #8)

Walk finding #8 asked whether the Step-4 template-chooser copy ("Same content,
different typography and layout") still describes the bundled templates
accurately. **Verified: yes** — the four bundled templates genuinely differ in
typography *and* layout (Classic/Modern are sans-serif, Spacious/Tech serif;
Modern carries a blue header band; Tech uses float-based two-column item rows;
margins, line-heights, heading treatments and accents all vary), so that Step-4
line is left unchanged.

The verification surfaced a stale **count**, fixed here. Migration 0005 curated
the bundled set from 5 → 4 at v1.0.0 (dropped Compact, renamed Hybrid Tech →
Tech), but the Résumé-templates settings copy still claimed "Five bundled
ATS-safe templates ship with the app." → corrected to "Four". The
`docs/bundled_templates_LICENSE.md` inventory (which still listed the
nonexistent `compact.docx` / `hybrid_tech.docx` and omitted `tech.docx`) was
corrected to the curated four.

- Copy/doc only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new
  dependency, no DB change. The canonical count of 4 is already pinned at the
  data layer by `tests/test_bundled_templates.py`; the new UX regression
  `tests/ux/regression/test_20260611_step4_template_copy.py` guards the *copy*
  against drifting from the rendered bundled set.

### Fixed — Compose custom bullet order no longer reverts on reload for a no-recommendations experience (`fix/compose-order-no-recommendations`)

A saved custom Compose bullet order *visually reverted* after a Compose reload —
but only for an experience that had **no LLM recommendations**. The persisted
order was always intact (`composition_overrides.bullet_order` round-trips through
POST/GET `/composition`, and `generate()` honors it via `_stable_user_prefix`);
only the on-screen render regressed.

- **Root cause (render-only).** `_renderComposeCard` (`static/app.js`) routed a
  no-recommendations experience through `_dropoffPick`, which re-sorted the
  fallback bullets by **score** — discarding the saved order the GET had already
  applied (`get_application_composition` ranks bullets by `bullet_order` and
  stamps `in_custom_order`). The common path (recommendations present → bullets
  land in the `visible` set, preserving GET order) was unaffected.
- **Fix.** On the no-recommendations fallback path, when the experience has a
  saved order (`has_custom_order`) honor the GET-returned order (the
  `in_custom_order` bullets, already in saved sequence) instead of re-deriving a
  score sort. No backend change, no `PROMPT_VERSION` bump, no new dependency.
- Covered by a UX regression
  (`tests/ux/regression/test_20260611_compose_order_no_recommendations.py`) on a
  seeded no-recommendations experience; the companion
  `test_20260604_bullet_drag_reorder.py` continues to guard the common path.

### Added — add an alternative job title in Compose + pin it per-JD (`feat/compose-add-title`, #7)

In Step 3 (Compose) a user often realizes a *different framing* of a role fits
this JD. Until now they couldn't act on it in the wizard: the Compose titles
list was read-only, the only way to add a title was the separate Career-corpus
tab (which added it as a *non-eligible* alternate), and titles had **no** per-JD
selection at all — the generate LLM picked one by fit and the preview showed
official-or-first (walk finding #7).

- **Add a title, written into the corpus.** A "+ Add title" affordance on each
  Compose experience card writes a **sourced, immediately-eligible**
  `ExperienceTitle` (`source=user_added`, `truthful_enough_to_use=1`,
  `is_pending_review=0`) via the existing `POST /api/experiences/<id>/titles` —
  a first-class corpus item, **not** a context-only override. It appears at once
  as a selectable option for this résumé.
- **Pin which title this JD uses.** Each card's titles are now a radio group; the
  pick persists as `composition_overrides.pinned_title_ids`
  (`{experience_id: title_id}`), collected by the existing debounced composition
  autosave. Only an explicit pin is sent (mirrors `bullet_order`'s
  `data-custom-order`), so an untouched default never persists a pin or busts the
  analyze→generate cache.
- **Honored in both the preview and the generated download.** The live preview /
  corpus render (`build_json_resume_from_corpus`) resolves the title as
  **pin → official → first**; generate marks the chosen `<eligible_title
  pinned="true">` in the corpus block and a new `<corpus_mode>` rule requires the
  model to use it as that experience's `chosen_title_id` and heading (dates stay
  immutable). Because generate reads a **frozen** corpus snapshot, the
  composition save **re-syncs** `career_corpus[exp].eligible_titles` from the DB
  for pinned experiences, so a title added after analyze still reaches generate.
- `PROMPT_VERSION` → `2026-06-11.1` (the `<corpus_mode>` rule changed). Per-JD
  pin scope was a user-approved extension of the #7 row.
- Covered by route/unit tests (`tests/test_career_corpus_routes.py` add contract;
  `tests/test_application_routes.py` `TestCompositionTitlePin` persist/validate/
  re-sync; `tests/test_corpus_to_json_resume.py` `TestTitlePin`;
  `tests/test_corpus_mode_prompt.py` `TestTitlePinEmission` + the rule) and a UX
  regression (`tests/ux/regression/test_20260611_compose_add_title.py` — add a
  title, pin it, persist across a Compose reload). No new dependency.

### Added — prior applications resume from their furthest step + editable cards (`feat/prior-app-resume-robustness`, #4 + #24)

The v1.0.5 click-to-resume only offered "Resume in wizard" when a résumé had
been generated, so an application abandoned at analyze / clarify / compose was a
dead card. And prior-app cards never showed which job they were for — the
company was never captured and the proposal pill read an opaque "N pending"
(walk findings #4 + #24).

- **#4 — resume from the furthest step with data.** `_build_resume_state`
  (`app.py`) now classifies a `target_step` (1 analyze · 2 clarify · 3 compose ·
  6 download) from the rediscovered iter-0 context file — `llm_analysis`,
  `clarification_questions`/`clarifications`,
  `llm_recommendations`/`composition_overrides`, generated résumé — and ships the
  per-step payload. `resumeApplicationIntoWizard` (`static/app.js`) dispatches on
  it: Steps 1–3 rehydrate the analysis panel (and, for Step 2, the saved clarify
  Q&A) **without re-spending** `/api/clarify` or `/api/generate`; Step 6 is the
  unchanged generated-résumé path. The Resume button is now offered for every
  analyzed application, not only generated ones.
- **#24 — editable cards + legible pill.** Job title and company are now
  user-editable in the app-detail modal (save-on-blur via the new DB-only
  `PUT /api/applications/<id>/meta`, mirroring `/notes`), so a card can finally
  carry the job it's for (`Application.company` was never populated). The
  proposal pill reads **"N to review"** (was the opaque "N pending").
- Covered by route tests (`tests/test_application_routes.py` — `target_step`
  classification + `/meta`) and a UX regression
  (`tests/ux/regression/test_20260611_prior_app_resume_robustness.py` —
  analyze-only resume to Step 1; editable company + relabeled pill).

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — UI + a
deterministic DB-only route; no LLM call added).

### Fixed — "Continue to Clarify" no longer asks clarify/skip twice (`fix/clarify-double-question`, #6)

The analyze→clarify gate presented the clarify-vs-skip choice **twice**. The
analysis panel already shows it ("Continue to Clarify →" / "Skip to Compose →"),
but "Continue to Clarify" only navigated to Step 2 and showed the
`#clarifyStartRow` row — a second "Get clarifying questions / Skip" prompt for a
user who had already chosen to clarify. The onboarding walk (finding #6) flagged
this as feeling broken.

- **One action:** "Continue to Clarify →" now navigates to Step 2 **and** fetches
  the questions directly (new `continueToClarify()` wrapper). A pending indicator
  fills the panel while `/api/clarify` runs; the row is restored on failure so
  the user can retry. An idempotency guard skips re-fetching when the current
  analysis already produced questions (back-nav / re-click never re-spends the
  LLM call).
- **Untouched paths:** a direct rail click / back-nav into Step 2 still shows the
  `#clarifyStartRow` row as its single, legitimate prompt; the post-question
  `Skip` and `Submit answers, continue →` controls are unchanged. The KW4
  `merge:true` / `merge:false` answer semantics are preserved byte-for-byte
  (this fix only changes how clarify is *entered*).
- Regression-tested in the UX tier
  (`tests/ux/regression/test_20260611_clarify_no_double_prompt.py`): the CTA
  renders questions with no second click and `#clarifyStartRow` is hidden.

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — front-end flow
only; no LLM route or template touched).

### Fixed — iterate-round clarify answers no longer drop analyze-round answers (`fix/clarify-generates-bullets`, KW4)

`/api/answer-clarifications` (`submit_clarifications`) did a whole-map replace
of `context["clarifications"]`. The iteration interview submits **only** its own
textareas (`_collectIterateClarifyAnswers`), so a 2nd-round submit wiped the
analyze-round answers from the new context file — and `generate()` at iter≥1
lost them as first-person ground truth (the JS comment claimed "merges by id";
the route did not). Surfaced 2026-06-10 while building
`feat/outcome-capture-complete`; this is the mechanism behind the KW4 report
that "a later clarify round adds nothing".

- **Merge by id (default):** the route now merges answers into the existing map
  (`merge` defaults to `True`), so a later round preserves earlier answers. The
  deliberate skip-clear path passes `merge:false` to replace/clear, and the
  three JS call sites (`submitClarifications`,
  `submitIterateClarificationsAndGenerate`, `skipClarifications`) declare their
  merge intent explicitly. Whitespace-only answers are dropped and cannot
  un-answer a prior key — use `merge:false` to clear.
- **Candidate-memory mirror unaffected** — the additive DB upsert is keyed by
  question and persisted independently of the context-map merge.
- Regression-tested across two clarify rounds (`tests/test_app_clarify.py`).

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — only the data
`generate()` reads is corrected, not the prompt template).

### Added — outcome capture completed + candidate memory goes live (`feat/outcome-capture-complete`, B.8 Part 1 + KW7)

The Sprint 6.0 kickoff walk found the Applications block showing "no
applications" after a completed tailor+download, and candidate memory empty
after clarify+interview (KW7). Diagnosis against the walkthrough evidence:
the `Application` row **was** created (at analyze) but the UI never
re-rendered the block after user-select; worse, nothing in the UI could ever
set `status='submitted'`, and the outcome buttons render only on submitted
cards — so the whole outcome funnel was unreachable. Candidate memory was
designed-but-unwired: the table, read route, panel, and promote path all
existed, but no code wrote `clarification` rows from the wizard.

- **KW7 fix (UI sync):** `refreshApplications()` now fires when analyze
  creates the row and when generation updates it — the block tracks the
  wizard instead of its pre-analyze snapshot.
- **Outcome funnel entry (B.8 Part 1):** draft cards gain a **Mark
  submitted** action, and Step 6 surfaces a "Submitted this application?"
  nudge after a successful download — the moment the user takes the file to
  go apply. Outcome buttons (interview / rejection / withdrew) are unchanged
  and now reachable. **Data-model decision (user-approved 2026-06-10): lean
  single-status, `interview` is terminal** — the product's signal is "this
  résumé got a callback", not job-hunt bookkeeping past that point. No
  schema change; the v2 `ApplicationOutcome` event table remains open.
- **Queryable:** `GET /api/users/<u>/applications` accepts a validated
  `?status=` filter (single or comma-separated) — the programmatic query
  surface for the B.8 Part 2 learning layer — and the Prior-applications
  panel gains a status filter select driving it.
- **Candidate memory write path:** `/api/answer-clarifications` now mirrors
  answered Q&A into the `clarification` table (additive upsert keyed on
  candidate + application + normalized question; promoted rows never
  clobbered; legacy file-only contexts unaffected; best-effort — a memory
  failure never fails the submit). The memory panel populates live after
  clarify/interview answers, and the existing promote-to-bullet path is now
  reachable for wizard-sourced answers. LLM `context_probe` questions file
  under `experience_probe` (the DB kind enum predates them); `target_gap`
  keeps the provenance.

No new dependency. No prompt change (`PROMPT_VERSION` unchanged).

### Fixed — generate() can no longer silently alter or duplicate job dates (`fix/generate-date-grounding`, KW6)

The Sprint 6.0 kickoff walk caught the iteration regenerate "reconciling"
employment dates: it reordered experiences by JD relevance and rewrote one
role's range onto its neighbor (two titles sharing `2016 – 2018` while
`2012 – 2016` vanished), though the corpus was correct. Root cause: the
corpus-mode prompt contract made *bullets* immutable but never mentioned
*dates*, and every deterministic check scanned bullet lines only — heading
date ranges were ungoverned on both sides.

- **Prompt** (`analyzer.py`): new SYSTEM_PROMPT ALWAYS/NEVER rule (dates are
  immutable facts; reordering never rewrites them), the `<corpus_mode>`
  contract now names the `dates` attribute immutable ground truth, and the
  GROUNDING CHECK gains an OK / NOT-OK worked date pair.
  **`PROMPT_VERSION` `2026-06-01.4` → `2026-06-10.1`** (same commit). Smoke
  eval: no grounding regression (mean 4.70, all fixtures pass; see
  `evals/TUNING_LOG.md` 2026-06-10 entry).
- **Guard** (`hardening.compute_date_grounding`, deterministic, warn-only):
  heading date ranges in the generated experience section must be a
  sub-multiset of the corpus's true ranges — catches both alteration and
  duplication. Both generate routes surface flags as plain-language
  `proofread_notes` warnings (no frontend change needed) plus a structured
  `date_grounding` response field; the LLM output itself is never mutated and
  generation is never blocked. Validated against the real walkthrough chain:
  the corrupted iteration draft flags, the clean fresh draft passes.

No new dependency.

### Docs — Sprint 6.0 kickoff-walk harvest recorded (`docs/sprint6-walkthrough-findings`)

The first v1.0.6 kickoff walkthrough completed end-to-end (sprint-1 blockers
cleared the hard stops) and produced **11 findings (KW1–KW13)**, now recorded in
`docs/dev/RELEASE_ARC.md` §Phase 4.5 under Sprint 6.0 and triaged into the
existing 6.x buckets: three correctness defects (KW6 generate-date integrity,
KW7 applications/memory not updating → B.8 gate, KW4 clarify-no-bullets) join
Sprint 6.1 as new branches; KW2 bulk accept-all-pending joins 6.3; KW1 confirms
the 6.4 smart-landing; KW3/KW9/KW10 fully spec the 6.5 help primitive
(first-view modal + persistent (i)-circle) and the new-user first-run modal
sequence; KW13 panel redesign joins 6.2. Docs only — no code change.

### Fixed — onboarding E2E-walkthrough blockers, sprint 1 (`fix/onboarding-e2e-blockers`)

Five first-run onboarding issues surfaced by the end-to-end walkthrough:

- **Résumé ingest silently did nothing (the critical one).** A table/column-laid-out
  `.docx` parsed to empty text because `parser._parse_docx` read only body
  paragraphs, never table cells — so extraction got nothing and zero experiences
  landed. The ingest route nonetheless returned `201` with the error buried in the
  body, and the uploader showed a green "ready" toast over an empty corpus and never
  refreshed the list in place. Now: the parser walks the document in order and reads
  table cells (recursing into nested tables, deduping merged cells); the route
  returns `422` when a parse/extract failure lands nothing; and the uploader
  refreshes the corpus in place on success and shows an honest "No experiences found"
  warning (not a success toast) on a zero result.
- **User-selection box collapsed on an accidental header click**, stranding
  first-time users with the dropdown hidden. It is now locked open
  (`.not-collapsible`, no chevron/pointer) until a user is selected.
- **"New user" button was a confusing toggle.** It now reveals the form (not
  toggles), hides itself, and focuses the username field; a **Cancel** button
  restores it.
- **Website/LinkedIn URL boxes were ambiguous and intolerant of format.** Added a
  tolerant client-side format checker (normalizes a bare `linkedin.com/in/you` to
  `https://`, flags genuine non-URLs), clearer placeholders, and a matching tolerant
  `validate_config` server-side (accepts bare dotted hosts; still rejects `not-a-url`).
- **Wizard back-navigation** is acknowledged as missing but **deferred** to the
  monolith→blueprints split (RELEASE_ARC Phase 4.8); no behavior change this branch.

No `PROMPT_VERSION` change and no new dependency.

### Fixed — profile URLs without a scheme no longer silently fail to fetch (`fix/normalize-url-scheme`)

A site address pasted without `http://`/`https://` (e.g. `github.com/you`) made
`requests.get` raise `MissingSchema`, which `scraper.fetch_url_content` caught
and swallowed as an empty result — the URL was silently dropped from the LLM
profile context with no user-visible error. The LinkedIn/Website fields are
`type="url"` (browser-enforced scheme), but the Portfolio URLs textarea has no
such guard, so bare hosts slipped through. `scraper._ensure_scheme()` now
normalizes at the fetch boundary: a bare host gets `https://` prepended; an
explicit scheme (`http://`, `https://`, …) is left untouched. One fix covers
all three URL sources since they all flow through `fetch_url_content`. No
`PROMPT_VERSION` change and no new dependency.

## [1.0.5] — 2026-06-07

The UI/UX redesign + the diagnostics/tuning console — establishes the design
system. **Local tag** (the project stays local-only until the user-owned v1.1.0
public release). Highlights: WYSIWYG (live preview = downloaded résumé), the
Step 6 (Output) redesign, cover letters in `.docx` / `.pdf` / `.md`,
prior-application click-to-resume, user-driven Compose bullet ordering, a
Playwright UX regression suite, the template-pagination fix across all four
bundled templates, the deterministic L0 grounding metric, and the tabbed
diagnostics + tuning + annotation console — including the browser-driven
"finish the faceplate" interactive tuning loop and the standalone, LLM-free
corpus-seed export. **No `PROMPT_VERSION` change across the stream** (no
persona-constant edit landed) and **no new runtime dependency**. Deferred to
later releases by design: the calibrated grounding layers (B, pre-v1.1.0), the
no-recommendations Compose-render order edge case, and the R1-Phase-2
architecture-doc debt.

### Added — standalone one-click corpus-seed export (`feat/seed-export-button`)

Producing a corpus `seed.json` is now a one-click, **LLM-free** action in the browser.
Previously the only in-browser trigger was bundled inside the **paid** Annotate-tab
bootstrap (`POST /api/annotation/bootstrap`, ~70s/JD of Sonnet/Haiku spend); the only
no-cost path was the `python -m scripts.export_corpus_seed --user <name>` CLI. This adds
a dedicated no-cost surface. No `PROMPT_VERSION` bump (no prompt touched) and no new
dependency.

- **`POST /api/annotation/seed/export`** (`app.py`, localhost-only, synchronous JSON —
  no SSE) — reads the live DB via `scripts.export_corpus_seed.export_seed` (read-only, no
  model calls) and writes `evals/fixtures/real/<slug>/seed.json` (the source the eval
  runner's `--seed` path and the grounding backfill score against). Mirrors the score
  route's guard structure: `_is_localhost_request()` + the security trio
  (`_safe_username()` + `secure_filename()` + `_within(seed_path, ANNOTATION_ROOT)`).
  Unknown user → 400; a config-only user with no provisioned corpus → 409 (same
  needs-onboarding shape as `/api/analyze`). Default slug `<user>-bootstrap` so an
  exported seed lands where a later bootstrap / `runner.py --seed` already looks.
- **Annotate-tab "Export seed (no LLM)" button** (`dashboard/templates/dashboard.html`) —
  sits in the bootstrap section's actions row next to the paid "Run bootstrap"; reuses the
  same candidate-username / fixture-slug inputs and reports the written path + corpus
  counts. A plain fetch + status line (no SSE) since the export is fast and synchronous.
- **`_write_seed_json(fixture_dir, seed)`** (`app.py`) — factored the seed.json dump out
  of the bootstrap route so the bootstrap and standalone export share one canonical writer
  (no duplicated `json.dumps` shape). Bootstrap behavior is byte-identical.

### Docs — tuning-loop discoverability (`docs/tuning-loop-discoverability`)

Step 4 (docs only) closes the "finish the diagnostics faceplate" arc: every durable
doc and the in-app entry points now point at the now-interactive `/_dashboard`
console instead of the pre-arc read-only world. No code, no `PROMPT_VERSION` bump,
no new dependency.

- **`evals/README.md`** — new "The in-browser tuning console (`/_dashboard`)" section
  walks the four shipped surfaces as one browser-driven loop (produce → annotate →
  grounding-score → run eval → A/B → read deltas), ending at the irreversible manual
  **promote**; it is the dev-doc home for the console walkthrough.
- **`docs/walkthrough.md`** — a short "See also" flag + link telling
  users/maintainers the local diagnostics & tuning console exists and that the LLM
  prompts can be tuned there (content lives in `evals/README.md`, not embedded here).
- **`docs/dev/GROUNDING_METRIC.md`** — the deferred-calibration ("B") note now records
  that the label-*producing* loop is browser-driven (no longer CLI-only); the
  calibration itself stays the open B work.
- **`docs/dev/RELEASE_ARC.md` / `RELEASE_CHECKLIST.md`** — merge hashes backfilled
  (`feat/run-eval-from-console` `3a91bea`, `feat/tuning-tab-ab` `812e6bb`/`5f708f7`);
  the arc's checklist item is checked complete; the standalone one-click corpus-seed
  export (`feat/seed-export-button`) is tracked as the next small `feat/` branch.
- **`templates/index.html`** — the Diagnostics modal, the Diagnostics-pill tooltip,
  and the Settings-drawer line are refreshed from "Read-only telemetry" to advertise
  the interactive eval/tuning console (copy only — no behavior/layout/route change).

### Added — in-browser prompt A/B on the Tuning tab (`feat/tuning-tab-ab`)

Step 3 of the "finish the diagnostics faceplate" arc replaces the Tuning tab's
read-only stub with a real candidate-vs-baseline A/B: pick an
`analyzer._BASE_SYSTEM_PROMPTS` constant, edit its text, and run baseline +
candidate evals in the browser, then read the per-(fixture, rubric) delta. The
irreversible **promote** (edit the constant + bump `PROMPT_VERSION` + log
`TUNING_LOG.md`) stays a human/agent step — **no route edits `analyzer.py`**. No
`PROMPT_VERSION` bump (no prompt template changed) and no new dependency.

- **`POST /api/tune/run`** (`app.py`, localhost-only, SSE) — drives
  `evals.runner.run_suite` **twice** in one worker (baseline with no overrides,
  then candidate with the pasted override map), then computes the delta with the
  LLM-free `evals.tune` helpers (`load_scores` + `build_delta_table` +
  `format_delta_table`) and streams it. The candidate run self-stamps
  `prompt_version=candidate:<hash>` via `analyzer.prompt_overrides()`, so it never
  pollutes score-over-time. Mirrors `/api/eval/run`'s input contract, including the
  optional corpus-seed mode (`slug` + `username` → `evals/fixtures/real/<slug>/seed.json`,
  reusing `_safe_username` + `_within(seed, ANNOTATION_ROOT)` + `secure_filename`).
  All eager validation — bad suite, empty/missing override, an unknown prompt-constant
  name (via the canonical `prompt_overrides()` validator), unknown user, missing seed —
  returns a JSON 4xx **before any paid call** (load-bearing: baseline runs first, so a
  doomed candidate key must be caught up front).
- **Tuning-tab UI** (`dashboard/templates/dashboard.html`) — a constant picker
  (with "Load current text" to prefill the baseline), a candidate textarea,
  suite/subset/grounding controls + an optional real-seed disclosure, a 2×-cost
  `confirm()` gate (~$0.20 smoke / ~$0.60 full), phased progress, and the rendered
  delta table + a manual-promote reminder. The shared SSE streamer is generalized to
  `window.sartorEval.stream(url, params, onEvent)` (the eval-run control now rides
  it too). The `dashboard/routes.py` index passes `tune_prompts` (read-only use of
  `analyzer._BASE_SYSTEM_PROMPTS`) for the picker + prefill.

### Added — run an eval from the console; `run_suite()` core extracted (`feat/run-eval-from-console`)

Step 2 of the "finish the diagnostics faceplate" arc closes the mandatory CLI hop
in the tuning loop: you can now run an eval **from the browser** instead of
dropping to a terminal, and the collate step's paste-this `run_command` dead-end
becomes a real button. No `PROMPT_VERSION` bump (no prompt template changed) and
no new dependency.

- **`evals.runner.run_suite(...)`** — the eval orchestration is extracted from
  `runner.main()` into an importable core taking structured args (`suite`,
  `subset`, `fixture_name`, `seed_data`, `prompt_overrides_map`,
  `grounding_signals`, `out_dir`, `client`) plus an optional `progress` sartor,
  returning an `EvalRunResult`. `main()` is now a thin argparse wrapper. The
  no-flag default path is **byte-identical** (empty overrides are a no-op,
  `progress=None` makes every emit a no-op, the analyze→generate cache and the
  result-record bytes are unchanged) — mirrors how `evals/bootstrap.py` already
  splits `main()` from `run_pipeline_over_jd_texts`.
- **`POST /api/eval/run`** (`app.py`, localhost-only, SSE) — drives `run_suite`
  in a worker thread (the `annotation_bootstrap_stream` threading/queue/`_sse`
  pattern) and streams `start` / `fixture_start` / `analyzing` / `clarifying` /
  `generating` / `rubric_done` / `fixture_done` / `done` / `error`. Two modes: the
  Quality-tab run (synthetic/anchor, no seed) and the Annotate-tab "Run this
  fixture" run (`--suite real --seed <slug>/seed.json`, the in-browser collate
  command). Guarded by `_is_localhost_request()` + `secure_filename` +
  `_within(seed, ANNOTATION_ROOT)` + `_safe_username`; all validation returns a
  JSON 4xx before any paid call.
- **Console UI** (`dashboard/templates/dashboard.html`) — a "Run eval" control on
  the **Quality** tab (suite/subset/grounding, a cost-band caption, a `confirm()`
  consent gate showing the ~$0.10 smoke / ~$0.30 full estimate, reload on done);
  on the **Annotate** tab the collate result now shows the CLI command **and** a
  "Run this fixture" button. Promote stays the agent's job — no route edits
  `analyzer.py`.

### Added — run the grounding scorers from the console; bootstraps capture a seed (`feat/grounding-scorers-in-console`)

Found during a v1.0.5 walkthrough: a dev-user installed the offline grounding
scorers (`pip install -e '.[eval-grounding]'`, DeBERTa NLI + MiniCheck-FT5) and
had **no interface to use them** — the only trigger was the CLI
`--grounding-signals` flag, and the browser bootstrap hard-coded `grounding_fn=None`.
Step 1 of the "finish the diagnostics faceplate" arc makes the scorers reachable
from the `/_dashboard` **Annotate** tab, keeping them eval-time (the L1/L2
hot-path discipline in `docs/dev/GROUNDING_METRIC.md` is unchanged):

- **Opt-in on the browser bootstrap** (`app.py`, `/api/annotation/bootstrap`) — a
  "Run grounding scorers" checkbox passes `grounding_signals: true`, which wires
  `evals.grounding_signals.run_grounding_signals` into `build_bootstrap_document`.
  The scorers are pure-Python to import but lazy-load heavy deps, so a missing
  `[eval-grounding]` extra (or any scoring failure) **degrades to an un-scored
  bootstrap + a streamed `warning`**, never a 500 — the paid pipeline output is
  always preserved.
- **"Score grounding" backfill** (`/api/annotation/fixture/<user>/<slug>/score`,
  SSE) — scores an existing bootstrap's deduped bullet representatives **without
  re-running the paid pipeline**, writes them under `grounding_signals`, and
  patches any in-progress `annotations.json` score fields **by `cluster_index`
  without touching human verdicts/notes**. The annotation editor's MiniCheck/NLI
  pre-scores now light up.
- **Bootstraps capture a `seed.json`** — the browser bootstrap now snapshots the
  entire approved corpus via `scripts.export_corpus_seed.export_seed` (non-fatal
  if it can't). This is the durable source the backfill scores against (imported
  via `evals.seed_import.seeded_session`, faithful even if the live corpus is
  later edited) and the file the collate step's `--seed` run-command already
  assumed but the in-browser path never produced.

No new dependency; no `PROMPT_VERSION` bump (deterministic, no prompt change).

### Added — auto-open the default browser on launch (`feat/auto-open-browser`)

`python app.py` (and the `sartor` console script) now opens
`http://localhost:5000` in the user's default browser once the server is
listening, so they land straight on the app instead of copying the URL by hand.
A short daemon `Timer` defers the open until the socket is up; under Flask's
reloader (`FLASK_DEBUG=1`, the default) the open fires only in the serving child
(`WERKZEUG_RUN_MAIN=true`) so there's no double tab; and the call is wrapped so a
missing browser can never crash startup. Set `SARTOR_NO_BROWSER=1` to skip it
on headless / remote / CI runs.

### Changed — retire the broken "legacy import" onboarding; the corpus self-provisions (`fix/retire-legacy-import-onboarding`)

Found during the v1.0.1 → v1.0.5 walkthrough: the **Import into corpus** modal
read like pre-migration cruft, its button `POST`ed to a route that no longer
exists (`/api/users/<u>/import-legacy` → HTTP 404), and there was **no working
way to populate the corpus**. Root cause: `create_user` writes a config but
never a `Candidate` DB row, so *every* user — not just pre-migration ones — landed
in the `needs_onboarding` state whose only UI exit was that broken modal.

The onboarding gate is removed; the candidate row is now provisioned on demand:

- **Self-provisioning** — a new `_get_or_provision_candidate()` helper (`app.py`)
  creates the `Candidate` row from the user's config on the first corpus *write*
  (résumé ingest, add-experience, add-summary, persona upload, analyze), reusing
  the idempotent `import_candidate_from_config`. Both onboarding paths are open to
  a brand-new user immediately: **import a résumé** (AI extraction) **or** add
  experiences/bullets by hand — and you can mix them. The five write routes that
  returned `409 + needs_onboarding` (and summaries' `404`) now just succeed.
- **Frontend** (`static/app.js`, `templates/index.html`) — the onboarding modal,
  the `import-legacy` fetch, `openOnboardingModal` / `_renderNeedsOnboarding`, and
  the "Legacy import" error labels are deleted. The Career corpus tab always shows
  its toolbar (import **and** add-experience) with a unified empty-state hint; the
  read-only tabs (Memory / Applications / Templates) show a non-modal "Go to
  Career corpus" CTA via `_renderCorpusEmptyCTA`. All "database migration" /
  "run onboarding" / "Select a user above" copy is rewritten.
- **Tab rename** — the first tab **Application → Tailor** everywhere (label, ids
  `topTabApplication`/`tab-application` → `topTabTailor`/`tab-tailor`, the
  `switchTopTab('tailor')` handler, and `ui_pages/selectors.py` `TopTabs.TAILOR`).
- **Module rename** — `onboarding/import_legacy.py` → `onboarding/corpus_import.py`
  (and its test file) so no "legacy" name remains in the runtime path; the CLI is
  now `python -m onboarding.corpus_import`. Behavior unchanged.
- **Tests** — the four write-route "missing candidate → 4xx" tests now assert
  auto-provision success and that the row was created; their fixtures patch
  `corpus_import.CONFIGS_DIR`. The new-user UX regression asserts the working
  "+ Import résumé" affordance instead of the removed CTA.

No prompt / `PROMPT_VERSION` change, no new dependency. (Shipped CHANGELOG /
architecture / benchmark mentions of the old file-based "legacy" pipeline are
left as accurate history.)

### Changed — needs-onboarding GET reads return `200`, not `409` (`refactor/needs-onboarding-200-on-reads`, v1.0.5)

Found during v1.0.5 verification: creating the first user and clicking across
the tabs logged a cascade of `409 (CONFLICT)` console errors — one per passive
tab load (`GET …/personas`, `…/applications`, `…/clarifications`,
`…/experiences`). The read endpoints were signalling "no corpus row yet" with a
`409`, which the browser logs red regardless of how the JS handled it (every
handler already rendered the import CTA — except the persona template picker,
which showed a misleading "Failed to load templates").

A `409 Conflict` on a **read** is a misuse: asking for a not-yet-onboarded
user's list is an unmet precondition, not a state conflict. The contract now
splits by method — **reads → `200`, writes → `409`**:

- **`GET` read endpoints** (`…/personas`, `…/applications`, `…/clarifications`,
  `…/experiences`, `…/duplicates`) return `200` with an empty, success-shaped
  body plus `needs_onboarding: true`. The console stays clean and the import CTA
  still renders; a naive consumer just sees empty lists. (Mirrors the
  pre-existing `pending-counts` / `summaries` `200`-empty precedent.)
- **`POST` write endpoints** (analyze, corpus ingest, experience/persona
  create, persona preview) keep `409 + needs_onboarding` — a write precondition
  failure reasonably *is* a conflict, and they never fire on a passive load. The
  live-preview `GET` also keeps `409` (it serves an HTML iframe, not a list, and
  isn't fired pre-onboarding).
- **Frontend** (`static/app.js`): `_needsOnboarding()` is now status-agnostic
  (keys off the body flag), so the one helper covers both the `200` reads and
  the `409` writes; the six read handlers branch on the flag before treating the
  body as a collection, and two secondary `/experiences` consumers are
  `Array.isArray`-guarded against the discriminated shape.
- **Tests**: the five GET-read route tests flip `409 → 200`; a new dated UX
  regression (`tests/ux/regression/test_20260606_new_user_no_4xx.py`) seeds a
  config-only user, sweeps all four tabs, and asserts **zero** `4xx` on any
  `/api/users/<u>/…` call plus a visible import CTA. Two tab selectors
  (`TopTabs.PERSONAS` / `TopTabs.MEMORY`) + the shared CTA name were added to the
  `ui_pages` registry.

No prompt / `PROMPT_VERSION` change, no new dependency.

### Added — annotation tab + browser bootstrap wrapper: the console's first read-write surface (`feat/annotation-tab`, v1.0.5)

The last branch of the v1.0.5 stream puts the v1.0.4 eval tuning loop on the
design system: a fifth `/_dashboard` tab — **Annotate** — that produces and
labels real annotation material in-browser, ending the need to hand-edit JSON.
It reads/writes the durable Phase 3 `annotations.json` contract **verbatim**
(reusing `evals.annotation` — schema not forked), so the labels it produces are
exactly what the deferred grounding calibration needs. **No prompt /
`PROMPT_VERSION` change, no new dependency, no new LLM-call shape** (the wrapper
reuses the existing `analyze`/`clarify`/`generate` primitives unchanged).

- **The console's first READ-WRITE routes** — added to `app.py` (not the
  read-only dashboard blueprint, which stays read-only). Every route is
  **localhost-only** and gated by the security pattern: `_safe_username()` (real
  candidate) + `secure_filename(slug)` + `_within(path, ANNOTATION_ROOT)`, writing
  ONLY under `evals/fixtures/real/` (gitignored, PII-bearing):
  - `GET /api/annotation/fixtures` — list bootstrap fixtures.
  - `GET`·`POST /api/annotation/fixture/<user>/<slug>` — load the working doc
    (existing `annotations.json` or a fresh `build_annotation_template`) / save it.
    Save runs the **fail-closed `validate_annotations`** (same contract the CLI
    uses), so the on-disk file is always collation-ready.
  - `POST /api/annotation/fixture/<user>/<slug>/collate` — deterministic
    `collate_expected` + `build_improvement_brief` → `expected.json` +
    `improvement_brief.md` + an anchor `jd.txt` (runnable by `runner.py --suite real`).
  - `POST /api/annotation/bootstrap` — **browser bootstrap wrapper (SSE)**: drives
    `analyze → clarify → generate` over N pasted JDs against the live corpus
    (reusing the `/api/analyze/stream` streaming pattern + the deterministic
    `build_bootstrap_document` dedup), streaming per-JD progress, then writes
    `bootstrap.json` + the pasted JDs. Paid (Sonnet/Haiku) + slow (~70s/JD).
- **`evals/bootstrap.py`** — `run_pipeline_over_jds` refactored to delegate to a
  new `run_pipeline_over_jd_texts` (in-memory `(name, text)` JD pairs + an optional
  `progress` sartor), so the browser wrapper needs no JD temp files. CLI path is
  behavior-preserving.
- **Annotate tab UI** (`dashboard/templates/dashboard.html`) on the cb-* tokens:
  bootstrap wrapper sub-panel → fixture picker → per-cluster verdict editor
  (`keep`/`fix`/`omit`/`fabricated`, `failed_rules` constrained to the rubric
  vocabulary, `should_omit`, conditional `honest_rewrite`/`forbidden_pattern`) +
  clarification ratings; Save + Collate. Vanilla JS; fetch-streamed SSE for the
  wrapper; validation errors surfaced inline (no `console.error`).
- **Tests** — `tests/test_annotation_routes.py` (fail-closed save, traversal-slug
  containment, localhost guard, collate shape, bootstrap SSE with the LLM pipeline
  stubbed). `tests/ux/flows/test_annotation_tab.py` drives the tab in headless
  Chromium against the unconditional console-error sentinel (seed bootstrap → pick
  → fill verdicts → Save → Collate). `Dashboard` selectors + `DashboardConsolePage`
  POM extended.

### Changed — diagnostics console redesign: tabbed observability on the cb-* design system (`feat/diagnostics-console-redesign`, v1.0.5)

`/_dashboard` moves from a single long-scroll page with its own hardcoded palette
to a **tabbed diagnostics + tuning console on the cb-* design system**. Read-only
throughout — **no new Flask route, no write affordances** (the localhost
host-header guard is preserved verbatim); **no `PROMPT_VERSION` bump, no new
dependency, no LLM call.** Chart.js still loads from CDN; tabs + drawer are vanilla
JS.

- **Four tabs, each a bento of summary tiles → shared right-hand drawer.**
  Pipeline · Quality · Groundedness · Tuning. A tile shows a headline stat;
  clicking it opens one shared drawer with the full chart/table + detail. Charts
  **lazy-init on drawer-open** (never into a hidden/zero-size canvas). Every tile's
  summary *and* detail are server-rendered, so the surface degrades gracefully
  with JS off (panes stack, details show inline).
- **Groundedness tab (the marquee surface)** — designed *around* the 2026-06-06
  metric contract, not retrofitted. New `dashboard/routes.py` helpers
  `_groundedness_trend` (L0 `groundedness.score` 0–5 over time by `prompt_version`,
  **deduped by `run_id`** so a run's value isn't plotted once per rubric) and
  `_latest_groundedness_detail` (the `fabricated_specifics` drill-down:
  `flagged_samples` + `per_bullet` as the actionable evidence).
- **Tier-0 observability over data we already log** (no new data emitted):
  `_run_trace` (per-`run_id` span waterfall from `call` + `latency_ms`),
  `_reliability` (error + `max_tokens`-truncation rates, split by call kind),
  `_cost_by_call_kind` (per-stage cost rollup), and `_baseline_health` /
  `_load_baseline` (health-vs-baseline drift badges: regressed Δ<−0.5 = the
  merge-block gate, watch Δ<−0.3, else ok — read from the in-repo
  `evals/results/baseline_v1.json`).
- **Tuning tab is a read-only scaffold** — documents the `analyzer.prompt_overrides()`
  A/B primitive + links to `/prompt-tune`, `/tune-from-annotations`, and
  `evals/TUNING_LOG.md`. No forms that POST; a banner states write affordances land
  in a later, sign-off-gated branch.
- **Tests** — `tests/test_dashboard_routes.py` gains pure-helper unit coverage for
  every new aggregator (dedup-by-run_id, empty/missing-block paths, verdict bands).
  `tests/ux/flows/test_dashboard_console.py` drives the tabs + drawer in headless
  Chromium against the unconditional console-error sentinel (seeds telemetry by
  monkeypatching the blueprint's `EVAL_RESULTS_DIR` / `LLM_LOG`); a
  `DashboardConsolePage` POM joins `ui_pages/`.

### Added — L0 grounding metric: deterministic fabricated-specifics rate + groundedness composite (`eval/grounding-metric-l0`, v1.0.5)

The first slice of the grounding/hallucination metric, defined *before* the
diagnostics console is redesigned around it ("data model before the view"). This
is the **deterministic, label-free, hot-path-safe** layer (L0); the calibrated
model-based layers are deferred to pre-v1.1.0 because no labeled data exists yet
(`evals/fixtures/real/` is empty). **Deterministic only**: no `analyzer.py`/prompt
edits, no `PROMPT_VERSION` bump, no new dependency, no LLM call.

- **`hardening.py`** — new `compute_fabricated_specifics(generated_text, source_texts)`:
  a typed, severity-weighted successor to `compute_grounding_overlap`'s lossy
  `missing_samples` n-gram heuristic. Per bullet it extracts the verifiable
  *specifics* (numbers / % / $ / years / durations / named-entity & tool tokens)
  and checks each for membership in the candidate's ground-truth source union
  **with tolerance**: numeric formatting variants (`~30` / `30` / `30+`) and light
  rounding (`$2.4M ≈ $2,400,000`) read as grounded; a different magnitude
  (`~30 → 100+`) is flagged; entity tokens are alias-normalized (`k8s ≡ kubernetes`)
  first. A fabricated number outweighs a fabricated entity in the rate.
- **`hardening.py`** — new `assemble_source_union(context_set)` factored out of
  `compute_iteration_signals` (behavior-preserving): the single definition of the
  dynamic ground-truth union (primary résumé + supplementals + clarification
  answers), now shared by the iteration clarifier and the L0 check so the two can
  never score against divergent source sets.
- **`evals/runner.py`** — `_post_generation_metrics` now rides `fabricated_specifics`
  (L0 detail) and a single reportable `groundedness` composite along on **every**
  eval record (nested in `deterministic_metrics`, so attributable by
  `prompt_version` on the dashboard's score-over-time chart). The composite is
  **L0-only by default**; it enriches in place to L0+L1+L2 (NLI entailment +
  MiniCheck) only when `--grounding-signals` produced real scores. The existing
  `grounding_overlap` source set is left untouched (L0 scores against the wider
  union via a separate `source_union` arg), so existing baselines are unperturbed.
  L1/L2 behavior is read, never re-tuned.
- **Precision caveat (honest by design):** L0 is high-precision on genuinely-novel
  specifics but **will false-positive on paraphrase / implication** (source
  "managed a small team" → output "led a 4-person team" flags "4"). It is a
  **flag-for-review** signal, **not a gate**; tolerance bands are deliberately
  conservative and its precision/recall is **unproven until calibration against
  `annotations.json`** (deferred-B). See `docs/dev/GROUNDING_METRIC.md` and the
  `evals/TUNING_LOG.md` note.
- **Tests** — `tests/test_hardening.py::TestFabricatedSpecifics` (exact match → 0;
  novel number → flagged; within/out-of tolerance; `k8s`≡`Kubernetes` aliasing;
  embedded-digit non-leak; severity weighting) + `TestAssembleSourceUnion`;
  `tests/test_eval_runner.py::TestGroundednessComposite` (L0-only default +
  graceful L1/L2 enrichment). Deterministic — default `pytest`, no LLM/Chromium.

### Fixed — template pagination: blank pages + paged.js console error (`feat/template-pagination`, v1.0.5)

Blank/short pages in the **Modern**, **Spacious**, and **Tech** bundled
templates are gone, and the long-standing cosmetic paged.js console error is
fixed at the source. **Rendering-only**: no `analyzer.py`/prompt edits, no
`PROMPT_VERSION` bump, no new dependency.

- **`personas/bundled/{modern,spacious,tech}.css`** — dropped
  `section { page-break-inside: avoid; }` (present in both the base rule and the
  `@media print` block), keeping the correct per-entry
  `article { page-break-inside: avoid }`. Telling paged.js never to break inside
  a *whole section* meant any Experience section taller than the space left on
  the page got shoved wholesale onto the next page, leaving a blank/short page.
  This matches **Classic**'s proven break model (which never had the section
  rule); also added Classic's `h2 { page-break-after: avoid }` so a section
  heading is never orphaned at the foot of a page.
- **`app.py`** (`_PAGED_PREVIEW_INJECTION`) — the preview iframe now drives
  paged.js **manually** (`window.PagedConfig = { auto: false }` +
  `new Paged.Previewer().preview()` inside `try/catch` + `.catch()`). The
  bundled polyfill's auto-run `await`s `preview()` with no `.catch()`, so a
  sparse-content layout throw escaped as the uncaught
  *"getBoundingClientRect of null"* console noise; driving it ourselves contains
  it. The `pagedjs_rendered` page-count `postMessage` contract is preserved.
- **`tests/ux/`** — new regression test
  `regression/test_20260604_template_pagination.py` renders a deliberately
  multi-page résumé through all four bundled templates via the real preview
  route and asserts every `.pagedjs_page` carries content (no blank page) with a
  clean console. The `getBoundingClientRect` **allowlist in
  `tests/ux/conftest.py` is removed** — the sentinel is now unconditional, so any
  paged.js console regression fails the suite.

### Added — Playwright UX regression suite + shared `ui_pages` driver (`feat/playwright-ux-suite`, v1.0.5)

Browser-level UI regression coverage so the 2026-05-26 punch-list bugs — which
lived in JS render paths the `pytest` unit suite can't reach — can't return.
**Test-only** change: no `analyzer.py`/prompt edits, no `PROMPT_VERSION` bump,
no new dependency (Playwright was already a dependency).

- **`ui_pages/`** (new package) — a shared, framework-free Page Object Model
  over a single selector registry, consumed by *both* the new test suite and
  `scripts/capture_screenshots.py` (converged onto it, so there is **one**
  navigation source rather than two drifting copies). `base_url` is injected,
  so the same POMs drive the ephemeral-port test server and the screenshot
  script's `:5000`.
- **`tests/ux/`** — a threaded live-server + headless-Chromium harness with a
  console-error + HTTP-5xx **sentinel**; LLM-free (analyzer functions stubbed
  at the public-streaming-fn seam, so the real Flask routes still run). One
  stubbed happy-path walk (analyze → compose → template), one seeded Step-6
  WYSIWYG walk (via the prior-app-resume path), and five regression tests
  (`test_<YYYYMMDD>_<slug>.py`, never deleted): import-résumé label, rail
  re-enable after analyze, corpus-tab render, the personas-500 → iframe →
  paged.js cascade root (AGENT_FAILURE_PATTERNS §5b), and Compose bullet
  drag/keyboard reorder persistence + reset.
- **`pyproject.toml`** — new `ux` pytest marker (`pytest -m ux`); ux tests are
  also `slow`/real-Chromium and skip when the browser binary is absent, so the
  default `pytest` stays green everywhere. `tests/*` ruff ignore widened to
  `tests/**` for the nested suite.

### Added — user-driven bullet ordering on Compose (`feat/bullet-drag-reorder`, v1.0.5)

Drag-and-drop (and keyboard) reordering of bullets within each experience on
the Compose step. The chosen order is **authoritative** — it propagates into
the `<career_corpus>` block fed to `generate()`, so it shapes which bullets the
LLM keeps in a length-limited résumé, not just the on-screen list. A data-order
change, **not a prompt-template change → `PROMPT_VERSION` unchanged, no new
dependency, no LLM call** (captured as a behavior note in
[`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) instead of a version bump).

- **`analyzer.py`** — `_stable_user_prefix` honors
  `composition_overrides.bullet_order = {experience_id: [bullet_id, ...]}`,
  reordering each experience's bullets before the corpus block is emitted.
  Bullets absent from a saved order keep their relative position at the end
  (covers a bullet added via the drawer *after* ordering — never silently
  re-sorted). Absent/empty order ⇒ output byte-identical, so the
  analyze→generate prompt cache is untouched.
- **`app.py`** — the existing `POST /api/applications/<id>/composition` threads
  and validates an optional `bullet_order` into the persisted overrides; `GET`
  returns bullets in the saved order with a per-experience `has_custom_order`
  and per-bullet `in_custom_order` flag. Existing `_safe_username` + `_within`
  guards unchanged; no new route.
- **`static/app.js` + `static/style.css`** — native HTML5 drag with a grab
  handle (`≡`, grab/grabbing cursors), an Up/Down keyboard path with
  `aria-label`s (the a11y floor; no deprecated
  `aria-grabbed`/`aria-dropeffect`), a one-sentence in-interface instruction
  plus an "(i)" depth affordance, a per-experience "Reset to AI ranking"
  button, and a "newly added — drag to reposition" hint. Reorders persist via a
  debounced (~300 ms) optimistic autosave.
- **Behavior change (consistency win):** pin / exclude / add now also persist on
  the debounced autosave, not only when you click Next — the autosave sends the
  full composition state, so it can't clobber those flags.

### Added — WYSIWYG live preview (Option 1) (`feat/wysiwyg-option1`, v1.0.5)

The application preview is now byte-for-byte the future downloaded résumé once a
generate has run. A pure rendering/caching change per RELEASE_ARC Key decision 5 —
**no prompt change, `PROMPT_VERSION` unchanged, no new dependency, no LLM call.**

- **`hardening.py`** — `save_iteration_context()` caches `last_generated_json_resume`,
  the deterministic `json_resume.md_to_json_resume()` of the markdown the LLM just
  wrote, into every post-generate context. Derived from `last_generated_resume`, so
  the preview source can never drift from the download. Added to the `ContextSet`
  TypedDict.
- **`app.py`** — `GET /api/applications/<id>/preview` serves
  `last_generated_json_resume` directly when the context carries it (preview ==
  download), bypassing the pre-generate curation gate. Pre-generate it still builds
  the JSON Resume from the corpus and gates on `llm_recommendations`. A new
  `_json_resume_has_content()` guard falls back to the corpus-direct render if the
  cached doc is an empty skeleton.

### Added — Step 6 (Output) redesign + styled cover-letter preview (`feat/step6-redesign`, v1.0.5)

Finishes the Step 6 output panel and gives the cover letter a styled live preview.
A UI/rendering change — **no prompt change, `PROMPT_VERSION` unchanged, no new
dependency** (`markdown` was already a dependency), no LLM call on the new path.

- **`personas/cover_letter.html` (new)** — a shared, persona-agnostic
  business-letter shell for the cover-letter preview: terser header (no name
  banner), dense single-spaced body, addressee block inline with the body, and the
  chosen persona's font (plainly) injected via a template variable. Honors
  `@page { size: letter }` so paged.js paginates it like the résumé.
- **`pdf_render.py`** — `render_cover_letter_html()` renders generated
  cover-letter text into that shell (`markdown` + `nl2br`, so header lines keep
  single-line breaks while blank-line-separated paragraphs become `<p>` blocks);
  `persona_font_family()` extracts a persona CSS's base `font-family` (multi-line
  values normalized) with a neutral fallback. Both deterministic — no LLM.
- **`app.py`** — `GET /api/applications/<id>/cover-letter-preview` serves the
  styled cover letter from a context's `last_generated_cover_letter`, returning an
  honest placeholder until one is generated. Same guard pattern as the résumé
  preview (`_safe_username` + `_within(OUTPUT_DIR)`).
- **Frontend** — the Cover-letter tab gains a styled paged.js preview iframe with
  a "Page N of M" chip; the Step 6 résumé preview gains the same chip (reusing
  `_updatePreviewPageCount`, now source-keyed so multiple preview frames don't
  cross-talk). The "Edit before downloading" drawer is parameterized to host either
  the résumé or cover-letter editor; edits still flow through `/api/save-edits`.
  Stale "WYSIWYG coming in v1.0.2" / "styled CL lands in B3" hint copy corrected.
- The cover letter still downloads as **`.docx`**; PDF/Markdown cover-letter output
  is the next branch.

### Added — Cover-letter output formats (`feat/cover-letter-formats`, v1.0.5)

The cover-letter download now honors a chosen output format — `.docx`, `.pdf`, or
`.md` — closing the v1.0.1 placeholder (which shipped only a UI hint). An
output-format change only — **no prompt change, `PROMPT_VERSION` unchanged, no new
dependency, no LLM call** (the renderers are deterministic, P1 Hardening).

- **`generator.py`** — `generate_cover_letter()` gains an `output_format` (+
  `template_path`) param and branches like `generate_resume()`: `.md` writes the
  normalized markdown; `.pdf` renders through the shared `personas/cover_letter.html`
  business-letter shell via Playwright (`_render_cover_letter_pdf`), so the `.pdf` is
  byte-faithful to the Step-6 preview (WYSIWYG); `.docx` uses a new
  `_write_cover_letter_docx()` aligned to the 2026-05-26 business-letter decisions
  (persona font matching the chosen résumé template, dense near-single spacing, no
  name banner, inline addressee). The `.docx` and `.pdf` share one font source (the
  persona CSS). The now-unused `is_cover_letter` param was removed from `_write_docx`
  (résumé output unchanged).
- **`pdf_render.py`** — `render_cover_letter_pdf()` mirrors `render_pdf`: renders the
  shell HTML (via the existing `render_cover_letter_html`) to a temp file and prints
  it through headless Chromium, letting the shell's `@page` rule govern page geometry
  (`prefer_css_page_size`) so the PDF matches the paged.js preview. Deterministic.
- **`app.py`** — `/api/download-edited` threads the chosen format and resolved persona
  template into `generate_cover_letter` for cover-letter downloads (no new route; the
  existing `_safe_username` / `_within` / `secure_filename` guards cover the path).
- **Frontend** — a dedicated DOCX / PDF / Markdown picker in the Step-6 cover-letter
  tab (independent of the résumé's Step-5 picker — résumé and cover letter can use
  different formats); `downloadCoverLetter()` sends the chosen format + persona id.
  The satisfied "PDF & Markdown coming next" hint copy was removed.

### Added — Resume a prior application into the wizard (`feat/prior-app-resume`, v1.0.5)

Clicking a prior application now offers **Resume in wizard**, which reloads that
application's last generated state — context + persona + generated résumé/cover
letter — into the live wizard and jumps to Step 6, closing the D.3.1 placeholder.
A UI state-hydration change only — **no prompt change, `PROMPT_VERSION` unchanged,
no new dependency, no LLM call, no schema migration.**

- **`app.py`** — `GET /api/applications/<id>` gains a `resume_state` block (latest
  run's generated/edited markdown, persona, rediscovered `context_path`, iteration,
  `resumable` flag). A new deterministic, LLM-free helper
  `_find_context_path_for_run()` rediscovers the run's on-disk `context_*.json`
  (ApplicationRun has no `context_path` column) by matching the `application_run_id`
  each context file embeds, newest by iteration then mtime; every candidate path is
  `_within(OUTPUT_DIR)`-guarded. No new route — `get_application`'s existing
  `_safe_username` guard covers it.
- **Frontend** — a "Resume in wizard" button on the application-detail modal (shown
  only when a run produced a résumé). `resumeApplicationIntoWizard()` reuses
  `_onGenerationComplete` + `_renderOutput` (converging on the exact post-generate
  state, not forking it): binds the preview routes to the application, reselects the
  persona, hydrates the editors, and advances the rail to Step 6. When the on-disk
  context file is gone it degrades gracefully — editors still hydrate from the DB
  markdown and downloads work; a toast notes that the styled preview + further
  iteration need a re-generate.

## [1.0.4] — 2026-06-02

The eval tuning loop: a real-data, human-in-the-loop, model-assisted
prompt-improvement loop, gated by the offline grounding scorers and the eval
suite. Internal/dev tooling — **no user-facing pipeline change** across the
stream, and `PROMPT_VERSION` is unchanged (no persona-constant edit landed; the
loop *promotes* edits under explicit user approval, which is when a bump occurs).
Six sequential branches: the prompt-override primitive, corpus seed
export/import, the corpus-backed runner, the bootstrap engine, the annotation
contract, and the draft-and-gate tuning skill.

### Added — Eval prompt-override primitive (`eval/prompt-override-primitive`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, and `PROMPT_VERSION` is unchanged (no prompt-constant edit).

- **`analyzer.py`** — a runtime prompt-override primitive. `prompt_overrides()`
  (a context manager) injects a candidate system prompt **by name** without
  editing the persona constants; `effective_prompt_version()` returns
  `PROMPT_VERSION` on the default path but a stable `candidate:<hash>` while an
  override is active, so candidate runs are quarantined from the dashboard's
  score-over-time. The default (no-override) path is **byte-identical**: the
  call-site resolver returns the *identical* constant object and the logged
  version is unchanged, so the analyze→generate prompt cache and the
  `PROMPT_VERSION` attribution discipline are untouched.
- **`evals/runner.py`** — `--prompt-overrides PATH` threads a JSON
  `{prompt-name: override-text}` file through a run; eval result records and
  telemetry stamp the candidate version. Eager-validated — bad JSON, wrong shape,
  or an unknown prompt name exits non-zero before any paid LLM call.
- **`/prompt-tune`** — retrofitted onto the primitive: the A/B trial injects the
  candidate via `--prompt-overrides` instead of editing `analyzer.py` in place
  (removing the fragile clean-revert dependency); the constant is edited only if
  you choose Keep.

### Added — Corpus seed export (`eval/corpus-seed-export`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls.

- **`scripts/export_corpus_seed.py`** — a deterministic, LLM-free CLI
  (`python -m scripts.export_corpus_seed --user <name>`) that snapshots one
  candidate's corpus (Candidate / Experience / ExperienceTitle / Bullet /
  SummaryItem / Skill / Education / Certification + the candidate-scoped Tag
  registry and tag links) into a `seed.json` under the gitignored
  `evals/fixtures/real/`. Original DB primary keys are preserved so foreign-key
  relationships round-trip; the export is a faithful snapshot (active + inactive
  rows) — the active-only / JD-aware filtering stays in
  `build_context_set_from_db`. The `seed.json` shape (`seed_schema_version: 1`)
  is the contract the upcoming corpus-backed eval runner imports into an
  in-memory SQLite.
- **Write-path guard** — a `_within`-style resolved-path check (mirroring
  `app.py:_within`) refuses to emit anywhere except `evals/fixtures/real/`, and
  `secure_filename` sanitizes the username directory component, so the snapshot
  (which carries real PII) can't escape the gitignored tree.

### Added — Corpus-backed eval runner (`eval/corpus-backed-runner`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls. The
file-based eval path is **byte-for-byte untouched** when `--seed` is absent.

- **`evals/seed_import.py`** — a deterministic, LLM-free importer: the faithful
  inverse of `scripts/export_corpus_seed.py`. Reads a `seed.json`
  (`seed_schema_version: 1`), validates the schema version against the versions
  the importer itself supports (drift is rejected, not half-imported), and
  reconstructs the candidate's corpus into a fresh in-memory SQLite —
  **preserving the original primary keys** so the seed's tag links stay
  FK-correct with no remap table. `seeded_session()` is the ergonomic
  context-manager entry (builds the engine + schema, imports, yields
  `(session, username)`, disposes on exit). The importer does NOT pre-filter —
  inactive rows are reconstructed too; the active-only / JD-aware filtering stays
  inside `build_context_set_from_db`.
- **`evals/runner.py`** — `--seed PATH` builds each fixture's context via
  `db.build_context.build_context_set_from_db` over the imported corpus (the REAL
  corpus→context product path) instead of parsing the fixture's resume file; the
  fixture's `jd.txt` + `expected.json` still drive grading. Eager-validated — a
  bad path, malformed JSON, or unsupported schema version exits non-zero before
  any paid LLM call. Absent flag → the resolver, `_load_fixture`, and the
  context-build branch are all byte-identical to today.

### Added — Corpus bootstrap engine (`eval/bootstrap-engine`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency. The bootstrap engine
*orchestrates* LLM calls (it lives in `evals/`, off the P1 hardening boundary,
like `evals/runner.py`), but every collation step is deterministic and LLM-free.
The runner's file-based and `--seed` paths are **untouched** (zero edits to
`evals/runner.py`).

- **`evals/bootstrap.py`** — drives **one corpus seed against N JDs**
  (`--jd-dir` of `*.txt`/`*.jd` files) through the REAL product pipeline
  (`analyze` → `clarify` → `generate`, reusing the public primitives + an
  in-memory `seeded_session` import + `build_context_set_from_db`), then
  deterministically dedups the generated bullets and skills across JDs at a
  Jaccard threshold (default 0.75). The cross-JD cluster span (`size` /
  `len(jd_files)`) is the JD-invariance signal: a wide-span cluster is grounded
  core; a `size: 1` cluster is JD-specific — a `jd_pandering` candidate the next
  branch annotates. Output is a `bootstrap.json` (`bootstrap_schema_version: 1`)
  written under the gitignored `evals/fixtures/real/<candidate>/`; a `_within`
  write-path guard (mirroring `scripts/export_corpus_seed.py`) refuses to emit
  the PII-bearing snapshot anywhere else. The seed + `--jd-dir` are
  eager-validated before any paid LLM call.
- **Second `run_grounding_signals` call site** — `--grounding-signals` scores the
  deduplicated bullet cluster representatives against the corpus source text
  (DeBERTa NLI + MiniCheck-FT5, eval-only), gated on the same opt-in as the
  runner.
- **`evals/rubrics/grounding.md`** — adds the `jd_pandering` slug to the
  `failed_rules` vocabulary (a fabrication subtype: re-skinning source experience
  with a JD's domain terms not present in source). Rubric-vocabulary edits are
  eval-apparatus, **not** a prompt change — `PROMPT_VERSION` is not bumped.

### Added — Eval annotation contract (`eval/annotation-contract`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls. The
file-based, `--seed`, and bootstrap paths are **untouched**. Deterministic
collation only — it consumes `bootstrap.json`, it does not call models (P1
hardening posture, like `evals/seed_import.py`).

- **`evals/annotation.py`** — the headless, file-based annotation contract: the
  human-in-the-loop seam between `bootstrap.json` and a `--suite real` regression
  fixture. It declares `annotation_schema_version: 1` and a fail-closed
  `validate_annotations` (mirroring `evals/seed_import.py`: an unsupported version,
  missing collections, an unknown verdict, an unknown `failed_rules` slug, or a
  verdict whose required payload is absent is rejected, not half-collated).
- **Verdict enum** — `keep` / `fix` / `omit` / `fabricated`. Disposition verbs,
  each mapping 1:1 to a collation action. **Verdict-aware** requirements: `fix`
  must carry an `honest_rewrite`; `fabricated` must carry a compilable
  `forbidden_pattern` regex. The grounding *subtype* of a finding
  (`jd_pandering`, `invented_metric`, …) rides in `failed_rules`, which **reuses
  the existing rubric vocabulary** in `evals/rubrics/` — that reuse is not a
  prompt change and bumps no `PROMPT_VERSION`.
- **Template emitter** (`build_annotation_template`) — `bootstrap.json` → a blank
  `annotations.json` skeleton pre-filled with every bullet/skill cluster +
  clarification question + the inline MiniCheck/NLI pre-scores (joined by index
  from the bootstrap's `grounding_signals`), so a human annotates with the model
  pre-scores in view. The headless stand-in for the v1.0.5 annotation UI, which
  wraps this same file format — so the format is the durable contract.
- **Deterministic collation** — a completed `annotations.json` (+ its
  `bootstrap.json`) produces (a) an `expected.json` fixture matching the schema
  `evals/runner.py:_load_fixture` reads (`must_keywords` from `keep`-verdict
  skills; `forbidden_inventions` from `fabricated`-verdict patterns; `min_*_score`
  defaults/overrides; `candidate_name`; provenance `notes`) and (b) an improvement
  brief (fabrication patterns, `fix` rewrites as worked-example seeds, omissions,
  clarification ratings, and a human-vs-scorer agreement section) — the source
  material for the next branch's prompt edits.
- **CLI** — `python -m evals.annotation --bootstrap PATH --emit-template` writes
  the skeleton beside the bootstrap; `… --collate --annotations PATH --jd-dir PATH`
  **auto-writes a runnable `--suite real` fixture directory** (`expected.json` +
  the widest-span anchor `jd.txt`) plus the brief. A `_within` write-path guard
  (mirroring `evals/bootstrap.py`) refuses to emit the PII-bearing artifacts
  anywhere except `evals/fixtures/real/`.

### Added — Tune-from-annotations skill (`tuning/draft-and-gate-skill`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, no new dependency. `PROMPT_VERSION` is **unchanged by this branch**:
only a user-approved *promote* edits a persona constant and bumps the version (in
that promote commit), never the skill itself. Closes the v1.0.4 loop (export →
bootstrap → annotate → collate → **draft / eval / promote**).

- **`/tune-from-annotations`** (`.claude-plugin/commands/tune-from-annotations.md`)
  — the annotations-driven sibling of `/prompt-tune`. It reads an
  `improvement_brief.md`, drafts a candidate system-prompt edit, A/Bs it against
  the annotation-produced `--suite real` fixture (via `--seed`) **plus an
  `--suite anchor` canary**, and presents the delta tables. Built on the
  prompt-override primitive, so `analyzer.py` is untouched during the trial and
  the candidate run is logged as `prompt_version=candidate:<hash>` (quarantined
  from score-over-time). Promotion — `Edit` the constant + bump `PROMPT_VERSION`
  in one commit + a `TUNING_LOG.md` entry — happens only on an explicit "promote."
- **`tune-drafter` subagent** (`.claude-plugin/agents/tune-drafter.md`) — drafts
  the full candidate constant text from the brief + the current constant. It is
  **read-only** (`Read`/`Grep`/`Glob`; no `Edit`/`Write`) by design: it cannot
  edit `analyzer.py`, so the baseline it drafts against stays intact for an
  honest A/B, and promotion stays a user-gated step in the command — not the
  drafter's job.
- **`evals/tune.py`** — a deterministic, LLM-free delta-table helper + CLI
  (`python -m evals.tune --baseline A.jsonl --candidate B.jsonl [--json]`). Reads
  eval result JSONL, groups `status == "ok"` scores by `(fixture, rubric)`, and
  emits per-pair baseline-vs-candidate deltas (regression flag at the runner's
  `REGRESSION_DELTA`). Standalone — it consumes result files only and imports
  nothing from `runner.py`/`annotation.py`/`bootstrap.py`/`seed_import.py`, so
  their paths are untouched. `tests/test_tune.py` covers it (LLM-free).

## [1.0.3] — 2026-06-02

R1 Phase 2 stream — two-pass analyze split (speed without quality loss) +
`clarify()` → Haiku 4.5. `analyze` p50 103.2s → 67.7s (−34%), per-run cost
−12%, `clarification_quality` recovered to ≥4.20 (pm-senior) with all other
rubrics held at or above the v1.0.2 baseline. No user-facing pipeline shape
change. `PROMPT_VERSION` `2026-05-24.4` → `2026-06-01.4`.

### Changed — Two-pass analyze split, gated for speed without quality loss (`r1/analyze-split-retry`)

- **`analyzer.py`** — `analyze()` is now a two-pass orchestrator instead of one
  Sonnet call:
  - **Pass 1 — extraction (Haiku 4.5, new `EXTRACTION_SYSTEM_PROMPT`):**
    `essential_skills`, `preferred_skills`, `industry_keywords`,
    `hidden_qualities` (the typed `HiddenQualityItem` shape), `professional_vocabulary`,
    `keyword_placement`. Enforced by the new `AnalyzeExtractionResponse` model — a
    bare-string `hidden_qualities` item or out-of-enum category triggers a parse-time
    retry (the guardrail that prevents the original split's `clarification_quality`
    regression).
  - **Pass 2 — synthesis (Sonnet 4.6, under the shared default `SYSTEM_PROMPT`):**
    `comparison`, `suggestions`, `overall_strategy`, grounded on Pass 1 via an
    `<extracted_signal>` block (`AnalyzeSynthesisResponse`). Synthesis runs under
    `SYSTEM_PROMPT` (not a dedicated persona) so its cached prefix is byte-identical
    to `generate()`'s — this **reclaims the analyze→generate prompt cache** (a
    dedicated synthesis persona diverges at the system block and forces `generate`
    to re-prefill the whole corpus). The synthesis-specific framing lives in the
    user prompt, after the cached prefix.
  - `analyze()` merges both passes into the existing `AnalyzeResponse` contract.
- **`analyzer.py` `analyze_streaming()`** — re-introduces the
  `("phase", {"phase": "extraction"|"synthesis"})` SSE sentinel before each pass;
  emits a single merged `done`.
- **`app.py`** — `/api/analyze/stream` forwards the new `phase` event.
- **`static/app.js`** — the analyze stream swaps its status label per phase
  ("Extracting JD signals…" → "Analyzing positioning…").
- **Removed two unconsumed analyze keys** — `ats_improvements` and
  `ideal_resume_profile` were produced but never read (no consumer in `static/app.js`,
  `app.py`, `clarify()`, `generate()`, or any eval rubric). Actionable ATS guidance
  remains in `keyword_placement`, the deterministic `ats_warnings`, and
  `comparison.gaps` / `suggestions`.
- **`PROMPT_VERSION`** `2026-06-01.1` → `2026-06-01.3` (`.2` was the dedicated-persona
  synthesis build; `.3` moves synthesis under the shared `SYSTEM_PROMPT` to reclaim the cache).

### Changed — `clarify()` moved to Haiku 4.5 (`r1/clarify-model-trial`)

- **`analyzer.py`** — `clarify()` now runs on Haiku 4.5 (was Sonnet 4.6); a one-keyword
  change (`model=HAIKU_MODEL`), no prompt-text change. Interview-question generation is short
  structured output (3–5 questions) that Haiku handles well; the post-R1-split
  `clarification_quality` floor (ds 4.20 / pm 4.26 / sre 4.02) was the precondition the prior
  model-selection note parked the switch behind. n=5 anchor eval: `clarification_quality` held
  (medians 4.2 = the Sonnet floor; means ds 4.00 / pm 4.20 / sre 4.00, all inside the 0.5
  drop-tolerance), `clarify_retry` rate 0/15, and the parse-time `ClarifyResponse` rules
  (`context_probe` + ≥60%-combined) satisfied on every call. Per clarify call: **~57% cheaper**
  ($0.0167 → $0.0072) and **~37% faster** (p50 11.9s → 7.5s). `clarify_iteration()` stays on
  Sonnet (iteration_quality not yet stably ≥ 4.0).
- **`PROMPT_VERSION`** `2026-06-01.3` → `2026-06-01.4` (model change recorded for telemetry
  attribution).

---

## [1.0.2] — 2026-05-30

Eval apparatus stream — internal tooling establishing the regression floor
and sartor-quality measurement layer before v1.0.3 R1 prompt engineering.
No user-facing pipeline changes; `PROMPT_VERSION` unchanged at `2026-05-24.4`.

Nine branches merged since v1.0.1 (newest first):

### Added — Offline grounding signal scorers (`eval/grounding-signals`)

- **`evals/grounding_signals.py`** — new eval-only module with two offline
  grounding scorers, gated behind `python evals/runner.py --grounding-signals`:
  - `score_nli_bullets`: DeBERTa-v3-base-mnli-fever-anli (Apache 2.0, ~180 MB)
    runs NLI entailment per bullet vs source material →
    `nli_entailment_score` (0–1) + `nli_contradiction_flag` (bool).
  - `score_minicheck_bullets`: MiniCheck flan-t5-large (~3 GB on first download)
    runs factual grounding check per bullet → `minicheck_grounding_score` (0–1).
  - Both models are lazy-loaded on first `--grounding-signals` run; model weights
    are cached in the OS HuggingFace cache dir (never in the repo).
- **`pyproject.toml`** — new `eval-grounding` optional-dependency group
  (`transformers`, `minicheck`). torch must be installed separately (CPU or CUDA
  variant); see CONTRIBUTING.md.
- **`evals/runner.py`** — `--grounding-signals` flag; per-bullet results ride
  along as `grounding_signals` key on every JSONL record (null when flag absent).
- **CONTRIBUTING.md** — new "Grounding signal scorers" section documenting the
  install sequence, MiniCheck license, and model download size.

### Added — Pareto frontier dashboard panel (`eval/pareto-dashboard`)

- **`dashboard/routes.py:_pareto_data()`** — aggregates `eval_composite` JSONL
  records, joins `cost_usd` by `run_id`, computes per-version p50/p90 latency +
  cost, builds Chart.js bubble-scatter + trend datasets and a most-recent-change
  summary (Δ composite, Δ latency, Δ cost, Pareto verdict).
- **`/_dashboard` Eval Quality section** gains a Pareto frontier panel at the
  top: quality (Y, 0–5) vs wall-clock latency (X, log scale); dot size = cost;
  dashed polyline connects successive baselines. Graceful empty-state when no
  `eval_composite` records exist yet.
- 8 new tests in `tests/test_dashboard_routes.py` cover empty input, None-score
  skip, single-version, cost join, missing-cost fallback, two-version delta,
  Pareto-improving, and Dominated classifications.

### Changed — Canonical 5-status tracker schema (`chore/tracker-status-schema-cleanup`)

- **Migration 0007** — backfills `no_response → submitted` (clears wrongly-stamped
  `outcome_at`), deletes `offer` and `accepted` rows (pre-release, no real data),
  tightens `CHECK` constraint to the canonical 5-value set:
  `draft | submitted | interview | rejected | withdrawn`.
- **`app.py`** — valid set reduced to 5 values; `outcome_at` stamps on
  `{interview, rejected, withdrawn}` (adds `interview`, which the JS
  `outcomeStatuses` already expected but the Python handler never wrote).
- **`static/style.css`** — removes `.status-no_response`, `.status-offer`,
  `.status-accepted` blocks.
- **`static/app.js`** — decouples chip CSS class from chip label so `submitted`
  cards show `status-submitted` styling + "NO RESPONSE" text; removes
  `no_response` from `sentStatuses`.

### Added — Application detail modal + card timestamps (`feat/tracker-notes-and-timestamps`)

- **`PUT /api/applications/<id>/notes`** — saves freeform notes to the
  `Application` row; `GET /api/applications/<id>` now returns `sent_at`,
  `outcome_at`, `notes`.
- **Card timestamp display** — `submitted`/`no_response` cards show
  "Sent · X ago"; `interview`/`rejected`/`withdrawn` cards show
  "Outcome · X ago" using the semantic timestamp rather than `updated_at`.
- **Application detail modal** replaces the prior toast on card click: shows
  title, company, status chip, timestamps, and a notes textarea that saves on
  blur via the new endpoint.

### Added — Application outcome tracking (`eval/applications-tracker`)

- **Migration 0006** — adds `sent_at TEXT`, `outcome_at TEXT`, `notes TEXT`
  to the `application` table; expands `status CHECK` to include
  `offer | accepted | rejected | no_response`; backfills `closed → withdrawn`.
- **`app.py`** — auto-stamps `sent_at` on `submitted` transition;
  `outcome_at` on any outcome transition; summary dict exposes both timestamps.
- **`static/app.js`** — `submitted` cards gain inline "Got sartor /
  Got rejection / No response" action buttons calling
  `PUT /api/applications/<id>/status`.
- 8 new tests covering timestamp stamping, new valid statuses, and rejection
  of the removed `closed` value.

### Added — Callback-likelihood rubric + post-generation metrics (`eval/sartor-metrics`)

- **`evals/rubrics/callback_likelihood.md`** — Haiku judge with a senior
  in-house recruiter persona (200-person company, 80 résumés, 7-second skim,
  1–5 scale). Sixth rubric in the anchor suite.
- **`hardening.py`** — two new deterministic helpers (no LLM calls):
  `compute_top_third_density(resume, jd_keywords)` and
  `compute_quantification_rate(resume)`. Both ride on `_post_generation_metrics`.
- **`evals/runner.py`** — `_score_distinctiveness()` (eval-time-only Haiku call
  with graceful fallback); `_post_generation_metrics()` extended to accept
  `jd_keywords`; `eval_composite` JSONL record written per fixture after all
  rubrics grade, weighted by `evals/callback_weights.json`.
- **`evals/callback_weights.json`** — recruiter-informed prior weights:
  `keyword_coverage×2, callback_likelihood×3, ats_format×1, tone×1,
  grounding×1, clarification_quality×0.5`.
- 12 new tests for `compute_top_third_density` and `compute_quantification_rate`.

### Added — Anchor fixture suite + PR gate + JSONL schema v3 (`eval/anchor-and-pr-gate`)

- **`evals/anchors/anchor-v1/`** — immutable copy of the 3 synthetic fixtures
  (`data-scientist-junior`, `pm-senior`, `sre-mid-level`) + rubrics +
  `manifest.json`. Anchor/exploration split documented in `evals/exploration/README.md`.
- **JSONL `schema_version 3`** — per-record additions:
  `anchor_version`, `suite` (anchor|exploration), `fixture_hash`,
  `rubric_version`, `model_snapshots`, `baseline_comparison`
  (pre-computed `delta` + `within_1_stdev`), `phase_latencies_ms`.
- **`.github/PULL_REQUEST_TEMPLATE.md`** — requires eval evidence (n=3 runs,
  mean ± stdev table, Δ vs baseline, latency + cost Δ) on any `analyzer.py` /
  `evals/` prompt PR. Regression > 0.5 = blocked; latency p50 regression > 20% =
  blocked; cost regression > 20% = blocked.
- **`evals/runner.py`** — `--suite anchor|exploration` flag; regression
  alerter exits code 2 on regression (previously just a log line).
- TUNING_LOG anchor-v1 promotion-rule entry.

### Changed — Schema-version 3 baseline + 5-run aggregate (`eval/baseline-v1-0-2`)

- **`evals/results/baseline_v1.json`** — upgraded schema_version 2 → 3; adds
  per-rubric `mean / stdev / min / max / n` across 5 back-to-back synthetic runs
  at `PROMPT_VERSION 2026-05-24.4`; adds `deterministic_metrics_baseline` and
  `performance_baseline` blocks; adds `fixture_set_hash` and `model_snapshots`.
- **`evals/runner.py`** — `_load_baseline_scores` now seeds from the stable
  5-run aggregate mean (rather than the noisiest single prior run), halving
  false-alarm rate from Haiku judge variance.
- **`evals/TUNING_LOG.md`** — new `## BASELINE — v1.0.2 — 2026-05-28` entry
  with full run metadata, raw scores, deterministic metrics, green-light criteria
  status, and "known below-threshold (pre-existing)" exceptions.
- Known below-threshold at this baseline (not new regressions; recovery targets
  for v1.0.3 `r1/structural-context-probe`):
  `data-scientist-junior × clarification_quality` (mean 3.92),
  `sre-mid-level × iteration_quality` (mean 3.73, n=3 fixture fragility),
  `data-scientist-junior grounding_overlap_ratio` 0.228 (< 0.25 threshold).
- Zero judge_errors across 90 gradings; cost CV < 5% per fixture.

### Changed — Pydantic v2 response models (`eval/pydantic-response-models`)

- **`pydantic>=2.0,<3.0`** added to `pyproject.toml` dependencies.
- **Pydantic response models** in [`analyzer.py`](analyzer.py) replace the
  six `frozenset *_REQUIRED_KEYS` presence checks in `_parse_or_retry` and
  `_parse_or_retry_streaming`:
  `AnalyzeResponse`, `GenerateResponse` / `GenerateNoCLResponse`,
  `ClarifyResponse`, `RecommendResponse`, `RecommendSummariesResponse`,
  `GenerateCorpusResponse` / `GenerateCorpusNoCLResponse`.
  Collateral models for the remaining callers:
  `CoverLetterOnlyResponse`, `CritiqueResponse`, `PromoteBulletResponse`.
- **`ExtractResponse`** in [`onboarding/extract_experiences.py`](onboarding/extract_experiences.py)
  mirrors the same pattern for the Haiku extraction call.
- `_parse_or_retry` and `_parse_or_retry_streaming` now accept
  `response_model: type[BaseModel]` (replaces `required_keys: frozenset[str]`).
  On `ValidationError`, the full Pydantic error text is appended to the retry
  prompt, giving the model richer feedback than the old "missing required keys" message.

---

## [1.0.1] — 2026-05-28

User-documentation overhaul + UX polish + bug fixes surfaced by a
Playwright-driven screenshot pass against a synthetic candidate,
plus an SSE streaming pass on `analyze()` and `generate()` for
perceived-latency improvement (R2). No prompt changes —
`PROMPT_VERSION` unchanged at `2026-05-24.4` (R1 split was attempted
and reverted; see "Attempted and deferred" below).

### Added — Performance (R2 streaming)

- **`/api/analyze/stream` and `/api/generate/stream` SSE routes**
  ([`app.py`](app.py)) — wrap the existing `_call_llm` /
  `_parse_or_retry` machinery with new streaming counterparts
  (`_call_llm_streaming`, `_parse_or_retry_streaming`,
  `analyze_streaming`, `generate_streaming` in
  [`analyzer.py`](analyzer.py)). Frontend consumes via a new
  `_consumeSSE` helper in [`static/app.js`](static/app.js) that
  parses Server-Sent Events off `fetch` + ReadableStream (POST-
  capable, unlike `EventSource`).
- **Spinner-default UX with collapsible "Show progress" toggle**
  on Step 1 (Analyze) and Step 5 (Generate). The token counter
  ticks during the call so the user knows the app isn't frozen;
  the raw stream is hidden by default and revealed via a small
  toggle button. `aria-live="polite"` regions announce progress
  to screen readers. Total LLM duration is unchanged; perceived
  latency improves from "90s of blank screen" to "alive within
  ~1s and showing progress throughout."
- **3 streaming tests** in [`tests/test_analyzer.py`](tests/test_analyzer.py)
  pin the chunk → retry → done event shape (happy path, retry-
  on-parse-failure, exhausted-retry failure).

### Added — `.claude-plugin/agents/headhunter.md`

- New subagent (Sonnet 4.6, restrictive tools: Read / Grep / Glob)
  for recruiting-domain quality consultations. Reasons from
  recruiting-domain expertise (10+ years placing engineers / PMs /
  SREs at mid-to-senior levels) to diagnose what would actually
  move a candidate from ATS-pass to scheduled interview. Returns
  recruiting-domain recommendations the engineer translates into
  prompt / schema edits; does NOT propose code or prompt fragments
  itself. Created in service of the R1 quality work and retained
  for v1.0.2's prompt-tune cycles.

### Attempted and deferred to v1.0.2 — R1 analyze split

- **R1 (split `analyze()` into Haiku extraction + Sonnet synthesis)**
  was attempted on 2026-05-26 with two iterations
  (`2026-05-26.1` naive split, `2026-05-26.2` atomic-extraction +
  `context_probe` clarify fix following a headhunter-agent
  consultation). Performance was a real win (analyze p50 103s →
  ~72s, ~30% reduction) but `clarification_quality` regressed on
  both pm-senior (4.2 → 3.2 → 2.1) and ds-junior (4.2 → 4.2 → 3.2)
  fixtures vs. the clean pre-R1 baseline. The "no quality loss"
  floor was hard-binding; the R1.2 code state is preserved on the
  `r1-attempted-2026-05-26` branch as the starting point for a
  focused v1.0.2 sprint using `/prompt-tune` smaller iteration
  cycles. Full diagnosis in [`evals/TUNING_LOG.md`](evals/TUNING_LOG.md)
  entries `2026-05-24.4 → 2026-05-26.1` and `2026-05-26.1 →
  2026-05-26.2`.

### Added — User documentation

- **`docs/walkthrough.md`** — screen-by-screen guide for first-time users.
  Two Mermaid flow diagrams (user-flow + information-flow), per-step
  educational depth ("What you see / What you do / Under the hood / Verify
  before continuing"), two human review gates explicit. Each step names the
  Flask route, the `analyzer.py` function, the model (Sonnet 4.6 vs.
  Haiku 4.5), cost band, latency. Includes a `## If something goes
  wrong mid-wizard` section covering tab-close / next-day return / LLM
  errors / start-over.
- **`docs/walkthrough_example.md`** — worked example threading a synthetic
  candidate (Priya, senior backend engineer) through all six wizard steps
  against a synthetic JD (Vertica Logistics Platform, Kafka-heavy). Concrete
  decisions per step, per-call cost table summing to ~$0.22.
- **10 wizard screenshots** embedded into [`README.md`](README.md) (1 hero),
  [`docs/install.md`](docs/install.md) (1 user-picker), and
  [`docs/walkthrough.md`](docs/walkthrough.md) (8 per-step). Captured at
  1440×900 light mode from a clean app state with the synthetic Priya
  corpus. Plain-git tracked (~1.2 MB total).
- **`docs/ux/onboarding_audit_2026-05-25.md`** — first UX audit pass via the
  new `ux-onboarding-designer` subagent. Seven fixed sections (Diagram
  Critique, Screenshot Manifest, Readability Pass, Decision-Point
  Inventory, Worked-Example Specification, Failure-Mode Coverage, Rewrite
  Ladder with 8 sequenced batches).
- **`docs/ux/screenshot_capture.md`** — capture checklist + filename
  convention + post-capture markdown-insertion pattern.
- **`scripts/capture_screenshots.py`** — Playwright harness that drives the
  wizard end-to-end against a synthetic corpus, captures the 10 manifest
  PNGs, and cleans up the demo user/artefacts. ~$0.27 per full run; runs
  via `python -m scripts.capture_screenshots --headless`.
- **`.claude-plugin/agents/ux-onboarding-designer.md`** — new subagent
  (Sonnet 4.6, restrictive tool list, scope-locked Write) for future UX
  audits of user-facing documentation. Auto-discovered from the
  `.claude-plugin/agents/` directory.

### Changed — Documentation polish

- **[`README.md`](README.md)** — canonical cost anchor (`<a name="cost">`)
  added so [`docs/install.md`](docs/install.md) and [`docs/walkthrough.md`](docs/walkthrough.md)
  link to a single source of truth instead of citing inconsistent ranges
  ($0.05–$0.10 vs. $0.15–$0.25 vs. $0.30–$0.50). LLM, JD, ATS, and corpus
  defined on first use in the README body (the walkthrough already had a
  glossary at line 28, but the README is read standalone). Line-5
  disclaimer rewritten in second person to remove the double negative.
  "The two human review gates" lifted to its own subsection so the load-
  bearing UX claim isn't buried under the wizard ASCII diagram.
- **[`docs/install.md`](docs/install.md)** — cost paragraph now links to
  the README anchor. "First-run walkthrough" intro flipped from
  reference-voice to teaching-voice ("By the end of these eight steps
  you'll have your first tailored résumé"). Ubuntu 22.04+ Playwright
  `apt install` fallback added (libnss3 / libatk1.0-0 / libxkbcommon0 /
  etc.). Commit-SHA reference dropped from the malformed-JSON
  troubleshooting entry. New Anthropic-API-error troubleshooting block
  covering 4xx/5xx, network drop, rate limit, key not picked up, and
  monthly cap.
- **[`vision.md`](vision.md)** — the "one question, honestly" quote
  lifted above the Purpose metadata block so the punch lands on the
  first screen. Acronym block under the H1 defining JD/LLM/ATS.
  `PERF_ANALYZE.md` link soft-gated as `(dev-facing)`.
- **[`docs/architecture.md`](docs/architecture.md)** — the four Mermaid
  diagrams (`pipeline.mmd`, `persistence.mmd`, `data-flow.mmd`,
  `llm-routing.mmd`) embedded inline so GitHub renders them natively.
- **AGENTS.md is now canonical**; [`CLAUDE.md`](CLAUDE.md) imports it
  via `@AGENTS.md` and layers only Claude-Code-specific overrides (skill
  catalog, plan-mode hook, `CLAUDE.local.md` machine-local file).

### Fixed — UI/UX

- **Corpus import button label** — `+ Drop résumé (AI extract)` →
  `+ Import résumé`. The old label conflated drag-and-drop (one input
  affordance) with the action, and the parenthetical leaked the AI-
  extract technique into a button label. The internal route
  `/api/users/<u>/import-legacy` keeps its name (route rename deferred
  to v1.1).
- **Wizard rail step 2 stays disabled after analyze** — `runAnalysis()`
  set `lastContextPath` but did not re-render the rail, so the step-2
  button stayed `disabled class="upcoming"` until the user clicked the
  in-flow "Continue to Clarify →" button. Now `runAnalysis()`'s success
  path calls `_wizardRender()` directly. `runGeneration()` was already
  fine via its existing `_wizardAdvanceTo(6)` call.
- **Bullet-dedup gap on same-file corpus re-import** — the dedup key
  flipped from `(source, text)` to `_normalize(text)` so the source-
  prefix flip from `primary:<file>` to `supplemental:<file>` on the
  merge path doesn't slip identical text through as a new bullet.
  Observed before the fix: a 22-bullet first import became 44 bullets
  on the second import of the same `.docx`.

### Fixed — Eval harness

- **Malformed judge JSON mis-categorized as `status=ok`** — when the
  judge's response wasn't parseable JSON, [`evals/runner.py`](evals/runner.py)
  returned `{"score": 0, "reasons": [...]}` without setting
  `status: "judge_error"`. The caller's `grade.setdefault("status",
  "ok")` then silently labelled the record as a successful grading,
  firing false-positive WARN regressions against the baseline. Now the
  return dict carries `"status": "judge_error"` and the existing
  `_detect_regression` / summary-roll-up skip path handles it.

### Changed — Observability

- **`_renderCorpusList()` and `_renderCorpusSummary()` wrapped in
  try/catch with element-presence guards + per-row guards.** A silent
  throw was observed during the screenshot pass (`_corpusExperiences`
  populated with length 3, DOM never updated, list `innerHTML.length`
  ~65 chars / placeholder-sized). The instrumentation surfaces any
  future trigger via `console.error`; root cause TBD on next repro
  with DevTools open. Workaround in
  [`scripts/capture_screenshots.py`](scripts/capture_screenshots.py)
  is `page.reload()` + re-select user, which clears the bad state.

### Tests

- **`tests/test_onboarding_import_legacy.py`** — 24/24 pass.
  `test_merge_dedupes_identical_bullet_text_across_sources` replaces
  `test_merge_skips_exact_duplicate_bullet_same_source` (which
  codified the bullet-dedup bug — its name said "skips" but its
  assertion expected `len == 2`).
- **[`tests/test_eval_runner.py`](tests/test_eval_runner.py)** — 25/25
  pass. New `test_unparseable_json_marks_status_judge_error` pins the
  `judge_error` categorization.
- **Full suite:** 633 passed in ~2 min. `ruff` + `mypy` clean.

### Carried forward to next release

Items tracked in [`docs/dev/RELEASE_CHECKLIST.md`](docs/dev/RELEASE_CHECKLIST.md) as
v1.0.1 "Should do (deferred)" / v1.1 work:

- Accessibility scan of all user-facing documentation (deferred actual
  scan; alt-text drafts already in screenshots).
- Playwright UX clickthrough regression suite under `tests/ux/` (specification only).
- Corpus tab render-after-refresh bug — root-cause chase pending a
  manual repro with DevTools open.
- Eval baseline re-cut against the v1.0.1 prompt landscape (the
  `baseline_v1.json` was sourced on `prompt_version=2026-05-12.1`;
  v1.0.1 ships on `2026-05-24.4`).

---

## [1.0.0] — 2026-05-25

**First public release.** Local-first résumé tailor with:
- Unified Corpus Item pattern (Bullet + SummaryItem + ExperienceTitle as variants-with-tags-with-score-with-recommend-call)
- JSON Resume v1.0 as canonical intermediate format
- Three output formats: `.md`, `.docx` (python-docx), `.pdf` (Playwright + Chromium)
- **Four curated bundled persona templates**, all ATS-safe by construction — `classic` (Arial 11pt baseline), `modern` (rebuilt from the official jsonresume-theme-class with blue accent header band), `spacious` (Arial 11pt with generous whitespace for early-career), `tech` (rebuilt from jsonresume-theme-dev-ats with Georgia serif + centered name + underlined sections for engineering / data / AI roles). Compact and Hybrid Tech retired as not-actually-ATS-safe (sidebar layouts / inline `<code>` chips both break parsers).
- ATS-safety badges on every template card in the Template step UI — green "ATS · safe" for the 4 bundled templates; neutral "ATS · unverified" for user-uploaded `.docx` files (which we can't introspect)
- **Real in-iframe pagination** via paged.js (MIT v0.4.3, self-hosted at `static/vendor/paged.polyfill.js`) — preview shows discrete Letter-sized page boxes, not a scroll-height estimate. The "Page 1 of N" toolbar reflects the real count via postMessage.
- Live HTML preview, corpus-direct (no sidecar dependency); surfaced in Step 4 (Template) and Step 6 (Output). The Step 3 (Compose) preview was removed after hands-on testing showed it competed for attention with the bullet-curation work.
- Six-step wizard: Job → Clarify (opt) → Compose → Template → Generate → Download
- Cover-letter detachment (opt-in, post-résumé) with full refine/iterate parity
- Iterative refinement with edit-aware baselines and per-iteration audit trail
- LLM eval harness with 0.0–5.0 rubric scoring (`baseline_v1.json` pinned)
- Read-only `/_dashboard` blueprint for score trends, cost cards, failure-mode clustering

**Visual assets** (screenshots, demo GIF, onboarding HTML page) deferred to v1.0.1, after the planned UI redesign — see [`docs/PRODUCT_SHAPE.md §10`](docs/PRODUCT_SHAPE.md) for the full v1.0.1 / v1.1 / v2 deferred list.

### Changed — Phase β.6 post-review: corpus-direct live preview + PDF format + ubiquitous iframe (2026-05-24)

The β.6 hands-on review surfaced five issues, three of which shared an
architectural root cause: the live preview was coupled to a generate-
time `resume_*.jsonresume.json` sidecar, so it couldn't render until
the user had paid for at least one `/api/generate` and afterwards
reflected the last-GENERATED résumé even as the corpus kept changing.
This commit breaks that coupling and tightens the surrounding surface.

- **`corpus_to_json_resume.build_json_resume_from_corpus(session, candidate_id, *, application_id=None, context_path=None)`** — new module that builds a JSON Resume v1.0 document directly from `Candidate` + `Experience` + `Bullet` + `SummaryItem` rows. Resolves the chosen SummaryItem variant through the priority chain pinned > recommended > first-active > `Candidate.profile_text` and applies `composition_overrides` (pin / exclude / added, `pinned_summary_id`) + `llm_recommendations` from `context_path` when present. Corpus-only fields (chosen variant id, `summary_source`, `bullet_overrides_active`) live under `meta.sartor.*` so themes that don't know about sartor. extensions ignore them. 18 new tests in `tests/test_corpus_to_json_resume.py` pin the resolution chain, the bullet override math, the soft-retire skip behavior, and the empty-document fallback.
- **`/api/applications/<id>/preview` refactored** — now reads from the corpus builder instead of locating a sidecar. Drops the 409 `needs_generate` path entirely; the preview works before any generate has run. Accepts an optional `context_path` query param (validated under `OUTPUT_DIR` via `_within`) so composition state shapes the preview output.
- **`/api/users/<u>/preview` added** — the same render pipeline scoped to a user without an application. Answers the "let me see how my résumé looks through Classic / Modern" question from the Library / pre-application flow. 409 surfaces `needs_onboarding=true` when a config exists but no candidate row.
- **`_inline_persona_css` extracted** — pulls the `<link rel="stylesheet">` inlining out of the preview route body so the two preview routes share it. `_latest_jsonresume_sidecar` removed; nothing in `app.py` reads sidecars anymore.
- **PDF output format** — Step 5's format picker gains a PDF button alongside DOCX / Markdown. `/api/download-edited` now accepts `.pdf` and threads the persona's HTML+CSS companions through `generate_resume` → `pdf_render.render_pdf`. Falls back to the bundled Classic HTML when the chosen persona doesn't ship an `.html` sibling yet (same fallback the in-process generator uses).
- **Live preview ubiquitous in the wizard** — Compose (Step 3) and Output (Step 6) gain inline preview iframes alongside the existing Template (Step 4) iframe. Compose's refreshes after every pin / exclude / add (driven through `loadComposition` → `_refreshComposePreview`); Output's refreshes after every generate (`_onGenerationComplete` → `_refreshOutputPreview`). All three iframes consume the same corpus-direct route, so the WYSIWYG promise holds across steps.
- **Replaced the "PREVIEW WITH MY RESUME" .docx download** — Library tab's button label is now `OPEN PREVIEW` and opens the corpus-direct HTML in a new tab via `window.open(/api/users/<u>/preview?template_id=<id>)`. Step 4's redundant button removed; the inline iframe right below the template grid already updates on every card click.
- **PROMPT_VERSION unchanged** — no LLM prompts touched in this commit.
- **Tests** — `tests/test_live_preview_route.py` rewritten end-to-end against the new corpus-direct shape (11 cases: happy path from corpus, CSS inline, pinned-summary override via `context_path`, 404 / 400 failure modes, explicit `template_id`, the new `/api/users/<u>/preview` route). Project test count 605 → 627; `ruff` + `mypy` clean.

### Added — Phase D: Career Corpus + Candidate Memory Frontend (2026-05-14)
- **Top-level tab navigation** — four tabs replace the prior single-page layout: APPLICATION (the legacy job-flow, still wired to the file-based pipeline pending Phase F), CAREER CORPUS, PERSONA TEMPLATES, CANDIDATE MEMORY. Tabs reuse the LCARS palette; `switchTopTab()` is the central dispatch (`static/app.js`).
- **Career Corpus tab (D.1 + D.2 + D.6)** — DB-backed editor for experiences, bullets, alternate titles. Compact card list sorted by `start_date DESC` with click-to-expand; inline edit on every scalar field with save-on-change toasts; per-title atomic SET OFFICIAL that clears the prior official sibling (matches the schema's partial unique index); per-bullet auto-detect of `has_outcome` via `METRIC_RE` on save; soft-retire (`is_active=0` / non-eligible flags) preserves the `application_bullet` audit chain. Pending-review banner at the top of the tab pulls aggregate counts from `GET /api/users/<u>/pending-counts` and surfaces a REVIEW NOW button that expands + scrolls to the first card with pending content. Per-row ACCEPT and per-experience ACCEPT ALL PENDING buttons appear only when relevant content is pending.
- **Applications tab (D.3)** — within the APPLICATION tab, a PRIOR APPLICATIONS panel above the legacy chip UI lists every `application` row newest-first with status chip (color-coded across the five `application.status` values), iteration count, pending-proposal violet badge, and relative timestamp. Detail click surfaces a summary toast; resuming an application into the live editing flow defers to D.3.1.
- **Persona Templates tab (D.4)** — two-section gallery: BUNDLED (the 5 ATS-safe templates shipped in C.1, read-only DOWNLOAD) and MY TEMPLATES (user-uploaded `.docx` files with DOWNLOAD / RENAME / DELETE). Upload widget validates `.docx` and is disabled until a user is selected. Thumbnails + "set default per role tag" defer to a follow-up.
- **Candidate Memory tab (D.5)** — searchable index of every `clarification` row. 250 ms-debounced text search across question + answer; kind dropdown; outcome-rich-only toggle (`METRIC_RE` match); show-promoted toggle (hidden by default). Each card: KIND chip, OUTCOME flag (when applicable), PROMOTED badge (after promotion), origin application title, relative date; PROMOTE TO BULLET button prompts for an experience and calls the existing B.4 endpoint.
- **Backend routes added in Phase D**:
  - D.1: `GET/POST /api/users/<u>/experiences`, `GET/PUT/DELETE /api/experiences/<id>`, `POST /api/experiences/<id>/bullets`, `PUT/DELETE /api/bullets/<id>`, `POST /api/experiences/<id>/titles`, `PUT/DELETE /api/experience-titles/<id>`, `GET /api/users/<u>/tags` (autocomplete by usage count)
  - D.3: `GET /api/users/<u>/applications`, `GET /api/applications/<id>`, `PUT /api/applications/<id>/status`
  - D.5: `GET /api/users/<u>/clarifications` (q / kind / only_outcome_rich / include_promoted filters)
  - D.6: `POST /api/bullets/<id>/accept`, `POST /api/experience-titles/<id>/accept`, `POST /api/experiences/<id>/accept-all`, `GET /api/users/<u>/pending-counts`
- **Security model preserved** — every mutating route validates the candidate via `_safe_username(candidate.username)` before any write; the existing `_within()` guard continues to gate persona file writes; soft-retire (`is_active=0`) is preferred to hard-delete on bullets and titles so historical `application_bullet` / `application_run_title` joins keep their referential integrity.
- **XSS hygiene** — the new tab DOM is constructed via a small `_el(tag, props, children, attrs)` helper that uses `textContent` exclusively. No new `innerHTML` writes on user-derived values across Phases D.1–D.6.
- **Tests** — 73 new cases across `test_career_corpus_routes.py` (D.1, 35), `test_application_routes.py` (D.3, 11), `test_clarifications_list.py` (D.5, 9), `test_pending_review_routes.py` (D.6, 9). Total project test count now 446; `ruff` + `mypy` + `pytest` all clean.
- **Deferred follow-ups**: interactive tag chip editing (D.2.1), resume-application-into-edit-flow (D.3.1), persona thumbnails + per-role-tag defaults (D.4.1), focused walk-through review modal (D.6.1). Phase F will delete the file-based primary/supplemental chip UI in `static/app.js` and the corresponding `app.py` plumbing.

### Added — Iterative Refinement Loop with Edit-Aware Baselines (2026-05-11)
- **Iteration data model in `hardening.py:ContextSet`** — seven new optional fields (`iteration`, `parent_context_path`, `edited_resume_text`, `edited_cover_letter_text`, `iteration_notes`, `last_generated_resume`, `last_generated_cover_letter`), all `total=False` so pre-iteration saved contexts continue to round-trip. `save_iteration_context()` helper deep-copies a parent into a new timestamped child file (`context_{ts}_iter{N}.json`), increments the counter, links via `parent_context_path`, snapshots the freshly generated text, consumes any pending edits, and appends an `iteration_note` for audit. The chain of parent_context_path pointers is the iteration audit trail.
- **`_supplemental_block(iteration=0)` in `analyzer.py`** switches its wrapper to `<historical_resumes>` at iteration ≥ 1, folding the original primary in alongside supplementals under demotion language ("EARLIER VERSIONS ... NEVER let a historical resume override or contradict the current draft"). The `<resume>` block in the cached prefix becomes the current draft via `_current_draft_text()` (precedence: edited > last_generated > primary). `_current_cover_letter_draft()` provides the parallel for the cover letter, surfacing as a `<current_cover_letter_draft>` prompt block when iterating. `generate()` widens the grounding check to accept first-person typed edits as ground truth, with a new OK/NOT-OK worked example: "Shipped V2 to enterprise" — typed edits are citable but never extensible with specifics the candidate didn't write.
- **`clarify_iteration()` in `analyzer.py`** — fourth LLM call kind (`call_kind="iterate_clarify"`) using a dedicated `CLARIFY_ITERATION_SYSTEM_PROMPT`. Takes four signal sources documented in the plan: current draft (resume + cover letter), `recent_edits_summary` (short unified diff), `deterministic_signals` (verb diversity / specificity / grounding overlap / keyword coverage on the current draft), and `prior_clarifications` (paired question + answer for already-confirmed truths the LLM must build on, not re-ask). Introduces `iteration_probe` as a third question kind alongside `experience_probe` / `scope_probe`.
- **Three new Flask routes in `app.py`**: `POST /api/save-edits` (stores typed edits on the current context, no iteration advance, appends an iteration_note); `POST /api/iterate-clarify` (rejects iteration-0 contexts with a 400 pointing at `/api/clarify`, computes signals via `summarize_recent_edits` + `compute_iteration_signals`, calls `clarify_iteration`, appends questions with iteration-prefixed ids `iter1_q1` / `iter2_q1` so they don't collide with prior `/api/clarify` ids); `POST /api/generate` updated to write a NEW iteration context per call via `save_iteration_context` (rather than mutating in place) and return `context_path` / `iteration` / `parent_context_path` so the frontend adopts the latest snapshot.
- **`summarize_recent_edits` and `compute_iteration_signals` in `hardening.py`** — pure deterministic helpers shared between the live `/api/iterate-clarify` route and the eval harness's iteration phase. The diff helper caps at ~60 unified-diff lines per document so prompt tokens stay predictable when users rewrite large sections.
- **Frontend iteration UI** — `templates/index.html` adds a violet iteration counter pill in the top bar (hidden until iteration ≥ 1), a `GET INTERVIEW QUESTIONS` button next to `REFINE` in the Output panel, an `iterateClarifyArea` panel below the refinement controls, and an edit-detection modal (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`). `static/app.js` adds iteration state (`currentIteration`, `lastGeneratedResume`, `lastGeneratedCoverLetter`), `_detectEdits` / `_showEditModal` (Promise-based with focus trap, Esc cancel, focus restored to trigger), `_gateEditsBeforeAction` common gate used by both REFINE and INTERVIEW QUESTIONS, `runIterateClarify` / `_renderIterateClarifyQuestions` / `submitIterateClarificationsAndGenerate` / `skipIterateClarifications`, and `_onGenerationComplete` which adopts the new `context_path` per iteration. `_resetIterationState` runs on user switch and on fresh analyze so edit-detection doesn't compare against stale prior-run baselines. CSS adds `.iteration-pill`, `.iterate-clarify-area`, `.clarify-kind-badge.iteration` (teal), `.lcars-modal*` with backdrop and slide-in animation respecting `prefers-reduced-motion`.
- **Latent bug fix in `static/app.js:runGeneration`** — `refinement_notes` serialization stringified `{note,status}` entries as `"[object Object]"`. The bug was dormant (only fired with non-empty `refinementHistory`, which never happened in pre-iteration paths) but the new iterate-clarify→regenerate flow exposed it. Now filters to applied notes and uses the same shape as `submitRefinement`.
- **Accessibility pass** — skip link as first focusable, hidden `aria-live="polite"` `#srAnnounce` region with sparse meaningful announcements (analysis complete, questions ready, iteration ready, edits saved), `aria-live="polite"` on `#statusPill`, `aria-busy="true"` on the active panel during long-running LLM calls, `aria-label` on the iteration pill, `for`/`id` association on every Config form label, `aria-label` on user/JD inputs, `role="textbox" aria-multiline="true" aria-label aria-describedby` on contenteditable previews, `role="tablist"`/`role="tab"`/`aria-controls`/`aria-selected` on output tabs (with `aria-selected` maintained by `showTab`), `:focus-visible` outline rings on `.lcars-btn`, `.tab-btn`, `.view-btn`, `.format-btn`, inputs, `.preview-editable`, and `.file-chip`. The hidden `#resumeSelect` is now `aria-hidden="true" tabindex="-1"`. Manual NVDA/VoiceOver smoke pass, 200% zoom layout reflow, and color-contrast verification of the LCARS palette must be done by a human and documented when complete.
- **`evals/rubrics/iteration_quality.md`** — fifth rubric grading whether iteration questions build on prior clarifications (no `redundant_question`), reference recent edits when present (no `missed_recent_edit`), target current-draft weaknesses (no `targets_stale_draft`), and cite signal-source values accurately (no `fabricated_gap`). Same 0.0–5.0 scale and slug taxonomy as `clarification_quality.md`.
- **`evals/runner.py` iteration phase** — when a fixture has `iteration_scenarios` in `expected.json` AND `iteration_quality` is in the rubric set, the runner: (a) applies the scripted edit_target_substring → edit_replacement to the freshly generated resume, (b) builds an iteration-1 context via the same shape `save_iteration_context` would write, (c) calls `clarify_iteration` with the four signal sources, (d) grades the questions against `iteration_quality`. Re-generation from the iteration context plus re-grading against grounding/keyword_coverage is deferred to a follow-up — see the 2026-05-11.2 TUNING_LOG entry. When the scenario edit_target_substring isn't found in the LLM's actual output, the runner emits a `scenario_misaligned` row (rather than silently degrading) so the dashboard surfaces the misalignment.
- **`evals/fixtures/synthetic/sre-mid-level/expected.json`** gains `iteration_scenarios` with one scenario (`user_typed_slo_ownership`) and `expected_iteration_themes` lists tailored to it, plus `min_iteration_quality_score: 4`. The other two fixtures defer to the next eval cycle.
- **`PROMPT_VERSION` 2026-05-11.1 → 2026-05-11.2** because the new `CLARIFY_ITERATION_SYSTEM_PROMPT` shipped, the generate prompt grew the `<current_cover_letter_draft>` block and the typed-edits worked example, and `_supplemental_block` produces a different prompt at iteration ≥ 1.
- **49 new tests across `test_hardening_iteration.py`, `test_analyzer_iteration.py`, `test_app_iteration.py`** covering `save_iteration_context` lineage and edit consumption, `_supplemental_block` demotion, `_current_draft_text` precedence, `generate` consuming edited text and including the cover-letter-draft block, `clarify_iteration` system prompt threading and signal-source inclusion, `/api/save-edits` security guards, `/api/generate` writing a new iteration file with parent_context_path, `/api/iterate-clarify` rejecting iteration-0 contexts, prefix-renaming question ids to avoid collisions, and threading the four signal sources to the clarifier. All 178 tests pass.

### Added — Optional Clarification Interview Between Analyze and Generate (2026-05-11)
- **`clarify()` in `analyzer.py`** — third LLM call (optional, between `analyze()` and `generate()`) that produces 3-5 targeted questions: experience probes surfacing JD-required skills missing or weak in the resume, and scope probes disambiguating ambiguity flagged by the analyzer. Uses a dedicated short `CLARIFY_SYSTEM_PROMPT` rather than the hiring-manager `SYSTEM_PROMPT` — narrower task, tighter grounding, cheaper tokens. Reuses `_parse_or_retry` for telemetry parity; emits `call: "clarify"` in `logs/llm_calls.jsonl`.
- **`POST /api/clarify` and `POST /api/answer-clarifications`** in `app.py`, between the existing `/api/analyze` and `/api/generate`. Both routes use the standard `_safe_username` + `_within(OUTPUT_DIR)` security guards. Questions and answers persist back to the same `context_*.json` file (no new timestamped files) so the UI is refresh-safe and `/api/generate` picks up clarifications by simply reloading the existing context. `run_id` propagates from analyze through clarify to generate so all three calls share a correlation key.
- **`generate()` injects `<candidate_clarifications>` block** when `context_set["clarifications"]` is non-empty. The grounding check widens to accept clarification answers as first-person ground truth — citable in the resume even when not present in the source — but the no-invention rule still applies beyond the union of (resume + clarifications).
- **`ContextSet` TypedDict gained two optional fields** in `hardening.py`: `clarification_questions: list[ClarificationQuestion]` and `clarifications: dict[str, str]`. Both `total=False` so pre-clarify saved contexts continue to round-trip without errors. New regression test in `test_hardening.py::TestContextSetClarificationFields` proves both directions.
- **Frontend "Clarifying Interview" panel** inside the existing Analysis panel: `templates/index.html` adds a collapsible section with `GET CLARIFYING QUESTIONS` / `SUBMIT ANSWERS & GENERATE` / `SKIP` controls. `static/app.js` adds `runClarify()`, `submitClarificationsAndGenerate()`, `skipClarifications()`, and a `_renderClarifyQuestions()` helper that uses safe DOM construction (`textContent`, `appendChild`) for all LLM-supplied strings — defense-in-depth on top of `esc()`. `static/style.css` adds the violet-accented divider and question-card styles, with amber `SCOPE` badges to visually distinguish scope from experience probes.
- **`evals/rubrics/clarification_quality.md`** — new rubric grading question composition (3-5 total, ≥50% experience probes), gap citation specificity (must cite a concrete source from `essential_skills`, `comparison.gaps`, `keyword_placement`, or `keyword_overlap.missing_from_resume`), word limit (≤25 per question), no compound or leading questions, and theme coverage against the new `expected_clarification_themes` field on each fixture.
- **`evals/runner.py` runs `clarify()` between analyze and generate** on every fixture; if clarify fails, the runner logs a warning, emits a `pipeline_error` row for `clarification_quality`, and continues with the existing four rubrics ungated. The clarification questions are added to every per-rubric payload (other rubrics ignore them).
- **`evals/fixtures/synthetic/{data-scientist-junior,pm-senior,sre-mid-level}/expected.json`** each gained `expected_clarification_themes` with `experience_probes` and `scope_probes` lists tailored to the fixture's real gaps, plus `min_clarification_quality_score: 4`.
- **`_call_llm` and `_parse_or_retry` gained an optional `system_prompt` arg** so narrowly-scoped calls like `clarify` can override the hiring-manager persona without code duplication. Default behavior unchanged; the existing `analyze()` and `generate()` calls keep using `SYSTEM_PROMPT` and continue to hit the system-block prompt cache.
- **`PROMPT_VERSION` 2026-05-09.3 → 2026-05-11.1** because new system prompt, new prompt template (clarify), and the generate prompt grew the `<candidate_clarifications>` injection point.
- **New tests**: `tests/test_app_clarify.py` (route handlers, security guards, persistence, idempotency, ID filtering); `tests/test_analyzer.py` expanded with `clarify()` happy-path, retry, `system_prompt` threading, and generate's three injection paths (present, absent, all-skipped); `tests/test_hardening.py` round-trip regression for ContextSet with and without the new fields. All 129 tests pass.

### Added — Response Validation & Typed Context (2026-05-09 follow-up)
- **`_parse_or_retry` helper in `analyzer.py`** replacing the silent `{"raw_response": raw, "parse_error": True}` fallback in `analyze()` and `generate()`. The helper strips markdown fences, runs `json.loads`, and checks the response against a per-call `frozenset` of required keys (`ANALYZE_REQUIRED_KEYS`, `GENERATE_REQUIRED_KEYS`). On `JSONDecodeError` or missing keys, it re-prompts via `_call_llm` with a `<retry_reason>` block appended (`call_kind="<kind>_retry"`) — the cached user prefix is byte-identical so the retry hits prompt cache and adds ~1 cached read instead of full input tokens. After `max_attempts=2` failures it raises `LLMResponseError(raw, validation_error)` rather than degrading silently.
- **`LLMResponseError` exception** carrying the raw response and validation error. Handled in `app.py` at both LLM call sites — returns HTTP 502 with a user-readable message and the validation detail. The eval runner's existing `except Exception` block catches it and records `pipeline_error` unchanged.
- **`ContextSet` `TypedDict` and four nested TypedDicts (`CandidateInfo`, `ResumeInfo`, `SupplementalResume`, `DeterministicAnalysisBlock`)** in `hardening.py`. `build_context_set` now returns `ContextSet`; `analyze`, `generate`, `_stable_user_prefix`, `_supplemental_block`, `save_context_set`, and the `context_set` locals in `app.py` and `evals/runner.py` are all annotated. mypy now catches field-name typos at access sites instead of letting them surface as runtime `KeyError`s. No new runtime dependency — pure stdlib `typing.TypedDict`. The two app-added keys (`llm_analysis`, `run_id`) are expressed via a `total=False` subclass rather than `typing.NotRequired` to keep Python 3.10 compatibility (`NotRequired` is 3.11+).
- **12 new unit tests** in `tests/test_analyzer.py` covering `_strip_fences` across five fence patterns and `_parse_or_retry` happy path, fence-stripped happy path, missing-key recovery, invalid-JSON recovery, missing-key exhaustion, invalid-JSON exhaustion, and `_retry` call_kind attribution. Mocks `analyzer._call_llm` directly — no Anthropic SDK in the test path.
- **`PROMPT_VERSION` 2026-05-09.2 → 2026-05-09.3** because retry attempts now carry a `<retry_reason>` block in the per-call user prompt, and JSONL telemetry uses `prompt_version` for attribution.
- **`_strip_fences` consolidates** the previously-duplicated fence-stripping logic that lived in both `analyze()` and `generate()`. Net deletion of ~16 lines. Uses a single regex (`^```(?:[a-zA-Z]+)?\s*\n?(.*?)\n?\s*```$`) that handles multiline and single-line fenced blocks with or without a language tag.

### Added — Eval & Dashboard Gap-Closing (2026-05-09 follow-up)
- **`run_id` correlation** between `logs/llm_calls.jsonl` and `evals/results/*.jsonl`. The runner mints one 12-hex UUID per fixture pipeline; both the analyze and generate calls share it in telemetry, and every per-rubric eval result inherits it. Live `app.py` traffic also generates run_ids and persists them on the saved `context_set` so `/api/analyze` and `/api/generate` from a single user session correlate. New "Run" column in both dashboard tables.
- **p50 / p95 latency and per-call cost percentiles** in `_summarize_calls`. A new `_percentile` helper does linear-interpolation percentiles over sorted lists. Surfaces tail behavior that means alone hide.
- **Local regression alerting** in `evals/runner.py`. Before a run starts, `_load_baseline_scores` walks every prior result file and builds a `{(fixture, rubric): most_recent_record}` baseline. After each grading, `_detect_regression` compares the new score to baseline; drops greater than `REGRESSION_DELTA` (default 0.5, env-overridable via `REGRESSION_DELTA`) log a `WARNING` with the prior `prompt_version` and accumulate into an end-of-run summary table.
- **`evals/rubrics/keyword_coverage.md` "covered in cover letter" rule** for keywords that match `expected.forbidden_inventions` (domain experience the candidate genuinely lacks). Prevents the no-win situation where the model is forced to choose between fabricating experience (loses grounding) or omitting keywords (loses keyword_coverage). The judge now credits a B2B PM applying to healthtech for placing `EHR` and `HIPAA` in the cover letter as transferable understanding rather than fabricated experience.
- **`SYSTEM_PROMPT` "metrics" rule expanded** with concrete examples: counts ("three reports"), durations ("one year", "monthly cadence"), team or scope sizes, GitHub stars, frequencies ("week over week", "24/7 on-call"). The previous narrower rule was being read as "only %s and $s" and dropping legitimate small numbers. `PROMPT_VERSION` 2026-05-09.1 → 2026-05-09.2.
- **TUNING_LOG entry for 2026-05-09.2** documenting the gap-closing iteration: 12/12 still pass, two +0.5 improvements, two -0.6 tone "regressions" flagged by the new alerter (within Haiku judge variance band; to be confirmed across the next 2-3 runs).
- **13 new unit tests** for `_normalize_eval_record` run_id default, `_percentile` interpolation/edge-cases, `_summarize_calls` percentile fields, `_detect_regression` baseline behaviors, and `_load_baseline_scores` excluding the current file. 96/96 tests passing total.

### Added — Eval & Dashboard Refinement (2026-05-09)
- **Float scoring (0.0–5.0, one-decimal precision)** across all four rubrics. Replaces the previous integer 0–5 scale; same band semantics, ~10× the granularity. The Haiku judge can now express "stronger than 4 but short of 5" as `4.3` instead of collapsing to `4` or `5`. Rationale: integer scoring hid real prompt-tuning progress and forced false equivalence between near-passing and clean-passing runs.
- **`schema_version` field** on every eval result (`schema_version: 2`). Old integer-score records load through `dashboard.routes._normalize_eval_record` which coerces them to floats and fills defaults; stored files are never rewritten.
- **Four deterministic post-generation metrics in `hardening.py`** computed on every eval run:
  - `compute_verb_diversity` — unique leading verbs / total bullets; flags repetition that the SYSTEM_PROMPT already discourages
  - `compute_specificity_density` — fraction of bullets containing a quantifier; pairs with grounding (high density + low grounding = invented numbers)
  - `compute_grounding_overlap` — 3-gram overlap between generated output and source. Returns up to 10 `missing_samples` 3-grams that the LLM produced but source doesn't contain — these are the actionable fabrication signals. Stopword-only n-grams excluded.
  - `compute_call_cost` — per-call USD using a `MODEL_PRICING` table for Sonnet 4.6 and Haiku 4.5
- **`prompt_version`, `deterministic_metrics`, `cost_usd`, `pipeline_latency_ms` fields** on every eval result, enabling regression attribution to specific prompt revisions.
- **Dashboard charts and aggregations** (no new Python deps; Chart.js loaded from CDN):
  - Per-rubric pass-rate bar chart
  - Score-over-time line chart with per-point `prompt_version` tooltip
  - Rubric × fixture heatmap (HSL color, red→green)
  - Top failure-modes table (per-record dedup of `failed_rules` slugs)
  - Total-cost and mean-cost-per-call summary cards
  - Graceful degradation: heatmap and failure-mode table render server-side; only bar/line charts require JS
- **Anti-invention prompt edits** in `analyzer.py` (`SYSTEM_PROMPT` and `generate()` GROUNDING CHECK): three new ALWAYS/NEVER rules and three OK/NOT-OK worked-example pairs targeting the failure patterns observed on `data-scientist-junior` (advanced-technique substitution, tool-vendor specificity, scope adjective escalation). `PROMPT_VERSION` bumped from `2026-05-06.5` to `2026-05-09.1` in the same commit.
- **`evals/TUNING_LOG.md`** — institutional-memory document recording each prompt iteration with what changed, why, scores before/after, and what we learned. Seeded with the 2026-05-09 anti-invention iteration (12/12 pass on synthetic suite, $1.46 total cost).
- **`dashboard/README.md`** — what the dashboard shows, how to launch it, schema-version compatibility notes, instructions for adding a new chart.
- **35+ new unit tests** (`tests/test_eval_runner.py`, extended `tests/test_hardening.py`, new `tests/test_dashboard_routes.py`) covering float coercion at the judge boundary, deterministic-metric edge cases, dashboard aggregations, and graceful-degradation rendering with no eval data.
- `pyproject.toml` replacing `requirements.txt` (pinned dep ranges + `[dev]` extras)
- `tests/` with 28 unit tests covering the deterministic helpers and path-traversal defenses
- GitHub Actions CI workflow (`ruff` + `mypy` + `pytest`, label-gated synthetic eval smoke)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub issue and PR templates
- `.claude-plugin/` scaffold: `plugin.json` manifest, three migrated plan-mode hooks, five new deterministic hooks (`block-secrets`, `ruff-changed`, `block-merge-to-main`, `validate-context`, `route-security-lint`)
- Three project subagents: `eval-judge` (Haiku, grading), `prompt-archaeologist` (Sonnet, prompt-failure diagnosis), `git-flow` (Sonnet, conventional-commit workflow)
- Five project skills: `/eval`, `/replay`, `/prompt-tune`, `/bench`, `/inspect-context`
- Eval harness under `evals/`: `runner.py`, four rubrics (grounding, keyword_coverage, ats_format, tone), three synthetic fixtures (sre-mid-level, pm-senior, data-scientist-junior), JSON Schema for `context_set`
- LLM telemetry: `analyzer.py` emits one JSONL record per call to `logs/llm_calls.jsonl` with timestamps, tokens (including `cache_creation_input_tokens` / `cache_read_input_tokens`), latency, prompt version, status
- Prompt caching: stable user-message prefix (resume + JD + supplementals + candidate profile) sent as a cacheable text block per call. Verified live: ~4,300 cached input tokens read on every generate call within the 5-minute TTL, ~37% input-token cost reduction across an analyze + generate + refinement-generate sequence
- Template-faithful docx output: `generator._write_docx` now walks the original resume's first ~30 paragraphs and captures formatting prototypes per role (name, subtitle, contact, section_heading, job_title, job_subtitle, body), then applies them to the matching markdown elements. Right-aligned date column on `### ` lines is preserved via the captured tab stop. Required for templates that use direct paragraph formatting rather than Word named styles.
- Dashboard blueprint at `/_dashboard` reading the JSONL telemetry and eval results into two filterable tables; localhost-only
- `PROMPT_VERSION` constant in `analyzer.py`; bumped on any `SYSTEM_PROMPT` change so eval results trace to a specific revision
- Project allowlist in `.claude/settings.json` for the `ruff`/`mypy`/`pytest`/`pip show` dev loop

### Changed
- `app.py` Flask debug flag is now env-driven (`FLASK_DEBUG`, default-on for dev). Set `FLASK_DEBUG=0` to disable for any future hosted deployment.
- Type annotations cleaned up across `analyzer.py`, `generator.py`, and `parser.py` to satisfy `mypy --strict-optional`.
- `CLAUDE.md` is now project-shared (committed) — was machine-local. Per-clone overrides moved to `CLAUDE.local.md` (gitignored).
- `.claude/launch.json` removed from tracking (had a hardcoded Windows path); kept locally and gitignored.
- `.gitignore` rewritten for `.claude/*` allow-list pattern: future Claude Code internals (worktrees, caches) auto-ignored; only `settings.json` is tracked.
- README install commands now use `pip install -e .` instead of `pip install -r requirements.txt`.
- README gains a "Claude Code Plugin" discovery section listing all commands, agents, and hooks.
- Hook wiring lives in `.claude/settings.json` rather than the plugin manifest, since Claude Code v2.1.131 in VSCode doesn't support `/plugin install` for local paths. The `.claude-plugin/` layout is preserved for future marketplace publication.
- `analyzer.py:MODEL` upgraded from `claude-sonnet-4-20250514` (May 2025 Sonnet 4) to `claude-sonnet-4-6`. Same per-token price; better structured-output adherence and instruction-following on the long generate prompt. Rationale comment added near the constant documenting the model-selection trade-offs (Sonnet for analyze/generate, Haiku for high-volume structured grading, no Opus for cost reasons). `PROMPT_VERSION` bumped to `2026-05-06.5` so telemetry distinguishes pre-/post-bump runs.
- `analyzer.py:MAX_TOKENS` raised from 4096 to 8192. Sonnet 4.6's analyze() output is more verbose than older Sonnet 4 was on detail-rich real inputs and was hitting the 4096 cap mid-JSON, surfacing as a downstream "non-JSON response" error. 8192 leaves headroom; the model still uses what it needs.

### Removed
- `requirements.txt` (superseded by `pyproject.toml`)

### Fixed
- `generate()` prompt now requires explicit `# / ## / ### / -` markdown markers on resume_content output. Without these markers the document writer fell back to undifferentiated plain paragraphs, losing template heading visual styles. Prompt was unchanged across the v0.1.x line; making the marker requirement loud is the fix.
- `_write_docx` no longer materializes empty markdown lines as empty paragraphs. The resulting double-gap between `## SECTION` headings and their body content was visible in every multi-section docx output. Templates' per-paragraph `space_after` provides the visual rhythm; empty paragraphs were stacking on top of it.
- `_call_llm` now logs a warning and records a `stop_reason` field in `logs/llm_calls.jsonl` whenever the model hits `max_tokens`. Previously a truncated JSON response surfaced as a confusing parse error in the UI; now truncations are visible directly in the telemetry stream.

### Known issues
- Junior-level fixtures (e.g., `evals/fixtures/synthetic/data-scientist-junior`) can score below the grounding rubric's pass threshold of 4 due to the model inflating an analyst's actual scope to match a more senior JD (slugs: `scope_inflation`, `verb_overreach`, `invented_metric`). Pre-existing across the v0.1.x line — surfaced for the first time by the new eval harness. To be addressed via prompt tightening in v0.2.1; the `prompt-archaeologist` subagent is the intended workflow.

---

## [0.1.0] — 2026-05-06

Initial public release.

### Added
- Two-call LLM pipeline (`analyze()` + `generate()`) producing tailored resume + cover letter from a job description
- Refinement scope validation via Haiku classifier
- Streaming LLM calls for warm-connection long-running generations
- Multi-resume source pool with primary/supplemental selection in the UI
- Full candidate profile injection into both LLM calls (skills, certifications, education, notes, scraped LinkedIn/portfolio content)
- Deterministic hardening layer: keyword extraction, ATS format checks, keyword overlap scoring, context-set assembly
- Resume parsing for `.docx`, `.pdf`, `.md` with section inference
- Document generation preserving the original `.docx` as a style template
- Two human-gated review checkpoints (analysis review, output review) per the P8 Strategic Human Gate principle
- LCARS-styled single-page UI
- MIT license, comprehensive `.gitignore`, `SECURITY.md`, `README.md`, `vision.md`
