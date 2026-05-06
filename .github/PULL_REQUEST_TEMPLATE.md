<!-- One-sentence summary of the change. The diff shows *what*; explain *why*. -->

## Summary

Closes #<!-- issue number, if any -->

## Layer touched

<!-- Tick the layer(s) — helps reviewers know what to focus on. -->

- [ ] Deterministic (hardening / parser / scraper / generator)
- [ ] LLM pipeline (analyzer)
- [ ] Frontend (templates / static)
- [ ] Flask routes (app.py)
- [ ] Plugin / Claude Code workflow (.claude-plugin)
- [ ] Eval harness (evals)
- [ ] Documentation / project meta

## Checklist

- [ ] `ruff check .` clean
- [ ] `mypy .` clean
- [ ] `pytest` green
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] If a Flask route now reads or writes the filesystem, it calls `_safe_username()` and `_within()`
- [ ] If `analyzer.py:SYSTEM_PROMPT` changed, `PROMPT_VERSION` was bumped in the same commit
- [ ] No real personal data committed (`evals/fixtures/real/` stays gitignored, `configs/*.config` ignored except `example.config`)
- [ ] If this changes user-visible behavior, the README is updated

## Test plan

<!-- How did you verify? Include commands run, fixtures used, manual gestures performed. -->

## Risk

<!-- What could go wrong, and how would you tell? -->
