# Bundled Template License

All `.docx` files under `personas/bundled/` are released under the **MIT
License**, matching this project's overall license (see `LICENSE` at the
repo root).

```
MIT License — callback. bundled templates

Copyright (c) 2026 callback. contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Bundled file inventory

| File | Display name | Typography |
|---|---|---|
| `classic.docx` | Classic Single-Column | Arial 11pt, conservative spacing, uppercase section headings |
| `modern.docx` | Modern Single-Column | Calibri 11pt, small-caps section headings, tighter line spacing |
| `spacious.docx` | Spacious (Career Changer / Junior) | Arial 11pt, generous spacing, uppercase headings |
| `tech.docx` | Tech (ATS-optimized) | Georgia 11pt, centered name, underlined section headings |

*(Compact and Hybrid Tech were retired in the v1.0.0 curation — Compact's
sidebar layout was ATS-unsafe; Hybrid Tech was rebuilt as `tech.docx`. See
`db/migrations/versions/0005_curate_bundled_templates.py`.)*

Each `.docx`'s core properties (visible in Word's File → Info pane) carry
the title, description, and an MIT license notice.

## Provenance

All four templates are **originally authored** for this project. None copy
content, structure, or styling directly from any third-party template.

Design conventions that informed the structure (single-column, standard
section headings, right-tab dates, no tables) are common ATS-resume best
practices documented widely. The following are credited for shaping the
project's understanding of those conventions but were NOT copied:

- **Jake's Resume** (Overleaf, MIT license, LaTeX) — informed the
  single-column + right-tabbed-date convention used in `classic.docx`.
- **Anubhav's single-column resume** (Overleaf, MIT license, LaTeX) —
  reinforced the value of typographic restraint (originally for the
  since-retired `compact.docx`).
- **Jobscan's ATS template guidance** (commercial, non-copying) — informed
  the rule set in `docs/template_authoring.md`.

Re-generate with `python -m scripts.build_bundled_templates`. The script is
the canonical source — the `.docx` files are derivative outputs.
