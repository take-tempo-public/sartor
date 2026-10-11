# Diagnosis — a Compose edit made after "Save and continue" never reaches preview, generate or download

> **Status:** root cause **PROVEN** at the server, by a deterministic HTTP-level instrument
> run against this branch's base tip. The client half (the Step-5 rail stays open) is read
> from code, not driven — see `## Inferred`.
> **Branch:** `fix/frozen-composition-staleness` (work items 106 + 132, folding in 66 and the
> typed-edits drop, owner's pick 2026-10-10)

Base tip: `76f7a44`. Instrument: `tests/test_frozen_composition_staleness.py` (commit 1 of this
branch). Machine: Windows 11, Python 3.13.14, about 1.06 GB free RAM. Session `b504b487`.

---

## Symptom

- **Item 106 (owner-reported 2026-09-02, "recurring"):** editing a bullet's text at the Compose
  step doesn't show up in the preview, the generated résumé, or the download — "as if the edits
  were never made."
- **Item 66 (Watching since 2026-08-09):** after Save and continue, going back to Compose and
  pinning, excluding or retyping leaves Step 5 open over the pre-edit snapshot.
- **Item 132 (filed 2026-09-29, unverified):** Step 6 "Submit answers and regenerate" saves the
  answers but may not change the résumé.

---

## Observed

Everything here is output from a command run on this branch at base `76f7a44`, not a reading of
the source. The instrument drives the real routes (analyzer stubbed, no LLM): seed a corpus →
`POST /api/analyze` → Compose Save and continue (`POST /api/applications/<id>/composition` with
`freeze: true`) → one post-freeze edit (the arm) → every surface. Each test prints one JSON
observation line.

**The two runs.**

```
python -m pytest tests/test_frozen_composition_staleness.py -p no:randomly -q --no-header -p no:rerunfailures -o addopts=""
......................xxxxxxxxxxxxxxxxxxxxxxxx                           [100%]
22 passed, 24 xfailed in 47.70s
```

```
python -m pytest tests/test_frozen_composition_staleness.py -p no:randomly -q --no-header -p no:rerunfailures -o addopts="" --runxfail -rA --tb=line > <scratch>/instrument-runxfail.log
24 failed, 22 passed in 52.60s
```

The quotes below are verbatim lines from `<scratch>/instrument-runxfail.log` (278 lines).

### O1. After any post-freeze Compose edit, both generate routes return 200 with the pre-edit snapshot

Eight arms, each one edit as the client issues it today: R1 bullet text (`PUT /api/bullets/<id>`,
item 106), R2 pin, R3 exclude, R4 summary retype (autosave, item 66), R5 gap-fill accept
(`/gap-fill-decide`), R7 approve a pending bullet (`POST /api/bullets/<id>/accept`), R8 approve
a pending skill (`PUT /api/skills/<id>`), R9 add a title then pin it. For **every** arm:
`compose_state_equals_snapshot: false`, and on **both** routes `status: 200`,
`body_equals_snapshot: true`, `body_equals_compose_state: false`, and zero LLM calls. R1, verbatim:

```
{"arm": "R1_bullet_text_item106", "compose_state_equals_snapshot": false, "generate": {"body_equals_compose_state": false, "body_equals_snapshot": true, "error": null, "llm_calls": {"analyze": 0, "cover_letter_llm": 0, "generate": 0, "generate_streaming": 0}, "marker_in_body": false, "marker_in_file": false, "status": 200}, "generate_stream": {"body_equals_compose_state": false, "body_equals_snapshot": true, "error": null, "llm_calls": {"analyze": 0, "cover_letter_llm": 0, "generate": 0, "generate_streaming": 0}, "marker_in_body": false, "marker_in_file": false, "status": 200}, "marker": "ZEBRA-EDITED led the billing rewrite that cut churn 18 percent", "marker_in_compose_state": true, "marker_in_compose_view": true, "marker_in_snapshot": false, "preview": {"marker": false, "status": 200}}
```

So the edited text **is** in Compose's own view (`GET /composition`, `marker_in_compose_view:
true`) and in what a re-freeze would approve, and is **absent** from the preview, the generate
body and the downloaded file. The D1 test fails for all eight arms, e.g.
`test_frozen_composition_staleness.py:793: AssertionError: {'arm': 'R1_bullet_text_item106', ...}`.

### O2. Nothing the client can read changes: the server reports the stale state as fresh

For every one of the eight arms, the projection of server-derived booleans (`resume_state` from
`GET /api/applications/<id>` plus an edit-free autosave's response, request echoes excluded) is
identical before and after the edit. R1, verbatim:

```
{"arm": "R1_bullet_text_item106", "projection": [{"autosave": {"frozen": false}, "resume_state": {"has_composition": true, "has_frozen_composition": true, "resumable": true}}, {"autosave": {"frozen": false}, "resume_state": {"has_composition": true, "has_frozen_composition": true, "resumable": true}}]}
```

`has_frozen_composition` stays `true` after the edit, and a non-freeze save answers
`frozen: false` both before and after. D3 fails for all eight arms
(`test_frozen_composition_staleness.py:809`).

### O3. The Step-6 refinement drafter is handed the stale snapshot

For the seven arms whose change shows in its `<current_resume>` block (all but R8), the block
`draft_surgical_refinement` received equals the snapshot's, not Compose's:

```
{"arm": "R1_bullet_text_item106", "blocks_differ": true, "drafter_sees_compose_state": false, "drafter_sees_snapshot": true}
```

R8 (a skill) is excluded on purpose: the block carries no skills, observed as
`{"arm": "R8_approve_pending_skill", ..., "drafter_blocks_differ": false, ...}`.

### O4. Item 132, server half: answers are saved, and the regenerate is byte-identical

```
{"answer_in_body": false, "answer_saved_to_context": true, "arm": "O1_answers_then_regenerate_item132", "generate_identical": true, "generate_status": 200, "llm_calls": [{"analyze": 0, "cover_letter_llm": 0, "generate": 0, "generate_streaming": 0}, {"analyze": 0, "cover_letter_llm": 0, "generate": 0, "generate_streaming": 0}], "stream_identical": true, "stream_status": 200}
```

`/api/answer-clarifications` wrote the answer into the child context's `clarifications`; the
following `/api/generate` and `/api/generate/stream` returned bodies identical to the first
generate, with no LLM call. (The client's "Submit answers and regenerate" calls
`/api/generate/stream`, `static/app.js:3182` → `runGeneration()`.)

### O5. Typed edits ("Use edits as baseline") vanish from the preview after a regenerate

```
{"arm": "O2_typed_edits", "edited_text_kept_in_new_context": false, "regenerate_identical": true, "resume_state_context_is_newest": true, "typed_in_preview_after_regenerate": false, "typed_in_preview_before_regenerate": true, "typed_in_resume_state_md": true}
```

Before the regenerate the preview shows the typed edit. The regenerate produced an identical
résumé, wrote a new context without `edited_resume_text`, and the preview of the new context no
longer shows the edit — while `resume_state.resume_md` (what resuming the application loads)
still does. The two disagree (D6 fails).

### O6. The builder reads exactly four context keys

```
{"arm": "O4_builder_reads", "keys": ["composition_overrides", "llm_recommendations", "llm_skill_recommendations", "llm_summary_recommendation"]}
```

Top-level keys `build_json_resume_from_corpus` read from the context dict (a recording dict
subclass), with overrides, an accepted gap-fill and a summary retype in place.

### O7. The preview serves the approved snapshot, edit or not

For all eight arms, `marker_in_preview == marker_in_snapshot` (e.g.
`{"arm": "R1_bullet_text_item106", "marker_in_preview": false, "marker_in_snapshot": false, "preview_status": 200}`).

### O8. Controls

- **C1 (frozen, no edit):** every surface equals the snapshot, and two `GET /composition` plus a
  `GET /api/applications/<id>` leave the context file's bytes unchanged (`PASSED`).
- **Arm validity:** each of the eight arms changes what Save and continue would approve
  (`compose_state_equals_snapshot: false` for all eight, `PASSED`).

---

## Falsified

- **"The edit is lost even on an application that was never frozen"** (item 106's open, more
  severe variant). Dead: C0 edits before the first Save and continue; the freeze captures it and
  both routes serve it:
  `{"arm": "C0_never_frozen", "compose_state_equals_snapshot": true, "edit_in_analyze_time_career_corpus": false, ... "marker_in_body": true, "marker_in_file": true, "status": 200 ...}`.
  The analyze-time `career_corpus` does **not** carry the edit (`false` above), and it doesn't
  need to: the freeze reads the DB.
- **"A second Save and continue doesn't help either."** Dead: C2 (edit, then freeze again) →
  `"marker_in_snapshot": true` and the edited text on both routes (`PASSED`).
- **"Submit answers and regenerate makes an AI call."** Dead: O4 above, zero `generate` /
  `generate_streaming` calls.
- **"`PUT /api/bullets/<id>` could tell a Compose edit from a Career Corpus panel edit."** Dead:
  R1 and C3 send byte-identical requests. So no server-only change to that route can mark the
  right application stale; the signal has to come from Compose.
- **"Staleness = the DB differs from the snapshot"** (a content diff). Ruled out by owner decision
  1 and C3: after a Career Corpus panel edit the DB differs from the snapshot
  (`"compose_state_equals_snapshot": false` in C3), yet that application must stay approved
  (`PASSED`: projection unchanged, both routes serve the snapshot).

---

## Inferred

- **The client half — Step 5 stays reachable after a post-freeze edit.** Not driven in a browser
  this session. Read from code: the rail gate is `if (step === 5 && !_compositionFrozen) return
  false;` (`static/app.js:7120`), and `_compositionFrozen` is assigned only at `:524`, `:1098`,
  `:6650` and `:9657` (the freeze). O2 shows the server gives the client nothing to clear it
  with. The UX instrument (rail truth table after a post-freeze Pin) was not run locally: one
  Chromium does not fit in about 1 GB free alongside the owner's applications. CI carries the UX
  tier; the fix's UX regression test is where this gets driven.
- **The bullet-edit modal and the Compose hint contradict each other** (`static/app.js:9368-9369`
  "applies to future applications too — not just this one" vs `templates/index.html:318-321`
  "Edits affect this application only"). Read, not a defect the instrument can see.
- **Item 132, client half.** The "Submit answers and regenerate" handler
  (`static/app.js:3143-3184`) saves then calls `runGeneration()`; with O4 that means the user sees
  an identical résumé. Read, not driven.
- **A cover letter generated separately may be dropped by a résumé-only regenerate**
  (`hardening.py:2078` writes `last_generated_cover_letter = ""` into the child). Not
  instrumented this session — the plan's O3 arm was dropped to keep commit 1 bounded. Carried
  forward; out of this branch's scope.

---

## Falsification

The instrument above. Stated in advance:

- **If the D1/D3/D5/D6 invariants fail on HEAD and the controls pass:** the mechanism is a
  frozen snapshot that no post-freeze Compose edit reaches, and that nothing reports as stale.
  Build the fix.
- **If they pass on HEAD:** the hypothesis is dead. Stop and widen.

**Result: they fail on HEAD** (24 failed under `--runxfail`; every control and design-kept fact
passed). Committed with `xfail(strict=True)`, so the tree stays green and the fix commit only
deletes the markers. One exception, declared: the corpus-edit arms (R1, R7, R8, R9) go through
`_Rig.compose_corpus_edit`, which today sends exactly what Compose sends. When the fix gives
Compose a new signal for its corpus edits, that one helper gains the call; the assertions do not
change.

---

## The fix

_Phase 2 of this branch; written when it lands._

---

## Acceptance bar

- `tests/test_frozen_composition_staleness.py` with every `xfail` marker deleted: all tests pass,
  with `-p no:rerunfailures`, and C3 still passes (a Career Corpus panel edit never stales an
  approved application).
- Both generate routes refuse a stale composition without any LLM call
  (`generate == generate_streaming == 0`), never falling through to the legacy `generate()`.
- A UX regression test drives the client half: a post-freeze Compose edit locks Step 5; Save and
  continue unlocks it; re-entering Compose with no edit does not lock it.
- CI: `python -m scripts.ci_wait <n>` exits 0 (exit 3 means a test needed a retry: stop and look).
