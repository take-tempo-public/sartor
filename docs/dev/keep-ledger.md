# KEEP / BOOST ledger — eval & governance (do-not-regress)

> **Purpose:** the do-not-regress catalogue for the eval and governance design
> surfaces the 2026-06 product-excellence review affirmed as load-bearing. Each
> entry names an invariant, where it lives, how it could silently regress, and
> how it's protected — so a future refactor (especially the v1.0.8 blueprint
> split) can't quietly weaken it.
> **Audience:** any agent or contributor touching `analyzer.py`, `evals/`,
> `dashboard/`, the `/api/eval` · `/api/tune` routes, the hooks, the subagents,
> or `docs/wiki/` — read the relevant entry before changing that surface.
> **Authoritative for:** the affirmation half of the KEEP/BOOST set (records the
> intent to preserve). The **test** half — converting these into guard tests so
> the split can't regress them — is PX-29 (`test/keep-ledger-guards`, v1.0.8).
> Severity anchor + evidence: the signed Product Charter and the
> [findings register](reviews/2026-06-product-excellence/02-assessment/findings-register.md)
> (pinned at `c6e0437`); symbol-level cites below resolve at HEAD.

This ledger is the v1.0.7 output of **PX-32** (the eval/governance KEEP+BOOST
affirmation pass). It is a sibling to the **security / PII** KEEP set, which is
PX-29's scope (see [Cross-reference](#cross-reference) below) — that set is not
re-authored here.

Each KEEP entry below reads: **Invariant · Where · Regression risk · Protection.**
"Protection" names a guard where one is feasible at the v1.0.8 split, or marks
the entry an affirmation-only design note to honor in review.

---

## Eval surfaces

### F-eval-05 — KEEP: candidate A/B is non-polluting; the default path is byte-identical
- **Invariant.** A prompt-override A/B run is quarantined from score-over-time and
  leaves the analyze→generate cache untouched on the default (no-override) path —
  the resolver returns the identical constant object, and the logged version stays
  `PROMPT_VERSION`. Only under an active override does it become
  `candidate:<sha256[:12]>`.
- **Where.** `analyzer.prompt_overrides()` (context manager) +
  `analyzer._BASE_SYSTEM_PROMPTS` (the name→constant registry, scoped to the named
  system-prompt constants only) + `analyzer.effective_prompt_version()`.
- **Regression risk.** An analyzer refactor that lets an override leak into the
  default path, changes the default logged version, or widens the registry to the
  dynamic user-prompt builders — any of which would pollute score-over-time or bust
  the cache.
- **Protection.** Natural guard-test candidate for the v1.0.8 split: assert
  `effective_prompt_version() == PROMPT_VERSION` and that the resolver returns the
  identical object with no override active (a byte-identity check; the same
  byte-identity discipline used for corpus-mode prompt changes per memory
  `feedback-corpus-mode-eval-coverage`).

### F-eval-06 — KEEP: manual promote + fail-closed, LLM-free annotation contract
- **Invariant.** Promotion of a winning candidate into the persona constants is a
  **manual human gate** — no auto-write into `analyzer.py` exists. The annotation
  contract validates **fail-closed** (an unsupported schema version, unknown
  verdict/slug, or a verdict missing its required payload is rejected, not
  half-collated) and is LLM-free by design.
- **Where.** `evals/annotation.py` (`validate_annotations` + the
  `_scorer_disagreements` "annotations validate the scorers" seam); the dashboard
  Tuning banner states promotion stays manual.
- **Regression risk.** "Automate promotion for convenience" (drops the C-4 human
  gate); loosening the validator to half-collate a degraded fixture instead of
  rejecting it.
- **Protection.** Affirmation-only design note + the existing annotation test suite;
  keep promotion manual and the validator fail-closed.

### F-eval-08 — KEEP: uncalibrated L1/L2 state is surfaced and tracked, not silently trusted
- **Invariant.** The deterministic L0 fabricated-specifics signal is presented as
  **flag-for-review, not a verdict/gate**; its tolerance is stamped `UNCALIBRATED`
  in code; the model-based L1/L2 NLI/MiniCheck scorers stay **eval-only** (behind
  `--grounding-signals`, never imported by the production pipeline) until PV-2
  calibrates them against real labels.
