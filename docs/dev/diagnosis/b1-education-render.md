# Diagnosis — education `studyType` is dropped by four of six render surfaces (Classic, Spacious, the docx writer, the markdown round-trip), and docx template font names are never captured

> **Status:** root cause PROVEN — reproduced live on HEAD `0838558`, all four surfaces
> observed directly, no mechanism inferred.
> **Branch:** `fix/b1-education-render`

---

## Symptom

A corpus education row carries three fields — institution, degree, field of study. Only
two of them reach the page. On the Classic and Spacious personas, on the `.docx`
download, and through the markdown round-trip, the field of study (`studyType`) is
silently absent; the Modern and Tech personas show it. Separately, a persona `.docx`
whose typography is direct run formatting rather than a named style loses its **font
name** in the generated download — sizes and bold survive, the typeface does not.

---

## Observed

**Every `path:line` in this section anchors the PRE-FIX tree at HEAD `0838558`** — that is
what was observed, and re-anchoring it to the fixed tree would make the evidence describe
code that did not exist when the measurement was taken. `## The fix` below carries
post-fix anchors, marked as such.

Instrument: a standalone probe (`repro_edu.py`, scratchpad — not committed; its assertions
are carried forward as the committed tests named under "Acceptance bar") that feeds ONE
JSON Resume document through every render surface and prints what each emits. Deliberately
scoped **wider than the brief's hypothesis**: the brief named only the docx writer, so the
probe renders all four bundled personas, the docx writer, and the markdown round-trip, and
additionally probes the font-capture path — precisely so a surface the brief did not name
could not hide behind one it did.

Fixture education entry (the corpus mapping is `Education.degree -> area`,
`Education.field -> studyType`, `corpus_to_json_resume.py:929-932`):

```python
{"institution": "State University", "area": "Bachelor of Science",
 "studyType": "Computer Science", "startDate": "2010-09",
 "endDate": "2014-05", "score": "GPA 3.8"}
```

**O-1 — `classic.html` drops `studyType`.** `pdf_render.render_html_string` against
`personas/bundled/classic.html:108-129`, verbatim output:

```html
Education</h2>
      <article class="degree">
        <header class="degree-header">
          <h3>
            <span class="institution">State University</span>
            <span class="sep">,</span>
            <span class="area">Bachelor of Science</span>
          </h3>
            <span class="dates">
              09-2010 – 05-2014
            </span>
        </header>
        <p class="score">GPA 3.8</p>
      </article>
```

`"Computer Science" in html` → **False**.

**O-2 — `spacious.html` drops `studyType`** (`personas/bundled/spacious.html:100-118`),
same probe, `"Computer Science" in html` → **False**:

```html
      <h3>
        <span class="institution">State University</span>
        <span class="sep">, </span>
        <span class="area">Bachelor of Science</span>
      </h3>
      <span class="dates">09-2010 – 05-2014</span>
```

**O-3 — `modern.html` and `tech.html` DO render it** → **True** for both. This is the
control arm: the field is present in the document handed to Jinja, so O-1/O-2 are a
template omission and not an upstream data loss.

```html
<!-- modern.html:148  -->  <p>Computer Science</p>
<!-- tech.html:133    -->  <div class="item-header-subtitle">Bachelor of Science — Computer Science</div>
```

**O-4 — the `.docx` writer drops `studyType`.** `generator._write_docx_from_json_resume`
with `template_path=None`, paragraphs read back with python-docx:

```
education block: ['Education',
                  'State University, Bachelor of Science\t09-2010 – 05-2014',
                  'GPA 3.8']
studyType 'Computer Science' present in docx text: False
```

This settles the brief's flagged conflict **in favour of the code trace**: the reported
docx behavior does not reproduce, and the writer's education block
(`generator.py:880-893`) reads `institution` / `area` / `startDate` / `endDate` / `score`
and nothing else. The brief's cite `generator.py:883-896` is off by three lines at HEAD —
the block is `880-893`. Re-anchored here rather than repeated.

**O-5 — the markdown round-trip is lossy.**
`json_resume.json_resume_to_markdown` → `json_resume.md_to_json_resume`:

```
emitted markdown education section:
## Education

### State University, Bachelor of Science	09-2010 – 05-2014

re-parsed education entries: [{'institution': 'State University',
                              'area': 'Bachelor of Science',
                              'startDate': '09-2010', 'endDate': '05-2014'}]
studyType survives round-trip: False
```

Both halves are lossy independently: the emitter (`json_resume.py:684-699`) never writes
`studyType`, and the parser's education branch (`json_resume.py:389-394`) has no field to
put it in.

