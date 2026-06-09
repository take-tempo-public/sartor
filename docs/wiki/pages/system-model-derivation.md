# How the system model was found

> **Concept:** the form-finding journey behind the seven-functions self-model — the
> lenses tried, the moves that worked, and why the settled vocabulary looks the way it
> does. The *result* is canonical elsewhere; this page is the *why*.
> **Defers to:** [`../../system-model.md`](../../system-model.md) (the canonical
> seven functions + one law) and [`../overview.md`](../overview.md) (the same at wiki
> altitude). This page does **not** restate the settled table — read those for it.
> **Sources:** [`excellence-walk.md`](../../dev/excellence-walk/excellence-walk.md)
> "Q1 — WORKING" · [`q1-overview.md`](../../dev/excellence-walk/q1-overview.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The starting problem: the binary was insufficient

Q1 began as "describe the architecture *and* the scaffolding to a layman," but that
**binary was judged insufficient** — it could not place the parts cleanly. The eval
harness, for instance, is not "scaffolding": it is a functional system in its own right.
So the walk set out to **find a rudimentary descriptive language** for the system that
maps elegantly onto what already exists `[synthesis]`.

Two scope refinements were locked early and survived into the final model:

- **The load-bearing test.** Architecture is what *stands on its own*; remove the rest
  and it still stands. (This became the Product / Work split.)
- **The dependency-direction rule.** A thing is "outer" only if it is *exclusive to the
  shaping process*: outer layers **may use** the core, the core **may not use** them —
  directional and acyclic.

## The "aha": the codebase's own law, scaled up

The dependency-direction rule was recognized as **the codebase's own internal law scaled
to the whole system** — the same one-way discipline already enforced in code
(deterministic core ↛ AI layer ↛ web layer; production ↛ the eval tooling). That is
*why* the model maps so cleanly onto what is there: the categories **inherit the
architecture's existing dependency discipline** rather than importing an outside frame
`[synthesis]`. The settled statement of this law lives in
[`../../system-model.md`](../../system-model.md).

## Three discovery lenses (used to find the model, not to name it)

| Lens | What it offered | Why it was not adopted as the vocabulary |
|---|---|---|
| **Estate** (house / workshop / utilities / blueprint / build-rig) | layman-friendly spatial picture | a *metaphor* (a picture that misleads — e.g. "scaffolding" smuggled in "temporary," false for permanent hooks) |
| **Dependency law** (strict directional layers) | rigorous, codebase-native, LLM-friendly | dry on its own; became the **spine** |
| **Ecology** (metabolism / fauna / homeostasis / selective pressure) | cracked several things open (below) | nature has *no designer* — so it strains exactly at Governance |

The decisive principle was **metaphor → analogue**: prefer *internal* analogues
(describe each role by correspondence to the system's *own* trusted laws — one-way
dependency, the deterministic/LLM boundary, grounding's source-vs-synthesis) over
borrowed external pictures. External metaphors are disposable skins, kept only where the
correspondence is exact `[synthesis]`.

## What ecology cracked open (harvested as insight, not vocabulary)

Ecology was the strongest *discovery lens*, and three of its findings were folded into
the settled model while its vocabulary was discarded:

- **User data is in the model**, not out-of-scope furniture — the corpus/configs/output
  are the **Substrate** (accumulated material the system metabolizes).
- **Knowledge is pulled, not pushed** — "Distribution" was wrong; the function is
  **Memory** (recalled when needed).
- **Operators and evaluators are active, first-class** — not a passive "observer axis";
  agents reshape the system (**Operation**) and the eval harness actively drives fixes
  (**Evaluation**).

**The honest seam:** ecology has no designer, so **Governance** is where the ecological
reading strains — best read as the *selective pressure / fitness target* the system is
measured against, not something it evolves on its own. The seam is **named, not papered
over**; it survives into the canonical model as the one deliberately *prescribed* layer.

## The sort exercise — friction cases were the gold

Running the real tracked surface through the model surfaced edge cases that *sharpened*
it `[synthesis]`:

- **Co-location ≠ category** — `dashboard/` lives in the product's Flask app but is
  **Evaluation** by dependency; sort by dependency, not by where a file sits.
- **The recurring cross-layer flow** — the Work *manufactures parts installed into the
  Product* (a tuning loop produces a prompt candidate), always through a human-gated
  **Regulation** step (promote + `PROMPT_VERSION` bump). One real workflow legally
  crosses Work → Product under supervision.
- **Mixed docs split across roles** — one file (e.g. the agent contract) can be Memory +
  prescriptive rule + the definition of a gate at once. This is **the same problem** the
  wiki's [[governance-extraction]] later resolves.
- **Double home by hot-path discipline** — runtime grounding/security live in the
  Product; their eval-time cousins live in the Work — same concept, two homes by the
  hot-path rule.

## The reframe it forced: two organisms, one charter

"Load-bearing" was ambiguous until the model named *for which subject*. The resolution is
the **Product / Work split** (which is literally Q5's "as a product AND as a work"):
the **Product** is what the user runs; the **Work** is everything that produces and
evolves it; **Governance** governs the Work. The settled form of this split — and the
final seven function-nouns it produced — is canonical in
[`../../system-model.md`](../../system-model.md); the four still-open framing calls it
left (the Governance honesty note, the "AI agents are first-class" line, the file map,
the opening) are carried in [`../overview.md`](../overview.md).

## Related

- [[excellence-walk]] — the walk this derivation belongs to.
- [[engineering-workstreams]] — the same lenses surfaced the WS-1/WS-2 gaps.
- [[governance-extraction]] — the "mixed docs" friction case, resolved.
