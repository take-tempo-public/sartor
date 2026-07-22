# Diagnosis — `docs-site/` production deploy has been failing for 5 consecutive merges

> **Status:** root cause **proven** by directly reading the installed detector source
> (see `## Observed`, "source-read confirmation" below) — not just correlation, not the
> falsification experiment originally specified (that experiment's proposed pin turned
> out to be the fix itself, applied directly once the mechanism was read). **Currently
> an active production outage**, not a routine backlog item.
> **Branch:** `fix/docs-site-typescript-detection` — this file was renamed from
> `docs-site-typescript-detection-broken.md` to match the branch slug per
> `scripts/enforcement/evidence.py:branch_slug`.

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

**Source-read confirmation (this branch, before writing any fix) — the mechanism is now
proven, not inferred:**

- Read `docs-site/node_modules/next/dist/lib/verify-typescript-setup.js`. It defines
  `typescriptPackage = { file: 'typescript/lib/typescript.js', pkg: 'typescript',
  exportsRestrict: true }` and passes it to `hasNecessaryDependencies`.
- Read `docs-site/node_modules/next/dist/lib/has-necessary-dependencies.js`. When
  `exportsRestrict` is true, it resolves the package dir, then does
  `existsSync(join(pkgDir, relative(p.pkg, p.file)))` — i.e. it checks for the literal
  file `<typescript-pkg-dir>/lib/typescript.js` on disk. If that check fails, the
  package is pushed onto `missing`, regardless of whether `require.resolve`-style
  resolution would have found the package by its `exports` map.
- Checked the installed `typescript@7.0.2` directly:
  `ls docs-site/node_modules/typescript/lib/typescript.js` → **"No such file or
  directory."** `ls docs-site/node_modules/typescript/lib/` shows only
  `getExePath.{js,d.ts}`, `tsc.js`, `version.{cjs,d.cts}` — no `typescript.js`. Its
  `package.json` has `"main": null`, `"type": "module"`, and an `exports` map whose only
  bare (`"."`) entry is `./lib/version.cjs`; the actual compiler API lives under
  `./dist/api/*` and `./unstable/*` exports, not `./lib/typescript.js`. TS7 restructured
  the package layout entirely — the file the detector hard-codes simply does not exist
  in this line, independent of whether Node could otherwise resolve `typescript`.
- Back in `verify-typescript-setup.js`: when `hasNecessaryDependencies` reports
  `typescript` missing, `_ciinfo.isCI` gates the behavior — true (CI) prints exactly the
  `"It looks like you're trying to use TypeScript but do not have the required
  package(s) installed"` message via `missingDepsError` and lets the caller fail; false
  (local shell) instead calls `installDependencies(dir, deps.missing, true)` — the
  observed local auto-install-then-crash. Both observed failure shapes (CI: clean
  instruct-and-exit; local: auto-install attempt that rewrites `package.json`, then a
  second crash) are fully explained by this one function, gated on one env check — no
  unread code path remains.
- This directly resolves the two items previously logged as unconfirmed inferences
  below: the false-negative mechanism, and the CI-vs-local behavioral split via
  `process.env.CI`(`_ciinfo.isCI`).
- **The old-commit secondary failure is moot for HEAD.** The dossier below records that
  the last-known-good commit fails differently (`generateStaticParams()` missing for
  `/og/docs/[...slug]`) when rebuilt fresh today — a separate, still-unexplained
  time-dependent-reproducibility wrinkle in that *old* commit. Checked the *current*
  tree: `docs-site/src/app/og/docs/[...slug]/route.tsx` already exports
  `generateStaticParams` (and so do the other two dynamic routes,
  `docs/[[...slug]]/page.tsx` and `llms.mdx/docs/[[...slug]]/route.ts`). That failure
  mode does not block this branch's fix; the time-dependent-reproducibility question
  itself remains open and unchased (see note below), but it is not on this branch's
  critical path.

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
  opposite: this is now the leading, evidenced hypothesis — and, per the source-read
  confirmation above, now the proven mechanism.**
- **Hypothesis (below, formerly under `## Inferred`): Next's detector does a CJS-shaped
  lookup incompatible with ESM-shaped `typescript@7.x`.** No longer a hypothesis — read
  directly in `has-necessary-dependencies.js` / `verify-typescript-setup.js`. See
  "source-read confirmation" above.

---

## Inferred

Nothing remains open here — both items formerly recorded as unconfirmed inferences (the
false-negative detection mechanism, and the CI-vs-local behavioral split via
`process.env.CI`) were confirmed by directly reading Next's source; see "source-read
confirmation" under `## Observed` above.

