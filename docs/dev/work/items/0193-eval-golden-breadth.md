```toml
schema = 1
id = 193
kind = "item"
title = "Eval redesign step 3b-i: golden-set breadth (per-family ladders, setting, certifications, mismatched pairs)"
status = "open"
depends_on = [183]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-golden-breadth"]
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-golden-breadth.md"]
summary = "Step 3b-i, no paid call: format changes so the golden set spans many fields, settings and mismatched pairs (3b-ii: 191)."
```

Step 3b of the eval redesign build order, first half (split by the owner's direction on 2026-10-27; 3b-ii is item 191). Scope and the reasons are in `docs/dev/blast-radius/eval-golden-breadth.md` and the design doc's 6.4; this item points, it does not restate.

## Updates

### 2026-10-27 -- filed and started on feat/eval-golden-breadth

The owner reviewed the matrix against the real need: the golden set exists to measure prompt and model performance across many job fields (administrative assistants, designers and product designers, mobile and hardware engineers, electricians, construction project managers, healthcare, support services, trades), across startups, enterprises and small employers, with a small public-sector share, and across **mismatched résumé/JD pairs** for career changers and career advancers.

Owner answers (chat, plan mode, 2026-10-27): the 24-profession list in four groups is about right; the government register is about 5% of fixtures; mismatched pairs are wanted; the **no-fetch route is recorded** (design doc 6.5; no USAJOBS fetch, no key, charter C-2 and D-6 untouched).

Found by reading the 3a format (not yet run): the level ladder is one global tuple of tech-flavoured scopes; the employer pool, JD header (`— Remote (US)`) and JD shape are tech-startup shaped; there is no certifications section although the corpus already has one; and tenure is drawn from a fixed 18 to 41 month window that ignores the ladder's `years`. This branch changes the format only: per-family ladders, a setting axis, certifications and training-aware education, and pairs derived from existing cells with no new prose. The facts for the new professions and the paid generation stay in item 191.
