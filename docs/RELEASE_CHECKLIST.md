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
> [`docs/PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) §10 for the full
> deferred-items table that drives the v1.0.1 / v1.1 / v2 ladder.

---

## Active release — v1.0.1

The v1.0.0 release landed in commit `075d830` (with subsequent
template curation, paged.js pagination, and docs reworks landing
on the same branch before tag). v1.0.1 is the first follow-up
release.

### Must do before tag (shipping blockers)

- [ ] **Manual fresh-clone verification** — clone in a clean
      directory; run `pip install -e .` + `python -m playwright
      install chromium` + `python app.py`; complete one
      application end-to-end. Time-to-first-generation < 5
      minutes (D.4 below).
- [ ] **Eval baseline check** — run
      `python evals/runner.py --suite synthetic --subset smoke`;
      confirm no regression against
      `evals/results/baseline_v1.json`.
- [ ] **Quality gate** — `ruff check .` + `mypy .` + `pytest`
      all clean.
- [ ] **`pyproject.toml` version bump** — `1.0.0` → `1.0.1`
      in the release commit.
- [ ] **`CHANGELOG.md` flip** — rename `[Unreleased]` →
      `[1.0.1] — <date>`; add new empty `[Unreleased]` block.

### Should do (v1.0.1 polish; document if skipped)

- [ ] **Step 6 (Output) redesign** — surfaced during the v1.0.0
      review: cut the obsolete tabs + raw/rendered toggle
      (replaced by paged.js preview); preview at the top of
      the step; edit-raw via modal; Changes → info-icon modal;
      cover letter → single "+ Generate" button until generated.
- [ ] **BACK / Continue spacing polish on Compose** — listed
      in PRODUCT_SHAPE §10 as deferred from v1.0.0.
- [ ] **`docs/install.md` updated** for any platform-specific
      lessons learned during v1.0.0 hands-on testing.

### Nice to have (defer to v1.1 if time-bound)

- [ ] **Visual assets** — screenshots, demo GIF, onboarding HTML
      page. PRODUCT_SHAPE §10 defers this to v1.0.1; if the
      planned UI redesign hasn't started, ship visual assets
      against the current UI rather than wait.
- [ ] **R2 — stream `analyze()` output** (PERF_ANALYZE.md, $0,
      perceived latency 90s → 10-15s). Owns its own commit
      and eval cycle.

---

## Forward-looking — v1.1 and v2

v1.1 + v2 items are tracked in
[`docs/PRODUCT_SHAPE.md §10`](PRODUCT_SHAPE.md). Don't duplicate
the list here — the strategy doc is the single source of truth
for the deferred table.

Highlights pulled from §10:

- **v1.1:** R1 (split analyze: Haiku-fast + Sonnet-deep),
  field-filter chips for templates by role tag, master résumé
  operationalization, Docker.
- **v2:** `recommend_template` Haiku call per JD class (gated
  on outcome data + an `ApplicationOutcome` table).

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