- **Where.** `hardening.compute_fabricated_specifics` (the `UNCALIBRATED`
  docstring/constant) + `evals/grounding_signals.py` (L1/L2, flag-gated in
  `evals/runner.py`).
- **Regression risk.** A dashboard polish pass that presents L1/L2 numbers as
  trustworthy verdicts before PV-2 lands; promoting L0 from flag to gate.
- **Protection.** Affirmation-only design note; this is the correct C-0 posture
  (mechanism + effort, no false trust) — do not present the numbers as verdicts
  before calibration. Tracked: PV-2 (`eval/grounding-calibration`) closes it.

### F-eval-09 — WATCH/precision: the sharpened typed L0 is eval/display-only, not yet hot-path-wired
- **Note (not a defect).** `hardening.compute_fabricated_specifics` (the sharpened
  typed L0) is called only from the eval runner + surfaced read-only in the
  dashboard; the iteration/generation hot path still uses the older lossy n-gram
  `hardening.compute_grounding_overlap`. `GROUNDING_METRIC.md`'s "per-call
  production signal" language describes a **not-yet-wired option**, not current
  behavior.
- **Why it's here.** So a follow-up agent does not assume `/api/generate` already
  logs the typed L0. If per-call production logging is wanted (for S-3), it's a
  small, deliberate wiring task — not an existing capability to lean on.

---

## BOOST

### F-eval-07 — BOOST: paid eval/tune routes are cost- and consent-gated
- **The pattern to keep and extend.** The paid power-user routes are fenced three
  ways: **localhost-only** (403 on non-localhost), **eager-4xx-before-spend** (bad
  suite / unknown user / missing seed return JSON 4xx before the worker spends a
  paid call), and a UI **cost-band `confirm()`** before POSTing (≈ $0.10 smoke /
  ≈ $0.30 full, live-updating). The seed path is contained under `ANNOTATION_ROOT`
  with `secure_filename` + `_within`.
- **Where.** `app._is_localhost_request()` gating `/api/eval/run` + `/api/tune/run`;
  the dashboard Tuning tab's cost-band confirm.
- **Why BOOST.** This is the model for fencing any future paid action on a
  power-user surface (C-1 local-and-yours + D-6 progressive-disclosure: spend is
  opt-in and disclosed). Extend this pattern, don't reinvent or weaken it — keep
  the localhost gate, the eager 4xx, and the explicit cost confirmation together.

---

## Governance surfaces

### F-gov-06 — KEEP: witness-class freshness reminder + honest sentinel
- **Invariant.** The freshness reminder always exits 0 (never blocks), emits only a
  `systemMessage` nudge, and is **honestly silent** while `docs/wiki/.last_ingest_sha`
  is the sentinel — it never makes a false "code was ingested" claim. This is the
  working "witness, not approver" precedent the amendment-ceremony /
  compliance-witness build inherits.
- **Where.** `.claude-plugin/hooks/wiki-freshness-reminder.sh`;
  `docs/wiki/.last_ingest_sha`.
- **Regression risk.** Turning a witness into a blocker, or advancing the sentinel
  to silence the signal without a real ingest.
- **Protection.** Affirmation-only design note; keep witnesses witness-class
  (always exit 0) and the sentinel honest.

### F-gov-09 — KEEP: read-only subagents are the compliance-witness precedent
- **Invariant.** The diagnose-don't-mutate subagents carry read-only tool grants
  (`Read`/`Grep`/`Glob`) and explicitly "do NOT apply the diff / output for the
  human to review"; the compliance-witness inherits this (read-only +
  no `Edit`/`Write`/`Task` — the tool grant *is* the enforcement). A witness that
  could write would not be a witness.
- **Where.** `agents/prompt-archaeologist.md`, `agents/tune-drafter.md` (read-only;
  the diff is for a human), `agents/compliance-witness.md` (read-only by tool
  grant). *(These moved to the repo-root `agents/` in Sprint 7.1 — see memory
  `reference-plugin-activation`.)*
- **Regression risk.** Granting a witness/diagnostic agent write authority "to save
  a round-trip."
