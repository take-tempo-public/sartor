---
status: review-artifact
evidence_sha: c6e0437
graduation: docs/wiki/ planning + docs/dev/ (v1.0.7 / WS-4b)
---

# Wiki architecture proposal — sartor.

> Discovery-brief ask #8. Evaluates the committed `docs/wiki/` against its
> own [`SCHEMA.md`](../../../docs/wiki/SCHEMA.md), then proposes
> document-architecture changes, the missing docs, and how the wiki
> relates to the governance extraction and the `recall/` memory substrate.
> Severity anchor: the SIGNED Product Charter
> ([`../00-interview/product-charter.md`](../00-interview/product-charter.md)).
> Evidence cited by F-id from the
> [findings register](../02-assessment/findings-register.md) +
> [verification log](../02-assessment/verification-log.md); WEAKENED
> findings carry their revised claim. Assessment is at the pin `c6e0437`;
> main has since moved (Sprint 6.4 + 6.6), and WS-4b is sequenced *after*
> Sprint 6.6 — so the code cold pass has not run at the pin by design.
> Honors C-0 and SCHEMA.md's own grounding rule: this page describes the
> wiki and cites its sources; it does not assert past them.

---

## 1. Wiki state assessment

**What works — the grounding rule is genuinely practiced, not aspirational.**
SCHEMA.md states one load-bearing invariant — *a wiki page may not assert
anything its cited sources do not support* — and the seeded population
honors it. `F-docs-07` (KEEP) verifies the convention by construction: all
8/8 `[[backlink]]` slugs resolve, every relative link target resolves
(22/22 per `log.md`), and `[synthesis]` tags appear 1–5 per page marking
concluded-vs-quoted claims for later audit. This is the project's own
product-grounding contract (C-3) turned on its documentation, and it is the
A-4 "whoa, this is robust" exhibit working as designed: the wiki *selects,
condenses, and connects* without inventing past source.

**What works — the sentinel is honest.** `F-docs-08` (KEEP) verifies the
single most trust-building decision in the wiki's short history:
`.last_ingest_sha` was deliberately **left at the sentinel** after the
2026-06-09 excellence-walk ingest rather than advanced. That ingest was a
*docs* pass, not a *code* pass; advancing the checkpoint would have falsely
asserted the code had been ingested and prematurely silenced the
commit-time freshness reminder before WS-4b ever runs (`log.md`
2026-06-09). The witness-class freshness reminder plus the un-advanced
sentinel together form a working amendment-ceremony precedent
(`F-gov-06`, KEEP): a soft-commitment posture (P-3, D-4) where the gate
keeps itself honest rather than relying on a human promise.

**What is untested — and the wiki itself says so.** Two gaps are real, and
both are correctly disclosed rather than hidden:

- **WS-4b code cold-ingest has never run.** `F-docs-10` (WATCH) records
  that the whole-repo code pass — module map, the P1 deterministic/LLM
  boundary, the `context_set` contract, pipeline flows, routes, the eval
  harness — is **not yet ingested**; `index.md` flags it as reserved. The
  grounding rule has been exercised only over a small, curated docs source
  (8 pages from one frozen capture), **not at module scale** over churning
  `path:line`-cited code.
- **Rot-detection has never fired.** Because `.last_ingest_sha` carries no
  40-char SHA, the `sha → HEAD` staleness check has *never executed*
  (`F-docs-10`). The freshness reminder is verified **silent**, not
  verified *working* — it has correctly stayed quiet, but its alarm path is
  unexercised. The honest sentinel is a strength; the untested alarm is the
  matching liability, and they are the same fact seen from two sides.

Net: the wiki's *conventions* are proven on a small corpus; its *engine at
scale* (code-grounded synthesis + drift detection) is designed, seeded, and
sequenced, but unfired. That is exactly the posture SCHEMA.md claims
("Skeleton only") — the gap is disclosed, not latent.

## 2. Document-architecture proposal — the public/internal boundary

