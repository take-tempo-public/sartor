# Document rendering

> **Audience:** `dev`
> **Concept:** the deterministic render path — LLM markdown (or the corpus DB)
> → JSON Resume v1.0 → `.docx` (original-as-style-template), `.pdf` (Playwright
> Chromium), or `.md`. No LLM call lives on this path, by contract.
> **Sources:** [`generator.py`](../../../generator.py), [`json_resume.py`](../../../json_resume.py), [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py), [`pdf_render.py`](../../../pdf_render.py), [`blueprints/generation.py`](../../../blueprints/generation.py), [`docs/architecture.md`](../../architecture.md) §Output formats.
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What this page covers

The render boundary turns produced content into a downloadable document. It is
P1 Hardening — purely deterministic, no LLM call (the boundary itself is canonical
in AGENTS.md; see [[deterministic-llm-boundary]]). Three sibling formats, one
canonical intermediate (JSON Resume v1.0), and one load-bearing rule for `.docx`:
the original file is opened as a **style template**, never `docx.Document()` on blank.

## The entry point and the three branches

[`generator.py:generate_resume`](../../../generator.py) is the single résumé entry
for the **LLM-markdown** path. It always runs
[`generator.py:_normalize_markdown`](../../../generator.py) first, then parses to
JSON Resume via [`json_resume.py:md_to_json_resume`](../../../json_resume.py), applies
[`json_resume.py:apply_identity_override`](../../../json_resume.py) and
[`json_resume.py:scrub_ats_unsafe`](../../../json_resume.py) to eliminate stale identity
and ATS-unsafe characters, then branches on `output_format`:

- `.md` → serialize the SAME `json_doc` the other formats render, via
  [`json_resume.py:json_resume_to_markdown`](../../../json_resume.py) — not the
  pre-override, pre-scrub markdown verbatim, so a fixed identity field or an
  ATS-unsafe character never leaks into a `.md` download
  ([`generator.py:generate_resume`](../../../generator.py)) `[synthesis]`.
- `.pdf` → `_render_pdf_from_json` → [`pdf_render.py:render_pdf`](../../../pdf_render.py).
- else (`.docx`) → [`generator.py:_write_docx_from_json_resume`](../../../generator.py) with the persona `.docx` as template.

The three-format table is mirrored in [`docs/architecture.md`](../../architecture.md) §Output formats.

## The frozen-composition entry point (no markdown round-trip)

[`generator.py:generate_resume_from_json_resume`](../../../generator.py) is the
sibling **deterministic** entry point for the generation-experience
re-architecture's Phase 4: when Compose has frozen an `approved_composition`
(a JSON Resume dict, already resolved by
[`corpus_to_json_resume.py:build_json_resume_from_corpus`](../../../corpus_to_json_resume.py)),
it renders that doc **directly** through the same `.md`/`.pdf`/`.docx` writers
`generate_resume` uses after its `md_to_json_resume` parse — skipping the parse
entirely, so download == preview == `approved_composition` by construction, with
zero résumé-body LLM calls and no markdown round-trip
([`generator.py:generate_resume_from_json_resume`](../../../generator.py)). It
writes the same `.jsonresume.json` sidecar as `generate_resume`. The Flask callers
are `POST /api/generate` / `POST /api/generate/stream`
([`blueprints/generation.py:run_generation`](../../../blueprints/generation.py) /
[`run_generation_stream`](../../../blueprints/generation.py)), which call it only
when [`blueprints/generation.py:_frozen_composition`](../../../blueprints/generation.py)
returns a non-`None` doc; legacy and pre-freeze corpus contexts fall through
unchanged to `generate_resume` off the LLM's markdown `[synthesis]`.

Every résumé call also writes a best-effort `resume_{ts}.jsonresume.json` sidecar
(the canonical intermediate) next to the primary output; a sidecar write failure
logs a warning but never blocks the primary document [`generator.py:generate_resume`](../../../generator.py).
Cover letters mirror the three formats through [`generator.py:generate_cover_letter`](../../../generator.py)
but emit **no** sidecar — a cover letter is not a résumé `[synthesis]`.

## Markdown normalization (defensive pre-pass)

