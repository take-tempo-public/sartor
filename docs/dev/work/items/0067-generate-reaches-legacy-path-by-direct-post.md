```toml
schema = 1
id = 67
kind = "item"
title = "`/api/generate` still reaches the legacy full-LLM `generate()` by direct POST, outside the Step-5 rail gate"
status = "watching"
decision_owner = "user"
refs = [
  "blueprints/generation.py",
  "tests/test_application_routes.py",
  "docs/dev/diagnosis/wizard-rail-frozen-composition-gate.md",
]
summary = "The rail is the gate; the server fallback is the floor. Filed so the surface is tracked, not assumed closed."
```

**What is still reachable.** Item 20 hard-gated the Step-5 *wizard rail* on
`hardening.frozen_composition_doc`, so the UI no longer offers Generate to a corpus-mode
user who skipped Compose. It did not change `/api/generate` itself: a POST straight to
the route with a context path and no assemblable `approved_composition` still falls
through to the legacy full-LLM `generate()`, exactly as before.

**This is deliberate, and the shape is worth stating once.** The rail is the **gate** —
it is what stops an ordinary user from walking into a non-deterministic run under copy
promising determinism. The server branch is the **floor** — it is what keeps every
context that cannot be assembled from failing outright. Removing the floor would break
real, legitimate callers:

- a **legacy file-based context** (no `career_corpus` at all), which has no frozen
  composition by construction and never will;
- a **candidate with zero active roles at analyze time**, whose `career_corpus` snapshot
  is `[]` — the case item 20's own tightened predicate deliberately locks out of the
  rail, precisely because that run *does* need the LLM path;
- `evals/runner.py`, which imports `_frozen_composition` and
  `_assemble_from_frozen_composition` by name and exercises both branches.

**Two committed tests pin the fallback**, so removing it would fail loudly rather than
quietly:
`tests/test_application_routes.py::TestResumeState::test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_document`
and `…::test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_corpus`. Each asserts
the *agreement* between the rail's answer and the assemble gate's, not two independent
expectations.

**Why file it at all.** A gate that lives in the client is not a server-side guarantee,
and "item 20 closed the legacy path" is the kind of summary that becomes a premise
(charter C-12). It did not: it closed the *route through the UI*. Anyone later reasoning
about C-6 determinism, prompt-cost accounting, or a security-boundary claim needs the
surface tracked, not assumed shut.

**The open question is the owner's**, which is what `decision_owner = "user"` records:
whether the floor should stay indefinitely, or whether corpus-mode contexts should
eventually get a hard server-side refusal (`409`) with the legacy path reserved for
file-based contexts alone. That is a product-behavior decision about what a corpus-mode
user with zero active roles is entitled to, not a mechanical cleanup.

## Updates

### 2026-08-09 — filed at `fix/wizard-rail-frozen-composition-gate` close-out (Epic A, item 20 sprint)

Filed by the sprint closer so the surface is tracked rather than inferred closed from
item 20's title. No `epic` pointer set, matching items 63–66.
