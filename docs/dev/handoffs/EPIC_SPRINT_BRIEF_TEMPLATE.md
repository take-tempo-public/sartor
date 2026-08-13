# Epic sprint-brief template

> **Purpose:** the artifact that carries one sprint to the next **inside a running chain
> epic**. It is deliberately NOT a session handoff.
> **Audience:** the orchestrating agent of a chain epic, writing to the next sprint's agents.
> **Authoritative for:** intra-epic sprint transitions only.
>
> **Do not use this in place of `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.** That template is the
> **session-to-session** handoff at a branch close: it carries mandatory `<!-- verbatim -->`
> blocks, it is validated by `scripts/verify_doc_template.py`, it anchors the C-9 pointer
> chain — and it works. It is still required at the **epic close-out**, and any time a session
> genuinely ends.
>
> **Origin:** owner direction, 2026-08-09 — *"perhaps we need an epic handoff template that
> allows us flexibility in prompting without disrupting a very effective sprint based
> handoff."* Rationale and cadence: `docs/dev/epic-a-chain-design-corrections.md` §15.

---

## How this differs from a session handoff, and why

A chain epic establishes its **standing context once** — the design of record, the
authorization envelope, binding rules, hard constraints, close-out cadence. Re-copying ~300
lines of that into every sprint transition costs real budget and, worse, buries the sprint's
own content in boilerplate a reader skims.

So this template **points at standing context and never restates it.** What it carries is only
what changed.

**Recoverability bar — the one property this must not lose.** A fresh agent handed this brief
plus its pointers must be able to reconstruct sprint state **without reading a transcript**.
That is exactly the property the first two Epic A stops lacked. If a section below would be
empty, say so explicitly rather than deleting the heading — an absent section reads as
"nothing to report," and a deleted one reads as "never considered."

**This is a floor, not a form.** Add whatever a given sprint needs. Do not remove the
recoverability content to make it shorter.

---

## Sprint identity

- **Sprint:** `<A3 / A4 / item-N fix / …>`
- **Branch to create:** `<type>/<slug>`
- **Stacked on:** `<branch> @ <sha>` — the previous sprint's tip, **never `main`**
- **Implementer model + effort:** `<per the epic's own model table — do not guess>`

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `<path>` — **read in full; skipping this is the most expensive mistake this chain has made>` |
| Authorization envelope (run vector, halt points, flag stops, seam) | `<path §>` |
| Close-out cadence for this epic | `<path §>` |
| Sprint scope | `<RELEASE_ARC.md § …>` |

## What just landed

`<Commit shas and what they did. Include anything UNVERIFIED — say "I have not verified this"
explicitly. A clean-sounding summary that hides an open question is how a wrong premise
travels.>`

## What this sprint builds

`<Scope, from the epic's own brief. And explicitly what is OUT of scope — the chain has
already lost a sprint to scope drift.>`

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** The implementer
> verifies the named mechanism is reachable on the failing path — by reproducing the defect —
> before implementing it. B1a's brief named an unreachable guard
> (`docx_to_persona_html.py:438-444`); implemented literally, the sprint would have shipped
> green with the user-visible defect intact (run-3 retrospective, "What went wrong" #3).

## First move

`<The concrete first action. If the branch is a fix/*, the first artifact is the diagnosis
dossier's `## Observed`, never the fix.>`

## Decisions taken alone last sprint that this one inherits

`<Anything the previous sprint decided under its own authority that constrains this one.
Include reversals — if a prior decision was overturned, say what was traded.>`

## Open risks handed forward

`<Unverified claims, deferred findings, known-fragile areas. Mark each: verified / reported /
inferred. A "reported" item is a lead, not evidence.>`

## Flag-stop state

`<Anything waiting on the owner, or "none". If a halt point was hit, this is where it lives.>`

## Gate + verification state

- Last gate run: `<sha>` — `<terminal summary line, verbatim>`
- Rerun sweep: `<count of uppercase RERUN — not a bare PASSED>`
- Wiki drift at handoff: `<n of 75>` — if it exceeds the epic's deferral margin, the wiki pass
  is owed **this** sprint, not at the epic close.

---

## Close-out obligations this sprint still owes

Light-cadence sprints do **not** skip these; the epic's cadence section says which are
deferred to the epic boundary and which are not. Restate the split here so no one has to
infer it:

- **Owed now:** `<…>`
- **Deferred to epic close:** `<…>`

**If this epic declares no intra-epic close-outs at all, the epic design must carry a written
justification argument** — silence is not a permissible answer.
