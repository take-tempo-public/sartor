```toml
schema = 1
id = 90
kind = "item"
title = "Institution-less/name-less markdown emitter ambiguity misroutes fields on round-trip (work, education, projects alike)"
status = "watching"
decision_owner = "agent"
branches = ["fix/b1-education-render"]
refs = [
  "json_resume.py",
  "docs/dev/diagnosis/b1-education-render.md",
]
summary = "A first-field-less entry emits ambiguous markdown that misroutes on re-parse; the fix spans three entry kinds."
```

**Origin.** B1b's Sonnet refuter raised this as finding F1 (HIGH) with an
executed reproduction; the judge CONFIRMED the mechanism but reattributed and
narrowed it — **not a regression** (pre-fix the same shape already misrouted
`area` into `institution` and dropped `studyType`; post-fix output is a
strict superset), and ordered it **filed, not fixed** ("fixing that grammar
hole across all three kinds WOULD be a scope change... fixing it for
education alone would be an inconsistent partial fix"). The flag_stop this
finding raised was the escalation primitive's **first live firing** (run
`wf_008f60f1-129`, 2026-08-13); the independent reviewer ruled
`targeted_fix` on the same not-a-regression grounds. Full trail:
`docs/dev/diagnosis/b1-education-render.md` §"Known limits (C-0)".

**The gap.** `json_resume_to_markdown` emits `f"{a}, {b}" if (a and b) else
(a or b)` for the h3 left segment (work `name`/`position`, education
`institution`/`area — studyType`, projects likewise). When the first field
is absent, the emitted segment carries no `", "` boundary, so
`_split_h3_header`'s `" — "` fallback (which exists for work entries and
predates B1b) consumes the remaining value as a name/position boundary:
`{area, studyType}` with no institution re-parses to
`{institution: <area>, area: <studyType>}`; a `work` entry with `position`
and no `name` re-parses to `{name: <position>}` — same misrouting, in code
B1b never touched.

**Reachability is narrow** (judge-verified): the corpus UI 400s on empty
institution (`blueprints/corpus/career_assets.py:104-106,168-172`),
`db/models.py` has `nullable=False`, and `corpus_to_json_resume.py` guards
`if ed.institution:` — but that guard *omits* the key for a falsy
institution, and `evals/seed_import.py` passes `institution` through
unvalidated, so a doc reaching the emitter can carry the shape.

**Scope for the eventual fix.** Decide ONE grammar for the h3 left segment
that is unambiguous with any subset of fields present, and apply it to all
three entry kinds together — never education alone. `_split_h3_header`'s
`" — "` work-entry affordance is load-bearing (`Harvard — MBA` free-typed
markdown must keep parsing; `test_em_dash_position_separator` pins it), so
any change is C-10 territory: the B1b blast-radius dossier's Consumer #11
decision (leave the shared helper alone) stands until deliberately reopened.
The institution-less education behavior is pinned as-is by
`test_institution_less_entry_re_keys_studytype_into_area_on_emit` — that
pin documents current behavior and must be updated by whichever branch
fixes the grammar.

## Updates

### 2026-08-13 — filed during `fix/b1-education-render` (B1b) by the invoking session

Filed by the invoker at the sprint gate: the judge's F1 verdict ordered the
closer to file this and the closer's report shows `itemsFiled: []` — the
divergence is recorded in item 84's run evidence. Content sourced from the
verdict rationale and the dossier's Known-limits section, both written this
sprint.
