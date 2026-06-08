# Excellence-walk — preserved raw source

> **What this is.** The full, verbatim capture from the 2026-06-07 "excellence
> walk" (a codebase self-assessment + an engineering-excellence design pass),
> **promoted on 2026-06-08** from gitignored scratch (`output/_dev-notes/`) into
> tracked source so nothing is lost. The scratch originals were deleted after this
> copy — git now holds the only copy.
> **Status.** Raw / undistilled. The *decisions* from this walk are already folded
> into the durable planning docs (see "Where it landed"); the *prose and the whys*
> live here until the **WS-4 wiki** ingests and decomposes them into proper pages
> (planned early in the v1.0.6 epic — "WS-4a"). Treat this as the wiki's `raw/`
> constitutional source: cite it, then let the wiki synthesize it.
> **Do not hand-edit to "improve" it** — it is a faithful record. Corrections and
> synthesis happen in the wiki pages it feeds, not here.

---

## Contents

| File | What it is |
|---|---|
| [`excellence-walk.md`](excellence-walk.md) | The master capture (65K): the **seven-functions system language** + its full derivation, the WS-1…WS-4 backlog, the five-question results, the **WS-4 LLM-wiki + Governance-extraction design**, and the live decisions log. The richest source of *why*. |
| [`q1-overview.md`](q1-overview.md) | Q1 deliverable — the layman architecture overview, written in the seven-functions language; carries 4 open revision points in its footer. |
| [`q2-consistency.md`](q2-consistency.md) | Q2 deliverable — the consistency audit ("consistency tracks enforcement") + per-area grade table. |
| [`q3-downloads.md`](q3-downloads.md) | Q3 deliverable — the verified "what gets downloaded & why" provenance table (sizes, licenses, cache paths). |
| [`walkthrough-sprint-plan.md`](walkthrough-sprint-plan.md) | The v1.0.5 walk-through → sprint plan (24 findings → topical sprints). Its content is fully folded into `RELEASE_ARC.md`; kept here for provenance. |

## Where it landed (decisions — already durable)

- **Realization plan / epic ladder** → [`../RELEASE_ARC.md`](../RELEASE_ARC.md) (the 1.0.6 → 1.1.0 epics + post-public 1.1.x).
- **Release gates** → [`../RELEASE_CHECKLIST.md`](../RELEASE_CHECKLIST.md).
- **System self-model + workstreams (WS-1…WS-4) + the Q2 finding** → [`../../PRODUCT_SHAPE.md`](../../PRODUCT_SHAPE.md) §11.
- **Deferred feature ideas** → [`../nursery.md`](../nursery.md).

## Where it's *going* (prose — scheduled)

- Seven-functions language → **`docs/system-model.md`** (authored in WS-4a, v1.0.6).
- `q1-overview.md` → the wiki **`overview.md`** (WS-4a); carry its 4 revision points.
- `q3-downloads.md` → the **Sprint 6.5 install guide** (`docs/eval-stack-install-guide`) + a README/`install.md` section.
- `excellence-walk.md` (full reasoning) → ingested by the wiki as `raw/` and synthesized into module/concept/flow pages (WS-4a/WS-4b).
