# 30 — Technical User (self-hoster / contributor)

> The user who runs sartor. on their own machine, extends it, tunes its prompts,
> or contributes. Their "UX" is the setup path, the diagnostics console, the eval
> harness, the Claude-Code plugin, and the docs. This is where sartor. is unusually
> deep for a résumé app — the question is whether that depth is *approachable*.
> Friction tagged **[F-xx]** (see [40-friction-register.md](40-friction-register.md));
> screenshots **📸**.

Persona: *Sam*, an engineer who found the repo, wants to run it locally, maybe
tune the prompts for their own field, and possibly contribute.

---

## Path A — Fresh-clone setup

**Goal:** get from `git clone` to a running app with real output.

The documented path (README + `docs/install.md`):

1. `git clone` → `pip install -e .` (deps: Flask, anthropic, python-docx,
   pdfplumber, sqlalchemy, alembic, playwright, model2vec, …).
2. `sartor --setup` — a one-time bootstrap that installs the Playwright Chromium
   (needed for PDF export) and builds the recall vector index. Idempotent.
3. Provide an Anthropic key: a `.api_key` file at the repo root, or
   `ANTHROPIC_API_KEY`.
4. `sartor` (or `python app.py`) → opens `http://localhost:5000`.

*Assessment:* this is a clean, standard Python path, and the container option
(`docker run … ghcr.io/…/sartor`) is documented for the non-Python user. Two
things to watch:

- *Friction* **[F-18]**: the app **auto-opens a browser** and defaults
  `FLASK_DEBUG=1` (the reloader is on). Both are friendly for a job seeker but
  surprising for a developer running it headless or in a container; the overrides
  (`--no-browser`, `SARTOR_NO_BROWSER=1`, `FLASK_DEBUG=0`) exist but aren't
  prominent.
- *Friction* **[F-19]**: the setup requires a real, billed Anthropic key to do
  *anything* meaningful — there is no offline/demo mode for a curious developer to
  see the flow without spending. (The test suite stubs the LLM, but that's not a
  product entry point.) A "try it with canned output" path would lower the bar to
  first value.

**📸 Screenshot (setup):** a terminal showing `sartor --setup` output (Chromium
install + vector index build) followed by `sartor` printing the localhost URL —
the "it's running" moment.

---

## Path B — The diagnostics console (`/_dashboard`)

The richest technical surface. Localhost-only (host-header guarded), read-only,
five tabs. All charts read `logs/llm_calls.jsonl` + `evals/results/*.jsonl`.

1. **Pipeline** — cost / calls / cache-hit / reliability / latency tiles + a
   per-run trace waterfall. Live numbers from this review's own traffic: **$38.88
   total across 3,087 calls, 33% cache hit, p95 latency ~99 s** (the Sonnet
   `analyze_synthesis` step dominates).
   - *Friction* **[F-06d]**: the **"RELIABILITY" tile shows "0%"** with the subtext
     "5 error · 0 truncated." That is the *error rate* (5/3087 ≈ 0%), i.e. the
     system is ~100% reliable — but a tile labeled "RELIABILITY: 0%" reads as
     catastrophic at a glance. It should show reliability (~100%) or be relabeled
     "error rate."
2. **Quality** — the eval cockpit: an in-browser "Run eval" (synthetic/smoke,
   grounding-signals toggle), Health-vs-baseline ("16 ok · 0 regressed"), rubrics
   tracked (8), score trend, an 8×3 heatmap, top failure mode
   (`missing_expected_theme`, 98 records), and a Pareto verdict.
3. **Groundedness** — the fabricated-specifics (L0) trend + drill-down; the
   actionable fabrication signal.
4. **Tuning** — a prompt A/B picker sourced live from the prompt registry.
5. **Annotate** — the console's *only* write surface: produce a bootstrap (runs
   the live paid pipeline over pasted JDs) and label each bullet kept/fixed/
   omitted/fabricated to build grounding ground-truth. Clearly marked
   "Read-write — localhost only."

*Assessment:* this is a serious observability + evaluation suite, better than most
production apps ship. Each tab opens with a one-line explainer and an "(i)" — the
learning curve is handled. The main polish item is the mislabeled reliability tile.

**📸 Screenshot (dashboard Pipeline):** the tiles row — "TOTAL COST $38.88",
"CALLS 3087 · cache hit 33%", "RELIABILITY 0% · 5 error", "P50/P95 LATENCY 24715 /
99564ms" — with the reliability tile circled as F-06d. **📸 (dashboard Quality):**
the eval cockpit — "Run eval" panel + the Health/Rubrics/Heatmap/Failure-mode/
Pareto tiles.

---

## Path C — The eval harness

**Goal:** measure and improve generation quality.

- `python evals/runner.py --suite synthetic --subset smoke` — grounding rubric on
  3 synthetic fixtures. Run live during this review: **3 pass, 0 fail, grounding
  4.6/5 each, fabricated_specifics 0.00–0.05, ~$0.12/fixture (~$0.37 total)**.