- **Protection.** Affirmation-only design note; the read-only tool grant is the
  contract — keep witnesses unable to mutate.

---

## docs/wiki surfaces

### F-docs-07 — KEEP: the wiki's one grounding rule + cite/backlink/synthesis convention
- **Invariant.** The committed wiki carries one grounding rule (the same
  no-invention rule the product enforces on résumés), and the convention is *used*,
  not just declared: backlink slugs resolve, `[synthesis]` tags mark synthesized
  claims, cites prefer a symbol over a bare line number, and `llms.txt`→`index.md`→
  `overview.md` form a working front door.
- **Where.** `docs/wiki/SCHEMA.md` (the grounding rule) + the `docs/wiki/pages/`
  convention in practice.
- **Regression risk.** The v1.0.7 extraction or a WS-4b cold-ingest churning the
  convention or letting synthesis become unmarked "facts."
- **Protection.** Affirmation-only design note; the `/wiki-lint` + `/wiki-audit`
  backstop + the self-documenting loop's grounding auditor guard it operationally.

### F-docs-08 — KEEP: sentinel-honesty — `.last_ingest_sha` not falsely advanced
- **Invariant.** The wiki checkpoint is left at its honest value rather than
  advanced to silence the staleness signal before the work it claims actually ran;
  the decision is recorded, not silent. This is what makes wiki staleness
  *measurable* (sha vs HEAD) instead of discovered.
- **Where.** `docs/wiki/.last_ingest_sha` + the `docs/wiki/log.md` decision record.
- **Regression risk.** Advancing the checkpoint as a convenience to quiet the
  freshness reminder without the corresponding ingest.
- **Protection.** Affirmation-only design note; advance the checkpoint only when the
  ingest it asserts has actually run, and log why.

