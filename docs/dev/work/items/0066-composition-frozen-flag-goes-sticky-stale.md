```toml
schema = 1
id = 66
kind = "item"
title = "`_compositionFrozen` goes sticky-stale: a post-freeze Compose edit leaves the Step-5 rail open over a stale snapshot"
status = "watching"
decision_owner = "agent"
refs = [
  "static/app.js",
  "blueprints/applications.py",
  "docs/dev/diagnosis/wizard-rail-frozen-composition-gate.md",
]
summary = "Freeze, return to Compose, edit: the debounced autosave omits `freeze`, so the client flag stays true."
```

**The sequence.** Save-and-continue freezes the composition and sets
`_compositionFrozen` from the server's `frozen` answer. The user then navigates back
to Compose (step 3) and edits — pins a bullet, retires a gap-fill, retypes the
summary. The debounced autosave (`_scheduleCompositionSave` → `_postComposition`
without `freeze`) rebuilds `composition_overrides` but deliberately does **not**
re-freeze, so `approved_composition` on the context file still holds the *pre-edit*
snapshot. Nothing clears `_compositionFrozen`, so the client keeps asserting frozen
over a document that no longer matches what Compose shows.

**Generation itself is unaffected, and that bounds the severity.** `/api/generate`
re-reads `approved_composition` from the context file on every run and never consults
the client flag (`blueprints/generation.py:_frozen_composition` →
`hardening.frozen_composition_doc`). A run in this state assembles the stale-but-real
frozen document deterministically — exactly what the user approved at freeze time,
and exactly what the Step-5 "no AI variation" copy promises. The output is honest;
what is dishonest is the *implied currency* of it. This is a UX-honesty gap, not a
correctness one.

**Pre-existing, but newly load-bearing.** The flag has behaved this way since the
freeze landed. Before item 20 it only chose which of two Step-5 copy blocks rendered
(`_renderGenerateStepCopy`); a stale `true` meant the user read the frozen copy a beat
early. Item 20 made the same flag the Step-5 **rail gate** (`_wizardReachable`), so it
now also decides navigability. The gap did not widen — its consequence did.

**Why it was not fixed in the item-20 sprint.** Closing it means deciding what a
post-freeze edit *means*: re-freeze on every autosave (cheap to write, but it silently
re-approves content the user never clicked Save-and-continue on — the freeze exists
precisely to be an explicit act), or clear the flag and re-lock Step 5 (honest, but it
bounces a user out of a step they were legitimately standing on). That is a product-flow
call, not a mechanical one, and item 20's branch was scoped to the rail gate.

**Detection sketch, for whoever takes it** (none evaluated, none endorsed): the server
already knows — `save_application_composition` could return the same
`frozen_composition_doc` answer on *non*-freeze saves too (it currently hard-codes
`frozen = false` there), letting the client distinguish "no frozen document" from
"frozen document, now stale" without a second predicate.

## Updates

### 2026-08-09 — filed at `fix/wizard-rail-frozen-composition-gate` close-out (Epic A, item 20 sprint)

Surfaced during the item-20 fix and deferred there deliberately; the sprint commit
records it as "filed not fixed". No `epic` pointer set, matching the precedent of items
63–65: attaching a `watching` item to epic 36 would block that epic's closure on an
observation nobody has committed to resolving.