**O-6 — `_capture_proto` captures no font name, and the template's typeface is lost in the
output.** Probe builds a `.docx` template whose every run carries
`run.font.name = "Georgia"` as direct formatting (no named style), captures it with
`generator._capture_template_styles`, then writes a download from it. Captured protos,
verbatim:

```
  job_title: {'alignment': None, 'space_before_pt': None, 'space_after_pt': None,
              'tab_stops': [(468.0, <WD_TAB_ALIGNMENT.RIGHT: 2>)],
              'run_bold': True, 'run_size_pt': 11.0}
  name:      {'alignment': <WD_PARAGRAPH_ALIGNMENT.CENTER: 1>, 'space_before_pt': None,
              'space_after_pt': None, 'tab_stops': [], 'run_bold': None,
              'run_size_pt': 18.0}
any proto carries a font name key: False
```

And the generated document, run by run:

```
output run fonts (paragraph text -> run.font.name):
    'Jane Doe' [None]
    'Experience' [None]
    'Acme, Engineer\t01-2015 – 01-2020' [None]
    'State University, Bachelor of Science\t09' [None]
template Normal style font: None
output   Normal style font: None
```

Georgia does not survive: `_capture_proto` (`generator.py:495-511`) reads
`run0.bold` and `run0.font.size` and stops, so `_apply_run_proto`
(`generator.py:588-595`) has nothing to re-apply. The brief's cite
`generator.py:498-514` is off by three lines at HEAD — the function is `495-511`.

**O-7 — the asymmetry that shows this is an omission, not a policy.** The HTML-companion
path already does exactly what the docx path does not:
`docx_to_persona_html.py:211` reads `family = run0.font.name if (run0 and run0.font.name)
else None` and feeds it into the companion's CSS `font-family`
(`docx_to_persona_html.py:315`). Two capture routines over the same `.docx`, one reads the
typeface and one does not.

**O-8 — editing `classic.html` self-heals existing companions; no manual bump exists to
forget.** `docx_to_persona_html.skeleton_version()` (`docx_to_persona_html.py:443-454`) is
`sha256(classic.html)[:16]`, and `companion_stamp_is_current`
(`docx_to_persona_html.py:466-492`) regenerates any companion whose sidecar stamp differs.
Verified as a fact about the code, not assumed: `tests/test_docx_to_persona_html.py:512`
recomputes the hash from the shipped file rather than pinning a literal.

---

## Falsified

**F-1 — "the docx writer reads `studyType` and renders it wrongly."** This is the reported
behavior the brief flagged as conflicting with the code trace, and it is the reason this
sprint's first artifact had to be a repro. **Dead.** O-4 shows the writer emits
`State University, Bachelor of Science` with no third component at all; the string
`Computer Science` is absent from every paragraph of the output. There is no wrong render
to correct — there is a missing one to add. Had the brief been implemented literally
without this check, the fix would have been aimed at a render path that does not exist.

**F-2 — "`area` and `studyType` are inverted upstream and the fix is to swap the mapping."**
Not falsified as a description — the inversion is real and observed
(`corpus_to_json_resume.py:929-932` maps `degree -> area` and `field -> studyType`, which
is the reverse of the JSON Resume convention where `studyType` is the degree). Falsified
**as this sprint's fix**: swapping it would silently rewrite how every already-rendered
document reads, with no audit of stored `Education` rows to say which column holds what in
practice, and the owner constraint is explicit — render both, never flip. Recorded here so
the next reader does not re-derive the temptation.

**F-3 — "put `studyType` on a body line under the education `### ` header instead of in the
header, so the markdown needs no new separator."** Dead by reading the parser:
`_entry_from_chunk` (`json_resume.py:406-421`) folds every non-bullet body line under an
education chunk into `entry["summary"]`, so a bare `Computer Science` line round-trips back
as a summary, not as `studyType` — and it would collide with any legitimate education
summary. The header is the only slot that round-trips.

---

## Inferred

Nothing load-bearing. Every claim above was observed directly; no mechanism in this
diagnosis rests on a hypothesis.

One genuinely unproven note, kept out of the fix: the origin of the *reported* docx
behavior in F-1 is unknown. It may have been a `modern`/`tech` persona observation
misattributed to the docx download (those two DO render `studyType`, O-3), but no artifact
of the original report exists in the repo to check against, so this stays a guess and
nothing is built on it.

---

## Falsification

**The experiment that settles it, run BEFORE the fix — and it was.** The probe in
`## Observed` is the falsification, stated as a prediction before it ran:

