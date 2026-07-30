```toml
schema = 1
id = 27
kind = "item"
title = "Mode C scroll residual: wizard smooth-scroll races refreshCorpus's baseline capture"
status = "closed"
decision_owner = "agent"
epic = 19
resolution = "Already fixed before this item was ever filed. fix/ux-scroll-wizard-rail-flake round 7 (commit 27d349b, merged 90e495d, 2026-07-26) falsified the wizard-rail attribution entirely (F-7) and root-caused the SAME test/signature to Chromium scroll-anchoring on refreshMergeSuggestions()'s async growth, fixed via document-level overflow-anchor:none (static/style.css:122). Confirmed still present and effective: 20/20 clean runs (0 failed, 0 reruns) on fix/ux-mode-c-scroll-residual, 2026-07-30, at the identical 6-loader/8-core calibration that produced 6/20 (30%) failures on the unfixed control in round 7's own A/B (scratchpad/capture_scroll_verify_20260730.log)."
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md",
]
summary = "Mode C residual (~17%/attempt): _wizardRender smooth-scroll races refreshCorpus's scroll baseline read."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 1 of that epic's original 5, and the oldest, best-understood
one.

`_wizardRender`'s smooth-scroll animation races `refreshCorpus`'s scroll-position baseline read,
independent of the `_captureScrollY`/`_restoreScrollY` primitive the O-10/O-11 fix patches — see
`docs/dev/diagnosis/ux-scroll-position-flake.md`'s Inferred §3 ("Mode C is confirmed structurally
independent... it doesn't involve `refreshCorpus`'s capture/restore at either end") and its
Acceptance-bar section ("mode C's measured rate here (4/24, ~17%) is not negligible... worth a
deliberate, separate pickup"). Explicitly scoped OUT of that fix, not fixed by it. No dedicated
diagnosis dossier exists yet for this candidate specifically — the fix's own diagnosis doc carries
the only evidence so far, gathered incidentally rather than through a campaign aimed at this mode.

## Updates

### 2026-07-29 — filed, split from epic 19

### 2026-07-30 — closed as already-resolved, on fix/ux-mode-c-scroll-residual

Before starting the C-7 evidence campaign this item calls for, checked whether the mechanism
this item names had already been investigated elsewhere. It had: `docs/dev/diagnosis/
ux-scroll-wizard-rail-flake.md` (a SEPARATE branch, `fix/ux-scroll-wizard-rail-flake`, seven
rounds, 2026-07-16 through 2026-07-26) is a dedicated follow-on to the exact same `~17%
(4/24)` residual this item's own summary describes, on the same test
(`test_corpus_reload_preserves_scroll_position`) and the same `dy≈dh` signature family. That
investigation **falsified** this item's own framing outright (F-7: "the wizard rail is not
involved in mode C at all") and found the real mechanism (Chromium scroll-anchoring on
`refreshMergeSuggestions()`'s fire-and-forget growth), fixing it with `overflow-anchor: none`
at the document/`body` scope. That fix merged to `main` (`27d349b`/`90e495d`) on **2026-07-26**
— three days before this item was filed (2026-07-28) and four days before the epic split
that produced this file (2026-07-29). Neither filing cross-referenced the wizard-rail-flake
dossier or its RESOLVED carry-forward-ledger entry (ledger item 2, closed in that round's own
handoff, `docs/dev/handoffs/fix-ux-scroll-wizard-rail-flake-round7.md`) — this item re-surfaced
an already-closed defect from the older, superseded `ux-scroll-position-flake.md` framing alone.

Verified live rather than closing on the paper trail alone: `static/style.css:122` carries the
fix on current `main`; the two wizard-render instrument tests are `xfail(strict=False)` citing
F-7/O-15 by name; and a fresh 20-run campaign at the original round-7 calibration (6 busy-loop
workers / 8 logical cores, `scratchpad/capture_scroll_phase1b.sh 6 20`) produced **20/20 passed,
0 failed, 0 reruns** — `scratchpad/capture_scroll_verify_20260730.log`.

**Process note, not this item's own defect:** the stale re-filing is itself worth tracking —
epic/item filings that cite a diagnosis doc should check for a newer, superseding dossier on
the same symptom before treating it as open. No action taken on that beyond this note; flagged
to the owner in this branch's close-out.
