# sartor. — AI agent contract

> **Purpose:** the universal contract that any AI coding agent (Claude
> Code, Cursor, Codex, Continue, Aider, etc.) reads before making
> non-trivial changes to this codebase. Pointers to deeper docs, key
> code patterns, branch / commit conventions, security guardrails,
> what NOT to do.
> **Audience:** AI coding agents AND humans who want the same
> at-a-glance rules. This is the *canonical* tool-agnostic version;
> tool-specific overrides live in companion files like `CLAUDE.md`.
> **Authoritative for:** branch / commit conventions; the
> `_safe_username` / `_within` security gate; the `ruff` + `mypy` +
> `pytest` minimum-bar; `PROMPT_VERSION` discipline; what kinds of
> changes are NOT welcome. Sibling docs:
> [`vision.md`](vision.md) (product intent),
> [`docs/architecture.md`](docs/architecture.md) (system + modules),
> [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md) (v1 → v2 ladder).

> **Canonical governance.** The *binding* constitution — claims discipline
> (C-0), the C-1…C-6 clauses, the D-1…D-6 defaults, the parallel-session
> working model (W-1), and the amendment ceremony — lives in
> [`docs/governance/charter.md`](docs/governance/charter.md), with enforcement
> detail in [`docs/governance/enforcement.md`](docs/governance/enforcement.md).
> The rules restated below are the at-a-glance operational mirror every agent
> needs at session start; the charter is canonical and governs on conflict.
> **Do not let this file become a pure import shell** — non-Claude agents
> (Codex/Cursor/Aider) read it raw and an `@import` would silently drop their
> guardrails.

---

## Read these first

- [docs/architecture.md](docs/architecture.md) — system overview, module map, four Mermaid diagrams (pipeline / persistence / data-flow / llm-routing). Start here for a fast tour.
- [vision.md](vision.md) — product intent, self-imposed constraints, learnings + direction.
- [docs/PRODUCT_SHAPE.md](docs/PRODUCT_SHAPE.md) — unified Corpus Item pattern; v1.0 → v2 sequencing ladder; deferred items.
- [SECURITY.md](SECURITY.md) — threat model, API key rules, accepted risks.
- [CONTRIBUTING.md](CONTRIBUTING.md) — branch + commit conventions, dev loop.
- [README.md](README.md) — user-facing overview.

The project follows the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/). The codebase is annotated with principle references (P1, P2, P5, P6, P8, P9) — they are load-bearing, not decoration. The five load-bearing principles are frozen in [`docs/governance/charter.md`](docs/governance/charter.md) ("The 10 Principles backbone").

---

## Architecture at a glance

Full system + module map in [`docs/architecture.md`](docs/architecture.md). Quick orientation:

- **All LLM calls live in `analyzer.py`.** Sonnet 5 (`claude-sonnet-5`) for heavy reasoning (`analyze` synthesis pass, `iterate_clarify`, `generate`, `generate_cover_letter`); Haiku 4.5 (`claude-haiku-4-5-20251001`) for structured selection (the `analyze` extraction pass, `clarify`, `recommend`, `recommend_summary`, `critique_proposal`, `extract_experiences`). Verified against `analyzer.py:SONNET_MODEL`/`HAIKU_MODEL`.
- **`hardening.py`, `parser.py`, `generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py`, `docx_to_persona_html.py` are deterministic** — no LLM calls allowed. The P1 Hardening boundary (canonical rule: charter **C-6**).
- **`context_set` is the JSON contract** between every pipeline stage. Each `/api/generate` writes a NEW timestamped child file via `hardening.save_iteration_context()`; the `parent_context_path` chain is the iteration audit trail.
- **`PROMPT_VERSION` in `analyzer.py`** must bump in the SAME commit when any prompt changes, so eval telemetry attributes scores correctly (a charter discipline rule — [`docs/governance/charter.md`](docs/governance/charter.md), C-0 / D-4).

