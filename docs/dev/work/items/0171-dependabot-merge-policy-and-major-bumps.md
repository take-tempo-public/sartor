```toml
schema = 1
id = 171
kind = "item"
title = "Dependabot PRs pile up unmerged: design a merge policy per update class, majors included"
status = "open"
decision_owner = "user"
branches = ["chore/dependabot-triage-item"]
refs = [
  ".github/dependabot.yml",
  ".github/workflows/ci.yml",
  ".github/workflows/release.yml",
  ".github/workflows/docker.yml",
  ".github/workflows/capture-smoke.yml",
  ".github/workflows/docs-deploy.yml",
  "pyproject.toml:113",
  "docs/dev/maintainer-lane.md",
  "docs/dev/work/items/0003-*.md",
  "docs/dev/work/items/0010-*.md",
  "docs/dev/work/items/0099-*.md",
  "docs/dev/work/items/0051-*.md",
]
summary = "16 Dependabot PRs open, oldest 2026-07-13; nothing acts on green ones. Design the per-class merge policy."
```

**Asked by the owner, 2026-10-16**, after a read-only board review. The owner asked for an item
that carries the recommendation and a design for the different cases, major bumps included.
**This item is a design, not a build.** Nothing below is implemented; the owner decides the
four questions under "Owner decisions" before any workflow is written.

## What was observed (2026-10-16, `main` at `f01d29e`)

