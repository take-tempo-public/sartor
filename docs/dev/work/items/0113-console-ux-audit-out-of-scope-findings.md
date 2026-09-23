```toml
schema = 1
id = 113
kind = "item"
title = "Triage the 19 out-of-scope findings from the pre-Epic-C console UX audit (UX-23..UX-41)"
status = "deferred"
blocked_on = "owner triage after Epic C lands: which findings become items, which fold into a later epic, which are dropped"
decision_owner = "user"
branches = ["docs/epic-c-kickoff"]
refs = ["docs/dev/reviews/epic-c-console-ux-audit.md"]
summary = "19 console UX findings outside Epic C's scope (7 major, 12 minor) await owner triage; UX-22 filed separately (item 112)."
```

The audit's "Findings — out of scope" section is the single home of the evidence. Every
row carries a `path:line` and quoted code, verified at `a078ca1`. I spot-checked the in-scope cites
against HEAD. I did not re-verify these out-of-scope rows individually; do that at
triage. Majors: UX-23 (a reload loses the tab and the Tuning draft), UX-24 (a second
"only write surface" claim, the same falsehood C1 fixes at `:230`), UX-25 (no way to
discard a draft), UX-26 (Score grounding reload restores a stale draft; code trace, not
reproduced), UX-27 (spend estimates contradict each other), UX-28 (Tuning constant switch
keeps stale text into a paid A/B), and UX-29 (groundedness fixture not shown).

Deliberately **not** folded into Epic C (C-10/scope discipline: sprint scope is quoted from
RELEASE_ARC, never derived). UX-24 is the one the audit suggests folding into C1. It is
the invoker's call to raise with the owner, not a silent expansion.