For the full pipeline sequence (with all eight LLM call kinds, which Flask route fires each, and cost/latency footprints), see [`docs/architecture.md`](docs/architecture.md) §"System overview" (pipeline) and §"LLM routing + cost" — the two fenced Mermaid diagrams there are the single source (the standalone `docs/diagrams/*.mmd` copies were retired in v1.0.9).

---

## Key patterns — always follow these

### Security (every Flask route that touches the filesystem)

```python
safe_user = _safe_username(username)          # sanitize + confirm user exists
safe_file = secure_filename(filename)         # strip traversal sequences
if not _within(path, PARENT_DIR): abort(403)  # resolved-path containment check
```

A `route-security-lint` hook enforces this on `app.py` + `blueprints/**.py` route edits (PX-21 widen), and a committed gate (`tests/test_route_containment_gate.py`, PX-29) asserts it across the whole blueprint tree — see [`.claude-plugin/hooks/`](.claude-plugin/hooks/). Canonical rule: charter **C-1** (Local and yours) + [`docs/governance/enforcement.md`](docs/governance/enforcement.md).

### Branch before code changes

A `require-feature-branch` PreToolUse hook blocks `Edit`/`Write` while on `main`/`master`. Create a feature branch when moving from plan to execute (`git checkout -b <type>/<short-desc>`). Intentional main edits: `export CLAUDE_ALLOW_MAIN_EDITS=1`.

**Mandatory steps have no escape hatch — your judgment does not decide
whether they apply.** Some hooks ship an env-var escape hatch
(`CLAUDE_CONFIRM_MERGE=1`, `CLAUDE_ALLOW_MAIN_EDITS=1`) and the plan gate has
its `.approved` marker — those are legitimate **only when the user explicitly
directs their use**, never on your own initiative, and you NEVER hand-create
the file a hook checks for to unblock yourself. The close-out steps below — the
pre-close sweep, the quality gate, and the handoff-template step — have **no
hatch at all**: there is no authorized way to skip them. Follow each as
written, or STOP and surface that you can't. "Good enough" / "approved enough"
is not a call you get to make — quietly downgrading a binding rule to advisory
is the failure mode this section exists to prevent.

