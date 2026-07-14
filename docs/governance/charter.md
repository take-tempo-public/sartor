# Constitution — sartor.

> **Purpose:** the single canonical home for sartor.'s *binding* governance —
> the constitutional clauses (C-0…C-8), the defaults (D-1…D-7), the parallel-session
> working model (W-1/W-2), and the amendment ceremony. Each rule is stated **once**,
> here; the descriptive docs that used to carry it now keep their prose and point back.
> **Audience:** every contributor and every AI agent (Claude Code, Cursor, Codex,
> Aider, …) making a non-trivial change; the future compliance agent that audits
> drift against this home.
> **Authoritative for:** the rule-bearing constitution. On any conflict between this
> charter and a restatement in a descriptive doc (`vision.md`, `AGENTS.md`,
> `SECURITY.md`, `CONTRIBUTING.md`, `docs/PRODUCT_SHAPE.md`, `docs/dev/RELEASE_ARC.md`),
> **the charter governs.** Enforcement detail (what is a gate vs witness vs tribal)
> lives in [`enforcement.md`](enforcement.md); success criteria + the eval ride-along
> + the review rubric live in [`metrics.md`](metrics.md).

---

## What this is

This is the constitution sartor. is built and audited against. It graduated
(Sprint 7.2, v1.0.7) from the SIGNED Product Charter that governed the 2026-06
product-excellence review
([`../dev/reviews/2026-06-product-excellence/00-interview/product-charter.md`](../dev/reviews/2026-06-product-excellence/00-interview/product-charter.md))
and the four-file governance-draft the review pre-authored. The decision of record is
**extract, don't register-in-place**
([`../wiki/pages/governance-extraction.md`](../wiki/pages/governance-extraction.md);
affirmed register-grade by **F-gov-05**): each rule lives in **exactly one** canonical
home and everything else **references** it. So this document does not duplicate the
prose of `vision.md`, `SECURITY.md`, or the others — it states the binding rule once and
**cites the source** for the mechanics. Every clause is tagged `[src: …]` so the
extraction is a verifiable citation map.

**Writing contract (C-0).** Categorical wording ("never / only / always") appears
only where a deterministic test can enforce it by construction; anywhere a claim rests
on LLM behavior, this document describes **mechanisms and effort**, not absolutes — and
carries no marketing language.

**Evidence base.** Findings are cited by `F-id` rather than re-derived
([`../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md`](../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md)
+ the verification log alongside it). The `F-id` evidence base is pinned at the review
SHA `c6e0437`; **the `[src: …]` tags below are reconciled to current `main`** — where a
correction the draft "owed" has since landed (the v1.0.6 PX batch), the tag cites it as
**already corrected**, not as still-owed. Only two gates stay forward-sequenced to
v1.0.8 (C-1 bind, C-6 boundary); both are marked inline.

**Load-bearing safety condition (F-gov-05).** `AGENTS.md` / `CLAUDE.md` are
harness-auto-loaded — the agent's operating instructions at session start. Extraction
preserves agent rule-access via `@import` (`CLAUDE.md` already does `@AGENTS.md`) or an
explicit canonical pointer, or future agents lose their guardrails. `AGENTS.md` stays
the entry point and keeps its rules **inline** (non-Claude agents read it raw); it
links this charter, it does not surrender the rules.

---

## Constitutional clauses

*Each clause is owner-voiced or machine-enforceable. Tier intent: a clause stating a
categorical is one a deterministic gate can enforce by construction (or is named below
as a gate still owed); a clause resting on LLM behavior is written as
mechanism-and-effort. The flat "won't-cross" list in `vision.md` is replaced by this
enforceability tiering — **F-vision-01**.*

**C-0 — Claims discipline.** Categorical claims are made only where a deterministic
test enforces them by construction (network egress, module boundary, shipped-template
properties). Where a claim depends on LLM behavior, describe mechanisms and effort,
never absolutes. *[src: charter C-0 (signed). The LLM-behavior absolutes flagged by
**F-vision-02** / **F-docs-03** — "the LLM cannot invent facts", the "No invention,
ever" heading, the "without inventing anything" / "may not fabricate" copy — were
reworded to mechanism-and-effort in v1.0.6 (**PX-09**): `vision.md` goal 1 + "Grounding
mechanism, not a guarantee", and the wiki overview / `llms.txt` copy. Cited as
corrected; not re-fixed.]*

