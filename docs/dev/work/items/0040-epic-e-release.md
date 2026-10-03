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

### 2026-10-02 — owner sequence for the cut (`chore/release-v1.1.0`)

Owner direction, 2026-10-02. Briefly considered relabeling as "1.0", then withdrawn.

1. **The public version stays 1.1.0.** The never-published local `v1.0.x` tags remain history.
2. **Before staging,** draw the board's Open items down, to 0 if possible (36 at this date).
3. **Stage a 1.1.0 alpha.** The owner then runs an end-to-end test on a fresh clone, for the
   last installation and documentation gaps.
4. **Public 1.1.0** comes only after the owner approves that alpha.

**E1's pre-flight ran on `chore/release-v1.1.0`, and the cut is paused.** Item 19 cannot close
on current evidence (see item 30's 2026-10-02 update).
