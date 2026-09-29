```toml
schema = 1
id = 130
kind = "item"
title = "Profile edits (Notes, identity fields) likely never reach the AI after the candidate row exists"
status = "open"
decision_owner = "agent"
branches = ["feat/user-docs"]
refs = [
  "onboarding/corpus_import.py:175-196",
  "web_infra/provisioning.py:35-47",
  "db/build_context.py:205-220",
  "blueprints/users.py:183-194",
  "analyzer.py:661",
]
summary = "Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty."
```

**Status of the evidence: code-read, NOT observed live.** Treat the mechanism below as a
hypothesis (charter C-7) until a reproduction shows it. The first commit on a fix branch is
that reproduction.

**What the code shows.**
- **Save path.** "Save config" (Settings drawer → Profile) writes only
  `configs/<user>.config` (`blueprints/users.py:183-194`).
- **Read path.** Analyze and generate build the prompt's `<candidate_profile>` from the DB row:
  `"notes": candidate.notes` (`db/build_context.py:214`).
- **The one sync.** The config is copied into `Candidate` once, when the row is created, and
  afterwards only into fields that are still empty: "Fill empty fields only — never overwrite
  real data on re-import" (`onboarding/corpus_import.py:193-196`). Row provisioning calls this
  only when the row is missing (`web_infra/provisioning.py:41-46`).
- **Negative result.** `git grep -n "\.notes\s*=" -- '*.py'` finds no other writer of
  `Candidate.notes`. The three hits are `Application`, `Education` and `Title` rows.

**Consequence (if confirmed).** Once a user has onboarded, editing **Notes** has no effect on
AI output. Notes is the field `analyzer.py:661` tells the model to treat as explicit
candidate directives. Name, email, phone, LinkedIn and website likely behave the same.

**Why it matters for docs.** RELEASE_ARC's D3 bullet asks for the Notes directive field to be
documented. The owner held that documentation on `feat/user-docs` (2026-09-29) until this is
verified or fixed, so the user docs don't describe a control that may do nothing.

## Updates

### 2026-09-29 — filed on `feat/user-docs` (Epic D D3), found while exploring the Settings copy
