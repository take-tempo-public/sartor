# Contributing to callback.

> **Purpose:** how to propose changes — quick start, branch and commit
> conventions, the local dev loop, what kinds of contributions are
> welcome vs out of scope.
> **Audience:** external contributors (humans) sending PRs.
> **Authoritative for:** the proposal/review process; the
> ruff + mypy + pytest minimum-bar; the rule that any LLM prompt
> change bumps `PROMPT_VERSION` in the same commit. Sibling docs:
> [`vision.md`](vision.md) (product intent + constraints),
> [`AGENTS.md`](AGENTS.md) (AI-agent operational contract — same
> rules apply to humans),
> [`docs/architecture.md`](docs/architecture.md) (system + modules),
> [`SECURITY.md`](SECURITY.md) (threat model).

Thanks for your interest. callback. tailors a résumé and (optionally) a cover letter to one specific job at a time, using a deterministic Python core and the Claude API for fuzzy reasoning. It is intentionally small — most contributions should *make it more deterministic*, not less.

The guiding philosophy is the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/). Read [`vision.md`](vision.md) before proposing significant changes; skim [`docs/architecture.md`](docs/architecture.md) for the pipeline diagram + module map.

---

## Quick start

```bash
git clone <your-fork-url>
cd callback
pip install -e ".[dev]"

# One-time: download the Chromium binary Playwright needs for PDF
# rendering. ~150 MB, lives in your OS user cache (NOT in the repo).
python -m playwright install chromium

# Sanity-check the toolchain
ruff check .
mypy .
pytest

# Run the app
python app.py            # → http://localhost:5000
```

Set your Anthropic API key in `ANTHROPIC_API_KEY` or in a local `.api_key` file (gitignored).

