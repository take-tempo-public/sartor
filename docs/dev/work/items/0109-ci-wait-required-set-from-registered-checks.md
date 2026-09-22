```toml
schema = 1
id = 109
kind = "item"
title = "scripts/ci_wait.py returned GREEN (exit 0) while 4 of 6 branch-protection-required checks were still pending -- it derives 'required' from the checks registered when the watch starts"
status = "open"
decision_owner = "agent"
refs = [
  "scripts/ci_wait.py",
]
summary = "ci_wait said GREEN with lint/test + UX pending: required = checks registered at watch start, not protection."
```

**Observed (2026-09-22, PR #135, head `865f714`).** `python -m scripts.ci_wait 135`
exited **0** (`ci-wait: GREEN (exit 0)`). Its own final report listed only the four
`Analyze (…)` jobs as required, and placed `Lint, type-check, test (py3.11/3.12/3.13)`
and `UX / a11y / PDF (Playwright, py3.12)` under "advisory (reported, never gating)"
as **pending**. Branch protection on `main` at the same moment
(`gh api repos/take-tempo-public/sartor/branches/main/protection/required_status_checks`)
requires all six contexts: the three lint/test jobs, the UX job, and both `Analyze`
jobs, with `strict: true`.

**Mechanism (observed, not inferred).** The log shows `gh pr checks 135 --watch
--required` listing **only** the four `Analyze` jobs on every refresh. The CI
workflow's jobs had not registered on the PR yet when the watch started (they began
minutes later, after `gh pr update-branch`). `--watch` exited as soon as the checks it
could see passed. A minute later, `gh pr checks 135 --required` listed all six, the
four non-Analyze ones pending. So "required" is whatever is registered at watch start,
not the protection rule's context list.

**Why this is the worst failure shape for this tool.** `ci_wait.py` is the single
sanctioned definition of "the PR is green" (AGENTS.md close-out step 4). A false exit
0 is exactly what a merge is gated on. It fires most easily right after
`gh pr update-branch` or a push, which is the normal close-out path, and it would have
merged PR #135 with the two previously-red required checks never run. It was caught
only because the verdict was read against branch protection by hand.

**Fail-closed direction (C-11), not built yet:** read the required contexts from
branch protection (`…/protection/required_status_checks`). Refuse any verdict other
than "not yet green" while a required context is missing from the check list or is
pending. Treat an unreadable protection rule as unknown, never green. Related: item 79
(delivery faults); this item is a *verdict* fault, which is more serious.

**Workaround used:** `ci_wait` re-run once all six contexts were registered.
