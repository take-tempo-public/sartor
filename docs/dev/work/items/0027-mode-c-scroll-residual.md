```toml
schema = 1
id = 27
kind = "item"
title = "Mode C scroll residual: wizard smooth-scroll races refreshCorpus's baseline capture"
status = "open"
decision_owner = "agent"
epic = 19
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
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
