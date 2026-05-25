# Contributing to callback.

> **Purpose:** how to propose changes — quick start, branch and commit
> conventions, the local dev loop, what kinds of contributions are
> welcome vs out of scope.
> **Audience:** external contributors (humans) sending PRs.
> **Authoritative for:** the proposal/review process; the
> ruff + mypy + pytest minimum-bar; the rule that any LLM prompt
> change bumps `PROMPT_VERSION` in the same commit. Sibling docs:
> [`vision.md`](vision.md) (product intent),
> [`CLAUDE.md`](CLAUDE.md) (contributor contract),
> [`SECURITY.md`](SECURITY.md) (threat model).

Thanks for your interest. callback. tailors a résumé and (optionally) a cover letter to one specific job at a time, using a deterministic Python core and the Claude API for fuzzy reasoning. It is intentionally small — most contributions should *make it more deterministic*, not less.

The guiding philosophy is the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/). Read [`vision.md`](vision.md) before proposing significant changes.

---

## Quick start

```bash
git clone <your-fork-url>
cd resume
pip install -e ".[dev]"

# Sanity-check the toolchain
ruff check .
mypy .
pytest

# Run the app
python app.py            # → http://localhost:5000
```

Set your Anthropic API key in `ANTHROPIC_API_KEY` or in a local `.api_key` file (gitignored).

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
- **Skills** — `/eval`, `/replay`, `/prompt-tune`, `/bench`, `/inspect-context` (added in Step 9)
- **Subagents** — `eval-judge`, `prompt-archaeologist`, `git-flow` (added in Step 8)

If you launch Claude Code from a terminal and want to load the manifest directly, `claude --plugin-dir ./.claude-plugin` works; the VSCode extension does not accept that flag. When `/plugin install` gains local-path support upstream, the project will republish a `hooks.json` so the manifest becomes self-wiring.

Hooks should remain deterministic shell. LLM-backed review is reserved for explicit `/code-review:code-review` and `/security-review` invocations.

---

## Adding eval fixtures

Two locations:

- `evals/fixtures/synthetic/` — **committed**, public-safe, fictional companies + resumes only. CI runs against these.
- `evals/fixtures/real/` — **gitignored**, your own JDs/resumes for local tuning. Never commit these.

A fixture is a directory with `jd.txt`, `resume.docx` (or `.md`/`.pdf`), and `expected.json`. See `evals/fixtures/synthetic/sre-mid-level/` once it lands as the canonical example.

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