- Full suite: 8 rubrics (grounding, callback_likelihood, ats_format,
  keyword_coverage, tone, clarification_quality, iteration_quality) judged by
  Haiku, with deterministic metrics riding along and a composite score.
- A **prompt-override** primitive (`--prompt-overrides`) A/B-tests a candidate
  prompt without editing `analyzer.py`, quarantining candidate runs from the
  score-over-time trend.
- `evals/TUNING_LOG.md` is the institutional memory of prompt iterations.

Two findings:

- *Friction* **[F-20]**: the documented smoke cost (**"≈ $0.10"**, shown in the
  dashboard and README) is stale — the live run cost **~$0.37** (3 × ~$0.12),
  ~3.7×, most likely because the models were upgraded to Sonnet 5 / Haiku 4.5
  since the estimate was written. Cost estimates should be regenerated post-upgrade.
- *Finding* **[F-11] (important)**: the eval pipeline calls a real LLM
  **`generate`** step (~27 s/fixture), but the **primary UI flow no longer does**
  — the UI assembles the frozen composition deterministically. So the harness
  measures a generation path users don't take. The prompt-quality signal (analyze,
  clarify) is still valid, but "generation quality" as evaluated ≠ what ships.
  The eval harness should either exercise the compose→freeze→assemble path or the
  divergence should be documented so no one over-trusts the generate rubric.

**📸 Screenshot (eval run):** the terminal tail of the smoke run — the
`analyze_extraction / analyze_synthesis / clarify / generate` call log with
latencies, the per-fixture `metrics:` line (verb_diversity, grounding_overlap,
fabricated_specifics, cost), and "Eval complete: 3 pass, 0 fail."

---

## Path D — The Claude-Code plugin

For a contributor working with Claude Code, sartor. ships a first-class plugin
(local marketplace): **12 slash commands** (`/sartor:eval`, `/sartor:replay`,
`/sartor:prompt-tune`, `/sartor:bench`, `/sartor:inspect-context`, the
`/sartor:wiki-*` family, `/sartor:compliance-witness`) and **9 subagents**
(eval-judge, prompt-archaeologist, tune-drafter, headhunter, git-flow,
wiki-scribe/auditor, compliance-witness, ux-onboarding-designer). Hooks enforce
the security gate, branch discipline, secret-blocking, and context validation.

- *Assessment:* this is a genuinely impressive contributor-experience investment —
  the repo is instrumented for AI-assisted development with governance baked in.
- *Friction* **[F-21]**: it is also a lot to meet at once, and the README mixes
  the **product** (the résumé app) with the **development harness** (plugin, wiki,
  governance) in a way that can blur "what do I run to use it" vs. "what do I run
  to develop it." A cleaner split — "Use it" vs. "Develop it" vs. "Extend the
  prompts" — would help a newcomer find their lane.

---

## Path E — Docs, wiki, governance

- **Entry docs**: README, `docs/install.md`, `CONTRIBUTING.md`, `vision.md`,
  `SECURITY.md`, `docs/architecture.md` (with four Mermaid diagrams).
- **Wiki**: a 36-page compiled knowledge base (24 dev-audience, 12
  user-audience), governed by a SCHEMA that forbids asserting beyond cited
  sources, with a self-updating diff-driven loop and a grounding auditor.
- **Governance**: a signed charter (C-0…C-6 claims discipline, D-1…D-6 defaults),
  an enforcement map, and a compliance-witness.

*Assessment:* the documentation depth is far above a typical OSS project of this
size, and the doc-grounded assistant (Path H in the job-seeker doc) makes it
*queryable*. The risk is again volume: a first-time contributor meets AGENTS.md,
CLAUDE.md, the charter, the wiki, and the plugin, and may not know the minimal
path. See the polish plan's "contributor on-ramp" item.

- *Friction* **[F-22]**: the model-routing description in `AGENTS.md` / `CLAUDE.md`
  ("Sonnet 4.6 for analyze/clarify/generate") no longer matches the running system
  (Sonnet 5 / Haiku 4.5; analyze is a two-phase Haiku+Sonnet; clarify is Haiku;
  the UI generate is deterministic). Doc drift that would mislead a contributor
  reading the contract.

**📸 Screenshot (architecture):** the `docs/architecture.md` LLM-routing Mermaid
diagram, to anchor the "where does the model run" mental model — flagged for the
F-22 update.

---

## Technical-user verdict

sartor. is not a toy: it has real observability, a real eval/tuning loop, a
governance model, and an AI-native contributor harness. For a technical user that
depth is the draw. The friction is not that the tools are bad — they're
excellent — but that (1) there's no low-cost/offline way to see the product before
committing an API budget (F-19), (2) the docs conflate *using* with *developing*
and *extending* (F-21), and (3) a few high-visibility facts have drifted from the
code (the reliability tile F-06d, the eval/generate divergence F-11, the smoke
cost F-20, the model routing F-22). None are hard to fix, and fixing them makes
the project's genuine sophistication legible instead of overwhelming.