**Branch close-out checklist (closing agent, in order):**
0. **Pre-close sweep — run this BEFORE the gate, ON THE BRANCH (never post-merge).** Enumerate the COMPLETE set of close-out obligations and resolve each (or explicitly defer *with the user*) so the session closes **once**, not three times:
   - working changes staged + internally consistent (no dangling refs / links);
   - **memory learnings** from the session written now — doing memory or cleanup *after* the merge (on `main`) gets blocked by `require-feature-branch` + the merge-wiped `~/.claude/plans/.approved` marker, forcing a repeat flag-clear-and-ceremony that steps on the next branch's work; the cheap window is here, pre-merge;
   - every **loose end flagged this session** resolved or explicitly deferred;
   - **trailing "track this" observations** — every note surfaced this session (flaky tests, drift spotted, process friction, follow-on flags, deferred sub-decisions) is **filed durably now** into the **one** Carry-forward ledger in `RELEASE_CHECKLIST.md` (a memory / a PX row may *also* hold detail, but the ledger is the single authoritative home — not scattered per-stream sections joined by pointers); never left to surface after merge as a new one-file branch;
   - **the handoff renders the FULL still-open ledger** — the `Carried-forward observations` section reproduces the *cumulative* still-open subset (every open item, not just this session's), so nothing falls out of attention across handoffs; at **~8–10 open items**, flag a reduction sprint. (Canonical: charter **W-1** "carry-forward discipline".)
   - **branches to prune** identified.
   "Done" is the *output* of this sweep, not a declaration — do not announce completion until it is empty. Declaring progress over verifying completeness manufactures tech debt, repeat close-outs, and eroded trust. In particular, NEVER merge and then open a follow-up branch for a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in before the merge.
1. Quality gate green — `python -m scripts.gate` (PX-55; runs `ruff check .` + `ruff format --check .` + `mypy .` + `pytest`, the same steps CI runs — see "Testing and validation" below).
2. Commit — message records what was done and why (or "no code change — verified" if the branch closed clean).
3. Ask user to confirm merge to `main`; execute merge after confirmation.
4. Prune the merged branch(es) with the user's OK, then generate the next-agent handoff prompt — **READ [`docs/dev/AGENT_HANDOFF_TEMPLATE.md`](docs/dev/AGENT_HANDOFF_TEMPLATE.md) FIRST and reproduce every fixed section (Documents to read, Hard constraints, Close-out checklist) verbatim, dropping none; a handoff written from memory is non-compliant** — **as copyable chat text (never a file written into `output/`)** and give it to the user as the **last act** before closing the window.

### Document generation

- Always pass `template_path` (original `.docx`) to `generate_resume()` when output is docx.
- `_write_docx_from_json_resume()` renders the SAME `md_to_json_resume()` doc the preview/PDF use (so download == preview) and opens the persona `.docx` as a style template — never call `docx.Document()` on blank when a template exists.
- `BULLET_RE` in `generator.py` normalizes all bullet variants.

### LLM prompts

- The hiring-manager persona lives at `analyzer.py:SYSTEM_PROMPT`; analyze-time interview persona at `analyzer.py:CLARIFY_SYSTEM_PROMPT`; iteration-time persona at `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT`. Edit there, not inline.
- When any prompt changes (or any per-call prompt template), bump `PROMPT_VERSION` in the same commit so observability/eval can attribute behavior.
- Supplemental resumes injected via `_supplemental_block(iteration)` — wrapper switches to `<historical_resumes>` (with the original primary folded in) when iteration ≥ 1.
- Grounding check in generation prompt enforces no invented facts; the worked-examples block (OK / NOT OK pairs) is the load-bearing teaching signal — when adding new failure modes to the SYSTEM_PROMPT, also add a worked example.
- When clarifications OR first-person preview edits are present, the grounding check widens to accept them as legitimate source material. The no-invention rule still applies beyond the union of (resume + clarifications + typed edits) — keep this carve-out surgical, not blanket.
- **D5 cross-JD reuse** (`feat/clarifications-to-corpus`): the THREE Compose content-drafting calls (`draft_positioning_summary`, `draft_gap_fill_bullets`, `suggest_skills`) additionally accept `context_set["prior_clarifications"]` — confirmed clarification facts from the candidate's OTHER applications, staged once by `db.build_context.build_context_set_from_db` (corpus-mode only) — as legitimate grounding source material via a `<prior_clarifications>` prompt block, and `hardening.assemble_source_union` widens to match so the deterministic grounding metric doesn't flag legitimately-reused facts. The **legacy `generate()` prompt is untouched** — this carve-out is scoped to the three drafting calls, not blanket.
- `_call_llm` and `_parse_or_retry` accept an optional `system_prompt` arg; every call that overrides it via `_resolve_system_prompt(...)` or a literal persona constant (not just `clarify` / `clarify_iteration` — grep `system_prompt=_resolve_system_prompt\|system_prompt=AVATAR_SYSTEM_PROMPT` in `analyzer.py` for the current call sites; 16 as of this writing, growing as new drafting/recommend calls are added) pays one extra cache-miss on the system block, but the heavy user-prefix cache is unaffected.

### Eval observability

- Eval results carry `prompt_version` so the dashboard's score-over-time chart can attribute regressions to specific prompt revisions.
- Deterministic post-generation metrics (`verb_diversity`, `specificity_density`, `grounding_overlap`, `cost_usd`) ride along on every result. `grounding_overlap.missing_samples` is the actionable fabrication signal.
- Document tuning iterations in `evals/TUNING_LOG.md` (what changed, why, scores before/after, lessons). This is the institutional-memory artifact for future tuners.
- **Prompt-override primitive** (`analyzer.prompt_overrides()` + `evals/runner.py --prompt-overrides`): A/B a candidate system prompt **without editing the persona constants**. Inside the context manager every LLM call sends the candidate prompt and stamps `prompt_version=candidate:<hash>` (telemetry + eval records), so candidate runs are quarantined from score-over-time. The default (no-override) path is byte-identical — the resolver returns the identical constant object and the logged version stays `PROMPT_VERSION`, so the analyze→generate cache is untouched. Override scope is the named system-prompt constants only (the `_BASE_SYSTEM_PROMPTS` registry), not the dynamic user-prompt builders. `/prompt-tune` and the v1.0.4 tuning loop build on this.

### Frontend config persistence

Profile config (name, contact, `portfolio_urls`, `included_resumes`, skills,
certifications, education) persists through a single canonical path — `saveConfig()`
in [`static/app.js`](static/app.js), which `PUT`s the full config to
`/api/users/<user>/config`. Add new per-config fields there (spread from
`currentConfig` so they survive panel saves), and reuse that one path rather than
adding per-handler helpers — match the live code, don't restate volatile function
names (charter D5, cite-don't-restate).

---

## Testing and validation

Every change should pass the local validator loop before commit. **`scripts/gate.py`
(PX-55) is the single definition of "gate green"** — the same four steps in the
same order run locally, in CI (`.github/workflows/ci.yml`'s `quality` job), and in
`CONTRIBUTING.md`'s PR checklist, so there is exactly one place that list can drift:

```bash
python -m scripts.gate
# equivalent to, in order: ruff check . / ruff format --check . / mypy . / pytest
```

The Playwright **UX** tier (`pytest -m ux`) drives the wizard in a headless Chromium against a threaded live server (LLM-free — analyzer functions are stubbed, the real routes run). It skips when the Chromium binary is absent (`python -m playwright install chromium`), so the default `pytest` stays green everywhere. The shared navigation/selector driver lives in [`ui_pages/`](ui_pages/) — one registry, consumed by the suite **and** `scripts/capture_screenshots.py`.

CI runs the same on PR. Eval harness (Anthropic API costs apply) runs locally and on label-gated CI:

```bash
python evals/runner.py --suite synthetic --subset smoke   # ~$0.35-0.40 under Sonnet 5, grounding only
python evals/runner.py --suite synthetic                  # ~$1.50, all 4 rubrics × 3 fixtures
```

Dashboard for trends + heatmap + failure-mode clustering: visit `http://localhost:5000/_dashboard` while `python app.py` is running locally. Only reachable via `localhost`/`127.0.0.1` (host-header guard).

---

## What NOT to do

*The binding form of several rules below is in [`docs/governance/charter.md`](docs/governance/charter.md) (deterministic boundary C-6, no-invention C-3, minimal deps D-1, the security gate C-1); this list is the operational mirror — the charter governs on conflict.*

- Do not call `docx.Document()` without a template — output won't match the original's style.
- Do not invent numbers, titles, or dates in LLM output — grounding check is the enforcement.
- Do not skip `_safe_username()` / `_within()` on any new route touching the filesystem.
- Do not commit real personal data: `evals/fixtures/real/`, `configs/*.config` (except `example.config`), `resumes/`, `output/`.
- Do not add features or refactor beyond what was asked — minimal targeted edits only.
- Do not call an LLM from any file in the deterministic-boundary list under "Architecture at a glance" (`hardening.py`, `parser.py`, `generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py`, `docx_to_persona_html.py`) — those are deterministic by design.
- Do not introduce a new dependency without adding it to `pyproject.toml` AND updating `CHANGELOG.md`.
- Do not bypass the `route-security-lint`, `require-feature-branch`, or `ruff-changed` PreToolUse hooks without explicit authorization documented in the commit message.
