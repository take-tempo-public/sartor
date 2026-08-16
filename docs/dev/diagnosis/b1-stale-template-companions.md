# Diagnosis — an imported template's preview companion freezes at the skeleton it was cloned from

> **Status:** root cause PROVEN — reproduced end to end, including a second
> mechanism the sprint brief did not predict (the guard is never reached on the
> preview path at all).
> **Branch:** `fix/b1-stale-template-companions`

---

## Symptom

A `.docx` persona imported before 2026-07-09 previews with wrong dates forever.
A current role renders its raw stored `2023-04` instead of `04-2023 – Present`:
the `– Present` disappears and the date is not in the product's `MM-YYYY`
presentation format. The downloaded `.docx` is correct — only the preview (and
the PDF built from it) is wrong. Nothing the user can do in the app fixes it;
re-saving or re-selecting the template changes nothing.

---

## Observed

Instrument: `repro_stale_companion.py`, run from the repo root against
`C:/Dev/sartor` (scratchpad script, not committed — its four facts are
reproduced verbatim below). It stages a companion exactly as a pre-2026-07-09
import would have left it, then exercises the guard, the sidecar, and the
render.

**Fact 1 — the `date_range` global entered the skeleton on 2026-07-09, and the
pre-image interpolated raw ISO dates.** `git log -1 --format='%H %ad' --date=iso 67b83cc`
returns `67b83ccfa4d27f164aeac59a9849289b477cafec 2026-07-09 00:05:36 -0700`.
The pre-image at `git show cb3d2d8:personas/bundled/classic.html` renders the
work dates as:

```jinja
{{ job.startDate or "" }}{% if job.startDate and job.endDate %} – {% endif %}{{ job.endDate or "" }}
```

HEAD's `personas/bundled/classic.html:54` renders `{{ date_range(job.startDate, job.endDate) }}`
instead. A companion cloned from the pre-image therefore has **no call to
`date_range` at all**, so registering the global
(`pdf_render.py:71-87`, `_register_date_range_global`) cannot reach it.

**Fact 2 — the regeneration guard returns early and rewrites nothing, so the
stale skeleton survives.** With the staged old-skeleton companion in place, the
instrument printed:

```
'date_range(' in staged companion : False
html >= docx (guard's condition)  : True
returned          : (WindowsPath('.../uploaded.html'), WindowsPath('.../uploaded.css'))
html mtime_ns changed : False
html bytes changed    : False
'date_range(' present after the call : False
sidecar contents  : '{\n  "layout_fidelity": "full"\n}'
```

`docx_to_persona_html.py:438-444` is the early return: it tests only
`html_path.exists()`, `css_path.exists()` and `html_path.stat().st_mtime >= docx.stat().st_mtime`.
Nothing in that condition mentions the skeleton, so a skeleton change is
invisible to it. The sidecar it wrote (`docx_to_persona_html.py:449-452`) carries
`layout_fidelity` and nothing else — there is no field the guard could have
consulted.

**Fact 3 — the render consequence, measured.** Rendering the same JSON Resume
(one current role, `startDate: "2023-04"`, `endDate: ""`) through
`pdf_render.render_html_string` against each companion:

```
stale companion dates line(s) : ['2023-04']
'Present' in stale render     : False
fresh companion dates line(s) : ['04-2023 – Present']
'Present' in fresh render     : True
```

The loss is **wider than the sprint brief predicted**: the stale companion loses
the `MM-YYYY` presentation format too, not only the `– Present` suffix. Both
come from the same missing `date_range` call.

**Fact 4 — no production call site ever passes `force=True`.** `git grep -n generate_companion`
(tests/docs filtered) returns exactly six call sites, all using the default
`force=False`:

