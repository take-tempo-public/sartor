# Diagnosis — after a generate or a detached letter consumes the typed letter edit, the run row still holds it, and `resume_state` shows the stale text (item 163)

> **Status:** mechanism OBSERVED for both routes that replace a letter (the with-letter
> generate, JSON and SSE, and the detached `/api/generate-cover-letter`); the fix is not yet
> written. One adjacent path (the frozen `carry_edits=True` generate) was observed and does NOT
> show this defect.
> **Branch:** `fix/run-row-letter-edit-shadow`

---

## Symptom

A candidate types a letter edit, then regenerates a letter. The wizard shows the new letter.
Resuming the application from the Pipeline shows the typed text again, because the run row's
`edited_cover_letter_text` outlived the edit the context consumed. `has_edits` also stays true.

---

## Observed

Run on `main` @ `562a3a0` plus `tests/test_run_row_letter_edit.py` only (no production edit),
2026-10-14, `python -m pytest tests/test_run_row_letter_edit.py -p no:rerunfailures
-p no:cacheprovider --runxfail -q -k "a1_a2 or a3"`. All three arms fail at the invariant line,
`assert 'ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter' is None`, after
three controls held in the same arm (the context holds the new letter, the context edit is
gone, the run row's `generated_cover_letter_md` is the new letter).

**O1. A with-letter generate over a typed edit, JSON route** (`A1A2-json`):

```
{"arm": "A1A2-json", "run_cover_letter_md": "ZEBRA-REWRITTEN a second, regenerated cover letter", "resume_state_cover_letter_md": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "child_last_generated_cover_letter": "ZEBRA-REWRITTEN a second, regenerated cover letter", "child_edited_cover_letter_text": null, "run_edited_cover_letter_text": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "run_edited_resume_text": null, "has_edits": true}
```

**O2. The same over the SSE route** (`A1A2-stream`): identical in every field quoted above
(`run_edited_cover_letter_text` and `resume_state_cover_letter_md` both the typed text,
`child_edited_cover_letter_text` null, `has_edits` true). This arm's first run raised
`ControlFailed` because the drive stubbed `generate` but the stream route calls
`generate_streaming`; the helper now stubs both (see Falsified F1).

**O3. The detached letter route over a typed edit** (`A3`), the half item 163 only inferred:

```
{"arm": "A3", "run_cover_letter_md": "ZEBRA-REWRITTEN a second, regenerated cover letter", "resume_state_cover_letter_md": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "child_last_generated_cover_letter": "ZEBRA-REWRITTEN a second, regenerated cover letter", "child_edited_cover_letter_text": null, "run_edited_cover_letter_text": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "has_edits": true}
```

**O4. Controls on the unfixed tree** (all passed; they must keep passing after the fix):
`C1` a saved letter edit lands on the context and the run row; `C2-json`/`C2-stream` a
résumé-only regenerate keeps the typed letter edit on both sides (owner decision D4 of item
162); `C3` a discarded résumé edit leaves `run_edited_cover_letter_text` untouched while
`run_edited_resume_text` is `None`.

**O5. The frozen `carry_edits=True` path with a produced letter** (`A5`; the handoff carried
this as "existing, unobserved"). Not this defect:

```
{"arm": "A5", "run_cover_letter_md": "LLM COVER LETTER", "child_last_generated_cover_letter": "LLM COVER LETTER", "child_edited_cover_letter_text": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "run_edited_cover_letter_text": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "response_edited_cover_letter": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "resume_state_cover_letter_md": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "has_edits": true}
```

The context, the run row, the response and `resume_state` all agree on the typed text; the
newly produced letter sits underneath it. That is `resolve_cover_letter_after_generate`'s
documented `carry_edits` behaviour (`hardening.py`, "except under `carry_edits`, where the
frozen path keeps both edits as it always has"), consistent across surfaces. Whether keeping
the edit over a newly produced letter is the right product behaviour is an owner question, not
a 163-class disagreement, and is not decided here.

---

## Falsified

**F1. "My drive reached the stream route."** The first `--rA` run of `A1A2-stream` raised
`ControlFailed` (`child_last_generated_cover_letter` was still the first detached letter), not
the invariant. `tests/test_regenerate_cover_letter.py::_generate_stub` replaces only
`bgen.generate`; `/api/generate/stream` calls `generate_streaming`, which the rig stubs
separately and never with a letter. A bare `assert` would have xfailed that arm and read the
broken drive as the defect (the item-167 failure class). Fixed in this file's own
`_generate_stub`; the other file's helper is untouched. Its stream arms are resume-only (no
letter expected either way), so they stay valid; that is a reading of the code, not re-run
evidence.

---

## Inferred

**I1. Why the column survives.** Reading the code, not observed: `_clear_run_edits`
(`blueprints/generation.py`) nulls only `edited_resume_text`, and only on a frozen discard;
`_persist_cover_letter_to_db` writes only `generated_cover_letter_md` via
`persist_cover_letter_md`; nothing else writes `edited_cover_letter_text` except
`_persist_edited_text_to_db`, which treats `None` as "no change". So no code path ever sets the
column to `None`. O1-O3 are consistent with this and do not distinguish it from a write that
happens and is overwritten; a test that fails without the fix and passes with it is the
discriminating evidence.

---

## Falsification

The three arms O1-O3 are the experiment. Each must fail at its invariant line on `main`
(done, above) and pass after the change, with `C1`-`C3` and `A5` holding throughout:

- **If an arm still fails after the fix at the invariant line:** the mechanism in I1 is not
  the whole story; widen the instrument, do not stack a second fix.
- **If an arm fails with `ControlFailed` after the fix:** the fix disturbed a behaviour the
  controls pin (D4); that is a regression, not a remaining defect.

---

## The fix

_Not written yet. Commit 2 on this branch. Planned: the run row's letter edit is nulled
exactly when the context consumes it, derived from `resolve_cover_letter_after_generate` so the
two sides cannot disagree; and `_persist_cover_letter_to_db` nulls it in its existing session._

---

## Acceptance bar

- `tests/test_run_row_letter_edit.py`: the three `xfail` markers removed and nothing else;
  8 passed with `-p no:rerunfailures`, no `ControlFailed`.
- `C1`-`C3` and `A5` unchanged; `tests/test_regenerate_cover_letter.py`,
  `tests/test_regenerate_persistence.py`, `tests/test_app_iteration.py` still pass.
- Mutation check: reverting the generate-route change alone fails A1/A2; reverting the
  `_persist_cover_letter_to_db` change alone fails A3.
- CI: `python -m scripts.ci_wait <n>` exits 0 (exit 3 means a test needed a retry: stop and
  look).