[`generator.py:_normalize_markdown`](../../../generator.py) re-injects newlines an
LLM may have smushed away, so every downstream renderer sees structural markers on
their own lines: a blank line before `#`/`##`/`###` headers, a newline before
`- <Capital>` bullets, and a break between a single-word `## Title` and its body.
It is conservative (only unambiguous markers) and idempotent — well-formed markdown
passes through unchanged [`generator.py:_normalize_markdown`](../../../generator.py).
The one case it does NOT repair is the name/subtitle/contact triad smushed onto the
first line; the docstring points the fix at the prompt side, not here `[synthesis]`.

`BULLET_RE` ([`generator.py`](../../../generator.py)) is the single regex that
normalizes every bullet variant (`-`, `*`, `•`, `–`, `—`, `·`, `◆`, `●`, `▪`, `›`, `‣`)
to plain text before rendering; it is reused by both the résumé writer and the
cover-letter writer.

## JSON Resume — the canonical intermediate

[`json_resume.py:md_to_json_resume`](../../../json_resume.py) lifts normalized
markdown into a JSON Resume v1.0 dict. It is best-effort and forgiving: a header
block (everything before the first `##`) becomes `basics` (name, email/phone/URL
detected by regex, profiles classified by host); `##` sections dispatch through
`_SECTION_MAP` to `work`/`education`/`skills`/etc. Unknown sections are NOT dropped —
they land under `meta.sartor.unparsed` so nothing is silently lost. sartor.-specific
fields live under `meta.sartor.*` so the doc still validates against the standard
schema [`json_resume.py:md_to_json_resume`](../../../json_resume.py). This is the
JSON contract the renderers consume — distinct from the pipeline's `context_set`
(see [[context-set-contract]]).

### Bracket-aware list splitting (item 15)

Free-text lists (skills, keywords) are comma / pipe / middot separated, which naively
fragments any entry containing a parenthetical: "Eval Framework Design (LLM-as-judge,
rubric-based)" split into two bogus skills.
[`json_resume.py:split_outside_brackets`](../../../json_resume.py) is the shared
primitive that fixes it — it splits on a caller-supplied delimiter pattern while
tracking `()` / `[]` depth and ignoring delimiters nested inside a group.
`_parse_skills` uses it on both forms it handles: the grouped `Label: a, b, c` line
and the flat `_SKILLS_SPLIT_RE` line ([`json_resume.py:_parse_skills`](../../../json_resume.py)).

Two degenerate-input behaviors are deliberate and documented in its docstring rather
than left to be discovered: a **stray closing bracket** with no opener is ignored
instead of letting tracked depth go negative (negative depth would mask every later
delimiter), and an **unclosed opening bracket** makes the remainder of the string one
trailing token — the same "give up gracefully" a plain split has on malformed input,
just scoped to the tail rather than the whole string. The pattern must contain no
capturing groups, since it is embedded into an internal alternation `[synthesis]`.

It is deliberately **public and shared** rather than duplicated: `evals/bootstrap.py`
imports it for résumé skill extraction, so the eval side and the render side cannot
disagree about where a skill ends — see [[eval-harness]].

## `.docx` — original-as-style-template

[`generator.py:_write_docx_from_json_resume`](../../../generator.py) opens the persona `.docx` via
`docx.Document(str(tp))` (only when the template exists and is `.docx`), then
**captures per-role formatting prototypes** from the template before clearing the
body and rewriting it:

- [`generator.py:_capture_template_styles`](../../../generator.py) walks the
  template's paragraphs and classifies each by role (name/subtitle/contact from the
  centered top triad; `job_title` = bold + right tab stop; `section_heading` = bold,
  no tab; `job_subtitle` = non-bold after a job title; else `body`). Missing roles
  fall back to the writer's built-in defaults so a partial capture still renders cleanly.
- [`generator.py:_clear_body`](../../../generator.py) removes all `w:p`/`w:tbl`
  children but preserves the trailing `w:sectPr` (margins/section props).
- [`generator.py:_extract_list_numPr`](../../../generator.py) deep-copies the
  template's list-numbering element so emitted bullets inherit the original's
  numbering style ([`generator.py:_apply_numPr`](../../../generator.py)).

