```toml
schema = 1
id = 91
kind = "item"
title = "spacious.html does not render education[].score while classic.html does"
status = "watching"
decision_owner = "user"
branches = ["fix/b1-education-render"]
refs = [
  "personas/bundled/spacious.html",
  "personas/bundled/classic.html",
  "docs/dev/blast-radius/b1-education-render.md",
]
summary = "Inconsistent GPA rendering between two bundled personas; no record of whether Spacious omits it deliberately."
```

**Origin.** Observed by B1b's implementer while enumerating the education
render surfaces (blast-radius dossier `## Deferred`, first bullet), handed
to the closer for filing, filed by the invoking session at the sprint gate
(closer's `itemsFiled` was empty — recorded in item 84's run evidence).

**The gap.** `classic.html` renders `education[].score` (GPA);
`spacious.html` omits it. A different field with a different judgment behind
it than B1b's `studyType` work — Spacious may omit GPA deliberately (its
design is airier) or by the same drift that dropped `studyType` from two
personas. Nothing in the repo says which, so `decision_owner = "user"`:
decide intent first, then either render it or record the omission as a
design choice in the persona's own comments.

## Updates

### 2026-08-13 — filed during `fix/b1-education-render` (B1b) by the invoking session
