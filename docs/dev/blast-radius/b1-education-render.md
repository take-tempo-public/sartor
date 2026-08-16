# Blast radius — b1-education-render

> **Branch:** `fix/b1-education-render`
> **Status:** enumeration complete — written **before** the first production edit.

**Every `path:line` below anchors the PRE-EDIT tree at HEAD `0838558`.** That is the point
of the ordering rule: this is the map that was drawn before the territory changed, and
re-anchoring it afterwards would turn it into a description of what got done. Post-fix
anchors live in `docs/dev/diagnosis/b1-education-render.md` § "The fix".

**Gate status, stated plainly (C-0):** `require-consumer-enumeration` does **not** fire on
this branch. None of the four files changed here is in `GATED` /`GATED_PREFIXES`
(`scripts/enforcement/blast_radius.py:78-185`); `json_resume.py` is in
`ACKNOWLEDGED_NOT_GATED` (`:211-214`, "8 non-test importers; deterministic renderer whose
output shape is already pinned by tests/test_json_resume*.py"). This dossier is written
anyway because the substance of C-10 applies whether or not the hook does: the education
render shape is reproduced independently across six surfaces — the four bundled personas
plus the `.docx` writer and the markdown round-trip — and the sprint's whole point is that
four of them (Classic, Spacious, the `.docx` writer, and the markdown round-trip) had
silently dropped `studyType` while the remaining two (Modern, Tech) rendered it correctly.
An enumeration was the cheapest way to find out whether there is a seventh.

---

## Surface

| File | What changes |
|---|---|
| `personas/bundled/classic.html` | education `<h3>`, lines 111-118 — add a `studyType` span after `area` |
| `personas/bundled/spacious.html` | education `<h3>`, lines 103-110 — same |
| `generator.py` | `_write_docx_from_json_resume`'s education block (`:880-893`) — join `area` + `studyType` for the entry header. Separately `_capture_proto` (`:495-511`), `_apply_run_proto` (`:588-595`), `_add_inline_runs_with_proto` (`:598-625`) — add `run_font_name` to the captured proto dict |
| `json_resume.py` | `json_resume_to_markdown`'s education emit (`:684-699`) and `_entry_from_chunk`'s education branch (`:389-394`) — carry `studyType` through the markdown round-trip |

The proto **dict shape** (`{"alignment", "space_before_pt", "space_after_pt", "tab_stops",
"run_bold", "run_size_pt"}`) is the one thing here that smells like a contract, so it gets
its own enumeration below.

---

## Enumeration

Ripgrep over the whole tree (gitignore-respecting), before the first edit.

**1. Every name `studyType` goes by.** The JSON Resume key is the only form — there is no
alias, no re-export, no column called `studyType` (the DB column is `Education.field`).

```
rg -c studyType --glob '!docs/**'
corpus_to_json_resume.py:2          # the producer: field -> studyType (:912 doc, :932 code)
json_resume.py:1                    # a comment only (:390) — no code path
personas/bundled/modern.html:1      # renders it (:148)
personas/bundled/tech.html:1        # renders it (:133)
tests/test_corpus_to_json_resume.py:2
-> 7 occurrences across 5 files
```

**Negative results, recorded because they are findings:**

- `static/app.js` — **0** hits for `studyType`. Its 22 `education` hits are the corpus
  editor, which speaks the API shape (`institution` / `degree` / `field`,
  `blueprints/corpus/_shared.py:259-278`), not the JSON Resume shape. Not a consumer.
- `templates/index.html` (4 `education` hits), `dashboard/templates/dashboard.html` (3) —
  **0** `studyType`. Section labels and corpus panels, not renderers.
- `evals/schemas/context_set.schema.json`, `docs-site/openapi.json`,
  `evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json` — **0** `studyType`.
  No schema pins the education entry's inner shape, so widening what a renderer reads
  breaks no contract.
- `db/ats_roundtrip.py` — has `"education"` only as a section-heading label in
  `_KNOWN_SECTIONS` (`:53`). It diffs bullets and headings, never education fields.

**2. Every consumer of the markdown round-trip** (both directions of the pair I am
changing):

```
rg -l 'json_resume_to_markdown|md_to_json_resume' -g '*.py'   -> 16 files
   non-test (7): generator.py  json_resume.py  hardening.py
                 blueprints/generation.py  blueprints/templates.py
                 db/ats_roundtrip.py  pdf_render.py (docstring reference only)
   tests   (9): test_json_resume  test_render_parity  test_deterministic_generate
                test_resume_date_formatting  test_app_iteration  test_eval_runner
                test_live_preview_route  test_hardening_iteration  test_egress_allowlist
```

**3. Every consumer of the proto dict shape.**

```
rg -n '_capture_proto|_apply_run_proto|_apply_para_proto|_capture_template_styles|run_size_pt|run_bold' -g '*.py'
```

All executable hits are inside `generator.py`. Three references outside it, all textual:
`docx_to_persona_html.py:38,141,146` ("mirrors `generator._capture_template_styles`"),
`scripts/build_bundled_templates.py:6`, `tests/test_docx_to_persona_html.py:175`. The proto
dict is **module-private and never serialized** — it is built and consumed within a single
`_write_docx_from_json_resume` call, so adding a key cannot reach stored data or another
module.

**4. Every renderer of an education entry** (the enumeration that actually mattered —
it is what proved the persona divergence is 2-of-4 — Classic and Spacious — rather than
1-of-4):

```
rg -n 'ed\.area|ed\.studyType|ed\.institution|ed\.score' -g '*.html'
  classic.html:115,116,117,125   spacious.html:107,108,109
  modern.html:140,141,142,148    tech.html:132,133
```

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `personas/bundled/classic.html:111-118` | **update** | Observed dropping `studyType` (diagnosis O-1). The primary/default persona. |
| 2 | `personas/bundled/spacious.html:103-110` | **update** | Observed dropping `studyType` (O-2). |
| 3 | `personas/bundled/modern.html:148` | **no change** | Already renders `studyType` as its own `<p>` (O-3). Its layout puts the field on a second line by design; forcing the h3 join would change a persona that is not defective. |
| 4 | `personas/bundled/tech.html:133` | **no change** | Already renders `area — studyType` (O-3). It is the **precedent** the other two are being brought into line with, including the exact ` — ` (U+2014) separator. |
| 5 | `generator.py:880-893` (docx education block) | **update** | Observed dropping `studyType` (O-4). |
| 6 | `generator.py:495-511` `_capture_proto` | **update** | Observed not capturing `run.font.name` (O-6). |
| 7 | `generator.py:588-595` `_apply_run_proto` | **update** | The re-apply half of #6; capturing without applying is a no-op. |
| 8 | `generator.py:598-625` `_add_inline_runs_with_proto` | **update** | Its three inline branches forward a **size-only** proto (`:614,618,622`). Left alone, a typeface would drop at every `**bold**` / `*italic*` boundary — a new defect created by #6/#7. Found by this enumeration, not by the brief. |
| 9 | `json_resume.py:684-699` markdown education emit | **update** | Observed dropping `studyType` (O-5, emit half). |
| 10 | `json_resume.py:389-394` `_entry_from_chunk` education branch | **update** | Observed dropping `studyType` (O-5, parse half). Both halves or the round-trip stays lossy. |
| 11 | `json_resume.py:428-468` `_split_h3_header` | **no change** | Shared by work / education / project. Its `", "`-preferred split already yields `position = "Area — StudyType"` when an institution is present; the education-specific second split belongs in #10, not in a helper three entry kinds share. |
| 12 | `corpus_to_json_resume.py:929-932` (`degree -> area`, `field -> studyType`) | **no change** | The documented inversion. Owner constraint is render-both-never-flip; flipping needs a data audit of stored `Education` rows that this sprint is not scoped to do (diagnosis F-2). |
| 13 | `blueprints/corpus/_shared.py:259-278` `_education_to_dict` | **no change** | The corpus REST shape is `institution`/`degree`/`field` — a different vocabulary that this change never touches. |
| 14 | `docx_to_persona_html.py:141-215` (companion capture) | **no change** | Already reads `run0.font.name` (`:211`) into the companion CSS (O-7). It is the model for #6, not a site to edit. |
| 15 | `docx_to_persona_html.py:443-454` `skeleton_version()` | **no change needed, but load-bearing** | A content hash of `classic.html`, so editing #1 auto-invalidates every generated companion sidecar and they regenerate (O-8). No constant to bump — verified, not assumed, because forgetting one would ship #1 to new users only. |
| 16 | `hardening.py`, `blueprints/generation.py`, `blueprints/templates.py` (round-trip callers) | **no change** | They pass markdown through the pair as an opaque string. Widening what education emits/parses is additive; no caller reads `education[].area` itself. |
| 17 | `db/ats_roundtrip.py:53` | **no change** | Section-label matching only; never reads education fields. |
| 18 | `tests/test_json_resume.py:320-333,431` | **update (extend)** | Existing assertions use no `studyType` and stay valid; new cases added for the round-trip. |
| 19 | `tests/test_pdf_render.py:162-180` | **update (extend)** | Same — the existing Classic education case has no `studyType`; it becomes the "unchanged when absent" control. |
| 20 | `tests/test_render_parity.py` | **update (extend)** | Its whole invariant is download == preview; education was never covered there, which is how the two surfaces drifted apart unnoticed. |
| 21 | `tests/test_docx_to_persona_html.py:512` | **no change** | Recomputes the skeleton hash from the shipped file, so #1 cannot break it. Checked rather than assumed. |
| 22 | `evals/schemas/context_set.schema.json` | **no change** | Does not constrain the education entry's inner keys (enumeration §1). |

---

## Deferred

- **`spacious.html` does not render `education[].score`** while `classic.html` does
  (`classic.html:125`). Observed while enumerating #2, genuinely inconsistent, and **not
  fixed here**: it is a different field with a different judgment behind it (Spacious omits
  GPA deliberately or by oversight — nothing in the repo says which), and folding it in
  would widen a sprint whose scope is `studyType` + the font gap. **Not filed by me** —
  work-item filing and `BOARD.md` regeneration belong to the closer (§11.9.1), and this
  file is evidence, not a tracker. Handed to the closer in this sprint's implementer
  report so it becomes a board row rather than a note nobody actions.
- **The `area`/`studyType` inversion itself** (#12) — deferred by owner constraint, not by
  my judgment. Needs a data audit of stored `Education.degree` / `Education.field` values
  before anyone can say which column actually holds a degree in practice.
- **`emit_bullet` applies no run proto at all** (`generator.py:788-796` calls
  `_add_inline_runs`, not `_add_inline_runs_with_proto`), so bullets already inherit
  nothing from the template — including, after this change, the font name. Pre-existing,
  observed while doing #8, and deliberately untouched: changing which paragraphs receive
  template typography is a rendering-policy change, not a capture-gap fix. **Not filed by
  me** — same reason as above; handed to the closer in the implementer report. Pinned in
  the meantime by `tests/test_render_parity.py::TestTemplateFontCapture`, which asserts
  fonts on the header/heading/summary paragraphs and deliberately does **not** claim
  anything about bullets.

---

## Verification

How a **missed consumer** would surface, as distinct from a broken change:

1. **The renderer enumeration is exact-set-checkable.** `rg 'ed\.area|ed\.studyType' -g
   '*.html'` returns four files; a fifth persona added later without `studyType` would show
   up as a new file in that set. The four are individually asserted: Classic and Spacious in
   `tests/test_pdf_render.py`, Modern and Tech already covered by their own existing render
   assertions plus the diagnosis control arm (O-3).
2. **`tests/test_render_parity.py` is the cross-surface tripwire.** It asserts the docx and
   the preview render the same document. Education was outside its coverage until now, which
   is precisely why #1/#2/#5 could diverge from #4 unnoticed for as long as they did.
   Extending it means a future change to one education surface and not the other fails
   loudly instead of silently.
3. **The markdown round-trip is self-checking by construction** — `emit -> parse -> compare`
   in `tests/test_json_resume.py` fails if either half is missed, so #9 and #10 cannot be
   half-done.
4. **`mypy .`** catches a proto-dict key typo at #6/#7/#8 only weakly (the dict is
   `dict[str, Any]`), so the font behavior is pinned by an output-level assertion —
   reading `run.font.name` back off the generated `.docx` — rather than by types.
5. **Not verified by me:** the full gate. Per §11.9 the gate belongs to the invoking
   session; this implementer ran no gate and makes no claim about one.