```
blueprints/templates.py:654:        if generate_companion(target) is None:
blueprints/templates.py:879:        generate_companion(target_path)
blueprints/templates.py:1051:            companion = generate_companion(docx_template_path)
blueprints/templates.py:1333:                companion = generate_companion(docx_template_path)
blueprints/templates.py:1419:            companion = generate_companion(docx_template_path)
generator.py:262:            companion = generate_companion(docx_template_path)
```

So the `force=True` escape hatch exists but is unreachable from the product; the
only caller that passes it is the test suite.

**Fact 5 — the preview and PDF paths never call the guard for an existing
companion, so fixing the guard alone would not fix the bug.** Four of the six
sites are resolution sites, and every one of them calls `generate_companion`
**only when the companion is absent**:

- `blueprints/templates.py:1044-1052` — `html_path = html_template_path_for(...)`, then `if html_path is None:` → generate.
- `blueprints/templates.py:1330-1334` — same shape.
- `blueprints/templates.py:1411-1420` — same shape.
- `generator.py:255-264` — same shape.

`pdf_render.py:66-68` (`html_template_path_for`) is `return html if html.exists() else None`.
A stale companion **exists**, so the resolver returns it and the `if ... is None`
branch never runs. This is a second gate in front of the first: the mtime guard
at `docx_to_persona_html.py:438-444` is not merely wrong on the preview path, it
is **not executed** there.

**Fact 6 — bundled personas have no `.persona.json` sidecar, and that is a usable
ownership discriminator.** `ls personas/bundled/` returns exactly
`classic/modern/spacious/tech` × `.css`/`.docx`/`.html` plus `__init__.py` — no
`*.persona.json`. `git show ba034a5:docx_to_persona_html.py` (the module's first
commit) already wrote the sidecar at its line 367/381, so **every** companion
this module has ever generated has one, and every hand-authored bundled
companion has none.

---

## Falsified

**"The user's `.docx` mtime is the problem; touching the file would refresh the
companion."** It would — but it is not the mechanism and not a fix. Fact 5 shows
the preview path never calls `generate_companion` while the companion exists, so
an mtime bump only helps at the two unconditional call sites (upload, copy),
neither of which a user can trigger for a template already in their library.

**"Registering the `date_range` Jinja global covers user companions
automatically."** The docstring at `pdf_render.py:80-83` says the generated
companion "is a verbatim copy of `classic.html`'s skeleton, so it inherits this
automatically." Fact 1 falsifies that for any companion cloned **before** the
skeleton changed: the global is registered on the environment, but the stale
template contains no call to it. The claim is true only at generation time, not
for the life of the companion.

**"Making the resolution sites call `generate_companion` unconditionally is the
simple fix."** Rejected on evidence, not taste: `_resolve_persona_template_path`
can return a **bundled** persona, whose hand-authored `modern.html` / `tech.html` /
`spacious.html` are not classic-skeleton clones. Calling a regenerating
`generate_companion` on those would overwrite them with the Classic skeleton and
re-typed CSS. Today that is unreachable only because the existence check keeps
the call from happening (Fact 5) — the moment regeneration is added, the
existence check stops protecting them. Fact 6 is what makes a safe version
possible.

**"A hand-maintained `SKELETON_VERSION = "2"` constant is enough."** Discarded:
it re-creates the exact failure class being fixed — the stamp and the artifact it
describes can drift apart silently, and the next skeleton edit lands with the
constant unbumped. A content hash of the skeleton file cannot drift from the
skeleton by construction.

---

## Inferred

Nothing load-bearing is left at the hypothesis stage. The one claim not directly
measured: that real user installs contain such companions. It is an inference
from Fact 1 + Fact 2 (any import before 2026-07-09 produced one, and nothing has
ever refreshed it), not an observation of a live install — no user `personas/`
tree was inspected, since that directory is gitignored real data. The fix does
not depend on the count being nonzero.

---

## Falsification

