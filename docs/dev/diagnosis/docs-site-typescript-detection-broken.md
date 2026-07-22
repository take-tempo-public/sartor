# Diagnosis — `docs-site/` production deploy has been failing for 5 consecutive merges

> **Status:** hypothesis only, evidence-backed — root cause not yet proven by a
> falsification experiment (see below). **Currently an active production outage**, not a
> routine backlog item.
> **Branch:** none yet — discovered incidentally on `chore/docs-site-npm-audit` while
> verifying an unrelated `next`/`sharp`/`fast-uri` audit fix. Whoever picks this up should
> rename this file to `docs/dev/diagnosis/fix-<slug>.md` (matching their branch) once a
> `fix/*` branch exists — the `require-evidence-before-fix` hook looks for that exact path.

---

## Symptom

`docs-deploy.yml` ("Docs site deploy") has failed on every push to `main` since
**2026-07-22T06:36:32Z** (PR #42, `chore/dependabot-docs-site`) — 5 consecutive runs (PRs
#42, #44, #45, #46, #47), each failing at the `npm run build` step. No PR check builds
`docs-site/` (the workflow only triggers on `push: branches: [main]`), so every one of
those 5 merges landed with a broken production deploy and nobody saw it happen at merge
time.

---

## Observed

- `gh run list --workflow=docs-deploy.yml --limit 8` (run 2026-07-22, this session):
  PR #41 (`docs/compose-rewrite-dial`, merged 2026-07-22T01:17:06Z) is the **last success**.
  PRs #42, #44, #45, #46, #47 (2026-07-22T06:36Z through 17:38Z) are all **failure**.
- `gh run view 29897302282 --log-failed` (the first failing run, PR #42) shows the exact
  failure text:
  ```
  Running TypeScript ...
  It looks like you're trying to use TypeScript but do not have the required package(s) installed.

  Please install typescript by running:

  	npm install --save-dev typescript
  ...
  Next.js build worker exited with code: 1 and signal: null
  ##[error]Process completed with exit code 1.
  ```
- Reproduced locally, twice, independently of any change on this branch:
  1. `git stash` (reverting this branch's own package.json/lockfile edits back to
     unmodified `main` state) → `npm install` → `npm run build` → same
     "It looks like you're trying to use TypeScript..." message, followed by an
     **auto-install attempt** (`Installing devDependencies (npm): - typescript`, then
     `up to date, audited N packages`), then a second, different crash:
     `The "id" argument must be of type string. Received undefined` /
     `Next.js build worker exited with code: 1`.
  2. Fresh isolated worktree at `main` HEAD (`0ce56b6`, this session, before any of my
     edits): `git worktree add /tmp/bisect-main 0ce56b6`, `cd docs-site && npm ci` (clean
     install, no reused `node_modules`), `npm run build` → **identical** two-stage failure
     to (1).
- `node_modules/typescript/package.json` (present after both `npm ci` and `npm install`,
  confirmed via `ls`/`cat`) shows `"version": "7.0.2"`, `"type": "module"`, and a `bin.tsc`
  entry — the package genuinely IS installed and the `tsc` binary genuinely IS present at
  `node_modules/.bin/tsc`.
- **CI's failure mode differs from the local failure mode at the same trigger point**: CI
  prints only the "please install typescript manually" message and exits immediately
  (no auto-install attempt visible in the log); locally (both via `npm install` reusing a
  node_modules dir, and via a from-scratch `npm ci`), Next.js visibly attempts an
  auto-install (`Installing dependencies` / `Installing devDependencies (npm): - typescript`)
  before crashing with the unrelated `"id" argument` error. This is consistent with Next's
  auto-install fallback checking `process.env.CI` and behaving differently in GitHub
  Actions vs. a plain interactive shell — but that specific code path was not read/proven,
  only inferred from the differing log shapes (see `## Inferred`).
- The local auto-install attempt has an observed **side effect**: it silently rewrites
  `docs-site/package.json`, stripping the `^` from `"typescript": "^7.0.2"` →
  `"typescript": "7.0.2"` (caught and reverted twice this session via `git diff` /
  `git checkout -- package.json`).
- A truly fresh `npm ci` + `npm run build` at the **last known-good** commit
  (`e935ee7`, PR #41's merge — the run `gh run list` reports as the last CI success) in
  an isolated worktree does **NOT** reproduce the typescript-detection failure — it fails
  differently, at a later build stage: `Error: Page "/og/docs/[...slug]" is missing
  "generateStaticParams()" so it cannot be used with "output: export" config.` This means
  a byte-for-byte-identical `npm ci` result is **not** obviously reproducible purely from
  git history + the committed lockfile across time — something time-dependent (a floating
  registry resolution not fully pinned by the lockfile, or a difference between the CI
  runner's exact install state on the day PR #41 ran vs. a fresh install today) is also in
  play, **separate from** the typescript-detection issue below. This was NOT chased
  further this session — flagging it here so the next investigation doesn't have to
  rediscover it blind.
- **`git diff e935ee7 e6eb12e -- docs-site/package.json` (last-good vs. first-bad merge
  commit) shows exactly the change that matters:** `typescript` `^6.0.3` → `^7.0.2`
  (plus unrelated `fumadocs-core`/`fumadocs-mdx`/`fumadocs-openapi`/`fumadocs-ui`/
  `@tailwindcss/postcss` minor bumps — none of which touch `next`, `sharp`, or
  TypeScript). `typescript@6.0.3` is the last CJS-shaped release line; `7.0.2` is the
  first ESM-only (`"type": "module"`) line. This is the exact commit where the
  ESM-shaped `typescript` first entered the tree, and it is also the exact commit where
  `docs-deploy.yml` first started failing — a strong correlation, not yet a proof (see
  `## Falsification` below for the experiment that would prove it).
  **Correction:** an earlier draft of this note claimed this diff was empty — that was
  wrong, caused by a shell-quoting issue with a trailing-slash directory path
  (`-- docs-site/`) in one Bash invocation that silently produced no output; re-running
  with an exact file path (`-- docs-site/package.json`) shows the real diff above. Flagged
  here rather than silently corrected, per the standing rule that a wrong claim gets
  named as wrong, not quietly edited away.
- **`chore/dependabot-docs-site`'s own CHANGELOG entry (the PR that made this exact
  typescript bump) claims:** *"Validated with a full local `npm run build` (not just
  lockfile resolution) — compiles, typechecks under TS 7, and generates all 126 static
  pages clean."* Yet that same PR's own merge-triggered `docs-deploy.yml` run
  (id `29897302282`) **failed**, with the exact typescript-detection error this note is
  about. Not chased further this session (would require asking whether the local claim
  was made against a stale/reused `node_modules` that predated the bump, a different
  local Node/npm version, or was simply unverified) — flagged as a second, related
  open question for whoever picks this up, since it may itself be a claims-discipline
  (C-0) gap worth its own note once the technical root cause is settled.

---

## Falsified

- **Hypothesis: caused by this session's `next`/`sharp`/`fast-uri` overrides.** Falsified —
  reproduces identically on unmodified `main` HEAD via an isolated worktree with a clean
  `npm ci`, before any of this branch's edits existed.
- **Hypothesis: `typescript` is simply missing from `node_modules` (a lockfile/install
  bug).** Falsified — `node_modules/typescript/package.json` and `node_modules/.bin/tsc`
  are both genuinely present after both `npm ci` and `npm install`.
- **Hypothesis: the break came from a `docs-site/`-local change in PR #42.** This was
  briefly (wrongly) marked falsified earlier in this same investigation, from a bad
  `git diff e935ee7 e6eb12e -- docs-site/` command that silently produced no output due to
  a shell-quoting issue with the trailing-slash path. Corrected above under `## Observed`:
  the real diff shows exactly the `typescript` `6.0.3→7.0.2` bump. **Not falsified — the
  opposite: this is now the leading, evidenced hypothesis.**

---

## Inferred

**THIS IS STILL A HYPOTHESIS, NOT FACT — but it is now backed by a direct correlation,
not just a plausible mechanism.** `typescript@7.0.2` ships as `"type": "module"` (pure
ESM) — a structurally different package shape than `typescript@6.0.3` (the last
CJS-shaped release, and the version in place at the last commit whose `docs-deploy.yml`
run succeeded). The exact commit that bumped `6.0.3 → 7.0.2` is the exact commit where
`docs-deploy.yml` first started failing, with no other change in that diff touching
`next`, TypeScript, or the build config. The leading hypothesis: Next.js's internal
"is TypeScript installed" detector was written against a CJS-shaped lookup (historically
something like `require.resolve('typescript')`), and a genuinely-installed ESM-only
`typescript@7.x` produces exactly this false negative — explaining the same symptom at
the "detected as absent" step in both CI and locally, and, locally, cascading into a
second, unrelated-looking crash when Next's own auto-install/recovery path then tries to
interact with the package in a way its assumptions don't hold. This has **not** been
confirmed by reading Next.js's actual detector source, and the correlation (one commit,
one diff) is strong but is still an inference, not a read mechanism — that is the
remaining gap, and exactly what the falsification experiment below is for.

A secondary, also-unconfirmed inference: the CI-vs-local difference in failure shape
(hard-fail-with-instructions vs. auto-install-then-crash) is Next checking
`process.env.CI` to decide whether to attempt the auto-install fallback at all. Not
verified against Next's source.

---

## Falsification

**The experiment that settles the primary hypothesis — run this BEFORE writing any fix:**

In `docs-site/`, with a clean `node_modules` (`rm -rf node_modules && npm ci`), pin
`devDependencies.typescript` back to `^6.0.3` — the exact last-known-good, CJS-shaped
version per `## Observed` above — instead of `^7.0.2`, reinstall, and run `npm run build`.

- **If the build now succeeds (reaches `Collecting page data` / produces `out/index.html`
  without the "not installed" message):** the hypothesis is confirmed — the fix is either
  pinning `typescript` to a CJS-compatible line as a stopgap, or (better, if available)
  upgrading `next` to a version whose detector handles ESM-shaped `typescript`, or filing
  upstream against Next.js.
- **If it still fails the same way:** the hypothesis is dead. Stop, do not "fix" this by
  downgrading `typescript`, and widen the instrument — re-read Next's actual
  `next/dist/lib/typescript/*` detection source at the installed version instead of
  guessing from symptom shape.

Note the **separate, still-open time-dependent-reproducibility question** from
`## Observed` above (last-known-good commit no longer builds cleanly either, but fails
differently) — that should be resolved or at least understood before declaring any fix
complete, since it complicates using CI's historical green/red as a clean bisection
signal.

---

## The fix

_Not written — no falsification experiment has been run yet. Do not skip to a fix
without running the experiment above first._

---

## Acceptance bar

_To be defined once the falsification experiment above has actually been run. At minimum:
a genuinely fresh `npm ci` + `npm run build` in `docs-site/` succeeds and produces
`out/index.html`, AND the next `docs-deploy.yml` run on `main` after the fix lands is
green (not just a local build — the whole reason this went unnoticed for 5 merges is that
no PR check exercises this, so a local pass alone repeats the same blind spot)._
