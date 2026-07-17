# Changelog

All notable changes to Sartor are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope:** this file tracks product/code changes. Wiki ingest/refresh passes
> (`docs/wiki/`) are recorded in [`docs/wiki/log.md`](docs/wiki/log.md) — the wiki's
> own changelog — not here.

---

## [Unreleased]

### Fixed vulnerabilities

No publicly known vulnerabilities in Sartor's own code were fixed in this release —
none were reported. (Charter D-7.4 requires this statement in every release, so that
silence is never mistaken for a disclosure. Scope is Sartor's own code; dependency
advisories — e.g. the nested `postcss` GHSA-qx2v-qp2m-jg93 patched below — are tracked
in the Security section, not here.)

### Added: handoff transfer integrity — committed, fingerprint-validated handoff files (`feat/handoff-integrity-kit`)

Handoffs copy-pasted between Claude Code sessions have been silently arriving corrupted —
confirmed on sartor's own `fix/plan-approval` branch and three more times in spolia (formerly
ai-research), the sibling project where this fix was built and proved first. The signature: a
fixed-length run of characters silently deleted mid-line, the flanking fragments fused into
something that reads as plausible but isn't — consistent with a clipboard/terminal-grid copy
(VS Code's integrated terminal, xterm.js) losing wrapped or redrawn rows in transit. **Three of
the four agents that received corrupted input said nothing and silently reconstructed it.**
Nothing in either project's binding rules named damaged input as a stop condition — full
evidence + decision record: [`docs/dev/handoff-integrity-design.md`](docs/dev/handoff-integrity-design.md).

- **Handoffs now transfer as a committed file**, not chat-pasted text — deletes the lossy
  clipboard/terminal-grid hop entirely. Supersedes the 2026-06-08 "handoffs are ephemeral chat
  text, never a committed file" policy **for the transfer-channel question specifically**; that
  policy's still-valid half (never write session scratch into `output/`) is unaffected.
- **`docs/dev/prov/SPEC.md`** — the provenance-stamp vocabulary, privacy tiers, and ledger event
  schema, vendored from spolia's already-proven kit (two real branches there, including a real
  CRLF fingerprint bug found and fixed before this vendoring).
- **`scripts/verify_doc_template.py`** — a generic doc/template validator: every structural
  heading present and in order, every `<!-- verbatim -->` section byte-identical to its
  template, a content fingerprint (newline-normalized, so a Windows `core.autocrlf` checkout
  can't spuriously "change" a doc that never changed) recorded at generation and re-checked at
  consumption.
- **`docs/dev/AGENT_HANDOFF_TEMPLATE.md`** extended (not replaced) with the provenance stamp,
  `<!-- verbatim -->` markers on its four fixed sections, and a fifth binding rule: **corrupted
  or fingerprint-mismatched input is a blocked gate** — surfaced as the consuming session's
  first output and STOPPED on, never silently reconstructed. `AGENTS.md`'s close-out checklist
  updated to match.
- `docs/dev/handoffs/` (committed handoff files) and `docs/dev/ledger/` (append-only, per-session
  JSONL event shards) are new, tracked directories.
- `tests/test_verify_doc_template.py` (24 tests) ports spolia's suite, including the CRLF
  regression test, adjusted for sartor's flat `tests/` layout.
- Advisory, not a hook, at launch (matches spolia's own rollout arc — escalate only if the
  advisory step is observed being skipped). Whether the new binding rule needs a formal charter
  amendment (near C-7/C-8) is an open question for the owner, not decided on this branch.

### Fixed: corpus/Compose reloads could snap your scroll position away (`fix/ux-scroll-position-flake`)

Accepting, retiring, or editing a bullet could scroll you back to the top of a long corpus or
Compose list — intermittently, worse under CPU load, and worse still with a large corpus, where
Compose's background auto-cascade (drafting the positioning summary, recommending skills, filling
gaps) can re-reload the list several times over a few seconds, each one a fresh chance to lose
your place.

**Root cause: capture/restore trusted a single, one-shot scroll read/write as final.**
`_captureScrollY`/`_restoreScrollY` (`static/app.js`) had no way to know "have I been superseded"
or "is the page still settling," so two independent races fell out of that one gap: a stale,
already-superseded reload's restore could fire last and silently overwrite a position something
else had since legitimately established; and a single `requestAnimationFrame`-deferred restore had
no defense against browser scroll-anchoring landing a frame or more late, as the lists' own async
growth (cards, fire-and-forget editors) continued after the "restore" had already fired.

The fix adds a per-load ordinal (a newer reload instantly voids an older one's pending restore, no
time limit, regardless of how long a background cascade takes) and a generation counter on the
explicit scroll APIs this app uses (a deliberate reposition also voids a stale pending restore),
plus a bounded settle loop that keeps re-asserting the restored position until the page's height
has genuinely stopped changing, instead of trusting a single frame.

> **How this was arrived at matters.** The failure showed four distinct value signatures across
> repeated runs, not one — a race with a variable-timing scroller, not a single deterministic path.
> Two of the four were confirmed **unrelated** to this defect (a wizard-rail smooth-scroll racing a
> test's own baseline read, and a harness-level tab-wait timeout under load) and deliberately left
> untouched. The other two were each deterministically reproduced on demand — not inferred from
> passing runs — by forcing the exact orderings two real-world captures had shown, before any fix
> was written (charter **C-7**). Full evidence record:
> [`docs/dev/diagnosis/ux-scroll-position-flake.md`](docs/dev/diagnosis/ux-scroll-position-flake.md).

### Security: one validated-resolver chokepoint for context-file paths (`fix/codeql-path-injection-context`)

CodeQL's `py/path-injection` query flagged seven "high" alerts on the context-file helpers in
`hardening.py`. They were **verified false positives** — every one of the twelve
`context_transaction` call sites is `_within`-guarded — but the guard lived in the route while
the filesystem operation ran in `hardening.py`, a different function, so the analyzer could not
carry the containment barrier across the call boundary. Rather than dismiss the alerts per-item
(which re-fires the moment any route is added), the containment is now expressed as a single
**validated-resolver chokepoint**:

- **`web_infra.resolve_within(candidate, root) -> Path`** normalizes the candidate with
  `os.path.realpath`, verifies containment, raises `PathTraversalError` on escape, and
  **returns the resolved-and-validated path** — the value callers use downstream. The eleven
  route sites in `blueprints/applications.py` that flow into `context_transaction` now derive
  their path from this call. `_within` is unchanged and still used directly by the in-function
  reader helpers.
- Because CodeQL's Python query recognizes no pathlib/containment sanitizer natively, a small
  repo-local **CodeQL model pack** (`.github/codeql/extensions/sartor-python-models/`, applied
  automatically — no publishing) declares that resolver a `path-injection` barrier. Net result,
  confirmed on CI: zero open `py/path-injection`, zero open high-severity alerts.
- HTTP behavior is **unchanged** (same `400 Invalid context_path`; existence stays a separate
  check). The `route-security-lint` guard and the `test_route_containment_gate` do-not-regress
  gate now accept `resolve_within` as containment proof **by design**, with an explicit test.

No behavior change for users; this hardens the static-analysis posture so "CodeQL green" is
earned by construction (it is required for the OpenSSF badge).

### Fixed: your drafted positioning summary could vanish for good — a lost update across twelve context writers (`fix/compose-summary-draft-settle-hole`)

A user arriving at Compose could watch the app write their drafted positioning summary and
then silently throw it away — permanently. Another could sit under **"Drafting your
summary…" forever**, with no error, no retry, no recovery. Both are fixed, along with the
write path beneath them and the reporting that made the whole class of failure invisible.

**The root cause was a lost update.** Twelve routes in `blueprints/applications.py` each read
the *whole* `context_*.json`, spend seconds inside an LLM call, then write the *whole* — by
now stale — dict back. Any route that wrote inside that window had its delta silently
deleted. `POST /draft-summary` persisted the summary and returned 200; a concurrent
`POST /recommend`, holding a copy read *before* that write, then wrote it back and erased it.
Nothing errored. Every response was a 200. The data was simply gone from disk.

- **`hardening.context_transaction`** — a `@contextmanager` taking a **per-path
  `threading.Lock`** that **re-reads the file fresh inside the lock**, discarding the caller's
  optimistic pre-call copy; yields it for the caller's own delta; writes via the existing
  `write_context_atomic` on a clean exit; and **skips the write entirely if the block raises**,
  so a failed delta can never half-land. The **LLM call stays outside the lock**, so no request
  ever waits on another's latency — only the delta application is serialized, and that is
  microseconds. In-process is the right scope: the container runs a single-process *threaded*
  server. **All twelve sites converted** — repairing only the two in the observed window would
  have fixed the symptom and left the defect class.
- **A trap worth naming, because the fix nearly stepped in it.** Six of the twelve sites are
  not LLM routes; they build a `composition_overrides` sub-dict *from the stale read* and then
  assign it back wholesale. Wrapping those in a transaction while still carrying that stale
  sub-dict in would have **re-created the very bug inside the fix**. Each now re-derives its
  delta against the fresh dict — "append this bullet id", "drop this proposal", "add this
  retired key" — rather than replacing a whole set it read minutes ago.
- **A hazard closed by construction rather than by vigilance.** The transient staging keys
  (`jd_text`, `career_facts`, `summary_items`, …) are absent from a fresh read, so the
  defensive `ctx.pop(transient)` at each write site — and the standing "don't leak staging keys
  into the iteration chain" hazard — is now structurally impossible instead of remembered.

> **How this was arrived at matters as much as the fix**, and is the reason it is trustworthy.
> Two earlier fixes on this branch were shipped for mechanisms that had **never been
> observed**; both addressed real defects, and **neither was the defect**. The repair above was
> built only *after* a falsification test was written, committed **while still red**, and shown
> to fail on HEAD — `tests/test_draft_summary.py::TestConcurrentContextWriters`, which forces
> the interleaving with `threading.Event`s instead of waiting for luck. The full evidence
> record — what was observed, what was falsified, and what remained merely inferred until it
> was proven — is at
> [`docs/dev/diagnosis/compose-summary-draft-settle-hole.md`](docs/dev/diagnosis/compose-summary-draft-settle-hole.md).
> Charter **C-7** in force: "X causes Y" is a claim, and no claim is made here without an
> observation behind it.

- **A torn read — real, and fixed, but not the cause.** `Path.write_text` truncates its
  target *before* it writes, so a concurrent reader could see an empty or half-written
  `context_*.json` and its `json.loads` would raise; `POST /draft-summary` then 400'd with
  "Context file unreadable." Measured against a ~1 MB context with concurrent readers:
  **449 torn reads**. All 14 write sites (12 in `blueprints/applications.py`, 2 in
  `hardening.py`) now go through the new `hardening.write_context_atomic` — a unique temp
  file plus `os.replace`, atomic on POSIX and Windows alike. Worth having on its own terms:
  that file is the pipeline's audit trail. It is *not* what broke CI — the instrumented run
  shows the draft POST returning **200**, with **zero** non-2xx `/api/` responses anywhere in
  the tier. Atomic writes close torn **reads**; they do nothing for lost **updates**.
- **The client burned its retry latch before it knew the draft had landed.**
  `_draftSummaryFiredForApp` was set *before* the fire, `if (res.ok)` silently skipped the
  reload on a non-OK response, `catch {}` swallowed throws — and the `finally` drained the
  settle counter regardless. The page therefore reported itself **settled** with the draft
  gone and nothing left to re-fire it. The once-*ever* latch is now an **in-flight claim**,
  released on any non-success path, and the failure is surfaced instead of swallowed.
- **The reporting was blind, twice over — which is why neither cause was ever seen.**
  `tests/ux/conftest.py` asserted on HTTP ≥ 500 and deliberately ignored 4xx as benign
  resource-load noise; the route failed with **400**, so the sentinel looked straight past
  it and the test could only report "the textarea never filled in." Worse,
  `pytest-rerunfailures` reports a test that fails twice and passes on the third attempt as
  a plain `PASSED`, with **no traceback anywhere in the log** — discarding the failures
  outright, and with them the fixture's own captured diagnostic. Both are closed: non-2xx
  `/api/` responses are collected and printed on failure (diagnostic, never an assertion —
  some 4xx here genuinely are benign), and **every rerun attempt now prints its traceback
  and captured output**. `ci.yml`'s flake policy heads itself "HONEST, not masking" and says
  a real regression fails all three attempts — a criterion nobody can apply to evidence they
  never see.

**On the CI red:** `test_compose_summary_draft_autofills_edits_and_persists` was failing
**64% of attempts** and had been for at least 11 runs. `--reruns 2` turned that into a
`0.636³ ≈ 25.8%` predicted red-per-run lottery against **27.3% observed** — so `main` had
not regressed at all; the governance commit that appeared to break it simply lost a coin
flip, and the "green" commit before it had also failed 2 of its 3 attempts. Windows note:
`os.replace` raises `PermissionError` while another handle holds the destination open (and
granting `FILE_SHARE_DELETE` does not lift it — measured), so the writer carries a bounded
retry; POSIX has no such constraint, so it never fires on Linux.

**Verified.** The falsification test flips red→green on the fix. 298 tests across every file
touching the twelve converted routes pass. Nine new `hardening` unit tests pin the transaction —
including a **control** that proves the naive read-modify-write really does lose updates under
the same harness, so the subject's green is not vacuous. And
`test_compose_summary_draft_autofills_edits_and_persists` ran **7/7 with zero reruns**, against
a ~36% pass-per-attempt baseline — a roughly 1-in-12,000 outcome had the bug survived. **What
is not yet met:** those seven runs are *local*. The acceptance bar is a bare `PASSED` with no
`RERUN` across **more than one CI run**, and CI clears that bar, not a local shell.

### Added: evidence-before-mechanism, enforced (charter C-7 + C-8)

An agent spent a day and ~30% of a weekly token budget on the flake above and shipped **no
solution** — it read the code, found a plausible mechanism, and fixed *that*, twice, without
ever instrumenting to see what actually happened. Both fixes were for real defects. Neither
was **the** defect. When it finally added visibility, the cause printed itself in a single
run. `AGENT_FAILURE_PATTERNS.md` §5a/5b/5e already said "instrument first"; the agent read
them and judged they did not apply. **The failure mode is an agent overruling the rule, so
the rule stopped being advice.**

- **Charter C-7 — evidence before mechanism.** A causal claim is a claim under C-0. For a
  defect you cannot reproduce on demand, the **first commit on the branch is the instrument
  or the reproduction — never the fix**; a fix commit must cite the observation that
  identified the mechanism; **green CI is not evidence if the test needed a retry**; and an
  instrument must be scoped **wider** than the hypothesis it tests, because one narrowed to
  your theory will confirm it by hiding its rivals. No escape hatch.
- **Charter C-8 — durable before deep.** The context window is not a durable store. Facts
  that cost work to learn are written to their durable home **in the turn they are learned**;
  compaction is an unannounced data-loss event; a thin context is a handoff trigger, not a
  push-harder trigger.
- **Three enforcement points over one artifact** (`docs/dev/diagnosis/<branch-slug>.md`),
  built into the existing portable enforcement core so they are not Claude-only:
  `require-evidence-before-fix` (PreToolUse) blocks production edits on a `fix/*` branch until
  its `## Observed` section is filled in — `docs/**`, `tests/**` and `*.md` stay writable, so
  the way through is always to write down what you saw; `restore-evidence` (SessionStart,
  including the **`compact`** matcher) replays `## Observed` + `## Falsified` into every fresh
  context, so the evidence survives a compaction — `## Inferred` is deliberately withheld,
  since an unproven mechanism re-injected as context reads as fact within a few turns; and
  `capture-before-compact` (PreCompact) warns the user when a window is about to be discarded
  with nothing captured.
- `tests/test_evidence_gate.py` (21 tests) asserts the **wiring**, not just the logic — a
  guard nobody calls is a comment. Hand-testing caught two defects before they shipped: an
  untouched copy of the diagnosis template **satisfied** the gate (a gate a `cp` can satisfy
  is theater), and the block message mangled on Windows' cp1252 stderr.

### Added: OpenSSF Best Practices badge — passing (100%)

The owner completed the [OpenSSF Best Practices](https://www.bestpractices.dev/projects/13598)
self-certification (project 13598): **passing, 100%**. Added to the README — and only now
that it is real. The badge was deliberately withheld until the certification existed, per
the rule the `unregistered` REUSE badge taught us: a badge that renders a placeholder is a
failing badge, because it asserts a status nobody checked. Verified by fetching the badge
SVG and reading the text it actually renders ("passing"), not by trusting the URL shape.

This also takes OpenSSF Scorecard's `CII-Best-Practices` check off 0.

### Added: release-versioning + release-notes discipline (charter D-7) (`chore/release-governance`)

The project publishes to PyPI and GHCR from a pushed tag, which means a version string
is parsed by pip's resolver before any human reads it. It now gets the same
claims-discipline treatment as any other categorical statement.

- **Semantic Versioning 2.0.0**, with pre-releases on a sanctioned `alpha` → `beta` →
  `rc` ladder: `1.1.0-alpha.1` < `1.1.0-beta.1` < `1.1.0-beta.11` < `1.1.0-rc.1` <
  `1.1.0`. This is deliberately a **subset** of semver — the intersection where semver
  and PEP 440 order versions *identically*. Semver's free-form identifiers
  (`1.0.0-alpha.beta`) are excluded because PEP 440 cannot express them, so pip could
  not order them.
- **A latent publish-time bug, found while writing the rule.** `release.yml` compared
  the pushed tag to the `pyproject` version as **raw strings**. That works only for
  final releases: PEP 440 normalizes `1.1.0-rc.1` to `1.1.0rc1`, so the very first
  pre-release tag would have failed the release job — after the tag was already public.
  The comparison now runs through `scripts/release_version.py`, which normalizes both
  sides and rejects versions outside the ladder.
- **Release notes must disclose fixed vulnerabilities** (from the
  [OpenSSF Best Practices](https://www.bestpractices.dev/) criteria): every released
  CHANGELOG section names each publicly known vulnerability in **Sartor's own code**
  that it fixes and that had a CVE/GHSA assigned at release time — or says there were
  none. Dependencies are out of scope for that statement.
- Gated by `tests/test_release_versioning_gate.py` (21 tests) and the tag-match step in
  `release.yml`. The disclosure gate checks that the statement **exists**, not that it
  is true — no test can verify "we disclosed every CVE we knew about"; the gate makes
  the claim unavoidable in front of a human at release-cut time, which is where the
  judgment belongs.
- New dev dependency: `packaging` (declared, not leaned on as a transitive — a gate
  that depends on an undeclared package is not a gate).

Charter **D-7** is a *default*, which amends in normal branch flow with a written
rationale (the full ceremony is reserved for the C-clauses). Enforcement mechanics:
`docs/governance/enforcement.md` §B2. Two stale rows in that file are also reconciled
to what actually shipped: the **UX/a11y/PDF required check** and the **E-2 machine
badge set** were both still marked "owed — v1.1.0" after landing.

### Fixed: the published docs site rendered no diagrams, no screenshots, and no working cross-links (`fix/docs-site-rendering`)

Three defects on <https://sartor-docs.taketempo.com>, all invisible from the repo
(every one of these links and images is correct *on GitHub* — they only broke in the
L3 projection):

- **Every screenshot was a broken-image glyph.** `next/image` — which fumadocs-ui
  uses to render markdown images — emits `src="/_next/image?url=…"`, a request to
  Next's **server-side** image optimizer. There is no server: `output: 'export'`
  produces static HTML for a traditional host, so all 8 requests 404'd while the
  real files underneath served 200. `images: { unoptimized: true }` makes next/image
  emit the actual `/_next/static/media/*` path. (Same family as the `trailingSlash`
  fix: a server-rendering default a static export can't honor.) This is also what
  made each walkthrough step *look* like it opened with a broken icon — the step's
  screenshot is the first thing in the section.
- **The four architecture diagrams shipped as raw code blocks.** Fumadocs ships no
  Mermaid renderer, so ` ```mermaid ` fences rendered as source. Enabled
  `remarkMdxMermaid` (already present in `fumadocs-core`) and added a client
  `Mermaid` component (`docs-site/src/components/mermaid.tsx`, `securityLevel:
  'strict'`, falls back to the diagram source if a chart fails to parse). Verified
  in a real browser: 4 SVGs render, 0 fallbacks, no page errors.
- **~490 cross-document links were dead, across 33 of the 35 pages.** The L1 docs
  link each other as repo-relative markdown (`[vision.md](vision.md)`), which is
  correct on GitHub and was a *documented non-goal* of the first projection ("a
  follow-up cross-doc link rewrite pass" — `scripts/project_docs_to_mdx.py`). On the
  site, `/docs/vision.md` is not a route. That pass now exists: a link to a projected
  doc becomes its site route (`/docs/vision`), and a link to anything the site
  doesn't carry — source files, `docs/wiki/**`, `CHANGELOG.md` — becomes the GitHub
  URL where that content actually lives. The rewrite is a pure function of the
  projection's own slug map, so it cannot invent a route; the source markdown is
  untouched and still resolves on GitHub. Verified end-to-end on the built export:
  **0 dead `.md` links** (was 490) and **1,406/1,406 internal links resolve**.
  Guarded by 8 new tests in `tests/test_docs_projection.py`.

New `docs-site` dependencies: `mermaid`, `next-themes` (both client-side, docs-site
only — the Python package is unaffected).

### Security: supply-chain hardening — OpenSSF Scorecard 4.9 → (pinned actions, least-privilege tokens, CodeQL, signed releases) (`chore/scorecard-and-docs-voice`)

The repo's first public OpenSSF Scorecard run scored **4.9/10**. Every check that
was fixable in-repo is now fixed; the two that are not (`Code-Review`, `Fuzzing`)
are recorded as reasoned, accepted gaps in
[`docs/dev/keep-ledger.md`](docs/dev/keep-ledger.md) (SC-01 / SC-02) rather than
gamed — a bot approver would raise the number while making the claim false.

- **Token-Permissions (0/10).** `docker.yml` granted `packages: write` at the
  **workflow** level, handing push scope to every job in the file. Moved to the one
  job that pushes the image; the workflow token is read-only again.
- **Pinned-Dependencies (0/10).** Every `uses:` across the five workflows (plus the
  shared composite action) is pinned to a full commit SHA with a `# vX.Y` comment,
  and the `Dockerfile` base image is pinned by digest instead of the mutable
  `python:3.13-slim` tag. Dependabot's `github-actions` ecosystem reads the trailing
  comment, so the pins still get bumped — they're pinned, not frozen.
- **SAST (0/10).** New `.github/workflows/codeql.yml` — CodeQL over both languages
  in the tree (`python` + `javascript-typescript`), on PR, on push to `main`, and
  weekly. Nothing had actually analyzed the source before; `scorecard.yml` only
  *reported*.
- **Vulnerabilities.** `next@16.2.10` pins `postcss@8.4.31` in its nested tree,
  affected by GHSA-qx2v-qp2m-jg93 (moderate: `</style>` isn't escaped when
  stringifying a CSS AST). An npm `overrides` entry lifts the nested copy to the
  patched line — `npm audit` now reports 0 vulnerabilities. `docs-site/` is also
  added to `.github/dependabot.yml` (it was watched only by security alerts, never
  by version updates — which is how it drifted onto a vulnerable transitive).
- **Signed-Releases.** `release.yml` now attests build provenance for the sdist +
  wheel via `actions/attest-build-provenance` (keyless, OIDC — no signing key
  stored), so v1.1.0's artifacts can be verified with
  `gh attestation verify <file> --repo take-tempo-public/sartor`.

### Fixed: the README's REUSE badge rendered a placeholder, not a status

`api.reuse.software/badge/…` rendered **`unregistered`** on the public README — the
repo was never registered with the REUSE API, so the badge asserted a compliance
status nobody had checked. Registered; the repo lints **REUSE 3.3 compliant**
(633/633 files carry copyright + license info, 0 bad licenses). The OpenSSF badge
also moved off the deprecated `api.securityscorecards.dev` host (it now only
302-redirects) to `api.scorecard.dev`, and the stale "these badges don't resolve
until the repo is pushed" comment — false since the repo went public — is replaced
with a note on what each badge sources.

### Changed: documentation voice — a style guide, the wordmark rule, and no disparagement (`docs/dev/doc-style-guide.md`)

- **New [`docs/dev/doc-style-guide.md`](docs/dev/doc-style-guide.md)** — the writing
  contract, sibling to `documentation-architecture.md` (which governs how docs are
  *published*, not how they *read*). Covers the wordmark rule, the no-disparagement
  rule, house voice (anchored to Google's developer-documentation style guide and
  Apple's HIG on writing), and prose-level claims discipline. `AGENTS.md` and
  `CONTRIBUTING.md` point to it, so agents and humans hit it before writing docs.
- **The wordmark rule.** `sartor.` (lowercase, trailing period) is the wordmark and
  is used only standing alone — a logo, UI chrome, a title where the name stands by
  itself. **In sentences it is `Sartor`**, which is what a reader can actually parse.
  Swept across the user-facing doc surface (39 prose occurrences); `docs/wiki/` and
  the review archive still carry the old form and are tracked for a follow-up pass.
- **No characterization of other products.** The README opened by describing what
  "generic AI résumé tools" do wrong — an ungrounded claim about someone else's
  software, in a project whose central discipline is not making ungrounded claims.
  Rewritten to state the three problems from the *candidate's* side (a padded
  history that collapses in an interview; a résumé an ATS can't read; tailored
  copies sprawling into document management) and what Sartor does about them — the
  corpus, sourced from real résumés and grown by clarifying interviews. Says
  strictly more about the product and nothing we can't back.

### Fixed: first public-CI-run remediation — Compose auto-draft race, docs directory index, cross-platform mypy, UX flakes (`fix/ci-first-linux-run`)

Pushing the v1.1.0 debt-burn train to the public GitHub repo ran CI on **Linux**
for the first time (the workflows were committed but latent while the repo was
private). This branch fixes what that first real run surfaced — plus a
user-facing Compose race the CI load exposed, and a docs-hosting bug.

- **Compose positioning-summary auto-draft could get stuck empty (user-facing).**
  The Compose background cascade (`static/app.js`) fired its five context-writing
  reloads (summary-draft, gap-fill, skills-recommend, summary-recommend,
  role-intro-recommend) with a fire-and-forget `loadComposition()`. The
  `_markComposeBgReload(±1)` counter the settle gate reads
  (`data-compose-bg-pending`) therefore decremented the instant a reload hit its
  first `await` — **before** the drafted value repainted the textarea. Under load
  the gate could read "terminal" over the empty "Drafting…" state, and the
  once-only latch meant the draft never re-fired, leaving the summary blank until
  a manual reload. All five auto-cascade fires now `await loadComposition()`, so
  the counter stays raised until the repaint lands. Verified by reproducing the
  flake under 8-core CPU saturation (empty textarea) and confirming 3/3 green
  under the same load with the fix, plus the full 14-test Compose family.
- **docs-site `/docs/` served a raw directory listing instead of the homepage.**
  `docs-site/next.config.mjs` used `output: 'export'` without `trailingSlash`, so
  Next emitted the docs root as `out/docs.html` and left `out/docs/` with no
  `index.html`; a traditional host (DreamHost/Apache) fell through to
  `mod_autoindex`. Added `trailingSlash: true` so every route gets its own
  `index.html` (verified: the build now emits `out/docs/index.html`, and
  `out/docs.html` is gone).
- **Cross-platform mypy (full-strict roster).** `onboarding/review_cli.py` guarded
  a win32-only `ctypes.windll` block behind `sys.platform`, which mypy narrows per
  `--platform` → unreachable → hard error on Linux; guard with `os.name` +
  `cast(Any, ctypes)`. `evals/grounding_signals.py` carried
  `# type: ignore[method-assign]` comments used on Windows but **unused** on Linux
  (`warn_unused_ignores`) — annotate the monkeypatched class `Any` so no ignore is
  needed on either platform.
- **UX/a11y flakes on the shared CI runner.** axe scanned the help modal mid
  opacity-fade (false color-contrast fail) → emulate `prefers-reduced-motion` in
  the axe suite; the pipeline-board and corpus-scroll tests asserted on snapshot
  reads that raced async row/card loads → assert auto-retrying
  `expect().to_have_count`.
- **OpenSSF Scorecard.** `ossf/scorecard-action@v2` doesn't resolve (no floating
  `v2` tag) → pinned `@v2.4.3`.
- **numpy 2.5 broke `mypy .` on py3.12/3.13.** numpy 2.5's stubs use the PEP 695
  `type X = …` statement, which mypy rejects under `python_version = "3.11"`
  ("Type statement is only supported in Python 3.12 and greater"). Capped
  `numpy<2.5` — a type-checking pin, not a runtime need (numpy 2.5 also dropped
  Python 3.11, so the py3.11 job already resolved 2.4.6 and passed). Lift when the
  supported-Python floor moves to 3.12 and `[tool.mypy] python_version` can follow.
- **Enforcement-equivalence test failed on CI's shallow clone.**
  `tests/test_enforcement_core.py` does `git show <OLD_SHA>:…` archaeology that
  needs full history, but `actions/checkout` defaults to depth 1. Set
  `fetch-depth: 0` on the quality job + a fixture skip-guard so the test degrades
  gracefully on any shallow clone instead of hard-failing.
- **Scoped retry for the CI-only compose/skills Playwright flake class.** The first
  real runs on the shared GitHub runner disproved the prior policy's assumption that
  the compose/skills settle-race "structurally cannot reproduce" in CI: across four
  runs a *different* compose/skills subset flaked each time (and a test re-flaked
  despite a correct structural fix) — the runner's own load variance reproduces the
  class. Per that policy's own documented exception for a *characterized* CI-only
  flake, the `ux` tier now runs `pytest -m ux --reruns 2` (reruns only failed tests;
  a real regression still fails all three attempts). The strict `quality`-matrix
  pytest and the deterministic PDF slice are untouched. Owner-authorized 2026-07-12.

`PROMPT_VERSION` untouched (no prompt text changed — the Compose fix is
client-side reload sequencing). One runtime dependency bound tightened
(`numpy<2.5`, a type-checking pin) and one dev dependency added
(`pytest-rerunfailures`, CI-`ux`-tier retry only); no migration change.

### Added: unified quality-gate wrapper + CI hygiene batch (PX-55/PX-43, `ci/portable-enforcement`)

v1.1.0 debt-burn Lane HARD (relaunch, reduced scope). Lands the two SAFE
items from this lane's scope; the L2 hook-re-home + PX-37 dispatcher are
DEFERRED to an owner-present session (see Carry-forward ledger).

- **PX-55** — new `scripts/gate.py`: one wrapper running `ruff check .` +
  `ruff format --check .` + `mypy .` + `pytest` (the same four steps, same
  order, as `.github/workflows/ci.yml`'s `quality` job), each print-labelled
  and stopping at the first failure. `AGENTS.md`, `CONTRIBUTING.md`, and
  `ci.yml` now invoke `python -m scripts.gate` instead of independently
  restating the step list — a single definition of "gate green" instead of
  three that can silently drift (the exact drift this closes: `AGENTS.md`'s
  close-out checklist and Testing section both omitted the `ruff format
  --check` step CI already ran). Invokes each tool via `sys.executable -m
  <tool>` rather than the bare console-script name, matching
  `ruff_changed.py`'s existing portability rationale (console scripts are
  not guaranteed to be on `PATH` for every install).
- **PX-43** — CI hygiene batch on `.github/workflows/`: (1) a top-level
  `concurrency:` group (`cancel-in-progress: true`) on `ci.yml` so a
  force-push/rapid follow-up cancels the previous push's in-flight run
  instead of letting it finish (F-tci-04); (2) `eval-smoke`'s duplicated
  `actions/setup-python` + `pip install -e ".[dev]"` block factored into a
  new composite action, `.github/actions/setup-python-env/`, now called by
  both `quality` and `eval-smoke` (F-tci-06); (3) `release.yml`'s `dist`
  artifact upload gains `retention-days: 30`, matching the existing
  `docs-deploy.yml` precedent (F-tci-10); (4)/(5) one-line owner-decision
  comments recording **fail-fast OFF** (`ci.yml`, `quality` job) and **keep
  the arm64 build** (`docker.yml`) — both per `RELEASE_ARC.md` dec 13. Does
  NOT change which checks are `required` (a `[HUMAN]` GitHub branch-protection
  step, unrelated to this branch).

No prompt/dep/migration change; `PROMPT_VERSION` untouched. These workflow
files only run on GitHub (the remote is private, CI not yet triggering) —
zero local runtime risk.

### Fixed/Added: diagnostics-DX round-2 batch — #3/#7/#9/#10/#17, CW-117, RH-1/RH-2, #1-scope (`feat/diagnostics-dx`)

v1.1.0 debt-burn Lane DX: closes out the still-open items from
[`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`](docs/dev/reviews/2026-07-diagnostics-round2-findings.md)
and [`docs/dev/reviews/2026-07-e2e-run-health-review.md`](docs/dev/reviews/2026-07-e2e-run-health-review.md).

- **RH-1 (grounding-signal persistence, highest value)** — `evals/annotation.py`
  gains `patch_grounding_scores_by_text`, wired into `evals/runner.py:run_suite`:
  a `--suite real` eval run's grounding signals now persist into the fixture's
  `annotations.json` (matched by normalized bullet text — a `--suite real` run
  grades a freshly-generated résumé, not the bootstrap's deduped cluster
  representatives, so index-alignment doesn't apply here the way the existing
  "Score grounding" button's `_patch_annotation_scores` uses). Before this fix,
  scores landed in every JSONL result record but never made it back to the
  ground-truth file the Annotate tab edits.
- **RH-2 (0-byte-run guard)** — `run_suite` now raises (and deletes the empty
  file) instead of silently returning a "0 pass / 0 fail" result when a run's
  fixture loop wrote ZERO result records (every matched fixture failed to load
  or grade); `main()` maps it to exit 1 like the other run_suite failure modes.
- **#3** — the Tuning tab's real-corpus-seed section cross-links the Annotate
  tab's "Export seed" button (switches tabs, opens step ①, focuses it) instead
  of only pointing at the CLI.
- **#7** — the `should_omit` checkbox gets the `.title` tooltip the verdict
  `<select>` already had, and relabels to "Also list under Omissions
  (independent of verdict)."
- **#9** — the Annotate editor's `state.doc` now debounce-snapshots to
  localStorage on every edit (restored on reload, cleared on a successful
  Save), and a failed Save's `bullets[N]`/`skills[N]` validation error scrolls
  to + briefly highlights the named item.
- **#10** — the eval/tune/bootstrap run controls get a real `<progress>` bar
  driven by the SSE's existing `index`/`total` payloads, replacing reliance on
  the plain-text progress line alone.
- **#13** — the grounding-score button (a single blocking scorer call with no
  per-item granularity) gets an indeterminate `<progress>` bar — a coarse busy
  signal, deliberately not granular (owner: acceptable, minimal).
- **#17** — the doc-grounded assistant is ported onto `/_dashboard`: `static/
  assistant.js` now self-promotes its own `_consumeSSE`/`esc` (guarded — never
  overrides an already-loaded `app.js` copy) so it works without the wizard's
  `app.js`; `dashboard.html` supplies a tiny `currentUser` shim, ports the
  `#assistantModal` block, and defaults its "Dev mode" checkbox CHECKED (the
  wizard's copy defaults unchecked). No backend change —
  `blueprints/assistant.py:ask()` already treats `username` as optional.
- **CW-117** — added Playwright coverage for the two hand-rolled SSE pumps
  (bootstrap, grounding-score) that independently acquire/release the shared
  paid-run lock; previously only the eval `_closed` path was regression-tested.
- **#1-scope** — verified already correct at this branch's base (seed-export
  never took the lock); additionally gave the dynamically-created "Run this
  fixture" button a stable id so the lock disables it too while another paid
  run is in flight.
- **Content cluster #2/#4/#5/#6/#16 (DRAFT — owner-review-before-merge)** — a
  handful of new field-level `.title` tooltips (Tuning's constant/slug
  pickers, the bootstrap JD name/text inputs) and one clarifying sentence
  added to the Annotate tab's help copy describing the new #9 draft behavior.
  This is a small down payment, not the full field-level authoring pass the
  finding calls for.

### UX Cohesion Epic — design-system pass (`feat/ux-cohesion`, v1.1.0 Wave 2 Lane UX)

The design-system remainder of the `docs/dev/reviews/2026-07-ux-round2-findings.md`
epic (Wave A's decision-free quick wins already landed on `main`). Owner decisions 1–7;
see `docs/dev/RELEASE_ARC.md` "UX Cohesion Epic" for the registration.

- **Sentence case app-wide (dec 1, G5)** — retired ALL-CAPS chrome. `static/style.css`:
  all `text-transform: uppercase` rules flipped to `none` app-wide (39 of 40 — the one
  exception, `.preview-rendered h2`, governs the RENDERED RÉSUMÉ DOCUMENT's own section
  headers inside the live preview, a document-typography choice, not app chrome; kept
  uppercase deliberately). `static/app.js` + `templates/index.html`: every hardcoded
  ALL-CAPS button/badge/label string converted to sentence case (`PENDING`→`Pending`,
  `+ ADD TITLE`→`+ Add title`, `← BACK`→`← Back`, etc.) — many were literal caps typed
  in source (not CSS-driven), left over from the pre-sartor. "LCARS era" alongside
  already-sentence-case newer code; three `.toUpperCase()` call sites (application
  status chips, the Compose "find more bullets" toggle) switched to the existing
  `_toSentence()` helper so they stop force-casing dynamic values (including, in one
  case, the user's own company name).
- **One ~150ms modal fade (dec 2, G1)** — `.cb-modal`/`.cb-modal-content` in
  `static/style.css`: replaced the open-only 120ms `cb-modal-in` keyframe (no close
  fade at all) with a symmetric `transition`-based fade driven by the same `.hidden`
  class toggle every modal already uses — `visibility` (not `display`) carries the
  hidden state so it's transitionable; a `display:flex!important` on `.cb-modal.hidden`
  defeats the global `.hidden{display:none!important}` utility rule that would
  otherwise snap it invisible before the fade could play. New `--t-modal: 150ms` token.
  Covers every `.cb-modal` surface app-wide (helpModal, appDetailModal, formModal,
  errorModal, assistantModal, changesModal, editModal, cbConfirmModal,
  refinementScopeModal, diagnosticsModal) with one change; the Settings drawer's
  distinct slide-in animation was left alone (different metaphor).
- **Phosphor icons, vendored inline SVG (dec 3, G3/Co1)** — skills-icon priority: a new
  `.skill-chip` component (glyph-on-colored-background badge + name, in a
  category-tinted pill) now renders on every skill row (Career Corpus editor, Compose
  skill list, pending-review and denied lanes in both). SVGs are vendored inline
  (Phosphor Icons, MIT license, phosphoricons.com — fetched from
  `raw.githubusercontent.com/phosphor-icons/core`, "duotone" weight), not a new
  npm/pip dependency. **Glyph→concept mapping is owner-review-before-merge** (see the
  branch report): language→code, framework→stack, platform→cloud,
  methodology→flow-arrow, domain→globe, uncategorized/unrecognized→gear (category is
  free-text; unrecognized values fall back safely). New color tokens `--violet-soft`,
  `--neutral-soft`.
- **State-communication two-tier (dec 4, G2/G4/G8)** — (a) the "scrape/fetch" profile-
  content action (`fetchProfileContent`, PX-02) now drives `_setBusy` like
  analyze/generate/clarify/cover-letter do (it previously had only a local status
  line); the Compose LLM actions (tailor/suggest skills, draft summary, draft
  gap-fill) were audited and deliberately left OFF `_setBusy` — they already have
  Compose's own equivalent always-visible "Updating suggestions…" chip
  (`_markComposeBgReload`/`#composeBgChip`), and adding the app-wide "don't navigate
  away" banner to every quick sequential Compose click would be louder than the
  "subtle" mandate intends. (b) every small in-flight button (the four Compose actions
  above, "Suggest skills from my corpus", "Get follow-up questions",
  "+ Generate cover letter", the profile-fetch button) now gets a shared subtle pulse
  (new `.btn-pending` class + `_setBtnPending()`/`_clearBtnPending()` helpers in
  `static/app.js`) on top of its existing disable + "…"-style relabel — two of these
  (iterate-clarify, cover-letter generate) previously disabled with NO relabel at all.
- **Save toast (dec 5, Co5)** — Compose's debounced composition autosave
  (`_scheduleCompositionSave`) toasted only on FAILURE before; it now also toasts
  "Saved" on success, using the same `_toast()` idiom every other save confirmation in
  the app already uses.
- **Skills redesign (dec 6, C1)** — **data-model change:** `DELETE /api/skills/<id>`
  (`blueprints/corpus/skills.py`) previously hard-deleted a denied (pending,
  `llm_proposed`) suggestion, freeing its name for a future suggest-pass to silently
  re-propose it — the opposite of "denied". It now ALWAYS soft-tombstones
  (`is_active=0`, `is_pending_review=0`, row kept), unifying deny and retire into one
  outcome: the name stays excluded from every future dedup scan (suggest-from-corpus
  already scans all rows regardless of `is_active`), and it is reversible — `PUT
  /api/skills/<id> {"is_active": true}` un-denies it (new field on `update_skill`,
  mirroring the existing title/bullet Restore idiom). The Career Corpus tab's Skills
  editor gained a collapsible "Denied / retired skills" lane (new
  `_renderDeniedSkillRow` + `#skillsEditorDeniedDetails`) with a Restore button, plus a
  reusable `.corpus-collapsible` wrapper (a generalized `.analysis-details`) applied to
  both the Corpus and Compose bounded skills lists (C2 landed the scroll-bounds only;
  this adds the deferred collapsible toggle on top).
- **Compact prior-application cards (dec 7, G7)** — `_renderApplicationCard` now
  renders ONLY a summary line (title/company) + a meta line (status · pending-review
  count · date); the status-transition row (Mark submitted / Got interview / …) and
  the retire/restore admin row moved into the existing click-to-open detail modal
  (`_showApplicationDetail`), which also gains a collapsed-by-default JD snippet and a
  per-run status list (`ats_roundtrip_status` — the closest existing concept to
  "scores"; no new scoring concept was added). `GET /api/applications/<id>` now
  returns `is_active` (needed by the modal to pick Retire vs Restore) — a new field on
  the existing `ApplicationDetail` OpenAPI model, not a new route.
- **PX-51 (style.css duplicate-cascade collapse) — DEFERRED, not landed.** Flagged
  HIGH RISK in the branch brief; several of the decisions above (1, 2) already had to
  edit rules living inside the ~780-line "restyle" duplicate block this item would
  collapse, and attempting a full selector-by-selector merge on top of those
  in-flight edits risked destabilizing everything else in this branch. No functional
  effect from deferring it — the duplicate-cascade "later rule wins" footgun still
  works correctly, just remains unre-architected. Left for a follow-up branch.

### Docs: agent-contract trim + corpus/pipeline dedup + affirm-and-protect notes (`docs/efficiency-px`)

2026-07 efficiency review doc-only lane (PX-45, PX-49, PX-56 + decision-14 doc-only
half of PX-47): compressed the ~90-line CLAUDE.md skill/subagent catalogs to a
directory pointer at `commands/`/`agents/`, folding the compliance-witness-only facts
into its own frontmatter; pointer-ized AGENTS.md's duplicated deterministic-boundary
list and corrected the cache-miss claim to cover all `system_prompt`-override call
sites in `analyzer.py` (16, not 11); reduced the corpus/pipeline mechanics restated in
`vision.md` and `docs/PRODUCT_SHAPE.md` to a pointer + one line each, with
`docs/architecture.md` as the single canonical home (charter D-5); added
`docs/dev/reviews/2026-07-efficiency/keep-notes.md` (do-not-regress notes: Haiku
call-kinds' zero-error record, deliberate eval prompt-version anchoring, Linux-only CI
as a decision-with-a-revisit-trigger, D-5 re-affirmation now due post-8.6-ingest); and
documented (not re-pinned) the dated-Haiku-vs-undated-Sonnet subagent model-pin split
in `docs/dev/decisions.md`. AGENTS.md remains a complete standalone contract — no
guardrail moved to a Claude-only file.

### Fixed — freshness-scrub: wiki-freshness `docs-site/` over-count + doc drift (`chore/freshness-scrub`)

Docs/tooling-only; no code path outside `scripts/wiki_freshness.py` touched, no dep/migration/prompt change.

- **Wiki-freshness gate `docs-site/` exclusion** (Carry-forward ledger #1). `scripts/wiki_freshness.py:drift_count`
  excluded only `docs/wiki/` from the merge-blocking drift count; the Fumadocs static-export tree under
  `docs-site/` is an L3 *projection* of the wiki (like `docs/wiki/` itself), not a wiki source, so its churn
  must not count as drift. Now excludes `docs-site/` alongside `docs/wiki/`; new
  `tests/test_wiki_freshness_gate.py::TestWikiFreshnessUnit::test_docs_site_changes_excluded_from_drift`
  pins the exclusion.
- **Baked-in absolute-path scrub.** Genericized out-of-project absolute paths left in tracked docs:
  `docs/dev/RELEASE_ARC.md` (`C:\Users\iam\...` reference-doc rows → `%USERPROFILE%\...`),
  `docs/dev/ORCHESTRATION_PLAYBOOK.md` (`C:\Dev\sartor-e2e` → `../sartor-e2e`), and a comment in
  `tests/test_enforcement_core.py`. Path genericization only — no reword of sign-off-gated prose.
- **Owner-handle/repo scrub, files-only** (no git-history rewrite). `amodal1/sartor` → `take-tempo-public/sartor`
  in `CHANGELOG.md` (this file's own historical entries) and `docs/dev/RELEASE_CHECKLIST.md`; `amodal-open` →
  `take-tempo-public` in `docs/dev/decisions.md` and `docs/dev/kit-adoption-design.md`. Left untouched:
  `pyproject.toml`'s `authors = [{ name = "amodal1" }]` (author attribution, owner decision separately) and
  everything under `docs/dev/reviews/**` (pinned historical review artifacts).
- **Stale `Dockerfile` comment.** The "wheel does not yet ship those data dirs" follow-up landed
  (`fix/packaging-install`, Carry-forward ledger #2) — the wheel now ships templates/static/personas/wiki via
  package-data. Comment reconciled: the image still installs editable from `/app` (unchanged behavior), but
  the wheel-can't-ship claim is no longer accurate and has been corrected.

### Changed: packaging floor — installed-app data dir + Python 3.11 (`chore/packaging-floor`)

Closes the two residual follow-ups left open by `fix/packaging-install`
(Carry-forward ledger #2, residuals (i) and (ii)):

- **Installed-app user-data dir.** On a bare `pip install sartor && sartor`
  (a real non-editable wheel), `Config.base_dir`'s default and
  `dashboard/routes.py`'s telemetry/eval-results root used to resolve into
  `site-packages/`, so user data (`configs/`/`resumes/`/`output/`) and
  telemetry (`logs/llm_calls.jsonl`, `evals/results/`) would land there
  instead of a proper per-user directory. `config._default_base_dir()` now
  resolves, in order: the `SARTOR_HOME` env var if set; the repo root,
  unchanged, for a dev/editable checkout; otherwise the platform user-data
  directory via the new `platformdirs` dependency
  (`%LOCALAPPDATA%\sartor` on Windows, `~/.local/share/sartor` on Linux,
  `~/Library/Application Support/sartor` on macOS). `dashboard/routes.py`'s
  `PROJECT_ROOT` now shares this same resolution instead of an independent
  `Path(__file__)`-relative computation. `Config.bundled_personas_dir` falls
  back to the packaged-data resolver (`config._package_dir`) when `base_dir`
  is at its default, so the shipped persona templates still resolve
  correctly once the default no longer coincides with `site-packages/`; an
  explicitly-overridden `base_dir` (test isolation) is unaffected.
  `Config.ensure_dirs()` now creates its three directories with
  `parents=True`, since a fresh platform data directory may not exist yet.
  New dependency: `platformdirs>=4.0,<5.0`. **Still open:** `analyzer.py`'s
  own `LOG_DIR` (what actually writes `llm_calls.jsonl`) is a separate,
  still-`Path(__file__)`-relative global, out of this fix's anchored scope —
  flagged as a new small follow-up.
- **Python floor `py310` → `py311`.** `[tool.ruff] target-version` and
  `[tool.mypy] python_version` now match the real floor
  (`requires-python = ">=3.11"`, already correct; CI already tests only
  3.11-3.13). The `target-version` bump surfaces new `UP017`/`UP042`
  pyupgrade findings plus `I001` import-sort drift (from `tomllib`'s
  stdlib reclassification) in files this branch does not otherwise touch —
  scoped, temporary `per-file-ignores` entries keep `ruff check .` green
  without an unplanned whole-tree autofix; each is tracked for a dedicated
  follow-up cleanup pass.

### Fixed: Compose-route N+1 + `is_active` index gap (PX-38, `perf/db-baseline`)

- **`get_application_composition`** (`blueprints/applications.py`) selectinloads
  `Experience.bullets`+`Bullet.tag_links`, `Experience.titles`+
  `ExperienceTitle.tag_links`, and `Experience.summary_items` on its top-level
  `Experience` query — was three separate per-experience query families
  (`O(experiences)` each: bullets, titles, and the `ExperienceSummaryItem`
  filter/sort), now three fixed selectin batches regardless of experience
  count. Mirrors the proven `list_applications` `selectinload(Application.runs)`
  fix. **Measured (this repo, `tests/test_application_routes.py`
  `test_avoids_n_plus_1_query_growth`): 2 experiences → 6 experiences was
  17 → 37 SQL queries before the fix (+5/experience); 12 → 12 after (flat).**
- **`db/models.py`** — `ix_application_candidate_status_updated` gained
  `is_active` (new column order: `candidate_id, is_active, status,
  updated_at`) — the index omitted the column `list_applications`' default
  (no `?status=`) path filters on every call. Migration
  `db/migrations/versions/0015_application_index_add_is_active.py` uses plain
  `op.create_index`/`op.drop_index` (no `batch_alter_table` — `application` is
  a CASCADE parent of `application_run`; index rebuilds are metadata-only DDL,
  carrying none of that rebuild's row-loss risk). Verified zero row loss
  upgrading 0014→head and downgrading back, both directions, on a scratch DB
  seeded with an application + run + run child
  (`tests/test_migrations_data_safety.py::TestApplicationIndexAddIsActive`).

### Documented: real-corpus latency baseline population-era labeling (PX-39)

- `docs/dev/perf/PERFORMANCE_HISTORY.md` gained a "Population eras" section
  distinguishing three eras — pre-split (ended 2026-06-01, DEFUNCT),
  split+Sonnet-4.6 (2026-06-01→2026-07-05, DEFUNCT — includes the 69.7s p50/
  84.6s p95 real split-pair figure previously at risk of being cited as
  "current") and split+Sonnet-5 (2026-07-05→present, CURRENT) — so future
  readers don't seed false-alarm comparisons against a retired population.
  Cites the already-committed Sonnet-5 synthetic anchor pipeline p50s from
  `evals/results/baseline_v1.json` (68.7s/80.7s/80.5s across the three
  fixtures) as the only Sonnet-5 measurement available so far, and leaves an
  explicit **open item**: a real-corpus Sonnet-5 p50/p95 baseline could not be
  captured from this branch's isolated worktree (no `.api_key`/
  `ANTHROPIC_API_KEY` present) — method + reproduction command documented for
  the next run with credentials, no numbers fabricated.

### Fixed: CONTRIBUTING.md pytest double-run; documented the honest fast-lane numbers (PX-44)

- `CONTRIBUTING.md`'s PR checklist told contributors to run `pytest` (green)
  *and* `pytest -m ux` (green) as two separate steps — since a plain `pytest`
  already carries no marker filter and executes the UX tier once (when
  Chromium is installed), the second invocation silently re-ran the same
  tests. Collapsed to one `pytest` bullet with the corrected guidance.
- New `docs/dev/perf/TEST_SUITE_PERFORMANCE.md` — the durable home for the
  idle-measured fast-lane numbers (full 308.9s / fast-lane 163.1s / slow-UX
  248.0s, `docs/dev/reviews/2026-07-efficiency/verification-log.md`
  addendum) plus a fixture-scoping PROBE: a static count found 46 of 118
  non-UX test files (658 of 1,868 test functions, ~35%) build a fresh Flask
  app + run the full 15-revision alembic chain at function scope, with only
  1 non-function-scoped fixture in the entire non-UX suite. **The
  fixture-scoping refactor itself is DEFERRED** (written note in the new
  doc) — it's a cross-cutting change to test-isolation guarantees across
  ~40% of the suite, landing mid-train alongside six concurrent lanes;
  follow-on branch `test/fixture-scoping` recommended, piloted on one
  low-risk file first.

## [1.0.9] — 2026-07-10

### Added: spectree/OpenAPI Layer B, Phase 1 — spec emission only (`feat/spectree-openapi-emit`)

Wires [`spectree`](https://spectree.readthedocs.io/) into the Flask app to
**emit** an OpenAPI spec — decorator-only, additive, zero request-validation,
zero route-body edits. This reconciles the stale drift flagged in the
`feat/fumadocs-site` docs-site lane below and in `docs/dev/RELEASE_ARC.md`
Phase 4.9 (both claimed spectree "landed in v1.0.8" / "pulled into v1.0.8" —
verified FALSE at the time; it had never been wired). It actually lands here,
in **v1.0.9**, as **Phase 1 only** (spec emission — Fumadocs *rendering* that
spec into a hosted HTTP-API reference page, the rest of kit Decision 2a's
Layer B, remains a separate, later branch).

- **New `web_infra/openapi.py`** — the shared `spec = SpecTree("flask", ...)`
  instance (`mode="strict"` so only spectree-decorated routes appear in the
  emitted spec, not all ~90 undecorated ones too; `annotations=False` since
  every call site passes `resp=`/`skip_validation=` explicitly rather than
  typed view-function params) plus the Pydantic response models for the 5
  decorated routes, styled after `analyzer.py`'s permissive-base convention
  (`model_config = ConfigDict(extra="allow")`).
- **Decorated exactly 5 read-only GET routes** with
  `@spec.validate(resp=Response(HTTP_200=<Model>), skip_validation=True,
  tags=[...])`: `users.list_users`, `users.get_config`,
  `corpus.experiences.list_experiences`, `applications.list_applications`,
  `applications.get_application`. **Zero edits to any route function body** —
  the load-bearing safety property; `list_experiences`/`list_applications`
  model their bare-array-or-needs-onboarding-object success/empty union via a
  `RootModel[list[X] | Y]`, safe to leave imperfect because
  `skip_validation=True`.
- **Decorator ORDER correction vs. the lane's original brief:** `@spec.validate`
  must be the decorator closest to the function (applied first), with
  `@<bp>.route(...)` as the outer decorator — the reverse order silently drops
  the route from the spec (Flask's `url_map` captures whichever function object
  existed at `@<bp>.route(...)` decoration time; the wrong order registers the
  *undecorated* function, so spectree's `mode="strict"` never sees its
  `_decorator` marker and excludes it). Verified empirically; documented in
  `web_infra/openapi.py`'s module docstring.
- **New `scripts/generate_openapi_spec.py`** — mirrors
  `scripts/project_docs_to_mdx.py`'s standalone-generator style: builds its own
  throwaway `create_app()` instance (temp-dir `Config`, no real
  `configs/`/`resumes/`/`output/` writes), calls `spec.register(app)` on it,
  and writes the cached `spec.spec` dict as pretty JSON to
  `docs-site/openapi.json` — gitignored (a build artifact CI regenerates; that
  CI wiring is a separate, later branch's job, per the docs-site lane's own
  division of labor).
- **New dependency**: `spectree[flask]>=2.0,<3.0` (`pyproject.toml`). Ships its
  own `py.typed` marker — no `[[tool.mypy.overrides]] ignore_missing_imports`
  entry needed.
- **Tests**: `tests/test_openapi_spec.py` — a parity assertion per decorated
  route (status + JSON body unchanged) plus a generator test asserting the
  built spec contains all 5 expected paths. `tests/test_route_containment_gate.py`
  and the `route-security-lint` hook both stay green with **zero edits** to
  either registry — the falsifiable proof the security gate stayed untouched.
- `docs/dev/RELEASE_ARC.md`: reconciled the Phase 4.9 / WS-3 "pulled into
  v1.0.8" claims to point at this branch's actual v1.0.9 Phase-1 landing.

### Added: spectree/OpenAPI Layer B, Phase 2 — render the spec in Fumadocs (`feat/spectree-fumadocs-render`)

Renders the `docs-site/openapi.json` spec (Phase 1, above) as an **API
reference** section of the hosted Fumadocs static-export site, and wires CI to
regenerate + render it on every deploy. Completes kit Decision 2a's Layer B.

- **New deps** (`docs-site/package.json`): `fumadocs-openapi@^11.1.1` +
  `shiki@^4.3.1` — the version compatible with this site's pinned
  `fumadocs-core@16.11.2` / `fumadocs-ui@npm:@fumadocs/base-ui@16.11.2`
  (fumadocs-openapi 11.1.1's own peer range is `fumadocs-core@^16.10.0` /
  `fumadocs-ui@^16.10.0`); confirmed via the npm registry before installing,
  per this branch's STOP-point instruction not to force a fumadocs major bump.
- **New `docs-site/scripts/generate-api-docs.mjs`** — a standalone generator
  (mirrors `scripts/generate_openapi_spec.py` / `scripts/project_docs_to_mdx.py`'s
  "builds its own instance" style): reads `docs-site/openapi.json`, calls
  `createOpenAPI()` + `generateFiles({ per: 'operation', groupBy: 'tag', meta:
  true })`, and emits MDX under `content/docs/api-reference/` grouped by the 3
  spectree route tags (`users`/`applications`/`corpus`), each with its own
  generated `meta.json`. Also appends exactly ONE nav entry (`"api-reference"`)
  to the already-projected `content/docs/meta.json`'s `pages` array (the
  low-risk nested approach — this script never edits
  `scripts/project_docs_to_mdx.py`'s own L1 ordering logic).
- **Reference-only rendering, by design**: `docs-site/src/components/api-page.tsx`
  sets `playground: { enabled: false }` on `createOpenAPIPage()` — replaces the
  interactive "try it" request builder with a static method+path badge.
  Parameters, request/response schemas, TypeScript definitions, and
  multi-language code-usage samples still render (all static, no live fetch).
  A live playground would fire cross-origin requests at each visitor's own
  `localhost:5000`, which is wrong for a static site documenting a local
  desktop app — no proxy route was added, keeping the site's `output: 'export'`
  static-export commitment intact.
- **Render wiring**: `docs-site/src/lib/openapi.ts` (the runtime
  `createOpenAPI()` instance, consumed via `openapi.preloadOpenAPIPage(page)`
  at Next static-build time — resolved during `next build`'s
  `generateStaticParams()` prerender, not at request time, so it stays
  compatible with static export); `docs-site/src/app/docs/[[...slug]]/page.tsx`
  adds an `OpenAPIPage` entry to its MDX `components` map; `docs-site/src/lib/source.ts`
  adds `openapiPlugin()` (method-badge page-tree decoration only); `global.css`
  imports `fumadocs-openapi/css/preset.css`.
- **`.github/workflows/docs-deploy.yml`**: added a `python
  scripts/generate_openapi_spec.py` step and a `npm run gen:api-docs` step,
  both before `npm run build` — both are pure functions of `main` HEAD
  (deterministic, no LLM, no network), so "merge = publish" still holds.
- **`.gitignore`**: `docs-site/content/docs/api-reference/` — a build
  artifact like the L1-projected MDX, same rationale.

### chore: mypy `--strict` tooling slice — `scripts/` + `evals/` + `db/migrations/versions/` (`chore/mypy-strict-tooling`)

- **Decision-7 amended** (kit-adoption-design.md §3/§6, owner-directed v1.0.9
  pull-in, 2026-07-10): the mypy `--strict` ratchet's exempt set narrows from
  `tests/`/`evals/`/`scripts/`/`db/migrations/versions` to **`tests/` only**.
  Fixed the 72 measured `mypy --strict --warn-unreachable` errors this
  surfaced (22 `scripts/` + 44 `evals/` + 6 `db/migrations/versions/`) —
  entirely annotation-only: parametrized bare generics (`dict` →
  `dict[str, Any]`, etc.), added missing param/return annotations, and a
  handful of `cast(...)`-wrapped `no-any-return`s on `json.loads(...)`
  boundaries. Zero behavior change, no prompt touched.
- `pyproject.toml`: added `scripts.*`, `evals.*`, `db.migrations.versions.*`
  to the strict `[[tool.mypy.overrides]]` roster (now 33 entries).
  `db.migrations.versions.*` is its own explicit glob entry (not folded into
  a `db.*` wildcard) — the alembic mako template already emits strict-clean
  scaffolding, so the friction on future autogenerated revisions is
  negligible.
- `tests/test_mypy_strict_roster_gate.py`: `_EXEMPT_PREFIXES` narrowed to
  `("tests/",)`; the migrations/versions-stays-permissive guard rewritten
  into its premise-reversal (`test_migrations_versions_is_strict_rostered`
  now asserts the tree **is** rostered); floor thresholds re-verified against
  the new measured counts (33 roster entries, 131 non-exempt production
  modules).
- `tests/` stays deliberately permissive — a separately-scoped, much larger
  burn (~3,252 errors measured) is deferred per owner direction.

### Docs: dev-tier depth verify (WS-B) + close the `docs/readme-icp-ladder` row (`docs/dev-home-depth-wsb`)

- **WS-B verify-first pass** against settled v1.0.8 code (v1.0.9 Phase 6, item 2)
  over the three dev-tier homes the README's "For developers" ICP rung points
  into (`docs/system-model.md`, `docs/dev/memory-architecture.md`,
  `docs/architecture.md`). Filled three genuine, narrowly-scoped gaps found
  during verification (no invented claims — each grounded in code read at
  HEAD):
  - `docs/architecture.md` — added a "Typed contracts (pydantic-in-the-loop)"
    paragraph to §LLM routing + cost: the README claims `pydantic`
    `model_validator`s enforce semantic rules and a validation failure is fed
    back as a structured retry, but the doc had **zero** mentions of
    `pydantic`. Documented the mechanism against `analyzer.py`'s actual
    `_LLMResponse`/`HiddenQualityItem`/`ClarifyResponse.enforce_composition_rules`
    (`analyzer.py:152/158/240`) and the `_parse_or_retry()` retry loop
    (`analyzer.py:1405`, `1452`-1474).
  - `docs/dev/memory-architecture.md` — the "Reuse boundary / extraction
    contract" section still called the `recall/` import boundary-lint "a
    candidate for its own boundary-lint," but it shipped in Sprint 7.4
    (`tests/test_recall_boundary.py`, plus the literal-leak guard
    `test_recall_sources_no_hardcoded_roots`). Updated to state it is
    **built** and enforced by construction, matching the README's "enforced,
    not narrated" claim.
  - `docs/system-model.md` — the "Where it lives" table/prose still framed
    `app.py` as "the web layer" (pre-8.3a-h; `app.py` is now a 296-line
    composition root with zero routes — all 93 routes live in `blueprints/`)
    and called the wiki "planned" (`docs/wiki/` ships 36 pages; the `recall/`
    Memory substrate is also unlisted). Updated both the Production and
    Memory rows/prose to the settled state.
  - **WS-E unification** (recursive grounding + the shared `user`/`dev`
    audience plane) — confirmed already folded into
    `docs/dev/documentation-architecture.md`, and `docs/system-model.md`
    already carries the "one law" framing it cites (§"The one law"). No
    edit needed (confirm-only, per the design doc).
- **Closed the `docs/readme-icp-ladder` Phase-6 sequence row.** Its content
  (`323bf6c`/`996d1c9`) and the governance `DOC-STATUS(governance-boundary)`
  reconcile are already on `main` and the flag reads RESOLVED (PX-19/PX-20).
  Marked DONE/struck-through in
  [`docs/dev/RELEASE_ARC.md`](docs/dev/RELEASE_ARC.md) (Phase 6 branch list +
  the numbered v1.0.9 sequence) and logged the resolution in
  [`docs/dev/RELEASE_CHECKLIST.md`](docs/dev/RELEASE_CHECKLIST.md)'s
  Carry-forward ledger.
- Docs-only: no product code, no new deps, `PROMPT_VERSION` untouched.
### Docs: paged.js render-engine design spike (`spike/pagedjs-design`, B.13)

- New [`docs/dev/pagedjs-preview-spike.md`](docs/dev/pagedjs-preview-spike.md) —
  the timeboxed design-spike doc for the paged.js preview-render engine
  replacement pulled pre-public per `RELEASE_ARC.md`:1227-1230. Grounds the
  current fidelity gap in `blueprints/templates.py`'s
  `_inject_paged_polyfill()`/`_PAGED_PREVIEW_INJECTION` and
  `static/app.js`'s `_wirePreviewPageCount()`, states an explicit scope fence
  (PDF export stays Playwright-native via `pdf_render.py`, untouched), and
  lists bounded spike tasks + a recommendation. **Doc only** — no product
  code, no dependency, no `PROMPT_VERSION` change; the replacement itself is
  owner-slotted for its own pre-public sprint, not built in v1.0.9.
### CI: doc merge-gate — the merge=publish gates (`ci/doc-merge-gate`, v1.0.9 docs epic item 5)

- **`docs/dev/documentation-architecture.md`'s "Gates — merge = publish" table, built.**
  Four of the five listed gates were not yet built (`tests/test_doc_status_gate.py`
  already covered the `DOC-STATUS`-trigger check, PX-50); this branch adds the remaining
  four as committed pytest gates (rides the existing `pytest` run — no new CI job), matching
  the repo's established pattern (`tests/test_doc_links.py` / `scripts/check_doc_links.py`,
  `tests/test_route_containment_gate.py`):
  - **link-integrity** — already built (`scripts/check_doc_links.py` +
    `tests/test_doc_links.py`, `chore/doc-link-sweep`); unchanged.
  - **frontmatter + audience** — new `scripts/check_doc_frontmatter.py` +
    `tests/test_doc_frontmatter_gate.py`. Checks every doc in a new explicit
    `PUBLISHED_DOC_FILES` registry (16 files: the repo-root canonical docs + `docs/*.md`
    top-level + `docs/governance/*.md` — deliberately narrower than all of `docs/dev/**`,
    which is a heterogeneous mix of live design docs and frozen review/perf artifacts most
    of which predate and were never meant to carry the convention; widening false-positived
    on ~12 files with no content decision made here) carries all three
    `**Purpose:**`/`**Audience:**`/`**Authoritative for:**` header fields. Green on the
    current tree with zero doc edits needed.
  - **single-home (D5)** — new `scripts/check_doc_single_home.py` +
    `tests/test_doc_single_home_gate.py`. The hardest of the five to automate (verifying
    restatement-vs-linking needs meaning, not grep) — implemented as a documented, narrower
    heuristic: near-verbatim (post-whitespace/case-normalization) duplicated prose paragraphs
    (>= 240 chars) across 2+ distinct files in the same `PUBLISHED_DOC_FILES` registry, fenced
    code excluded, with a reviewed-exception registry for the (currently empty) case of an
    intentional duplication. Proven to have real detection teeth on synthetic fixtures before
    trusting the green real-tree result (D5 discipline is genuinely holding across the
    registry — zero duplication found even at an 80-char probe threshold).
  - **cite-resolution** — widened `scripts/check_doc_links.py`'s `CITE_CHECK_FILES` from
    `{AGENTS.md, CLAUDE.md}` to the full `PUBLISHED_DOC_FILES` registry (imported from the
    frontmatter gate, not restated — D5 applied to this gate's own code);
    `CITE_CHECK_DIRS = ("docs/governance/",)` stays directory-wide unchanged so
    `compliance-log.md` (an append-only log, deliberately excluded from the frontmatter
    registry) keeps its existing cite coverage. Green on the current tree; no new dead cites
    found.
  - **wiki-freshness** — new `scripts/wiki_freshness.py` (stdlib + git only, no LLM), reusing
    `wiki-freshness-reminder.sh`'s drift computation but as a hard block: `BLOCK_THRESHOLD =
    75` (distinct from the reminder hook's soft `THRESHOLD = 10`, calibrated above ordinary
    branch-scale drift but below the 119-434 file drift that went unblocked for ~7 weeks
    before the 2026-07-10 catch-up ingest). Rides `pytest` via
    `tests/test_wiki_freshness_gate.py`, **and** is wired into
    `scripts/enforcement/guards/block_merge_to_main.py` (`decide()` /
    `git_operation_check()` / `git_push_check()`) as a genuine merge-time block — checked
    once a command would otherwise be allowed, **not bypassed by `CLAUDE_CONFIRM_MERGE=1`**
    (that token confirms the merge target, not doc freshness; the only way through is running
    `/wiki-self-update` or `/wiki-ingest`, mirroring the `DOC-STATUS` gate's no-escape-hatch
    design). 6 new unit/integration tests added to `tests/test_enforcement_core.py`
    (`TestBlockMergeToMainUnit`); all 61 pre-existing tests in that file still pass unchanged
    (the extension only fires when a real `docs/wiki/.last_ingest_sha` baseline exists —
    every existing fixture repo has none, so it silently no-ops for them). Currently green:
    the wiki was refreshed to `e785e53` on this same train (1-file drift at authoring time).
- **No product code, prompt, route, or dependency change** — doc-tooling + test-infra only
  (`scripts/**`/`tests/**`, both KIT-7 ANN/D-exempt). `PROMPT_VERSION` untouched.
- **Doc issues found while scoping:** none required a content fix — the widened cite-check
  and the new frontmatter/single-home registries were green against the current tree with no
  doc edits needed (see the per-gate notes above for the scope decisions that kept it that
  way; `docs/dev/**`'s ~12 files with a partial `Purpose`/`Audience`/`Authoritative-for`
  header are a known, out-of-scope-for-this-gate observation, not a fix made here — see the
  lane report for the full list).
- **Flags for the train tip / sibling lanes:** `PUBLISHED_DOC_FILES` (in
  `scripts/check_doc_frontmatter.py`) should converge with `scripts/project_docs_to_mdx.py`'s
  own published-page scope once `feat/fumadocs-site` lands (this branch predates that script
  and defines its registry independently, per the lane's task brief); any new top-level
  `docs/*.md`/root doc a sibling lane adds should carry the Purpose/Audience/Authoritative-for
  header or it will need adding to (or excluding from) `PUBLISHED_DOC_FILES` explicitly.

### Chore: DOC-STATUS grep gate (`ci/px50-doc-status-gate`, PX-50)

- New `tests/test_doc_status_gate.py` — a pytest gate (rides the normal
  `pytest` run, no separate CI wiring) that enforces the `DOC-STATUS`
  marker convention documented in
  [`docs/dev/documentation-architecture.md`](docs/dev/documentation-architecture.md)
  (F-doc-09): every `<!-- DOC-STATUS(key): ... Canonical: ... -->` marker
  must parse to the documented grammar shape, and any marker whose own
  text frames a `vX.Y[.Z]` version as an open trigger ("owed at vX",
  "until vX", "update when vX lands") fails the build once that version is
  `<=` the current `pyproject.toml` version — the freshness-gate "hook
  point" the architecture doc proposed but never built. Proximity-based
  phrase/version pairing so a marker mixing a resolved past trigger with a
  distinct, still-open future one is not wrongly flagged for the resolved
  half. Grammar deviation found and tolerated: real markers use "Canonical
  homes:" (plural) alongside the documented singular "Canonical:".
- The gate found 3 real unreconciled markers in `README.md` — all three
  cited PX-19/PX-20 as still owed at v1.0.8, but both shipped in v1.0.8
  Sprint 8.3a (`docs/governance/enforcement.md`) and v1.0.8 is already
  tagged. Reconciled the 3 markers (and their immediately adjacent
  claim-state prose: the "Governed by construction" paragraph, the egress
  paragraph's marker, and the Status section's governance bullet) to the
  already-established SHIPPED status. No new claim invented — text mirrors
  `enforcement.md`'s existing "SHIPPED v1.0.8 Sprint 8.3a" language. The
  `v1.1.0`-triggered portion of the Status bullet stays open (untagged).
- **TRAIN-ASSEMBLY note (2026-07-10, `train/v109-docs-hygiene`):** this gate
  now also runs against the combined tree assembled by this train, which
  adds PX-40's new `docs/PRODUCT_SHAPE.md` marker and PX-48's two new
  design-doc markers that PX-50 never saw at cherry-pick time — see the
  gate-pass evidence in the train assembly commit / manifest.
- No product code / prompt / route / dependency change; `PROMPT_VERSION`
  untouched.

### Test: consolidate the triplicated `_imported_roots()` AST helper (`test/px53-shared-ast-helper`)

- **PX-53 (2026-07 efficiency review, F-tci-02).** The whole-tree AST
  import-walk helper backing the three boundary-gate tests
  (`tests/test_construction_boundary.py`, `tests/test_recall_boundary.py`,
  `tests/test_web_infra_is_leaf.py`) was duplicated near-verbatim three
  times. Extracted the ONE shared implementation to
  `tests/_ast_import_roots.py::imported_roots()`; all three gate files now
  import it instead of defining their own copy. **Verified the three bodies
  before touching anything:** `test_construction_boundary.py` and
  `test_web_infra_is_leaf.py` were byte-identical (skip relative imports
  outright — they can never resolve to an absolute forbidden root);
  `test_recall_boundary.py` differs in exactly one place — it resolves a
  relative import to a local root (falling back to `"recall"`) instead of
  skipping it, so `recall/`'s own self-referential imports read as
  in-package rather than third-party. Preserved that exactly via a
  `resolve_relative: bool = False` parameter — the default reproduces the
  skip behavior the other two gates need; `test_recall_boundary.py`'s two
  call sites pass `resolve_relative=True`. No gate semantics changed: all 16
  tests across the three files still pass, and a manual sanity check
  confirmed each gate still fails closed on a deliberate violation
  (`import analyzer`/`import app`/`from blueprints import assistant`
  injected ad hoc against the shared helper). TEST-INFRA only — no product
  code, prompt, route, or dependency touched; `PROMPT_VERSION` untouched.
  Gate green: `ruff check .` + `ruff format --check` (touched files) +
  `mypy .` ("Success: no issues found in 300 source files") + full pytest.

### Docs: dev-doc staleness batch (PX-48, `docs/px48-doc-staleness-batch`)

- **SUPERSEDED/SHIPPED status banners** on two completed design docs, per the
  `DOC-STATUS` convention (`docs/dev/documentation-architecture.md`):
  [`docs/dev/app-blueprints-design.md`](docs/dev/app-blueprints-design.md) is
  marked SHIPPED (the 8.1→8.3h `app.py`→blueprints decomposition landed
  2026-06-22, `app.py` carries zero routes);
  [`docs/dev/kit-adoption-design.md`](docs/dev/kit-adoption-design.md) is
  marked Phases 1–2 SHIPPED (mypy `--strict` §6-exit reached 2026-07-10) with
  commitment (3) [skills/hooks-packaging coherence] still open, deferred to
  the v1.1.0-gate `feat/portable-enforcement-core` (8.7) window — the doc
  stays authoritative for that remainder.
- **CHANGELOG archive split.** Moved the `[1.0.3]` through `[0.1.0]` sections
  (~585 lines, byte-preserved) out of this file into
  [`CHANGELOG-archive.md`](CHANGELOG-archive.md), with a pointer left in their
  place. `[Unreleased]` through `[1.0.4]` stay here.
- **Ledger head-note compression.** Replaced the ~500-word chronological
  run-on head-note atop `docs/dev/RELEASE_CHECKLIST.md`'s carry-forward
  ledger "Open" subsection with a 3-sentence current-state note (rendered
  open count + the reduction-ceiling reminder + a pointer that git history
  holds the per-item chronology). Re-verified the rendered `- [ ]` count
  programmatically: **7**, unchanged by this doc-only edit. No ledger items
  touched.

### Docs: reconcile PRODUCT_SHAPE.md to the post-split reality (PX-40, `docs/px40-product-shape-reconcile`)

- **WS-1 row (§11.2) updated from scheduled to shipped.** Verified at HEAD
  (2026-07-10): `app.py` is a ~296-line application-factory composition root
  with **zero** `@app.route` decorators (`grep -c` confirms both hits are
  prose in the module docstring, not decorators); every route lives on a
  domain blueprint (`blueprints/` + the read-only `dashboard/`), per
  `app.py`'s own docstring. The row now reads ✓ **SHIPPED (v1.0.8)** instead
  of describing the split as future work.
- **The two `app.py:1403-1423` dead citations the prescription named
  (`PRODUCT_SHAPE.md:186`, `:481`) are already gone** — re-verified: no
  `app.py:` line-number citations remain anywhere in the file; both
  locations were already re-anchored to `blueprints/templates.py` by prior
  work (the 8.3e blueprint-decomposition docs pass). No edit needed for
  this sub-item; noted here so the prescription doesn't re-surface it.
- **Added as-of/status markers to the §11.2 workstream table** — a Status
  column (✓ SHIPPED / ◐ PARTIAL / PLANNED) plus a visible "Snapshot —
  updated as these land" note and a `DOC-STATUS` HTML-comment trigger (the
  convention documented in `docs/dev/documentation-architecture.md`), so a
  reader can tell shipped from aspirational without cross-referencing
  `RELEASE_ARC.md`. WS-2 is corrected from "post-public 1.1.x" to
  **PARTIAL**: the `mypy --strict` §6 exit criterion was reached
  2026-07-10 (same day, prior branch on this train) — only the typed
  `context_set` spine itself remains post-public.

### Chore: mypy --strict ratchet COMPLETE — §6 exit (`chore/kit-mypy-strict-uipages-exit`)

- **Kit-adoption Phase 2 #2, ratchet rung 8 — the FINAL rung, reaching the §6
  exit criterion.** Appended `ui_pages.*` (the Playwright Page-Object-Model —
  a test *driver*, but not in the Decision-7 exempt set, so strict per
  Decision-7; the `D`/`interrogate` families already treated it as production
  scope) plus the 4 setuptools data-package **marker `__init__.py`** files
  (`templates`, `static`, `personas.bundled`, `docs.wiki` — verified
  pure-docstring, zero code, already strict-clean) to the `pyproject.toml`
  strict-roster `[[tool.mypy.overrides]]` block (`docs/dev/kit-adoption-design.md`
  §4/§6), and rewrote the block's leading comment into its final terse
  cohort-history form (rungs 1-8) declaring the ratchet complete. Measured **1
  error** live (`mypy --strict --warn-unreachable ui_pages/`):
  `ui_pages/user_picker.py`'s `options()` `no-any-return` on
  `eval_on_selector_all(...)` → wrapped in `cast("list[str]", ...)` (a runtime
  no-op; `cast` added to a top-level `from typing import cast`, not under
  `TYPE_CHECKING`, since `cast()` runs at runtime). The 4 markers added **zero**
  errors (roster-add only). **§6-exit proof:** with the roster complete, the
  non-covered/non-root production-`.py` list is empty —
  `git ls-files '*.py' | grep -vE '^(tests/|evals/|scripts/|db/migrations/versions/)'
  | grep -vE '^(blueprints/|dashboard/|web_infra/|recall/|onboarding/|ui_pages/|db/|
  templates/__init__|static/__init__|personas/bundled/__init__|docs/wiki/__init__)'
  | grep '/'` prints nothing — so **all 81 non-exempt production `.py` modules**
  are now at full `mypy --strict` + `warn_unreachable`; only the named Decision-7
  exempt set (`tests/`, `evals/`, `scripts/`, `db/migrations/versions`) stays
  permissive. **This completes kit-adoption commitment (1)** [the mypy `--strict`
  ratchet, `docs/dev/kit-adoption-design.md` §6] — the row in
  `docs/dev/RELEASE_CHECKLIST.md` stays open pending commitment (3) [the 8.7
  hooks-rehome / skills-packaging coherence pass]. **PROMPT-SAFE (grep-0):**
  `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|_BASE_SYSTEM_PROMPTS)`
  across `ui_pages/` returned 0 hits (the 4 markers hold no prompts either) —
  no `PROMPT_VERSION` bump, no eval run. No new dependency, no behavior change
  beyond the one `cast`. Gate green: `ruff check .` + `ruff format --check`
  (touched files) + `mypy .` ("Success: no issues found in 298 source files").

- **§6-exit enforced by construction (charter C-0 / compliance-witness CW-118).**
  Added `tests/test_mypy_strict_roster_gate.py` — the mypy-roster analogue of the
  route-containment + docstring-coverage KEEP gates. It parses the strict
  `[[tool.mypy.overrides]]` roster and asserts every non-exempt tracked `.py`
  module is covered (under mypy's own `pkg.*` glob semantics), so a module added
  outside the Decision-7 exempt set and left off the roster fails the suite —
  instead of silently type-checking permissively while `mypy .` still prints
  Success. Turns the §6 claim from a one-time manual proof into a by-construction
  invariant (and guards the exempt `db/migrations/versions` tree against a `db.*`
  wildcard). `mypy .` now reports 299 source files (the added gate).

### Chore: mypy --strict roster — dashboard (`chore/kit-mypy-strict-dashboard`)

- **Kit-adoption Phase 2 #2, ratchet rung 7 — the localhost-only diagnostics
  dashboard brought to full `mypy --strict`.** Appended `dashboard.*` to the
  `pyproject.toml` strict-roster `[[tool.mypy.overrides]]` block
  (`docs/dev/kit-adoption-design.md` §4/§6). Measured **36 errors** live
  (`mypy --strict --warn-unreachable dashboard/`), all in `dashboard/routes.py`
  (`dashboard/__init__.py` was already strict-clean) and all mechanical: **35
  bare-generic `type-arg`** (the JSONL eval/telemetry aggregators →
  `dict[str, Any]` / `list[dict[str, Any]]`, reusing the rung-4/5/6
  precedent) + **1 `no-any-return`** (`_load_baseline`'s `json.load(f)` →
  `cast("dict[str, Any]", ...)`). No `warn_unreachable`. **Route-security-lint
  doesn't apply here** — the hook is scoped to `app.py` + `blueprints/**.py`
  and deliberately excludes `dashboard/` (its routes are localhost-gated, take
  no `<username>`, read fixed diagnostic dirs), so route decorator lines
  needed no separate carve-out. **PROMPT-SAFE (grep-verified):**
  `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|_BASE_SYSTEM_PROMPTS)`
  across `dashboard/` matched only `analyzer._BASE_SYSTEM_PROMPTS`
  registry reads (the Tuning-tab picker) and template display-text
  instructing the user to bump `PROMPT_VERSION` by hand — never a constant
  definition. So **no `PROMPT_VERSION` bump, no eval run**. No new
  dependency, no behavior change beyond annotations. Gate green:
  `ruff check .` + `ruff format --check` (touched files) + `mypy .`
  ("Success: no issues found in 298 source files").

### Chore: mypy --strict roster — blueprints (`chore/kit-mypy-strict-blueprints`)

- **Kit-adoption Phase 2 #2, ratchet rung 6 — the rest of `blueprints/**` brought
  to full `mypy --strict`, closing the top-level-root + blueprints cohort.**
  Appended `blueprints.*` to the `pyproject.toml` strict-roster
  `[[tool.mypy.overrides]]` block (`docs/dev/kit-adoption-design.md` §4/§6) —
  mypy's `*` glob matches across dots, so one entry covers every
  `blueprints/` submodule including the `corpus/` subpackage. The
  pre-existing explicit `blueprints.applications` entry (rung 2) is now
  redundant — subsumed by the glob, identical flags — and was **dropped for
  cleanliness**. Measured **51 errors** live
  (`mypy --strict --warn-unreachable blueprints/`) across 9 files, all
  mechanical: `diagnostics.py` 14 · `generation.py` 11 · `corpus/_shared.py`
  10 · `templates.py` 5 · `analysis.py` 4 · `assistant.py` 3 ·
  `corpus/curation.py` 2 · `corpus/tags.py` 1 · `corpus/skills.py` 1 — **49
  bare-generic `type-arg`** (JSON-object dicts → `dict[str, Any]`; lists →
  `list[...]`; one SSE progress `Queue` → `Queue[Any]`; one heterogeneous
  4-tuple return (`corpus/tags.py:_tag_link_target`) →
  `tuple[Any, Any, Any, Any]`, reusing the rung-2 "`Any` over a costly precise
  type" judgment call) + **2 `no-any-return`** (`cast(...)` —
  `diagnostics._load_bootstrap_doc`'s `json.loads(...)` and
  `assistant._embed`'s `matrix / norms` numpy division). No
  `warn_unreachable` this rung. **Route-security-lint technique:** every edit
  window was scoped to the function signature/body, never the `@…route`
  decorator line (the ruff-`D` blueprints-unit pattern from
  `docs/dev/kit-adoption-design.md` §4) — the hook never fired. **PROMPT-SAFE
  (grep-0):** `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|_BASE_SYSTEM_PROMPTS)`
  across `blueprints/` matched only prose/docstring references and
  `analyzer.*` imports/uses, never a constant definition — blueprints hold no
  prompt constants of their own. So **no `PROMPT_VERSION` bump, no eval
  run**. No new dependency, no behavior change beyond annotations. Gate
  green: `ruff check .` + `ruff format --check` (touched files) + `mypy .`
  ("Success: no issues found in 298 source files").

### Chore: mypy --strict roster — backend substrate (`chore/kit-mypy-strict-backend`)

- **Kit-adoption Phase 2 #2, ratchet rung 5 — the backend substrate brought
  to full `mypy --strict`.** Appended `web_infra.*`, `recall.*`,
  `onboarding.*`, and `db` — listed as explicit submodules (`db`,
  `db.ats_roundtrip`, `db.build_context`, `db.models`, `db.persist_run`,
  `db.session`, `db.migrations.env`, `db.migrations._sqlite_check_constraint`)
  rather than a `db.*`/`db.migrations.*` wildcard, since either wildcard would
  capture `db.migrations.versions.*` — the Decision-7 EXEMPT set — to the
  `pyproject.toml` strict-roster `[[tool.mypy.overrides]]` block
  (`docs/dev/kit-adoption-design.md` §4/§6). `recall.*` measured
  strict-clean already (roster-add only, zero fixes). Measured **17 errors**
  live (`mypy --strict --warn-unreachable`) across the rest: **web_infra**
  (5 — 4 bare-generic `type-arg` + 1 `no-any-return`, in `config_io.py` and
  `http.py`), **onboarding** (4 — 3 `type-arg` + 1 `no-any-return`, in
  `extract_experiences.py` and `corpus_import.py`), and **db** (8 — 5
  `type-arg` in `ats_roundtrip.py`/`persist_run.py` + **3 `warn_unreachable`**
  in `db/persist_run.py:180,270,350`). The 3 unreachable were
  `isinstance(entry, dict)` runtime guards over the `selected`/`proposals`
  params of `_persist_selected_bullets`/`_persist_proposed_bullets`/
  `_persist_proposed_titles` — each carries untrusted LLM JSON, so the guard
  is live defense, not dead code. **Resolved by widening the param type**
  from `list[dict]` to `list[Any]` (not a scoped ignore) — this also fixes
  the `type-arg` error on the same declaration in one edit, keeps the guard
  reachable, and stays honest that the entries are untrusted at the type
  level; zero runtime change (the rung-3/4 "widen a local to keep the branch
  live" precedent, applied to a parameter). All other `type-arg`/
  `no-any-return` fixes were the usual mechanical pattern (`dict[str, Any]`
  parametrization; `cast(...)` on `json.load`/`json.loads` returns; `Any`/
  `cast` added to each file's `typing` import). **PROMPT-SAFE:** the only
  prompt constant in scope, `EXTRACT_EXPERIENCES_SYSTEM_PROMPT` in
  `onboarding/extract_experiences.py`, sha256-verified byte-identical
  HEAD-vs-branch (`602e8ef4a68c...4283e9c`), and the branch's diff never
  enters its line range; the
  `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|_BASE_SYSTEM_PROMPTS)`
  grep across `web_infra/`, `recall/`, `db/` returned zero hits (the one hit
  in `db/build_context.py` is an *import/use* of `analyzer.PROMPT_VERSION`,
  not a definition). So **no `PROMPT_VERSION` bump, no eval run**. No new
  dependency, no logic change beyond the one deliberate param-type widening.
  Gate green: `ruff check .` + `ruff format --check` (touched files) +
  `mypy .` ("Success: no issues found in 298 source files").

### Chore: mypy --strict roster — top-level modules (`chore/kit-mypy-strict-toplevel`)

- **Kit-adoption Phase 2 #2, ratchet rung 4 — all 8 remaining top-level root
  `.py` modules brought to full `mypy --strict`.** Appended `hardening`,
  `parser`, `generator`, `corpus_to_json_resume`, `docx_to_persona_html`,
  `config`, `demo_fixtures`, `app` to the `pyproject.toml` strict-roster
  `[[tool.mypy.overrides]]` block (`docs/dev/kit-adoption-design.md` §4/§6).
  `config.py`/`demo_fixtures.py`/`app.py` were already strict-clean
  (roster-add only, zero fixes). The 5 C-6 deterministic modules measured
  **51 errors** live (`mypy --strict --warn-unreachable`): **48 bare-generic
  `type-arg`** (JSON-object dicts parametrized to `dict[str, Any]`, section/
  proto lists to `list[dict[str, Any]]`; `Any` added to each file's
  `typing` import), **1 `no-any-return`**
  (`generator.py:_extract_list_numPr` — wrapped the `deepcopy(numPr)` return
  in `cast("CT_NumPr | None", …)`, a runtime no-op; `cast` added to the
  `typing` import), and **2 `unreachable`** in `hardening.py` (`:1504`'s
  `resume` access and `:1535`'s `keyword_overlap` access — both the same
  ContextSet-TypedDict always-truthy `or {}` JSON-defense artifact already
  resolved identically in `analyzer.py`'s rung-3 precedent; kept the
  defensive fallback behind a scoped `# type: ignore[unreachable]` with a
  one-line comment, zero runtime change). **PROMPT-SAFE:** the
  `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|_BASE_SYSTEM_PROMPTS)`
  grep across the 8 modules returned 3 hits, all verified false positives —
  `demo_fixtures.py`'s `DEMO_AVATAR_ANSWER` (a canned demo-mode fixture
  string, not a prompt constant) and two `hardening.py` docstring prose
  mentions of "SYSTEM_PROMPT" as a cross-reference to the real constant in
  `analyzer.py` — neither is a prompt definition and neither line was
  touched by this branch's edits, so **no `PROMPT_VERSION` bump, no eval
  run**. No new dependency, no logic change — annotations/casts/a scoped
  ignore only. Gate green: `ruff check .` + `ruff format --check` (touched
  files) + `mypy .` ("Success: no issues found") + full `pytest`.

### Fix: diagnostics anchor-JD path reconciliation (`fix/diagnostics-15-anchor-jd-path`)

- **Diagnostics round-2 #15 — "No anchor JD is saved" root cause.** The
  browser bootstrap worker's writer normalizes each pasted JD's filename
  (`secure_filename` + a force-appended `.txt`) before saving it under
  `jds/`, but `annotation_collate`'s reader resolved the anchor filename
  with `secure_filename()` alone — so any JD whose display name didn't
  already end in `.txt` (e.g. `"kafka backend"` → `jds/kafka_backend.txt`)
  could never be found, `jd.txt` was never written, and `_load_fixture`
  (which hard-requires `jd.txt`) could never run that fixture. Extracted
  the shared normalization into one helper, `_jd_filename()`
  (`blueprints/diagnostics.py`), used by both the writer (bootstrap SSE
  route) and the reader (`annotation_collate`) so they can't drift apart
  again. See
  [`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`](docs/dev/reviews/2026-07-diagnostics-round2-findings.md)
  item #15 (root of the broken fixture flow; unblocks #11 next). Added a
  regression test (`tests/test_annotation_routes.py`) driving both real
  routes end-to-end with a space-containing, `.txt`-less JD name.

### Fix: diagnostics collate CLI command targets one fixture (`fix/diagnostics-11-collate-cli-fixture`)

- **Diagnostics round-2 #11 — collate's printed CLI command didn't match the
  adjacent "Run this fixture" button.** `annotation_collate`'s `run_command`
  read `python evals/runner.py --suite real --seed
  evals/fixtures/real/<slug>/seed.json` — no `--fixture <slug>`, and `--seed`
  doesn't restrict which fixtures run, so copy-pasting it globbed every real
  fixture and crashed in `_load_fixture` (which hard-requires each fixture's
  `jd.txt`), while the button posts a single `fixture: slug`. Added
  `--fixture <slug>` (and dropped the now-redundant `--suite real`, since
  `--fixture` overrides it) so the printed command matches the button's
  single-fixture semantics. See
  [`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`](docs/dev/reviews/2026-07-diagnostics-round2-findings.md)
  item #11 (blocked by #15, fixed above first). Extended the existing
  collate test to assert `run_command` contains `--fixture <slug>`.

### Fix: bootstrap skills parser strips inline category labels (`fix/diagnostics-08-skills-parser`)

- **Diagnostics round-2 #8 — skills rendered strangely when annotating.**
  `_heading_text` (`evals/bootstrap.py`) only recognizes a full-line
  bold/`#` heading, so an inline category line like `**Languages:**
  Python, Go` falls through to `_split_skill_line` as a content line —
  which stripped a leading bullet marker but not the inline bold label,
  so the first "skill" came out as the garbled `**Languages:** Python`
  instead of `Python`. `_split_skill_line` now also strips a leading
  inline bold/underscore category-label prefix (`**Label:** …` and
  `**Label**: …`, colon inside or outside the bold span, `**`/`__`
  both supported) before splitting on delimiters — deliberately
  requiring the colon adjacent to the bold close so a genuinely bolded
  skill token with no label colon is left untouched. `_heading_text`
  and its heading semantics are unchanged. See
  [`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`](docs/dev/reviews/2026-07-diagnostics-round2-findings.md)
  item #8. Added regression tests (`tests/test_bootstrap.py`) covering
  both colon placements, the `__…__` variant, a bulleted inline label,
  a plain comma list (no over-stripping), and a bolded skill token with
  no label colon.

### Fix: diagnostics global paid-run lock (`fix/diagnostics-01-run-lock`)

- **Diagnostics round-2 #1 — no shared single-flight across the four paid-run
  buttons.** Each of the eval / tune / bootstrap / grounding-score run
  controls (`dashboard/templates/dashboard.html`) toggled only its own
  `disabled` flag, so switching tabs mid-run and clicking a second button
  could silently fire a duplicate **paid** Anthropic run. Added a shared
  client-side `window.sartorRunLock` (`acquireRunLock()`/`releaseRunLock()`):
  ships the **conservative "block any second run" default** — while any one
  of the four is live, the lock disables all four (including re-clicks of the
  live one), shows a prominent `#runLockBanner`, and arms a `beforeunload`
  guard that only warns while a run is actually in flight. `releaseRunLock()`
  is wired at each entry point's existing terminal paths, mirroring each
  button's own pre-existing re-enable (eval/tune SSE `_closed` + `error`;
  bootstrap/grounding-score `!ok` / `chunk.done` / `.catch()`), so a completed,
  failed, or aborted run releases the lock. The eval `_closed` release is
  covered by the regression test below; the other sites are wired by hand
  identically to their button re-enable — funnelling bootstrap/grounding-score
  through the shared streamer, or extending the test to all four entry points,
  is tracked as a WATCH in the Diagnostics-DX ledger row (witness CW-117). See
  [`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`](docs/dev/reviews/2026-07-diagnostics-round2-findings.md)
  item #1 / the RUN-LIFECYCLE note. Client-side lock only — the real run-cancel
  abort endpoint and `app.run(threaded=True)` are separate, owner-gated epic
  items, deliberately out of scope here. Added a UX regression test
  (`tests/ux/regression/test_20260709_diagnostics_run_lock.py`) that holds a
  `POST /api/eval/run` open via a Playwright route interceptor, asserts all
  four buttons + the banner lock, then fulfills the held request and asserts
  they release.
### Docs: recruiter Pipeline-tab wiki coverage, closes F-17 (`docs/wiki-content-pass`, v1.0.9 docs epic)

- Authored the `audience: user` how-to page
  [`docs/wiki/pages/recruiter-pipeline-tab.md`](docs/wiki/pages/recruiter-pipeline-tab.md) for
  the recruiter-tier **Pipeline** tab (`feat/ux-w2-recruiter`, F-17) — the cross-candidate
  application-status board. Closes the gap where the in-app doc-grounded assistant's
  `user`-scoped access plane had no page to cite and refused Pipeline questions. See
  [`docs/wiki/log.md`](docs/wiki/log.md) for the full content-pass record (per this file's
  scope rule, wiki content itself is logged there, not restated here).
- Closed the corresponding Carry-forward-ledger row in
  [`docs/dev/RELEASE_CHECKLIST.md`](docs/dev/RELEASE_CHECKLIST.md) — added and resolved in the
  same edit, so the rendered open count is unchanged.
### Docs: diagram accessibility + single-source consolidation (`docs/diagrams-a11y`, 2026-07-10)

- Added Mermaid `accTitle`/`accDescr` a11y directives (screen-reader title +
  description) to all four canonical diagrams in `docs/architecture.md`
  (pipeline sequence, persistence ER, LLM routing, `context_set` data flow).
- Retired the 4 standalone `docs/diagrams/*.mmd` files — byte-identical
  duplicates of the `docs/architecture.md` embeds that relied on "edit
  either copy and keep both in sync" discipline alone; `docs/architecture.md`
  is now the single source. Re-pointed every cross-document link/cite that
  targeted a retired path (`AGENTS.md`, `docs/wiki/pages/*.md`); verified
  clean via `scripts/check_doc_links.py`.
### Added: hosted Fumadocs docs site (`feat/fumadocs-site`, v1.0.9 Phase 6 docs epic)

- **New `docs-site/` app** — a self-hosted [Fumadocs](https://fumadocs.dev)
  (Next.js App Router) site configured for **static export**
  (`output: 'export'` → `docs-site/out/`, no server process). Scaffolded via
  `create-fumadocs-app` (`+next+fuma-docs-mdx+static` template). **New JS
  toolchain** (`docs-site/package.json`): `next`, `fumadocs-core`,
  `fumadocs-mdx`, `fumadocs-ui`, React 19, TypeScript, Tailwind CSS 4 — a
  separate dependency tree from the Python product (the "no new dep without
  a `pyproject.toml` + CHANGELOG entry" rule is a Python-tree rule; this is
  its JS-tree documentation instead, per the lane's scope).
- **New `scripts/project_docs_to_mdx.py`** — the deterministic, stdlib-only
  (no new Python dependency) projection adapter: reads the L1 doc set
  (README + `docs/**` pages carrying the `Purpose`/`Audience`/
  `Authoritative-for` header, excluding `docs/wiki/**` which is L2) and
  emits `docs-site/content/docs/*.mdx` + a `meta.json` ordered by README's
  own "Documentation map" (the ICP ladder) partitioned by the
  `docs/wiki/SCHEMA.md` `user`/`dev` audience tag. See the module docstring
  for the full frontmatter map, audience-classification fallback chain, and
  the MDX-safety escaping (including a `<!-- -->` → `{/* */}` rewrite — MDX
  has no raw-HTML-comment syntax). Covered by `tests/test_docs_projection.py`
  (23 tests).
- **New `.github/workflows/docs-deploy.yml`** — on push to `main`: runs the
  projector, builds the static export, and always publishes it as a
  downloadable artifact (works with any webhost). An optional, guarded
  SFTP/SSH auto-push (`SFTP_HOST`/`SFTP_USER`/`SFTP_KEY`-or-`SFTP_PASSWORD`
  repo secrets) skips gracefully when unconfigured. No literal secrets.
- **New [`docs/dev/docs-site-deploy.md`](docs/dev/docs-site-deploy.md)** —
  the self-host runbook (DNS, SFTP/SSH setup, manual-upload fallback).
- `pyproject.toml` — `docs-site/` excluded from `ruff`/`mypy`/`interrogate`
  (a separate JS toolchain; see `docs-site/README.md` for its own dev loop).
- **Deferred, not built this lane (STOP-AND-REPORT at the time):**
  RELEASE_ARC.md's Phase 4.9 plan has Fumadocs render an HTTP-API reference
  (Layer B) from an OpenAPI spec `spectree` emits. `spectree` was **not
  present** in this codebase at this lane's HEAD (zero `.py` imports, absent
  from `pyproject.toml`) — the ARC's "pulled into v1.0.8" claim was stale.
  Wiring `spectree` into the Flask route surface was product code + a
  security-gated change, out of this docs lane's scope; flagged for an owner
  decision. **Resolved** — spec-emission (spectree Phase 1: 5 read-only GET
  routes decorated, `web_infra/openapi.py` + `scripts/generate_openapi_spec.py`)
  landed in v1.0.9 via `feat/spectree-openapi-emit` (see the `[Unreleased]`
  entry above). Fumadocs actually *rendering* that spec remains a separate,
  still-deferred branch.
  **Correction (2026-07-10):** this is now stale — the Fumadocs render
  (Layer B, Phase 2) **LANDED** via `c8899fd` in this same v1.0.9 pull-in
  train; see the "spectree/OpenAPI Layer B, Phase 2 — render the spec in
  Fumadocs" Added entry under `[1.0.9]` above. The prose above is retained
  as the historical record of what was deferred at `feat/fumadocs-site`'s
  authoring time.

## [1.0.8] — 2026-07-09

### Fix: UX round-2 quick wins (`fix/round2-quick-wins`, 2026-07-09)

Six decision-free fixes from the owner's e2e round-2 walkthrough (Wave A;
see [`docs/dev/reviews/2026-07-ux-round2-findings.md`](docs/dev/reviews/2026-07-ux-round2-findings.md)
for the full findings + disposition table — the design-heavy remainder is
registered as the UX Cohesion Epic in `docs/dev/RELEASE_ARC.md`, not landed
here).

- **G6 — clarify busy-state gap** — `runClarify()` and `runIterateClarify()`
  (`static/app.js`) now wrap their `/api/clarify` and `/api/iterate-clarify`
  calls with the existing `_setBusy(true, 'Generating clarifying
  questions…')` / `_setBusy(false)` idiom, matching every other long-running
  action (analyze/generate/compose). No new mechanism — just filled the two
  sites the busy-state work had skipped.
- **Co2 — "Tailor skills to this JD" working-state** — `_fireRecommendSkills()`
  (`static/app.js`) now disables its button and relabels it "Tailoring…"
  for the duration of the call, restored in a `finally`, mirroring the
  adjacent `_fireSuggestSkills()`.
- **Co4 — wire "Suggest skills from my corpus"** — a new button in the
  Career Corpus tab's Skills editor (`templates/index.html`) calls the
  already-built, already-tested `POST
  /api/users/<username>/skills/suggest-from-corpus` route
  (`blueprints/corpus/skills.py`, backing `analyzer.suggest_skills_from_corpus`)
  so a candidate can populate Skills before their first application, not
  just from a JD in Compose. Same working-state pattern as Co2/the existing
  Compose suggest button.
- **T1 — owned-template card button overflow** — `.persona-card-actions`
  (`static/style.css`) gained `flex-wrap: wrap` so a template card's 5
  action buttons (including Delete, rendered last) wrap instead of
  overflowing the ~280–320px card.
- **C2 — bounded skill lists** — `.skills-editor-section` (Career Corpus
  tab) and `.compose-skill-list` (Compose skills card) got a bounded
  `max-height` + `overflow-y: auto` so a candidate with many skills scrolls
  within the section instead of the editor taking over the window. The
  collapsible-toggle refinement is deferred to the UX Cohesion Epic.
- **O1a — docx section/entry spacing** — `generator.py:_write_docx_from_json_resume`
  (the shared download/preview/PDF writer — download == preview is
  preserved) now inserts a blank-paragraph spacer between top-level
  sections and between `work` entries, deterministically — no LLM
  involved. A template's own captured `space_before`/`space_after` for the
  relevant role is respected: the spacer is skipped when the template
  already spaces that role, and added only where none exists.

### Docs/CI: E-2 machine badge set + pip-audit (`docs/badges-readme-prep`, 2026-07-09)

Lands PX-26 (E-2 machine badge set) + PX-54 (pip-audit) as committed files —
Train-4b, freeze-independent per `RELEASE_ARC.md` "Big-push scope brief"
Phase 4.

- **README badges row** — replaces the `docs/badges-readme-prep` placeholder
  with CI status, static MIT license, static Python 3.11/3.12/3.13, a static
  "network egress: allowlisted" badge citing `tests/test_egress_allowlist.py`
  (PX-08), OpenSSF Scorecard, and REUSE status, with an HTML comment noting
  the CI/Scorecard/REUSE badges resolve live data only once the repo is
  pushed to GitHub and promoted public.
- **`.github/dependabot.yml`** — `pip` (against `pyproject.toml`, no
  lockfile) + `github-actions` ecosystems, weekly.
- **`pip-audit` CI job** (PX-54) — a separate advisory job in
  `.github/workflows/ci.yml` with `continue-on-error: true`, not gating the
  `quality`/PR path (a CVE-triggered CI failure is a new triage source for a
  solo maintainer, per the prescription).
- **`.github/workflows/scorecard.yml`** — standard `ossf/scorecard-action`
  workflow, gated `if: ${{ !github.event.repository.private }}` so it's an
  inert no-op while the repo is private.
- **REUSE/SPDX manifest** — a wildcard `REUSE.toml` (`path = "**"` → MIT)
  plus one override for `tests/ux/a11y/vendor/axe.min.js` (MPL-2.0, Deque
  Systems), with `LICENSES/MIT.txt` + `LICENSES/MPL-2.0.txt` (canonical SPDX
  license texts). No per-file SPDX headers — large-diff and prompt-adjacent
  risk (`analyzer.py` is the prompt home). Verified locally: `reuse lint`
  reports 578/578 files covered, 0 issues. `SECURITY.md` "Bundled
  third-party assets" updated from "planned for the public release" to cite
  the committed manifest.
- **Owner-activation still owed** ([HUMAN], out of this branch's scope):
  creating the `take-tempo-public/sartor` GitHub repo, promoting it public,
  and the PyPI Trusted Publisher config — until then the CI/Scorecard/REUSE
  badges render as unresolved/404. A pinned dependency lockfile for
  Dependabot's `pip` ecosystem is a separate owner decision, not addressed
  here.

### Fix: persona preview fidelity + walkthrough residuals + witness reconciles (`fix/persona-fidelity-and-residuals`, 2026-07-09)

Closes the "Walkthrough residuals (post-Train-5)" carry-forward row: the six
items the four Train-5 repair lanes didn't cover, plus three governance-witness
FLAGs (CW-101/102/104) and one live-backfill extractor gap, in one lane before
the code freeze.

- **Persona-preview style fidelity** — `docx_to_persona_html.extract_persona_style`
  now captures per-role vertical rhythm (`header_space_after_pt`,
  `heading_space_before_pt`/`heading_space_after_pt`, `job_title_space_before_pt`
  — mirroring `generator._capture_template_styles`'s `space_before_pt`/
  `space_after_pt`), and `_build_css` renders it (falling back to the historical
  hardcoded px literals when the source `.docx` never set it — no behavior
  change for documents without direct spacing overrides). Verified against the
  owner's uploaded persona + before/after walkthrough artifacts (python-docx
  property analysis, not committed): real captured values (10.9pt header gap,
  2.8pt heading gap) now reach the preview instead of the generic 20px/8px
  defaults; all 4 bundled templates round-trip their `TypographyPreset` values
  exactly. **Date-column honesty (owner decision — no right-alignment work in
  the docx writer):** the owner's real artifacts show job-title lines with NO
  captured right tab stop (all 3 examined), so the actual `.docx` download does
  NOT right-align the date — the companion CSS's `.job-header` now only forces
  `justify-content: space-between` when the source `.docx` actually defines a
  right tab stop (`job_title_has_right_tab`); otherwise it renders inline
  instead of idealizing a right-alignment the download doesn't produce.
  Bundled templates (which do define the tab stop) are unaffected.
- **`preview_candidate_html` lazy-regen fallback** — gained the same
  lazy-companion-generation fallback its two sibling preview routes already had
  (`preview_application_html` / `preview_edited_html`): an uploaded persona
  with no `.html`/`.css` companion yet now regenerates it on first preview
  instead of falling back to Classic forever.
- **Silent persona-companion-generation failure surfaced** — `upload_user_persona`
  no longer discards `generate_companion`'s return value: a companion failure
  now adds `companion_warning` to the 201 response ("Preview will use the
  default style; download unaffected"), and both frontend upload paths
  (`uploadPersonaFromInput` / `uploadTemplateFromTemplateStep`) surface it via
  toast. Upload still succeeds either way (degrade, don't block); the
  underlying failure was already logged inside `generate_companion`.
- **`/api/download-edited` identity-override wiring** — `run_generation` /
  `run_generation_stream` already resolved `identity_override` from the
  current Candidate DB row (`_resolve_candidate_identity`, keyed by
  `application_id`); `download_edited` had no `context_set` in scope to reuse
  that helper, so hand-edited re-downloads could resurrect stale identity
  fields. New `_resolve_candidate_identity_by_username` (same dict shape, same
  best-effort None-on-miss) closes the gap.
- **Page-break preview/download parity — documented as an accepted
  limitation.** Preview/PDF paginate via CSS + paged.js (byte-identical
  engines); a `.docx` download page-breaks the same content through Word at
  open time instead, so exactly where a page splits can differ — parity is
  content-level (D3), not pagination-level. Noted in the Step 4 (Template)
  in-app help copy and `docs/PRODUCT_SHAPE.md` §5.5.
- **CW-101 (witness FLAG)** — `docx_to_persona_html.py` added to
  `tests/test_construction_boundary.py`'s `DETERMINISTIC_MODULES` gate (it was
  named C-6-deterministic in AGENTS.md but the gate omitted it). The module
  passes as-is — no LLM import, confirming the witness's "clean today" read.
- **CW-102 / CW-104 (witness FLAGs — owner-approved factual reconciles)** —
  `docs/governance/charter.md` + `docs/governance/enforcement.md` still marked
  PX-19 (loopback-bind gate) and PX-20 (deterministic–LLM boundary gate) "owed
  — v1.0.8"; both shipped in Sprint 8.3a (`RELEASE_CHECKLIST.md` 8.3a row —
  `tests/test_config.py` pins the host, `tests/test_construction_boundary.py`
  is the boundary gate). Status cells updated to SHIPPED with cites; no clause
  meaning changed. charter.md's D-6 Chromium-classification cite (flagged
  stale by the witness, already fixed in reality by PX-31) reconciled to cite
  the PX-31 reclassification instead of describing the pre-fix inconsistency.
- **CW-103 prose slice** — `docs/PRODUCT_SHAPE.md`'s dangling `app.py` route
  citations (persona preview route, `_resolve_default_persona_template_path`,
  `_PAGED_PREVIEW_INJECTION`) repointed to `blueprints/templates.py`, the
  post-8.3 reality (`app.py` is a zero-route composition root). Wiki pages
  untouched (PX-41 owns them).
- **Role-title extractor improvements** (`db.build_context._infer_role_title`,
  real live-backfill evidence) — (a) `About the <Role> at <Company>:`
  boilerplate lines now extract the role segment instead of being skipped
  wholesale (`About the Director, AI Enablement at Headspace:` →
  `Director, AI Enablement`); (b) glued/mojibake prose lines never win as a
  title anymore — a new `As the<Role>, you will ...` extractor (handling the
  article gluing onto the role word) plus a `_looks_role_shaped` guard
  (≤ 8 words, no sentence-marker phrase) on the generic keyword-scan fallback
  keep a run-on JD sentence from being mistaken for a title just because it
  contains a role-hint keyword; failing open still lands on the cleaned first
  line, never a raw prose fragment. No backfill-script change — the safety
  rule already leaves hand-edited rows alone.

### Feat: visible working states + full wizard hydration on resume (`feat/ux-busy-states-and-hydration`, 2026-07-08)

Owner-observed UX gaps closed against a verified mechanism inventory (reused the existing
`_setBusy` full-overlay, per-element loading-placeholder, and `data-compose-bg-pending`
test-observability counter idioms; one new affordance).

- **Clarify→Compose busy states** — `submitClarifications`, `skipClarifications`, and the
  recommend call inside `_fireRecommendThenCompose` now wrap in `_setBusy` ("Integrating your
  answers…" / "Preparing compose…"), matching `runGeneration`'s existing overlay idiom. Before
  this, all three ran real LLM calls behind only a status-pill text change.
- **Regenerate-summary feedback** — `_fireDraftSummary(force=true)`'s explicit Compose
  "Regenerate" click now disables the button + relabels it ("Regenerating…") for the fetch,
  restoring in `finally` (idiom: `_fireDraftGapFill`'s existing button-disable pattern). The
  silent auto-fire on Compose arrival (`force=false`, no button) is unaffected.
- **Compose background-cascade visibility (new)** — a subdued `#composeBgChip`
  ("Updating suggestions…", `aria-live="polite"`) now renders near the Compose header while the
  auto-recommend/draft/gap-fill cascade is in flight, driven off the SAME
  `data-compose-bg-pending` counter `_markComposeBgReload` already maintained for the UX settle
  gate — never a second source of truth, so the chip and the gate can never disagree.
- **Scroll preservation** — `loadComposition()`, `refreshCorpus()`, and `_loadCorpusDetail()`
  all clear + rebuild a list/card body on every reload (accept/deny/retire/pin), which briefly
  shrinks the page and snapped window scroll back toward the top. All three now capture
  `window.scrollY` before the reload and restore it once the terminal render lands.
- **Keyword-coverage explainer** — the Analyze `.score-note` and the `panelAnalysis` help entry
  now answer what the JD Keyword Coverage percentage measures (literal-term overlap after
  company/boilerplate cleaning), why it matters (the same signal an ATS keyword scan uses), and
  what a good target looks like (30–50% typical for a strong match — it's coverage, not a
  grade), consistent with the existing F-01/F-12 framing.
- **Assistant guidance** (`AVATAR_SYSTEM_PROMPT`, `AVATAR_PROMPT_VERSION` → `2026-07-08.1`) — two
  new rules: dev-tier operations (seed export, grounding calibration, running evals) are now
  named explicitly as requiring Dev mode, not just offered as "more detail"; and when an answer
  mixes what sartor. does today with what's only planned/deferred, the avatar now separates them
  into labeled **What exists now** / **What's planned** sections instead of blending them into
  one claim. `PROMPT_VERSION` (the résumé pipeline) is untouched.
- **Full wizard hydration on resume (Option A)** — `_build_resume_state`
  (`blueprints/applications.py`) previously early-returned at Step 6 with ONLY the résumé/cover-
  letter payload whenever a run had a generated résumé, discarding the `llm_analysis` /
  clarifications / composition data already parsed from the SAME context file. It now ALWAYS
  merges that pre-generate hydration block (`_pre_generate_hydration`, shared with the existing
  pre-generate branch) into the Step-6 response. `_resumeIntoStep6` (`static/app.js`) renders it
  — mirroring `_resumeIntoPreGenerateStep` — and hydrates Compose via `loadComposition()` only
  when the saved context actually reached Compose (`has_composition`), so back-navigation from a
  resumed Step 6 shows populated Step 1-3 panels without clobbering saved state or re-firing the
  auto-cascade (the persisted `has_draft`/`has_gap_fill` flags gate it shut, same as a normal
  Step-3 arrival). `_compositionFrozen` stays conservative on resume (unchanged — F-09).

### Fix: review-surface unification, corpus skill suggestions, honest application titles (`fix/review-surface-and-flows`, 2026-07-08)

Six independently-verified fixes from a review pass, landed on one branch (owner-decided where noted).

- **ProposalReview bridge (owner-decided: bridge, not delete).** The applications-list "N to
  review" badge counts `ProposalReview.decision=='pending'`
  ([`blueprints/applications.py`](blueprints/applications.py)), but the only UI-reachable review
  path — the corpus accept routes (`accept_bullet` / `accept_experience_title` /
  `accept_experience_all` / `accept_all_pending`,
  [`blueprints/corpus/curation.py`](blueprints/corpus/curation.py)) and the retire routes
  (`delete_bullet` / `delete_experience_title`,
  [`blueprints/corpus/experiences.py`](blueprints/corpus/experiences.py)) — cleared
  `is_pending_review`/`is_active` directly and never touched `ProposalReview.decision`, so the
  badge over-counted forever; the `/api/proposals/*` critique/decide lane has zero frontend
  callers. New helper `blueprints/corpus/_shared.py:_resolve_proposal_reviews` resolves any
  still-pending `ProposalReview` row referencing an accepted bullet/title to
  `decision="accept_original"`, and any retired one to `decision="reject"` — the same values
  `/api/proposals/<id>/decide` would have recorded. Idempotent (only touches `decision="pending"`
  rows) and wired into all 4 accept routes + both retire routes. New migration
  [`0014_backfill_orphaned_proposal_reviews`](db/migrations/versions/0014_backfill_orphaned_proposal_reviews.py)
  (UPDATE-only, no `batch_alter_table` — `proposal_review`'s FK parents are non-CASCADE toward it
  anyway) resolves already-orphaned pending rows whose referenced bullet/title is no longer
  pending (49 such rows on the owner's clone) to `accept_original` or `reject` per its current
  state; a genuinely-still-pending row is left alone. The `/api/proposals/*` backend stays intact
  (owner-decided).
- **Corpus-wide skill suggestion** (owner feature ask — closes the "pre-F-02 corpus has no
  skills" onboarding gap). New `POST /api/users/<username>/skills/suggest-from-corpus`
  ([`blueprints/corpus/skills.py`](blueprints/corpus/skills.py)) runs the grounded suggest-skills
  machinery over the candidate's WHOLE career corpus with no job description in view. The
  existing `analyzer.suggest_skills` prompt hard-gates every proposal on "the JD wants X AND the
  corpus evidences X" — with no JD in scope that AND can never fire, so reusing it unchanged
  would have silently returned zero proposals forever. A **new** sibling prompt constant,
  `SUGGEST_SKILLS_FROM_CORPUS_SYSTEM_PROMPT`, and a new function `analyzer.suggest_skills_from_corpus`
  drop the JD condition down to evidence-alone (same grounding discipline, same worked-example
  teaching pattern). **This is a genuine prompt-text addition** — per the merge-train
  instructions, this branch deliberately did **not** bump `PROMPT_VERSION` itself; the
  merge-train orchestrator assigns the next suffix on landing: `PROMPT_VERSION` `2026-07-08.3` →
  `2026-07-08.4` (see `analyzer.py`). Proposals land as pending `Skill` rows
  (`source="llm_proposed"`, dedup case-insensitive against every existing row for the candidate
  incl. retired, mirroring `onboarding/corpus_import.py:_insert_pending_skills`), reviewed via
  the existing approve/deny UI.
- **Application title inference** — owner-approved format (revised mid-branch, see below):
  `Application.title` is now the cleaned **role title only** — no company prefix. A new
  deterministic extractor, `db.build_context._infer_role_title`, strips markdown heading
  markers, U+FFFD/mojibake artifacts, and normalizes whitespace; skips boilerplate-shaped opening
  lines ("About the...", "Who We Are", ...) in favor of the first role-shaped line (conservative
  keyword heuristic); fails open to the cleaned first line. Company is unchanged — it stays
  exclusively in `Application.company` (F-15) and its existing card/detail-modal rendering; an
  earlier draft of this fix composed `"Company — Role Title"` into the title string, but the
  owner redirected mid-branch (the company column already renders company, so the composition
  would have duplicated it) — reverted before landing. Applied at creation
  (`db.build_context.build_context_set_from_db`). **Backfill** (owner-approved, manual only):
  [`scripts/backfill_application_titles.py`](scripts/backfill_application_titles.py) rewrites
  ONLY rows whose current title still equals the raw first-line inference (hand-edited titles
  untouched); dry-run by default, `--apply` to write. Never wired to a route, a migration, or app
  startup. A small CSS polish accompanies this (owner request): `.application-card-company` gets
  a modest weight/letter-spacing lift (`static/style.css`) so it reads as scannable metadata
  without out-competing the (now role-only) title — verified the roster card, pipeline row, and
  application detail modal all already render company alongside title/role consistently
  (conditional on `company` being detected, same fail-open contract as before).
- **Corpus date-rail propagation** — `_saveExperienceField` (`static/app.js`) now calls
  `refreshCorpusSummaryFor(expId)` after a successful field PUT, and `refreshCorpusSummaryFor`
  now also refreshes `.corpus-card-dates` (previously only company/title/meta) — editing an
  experience's start/end date inline used to leave the collapsed card header showing the stale
  date until a full page reload.
- **Surgical-refine resilience** — `_submitSurgicalRefinement` (`static/app.js`) had a
  try/finally with no catch, so a transient failure on `POST /api/validate-refinement`
  propagated uncaught and the UI just reset silently. Added a catch mirroring the legacy refine
  path: `reportError('Refine', ...)` + a "NOT EXECUTED" entry in the shared refinement-history
  panel. The note stays in the input box and the button re-enables, so retrying is just clicking
  Refine again.
- **Roster search threshold** — the searchable candidate roster (`static/app.js`) appeared at
  `_candidateRoster.length >= 2`; raised to `>= 6` so it shows only once there are enough
  candidates that search actually helps (a couple of names scan fine in the plain `<select>`).

Tests: `tests/test_proposal_review_bridge.py` (bridge routes, both bulk routes, idempotency, the
0014 migration's 49-orphan shape + a genuinely-pending control row + migration idempotency);
`tests/test_suggest_skills_from_corpus.py` (analyzer function + route: dedup incl. retired, empty
corpus short-circuit, no `<analysis>`/JD gate in the prompt); `tests/test_build_context_db.py`
(the `_infer_role_title` extractor: markdown/mojibake/boilerplate/fallback + the role-only
creation-time integration); `tests/test_backfill_application_titles.py` (eligibility safety
rule, dry-run, apply, idempotency); `tests/ux/regression/test_20260708_review_surface_and_flows.py`
(date-rail propagation + refine-failure error/retry, both LLM-free); the roster-threshold change
updates `tests/ux/regression/test_20260707_recruiter_roster_pipeline.py` (adds a
below-threshold-hidden case, pads the above-threshold case to 6 candidates).

### Fix: output identity integrity, MM-YYYY dates, education/certs projection, dropped-role telemetry, ATS scrub (`fix/output-identity-and-dates`, 2026-07-08)

Five independently-verified output-fidelity bugs, all bound by the same D3
"download == preview" invariant. Highest severity: a real user saw a website
in a **downloaded** résumé that was in neither their corpus nor their preview.

- **Identity-field divergence (highest severity).** `/api/generate` replayed
  ANY saved `context_*.json` with no schema/version check, including
  pre-corpus-era files whose identity was frozen by the now-dead
  `hardening.build_context_set`, and `candidate.online_profile_text`
  (scraped web presence) was an ungoverned source the corpus-mode GROUNDING
  rule never excluded from identity/header fields. Fixed the class, not the
  instance:
  - **(a) Deterministic identity override** — `json_resume.apply_identity_override()`
    unconditionally re-resolves `basics.name/email/phone/url/profiles` from
    the live `Candidate` DB row, overriding whatever the LLM markdown or a
    stale context carried. Wired into `generator.generate_resume()` (all
    three output formats) AND into `blueprints/generation.py`'s
    `_apply_output_fidelity_fixes()`, which corrects `result["resume_content"]`
    itself — the text also cached as `last_generated_resume` and served back
    as the WYSIWYG live preview — so a download and the in-app preview can
    never disagree. The frozen-composition path is untouched by design:
    `corpus_to_json_resume.build_json_resume_from_corpus` already resolves
    identity from the DB at build time.
  - **(b) Pre-corpus context-shape guard** — `/api/generate` and
    `/api/generate/stream` now reject (409, `needs_reanalyze: true`) a
    context missing `application_id`, the reliable corpus-era marker every
    `/api/analyze` call has stamped since Phase C.4.
  - **(c) Prompt tightening** — the corpus-mode GROUNDING rule
    (`analyzer.py`'s `_build_generate_prompt`) now states explicitly that the
    name and header contact line come ONLY from `<candidate_profile>`, never
    `<candidate_web_presence>`. `PROMPT_VERSION` bumped `2026-07-08.2` →
    `2026-07-08.3` (generate-prompt-only; analyze/clarify unchanged).
- **Dates — owner-decided `MM-YYYY` format.** One canonical
  presentation-boundary helper, `json_resume.format_date_range()` (+
  `format_month_year()`), renders `MM-YYYY`, ranges `MM-YYYY – MM-YYYY`, and
  open-ended roles as `MM-YYYY – Present` (previously nothing rendered
  "Present" for a missing end date, and raw ISO `YYYY-MM` passed through
  verbatim everywhere). Used by `generator.py` (.docx), `json_resume_to_markdown`
  (.md), and every bundled persona template (classic/modern/spacious/tech)
  via a `date_range` Jinja global registered in `pdf_render.py` — so preview,
  PDF, and download can never disagree on date formatting. Storage stays ISO.
- **Education/certificates preview-parity gap-close.**
  `corpus_to_json_resume.py` hardcoded `education: []` / `certificates: []`
  even though both DB tables were already populated and already consumed by
  the corpus-mode generate prompt (`db/build_context.py`). New
  `_collect_education()` / `_collect_certificates()` (mirroring
  `_collect_skills`'s active/display_order shape) close the gap; the stale
  deferred-scope note in `blueprints/corpus/career_assets.py` is updated.
- **Dropped-role import telemetry.** `onboarding/extract_experiences.py`'s
  `_normalize_experience()` used to collapse a role with no parseable start
  date to a fully-blank sentinel, discarding the company/title/bullets the
  LLM DID extract. It now blanks only `start_date` (still the drop signal)
  and retains everything else; `onboarding/corpus_import.py`'s `ImportReport`
  gained `experiences_dropped` / `dropped_experiences`, surfaced in the
  ingest response, the corpus UI ("N roles could not be parsed... review and
  add manually"), and the CLI report.
- **ATS character scrub (owner-decided policy).** New
  `json_resume.scrub_ats_unsafe()` recursively strips `[ ] { } " ` ` `
  (backtick) from every rendered string leaf; `< >` only as tag-shaped pairs
  (`<[^<>]{1,30}>`), so `<50ms` survives untouched. Every changed string is
  recorded into `meta.sartor.ats_scrubbed`. Called at the two finalization
  choke points — `generator.generate_resume()` and
  `corpus_to_json_resume.build_json_resume_from_corpus` — covering freeze,
  preview, and every download in one.

Real-LLM validation of the prompt change (sandbox candidate + temp DB, no
repo data touched): a candidate with no `website_url` but `online_profile_text`
containing a decoy website + email produced a résumé header with the
candidate's real name/email only — the decoy never appeared — while grounded
generation (verbatim corpus bullet + metric) still worked. Cost: **$0.0306**
(1 Sonnet 5 call), well under the $0.10 estimate. See
[`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) for the full record.

### Fix: eval-run resilience + annotate flow + migration data-safety (`fix/eval-pipeline-and-data-safety`, 2026-07-08)

Four pre-existing bugs surfaced by the owner's E2E walkthrough triage (root-caused by a
read-only investigation, not new regressions from any recent branch — in particular, not
F-11): a scorer failure could abort a whole paid eval run, the pinned MiniCheck loader could
hard-crash on low-RAM hosts, the Annotate tab's bootstrap-complete handler could leave the
editor stuck hidden, and two 2026-05-29 migrations could silently cascade-delete a real user's
entire application/generation history on upgrade. All four fixed; each had zero prior test
coverage for the specific failure path (confirmed by reverting each fix in isolation and
re-running its new test, which then fails exactly as described below).

- **Eval run degrades, not aborts, on grounding-scorer failure**
  (`evals/runner.py`) — `run_grounding_signals(...)` sat outside the per-fixture
  `try/except` (which closes before the metrics/grounding block), so any scorer
  exception propagated out of `run_suite()` and hit the worker-thread `except Exception`
  handler in `blueprints/diagnostics.py`'s `/api/eval/run` SSE route, turning one scorer
  hiccup into a failed run — discarding the already-completed, already-paid
  analyze/clarify/generate/judge work for every fixture. Now wrapped per-fixture: a scorer
  exception degrades `grounding_signals_data` to `None` (skips `_enrich_groundedness`,
  records still write with `status: "ok"`), emits an `_emit("warning", ...)` progress event,
  and the loop continues — the same contract `evals/bootstrap.py`'s
  `build_bootstrap_document()` already uses (EV-2, window-8.5-findings). The dashboard's
  Quality-tab streamer (`dashboard/templates/dashboard.html`) gained a `warning` case in
  `describe()` mirroring the bootstrap-wrapper JS's existing `⚠` rendering.
- **MiniCheck loader hardening** (`evals/grounding_signals.py`) — the pinned minicheck
  commit's `Inferencer` hardcodes `device_map="auto"` on
  `AutoModelForSeq2SeqLM.from_pretrained` for `flan-t5-large` with no `offload_folder` or
  `device` kwarg exposed through `MiniCheck.__init__` (verified against the installed
  package's actual source, not assumed) — on a RAM-constrained host, accelerate's auto
  device-map planning can raise before the model even loads. `_load_minicheck_scorer()` now
  runs inside `_hardened_device_placement()`, a scoped monkeypatch of that one
  `from_pretrained` classmethod that forces `device_map="cpu"` (skips the GPU+CPU+disk
  auto-plan entirely) and sets an `offload_folder` fallback for genuinely constrained hosts —
  a no-op on hosts with enough RAM, always restored on exit (success or exception). The EV-1
  pin is untouched.
- **Annotate tab: bootstrap-complete now loads the editor** (`dashboard/templates/dashboard.html`)
  — the bootstrap-`done` and seed-export handlers set `$('fixtureSelect').value = slug`
  directly, which never fires `change` (and re-picking the same value manually can't fire it
  either), so the editor stayed hidden until an unrelated interaction happened to trigger a
  reload. Both handlers now call `loadFixture(slug, user)` directly after setting the select.
- **Migration data-loss fix (forward-protection P0)** (`db/migrations/versions/0006_*.py`,
  `0007_*.py`) — both used `op.batch_alter_table("application", recreate="always")` to add
  columns / swap the `status` CHECK constraint. `application` is a CASCADE parent of
  `application_run`; with the app's `PRAGMA foreign_keys=ON` connect-time default active
  during migrations too (the listener is registered on the `Engine` class, so Alembic's engine
  gets it too), the recreate's internal `DROP TABLE application` cascade-deleted every run +
  its audit trail on any DB that already had them — reproduced end-to-end (downgrade → seed
  app+run → upgrade → run count 1→0). Column adds now go through native `op.add_column` (no
  batch — the PX-02 precedent already used in migrations 0010/0011/0013). The CHECK-constraint
  swap can't go through native `ALTER TABLE` at all (SQLite has none for CHECK) and disabling
  `PRAGMA foreign_keys` around the batch recreate does NOT work either — empirically confirmed
  the pragma is a no-op once Alembic's `env.py` has opened its single wrapping transaction for
  the whole migration run. New `db/migrations/_sqlite_check_constraint.py` rewrites the CHECK
  clause by editing `sqlite_master.sql` in place (`PRAGMA writable_schema` + a
  `PRAGMA schema_version` bump) instead of rebuilding the table — no `DROP TABLE` is ever
  issued against the parent, so there's nothing for the cascade to fire on, and the chain
  reaches `head` successfully even on a DB with existing run history (verified: children
  survive, `PRAGMA integrity_check` and `PRAGMA foreign_key_check` stay clean, for a fresh
  empty DB, a pre-0006 DB with seeded history, and an already-at-head DB re-run).

### Chore: cross-document link checker + repo-wide link sweep (`chore/doc-link-sweep`, 2026-07-08)

Carry-forward ledger item #7 / RELEASE_ARC §Phase 4.8 (ii): `wiki-lint` only checks
`docs/wiki/` structural integrity, so the plain `[text](path)` links the extract-don't-restate
move multiplied across the contract docs + `docs/governance/` (and the rest of the doc set)
were ungated pointer-rot risk. **Deterministic, stdlib-only — no new dependency.**

- **New checker** — [`scripts/check_doc_links.py`](scripts/check_doc_links.py): resolves every
  relative `[text](path)` / `[text](path#anchor)` markdown link in all 190 tracked `*.md` files
  (repo-wide, including `docs/wiki/*.md` — it uses the identical relative-link convention as
  every other doc) against its containing file, verifies the target exists, and — for `.md`
  targets with a `#fragment` — verifies a matching heading via a conservative GitHub-anchor
  slugger (handles the repo's real double-hyphen cases from stripped `&`/`—`/`→`). Separately,
  scoped to `docs/governance/*.md` + `AGENTS.md` + `CLAUDE.md`, verifies the **file** named by
  each `` `path:SYMBOL` ``/`` `path:LINE` `` cite exists (existence only — line-drift checking
  stays `wiki-lint`'s job). Skips external URLs, fenced code, literal backtick-quoted link
  syntax examples, and gitignored targets; two narrow documented `(file, target)` exclusions
  cover a generic `[text](path)` prose idiom and a destination-relative insertion-template doc.
- **Wired into the existing gate, not a new CI job** —
  [`tests/test_doc_links.py`](tests/test_doc_links.py) re-runs the checker as a subprocess and
  asserts exit 0, so it rides `pytest` on every PR (already CI-covered).
- **The sweep** — fixed every link/cite the checker found: a systemic `../../` depth bug in 6
  `commands/`/`agents/` files (pre-dated the plugin-activation move to repo root), 4 stale
  relative-depth links (`docs/dev/RELEASE_ARC.md`'s `excellence-walk/` refs, a design doc's
  nested review-directory refs, a stale `.claude-plugin/agents/` path), 3 dangling `README.md`
  anchors from a since-removed "Claude Code Plugin" heading (retargeted to the current
  `#architecture--developer-reference` section) and 4 from a never-landed `#cost` anchor
  (retargeted to `#install`, the closest live section), and 3 historical entries in
  `CHANGELOG.md`/`RELEASE_CHECKLIST.md`/an archived UX audit that named a since-renamed file —
  de-linked (kept as plain text) rather than retargeted, so the historical record stays accurate.

### CI: UX/a11y tier as a CI job, required-check ready (`ci/ux-a11y-required-check`, 2026-07-08)

PX-25 (2026-06 product-excellence review, `F-qe-rel-01` P0): the browser-driven
UX/a11y/PDF tier (`pytest -m ux` + the axe a11y gate + the PDF end-to-end
renders) ran on the maintainer's laptop only — `ci.yml` had no `playwright
install`, so the tier was silently collected-then-skipped in CI (documented as
a known gap in `ACCESSIBILITY.md`). This lands the CI job the tier needed; the
GitHub "required status check" flip is a separate, owner-gated repo setting
that cannot be configured until the `[HUMAN]` GitHub-repo-creation step
(RELEASE_ARC Phase 4) — see the activation note below.

- **New `ux` job in `.github/workflows/ci.yml`**, separate from the `quality`
  matrix so the fast py3.11–3.13 lint/type/unit gate isn't slowed by a
  Chromium install: `pip install -e '.[dev]'` → `python -m playwright install
  --with-deps chromium` → `pytest -m ux`. Single Python version (3.12, the
  middle of the `quality` matrix's 3.11–3.13 range) — Playwright/browser
  behavior isn't Python-version-sensitive, so matrixing would ~triple runtime
  for no coverage gain. `needs`/concurrency wiring between jobs is
  deliberately left undecided (PX-43, Phase 7 — out of scope here).
- **Caching:** `actions/setup-python`'s built-in `cache: pip` (same as
  `quality`) plus a new `actions/cache` step keyed on the installed
  Playwright version, caching `~/.cache/ms-playwright` (the ~150MB Chromium
  binary) — the slowest step in the job on a cache hit. `actions/cache` is
  GitHub-maintained, the same trust tier as `actions/checkout`/
  `actions/setup-python` already used in this file. OS-level Playwright deps
  (`install-deps`) still run every time — ephemeral runner VMs don't preserve
  apt packages regardless of the browser-binary cache.
- **Flake policy (HONEST, not masking) — no automatic retry.** The suite's
  known flake class (a Compose-wizard settle race under heavy LOCAL
  multi-suite concurrency) was root-caused and fixed 2026-07-06
  (`fix/compose-settle-bg-reload` — see that entry below); every recurrence
  since has reproduced ONLY under that concurrent-load condition, always
  green in isolation. A single dedicated CI job running one `pytest -m ux`
  invocation with no sibling suite contending for the same server cannot
  reproduce that precondition, so a retry step here would not be absorbing a
  *known* flake — it would silently re-run under an uncharacterized failure
  mode and report green, which is exactly the masking this policy avoids. If
  the `ux` job fails in CI, treat it as a real signal and investigate first;
  a genuinely new CI-only flake class would need its own scoped, documented
  retry, not a pre-emptive blanket one. Full rationale recorded as a comment
  block in the workflow itself.
- **PDF slice included.** RELEASE_ARC/RELEASE_CHECKLIST call this the
  "UX/a11y/PDF tier", but `pytest -m ux` alone doesn't cover the PDF
  end-to-end tests — the 4 tests in `tests/test_pdf_render.py` are marked
  `slow` only. The job's last step runs `pytest -m "slow and not ux"` too,
  reusing the Chromium install already done for the `ux` step rather than
  standing up a second job for 4 tests — so the tier's name is now accurate
  in CI, not just on the maintainer's machine.
- **Activation note (owed at the `[HUMAN]` GitHub-repo-creation step):** a CI
  job existing does not make it a "required check" — that's a GitHub repo
  setting (Settings → Branches → branch protection rule for `main` →
  "Require status checks to pass before merging"), unavailable until the
  repo exists. When it does: mark the `ux` job's check ("UX / a11y / PDF
  (Playwright, py3.12)") AND the `quality` matrix's 3 checks required. Do
  NOT mark `eval-smoke` required — it's label-gated (`eval` label only), so
  a required-but-conditional check would block every unlabeled PR forever.
- **Docs/workflow only** — no dependency change (`playwright` is already a
  pinned hard dep; `actions/cache` is a workflow-file action, not a Python
  package), no route/prompt/migration; `PROMPT_VERSION` unchanged.

### Feat: portable enforcement core — one guard implementation, three consumers (`feat/portable-enforcement-core`, 2026-07-08)

Lifts the six portable dev-loop guards (`require-feature-branch`, `block-merge-to-main`,
`block-secrets`, `route-security-lint`, `ruff-changed`, `validate-context`) out of
standalone `.claude-plugin/hooks/*.sh` bash and into a tool-agnostic shared core, so the
rules hold for plain `git commit`/`git merge`/`git push` too, not only inside a Claude
Code session (RELEASE_ARC §Phase 4.8 public-prep item (i); `docs/governance/
enforcement.md` "gate" side of the gate/witness/tribal split).

- **One implementation per guard** in `scripts/enforcement/guards/` (pure `decide()`
  functions, stdlib-only). **Three consumers**: the Claude Code PreToolUse adapter
  (`scripts/enforcement/adapters/claude_hook.py`, invoked by thin wrappers left at the
  same `.claude-plugin/hooks/*.sh` paths — `.claude/settings.json` wiring untouched); the
  native git hooks at `.githooks/` (`pre-commit`, `pre-merge-commit`, `pre-push`), opt-in
  per clone via `git config core.hooksPath .githooks` (see `.githooks/README.md` — **not**
  activated automatically); and a CI backstop step (`scripts/enforcement/ci_backstop.py`,
  a repo-wide secrets scan wired into `.github/workflows/ci.yml`, itself still latent
  until the git remote activates, same as the rest of that workflow).
- **Fixes both defects filed against `block-merge-to-main`** (RELEASE_CHECKLIST.md
  "Portable-enforcement-core migration" ledger row, Train-1 note, 2026-07-07): (i) the
  `\bgit merge\b` pattern false-positived on read-only `git merge-base`/`git merge-tree`
  (the `\b` boundary is satisfied at the `e`→`-` transition) — fixed with a negative
  lookahead; (ii) the dominant-direction check resolved HEAD via a bare
  `git rev-parse --abbrev-ref HEAD`, which runs in the hook *process's* ambient cwd —
  under parallel-worktree sessions (charter W-1) that isn't guaranteed to be the invoking
  agent's own worktree. Fixed by resolving against the PreToolUse hook-input `cwd` field
  instead. The native `pre-merge-commit`/`pre-push` git hooks never had either bug — git
  itself supplies the real operation and resolves HEAD in the invoking worktree.
- **Plan-mode lifecycle hooks** (`check-plan-approved`, `mark-plan-approved`,
  `cleanup-plan-on-merge`) and the wiki-freshness reminder stay Claude-only, untouched.
- Proven with `tests/test_enforcement_core.py`: a >=3-case-per-guard block/allow/edge unit
  matrix over the pure `decide()` functions, plus an OLD-vs-NEW equivalence harness that
  runs the pre-migration standalone scripts (extracted from git history) side-by-side with
  the migrated wrappers against byte-correct PreToolUse JSON, asserting matching exit
  codes and block-message substance — including two dedicated regression cases proving
  each `block-merge-to-main` defect existed pre-fix and is gone post-fix.
- The PX-29 blocker/witness governance gate (`tests/test_governance_hooks_gate.py`)
  tightened to the new architecture: the six core-delegated blockers now prove their
  reachable exit-2 structurally (the wrapper execs the shared adapter, naming its own
  guard) + behaviorally (the adapter's blocked path returns 2, asserted in-process),
  replacing the literal-`exit 2` grep those wrappers no longer satisfy;
  `check-plan-approved` keeps the literal-text check. Blocker/witness counts and the
  `settings.json` wiring pins are unchanged.

### Feat: clarifications persist to the corpus for cross-JD reuse (`feat/clarifications-to-corpus`, 2026-07-08)

Generation-experience re-architecture — item (c) of the LATER-branch remainder
(D5: [`docs/dev/generation-experience-rearchitecture.md`](docs/dev/generation-experience-rearchitecture.md)
§2 Stage 3 / §3.5 point 3). A clarification the candidate confirms while
working one JD now informs Compose content drafting for every LATER JD, not
just the one it was answered under.

- **`db.build_context.build_context_set_from_db`** stages a new
  `context_set["prior_clarifications"]` field — every `clarification` DB row
  for the candidate (cross-application by design; see `Clarification`'s
  docstring) EXCEPT the just-created application's own (which can't own any
  yet at build time, so no origin filter is needed), most-recent-first, capped
  at 40. Corpus-mode only; legacy (file-based) contexts are unaffected.
- **The three Compose CONTENT DRAFTING calls** (`analyzer.draft_positioning_summary`,
  `draft_gap_fill_bullets`, `suggest_skills`) each read
  `context_set["prior_clarifications"]` and render it as a `<prior_clarifications>`
  prompt block, distinct from the existing THIS-application `<clarifications>`
  block. `draft_positioning_summary` and `suggest_skills` treat it as full
  grounding source material (same posture as `<clarifications>`) — a confirmed
  fact from an earlier application is real evidence for this one too.
  `draft_gap_fill_bullets` keeps it CONTEXT-only: a proposed bullet's cited
  evidence must still come from `<career_corpus>`, unchanged.
- **Grounding widened, surgically.** `hardening.assemble_source_union` (the
  deterministic 3-source grounding metric) now also folds in
  `prior_clarifications` answers, so it scores against the same source union
  the Compose prompts are shown — it no longer over-reports legitimately
  cross-JD-sourced content as fabrication. The legacy `generate()` prompt is
  byte-identical; the widened carve-out is scoped to the three drafting calls
  only (AGENTS.md "LLM prompts").
- `PROMPT_VERSION` bumped `2026-07-08.1 → 2026-07-08.2` (the three drafting
  system prompts changed text; the legacy résumé-body `generate()` prompt is
  untouched).
- Real-LLM validated end to end on a throwaway sandbox candidate + temp DB
  (never touched `configs/`/`output/`/`resumes/`): answered a clarification
  under a Platform Engineer JD, then ran an SRE JD for the same candidate —
  the drafted summary wove in the cross-JD fact, `suggest-skills` proposed
  3 new skills evidenced ONLY by the clarification (corpus-evidenced skills
  still cite a bullet id), `draft-gap-fill` correctly proposed ZERO bullets
  from the clarification alone (its evidence-must-be-corpus rule held), and a
  second unrelated candidate saw zero prior_clarifications (candidate-scoped).
  9 real calls, $0.11 total. See `evals/TUNING_LOG.md` for the full record.

### Feat: WYSIWYG as source of truth — in-app edits are the document (`feat/wysiwyg-source-of-truth`, 2026-07-08)

Generation-experience re-architecture item (b) (D4, the LATER-branch remainder
tracked in the carry-forward ledger): closes the "preview != download" window
that existed between typing an edit into `#resumePreview` / `#coverLetterPreview`
and the next unrelated action (refine/iterate) that happened to persist it.

- **`POST /api/applications/<id>/preview-edited` (new route, `blueprints/templates.py`).**
  The preview-side twin of the existing `/api/download-edited`: content in,
  rendered HTML out, NOTHING persisted (no context write, no DB write). Renders
  résumé markdown through the same `md_to_json_resume` → `render_html_string`
  pipeline `save_edits` already uses to recompute its cache, and cover-letter
  markdown through `render_cover_letter_html` — the identical deterministic
  pipelines the cached preview routes use, just applied to live POSTed text
  instead of a stored snapshot.
- **`static/app.js`** wires a debounced (300ms, matching Compose's autosave
  cadence) `input` listener on both editors (`_wireLiveEditPreview` /
  `_refreshLiveEditPreview`) that POSTs the live text to the new route and
  swaps the styled iframe's `srcdoc` — so the visible Step-6 preview never lags
  behind what Download would produce. The existing "Use edits as baseline"
  edit-detection modal and `/api/save-edits` persistence path are UNCHANGED —
  this is a pure display refresh, not a new autosave.
- **Cover-letter preview precedence fix** (`preview_cover_letter_html`): the
  route now prefers a saved `edited_cover_letter_text` over the un-edited
  `last_generated_cover_letter`, mirroring the résumé preview's existing
  `edited_resume_text` precedence (D6(a)). Previously the cover-letter preview
  ignored a saved edit entirely — `/api/save-edits` persisted it but the
  styled iframe kept showing the pre-edit AI text forever.
- **DB durability fix** (`_persist_edited_text_to_db`, `blueprints/generation.py`):
  `save_edits` now mirrors a corpus-backed edit onto
  `ApplicationRun.edited_resume_text` / `edited_cover_letter_text` — columns
  the model already documents as "every generated and edited artifact" and
  `_build_resume_state` / `get_application`'s `has_edits` already READ, but
  that were never written. Without this, an edit survived only in the
  context_*.json sidecar: resuming an application after that file was cleaned
  up silently reverted Step 6 to the un-edited AI text. Best-effort (mirrors
  the sibling `_persist_run_persona`) — a DB hiccup never fails the save.
- Tests: `tests/test_live_preview_route.py::TestPreviewEditedRoute` (renders
  résumé/cover-letter content matching the editor, matches the persisted
  WYSIWYG preview for the same content — the transitive download==preview
  proof, nothing persisted, validation/ownership/404s) +
  `::TestCoverLetterPreview::test_edited_text_wins_over_last_generated` +
  `tests/test_app_iteration.py::TestSaveEditsRoute` (DB row persists, missing
  run row doesn't fail the save, legacy contexts skip the DB write).
- No prompt text changed — `analyzer.py` untouched; `PROMPT_VERSION` stays at
  `2026-07-08.1`.

### Feat: regenerate gap-fill + durable retirals (`feat/regenerate-gap-fill`, 2026-07-08)

Generation-experience re-architecture LATER-branch remainder item (d) (see
[`docs/dev/generation-experience-rearchitecture.md`](docs/dev/generation-experience-rearchitecture.md)
§4/§6 and the RELEASE_CHECKLIST carry-forward ledger). Phase 3
(`fix/compose-frozen-composition`) shipped Compose gap-fill drafting +
accept/retire, but retire was TRANSIENT — a re-draft could resurface a proposal
the user had just rejected, and there was no explicit way to ask for a fresh
draft at all.

- **`composition_overrides.retired_gap_fill_keys`** — a durable set of retired
  proposal keys (the existing `sha256(eid|text)[:12]` stable key), written
  directly by `/gap-fill-decide` (retire) alongside dropping the transient
  proposal. Rides `_collectCompositionState()`'s wholesale rebuild like every
  other override key (`accepted_generated_bullet_ids`, `summary_text`, …), so
  it survives a subsequent `/composition` save instead of being silently
  dropped.
- **"Regenerate suggestions"** — an always-visible control above the per-role
  gap-fill lanes (once experiences exist), calling the SAME `/draft-gap-fill`
  route the auto-fire uses. It's a THIRD context-writing firing path
  (alongside the summary draft + skills recommend) and serializes through the
  same `data-compose-bg-pending` counter.
- **Route-level exclusion filter** (`draft_application_gap_fill`, deterministic
  — no prompt change, no `PROMPT_VERSION` bump): a fresh draft filters out any
  proposal whose stable key is in `retired_gap_fill_keys`, OR matches an
  existing accepted `Bullet.source` (`llm_proposed:<key>`) for this candidate
  — so a Regenerate never resurfaces a proposal the user already decided on,
  either way.
- Tests: `tests/test_regenerate_gap_fill.py` (draft-side exclusion filter +
  decide-side durable write + `/composition` GET/POST round-trip, incl. the
  clobber-invariant regression), `tests/ux/regression/test_20260708_compose_gap_fill_regenerate.py`
  (the button + durability across Regenerate + reload + Save-and-continue),
  plus a `retired_gap_fill_keys` case folded into the existing
  `TestGapFillPromptInvariance` byte-identity guard.

### Fix: surgical single-item refinement + richer loop-back (`fix/surgical-refinement-and-loopback`, 2026-07-08)

Generation-experience re-architecture item (a) (the LATER-branch remainder tracked
in the carry-forward ledger, off `fix/compose-frozen-composition`'s minimal interim
loop-back): a corpus-mode refinement note now drafts ONE scoped, grounded change
instead of just pointing the user back at Compose to redo it themselves.

- **`analyzer.draft_surgical_refinement()` (Sonnet, new `DRAFT_SURGICAL_REFINEMENT_SYSTEM_PROMPT`).**
  Reads the CURRENT frozen `approved_composition` (with numeric bullet/role ids)
  and the free-text note, and proposes exactly ONE of: sharpen an EXISTING bullet
  in place (`supersedes_bullet_id`), a genuinely stronger NEW bullet where the
  corpus is silent, a rewritten positioning summary, or — for a broad "rewrite
  everything" ask with no single scoped target — nothing (`target_kind: "none"`,
  falling back to the plain loop-back). Grounded (no invention beyond
  `<current_resume>`/`<clarifications>`, the same posture as `draft_gap_fill_bullets`).
  `PROMPT_VERSION 2026-07-06.3 → 2026-07-08.1` (a new per-call template; the
  generate prompt is unchanged, so legacy + `--suite synthetic` stay byte-identical).
- **Two new routes** (`blueprints/applications.py`): `POST /api/applications/<id>/draft-refinement`
  (a pure read — stages the note + JD, re-validates any id the model returns against
  the candidate's own corpus, never writes to the context file) and
  `POST /api/applications/<id>/accept-refinement` (applies an accepted proposal:
  a pending Bullet + `accepted_generated_bullet_ids`, and — when the proposal named
  a superseded bullet — that bullet folds into `composition_overrides.excluded` too,
  so the composition gains exactly ONE net item; a summary proposal persists into
  `composition_overrides.summary_text`). Both reuse the EXISTING override keys the
  frozen-composition resolver already honors — zero changes to
  `corpus_to_json_resume.py`. Retire never reaches the server (nothing was written
  for a proposal the user hasn't accepted) — the banner dismisses it client-side.
- **The Compose loop-back banner is richer** (`static/app.js`, `.compose-loopback-*`
  in `static/style.css`): `submitRefinement()`'s corpus-mode path now runs the
  existing fact-scope check (`/api/validate-refinement` + `_showRefinementScopeModal`
  — previously skipped in corpus mode), drafts the scoped proposal, and routes to
  Compose with it stashed. `_renderComposeLoopbackBanner()` renders the ACTUAL
  proposed change (old text struck through when superseding, then the new text,
  plus the model's rationale) with Accept/Retire, falling back to the prior plain
  "adjust it yourself" copy when no proposal came back.
- Tests: `tests/test_draft_surgical_refinement.py` (short-circuit + route
  normalization/ownership-revalidation), `tests/test_accept_refinement.py` (bullet
  accept with/without supersede, idempotency, summary accept, validation),
  `tests/test_demo_mode.py::test_draft_surgical_refinement` (demo mode proposes
  nothing — same grounding-safety posture as `draft_gap_fill_bullets`).
- Real-LLM validation: one scoped refinement drafted against a live sandbox
  application (see `evals/TUNING_LOG.md` "surgical-refinement-and-loopback" entry
  for the transcript + telemetry cost).

### Feat: aesthetic coherence — app-native confirms, wizard-first Tailor, optional gap-fill framing, clearer edit gate, honest dev defaults (`feat/ux-w4-aesthetic`, 2026-07-07)

UX-review Wave 4 (P2, aesthetic/interaction polish — `50-oss-polish-plan.md`):
F-07, F-23, F-13, F-14, F-18.

- **F-07 — every native `confirm()` replaced by the app's own modal.** A new
  reusable `cbConfirm(message, opts)` helper (`static/app.js`) + a generic
  `#cbConfirmModal` skeleton (`templates/index.html`) mirror the existing
  `_showEditModal`/`_showRefinementScopeModal` a11y posture (focus trap, Esc,
  backdrop dismiss, focus restored to the trigger); call sites read
  `if (await cbConfirm(...))`. All 10 sites migrated (corpus summary-variant/
  skill/role-intro/title/bullet/experience retire, role merge, corpus-wide
  accept-all, application retire, persona delete). Destructive actions keep a
  destructive-styled confirm button (new `.cb-bg-danger` variant); the
  non-destructive accept-all keeps its confirm (a KW2 high-stakes guard) but
  drops the danger styling. Dialog-handler-dependent tests updated: the KW2
  accept-all UX test no longer needs a `page.on("dialog", ...)` auto-accept —
  it clicks the in-page modal instead.
- **F-23 — the Tailor tab folds the ambient panels behind the wizard.** User
  selection + Prior applications default to a compact/collapsible summary
  (reusing the existing `.cb-panel` collapse mechanism) once a user is
  selected, so the wizard rail is the primary surface instead of sitting below
  a full account switcher + untruncated applications list. The expand/collapse
  choice persists per panel via `localStorage` (`cb_panel_collapsed:<id>`), so
  a returning visitor's own preference sticks. Every existing id/selector is
  unchanged; `PriorAppsPage.open_detail()` (`ui_pages/prior_apps.py`) expands
  the panel first if it's collapsed.
- **F-13 — the Compose gap-fill lane reads as optional.** A subdued "Optional"
  badge on the lane title + a "Optional — add only what fits" lead-in on the
  hint copy. Presentation only — the gap-fill data flow, `bgDraftFiring`
  serialization, and the Compose settle markers are untouched.
- **F-14 — the edit-detection modal uses plain language.** "You edited the
  preview" → "Your edits aren't saved yet"; the body now names each choice's
  effect directly instead of the denser "ground truth" phrasing. Same ids,
  same three choices, same timing (`_gateEditsBeforeAction` already fires it
  at the moment the user acts on a stale preview, not on a delay) — the
  typed-edits-feed-grounding function is untouched.
- **F-18 — honest dev defaults.** `python app.py` still auto-opens a browser
  and runs Flask's debug reloader by default for a local desktop run. A new
  `app._is_ci_or_container()` (checks the `CI` env var and `/.dockerenv`) now
  fills in the off default (no browser open, `FLASK_DEBUG=0`) when NEITHER
  `SARTOR_NO_BROWSER` nor `FLASK_DEBUG` is set explicitly, so a bare
  `python app.py` in a CI job or an ad-hoc devcontainer/Codespace no longer
  surprises with a hung browser-open or a debug traceback. An explicit env var
  always wins over the auto-detection; the shipped `Dockerfile` already sets
  both explicitly, so this only covers runs outside that image.
  `_should_open_browser`'s existing tested 2-arg contract is unchanged — the
  detection only changes what `main()` passes in. Documented in
  `docs/install.md` ("Local development: headless / container / CI runs") and
  the README install section.

No prompt/dep/migration; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched.

### Feat: honest Generate surface — deterministic-assembly copy + reliable server-side download (`feat/ux-w1-generate-surface`, 2026-07-07)

UX-review Wave 1 items F-09 + F-10 (`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`).

- **F-09 — the deterministic Generate is finally said out loud.** On the primary
  corpus-mode path the final Generate is a deterministic assemble of the frozen
  `approved_composition` (`blueprints/generation.py:_frozen_composition` — LLM cost
  front-loaded into Analyze/Compose), but Step 5's copy still read as "another AI
  step". Step 5 now carries a state-aware copy pair (`#generateStepCopyFrozen` /
  `#generateStepCopyLegacy` in `templates/index.html`, toggled by
  `_renderGenerateStepCopy()` on every entry to the step): after Compose's
  Save-and-continue freeze actually lands (`_compositionFrozen` in `static/app.js`,
  set from the freeze POST's success and reset on fresh analysis / new-tailoring /
  prior-app resume — mirroring the server gate's own predicate), the step says
  "Assembled instantly from your approved composition — same input, same résumé,
  no AI variation"; the legacy/fallback LLM path keeps the original ~30–60s framing
  and NEVER gets the determinism claim. The `_HELP_REGISTRY.panelGenerate` (i) entry
  carries the longer both-paths explanation. No prompt or backend behavior change;
  no `PROMPT_VERSION` bump.
- **F-10 — the download can no longer silently fail.** `downloadResume()` /
  `downloadCoverLetter()` used to pull the bytes into a blob and click a synthetic
  `<a>` — the pattern Chrome's multiple-automatic-downloads heuristic could silently
  block on a second download without a fresh gesture, which the Step-6 panel
  *documented in-app* as a known caveat. `POST /api/download-edited` now returns
  JSON `{download_url, filename}` pointing at the existing containment-gated
  `GET /api/download/<path>` (`send_file(as_attachment=True)`), and the client
  follows it as a plain navigation the browser's download manager owns. The
  `download_url` is OUTPUT_DIR-relative (an absolute POSIX path would double-slash
  the URL; Windows paths carry a drive colon); `download_file` re-anchors a relative
  path under OUTPUT_DIR *before* its unchanged `_within` containment gate (traversal
  still 403s — new `TestDownloadFileContainment` cases pin it). Failures surface in
  the shared error modal (`reportError`) — never a silent no-op — and the retired
  Chrome caveat copy is REMOVED from `templates/index.html`. The 2026-05-26
  round-6 diagnostic `console.log`s in the download path retire with the bug they
  were instrumenting.
- **Tests.** `tests/ux/regression/test_20260707_generate_surface_download.py` — the
  deterministic copy shows on the frozen path and is absent on the legacy path (both
  driven through the stubbed wizard), the download is a server-served attachment
  (`download.url` is `/api/download/…`, not a `blob:`), and a forced failure opens
  the error modal. `tests/test_persona_routes.py` — download-edited's new JSON
  contract + the four `download_file` containment cases (relative serve, relative
  traversal 403, legacy absolute serve, absolute escape 403).

### Feat: recruiter tier — candidate roster, cross-candidate pipeline, house templates (`feat/ux-w2-recruiter`, 2026-07-07)

UX-review Wave 2 (`docs/dev/reviews/2026-07-ux-review/50-oss-polish-plan.md`) —
F-08 / F-17 / F-16. The multi-candidate data model already supported all of
this; this branch is presentation only, layered on the existing per-user
model without breaking any existing route contract.

- **F-08 — candidate roster.** The flat username `<select>` (`#userSelect`)
  is still the mechanism every flow keys off of, but it now has a searchable
  roster surface above it (`#candidateRoster`): each candidate's display
  name, latest target role/company, and a per-status application-count
  summary. Clicking a card just sets the `<select>` and fires the same
  `onUserSelect()` every other selection path uses — `currentUser` semantics
  are unchanged. Hidden for single-candidate installs (shows once 2+
  candidates exist) so the job-seeker experience is undisturbed.
- **F-17 — cross-candidate pipeline board.** A new read-only **Pipeline**
  top-level tab: every candidate's applications grouped into the five
  canonical lifecycle-status columns (draft / submitted / interview /
  rejected / withdrawn). Clicking a row switches the selected candidate and
  hands off to the Tailor tab on that application.
- **F-16 — house templates.** Personas stay per-candidate (no account-level
  scope, no schema change) — the smallest honest fix is a one-click
  **COPY TO CANDIDATE** action on an owned persona card
  (`POST /api/personas/<id>/copy`) that copies the `.docx` + regenerates its
  HTML/CSS preview companion into the target candidate's own template list,
  instead of re-uploading by hand for every candidate.
- **New aggregate endpoint** — `GET /api/candidates/roster`
  (`blueprints/users.py:candidate_roster`) backs both F-08 and F-17 in ONE
  response: exactly two DB queries regardless of candidate/application count
  (one `Candidate` `IN`-query, one `Application` `IN`-query), guarded by a
  constant-query-count regression test
  (`tests/test_users_routes.py::TestCandidateRoster::test_avoids_n_plus_1_query_growth`),
  mirroring the `list_applications` selectinload + grouped-count discipline.
- `copy_persona_to_candidate` carries the full `_safe_username` +
  `secure_filename` + `_within` guard sequence (containment + traversal
  tests in `tests/test_persona_routes.py::TestCopyPersonaToCandidate`); the
  committed route-containment gate (`tests/test_route_containment_gate.py`)
  stays green.

### Feat: one home per section — corpus skills/education/certifications editors + honest Settings fields (`feat/ux-w1-skills-education`, 2026-07-07)

UX-review Wave 1, F-03 + F-04 (`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`).
Both findings were SHARPENED during the review's verification pass, and the
F-02 skills-import fix that just merged to `main` changed the F-03 landscape
further (résumé import now also feeds the corpus Skill rows), so this branch
re-verified both against current code before designing a fix.

- **F-03 — one home for Skills.** The Settings drawer's flat Skills field
  is a ONE-TIME seed into the corpus (`onboarding/corpus_import.py`), not a
  permanent "legacy mode": `blueprints/analysis.py` confirms Phase C.4 already
  removed the file-based analyze/generate path for every user — everyone is
  corpus-backed once `_get_or_provision_candidate` has run once (on the first
  Analyze, or any Career-corpus write). So the real per-candidate state is
  pre-provision (flat field is still the only source of truth — nothing to
  point at yet) vs. post-provision (corpus Skill rows are authoritative, and
  the flat field silently does nothing). `GET /api/users/<u>/config` now
  returns `needs_onboarding` (does a Candidate DB row exist yet — the same
  flag `/api/users/<u>/experiences` etc. already expose) so the frontend can
  tell the two states apart. Chose the smallest honest fix: pre-provision, the
  live input renders unchanged; post-provision, it's replaced by a labeled
  "Managed in your Career corpus now… Go to Career corpus →" pointer that
  switches to the Corpus tab. No live mirror (extra fetch, staleness risk for
  no real benefit over a link) and no automatic data migration between the two
  homes — only the existing one-time config-seed import.
- **F-04 — a real corpus editor for Education + Certifications.** The
  `Education`/`Certification` DB tables already existed and were already
  consumed (`db/build_context.py` reads both, ordered by `display_order`, into
  the synthesized corpus-mode résumé the analyze/generate prompts see) — the
  gap was UI-only. Added 8 routes (`blueprints/corpus/career_assets.py`, list/
  create/update/delete × 2 entities, candidate-scoped via `_safe_username`,
  DB-only so no filesystem containment applies) and a matching Career-corpus
  editor section for each, reusing the Skills editor's row chrome
  (`.summary-variant-row` / `.corpus-action-btn`) rather than inventing a new
  component family. Neither entity gets a pending-review/LLM-proposal
  lifecycle (the DB models carry no `source`/`is_pending_review` column — a
  human types these directly). Delete always soft-retires (`is_active=0`,
  already on both models) — never hard-deleted, matching the project's
  "nothing hard-deleted" promise. Reorder: since neither the Skills nor
  Summary-variant editors have visible reorder controls to copy, added a small
  swap-with-neighbor ↑/↓ affordance (`.reorder-controls`/`.reorder-btn`,
  reused from the Compose bullet-list's keyboard-reorder styling) that PUTs
  both affected rows' `display_order` immediately. The Settings drawer's flat
  Certifications/Education fields get the exact same F-03 pointer treatment.
- No data migration: the flat config fields and the corpus rows stay two
  independent homes, reconciled only by the existing one-time import — never
  synced automatically, per the review's explicit scope.

### Feat: first-run flow — calm Analyze + guided landing + display-name-first + application company capture (`feat/ux-w1-first-run-flow`, 2026-07-07)

UX-review Wave 1 "first-run delight" slice — F-12 / F-06 / F-05 / F-15 from
`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`.

- **F-12 — the Analyze screen leads calm.** `_renderAnalysis` (static/app.js) now
  opens with the F-01 coverage block (heading, score bar, `.score-note` explainer —
  preserved verbatim), then a **"Where to Focus"** verdict line + up to three actions
  derived **deterministically from the payload** (top missing keywords + top
  comparison gaps, backfilled from the analyzer's own suggestions — no new LLM call,
  no prompt change, no `PROMPT_VERSION` bump). Everything else (skill chip clouds,
  hidden qualities, matched/could-add keyword lists incl. the verbatim "Keywords You
  Could Add" heading, comparison, suggestions, placement, strategy) folds into a
  native `<details id="analysisDetails">` "Show full analysis" disclosure, collapsed
  by default. ATS warnings (legacy path only) stay above the fold.
- **F-06 — the post-create tab jump is explained.** Smart-landing an empty-corpus
  user onto Career corpus now fires a one-time `tourCorpusLanding` help modal
  ("Let's build your corpus first") via the existing `_HELP_REGISTRY` +
  `cb_help_seen:` primitive — no new modal machinery; suppressed by default in the
  UX suite like every other auto-firing stop (`_TOUR_STOP_BLOCKS`).
- **F-05 — display-name-first new-user form.** Full name is the first field and gets
  focus; typing it live-derives a username slug (lowercased, hyphenated, diacritics
  stripped — `_slugify`) into the still-visible, still-editable username field with a
  "this is your storage key" hint. A manual username edit stops the auto-derive for
  that form session. Username remains the storage key; `POST /api/users` payload and
  validation (`secure_filename`, required markers) are unchanged.
- **F-15 — applications capture company at creation.** `build_context_set_from_db`
  (db/build_context.py) stamps `Application.company` via the new
  `_infer_application_company` — `hardening.extract_company_terms(jd_text)` (the
  deterministic, fail-open F-01 detector), longest term wins deterministically,
  title-cased for display; `None` on a miss (prior behavior). The applications card,
  detail modal, and editable save path (#24 `PUT /api/applications/<id>/meta`)
  already surfaced company — no migration needed either: `Application.company` has
  existed since migration 0001.
- Tests: `tests/ux/regression/test_20260707_first_run_flow.py` (progressive
  disclosure collapsed/expandable + F-01 preservation; one-time transition modal via
  the name-first create path; slug derivation/manual-edit-wins/re-arm; application
  card shows the captured company) + `TestInferApplicationCompany` and two
  capture-wiring cases in `tests/test_build_context_db.py`.

### Feat: demo mode — run without an API key (`feat/ux-w3-demo-mode`, 2026-07-07)

UX review F-19 (`docs/dev/reviews/2026-07-ux-review/40-friction-register.md`): a
technical evaluator had no way to see the product without a billed Anthropic key.

- **Activation.** `SARTOR_DEMO=1` (env) is the single source of truth
  (`demo_fixtures.is_demo_mode()`); `config.Config.demo_mode` reads it as a
  `field(default_factory=...)` so `create_app()` surfaces it to Flask config
  (`DEMO_MODE`, for the banner) with no extra wiring, while `analyzer.py` checks
  the same env var directly so it keeps working outside a Flask request context
  (evals, onboarding scripts, tests). Demo mode never activates implicitly — a
  missing/blank key alone is unchanged (still fails at the first live API call,
  same as always); a real key present alongside the flag still means demo (checked
  before any key lookup, so a demo run can never accidentally spend).
- **Mechanism.** `web_infra.clients._get_client()` returns a `_DemoClient`
  sentinel instead of constructing `anthropic.Anthropic` when the flag is set —
  no key read, no client built. Every one of `analyzer.py`'s 18 public LLM call
  kinds (`analyze`, `analyze_streaming`, `avatar_answer_streaming`, `clarify`,
  `clarify_iteration`, `generate`, `generate_streaming`,
  `generate_cover_letter_against_resume`, `check_refinement_scope`,
  `critique_proposal`, `recommend_bullets`, `recommend_summaries`,
  `recommend_experience_summaries`, `recommend_skills`, `suggest_skills`,
  `promote_clarification_to_bullet`, `draft_positioning_summary`,
  `draft_gap_fill_bullets`) independently short-circuits to a canned response
  before it would ever touch the client, so the sentinel is never dereferenced.
  New product-side module `demo_fixtures.py` (LLM-free, like `hardening.py`)
  holds the canned payloads: the analysis/clarify/résumé/cover-letter story is
  adapted from `evals/fixtures/synthetic/sre-mid-level/` (a coherent JD +
  candidate + analysis, not disconnected scraps); the `recommend_*` family
  selects deterministically from whatever the caller staged on `context_set`
  (never fixture-fixed ids that wouldn't exist in a real corpus); calls needing
  genuine grounded judgment (`suggest_skills`, `draft_gap_fill_bullets`,
  `critique_proposal`, `promote_clarification_to_bullet`,
  `draft_positioning_summary`) return conservative, clearly-labeled no-ops
  rather than fabricated content.
- **Honesty.** A persistent, always-visible banner ("Demo mode — canned AI
  responses, no API calls") renders at the very top of every page while
  `DEMO_MODE` is set (`templates/index.html`, `.demo-mode-banner` in
  `static/style.css`) — never a dismissible toast. Telemetry is suppressed by
  construction, not filtered after the fact: every demo call kind returns
  before it would ever call `analyzer._call_llm`/`_call_llm_streaming`, so
  `logs/llm_calls.jsonl` and the `/_dashboard` cost/latency/reliability stats
  never see a demo row.
- Zero new dependencies; no `PROMPT_VERSION` change (no prompt touched); the
  deterministic modules stay LLM-free.
- Docs: README quickstart + `docs/install.md` gain a "Try it without an API
  key" section.

### Docs: contributor-facing truth pass — reader paths, model routing, eval costs, README polish, dashboard label (`docs/ux-w3-contributor`, 2026-07-07)

UX-review Wave 3 (contributor on-ramp): F-21, F-22, F-20, F-27, F-06d. Doc/copy-level
only — no code-behavior change.

- **F-21 — un-conflate using/developing/extending.** Added a "Three ways to meet
  Sartor" section to `README.md` (front matter, before "What Sartor does") with three
  explicitly labeled reader paths — Use it / Develop on it / Extend it — each pointing
  into the existing doc set; the "Extend it" path scopes the tuning slash commands
  (`/prompt-tune`, `/tune-from-annotations`, …) as Claude-Code-specific (they need the
  `sartor` plugin), distinct from the plugin-independent eval harness CLI.
- **F-22 — model-routing drift (Sonnet 4.6 → Sonnet 5).** Verified current routing
  against `analyzer.py:SONNET_MODEL`/`HAIKU_MODEL` and corrected drifted prose in:
  `AGENTS.md`, `docs/architecture.md` (prose only — the four fenced/linked diagrams
  are known-drifted, scheduled for full replacement in the v1.0.9 docs epic; added a
  one-line staleness note instead of reworking them), `README.md` (also fixed a
  pre-existing tier bug — `clarify()` was listed under "Sonnet"; it runs on Haiku
  4.5), `vision.md`, `docs/PRODUCT_SHAPE.md` (same `clarify()` tier fix),
  `docs/walkthrough.md`, `docs/walkthrough_example.md`, `evals/README.md`,
  `templates/index.html`, `scripts/capture_screenshots.py`, `blueprints/analysis.py`,
  `blueprints/generation.py`, `docs/dev/RELEASE_CHECKLIST.md` (risk-register item).
  Historical/dated artifacts (CHANGELOG entries, `evals/TUNING_LOG.md`,
  `docs/dev/perf/*`, `docs/dev/reviews/**`, `evals/results/baseline_v1.json`,
  `hardening.py`'s intentionally-retained `claude-sonnet-4-6` pricing entry) were
  left untouched — they're point-in-time records, not current-state claims.
- **F-20 — stale eval smoke cost.** The documented "~$0.10" smoke estimate was
  ~3.7× stale post-Sonnet-5 (measured ~$0.37 total / ~$0.12 per fixture in the
  2026-07-07 UX review). Restated as "~$0.35–0.40 under Sonnet 5" in `AGENTS.md`,
  `README.md`, `evals/README.md` (Quick start + Cost considerations table + the
  Tuning-tab 2×-cost gate estimate), the dashboard Quality-tab copy
  (`dashboard/templates/dashboard.html`: help text, `updateCost()`, the `confirm()`
  estimate string), and `blueprints/diagnostics.py`'s route docstring.
- **F-27 — README polish bundle.** Added a `git` prerequisite line to Install; moved
  the `## Install` section up (right after "How it works", before the audience
  sections) for prominence; expanded "ATS" on first use in "What Sartor does";
  softened `docs/architecture.md`'s "read in 5 minutes" claim (no such claim existed
  in the current README — the closest survivor was this one); added a brief
  "formerly Callback" note under the title.
- **F-06d — dashboard "RELIABILITY 0%" tile.** Relabeled the Pipeline-tab tile from
  "reliability" to "error rate" (`dashboard/templates/dashboard.html`) — the tile
  always rendered `error_rate * 100`, so the old label read as catastrophic at a
  glance. No metric/computation change. Updated the tile's `data-title` and the
  `_DASH_HELP.dashPipeline` body text to match.

No test asserted the old copy in any touched file (verified via grep), so no test
changes were needed.

### Fix: installable wheel + python floor + install-doc truth (`fix/packaging-install`, 2026-07-07)

Carry-forward ledger "PyPI wheel not installable" + UX-review Wave 0 F-24/25/26 +
2026-07-efficiency-review PX-42, bundled together per the ledger's own note
("F-24/25/26 ... overlaps the PyPI-wheel item below — fix together").

- **The wheel is now installable.** `create_app()`'s `Flask(__name__)` used to resolve
  `templates/`/`static/` relative to `app.py`'s own directory — correct only when they
  happened to be co-located on disk (a source checkout or `pip install -e .`), and there
  was no `package-data`/`MANIFEST.in`, so a real (non-editable) `pip install sartor` 500'd
  on the first page load. Fixed with the smallest change that makes a real wheel serve,
  not a `sartor/` package restructure:
  - `templates/`, `static/`, `personas/bundled/`, and `docs/wiki/` each got a marker
    `__init__.py` (see each file's own docstring) turning them into tiny data-only Python
    packages, shipped via new `[tool.setuptools.package-data]` globs — narrow and
    explicit (never `**/*`), so `personas/robert/` (a real gitignored per-user upload dir
    sitting right next to `personas/bundled/`) can never leak into a build.
  - `config.py` gains `_package_dir()` (import-based resolution — correct in both
    editable and wheel installs) and exports `TEMPLATES_DIR`/`STATIC_DIR`; `app.py`
    passes them explicitly to `Flask(__name__, template_folder=..., static_folder=...)`
    instead of relying on the implicit default. `blueprints/assistant.py`'s `_WIKI_DIR`
    (the doc-grounded assistant's S1 tier) gets the same `_package_dir`-style treatment,
    locally (matching the file's existing "re-derived locally, never imports app.py"
    precedent). `Config.bundled_personas_dir` is DELIBERATELY left untouched
    (`base_dir`-relative, as before) — many existing tests fabricate an isolated
    fake-bundled fixture under `Config(base_dir=tmp_path)`, and routing it through
    `_package_dir` instead redirected those test writes onto the real, tracked
    `personas/bundled/` files (caught by the fast test lane before landing). No code
    change was needed there anyway: the default `base_dir` is `_PROJECT_ROOT`
    (`config.py`'s own directory), which in an installed wheel IS `site-packages/`, and
    `personas.bundled`'s new package-data ships to `site-packages/personas/bundled/` —
    exactly where the existing `base_dir`-relative arithmetic already looks. The
    dev/editable path for `templates`/`static`/`docs.wiki` is byte-identical (same
    directories, resolved via import instead of `Path(__file__)` arithmetic).
  - Verified end-to-end: `python -m build` → fresh venv → `pip install <wheel>` → app
    started from a directory OUTSIDE the repo with a temp base dir → a real HTTP
    `GET /` returns 200 with the shell HTML (and `/static/style.css` serves), proving both
    halves (path resolution + packaging) together, not just in isolation. The `GATE` step
    in `.github/workflows/release.yml` (added specifically to block publishing until this
    landed) is removed. Publishing itself stays `[HUMAN]`-blocked on an unrelated
    prerequisite (PyPI Trusted Publisher + GHCR, gated on the GitHub repo rename) — see
    `docs/dev/RELEASE_CHECKLIST.md`.
  - New regression test `tests/test_packaging.py` pins the code-level contract (absolute,
    existing Flask folders; the four packages resolve; `py-modules` matches the repo's
    actual root `.py` files; the `requires-python` floor) so a future edit can't silently
    re-break the wheel between the (necessarily manual/scripted) fresh-venv verifies.
- **PX-42 — the python floor tells the truth.** `requires-python` was `>=3.10`, but CI
  (`ci.yml`) only ever tested 3.11–3.13, and `tests/test_docstring_coverage_gate.py` (dev
  tooling) already used `tomllib` (3.11+ stdlib) — a real 3.10 install was untested and
  would fail at *runtime*, not at `pip install` time. Raised to `requires-python = ">=3.11"`
  and dropped the `Python :: 3.10` classifier; `docs/install.md` "Python 3.10 or newer"
  corrected to 3.11.
- **F-26 — `py-modules` omission fixed.** `[tool.setuptools] py-modules` listed 7 of the
  repo's 11 root-level `.py` modules; `corpus_to_json_resume`, `docx_to_persona_html`,
  `json_resume`, and `pdf_render` were missing (all four are imported at runtime) and would
  have been absent from an installed wheel. Now lists all 11; `tests/test_packaging.py`
  pins the roster against a live glob of the repo root so this can't silently drift again.
- **F-24 — `docs/install.md` "Verifying the install" needs `[dev]`.** The verify steps ran
  `pytest`/`ruff`, but the install steps only ever ran `pip install -e .` — neither tool is
  a runtime dependency, so a clean install failed the very verification steps meant to
  confirm it. Added `pip install -e '.[dev]'` as the first step of "Verifying the install".
- **F-25 — `sartor --setup` added to every OS walkthrough.** The per-OS Windows/macOS/Linux
  steps only ever documented the raw `python -m playwright install chromium` call, never the
  documented one-time bootstrap (`sartor --setup`, which does that AND builds the assistant's
  semantic-recall index) — a reader following an OS section got PDF export working but the
  recall index unbuilt (silent lexical/wiki-tier fallback). Each OS section's Chromium step
  now runs `sartor --setup` instead, documented as covering both.

### Fix: eval harness scores the shipped frozen-assembly path (`fix/eval-f11-frozen-assembly`, 2026-07-07)

UX-review Wave 0, F-11 ([`40-friction-register.md`](docs/dev/reviews/2026-07-ux-review/40-friction-register.md)) —
on the UI happy path corpus-mode `/api/generate` assembles the résumé body **deterministically**
from the frozen `approved_composition` (`blueprints/generation.py`'s `_frozen_composition` gate,
zero résumé-body LLM calls), but `evals/runner.py` always ran `analyze → clarify → generate`,
where `generate()` is a real ~27s Sonnet call — the harness was scoring the fallback/legacy path,
not the assembled document users actually download.

- **New `evals/runner.py --mode {generate,assemble}` flag** (default `generate`, byte-identical to
  before). `assemble` REQUIRES `--seed` (frozen-composition assembly needs a real corpus) and
  drives the SAME Compose → freeze → assemble path the product uses instead of calling
  `analyzer.generate()`: `analyzer.recommend_bullets` / `recommend_summaries` (Haiku — the exact
  functions the `/recommend` + `/recommend-summary` routes call) populate
  `llm_recommendations` / `llm_summary_recommendation` on the context, then
  `corpus_to_json_resume.freeze_approved_composition` (the exact function Compose's
  Save-and-continue calls) resolves + freezes the composition, and
  `blueprints.generation._assemble_from_frozen_composition` (the exact function `/api/generate`
  calls once frozen) assembles it — zero résumé-body LLM calls. The cover letter stays a real
  Sonnet call (`generate_cover_letter_against_resume`) for tone-rubric parity with the legacy
  path's own default. Skill curation is left at its documented product default (no
  `recommend-skills` call → all active, approved skills), not an eval shortcut.
- **`eval_mode` rides every JSONL record** (`"generate"` or `"assemble"`), mirroring how
  `prompt_version` / `suite` attribute records — so the dashboard/baseline tooling can tell the
  two content-generation populations apart.
- **Baseline-gating scoped away from the new mode** — `assemble`-mode scores are never compared
  against `baseline_v1.json` (measured on the `generate`-mode population): `baseline_comparison`
  is always `null` and assemble-mode scores never feed the regression-gate `exit_code` (a
  sub-threshold score still counts via `n_fail`). No `PROMPT_VERSION` bump — no prompt changed.
- Unblocks the "Eval baseline stale vs production model (Sonnet 5)" carry-forward ledger row
  (`docs/dev/RELEASE_CHECKLIST.md`), scheduled to run after this landed.
- Tests: `tests/test_eval_runner.py::TestAssembleMode` — proves the graded résumé text is
  byte-identical to an independently re-derived `freeze_approved_composition(...) →
  json_resume_to_markdown(...)` call (not an LLM-authored stand-in), `analyzer.generate()` is
  never invoked in `assemble` mode (patched to raise), every record carries `eval_mode`, and the
  default `generate` mode never touches `recommend_bullets`/`recommend_summaries`/
  `freeze_approved_composition` (patched to raise) — proving the legacy path is unchanged.

### Fix: résumé import creates pending skills (`fix/ux-f02-import-skill-rows`, 2026-07-07)

UX-review Wave 0, F-02 ([`40-friction-register.md`](docs/dev/reviews/2026-07-ux-review/40-friction-register.md)) —
résumé import created Experiences, ExperienceTitles, Bullets, and role-intro summary variants,
but never Skill rows: a freshly imported candidate had an empty Skills section, the Compose
skills card never appeared, and skills silently dropped out of every tailored output.

- **One Haiku call, two outputs** (`onboarding/extract_experiences.py`) — the résumé-extraction
  system prompt now also asks for a flat `"skills"` array (verbatim names from an explicit
  Skills/Technologies section only; no invention, no pulling terms out of bullet prose). New
  `extract_experiences_and_skills()` returns `(experiences, skill_names)` from that single call;
  `extract_experiences()` becomes a thin backward-compatible wrapper over it, so every existing
  caller/test keeps working unchanged. No second API round trip, no cost increase.
- **`onboarding/corpus_import._insert_pending_skills`** — inserts the extracted names as
  `is_pending_review=1, is_active=1, source="imported"` Skill rows (`source` is DB-CHECK-limited
  to `manual|imported|llm_proposed` — `ck_skill_source` — so it reuses the same value the
  config-seeded importer and the legacy-row backfill already use). Deduped case-insensitively
  against **every** existing Skill row for the candidate (active, retired, or already pending),
  both within one extraction batch and across re-imports/re-uploads, so re-running an import is
  always safe. Wired into `ingest_one_resume`, so both the CLI importer (`--with-llm`) and the
  live `POST /api/users/<u>/corpus/ingest-resume` route pick it up with no route changes.
- Reuses the existing review surface end to end — no new UI. The Career Corpus tab's
  "AI-suggested skills" lane and the existing approve/deny routes (`blueprints/corpus/skills.py`)
  already list any `is_pending_review=1` Skill row regardless of source, and `refreshCorpus()`
  already re-fetches skills after an ingest. `static/app.js`'s post-upload status line and the
  route's JSON payload now also report `skills_created` alongside the existing experience/bullet
  counts.
- No `PROMPT_VERSION` bump — the changed prompt lives in `onboarding/extract_experiences.py`,
  which the project does not version-stamp (unlike `analyzer.py`'s persona prompts).
- Tests: pending-skill creation with the `imported` source, case-insensitive dedup against
  pre-existing rows and within one extraction batch, re-import idempotence, dry-run counting,
  and an end-to-end check that an approved skill flows through to
  `corpus_to_json_resume._collect_skills` (the deterministic JSON-Resume/frozen-composition
  skills source) while still-pending ones do not.

### Fix: keyword score no longer graded on the company name + JD boilerplate (`fix/ux-review-wave0-keyword-score`, 2026-07-07)

UX-review Wave 0, F-01 ([`40-friction-register.md`](docs/dev/reviews/2026-07-ux-review/40-friction-register.md)) —
the highest-leverage P0: a strong SRE-to-SRE match scored **18%** because the hiring company's
own name ("lattice cloud") and hiring boilerplate ("hiring", "serving") counted as keywords
missing from the résumé. Deterministic fix (`hardening.py` — charter C-6, no LLM, no
`PROMPT_VERSION` bump, no new dependency):

- **`JD_BOILERPLATE_WORDS`** — hiring-administrivia (process / qualifier / package /
  arrangement words) is dropped from the JD keyword universe inside `compute_keyword_overlap`:
  matching "hiring" is not signal, missing it is not a deficit.
- **`extract_company_terms(jd_text)`** — conservative deterministic company detection
  (header-zone "X — location" lines + "About X" / "at X" / "X is|runs|builds…" patterns);
  job-title vocabulary disqualifies a candidate term, so duty-bullet proper nouns
  (Kubernetes, Prometheus) are never captured; fail-open on any miss.
- **Forgive-absence scoring** — a company term absent from the résumé leaves both the missing
  list and the denominator; when present it still counts as matched (a Databricks engineer
  applying to Databricks keeps the credit). New `excluded_terms` key reports what was cleaned
  (also added to `evals/schemas/context_set.schema.json`).
- Company terms are passed at the two overlap call sites — `db/build_context.py` (corpus mode)
  and `evals/runner.py` (the eval harness stays on the live code path). Compose bullet ordering
  and corpus-snapshot selection intentionally keep the raw JD keywords (`extract_keywords`
  unchanged).
- **Analyze-screen reframe** (`static/app.js`): "Keyword Match Score" → "JD Keyword Coverage"
  plus a one-line explainer; "Keywords Missing From Resume" → "Keywords You Could Add".
- Tests: company-term detection, cleaning semantics, and a fixture regression asserting the
  SRE fixture's company/boilerplate never appear in the missing list and the cleaned score
  strictly exceeds the raw-overlap before-state.

### Fix: deterministic Compose settle gate — stop the flaky-UX class (`fix/compose-settle-bg-reload`, 2026-07-06)

A reduction-sprint knock-down of the carry-forward "recurring flaky Compose-UX" ledger item.
**Test-observability only** — no product behavior change, no prompt bytes, no `PROMPT_VERSION` bump.

- **Root cause** — the Compose (Step 3) auto-recommend/draft cascade fires background POSTs that
  each re-run `loadComposition()` on success; the `data-compose-ready` settle marker is re-set at
  the END of each synchronous render, but a background reload (the Phase-3 deferred
  `/draft-gap-fill` most visibly) lands *later*, so the POM's `_wait_settled` — a one-shot
  `networkidle` + a hand-rolled 3×50 ms marker-stability poll — could settle on a non-terminal
  render and race the re-render (the positioning-pin clobber).
- **Fix (settle-marker, not serialize)** — a `data-compose-bg-pending` counter attribute on
  `#composeList` ([`static/app.js`](static/app.js)), incremented as the first synchronous statement
  of every `loadComposition()`-on-success reload site (the 5 auto-cascade `_fire*` **and** the 6
  user-action pin/suggest/review/accept/add reloads) so it is present before the marker is re-set,
  and decremented in a `finally` so a failed POST still balances (no stuck attribute → no hang).
- **Deterministic gate** — `_wait_settled` ([`ui_pages/wizard_compose.py`](ui_pages/wizard_compose.py))
  now waits on `#composeList[data-compose-ready]:not([data-compose-bg-pending])`
  ([`Compose.SETTLED`](ui_pages/selectors.py)) — the only state that is the true terminal render
  with no reload queued — replacing the stability poll with a single `wait_for_selector`.
- **Regression test** — `tests/ux/regression/test_20260706_compose_settle_bg_reload.py` slow-stubs
  the gap-fill draft so its reload is reliably in flight, then asserts the counter fires and the
  settle blocks until it drains. The two previously-flaky members + the gap-fill tests passed
  **18/18** across 3 stability re-runs; full `pytest -m ux` (77) and the whole suite (1535) green.

### Chore: pin ruff + add a whole-tree `ruff format --check` CI gate (`chore/ruff-format-pin`, 2026-07-06)

A reduction-sprint knock-down of the carry-forward "ruff-format-drift" ledger item.
**Formatting-only and prompt-safe** — no logic, no prompt bytes, no `PROMPT_VERSION` bump.

- **One-time `ruff format .` sweep** — 5 files that predated the current formatter re-formatted
  under ruff 0.15.12 though no branch touched them (`docx_to_persona_html.py` + four `tests/`
  files): f-string inner-quote normalization, single-line collapsing, string-concat re-wrapping.
  None is `analyzer.py`, so no prompt changed.
- **Ruff exact-pinned** — [`pyproject.toml`](pyproject.toml) dev extra: `ruff>=0.6,<1.0` →
  `ruff==0.15.12`. Ruff does not guarantee formatter-output stability even across patch releases,
  so a floating range let the drift accumulate; the exact pin makes local + CI format identically.
- **New CI format gate** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml) `quality` job now
  runs `ruff format --check .`, which CI previously never did (it only ran `ruff check`, and the
  commit hook only checks *staged* files). Pin + gate are one inseparable fix: a gate without the
  pin would flake CI on unrelated PRs the day a new ruff releases. Bumping ruff is now a deliberate
  one-commit action (upgrade + `ruff format .` + re-pin).

### Feature: Compose authors + freezes the composition; Generate becomes deterministic (`fix/compose-frozen-composition`, 2026-07-06)

The generation-experience re-architecture (Option B — one cohesive branch). North
star: **NO SURPRISES** — content is authored + approved ONCE at Compose, frozen, then
rendered deterministically by every downstream surface. What you see is what you
download. `PROMPT_VERSION 2026-07-06.1 → 2026-07-06.3`. Full design + decision record:
[`docs/dev/generation-experience-rearchitecture.md`](docs/dev/generation-experience-rearchitecture.md).

- **Frozen `approved_composition` contract (Phase 1)** — `corpus_to_json_resume` is the
  sole producer of a resolved JSON-Resume snapshot (honors `bullet_order`, folds
  `accepted_generated_bullet_ids`, resolves `summary_text`, emits `meta.sartor`
  provenance); `freeze_approved_composition()` stamps it on Compose "Save and continue".
- **Compose authors the 2-sentence positioning summary (Phase 2)** — a dedicated Sonnet
  `draft_positioning_summary` (grounded, editable, retire-able) fires once on Compose
  arrival, replacing the summary the résumé LLM used to write.
- **Compose authors gap-fill bullets (Phase 3)** — a Sonnet `draft_gap_fill_bullets`
  proposes GROUNDED bullets for JD requirements the corpus doesn't cover, shown as a
  per-role "Suggested for this JD" accept/retire lane; ACCEPT creates a pending `Bullet`
  folded into this application's composition, RETIRE drops it. A resolver **pending-leak
  guard** keeps a pending+active bullet from rendering in other applications (mirrors the
  skills guard); this also stops any pre-existing pending+active bullet (e.g. a
  promoted-clarification bullet) from leaking into every all-active render.
- **Generate becomes deterministic (Phase 4)** — in corpus mode, `/api/generate`
  (+ streaming) ASSEMBLE the frozen `approved_composition` (ZERO résumé-body LLM calls)
  instead of calling `generate()`; the résumé renders directly from the doc, so
  **preview == assemble == download** by construction. The **cover letter stays an LLM
  call**; **legacy (file-based) mode is byte-identical**, so `--suite synthetic` is
  unchanged. A corpus-mode Refine now routes BACK to Compose (minimal loop-back) with an
  explaining banner instead of an LLM full-regenerate. New deterministic helpers:
  `json_resume.json_resume_to_markdown`, `generator.generate_resume_from_json_resume`.
- **Also folded in** (two pre-existing branch bugs, confirmed on clean HEAD): a
  `ui_pages/wizard_compose.reset_order` helper fix (used `EXPERIENCE_CARD.first`, which now
  resolves to the always-present positioning card) and an `aria-label` on
  `#composeSummaryDraft` (axe "form elements must have labels").
- **Deferred to LATER branches:** surgical (non-rewrite) refinement + the richer
  loop-back-with-accept/retire banner; WYSIWYG-as-source (D4); clarifications→corpus
  persistence (D5); a "Regenerate gap-fill" affordance.

### Fix: refinement scope warning is an in-app modal, not a native browser confirm (`fix/refinement-and-loopback`, 2026-07-06)

Preview #3: when a refinement looked like it might change facts (via
`/api/validate-refinement`), `submitRefinement()` fired a browser-native
`confirm()` — an OS dialog in a different visual format from every other modal in
the app, which read as jarring and untrustworthy.

- **`templates/index.html` + `static/app.js`** — new `refinementScopeModal` using
  the same `.cb-modal` shell as `editModal`, driven by a promise-based
  `_showRefinementScopeModal()` helper that mirrors `_showEditModal`'s a11y posture
  (focus trap, Esc-to-cancel, backdrop dismiss, focus restored to the trigger).
  `submitRefinement()` now awaits it instead of `confirm()`. Still FLAGS-not-BLOCKS
  (correcting a fabricated fact is a legitimate refinement), and reminds the user
  that changed claims stay grounded in their corpus + clarifications.
- **Tests** — `tests/ux/regression/test_20260706_refinement_scope_modal.py` drives
  the modal helper directly (LLM-free): reason shown in-modal, Cancel → `'cancel'`,
  Proceed → `'proceed'`.
- Deterministic UI-only change; no LLM/prompt changes, `PROMPT_VERSION` unchanged.

> **Note on scope.** The deeper items from the same plan — surgical (non-rewrite)
> refinement, deterministic assembly at Generate, and the loop-back-to-Compose for
> newly-generated content — are a larger, coupled re-architecture that depends on a
> Compose-authored *frozen composition* object (not yet built). They are deferred to
> a dedicated effort; the app is fully usable after the render-fidelity + richness
> branches.

### Fix: generation richness — rich bullets across every role, metrics surfaced, real Summary + Skills (`fix/generation-richness`, 2026-07-06)

Second branch of the remediation, targeting "weak first-generation bullets/summaries."
Corpus generation was collapsing most roles to a title-only "weak summary," dropping
metric bullets, and emitting no Summary/Skills.

- **`analyzer.py` — code-side anti-starvation floor.** `_stable_user_prefix`'s
  recommendation narrowing is now PER-ROLE: a role the user or `recommend_bullets`
  curated still narrows to that set, but a role with **no** curation signal keeps its
  active bullets instead of being filtered to empty. Previously any role
  `recommend_bullets` under-picked or omitted reached generate with **zero** bullets —
  so the v1.0.8 COVERAGE rule ("every role keeps its bullets") was moot because the
  bullets were already stripped. This also makes generate agree with the Compose
  preview (`corpus_to_json_resume` already kept all active bullets for un-recommended
  roles). On the owner's `robert` corpus: roles reaching generate with bullets **3/8 →
  8/8**, total bullets **11 → 24**.
- **`analyzer.py` — generous, metric-first RECOMMEND.** `RECOMMEND_SYSTEM_PROMPT` now
  targets 3-6 bullets/role, STRONGLY prefers `has_outcome` metric bullets, and never
  zeroes out a role — replacing the old "down to 1 / soft ceiling" stinginess that
  starved the Compose card.
- **`analyzer.py` — first-class Summary + Skills.** Resume rule #1 asks for a
  two-sentence positioning Summary (was one sentence); new rule #9 requires a `## Skills`
  section; and the corpus-mode grounding now explicitly declares the Summary paragraph +
  Skills list as EXPECTED non-bullet sections, so the verbatim-bullet rule no longer
  suppresses them.
- `PROMPT_VERSION` `2026-07-01.1` → `2026-07-06.1`.
- **Validation.** Grounding smoke (`--suite synthetic --subset smoke`): 3 pass / 0 fail,
  grounding 4.6, `fabricated_specifics` ≤ 0.13 — the Summary/Skills carve-out did not
  loosen grounding. Real `generate()` on `robert`: 8/8 roles, 24 bullets (16 with
  metrics), 2-sentence Summary, Skills section. New corpus-mode unit tests pin the
  anti-starvation floor + the generous-RECOMMEND + Summary/Skills prompt rules.

### Fix: single render engine — download == preview, and section titles never silently drop (`fix/single-render-engine`, 2026-07-06)

First branch of the preview/download-fidelity remediation. The `.docx` download
was a **second, divergent renderer**: it parsed the résumé markdown itself and
emitted any `## heading` verbatim, while the on-screen preview + PDF render the
`md_to_json_resume()` structured document through the persona HTML template. The
two disagreed on both styling and *content* — a résumé titled "Professional
Summary" / "Core Competencies" (what plain Word imports produce) rendered those
sections in the `.docx` but dropped them from the preview (they fell to
`meta.sartor.unparsed`).

- **`generator.py`** — replaced the markdown-walking `_write_docx()` with
  `_write_docx_from_json_resume()`, which consumes the SAME `json_doc` the
  preview/PDF use and walks it in `personas/bundled/classic.html`'s section order
  (header → summary → experience → skills → certifications → education →
  projects). Persona typography capture (`_capture_template_styles`, list
  numbering, per-role protos) is unchanged — only the content *source* moved from
  a raw markdown parse to the structured document. Result: **download == preview
  by construction**; a non-canonically-titled section can no longer appear in one
  surface and vanish from the other.
- **`json_resume.py`** — widened `_SECTION_MAP` with the common heading aliases
  ("Professional Summary", "Summary of Qualifications", "Professional
  Experience", "Work History", "Technical Skills", "Core Competencies", "Areas of
  Expertise", …) so those sections land in the canonical JSON Resume fields
  instead of `meta.sartor.unparsed`. Purely widening — can only rescue a title
  that would otherwise be dropped.
- **`db/ats_roundtrip.py`** — the round-trip section-presence check now compares
  on the canonical `_SECTION_MAP` key, so the audit agrees with the
  now-canonicalizing writer instead of flagging equivalent headings as "missing."
- **UI** — added a **"↻ Start new tailoring"** action under the wizard rail
  (`startNewTailoring()` in `static/app.js`, revealed by `wizardInit()`): clears
  the in-flight run (JD, analysis, clarify, composition, generated docs, preview)
  and returns to Step 1 for the same user without a browser refresh. The next
  ANALYZE opens a fresh application. Corpus untouched.
- **Tests** — `tests/test_render_parity.py` pins both invariants: the JSON Resume
  sidecar (download's source) equals `md_to_json_resume()` (preview's source),
  every preview bullet/summary/skill appears in the generated `.docx`, and the
  writer emits canonical headings regardless of the source's titles.
- Deterministic-only change (no LLM calls touched); `PROMPT_VERSION` unchanged.

### Model upgrade: Sonnet 4.6 → Sonnet 5 for the heavy-reasoning calls (`chore/upgrade-sonnet-5-model`, 2026-07-05)

Upgraded the Sonnet-tier LLM calls (analyze/synthesis, generate, cover letter,
clarify_iteration) from `claude-sonnet-4-6` to `claude-sonnet-5`. The Haiku-tier
calls are unchanged — **Haiku 4.5 (`claude-haiku-4-5-20251001`) is still the
latest Haiku; there is no Haiku 5.**

- **`analyzer.py`** — `SONNET_MODEL = "claude-sonnet-5"`. The streaming call now
  sends `thinking={"type": "disabled"}` on the Sonnet path. Sonnet 5 turns
  **adaptive thinking on by default** when `thinking` is omitted (4.6 ran
  thinking-off); left implicit, that would spend part of the 8192-token
  `MAX_TOKENS` budget on reasoning (risking a `max_tokens` truncation of the
  JSON payload), add latency before the streamed resume, and drift eval scores.
  Behavior is thus held identical to 4.6. Adopting adaptive thinking is a
  separate, eval-gated change. Haiku calls are untouched.
- **`hardening.py`** — added a `claude-sonnet-5` entry to `MODEL_PRICING`
  ($3/$15 in/out, standard rate — identical to 4.6; an intro discount of
  $2/$10 runs through 2026-08-31 but the durable rate is used to keep cost
  tracking stable). The `claude-sonnet-4-6` entry is **retained** so historical
  `llm_calls.jsonl` records keep costing correctly.
- **Eval + config provenance** — `evals/runner.py` `MODEL_SNAPSHOTS["sonnet"]`
  and the `promptfooconfig.yaml` provider now name `claude-sonnet-5`.
- **Docs** — `docs/architecture.md` and the two `docs/wiki/` cite lines
  (`deterministic-llm-boundary`, `llm-call-catalog`) updated to the new string.
- **Plugin subagents** — the six Sonnet-pinned `agents/*.md` frontmatter
  entries (`compliance-witness`, `git-flow`, `prompt-archaeologist`,
  `tune-drafter`, `headhunter`, `ux-onboarding-designer`) bumped to
  `claude-sonnet-5`, closing the model-version-drift the 2026-07 efficiency
  review flagged. The three Haiku-pinned subagents are unchanged.

`PROMPT_VERSION` is **not** bumped: no prompt text changed, and the model is an
independent telemetry axis already recorded per call (`model` in
`llm_calls.jsonl`, `MODEL_SNAPSHOTS` in eval results). Tests: added a
`claude-sonnet-5` case to `TestCallCost`. No new dependency. Recommended before
release: run `python evals/runner.py --suite synthetic` to confirm no rubric
regression on the new model.

### 2026-07 efficiency review — witness-only archive (`review/2026-07-efficiency`, 2026-07-03)

Four-area efficiency/optimization review (agent-process & governance DX ·
runtime performance & reliability · docs & wiki processes · tests/CI &
gates), pinned at `4196d0c`, mirroring the 2026-06 excellence-review
formats. Report-and-prescribe only — no code, hook, config, or prompt
changes ride this branch.

- **Archive:** `docs/dev/reviews/2026-07-efficiency/` — 42-row findings
  register (every P0/P1 adversarially verified: 4 CONFIRMED, 9 WEAKENED,
  1 REFUTED-and-dropped), per-area findings files with a measured
  LLM-telemetry appendix (2,955 calls, $35.14 tracked), a verification log
  (incl. an idle re-measurement that resolved a contested test-lane
  number), and 20 banded prescriptions (PX-37..PX-56; 2-judge panel +
  orchestrator tiebreak; 0 CONTESTED).
- **Headliners:** Edit/Write hook process-spawn tax measured ~3.5–4s per
  call (consolidation → PX-37); the Python 3.10 floor is actively broken
  (`import tomllib` fails collection) — PX-42 banded before the first PyPI
  tag; wiki 119 commits behind its checkpoint (PX-41 rides the scheduled
  8.6 ingest); a documented fast test lane halves the inner loop
  (309s → 163s, measured idle).
- **Ledger:** one aggregate carry-forward row; the stale "Open count: 7"
  header corrected per F-doc-02 (post-merge count: 10 — see the ledger head-note).

### Packaging: container image + `sartor --setup` + PyPI workflow (`feat/packaging-publish`, 2026-07-02)

Distribution surface for shipping Sartor beyond a git clone.

- **`sartor --setup`** — one-time post-install bootstrap in `app.py:main()` (now
  argparse-driven): installs Chromium for PDF (`python -m playwright install
  chromium`, `--with-deps` on Linux) and builds the semantic-recall vector index
  (`python -m scripts.build_vector_index`), then exits. Also adds `--host` / `--port`
  (so the container can bind `0.0.0.0` while the default stays loopback-only per
  PX-19) and `--no-browser`. Default (no-flag) behavior is unchanged.
- **Container** — `Dockerfile` (Docker- and Podman-compatible) + `.dockerignore`.
  `python:3.13-slim`, editable install so Flask resolves `templates/` · `static/` ·
  `personas/` under `/app`, Chromium + the vector index **baked in**, non-root user,
  `CMD ["sartor","--host","0.0.0.0"]`. `.github/workflows/docker.yml` builds + pushes
  a multi-arch (amd64 + arm64) image to `ghcr.io/take-tempo-public/sartor` on a tag.
- **PyPI** — `.github/workflows/release.yml` builds the wheel + publishes via OIDC
  **Trusted Publishing** (no stored token), with a tag↔version guard and a wheel
  smoke. The `publish` job is **intentionally gated (fails fast)**: the wheel does
  not yet ship the app's data dirs (`templates/` · `static/` · `personas/` ·
  `docs/wiki`), so `pip install sartor` would 500 at runtime — the fix is a tracked
  follow-up (see `RELEASE_CHECKLIST.md`), and the gate is removed once a fresh-venv
  wheel install actually serves a page.
- **Packaging fix:** added `scripts*` to the wheel's packaged modules — it is
  imported at runtime (`blueprints/diagnostics.py` → `scripts.export_corpus_seed`;
  `sartor --setup` → `scripts.build_vector_index`) but was previously omitted, so it
  only worked from an editable clone.

Docs: install paths (source + container + `sartor --setup`) in `README.md` +
`docs/install.md`, incl. the one-time `[HUMAN]` PyPI Trusted-Publisher + GHCR setup.
Tests: `tests/test_cli_setup.py`. No new runtime dependency.

### Product rename: Callback → Sartor (`rename/callback-to-sartor`, 2026-07-02)

Renamed the product from **Callback** to **Sartor** across the whole repo — brand
mark (the lowercase `sartor.` wordmark, incl. the letter-split masthead spans),
package/CLI name (`pyproject.toml`), the Claude Code plugin + namespace
(`/callback:*` → `/sartor:*`, `.claude-plugin/*`, `.claude/settings.json`, agents +
commands), the JSON Resume `meta.callback.*` → `meta.sartor.*` extension key, UI help
text, docs, wiki (`using-callback.md` → `using-sartor.md`), governance, and the
`AVATAR_SYSTEM_PROMPT` brand mark (`AVATAR_PROMPT_VERSION` → `2026-07-02.1`).

**Guarded false positives — "callback" is also a recruiting term** (the product name
is a pun on getting a call-back/interview). Left untouched: `callback_likelihood` /
`callback_weights` (eval), "generate a callback", "the callback signal/funnel",
"callbacks", `callback-worthy`, and Chart.js's `callback:` tick formatter — all the
recruiting/generic-JS uses. GitHub URLs point to `github.com/take-tempo-public/sartor`
(the résumé `PROMPT_VERSION` was untouched — the main personas carry no brand mark).

`[HUMAN]` follow-ups (not done here): rename the GitHub repo + registries + trademark
clearance (in-app URLs 404 until the repo rename); rename the working directory
`Dev/callback` → `Dev/sartor` (the code is path-agnostic, so no in-repo change needed);
and reload + re-trust the Claude Code marketplace to pick up the `sartor:*` namespace.

### v1.0.8 walkthrough remediation — Branch 8: generation quality (`fix/generation-quality`, 2026-07-01)

The hardest slice — generation correctness. `PROMPT_VERSION` → `2026-07-01.1`.

Deterministic / frontend (no eval):
- **C3 — cover-letter text leaking into the résumé.** A new deterministic
  `hardening.strip_cover_letter_block` drops any block starting at a "Dear …" /
  "To Whom It May Concern" salutation from `resume_content` (a résumé body never
  contains one), applied right after `generate()` in `run_generation`. This stops
  the stray cover letter that appeared at the bottom of the résumé editor + download
  and inflated length past two pages.
- **E4 — user blocked from correcting a hallucination.** The Haiku refinement
  scope-check flagged corrections as "changing facts" and the frontend *blocked*
  them. Now it **flags but never blocks**: the concern is surfaced as a
  confirm-to-proceed prompt, and the user can always proceed.

Prompt changes (`PROMPT_VERSION` bump; each conditional so the iteration-0 /
no-clarification path is unchanged):
- **C1/C2 — older roles came out with no bullets.** The corpus payload carries every
  role's bullets and `md_to_json_resume` parses them fine, so the LLM was dropping
  them. Added a **COVERAGE rule**: every experience that has corpus bullets must
  contribute at least one to `resume_content` — never leave a role title-only when
  bullets exist.
- **E2 — refine clobbered manual fixes.** In corpus mode `_stable_user_prefix` never
  emitted the current draft, so a refine re-derived from the corpus and discarded
  edits. A conditional `<current_resume_draft>` block (iteration>0 + edits) now feeds
  the edited draft in with an evolve-don't-rebuild instruction.
- **E5 — invented "10 years of…" tenure re-appearing.** Added a grounding-check
  worked example forbidding fabricated years-of-experience/ownership figures in the
  summary and making a prior removal binding.
- **H1 — a multi-role clarification answer mashed into one bullet.** The
  clarifications block now instructs the model to attribute each role's content to
  its own experience and never merge two roles into one bullet.

Tests: prompt-structure assertions (`tests/test_corpus_mode_prompt.py`), the C3
stripper (`tests/test_hardening.py`), and a grounding eval run (see
`evals/TUNING_LOG.md`). C1/E2 are corpus-mode-only (not exercised by the synthetic
suite) — validated structurally + owner E2E.

### v1.0.8 walkthrough remediation — Branch 7: retire / restore prior applications (`feat/prior-applications-retire`, 2026-07-01)

The Prior Applications list grew unbounded with no way to hide poor examples or
abandoned drafts (walkthrough J1 / E3 cleanup half). Added a soft-retire flag,
mirroring the corpus `ExperienceTitle.is_active` pattern (migration 0011):

- **`application.is_active`** column (migration `0013`, native `ADD COLUMN` — no
  batch recreate, since `application` is a parent of `application_run`; no backfill,
  everything starts active).
- **Routes:** `DELETE /api/applications/<id>` soft-retires (kept, not hard-deleted —
  runs + audit survive); `POST /api/applications/<id>/restore` reverses it. Both are
  DB-only with an ownership guard (`_safe_username`).
- **List:** `list_applications` hides retired rows by default; `?include_retired=1`
  returns them; the summary payload carries `is_active`.
- **UI:** a "Show retired" toggle in the Prior Applications tab, a `Retire` action on
  each card (`Restore` on retired cards), a `RETIRED` chip, and dimmed retired cards.
  The native checkbox gets the same `appearance:auto` override as the corpus one.

This also closes the deferred cleanup half of E3 (deserted résumés/applications).
Note: collapsing *resolved* applications (interview/rejected/withdrawn) into a
grouped section was considered but deferred — retire + the existing status filter
already tame the "too many to see" problem. Tests: `tests/test_application_routes.py`
(`TestRetireApplication`: retire hides + `include_retired` surfaces, restore, summary
`is_active`, 404).

### v1.0.8 walkthrough remediation — Branch 6: no legacy ATS advice in corpus mode (`fix/analyze-corpus-advice`, 2026-07-01)

Analyze (Step 1) showed "No standard ATS section headings detected…" and "Resume is
quite long (N words). Consider trimming to 1-2 pages…" even though there is no
uploaded résumé — the content is synthesized from the corpus (walkthrough G1).
`db.build_context` ran `check_ats_format` on the corpus synthesis with an always-empty
`sections` list (so the heading warning always fired) against the *whole* corpus (so
the length warning always fired) — both legacy artifacts of the old uploaded-résumé
flow. The corpus synthesis is a structured projection, not the final deliverable, so
those warnings are suppressed in corpus mode; the meaningful JD keyword-overlap signal
is unchanged, and ATS formatting is still judged on the rendered output
(preview/download). Test: `tests/test_build_context_db.py` asserts corpus-mode
`ats_warnings == []`.

### v1.0.8 walkthrough remediation — Branch 5: corpus import — year-only dates + role summaries (`fix/corpus-import`, 2026-07-01)

- **Year-only work dates accepted (F3 → also fixes much of F1).** The extractor and
  the manual add/edit-experience routes required `YYYY-MM` and **dropped** any role
  whose date was a bare year. Résumés that list years only lost those roles — and
  because the extraction prompt was told to omit undated roles, the model tended to
  lump their bullets under the one role it could date ("every bullet in one job").
  A bare `YYYY` is now valid across the extraction normalizer (`_DATE_RE`), the
  extraction prompt, both backend validations (create + update), and the frontend
  patterns. Year-only dates are stored **verbatim** (JSON Resume renders the date
  string as-is; nothing parses it as `%Y-%m`).
- **Role summaries import as role intros, not bullets (F2).** A résumé's role
  intro/scope paragraph was extracted as a bullet. Extraction now has a dedicated
  `summary` field (with a prompt rule separating an intro paragraph from achievement
  bullets), and import turns it into a pending-review **`ExperienceSummaryItem`** —
  the live role-intro path the Compose "Add role intros" picker and the résumé
  render actually read — plus the denormalized `Experience.summary` column for
  parity with the manual add route. Deduped across re-imports/merges.
- **F1 residual.** True LLM mis-grouping on unusually formatted résumés isn't fully
  deterministic; the existing post-import similar-role merge suggestions remain the
  cleanup path for that.

The extraction prompt lives in `onboarding/` (not the `PROMPT_VERSION`-tracked
generation personas) and isn't eval-gated, so no version bump / eval run. Tests:
`tests/test_extract_experiences.py` (year-only accepted; summary captured separately
from bullets) and `tests/test_corpus_import.py` (import summary → `ExperienceSummaryItem`,
not a bullet; year-only kept verbatim).

### v1.0.8 walkthrough remediation — Branch 4: inline bullet edit/approve + Compose UX (`feat/compose-inline-approve`, 2026-07-01)

Frontend-only (CSS/JS); no `PROMPT_VERSION` change, no new dependency:

- **Edit + approve a proposed bullet inline (D3).** A pending-review bullet in the
  Compose step now carries **EDIT** and **APPROVE** actions next to its `PENDING`
  flag. EDIT opens the bullet for editing and `PUT`s the new text to the corpus;
  APPROVE clears the pending flag via `POST /api/bullets/<id>/accept` — both the
  same routes the Career Corpus tab uses. The user no longer has to leave the
  tailor flow, edit in the Corpus tab, and come back for a proposed change to stick.
- **Role-intros checkbox alignment (I1).** The "Add role intros" native checkbox
  was hit by the global `input { flex:1; padding }` rule and stretched across the
  row (label wrapping asymmetrically). Added the `appearance:auto; flex:0 0 auto`
  override (mirrors `.corpus-show-retired input`).
- **Pending banner fades at zero (I2).** Retiring the last pending bullet/title
  now refreshes the corpus pending-review banner (accept already did; retire
  didn't), so it correctly transitions to the "ready" state instead of lingering
  on stale "Accept all pending" copy.

### v1.0.8 walkthrough remediation — Branch 3: edits reach the preview + refine overlay + back-nav (`fix/edit-backprop`, 2026-07-01)

Deterministic (no LLM, no `PROMPT_VERSION` change, no eval):

- **Edits now show in the styled preview (D1/D2).** The Step-6 preview iframe serves
  the cached `last_generated_json_resume` (WYSIWYG). `/api/save-edits` now recomputes
  that cache from the edited résumé markdown via the same deterministic path the
  download uses (`_normalize_markdown` → `md_to_json_resume`), and the frontend
  refreshes the preview iframe after a successful save — so a typed edit appears in
  the styled preview immediately, with zero LLM cost. Cover-letter-only edits leave
  the résumé cache untouched.
- **Refine shows the working overlay (E1).** `submitRefinement` now raises the
  persistent `_setBusy` banner while the refine regenerates (mirrors `runGeneration`),
  instead of only flipping a status label — no more dead-looking ~30-60s wait.
- **Back-navigation is discoverable (E3).** The wizard step rail read as a passive
  progress bar; reachable steps now carry a "Go to step N: <label>" tooltip so users
  find the click-to-go-back affordance. (The deserted-résumé cleanup half of E3 lands
  with the Prior-Applications retire work.)

Tests: `tests/test_app_iteration.py` — `/api/save-edits` recomputes
`last_generated_json_resume` (equals `md_to_json_resume(_normalize_markdown(edit))`,
carries the edit's name) and a cover-only edit leaves it untouched.

### v1.0.8 walkthrough remediation — Branch 2: faithful preview for uploaded templates (`feat/docx-html-companion`, 2026-07-01)

The live preview renders a résumé through a persona's `.html` + `.css` **companion**
(the sibling of the `.docx`). Only the 4 bundled personas shipped companions, so an
uploaded `.docx` template silently fell back to Classic — every uploaded template
previewed as Classic 1-column even though the `.docx` **download** was faithful
(walkthrough B2 / B3 / Step-6 #4).

- **New deterministic module `docx_to_persona_html.py`** (charter C-6, no LLM,
  no new dependency): reads an uploaded `.docx` with python-docx and reconstructs
  the same typography knobs the bundled templates are built from
  (`TypographyPreset` — font family/size, margins, name/heading/job sizes, heading
  treatment: uppercase / small-caps / underline / color, line spacing), then emits
  a companion `.html` (a byte-for-byte copy of the `classic.html` Jinja2 skeleton
  with only the CSS `href` swapped) + a `.css` (Classic's ATS-safe single-column
  structure, re-typed with the uploaded template's own typography) + a
  `<stem>.persona.json` fidelity sidecar.
- **Honest fidelity ceiling.** python-docx can't represent multi-column sections,
  tables, text boxes, or floating images; those sources are marked
  `layout_fidelity: "typography_only"` and rendered single-column with the source's
  fonts/colors/margins — which is exactly what the `.docx` download's `_write_docx`
  produces, so preview and download stay mutually consistent. Never fabricates a
  layout it can't deliver.
- **Wiring.** Companions are generated eagerly on upload (`upload_user_persona`,
  best-effort — a failure logs and still 201s, falling back to Classic as before)
  and lazily on first preview / PDF render for personas uploaded before this shipped
  (`preview_application_html`, `generator._render_pdf_from_json`). Idempotent
  (mtime-cached).
- **Spacious page-break.** Added `page-break-after: avoid` to the Spacious
  letterhead so paged.js stops occasionally orphaning the header on page 1
  (walkthrough Preview #2). Pagination of long résumés should be confirmed visually.

Tests: `tests/test_docx_to_persona_html.py` (round-trip extraction vs each
`TypographyPreset`; emit + skeleton-contract parity; fidelity fallback on tables;
`html_template_path_for` now resolves the companion so the preview stops falling
back to Classic). `PROMPT_VERSION` untouched; no new dependency.

### v1.0.8 walkthrough remediation — Branch 1: Step-4 template picker polish (`fix/preview-template-bugs`, 2026-07-01)

First slice of the pre-tag walkthrough-remediation epic. Two Step-4 template-picker fixes:

1. **Template-card badge overflow (B1).** A long owned-template filename pushed the
   `ATS` / `MINE` badges outside the card and triggered a horizontal scrollbar. The
   template name now truncates with an ellipsis (`.template-mini-label`: `flex:1;
   min-width:0`) and the two badges are pinned non-shrinking (`flex:0 0 auto`), so they
   always stay inside the row.
2. **Confusing picker copy (B4).** The Step-4 hint ("…the preview shows pages just as
   they'll print. Same content, different typography and layout.") read ambiguously.
   Reworded to state plainly that the résumé content stays the same and the template
   only changes how it looks (fonts, spacing, layout).

Frontend-only (CSS/HTML/JS); `PROMPT_VERSION` untouched; no new dependency. Full suite
green (1418 passed). Remaining walkthrough items (preview fidelity, edit-backprop,
generation quality, corpus import, prior-apps retire, Sartor rename, …) follow as
their own branches per the epic plan.

### Corpus import: similar-role merge suggestions + retire-hidden-by-default + persistent busy cue (`fix/corpus-import-and-curation-ux`, 2026-06-29)

Four corpus-building UX problems surfaced during e2e testing:

1. **Duplicate roles on import (P1).** The importer matched existing roles on an
   exact `(company, start_date)` key, so any date/company drift forked the same
   job into a new experience and split its bullets. Added a deterministic
   similarity scorer (company/title/dates/bullets → EXACT/SIMILAR/DISTINCT — pure
   stdlib, no LLM, inside the C-6 hardening boundary) and a post-import "possible
   duplicate roles" review card: the user **merges** (the extra title becomes an
   alternate, bullets combine + dedup, the **corpus dates are kept**) or **keeps
   separate** (persisted, so it stops re-surfacing). The importer's exact-match
   auto-merge is unchanged — only fuzzy matches ask.
2. **No persistent busy cue (P2).** Long actions (ingest / analyze / generate /
   cover letter) now raise a persistent flashing "working…" banner (vs the 2.4s
   toast) and disable the in-progress control, so the user doesn't click around
   mid-call.
3. **Couldn't truly remove an alternate title (P3) + retired clutter (P4).**
   "Delete" on a title was a soft-retire that left it visible as an `ALT` row.
   Retired titles **and** bullets are now hidden by default and shown only when
   the new "Show retired" checkbox is ticked (each with a RESTORE action);
   generation hard-excludes retired items. Soft-retire is kept (no hard-delete) —
   `application_run_title` / `proposal_review` FKs reference the rows for audit.

`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched; no new dependency (stdlib
`difflib` only). Two migrations, both FK-cascade-safe (plain `add_column` /
`create_table`, never a batch recreate of a parent table).

**Added**
- `onboarding/experience_match.py` — deterministic experience-similarity scorer.
- `ExperienceTitle.is_active` (migration `0011`) + the `merge_dismissal` table
  (migration `0012`).
- Routes: `GET /api/users/<u>/corpus/merge-suggestions`,
  `POST /api/experiences/<id>/merge`,
  `POST /api/users/<u>/corpus/merge-suggestions/dismiss`.
- Frontend: "possible duplicate roles" review card, global "Show retired"
  toggle + RESTORE actions, persistent busy banner (`_setBusy`).
- Tests: `tests/test_experience_match.py`, `tests/test_corpus_merge_and_retire.py`,
  `tests/ux/regression/test_20260629_corpus_retire_and_busy.py`.

**Changed**
- `blueprints/corpus/experiences.py` — title `DELETE` soft-retires via `is_active`;
  title/bullet `PUT` accept `is_active` for restore; the experience detail route
  honors `?include_retired=1`.
- `blueprints/corpus/_shared.py` — `_experience_detail_dict` hides retired rows by
  default; `title_count` is active-only.
- `db/build_context.py` — `eligible_titles_for` hard-gates on `is_active` so a
  retired title can never reach a generated résumé.
- `static/app.js` / `static/style.css` / `templates/index.html` — corpus UX, busy
  banner, import summary now surfaces `alternate_titles_created`.

**Fixed**
- Import no longer silently forks the same role across drifted dates/titles.
- Retired titles/bullets no longer linger in the corpus view.

### README rebuilt as a three-audience front door (`docs/readme-icp-ladder`, 2026-06-29)

The README is restructured around a cumulative three-audience ladder — job seeker →
coach/headhunter → developer (`one → many → extend`) — and brought under the project's
doc disciplines: a `Purpose / Audience / Authoritative-for` header, a documentation map,
and single-home / cite-don't-restate (it owns the pitch + the ladder; everything else
links to its canonical doc, with volatile facts linked out so the auto-published front
door can't drift). Two C-0 honesty corrections fold in: the governance status is flagged
as having two boundary gates owed (scheduled v1.0.8), and the egress claim is upgraded to
"machine-verified" by `tests/test_egress_allowlist.py`. No new dependency; `PROMPT_VERSION`
/ `AVATAR_PROMPT_VERSION` untouched.

**Changed**
- `README.md` — full rewrite as the product front door; clone URL corrected to
  `github.com/take-tempo-public/sartor`; `DOC-STATUS` freshness markers added.

**Added**
- `docs/dev/documentation-architecture.md` — the documentation publishing strategy that
  the README front door embodies (the layered L0–L3 source chain, Fumadocs-as-projection,
  the merge=publish gate, the `DOC-STATUS` convention). Dev-internal.

### Compose UX flaky-test class stabilized + a real server-side title-pin race fixed (`fix/compose-ux-stabilization`, 2026-06-26)

A v1.0.8 reduction-sprint branch closing carry-forward ledger #3 — the recurring flaky Compose-wizard
UX-test class (~25 logged recurrences). Chasing the last ~1% surfaced **two distinct causes**:

1. **Test-timing (5 of the 6 members).** Entering Compose runs `loadComposition()`, which fires up to 3
   background `recommend-*` calls, each re-running `loadComposition()` (a full `#composeList` teardown +
   rebuild); the Playwright page-object read-helpers did raw queries with no wait and read the DOM
   mid-rebuild. The 8.5 partial fix (waiting on `.compose-experience-card`) only proved the *initial*
   render, not the terminal one.
2. **A real, rare server-side race (the 6th member, `test_positioning_pin_preserves_title_pin`).** The
   flaky test was catching an actual bug, not a harness artifact: the client sends the title pin
   correctly in every `/composition` POST, but the save's title-eligibility validation could
   intermittently not see a just-added title (pooled SQLite + WAL read-snapshot visibility), return
   400, and drop the pin — so a user pinning a title then quickly pinning a positioning variant could
   rarely lose the title pin. The race resists reproduction (it vanished under every instrumentation
   attempt — a Heisenbug), so it's fixed defensively and validated by a deterministic unit test rather
   than an end-to-end repro.

`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched; no new dependency.

**Fixed**
- **Server-side (real bug):** `blueprints/applications.py` `save_application_composition` now self-heals
  a transient title-eligibility miss — on a miss it ends the read transaction (`session.rollback()`)
  and re-reads with a fresh snapshot before returning 400, so a momentarily-invisible just-added title
  is no longer dropped; a genuinely stale/foreign id still 400s. Covered by a deterministic
  miss-then-hit unit test (`test_post_self_heals_transient_title_visibility_miss`).
- **Test-infra (the flaky class):** all 6 members —
  `test_positioning_pin_preserves_title_pin`, `test_keyboard_reorder_persists_and_reset_reverts` /
  `test_pointer_drag_reorders`, `test_add_title_then_pin_persists`,
  `test_no_recommendations_order_persists_on_reload`, `test_compose_skills_card_drop_persists`,
  `test_happy_path_through_template_preview`.

**Changed**
- `static/app.js`: `loadComposition()` clears a `data-compose-ready` attribute on `#composeList` at
  entry (before its `/composition` fetch) and sets it after the final synchronous append — a *stably
  present* marker proves the auto-recommend re-render cascade reached its terminal render. Two
  non-behavioral lines (a `data-` attribute no code/CSS reads → byte-identical render/save/prompt).
- `ui_pages/wizard_compose.py`: new `_wait_settled()` (drains in-flight recommend POSTs via
  `networkidle`, then waits for the marker present + stable across 3×50ms samples); `_wait_loaded()`
  delegates to it; the read-helpers (`bullet_texts` / `title_texts` / `title_is_selected` /
  `experience_card_count` / `chosen_intro_texts`) and action helpers (`reset_order` / `add_title` /
  `drag_below` / `move_*` / `select_title` / `enable_role_intros`, via the `_first_card` /
  `_bullet_list` anchors or explicit calls) settle first; new `wait_skills_card()` / `drop_skill()` /
  `pin_positioning_variant()`.
- `ui_pages/selectors.py`: add `Compose.SKILLS_CARD` / `SKILL_ROW` / `SKILL_DROP` / `READY` /
  `POSITIONING_VARIANT` / `POSITIONING_CHOSEN`.
- `tests/ux/regression/test_20260613_skill_corpus_item.py` + `…/test_20260612_experience_summary_item.py`:
  use the new POM helpers (close the resolve-then-click + raw-positioning-click windows).

**Validation:** the server self-heal is proven by a deterministic miss-then-hit unit test (the live
race is unreproducible — it masked under three separate instrumentation attempts). Supporting empirical
evidence: the previously-flaky positioning test ran **400/400** with the fix (it was ~0.37%, 2-in-544,
before); the other 5 members **30/30** each + group **10/10**; full `pytest -m ux` ✓ (69) and full
`pytest` ✓ (1394). Gate: ruff ✓ · ruff format --check ✓ · mypy ✓ (228). Carry-forward ledger #3 →
Resolved (open count 7 → 6).

### Help-opener de-duplication — shared `static/help-modal.js` leaf (`refactor/help-opener-dedup`, 2026-06-25)

A v1.0.8 reduction-sprint branch closing carry-forward ledger #7. The wizard's help-modal opener
`openHelpModal` (`static/app.js`) and the self-contained diagnostics console's ported `openDashHelp`
(`dashboard/templates/dashboard.html`) were byte-identical logic plus a duplicated `cb_help_seen:`
localStorage seam. Extracted the single implementation into a NEW shared **leaf** module both pages
load — which does **not** make the console load `app.js` (the leaf is loaded like `style.css` / the
vendored chart bundle it already pulls), so the console's self-containment is preserved. **No
product behavior, prompt, route, dep, or version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`
untouched (frontend-only → no eval run owed).

**Changed**
- `static/help-modal.js` (new): the shared primitive — `window.cbOpenHelpModal(entry, triggerEl)`
  (opens the shared `#helpModal` for an already-resolved `{title, body}`; Esc / Tab focus-trap /
  `[data-help-dismiss]` click-away / `aria-expanded` toggle / focus-restore, all null-trigger safe)
  plus the `cb_help_seen:` seam (`cbHelpSeen` / `cbMarkHelpSeen` / `CB_HELP_SEEN_PREFIX`). ES5,
  exposed as `window` globals (no JS build step in the repo; the dashboard inline JS is not an ES
  module).
- `static/app.js`: `openHelpModal` / `_helpSeen` / `_markHelpSeen` reduced to thin wrappers that
  resolve `_HELP_REGISTRY` (kept local) and delegate to the shared globals. Signatures, callers,
  `_HELP_REGISTRY`, `_initHelp`, and all tour logic unchanged.
- `dashboard/templates/dashboard.html`: `openDashHelp` / `_dashSeen` / `_markDashSeen` reduced to
  thin wrappers over `_DASH_HELP` (kept local); the stale "opener lives here" comment refreshed to
  reflect the shared leaf (registry stays local; console still never loads `app.js`).
- `templates/index.html` + `dashboard/templates/dashboard.html`: load the leaf as a classic
  `<script>` (no `defer`) **before** `app.js` (index) and in the dashboard `<head>` **before** the
  inline help IIFE, so the shared globals exist at parse time.

**Gate:** ruff check ✓ · ruff format --check ✓ · mypy ✓ (228) · pytest ✓ (1324) · UX help/dashboard
+ axe tiers ✓ (25). Public function names, DOM ids (`#helpModal` / `#help-icon-*`), and the
`cb_help_seen:` keys are all unchanged → zero test-code changes (the `_TOUR_STOP_BLOCKS` suppression
contract still holds). Carry-forward ledger #7 → Resolved (open count 8 → 7).

### Kit-adoption Phase 2 #4 — `interrogate` docstring-coverage floor-lock gate (`chore/kit-phase2-interrogate`, 2026-06-25)

Fourth and final implementation sub-item of the agent-coding-practices kit-adoption arc **Phase 2**
(the strictness ratchet — kit-adoption-design.md §4/§6; Decision KIT-6 "measured-current /
warn-start" + KIT-7 named-exempt scope). Adds a docstring-**coverage** gate via **interrogate** (a
NEW dev dependency), shaped as a **pytest floor-lock ratchet** mirroring
`tests/test_route_containment_gate.py`: today's measured production coverage is recorded as
`[tool.interrogate].fail-under` and the gate asserts `coverage >= floor` — green today (forces no
new docstrings; KIT-6 "lock the gain, don't force new work"), red only on a regression below the
floor. It is the aggregate-% companion to the ruff-`D` family (which gates per-symbol docstring
*presence*) and runs inside the standard `pytest` gate — no new hook, no `.claude/settings.json`
change, no governance-hooks-gate change. **No product behavior, prompt, route, or version change**;
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (no prompt constant touched → no eval run owed).

**Changed**
- `pyproject.toml`: new `interrogate>=1.7,<2.0` dev dependency in `[project.optional-dependencies].dev`;
  new `[tool.interrogate]` block recording the floor (`fail-under = 99`), the production-only scope
  (`exclude` = the KIT-7 exempt set `tests`/`evals`/`scripts`/`db/migrations` + data/build dirs), and
  the ignore flags chosen to keep the metric coherent with the ruff-`D` google scope
  (`ignore-module`/`ignore-magic`/`ignore-private`/`ignore-semiprivate`/`ignore-nested-functions`/
  `ignore-overloaded-functions`/`ignore-init-method`; `@property` accessors COUNT —
  `ignore-property-decorators = false` — to match the D102 treatment of `config.py`'s derived-root
  properties). Single-underscore helpers are semiprivate and excluded, so a helper-only module like
  `web_infra/` contributes zero counted symbols by design.
- `tests/test_docstring_coverage_gate.py` (new): the floor-lock gate. Re-runs the bare interrogate
  CLI via subprocess (single source of truth = `[tool.interrogate]`; no `import interrogate`, so no
  mypy/stub coupling and robust to interrogate API drift) and asserts exit 0. Skips gracefully when
  interrogate is not installed (mirrors the `tests/ux/conftest.py` Chromium skip-guard) so default
  `pytest` stays green without dev-extras; has teeth in CI. Teeth assertions: the scan names core
  production modules and covers a non-trivial symbol surface (≥ 250 of the current 417). `ui_pages/**`
  is IN scope (matching the surface the ruff-`D` family covers, its ratchet unit 8).
- `onboarding/review_cli.py`, `onboarding/extract_experiences.py` (docstrings only): documented the two
  public classes `Color` and `ExtractResponse` that interrogate surfaced at adoption — genuine gaps
  that ruff-`D`/google's D101 does not flag (attribute-only / pydantic-model classes). Documenting them
  took public-API production coverage from 99.5% to **100%**, so the recorded floor (`fail-under = 99`)
  locks a fully-documented baseline with ~1 pt of headroom against incidental churn (not a brittle 100).
- Owner-directed documentation pass (docstrings only, no behavior change): documented the **50**
  below-public-bar internal symbols interrogate surfaces at *maximal* scope (single-underscore helpers,
  nested SSE/worker closures, and private methods across ~20 production files — `analyzer.py`,
  `blueprints/**`, `parser.py`, `json_resume.py`, `corpus_to_json_resume.py`, `dashboard/`, `recall/`,
  `web_infra/`, `onboarding/`, `ui_pages/`), taking *maximal*-scope production coverage (all ignore
  flags off) to **100%** as well. The interrogate **gate stays public-API-scoped** (ignore flags
  unchanged, coherent with ruff-`D`) — these docstrings are a quality pass, not a gate-scope change.
  `analyzer.py` re-verified **PROMPT-SAFE** (all 15 prompt constants sha256 byte-identical vs HEAD).
  Also added module docstrings to the 5 empty `tests/**/__init__.py` package markers; KIT-7 keeps
  `tests/` D-exempt, so no per-function test docstrings were added.

**Gate:** ruff check ✓ · ruff format --check (218) ✓ · mypy (228) ✓ · pytest. New dependency
(interrogate) added → CHANGELOG updated (charter D-1 / AGENTS.md "What NOT to do"). No version bump
(tooling config + one test + a docstring-only pass: 2 public-class fixes + 50 internal helpers + 5 test
`__init__` modules); the `ruff-changed` hook needs no edit (the gate is the standard `pytest` arm).
Teeth verified: with `fail-under` temporarily at 100 vs 99.5% actual the
floor-lock test went red, then green again at the locked floor. KIT-6 "warn-start": the floor locks
today's coverage; "ratchet up later" = raise `fail-under` in a future branch. **Phase 2 of the
kit-adoption arc is now COMPLETE** (only the 8.7 skills/hooks-coherence remainder rides on).

### Kit-adoption Phase 2 #3 — ruff `D` (pydocstyle/google) enabled + first ratchet rung (`chore/kit-phase2-ruff-d`, 2026-06-24)

Third implementation branch of the agent-coding-practices kit-adoption arc **Phase 2** (the
strictness ratchet — kit-adoption-design.md §4; Decision KIT-6 "ratchet-then-block" + KIT-7
named-exempt end-state). Enables the ruff `D` (pydocstyle) family with the **google** convention.
The docstring-**content** rules block tree-wide; the **missing-docstring** rules ratchet per-module
(first documented module: `hardening.py`). Tooling-config + docstrings only — **no product behavior,
dependency, prompt, route, or version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched
(docstrings are not prompt constants — the analyzer prompt-constant sha256 dump is byte-identical
pre/post, so no eval run is owed).

**Changed**
- `pyproject.toml`: `select += "D"`; new `[tool.ruff.lint.pydocstyle] convention = "google"` (narrows
  D to google's subset + silences the D203/D211 + D212/D213 conflicts). `per-file-ignores`: `"D"`
  added to the three exempt entries (`tests/**`, `evals/*`, `scripts/**`); a new **D missing-docstring
  ratchet block** waives only `D101/D102/D103/D105/D107` on the 27 not-yet-documented production
  modules (16 entries; `ui_pages/**` is the 12-file POM glob) — the content rules still apply to them.
  The list shrinks branch-by-branch toward the §6 exit criterion (empty → D blocks everywhere outside
  the exempt set).
- Docstring-content sweep across the production tree (39 files, docstrings only): 105 safe autofixes
  (D209/D411/D412) + 143 hand fixes (D205 blank-line-after-summary ×139, D301 raw-string ×3, D415
  terminal-period ×1) so the content rules pass tree-wide. `D205` has no safe autofix in ruff 0.15.12.
- `hardening.py`: documented its 10 public TypedDict classes (`CandidateInfo` … `ContextSet` — the
  `context_set` JSON contract between pipeline stages) → the module is now fully `D`-clean and the
  google-style reference for later ratchet branches.
- `.git-blame-ignore-revs`: the mechanical content-sweep commit (`6ee0be1`) added so blame skips it.
- **Ratchet COMPLETE — §6 exit for `D`** (`chore/kit-phase2-ruff-d-ui-pages`, 2026-06-25): units 2–8
  drained the remaining production modules branch-by-branch (`recall/` · `config.py` ·
  small-blueprints trio · `onboarding/` trio · `db/models.py` · `analyzer.py` · `ui_pages/**`), so the
  missing-docstring ratchet block is now **empty**. `D` (incl. `D101/D102/D103/D105/D107`) blocks
  **everywhere outside the KIT-7 exempt set** (`tests/**` · `evals/*` · `scripts/**` ·
  `db/migrations/versions`). `ui_pages/**` — the 12-file Playwright Page-Object-Model, 89 symbols —
  was the last + largest unit; docstrings only across every unit (no dependency/version/prompt change).

**Gate:** ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest. No new dependency
(ruff already present); no version bump (lint config only); the `ruff-changed` hook needs no edit
(`ruff check` inherits `select`). `D` hard-blocks day one (KIT-6 — unambiguous, not warn→block).

### Kit-adoption Phase 2 #2 — mypy `--strict` on leaf modules (`chore/kit-phase2-mypy-strict-leaves`, 2026-06-24)

Second implementation branch of the agent-coding-practices kit-adoption arc **Phase 2** (the
strictness ratchet — kit-adoption-design.md §4; Decision KIT-6 "ratchet-then-block" + KIT-7
named-exempt end-state). Brings the first three modules to full mypy `--strict` + `warn_unreachable`
via a per-module override — the **first rung** of the module-by-module `--strict` ratchet toward the
§6 exit criterion. Tooling-config + one type-annotation only — **no product behavior, dependency,
prompt, route, or version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

**Changed**
- `pyproject.toml` `[[tool.mypy.overrides]]`: new per-module block tightening `scraper`,
  `json_resume`, `pdf_render` (the deterministic, LLM-free P1-Hardening leaves) to the `--strict`
  preset + `warn_unreachable`. `strict` is **not** a per-module-settable option
  (`mypy.options.PER_MODULE_OPTIONS`), so the preset is spelled out as its per-module-capable
  component flags (`disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_untyped_calls`,
  `disallow_untyped_decorators`, `disallow_any_generics`, `disallow_subclassing_any`,
  `check_untyped_defs`, `warn_return_any`, `strict_equality`, `extra_checks`) + `warn_unreachable`.
  The global mypy config stays permissive; these three modules now block.
- `scraper.py`: `fetch_profile_content(config: dict)` → `dict[str, Any]` (the one
  `disallow_any_generics` hit — keys are `str`, values heterogeneous, so `dict[str, Any]` is the
  honest minimal type; not bare `Any`, so `ANN401` does not flag it) + `from typing import Any`.
  `json_resume.py` and `pdf_render.py` were already `--strict`-clean (0 changes). The three leaves
  are pure (stdlib / 3rd-party imports only, no intra-project calls) → strict treatment surfaced no
  cross-module cascade.

**Verification** — `ruff check .` clean tree-wide · `ruff format --check` (217 files) ok ·
`mypy .` (227 files) ok · `pytest` **1390 passed / 1 known-flaky** (the tracked Compose-load UX race
`test_20260604_bullet_drag_reorder::test_pointer_drag_reorders` — intermittent on both this branch
and the clean tree, **not code-caused**: this branch touches no Compose/`app.js` code; see
RELEASE_CHECKLIST carry-forward ledger #3). No eval run (no prompt change). Per-module tracking:
3 production modules now at full strict; the rest remain permissive (no override = permissive).
Remaining Phase 2: `D` + google pydocstyle, `interrogate` coverage gate, larger-module `--strict`
(`analyzer.py` / `applications.py`) — each its own later branch.

- **Rung 2 — `blueprints.applications`** (`chore/kit-phase2-mypy-strict-applications`, 2026-06-25):
  the next rung adds `blueprints.applications` (~2,100 LOC — the first **non-leaf route/seam**
  module) to the same strict override roster. Clean for a different reason than the pure leaves:
  Phase-2 #1 (`ANN`) had already annotated its whole call graph, so `--strict` + `warn_unreachable`
  surfaced **no `disallow_untyped_calls` cascade** — only **13 errors**, all mechanical (12
  bare-generic `type-arg` → parametrized, predominantly `dict[str, Any]`; 1 `no-any-return` →
  `cast("str | None", …)`, a runtime no-op). `_load_application_owned` stays `tuple[Any, Any]`
  (parametrized for `disallow_any_generics`; the precise `tuple[Application|None, Candidate|None]`
  would force a None-narrowing change at its 9 in-module callers — a deferred None-safety pass, out
  of scope for a typing rung; the docstring records this). The strict roster is now
  `scraper`/`json_resume`/`pdf_render`/`blueprints.applications`. PROMPT-SAFE (no prompt constants
  in the module — grep-0; the `anthropic` refs are exception types). No prompt/dep/version change;
  gate green (ruff/format ✓ 217, mypy ✓ 227, pytest **1389 passed / 2 known-flaky** — both the
  ledger #3 Compose load-race, passed clean isolated 2/2). Remaining Phase 2: `interrogate`
  coverage gate + larger-module `--strict` (`analyzer.py`).

- **Rung 3 — `analyzer.py`** (`chore/kit-phase2-mypy-strict-analyzer`, 2026-06-25): the final
  *larger-module* rung adds `analyzer.py` (~3,800 LOC — the prompt-home module and the sole LLM-call
  site) to the strict override roster, **completing the larger-module `--strict` commitment** (the
  three leaves landed rung 1, `applications.py` rung 2). Clean for the same reason as rung 2: Phase-2
  #1 (`ANN`) had pre-typed the whole call graph, so `--strict` + `warn_unreachable` surfaced **no
  `disallow_untyped_calls` cascade** — only **47 errors**, ~91% mechanical: 43 bare-generic `type-arg`
  → parametrized (`dict[str, Any]` / `list[dict[str, Any]]`), 2 `no-any-return` →
  `cast("dict[str, Any]", …)` (runtime no-ops), and 2 `warn_unreachable` — one a `ContextSet`-TypedDict
  always-truthy artifact on a deliberate `or {}` persisted-JSON defense (kept behind a scoped
  `# type: ignore[unreachable]`), the other fixed by widening one local to `object` so a documented
  dict-or-list branch stays live (no runtime change). The strict roster is now
  `scraper`/`json_resume`/`pdf_render`/`blueprints.applications`/`analyzer`. **PROMPT-SAFE the GOTCHA-4
  way** (analyzer.py is the prompt home, so the module's grep-0 shortcut doesn't apply): the 15 prompt
  constants (11 `_BASE_SYSTEM_PROMPTS` values + `AVATAR_SYSTEM_PROMPT` + `_COVER_LETTER_RULES_BLOCK` +
  `PROMPT_VERSION` + `AVATAR_PROMPT_VERSION`) were sha256-proven byte-identical pre/post → no
  `PROMPT_VERSION` bump, no eval. Gate: ruff ✓ · ruff format --check ✓ 217 · mypy ✓ 227 · pytest — the
  ledger #3 Compose bullet-load race **fired on the pre-commit run** (**1389 passed / 2 failed**:
  `test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts` +
  `::test_pointer_drag_reorders`), both **passed clean isolated** (1/1, 2/2); an earlier same-session
  full run on the **identical** code was clean (1391/0) — the same-code fire-then-clean alternation is
  itself proof the branch (annotations + config + docs, runtime-inert for Compose) is **not
  code-caused**. Remaining Phase 2: the `interrogate` coverage gate (the larger-module `--strict`
  commitment is now complete).

### Kit-adoption Phase 2 #1 — enable ruff `ANN` (`chore/kit-phase2-ruff-ann`, 2026-06-24)

First implementation branch of the agent-coding-practices kit-adoption arc **Phase 2** (the
strictness ratchet — kit-adoption-design.md §4; Decision KIT-6 "ratchet-then-block" + KIT-7
exempt set). Enables the `flake8-annotations` (`ANN`) lint family whole across the production
tree, fixes every real hit by hand, and carves the Decision-7 exempt set. Tooling-config +
type-annotation only — **no product behavior, dependency, prompt, route, or version change**;
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (no prompt string was edited; annotations
are runtime-inert, so generation output is byte-identical).

**Changed**
- `pyproject.toml` `[tool.ruff.lint]`: `select += ["ANN"]` (whole-family, forward-protective —
  ANN is unambiguous, so it hard-blocks day one via `ruff-changed.sh`, not warn→block
  ratcheted). `per-file-ignores += "ANN"` for the Decision-7 strictness-exempt set:
  `tests/**`, `evals/*`, and a net-new `scripts/**` entry (`db/migrations/versions` is already
  fully `extend-exclude`d). Production carries **no** ANN override — the §6 exit-criterion shape
  for this rule family.
- Hand-annotated **60 production violations across 18 files** (ruff's ANN autofix is
  `--unsafe-fixes`-only — none used, per Phase-1 discipline): SSE `stream`/`worker` inner-fns
  → `Iterator[str]` / `None` (`blueprints/diagnostics|analysis|generation|assistant.py`); route
  handlers → `ResponseReturnValue`; serializers/loaders → the `db.models` row types + `Session`
  (via `TYPE_CHECKING` blocks); docx plumbing → `Paragraph` / `Run` / `CT_NumPr`
  (`generator.py`, `parser.py`).
- **`ANN401`** (11 any-type hits) handled case-by-case (no blanket family ignore): typed the
  typeable (`session: Session`, `client: Anthropic`, `exp: Experience`, `raw: object`,
  `val: str | int | float | None`, `parent: Document | _Cell`); one **targeted `# noqa: ANN401`**
  on `db/session.py`'s SQLAlchemy `connect`-event listener (DBAPI / pool objects are dynamically
  typed at that boundary by design).
- Minor typing-driven, behavior-preserving body touches surfaced by the now-checked bodies:
  `_load_application_owned` / `_tag_link_target` return a bare `tuple` (their slots are
  correlated/polymorphic — precise typing would force an out-of-scope None-narrowing pass at the
  call sites); `_tag_link_target` uses a distinct `skill` local so `subject` is a clean
  `Bullet | ExperienceTitle` union; `blueprints/assistant.ask()` keeps `safe_user` a plain `str`
  via a `resolved` temp (a latent `str | None` surfaced once `ask()` gained a return type).

**Verification** — `ruff check .` clean tree-wide · `ruff format --check` (217 files) ok ·
`mypy .` (227 files) ok · `pytest` **1391 passed** (the tracked Compose-wizard load-race class
passed clean this run). No eval run (no prompt change). Phase 2 sub-items `D` / `interrogate` /
mypy `--strict` remain (each its own later branch).

### Kit-adoption Phase 1 — SIM/RUF ruff triage (`chore/kit-phase1-sim-ruf-triage`, 2026-06-24)

Final implementation branch of the agent-coding-practices kit-adoption arc Phase 1
(kit-adoption-design.md §4; Decision-6 "ratchet-then-block"). Enables the `flake8-simplify` (`SIM`)
+ `ruff`-specific (`RUF`) lint families whole, fixes the real hits, and ignores the documented noise.
Tooling-config + mechanical-cleanup only — **no product behavior, dependency, prompt, route, or
version change**; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (no prompt string was edited —
the ambiguous-unicode hits inside prompt text are *ignored*, not rewritten).

**Changed**
- `pyproject.toml` `[tool.ruff.lint]`: `select += ["SIM", "RUF"]` (whole-family, forward-protective);
  `ignore += ["RUF001", "RUF002", "RUF003"]` (117 ambiguous-unicode false-positives — em-dashes /
  smart-quotes in prompt + UI copy, the documented Decision-6 noise) `+ ["SIM905"]` (the
  `hardening.STOP_WORDS` compact `.split()` constant — the fix explodes it into a ~110-element literal);
  `per-file-ignores["tests/**"] += ["RUF059"]` (idiomatic unused-tuple-unpack in tests, matching the
  existing S-family test carve-outs).
- Auto-fixed 41 hits via `ruff check --fix` (no `--unsafe-fixes`): **RUF100** unused-noqa ×33, **SIM300**
  yoda-conditions ×3, **RUF022** unsorted-`__all__` ×3, **RUF023** unsorted-`__slots__` ×1
  (`analyzer._StreamDone` — prompt-inert), **SIM114** if-with-same-arms ×1.
- Hand-fixed 32 real hits: **SIM115** open-without-context-manager ×16 → `Path(...).read_text/write_text`
  (all in tests); **RUF012** mutable-class-default ×7 → `ClassVar[...]` (6 test data tables + one
  `ui_pages` lookup dict); **SIM117** nested-`with` ×4 → combined; **SIM105** suppressible-exception ×4 →
  `contextlib.suppress`; **RUF022** ×1 → `# noqa: RUF022` on `db/models.py` `__all__` (preserves the
  curated domain grouping a flat sort would scatter).

**Verification** — `ruff check .` clean tree-wide · `ruff format --check` (217 files) ok · `mypy .`
(227 files) ok · `pytest` **1390 passed / 1 flaky** (`test_add_title_then_pin_persists`, the tracked
Compose-wizard load-race class — passed clean on isolated re-run; diff touches no Compose/frontend code).
No eval run (no prompt change). **Closes kit-adoption Phase 1.**

### Kit-adoption Phase 1 — ruff format (`chore/kit-phase1-ruff-format`, 2026-06-23)

Second implementation branch of the agent-coding-practices kit-adoption arc (kit-adoption-design.md
§4 Phase 1). Applies the `ruff format` auto-formatter tree-wide and wires it as a commit-time gate.
Style/tooling only — **no product code, dependency, prompt, route, or version change**;
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched (proven byte-identical).

**Changed**
- Applied `python -m ruff format .` across the tree — **161 of 217 files** reformatted (56 already
  clean). Pure formatter output: hand-packed collection literals (`frozenset({...})`) exploded one
  item per line, type annotations / comprehensions reflowed, blank-line normalization. No hand edits.
- `.claude-plugin/hooks/ruff-changed.sh` — the pre-commit `ruff` hook now also runs
  `ruff format --check` on staged Python and blocks an unformatted commit (KIT-6 "hard-block
  unambiguous gates day one"), alongside the existing `ruff check`.
- `pyproject.toml` `[tool.ruff.format]` — declares the adopted formatter style
  (`quote-style = "double"`, `indent-style = "space"`; matches ruff defaults, so reformat output is
  unchanged) so the gate is deterministic across machines + ruff versions.

**Added**
- `.git-blame-ignore-revs` — lists the reformat commit so `git blame` (and GitHub) skip the
  mass-formatting noise.

**Verification** — prompt constants proven byte-identical via a sha256 dump-diff (31 entries: every
`*_SYSTEM_PROMPT`, the `_BASE_SYSTEM_PROMPTS` registry, `_COVER_LETTER_RULES_BLOCK`, both version
strings — zero differences); gate green: `ruff check .` ok · `mypy .` (227 files) ok · `pytest` 1391
passed. No eval run (provably prompt-inert).

### Kit-adoption Phase 1 — Pydantic-aware mypy (`chore/kit-phase1-pydantic-mypy`, 2026-06-23)

First implementation branch of the agent-coding-practices kit-adoption arc (kit-adoption-design.md §4
Phase 1; owner-selected "lint+typing wins, defer format" subset). Tooling-config only — **no product
code, dependency, prompt, route, or version change**; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` untouched.

**Changed**
- `pyproject.toml` `[tool.mypy]`: enabled the `pydantic.mypy` plugin so mypy understands the analyzer
  Pydantic response models' generated `__init__`/validator signatures. The plugin ships inside the
  already-present `pydantic` dependency — **no new dependency**. mypy stays green ("no issues found in
  227 source files").

**Notes — two Phase-1 items evaluated and rejected for this codebase (recorded in
`docs/dev/kit-adoption-design.md` §4):**
- **ruff `ERA` (commented-out-code) NOT enabled** — all 8 `ERA001` hits are false positives on
  legitimate documentation prose (JSON-shape examples, TypedDict shape docs, `# Section (name)`
  dividers). This is the case Decision 6 (KIT-6) marks *warn-only forever*; enabling it blocking would
  clutter docs and block future prose comments, with no advisory lane until the 8.7 pre-commit core.
- **SQLAlchemy mypy plugin NOT enabled** — `db/models.py` uses native SQLAlchemy 2.0 typing
  (`DeclarativeBase` + `Mapped[...]` + `mapped_column`), for which `sqlalchemy.ext.mypy.plugin` is
  deprecated/unneeded.

Deferred to their own Phase-1 branches: `ruff format` (161-file restyle) and `SIM`/`RUF` per-family triage.

### Agent-coding-practices kit-adoption — evaluation + planning record (`docs/kit-adoption-arc`, 2026-06-23)

Docs-only. Persisted the settled evaluation of the lichen `agent-coding-practices-kit` handoff
(8 decisions; full faithful adoption, "implement + flag promotable") so it doesn't live only in
the session. **No code, config, dependency, or version change** — this is the planning record;
the implementation phases are scheduled separately and thread `feat/portable-enforcement-core`
(8.7) + WS-2-full.

**Added**
- `docs/dev/kit-adoption-design.md` — canonical evaluation, the 8 decisions + rationale, the
  5-phase sequenced arc, the temporal map, and the strict-ratchet exit criterion.
- `docs/dev/decisions.md` — a thin architectural-decision index (one line + pointer per
  decision), seeded with the 8 kit decisions + the enforcement-portability SPLIT backfill.

**Changed**
- `docs/dev/RELEASE_ARC.md` — recurring workstreams: tied WS-2-full to the arc + added the
  kit-adoption workstream bullet.
- `docs/dev/RELEASE_CHECKLIST.md` — folded the kit's gates + skills/hooks coherence into the 8.7
  `feat/portable-enforcement-core` item; added one Carry-forward ledger row for the staged
  commitments (open count 8 → 9).

### v1.0.8 correction sprint — cover-letter tone (`fix/window-findings-tone`, Sprint 8.6, PV-3)

The second 8.6 sub-branch: **PV-3 cover-letter tone tune** — the only `PROMPT_VERSION`-bumping
change in the v1.0.7/v1.0.8 epics. Reinforces the existing throat-clearing/hedging bans (the
v1.0.3 `tone` lapse was an *adherence* slip, not a missing rule) via the project's standard
mechanism — a worked OK/NOT-OK example. `AVATAR_PROMPT_VERSION` untouched; no new dependency.

**Changed**
- `analyzer.py` `_COVER_LETTER_RULES_BLOCK`: de-cloned the single STRUCTURE-Para-3 close example
  (the model was copying `"I'd welcome a direct conversation about what this team is building."`
  near-verbatim into the documented lapse) — replaced with a functional description of the close's
  job (concrete topic / timing signal / scheduling line; implies initiative, never polite waiting).
- `PROMPT_VERSION` `2026-06-13.1` → `2026-06-23.1` (same commit).

**Added**
- `analyzer.py` `_COVER_LETTER_RULES_BLOCK`: a `WORKED EXAMPLES` sub-block — OK / NOT-OK pairs for
  the cover-letter **opener** and **close**, the two surfaces the v1.0.3 lapse hit.
- `tests/test_corpus_mode_prompt.py::TestCoverLetterWorkedExamples` — deterministic ($0) assertions
  that the worked-example scaffold is present and wired into the generate prompt when
  `with_cover_letter=True`, absent when `False`.

**Fixed**
- `evals/runner.py`: the **EV-3-class cp1252 console crash** the 8.6 grounding fix didn't cover —
  `--help` (the `→` epilog) and any `→` print raised `UnicodeEncodeError` under a Windows cp1252
  console. Added the same `sys.stdout`/`sys.stderr.reconfigure(encoding="utf-8")` loop at
  `runner.main()` entry (mirrors `scripts/export_corpus_seed.py` + `capture_screenshots.py`); verified
  exit 0 plain and under forced `PYTHONIOENCODING=cp1252`. Surfaced during the PV-3 validation;
  owner-directed fold-in before the merge.

**Validation** — paired before/after `--suite synthetic --subset full`, n=3 each side: **tone holds
at the 4.2 floor with no regression on any rubric**; the opener/close fix is judge-confirmed adopted
(substance-first opener + concrete close). One sub-4.0 after-sample (pm 3.2) was a scenario-specific
gap-admission hedge, a *different* tone failure mode than PV-3 targeted. Detail + tables:
[`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) (2026-06-23 PV-3 entry). Gate: ruff · mypy (227) ·
pytest **1391** incl. `-m ux`.

### v1.0.8 correction sprint — grounding slice (`fix/window-findings-grounding`, Sprint 8.6)

The first 8.6 sub-branch burns the **grounding slice** of the
[`window-8.5-findings.md`](docs/dev/window-8.5-findings.md) backlog (EV-1/EV-2/EV-3 + S3-1).
**Eval/dev tooling only — no product-behavior change**; `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched. PV-3 cover-letter tone is a sibling branch; the
`/wiki-ingest` re-anchor folds into 8.6a. PV-1 labels + PV-2 calibration are staged
(owner-gated, may spill to v1.0.9).

**Changed**
- `pyproject.toml` (`eval-grounding` extra): **pinned `minicheck`** to commit
  `b58b9fa69acbd1015ec970fa65dd752413a053d2` (was an unpinned `git+` ref that drifted to a
  vLLM/Bespoke-7B rewrite — EV-1, HIGH) and **widened the `transformers` cap** `>=4.40,<5.0`
  → `>=4.40,<6.0` (the `<5.0` pin was already being violated by a fresh install; validated on
  5.10.2). The CPU `flan-t5-large` scorer was re-validated end-to-end (NLI mean 0.995,
  MiniCheck mean 0.973).

**Added**
- `pyproject.toml` (`eval-grounding` extra): **`accelerate>=1.0`** (required by
  `transformers>=5` for the `device_map="auto"` the MiniCheck loader uses) and **`nltk>=3.9`**
  (declared directly — `evals/grounding_signals.py` now ensures its `punkt_tab` data).
- `scripts/build_vector_index.py`: a `manifest.json` (`built_at_sha`) written on build + a
  `--check` staleness mode (manifest sha vs HEAD) so the gitignored vector index can no longer
  silently stale after a refactor moves code (S3-1). Local `--full` rebuild re-anchored the
  index onto `blueprints/**`.

**Fixed**
- **EV-1** — the L2/MiniCheck grounding scorer no longer crashes: dropped the removed `device`
  kwarg in `evals/grounding_signals.py` and auto-ensure NLTK `punkt_tab` before scoring. (The
  finding's "dropped `flan-t5-large`/`score()`-shape" root cause was inaccurate — corrected in
  the findings doc; the real breaks were `device` + the `accelerate`/`punkt_tab` deps.)
- **EV-2** — `evals/bootstrap.py:build_bootstrap_document` wraps the optional `grounding_fn`
  call in `try/except` (log + `grounding=None` + still return the doc), so a grounding scorer
  failure never discards the completed (paid) analyze/clarify/generate work. The browser
  bootstrap route (`blueprints/diagnostics.py`) reconciled to a single outcome-derived note.
- **EV-3** — `scripts/export_corpus_seed.py` + `scripts/capture_screenshots.py` reconfigure
  `stdout`/`stderr` to UTF-8 at entry, so the unicode in their progress output and `--help`
  text no longer `UnicodeEncodeError`s on a Windows cp1252 console (the export previously
  exited non-zero *after* the seed had written).

### v1.0.8 gated test window — eval half (`eval/live-shakedown-labels`, Sprint 8.5)

The first run of the real-data eval/tuning loop on the decomposed code, plus the S3
gate-override validation owed since v1.0.7. **No product-behavior change** — the only new
code is eval/test apparatus; `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched, no
dependency or migration. The window's *purpose* — surfacing so-far-unexercised
integration issues — is met; the issues themselves are triaged into a findings backlog
that the 8.6 correction sprint burns.

**Added**
- `scripts/vector_before_after_eval.py` — a judge-scored **before/after relevance eval**
  for the S3 vector tier (the gate-override validation the 7.6 override owed). Runs a
  dev-vocab question set through `recall.assemble` with the lexical tiers vs +S3 and scores
  each set's relevance with the Haiku eval-judge (reuses `evals.runner._grade`, so no
  egress-allowlist change; retrieval corpus = committed wiki+code, no PII). **Verdict:
  KEEP** — mean relevance 1.12 → 2.58 (+1.46); the `numpy`+`model2vec` footprint earns its
  keep. See `evals/TUNING_LOG.md` (2026-06-23) + `docs/dev/window-8.5-findings.md`.
- `docs/dev/window-8.5-findings.md` — the one numbered findings backlog (EV-1 minicheck
  unpinned-git-dep drift · EV-2 grounding-abort discards work · EV-3 seed-export unicode
  crash · S3-1 stale vector index) the 8.6 sprint consumes.
- `docs/dev/window-8.5-walkthrough.md` — the E2E walkthrough runbook (R2-live + post-split
  route surface + assistant + diagnostics) for the deferred walkthrough half.

**Fixed**
- The recurring flaky Compose-wizard UX race (Carry-forward ledger #3, ≥3 members) —
  **test-only**: `ui_pages/wizard_compose.py:_wait_loaded()` now settles on
  `.compose-experience-card` (always rendered) instead of `.compose-row.recommended`
  (absent on no-recommendations fixtures = the race). 20/20 loop, zero flakes.

**Deferred to 8.6 (owner-decided 2026-06-23)** — PV-1 label production (blocked on EV-1:
fix minicheck first, then one full L0+L1+L2 annotation pass) and the E2E walkthrough +
R2-live verification (run against `main`).

### Added — KEEP-ledger do-not-regress guard tests (`test/keep-ledger-guards`, Sprint 8.4, PX-29)

The load-bearing security / PII / accessibility / governance KEEP affirmations from
the 2026-06 product-excellence review (cross-referenced from
[`docs/dev/keep-ledger.md`](docs/dev/keep-ledger.md) → the findings register) are now
committed **guard tests** asserting the **final post-blueprint-split layout**, so
neither the split nor the v1.1.0 public tag can quietly weaken them. They reuse the
existing AST-gate precedents (`tests/test_egress_allowlist.py` reviewed-allowlist +
`tests/test_construction_boundary.py` AST-walk). **No prompt / dependency / migration**
— `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

- **F-sec-05 route containment** — `tests/test_route_containment_gate.py` AST-walks
  every `blueprints/**.py` route and asserts every filesystem-touching route carries
  `_within` (containment) + `_safe_username` (user-scoping), with two reviewed,
  reasoned exemption registries: `WITHIN_NOT_REQUIRED` (containment delegated to a
  sanitizing helper, or a fixed / sanitized-only path) and `SAFE_USERNAME_NOT_REQUIRED`
  (no `<username>` to verify). Each registry waives exactly one guard, so a no-username
  download that loses `_within`, or an exemption that later gains its guard, still
  fails. Detection is docstring/comment-free (per-statement `ast.unparse`) and
  call-form (`_within(` / `_safe_username(`), so a guard named only in prose never trips
  it. This commits the `route-security-lint` hook's intent over the **whole** tree (the
  hook scans only the Edit diff), closing the WATCH rider the review flagged.
- **F-sec-06 zero-PII clone** — `tests/test_zero_pii_clone.py` generalizes the
  `configs/`-only `git ls-files` check to the whole PII/secret surface (configs /
  resumes / output / personas / `evals/fixtures/real` / db / logs track only synthetic
  fixtures), asserts no secret-shaped file is tracked, scans tracked text files for the
  `sk-ant-…` API-key shape (self-safe assembled pattern), and pins the load-bearing
  `.gitignore` lines so a future "tidy" can't silently un-ignore real data.
- **F-expa11y-07 / F-expa11y-08 a11y floor** — `tests/test_a11y_floor_guards.py`
  (always-runs static scan: the `#srAnnounce` polite/atomic live region + the
  `_announce()` helper + its ≥7 success call sites; the keyboard reorder
  buttons/aria-labels/`_moveBulletRow`) + `tests/ux/a11y/test_announce_live_region.py`
  (Chromium-gated: drives analyze→completion and asserts the live region receives the
  announcement). The review had flagged `_announce()` as "no test guards it."
- **F-gov-04 hook witness/blocker split** — `tests/test_governance_hooks_gate.py` pins
  the 7 enforced blockers (reachable `exit 2`) and 3 witnesses (never `exit 2`) as named
  frozensets and cross-checks the `.claude/settings.json` wiring (blockers → PreToolUse,
  witnesses → PostToolUse).

### Changed — route-containment drift closed (3 behavior-identical hardenings, Sprint 8.4)

Restoring the `_within` containment guard the route-containment gate requires, after
the 8.3 blueprint split's body-only move-edits had silently dropped it from two routes
(the F-sec-05 WATCH rider). **All three are behavior-identical** (verified green under
the existing route tests):

- `upload_resume` / `list_resumes` (`blueprints/corpus/curation.py`) gain a redundant
  `_within(…, RESUMES_DIR)` — always-True today because the path is built only from
  `secure_filename` / `_safe_username`-sanitized parts (belt-and-suspenders).
- `download_file` (`blueprints/generation.py`) replaces its inline
  `full_path.resolve().relative_to(OUTPUT_DIR.resolve())` containment check with the
  canonical `_within(full_path, OUTPUT_DIR)` (a literal extraction — `_within`'s body
  *is* that check).
- Doc accuracy: `AGENTS.md` now states `route-security-lint` covers `app.py` +
  `blueprints/**.py` (the PX-21 widen) and names the committed gate.

### Changed — diagnostics blueprint seam — the last seam, app.py → zero routes (`refactor/app-blueprints-diagnostics`, Sprint 8.3h)

The seventh and **final** domain seam of the v1.0.8 `app.py`→blueprints
decomposition. The 9 diagnostics routes (annotation / bootstrap / eval / tune — the
localhost dev-console write/SSE backend) moved out of `app.py` to a new single-module
`blueprints/diagnostics.py`, after which **`app.py` carries zero `@app.route`
handlers** and is the thin composition root (factory + WSGI handle + `main()`). **No
behavior change** — every URL / method / request / response is byte-identical; **no
prompt / dependency / migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`
untouched.

- **9 routes → `blueprints/diagnostics.py`** (registered with **no `url_prefix`** →
  all 9 URLs byte-identical, verified by an `app.url_map` path+methods diff: 96 rules
  unchanged, only the 9 endpoints gain a `diagnostics.` prefix): `annotation_fixtures`
  · `annotation_load` · `annotation_save` · `annotation_collate` ·
  `annotation_score_grounding` (SSE) · `annotation_seed_export` ·
  `annotation_bootstrap_stream` (SSE) · `eval_run_stream` (SSE) · `tune_run_stream`
  (SSE). The 4 diagnostics-only domain helpers moved with them
  (`_annotation_fixture_path`, `_load_bootstrap_doc`, `_write_seed_json`,
  `_patch_annotation_scores`); `_annotation_fixture_path` is now **pure** (takes its
  `annotation_root` explicitly rather than reading a module global). Bodies read
  `current_app.config["ANNOTATION_ROOT"]` / `["CONFIGS_DIR"]` and import the shared
  `web_infra` helpers; PV-4 `-> ResponseReturnValue` on every route. The 5 SSE routes
  keep the established pattern (config captured as a local **before** the `stream()`
  generator, which never touches `current_app`).
- **The transitional `app.py`-local block retired (zero-debt completion).** With the
  last routes gone, the local helper copies (`_safe_username` / `_load_config` /
  `_save_config` / `_get_or_provision_candidate`) and the module path globals
  (`BASE_DIR` / `CONFIGS_DIR` / `RESUMES_DIR` / `OUTPUT_DIR` / `ANNOTATION_ROOT` /
  `ALLOWED_EXTENSIONS`) — kept since 8.3a's "Option X" for the not-yet-moved routes —
  were deleted; the orphaned imports were pruned. `_should_open_browser` stays
  (`tests/test_browser_open.py` imports it; `main()` calls it).
- **Egress unchanged.** `blueprints/diagnostics.py` imports no `anthropic` — the routes
  catch only generic `Exception` and delegate the paid work to `evals.runner` /
  `evals.bootstrap` / `evals.grounding_signals` (already allowlisted) and the
  `web_infra` client factory — so it is **not** added to the egress allowlist, and
  `app.py` stays off it.
- **Tests migrated, no module-global monkeypatch left for the seam.**
  `tests/test_annotation_routes.py` builds a `create_app(Config(base_dir=tmp))` app
  (DB-path monkeypatch kept; the containment helpers exposed via a `SimpleNamespace` so
  the bodies are unchanged). `tests/test_app_security.py`'s three helper-test classes
  (`TestSafeUsername` / `TestWithin` / `TestConfigHelperContainment`) retarget to the
  canonical `web_infra` helpers. The UX harness drops the now-dead module-global
  monkeypatch and injects `ANNOTATION_ROOT` onto the live app config; `tests/ux/`
  (`conftest.py` / `seeding.py` / `stubs.py` / `flows/test_annotation_tab.py` / the
  education-diagnostics regression) read paths from `app.config` and stub
  `_get_client` on `blueprints.diagnostics`.
- **Definition-of-done:** the v1.0.8 `app.py`→blueprints decomposition is **complete**
  — all 93 routes live on a domain blueprint, `app.py` has zero routes / no path
  globals / no per-request helpers, and no moved seam relies on a module-global
  monkeypatch.

### Fixed — docs/test hygiene (`chore/ledger-reduction`, Sprint 8.0)

The v1.0.8 epic opens with a contained reduction micro-branch (run before the blueprint
refactor) that clears two carry-forward ledger items. **No code/prompt change** —
`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched, no new dependency, no migration.

- **`CONTRIBUTING.md` plugin-section drift corrected.** "Working with the Claude Code plugin"
  described the pre-Sprint-7.1 layout (`.claude-plugin/` "holds the project's commands, agents,
  and hook scripts", plus stale "Step 5 / 8 / 9 of the OSS migration" references). It now
  documents the actual layout — commands/subagents in the repo-root `commands/` / `agents/`
  loading namespaced via the local `sartor-tools` marketplace; only hooks + manifest +
  marketplace in `.claude-plugin/` — and points to README → Claude Code Plugin for the full
  catalog instead of re-listing entries.
- **pytest-socket `UserWarning ×2` silenced.** Added one message-scoped `filterwarnings` ignore
  (`pyproject.toml` `[tool.pytest.ini_options]`) for the egress-allowlist suite's expected
  socket-block warning, so gate runs no longer report 2 benign warnings. Scoped to the exact
  message; the socket block itself is unchanged.

### Added — blueprint-decomposition design (`design/app-blueprints`, Sprint 8.1)

The design session that resolves the v1.0.8 `app.py`→blueprints architecture **with the
owner**, before any route moves. Read-only investigation of the monolith; **no code/route/
prompt change** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched, no dependency, no
migration.

- **New design doc [`docs/dev/app-blueprints-design.md`](docs/dev/app-blueprints-design.md)** —
  records the locked decisions, the full 93-route→8-seam map, the SSE handling, the
  test-harness migration, the hook/gate sequencing (PX-19/20/21/22/29, PV-4), and an explicit
  **zero-tech-debt definition-of-done** for the epic (owner bar: minimum tech debt at v1.1.0).
- **Owner decisions locked (2026-06-21):** *Crafted* architecture — a `create_app(config)`
  application-factory (retained module-level `app = create_app()` WSGI handle) + a typed
  injected `Config` + a shared web-infra package both `app.py` and every blueprint import; and
  **8 domain seams** (analysis · generation · corpus · templates/personas · applications ·
  users/config · diagnostics · assistant), splitting the user-facing tracker from the dev
  diagnostics backend.
- `RELEASE_ARC.md` §Phase 4.8 + `RELEASE_CHECKLIST.md` items 8.1/8.2/8.3 updated to record the
  resolution and the refined branch sequence (an 8.3a `refactor/app-factory-and-infra`
  foundation branch precedes the seam moves).

### Security — route-security-lint widen + config-helper containment (`refactor/route-security-lint-widen`, Sprint 8.2)

The hardening branch that **leads** the v1.0.8 blueprint refactor (PX-21): the route-security
lint hook is widened to cover blueprint route modules *before* any route leaves `app.py`, and
the two config helpers' path-traversal gap is closed at the helper. **No behavior change for
valid users; no prompt/dependency/migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`
untouched.

- **`route-security-lint` hook widened past `app.py`.** The file matcher now also covers
  `blueprints/**.py` (any depth — a future `blueprints/corpus/*.py` sub-package is included);
  the route detector catches blueprint decorators (`@<bp>.route/.get/.post/.put/.delete/.patch`,
  the leading `@` keeping ordinary `data.get(` from false-matching); and `send_from_directory(`
  joins the filesystem-access markers. The read-only localhost `dashboard/` surface is
  **deliberately excluded** (its routes take no `<username>` and read fixed diagnostic dirs).
  Hand-verified across a 10-case exit-code matrix. The hook stays a self-contained bash script
  (migration-friendly for the 8.7 portable-enforcement-core lift).
- **`_load_config` / `_save_config` containment closed at the helper.** Both now sanitize the
  username via `secure_filename` *inside* the helper, so containment to `CONFIGS_DIR` holds even
  for a raw caller — not only at the call site (PX-21). `get_config` / `update_config` (the two
  raw-input routes) gain a `secure_filename`-non-empty → `400` guard (the `create_user` pattern),
  so a nonsense username is rejected cleanly instead of 500-ing. `secure_filename` is idempotent
  on already-safe names → existing users resolve to the same file.
- **`SECURITY.md` scoped** to the post-split layout — the hook-coverage claims now read `app.py`
  + `blueprints/` (with the `dashboard/` exclusion noted), plus a note that config filenames are
  canonicalized through `secure_filename` (`josé` → `jose`). The `app.debug` 5xx-gate passage is
  left HEAD-accurate (its `current_app.debug` re-cite lands in 8.3a, when `_error_detail_payload`
  moves to the web-infra package).
- **Tests.** `tests/test_app_security.py` gains `TestConfigHelperContainment` +
  `TestConfigRouteContainment`; the helper-level cases are the real proof — an encoded-slash
  route request is werkzeug-404'd before the handler, so that case asserts *routing* rejection,
  not helper containment.

### Changed — application factory + shared web-infra package (`refactor/app-factory-and-infra`, Sprint 8.3a)

The **foundation** branch of the `app.py`→blueprints decomposition (no route moves; the 8
domain seams are 8.3b–h). `app.py` becomes a `create_app(config)` factory over a typed
injected `Config`, and the cross-cutting helpers move to a shared leaf `web_infra/` package
both `app.py` and the blueprints import. **Pure refactor — every route's URL/method/request/
response is byte-identical; no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **Application factory.** New `create_app(config: Config | None = None)` is the composition
  root: it pushes the config, runs the directory-creation (the old import-time `mkdir` loop),
  and registers the blueprints. The module-level `app = create_app()` WSGI / console-script
  handle is retained. `main()` + `_should_open_browser` stay in `app.py`.
- **Typed `Config` (new top-level `config.py`).** Replaces the eight module-global path
  constants + `ALLOWED_EXTENSIONS` + the bind host; `Config(base_dir=...)` re-points every
  derived directory off one root. `ensure_dirs()` is byte-identical to the retired loop
  (configs/resumes/output only — annotation_root/personas stay lazily created).
- **Shared `web_infra/` package (new).** Six fixed groups — `security` (`_safe_username` /
  `_within`), `http` (`_sse` / `_error_detail_payload`), `clients` (`_get_client`), `config_io`
  (`_load_config` / `_save_config`), `provisioning` (`_get_or_provision_candidate`),
  `request_gates` (`_is_localhost_request`). It is leaf infrastructure — it never imports
  `app.py`, a blueprint, or `config.py` (enforced by `tests/test_web_infra_is_leaf.py`).
  `_error_detail_payload` now reads `current_app.debug` (same flag, behavior-identical).
- **Dedup.** `blueprints/assistant.py` deletes its duplicated `_safe_username` / `_get_client`
  / `_sse` and imports them from `web_infra/`; `dashboard/routes.py` consumes the shared
  `_is_localhost_request` rather than a third loopback copy.
- **`onboarding/corpus_import.py` second front folded in.** `_safe_load_config` /
  `import_candidate_from_config` take an explicit, defaulted `configs_dir` (additive — the CLI
  + legacy tests are unaffected); the app reaches them via `web_infra._get_or_provision_candidate`,
  which threads `current_app.config["CONFIGS_DIR"]`.
- **PX-19 — loopback bind.** `app.run(...)` now binds `host="127.0.0.1"` from `Config.host`;
  `SERVER_NAME` noted as a third silent-flip vector.
- **PX-20 — construction boundary gate.** New `tests/test_construction_boundary.py` fails if any
  deterministic module (`hardening` / `parser` / `generator` / `scraper` / `json_resume` /
  `corpus_to_json_resume` / `pdf_render`) imports `analyzer` or `anthropic` (charter C-6, by
  construction not review).
- **Tests.** New `tests/test_config.py`, `tests/test_web_infra.py`, `tests/test_web_infra_is_leaf.py`;
  `tests/conftest.py` gains the canonical `app` / `client` factory fixtures; `tests/test_assistant_route.py`
  migrates onto them; `web_infra/clients.py` added to the egress allowlist. The remaining
  module-global monkeypatch test pattern is **intentionally retained** — those seam tests migrate
  with their routes in 8.3b–h (the zero-tech-debt DoD is measured at the v1.1.0 tag).

### Changed — analysis blueprint seam (`refactor/app-blueprints-analysis`, Sprint 8.3b)

The **first domain seam** moved out of the `app.py` monolith. The five analysis routes leave
`app.py` for a new `blueprints/analysis.py`. **Pure refactor — every route's URL/method/request/
response is byte-identical; no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/analysis.py`.** `POST /api/analyze`, `POST /api/analyze/stream` (SSE),
  `POST /api/clarify`, `POST /api/answer-clarifications`, `POST /api/iterate-clarify` — plus
  their three analysis-only domain helpers (`_run_analysis_corpus_backed`,
  `_run_analysis_corpus_backed_streaming`, `_persist_clarifications_to_memory`). Registered with
  **no `url_prefix`** (full-path decorators) so the URLs stay identical; the blueprint never
  imports `app.py`.
- **Reads config via `current_app`.** Route/helper bodies take their paths from
  `current_app.config["OUTPUT_DIR"]` / `["CONFIGS_DIR"]` and use the shared `web_infra` helpers
  (`_safe_username` / `_within` / `_get_client` / `_sse` / `_get_or_provision_candidate`,
  threading `configs_dir=current_app.config["CONFIGS_DIR"]`). The SSE helper captures the output
  dir as a local **before** the generator, so `stream()` never touches `current_app` (no
  `stream_with_context` needed — matches `blueprints/assistant.py`).
- **PV-4 typing.** Every moved route and the two corpus-backed helpers are annotated
  `-> ResponseReturnValue` (which also fixed one latent `clarification_questions` TypedDict
  imprecision the untyped monolith body had skipped). `blueprints/analysis.py` added to the
  egress allowlist (it catches `anthropic` error types).
- **Tests migrate onto the factory fixture.** `tests/test_app_clarify.py` and
  `tests/test_app_corpus_backed.py` drop the module-global monkeypatch + `importlib.reload` for
  `create_app(Config(base_dir=tmp_path))`, stubbing the analyzer functions on the blueprint
  module; the iterate-clarify tests relocate to a new `tests/test_app_iterate_clarify.py` on the
  same fixture (seeding the iteration≥1 context directly, so they no longer depend on the
  still-in-`app.py` `/api/generate`). The UX harness injects the moved routes' config onto the
  live app and retargets `install_llm_stubs` to `blueprints.analysis`. `app.py` keeps its
  module-global constants + config-dependent helper copies for the un-moved seams (they retire in
  8.3c–h).

### Changed — generation blueprint seam (`refactor/app-blueprints-generation`, Sprint 8.3c)

The **second domain seam** moved out of the `app.py` monolith. The seven generation routes leave
`app.py` for a new `blueprints/generation.py`. **Pure refactor — every route's URL/method/request/
response is byte-identical; no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/generation.py`.** `POST /api/save-edits`, `POST /api/generate`,
  `POST /api/generate/stream` (SSE), `POST /api/validate-refinement`,
  `POST /api/generate-cover-letter`, `GET /api/download/<path:filepath>`,
  `POST /api/download-edited` — plus their generation-only domain helpers
  (`_check_date_grounding`, `_persist_run_persona`, `_persist_cover_letter_to_db`,
  `_persist_corpus_generation_to_db`, and the composition-application trio
  `_apply_chosen_summary` / `_apply_chosen_experience_summaries` / `_apply_recommended_skills`).
  Registered with **no `url_prefix`** (full-path decorators) so the URLs stay identical; the
  blueprint never imports `app.py`.
- **Cross-seam helper bridge (owner decision).** Three generation routes resolve a persona
  template via `_resolve_persona_template_path` / `_resolve_default_persona_template_path`, which
  belong to the **templates/personas** seam (8.3e) and are still called by the persona-preview
  routes in `app.py`. Since a blueprint cannot import `app.py`, this pair is carried in
  `blueprints/generation.py` as a clearly-commented **transitional duplicate** (canonical copies
  stay in `app.py`); it is deduplicated when the templates seam lands at 8.3e (generation will then
  import it). Tracked in the Carry-forward ledger. The `_apply_*` trio — generation's sole callers
  today, grouped with the applications seam by the 8.1 design — moves here outright (no dead code);
  revisited at 8.3f if an applications route grows a caller.
- **Reads config via `current_app`.** Route/helper bodies take paths from
  `current_app.config["OUTPUT_DIR"]` / `["CONFIGS_DIR"]` / `["RESUMES_DIR"]` / `["BASE_DIR"]` /
  `["PERSONAS_DIR"]` and use the shared `web_infra` helpers (`_safe_username` / `_within` /
  `_get_client` / `_sse`, threading `configs_dir=current_app.config["CONFIGS_DIR"]`). The streaming
  route captures `output_dir` as a local **before** the generator, so `stream()` never touches
  `current_app`. `download_file`'s inline containment guard is preserved byte-identically.
- **PV-4 typing.** Every moved route is annotated `-> ResponseReturnValue`. The loose
  `_apply_*(context_set: dict)` helpers (which read/write keys outside the `ContextSet` schema) are
  bridged at the call site with a runtime-noop `cast(dict, context_set)` so mypy's TypedDict→dict
  variance check passes without copying (the in-place mutations still land on the same object).
  `blueprints/generation.py` added to the egress allowlist (it catches `anthropic` error types).
- **Tests migrate onto the factory fixture.** `tests/test_app_iteration.py` and
  `tests/test_cover_letter_detached.py` drop the module-global monkeypatch + `importlib.reload` for
  `create_app(Config(base_dir=tmp_path))`, stubbing the generate functions on the blueprint module
  (keeping the distinct `db.session.DEFAULT_DB_PATH` monkeypatch + the lazy-imported
  `analyzer.generate_cover_letter_against_resume` stub). The three `_apply_*` unit tests
  (`test_apply_chosen_summary` / `test_experience_summary_composition` / `test_skill_composition`)
  retarget the moved helper to `blueprints.generation`. `test_persona_routes.py`'s `/api/download-edited`
  case gets live-app config injection (the persona seam's own fixture migrates at 8.3e). The UX
  harness retargets `install_llm_stubs` `generate_streaming` + `_get_client` to
  `blueprints.generation`. `app.py` keeps its module-global constants + config-dependent helper
  copies for the un-moved seams (they retire in 8.3d–h).

### Changed — corpus blueprint seam (`refactor/app-blueprints-corpus`, Sprint 8.3d)

The **third and largest domain seam** moved out of the `app.py` monolith: all **42 corpus
routes** leave `app.py` for a new `blueprints/corpus/` **sub-package**. **Pure refactor — every
route's URL/method/request/response is byte-identical (verified by an `app.url_map` path+methods
diff vs a pre-move baseline); no prompt/dependency/migration**, `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/corpus/` sub-package (owner decision: 6 route files + shared layer).** One
  `corpus_bp = Blueprint("corpus", __name__)` (in `_bp.py`) with the route families split by
  entity: `experiences.py` (15 — experiences/bullets/titles/experience-summaries),
  `summaries.py` (4), `skills.py` (4), `tags.py` (7 + tag-mutation helpers), `curation.py`
  (9 — upload/resumes/duplicates/ingest/accept/pending + `_find_root`), `proposals.py`
  (3 — critique/decide/promote). Cross-cutting serializers live in `_shared.py`. Registered with
  **no `url_prefix`** (full-path decorators) so the URLs stay identical; the package never imports
  `app.py`.
- **Shared serializers `_tag_list` / `_skill_to_dict` (owner decision).** Both are corpus-domain
  serializers (design §3.4) but are also called by two still-resident *applications* routes
  (`get_application_composition`, `suggest_application_skills`, 8.3f). Since `app.py → blueprint`
  is the legal import direction, corpus owns the **canonical** copy in `_shared.py` and `app.py`
  imports them — **no transitional duplicate, no new carry-forward ledger item** (the inverse of
  8.3c's `_resolve_*` case, where the owning seam was in the future). The import relocates to
  `blueprints/applications` at 8.3f.
- **Reads config via `current_app`.** Every route/helper takes paths from
  `current_app.config["CONFIGS_DIR"]` / `["RESUMES_DIR"]` / `["OUTPUT_DIR"]` / `["ALLOWED_EXTENSIONS"]`
  and uses the shared `web_infra` helpers (`_safe_username` / `_within` / `_get_client` /
  `_get_or_provision_candidate` / `_load_config` / `_save_config`), threading
  `configs_dir=current_app.config["CONFIGS_DIR"]`. The `onboarding.corpus_import` "second
  monkeypatch front" retires for the migrated corpus tests: provisioning threads `configs_dir`
  through `web_infra._get_or_provision_candidate`, so the `corpus_import.CONFIGS_DIR` monkeypatch
  is gone.
- **PV-4 typing.** All 42 moved routes are annotated `-> ResponseReturnValue`; the
  `_get_or_provision_candidate` result is bridged with `cast("Candidate", …)` where `.id` is
  accessed, preserving byte-identical runtime behavior. `blueprints/corpus/proposals.py` is the one
  corpus submodule added to the egress allowlist (critique + promote catch `anthropic` error types);
  ingest delegates its Haiku call to `onboarding.corpus_import`, so `curation.py` imports no
  `anthropic`. `app.py` drops the now-unused top-level `from analyzer import LLMResponseError` (the
  remaining applications `recommend_*` routes import it locally); it keeps `import anthropic` and its
  allowlist entry (those routes still use it).
- **route-security-lint refinement (owner-authorized).** The hook's filesystem-indicator heuristic
  dropped `CONFIGS_DIR` from its match set: post-8.3a a route body only ever reaches `CONFIGS_DIR`
  via `_safe_username(configs_dir=…)` — which IS the containment guard — and the raw
  `CONFIGS_DIR / f"{u}.config"` construction `_within` protected was removed in PX-21. The
  FS-free corpus submodules (which reference `CONFIGS_DIR` only as that argument) were otherwise
  false-flagged for a missing `_within`. `OUTPUT_DIR`/`RESUMES_DIR`/`open(`/`Path(`/`send_file(`
  remain indicators, so upload/ingest/download still require `_within` (all three hook arms
  hand-verified).
- **Tests migrate onto the factory fixture.** The eight corpus test files drop the module-global
  monkeypatch + `importlib.reload` for `create_app(Config(base_dir=tmp_path))` (keeping the distinct
  `db.session.DEFAULT_DB_PATH` monkeypatch); the ingest/proposal `_get_client` patches retarget to
  `blueprints.corpus.curation` / `.proposals`; the analyzer-function patches are unchanged (the
  routes import them lazily from `analyzer`). `app.py` keeps its module-global constants +
  config-dependent helper copies for the remaining un-moved seams (templates/personas,
  applications, users/config, diagnostics — they retire in 8.3e–h).

### Changed — templates/personas blueprint seam + PX-22 wizard back-nav (`refactor/app-blueprints-templates`, Sprint 8.3e)

The **fourth domain seam** moved out of the `app.py` monolith: all **11 persona-template +
live-preview routes** leave `app.py` for a new `blueprints/templates.py`, the
`_resolve_persona_*` transitional duplicate 8.3c left in `blueprints/generation.py` is cleared,
and (owner-approved) the wizard gains browser Back/Forward navigation (PX-22). The route move is
a **pure refactor — every URL/method/request/response is byte-identical** (verified by an
`app.url_map` path+methods diff vs a pre-move baseline, 96 rules unchanged); **no
prompt/dependency/migration**, `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched. PX-22 is a
front-end behavior change only.

- **New `blueprints/templates.py` (single module, 11 routes).** `templates_bp =
  Blueprint("templates", __name__)`, registered with **no `url_prefix`** (full-path decorators):
  `list_bundled_personas` · `list_user_personas` · `upload_user_persona` · `get_persona` ·
  `update_persona` · `delete_persona` · `download_persona` · `preview_persona_with_resume` ·
  `preview_application_html` · `preview_cover_letter_html` · `preview_candidate_html`. The
  persona-only helpers move with the seam (`_persona_dict`/`_persona_dicts_safe`,
  `_preview_placeholder_html`, `_json_resume_has_content`, `_cover_letter_placeholder_html`,
  `_latest_generated_resume_md`, `_inline_persona_css`, `_inject_paged_polyfill` +
  `_PAGED_PREVIEW_INJECTION`). Reads paths from `current_app.config["PERSONAS_DIR"]` /
  `["BUNDLED_PERSONAS_DIR"]` / `["BASE_DIR"]` / `["OUTPUT_DIR"]` and the shared `web_infra` helpers
  (`_safe_username(configs_dir=…)` / `_within` / `_error_detail_payload` /
  `_get_or_provision_candidate`); the package never imports `app.py`. **LLM-free** — no
  `anthropic` reference, so the module is deliberately **not** on the egress allowlist. PV-4:
  every route annotated `-> ResponseReturnValue`; the provision result is bridged with
  `cast("Candidate", …)` where `.id` is read (byte-identical runtime behavior). The now-unused
  `PERSONAS_DIR` / `BUNDLED_PERSONAS_DIR` module globals + the `send_file` / `generate_resume`
  imports are dropped from `app.py` (`config.py` is the canonical home).
- **`_resolve_persona_*` duplicate cleared (carry-forward ledger item Resolved).**
  `_resolve_persona_template_path` / `_resolve_default_persona_template_path` now live **canonically**
  in `blueprints/templates.py`; the app.py copies and the 8.3c transitional copy in
  `blueprints/generation.py` are deleted, and `generation.py` imports the pair from
  `blueprints.templates` (sibling blueprint→blueprint import; templates never imports generation, so
  no cycle).
- **`_load_application_owned` transitional duplicate (new carry-forward ledger item).** The two
  application-preview routes need it, but it is owned by the *applications* seam (8.3f, still in
  `app.py` with ~10 callers). Mirroring the 8.3c decision, a clearly-commented transitional copy
  rides `blueprints/templates.py` (its one port: `_safe_username(configs_dir=current_app.config[…])`);
  it dedupes when the applications seam lands. Net ledger: item 2 Resolved, this added → unchanged.
- **PX-22 — browser Back/Forward traverse wizard steps (`static/app.js`).** `wizardGoTo` pushes a
  `{wizardStep}` `history` entry on each step change (`wizardInit` + the resume-from-prior landings
  stamp a `replaceState` baseline); a `popstate` listener restores the step (re-running its
  side-effects, never re-pushing). Two correctness fixes were required for Back to actually step the
  wizard rather than feel dead: (a) `_wizardPushHistory` **skips a duplicate** entry for the
  step already current (the Skip-to-Compose path navigates to step 3 twice); (b) the live-preview
  iframes load history-neutrally via `contentWindow.location.replace()` (a new `_loadPreviewFrame`
  helper) instead of `frame.src =`, so preview reloads on steps 4/6 don't pollute the joint session
  history. Scope is session-only (no address-bar `?step=N`, no deep-link-on-load).
- **Tests migrate onto the factory fixture.** `test_persona_routes.py`,
  `test_default_template_resolver.py`, and `test_live_preview_route.py` drop the module-global
  monkeypatch + `importlib.reload` (and the 8.3c `/api/download-edited` config-injection stopgap) for
  `create_app(Config(base_dir=tmp_path))` (keeping the `db.session.DEFAULT_DB_PATH` monkeypatch); the
  moved resolvers are invoked inside an app context. A new `pytest -m ux` regression
  (`test_20260622_wizard_back_nav.py`) drives the wizard forward, then asserts browser Back steps it
  backward and Forward restores it. The UX harness leaves `BASE_DIR`/`PERSONAS_DIR` at the real repo
  root (so bundled personas resolve) while injecting the tmp `CONFIGS_DIR`/`OUTPUT_DIR`.

### Changed — applications blueprint seam (`refactor/app-blueprints-applications`, Sprint 8.3f)

The **fifth domain seam** moved out of the `app.py` monolith: all **13 application-tracker +
per-application Compose routes** leave `app.py` for a new `blueprints/applications.py`. The route
move is a **pure refactor — every URL/method/request/response is byte-identical** (verified by an
`app.url_map` path+methods diff vs a pre-move baseline: 96 rules unchanged, only the 13 endpoint
*names* gained the `applications.` blueprint prefix). Two **owner-signed** clean-ups ride along
(below). **No prompt/dependency/migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/applications.py` (single module, 13 routes).** `applications_bp =
  Blueprint("applications", __name__)`, registered with **no `url_prefix`** (full-path decorators):
  `list_applications` · `get_application` · `update_application_status` · `update_application_notes` ·
  `update_application_meta` · `get_application_composition` · `save_application_composition` ·
  `recommend_application_bullets` · `recommend_application_summary` ·
  `recommend_application_experience_summaries` · `recommend_application_skills` ·
  `suggest_application_skills` · `list_clarifications` (the candidate-memory list — the design's
  ‡ "finalize at move time" route, owner-placed here). The applications-only helpers move with the
  seam (`_VALID_APP_STATUSES`, `_application_summary_dict`, `_build_resume_state`, `_parse_ats_status`,
  `_find_context_path_for_run`, `_latest_analysis_essentials`, and the seven `_read_*` context-override
  readers). Reads paths from `current_app.config["OUTPUT_DIR"]` / `["CONFIGS_DIR"]` and the shared
  `web_infra` helpers (`_safe_username(configs_dir=…)` / `_within` / `_error_detail_payload` /
  `_get_client`); the corpus serializers `_tag_list` / `_skill_to_dict` are imported from
  `blueprints.corpus` (the legal corpus→applications direction); the module never imports `app.py`.
  PV-4: every route annotated `-> ResponseReturnValue`.
- **Egress allowlist: `app.py` out, `blueprints/applications.py` in.** The five recommend/suggest
  routes carry the last `anthropic` error-type references in `app.py`; with them moved, `app.py` no
  longer imports `anthropic`, so its `import anthropic` is dropped and `app.py` is **removed** from
  `tests/test_egress_allowlist.py` (the gate asserts both directions — a listed non-importer is
  "allowlist rot"). `blueprints/applications.py` is added in its place.
- **`_load_application_owned` transitional duplicate cleared (carry-forward ledger item Resolved).**
  The helper is now **canonical** in `blueprints/applications.py`; the `app.py` copy and the 8.3e
  transitional copy in `blueprints/templates.py` are deleted, and `templates.py` imports it from
  `blueprints.applications` (sibling blueprint→blueprint import; applications never imports templates,
  so no cycle).
- **`list_resumes` raw-username hardening (owner-signed behavior tightening; carry-forward ledger item
  Resolved).** `GET /api/users/<username>/resumes` (in `blueprints/corpus/curation.py`) built its
  directory path from the **raw** route `username` without the `_safe_username` guard its sibling
  corpus routes use. It now calls `_safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])`
  and returns `400` for an unknown/unsafe user (matching `list_corpus_duplicates`). The only behavior
  change in the branch: a real selected user is unaffected; an unknown username is now rejected rather
  than reading an empty directory.
- **Tests migrate onto the factory fixture.** The application / composition / clarifications / recommend /
  suggest test files drop the module-global monkeypatch + `importlib.reload` for
  `create_app(Config(base_dir=tmp_path))` (keeping the `db.session.DEFAULT_DB_PATH` monkeypatch); the
  recommend/suggest `_get_client` stubs retarget to `blueprints.applications` (the analyzer
  `recommend_*`/`suggest_*` stubs stay on `analyzer`). The UX harness adds the
  `blueprints.applications._get_client` stub for the Compose recommend/suggest steps.

### Changed — users/config blueprint seam (`refactor/app-blueprints-users-config`, Sprint 8.3g)

The **sixth domain seam** moved out of the `app.py` monolith: all **6 users/config routes** leave
`app.py` for a new `blueprints/users.py`. The move is a **pure refactor — every URL/method/request/
response is byte-identical** (verified by an `app.url_map` path+methods diff vs a pre-move baseline:
96 rules unchanged, only the 6 endpoint *names* gained the `users.` blueprint prefix). **No prompt/
dependency/migration** — `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched.

- **New `blueprints/users.py` (single module, 6 routes).** `users_bp = Blueprint("users", __name__)`,
  registered with **no `url_prefix`** (full-path decorators): `index` (the SPA shell) · `list_users` ·
  `create_user` · `get_config` · `update_config` · `fetch_profile` (the PX-02 opt-in profile scrape).
  Reads paths from `current_app.config["CONFIGS_DIR"]` / `["RESUMES_DIR"]` and the shared `web_infra`
  config-io / security / provisioning helpers (`_load_config(configs_dir=…)` / `_save_config(configs_dir=…)`
  / `_safe_username(configs_dir=…)` / `_within` / `_get_or_provision_candidate(configs_dir=…)`); the
  `db.session` + `scraper` imports stay lazy inside `fetch_profile`; the module never imports `app.py`.
  PV-4: every route annotated `-> ResponseReturnValue`. **LLM-free** — `fetch_profile`'s only egress is
  inside `scraper.py` (already allowlisted), so `blueprints/users.py` is **not** on the egress allowlist.
- **app.py.** `users_bp` registered in `register_blueprints()`; the 6 route bodies removed; the
  now-unused `make_response` / `render_template` / `validate_config` imports pruned. The app.py-local
  helper copies (`_safe_username` / `_load_config` / `_save_config` / `_get_or_provision_candidate`) and
  the `CONFIGS_DIR` / `RESUMES_DIR` globals are **kept** — the still-resident diagnostics routes use
  `_safe_username` + the globals; the whole local-helper block retires together at 8.3h when `app.py`
  has zero routes.
- **Second monkeypatch front retired for this seam.** `fetch_profile`'s provisioning chain
  (`_get_or_provision_candidate` → `import_candidate_from_config` → `_safe_load_config`) is fully
  `configs_dir`-parameterized in `web_infra/`, so the blueprint passes
  `current_app.config["CONFIGS_DIR"]` end-to-end and `tests/test_profile_fetch_route.py` **drops** its
  `onboarding.corpus_import.CONFIGS_DIR` monkeypatch (design §7 zero-debt).
- **Tests.** `test_profile_fetch_route.py` and the `TestConfigRouteContainment` class of
  `test_app_security.py` migrate from module-global monkeypatch + `importlib.reload` to
  `create_app(Config(base_dir=tmp_path))` (keeping the `db.session.DEFAULT_DB_PATH` monkeypatch; the
  `scraper.fetch_url_content` stub is unchanged). The helper-level classes (`TestSafeUsername` /
  `TestWithin` / `TestConfigHelperContainment`) stay on the `app_module` fixture — they test the
  app.py-local helpers that remain. New `tests/test_users_routes.py` adds the previously-absent
  `list_users` / `create_user` unit coverage (pinning the `RESUMES_DIR` config-key swap). The UX harness
  injects `RESUMES_DIR` onto the live app config so a new-user flow can't write into the real `resumes/`.

## [1.0.7] — 2026-06-20

### Changed — avatar citation/reference-format consistency (`feat/avatar-citation-format`, Sprint 7.8d)

Owner testing (2026-06-19) found the doc-grounded assistant's citations rendering
inconsistently — markdown links `[text](path)`, parentheticals, and numeric `[N]` markers
colliding in the same sentences, over a "Sources:" footer the `[N]` never resolved to. This
makes every reference **numbered, resolvable, and clickable**, and the footer **honest** (it
lists only what the answer actually cited). Tunes the **avatar only** — `AVATAR_PROMPT_VERSION`
bumps `2026-06-18.1` → `2026-06-19.1`; **`PROMPT_VERSION` is unchanged**. No new route, no new
dependency, no migration.

- **Numbered footnote citations (Scheme B).** `AVATAR_SYSTEM_PROMPT` (`analyzer.py`) now
  instructs the avatar to cite a claim with the **bracketed number** of the unit it rests on
  (`[1]`, `[2]`) at the end of the sentence — never a slug, a markdown link, or a URL — with
  worked OK/NOT-OK examples. The per-turn closer and the `<recalled_context>` renderer docstring
  match.
- **Cited-only, renumbered, resolving footer.** `avatar_answer_streaming`'s `done` payload now
  carries `citations` as a list of `{n, label, href}` for **only the units the answer cited**
  (a new `_resolve_cited` parses the emitted `[n]`, renumbers them consecutively in
  first-appearance order, and remaps the body) — so the footer can no longer overstate grounding
  and every marker resolves. A refusal that cites nothing shows "no sources cited." A stray
  `[[slug]]` the model occasionally mirrors into prose is normalized to plain text (never a real
  numbered cite, so it can't show as raw bracket-soup).
- **Clickable GitHub links.** Each citation links to its source on GitHub — wiki pages on `main`,
  code lines pinned to the unit's provenance `sha` (`_citation_href`). The model still never emits
  a URL (the no-URL invariant holds); the client builds the anchor from the citation.
- **Constrained inline markdown (`static/assistant.js`).** On completion the answer re-renders a
  tiny fixed subset — `` `inline code` ``, `**bold**`, and the `[n]` links — **XSS-safe by
  construction** (escape first, then introduce only fixed tags + a re-validated GitHub href). The
  numbered "Sources" key renders into a dedicated non-`aria-live` `#assistantSources` block; the
  polite status region keeps a short "Answer ready."
- **Tests (`tests/test_avatar_streaming.py`):** the deterministic LLM-free layer now covers href
  construction, cited-only + consecutive renumbering, out-of-range markers left literal, the
  empty refusal footer, and "every body `[n]` resolves / no `](` / no URL." Route + UX stubs move
  to the new `citations` shape and assert the rendered links.
- **Deferred (ledger):** an in-app rendered citation viewer — clickable links go to GitHub for
  now; an in-app viewer waits until friction warrants it (owner 2026-06-19).

### Fixed — assistant answers without a user selected (`fix/assistant-runs-without-user`, Sprint 7.8c)

The doc-grounded assistant no longer requires a user to be selected before it will
answer. Its answer is **project-global** — grounded in the committed wiki + code at
HEAD, identical for every user — so gating it behind user-selection was an artifact
of the per-user route pattern, and it blocked the assistant at exactly the first-run
moment ("how does sartor. work?") a brand-new visitor benefits from it most. Route +
client behavior only; no prompt, dependency, or migration change; `PROMPT_VERSION` and
`AVATAR_PROMPT_VERSION` unchanged.

- **Route (`blueprints/assistant.py`):** `POST /api/assistant/ask` now requires only a
  `question`. `username` is optional — `_safe_username`-validated only when supplied (a
  provided-but-unknown user is still a `400`), and absent → anonymous telemetry (`""`,
  already the `_call_llm_streaming` default). Retrieval and the answer are unchanged.
- **Client (`static/assistant.js`):** dropped the "Pick a user first, then ask." gate; the
  Ask button works with no user selected and sends an empty username.
- **Tests (`tests/test_assistant_route.py`):** the missing-username case now asserts a
  streamed anonymous `200` instead of a `400`; the missing-question and unknown-user `400`s
  are retained.
- **UX regression (`tests/ux/regression/test_20260619_assistant_no_user.py`):** drives the
  top-bar magnifier modal with **no user selected** and asserts the streamed cited answer
  renders end-to-end — the path the route test can't cover (the real `static/assistant.js`
  sending an empty username).

### Changed — avatar voice/tone & behavior tuning (`feat/avatar-voice-tone-tuning`)

Executes the voice/tone/behavior guidance package ([`docs/dev/avatar-voice-tone-guidance.md`](docs/dev/avatar-voice-tone-guidance.md))
against the live doc-grounded assistant. Tunes the **avatar only** — `AVATAR_PROMPT_VERSION`
bumps `2026-06-16.1` → `2026-06-18.1`; **`PROMPT_VERSION` is unchanged** (the avatar carries
its own version and is deliberately not in the résumé `_BASE_SYSTEM_PROMPTS` eval registry).
No new dependency, no migration.

- **Persona (`AVATAR_SYSTEM_PROMPT`, `analyzer.py`)** is now a *friendly, encouraging guide*
  — warmth delivered through helpfulness and a real next step, never cheer, flattery, or
  instructed wit. The prime directive is unchanged and made explicit: when voice and grounding
  conflict, grounding wins.
- **The refusal is now a doorway, not a dead end.** The exact string `"I don't have that in my
  docs."` is byte-unchanged, but the redirect to the nearest *cited* covered topic is now
  near-mandatory, and an in-domain-but-undocumented question is invited to be reported on the
  project's GitHub (the model states the behavior; the real link lives only in the UI).
- **New behavioral guardrails:** a calibrated-middle (answer the covered part, mark the gap),
  explicit anti-sycophancy / anti-over-promise (ATS-safety is described as *parseability*,
  never "reaches a human" or "improves your chances"), no performed honesty/empathy, and a
  connect-the-capability-to-the-concern move on reassurance-fishing instead of predicting outcomes.
- **Readable citations:** answers now read as natural sentences with the source in clean
  single square brackets at the end of the sentence (`[using-sartor]`, `[analyzer.py:49]`),
  rather than `[[…]]` mid-sentence — easier for non-technical readers. The "Sources:" footer
  strips the double brackets to match.
- **Microcopy (`templates/index.html`, `static/assistant.js`):** plain-languaged intro ("I show
  my sources"); a persistent empty state (scope/boundary line + verified example prompts) replacing
  the vanishing placeholder; blame-free transport-error copy kept distinct from the grounded
  refusal; and a real "report it on the project's GitHub" link.
- **Accessibility fix:** `#assistantAnswer` is no longer an `aria-live` region — streaming
  tokens into it announced the whole answer to screen readers on every chunk. It is now
  `aria-busy`-toggled and silent; the single completion announcement rides the `#assistantStatus`
  polite region.
- **Tests:** added LLM-free deterministic tone checks (`tests/test_avatar_streaming.py`) —
  refusal byte-sync across the two locations, the locked voice clauses, banned-phrase /
  over-promise / no-URL-in-output scanners, a cite-membership checker, the brand-mark sweep, and
  the answer-node-not-a-live-region assertion. Validated live against a Haiku spot-check matrix
  (the guide's §6.3); see [`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) 2026-06-18.

### Fixed — UI-polish trio (`fix/v107-ui-polish-trio`, Sprint 7.8b)

Three small, independent fixes from the v1.0.7 UI-polish band. No prompt,
dependency, or migration change; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION`
unchanged.

- **Stray browser windows (#1):** `python app.py` re-opened a browser window on
  every Flask debug-reloader restart, because the auto-open ran inside the
  serving child (`WERKZEUG_RUN_MAIN == "true"`) that the reloader re-executes on
  each reload — so editing files popped a new window each time ("5–6 windows per
  session"). A new pure `app._should_open_browser()` opens **exactly once** — in
  the persistent supervisor / non-debug single process, never in the reload
  child — and still honors `SARTOR_NO_BROWSER=1`.
- **Slow application load (#3):** selecting a user loaded the prior-applications
  list with `1 + 2N` SQL queries (lazy `Application.runs` per row + a per-app
  pending `ProposalReview` count), so it slowed as a user accrued applications.
  `GET /api/users/<u>/applications` now eager-loads runs with `selectinload` and
  batches the pending counts into one grouped query (~3 queries regardless of
  N). Output JSON and ordering unchanged; a regression test asserts the query
  count stays constant as the application count grows.
- **New-user form stale heading (#4):** with a user selected, clicking "New
  user" left the previous username in the `#userSelect` dropdown directly above
  the new-profile fields. `showNewUserForm()` now clears the dropdown (Cancel
  restores it). Front-end label fix only.

### Changed — assistant moved to a fixed top-bar icon + floating modal (`feat/assistant-topbar-modal`, Sprint 7.x)

A **front-end-only** relocation of the doc-grounded assistant so it is always findable in
the same place. No route, LLM, prompt, dependency, or migration change; `PROMPT_VERSION`
and `AVATAR_PROMPT_VERSION` unchanged.

- **Entry point** is now a fixed **magnifier icon** in the floating top bar (`#assistantPill`,
  left of Diagnostics) instead of an always-visible collapsible `<details>` panel parked
  below the wizard. The panel (`#panelAssistant`) is **removed** — one stable, discoverable
  entry point.
- **Presentation** is a **floating, scrollable modal** (`#assistantModal`) built on the
  existing `.cb-modal` skeleton (widened to ~680px; the `.cb-modal-body` internal scroll +
  90vh cap keep a long streamed answer scrollable under a pinned title + Close). The
  question box, Dev-mode toggle, streamed answer, and cited-sources line keep their element
  ids, so the SSE client (`static/assistant.js` `askAssistant()`) is unchanged; a new
  `openAssistantModal()` adds the open/close mechanics (focus-trap, Esc, backdrop,
  focus-restore, `aria-expanded`) mirroring `openDiagnosticsModal()`.
- **a11y:** `role="dialog"`/`aria-modal`, a static dialog title, `aria-haspopup`/
  `aria-controls`/`aria-expanded` on the icon button (explicit `aria-label`, since it has no
  visible text). Covered by the relocated UX regression (pill → modal → streamed cited
  answer) and a new open-state scan in the axe a11y gate.

### Documentation — accessibility status, Chromium reclassification, KEEP/BOOST ledger (`px/v107-band`, Sprint 7.8)

A docs-only PX band (no code, prompts, routes, deps, or migrations; `PROMPT_VERSION`
unchanged) clearing four v1.0.7 review prescriptions:

- **`ACCESSIBILITY.md`** (PX-18, `F-expa11y-03`): a new root-level **honest-status page**
  per the signed charter's E-2 — what is machine-checked (the vendored axe-core
  serious/critical gate, the keyboard "a11y floor" regression, the `_announce()`
  live-region, modal focus-trap/Escape/focus-return, the `--fg-2/3` WCAG-AA contrast
  retune) versus the **known gaps** (the UX/a11y tier isn't yet run in CI → PX-25;
  serious/critical-only; the Clarify/Output/cover-letter steps + modals + tab-order/
  reflow/history are unscanned; the bounded pre-public NVDA walkthrough hasn't run).
  **No conformance claim, no tag gate, no recurring-audit promise**; the v1.1.0 WCAG 2.2
  AA self-evaluation is stated as intent, not a present claim. Linked from the README doc map.
- **Chromium reclassified as PDF-output-only** (PX-31, `F-docs-05`): `docs/install.md`
  lifts the ~150 MB `playwright install chromium` step out of the base **Prerequisites**
  and gates it "optional — only for PDF output" in all three OS sequences; corrects the
  "renders every PDF and the live preview" claim — the in-browser preview is browser-side
  paged.js, **Chromium-free**; only PDF output needs the binary (`pdf_render.py` is the
  sole Playwright renderer; cf. `SECURITY.md` bundled-assets). README quick-install and the
  `pyproject.toml` playwright comment tightened to match.
- **`docs/dev/keep-ledger.md`** (PX-32): a new **eval/governance KEEP/BOOST do-not-regress
  ledger** — the non-polluting prompt-override A/B, the manual-promote/fail-closed
  annotation contract, the surfaced-uncalibrated L1/L2 state, the cost/consent-gated paid
  routes (**BOOST**), the witness-class hooks + read-only subagents, and the wiki
  grounding/sentinel/`@import` disciplines, each with its regression risk. `F-gov-08`
  (W-4 maturity signal) and `F-gov-10` (governance→assistant interface) logged as deferred
  design items. The **affirmation** half of the set the v1.0.8 split guards (PX-29) will test.
- **`docs/PRODUCT_SHAPE.md` R2 reconciled** (§10): the "stream `analyze()` output" entry,
  still listed as a v1.1 deferral, marked **shipped in v1.0.3** — consistent with the §10
  banner and the live `/api/analyze/stream` route.

### Added — the S3 vector tier for the assistant (`feat/doc-assistant-vector`, Sprint 7.6)

**Stage 2** of the Memory substrate: a static-embedding **semantic retrieval tier** that
finds the right code/doc when the question's words don't match the source's words — the
*vocabulary bridge* the lexical `git grep` (S2) tier misses. Built ahead of the formal
v1.0.8 labeled-eval gate **at owner direction** (the Stage-1 assistant tested too literal /
lacking semantic flexibility); the dependency add + the boundary-test relaxation are a
deliberate, documented gate-override (`docs/dev/RELEASE_ARC.md` §Phase 4.7).

- **`VectorSource` on the `recall/` `Source` protocol** ([`recall/sources/vector_source.py`](recall/sources/vector_source.py)):
  brute-force cosine over a rebuildable embedding sidecar. **Project-agnostic by
  construction** — the index dir, the **embedder** (`Callable[[Sequence[str]], ndarray]`),
  the audience resolver, and the document provider are all injected; the substrate never
  imports `model2vec`, so it stays embedder-agnostic + extractable. Build (`refresh`) and
  search are split: `refresh` re-embeds only chunks whose content changed (content-hash
  reuse → incremental, $0-on-unchanged); `search` loads the process-cached sidecar, embeds
  the query, returns top-k `path:line`-cited Units. No index → `[]` (graceful degradation).
  Re-exported from `recall`.
- **Wiring** ([`blueprints/assistant.py`](blueprints/assistant.py)): the `model2vec`
  embedder is built lazily + process-cached here (confined to the project layer); the
  vector tier joins the source list + `Tier.VECTOR` joins the scope **only when the model +
  index are both present** ("on when available"; no user-facing toggle). Runtime retrieval
  is fully local — no network.
- **Build step** ([`scripts/build_vector_index.py`](scripts/build_vector_index.py)):
  downloads the static model ONCE (~30MB — the single deliberate network step, like
  `playwright install chromium`) into the gitignored sidecar `db/vector_index/`, enumerates
  tracked code + docs, chunks + embeds, writes the index. `--full` cold-rebuilds. A probe
  ([`scripts/vector_index_probe.py`](scripts/vector_index_probe.py)) measures what the tier
  recovers over the lexical tiers (the gate-override evidence; logged in `evals/TUNING_LOG.md`).
- **New dependencies (hard):** `numpy` (the source's cosine + the `.npy` sidecar) and
  `model2vec` (the static embedder: numpy + tokenizers + safetensors — **no torch /
  onnxruntime**, the lightest semantic path). The `recall/` stdlib-only boundary test
  ([`tests/test_recall_boundary.py`](tests/test_recall_boundary.py)) is deliberately
  relaxed to admit **`numpy` in `recall/sources/` only** (core `recall/` stays stdlib-only;
  `model2vec` stays forbidden anywhere in `recall/`).
- **No migration; the vector index is a derived, rebuildable sidecar** (`db/vector_index/`,
  gitignored) — never `db/resume.sqlite` (it would inherit migrations + the corpus PII).
  Résumé `PROMPT_VERSION` unchanged (no prompt change). Unit tests use a fake numpy
  embedder, so the default `pytest` stays green with no model download.

### Added — the doc-grounded assistant (`feat/doc-assistant`, Sprint 7.5)

The **Stage 1** Memory capability: a working, **cited** chat over the committed
`docs/wiki/` + the code at HEAD — *"a product that knows itself."* It turns the Stage-0
`recall/` skeleton into a real assistant by adding the two free retrieval tiers, the
Haiku **avatar** (the only LLM in the stack, reusing the user's existing Anthropic key —
**no new credential, no new dependency**), a **user/dev audience toggle** + model-detected
disclosure, and an S5-P1 session buffer. Built per
[`docs/dev/memory-architecture.md`](docs/dev/memory-architecture.md) "Stage 1"; the S3
vector tier stays out (Sprint 7.6, eval-gated).

- **Two real source tiers on the `recall/` `Source` protocol** ([`recall/sources/`](recall/sources/),
  generic + stdlib-only, roots/audience injected): `WikiSource` (S1 — `docs/wiki/pages/*.md`
  → `[[slug]]`-cited Units, audience from each page's `**Audience:**` tag, sha from
  `.last_ingest_sha`); `GitGrepSource` (S2 — `git grep` over **tracked** files → `path:line`
  Units, audience from the SCHEMA path rules; ignored user data is structurally excluded);
  `SessionSource` (S5-P1 — the in-memory session buffer). Re-exported from `recall`.
- **The avatar** ([`analyzer.py`](analyzer.py) — honoring charter C-6 "all LLM calls live in
  `analyzer.py`"): `avatar_answer_streaming()` + `AVATAR_SYSTEM_PROMPT`, a grounded Haiku
  call over an assembled `recall.Context` that cites what it claims and refuses what the
  context doesn't support. Carries its **own** `AVATAR_PROMPT_VERSION` (= `2026-06-16.1`)
  so persona tweaks never bump the résumé-pipeline `PROMPT_VERSION`; intentionally **not**
  in the résumé-scoped `_BASE_SYSTEM_PROMPTS` eval registry.
- **The SSE chat route**, authored as the first module in a new `blueprints/` package
  ([`blueprints/assistant.py`](blueprints/assistant.py), `assistant_bp`,
  `POST /api/assistant/ask`) — blueprint-shaped so the v1.0.8 `app.py`→blueprints split is
  a *move*, not a rewrite. It is the project-wiring layer (the callback roots + the SCHEMA
  audience rules injected into the generic tiers); it does **not** import `app.py` (the
  `dashboard/` precedent). The `_safe_username` security gate applies; `_within` is N/A
  (no user-supplied path is resolved).
- **A minimal in-app assistant panel** ([`templates/index.html`](templates/index.html) +
  [`static/assistant.js`](static/assistant.js)) — an always-available collapsible
  `<details>` with a dev-mode toggle, reusing the existing `_consumeSSE` SSE helper.
- **Guards:** the `recall/sources/` tiers stay project-agnostic — a new
  `test_recall_sources_no_hardcoded_roots` guard in
  [`tests/test_recall_boundary.py`](tests/test_recall_boundary.py) rejects sartor-specific
  path literals (the import-boundary test can't see string literals). `blueprints/assistant.py`
  is added to the PX-08 egress allowlist (it constructs the Anthropic client). `subprocess`
  in `GitGrepSource` carries justified `# noqa: S603, S607` (fixed argv, no shell, local git).
- **Tests:** unit suites for all three tiers + the avatar (LLM-free), a Flask `test_client`
  route suite, and a Playwright UX panel test (avatar stubbed). **`PROMPT_VERSION` unchanged
  at `2026-06-13.1`; zero new dependencies.**

### Added — the Memory substrate skeleton (`feat/recall-skeleton`, Sprint 7.4)

The first piece of sartor's **Memory** function as a first-class subsystem: a new
deterministic `recall/` Python package — the **Stage 0 skeleton** of the reusable
retrieval/assembly substrate the doc-grounded avatar (7.5) and the self-documenting wiki
loop build on. It defines the *seams* only — the public types + the two cross-cutting
planes + a working `assemble()` orchestration — and ships **no real source tier and no
LLM** (the S1 wiki + S2 `git grep` tiers are 7.5; the S3 vector tier is 7.6). **No route,
no LLM call, no new dependency (stdlib-only), no migration; `PROMPT_VERSION` unchanged at
`2026-06-13.1`; no user-facing behavior change** (nothing is wired into the pipeline yet).

- **New `recall/` package** ([`recall/README.md`](recall/README.md) is the contract):
  `Unit` / `Tier` / `Audience` / `Scope` / `Context` value types ([`recall/models.py`](recall/models.py)),
  the `Source` protocol ([`recall/source.py`](recall/source.py)), the access/disclosure
  plane ([`recall/planes.py`](recall/planes.py)), and `assemble(query, scope, sources)
  -> Context` — search → RRF fusion → access-filter → token-budget pack
  ([`recall/assemble.py`](recall/assemble.py)). The whole public API is those four types +
  one entry point.
- **Two cross-cutting planes.** *Provenance/grounding* — every `Unit` carries its stamp
  (`tier · source_id · citation · audience · sha`), enforced at construction; `assemble()`
  only filters/reorders/truncates, never rewrites text, so the stamp survives into the feed.
  *Access/disclosure* — `Scope` resolves the user/dev toggle into an allowed-audience set and
  drops units that exceed it. Design: [`docs/dev/memory-architecture.md`](docs/dev/memory-architecture.md).
- **Shipped reference `Source`** ([`recall/memory_source.py`](recall/memory_source.py)):
  `InMemorySource`, a minimal deterministic source — the worked example a 7.5 tier author
  copies, and the shape the future S5-P1 session buffer takes.
- **The refactor-immune boundary, enforced by test.** `recall/` must never import `app.py`,
  `analyzer.py`, the DB models, Flask, or an LLM client — the rule that makes the v1.0.8
  blueprint split a *move*, not a rewrite. [`tests/test_recall_boundary.py`](tests/test_recall_boundary.py)
  is the AST boundary-lint (mirrors the PX-08 egress gate); no new hook
  (enforcement-portability is the Sprint 8.7 work).

### Added — the compliance-agent pilot (`feat/compliance-agent-pilot`, Sprint 7.7)

Governance gains a witness for the Regulation function — a read-only periodic read of
whole-repo coherence that emits a **ranked, capped drift report**: places where what the
charter / release arc / changelog / code / wiki provenance *say* has drifted from what the
repo *is* at a pinned sha. It cautions and suggests; it **never edits, never blocks, never
files issues** — the [`/wiki-lint`](commands/wiki-lint.md) witness posture turned on the
governance surface, composing the read-only-subagent pattern + the witness-command pattern.
**Dev-harness only — no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged at
`2026-06-13.1`; no migration.**

- **New [`/sartor:compliance-witness`](commands/compliance-witness.md)** — the
  orchestrator command: resolves the pinned sha (`--since <sha>` or the last release tag),
  delegates the read to the model-pinned `compliance-witness` subagent via `Task`, applies a
  **flag cap (default 12, `--cap N`)**, renders the findings-register table (stable id ·
  one-line claim · ≥2 disagreeing sources cited `path:line @ <sha>` · disposition verb
  FLAG / WATCH / AFFIRM · a suggested direction), prints a `/wiki-lint`-style gate verdict
  (clean / needs attention), and **appends a dated counts-per-tier line to
  [`docs/governance/compliance-log.md`](docs/governance/compliance-log.md)**. Its only writes
  are the report surface + that log append — it **never commits, never blocks**.
- **New [`sartor:compliance-witness`](agents/compliance-witness.md)** (Sonnet, read-only
  `Read`/`Grep`/`Glob`/`Bash` — `Bash` is read-only git only) — re-derives every cited line
  at the pinned sha, finds **pairwise drift** (two named sources disagree, or one C-0
  categorical lacks the by-construction enforcement the charter requires), ranks against the
  charter + leverage tier, and returns FLAG / WATCH / AFFIRM flags. The tool grant (**no
  `Edit`, no `Write`, no `Task`**) *is* the enforcement of every HARD non-goal — it cites,
  it never asserts; zero drift is a valid honest-silence verdict.
- **Pilot run (v1.0.7) — PASSES.** One supervised run against the freshly-graduated
  [`docs/governance/`](docs/governance/) surface (born
  [`docs/governance/compliance-log.md`](docs/governance/compliance-log.md); window
  `e299ac8`→`1741ab1`, FLAG 1 / WATCH 2 / AFFIRM 3). The one FLAG (CW-01 — the
  `RELEASE_CHECKLIST` 7.2 row left `[ ]`/"pending" after `feat/governance-extraction`
  merged) was owner-scored **true drift → flag-precision 1.0 ≥ 0.66** and corrected, so the
  witness graduates toward the standing pre-tag companion (v1.1.x). The amendment
  ceremony's "a flag in the compliance agent's next drift report — witness, not approver"
  step is now satisfiable. Full design in
  [`compliance-agent-design.md`](docs/dev/reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md).

### Added — the self-documenting wiki loop (`feat/self-documenting-wiki`, Sprint 7.3)

The `docs/wiki/` knowledge layer now refreshes itself against the code through a bounded,
cost-aware Claude Code dev-harness loop — "the docs track the code without a human author,"
while a human stays at the spend boundary and the commit boundary. **Dev-harness only — no
product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged at `2026-06-13.1`; no migration.**

- **New [`/sartor:wiki-self-update`](commands/wiki-self-update.md)** — the orchestrator
  command: resolves the `.last_ingest_sha`→HEAD diff, **surfaces cost before spending** and
  enforces a per-run page cap (default 8, `--cap N`), delegates per-page synthesis to the
  `wiki-scribe` subagent and per-page grounding audit to the separate `wiki-grounding-auditor`
  subagent (author ≠ auditor), runs [`/sartor:wiki-lint`](commands/wiki-lint.md) as the
  deterministic gate, advances the checkpoint, logs, and **presents a reviewable diff — it
  never auto-commits.**
- **New [`sartor:wiki-scribe`](agents/wiki-scribe.md)** (Haiku, `Read`/`Grep`/`Glob`/`Edit`)
  — minimal SCHEMA-conformant per-page synthesis from the source at HEAD + named exemplar pages.
- **New [`sartor:wiki-grounding-auditor`](agents/wiki-grounding-auditor.md)** (Haiku,
  read-only `Read`/`Grep`/`Glob`) — adversarial quote-match of each cite/`[synthesis]` claim
  against source at HEAD → SUPPORTED / DRIFTED / UNSUPPORTED; the read-only tool grant *is* the
  "never silently rewrite committed history" enforcement.
- **Freshness hook escalation** — [`wiki-freshness-reminder.sh`](.claude-plugin/hooks/wiki-freshness-reminder.sh)
  now escalates its message to `/wiki-self-update` past a 10-file drift threshold (below it, the
  existing `/wiki-ingest` nudge). It **stays a witness** (always exit 0, silent under the
  sentinel and when nothing changed) — only the wording tiers.
- **Trigger = bounded checkpoint** (branch close-out / pre-tag — a `RELEASE_CHECKLIST` line on
  the version-bump), **no scheduler**; the loop is invoked, never self-firing. Scope is
  `docs/wiki/`-only — the cross-document link/cite checker stays a separate tracked follow-on.

### Added — governance extraction: one canonical rules home (`feat/governance-extraction`, Sprint 7.2)

Lifts sartor.'s *binding* governance rules out of the six descriptive docs they were tangled
into and into **one canonical home**, `docs/governance/` — the "extract, don't register-in-place"
decision of record (F-gov-05). Each rule is now stated **once**; each source doc keeps its prose
and gains a pointer back. Docs + hook-script only: **no product code, route, or LLM call;
`PROMPT_VERSION` unchanged at `2026-06-13.1`; no dependency; no migration.**

- **New [`docs/governance/`](docs/governance/)** — `charter.md` (the constitution: C-0…C-6,
  D-1…D-6, the W-1/W-2 working model, the amendment ceremony, the frozen 10-Principles backbone),
  `enforcement.md` (gate vs witness vs tribal, with each item's ship state), `metrics.md` (the
  v1.1.0 tag checklist SC-1..SC-5, the eval ride-along contract, the reusable review rubric).
  Graduated from the 2026-06 product-excellence review's four-file governance-draft;
  **drift-reconciled to HEAD** — the ~8 corrections that already landed in v1.0.6 (PX-01/02/03/05/
  07/08/09/13/14) are cited as corrected, not re-fixed; only the C-1 bind and C-6 boundary gates
  stay forward-sequenced to v1.0.8.
- **New [`docs/dev/EXTRACTION.md`](docs/dev/EXTRACTION.md)** — the incubant-maturity extraction
  playbook (when an in-repo system graduates to a product).
- **Source-doc pointers** — `vision.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `docs/PRODUCT_SHAPE.md`, `docs/dev/RELEASE_ARC.md` each gain a canonical-governance pointer and
  keep their descriptive content. **`AGENTS.md` stays inline-with-pointer** (non-Claude agents read
  it raw — a pure `@import` shell would strip their guardrails); `CLAUDE.md` carries the home
  transitively via `@AGENTS.md`.
- **PX-23** — the stale serial-session framing in `RELEASE_ARC.md` is reframed to the charter W-1
  worktree-per-session parallelism model.
- **PX-27** — `vision.md` gains the ATS escape hatch (goal 2), names the admitted audiences
  (A-2/A-3/A-5), and demotes "single-tenant **by design**" to a threat-model statement.
- **PX-24** — `block-merge-to-main.sh` now also blocks the dominant `git merge feature --no-ff`
  path issued while `HEAD` is `main`/`master` (via worktree-local `git rev-parse --abbrev-ref HEAD`).
- **PX-28** — `check-plan-approved.sh` no longer prints the `New-Item … .approved` hand-create hint
  (it contradicted the never-hand-create rule); the no-marker message is now just "Write a plan and
  call ExitPlanMode."
- **Carry-forward ledger** — the three scattered per-stream "Discovered…(tracked, deferred)"
  sections in `RELEASE_CHECKLIST.md` are consolidated into ONE physical authoritative ledger
  (Open / Resolved); `AGENTS.md` close-out step 0 + `AGENT_HANDOFF_TEMPLATE.md` + charter W-1 now
  require every handoff to render the full *cumulative* still-open subset, with a ~8–10 reduction-
  sprint threshold.
- **Drift fixes folded in:** `AGENTS.md` "Frontend config persistence" (dropped the absent
  `_savePrimaryResume`/`_saveIncludedResumes` names → cite the live `saveConfig()` path);
  `RELEASE_ARC.md` version map ("B.5 SkillGroupItem" → "Skill-as-Corpus-Item") + the §4.7 wiki-lint
  overclaim softened (wiki-lint is `docs/wiki/`-scoped today); `CONTRIBUTING.md` stale OSS-migration
  step reference; `CLAUDE.md` stale `.claude/hooks/` path → `.claude-plugin/hooks/`.

### Changed — plugin activation: `.claude-plugin/` commands + subagents now load (`chore/plugin-activation`, Sprint 7.1)

Makes the dormant Claude Code plugin's **10 commands + 6 subagents** invocable — previously
only the 10 hooks loaded (hand-wired in `.claude/settings.json`), while the commands/agents
were never registered (no marketplace, no install). Dev-harness only — no product code,
route, LLM call, prompt (`PROMPT_VERSION` unchanged at `2026-06-13.1`), dependency, or
migration. Unblocks the v1.0.7 self-documenting loop (`/sartor:wiki-*`) and compliance
pilot.

- **New [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)** — a local
  `sartor-tools` marketplace listing the `sartor` plugin (`source: "."`).
- **[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)** — `name`
  `resume-optimizer → sartor`; `version` `0.1.0 → 1.0.6` (lockstep with `pyproject.toml`).
  The 10 command + 6 agent `.md` files **moved out of `.claude-plugin/` to the plugin root**
  (`commands/`, `agents/`): Claude Code reserves `.claude-plugin/` for
  `plugin.json`/`marketplace.json` and **silently skips any components nested inside it**, so
  the manifest relies on the default root-level scan (no `commands`/`agents` path-overrides).
  No `hooks` key.
- **`.claude/settings.json`** — added `extraKnownMarketplaces` (`sartor-tools`, directory
  source) + `enabledPlugins` (`sartor@sartor-tools`). The existing **hooks block is
  untouched** — the security/quality hooks stay wired here, deliberately *not* migrated into
  the plugin manifest. The tool-agnostic-enforcement question (git-hooks/CI vs Claude
  plugin) is an explicit agenda item deferred to the v1.0.7 governance pass (see
  [`RELEASE_CHECKLIST.md`](docs/dev/RELEASE_CHECKLIST.md) tracked-deferred).
- Commands now load **namespaced** as `/sartor:<name>`; subagents as `sartor:<name>`.
- **Docs corrected to match reality:** command/agent path references repointed from
  `.claude-plugin/commands|agents/` to the root-level `commands/`/`agents/` across `CLAUDE.md`
  (Skill catalog + a new Subagent catalog, namespaced names), `README.md` (plugin section +
  activation line; added the omitted `headhunter` agent + `require-feature-branch` hook),
  `CONTRIBUTING.md`, `docs/system-model.md`, `docs/walkthrough.md`, `evals/README.md`, and the
  `llm-wiki-design` wiki page. Historical CHANGELOG/review/benchmark entries left as-is.

## [1.0.6] — 2026-06-15

### Changed — v1.0.6 release cut: PX-10 blast-radius correction + install test-count fix (`chore/version-bump-v1.0.6`)

Cuts the v1.0.6 release (`pyproject` `1.0.5 → 1.0.6`) and closes the durable-doc loops
that ride the version bump. v1.0.6 is an **internal** tag (public ships at v1.1.0).

- **PX-10 — stale v1.0.8 blast-radius numbers corrected** (`F-arch-02`; 2026-06 product-
  excellence review). The v1.0.8 monolith-decomposition epic's coupling rationale in
  [`docs/dev/RELEASE_ARC.md`](docs/dev/RELEASE_ARC.md) cited a `6,290-LOC / 75-route`
  `app.py` with `67 test files` importing it. Corrected to the **current-accurate**
  `8,251-LOC / 93-route` `app.py` with `32 test files` importing `app`. The prescription's
  literal targets (`6992 / 78 / 24`) were accurate only at the review-era commit `93ecc95`
  and had since drifted as B.4/B.5/PX-02 landed; writing them would have re-introduced the
  inaccuracy PX-10 exists to fix, so the numbers were re-verified against HEAD and the
  current figures used (owner-approved deviation, 2026-06-15). The historical prescription
  is annotated with the deviation, not rewritten.
- **`docs/install.md` — stale test-count floor corrected.** The "Verifying the install"
  step claimed `637+ passed`; the suite is now `1212`, so the floor is updated to
  `1200+ passed`.
- **Dev-tier wiki diff-refresh.** The deferred consolidated `docs/wiki/` refresh of the
  two drifted `audience: dev` pages (`diagnostics-console.md` + `frontend-wizard.md`,
  advancing `.last_ingest_sha` `93a34b9 → 7d8f427`) is recorded in
  [`docs/wiki/log.md`](docs/wiki/log.md) — wiki passes are tracked there, not here (see the
  Scope note at the top of this file).
- **Boundary.** Docs + version metadata only — no route, LLM call, prompt change
  (`PROMPT_VERSION` unchanged at `2026-06-13.1`), new dependency, or migration.

### Added — user-facing "what gets downloaded & why" + in-app eval-stack pointer (`docs/eval-stack-install-guide`, Sprint 6.5 #17)

The user-facing half of the downloads story. The dev-tier provenance already lives in
`docs/dev/excellence-walk/q3-downloads.md` + the `audience:dev` wiki page
`non-dependency-downloads.md`, and `CONTRIBUTING.md` owns the exact eval-stack install
commands — this adds the *user* layer. Authored from the excellence walk's Q3 deliverable;
every figure re-verified against `pyproject.toml`, `docs/install.md`, and `CONTRIBUTING.md`.

- **`docs/install.md` — new "What gets downloaded & why" section** (after Prerequisites,
  with a `what-gets-downloaded` anchor). Plain-language: the only sizeable non-pip download
  to run the app is the Chromium binary (~150 MB, OS user cache, not the repo); the optional
  grounding/eval stack (~3.2 GB of model weights) is flagged as a dev / power-user feature
  that runs only in the eval harness, with a link to `CONTRIBUTING.md` → "Grounding signal
  scorers" for the exact steps — no dev install commands inlined.
- **`README.md` — a "what actually downloads" pointer** beside the existing "What gets saved
  on your machine" section, linking the new install.md section.
- **`dashboard/templates/dashboard.html` — in-app pointer.** One sentence appended to the
  Quality-tab `dashQuality` help body (where the "grounding signals" checkbox is described):
  the offline scorers need the optional `[eval-grounding]` extras (~3.2 GB, dev-only), with
  the CONTRIBUTING.md / install.md references. Plain prose (the help body renders via
  `textContent`).
- **Boundary.** Docs + one dashboard help-copy line — no route, LLM, prompt, dependency, or
  migration; `PROMPT_VERSION` unchanged. Eval-stack install commands stay solely in
  `CONTRIBUTING.md` (single source).

### Added — in-app education for the diagnostics console (`feat/education-diagnostics-annotate`, Sprint 6.5)

Finishes the Sprint 6.5 education sweep on the one surface still left raw: the
localhost-only `/_dashboard` diagnostics console (KW9 + KW13). Plain-language,
a11y-safe, aimed at a first-time (technical) visitor.

- **Ported help mechanism.** The console is self-contained — it never loads
  `static/app.js`, and the wizard's `_initHelp` targets `.cb-panel` headers the
  dashboard doesn't have — so it carries its **own port** of the help primitive in
  `dashboard/templates/dashboard.html`: the same `#helpModal` skeleton (ids reused,
  so the `Help` POM applies unchanged), a per-tab `_DASH_HELP` registry, and an
  `openDashHelp` opener faithful to `app.js` `openHelpModal` (Esc / Tab focus-trap /
  backdrop click-away / `aria-expanded` toggle / focus-restore; the keydown listener
  is removed in cleanup so it never leaks a trap across tab switches).
- **Per-tab summary + first-expand explainer (KW9).** Every diagnostics tab opens
  with a one-line summary + an (i)-circle, and a once-ever explainer modal: the
  Pipeline explainer auto-opens on first visit (the welcome-equivalent), each other
  tab's auto-opens on its first click. Re-openable anytime via the (i). Once-ever via
  the **shared** `cb_help_seen:` localStorage prefix — so the explainers ride the
  same suppression seam as the wizard tour (the five `dash*` ids were added to the UX
  suite's `_TOUR_STOP_BLOCKS`).
- **Annotate tab rewritten for lay readers.** The verdict legend keeps the contract
  codes (`keep`/`fix`/`omit`/`fabricated`) but glosses each plainly; the read-write
  scaffold-banner + ① bootstrap copy are reframed; and the bootstrap `<details>`
  **auto-expands when there are no fixtures to annotate** so the path forward is
  obvious. Per-option `title` tooltips on the suite / subset / grounding controls
  (KW13 "grounding box" / "synthetic-vs-smoke options").
- **"Why empty" everywhere (KW13).** The Pipeline / Quality / Groundedness empty-states
  now say what the panel is, why it's empty, and what populates it.
- **Tests.** New `tests/ux/regression/test_20260615_education_diagnostics_annotate.py`
  (8 cases: per-pane (i) aria; modal open/close/focus-restore; per-tab auto-fire +
  once-ever under `show_tour`; plain-language verdict legend; bootstrap auto-expand on
  empty; "why empty" copy). The `test_axe_dashboard_console` gate now also scans the
  ported `#helpModal` in its **open** state. The stale `No eval results yet`
  route-test copy assertion was tightened to the new strings.
- **Boundary.** Front-end + copy only — **no route, no LLM call, no `PROMPT_VERSION`
  change, no new dependency, no migration.** The diagnostics console is a dev surface,
  so the education is dev content; no user-facing wiki page is authored here.

### Added — in-app education sweep: per-surface help + KW3 new-user tour (`feat/education-tailor-corpus-wizard`, Sprint 6.5)

The per-surface education **content** the help primitive was built for — plain-language,
assumes no technical background. Applies the pattern across every user-facing surface and
authors the new-user first-run tour, mirrored INTO the WS-4 wiki's reserved user section.

- **Per-surface help** — `_HELP_REGISTRY` entries (no engine change) add an (i)-circle +
  plain-language explainer to the user picker, prior applications, all six wizard-step
  panels, and the Career corpus / Résumé templates / Candidate memory panels.
- **KW3 new-user first-run tour** — a small once-ever sequence layered on the primitive:
  a welcome, an add-user tip, a post-ingest corpus explainer, a per-step modal across the
  six wizard steps, and generating / cover-letter tips. **New-users-only** via an in-memory
  "armed" flag (set on user creation / empty-corpus landing); returning users are never
  walked through onboarding. Each stop fires once (reusing the `cb_help_seen:` localStorage
  seam) and is re-openable from the nearest section's (i); wizard stops fire only when the
  panel is actually on screen (visibility-guarded).
- **Wiki** — five new `audience: user` guides under `docs/wiki/pages/` (`using-sartor`
  hub + tailoring / corpus / templates / memory), mirrored by the in-app copy. Recorded in
  [`docs/wiki/log.md`](docs/wiki/log.md) (a content pass — `.last_ingest_sha` unchanged).
- **Tests** — new `tests/ux/regression/test_20260614_education_help.py` (every panel's icon
  + aria; open/close/focus for regular and wizard-step headers; tour arming, once-ever, and
  the visibility guard); the vendored axe a11y gate gains a help-modal-from-step-header scan;
  the autouse welcome-suppression fixture generalized to all tour stops + a new `show_tour`
  marker. A scoped `.cb-step-header.has-help-icon .help-info` rule centres the (i) on the
  baseline-aligned step headers.

Front-end + content only — no Flask route, no LLM call, no prompt change (no `PROMPT_VERSION`
bump), no new dependency, no migration.

### Added — reusable in-app help primitive (`feat/help-pattern-component`, Sprint 6.5)

The mechanism the Sprint 6.5 in-app education sweep hangs its copy on — built once,
a11y-safe, reusable. **No per-surface education copy is authored here** (that is the
next branch); this ships the engine plus a single demo entry so it is exercised and
gated.

- **One shared `#helpModal`** (cloned from the existing `.cb-modal` skeleton) whose
  title/body are swapped per block; the stable `#helpModalTitle`/`#helpModalBody` ids
  keep `aria-labelledby`/`aria-describedby` valid without per-open rewiring.
- **One generic `openHelpModal(blockId, triggerEl)`** factored from the existing
  per-modal pattern (Esc, Tab focus-trap, backdrop click-away, focus restored to the
  trigger) — the reusable opener the five existing modals each re-implemented. They are
  left untouched.
- **A `.help-info` (i)-circle** injected into each registered `.cb-panel` header
  (mirrors `.compose-order-info`) re-opens that block's modal. **No color-only meaning:**
  the literal "i" glyph + an `aria-label` ("Help: <title>") + `aria-haspopup="dialog"`/
  `aria-expanded` carry the semantics; colour is decorative hover only. An optional inline
  short-form line is injected atop the panel body and associated via `aria-describedby`.
- **First-view welcome auto-modal** (graceful fade-in via the existing `cb-modal-in`
  keyframe + `prefers-reduced-motion`), shown **once-ever** via a `cb_help_seen:<block>`
  **localStorage** flag — the app's first client-side storage usage (wrapped so a
  disabled/throwing store is non-fatal).
- **Tests:** new `tests/ux/regression/test_20260614_help_pattern.py` (auto-open,
  click-away, once-ever, icon re-open, focus restore, aria wiring); `#helpModal` added to
  the vendored axe a11y gate's scanned surfaces; a `Help` selector class in `ui_pages/`.
  The welcome is default-suppressed for the rest of the UX suite by an autouse fixture +
  the new `show_welcome` marker, so its full-screen backdrop never blocks other tests.

Front-end + help-component only — no Flask route, no LLM call, no prompt change (no
`PROMPT_VERSION` bump), no new dependency, no migration.

### Added — eval-smoke gate guard + README exit-code reconciliation (`test/eval-gate-guard`, PX-13)

Affirms and guards the eval-quality regression gate so it can't silently rot (2026-06
product-excellence review: `F-qe-rel-05`, KEEP/CONFIRMED; rides the PX-08 egress gate). The
eval-smoke gate is a real machine gate: `evals/runner.py` returns process exit-code `2`
(failing the label-gated CI check) on **either** a sub-`PASS_THRESHOLD` (4.0) rubric score
**or** a regression past `REGRESSION_DELTA` (0.5) vs the committed `baseline_v1.json`
(`exit_code = 0 if (n_fail == 0 and not regressions) else 2`).

- **Meta-test** — new `tests/test_eval_runner.py::TestEvalGateGuard` pins **both** exit-`2`
  arms with an LLM-free stub (runs in the default `pytest`, no paid Anthropic call): a
  grounding score below the threshold (`n_fail` path), and a grounding score that passes the
  threshold but drops past `REGRESSION_DELTA` below a seeded baseline (`regressions` path,
  `n_fail == 0`). If a future change softens the gate (drops `not regressions`, loosens a
  threshold, adds `continue-on-error`), the test goes red.
- **Do-not-regress note + CI scope** — reconciled `evals/README.md`, which had drifted: three
  spots (quick-start, the exit-codes table, the "Regression alerting" section) still claimed
  regressions were *informational* and didn't affect the exit code. That was true before commit
  `a60a008` ("PR gate") made regressions gate; the narrative was never updated. Corrected to the
  actual contract, added a "Do-not-regress: the gate is machine-enforced" callout, and recorded
  the CI scope explicitly — grounding-rubric-only across the 3 synthetic fixtures, label-gated
  (`eval`), no `continue-on-error`.

Test + docs only — no change to the gate's behavior, no prompt, route, dependency, or
migration; `PROMPT_VERSION` unchanged.

### Changed — C-0 claims discipline: no-invention absolutes reworded (`docs/c0-claims-discipline`, PX-09 + PX-14)

Documentation-only corrections from the 2026-06 product-excellence review's PX band, reconciling
the absolute "no invention" register on the highest-audience surfaces with what the system
actually enforces. C-0 bars LLM-behavior absolutes; the owner recanted the exact strings in the
review interview (R2-4.2 "'LLM cannot invent' is a bold claim … we do our best"; R2-4.4 "no
invention ever is over-stated").

- **PX-09 — no-invention absolutes → mechanism-and-effort** (`F-vision-02` / `F-docs-03`; charter
  C-0, A-4). Reworded the categorical "The LLM cannot invent facts." and the "No invention, ever"
  heading (`vision.md`), and the "without inventing anything about you" / "may not fabricate"
  taglines (`llms.txt`, `docs/wiki/overview.md`, `docs/system-model.md`), to describe the actual
  mechanism — a grounding check in the generation prompt plus the `grounding_overlap` *witness*
  metric that **measures** rather than enforces-by-construction — and to say plainly it is
  best-effort, **not** a categorical guarantee. The two near-identical product taglines (overview /
  system-model) now read identically; each file's "Open revision points → point 4" self-reference
  was updated so it no longer quotes the retired opening.
- **PX-14 — `GROUNDING_METRIC.md` union correction** (`F-eval-04`; rides PX-09's branch per the
  prescription). The metric design note claimed a **four-part** source union (incl. first-person
  typed edits); corrected to the actual **three-source** deterministic union (`original primary
  résumé + supplemental résumés + clarification answers`). Typed edits remain prompt-side ground
  truth for the *model* — they widen the generation grounding check — but are not a member of the
  *metric's* source set. Doc now follows code (`hardening.assemble_source_union`); no code change.

Docs only — no code, prompt, route, dependency, or migration; `PROMPT_VERSION` unchanged.

### Changed — disclosure-doc corrections (`docs/disclosure-doc-corrections`, PX-03/05/07)

Documentation-only corrections from the 2026-06 product-excellence review's PX band, aligning
the public-facing security / governance docs with what the tool actually does.

- **PX-03 — two-class egress enumeration** (`AL-7`; charter C-2). `SECURITY.md` listed a third
  "any URL you explicitly paste as a job description" HTTP-egress class that has never existed:
  `jd_url` is provenance metadata, never fetched (the only network fetch is
  `scraper.fetch_url_content`, called solely for profile / portfolio URLs). Corrected to the two
  real classes — the Anthropic API and the opt-in profile/website scrape — with an explicit "JDs
  are always pasted text" note. `vision.md` / `README.md` already enumerated two classes; left
  unchanged. Corroborated by the PX-08 egress allowlist gate.
- **PX-05 — disclosure channel repointed** (`F-sec-11`, P1 / S-1). Conduct / vulnerability
  reports routed to a stale `Cooksey/resume` GitHub advisories inbox; corrected to the canonical
  `take-tempo-public/sartor` in `CODE_OF_CONDUCT.md` and `.github/ISSUE_TEMPLATE/config.yml`.
- **PX-07 — human SLAs softened** (`F-qe-rel-08` / `F-sec-07`; charter D-4 + P-3). The hard
  "5 business days / 30 days" promises in `SECURITY.md` and `CODE_OF_CONDUCT.md` are reworded to
  best-effort intent (no guaranteed timeline) for a solo project. Machine gates unchanged.
- **Stale-ref fold-in** (owner-authorized). The same stale `Cooksey/resume` repo target in
  `CONTRIBUTING.md` (`cd resume`), `.claude-plugin/plugin.json` (`homepage`), and
  `evals/schemas/context_set.schema.json` (`$id` — cosmetic; resolved only by file path) was
  corrected in the same pass to avoid future one-file branches. The plugin's `author.name` (the
  maintainer) and `name` / description (a project-rename concern for v1.0.7) were left untouched.

Docs / metadata only — no code, prompt, route, dependency, or migration; `PROMPT_VERSION`
unchanged.

### Added — profile/website scrape re-wired into the runtime path (`fix/profile-scrape-rewire`, PX-02)

The opt-in LinkedIn / website / portfolio scrape (`scraper.fetch_profile_content`) had been
**dead code** — no runtime caller since the corpus/DB refactor — so the docs' "live profile
scrape" claim was false (2026-06 product-excellence review: `F-docs-04` / `AL-5`). It is now
wired to an explicit, opt-in user action so the claim is honest.

- **New route** `POST /api/users/<u>/profile/fetch` — reads the saved config's `linkedin_url` /
  `website_url` / `portfolio_urls`, runs the deterministic best-effort scraper, and caches the
  combined text. Triggered by a **"Fetch profile content"** button in the Settings drawer (saves
  config first, then fetches). Guarded by `_safe_username` + `_within`; the network egress stays
  inside the already-sanctioned `scraper.py` (PX-08 allowlist unchanged — no new egress site).
- **Dedicated storage** — cached in a new `Candidate.online_profile_text` column (alembic `0010`)
  and surfaced to the LLM via a new `<candidate_web_presence>` prompt block (`PROMPT_VERSION` →
  `2026-06-13.1`). Deliberately **distinct** from `profile_text`, which β.6 repurposed as the
  positioning summary (résumé `basics.summary` fallback) — so the scrape can never clobber a
  candidate's summary.
- Opt-in + graceful: nothing fetches until the user clicks; unreachable URLs are swallowed to
  empty; a config with no URLs is a valid opt-out. No new dependency (`requests` + `beautifulsoup4`
  already shipped for `scraper.py`). The runtime wiring is pinned by a regression test so it can't
  silently die again. (PX-03 egress-doc alignment is a separate later branch.)

### Added — network-egress falsifiability gate (`test/egress-falsifiability`, PX-08 / G-2)

A committed test (`tests/test_egress_allowlist.py`) now makes charter claim **C-2**
machine-falsifiable instead of a one-time hand audit (2026-06 product-excellence review:
`F-qe-rel-02` P0 + `F-sec-01`; gate **G-2**, release-pass-plan.md §2). It fails if anything
opens an outbound socket outside the **two** sanctioned destination classes — the configured
LLM provider (`api.anthropic.com` via the `anthropic` SDK) and the opt-in profile/website
scrape of arbitrary user URLs (`requests` in `scraper.py`) — or if any Jinja template loads an
off-box CDN resource. This is the construction that keeps **PX-01**'s Chart.js vendoring honest:
it would have caught the prior `cdn.jsdelivr.net` `<script>` by construction.

- **Static egress allowlist** (the core gate) — an AST scan asserts the set of production
  modules importing a network-egress library is *exactly* the sanctioned eight (anthropic in
  `analyzer.py` / `app.py` / `evals/runner.py` / `evals/bootstrap.py` /
  `onboarding/extract_experiences.py` / `onboarding/corpus_import.py` / `scripts/smoke_phase_b1.py`;
  `requests` in `scraper.py`). A new egress site anywhere — or allowlist rot — fails. Walks the
  whole AST so lazy / `TYPE_CHECKING` imports are caught; `urllib.parse` (string parsing) is not
  flagged.
- **Runtime checks** (pytest-socket) — the provider `base_url` is pinned to `api.anthropic.com`;
  the seven deterministic modules open no socket at call time; and the scrape path is proven a
  real, blockable egress (IP-literal so the block fires before DNS, not swallowed to `""`).
- **Template scan** — generalizes the rendered-output assertion at
  `tests/test_dashboard_routes.py:377-379` to a static scan of every template source
  (`templates/`, `dashboard/templates/`, `personas/`), flagging any off-box `<script>`/`<link>`/
  media/`url()` resource load or known CDN host.

New dev dependency `pytest-socket` (`[dev]` extras only; inert until invoked — no global
`--disable-socket`, so the default suite and the `-m ux` live-server tier are untouched). G-2
becomes a required CI check at **v1.0.7**; this lands the committed test + dependency it enforces.

### Changed — vendored Chart.js; declared vendored-asset licenses (`fix/vendor-chartjs`, PX-01 + PX-06)

Chart.js 4.4.0 (MIT) is now **vendored** at `static/vendor/chart.umd.min.js` instead of
loaded from `cdn.jsdelivr.net` at runtime — closing the runtime-CDN contradiction with
SECURITY.md / vision.md's "no external CDN / no third-party fetch at runtime" promise
(2026-06 product-excellence review: `F-sec-03` / `F-vision-05` / `F-docs-02`; charter
C-2(i)). The downloaded bytes were verified byte-for-byte against the prior `integrity`
SHA-384 before the CDN `integrity`/`crossorigin` attributes were dropped. SECURITY.md now
inventories both vendored assets' licenses — Chart.js (MIT) and the test-tier axe-core
4.10.2 (**MPL-2.0**) (`F-sec-08`, PX-06). No new Python dependency (vendored static asset,
like `paged.polyfill.js`).

### Added — individual skills as a Corpus Item (`feat/skill-group-item`, Sprint 6.6 B.5)

The flat `Skill` row is promoted to a full Corpus Item — the same lifecycle every
other corpus type already has (mirrors **Bullet**): taggable, recommend-curated,
pin/drop/reorder per JD, with a suggested → approved/denied review flow. Maps to
JSON Resume `skills[]`. New migration `0009` (ALTER `skill` + new `skill_tag` join
+ backfill) and **two** new Haiku calls; **`PROMPT_VERSION` bumped to `2026-06-12.2`**
(two new system prompts registered). No new dependency. (Settled interactively with
the owner: this replaces the original "skill clusters" framing — individual skills,
no grouping — and the grounded-suggestion generator is a **user-authorized** scope
addition beyond the literal RELEASE_ARC row.)

- **`Skill` promoted to a Corpus Item.** Gains `is_active` / `is_pending_review` /
  `source` / `display_order` / timestamps + a `SkillTag` join (mirrors `BulletTag`).
  Migration `0009` backfills every legacy row as `source='imported'`, active,
  approved, with `display_order` preserving the prior name-sorted order — so the
  no-curation output is unchanged.
- **`recommend_skills` (Haiku) — order + curate.** Given the candidate's active,
  approved skills (+ tags) and the JD, returns the relevance-ordered set the Compose
  card seeds as the default. Selects only from the approved set, so it can never
  invent a skill. Auto-applied like bullets; the user pins / drops / reorders on top.
- **`suggest_skills` (Haiku) — grounded generator.** Proposes skills the JD wants
  **and** the candidate's corpus evidences (evidence-or-nothing; never JD-only).
  Proposals land as **pending** (`source='llm_proposed'`) for the user to approve or
  deny — the human gate is the grounding backstop: a pending skill never reaches the
  recommend set, the preview `skills[]`, or the generate prompt until approved.
- **Per-application curation.** `composition_overrides` gains `pinned_skill_ids` /
  `excluded_skill_ids` / `skill_order` (each persisted only when non-empty, so the
  default path stays byte-identical). The recommend output rides on
  `llm_skill_recommendations`. All save paths route through the canonical
  `_collectCompositionState()`, so a skill save never clobbers sibling overrides.
- **Reach: download + preview.** `_collect_skills` (deterministic) applies the
  recommend ∪ pinned − excluded selection (ordered) to the preview `skills[]`; at
  generate time `_apply_recommended_skills` patches the candidate's skills list so
  the **LLM-authored download** surfaces the same curated/ordered set. No-op (and
  byte-identical) when there's no recommendation and no overrides.
- **Surfaces.** Compose gets a candidate-level **Skills** card (Tailor / Suggest +
  pin/drop/reorder + a pending review lane); the Career-corpus tab gets a **Skills**
  editor (add / retire / tag + approve/deny suggestions).
- **5 route families** — skill CRUD (`GET`/`POST /api/users/<u>/skills`,
  `PUT`/`DELETE /api/skills/<id>`), skill tag link/unlink, and per-application
  `POST .../recommend-skills` + `POST .../suggest-skills`, plus the `/composition`
  extension. Eval: corpus-mode-only; the legacy generate path is byte-identical, so
  the paid smoke is skipped (covered by unit + UX); see `evals/TUNING_LOG.md`.

### Added — per-role intro as a multi-variant Corpus Item (`feat/experience-summary-item`, Sprint 6.6 B.4)

The per-role intro paragraph — the line a recruiter reads first under each job —
becomes a first-class, multi-variant Corpus Item, mirroring the candidate-level
`SummaryItem` but scoped per-`Experience`. Maps to JSON Resume `work[].summary`.
New migration `0008` + a new Haiku `recommend_experience_summaries`; **`PROMPT_VERSION`
bumped to `2026-06-12.1`** (the generate prompt gained a conditional `<summary>`
element + guide). No new dependency.

- **Opt-in, not auto-applied.** Unlike `SummaryItem` (which auto-lands on the
  recommendation → first-active → profile_text), a role intro appears **only when
  the user turns on the Compose-step "Add role intros" toggle for that application
  AND a variant is chosen** (`composition_overrides.use_experience_summaries` +
  `chosen_experience_summary_ids`). Toggle off (the default) is a full no-op — the
  generate prompt is **byte-identical**, so the analyze→generate cache is untouched
  for anyone who doesn't opt in. The sentinel `0` records an explicitly-cleared role.
- **WYSIWYG into the real résumé.** A chosen intro is injected into the frozen
  `career_corpus` snapshot at generate time by `_apply_chosen_experience_summaries`
  (mirroring `_apply_chosen_summary`), so it reaches **both** the LLM-tailored output
  **and** the deterministic JSON-resume/PDF preview (`work[].summary`). The legacy
  single `Experience.summary` column is now a denormalized cache — migration `0008`
  backfills it into one `imported` variant; it is no longer auto-emitted.
- **Model + migration.** New `ExperienceSummaryItem` (+ `ExperienceSummaryItemTag`)
  tables (FK → `experience.id`, CASCADE), mirroring `SummaryItem`. Idempotent Alembic
  `0008` with a backfill from non-empty `Experience.summary`.
- **Routes.** Experience-scoped CRUD (`GET`/`POST /api/experiences/<id>/summaries`,
  `PUT`/`DELETE /api/experience-summaries/<id>`) with the bullet routes' ownership
  pattern (experience → candidate → `_safe_username`); a batched
  `POST /api/applications/<id>/recommend-experience-summaries` (one Haiku call keyed
  by `experience_id`, mirroring `recommend_application_summary`).
- **UI.** A per-role intro picker inside each Compose experience card (sits between
  the title and the bullets); the application-level **Add role intros** toggle (seeds
  each role from the AI recommendation on enable); a per-experience intro-variants
  editor in the Career-corpus tab (add / rename / retire). Composition GET surfaces a
  per-experience `summary` block + the toggle state; the per-role picks ride the
  canonical composition autosave so bullet/title saves never clobber them.
- **Tests.** New `tests/test_experience_summary_item_routes.py` (CRUD + ownership +
  soft-delete + real migration backfill), `tests/test_recommend_experience_summaries.py`
  (batch short-circuit + dedup + route), `tests/test_experience_summary_composition.py`
  (GET/POST + generate-path injection + a **byte-identity** guard on the default
  prompt), an opt-in mapping suite in `tests/test_corpus_to_json_resume.py`, and a UX
  regression `tests/ux/regression/test_20260612_experience_summary_item.py`. New
  `ui_pages` selectors + Corpus/Compose page-object methods; the UX stub gains
  `fake_recommend_experience_summaries`.
- **Fixed (in-scope, user-authorized): Compose save no longer clobbers sibling
  overrides.** `_togglePositioningPin` (the candidate positioning-summary pin) used
  to hand-gather only bullets, so pinning a summary silently wiped `bullet_order` +
  `pinned_title_ids` (and the bullet autosave wiped `pinned_summary_id`). All save
  paths now route through the canonical `_collectCompositionState()`, so every
  override family — bullets, order, title pins, **and** the new role intros —
  survives any single save. Regression-locked (`test_positioning_pin_preserves_title_pin`).
  Also fixed the `fake_recommend_summaries` UX stub's shape (it never set
  `has_recommendation`, looping the positioning card's auto-fire once 2+ candidate
  variants existed). ruff ✓ · mypy ✓ (149 files) · pytest **1127/1127** incl. `-m ux`.

### Added / Changed — corpus-first IA + smart landing (`feat/corpus-first-tab-onboarding`, Sprint 6.4 #16 + #1 + KW1)

Front-end only — SPA tab routing over one existing read endpoint
(`GET /api/users/<u>/experiences`). No new route, no LLM call, no
`PROMPT_VERSION` bump, no new dependency, no migration.

- **Tabs reordered to corpus-first.** The top tabs now read **Career corpus →
  Tailor → Résumé templates → Candidate memory**. Only the `<nav>` button order
  changes; **Tailor keeps the default active state** because the user picker
  (`#panelUser`) lives in the Tailor tab and the no-user landing must show it.
- **Smart landing on user select (KW1).** `onUserSelect()` now routes through a
  new side-effect-free `_landingTab()` helper instead of unconditionally showing
  the applications panel: an **empty corpus lands on Career corpus** (onboard —
  import a résumé), a **populated corpus lands on Tailor** (straight to the
  workflow). Fixes the dead-end where a brand-new user landed on JD entry with
  nothing to tailor from.
- **`goHome()` honors smart landing.** The wordmark route now goes through the
  same `_landingTab()` (single source of truth for "which tab is home") rather
  than a hardcoded `'tailor'`. Because it deselects the user first, it still
  resolves to the picker's home (Tailor).
- **"Start tailoring →" hand-off CTA.** When corpus review is finished — a
  non-empty corpus with **0 items pending** — the onboarding banner flips to a
  success (`is-ready`) state offering **Start tailoring →**, which switches to
  the Tailor tab. Replaces the old dead-end (the banner used to just disappear).
  The banner refresh in `refreshCorpus()` was relocated to fire after the list
  renders so its ready/empty decision reads fresh `_corpusExperiences`.
- **Tests.** New UX regression
  `tests/ux/regression/test_20260612_corpus_first_landing.py` (empty→Corpus,
  populated→Tailor, ready→CTA→Tailor). `test_20260612_logo_home_route.py` now
  seeds a non-empty user so its select-then-home flow still lands on Tailor under
  smart landing. New `Corpus.START_TAILORING_BUTTON` selector +
  `CorpusPage.start_tailoring_button()` POM accessor.

### Fixed — logo routes home (`fix/logo-home-route`, Sprint 6.4 #23)

Front-end only — no LLM call, no `PROMPT_VERSION` bump, no new dependency, no
route (pure client-side SPA navigation), no migration.

- **The `sartor.` wordmark now routes home.** It was an inert `<a href="#">`
  with no handler — once a user was selected (and the wizard or another tab
  engaged) there was no way back to the landing state. A new public `goHome()`
  clears the selected user via `onUserSelect()`'s no-user branch (hides the flow
  panels, re-locks the user picker open, resets iteration state) and restores the
  default **Tailor** landing tab via `switchTopTab('tailor', …)`. The wordmark
  anchor gains `onclick="goHome(); return false;"` (cancels the bare `#`
  navigation) plus a clearer `aria-label`/`title`. Which tab counts as "home"
  stays the current default — the smart-landing reorder is the separate next
  6.4 branch (`feat/corpus-first-tab-onboarding`).
- **Tests.** New UX regression
  `tests/ux/regression/test_20260612_logo_home_route.py` (select user → off-tab →
  wordmark click → asserts the Tailor tab restored, user deselected, picker
  re-locked open, flow panel hidden). New `Header` selector in
  `ui_pages/selectors.py`. Axe a11y gate stays green.

### Fixed — internal tooling (`fix/require-feature-branch-worktree-aware`)

- **`require-feature-branch` hook is now worktree-aware.** It resolves the
  branch of the repo containing the *target file* (`git -C`) instead of the
  hook's cwd, so edits to a feature branch in a separate worktree/clone are no
  longer falsely blocked by the launch clone being on `main`. Hook-only change;
  no LLM call, no `PROMPT_VERSION` bump, no new dependency, no route, no migration.

### Added / Changed — corpus affordance polish (`fix/corpus-affordance-polish`, Sprint 6.3 #2 + #5 + KW2)

Front-end polish + one DB-only route on the Career Corpus tab. No LLM call, no
`PROMPT_VERSION` bump, no new dependency, no migration.

- **KW2 — corpus-wide "Accept all pending."** A new `Accept all pending` button
  in the onboarding banner clears `is_pending_review` across **every** role in
  one click (senior résumés have many roles, previously accepted one-by-one). New
  DB-only route `POST /api/users/<username>/accept-all-pending` (`_safe_username`
  guard; mirrors `accept_experience_all` candidate-scoped, reusing the `exp_ids`
  query from `pending-counts`). The existing per-experience `ACCEPT ALL PENDING`
  still covers the by-role case. The control guards behind a **sharp confirm**:
  accepted items become source-of-truth the system scores for fit, generates new
  bullets from, and builds résumés on — one bad seed poisons everything
  downstream.
- **Empty-state copy — dropped the "automatically" overpromise.** Imported
  résumé items land *pending review*, so the empty-corpus copy (`static/app.js`)
  and the static corpus hint (`templates/index.html`) now say the import is
  extracted "for you to review" rather than built "automatically."
- **#5 — enlarged the panel collapse chevron.** `.panel-header::after` (`▾`)
  10px → 18px; it was near-imperceptible. (A later redesign rule had pinned the
  *effective* size to 10px, overriding the legacy 12px rule — sized on the live
  rule, with a comment so the next editor doesn't hit the same trap.)
- **#2 — regression-locked the "Add variant" affordance.** The finding ("Add
  variant referenced in copy but no affordance") was already resolved by the
  β.6e summary-variants editor; a new UX test now asserts the `+ Add variant`
  control is present so it can't regress.
- **Tests.** New backend `TestAcceptAllPendingCorpus`
  (`tests/test_pending_review_routes.py`) + new UX regression
  `tests/ux/regression/test_20260612_corpus_affordance_polish.py` (affordance
  present · review-honest empty copy · accept-all clears + hides the banner ·
  chevron size). New `Corpus` selectors in `ui_pages/selectors.py` +
  `CorpusPage` helpers. Axe a11y gate stays green.

### Added — reusable required-field marker + auto-populatable username dropdown (`feat/required-field-and-dropdown-pattern`)

Two reusable front-end conventions (Sprint 6.3, findings #21 + #20-dropdown),
built on the axe a11y gate that the prior branch landed. Front-end + tests only —
no LLM call, no `PROMPT_VERSION` bump, no new route (reuses `GET /api/users`),
no new dependency, no migration.

- **#21 — reusable required-field marker.** A new convention: a required input
  carries `required` + `aria-required="true"`; its visible label carries a
  decorative `<span class="required-marker" aria-hidden="true">*</span>`; a field
  cluster gets one `<p class="form-required-legend">` line. The two classes live
  in `static/style.css` (shared — the dashboard loads it too), documented by a
  load-bearing comment. `aria-required` is the real signal assistive tech
  announces; the asterisk is purely visual (`aria-hidden`). Proven across **three
  render paths**: the static new-user form (`templates/index.html` —
  username/name/email; the optional contact fields stay unmarked), the
  JS-rendered `openFormModal` modals (`static/app.js` — every `required:true`
  field gets the marker + `aria-required` for free, covering add-title /
  add-bullet / add-experience), and the console dropdown label (below).
- **#20 (dropdown) — auto-populatable input → `<select>`.** The diagnostics
  console's candidate-username fields (`#bsUser` on the Annotate tab, `#tuneUser`
  on the Tuning tab) were free-text `<input>`s that should pick from the known
  set of candidates. They are now `<select data-user-source>` auto-filled on load
  by a small reusable `populateUserSelects()` helper that fetches the existing
  `GET /api/users` (mirrors `loadUsers()` in `app.js`) — any select opting in via
  `data-user-source` is filled, with the placeholder `<option value="">`
  preserved so the existing `.value` reads + "provide a username" guards still
  work. `#bsUser` (genuinely required) carries the required marker; `#tuneUser`
  does not — its "Real-corpus seed (optional)" section is optional.
- **Tests.** New regression
  `tests/ux/regression/test_20260612_required_field_and_dropdown.py` (the marker
  across all three render paths + dropdown populate/select round-trip); the
  dashboard axe scan now seeds a candidate and opens the collapsed sub-panels so
  the **populated** dropdowns are scanned, not just empty placeholders. Selector
  registry gains a shared `Forms` class + the Tuning username handles.

### Added — axe-core accessibility smoke gate + a11y fixes (`fix/form-field-labels-a11y`)

The never-shipped a11y gate (Sprint 6.3, finding #3) — the arbiter that guards
every later v1.0.6 branch — plus the violations it surfaced. Front-end + one new
test tier only; no LLM call, no `PROMPT_VERSION` bump, no route, no migration,
**no new pip dependency** (axe-core is vendored, not installed).

- **New a11y gate — `tests/ux/a11y/test_axe_smoke.py`.** Injects the **vendored**
  axe-core engine (`tests/ux/a11y/vendor/axe.min.js`, axe-core `4.10.2`, MPL-2.0)
  into each reachable panel — landing, new-user form, the four top tabs, the
  Settings drawer, a stubbed Compose/Template drive, and every `/_dashboard` tab
  — and asserts **no `serious`/`critical` violations**. Vendored (not a pip dep)
  so it runs wherever the UX-tier Chromium runs and can never silently skip from
  a missing extra; rides the existing `tests/ux/conftest.py` harness (Chromium
  graceful-skip + console/5xx sentinel). New `a11y` pytest marker — the tests are
  also `ux`, so they run inside `pytest -m ux`; `pytest -m a11y` runs them alone.
- **Form-field labels were already clean** (defect-vs-expected: the "~150 flagged
  fields" predated the v1.0.5/v1.0.6 redesign). The gate found **zero** label/name
  `serious`/`critical` violations. Belt-and-suspenders completion of #3 anyway:
  `sr-only` labels on the three hidden file inputs (`templateUploadInput`,
  `corpusIngestFile`, `personaUploadInput`) and `name` + `autocomplete` on the
  new-user form + Settings-drawer personal fields (the "missing autofill" half).
- **Fixed — color-contrast (the only `serious` violations the gate found).** The
  muted-text tokens were sub-WCAG-AA on the dark surfaces: `--fg-2` (`#6c6c7a`,
  down to 3.19:1) and `--fg-3` (`#4a4a56`, down to 1.72:1) are lightened to
  `#9b9ba7` / `#8f8f9b` (≥4.5:1 on the darkest surface, including the warm
  selected template-row bg), and `.edit-hint` drops its `opacity: 0.7` (which
  composited `--fg-1` to a sub-AA `#7c7d88`) for a solid `--fg-2`. Token-level fix
  in `static/style.css`, so it clears the Settings hints, the Step-4 template
  chips/sub-labels, and the `/_dashboard` meta/cost/link text in one place
  (user-approved scope addition — design-system color change).

### Fixed — diagnostics-console chart + layout corrections (`fix/diagnostics-chart-corrections`)

Three `/_dashboard` defects from the v1.0.6 kickoff walkthrough harvest (Sprint
6.2; findings #11 + #12 + #13), plus the KW13 space-usage restructure. Front-end
+ deterministic-aggregation only — no LLM call, no `PROMPT_VERSION` bump, no new
route, no new dependency, no migration.

- **KW13 + #12 — panels now use the page width; the Calls table no longer
  horizontal-scrolls.** The detail surface was a cramped 560px right-hand side
  drawer, so the 10-column **Calls** (throughput) table overflowed with a
  horizontal scrollbar (#12). The drawer is replaced by a **full-width inline
  detail panel** rendered in the page flow beneath the tabs: the selected tile's
  detail block is moved into it from `#detailStore` (reusing the existing
  move-the-node + lazy-`initCharts` machinery — only the destination changed) and
  scrolled into view. Every detail (Calls, heatmap, health, reliability, pareto,
  trace, all charts) now renders at full width (KW13), and the Calls table fits
  with no scroll (a defensive `word-break` on its cells guards narrow viewports).
- **#13 — latest-trace bars now render and scale to the longest span.** Two
  problems compounded into "bars look empty": the `.wf-bar` was a `<span>` left
  at `display:inline`, so its `width` never applied and **every bar rendered at
  0px**; and the width was each span's share of the run *total*, so even once
  visible a short span (e.g. a 4s `clarify` beside a 60s `analyze_synthesis`) was
  a sliver. Fix: `.wf-bar` is now `display:block` with a 2px `min-width` floor,
  and `dashboard/routes._run_trace` emits `bar_pct` scaled to the **longest
  span** (max → 100%); the template binds bar width to `bar_pct`, keeps the
  share-of-total `pct` on hover, and keeps `latency_ms` as the absolute truth.
- **#11 — cost-by-kind chart tooltip is now unambiguous.** The walkthrough read
  the cost chart's tooltip as "Total" but plotting the mean. It always plotted
  the **total** (`total_cost_usd = sum`, unchanged since the console was built);
  the confusion was an unlabeled default tooltip beside a `mean $` table column.
  The chart now carries an explicit tooltip naming the value as the total with
  count + mean for context (e.g. `generate — total $0.02340 · 12 calls · mean
  $0.00195`). Data unchanged.
- Covered by a deterministic unit test for `bar_pct`
  (`tests/test_dashboard_routes.py::TestRunTrace`) and a UX-tier regression
  (`tests/ux/regression/test_20260611_diagnostics_chart_corrections.py`): the
  detail panel uses the page width with no horizontal overflow on Calls, the
  trace bars scale to the longest span, and the cost tooltip names total + mean.
  The dashboard POM + selectors moved from `drawer` to `detail-panel` handles.

### Fixed — wizard-flow polish: follow-up-question auto-scroll + copy alignment (`fix/wizard-flow-polish`)

Two small Output-panel polish fixes from the v1.0.5 walkthrough harvest
(Sprint 6.1, final row; findings KW5 + KW8):

- **KW5 — auto-scroll.** Clicking the post-generation **"Get follow-up
  questions"** button rendered the iteration questions *below the fold*, so it
  looked like nothing happened. `runIterateClarify()` now scrolls the revealed
  `#iterateClarifyArea` section into view in its success path (reusing the
  existing `scrollIntoView({behavior:'smooth',block:'start'})` idiom), covering
  both the questions and the "no follow-up questions surfaced" branches.
- **KW8 — copy alignment.** The button label and section divider used
  "interview" wording inconsistent with the clarify vocabulary (the button's own
  tooltip already said "clarifying questions"). They now read **"Get follow-up
  questions"** and **"Follow-up clarification"**. The `#btnIterateClarify` id is
  unchanged, so selectors / page objects are unaffected. The tracker "Got
  interview" outcome status is a different concept and was left untouched.
- Front-end only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new
  dependency, no migration. Covered by a UX-tier regression
  (`tests/ux/regression/test_20260611_wizard_flow_polish.py`): a cheap static
  copy guard plus a full analyze→generate→follow-up drive that verifies the
  scroll deterministically by spying on `scrollIntoView`. That drive needed two
  new UX stubs (`fake_generate_streaming` + `fake_clarify_iteration` in
  `tests/ux/stubs.py`) — the first UX test to exercise the generate route.

### Fixed — a detached cover letter is now persisted to its run row (`fix/run-cover-letter-persistence`)

Generating a cover letter via the Step-6 "+ Generate cover letter" button left
**no DB trace**: `ApplicationRun.generated_cover_letter_md` stayed empty even
after the letter was generated and downloaded (confirmed against the e2e
walkthrough run row, which had résumé md + bullets + titles + ATS json but no
cover-letter md). The detached route `POST /api/generate-cover-letter` wrote the
letter to disk and into the context file but never touched the database. (The
*other* path — `/api/generate` with `with_cover_letter=True` — already persisted
it; the gap was exclusively the detached, common-case route.)

- **Fix.** After writing the letter, the route now persists
  `generated_cover_letter_md` onto the **same** run row the résumé generation
  wrote to (identified by `context_set["application_run_id"]`), via a new
  surgical single-column write-back (`db.persist_run.persist_cover_letter_md` +
  the `app._persist_cover_letter_to_db` wrapper, mirroring
  `_persist_corpus_generation_to_db`). Corpus-backed mode only (legacy contexts
  without a run id skip it, as `/api/generate` does), and best-effort — a DB
  hiccup logs but never fails a letter the user already downloaded.
- **Why a dedicated helper, not `persist_corpus_generation`.** That function
  unconditionally writes `generated_resume_md = result.get("resume_content")`;
  a cover-letter result carries no résumé content, so reusing it would have
  *nulled out the already-saved résumé md*. The new helper writes one column and
  leaves the résumé md untouched.
- **Why now.** B.8 Part 2 (post-public, outcome-weighted recommend) will
  correlate interviews with the cover letters that earned them; rows generated
  now without the write-back can't be backfilled, so the signal is captured
  during v1.0.6 while real outcome data accrues.
- No LLM call (the persist module stays deterministic), no `PROMPT_VERSION` bump,
  no new route, no new dependency, no migration (the column already exists).
  Covered by a unit test (no-clobber surgical write,
  `tests/test_persist_run.py`) and a route test (run-row populated end-to-end,
  `tests/test_cover_letter_detached.py`). The architecture pipeline + data-flow
  diagrams were synced to show the new write-back.

### Fixed — Step-4 / Résumé-templates copy now matches the real bundled set (`fix/step4-template-copy`, #8)

Walk finding #8 asked whether the Step-4 template-chooser copy ("Same content,
different typography and layout") still describes the bundled templates
accurately. **Verified: yes** — the four bundled templates genuinely differ in
typography *and* layout (Classic/Modern are sans-serif, Spacious/Tech serif;
Modern carries a blue header band; Tech uses float-based two-column item rows;
margins, line-heights, heading treatments and accents all vary), so that Step-4
line is left unchanged.

The verification surfaced a stale **count**, fixed here. Migration 0005 curated
the bundled set from 5 → 4 at v1.0.0 (dropped Compact, renamed Hybrid Tech →
Tech), but the Résumé-templates settings copy still claimed "Five bundled
ATS-safe templates ship with the app." → corrected to "Four". The
`docs/bundled_templates_LICENSE.md` inventory (which still listed the
nonexistent `compact.docx` / `hybrid_tech.docx` and omitted `tech.docx`) was
corrected to the curated four.

- Copy/doc only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new
  dependency, no DB change. The canonical count of 4 is already pinned at the
  data layer by `tests/test_bundled_templates.py`; the new UX regression
  `tests/ux/regression/test_20260611_step4_template_copy.py` guards the *copy*
  against drifting from the rendered bundled set.

### Fixed — Compose custom bullet order no longer reverts on reload for a no-recommendations experience (`fix/compose-order-no-recommendations`)

A saved custom Compose bullet order *visually reverted* after a Compose reload —
but only for an experience that had **no LLM recommendations**. The persisted
order was always intact (`composition_overrides.bullet_order` round-trips through
POST/GET `/composition`, and `generate()` honors it via `_stable_user_prefix`);
only the on-screen render regressed.

- **Root cause (render-only).** `_renderComposeCard` (`static/app.js`) routed a
  no-recommendations experience through `_dropoffPick`, which re-sorted the
  fallback bullets by **score** — discarding the saved order the GET had already
  applied (`get_application_composition` ranks bullets by `bullet_order` and
  stamps `in_custom_order`). The common path (recommendations present → bullets
  land in the `visible` set, preserving GET order) was unaffected.
- **Fix.** On the no-recommendations fallback path, when the experience has a
  saved order (`has_custom_order`) honor the GET-returned order (the
  `in_custom_order` bullets, already in saved sequence) instead of re-deriving a
  score sort. No backend change, no `PROMPT_VERSION` bump, no new dependency.
- Covered by a UX regression
  (`tests/ux/regression/test_20260611_compose_order_no_recommendations.py`) on a
  seeded no-recommendations experience; the companion
  `test_20260604_bullet_drag_reorder.py` continues to guard the common path.

### Added — add an alternative job title in Compose + pin it per-JD (`feat/compose-add-title`, #7)

In Step 3 (Compose) a user often realizes a *different framing* of a role fits
this JD. Until now they couldn't act on it in the wizard: the Compose titles
list was read-only, the only way to add a title was the separate Career-corpus
tab (which added it as a *non-eligible* alternate), and titles had **no** per-JD
selection at all — the generate LLM picked one by fit and the preview showed
official-or-first (walk finding #7).

- **Add a title, written into the corpus.** A "+ Add title" affordance on each
  Compose experience card writes a **sourced, immediately-eligible**
  `ExperienceTitle` (`source=user_added`, `truthful_enough_to_use=1`,
  `is_pending_review=0`) via the existing `POST /api/experiences/<id>/titles` —
  a first-class corpus item, **not** a context-only override. It appears at once
  as a selectable option for this résumé.
- **Pin which title this JD uses.** Each card's titles are now a radio group; the
  pick persists as `composition_overrides.pinned_title_ids`
  (`{experience_id: title_id}`), collected by the existing debounced composition
  autosave. Only an explicit pin is sent (mirrors `bullet_order`'s
  `data-custom-order`), so an untouched default never persists a pin or busts the
  analyze→generate cache.
- **Honored in both the preview and the generated download.** The live preview /
  corpus render (`build_json_resume_from_corpus`) resolves the title as
  **pin → official → first**; generate marks the chosen `<eligible_title
  pinned="true">` in the corpus block and a new `<corpus_mode>` rule requires the
  model to use it as that experience's `chosen_title_id` and heading (dates stay
  immutable). Because generate reads a **frozen** corpus snapshot, the
  composition save **re-syncs** `career_corpus[exp].eligible_titles` from the DB
  for pinned experiences, so a title added after analyze still reaches generate.
- `PROMPT_VERSION` → `2026-06-11.1` (the `<corpus_mode>` rule changed). Per-JD
  pin scope was a user-approved extension of the #7 row.
- Covered by route/unit tests (`tests/test_career_corpus_routes.py` add contract;
  `tests/test_application_routes.py` `TestCompositionTitlePin` persist/validate/
  re-sync; `tests/test_corpus_to_json_resume.py` `TestTitlePin`;
  `tests/test_corpus_mode_prompt.py` `TestTitlePinEmission` + the rule) and a UX
  regression (`tests/ux/regression/test_20260611_compose_add_title.py` — add a
  title, pin it, persist across a Compose reload). No new dependency.

### Added — prior applications resume from their furthest step + editable cards (`feat/prior-app-resume-robustness`, #4 + #24)

The v1.0.5 click-to-resume only offered "Resume in wizard" when a résumé had
been generated, so an application abandoned at analyze / clarify / compose was a
dead card. And prior-app cards never showed which job they were for — the
company was never captured and the proposal pill read an opaque "N pending"
(walk findings #4 + #24).

- **#4 — resume from the furthest step with data.** `_build_resume_state`
  (`app.py`) now classifies a `target_step` (1 analyze · 2 clarify · 3 compose ·
  6 download) from the rediscovered iter-0 context file — `llm_analysis`,
  `clarification_questions`/`clarifications`,
  `llm_recommendations`/`composition_overrides`, generated résumé — and ships the
  per-step payload. `resumeApplicationIntoWizard` (`static/app.js`) dispatches on
  it: Steps 1–3 rehydrate the analysis panel (and, for Step 2, the saved clarify
  Q&A) **without re-spending** `/api/clarify` or `/api/generate`; Step 6 is the
  unchanged generated-résumé path. The Resume button is now offered for every
  analyzed application, not only generated ones.
- **#24 — editable cards + legible pill.** Job title and company are now
  user-editable in the app-detail modal (save-on-blur via the new DB-only
  `PUT /api/applications/<id>/meta`, mirroring `/notes`), so a card can finally
  carry the job it's for (`Application.company` was never populated). The
  proposal pill reads **"N to review"** (was the opaque "N pending").
- Covered by route tests (`tests/test_application_routes.py` — `target_step`
  classification + `/meta`) and a UX regression
  (`tests/ux/regression/test_20260611_prior_app_resume_robustness.py` —
  analyze-only resume to Step 1; editable company + relabeled pill).

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — UI + a
deterministic DB-only route; no LLM call added).

### Fixed — "Continue to Clarify" no longer asks clarify/skip twice (`fix/clarify-double-question`, #6)

The analyze→clarify gate presented the clarify-vs-skip choice **twice**. The
analysis panel already shows it ("Continue to Clarify →" / "Skip to Compose →"),
but "Continue to Clarify" only navigated to Step 2 and showed the
`#clarifyStartRow` row — a second "Get clarifying questions / Skip" prompt for a
user who had already chosen to clarify. The onboarding walk (finding #6) flagged
this as feeling broken.

- **One action:** "Continue to Clarify →" now navigates to Step 2 **and** fetches
  the questions directly (new `continueToClarify()` wrapper). A pending indicator
  fills the panel while `/api/clarify` runs; the row is restored on failure so
  the user can retry. An idempotency guard skips re-fetching when the current
  analysis already produced questions (back-nav / re-click never re-spends the
  LLM call).
- **Untouched paths:** a direct rail click / back-nav into Step 2 still shows the
  `#clarifyStartRow` row as its single, legitimate prompt; the post-question
  `Skip` and `Submit answers, continue →` controls are unchanged. The KW4
  `merge:true` / `merge:false` answer semantics are preserved byte-for-byte
  (this fix only changes how clarify is *entered*).
- Regression-tested in the UX tier
  (`tests/ux/regression/test_20260611_clarify_no_double_prompt.py`): the CTA
  renders questions with no second click and `#clarifyStartRow` is hidden.

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — front-end flow
only; no LLM route or template touched).

### Fixed — iterate-round clarify answers no longer drop analyze-round answers (`fix/clarify-generates-bullets`, KW4)

`/api/answer-clarifications` (`submit_clarifications`) did a whole-map replace
of `context["clarifications"]`. The iteration interview submits **only** its own
textareas (`_collectIterateClarifyAnswers`), so a 2nd-round submit wiped the
analyze-round answers from the new context file — and `generate()` at iter≥1
lost them as first-person ground truth (the JS comment claimed "merges by id";
the route did not). Surfaced 2026-06-10 while building
`feat/outcome-capture-complete`; this is the mechanism behind the KW4 report
that "a later clarify round adds nothing".

- **Merge by id (default):** the route now merges answers into the existing map
  (`merge` defaults to `True`), so a later round preserves earlier answers. The
  deliberate skip-clear path passes `merge:false` to replace/clear, and the
  three JS call sites (`submitClarifications`,
  `submitIterateClarificationsAndGenerate`, `skipClarifications`) declare their
  merge intent explicitly. Whitespace-only answers are dropped and cannot
  un-answer a prior key — use `merge:false` to clear.
- **Candidate-memory mirror unaffected** — the additive DB upsert is keyed by
  question and persisted independently of the context-map merge.
- Regression-tested across two clarify rounds (`tests/test_app_clarify.py`).

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — only the data
`generate()` reads is corrected, not the prompt template).

### Added — outcome capture completed + candidate memory goes live (`feat/outcome-capture-complete`, B.8 Part 1 + KW7)

The Sprint 6.0 kickoff walk found the Applications block showing "no
applications" after a completed tailor+download, and candidate memory empty
after clarify+interview (KW7). Diagnosis against the walkthrough evidence:
the `Application` row **was** created (at analyze) but the UI never
re-rendered the block after user-select; worse, nothing in the UI could ever
set `status='submitted'`, and the outcome buttons render only on submitted
cards — so the whole outcome funnel was unreachable. Candidate memory was
designed-but-unwired: the table, read route, panel, and promote path all
existed, but no code wrote `clarification` rows from the wizard.

- **KW7 fix (UI sync):** `refreshApplications()` now fires when analyze
  creates the row and when generation updates it — the block tracks the
  wizard instead of its pre-analyze snapshot.
- **Outcome funnel entry (B.8 Part 1):** draft cards gain a **Mark
  submitted** action, and Step 6 surfaces a "Submitted this application?"
  nudge after a successful download — the moment the user takes the file to
  go apply. Outcome buttons (interview / rejection / withdrew) are unchanged
  and now reachable. **Data-model decision (user-approved 2026-06-10): lean
  single-status, `interview` is terminal** — the product's signal is "this
  résumé got a callback", not job-hunt bookkeeping past that point. No
  schema change; the v2 `ApplicationOutcome` event table remains open.
- **Queryable:** `GET /api/users/<u>/applications` accepts a validated
  `?status=` filter (single or comma-separated) — the programmatic query
  surface for the B.8 Part 2 learning layer — and the Prior-applications
  panel gains a status filter select driving it.
- **Candidate memory write path:** `/api/answer-clarifications` now mirrors
  answered Q&A into the `clarification` table (additive upsert keyed on
  candidate + application + normalized question; promoted rows never
  clobbered; legacy file-only contexts unaffected; best-effort — a memory
  failure never fails the submit). The memory panel populates live after
  clarify/interview answers, and the existing promote-to-bullet path is now
  reachable for wizard-sourced answers. LLM `context_probe` questions file
  under `experience_probe` (the DB kind enum predates them); `target_gap`
  keeps the provenance.

No new dependency. No prompt change (`PROMPT_VERSION` unchanged).

### Fixed — generate() can no longer silently alter or duplicate job dates (`fix/generate-date-grounding`, KW6)

The Sprint 6.0 kickoff walk caught the iteration regenerate "reconciling"
employment dates: it reordered experiences by JD relevance and rewrote one
role's range onto its neighbor (two titles sharing `2016 – 2018` while
`2012 – 2016` vanished), though the corpus was correct. Root cause: the
corpus-mode prompt contract made *bullets* immutable but never mentioned
*dates*, and every deterministic check scanned bullet lines only — heading
date ranges were ungoverned on both sides.

- **Prompt** (`analyzer.py`): new SYSTEM_PROMPT ALWAYS/NEVER rule (dates are
  immutable facts; reordering never rewrites them), the `<corpus_mode>`
  contract now names the `dates` attribute immutable ground truth, and the
  GROUNDING CHECK gains an OK / NOT-OK worked date pair.
  **`PROMPT_VERSION` `2026-06-01.4` → `2026-06-10.1`** (same commit). Smoke
  eval: no grounding regression (mean 4.70, all fixtures pass; see
  `evals/TUNING_LOG.md` 2026-06-10 entry).
- **Guard** (`hardening.compute_date_grounding`, deterministic, warn-only):
  heading date ranges in the generated experience section must be a
  sub-multiset of the corpus's true ranges — catches both alteration and
  duplication. Both generate routes surface flags as plain-language
  `proofread_notes` warnings (no frontend change needed) plus a structured
  `date_grounding` response field; the LLM output itself is never mutated and
  generation is never blocked. Validated against the real walkthrough chain:
  the corrupted iteration draft flags, the clean fresh draft passes.

No new dependency.

### Docs — Sprint 6.0 kickoff-walk harvest recorded (`docs/sprint6-walkthrough-findings`)

The first v1.0.6 kickoff walkthrough completed end-to-end (sprint-1 blockers
cleared the hard stops) and produced **11 findings (KW1–KW13)**, now recorded in
`docs/dev/RELEASE_ARC.md` §Phase 4.5 under Sprint 6.0 and triaged into the
existing 6.x buckets: three correctness defects (KW6 generate-date integrity,
KW7 applications/memory not updating → B.8 gate, KW4 clarify-no-bullets) join
Sprint 6.1 as new branches; KW2 bulk accept-all-pending joins 6.3; KW1 confirms
the 6.4 smart-landing; KW3/KW9/KW10 fully spec the 6.5 help primitive
(first-view modal + persistent (i)-circle) and the new-user first-run modal
sequence; KW13 panel redesign joins 6.2. Docs only — no code change.

### Fixed — onboarding E2E-walkthrough blockers, sprint 1 (`fix/onboarding-e2e-blockers`)

Five first-run onboarding issues surfaced by the end-to-end walkthrough:

- **Résumé ingest silently did nothing (the critical one).** A table/column-laid-out
  `.docx` parsed to empty text because `parser._parse_docx` read only body
  paragraphs, never table cells — so extraction got nothing and zero experiences
  landed. The ingest route nonetheless returned `201` with the error buried in the
  body, and the uploader showed a green "ready" toast over an empty corpus and never
  refreshed the list in place. Now: the parser walks the document in order and reads
  table cells (recursing into nested tables, deduping merged cells); the route
  returns `422` when a parse/extract failure lands nothing; and the uploader
  refreshes the corpus in place on success and shows an honest "No experiences found"
  warning (not a success toast) on a zero result.
- **User-selection box collapsed on an accidental header click**, stranding
  first-time users with the dropdown hidden. It is now locked open
  (`.not-collapsible`, no chevron/pointer) until a user is selected.
- **"New user" button was a confusing toggle.** It now reveals the form (not
  toggles), hides itself, and focuses the username field; a **Cancel** button
  restores it.
- **Website/LinkedIn URL boxes were ambiguous and intolerant of format.** Added a
  tolerant client-side format checker (normalizes a bare `linkedin.com/in/you` to
  `https://`, flags genuine non-URLs), clearer placeholders, and a matching tolerant
  `validate_config` server-side (accepts bare dotted hosts; still rejects `not-a-url`).
- **Wizard back-navigation** is acknowledged as missing but **deferred** to the
  monolith→blueprints split (RELEASE_ARC Phase 4.8); no behavior change this branch.

No `PROMPT_VERSION` change and no new dependency.

### Fixed — profile URLs without a scheme no longer silently fail to fetch (`fix/normalize-url-scheme`)

A site address pasted without `http://`/`https://` (e.g. `github.com/you`) made
`requests.get` raise `MissingSchema`, which `scraper.fetch_url_content` caught
and swallowed as an empty result — the URL was silently dropped from the LLM
profile context with no user-visible error. The LinkedIn/Website fields are
`type="url"` (browser-enforced scheme), but the Portfolio URLs textarea has no
such guard, so bare hosts slipped through. `scraper._ensure_scheme()` now
normalizes at the fetch boundary: a bare host gets `https://` prepended; an
explicit scheme (`http://`, `https://`, …) is left untouched. One fix covers
all three URL sources since they all flow through `fetch_url_content`. No
`PROMPT_VERSION` change and no new dependency.

## [1.0.5] — 2026-06-07

The UI/UX redesign + the diagnostics/tuning console — establishes the design
system. **Local tag** (the project stays local-only until the user-owned v1.1.0
public release). Highlights: WYSIWYG (live preview = downloaded résumé), the
Step 6 (Output) redesign, cover letters in `.docx` / `.pdf` / `.md`,
prior-application click-to-resume, user-driven Compose bullet ordering, a
Playwright UX regression suite, the template-pagination fix across all four
bundled templates, the deterministic L0 grounding metric, and the tabbed
diagnostics + tuning + annotation console — including the browser-driven
"finish the faceplate" interactive tuning loop and the standalone, LLM-free
corpus-seed export. **No `PROMPT_VERSION` change across the stream** (no
persona-constant edit landed) and **no new runtime dependency**. Deferred to
later releases by design: the calibrated grounding layers (B, pre-v1.1.0), the
no-recommendations Compose-render order edge case, and the R1-Phase-2
architecture-doc debt.

### Added — standalone one-click corpus-seed export (`feat/seed-export-button`)

Producing a corpus `seed.json` is now a one-click, **LLM-free** action in the browser.
Previously the only in-browser trigger was bundled inside the **paid** Annotate-tab
bootstrap (`POST /api/annotation/bootstrap`, ~70s/JD of Sonnet/Haiku spend); the only
no-cost path was the `python -m scripts.export_corpus_seed --user <name>` CLI. This adds
a dedicated no-cost surface. No `PROMPT_VERSION` bump (no prompt touched) and no new
dependency.

- **`POST /api/annotation/seed/export`** (`app.py`, localhost-only, synchronous JSON —
  no SSE) — reads the live DB via `scripts.export_corpus_seed.export_seed` (read-only, no
  model calls) and writes `evals/fixtures/real/<slug>/seed.json` (the source the eval
  runner's `--seed` path and the grounding backfill score against). Mirrors the score
  route's guard structure: `_is_localhost_request()` + the security trio
  (`_safe_username()` + `secure_filename()` + `_within(seed_path, ANNOTATION_ROOT)`).
  Unknown user → 400; a config-only user with no provisioned corpus → 409 (same
  needs-onboarding shape as `/api/analyze`). Default slug `<user>-bootstrap` so an
  exported seed lands where a later bootstrap / `runner.py --seed` already looks.
- **Annotate-tab "Export seed (no LLM)" button** (`dashboard/templates/dashboard.html`) —
  sits in the bootstrap section's actions row next to the paid "Run bootstrap"; reuses the
  same candidate-username / fixture-slug inputs and reports the written path + corpus
  counts. A plain fetch + status line (no SSE) since the export is fast and synchronous.
- **`_write_seed_json(fixture_dir, seed)`** (`app.py`) — factored the seed.json dump out
  of the bootstrap route so the bootstrap and standalone export share one canonical writer
  (no duplicated `json.dumps` shape). Bootstrap behavior is byte-identical.

### Docs — tuning-loop discoverability (`docs/tuning-loop-discoverability`)

Step 4 (docs only) closes the "finish the diagnostics faceplate" arc: every durable
doc and the in-app entry points now point at the now-interactive `/_dashboard`
console instead of the pre-arc read-only world. No code, no `PROMPT_VERSION` bump,
no new dependency.

- **`evals/README.md`** — new "The in-browser tuning console (`/_dashboard`)" section
  walks the four shipped surfaces as one browser-driven loop (produce → annotate →
  grounding-score → run eval → A/B → read deltas), ending at the irreversible manual
  **promote**; it is the dev-doc home for the console walkthrough.
- **`docs/walkthrough.md`** — a short "See also" flag + link telling
  users/maintainers the local diagnostics & tuning console exists and that the LLM
  prompts can be tuned there (content lives in `evals/README.md`, not embedded here).
- **`docs/dev/GROUNDING_METRIC.md`** — the deferred-calibration ("B") note now records
  that the label-*producing* loop is browser-driven (no longer CLI-only); the
  calibration itself stays the open B work.
- **`docs/dev/RELEASE_ARC.md` / `RELEASE_CHECKLIST.md`** — merge hashes backfilled
  (`feat/run-eval-from-console` `3a91bea`, `feat/tuning-tab-ab` `812e6bb`/`5f708f7`);
  the arc's checklist item is checked complete; the standalone one-click corpus-seed
  export (`feat/seed-export-button`) is tracked as the next small `feat/` branch.
- **`templates/index.html`** — the Diagnostics modal, the Diagnostics-pill tooltip,
  and the Settings-drawer line are refreshed from "Read-only telemetry" to advertise
  the interactive eval/tuning console (copy only — no behavior/layout/route change).

### Added — in-browser prompt A/B on the Tuning tab (`feat/tuning-tab-ab`)

Step 3 of the "finish the diagnostics faceplate" arc replaces the Tuning tab's
read-only stub with a real candidate-vs-baseline A/B: pick an
`analyzer._BASE_SYSTEM_PROMPTS` constant, edit its text, and run baseline +
candidate evals in the browser, then read the per-(fixture, rubric) delta. The
irreversible **promote** (edit the constant + bump `PROMPT_VERSION` + log
`TUNING_LOG.md`) stays a human/agent step — **no route edits `analyzer.py`**. No
`PROMPT_VERSION` bump (no prompt template changed) and no new dependency.

- **`POST /api/tune/run`** (`app.py`, localhost-only, SSE) — drives
  `evals.runner.run_suite` **twice** in one worker (baseline with no overrides,
  then candidate with the pasted override map), then computes the delta with the
  LLM-free `evals.tune` helpers (`load_scores` + `build_delta_table` +
  `format_delta_table`) and streams it. The candidate run self-stamps
  `prompt_version=candidate:<hash>` via `analyzer.prompt_overrides()`, so it never
  pollutes score-over-time. Mirrors `/api/eval/run`'s input contract, including the
  optional corpus-seed mode (`slug` + `username` → `evals/fixtures/real/<slug>/seed.json`,
  reusing `_safe_username` + `_within(seed, ANNOTATION_ROOT)` + `secure_filename`).
  All eager validation — bad suite, empty/missing override, an unknown prompt-constant
  name (via the canonical `prompt_overrides()` validator), unknown user, missing seed —
  returns a JSON 4xx **before any paid call** (load-bearing: baseline runs first, so a
  doomed candidate key must be caught up front).
- **Tuning-tab UI** (`dashboard/templates/dashboard.html`) — a constant picker
  (with "Load current text" to prefill the baseline), a candidate textarea,
  suite/subset/grounding controls + an optional real-seed disclosure, a 2×-cost
  `confirm()` gate (~$0.20 smoke / ~$0.60 full), phased progress, and the rendered
  delta table + a manual-promote reminder. The shared SSE streamer is generalized to
  `window.sartorEval.stream(url, params, onEvent)` (the eval-run control now rides
  it too). The `dashboard/routes.py` index passes `tune_prompts` (read-only use of
  `analyzer._BASE_SYSTEM_PROMPTS`) for the picker + prefill.

### Added — run an eval from the console; `run_suite()` core extracted (`feat/run-eval-from-console`)

Step 2 of the "finish the diagnostics faceplate" arc closes the mandatory CLI hop
in the tuning loop: you can now run an eval **from the browser** instead of
dropping to a terminal, and the collate step's paste-this `run_command` dead-end
becomes a real button. No `PROMPT_VERSION` bump (no prompt template changed) and
no new dependency.

- **`evals.runner.run_suite(...)`** — the eval orchestration is extracted from
  `runner.main()` into an importable core taking structured args (`suite`,
  `subset`, `fixture_name`, `seed_data`, `prompt_overrides_map`,
  `grounding_signals`, `out_dir`, `client`) plus an optional `progress` sartor,
  returning an `EvalRunResult`. `main()` is now a thin argparse wrapper. The
  no-flag default path is **byte-identical** (empty overrides are a no-op,
  `progress=None` makes every emit a no-op, the analyze→generate cache and the
  result-record bytes are unchanged) — mirrors how `evals/bootstrap.py` already
  splits `main()` from `run_pipeline_over_jd_texts`.
- **`POST /api/eval/run`** (`app.py`, localhost-only, SSE) — drives `run_suite`
  in a worker thread (the `annotation_bootstrap_stream` threading/queue/`_sse`
  pattern) and streams `start` / `fixture_start` / `analyzing` / `clarifying` /
  `generating` / `rubric_done` / `fixture_done` / `done` / `error`. Two modes: the
  Quality-tab run (synthetic/anchor, no seed) and the Annotate-tab "Run this
  fixture" run (`--suite real --seed <slug>/seed.json`, the in-browser collate
  command). Guarded by `_is_localhost_request()` + `secure_filename` +
  `_within(seed, ANNOTATION_ROOT)` + `_safe_username`; all validation returns a
  JSON 4xx before any paid call.
- **Console UI** (`dashboard/templates/dashboard.html`) — a "Run eval" control on
  the **Quality** tab (suite/subset/grounding, a cost-band caption, a `confirm()`
  consent gate showing the ~$0.10 smoke / ~$0.30 full estimate, reload on done);
  on the **Annotate** tab the collate result now shows the CLI command **and** a
  "Run this fixture" button. Promote stays the agent's job — no route edits
  `analyzer.py`.

### Added — run the grounding scorers from the console; bootstraps capture a seed (`feat/grounding-scorers-in-console`)

Found during a v1.0.5 walkthrough: a dev-user installed the offline grounding
scorers (`pip install -e '.[eval-grounding]'`, DeBERTa NLI + MiniCheck-FT5) and
had **no interface to use them** — the only trigger was the CLI
`--grounding-signals` flag, and the browser bootstrap hard-coded `grounding_fn=None`.
Step 1 of the "finish the diagnostics faceplate" arc makes the scorers reachable
from the `/_dashboard` **Annotate** tab, keeping them eval-time (the L1/L2
hot-path discipline in `docs/dev/GROUNDING_METRIC.md` is unchanged):

- **Opt-in on the browser bootstrap** (`app.py`, `/api/annotation/bootstrap`) — a
  "Run grounding scorers" checkbox passes `grounding_signals: true`, which wires
  `evals.grounding_signals.run_grounding_signals` into `build_bootstrap_document`.
  The scorers are pure-Python to import but lazy-load heavy deps, so a missing
  `[eval-grounding]` extra (or any scoring failure) **degrades to an un-scored
  bootstrap + a streamed `warning`**, never a 500 — the paid pipeline output is
  always preserved.
- **"Score grounding" backfill** (`/api/annotation/fixture/<user>/<slug>/score`,
  SSE) — scores an existing bootstrap's deduped bullet representatives **without
  re-running the paid pipeline**, writes them under `grounding_signals`, and
  patches any in-progress `annotations.json` score fields **by `cluster_index`
  without touching human verdicts/notes**. The annotation editor's MiniCheck/NLI
  pre-scores now light up.
- **Bootstraps capture a `seed.json`** — the browser bootstrap now snapshots the
  entire approved corpus via `scripts.export_corpus_seed.export_seed` (non-fatal
  if it can't). This is the durable source the backfill scores against (imported
  via `evals.seed_import.seeded_session`, faithful even if the live corpus is
  later edited) and the file the collate step's `--seed` run-command already
  assumed but the in-browser path never produced.

No new dependency; no `PROMPT_VERSION` bump (deterministic, no prompt change).

### Added — auto-open the default browser on launch (`feat/auto-open-browser`)

`python app.py` (and the `sartor` console script) now opens
`http://localhost:5000` in the user's default browser once the server is
listening, so they land straight on the app instead of copying the URL by hand.
A short daemon `Timer` defers the open until the socket is up; under Flask's
reloader (`FLASK_DEBUG=1`, the default) the open fires only in the serving child
(`WERKZEUG_RUN_MAIN=true`) so there's no double tab; and the call is wrapped so a
missing browser can never crash startup. Set `SARTOR_NO_BROWSER=1` to skip it
on headless / remote / CI runs.

### Changed — retire the broken "legacy import" onboarding; the corpus self-provisions (`fix/retire-legacy-import-onboarding`)

Found during the v1.0.1 → v1.0.5 walkthrough: the **Import into corpus** modal
read like pre-migration cruft, its button `POST`ed to a route that no longer
exists (`/api/users/<u>/import-legacy` → HTTP 404), and there was **no working
way to populate the corpus**. Root cause: `create_user` writes a config but
never a `Candidate` DB row, so *every* user — not just pre-migration ones — landed
in the `needs_onboarding` state whose only UI exit was that broken modal.

The onboarding gate is removed; the candidate row is now provisioned on demand:

- **Self-provisioning** — a new `_get_or_provision_candidate()` helper (`app.py`)
  creates the `Candidate` row from the user's config on the first corpus *write*
  (résumé ingest, add-experience, add-summary, persona upload, analyze), reusing
  the idempotent `import_candidate_from_config`. Both onboarding paths are open to
  a brand-new user immediately: **import a résumé** (AI extraction) **or** add
  experiences/bullets by hand — and you can mix them. The five write routes that
  returned `409 + needs_onboarding` (and summaries' `404`) now just succeed.
- **Frontend** (`static/app.js`, `templates/index.html`) — the onboarding modal,
  the `import-legacy` fetch, `openOnboardingModal` / `_renderNeedsOnboarding`, and
  the "Legacy import" error labels are deleted. The Career corpus tab always shows
  its toolbar (import **and** add-experience) with a unified empty-state hint; the
  read-only tabs (Memory / Applications / Templates) show a non-modal "Go to
  Career corpus" CTA via `_renderCorpusEmptyCTA`. All "database migration" /
  "run onboarding" / "Select a user above" copy is rewritten.
- **Tab rename** — the first tab **Application → Tailor** everywhere (label, ids
  `topTabApplication`/`tab-application` → `topTabTailor`/`tab-tailor`, the
  `switchTopTab('tailor')` handler, and `ui_pages/selectors.py` `TopTabs.TAILOR`).
- **Module rename** — `onboarding/import_legacy.py` → `onboarding/corpus_import.py`
  (and its test file) so no "legacy" name remains in the runtime path; the CLI is
  now `python -m onboarding.corpus_import`. Behavior unchanged.
- **Tests** — the four write-route "missing candidate → 4xx" tests now assert
  auto-provision success and that the row was created; their fixtures patch
  `corpus_import.CONFIGS_DIR`. The new-user UX regression asserts the working
  "+ Import résumé" affordance instead of the removed CTA.

No prompt / `PROMPT_VERSION` change, no new dependency. (Shipped CHANGELOG /
architecture / benchmark mentions of the old file-based "legacy" pipeline are
left as accurate history.)

### Changed — needs-onboarding GET reads return `200`, not `409` (`refactor/needs-onboarding-200-on-reads`, v1.0.5)

Found during v1.0.5 verification: creating the first user and clicking across
the tabs logged a cascade of `409 (CONFLICT)` console errors — one per passive
tab load (`GET …/personas`, `…/applications`, `…/clarifications`,
`…/experiences`). The read endpoints were signalling "no corpus row yet" with a
`409`, which the browser logs red regardless of how the JS handled it (every
handler already rendered the import CTA — except the persona template picker,
which showed a misleading "Failed to load templates").

A `409 Conflict` on a **read** is a misuse: asking for a not-yet-onboarded
user's list is an unmet precondition, not a state conflict. The contract now
splits by method — **reads → `200`, writes → `409`**:

- **`GET` read endpoints** (`…/personas`, `…/applications`, `…/clarifications`,
  `…/experiences`, `…/duplicates`) return `200` with an empty, success-shaped
  body plus `needs_onboarding: true`. The console stays clean and the import CTA
  still renders; a naive consumer just sees empty lists. (Mirrors the
  pre-existing `pending-counts` / `summaries` `200`-empty precedent.)
- **`POST` write endpoints** (analyze, corpus ingest, experience/persona
  create, persona preview) keep `409 + needs_onboarding` — a write precondition
  failure reasonably *is* a conflict, and they never fire on a passive load. The
  live-preview `GET` also keeps `409` (it serves an HTML iframe, not a list, and
  isn't fired pre-onboarding).
- **Frontend** (`static/app.js`): `_needsOnboarding()` is now status-agnostic
  (keys off the body flag), so the one helper covers both the `200` reads and
  the `409` writes; the six read handlers branch on the flag before treating the
  body as a collection, and two secondary `/experiences` consumers are
  `Array.isArray`-guarded against the discriminated shape.
- **Tests**: the five GET-read route tests flip `409 → 200`; a new dated UX
  regression (`tests/ux/regression/test_20260606_new_user_no_4xx.py`) seeds a
  config-only user, sweeps all four tabs, and asserts **zero** `4xx` on any
  `/api/users/<u>/…` call plus a visible import CTA. Two tab selectors
  (`TopTabs.PERSONAS` / `TopTabs.MEMORY`) + the shared CTA name were added to the
  `ui_pages` registry.

No prompt / `PROMPT_VERSION` change, no new dependency.

### Added — annotation tab + browser bootstrap wrapper: the console's first read-write surface (`feat/annotation-tab`, v1.0.5)

The last branch of the v1.0.5 stream puts the v1.0.4 eval tuning loop on the
design system: a fifth `/_dashboard` tab — **Annotate** — that produces and
labels real annotation material in-browser, ending the need to hand-edit JSON.
It reads/writes the durable Phase 3 `annotations.json` contract **verbatim**
(reusing `evals.annotation` — schema not forked), so the labels it produces are
exactly what the deferred grounding calibration needs. **No prompt /
`PROMPT_VERSION` change, no new dependency, no new LLM-call shape** (the wrapper
reuses the existing `analyze`/`clarify`/`generate` primitives unchanged).

- **The console's first READ-WRITE routes** — added to `app.py` (not the
  read-only dashboard blueprint, which stays read-only). Every route is
  **localhost-only** and gated by the security pattern: `_safe_username()` (real
  candidate) + `secure_filename(slug)` + `_within(path, ANNOTATION_ROOT)`, writing
  ONLY under `evals/fixtures/real/` (gitignored, PII-bearing):
  - `GET /api/annotation/fixtures` — list bootstrap fixtures.
  - `GET`·`POST /api/annotation/fixture/<user>/<slug>` — load the working doc
    (existing `annotations.json` or a fresh `build_annotation_template`) / save it.
    Save runs the **fail-closed `validate_annotations`** (same contract the CLI
    uses), so the on-disk file is always collation-ready.
  - `POST /api/annotation/fixture/<user>/<slug>/collate` — deterministic
    `collate_expected` + `build_improvement_brief` → `expected.json` +
    `improvement_brief.md` + an anchor `jd.txt` (runnable by `runner.py --suite real`).
  - `POST /api/annotation/bootstrap` — **browser bootstrap wrapper (SSE)**: drives
    `analyze → clarify → generate` over N pasted JDs against the live corpus
    (reusing the `/api/analyze/stream` streaming pattern + the deterministic
    `build_bootstrap_document` dedup), streaming per-JD progress, then writes
    `bootstrap.json` + the pasted JDs. Paid (Sonnet/Haiku) + slow (~70s/JD).
- **`evals/bootstrap.py`** — `run_pipeline_over_jds` refactored to delegate to a
  new `run_pipeline_over_jd_texts` (in-memory `(name, text)` JD pairs + an optional
  `progress` sartor), so the browser wrapper needs no JD temp files. CLI path is
  behavior-preserving.
- **Annotate tab UI** (`dashboard/templates/dashboard.html`) on the cb-* tokens:
  bootstrap wrapper sub-panel → fixture picker → per-cluster verdict editor
  (`keep`/`fix`/`omit`/`fabricated`, `failed_rules` constrained to the rubric
  vocabulary, `should_omit`, conditional `honest_rewrite`/`forbidden_pattern`) +
  clarification ratings; Save + Collate. Vanilla JS; fetch-streamed SSE for the
  wrapper; validation errors surfaced inline (no `console.error`).
- **Tests** — `tests/test_annotation_routes.py` (fail-closed save, traversal-slug
  containment, localhost guard, collate shape, bootstrap SSE with the LLM pipeline
  stubbed). `tests/ux/flows/test_annotation_tab.py` drives the tab in headless
  Chromium against the unconditional console-error sentinel (seed bootstrap → pick
  → fill verdicts → Save → Collate). `Dashboard` selectors + `DashboardConsolePage`
  POM extended.

### Changed — diagnostics console redesign: tabbed observability on the cb-* design system (`feat/diagnostics-console-redesign`, v1.0.5)

`/_dashboard` moves from a single long-scroll page with its own hardcoded palette
to a **tabbed diagnostics + tuning console on the cb-* design system**. Read-only
throughout — **no new Flask route, no write affordances** (the localhost
host-header guard is preserved verbatim); **no `PROMPT_VERSION` bump, no new
dependency, no LLM call.** Chart.js still loads from CDN; tabs + drawer are vanilla
JS.

- **Four tabs, each a bento of summary tiles → shared right-hand drawer.**
  Pipeline · Quality · Groundedness · Tuning. A tile shows a headline stat;
  clicking it opens one shared drawer with the full chart/table + detail. Charts
  **lazy-init on drawer-open** (never into a hidden/zero-size canvas). Every tile's
  summary *and* detail are server-rendered, so the surface degrades gracefully
  with JS off (panes stack, details show inline).
- **Groundedness tab (the marquee surface)** — designed *around* the 2026-06-06
  metric contract, not retrofitted. New `dashboard/routes.py` helpers
  `_groundedness_trend` (L0 `groundedness.score` 0–5 over time by `prompt_version`,
  **deduped by `run_id`** so a run's value isn't plotted once per rubric) and
  `_latest_groundedness_detail` (the `fabricated_specifics` drill-down:
  `flagged_samples` + `per_bullet` as the actionable evidence).
- **Tier-0 observability over data we already log** (no new data emitted):
  `_run_trace` (per-`run_id` span waterfall from `call` + `latency_ms`),
  `_reliability` (error + `max_tokens`-truncation rates, split by call kind),
  `_cost_by_call_kind` (per-stage cost rollup), and `_baseline_health` /
  `_load_baseline` (health-vs-baseline drift badges: regressed Δ<−0.5 = the
  merge-block gate, watch Δ<−0.3, else ok — read from the in-repo
  `evals/results/baseline_v1.json`).
- **Tuning tab is a read-only scaffold** — documents the `analyzer.prompt_overrides()`
  A/B primitive + links to `/prompt-tune`, `/tune-from-annotations`, and
  `evals/TUNING_LOG.md`. No forms that POST; a banner states write affordances land
  in a later, sign-off-gated branch.
- **Tests** — `tests/test_dashboard_routes.py` gains pure-helper unit coverage for
  every new aggregator (dedup-by-run_id, empty/missing-block paths, verdict bands).
  `tests/ux/flows/test_dashboard_console.py` drives the tabs + drawer in headless
  Chromium against the unconditional console-error sentinel (seeds telemetry by
  monkeypatching the blueprint's `EVAL_RESULTS_DIR` / `LLM_LOG`); a
  `DashboardConsolePage` POM joins `ui_pages/`.

### Added — L0 grounding metric: deterministic fabricated-specifics rate + groundedness composite (`eval/grounding-metric-l0`, v1.0.5)

The first slice of the grounding/hallucination metric, defined *before* the
diagnostics console is redesigned around it ("data model before the view"). This
is the **deterministic, label-free, hot-path-safe** layer (L0); the calibrated
model-based layers are deferred to pre-v1.1.0 because no labeled data exists yet
(`evals/fixtures/real/` is empty). **Deterministic only**: no `analyzer.py`/prompt
edits, no `PROMPT_VERSION` bump, no new dependency, no LLM call.

- **`hardening.py`** — new `compute_fabricated_specifics(generated_text, source_texts)`:
  a typed, severity-weighted successor to `compute_grounding_overlap`'s lossy
  `missing_samples` n-gram heuristic. Per bullet it extracts the verifiable
  *specifics* (numbers / % / $ / years / durations / named-entity & tool tokens)
  and checks each for membership in the candidate's ground-truth source union
  **with tolerance**: numeric formatting variants (`~30` / `30` / `30+`) and light
  rounding (`$2.4M ≈ $2,400,000`) read as grounded; a different magnitude
  (`~30 → 100+`) is flagged; entity tokens are alias-normalized (`k8s ≡ kubernetes`)
  first. A fabricated number outweighs a fabricated entity in the rate.
- **`hardening.py`** — new `assemble_source_union(context_set)` factored out of
  `compute_iteration_signals` (behavior-preserving): the single definition of the
  dynamic ground-truth union (primary résumé + supplementals + clarification
  answers), now shared by the iteration clarifier and the L0 check so the two can
  never score against divergent source sets.
- **`evals/runner.py`** — `_post_generation_metrics` now rides `fabricated_specifics`
  (L0 detail) and a single reportable `groundedness` composite along on **every**
  eval record (nested in `deterministic_metrics`, so attributable by
  `prompt_version` on the dashboard's score-over-time chart). The composite is
  **L0-only by default**; it enriches in place to L0+L1+L2 (NLI entailment +
  MiniCheck) only when `--grounding-signals` produced real scores. The existing
  `grounding_overlap` source set is left untouched (L0 scores against the wider
  union via a separate `source_union` arg), so existing baselines are unperturbed.
  L1/L2 behavior is read, never re-tuned.
- **Precision caveat (honest by design):** L0 is high-precision on genuinely-novel
  specifics but **will false-positive on paraphrase / implication** (source
  "managed a small team" → output "led a 4-person team" flags "4"). It is a
  **flag-for-review** signal, **not a gate**; tolerance bands are deliberately
  conservative and its precision/recall is **unproven until calibration against
  `annotations.json`** (deferred-B). See `docs/dev/GROUNDING_METRIC.md` and the
  `evals/TUNING_LOG.md` note.
- **Tests** — `tests/test_hardening.py::TestFabricatedSpecifics` (exact match → 0;
  novel number → flagged; within/out-of tolerance; `k8s`≡`Kubernetes` aliasing;
  embedded-digit non-leak; severity weighting) + `TestAssembleSourceUnion`;
  `tests/test_eval_runner.py::TestGroundednessComposite` (L0-only default +
  graceful L1/L2 enrichment). Deterministic — default `pytest`, no LLM/Chromium.

### Fixed — template pagination: blank pages + paged.js console error (`feat/template-pagination`, v1.0.5)

Blank/short pages in the **Modern**, **Spacious**, and **Tech** bundled
templates are gone, and the long-standing cosmetic paged.js console error is
fixed at the source. **Rendering-only**: no `analyzer.py`/prompt edits, no
`PROMPT_VERSION` bump, no new dependency.

- **`personas/bundled/{modern,spacious,tech}.css`** — dropped
  `section { page-break-inside: avoid; }` (present in both the base rule and the
  `@media print` block), keeping the correct per-entry
  `article { page-break-inside: avoid }`. Telling paged.js never to break inside
  a *whole section* meant any Experience section taller than the space left on
  the page got shoved wholesale onto the next page, leaving a blank/short page.
  This matches **Classic**'s proven break model (which never had the section
  rule); also added Classic's `h2 { page-break-after: avoid }` so a section
  heading is never orphaned at the foot of a page.
- **`app.py`** (`_PAGED_PREVIEW_INJECTION`) — the preview iframe now drives
  paged.js **manually** (`window.PagedConfig = { auto: false }` +
  `new Paged.Previewer().preview()` inside `try/catch` + `.catch()`). The
  bundled polyfill's auto-run `await`s `preview()` with no `.catch()`, so a
  sparse-content layout throw escaped as the uncaught
  *"getBoundingClientRect of null"* console noise; driving it ourselves contains
  it. The `pagedjs_rendered` page-count `postMessage` contract is preserved.
- **`tests/ux/`** — new regression test
  `regression/test_20260604_template_pagination.py` renders a deliberately
  multi-page résumé through all four bundled templates via the real preview
  route and asserts every `.pagedjs_page` carries content (no blank page) with a
  clean console. The `getBoundingClientRect` **allowlist in
  `tests/ux/conftest.py` is removed** — the sentinel is now unconditional, so any
  paged.js console regression fails the suite.

### Added — Playwright UX regression suite + shared `ui_pages` driver (`feat/playwright-ux-suite`, v1.0.5)

Browser-level UI regression coverage so the 2026-05-26 punch-list bugs — which
lived in JS render paths the `pytest` unit suite can't reach — can't return.
**Test-only** change: no `analyzer.py`/prompt edits, no `PROMPT_VERSION` bump,
no new dependency (Playwright was already a dependency).

- **`ui_pages/`** (new package) — a shared, framework-free Page Object Model
  over a single selector registry, consumed by *both* the new test suite and
  `scripts/capture_screenshots.py` (converged onto it, so there is **one**
  navigation source rather than two drifting copies). `base_url` is injected,
  so the same POMs drive the ephemeral-port test server and the screenshot
  script's `:5000`.
- **`tests/ux/`** — a threaded live-server + headless-Chromium harness with a
  console-error + HTTP-5xx **sentinel**; LLM-free (analyzer functions stubbed
  at the public-streaming-fn seam, so the real Flask routes still run). One
  stubbed happy-path walk (analyze → compose → template), one seeded Step-6
  WYSIWYG walk (via the prior-app-resume path), and five regression tests
  (`test_<YYYYMMDD>_<slug>.py`, never deleted): import-résumé label, rail
  re-enable after analyze, corpus-tab render, the personas-500 → iframe →
  paged.js cascade root (AGENT_FAILURE_PATTERNS §5b), and Compose bullet
  drag/keyboard reorder persistence + reset.
- **`pyproject.toml`** — new `ux` pytest marker (`pytest -m ux`); ux tests are
  also `slow`/real-Chromium and skip when the browser binary is absent, so the
  default `pytest` stays green everywhere. `tests/*` ruff ignore widened to
  `tests/**` for the nested suite.

### Added — user-driven bullet ordering on Compose (`feat/bullet-drag-reorder`, v1.0.5)

Drag-and-drop (and keyboard) reordering of bullets within each experience on
the Compose step. The chosen order is **authoritative** — it propagates into
the `<career_corpus>` block fed to `generate()`, so it shapes which bullets the
LLM keeps in a length-limited résumé, not just the on-screen list. A data-order
change, **not a prompt-template change → `PROMPT_VERSION` unchanged, no new
dependency, no LLM call** (captured as a behavior note in
[`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) instead of a version bump).

- **`analyzer.py`** — `_stable_user_prefix` honors
  `composition_overrides.bullet_order = {experience_id: [bullet_id, ...]}`,
  reordering each experience's bullets before the corpus block is emitted.
  Bullets absent from a saved order keep their relative position at the end
  (covers a bullet added via the drawer *after* ordering — never silently
  re-sorted). Absent/empty order ⇒ output byte-identical, so the
  analyze→generate prompt cache is untouched.
- **`app.py`** — the existing `POST /api/applications/<id>/composition` threads
  and validates an optional `bullet_order` into the persisted overrides; `GET`
  returns bullets in the saved order with a per-experience `has_custom_order`
  and per-bullet `in_custom_order` flag. Existing `_safe_username` + `_within`
  guards unchanged; no new route.
- **`static/app.js` + `static/style.css`** — native HTML5 drag with a grab
  handle (`≡`, grab/grabbing cursors), an Up/Down keyboard path with
  `aria-label`s (the a11y floor; no deprecated
  `aria-grabbed`/`aria-dropeffect`), a one-sentence in-interface instruction
  plus an "(i)" depth affordance, a per-experience "Reset to AI ranking"
  button, and a "newly added — drag to reposition" hint. Reorders persist via a
  debounced (~300 ms) optimistic autosave.
- **Behavior change (consistency win):** pin / exclude / add now also persist on
  the debounced autosave, not only when you click Next — the autosave sends the
  full composition state, so it can't clobber those flags.

### Added — WYSIWYG live preview (Option 1) (`feat/wysiwyg-option1`, v1.0.5)

The application preview is now byte-for-byte the future downloaded résumé once a
generate has run. A pure rendering/caching change per RELEASE_ARC Key decision 5 —
**no prompt change, `PROMPT_VERSION` unchanged, no new dependency, no LLM call.**

- **`hardening.py`** — `save_iteration_context()` caches `last_generated_json_resume`,
  the deterministic `json_resume.md_to_json_resume()` of the markdown the LLM just
  wrote, into every post-generate context. Derived from `last_generated_resume`, so
  the preview source can never drift from the download. Added to the `ContextSet`
  TypedDict.
- **`app.py`** — `GET /api/applications/<id>/preview` serves
  `last_generated_json_resume` directly when the context carries it (preview ==
  download), bypassing the pre-generate curation gate. Pre-generate it still builds
  the JSON Resume from the corpus and gates on `llm_recommendations`. A new
  `_json_resume_has_content()` guard falls back to the corpus-direct render if the
  cached doc is an empty skeleton.

### Added — Step 6 (Output) redesign + styled cover-letter preview (`feat/step6-redesign`, v1.0.5)

Finishes the Step 6 output panel and gives the cover letter a styled live preview.
A UI/rendering change — **no prompt change, `PROMPT_VERSION` unchanged, no new
dependency** (`markdown` was already a dependency), no LLM call on the new path.

- **`personas/cover_letter.html` (new)** — a shared, persona-agnostic
  business-letter shell for the cover-letter preview: terser header (no name
  banner), dense single-spaced body, addressee block inline with the body, and the
  chosen persona's font (plainly) injected via a template variable. Honors
  `@page { size: letter }` so paged.js paginates it like the résumé.
- **`pdf_render.py`** — `render_cover_letter_html()` renders generated
  cover-letter text into that shell (`markdown` + `nl2br`, so header lines keep
  single-line breaks while blank-line-separated paragraphs become `<p>` blocks);
  `persona_font_family()` extracts a persona CSS's base `font-family` (multi-line
  values normalized) with a neutral fallback. Both deterministic — no LLM.
- **`app.py`** — `GET /api/applications/<id>/cover-letter-preview` serves the
  styled cover letter from a context's `last_generated_cover_letter`, returning an
  honest placeholder until one is generated. Same guard pattern as the résumé
  preview (`_safe_username` + `_within(OUTPUT_DIR)`).
- **Frontend** — the Cover-letter tab gains a styled paged.js preview iframe with
  a "Page N of M" chip; the Step 6 résumé preview gains the same chip (reusing
  `_updatePreviewPageCount`, now source-keyed so multiple preview frames don't
  cross-talk). The "Edit before downloading" drawer is parameterized to host either
  the résumé or cover-letter editor; edits still flow through `/api/save-edits`.
  Stale "WYSIWYG coming in v1.0.2" / "styled CL lands in B3" hint copy corrected.
- The cover letter still downloads as **`.docx`**; PDF/Markdown cover-letter output
  is the next branch.

### Added — Cover-letter output formats (`feat/cover-letter-formats`, v1.0.5)

The cover-letter download now honors a chosen output format — `.docx`, `.pdf`, or
`.md` — closing the v1.0.1 placeholder (which shipped only a UI hint). An
output-format change only — **no prompt change, `PROMPT_VERSION` unchanged, no new
dependency, no LLM call** (the renderers are deterministic, P1 Hardening).

- **`generator.py`** — `generate_cover_letter()` gains an `output_format` (+
  `template_path`) param and branches like `generate_resume()`: `.md` writes the
  normalized markdown; `.pdf` renders through the shared `personas/cover_letter.html`
  business-letter shell via Playwright (`_render_cover_letter_pdf`), so the `.pdf` is
  byte-faithful to the Step-6 preview (WYSIWYG); `.docx` uses a new
  `_write_cover_letter_docx()` aligned to the 2026-05-26 business-letter decisions
  (persona font matching the chosen résumé template, dense near-single spacing, no
  name banner, inline addressee). The `.docx` and `.pdf` share one font source (the
  persona CSS). The now-unused `is_cover_letter` param was removed from `_write_docx`
  (résumé output unchanged).
- **`pdf_render.py`** — `render_cover_letter_pdf()` mirrors `render_pdf`: renders the
  shell HTML (via the existing `render_cover_letter_html`) to a temp file and prints
  it through headless Chromium, letting the shell's `@page` rule govern page geometry
  (`prefer_css_page_size`) so the PDF matches the paged.js preview. Deterministic.
- **`app.py`** — `/api/download-edited` threads the chosen format and resolved persona
  template into `generate_cover_letter` for cover-letter downloads (no new route; the
  existing `_safe_username` / `_within` / `secure_filename` guards cover the path).
- **Frontend** — a dedicated DOCX / PDF / Markdown picker in the Step-6 cover-letter
  tab (independent of the résumé's Step-5 picker — résumé and cover letter can use
  different formats); `downloadCoverLetter()` sends the chosen format + persona id.
  The satisfied "PDF & Markdown coming next" hint copy was removed.

### Added — Resume a prior application into the wizard (`feat/prior-app-resume`, v1.0.5)

Clicking a prior application now offers **Resume in wizard**, which reloads that
application's last generated state — context + persona + generated résumé/cover
letter — into the live wizard and jumps to Step 6, closing the D.3.1 placeholder.
A UI state-hydration change only — **no prompt change, `PROMPT_VERSION` unchanged,
no new dependency, no LLM call, no schema migration.**

- **`app.py`** — `GET /api/applications/<id>` gains a `resume_state` block (latest
  run's generated/edited markdown, persona, rediscovered `context_path`, iteration,
  `resumable` flag). A new deterministic, LLM-free helper
  `_find_context_path_for_run()` rediscovers the run's on-disk `context_*.json`
  (ApplicationRun has no `context_path` column) by matching the `application_run_id`
  each context file embeds, newest by iteration then mtime; every candidate path is
  `_within(OUTPUT_DIR)`-guarded. No new route — `get_application`'s existing
  `_safe_username` guard covers it.
- **Frontend** — a "Resume in wizard" button on the application-detail modal (shown
  only when a run produced a résumé). `resumeApplicationIntoWizard()` reuses
  `_onGenerationComplete` + `_renderOutput` (converging on the exact post-generate
  state, not forking it): binds the preview routes to the application, reselects the
  persona, hydrates the editors, and advances the rail to Step 6. When the on-disk
  context file is gone it degrades gracefully — editors still hydrate from the DB
  markdown and downloads work; a toast notes that the styled preview + further
  iteration need a re-generate.

## [1.0.4] — 2026-06-02

The eval tuning loop: a real-data, human-in-the-loop, model-assisted
prompt-improvement loop, gated by the offline grounding scorers and the eval
suite. Internal/dev tooling — **no user-facing pipeline change** across the
stream, and `PROMPT_VERSION` is unchanged (no persona-constant edit landed; the
loop *promotes* edits under explicit user approval, which is when a bump occurs).
Six sequential branches: the prompt-override primitive, corpus seed
export/import, the corpus-backed runner, the bootstrap engine, the annotation
contract, and the draft-and-gate tuning skill.

### Added — Eval prompt-override primitive (`eval/prompt-override-primitive`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, and `PROMPT_VERSION` is unchanged (no prompt-constant edit).

- **`analyzer.py`** — a runtime prompt-override primitive. `prompt_overrides()`
  (a context manager) injects a candidate system prompt **by name** without
  editing the persona constants; `effective_prompt_version()` returns
  `PROMPT_VERSION` on the default path but a stable `candidate:<hash>` while an
  override is active, so candidate runs are quarantined from the dashboard's
  score-over-time. The default (no-override) path is **byte-identical**: the
  call-site resolver returns the *identical* constant object and the logged
  version is unchanged, so the analyze→generate prompt cache and the
  `PROMPT_VERSION` attribution discipline are untouched.
- **`evals/runner.py`** — `--prompt-overrides PATH` threads a JSON
  `{prompt-name: override-text}` file through a run; eval result records and
  telemetry stamp the candidate version. Eager-validated — bad JSON, wrong shape,
  or an unknown prompt name exits non-zero before any paid LLM call.
- **`/prompt-tune`** — retrofitted onto the primitive: the A/B trial injects the
  candidate via `--prompt-overrides` instead of editing `analyzer.py` in place
  (removing the fragile clean-revert dependency); the constant is edited only if
  you choose Keep.

### Added — Corpus seed export (`eval/corpus-seed-export`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls.

- **`scripts/export_corpus_seed.py`** — a deterministic, LLM-free CLI
  (`python -m scripts.export_corpus_seed --user <name>`) that snapshots one
  candidate's corpus (Candidate / Experience / ExperienceTitle / Bullet /
  SummaryItem / Skill / Education / Certification + the candidate-scoped Tag
  registry and tag links) into a `seed.json` under the gitignored
  `evals/fixtures/real/`. Original DB primary keys are preserved so foreign-key
  relationships round-trip; the export is a faithful snapshot (active + inactive
  rows) — the active-only / JD-aware filtering stays in
  `build_context_set_from_db`. The `seed.json` shape (`seed_schema_version: 1`)
  is the contract the upcoming corpus-backed eval runner imports into an
  in-memory SQLite.
- **Write-path guard** — a `_within`-style resolved-path check (mirroring
  `app.py:_within`) refuses to emit anywhere except `evals/fixtures/real/`, and
  `secure_filename` sanitizes the username directory component, so the snapshot
  (which carries real PII) can't escape the gitignored tree.

### Added — Corpus-backed eval runner (`eval/corpus-backed-runner`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls. The
file-based eval path is **byte-for-byte untouched** when `--seed` is absent.

- **`evals/seed_import.py`** — a deterministic, LLM-free importer: the faithful
  inverse of `scripts/export_corpus_seed.py`. Reads a `seed.json`
  (`seed_schema_version: 1`), validates the schema version against the versions
  the importer itself supports (drift is rejected, not half-imported), and
  reconstructs the candidate's corpus into a fresh in-memory SQLite —
  **preserving the original primary keys** so the seed's tag links stay
  FK-correct with no remap table. `seeded_session()` is the ergonomic
  context-manager entry (builds the engine + schema, imports, yields
  `(session, username)`, disposes on exit). The importer does NOT pre-filter —
  inactive rows are reconstructed too; the active-only / JD-aware filtering stays
  inside `build_context_set_from_db`.
- **`evals/runner.py`** — `--seed PATH` builds each fixture's context via
  `db.build_context.build_context_set_from_db` over the imported corpus (the REAL
  corpus→context product path) instead of parsing the fixture's resume file; the
  fixture's `jd.txt` + `expected.json` still drive grading. Eager-validated — a
  bad path, malformed JSON, or unsupported schema version exits non-zero before
  any paid LLM call. Absent flag → the resolver, `_load_fixture`, and the
  context-build branch are all byte-identical to today.

### Added — Corpus bootstrap engine (`eval/bootstrap-engine`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency. The bootstrap engine
*orchestrates* LLM calls (it lives in `evals/`, off the P1 hardening boundary,
like `evals/runner.py`), but every collation step is deterministic and LLM-free.
The runner's file-based and `--seed` paths are **untouched** (zero edits to
`evals/runner.py`).

- **`evals/bootstrap.py`** — drives **one corpus seed against N JDs**
  (`--jd-dir` of `*.txt`/`*.jd` files) through the REAL product pipeline
  (`analyze` → `clarify` → `generate`, reusing the public primitives + an
  in-memory `seeded_session` import + `build_context_set_from_db`), then
  deterministically dedups the generated bullets and skills across JDs at a
  Jaccard threshold (default 0.75). The cross-JD cluster span (`size` /
  `len(jd_files)`) is the JD-invariance signal: a wide-span cluster is grounded
  core; a `size: 1` cluster is JD-specific — a `jd_pandering` candidate the next
  branch annotates. Output is a `bootstrap.json` (`bootstrap_schema_version: 1`)
  written under the gitignored `evals/fixtures/real/<candidate>/`; a `_within`
  write-path guard (mirroring `scripts/export_corpus_seed.py`) refuses to emit
  the PII-bearing snapshot anywhere else. The seed + `--jd-dir` are
  eager-validated before any paid LLM call.
- **Second `run_grounding_signals` call site** — `--grounding-signals` scores the
  deduplicated bullet cluster representatives against the corpus source text
  (DeBERTa NLI + MiniCheck-FT5, eval-only), gated on the same opt-in as the
  runner.
- **`evals/rubrics/grounding.md`** — adds the `jd_pandering` slug to the
  `failed_rules` vocabulary (a fabrication subtype: re-skinning source experience
  with a JD's domain terms not present in source). Rubric-vocabulary edits are
  eval-apparatus, **not** a prompt change — `PROMPT_VERSION` is not bumped.

### Added — Eval annotation contract (`eval/annotation-contract`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls. The
file-based, `--seed`, and bootstrap paths are **untouched**. Deterministic
collation only — it consumes `bootstrap.json`, it does not call models (P1
hardening posture, like `evals/seed_import.py`).

- **`evals/annotation.py`** — the headless, file-based annotation contract: the
  human-in-the-loop seam between `bootstrap.json` and a `--suite real` regression
  fixture. It declares `annotation_schema_version: 1` and a fail-closed
  `validate_annotations` (mirroring `evals/seed_import.py`: an unsupported version,
  missing collections, an unknown verdict, an unknown `failed_rules` slug, or a
  verdict whose required payload is absent is rejected, not half-collated).
- **Verdict enum** — `keep` / `fix` / `omit` / `fabricated`. Disposition verbs,
  each mapping 1:1 to a collation action. **Verdict-aware** requirements: `fix`
  must carry an `honest_rewrite`; `fabricated` must carry a compilable
  `forbidden_pattern` regex. The grounding *subtype* of a finding
  (`jd_pandering`, `invented_metric`, …) rides in `failed_rules`, which **reuses
  the existing rubric vocabulary** in `evals/rubrics/` — that reuse is not a
  prompt change and bumps no `PROMPT_VERSION`.
- **Template emitter** (`build_annotation_template`) — `bootstrap.json` → a blank
  `annotations.json` skeleton pre-filled with every bullet/skill cluster +
  clarification question + the inline MiniCheck/NLI pre-scores (joined by index
  from the bootstrap's `grounding_signals`), so a human annotates with the model
  pre-scores in view. The headless stand-in for the v1.0.5 annotation UI, which
  wraps this same file format — so the format is the durable contract.
- **Deterministic collation** — a completed `annotations.json` (+ its
  `bootstrap.json`) produces (a) an `expected.json` fixture matching the schema
  `evals/runner.py:_load_fixture` reads (`must_keywords` from `keep`-verdict
  skills; `forbidden_inventions` from `fabricated`-verdict patterns; `min_*_score`
  defaults/overrides; `candidate_name`; provenance `notes`) and (b) an improvement
  brief (fabrication patterns, `fix` rewrites as worked-example seeds, omissions,
  clarification ratings, and a human-vs-scorer agreement section) — the source
  material for the next branch's prompt edits.
- **CLI** — `python -m evals.annotation --bootstrap PATH --emit-template` writes
  the skeleton beside the bootstrap; `… --collate --annotations PATH --jd-dir PATH`
  **auto-writes a runnable `--suite real` fixture directory** (`expected.json` +
  the widest-span anchor `jd.txt`) plus the brief. A `_within` write-path guard
  (mirroring `evals/bootstrap.py`) refuses to emit the PII-bearing artifacts
  anywhere except `evals/fixtures/real/`.

### Added — Tune-from-annotations skill (`tuning/draft-and-gate-skill`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, no new dependency. `PROMPT_VERSION` is **unchanged by this branch**:
only a user-approved *promote* edits a persona constant and bumps the version (in
that promote commit), never the skill itself. Closes the v1.0.4 loop (export →
bootstrap → annotate → collate → **draft / eval / promote**).

- **`/tune-from-annotations`** (`.claude-plugin/commands/tune-from-annotations.md`)
  — the annotations-driven sibling of `/prompt-tune`. It reads an
  `improvement_brief.md`, drafts a candidate system-prompt edit, A/Bs it against
  the annotation-produced `--suite real` fixture (via `--seed`) **plus an
  `--suite anchor` canary**, and presents the delta tables. Built on the
  prompt-override primitive, so `analyzer.py` is untouched during the trial and
  the candidate run is logged as `prompt_version=candidate:<hash>` (quarantined
  from score-over-time). Promotion — `Edit` the constant + bump `PROMPT_VERSION`
  in one commit + a `TUNING_LOG.md` entry — happens only on an explicit "promote."
- **`tune-drafter` subagent** (`.claude-plugin/agents/tune-drafter.md`) — drafts
  the full candidate constant text from the brief + the current constant. It is
  **read-only** (`Read`/`Grep`/`Glob`; no `Edit`/`Write`) by design: it cannot
  edit `analyzer.py`, so the baseline it drafts against stays intact for an
  honest A/B, and promotion stays a user-gated step in the command — not the
  drafter's job.
- **`evals/tune.py`** — a deterministic, LLM-free delta-table helper + CLI
  (`python -m evals.tune --baseline A.jsonl --candidate B.jsonl [--json]`). Reads
  eval result JSONL, groups `status == "ok"` scores by `(fixture, rubric)`, and
  emits per-pair baseline-vs-candidate deltas (regression flag at the runner's
  `REGRESSION_DELTA`). Standalone — it consumes result files only and imports
  nothing from `runner.py`/`annotation.py`/`bootstrap.py`/`seed_import.py`, so
  their paths are untouched. `tests/test_tune.py` covers it (LLM-free).

## Archived versions

Releases **1.0.3 and earlier** (through the initial 0.1.0 release) moved to
[`CHANGELOG-archive.md`](CHANGELOG-archive.md) to keep this file scannable
([PX-48](docs/dev/reviews/2026-07-efficiency/prescriptions.md)). Content is
byte-preserved there, unchanged — this is a cut, not a rewrite.