**The experiment, stated so it can fail** — `tests/test_docx_to_persona_html.py::test_stale_skeleton_companion_is_regenerated`:
stage a companion whose sidecar carries no `skeleton_version` (byte-identical to
what every pre-fix generation wrote — Fact 2's artifact) with an mtime newer than
the `.docx`, call the resolution entry point, and assert the resolved `.html`
contains `date_range(`.

- **If it fails on HEAD:** confirmed — the guard/resolver pair really does freeze
  the companion, and the fix may be built.
- **If it passes on HEAD:** the hypothesis is dead. Stop, widen the instrument,
  report.

Result: **fails on HEAD**, verified in a pristine detached worktree at HEAD
(`git worktree add --detach ... HEAD`, `acdb737`; removed afterwards). Two forms
of evidence, kept apart on purpose because they are not equally strong:

1. **Weak form** — the committed tests fail there with
   `AttributeError: module 'docx_to_persona_html' has no attribute 'resolve_companion_html'`
   (7 failed, 4 passed). That only proves the new API is new. It is **not**
   evidence of the defect, and is recorded here so no later reader mistakes it
   for evidence.
2. **Strong form** — the instrument, run inside that same HEAD worktree against
   untouched HEAD code, reproduced the defect exactly: `html bytes changed :
   False`, `'date_range(' present after the call : False`,
   `'Present' in stale render : False`. This is the falsification that counts,
   and it is what licensed building the fix.

The companion experiment, guarding the fix's own blast radius:
`test_resolve_companion_html_does_not_touch_bundled_companions` — resolving a
bundled persona must leave `modern.html` byte-identical. It passes on HEAD
(nothing regenerates today) and must keep passing after the fix.

---

## The fix

Two changes, because Fact 5 proved one was not enough.

1. **Stamp the skeleton, and make the guard read it** — `docx_to_persona_html.py`.
   `skeleton_version()` is the SHA-256 (first 16 hex chars) of
   `personas/bundled/classic.html`, computed once per process and cached, so the
   stamp cannot drift from the artifact it describes. `generate_companion` writes
   it into `.persona.json` alongside `layout_fidelity`, and its early return now
   also requires the recorded stamp to equal the current one. A pre-fix sidecar
   has no `skeleton_version` key, so it compares unequal and regenerates — no
   migration needed.

2. **Give the resolution path an entry point that can refresh** —
   `resolve_companion_html(docx_path)`, called at the four sites in Fact 5 in
   place of the `html_template_path_for` → `if None: generate` dance. It resolves
   an existing companion, regenerates it when the module owns it (sidecar
   present — Fact 6) and the stamp is stale, generates one when absent, and
   returns `None` on failure so every caller's existing bundled-Classic fallback
   is unchanged. Hand-authored bundled companions have no sidecar and are
   therefore never rewritten, which is what keeps Falsified #3 from coming true.

Deterministic throughout — no LLM call enters `docx_to_persona_html.py` (charter
C-6). Cost on the hot preview path when the companion is current: one `stat`,
one ~90-byte JSON read, and a cached hash lookup — no `.docx` parse, which is
the expensive part and still happens only on an actual mismatch.

---

## Acceptance bar

- `test_stale_skeleton_companion_is_regenerated` fails on HEAD and passes after
  the fix, with no rerun (`pytest-rerunfailures` reports a fail-fail-pass as a
  bare `PASSED` — a green line is not evidence unless the log has no `RERUN`).
- `test_current_companion_not_regenerated` proves the "not needlessly
  regenerated" half: a second resolve leaves `mtime_ns` byte-identical, so the
  fix cannot have turned every preview into a `.docx` re-parse.
- `test_resolve_companion_html_does_not_touch_bundled_companions` keeps the
  Falsified #3 clobber from shipping.
- End-to-end: rendering through a refreshed companion yields `04-2023 – Present`,
  matching Fact 3's fresh-companion measurement exactly.
- The four resolution sites in Fact 5 all route through the new entry point —
  `git grep -n html_template_path_for` shows no remaining resolve-then-generate
  pair.
