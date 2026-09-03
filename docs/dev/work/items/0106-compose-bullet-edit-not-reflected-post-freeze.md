```toml
schema = 1
id = 106
kind = "item"
title = "Compose bullet-text edits don't reach an already-frozen application's preview, generate, or download"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
refs = [
  "static/app.js:9318-9346",
  "blueprints/corpus/experiences.py:499-555",
  "blueprints/generation.py:837-853",
  "blueprints/generation.py:919-1119",
  "blueprints/templates.py:1081-1097",
  "corpus_to_json_resume.py:363-400",
  "docs/dev/work/items/0066-composition-frozen-flag-goes-sticky-stale.md",
]
summary = "Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot."
```

**Reported by the owner** (2026-09-02): editing a bullet's text at the Compose step does not
show up in the preview, the generate-preview, or the downloaded résumé — "as if the edits
were never made." Described as a recurring bug (multiple sessions), not a one-off.

**Confirmed mechanism, read from code** (not yet reproduced live — see Unverified below).
The Compose "Edit" button on a bullet (`static/app.js:9282-9287` →
`_editComposeBullet`, :9325-9346) calls `PUT /api/bullets/<id>` with the new text. That
route, `update_bullet` (`blueprints/corpus/experiences.py:499-555`), writes only
`Bullet.text` (+ recomputed `has_outcome`) to the corpus DB row. It never touches the
application's `approved_composition` and never re-freezes anything.

For an application whose composition has already been frozen (Compose's "Save and
continue"), **all three surfaces the owner named read that frozen snapshot verbatim, not
the corpus:**

- **Generate** — `/api/generate` resolves `frozen_doc = _frozen_composition(context_set)`
  (`blueprints/generation.py:837-853` → `hardening.frozen_composition_doc`) and, when
  present, assembles the résumé directly from `frozen_doc` via
  `_assemble_from_frozen_composition` (`blueprints/generation.py:1003-1012`) — zero
  résumé-body LLM call, zero corpus re-read.
- **Download** — same `frozen_doc`, rendered directly
  (`blueprints/generation.py:1095-1102`).
- **Preview** — `blueprints/templates.py:1092-1095` serves `ctx_data["approved_composition"]`
  verbatim unless the user has a separate hand-edit override (`edited_resume_text`).

The comment at `blueprints/generation.py:1092-1094` states this is by construction:
"download == preview == approved_composition ... no markdown round-trip." And
`freeze_approved_composition`'s own docstring (`corpus_to_json_resume.py:376-380`) says the
freeze is *deliberately* a value snapshot "so a later edit to a corpus row can't
retroactively change an approved application." So for a frozen application, today's
behavior matches a documented design decision — the defect is that nothing tells the user
this at the moment they act.

**The misleading affordance.** The Edit-bullet modal's own copy
(`static/app.js:9330-9331`) reads: "This edits the bullet in your career corpus, so it
applies to future applications too — not just this one." That phrasing implies the edit
*does* apply to the current application, immediately — it says nothing about the current
application already being frozen and therefore NOT picking up the edit until an explicit
re-freeze. A user reading that copy and then checking preview/generate/download has no way
to know why nothing changed.

**Related but distinct from item 66.** Item 66 documents the same frozen-snapshot-doesn't-
reread-the-corpus family, but for `composition_overrides` fields (pin/exclude/summary
retype) going through the debounced *autosave*, which item 66 says deliberately omits
`freeze`. This item's trigger — the corpus-wide bullet **text** edit via
`PUT /api/bullets/<id>` — doesn't go through the autosave or the composition-save route at
all, so it isn't just "omits freeze," it never attempts to persist against the application
in any form. Same root cause class, different, uncovered trigger.

**Unverified — flagged, not asserted (C-7/C-12):**
- Not yet reproduced live in this session; the above is read-from-code, not an observed
  run. The exact repro (frozen application, edit an included bullet's text via Compose,
  check preview/generate/download) should be run before this is treated as confirmed.
- Whether the same failure reproduces on an application that has **never** been frozen
  (first-time Compose, before any "Save and continue"). If the pre-freeze preview /
  legacy `generate()` path also fails to reflect the edit, that is a materially different
  (and more severe — no freeze involved at all) bug than the one described above.
- Whether clicking "Save and continue" again re-resolves fresh corpus text and fixes the
  view. `freeze_approved_composition` → `build_json_resume_from_corpus` reads the DB at
  call time, so re-running it should pick up the edit — reasoned from code, not run.

**Proposed fix (not evaluated against product intent — same class of call item 66 left
open):** either (a) invalidate/re-freeze `approved_composition` when a bullet belonging to
an already-frozen application's active composition is edited from Compose, or (b) if the
snapshot-immutability is intentional, say so in the Edit-bullet modal at the moment of the
edit rather than leaving the user to discover it as silent non-persistence across three
surfaces.

## Updates

### 2026-09-02 — filed at owner request, from a live bug report

Filed from the owner's description plus a read-code trace to the exact write/read paths;
not yet reproduced against a running instance. Cross-referenced against item 66, the
closest existing item, and confirmed the trigger (`PUT /api/bullets/<id>`) is not the one
item 66 covers.
