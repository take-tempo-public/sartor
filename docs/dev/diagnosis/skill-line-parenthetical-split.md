# Diagnosis — skill names split mid-parenthetical into separate entries

> **Status:** root cause PROVEN — item 15's own filed mechanism (`suggest_skills`'s
> output parsing) is FALSIFIED; the real defect is a parenthesis-blind delimiter
> split present at three independent, unrelated sites.
> **Branch:** `fix/skill-line-parenthetical-split`

---

## Symptom

Item 15 (filed 2026-07-28, `docs/dev/work/items/0015-skill-suggestion-rendering-split.md`):
reviewing the `robert-bootstrap` annotation fixture, multiple suggested skills are
visibly broken mid-phrase — `Eval Framework Design (LLM-as-judge` / `rubric-based)`,
`Retrieval Systems (hybrid search` / `reciprocal-rank fusion)`, `Cross-Functional
Leadership (Engineering` / `Design` / `QA)`, `Roadmap & KPI Ownership (NPS` /
`engagement` / `retention)`. The filing guesses: "Reads like a naive comma-split
somewhere in `suggest_skills`'s output parsing not accounting for commas inside
parentheticals. Not yet traced to the exact call site."

---

## Observed

**O-1. `suggest_skills`'s post-LLM transformation is exactly `.strip()` — no split
of any kind.** Read in full, `analyzer.py:3941-3957`:

```python
existing_lower = {s.strip().lower() for s in existing_list}
for p in result.get("proposals") or []:
    if not isinstance(p, dict):
        continue
    name = (p.get("name") or "").strip()
    key = name.lower()
    if not name or key in existing_lower or key in seen:
        continue
    seen.add(key)
    p["name"] = name
```

`suggest_skills_from_corpus` (`analyzer.py:4042-4058`) is byte-identical. The
response model `SuggestSkillsResponse` (`analyzer.py:312-315`) is a bare
`proposals: Any` with no validator — the only `model_validator` in `analyzer.py`
is on `ClarifyResponse` (`:240`). `_parse_or_retry` only does JSON/fence parsing
(`analyzer.py:2864-2866`). Both consuming routes
(`blueprints/applications.py:3140`, `blueprints/corpus/skills.py:334`) also only
`.strip()`. **This function structurally cannot produce a comma-split.**

**O-2. `evals/bootstrap.py:_split_skill_line` (line 204) reproduces all four of
item 15's cited examples byte-for-byte**, driven through the real public entry
point `_extract_skills`:

```
>>> from evals.bootstrap import _extract_skills
>>> md = """## Skills

Eval Framework Design (LLM-as-judge, rubric-based), Retrieval Systems (hybrid search, reciprocal-rank fusion), Cross-Functional Leadership (Engineering, Design, QA), Roadmap & KPI Ownership (NPS, engagement, retention)
"""
>>> _extract_skills(md)
['Eval Framework Design (LLM-as-judge', 'rubric-based)',
 'Retrieval Systems (hybrid search', 'reciprocal-rank fusion)',
 'Cross-Functional Leadership (Engineering', 'Design', 'QA)',
 'Roadmap & KPI Ownership (NPS', 'engagement', 'retention)']
```

The mechanism: `_split_skill_line` (`evals/bootstrap.py:185-204`) ends with
`re.split(r"[,;|·•]", line)` — a plain character-class split with no awareness
of enclosing parentheses. `_extract_skills` calls it once per content line under
a `## Skills` heading (`:207-232`, call site at `:456`:
`"skills": _extract_skills(resume_md)`); those tokens flow into
`dedup_texts` clusters (`:260-262`) and then into the annotation template
(`evals/annotation.py:488-493` `_skill_item_template`) — the exact fixture item
15 was reviewing when it observed the symptom. `evals/annotation.py:564,581-587`
then promotes `keep`-verdict skill-cluster representatives into
`expected.json`'s `must_keywords`, so the breakage propagates into eval
expectations too.

**O-3. The identical parenthesis-blind pattern independently reproduces on the
user-facing document-rendering path**, `json_resume.py:_parse_skills` (both
shapes), executed directly:

```
>>> from json_resume import md_to_json_resume
>>> md = "# X\n\n## Skills\n\nEval Framework Design (LLM-as-judge, rubric-based), Retrieval Systems (hybrid search, reciprocal-rank fusion)\n"
>>> md_to_json_resume(md)["skills"]
[{'name': 'Eval Framework Design (LLM-as-judge'}, {'name': 'rubric-based)'},
 {'name': 'Retrieval Systems (hybrid search'}, {'name': 'reciprocal-rank fusion)'}]
```

