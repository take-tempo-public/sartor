```toml
schema = 1
id = 68
kind = "item"
title = "The Step-5 lock reason names Compose only — wrong for an empty analyze-time `career_corpus`, where recovery is outside the rail"
status = "watching"
decision_owner = "user"
refs = [
  "static/app.js",
  "hardening.py",
  "docs/dev/diagnosis/wizard-rail-frozen-composition-gate.md",
]
summary = "One lock message covers two refusal causes; telling them apart needs the server to say WHY, a payload change."
```

**The message.** `_wizardLockReason(5)` says: *"Save your composition in Compose (step 3)
first — Generate builds the documents from exactly what you approved there."* It is the
text on both the refusal toast and the greyed rail button's `title`, and it is a strict
improvement over the generic "Run ANALYZE first (step 1)" it replaced.

**It is right for one of the two ways Step 5 can be locked, and wrong for the other.**
`hardening.frozen_composition_doc` returns `None` on three conditions, which collapse
into two user-visible causes:

1. **No assemblable frozen document** — Compose was skipped, or Save-and-continue
   produced a contentless document. Recovery *is* Compose. The message is correct.
2. **Empty analyze-time `career_corpus`** — the candidate had zero active roles when
   analyze ran, so the snapshot is `[]` however diligently they then work in Compose.
   Recovery is **outside the rail entirely**: open the Career Corpus top tab, add or
   un-retire a role, then re-run analyze (step 1) to take a fresh snapshot. Following the
   message here sends the user to a step that cannot possibly unlock the one they want —
   the worst kind of wrong instruction, because it looks actionable.

Case 2 is not hypothetical: it is the exact scenario item 20's tightened predicate
deliberately locks out (see item 67), and A1b's role-level soft-retire makes "every role
retired" a state a user can reach in a few clicks.

**Why this is not a copy edit.** The client cannot tell the two cases apart. It holds one
boolean, `_compositionFrozen`, sourced from the server's answer to a yes/no question. The
server knows *which* of the three conditions failed and does not say. Distinguishing them
means widening what `/api/applications/<id>` and the `/composition` POST return — a
reason code alongside the boolean — which is a payload-shape change to a shared contract,
with the consumer enumeration (C-10) and the OpenAPI surface that implies. That is why
this was deferred out of the item-20 sprint rather than patched with a guess.

**A cheaper option exists and is not obviously worse** (neither evaluated nor endorsed):
leave the payload alone and widen the message to name both recoveries in one sentence.
It costs nothing and is never actively wrong, but it makes every locked user read a
branch that applies to one of them. Whether the honest-but-noisy message or the
structured reason code is the right trade is a product-voice decision — hence
`decision_owner = "user"`.

## Updates

### 2026-08-09 — filed at `fix/wizard-rail-frozen-composition-gate` close-out (Epic A, item 20 sprint)

Deferred out of the item-20 sprint, which recorded it in the commit message as filed not
fixed. No `epic` pointer set, matching items 63–67.