**C-1 — Local and yours.** sartor. is a local tool under the control of a single
unauthenticated user; all user artifacts stay on the user's disk, never uploaded; there
is no hosted service. The loopback bind is the construction that makes this categorical
true. *[src: charter C-1; `../../vision.md` "Local-first, single-tenant"; `../../SECURITY.md`
"Scope". The "single-tenant **by design / as a value**" framing is demoted to a
threat-model statement (**F-vision-04**: `list_users()` / multi-profile UI contradict
the value claim; the single-unauthenticated-user threat model is preserved) — the
demotion lands in `vision.md` on this branch (PX-27). **Gate shipped — v1.0.8 Sprint
8.3a (PX-19):** the 127.0.0.1 bind is now pinned + asserted by a test (was implicit,
neither pinned nor asserted — **F-sec-02**, `app.py app.run()` had no `host=`;
`SERVER_NAME` a silent-flip vector) — see [`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md)
Sprint 8.3a. Owner-approved factual reconcile, 2026-07-09, witness CW-102.]*

**C-2 — Egress.** Outbound traffic is confined to an enumerable destination set;
because it is enumerable, this clause is machine-verifiable. The sanctioned classes are
exactly two: **(a)** the configured LLM provider, and **(b)** the optional
profile/website scrape when the user supplies LinkedIn/portfolio URLs. JDs are pasted
text — no JD-URL fetch exists. No telemetry, analytics, or error reporting leaves the
machine. *[src: charter C-2; `../../vision.md` "Local-first"; `../../SECURITY.md` threat
model. The egress falsifiability gate C-0 requires is **SHIPPED** (**PX-08**;
[`../../tests/test_egress_allowlist.py`](../../tests/test_egress_allowlist.py) —
**F-qe-rel-02** P0 / **F-sec-01**). The pin-era divergences are resolved: Chart.js
vendored + SRI-pinned, no runtime CDN (**PX-01**; **F-vision-05** / **F-sec-03** /
**F-docs-02**); the dead profile scrape re-wired (**PX-02**; **F-docs-04**); SECURITY's
phantom third JD-URL egress class corrected to the two-class enumeration (**PX-03**;
**F-sec-04** / **F-docs-01**). The eval-grounding model download (~3.2GB from
huggingface.co) is a sanctioned power-user opt-in under D-6, not a third egress class —
**F-sec-10**.]*

**C-3 — Grounding mechanisms; grounded synthesis is the feature.** sartor. works to
keep the LLM grounded in real experience through stated mechanisms — grounding rules in
the prompts (with worked OK/NOT-OK examples), clarifying questions that extend ground
truth, human review at each step, corpus approval of LLM-generated bullets, and a
candidate memory. Grounded synthesis — abstracting useful bullets from corpus +
clarifications toward a JD — is the feature; the violation is asserting beyond that
ground, not synthesizing within it. Grounding tightening that suppresses useful grounded
synthesis is a regression (lead AL-1). *[src: charter C-3; `../../vision.md` goal 1 +
"Grounding mechanism, not a guarantee" (already C-0-corrected, PX-09 — cited, do not
edit); `../../AGENTS.md` "LLM prompts"; `../system-model.md` "What it is". The
deterministic source-union metric folds **three** sources — primary + supplementals +
clarification answers — not typed edits; `GROUNDING_METRIC.md` states the three-source
union as of **PX-14** (**F-eval-04**, WEAKENED AFFIRM — cited as corrected). AL-1
over-suppression is uninstrumented in eval data today (**F-eval-01**) — tracked in
[`metrics.md`](metrics.md) §2.]*

**C-4 — The candidate stays in control.** Human review gates sit along the pipeline;
the user can edit anything before using it, and the tool produces documents rather than
submitting them. *[src: charter C-4; `../../vision.md` goal 3 + P8 Human Gates;
`../system-model.md` "Production". Affirmed surfaces to protect: keyboard
bullet-reorder alternative (**F-expa11y-07**), live-region announcements
(**F-expa11y-08**), manual-promote annotation contract (**F-eval-06**).]*

**C-5 — Everything sartor. ships is ATS-safe.** All bundled templates are
single-column, plain-bullet, standard-font; non-ATS templates are retired. Users who
want non-ATS output edit the document they produced. This categorical is enforceable on
shipped-template properties (a deterministic domain under C-0). *[src: charter C-5;
`../../vision.md` goal 2 + "ATS-safety is the product". The escape hatch ("users who
want non-ATS output edit the document they produced") is named in `vision.md` goal 2 as
of this branch's PX-27 edit (**F-vision-07**). The shipped-template property gate is
forward-sequenced to v1.1.0 — see [`enforcement.md`](enforcement.md) §A.]*

**C-6 — The deterministic–LLM boundary.** Deterministic modules make no LLM calls; one
module (`analyzer.py`) owns all LLM calls. *[src: charter C-6; `../../vision.md`
"Deterministic where possible"; `../../AGENTS.md` "Architecture at a glance" + "What NOT
to do"; `../system-model.md` "Production" + "the one law". The boundary **holds by
behavior** (7 modules clean, AST-verified — **F-arch-04**) but by **convention only**:
no import-lint/boundary test fails on a regression. **Gate shipped — v1.0.8 Sprint
8.3a (PX-20, WS-1):** an AST-walk boundary test,
[`../../tests/test_construction_boundary.py`](../../tests/test_construction_boundary.py)
(**F-arch-01** / **F-qe-rel-04**) — see [`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md)
Sprint 8.3a. Owner-approved factual reconcile, 2026-07-09, witness CW-102.]*