When NO valid template is supplied, the writer falls back to `docx.Document()` on
blank with Calibri 11 and clean default margins — the explicit "clean defaults"
escape, not the styled path `[synthesis]`. The "never call `docx.Document()` on a
blank when a template exists" rule is canonical in AGENTS.md; this is its
implementation site `[synthesis]`. Inline `**bold**`/`*italic*` markers are honored
per-run by [`generator.py:_add_inline_runs`](../../../generator.py) /
[`generator.py:_add_inline_runs_with_proto`](../../../generator.py).

The cover-letter `.docx` is a separate, terser writer
([`generator.py:_write_cover_letter_docx`](../../../generator.py)): plain `Normal`
paragraphs, persona font, dense line spacing, no name banner — incidental headings
and bullets are stripped to plain text.

## `.pdf` — Playwright Chromium

[`pdf_render.py:render_pdf`](../../../pdf_render.py) renders the JSON Resume dict
through a Jinja2 HTML template + persona CSS, writes the result to a temp file in the
template's own directory (so the relative `<link href="...css">` resolves under
Chromium's file:// same-origin), and prints via headless Chromium `page.pdf()`
(Letter, fixed margins). The HTML companion (the `.html` sibling of the `.docx`) is
resolved by
[`docx_to_persona_html.py:resolve_companion_html`](../../../docx_to_persona_html.py),
which generates the companion lazily when absent AND regenerates it when a
sidecar-stamped `skeleton_version` shows it predates the currently-shipped HTML
skeleton (a pre-2026-07-09 imported template otherwise froze at its clone-time
skeleton forever — B1a, `docs/dev/diagnosis/b1-stale-template-companions.md`); the
lower-level [`pdf_render.py:html_template_path_for`](../../../pdf_render.py) is now
an internal existence check `resolve_companion_html` calls, not the resolution
entry point itself. `_render_pdf_from_json` falls back to bundled `classic.html` and
raises `FileNotFoundError` if none exists [`generator.py`](../../../generator.py).
Playwright (not WeasyPrint) was chosen because the same HTML+CSS feeds the in-app
live preview ([`pdf_render.py:render_html_string`](../../../pdf_render.py)) — true
WYSIWYG, no GTK3/Pango system deps. Chromium is a one-time out-of-repo install
[`pdf_render.py`](../../../pdf_render.py).

## The corpus-direct preview path

[`corpus_to_json_resume.py:build_json_resume_from_corpus`](../../../corpus_to_json_resume.py)
builds the SAME JSON Resume shape directly from the DB (Candidate + Experience +
Bullet + SummaryItem + Skill rows), bypassing markdown entirely. It exists to break
the old "preview only after a generate" coupling: it reflects the candidate's live
curation state, optionally applying `composition_overrides` read from a
`context_*.json` (pin/exclude/added bullets, pinned summary/title/skill, per-role
intros) [`corpus_to_json_resume.py:build_json_resume_from_corpus`](../../../corpus_to_json_resume.py).
Because structured fields come from columns, the header has no smushed name/contact
triad — the failure mode `_normalize_markdown` cannot fully repair is sidestepped
on this path `[synthesis]`. Skill curation logic is shared with the generate prompt
via [`corpus_to_json_resume.py:resolve_skill_selection`](../../../corpus_to_json_resume.py)
so preview and output agree exactly (the dual-reach is in [[corpus-to-output-reach]]).

## Why this matters

Two producers (LLM markdown, corpus DB) converge on one intermediate — JSON Resume —
which fans out to three renderers through **two** entry points that share the same
writers: `generate_resume` (parses markdown first) and `generate_resume_from_json_resume`
(renders an already-built doc directly). Keeping every step deterministic makes the
document exactly reproducible from a saved sidecar or context file, and keeps the LLM
out of the formatting layer entirely `[synthesis]`.

## Related

- [[code-module-map]] — where these four modules sit in the deterministic layer.
- [[generation-and-grounding]] — the upstream LLM that produces the markdown this path renders.
- [[corpus-to-output-reach]] — how corpus curation reaches both the preview and the generate prompt.
- [[deterministic-llm-boundary]] — the P1 rule that forbids an LLM call here.
- [[eval-harness]] — the other consumer of `json_resume.split_outside_brackets`.
