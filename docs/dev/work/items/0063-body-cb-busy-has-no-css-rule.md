```toml
schema = 1
id = 63
kind = "item"
title = "`body.cb-busy` has no CSS rule — `_setBusy` blocks no input anywhere in the app despite its \"don't navigate away\" copy"
status = "watching"
decision_owner = "user"
refs = [
  "static/app.js",
  "static/style.css",
  "docs/dev/blast-radius/compose-wait-ux.md",
]
summary = "`_setBusy` adds `body.cb-busy`, but no rule matches it — the busy banner is cosmetic, not blocking."
```

**Found by the sprint A2 implementer while attaching the Compose arrival hold, and
confirmed independently by that sprint's adversarial reviewer.** Filed, not fixed.

`_setBusy(on, label)` (`static/app.js`, the app-wide busy banner) does two things: it
shows a `.cb-busy-banner` element, and it toggles a class on the document body —
`document.body.classList.add('cb-busy')` / `.remove('cb-busy')`.

**Nothing styles that class.** A grep for `cb-busy` over `static/style.css` at this tip
finds `.cb-busy-banner`, `.cb-busy-banner.show`, `.cb-busy-dot`, `.cb-busy-text` and a
comment mentioning `.cb-busy-banner` — and **no `body.cb-busy` / `.cb-busy` rule at all**
(`grep -n "\.cb-busy[^-]" static/style.css` returns nothing). So the body class is set,
removed, and never read.

**What that means.** The banner's copy tells the user to wait and not navigate away, but
no `pointer-events`, `overflow`, `cursor`, or overlay rule is attached to the state. The
app remains fully interactive underneath the banner for the entire duration of every busy
operation — corpus ingest, analyze, generate, refine, and now the A2 Compose arrival hold.
The affordance is **advisory only**, and reads as blocking.

**Why it was not fixed in A2.** Adding a blocking rule is a user-visible behavior change
at every `_setBusy` invocation, not just the one A2 added — well outside that sprint's
brief, and the kind of change that wants its own branch with its own UX-tier run (a
full-page pointer block is exactly the sort of thing that starts intercepting clicks in
the Playwright tier). Source: `docs/dev/blast-radius/compose-wait-ux.md` `## Deferred`
note 3.

**Count discrepancy, recorded rather than smoothed over.** That deferred note says "all 22
`_setBusy` call sites". A raw grep at `2a0b37a` finds **27** invocations (`grep -n
"_setBusy(" static/app.js` → 30 hits, minus the `function _setBusy` definition and two
prose comments). Whether the note counted distinct *operations* (a paired
`_setBusy(true)`/`_setBusy(false)` as one) or was simply stale was not established. The
blast radius is "every busy operation in the app" either way; the exact number should be
re-derived by whoever takes this, not inherited from here.

**What taking this looks like.** Decide first whether the intended semantics are (a)
genuinely blocking — then the rule and the accessibility story (focus trap, `aria-busy`,
keyboard escape) both need designing, and the whole UX tier is the regression surface — or
(b) advisory, in which case the honest fix is to delete the unused body-class toggle and
soften the copy. `decision_owner = "user"`: this is a product-behavior call, not a defect
with one correct repair.

## Updates

### 2026-08-09 — filed at `feat/compose-wait-ux` close-out (Epic A, sprint A2)

Filed by the A2 closer from the implementer's `## Deferred` note 3. Not caused by this
branch; A2 added one more `_setBusy` caller to a pre-existing condition. The absence of the
CSS rule was re-verified at `2a0b37a` before filing.