- **If `studyType` appeared in classic/spacious/docx/markdown output:** the reported
  defect is not this defect. Stop, do not fix, widen the instrument and report.
- **If it did not appear:** the omission is confirmed at each named surface and the fix
  may be built, scoped to exactly the surfaces where it was observed missing.

Outcome: absent at all four (O-1, O-2, O-4, O-5), present at the two control surfaces
(O-3). The second branch held.

For the font gap the same shape: **if a captured proto had carried a font name, or if the
output runs had come back as `Georgia`, the gap would be dead.** Outcome: no key captured
and `None` on every output run (O-6).

Both must fail on HEAD without the fix. The committed regression tests below are written to
do exactly that.

---

## The fix

Four changes, each aimed at a surface where the loss was **observed**, none wider.
**Anchors below are POST-fix.**

0. **One canonical joiner, not four copies** — `json_resume.education_position_text`
   (`json_resume.py:640`) plus `split_education_position` (`:662`) and the
   `EDUCATION_FIELD_SEPARATOR` constant (`:637`). This is the same arrangement
   `format_date_range` already has, and for the same reason: Classic, Spacious, the
   `.docx` writer and the markdown round-trip had each silently dropped `studyType`
   this way — Modern and Tech had not. The Jinja templates cannot import, so they
   mirror the separator inline — the one unavoidable copy, and it already existed at
   `tech.html:133`.
1. **`personas/bundled/classic.html:108`, `personas/bundled/spacious.html:100`** — render
   `studyType` in the degree `<h3>` after `area`, separated by an em dash, following
   `tech.html:133`'s existing precedent. Both render **both** fields; neither swaps them.
   Reuses the existing `.area` / `.sep` classes rather than introducing a new one:
   `docx_to_persona_html.py`'s generated-companion CSS knows only
   `.institution` / `.area` / `.sep`, so a new class would style correctly in the bundled
   personas and silently not in every user's generated companion. **Zero CSS changes.**