### F-docs-09 — KEEP: the `@import` safety condition for one-home-per-rule
- **Invariant.** Lifting each canonical rule into exactly one home (extract,
  don't register-in-place) is non-destructive **only because** agent rule-access is
  preserved via `@import` / canonical pointer — `AGENTS.md` / `CLAUDE.md` are
  harness-auto-loaded, so dropping the import would silently strip every future
  agent's guardrails.
- **Where.** `CLAUDE.md`'s `@AGENTS.md` import chain; the `docs/governance/`
  canonical homes graduated in Sprint 7.2; the governance-extraction design doc.
- **Regression risk.** A future "DRY cleanup" that removes the import/pointer, or an
  `@import`-only shell that drops inline guardrails non-Claude agents read raw.
- **Protection.** Affirmation-only design note; preserve the `@import`/pointer chain
  through any further consolidation (AGENTS.md stays inline-with-pointer, not a pure
  import shell).

---

## Open design items (deferred — logged here)

These two are the review's open design gaps, logged here as deferred design items
per PX-32 (kept in this ledger, not promoted to the RELEASE_CHECKLIST carry-forward
ledger):

- **F-gov-08 — a W-4 maturity signal per incubant.** W-4 leaves the extraction
  *maturity metric* "TBD." At present only `recall/` carries an observable
  extraction-readiness condition — "lifting `recall/` should be packaging-only *if*
  the boundary [no import of `app.py`/`analyzer.py`/DB] stays clean"
  ([`memory-architecture.md`](memory-architecture.md)), a checkable gate (the
  Sprint 8.7 boundary-lint candidate). The other four incubants (governance
  rulebook + compliance agent; the LLM-wiki self-documenting loop; the doc-grounded
  assistant; the grounding-metric three-tier pattern) have trigger-language but no
  per-system readiness signal. **Deferred design item:** propose one observable
  readiness signal per incubant, mirroring the `recall/` boundary-clean condition.
  Not v1.1.0-blocking (extraction is a post-v2 horizon, P-6).

- **F-gov-10 — the governance→assistant build-time interface.** The memory→context
  leg of the operator-stack triad is thoroughly designed (the
  AVATAR/ASSEMBLE/RETRIEVE/SOURCES stack in
  [`memory-architecture.md`](memory-architecture.md)), and the Sprint 7.5 assistant
  ships retrieving over the wiki + git with citations (`blueprints/assistant.py` +
  `analyzer.avatar_answer_streaming` / `AVATAR_SYSTEM_PROMPT`). But the
  **governance→posture** leg — the assistant's persona/capabilities/guardrails read
  *from the extracted constitution at build time* — is not yet captured in a design
  artifact: the avatar honors the deterministic-LLM boundary (C-6), but there is no
  artifact wiring the assistant's posture to `docs/governance/`. **Deferred design
  item:** capture the assistant's constitutional governance interface so a future
  iteration reads governance, not only memory.

---

## Supply-chain surfaces (OpenSSF Scorecard)

> Added 2026-07-13 (`chore/scorecard-and-docs-voice`). The first public Scorecard
> run scored **4.9/10**. The fixable checks were fixed on that branch
> (Token-Permissions, Pinned-Dependencies, SAST, Vulnerabilities, Signed-Releases).
> The two below are **accepted, reasoned gaps** — recorded here so a later reader
> doesn't mistake a 0 for an oversight, and so nobody "fixes" them by gaming the
> metric.

### SC-01 — ACCEPT: `Code-Review` scores 0 for a solo maintainer

- **The check.** Scorecard counts merged changesets that carried an approving
  review ("Found 0/16 approved changesets").
- **Why it's 0.** GitHub does not let an author approve their own pull request. A
  single-maintainer repo therefore cannot score above 0 on this check, no matter
  how it configures branch protection.
- **What we will NOT do.** Require an approval on `main` and then satisfy it with a
  second account, a bot approver, or an admin bypass. That would raise the number
  while making the claim ("changes here were reviewed by someone else") false — a
  C-0 violation, and precisely the kind of metric-gaming this ledger exists to
  prevent.
- **What we DO have instead.** Branch protection with PR-required + 4 required
  status checks (the 3 quality jobs + UX/a11y/PDF); the committed gate
  (`scripts/gate.py`); the enforcement hooks; and the read-only compliance-witness
  auditor. Revisit if a second maintainer ever joins — at that point the check
  becomes both meaningful and free.

### SC-02 — ACCEPT: `Fuzzing` scores 0 (no fuzz harness)

- **The check.** Scorecard looks for an integrated fuzzing setup (OSS-Fuzz,
  CIFuzz, a language-native fuzz target).
- **Why it's 0.** None exists. The deterministic parsing surface
  (`parser.py` · `json_resume.py` · `corpus_to_json_resume.py` · `docx_to_persona_html.py`)
  is the only part of the tree where fuzzing would pay, and it is exercised today by
  unit tests over hand-written fixtures, not generated input.
- **Position.** Reasonable future work, not a v1.1.0 blocker: this is a local-first,
  single-user tool whose parsers consume the user's *own* files, so the untrusted-input
  threat model that motivates fuzzing barely applies (see [`SECURITY.md`](../../SECURITY.md)).
  A `hypothesis`-based property suite over the deterministic parsers is the natural
  shape if it's ever wanted — logged as a candidate in [`nursery.md`](nursery.md),
  not scheduled.

---

## Cross-reference

The **security / PII** KEEP ledger — route containment (`F-sec-05`), zero-PII clone
(`F-sec-06`), the keyboard bullet-reorder a11y floor (`F-expa11y-07`), the
`_announce()` live region (`F-expa11y-08`), and the honest blocker/witness hook split
(`F-gov-04`/`F-gov-05`) — is **PX-29's** scope
(`test/keep-ledger-guards`, v1.0.8 item 8.4), where those affirmations become guard
tests. They are evidenced in the
[findings register](reviews/2026-06-product-excellence/02-assessment/findings-register.md)
and not re-authored here.

> **Count update (2026-07-14).** F-gov-04 affirmed **seven** blockers, and that was true at
> the review pin. The C-7/C-8 work has since added an eighth (`require-evidence-before-fix`)
> and a **third category** — the context hooks `restore-evidence` (SessionStart) and
> `capture-before-compact` (PreCompact), which gate nothing and carry evidence *across* a
> context boundary. The KEEP affirmation is the **honest split**, not the integer; the split
> holds, and `tests/test_governance_hooks_gate.py` is its live source of truth. The archived
> finding is left as written — it was correct when signed.
