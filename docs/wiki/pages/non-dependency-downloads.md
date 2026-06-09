# Non-dependency downloads

> **Concept:** everything you must obtain that `pip install`-ing the *declared*
> dependencies does **not** hand you — the interpreter, the repo, browser binaries, model
> weights, a credential — split by what you are trying to run. (Q3.)
> **Sources:** [`q3-downloads.md`](../../dev/excellence-walk/q3-downloads.md), whose
> facts were **verified 2026-06-07** against [`pyproject.toml`](../../../pyproject.toml),
> [`../../install.md`](../../install.md), and [`../../../CONTRIBUTING.md`](../../../CONTRIBUTING.md).
> **Use:** this is the direct input to the Sprint 6.5 `docs/eval-stack-install-guide`
> (finding #17) and a candidate README / `install.md` "what gets downloaded & why"
> section — see [`../../dev/RELEASE_CHECKLIST.md`](../../dev/RELEASE_CHECKLIST.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); sizes/licenses are the source's
> verified 2026-06-07 figures.

---

## (a) To run the basic tool

1. **Python 3.10+** — the interpreter (supports 3.10–3.13).
2. **`git` + a repo clone** — callback. ships no end-user PyPI wheel; you clone and
   `pip install -e .`.
3. **A headless Chromium binary** (~150 MB, one-time) via
   `python -m playwright install chromium` — **the single biggest non-pip download for
   normal use.** It renders every PDF and the live in-browser preview, so output matches
   the preview byte-for-byte. Lives in the OS user cache, not the repo. *(The pip package
   `playwright` is a declared dependency; the browser binary it pulls is not — hence the
   separate step.)*
4. **An Anthropic API key** — a *credential*, not a download, but required: all AI writing
   goes to Claude. `ANTHROPIC_API_KEY` env var or a `.api_key` file at the repo root.
5. **A modern browser** — the app is a local site at `http://localhost:5000`.
6. **(Linux only) a few system libraries** Chromium needs (`libnss3`, `libatk1.0-0`,
   `libgbm1`, …) — surfaced by the Playwright installer if missing.

## (b) To also run the full test + eval suite

The dev extras (`pip install -e ".[dev]"` → pytest / ruff / mypy / pyyaml /
types-requests) are pip, so just the *trigger*. The Playwright UX test tier reuses the
Chromium binary from (a)#3. The real non-pip weight is the **offline grounding scorers**
— *dev-only, never in the shipped app* (they grade whether the AI invented anything):

7. **`torch`** (~200 MB CPU wheel, larger for CUDA) — installed **first**, from a
   platform-specific PyTorch index URL, and **deliberately kept out of `pyproject.toml`**
   because the correct wheel depends on your hardware.
8. **The `[eval-grounding]` extras** — `transformers` + **MiniCheck installed from GitHub**
   (`git+https://github.com/Liyan06/MiniCheck.git`, not PyPI).
9. **DeBERTa-v3 NLI weights** (~180 MB, Apache-2.0) — auto-download to the HuggingFace
   cache on first use. *Is each bullet entailed by your source résumé?*
10. **MiniCheck `flan-t5-large` weights** (~3 GB, **academic/research license — never
    ships to production**) — auto-download to the HF cache. *Is each claim supported by
    the source document?*

*(First grounding run downloads ~3.2 GB total; cached permanently after.)*

## The why, in one breath

- **The heavy stuff is about honesty, not features.** Chromium makes the output *exact*;
  `torch` + the two model families are *graders* that measure whether the AI fabricated
  anything — and they run **only in the eval harness**, never in the app an end user
  launches `[synthesis]`.
- **The pip-vs-fetch split is deliberate.** Anything platform-specific (Chromium, the
  `torch` wheel) or licensing-sensitive (MiniCheck) is kept *out* of the dependency list,
  so a plain `pip install -e .` stays clean, fast, fully-permissive (MIT), and
  end-user-safe.

## Provenance (verified 2026-06-07)

| # | Item | For | Size | Pip-managed? | License |
|---|---|---|---|---|---|
| 1 | Python 3.10+ | (a) | — | no (OS installer) | PSF |
| 2 | `git` + repo clone | (a) | small | no | repo is MIT |
| 3 | Chromium binary | (a) | ~150 MB | no — `playwright` triggers it | Chromium (BSD-style) |
| 4 | Anthropic API key | (a) | credential | no | n/a |
| 5 | Modern browser | (a) | usually present | no | n/a |
| 6 | Chromium sys libs (Linux) | (a) | small | no (`apt`/`dnf`) | distro |
| 7 | `torch` | (b) | ~200 MB CPU / more CUDA | **special** — separate index URL | BSD-3-Clause |
| 8 | `transformers` + MiniCheck pkg | (b) | code only | yes — `[eval-grounding]`; MiniCheck via `git+` | Apache-2.0 / academic |
| 9 | DeBERTa-v3 NLI weights | (b) | ~180 MB | no (auto HF download) | Apache-2.0 |
| 10 | MiniCheck `flan-t5-large` weights | (b) | ~3 GB | no (auto HF download) | **academic/research — never ship** |

On-disk caches: Chromium → `%LOCALAPPDATA%\ms-playwright` · `~/.cache/ms-playwright` ·
`~/Library/Caches/ms-playwright`; HF weights → `~/.cache/huggingface` (verified 2026-06-07).

## Related

- [[excellence-walk]] — the walk this provenance belongs to.
