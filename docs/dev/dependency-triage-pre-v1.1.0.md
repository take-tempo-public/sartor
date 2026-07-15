# Dependency triage — the 12 open Dependabot PRs, pre-v1.1.0

> **Purpose:** the finished research product for clearing Dependabot PRs #5–#18 before the
> v1.1.0 public release. Per-PR verdict, the reason, and — where it matters — **the thing
> Dependabot got wrong**. Four of these twelve are **not safe to merge as-authored**.
> **Audience:** whoever executes `chore/deps-triage-pre-v110`.
> **Status:** research complete, **nothing merged yet**.
> **Provenance:** every claim below is tagged **[measured]** (I ran it) or **[read]** (from
> upstream release notes / source, not executed here). Do not silently promote a **[read]** to a
> fact — charter **C-7**.

---

## Read this first: two structural findings that explain the rest

### 1. There is no lockfile, so a "range widen" is a **live major adoption**

`.github/actions/setup-python-env/action.yml` runs a bare `pip install -e ".[dev]"`. **CI
re-resolves newest-satisfying on every run.** So a PR that merely widens a ceiling (`mypy <2.0` →
`<3.0`) does not "allow" a future upgrade — it **performs one, immediately, on the next CI run**.
Three of these PRs are that shape (#5, #6, #14) and must be read as adoptions, not permissions.

`.github/dependabot.yml` has a comment pointing at a "RELEASE_CHECKLIST.md Carry-forward ledger"
row for the lockfile decision. **That row does not exist.** The decision survives only as a
sentence buried inside another row's update log (`docs/dev/RELEASE_CHECKLIST.md:980`). Promote it
to a real ledger row. **[measured]**

### 2. The docs-site has **no PR-time build gate at all**

Workflow trigger map **[measured]** — read from the `on:` blocks:

| Workflow | Runs on `pull_request`? |
|---|---|
| `ci.yml` | **yes** |
| `codeql.yml` | **yes** |
| `release.yml` | **no** |
| `docker.yml` | **no** |
| `docs-deploy.yml` | **no** |
| `scorecard.yml` | **no** |

**This is why #16 and #17 both show 9/9 green while being broken.** Nothing builds the docs-site
on a PR. The green checkmarks are the Python suite, which never touches `docs-site/`. Two of the
four dangerous PRs in this batch are dangerous *because of this hole*.

Build the docs-site PR gate (user-approved) **before** merging any `docs-site/` dependency PR, or
you are merging on faith.

---

## Verdicts

| PR | Bump | Verdict |
|---|---|---|
| **#14** | `pytest-rerunfailures <16` → `<17` | **MERGE — and merge it FIRST** |
| **#6** | `pytest <9.0` → `<10.0` | **MERGE, strictly AFTER #14** |
| **#5** | `mypy <2.0` → `<3.0` | **MERGE** + CHANGELOG |
| **#7** | `ruff ==0.15.12` → `==0.15.21` | **MERGE** + a doc fix (C-0) |
| **#12** | `setup-python` v5 → v6 | **MERGE** + a 5th pin Dependabot missed |
| **#10** | `download-artifact` v4 → v8 | **MERGE** + hand-bump the upload side |
| **#11** | `setup-buildx-action` v3 → v4 | **MERGE** |
| **#18** | `build-push-action` v6 → v7 | **MERGE** |
| **#15** | `fumadocs-mdx` 15.1.0 → 15.1.1 | **MERGE** |
| **#13** | `fumadocs-openapi` 11.1.1 → 11.2.0 | **MERGE** |
| **#16** | `fumadocs-core` 16.11.2 → 16.11.4 | **MERGE — but `npm ci` FAILS as-authored** |
| **#17** | `typescript` 6.0.3 → 7.0.2 | **CLOSE. Do not merge.** |

---

## The four that bite

### #14 before #6 — this ordering is load-bearing

`pytest 9.1.1` + `pytest-rerunfailures 15.1` makes a test whose **fixture** fails on rerun raise
`assert not self._finalizers` — an ERROR, not a failure. **[read]** — from the rerunfailures 16.x
changelog; I did not construct the failing case.

**pip will not catch this**: `pytest-rerunfailures 15.1` does not declare an upper pytest bound, so
the resolver happily installs the broken pair. Merging #6 first gives you a CI failure with a
traceback pointing into pytest internals and no obvious cause.

**Merge #14 (→ 16.4) first. Then #6.** This is also the PR that governs `--reruns`, which is
currently masking a real bug — see `docs/dev/diagnosis/compose-summary-draft-settle-hole.md`.

### #7 (ruff) carries a **C-0 violation** if merged as-is

The format sweep at 0.15.21 is a **verified no-op** — 302/302 files already conform. **[measured]**

But `docs/wiki/pages/non-dependency-downloads.md:46` states the pin is `(==0.15.12, not a range)`.
Bumping the pin without fixing that line leaves a doc asserting a false fact — an ungrounded claim,
which is a **C-0 violation**. Fix the line in the same commit. **[measured]** — I read the line.

### #12 (setup-python) — Dependabot **missed a pin**

Dependabot's `directory: "/"` for `github-actions` scans **`.github/workflows/` only**. It does not
see composite actions. So it bumped 4 pins and left the 5th:

**`.github/actions/setup-python-env/action.yml:17`** — the composite that feeds the `quality`
matrix **and** `eval-smoke`. **[measured]**

Bump it by hand in the same PR. Then fix the root cause: add
`directory: "/.github/actions/setup-python-env"` to `.github/dependabot.yml`.

### #16 (fumadocs-core) — **`npm ci` fails as-authored**

`fumadocs-ui` is an **npm alias**: `"fumadocs-ui": "npm:@fumadocs/base-ui@16.11.2"`. It is
peer-pinned **exactly** to `fumadocs-core`. Bumping core to 16.11.4 alone leaves an unsatisfiable
peer and `npm ci` fails. **[measured]** — reproduced the install failure.

Bump **both**, in lockstep: `fumadocs-ui` → `npm:@fumadocs/base-ui@16.11.4`.

And note *why this wasn't caught*: no PR-time docs-site build (see finding 2 above). The PR is
green and broken.

### #17 (typescript 6 → 7) — **CLOSE it**

TypeScript 7 is the **Go native port**. It ships no `lib/typescript.js`, no `tsserver`, and
`ts.createProgram` is `undefined`. **[read]** — from the TS7 release notes and the published
package contents.

Next.js 16 resolves TypeScript by that literal file path, so the build **exits 1**. With
`ignoreBuildErrors` set it **segfaults (exit 139)**. **[measured]** — I ran both.

**Close the PR and add a `typescript` major-version `ignore` to `.github/dependabot.yml`**, or it
will be re-offered forever.

---

## The clean eight (verdicts, briefly)

- **#5 mypy → 2.3.0.** Clean across 317 files **[measured]** — but **on py3.13 only**. Gate on the
  PR's own 3.11/3.12/3.13 matrix before merging. ⚠️ `pyproject.toml:59-66` justifies the
  `numpy<2.5` cap **against mypy 1.20.2** — that justification is now stale; re-verify whether the
  cap is still needed. **[measured]** — I read the comment; I did **not** test lifting the cap.
- **#6 pytest → 9.1.1.** Green, 1916 passed. **[measured]** (after #14.)
- **#10 download-artifact v4 → v8.** The breaking changes don't touch us: `artifact-ids` is absent
  and we download by `name: dist`. **[measured]** — grepped the workflow. **Also hand-bump the
  upload side**: `actions/upload-artifact` 4.6.2 → **7.0.1**
  (SHA `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`). ⚠️ `release.yml` is **not PR-exercised** — the
  `v1.1.0-rc.1` tag is the first thing that will ever run it.
- **#11 setup-buildx-action v3 → v4.** Bare `uses:`, zero inputs. v4 removed
  `config`/`config-inline`/`install`; we pass none. **[measured]**
- **#18 build-push-action v6 → v7.** v7 removed `DOCKER_BUILD_NO_SUMMARY` and
  `DOCKER_BUILD_EXPORT_RETENTION_DAYS`; **neither string appears anywhere in the repo**.
  **[measured]**
- **#15 fumadocs-mdx 15.1.1.** js-yaml → yaml swap only; build verified. **[measured]**
- **#13 fumadocs-openapi 11.2.0.** The release note's "raw access" caveat doesn't apply — we use
  only the public API. **[measured]**

---

## No-PR items (Dependabot will never offer these)

### `codeql-action` v3 → v4.37.0 — do this by hand

v3 is **deprecated December 2026**. Dependabot PR **#1 was closed**, so it will **never be
re-offered**. Three pins to update **[measured]**:

- `.github/workflows/codeql.yml:44`
- `.github/workflows/codeql.yml:57`
- `.github/workflows/scorecard.yml:49`  ← easy to miss

Commit SHA (dereferenced from the annotated tag, per the repo's SHA-pinning policy):
**`99df26d4f13ea111d4ec1a7dddef6063f76b97e9`**

### `.github/dependabot.yml` — three fixes

1. Add `directory: "/.github/actions/setup-python-env"` (the missed-pin root cause, #12).
2. Raise `open-pull-requests-limit` for `github-actions` — it is **5**, which is **hiding a
   ~9-deep backlog** **[measured]**: `checkout` v4→v7, `upload-artifact` v4→v7, `cache` v4→v6,
   `setup-node` v4→v6, `attest-build-provenance` v2→v4, `setup-qemu` v3→v4, `login-action` v3→v4,
   `metadata-action` v5→v6.
3. `ignore` `typescript` majors (#17).

---

## Suggested execution order

1. **#14** (rerunfailures) — unblocks #6.
2. **#6** (pytest), **#5** (mypy), **#7** (ruff + the C-0 doc fix) — the Python tier.
3. **codeql v4** + the `dependabot.yml` fixes + the missed `setup-python` pin — by hand.
4. **#12, #10** (+ upload-artifact), **#11, #18** — the Actions tier.
5. **Build the docs-site PR gate.** Then and only then:
6. **#15, #13, #16** (with the `fumadocs-ui` lockstep bump).
7. **Close #17.**

Every merge is `gh pr merge --squash` (merge commits are disallowed on `main`).
