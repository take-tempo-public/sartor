```toml
schema = 1
id = 178
kind = "item"
title = "The wiki cite check passes a line cite whose content moved: it checks only that the line exists"
status = "watching"
decision_owner = "agent"
branches = ["chore/wiki-checkpoint-pass"]
refs = [
  "scripts/wiki_cites.py",
  "docs/wiki/log.md",
  "docs/dev/work/items/0065-wiki-freshness-counter-measures-the-wrong-thing.md",
  "docs/dev/work/items/0168-measure-sonnet-wiki-auditor-against-haiku.md",
]
summary = "wiki_cites passed 4 line cites that no longer pointed at their claim; 17 bare line cites remain allowed."
```

**Observed (2026-10-19, `chore/wiki-checkpoint-pass`).** `python -m scripts.wiki_cites` read clean before the
checkpoint pass. Reading the seven line cites into files the window had changed, by hand, found four that no longer
pointed at their claim: `web_infra/openapi.py:138` (`needs_month` had moved to :143) and
`corpus_to_json_resume.py:914-915`, `:916-917`, `:920-922` (now inside `_collect_education`'s docstring), plus a prose
"lines 939–941". The check's E2 rule asks only that a line cite not run past the end of its file, so a cite that
still exists but points at other text passes. Two further drifted cites turned up in the auditors' reports
(`json_resume.py` "lines 389–394", `b1-education-render.md` "lines 357–360"); the check could not have caught those either.

**Why it is a mechanism gap, not a note (charter C-11).** This is a recurrence: item 166 introduced the ratchet
because line cites rot, and the ratchet only stops *new* ones. 17 bare line cites are still allowed
(`ALLOWED_LINE_CITES`: `diagnostics-console` 2, `document-rendering` 3, `education-degree-field-rendering` 8,
`governance-extraction` 2, `route-surface` 2), and each can rot silently.

**What a mechanism could be (none evaluated, none built):**

1. Drive `ALLOWED_LINE_CITES` to zero by converting the remaining 17 to symbol cites, then make a line cite an
   error with no allowance.
2. A content check for a line cite that sits beside a named symbol (`path:symbol (lines a-b)`): the symbol must
   appear within `a-b`.
3. Leave it and accept the 17, stating that the gate does not check what a line cite points at.

**Known limit of this record:** the four were found by reading, not by instrument. How many of the 17 have already
drifted is not measured.

## Updates

### 2026-10-19 — filed on `chore/wiki-checkpoint-pass`

Filed at close-out so the gap is on the board and not only in the `log.md` entry. The four drifted cites named above
were re-anchored to symbols on that branch; the 17 remaining were not touched.
