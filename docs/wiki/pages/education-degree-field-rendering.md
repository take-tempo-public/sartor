# Education degree and field rendering

> **Audience:** `dev`
> **Concept:** how an education entry's degree and field of study travel from
> the corpus to a rendered résumé line, and why both fields are shown together
> with a single canonical separator across all output formats.
> **Sources:** [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py),
> [`json_resume.py`](../../../json_resume.py),
> [`generator.py`](../../../generator.py),
> [`docs/dev/diagnosis/b1-education-render.md`](../../dev/diagnosis/b1-education-render.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The field mapping: corpus → JSON Resume

The corpus stores three discrete education fields: `institution`, `degree`, and
`field` of study. When building a JSON Resume document,
[`corpus_to_json_resume.py:_collect_education`](../../../corpus_to_json_resume.py)
maps them as follows (lines 939–941):

- `Education.degree` → JSON Resume `area`
- `Education.field` → JSON Resume `studyType`
- `Education.institution` → JSON Resume `institution`

**This mapping reverses the JSON Resume convention**, where `studyType` is
defined as the degree and `area` as the field of study
([`corpus_to_json_resume.py:914-915`](../../../corpus_to_json_resume.py)). The
reversal is deliberate and **not flipped**: the canonical comment explains that
answering which column *really* holds which would require a data audit of stored
`Education` rows (owner constraint, per
[`corpus_to_json_resume.py:916-917`](../../../corpus_to_json_resume.py)).
Instead, every renderer shows **both** fields joined by a single canonical
separator `[synthesis]`.

## The canonical joiner: `education_position_text`

The single presentation-boundary helper for joining the two fields is
[`json_resume.py:education_position_text`](../../../json_resume.py) (lines
673–692). It takes a JSON Resume education entry and returns a position string
combining `area` and `studyType`:

```python
parts = [str(entry.get(key) or "").strip() for key in ("area", "studyType")]
return EDUCATION_FIELD_SEPARATOR.join(p for p in parts if p)
```

The separator is [`json_resume.py:EDUCATION_FIELD_SEPARATOR`](../../../json_resume.py)
(line 670), defined as `" — "` (em dash, U+2014, deliberately not the en dash
U+2013 used by `format_date_range` for dates). The two dashes stay
distinguishable so that when an institution is present, the em dash never
collides with the institution/position boundary split
([`json_resume.py:658-669`](../../../json_resume.py)) `[synthesis]`.

This is the same "one canonical helper at the presentation boundary" arrangement
that `format_date_range` already follows — and for the same historical reason:
before `fix/b1-education-render` (2026-08-13), Classic, Spacious, the `.docx`
writer, and the markdown round-trip had each silently dropped `studyType`
entirely; Modern and Tech had not (`corpus_to_json_resume.py:920-922`)
`[synthesis]`.

The inverse helper [`json_resume.py:split_education_position`](../../../json_resume.py)
(lines 695–705) parses the joined line back into `(area, studyType)` for
round-trip fidelity `[synthesis]`.

## Rendering: `.docx` and all other formats

**`.docx` generation.** [`generator.py:_write_docx_from_json_resume`](../../../generator.py)
(lines 920–935) renders education entries by calling `education_position_text`
directly when building the entry header (line 929). This ensures the `.docx`
education line is the same string the preview and `.md` render
([`generator.py:927-928`](../../../generator.py)) `[synthesis]`.

**Markdown round-trip.** [`json_resume.py:json_resume_to_markdown`](../../../json_resume.py)
emits education entries as `"Institution, Area — StudyType"` with the em-dash
join (lines 784–785, per diagnosis F1
[`docs/dev/diagnosis/b1-education-render.md`](../../dev/diagnosis/b1-education-render.md)).
The parser [`json_resume.py:_entry_from_chunk`](../../../json_resume.py) (lines
389–394) splits the h3 header back apart, so `studyType` survives the
round-trip `[synthesis]`.

**Bundled personas (HTML/PDF).** The persona Jinja2 templates (`classic.html`,
`spacious.html`, `modern.html`, `tech.html`) render `area` and `studyType`
inline, mirroring the em-dash separator (which cannot be imported like
`education_position_text` can). Both fields are shown; neither is reordered
([`docs/dev/diagnosis/b1-education-render.md:247-253`](../../dev/diagnosis/b1-education-render.md))
`[synthesis]`.

## Known edge cases

**Institution-less entries.** When `institution` is absent, the emitted markdown
is just `"Area — StudyType"` (no leading comma). The markdown parser's fallback
(`_split_h3_header`, lines 456–457) then treats the whole string as the
name/position boundary and re-parses it, moving `studyType`'s value into the
`area` key. This is **not a regression** — pre-fix the field was dropped
entirely; post-fix it survives, re-keyed (`docs/dev/diagnosis/b1-education-render.md:F1`,
lines 326–350) `[synthesis]`. The shape is not reachable from the product's own
forms today (the corpus rejects empty `institution` at create/edit per
`blueprints/corpus/career_assets.py:104-106`), and fixing it would require
changing `_split_h3_header`'s shared fallback, which serves `work`/`project`
entries too — deliberately left for a separate work item per diagnosis lines
357–360 `[synthesis]`.

## Related

- [[document-rendering]] — the full render pipeline this education line feeds into.
- [[career-corpus]] — where education data originates and is curated by the user.
- [[deterministic-llm-boundary]] — why this path is deterministic (no LLM call).