Grouped-bullet shape (`json_resume.py:500`, feeding `keywords`) breaks the same
way:

```
>>> md = "# X\n\n## Skills\n\n- Languages: Python (3.11, 3.12), Go\n"
>>> md_to_json_resume(md)["skills"]
[{'name': 'Languages', 'keywords': ['Python (3.11', '3.12)', 'Go']}]
```

`md_to_json_resume` is on the path a real user's preview/PDF/DOCX renders
through (`generator.py:145`, `blueprints/generation.py:387,721`,
`blueprints/templates.py:1339`, `hardening.py:1974`) — this is not confined to
the eval/annotation surface.

**O-4. The same class of bug independently reproduces on the Settings
save round trip**, `static/app.js:611` (and its sibling `:612` for
certifications), executed under node against the literal production
expression:

```
> const skills = ['Eval Framework Design (LLM-as-judge, rubric-based)', 'Go'];
> const textarea = skills.join(', ');                                          // app.js:559, populates #cfgSkills
> const saved = textarea.split(',').map(s => s.trim()).filter(Boolean);        // app.js:611, saveConfig()
> textarea
'Eval Framework Design (LLM-as-judge, rubric-based), Go'
> saved
[ 'Eval Framework Design (LLM-as-judge', 'rubric-based)', 'Go' ]
```

This one is not fixture-only: it silently corrupts a real candidate's persisted
`skills` config on every Settings save, whether or not the field was touched,
whenever an existing skill name contains an internal comma.

**O-5. `evals/runner.py` does not import `evals.bootstrap` or
`json_resume.md_to_json_resume`**, and none of the three synthetic eval
fixtures (`evals/fixtures/synthetic/{data-scientist-junior,pm-senior,sre-mid-level}`)
contains a parenthetical skill (`grep` for `(` inside skill fields: zero hits).
`baseline_v1.json` cannot be perturbed by this fix.

**O-6. Current test baseline before any change:**
`pytest tests/test_bootstrap.py tests/test_json_resume.py -q` → **80 passed**.

---

## Falsified

**F-1. Item 15's own filed mechanism — "a naive comma-split somewhere in
`suggest_skills`'s output parsing."** Killed by O-1: the function's entire
post-LLM transformation is `.strip()`. There is no split, retry-parse fence
logic, or validator anywhere in that call's path that could produce a
mid-parenthetical break. The item was reviewing the `robert-bootstrap`
fixture's *annotated skills*, which are `_extract_skills` output
(O-2's cluster→annotation-template chain), not `suggest_skills` output — the
filing conflated the two skill-producing pipelines.

---

## Inferred

None needed — root cause is proven by direct execution (O-2, O-3, O-4), not
inferred from reading code.

---

## Falsification

Already run in place of a separate pre-fix experiment, since the defect is
deterministic and directly executable (O-1 through O-4 above ARE the
falsification runs): item 15's stated mechanism fails to reproduce anything
(O-1 shows it cannot), while the real mechanism reproduces the exact cited
strings byte-for-byte at O-2, and the same parenthesis-blind pattern
independently reproduces at O-3 and O-4. All three will be pinned as
regression tests (RED before fix, GREEN after) in `tests/test_bootstrap.py`,
`tests/test_json_resume.py`, and a new UX flow test for the Settings round
trip, per the branch plan.

---

## The fix

A shared depth-aware split primitive (`json_resume.split_outside_brackets`,
a stdlib-only leaf module) used at all three sites, each keeping its own
existing delimiter regex so current delimiter semantics are unchanged — only
the "ignore delimiters nested inside `()`/`[]`" behavior is added. JS gets a
small mirrored helper (`_splitOutsideBrackets`) since it can't share the
Python code. Full design in the approved plan
(`C:\Users\iam\.claude\plans\polymorphic-waddling-cookie.md`).

---

## Acceptance bar

- All four of item 15's cited examples parse as one skill each through
  `_extract_skills`.
- All 10 currently-pinned `TestExtractSkills` cases stay green, unmodified,
  including the deliberate anti-over-strip case (`**Kubernetes**, Go` →
  `["**Kubernetes**", "Go"]`).
- New RED-then-GREEN regression tests exist for all three sites (bootstrap,
  json_resume ×2 shapes, Settings JS round trip), not just the one item 15
  literally observed.
- Full `python -m scripts.gate` green — no reruns needed for the new tests.
- `must_keywords` derived from a parenthetical skill in a future bootstrap run
  is the whole phrase, not a fragment.