2. **`generator.py:911`** (`_write_docx_from_json_resume`'s education block) — passes
   `education_position_text(ed)` as the entry header's position, so the docx header line
   is the same string the preview and the `.md` render.
3. **`json_resume.py:751`** (`json_resume_to_markdown`'s education emit) and
   **`json_resume.py:389`** (`_entry_from_chunk`'s education branch) — emit
   `Institution, Area — StudyType`, and split it back apart on parse. The em dash (U+2014)
   is chosen deliberately: `_split_h3_header` prefers `", "` for the name/position split
   (`json_resume.py:434`) so, WHEN AN INSTITUTION IS PRESENT, the em dash never competes
   with it, and the date-range splitter operates only on the post-TAB segment, so it
   cannot collide with the en dash (U+2013) used between dates. `_split_h3_header`'s
   existing `" — "` fallback for work entries is untouched — it is a tested, documented
   affordance (`tests/test_json_resume.py::TestExperience::test_em_dash_position_separator`).
   When the institution is ABSENT this fallback DOES collide with the joiner — see
   "Known limits" below.
4. **`generator.py:495` `_capture_proto` / `:599` `_apply_run_proto`** — capture
   `run0.font.name` as `run_font_name` and re-apply it, mirroring `docx_to_persona_html.py`'s
   companion capture exactly. **`generator.py:611` `_add_inline_runs_with_proto`** is
   widened with it: its three emphasis branches forwarded a size-only proto, so without
   this a typeface would drop at every `**bold**` boundary — a new defect the font fix
   would otherwise have introduced. The forwarded dict is now built once instead of
   per emphasized segment.

`corpus_to_json_resume.py`'s mapping is unchanged (F-2); only its `_collect_education`
docstring (`corpus_to_json_resume.py:902`) is corrected, because it asserted `studyType` is
"not yet surfaced by any renderer" — true when written, false as of this branch.

---

## Acceptance bar

Not "the suite is green". Each observation above gets a committed test that **fails on the
pre-fix tree**:

- `tests/test_json_resume.py::TestEducationStudyTypeRoundTrip` (9 cases) — `studyType`
  survives `json_resume_to_markdown` → `md_to_json_resume`; the emitted h3 carries the
  em-dash join; `area` precedes `studyType` always (never flipped); the separator is not
  the date en dash; the cycle is idempotent; an entry with no `studyType` emits
  **byte-identically to before** with no stray separator; `_normalize_markdown` does not
  split the em-dash header into a phantom bullet.
- `tests/test_pdf_render.py::TestEducationStudyTypeRender` — all **four** bundled personas
  render both fields and never flip the pair; Classic and Spacious render `area` alone
  unchanged when `studyType` is absent, and render institution + `studyType` with no
  dangling separator when `area` is absent.
- `tests/test_render_parity.py::TestEducationRenderParity` — the `.docx` education header,
  the `.md` download, and the Classic preview all carry both fields from one source
  document: download == preview **for education**, which is the invariant that file exists
  to pin and which had no education coverage until now.
- `tests/test_render_parity.py::TestTemplateFontCapture` — a template with direct-run
  `Georgia` yields captured protos carrying it and a download whose runs report
  `font.name == "Georgia"`, including across an inline `**bold**` boundary; a template with
  no direct font yields `None` everywhere (the proto must not invent one).

Strictness notes: `pytest-rerunfailures` reports fail-fail-pass as a bare `PASSED`, so the
gate log is swept for `RERUN` by the invoking session — these tests are deterministic (no
browser, no network, no clock) and any rerun on them is itself a finding.

**What this implementer ran, and what it did not** (C-12): the four files above pass, as do
the downstream consumers of the changed surfaces —
`test_deterministic_generate`, `test_resume_date_formatting`, `test_corpus_to_json_resume`,
`test_docx_to_persona_html`, `test_ats_roundtrip`, `test_bundled_templates`,
`test_live_preview_route`, `test_app_iteration`, `test_hardening_iteration`,
`test_persona_routes`, `test_export_corpus_seed`, `test_seed_import`, `test_openapi_spec`,
`test_normalize_markdown` — plus the doc/enforcement gates
(`test_doc_links`, `test_doc_status_gate`, `test_doc_frontmatter_gate`,
`test_doc_single_home_gate`, `test_wiki_relevance_classification`,
`test_docstring_coverage_gate`, `test_evidence_gate`, `test_consumer_enumeration_gate`,
`test_blast_radius_classification`), and `ruff check` / `ruff format` / `mypy` scoped to the
changed files. **It did NOT run `python -m scripts.gate`** — the gate belongs to the
invoking session (§11.9), so no claim is made here about the full suite or the UX tier.

---

## Known limits (C-0)

**F1, raised by the branch's Sonnet refuter, investigated and NOT a regression.** The
emitter idiom `f"{a}, {b}" if (a and b) else (a or b)` (`json_resume_to_markdown`'s
education emit, `json_resume.py:751`) means an institution-less education entry emits
just `"Area — StudyType"` as the whole h3 left segment. `_split_h3_header`'s `" — "`
fallback (`json_resume.py:455-456`), which exists for `work`/`project` entries and
predates this branch, then consumes that whole string as the name/position boundary:
the joined value re-parses to `{institution: <area>, area: <studyType>}` and the
original `studyType` is lost on that cycle.

**Verified NOT a regression, by executing the actual pre-fix code** (checked out at
HEAD `0838558`, before this branch's edits — not hand-traced): pre-fix, the emitter
(`str(e.get("area") or "")` alone, never reading `studyType`) drops the field of study
from the markdown **before parsing ever runs**, so an institution-less
`{area: "Bachelor of Science", studyType: "Computer Science"}` round-trips to
`{institution: "Bachelor of Science"}` — `studyType` gone, and no `area` key either.
Post-fix the same input round-trips to
`{institution: "Bachelor of Science", area: "Computer Science"}` — `studyType`'s value
survives, re-keyed into `area`, rather than vanishing. **Not byte-identical, and not
claimed to be** — post-fix is a strict superset of pre-fix's output (one extra key,
carrying data pre-fix discarded), which is the sense in which this is proven not a
regression. Confirmed by execution, not just hand-trace:
`tests/test_json_resume.py::TestEducationStudyTypeRoundTrip::test_institution_less_entry_re_keys_studytype_into_area_on_emit`
pins the exact re-keyed shape and its second-cycle stability.

**Not reachable from the product's own forms today:** `blueprints/corpus/career_assets.py`
returns 400 for an empty `institution` at both create (`:104-106`) and edit (`:168-172`),
so this shape needs a hand-constructed JSON Resume document to reach. It is recorded here
rather than fixed because a fix would mean changing `_split_h3_header`'s shared fallback —
Consumer #11 in `docs/dev/blast-radius/b1-education-render.md` — which also serves
`work`/`project` entries and is explicitly **not** in this sprint's scope. That change,
and the more general institution-less/name-less emitter ambiguity across `work`,
`education`, and `projects` alike, is deliberately left for a separate work item rather
than fixed here or in this sprint's scope-limited fashion.
