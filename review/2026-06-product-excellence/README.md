---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Product Excellence Review — 2026-06 (pre-v1.1.0)

> **This is a review artifact, not canonical documentation.** Nothing in this
> directory is authoritative until it graduates — explicitly, via the
> [graduation manifest](04-final/graduation-manifest.md) — into `docs/`
> through a normal dev branch. These pages are NOT wiki pages and must never
> be ingested by `/wiki-ingest` (they would violate the wiki's provenance
> model in `docs/wiki/SCHEMA.md`).

A surgical, prescriptive product evaluation ahead of the v1.1.0 public
release. All evidence is pinned at commit `c6e0437` (main, 2026-06-12);
a drift check against then-current main runs once, in Phase 5. The review
operates witness-only: it cites, it prescribes, it never edits existing
files — deliberately modeling the compliance-agent posture it evaluates.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Setup: worktree, branch, scaffold | ✅ done (2026-06-12) |
| 1 | Discovery interview → signed Product Charter | 🔄 in progress |
| 2 | Domain guides ×8, product map, question bank | ⬜ pending |
| 3 | Evidence assessment + adversarial verification | ⬜ pending |
| 4 | Prescriptions, governance draft, overlays, compliance-agent design | ⬜ pending |
| 5 | Drift check, final assessment, graduation manifest | ⬜ pending |

## Directory map

```
00-interview/   interview-record.md, product-charter.md (owner-signed rubric)
01-maps/        product-map.md, domain-guides/<domain>.md ×8, question-bank.md
02-assessment/  findings/<domain>.md ×8, findings-register.md, verification-log.md
03-prescriptions/
                prescriptions.md, release-pass-plan.md, timeline-overlay.md,
                governance-draft/ (constitution, metrics-and-rubrics,
                enforcement-practices), extraction-playbook.md,
                compliance-agent-design.md, wiki-architecture-proposal.md
04-final/       assessment.md, graduation-manifest.md
```

## Domains (8)

1. Product vision & definition
2. Architecture & code health
3. Product experience & accessibility (a11y co-equal track)
4. Quality engineering & release discipline
5. Eval / grounding / tuning as product
6. Open-source readiness, security & privacy
7. Documentation & wiki architecture
8. Governance, memory & incubation

## Conventions

- Front-matter on every file: `status: review-artifact`, `evidence_sha`,
  `graduation: none | <target path>`.
- Findings: `F-<domain>-<nn>`, evidence as `path:line@c6e0437` / commit /
  doc section; disposition BOOST / FIX / DEBUFF / KEEP / WATCH; leverage
  P0 (blocks v1.1.0) / P1 (before public) / P2 (post-public) / P3
  (opportunistic). Prescriptions: `PX-<nn>`, each naming one landing spot
  in the release arc.
- Process plan of record: approved 2026-06-12 (owner). Checkpoints gate
  every phase; the owner may stop or redirect at any checkpoint.
