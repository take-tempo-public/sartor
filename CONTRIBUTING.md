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

> **Canonical rule home.** The binding rules this section and the PR checklist
> restate — branch conventions, the ruff + mypy + pytest bar, the `PROMPT_VERSION`
> bump, and minimal-dependencies (D-1) — live once in
> [`docs/governance/`](docs/governance/) (`charter.md` + `enforcement.md`). This doc
> keeps its descriptive how-to; on any conflict the governance home governs.

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
- [ ] If you changed `analyzer.py:SYSTEM_PROMPT` (or any per-call prompt template), bump `PROMPT_VERSION` in the same commit — a charter discipline rule ([`docs/governance/charter.md`](docs/governance/charter.md), C-0 / D-4)

CI runs `ruff` + `mypy` + `pytest` on every PR. Add the `eval` label to also run synthetic smoke evals (uses Anthropic API; ~$0.10 per run).

---

## Working with the Claude Code plugin

The project ships a Claude Code plugin (`callback`). The pieces live in three places:

- **Slash commands** in repo-root [`commands/`](commands/) and **subagents** in repo-root [`agents/`](agents/) — they load as the `callback` plugin via a bundled local marketplace (`callback-tools`), declared by the `extraKnownMarketplaces` + `enabledPlugins` entries committed in `.claude/settings.json`. Because they load as a plugin they appear **namespaced**: commands as `/callback:<name>`, subagents as `callback:<name>`.
- **Hooks** in [`.claude-plugin/hooks/`](.claude-plugin/hooks/) — wired **directly** in the same `.claude/settings.json` (path-referenced, not plugin-discovered), so they stay independent of the marketplace loader.
- The plugin **manifest** + local **marketplace** definition live in [`.claude-plugin/`](.claude-plugin/) (`plugin.json` + `marketplace.json`).

Cloning the repo activates everything on session start — a fresh clone needs a one-time marketplace-trust prompt + reload, no install step. For the full command/subagent/hook catalog see [README → Claude Code Plugin](README.md#claude-code-plugin) (and [`CLAUDE.md`](CLAUDE.md) for the agent-facing contract); this section is the layout-and-activation orientation, not a catalog, so it deliberately doesn't re-list every entry.

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

The first run also auto-downloads NLTK's `punkt_tab` sentence-tokenizer data (a
few MB) that MiniCheck needs — no manual step required.

> **Note — pinned dependencies (window-8.5 EV-1, 2026-06-23).** `minicheck` is
> pinned to a specific commit in `pyproject.toml` rather than tracking the
> upstream default branch, which drifted to a vLLM/`Bespoke-7B` rewrite that
> dropped the CPU `flan-t5-large` path's `device` kwarg. The extra also installs
> `accelerate` (required by `transformers>=5` for the `device_map="auto"` the
> MiniCheck loader uses) and allows `transformers<6.0` (validated on 5.10.2). The
> scorer was re-validated end-to-end on CPU on this stack.

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

Per-agent personal access tokens or separate user accounts are explicitly *not* the recommended path. See the agent definitions in `agents/` for the current personas and their permissions.

---

## Code of conduct

Participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
