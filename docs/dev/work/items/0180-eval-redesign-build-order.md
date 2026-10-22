```toml
schema = 1
id = 180
kind = "epic"
title = "Eval redesign build order"
status = "open"
decision_owner = "agent"
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Build the eval redesign (design doc section 9): steps 1-10 are items 181-190, step 11 is item 137."
```

Filed 2026-10-20 after the owner answered the eight decisions in the design doc's section 8.
The scope, the order and the reason for each step live in that doc; this epic does not restate them.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

Step 1 (item 181) is open; steps 2 to 10 are blocked, each on the one before. Item 137 (the
Haiku 5.5 A/B, step 11) is a child of this epic and depends on step 10.

### 2026-10-21 -- step 1 closed, step 2 built on feat/eval-catalog-skeleton

Step 1 (item 181) merged as PR #198 and is closed. Step 2 (item 182) is built on `feat/eval-catalog-skeleton` and waits on its own PR; item 183 (step 3) stays blocked until it lands. Three findings from building step 2 that belong to the build order, not to one item:

- **No step covers a single-call eval of `generate` or `generate_cover_letter`.** Section 9 names the kinds of steps 4 to 6 and neither is in them; their catalog entries are `covered` through the finished document only. Owner's call whether a step should add one (decision_owner stays with the agent for the epic; this one is the owner's).
- **`--max-spend`'s pre-flight cannot price an unmeasured kind**, and both judge kinds are unmeasured until a paid run writes judge rows to the call log. The runtime cap bounds them. Re-run `python -m evals.eval_catalog measure --write` after the first paid run (step 3's calibration run) so the estimate prices the judge.
- **`evals/catalog/costs.json` holds one machine's token means.** Step 3's calibration run on the standard dataset is what makes them a shared figure.