**C-7 — Evidence before mechanism.** A causal claim is a claim, and therefore falls under
C-0. Reading code and finding a plausible mechanism is a **hypothesis**, not an observation.
Four binding rules follow. (1) For a defect you cannot reproduce on demand, **the first commit
on the branch is the instrument or the reproduction — never the fix.** (2) A commit that
changes production code to fix a defect must cite the **observation** that identified the
mechanism: a log line, a response body, a CI run id, or a test that fails without the change.
(3) **Green CI is not evidence if the test needed a retry** — `pytest-rerunfailures` reports a
fail-fail-pass as a bare `PASSED` with no traceback anywhere in the log. (4) **Scope the
instrument wider than the hypothesis**: an instrument narrowed to the theory it is testing
will confirm that theory by hiding its rivals. **No escape hatch** — and none is needed, since
docs, tests and prose stay writable, so the way through is always to write down what you saw.
*[src: adopted 2026-07-14, owner-directed, from friction. Enforced by the
`require-evidence-before-fix` PreToolUse guard
([`../../scripts/enforcement/guards/require_evidence_before_fix.py`](../../scripts/enforcement/guards/require_evidence_before_fix.py))
over `docs/dev/diagnosis/<branch-slug>.md`; gated by
[`../../tests/test_evidence_gate.py`](../../tests/test_evidence_gate.py). Worked example and
the reason this clause exists:
[`../dev/diagnosis/compose-summary-draft-settle-hole.md`](../dev/diagnosis/compose-summary-draft-settle-hole.md);
failure pattern **5f** in [`../dev/AGENT_FAILURE_PATTERNS.md`](../dev/AGENT_FAILURE_PATTERNS.md).
This clause exists because the *advisory* form of it (§5a/5b/5e) was read and overruled — the
failure mode is an agent judging that the rule does not apply this time, which is precisely
what a rule may not leave to judgment.]*

**C-8 — Durable before deep.** The context window is **not a durable store**. A fact that cost
work to learn — a measurement, a falsified hypothesis, an observed artifact — is written to its
durable home **in the turn it is learned**, never deferred to close-out; the pre-close sweep
*reconciles*, it must not *discover*. Compaction is an unannounced **data-loss event**: after
one, or when resuming from a summary, the next action is to **reconcile against the repo and
git**, never to continue from the summary as though it were the evidence. Do not fan out to
subagents on an un-captured context — their findings return *into* a window that can compact
away. And **a degraded context is a handoff trigger, not a push-harder trigger**: an
investigation that has not converged by the time the window is thin should be captured and
handed off, because a model on a thinning record keeps answering with undiminished confidence.
*[src: adopted 2026-07-14, owner-directed, from friction — the harness compacted the working
context *while the agent was on its way to write the capture*. Enforced by the `restore-evidence`
SessionStart hook (which replays the branch's `## Observed` + `## Falsified` into every fresh
context, including the one rebuilt after a compaction) and the `capture-before-compact`
PreCompact hook; both in
[`../../scripts/enforcement/adapters/claude_context_hook.py`](../../scripts/enforcement/adapters/claude_context_hook.py),
gated by [`../../tests/test_evidence_gate.py`](../../tests/test_evidence_gate.py). C-8 is the
structural complement to C-7: C-7 makes the evidence exist, C-8 makes it survive.]*

### Defaults (binding until changed; changeable in normal flow with a written rationale)

- **D-1 — Minimal dependencies.** New dep = `pyproject.toml` + `CHANGELOG.md` +
  "couldn't reasonably be done in pure Python or an existing dep." *[src: charter D-1;
  `../../vision.md` "Minimal dependencies"; `../../CONTRIBUTING.md`; `../../AGENTS.md`
  "What NOT to do".]*
