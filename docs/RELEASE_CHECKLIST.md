# Release Checklist — callback.

> **Purpose:** the ship-list. What must be true before tagging a release,
> in what order, to what quality bar. The verify-before-ship gates.
> **Audience:** humans driving a release; LLMs proposing version-bump
> work or release-blocking fixes.
> **Authoritative for:** the v1.0.0 / v1.x release definitions; the
> minimum-bar tests / ruff / mypy / eval gates; which items are
> shipping-blockers vs nice-to-haves.
>
> **Companion:** see [`docs/PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) for the
> unified Corpus Item pattern this checklist works toward (cover
> letters optional, master résumés per role, PDF output via
> Playwright, JSON Resume v1.0 as canonical intermediate, live
> preview).

The notes below are the committed scope for the
`feat/release-visual-ia` → release-readiness arc. Each item is sized
for an independent commit; check them off in order, but most can be
parallelised across people/agents.

This file lives in `docs/` so it ships with the repo (gitignored
counterpart `docs/RELEASE_CHECKLIST.local.md` exists if you need to
note environment-specific things you don't want in history).

---

## A. Codebase hygiene

### A.1 — PII scrub of git history (must do before public release)

**Why:** the project moved from solo prototype to release-ready while
real candidate data was in the loop. `configs/*.config`,
`resumes/{user}/`, `output/{user}/`, `evals/fixtures/real/`, and
`logs/llm_calls.jsonl` are gitignored *now*, but earlier history
may contain bullets, emails, phone numbers, addresses, or job
descriptions for real applications.

**Plan:**
1. Run `git log --all --full-history -- configs/ resumes/ output/
   evals/fixtures/real/ logs/` to find any commits that touched
   those paths.
2. Search blob contents for PII patterns:
   ```bash
   git rev-list --all | while read sha; do
     git ls-tree -r $sha | grep -E '\.(config|md|txt|json|jsonl)$'
   done | sort -u | head
   git log -p --all | grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | head
   git log -p --all | grep -nE '\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}' | head
   ```
3. If any hits land: `git-filter-repo --invert-paths --path configs/
   --path resumes/ --path output/ --path evals/fixtures/real/`.
   (Prefer `git-filter-repo` over `git filter-branch` — it's the
   officially recommended tool now.)
4. Force-push to a clean remote (mint a fresh repo URL if the
   project was ever public; do NOT force-push over a public history
   that other people may have cloned).
5. Re-add the deliberate test fixtures (`evals/fixtures/synthetic/`,
   `testuser` skeleton). Verify CI green on the rewritten history.
6. Rotate any secrets that may have been committed. Grep for
   `sk-ant-`, `anthropic`, `bearer `, `api_key`, `password`, plus
   any custom secret prefixes. Document the rotation in
   `SECURITY.md`.

**Acceptance:** `git log -p --all` produces no email addresses,
phone numbers, or candidate-specific bullets outside `synthetic/`
and `testuser/`.

### A.2 — Stray-code sweep

**Why:** the codebase accumulated dead UI (the LCARS bottom bar,
token pill), legacy paths, debug `console.log`s, commented-out
blocks, and inconsistent file headers during rapid iteration. A
focused pass before release.

**Plan:**
1. **Static JS:** `grep -nE 'console\.log|console\.debug|TODO|FIXME|
   XXX' static/app.js` and resolve each. Console logs that are
   useful for prod observability should go through the `_announce`
   / status-pill path; everything else deletes.
2. **Dead CSS:** scan `static/style.css` for selectors that no
   templates reference any more. Candidates to check:
   `.lcars-elbow*`, `.lcars-title`, `.lcars-bar-bottom`,
   `.lcars-block`, `#tokenInfo` (already gone), per-color
   `.lcars-bg-*` variants on panel headers (overridden but rules
   still present). Decide: delete or leave with a `/* dead — kept
   for ... */` comment.
3. **Dead Python:** `python -m vulture . --min-confidence 80`
   (one-time dev dep), or `grep -RnE 'TODO|FIXME|XXX|HACK' --include='*.py'`
   and triage. Anything < 6 months old that says TODO and isn't
   actively tracked: file an issue or delete.
4. **Commented-out blocks:** delete (`git blame` is the history).
   Exception: scaffolding for the next phase explicitly noted as
   such.
5. **File headers:** every `.py` should have a 1–3 line docstring
   stating intent. Every CSS section should have the `/* ====
   region heading ==== */` banner used in style.css. Inconsistent
   ones — bring them into line.

**Acceptance:** ruff + mypy clean, pytest green, manual scan of
`app.py` / `analyzer.py` / `static/app.js` finds no obvious dead
code.

### A.3 — Semantic naming consistency

**Why:** mixed conventions (`_resetIterationState` vs
`refreshApplications` vs `_renderTemplatePicker`) crept in across
the JS file; same with Python (`_safe_username` vs
`secure_filename` reuse). Inconsistency makes the codebase look
younger than it is.

**Plan:**
1. **JS naming convention:**
   - Public functions: `camelCase` (`loadComposition`,
     `wizardGoTo`).
   - Private helpers: `_camelCase` leading underscore
     (`_wizardRender`, `_toSentence`).
   - DOM-element IDs: `camelCase` (`statusPill`, `userSelect`).
   - CSS classes: `kebab-case` (`cb-wordmark`, `wizard-step`).
   - Constants: `UPPER_SNAKE_CASE` (`_WIZARD_PANELS`,
     `_WIZARD_STEP_LABELS`).
   Grep for outliers; rename in-place with `git mv`-equivalent
   refactors. Update the contributor README section accordingly.
2. **Python:** `snake_case` everywhere, leading underscore for
   module-private. Reuse `_safe_username` + `_within` everywhere
   the filesystem is touched (the `route-security-lint` hook
   enforces this on `app.py` already — extend coverage if any
   blueprints land).
3. **CSS:** all custom properties under the `--cb-*` or token
   namespaces defined in `:root`. Components prefixed `.cb-` for
   the callback. design system; legacy `.lcars-*` kept as
   redirect aliases until the next major refactor.

**Acceptance:** a fresh reader can predict whether a symbol is
public/private/constant from its case without grepping.

### A.4 — CSS cleanup

**Why:** `static/style.css` grew to ~2700 lines mixing LCARS
heritage, Phase D additions, the callback. token system, and
component overrides. Some sections are visually similar to others
because rules duplicate.

**Plan:**
1. Group all `--cb-*` tokens at the top, alphabetised by family
   (surface, fg, brand, functional, radius, edge, shadow, gradient,
   motion). They're already there but spot-check.
2. Inventory rules using `var(--amber)` / `var(--teal)` /
   `var(--text-dim)` etc. — these still resolve via aliases. Each
   one is a candidate to migrate to a token directly (`--brand`,
   `--success`, `--fg-1`). After migration, document remaining
   alias usage.
3. Extract the callback. layer (currently appended at the bottom
   under `=== callback. component layer ===`) into a stable
   section. Comment each block with its purpose and where in the
   UI it surfaces.
4. Delete confirmed-dead selectors found in A.2.
5. Ensure every interactive element has all three states styled:
   rest / hover / active. Use the same shadow stack pattern
   (`--edge-top` + `--shadow-1` + brand glow as applicable).

**Acceptance:** `wc -l static/style.css` drops or stays flat;
every selector in the file can be traced to either the templates
or the live JS in under 30 seconds.

---

## B. Phase 2 — remaining visual polish

The Phase 1 token bind already flips the major surfaces (topbar,
panels, wizard rail, buttons). Phase 2 brings the per-feature
surfaces into the same finished language.

- [ ] **Compose step** — `.exp-card`, `.bullet`, `.score-chip`,
  `.compose-experience` — apply gradient surfaces, edge highlight,
  recommended-stripe accent, drawer cascade reveal. Mirror the
  mockup exactly.
- [ ] **Applications list** — `.application-card` — gradient
  surface, the same edge stack, ITER badge with brand pill,
  pending-proposal violet treatment refined.
- [ ] **Template picker** — `.template-pick-card` — selected state
  uses brand-soft halo + edge-top, hover lifts 1px, the picker is
  a card grid not a select.
- [ ] **Corpus tab** — `.experience-row`, `.bullet-row` editors,
  duplicates merge UI, the + Drop résumé button. Sentence case,
  the same chip + button language.
- [ ] **Memory tab** — `.memory-card` for clarifications, promote
  affordance refined.
- [ ] **Modals** — `formModal`, `errorModal`, `diagnosticsModal`,
  `onboardingModal` — gradient surface, refined edges, sentence-case
  titles (done in Phase 1c).
- [ ] **Settings drawer** — Profile form, resume templates list,
  diagnostics link. Same form-field treatment as Phase 1.

---

## C. Documentation pass

A staged, audience-segmented plan. The target user shapes where the
doc lives and how it reads.

### C.1 — User-facing (`README.md` rewrite + `docs/install.md`)

Audience: a candidate or hiring-team member who heard about
callback. and wants to try it.

Must include:
- **What is callback.** — one paragraph, three sentences, plain
  English. Mention what it doesn't do (it doesn't apply to jobs,
  doesn't send emails, doesn't store data off-device).
- **A 60-second install.** Clone, `pip install -e .`, drop your
  API key into `.api_key`, `python app.py`. One screenshot of the
  result.
- **The flow in five screenshots:** Import → Job + Analyze →
  Clarify → Compose → Generate. Each screenshot's caption is
  one sentence. Generated by the canon script in
  `scripts/screenshot.py` so they're rerunnable.
- **What gets saved on your machine.** The three layers:
  `resumes/{user}/`, `output/{user}/`, `db/resume.sqlite`. State
  it explicitly because users worry about this.
- **API key + cost.** Anthropic API; rough per-application cost
  estimate ($0.05–$0.30 depending on iterations). How to set
  budget guards.
- **The license + threat model link.** Single-tenant local-first;
  see `SECURITY.md`. MIT/Apache (decide).

Avoid: implementation details, dev setup, prompt-tuning concepts.

### C.2 — Developer-facing (CLAUDE.md + `docs/architecture.md`)

Audience: a human or LLM contributor opening a PR.

CLAUDE.md is already excellent for AI contributors. Two additions:
- **System diagram** in `docs/architecture.md` rendered from a
  Mermaid source block so both humans and LLMs can read + edit
  it. Show the analyzer pipeline (analyze → clarify → recommend
  → generate → iterate), the deterministic-helpers boundary,
  the DB schema, the file-on-disk lifecycle, and which Anthropic
  model handles which call (Sonnet 4.6 for analyze/generate,
  Haiku 4.5 for recommend — confirm in `analyzer.py`).
- **Module map.** Each file gets one line: purpose, key public
  functions, what NOT to put there. Already partly in CLAUDE.md;
  break it out as its own page for browseability.

Source for the diagrams:
- `docs/diagrams/pipeline.mmd` — Mermaid sequenceDiagram of one
  full apply run.
- `docs/diagrams/data-flow.mmd` — Mermaid flowchart of context_set
  lifecycle (`build_context_set` → analyze → clarify → answer →
  generate → save_iteration_context → child JSON files).
- `docs/diagrams/persistence.mmd` — Mermaid entity-relationship
  of the DB (Candidate / Experience / Bullet / Title / Tag /
  Application / ApplicationRun / Clarification / Persona).
- `docs/diagrams/llm-routing.mmd` — Mermaid graph showing each
  `_call_llm` site, its `call_kind`, its model
  (Sonnet/Haiku), and whether it uses cached_user_prefix.

Mermaid renders on GitHub natively + parses cleanly by every LLM.
Self-update friendly.

### C.3 — Onboarding HTML page (`docs/onboarding.html`)

Audience: someone landing in the repo who wants to see callback.
running before reading anything.

Use the existing `docs/mockups/index.html` styling — same dark
surface + amber accent + system font — so the docs feel like part
of the product. One page, three blocks:
- TL;DR install (one code block)
- The five-screenshot flow
- Where to go next (link to README, CLAUDE.md, architecture.md).

This page is what `ShareOnboardingGuide` should push to teammates.

### C.4 — `docs/SECURITY.md` update

Already exists. Add for release:
- Explicit threat-model statement: single-tenant local-first;
  not multi-user. No auth/CSRF/rate-limit; that's intentional.
- Anthropic API key handling: where it's read, what it's used
  for, that it never leaves the machine.
- Data residency: every artifact stays on the user's disk.
- What we DON'T do: telemetry, analytics, error reporting,
  external HTTP calls beyond Anthropic + scraper (linkedin /
  portfolio URLs).

### C.5 — `CHANGELOG.md` + version cut

Make sure CHANGELOG covers every Phase 1 / Phase 1b / Phase 1c
commit on `feat/release-visual-ia`, the markdown normalizer
shipping in `2026-05-24.1`, the duplicates work from Branch 1, and
the wizard reorder. Cut a `v1.0.0` tag once the release pass is
complete.

### C.6 — Project-meta files an open-source project should ship

- [x] `README.md` — covered in C.1
- [x] `CHANGELOG.md` — covered in C.5
- [x] `LICENSE` — pick MIT vs Apache; commit
- [x] `CONTRIBUTING.md` — exists; verify it points at CLAUDE.md
  + branch conventions
- [x] `SECURITY.md` — covered in C.4
- [ ] `CODE_OF_CONDUCT.md` — standard Contributor Covenant
  template
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md`,
  `.github/ISSUE_TEMPLATE/feature_request.md`,
  `.github/PULL_REQUEST_TEMPLATE.md` — exists for the latter,
  verify
- [ ] `.github/FUNDING.yml` if sponsorship welcome
- [ ] `pyproject.toml` `[project]` metadata — name, version,
  description, authors, license, urls (homepage, source, issues)
- [ ] `pyproject.toml` `[project.scripts]` — `callback =
  "app:main"` CLI shim
- [ ] `Dockerfile` + `docker-compose.yml` — one-command run
- [ ] `docs/screenshots/` + `scripts/screenshot.py` to
  regenerate
- [ ] An animated demo: `docs/demo.gif` or asciicast
- [ ] Topic badges on the repo (when GitHub URL exists): build,
  license, version
- [ ] `.editorconfig` for cross-editor consistency
- [ ] `docs/diagrams/*.mmd` per C.2

---

## D. Risk register (things to test before tagging v1)

1. **PII in fixtures:** any `evals/fixtures/real/` files crept
   into the main suite? Run `pytest -k 'real'` separately,
   verify they're gitignored.
2. **Anthropic model availability:** the model IDs in
   `analyzer.py` (Sonnet 4.6, Haiku 4.5) — confirm they're still
   GA when v1 cuts. Document the fallback path.
3. **Cross-platform path handling:** `_safe_username` + `_within`
   are POSIX-friendly; verify on Windows with users that have
   spaces / unicode in their username. `_safe_username` already
   sanitizes, but path containment must work too.
4. **First-run experience:** clone fresh, follow the README,
   measure time-to-first-generation. Goal: < 5 minutes including
   .api_key setup.
5. **eval baseline:** run `python evals/runner.py --suite
   synthetic` and pin scores in `evals/results/baseline_v1.json`
   so post-release regressions are detectable.

---

*Source: this checklist was committed alongside the
`feat/release-visual-ia` work — see the commit that introduced
this file for the conversation context that produced it.*
