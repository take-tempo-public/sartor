<!--
  TEMPORARY / UNTRACKED ARTIFACT — output/ (gitignored). Do NOT commit.
  Q3 deliverable (draft v1), 2026-06-07. Feeds the planning process after the
  five-question walk — and is a direct input to Sprint 6.5 branch
  `docs/eval-stack-install-guide` (#17), and a candidate README/install section.

  Decisions (see output/_dev-notes/excellence-walk.md):
   - Shape: LAYERED (like Q1) — plain "what & why" on top, precise provenance
     table beneath (size · location · license · why).
   - Scope of "non-dependency download": everything you must obtain that
     `pip install`-ing the DECLARED dependencies does NOT hand you. The regular
     pip deps + the [dev]/[eval-grounding] extras are themselves "dependencies"
     (the triggers), not the answer.
   - Facts VERIFIED against pyproject.toml + docs/install.md + CONTRIBUTING.md.
-->

# callback. — what you actually have to download, and why

*Everything you must obtain that `pip install`-ing the declared dependencies does
**not** hand you. The ordinary Python packages (Flask, the Anthropic SDK, Pydantic,
SQLAlchemy, …) install themselves with `pip install -e .`; this is the list of
**other** things — the interpreter, the repo, browser binaries, model weights, a
credential — split by what you're trying to run.*

## (a) To run the basic tool

1. **Python 3.10+** — the interpreter; the whole app is Python (supports 3.10–3.13).
2. **`git` + the repo clone** — callback. isn't shipped as a PyPI wheel for end
   users; you `git clone` it and `pip install -e .` from the clone.
3. **A headless Chromium binary** *(~150 MB, one-time)* — fetched by
   `python -m playwright install chromium`. **The single biggest non-pip download
   for normal use.** *Why:* every PDF, and the live in-browser résumé preview, are
   rendered by driving a headless Chromium — so the download matches the preview
   byte-for-byte and the output is deterministic. It lives in your OS user cache,
   **not** the repo. *(Note: the pip package `playwright` IS a declared dependency;
   the browser binary it pulls is not — that's why it's a separate step.)*
4. **An Anthropic API key** — a *credential*, not a download, but required: all the
   AI writing goes to Claude. Set `ANTHROPIC_API_KEY` or drop it in a `.api_key`
   file at the repo root.
5. **A modern browser** — the app is a local website you open at
   `http://localhost:5000`.
6. **(Linux only) A handful of system libraries** Chromium needs (`libnss3`,
   `libatk1.0-0`, `libgbm1`, …) — OS packages, surfaced by the Playwright installer
   if they're missing (one `apt`/`dnf`/`pacman` line).

## (b) To also run the full test + eval suite

First the dev extras — these are pip, so just the *trigger*, not a "non-dependency"
download: `pip install -e ".[dev]"` brings `pytest` / `ruff` / `mypy` / `pyyaml` /
`types-requests`. The Playwright **UX** test tier reuses the same Chromium binary
from (a)#3.

The real non-pip weight comes from the **offline grounding scorers** — *dev-only,
never in the shipped app* (they grade whether the AI invented anything):

7. **`torch`** *(~200 MB CPU wheel, larger for CUDA)* — installed **first**, from a
   platform-specific PyTorch index URL, and **deliberately kept out of
   `pyproject.toml`** because the correct wheel depends on your hardware (CPU vs
   CUDA). The compute backbone the grading models run on.
8. **The `[eval-grounding]` extras** — `transformers` plus **MiniCheck installed
   from GitHub** (`git+https://github.com/Liyan06/MiniCheck.git`, not PyPI).
9. **DeBERTa-v3 NLI weights** *(~180 MB, Apache-2.0)* — auto-download to the
   HuggingFace cache on first use. Asks: *is each bullet entailed by your source
   résumé?*
10. **MiniCheck `flan-t5-large` weights** *(~3 GB, **academic/research license —
    not permissive, never ships to production**)* — auto-download to the HF cache.
    Asks: *is each claim supported by the source document?*

*(First grounding run downloads ~3.2 GB total; cached permanently after.)*

## The why, in one breath

- **The heavy stuff is about honesty, not features.** Chromium makes the output
  *exact*; `torch` + the two model families are *graders* that measure whether the
  AI fabricated anything — and they run **only in the eval harness**, never in the
  app an end user launches.
- **The pip-vs-fetch split is deliberate.** Anything platform-specific (the
  Chromium binary, the `torch` wheel) or licensing-sensitive (MiniCheck) is kept
  *out* of the dependency list, so a normal `pip install -e .` stays clean, fast,
  fully-permissive (MIT), and end-user-safe.

## Provenance table (precise; verified 2026-06-07)

| # | Item | For | Size | Pip-managed? | On-disk location | License | Why |
|---|---|---|---|---|---|---|---|
| 1 | Python 3.10+ | (a) | — | no (OS installer) | system | PSF | the interpreter |
| 2 | `git` + repo clone | (a) | small | no | your chosen dir | repo is MIT | source (no end-user wheel) |
| 3 | Chromium binary | (a) | ~150 MB | no — `playwright` triggers it | `%LOCALAPPDATA%\ms-playwright` · `~/.cache/ms-playwright` · `~/Library/Caches/ms-playwright` | Chromium (BSD-style) | deterministic PDF + live preview |
| 4 | Anthropic API key | (a) | n/a (credential) | no | `$ANTHROPIC_API_KEY` / `.api_key` | n/a | the AI that writes |
| 5 | Modern browser | (a) | usually present | no | system | n/a | the UI shell |
| 6 | Chromium sys libs (Linux) | (a) | small | no (`apt`/`dnf`) | system | distro | Chromium runtime deps |
| 7 | `torch` | (b) | ~200 MB CPU / more CUDA | **special** — separate index URL, not in `pyproject` | site-packages | BSD-3-Clause | grading compute backbone |
| 8 | `transformers` + MiniCheck pkg | (b) | code only | yes — `[eval-grounding]`; MiniCheck via `git+` | site-packages | Apache-2.0 / academic (MiniCheck) | model runners |
| 9 | DeBERTa-v3 NLI weights | (b) | ~180 MB | no (auto HF download) | `~/.cache/huggingface` · `%USERPROFILE%\.cache\huggingface` | Apache-2.0 | NLI-entailment grounding |
| 10 | MiniCheck `flan-t5-large` weights | (b) | ~3 GB | no (auto HF download) | HF cache (as above) | **academic/research — never ship** | factual-support grounding |

---

*Status: DRAFT v1. Facts verified against `pyproject.toml`, `docs/install.md`,
`CONTRIBUTING.md` (2026-06-07). Direct input to Sprint 6.5 `docs/eval-stack-install-guide`
(#17); candidate README/`docs/install.md` "what gets downloaded & why" section.*
