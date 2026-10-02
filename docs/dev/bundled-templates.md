# Bundled templates — how they're built and how to add one

> **Purpose:** the maintainer half of the template docs: the role-paragraph order the
> generator depends on, how the four bundled `.docx` templates are produced, and the steps
> to add a new one. Split out of the user template guide in Epic D sprint D3.
> **Audience:** `dev` — contributors changing the bundled templates or the style-capture
> code in `generator.py`.
> **Authoritative for:** the role-paragraph order a template must carry; the bundled-template
> build and add procedure. The **ATS rule set** itself lives in the user guide,
> [`docs/user/templates.md`](../user/templates.md#the-ats-rules-every-template-should-follow),
> which `scripts/build_bundled_templates.py` and `docs/bundled_templates_LICENSE.md` cite.

---

## Role-paragraph order (load-bearing)

`generator.py:_capture_template_styles` walks the first ~30 paragraphs of a template and
classifies each by role, using position and formatting. The generator then re-renders the
user's content by mapping its markdown onto these captured roles. A template whose
paragraphs don't follow this order produces wrongly styled output.

| # | Role | What it carries | Notes |
|---|---|---|---|
| 1 | `name` | Candidate's full name | Bold, larger than body. Alignment may vary by preset. |
| 2 | `subtitle` | Optional title line (e.g., "Senior Product Manager") | Same alignment as name. Smaller font. |
| 3 | `contact` | Email \| phone \| linkedin \| website | Same alignment. Body-sized or smaller. |
| 4 | `section_heading` | "Experience" (first section heading) | Bold; uppercase / underline / small-caps optional. |
| 5 | `job_title` | "Company, Role" + right tab + "Date – Date" | Tab stop required for date alignment. |
| 6 | `job_subtitle` | Optional italic context line | One line under job_title; commonly italic. |
| 7 | `body` | Plain prose paragraph | Used for Summary sections that aren't bulleted. |
| 8 | `bullet` | List Bullet style paragraph | Indented `-` glyph; preserves throughout the document. |

After the first instance of each role, the generator extends with cloned copies. Extra
paragraphs beyond the role examples are allowed but not needed.

---

## The four bundled templates

The files under `personas/bundled/` differ **only in typography** (font, size, spacing,
alignment, casing) at the `.docx` level; their structure is identical. Their `.html`/`.css`
companions, used by the live preview and the PDF render, also differ in layout (see
`personas/bundled/*.css`).

| File | Display name | Font |
|---|---|---|
| `classic.docx` | Classic Single-Column | Arial |
| `modern.docx` | Modern Single-Column | Calibri |
| `spacious.docx` | Spacious (Career Changer / Junior) | Arial |
| `tech.docx` | Tech (ATS-optimized) | Georgia |

The typography knobs for each are the `PRESETS` entries in
`scripts/build_bundled_templates.py`. All four are regenerated with:

```bash
python -m scripts.build_bundled_templates
```

The script is idempotent and overwrites the existing files.

The set was curated from five to four at v1.0.0: Compact's sidebar layout was not ATS-safe,
and Hybrid Tech was rebuilt as `tech.docx`. See
`db/migrations/versions/0005_curate_bundled_templates.py`.

---

## Adding a bundled template

1. Add a `TypographyPreset` entry to `scripts/build_bundled_templates.py:PRESETS`.
2. Choose `filename`, `display_name` and `description`, and tune the typography knobs. Keep
   the structure. Use a font from `json_resume.APPROVED_FONTS`, because output maps any
   other font onto that list.
3. Add `suggested_role_tags`, which the template picker surfaces as defaults.
4. Run `python -m scripts.build_bundled_templates` to regenerate.
5. Update the seed migration (`db/migrations/versions/0002_seed_bundled_templates.py`) to
   insert the new `persona_template` row.
6. Update `docs/bundled_templates_LICENSE.md`.

## How output is checked

Every generated `.docx` is parsed back through `parser.py` by `db/ats_roundtrip.py`, which
compares the recovered sections and bullet count with what the generator emitted. The
result is stored on the application run (`ats_roundtrip_json`, written in
`blueprints/generation.py`) and shown per iteration in the Pipeline detail modal. It is
best-effort: it catches gross failures, and is not a guarantee of acceptance by any specific
ATS.