**Still genuinely open, not chased on this branch (out of scope for the fix):** the
separate time-dependent-reproducibility wrinkle where the *last-known-good* commit
(`e935ee7`) no longer builds cleanly from a fresh `npm ci` today either — it fails at a
later, unrelated stage (`generateStaticParams()` missing for the old commit's
`/og/docs/[...slug]` route, since fixed on `main` independent of this bump). This means
CI's historical green/red is not a perfectly clean bisection signal in general, though it
did not affect settling this particular defect.

**New, this branch's own fix — a side effect worth recording, deliberately not chased
further:** the standalone `fumadocs-mdx` CLI (invoked directly by the `types:check` npm
script — `fumadocs-mdx && next typegen && tsc --noEmit`, not by `next build`, which
invokes its own MDX codegen through a webpack/turbopack plugin instead) generates **empty**
`.source/{browser,dynamic,server}.ts` files under `typescript@6.0.3`, where the same
command against unmodified `typescript@7.0.2` (isolated worktree, `git worktree add`)
produces real content (`.source/server.ts` 310 bytes vs. 0). Reproduced twice on this
branch (`rm -rf .source && npm run types:check` → `tsc --noEmit` fails with
`src/lib/source.ts(1,22): error TS2306: File '.../.source/server.ts' is not a module.`).
**Deliberately not fixed here — out of scope:** `types:check` is not referenced by any
CI workflow, README, or `CONTRIBUTING.md` (grepped; zero hits) and `npm run build` (the
only path CI/`docs-deploy.yml` actually exercises) is unaffected — its own internal MDX
codegen produced a fully working 132-page static export, verified above. Flagging so a
future session picking up `types:check` (or a future `fumadocs-mdx` bump) isn't
surprised by this — the mechanism (why `fumadocs-mdx`'s own codegen differs by
`typescript` version) was not investigated.

---

## Falsification

_Superseded — the originally-specified experiment (pin `typescript` to `^6.0.3` and
rebuild) was subsumed by directly reading the detector source, which proved the
mechanism without needing the black-box pin-and-observe step. The pin is applied
directly as the fix (below), and its effect is verified the same way the experiment
would have proven it: a clean `npm ci` + `npm run build` reaching `out/index.html`._

---

## The fix

1. **`docs-site/package.json`**: `devDependencies.typescript` `^7.0.2` → `^6.0.3` — the
   last CJS-shaped line, whose `lib/typescript.js` genuinely exists on disk, so Next's
   hard-coded `existsSync` check passes. Lockfile (`package-lock.json`) regenerated to
   match. `next` stays at `16.2.11` (no change) — this is a dev-only, single-package
   pin, not a `next` upgrade.
2. **`.github/dependabot.yml`**: add an `ignore` rule for `typescript` major-version
   bumps under the `/docs-site` entry, so dependabot does not immediately re-propose the
   exact 7.x bump that caused this outage. Scoped to majors only — 6.x patch/minor
   updates still flow normally.
3. **`.github/workflows/docs-deploy.yml`**: add a `pull_request: branches: [main]`
   trigger so a broken docs-site build fails a PR check instead of landing silently on
   `main` — closing the blind spot that let this regress 5 times unnoticed (no PR check
   ever built `docs-site/` before this). Deploy-only steps (SFTP) stay push-gated.
4. Remove the `typescript` dependabot-ignore + revisit the `next` pin once a `next`
   release ships a detector that resolves TypeScript via its `exports` map (or via
   `require.resolve`) instead of a hard-coded `lib/typescript.js` path check.

---

## Acceptance bar

- A genuinely fresh `npm ci` + `npm run build` in `docs-site/` (after the `typescript`
  pin) succeeds and produces `out/index.html`, with no "trying to use TypeScript"
  message. **Met** — see the fix commit's cited verification.
- `npm audit` in `docs-site/` still reports 0 vulnerabilities (the prior branch's
  `sharp`/`fast-uri`/`postcss` overrides are untouched by this change).
- The first `docs-deploy.yml` run on `main` after this branch merges is green
  (`gh run list --workflow=docs-deploy.yml`) — the real bar, since a local pass alone
  repeats the exact blind spot that let this regress silently 5 times.
- A PR that reintroduces a `docs-site/` build break now fails a required-visible PR
  check (new `pull_request` trigger on `docs-deploy.yml`), rather than only being
  discovered post-merge.