For a deeper architectural tour before opening a PR, read [`docs/architecture.md`](docs/architecture.md) (system + module map + four Mermaid diagrams) and [`AGENTS.md`](AGENTS.md) (the universal contract — same rules apply whether you're a human or an LLM agent).

---

## Branch conventions

- One branch per change: `kebab-case-description` (e.g. `fix/cover-letter-spacing`, `feat/jd-template-library`)
- Branch off `main`
- Merge with `git merge --no-ff` so branch history is preserved
- Delete the branch after merge

## Commit messages

```
feat: short imperative summary

Optional body explaining *why* — never *what* (the diff already shows what).
Reference the principle being applied if it clarifies intent.
```

Prefixes: `feat` (new behavior), `fix` (bug), `refactor` (no behavior change), `chore` (tooling/deps), `docs`, `test`.

When commits are produced with assistant help, add a trailer:

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

This signals collaboration without conflating attribution. The human author remains responsible for the change.

---

## Pull request checklist

Before opening a PR:

- [ ] `ruff check .` — clean
- [ ] `mypy .` — clean
- [ ] `pytest` — green
- [ ] `pytest -m ux` — green (Playwright UI suite; needs `python -m playwright install chromium`, see [Quick start](#quick-start))
- [ ] `CHANGELOG.md` — entry under `[Unreleased]` describing the user-visible change
- [ ] No real personal data committed (`evals/fixtures/real/` is gitignored — keep it that way)
- [ ] If you touched a Flask route that reads or writes the filesystem, the route uses `_safe_username()` and `_within()` — see [`app.py`](app.py)
- [ ] If you changed `analyzer.py:SYSTEM_PROMPT`, bump `PROMPT_VERSION` in the same file (see Step 6 of the OSS migration once landed)

CI runs `ruff` + `mypy` + `pytest` on every PR. Add the `eval` label to also run synthetic smoke evals (uses Anthropic API; ~$0.10 per run).

---

## Working with the Claude Code plugin

The `.claude-plugin/` directory holds the project's commands, agents, and hook scripts. As of Claude Code v2.1.131 the `/plugin install` command targets registered marketplaces only — not local directories — so plugin components are wired via `.claude/settings.json` (committed) rather than through the plugin loader. Cloning the repo activates them automatically; no install step is required.

The settings.json wiring covers:

- **Hooks** — plan-mode workflow scripts; Step 5 adds secret-blocking, `ruff` on commit, route-security lint, context-set schema validation, and merge-to-main confirmation
- **Skills** — `/eval`, `/replay`, `/prompt-tune`, `/tune-from-annotations`, `/bench`, `/inspect-context` (added in Step 9)
- **Subagents** — `eval-judge`, `prompt-archaeologist`, `git-flow` (added in Step 8)

If you launch Claude Code from a terminal and want to load the manifest directly, `claude --plugin-dir ./.claude-plugin` works; the VSCode extension does not accept that flag. When `/plugin install` gains local-path support upstream, the project will republish a `hooks.json` so the manifest becomes self-wiring.

Hooks should remain deterministic shell. LLM-backed review is reserved for explicit `/code-review:code-review` and `/security-review` invocations.

---

## Grounding signal scorers (optional, dev-only)

The `--grounding-signals` flag in `evals/runner.py` runs two offline grounding
scorers — DeBERTa NLI and MiniCheck-FT5 — per generated bullet. This is
**dev tooling only**: it runs in the eval harness, never in the production app
(`python app.py`). End users do not install these packages.

### What the models do

| Model | Size | License | Signal |
|---|---|---|---|
| `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | ~180 MB | Apache 2.0 | NLI entailment: is the bullet *entailed by* the source résumé? |
| MiniCheck `flan-t5-large` | ~3 GB (first download) | See note below | Factual grounding: is the claim *supported by* the source document? |

Both model weights download automatically to the OS HuggingFace cache on first
use (`~/.cache/huggingface/` on Linux/Mac;
`%USERPROFILE%\.cache\huggingface\` on Windows). They are never stored in the
repo.

### MiniCheck license

MiniCheck (Liyan06/MiniCheck) is published for **academic/research use**.
This is not a permissive open-source license (not MIT, not Apache). Do **not**
ship MiniCheck in a SaaS product or distribute it to end-users without
verifying the current license permits your use case. In this project it is used
solely as an offline eval scorer and never reaches production.

### Install sequence

**Step 1 — install torch for your hardware (do this first)**

CPU-only (most laptops, ~200 MB):
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

CUDA (if you have an NVIDIA GPU — pick the wheel matching your CUDA version):
```bash
# CUDA 12.1 example — check https://pytorch.org/get-started/locally/ for your version
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

**Step 2 — install the eval-grounding extras**

```bash
pip install -e ".[eval-grounding]"
```

**Step 3 — first run (triggers model downloads)**

```bash
# ~3.2 GB download on first run; cached permanently after that
python evals/runner.py --suite anchor --subset smoke --grounding-signals
```

### CPU inference time

On a CPU-only laptop: ~2–4 s per bullet. A typical résumé has 15–25 bullets,
so `--grounding-signals` adds ~1–3 min per fixture on top of the normal LLM
pipeline time. Acceptable for ad-hoc grounding analysis; not intended for every
eval run.

---

## Adding eval fixtures

Two locations:

- `evals/fixtures/synthetic/` — **committed**, public-safe, fictional companies + resumes only. CI runs against these.
- `evals/fixtures/real/` — **gitignored**, your own JDs/resumes for local tuning. Never commit these.

A fixture is a directory with `jd.txt`, `resume.docx` (or `.md`/`.pdf`), and `expected.json`. See `evals/fixtures/synthetic/sre-mid-level/` once it lands as the canonical example.

### Exporting a corpus seed (real fixtures)

If your corpus lives in the SQLite DB (the corpus tab), snapshot it to a
portable `seed.json` with the deterministic, LLM-free exporter:

```bash
python -m scripts.export_corpus_seed --user <name>
# → evals/fixtures/real/<name>/seed.json   (gitignored)
```

The exporter writes **only** under `evals/fixtures/real/` (a `_within`-style
resolved-path guard refuses any other destination, even via `--out`), so the
snapshot — which contains your real data — can't leak outside the gitignored
tree. The `seed.json` is the input the corpus-backed eval runner consumes.

### Tuning a prompt from real-data annotations

Once you have a `seed.json`, the v1.0.4 eval tuning loop turns real output into a
promoted prompt edit: `bootstrap` the seed against several JDs, annotate the
generated bullets/skills, collate to a `--suite real` fixture + an
`improvement_brief.md`, then run the **`/tune-from-annotations`** skill. It drafts
a candidate system-prompt edit from the brief (via the read-only `tune-drafter`
subagent), A/Bs it against your real fixture plus an `--suite anchor` canary using
the prompt-override primitive (so `analyzer.py` is never touched during the
trial), and shows a `python -m evals.tune` delta table. A change is **promoted**
— constant edited, `PROMPT_VERSION` bumped in the same commit, `TUNING_LOG.md`
entry written — only on your explicit approval. Full walkthrough in
[`evals/README.md`](evals/README.md) ("Tune-from-annotations workflow").

---

## Security

Sensitive issues should go through GitHub Security Advisories — see [`SECURITY.md`](SECURITY.md). Do not file public issues for vulnerabilities.

---

## Future: multi-agent identity

The plugin's subagents currently act under your local `gh auth` identity, with `Co-Authored-By:` trailers attributing assistant work. If this project ever grows to need scheduled or multi-agent autonomy, the pathway is:

1. **GitHub Actions with built-in `GITHUB_TOKEN`** for scheduled jobs (no secrets to manage)
2. **A scoped GitHub App** ("callback. Bot") for distinct-identity automation

Per-agent personal access tokens or separate user accounts are explicitly *not* the recommended path. See the agent definitions in `.claude-plugin/agents/` for the current personas and their permissions.

---

## Code of conduct

Participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
