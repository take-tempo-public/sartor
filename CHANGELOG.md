# Changelog

All notable changes to Resume Optimizer are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `pyproject.toml` replacing `requirements.txt` (pinned dep ranges + `[dev]` extras)
- `tests/` with 28 unit tests covering the deterministic helpers and path-traversal defenses
- GitHub Actions CI workflow (`ruff` + `mypy` + `pytest`, label-gated synthetic eval smoke)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub issue and PR templates

### Changed
- `app.py` Flask debug flag is now env-driven (`FLASK_DEBUG`, default-on for dev). Set `FLASK_DEBUG=0` to disable for any future hosted deployment.
- Type annotations cleaned up across `analyzer.py`, `generator.py`, and `parser.py` to satisfy `mypy --strict-optional`.

### Removed
- `requirements.txt` (superseded by `pyproject.toml`)

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
