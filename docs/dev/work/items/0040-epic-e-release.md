```toml
schema = 1
id = 40
kind = "epic"
title = "Final March epic E - the public v1.1.0 cut"
status = "blocked"
decision_owner = "user"
blocked_on = "sequenced after epic D; the tag itself is the owner's act (item 10) and the [HUMAN] toggles (item 3) execute during this epic"
depends_on = [39]
branches = ["epic/e-release"]
refs = ["docs/dev/RELEASE_ARC.md"]
summary = "Version bump, CHANGELOG cut, pre-tag gates, tag; PyPI publish + GitHub Release; owner toggles during the epic."
```

Final March epic E. Briefs in `RELEASE_ARC.md` §"v1.1.0 Final March" (E1). Child:
item 10 (the release cut, which carries the full `depends_on` chain to items
3/6/7/9/19).

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff
