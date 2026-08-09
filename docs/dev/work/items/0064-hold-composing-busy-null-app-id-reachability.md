```toml
schema = 1
id = 64
kind = "item"
title = "Open question: is the `_composeApplicationId == null` strand actually reachable, or is the A2 guard defending an impossible state?"
status = "watching"
decision_owner = "agent"
refs = [
  "static/app.js",
  "docs/dev/blast-radius/compose-wait-ux.md",
]
summary = "A2 guarded a confirmed mechanism whose reachability was never established — the question, not a bug claim."
```

**Found by the sprint A2 adversarial review. Fixed defensively in `2a0b37a`.
Reachability was NOT established — this item files the open question, not a bug.**

**The mechanism (confirmed, by reading).** `_fireRecommendThenCompose` ends by raising the
Compose arrival hold:

```js
if (_wizardStep === 3 && _composeApplicationId != null) _holdComposingBusy();
```

`loadComposition()` is `async`, so the fire-and-forget call above it runs its body
synchronously only up to the first `await`. Its `_composeApplicationId == null` early
return is **the one exit with no `await` before it** — on that path the entire function,
including its own `_settleComposeIfIdle()` (which flushes an empty waiter list), has
already returned by the time the hold would be raised. A hold raised at that moment has
nothing left to flush it, and the "Composing your tailored résumé" banner would sit over a
usable page until `_COMPOSE_SETTLE_CAP_MS` (20 s) expires. That reasoning is sound and the
`_composeApplicationId != null` half of the guard closes it.

**What was NOT established: that any live path reaches it.** The guard only matters when
`lastContextPath` is truthy (otherwise `loadComposition` takes a different exit) *while*
`_composeApplicationId` is null *at that line*. No such path was found. The search was
reading, not instrumentation — no probe was added, no run was observed taking it, and
absence-of-a-found-path is not proof of absence.

**Why this is filed as a question and not a defect.** Per C-7, a mechanism found by reading
is a hypothesis. Two outcomes are live and they want opposite responses:

1. **Reachable** — then this is a real (if rare) stranded-banner bug that pre-dated A2 in
   latent form, and it deserves a reproduction plus a regression test pinning it.
2. **Unreachable** — then the guard is dead weight asserting an invariant nobody has
   written down, and the honest repair is to *state the invariant* (`_composeApplicationId`
   is non-null whenever `lastContextPath` is, at this point in the flow) and let the guard
   cite it, or drop the guard and assert the invariant instead.

**Deliberately kept as-is for now.** The guard costs one comparison and cannot itself
misbehave; removing it on the strength of "we could not find a path" would be the same
unsourced-narrowing move C-12 exists to prevent. The comment at the call site already
records the honest state — that it "closes the logic hole, it is not a fix to an observed
failure" — so the code does not overclaim.

**What settling this looks like.** Enumerate every assignment to and clear of
`_composeApplicationId` and of `lastContextPath`, and identify whether any ordering leaves
them disagreeing when `_fireRecommendThenCompose` reaches its final line — in particular
around application switching, user switching, and a failed/rejected recommend POST. A
temporary console probe at the guard, run across the compose UX modules, would answer it
empirically and cheaply.

## Updates

### 2026-08-09 — filed at `feat/compose-wait-ux` close-out (Epic A, sprint A2)

Filed by the A2 closer. The fix shipped in `2a0b37a`; this item exists so the *unproven*
half of it is visible rather than absorbed into the branch as though it were established.
