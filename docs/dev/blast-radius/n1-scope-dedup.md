# Blast radius — `fix/n1-scope-dedup`

> Surface changed: the **caller args contract of `.claude/workflows/n1-baseline.mjs`**
> (`closeoutKind` removed from the caller's decision space; `epicSprintIndex` +
> `epicSprintCount` required for the sprint stage; `closeoutKind` derived).
> Not a registry-gated surface (`scripts/enforcement/blast_radius.py` — verified);
> enumerated anyway per charter C-10: it is a shared contract with doc + test
> consumers, and the ordering (enumerate before edit) is the mechanism.

## Consumers

Grep-complete over every name the contract goes by (`closeoutKind`,
`nextSprintBriefPath`; the new `epicSprintIndex`/`epicSprintCount` have zero
pre-existing consumers — verified negative): 12 files, 51 occurrences.

| Site | Decision |
|---|---|
| `.claude/workflows/n1-baseline.mjs` | EDIT — the mechanism: require + derive, reject caller `closeoutKind` by name |
| `tests/test_n1_pipeline.py` | EDIT — args-region arms flipped red-first to the new contract; new derivation pins |
| `docs/dev/n1-baseline-pipeline.md` | EDIT — args table rows + step-1 invocation text + step-9 terminal note |
| `docs/dev/handoffs/epic-b-b1b-brief.md` | EDIT — §"First move" Workflow args block (the executor's actual input) + the out-of-scope note that names closeoutKind |
| `docs/dev/handoffs/epic-b-design-brief.md` | EDIT — §"Close-out intervals" wiring note (also carries S1's scope-sentence change) |
| `docs/dev/diagnosis/n1-scope-dedup.md` | this branch's dossier — describes the change; current |
| `docs/dev/diagnosis/n1-pipeline-hardening-review.md` | this branch's review record — describes the change; current |

## Deferred (historical records — deliberately untouched, with the reason)

| Site | Reason |
|---|---|
| `docs/dev/handoffs/fix-n1-invoker-loop.md` | consumed handoff; gets ONLY the S1 superseded-banner (+ re-stamp), never a contract rewrite — item 58's post-stamp-amendment hazard |
| `docs/dev/diagnosis/n1-invoker-loop.md` | evidence record of the polish round; quotes the OLD contract as evidence, correctly |
| `docs/dev/work/items/0084-build-n1-baseline-pipeline.md` | append-only run record; new entry added, old entries immutable |
| `docs/dev/work/items/0089-sprint-brief-template-not-wired-into-n1-pipeline.md` | closed item; its `verified_by` pins the closer-ceremony BRANCH (which S2 keeps — only the arg's origin changes) |
| `docs/dev/work/BOARD.md` | generated file; regenerated only if `work_items check` requires it at the gate |

Negative results recorded: no matches in `docs/wiki/**`, `scripts/**`,
`hooks/**`, `agents/**`, `commands/**`, `.claude/settings.json`.