The charter's A-2 axis is a **continuum** (user → power-user → dev), not
two populations, and the wiki should encode that continuum as a *first-class
metadata dimension*, not a folder split. The mechanism already exists in the
plan: WS-4b stamps each page with an `audience:` tag (`user | dev`), authored
once and consumed by three beneficiaries — the wiki, the 6.5 user/dev
education sweep, and the assistant's access plane
([`memory-architecture.md`](../../../docs/dev/memory-architecture.md)
decision #2; RELEASE_ARC §Phase 4.5). Proposal:

- **Make `audience:` a required front-matter field in SCHEMA.md's page
  conventions**, not an implicit path rule introduced only at ingest. A page
  without an audience tag should lint as an ERROR once WS-4b lands. This
  turns the A-2 continuum into a machine-checkable property (P-3/D-4: a gate,
  not a promise) rather than a reviewer's judgment call.
- **Reserve the user-facing section now, in `index.md`, as a named slot.**
  RELEASE_ARC §Phase 4.5 already directs WS-4b to "reserve a user-facing
  section that Sprint 6.5 authors into"; the M-2 v1.0.7 criterion names the
  user-facing *"how sartor. grounds, clarifies, and tunes"* page
  explicitly. That slot should appear in `index.md` as a reserved entry
  today so the obligation is visible and the assistant has a stable retrieval
  target. This page is also the natural home for S-3 — the owner's
  self-named furthest-below-bar area (`F-eval-03`, `F-expa11y-04`): the lay
  metrics legend and the grounding/clarify/tune explanation are the same
  user-altitude content.

**Where the support agent gets its sourceable, current self-description.**
The charter's P-3 posture names a support agent (the doc-grounded assistant,
v1.0.7) that "can help a dev or agent-savvy user understand whatever it knows
about itself." The assistant retrieves over the wiki as its S1 tier
([`memory-architecture.md`](../../../docs/dev/memory-architecture.md): "WS-4b
code-ingest feeds S1"). Therefore the wiki *is* the assistant's
self-description, and two properties become load-bearing: **(a) it must be
current** — which is precisely what the sentinel + freshness reminder exist
to police, and what WS-4b first makes meaningful; **(b) it must be
audience-scoped** — the access plane gates dev-tier spans behind the user/dev
toggle, so the `audience:` tag is not cosmetic but the authorization seam the
assistant disposes against (`memory-architecture.md` access plane;
"detected depth proposes, the access plane disposes"). The proposal: treat
the wiki's currency and audience-tagging as the assistant's **correctness
preconditions**, documented as such on the reserved user-facing page's dev
counterpart, so a future agent building `feat/doc-assistant` reads one place
that says *what the assistant may say and how it stays true*.

## 3. Missing docs

These are absent at the pin and each is charter-traceable. None should be a
recurring human-labor obligation (D-4); each is a one-time artifact or a
machine-checkable file.

- **ACCESSIBILITY.md** — `F-expa11y-03` (CONFIRMED): no honest-status a11y
  page exists at `c6e0437`, and it is **not scheduled anywhere in
  RELEASE_ARC** at the pin. The charter (E-2) wants it explicitly as a
  status page with *no conformance claim, no tag gate, no recurring
  manual-audit promise* — i.e. exactly the soft-commitment shape. Schedule it
  to v1.0.7 / Sprint 6.5 and give it a reserved `index.md`/wiki backlink.
- **PRIVACY.md** — `F-sec-09` (WATCH) lists it among the absent E-2
  artifacts. It is the natural home for the C-2 two-class egress enumeration
  (configured LLM provider + optional profile/website scrape) and for naming
  the sanctioned power-user opt-in (the ~3.2 GB HF eval-grounding download,
  C-2(ii)/D-6). Writing it also closes the egress-enumeration drift the
  public docs currently carry (`F-sec-04`, `F-docs-01`).
- **The eval-stack install guide** — `F-docs-06` (FIX): the Sprint 6.5
  eval-stack install guide *does not exist*; the ~3.2 GB HF opt-in is
  documented only in a `docs/dev/` page and one wiki provenance page. D-6
  (per-system bundling, progressively disclosed) wants this as a threaded,
  power-user install doc — not folded into base prerequisites. Note the
  adjacent **Chromium classification drift** (`F-docs-05`, WEAKENED → ~P3):
  the real action is *reconciling* how Chromium is classified across
  install.md / README / the `non-dependency-downloads` wiki page (basic-tool
  vs dev-only — the docs disagree with each other), not asserting any one doc
  violates D-6.
- **CREDITS / REUSE (machine-readable license declaration)** — `F-sec-08`
  (FIX) and `F-qe-rel-03` (CONFIRMED): the vendored axe asset is MPL-2.0
  while LICENSE is MIT-only; the prose declaration exists
  (`tests/ux/a11y/vendor/README.md`) but the machine-readable REUSE/SPDX form
  does not. Per the verification log's tightening on `F-qe-rel-03`, REUSE
  adds *machine-readable/aggregated* declaration, not first-time honesty —
  frame it that way (D-5 credits-upstreams default), not as a correction of a
  dishonest state.

## 4. Governance + memory guidance

**Wiki ↔ governance extraction.** The wiki and the governance home are two
strata of the same Memory/Governance split (`overview.md` seven-functions;
[`governance-extraction.md`](../../../docs/wiki/pages/governance-extraction.md)).
The discipline to preserve is *one job per rule-bearing doc*: SCHEMA.md's D5
fork already states the binding rules **once**, in their canonical homes, and
the wiki only **cites** them — "on any conflict the canonical docs win, and
the wiki is the thing that is wrong." `F-gov-05` and `F-docs-09` (both KEEP)
verify the governance-extraction design is register-grade and records the
**load-bearing `@import` safety condition**: `AGENTS.md`/`CLAUDE.md` are
harness-auto-loaded, so the extraction must preserve agent rule-access via
`@import` (CLAUDE.md already does `@AGENTS.md`) — *or every future agent
loses its guardrails*. Guidance: **the wiki must never become a second copy
of a rule.** When the governance home lands (v1.0.7, Phase 4.7), the wiki's
job is to *cite and audit* it — `/wiki-lint` / `/wiki-audit` checking whether
the descriptive layer (code, synthesized pages) has drifted from the
prescriptive constitution — not to restate it. The `raw/` constitutional
layer stays at zero in the wiki (SCHEMA.md; `log.md` 2026-06-09): in a git
repo every tracked doc already *is* a raw layer, so copying a live doc into
`raw/` would be pure duplication and rot.

**Wiki ↔ the `recall/` memory substrate.** The wiki is S1 (the
wiki-synthesis tier) in the `recall/` stack — the *vocabulary-bridge and map*
the assistant retrieves over first, before dropping to S2 (`git grep` →
exact `path:line`)
([`memory-architecture.md`](../../../docs/dev/memory-architecture.md) tiers
table). The provenance plane there is the *same spine* as SCHEMA.md's
grounding rule: every `Unit` carries `(tier, source_id, path:line, audience,
sha)`, retrieval returns source units never rewritten facts, and the avatar
must cite them. Guidance: keep these two grounding contracts **deliberately
identical** — the wiki's `path:line` + `[[backlink]]` + `[synthesis]`
convention and `recall/`'s provenance stamp are one invariant expressed at
two altitudes, so a page that passes `/wiki-audit` is also a trustworthy
retrieval unit. The interaction-memory family (S5) is the *one genuinely
personal* tier — local, gitignored, user-clearable, never egress — and must
stay outside the wiki (it is about *you*, not about the system); its
retention/forgetting policy is the open gate on pulling S5 P2–P4 forward and
should not be rushed (`memory-architecture.md` "Still genuinely open").

## 5. WS-4b sequencing guidance

WS-4b (`wiki/cold-ingest-code`) is sequenced **after Sprint 6.6** so the cold
pass also captures the B.4/B.5 corpus-completer Compose cards and runs
against settled route-churn (RELEASE_ARC §Phase 4.5, re-sequenced
2026-06-12). Two guidance points layer onto that:

- **Ingest *corrected* code, not the pinned state.** Several C-2 corrections
  land in v1.0.6 *before* WS-4b: PX-01 vendors Chart.js
  (`F-sec-03`/`F-docs-02`/`F-vision-05`), PX-02 re-wires the dead profile
  scrape (`F-docs-04`), PX-03 corrects the egress enumeration
  (`F-sec-04`/`F-docs-01`). If WS-4b ingested `c6e0437` as-is, the wiki would
  faithfully synthesize *known-wrong* facts — a CDN fetch, a live scrape that
  is dead code, a phantom JD-URL egress class. Guidance: **WS-4b must ingest
  the post-PX-01/02/03 tree**, so the first code-grounded pages inherit the
  corrected reality rather than the pinned drift. (Phase 5 of this review
  reconciles the assessment-time drift; WS-4b is where the *wiki* must not
  re-import it.)
- **Treat the cold pass as the first grounding-rule-at-scale test.** The
  excellence-walk ingest proved the conventions on 8 curated docs; WS-4b is
  the first time the *one grounding rule* meets module-scale code with
  `path:line` cites that drift (SCHEMA.md warns line numbers drift; prefer a
  symbol/anchor). It is also the first time `.last_ingest_sha` advances off
  its sentinel — the moment the `sha → HEAD` rot-detection path *fires for
  the first time* (`F-docs-10`). Guidance: gate WS-4b's merge on a
  `/wiki-audit` of a sample of the new code pages against their cited sources
  (the audit already SUPPORTED the two excellence-walk pages it ran on per
  `log.md`), and on the freshness reminder demonstrably *un-silencing* when
  HEAD moves past the freshly-written SHA — so the alarm path is verified
  *working*, not merely verified silent. `F-vision-08` (KEEP) confirms
  `system-model.md` is the canonical seed for `overview.md`; WS-4b should keep
  that deferral (overview defers to system-model) and not duplicate the
  seven-functions vocabulary into the code-ingested pages.

---

**Severity framing.** None of the above proposes a recurring human-promise
SLA (D-4): the `audience:` tag is a lint gate, the missing docs are one-time
artifacts or machine-readable files, and the wiki↔governance↔recall
grounding is a single machine-auditable invariant. The wiki's existing
honesty — the un-advanced sentinel, the `[synthesis]` tags, the "canonical
docs win" deference — is the affirm-and-protect ledger (`F-docs-07/08/09`,
`F-gov-06`): it must survive WS-4b and the v1.0.7 governance extraction
intact.
