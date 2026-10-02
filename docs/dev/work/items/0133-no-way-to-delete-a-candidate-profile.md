```toml
schema = 1
id = 133
kind = "item"
title = "There is no way to delete a candidate profile"
status = "open"
decision_owner = "user"
branches = ["feat/user-docs"]
refs = ["blueprints/users.py", "templates/index.html:102-168"]
summary = "No route, UI or script removes a user. Product decision: wanted, and when?"
```

**Observed in code (2026-09-29).** `blueprints/users.py` defines list, create, config, fetch and
roster routes only. The User selection panel offers **New user** and nothing else
(`templates/index.html:102-168`). The only removal in the product is retiring an
*application*.

**Why the owner decides.** Deleting a profile removes corpus rows, `configs/`, `resumes/` and
`output/` data. That's a destructive, user-visible behavior (failure pattern 5c), not a doc
fix. `docs/user/coaching.md` states the gap plainly and links here.

## Updates

### 2026-09-29 — filed on `feat/user-docs` (Epic D D3)