- `gh pr list --state open --author app/dependabot`: **16 open PRs**. Created 2026-07-13 (#10),
  07-22 (#51, #54), 08-06 (#106), 08-07 (#109), 08-13 (#127), 09-03 (#132), 09-08 (#137),
  09-24 (#146, #147), 10-02 (#151, #152), 10-16 (#175, #176, #177). Five are over five weeks old.
- By ecosystem: github-actions #10, #51, #54, #109, #147; pip #106, #127; npm `/docs-site` #132,
  #137, #146, #151, #152, #175, #176, #177.
- `ci.yml`, `codeql.yml`, `chain-verify.yml` and `docs-deploy.yml` run on `pull_request`, so every
  Dependabot PR already gets the checks. **Nothing acts on the result**: no auto-merge, no rebase
  request, no age report.
- Branch protection on `main`: six required checks, `strict: true`, `enforce_admins: false`, zero
  required reviews. Repo settings: `allow_auto_merge: true`, merge commit only (squash and rebase
  off), `delete_branch_on_merge: true`.
- Sampled check states: #175, #176 and #177 (opened 2026-10-16) pass every check; #127 fails the
  three `Lint, type-check, test` jobs and is `BEHIND`.
- `gh api repos/.../dependabot/alerts`: **23 open alerts** (count only, not triaged). The
  2026-08-07 owner direction on the six docs-site alerts is in the agent memory
  `project-dependabot-docs-site-alerts`.

### Two findings that change the design

1. **A green PR is not evidence for the workflows that matter most.** `release.yml` and
   `docker.yml` trigger only on a `v*` tag push or `workflow_dispatch`; `capture-smoke.yml` runs
   monthly or on dispatch. `gh run list --workflow release.yml` and `--workflow docker.yml` each
   return **no runs, ever**. So an action bump in those files cannot fail on the PR, and the
   first execution of the bumped pin would be the real tag push. Per `RELEASE_CHECKLIST.md` the
   v1.0.x tags are local-only, and nothing has been published (item 99), so that tag push is also
   the first time those workflows run at all. Actions in those files: `actions/upload-artifact`
   (`release.yml:79`, `capture-smoke.yml:101`, `docs-deploy.yml:123`), `actions/download-artifact`
   (`release.yml:93`), `actions/cache` (`ci.yml:203`, `capture-smoke.yml:52`),
   `docker/setup-qemu-action` (`docker.yml:39`).
2. **`capture-smoke.yml` has failed on its last three scheduled runs** (2026-08-01, 09-01, 10-01;
   latest run `36858103525`). The cause was **not examined** and no work item mentions it
   (grep of `docs/dev/work/` for `capture-smoke` finds nothing). Its log also carries a Node.js 20
   deprecation warning for `actions/cache`, which is itself a reason the action pins must keep
   moving. File as its own item once looked at; do not fold it into this one.

### Not yet observed (instrument first, C-7)

- **Why #127 (ruff 0.17.0) fails.** `pyproject.toml:113` exact-pins `ruff==0.15.22`, and the
  comment above it says bumping ruff is a deliberate one-commit action (upgrade, then
  `ruff format .`) because the whole-tree format check must match local. That makes "ruff changed
  the formatter or added findings" the likely cause, but it is a **hypothesis**: the failing log
  was not read. #106 (0.16.1) looks superseded by #127 (0.17.0), both from 0.15.22.
- **Whether `release.yml` is safe to `workflow_dispatch` as a dry run.** Its `publish` job uses
  `environment: pypi` and `pypa/gh-action-pypi-publish`; line 53 gates one step on
  `github.event_name == 'push'`, but whether the publish job itself runs on dispatch was not
  traced. `RELEASE_CHECKLIST.md` warns that an early tag push would fire PyPI/GHCR publish.
  Establish this before proposing any dispatch-based verification.
- **Whether Dependabot rebases `BEHIND` PRs on its own.** Believed to happen only on conflicts;
  not verified here.

## Recommendation

Add one small event-driven workflow that enables GitHub auto-merge on a Dependabot PR **only when
the PR is in a class the policy table marks auto**. Auto-merge waits for the six required checks,
so the safety comes from the existing gate and the workflow adds no new trust. Everything else
stays a human PR, but gets a **named lane and an age bound** so it cannot sit for 13 weeks unseen.

Design constraints for that workflow, all from this repo's existing rules:
- Trigger `pull_request`, never `pull_request_target`; job-level `if: github.actor == 'dependabot[bot]'`;
  `permissions` declared per job (`contents: write`, `pull-requests: write`) and nothing wider.
- Every `uses:` pinned to a full SHA with a `# vX.Y` trailing comment (OpenSSF Scorecard, item
  on `openssf-scorecard-hardening`); that includes `dependabot/fetch-metadata`.
- Merge method is `--merge`; squash and rebase are disabled on the repo.
- Event-driven only. No polling loop, no scheduled sweep that lists all PRs per run.

### Policy by case

| Case | Today's examples | Policy | Why |
|---|---|---|---|
| pip, grouped minor/patch, **excluding ruff** | none open now | **auto-merge** when required checks pass | runtime/test deps; the six checks (py3.11-3.13, UX, CodeQL x2) are real evidence |
| **ruff** (exact-pinned) | #106, #127 | **never auto**; its own deliberate branch: bump the pin, `ruff format .`, fix new findings, one commit | the pin exists so local and CI format identically; a bot cannot do the format step. Close #106 as superseded. Keep ruff out of the `pip-minor-patch` group so it stops riding in it. |
| github-actions, minor/patch, **diff touches only PR-path workflows** (`ci.yml`, `codeql.yml`, `chain-verify.yml`, `docs-deploy.yml`, `scorecard.yml`) | part of #147 | **auto-merge** | PR checks execute these files, so a green PR is real evidence |
| github-actions, any bump whose diff touches `release.yml`, `docker.yml` or `capture-smoke.yml` | #10, #51, #54, #109, part of #147 | **manual**, see "Release-path actions" | PR checks never run these files (finding 1) |
| **Major** of any ecosystem | #10, #51, #54, #109 | **manual, no exceptions** | Dependabot leaves majors out of every group on purpose; keep that |
| **0.x "minor"** | ruff 0.15 to 0.17, katex 0.16 to 0.18 (#176) | **treat as major** | semver permits breaking changes in a 0.x minor, and Dependabot labels it `minor`, so a rule keyed on update type alone would auto-merge it |
| npm `/docs-site`, minor/patch | #132, #137, #146, #151, #152, #175 | **owner decision** (Q2), default manual | owner carve-out of 2026-08-07; `docs-deploy.yml` also builds on every PR, so build breakage is covered, but a merge to `main` runs the publish path |
| npm ancestor/peer bumps (`next` 16.2 to 16.4, `mermaid`) | #176, #177 | **manual** | these bump a framework with a history of breaking the build (typescript detector, `docs/dev/diagnosis/docs-site-typescript-detection.md`) |
| **Security update** | the 23 open alerts | separate fast lane, **never auto-merged blind** | a security bump can itself be a major; human reads it, but it is first in the queue |
| PR failing a required check | #127 | **no automation**; surface it | a bot cannot tell a flake from a real break; item 51 and the flake-rate work own the flake side |
| PR `BEHIND` under `strict: true` | #127 | `gh pr update-branch` on **auto-eligible PRs only** | see "Cost under strict" |

### Release-path actions (the major-bump design)

The four majors (#10 download-artifact 4.3.0 to 8.0.1, #109 upload-artifact 4.6.2 to 7.0.1, #51
cache 4.3.0 to 6.1.0, #54 setup-qemu 3.7.0 to 4.2.0) share one risk: **no PR check exercises
them**. Proposed handling, in order:

1. **Bump upload and download together, in one branch.** `release.yml:79` uploads and `:93`
   downloads the same artifact; two independent Dependabot PRs can land at different majors.
   Whether mixed majors interoperate was **not verified**; read both changelogs before assuming.
2. **Read the release notes for removed inputs and runtime changes** (Node 20 to 24) and diff
   every `with:` block in our workflows against the new action's `action.yml`.
3. **Verify without publishing.** Only if the instrument above shows dispatch cannot publish:
   `workflow_dispatch` the bumped workflow and read the run. If it cannot be shown safe, verify
   by reading and leave the first real run to the tag, and say so in the PR (declare the gap,
   C-12).
4. **Timing: do this before the 1.1.0 tag, not after.** The tag push is the first execution of
   `release.yml` and `docker.yml`; leaving pins four majors behind makes that first run also the
   first run on a stack nobody checked.

### Cost under strict mode (efficiency, stated up front)

With `strict: true`, each merge makes every other open PR `BEHIND`, and `update-branch` re-runs
the full CI (the UX job has a ~5 minute baseline, 14m49s on one outlier, item 48). N eligible
PRs merged serially cost on the order of N squared check runs. Mitigations, cheapest first:
keep minor/patch grouped (already done, one PR per ecosystem per week); keep
`open-pull-requests-limit: 5`; update a branch only when it is the next one eligible to merge,
not all at once; and consider a merge queue, which is a **branch-protection change and the
owner's** (same lane as item 3). Do not build a loop that rebases everything.

### Make staleness a mechanism, not a note (C-11)

PRs sat 13 weeks because nothing fails when they do. A recurrence of "backlog nobody looks at"
needs a check that fails closed or reports from a derived source, not another ledger row.
Proposal: a derived age figure (oldest open Dependabot PR, from `gh pr list`) printed by the
close-out sweep or `scripts.ci_wait`-adjacent tooling, with a stated ceiling (suggest 14 days
for auto-eligible classes, 30 for manual) and a work item filed automatically by hand when
breached. Pattern to copy: item 51 (flake-rate budget `report --check`). Label it **unenforced**
until a script exists.

## Owner decisions (these block the build)

1. **Q1.** May a bot enable auto-merge into `main` for the auto classes? `maintainer-lane.md`
   close-out step 4 and the standing feedback say ask before any merge; those are written for agent
   branches. Extending the rule to bot PRs is a policy change that should be written down.
2. **Q2.** Does the 2026-08-07 carve-out (owner handles docs-site alerts personally) still stand,
   and does it cover version updates or only security alerts?
3. **Q3.** Is the pre-tag rule in "Release-path actions" 4 accepted: the four majors resolved, or
   consciously pinned with a recorded reason, before 1.1.0?
4. **Q4.** Merge queue: in scope, or accept the squared cost with the mitigations above?

## Done means (proposed)

- A committed policy (table above, as decided) and the workflow implementing the auto classes,
  with a test or a CI run id showing one auto-eligible PR merged and one manual-class PR left alone.
- The ruff bump landed on a deliberate branch, #106 closed as superseded.
- The four release-path majors resolved or pinned with a written reason, per Q3.
- The staleness figure exists and has a stated ceiling.
- The 16 open PRs triaged: each merged, closed with a reason, or named in this item's Updates.

## Updates

### 2026-10-16 - filed

Filed from a read-only board review at the owner's request. Evidence gathered with `gh pr list`,
`gh pr view`, `gh run list --workflow <file>`, `gh api repos/.../branches/main/protection`,
`gh api repos/.../dependabot/alerts` and a read of `.github/dependabot.yml` and the workflow
triggers. Filed from a separate worktree off `main` because another agent was working in the
main checkout. Not examined: the failing #127 log, the `capture-smoke.yml` failure cause, whether
`release.yml` publishes on dispatch, and the contents of the 23 alerts.
