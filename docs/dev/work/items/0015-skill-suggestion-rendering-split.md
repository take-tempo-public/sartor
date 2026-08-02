```toml
schema = 1
id = 15
kind = "item"
title = "Suggested skills split mid-parenthetical into separate entries"
status = "closed"
resolution = "Fixed on fix/skill-line-parenthetical-split. This item's own filed mechanism (a comma-split in suggest_skills' output parsing) was FALSE -- that function's entire post-LLM transformation is .strip(), no split of any kind (analyzer.py:3941-3957 / suggest_skills_from_corpus :4042-4058, both read in full). The real defect is evals/bootstrap.py:_split_skill_line (re.split on a bracket-blind character class), reproduced byte-for-byte against all four of this item's own cited examples via the real _extract_skills entry point. Widened during diagnosis: the identical bracket-blind pattern independently reproduced at two more, unrelated sites -- json_resume.py:_parse_skills (both shapes; the user-facing preview/PDF/DOCX rendering path) and static/app.js:611 (the Settings skills/certifications save round trip, which silently corrupts persisted corpus data on every save whenever an existing entry has an internal comma). Fixed all three with one shared depth-aware split primitive, json_resume.split_outside_brackets (Python) plus a mirrored _splitOutsideBrackets (JS, can't share code across the language boundary) -- each call site keeps its own existing delimiter regex/semantics, only delimiters nested inside ()/[] are now ignored. All 10 pre-existing TestExtractSkills cases (evals/bootstrap.py) pass unmodified, including the deliberate anti-over-strip case. RED-then-GREEN regression tests added at all three sites, including a UX flow test -- the first test-writing attempt for the Settings round trip asserted against the re-rendered textarea text and passed even against the UNFIXED code, because join(', ') on the corrupted 3-entry array reconstructs the identical display string; the corrected test reads the real persisted array via the config GET route instead, which does fail pre-fix. No eval re-baselining needed: evals/runner.py imports neither of the two Python call sites, and none of the three synthetic fixtures contains a parenthetical skill."
decision_owner = "agent"
refs = [
  "evals/bootstrap.py:_split_skill_line",
  "json_resume.py:_parse_skills",
  "json_resume.py:split_outside_brackets",
  "static/app.js:_splitOutsideBrackets",
  "docs/dev/diagnosis/skill-line-parenthetical-split.md",
]
summary = "e.g. 'Eval Framework Design (LLM-as-judge' and 'rubric-based)' saved as two separate skill entries - a comma-split bug."
```

Found 2026-07-28 reviewing the `robert-bootstrap` fixture's annotated
skills. Multiple suggested skills are visibly broken mid-phrase: `Eval
Framework Design (LLM-as-judge` / `rubric-based)`, `Retrieval Systems
(hybrid search` / `reciprocal-rank fusion)`, `Cross-Functional Leadership
(Engineering` / `Design` / `QA)`, `Roadmap & KPI Ownership (NPS` /
`engagement` / `retention)`. Reads like a naive comma-split somewhere in
`suggest_skills`'s output parsing not accounting for commas inside
parentheticals. Not yet traced to the exact call site.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking

### 2026-08-02 — fixed and closed (`fix/skill-line-parenthetical-split`)

Corrected this item's own filing: the mechanism was never `suggest_skills`
(that function only `.strip()`s each proposed name — no split exists in its
path). The real, capability-proven mechanism is a bracket-blind delimiter
split in `evals/bootstrap.py:_split_skill_line`, reproduced byte-for-byte
against this item's own four cited examples. Diagnosing that also surfaced
the identical bug at two further, unrelated sites — `json_resume.py`'s
skills parser (the user-facing document-rendering path) and the Settings
save round trip in `static/app.js` (silent corpus-data corruption on save) —
both fixed in the same branch. Full evidence chain, falsification of the
original attribution, and acceptance bar:
`docs/dev/diagnosis/skill-line-parenthetical-split.md`.