- **D-2 — Anthropic as sole LLM client**, with a planned amendment to provider-agnostic
  + local models post-public; C-2 amends by ceremony then. *[src: charter D-2.]*
- **D-3 — No accounts, no auth** — the current shape, explicitly negotiable. *[src:
  charter D-3; `../../SECURITY.md` "Out of scope".]*
- **D-4 — Commitments hygiene.** Public docs make no response-time SLAs and no recurring
  human-labor promises; machine-enforced gates are exempt. *[src: charter D-4. The two
  hard human SLAs flagged by **F-qe-rel-08** / **F-sec-07** (`SECURITY.md` 5-day/30-day;
  `CODE_OF_CONDUCT.md`) were softened to best-effort in v1.0.6 (**PX-05/07**) — both now
  state no guaranteed timeline. Cited as corrected; do not re-soften.]*
- **D-5 — Open-standards + auditable-iterations mechanics** (JSON Resume intermediate;
  standard fonts, offline render; MIT-compatible licensing with vendored headers;
  per-generation timestamped child context as the audit trail). *[src: charter D-5;
  `../../vision.md`; `../system-model.md`. Audit-trail spine affirmed — **F-arch-07**.
  Vendored axe is MPL-2.0, under-declared in a MIT-only LICENSE — **F-sec-08**; a
  REUSE/SPDX manifest is planned for the public release (v1.1.0).]*
- **D-6 — Per-system tool bundling, progressively disclosed.** Capabilities needing
  extra installs (grounding-scorer models, Chromium) bundle per system; install docs are
  progressive. *[src: charter D-6. Chromium's docs classification (was inconsistent
  across docs, basic-tool vs dev-only — **F-docs-05**) was reconciled in v1.0.7
  (**PX-31**): reclassified PDF-output-only across `docs/install.md`'s Prerequisites +
  all 3 OS sequences, correcting the "renders every PDF and the live preview"
  conflation (the live preview is browser-side paged.js, Chromium-free). Cited as
  corrected; do not re-flag. Owner-approved factual reconcile, 2026-07-09, witness
  CW-104.]*
- **D-7 — Release versioning + release notes (adopted 2026-07-13, owner-directed, from
  the v1.1.0 public cut onward).** *Rationale: the project publishes to PyPI and GHCR from
  a pushed tag; a version string is a claim about compatibility and readiness, and it is
  read by machines (pip's resolver) before it is read by anyone. It gets the same
  claims-discipline treatment as any other categorical statement (C-0).*
  1. **Semantic Versioning 2.0.0** ([semver.org](https://semver.org/)) governs the version
     number: MAJOR (incompatible), MINOR (backward-compatible capability), PATCH
     (backward-compatible fix).
  2. **Pre-releases ship under the `alpha → beta → rc` ladder** with a numeric counter —
     `1.1.0-alpha.1` < `1.1.0-beta.1` < `1.1.0-beta.11` < `1.1.0-rc.1` < `1.1.0`. This is a
     deliberate **subset** of what semver permits: it is the intersection where semver and
     Python's PEP 440 order versions *identically*, so the git tag and the published Python
     package can never disagree about which release is newer. Semver's free-form
     alphanumeric identifiers (`1.0.0-alpha.beta`) are **not** used — PEP 440 cannot express
     them, so pip could not order them.
  3. **The git tag is semver; the `pyproject.toml` version is its PEP 440 normalization**
     (tag `v1.1.0-rc.1` ↔ version `1.1.0rc1`). The two are one fact in two dialects, and the
     release workflow verifies they agree *after* normalization — never as raw strings.
  4. **Release notes must disclose fixed vulnerabilities.** Every released `CHANGELOG.md`
     section names every publicly known **runtime vulnerability in Sartor's own code** that
     the release fixes and that already had a CVE (or equivalent public ID) assigned when
     the release was cut. Scope is **the project's own results, not its dependencies**. When
     there are none, the section says so explicitly — silence is not a disclosure. *(From
     the [OpenSSF Best Practices](https://www.bestpractices.dev/) criteria; the N/A
     escape — "users cannot practically update the software themselves" — does not apply
     here, since users install Sartor themselves from PyPI or GHCR.)*
  Enforced by `tests/test_release_versioning_gate.py` + the tag-match step in
  `.github/workflows/release.yml`; mechanics in
  [`enforcement.md`](enforcement.md#b2-d-7--release-versioning--release-notes).
