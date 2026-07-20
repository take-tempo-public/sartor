# sartor. — Diagnostics-page round-2 e2e feedback (owner, 2026-07-09)

> **What this is.** The owner's round-2 walkthrough of the **diagnostics
> console** (`/_dashboard` — the Quality / Tuning / Annotate / Bootstrap
> backend), captured as 17 numbered items, each grounded in code and given a
> disposition. Companion to
> [`2026-07-ux-round2-findings.md`](2026-07-ux-round2-findings.md) (the app-side
> round-2 feedback) and [`2026-07-e2e-run-health-review.md`](2026-07-e2e-run-health-review.md)
> (item **#14** — the read-only run-health review).
>
> **What this is not.** No design spec. **Owner decision (2026-07-09): all of it
> bundles into the post-tag v1.0.9 epic — nothing jumps the v1.0.8 queue**, and
> the broken fixture flow (#15) knowingly ships in v1.0.8 as-is. The owner also
> opted **in** to a real run-**cancel** path (not just a click-lock) as part of the
> epic diagnostics work.
>
> **Provenance note.** An earlier capture lane for this batch was blocked by the
> `check-plan-approved` hook and its worktree auto-cleaned before it could commit —
> nothing was written. This document (reconstructed from the session transcript) is
> the **durable capture**; it supersedes that lost lane. HEAD at triage: `e76d622`.

## Owner decisions (locked)

- **Sequencing:** bundle the whole diagnostics wave into the **v1.0.9 epic**
  (post-tag). Nothing pre-empts the v1.0.8 freeze; #15 ships as-is.
- **Run-cancel:** add a real **abort endpoint** that stops a worker before its next
  paid Anthropic call — not just a UI lock.
- **Assistant on the dashboard (#17):** integrate the doc-grounded assistant into the
  diagnostics pages with the dev-mode checkbox **checked by default** there.

## The 17 items — condensed ask + grounded disposition

- **#1 — Run-collision safety for paid runs.** Many run buttons; no shared lock, so
  switching tabs and starting a second run risks a silent duplicate **paid** run.
  → *Missing-guard bug + UX.* Each button has its own `disabled` toggle, no shared
  single-flight (`dashboard.html` `1140-1156` / `1230-1256` / `1470-1477` /
  `1518-1543`). Fix = a global `run-lock` toggling all four + a prominent status
  banner + `beforeunload` guard. **Size S.**
- **RUN-LIFECYCLE (load-bearing, under #1).** Every long run spawns a
  `threading.Thread(daemon=True)` with no request handle — **closing the tab does not
  abort the run**; it bills and completes silently; **no cancel endpoint exists**
  (`diagnostics.py:421, 650, 872, 1039`). And `app.run()` is never `threaded=True`
  (`app.py:292`; `Dockerfile:57`) → one request app-wide at a time → a 2nd click
  hangs, then silently fires a 2nd paid run when the first connection closes. True
  concurrent corruption is foreclosed; the real risk is the **silent queued paid run**.
  **→ Landed (`feat/diagnostics-run-cancel`):** disconnect-as-cancel, not a literal
  second route — `app.run()` staying single-threaded (the architectural flag below,
  still deliberately deferred) means a real `POST /cancel` couldn't be serviced while
  the original SSE connection is open, so the cancel signal travels over that SAME
  connection instead. All 4 SSE routes now poll their result queue with a timeout,
  yielding a heartbeat SSE comment on each `queue.Empty`; a real client disconnect
  (or the new frontend Cancel button's `AbortController.abort()`) causes the next
  write to fail, Werkzeug tears the generator down, and the caught `GeneratorExit`
  sets a per-request `threading.Event` the worker checks before its next paid/CPU
  call (`run_suite`/`run_pipeline_over_jd_texts`/`run_grounding_signals` all gained an
  optional `cancel_check` param, mirroring the existing `progress` pattern).
- **#2 — Diagnostics cards need informational + instructional "love" in main-app
  style.** → *UX content-authoring* (cluster with #4/#5/#6/#16; plumbing already exists).
- **#3 — Does Tuning A/B leverage the Annotate seed export? No GUI indication, only a
  CLI hint; I ran an A/B by accident.** → *Design correct; CLI-only pointer is polish
  (XS).* Chain: Annotate "Export seed" → `POST /api/annotation/seed/export`
  (`diagnostics.py:517-588`) writes `<slug>/seed.json`; Tuning's `/api/tune/run`
  resolves that seed or 409s "re-run the bootstrap" (`diagnostics.py:1010-1034`). Fix =
  cross-link the Annotate export button from the Tuning tab (`dashboard.html:417-420`).
- **#4 — Instructional text needs cleanup, consistent with main-app styles.** → Polish
  (content cluster).
- **#5 — Each section needs "what is this / how to read it"; each action the same +
  step-by-step; terse + deep-doc links.** → Polish (content cluster).
- **#6 — The prompt-tuning-loop exemplar text is solid but hard to parse; rewrite in
  clear language.** → Polish (content cluster).
- **#7 — Why both a `should_omit` checkbox AND an omit choice in the verdict dropdown?**
  → *Distinct fields, not redundant — the bug is zero UI explanation.* `verdict`
  (required; keep/fix/omit/fabricated) feeds collation (`evals/annotation.py:82,
  192-197`); `should_omit` (optional, defaults False; `evals/annotation.py:334, 354`)
  feeds **only** the improvement-brief Omissions section (`614-619`) — no collation
  effect. The verdict `<select>` has a `.title` tooltip (`dashboard.html:1310-1318`),
  the checkbox has none (`1342-1344`). **Size XS** (tooltip); *design-Q:* keep-two +
  tooltip vs collapse into a `keep-but-omit` verdict (M).
- **#8 — Some skills rendered strangely when annotating.** → *Bug in the deterministic
  bootstrap skills parser.* Bootstrap runs legacy `analyzer.generate()` free-form
  markdown (`evals/bootstrap.py:386`); `_heading_text` only matches a fully-bold
  standalone line (`166-181`), so an inline `**Category:** …` prefix falls through
  `_split_skill_line`/`_extract_skills` (`184-219`) and renders garbled
  (`dashboard.html:1327`). **Size S, LLM-free** (strip the inline prefix; no
  PROMPT_VERSION).
- **#9 — "Annotations failed validation" was a dead end; I lost partial work on
  reload.** → *Fail-closed validation is correct; the UX gaps are real (labor-loss).*
  Save route runs `validate_annotations` fail-closed (`diagnostics.py:215-262`,
  `evals/annotation.py:234-266`); one unfilled verdict 400s the whole save. Gaps: (a)
  UI never scrolls to the named item; (b) `state.doc` is in-memory only
  (`dashboard.html:1270`) — **no localStorage draft**, so a reloaded tab at 49/50 loses
  labor a paid bootstrap produced. Fix = localStorage draft-snapshot/restore +
  jump-to-flagged-item (parse `bullets[N]` from the 400). **Size S / M.**
- **#10 — Long runs need a real sense of progress; the "Scoring 32 bullet clusters"
  line is the least-visible font. Design for the recruiter ICP + devs.** → SSE for
  eval/tune/bootstrap already carries `index`/`total` (`evals/bootstrap.py:361`;
  `dashboard.html:1105`) shown only as plain text → a real `<progress>` bar is
  **low-hanging (S)**. Grounding-score route lacks granular events (see #13).
- **#11 — The printed `python evals/runner.py … --seed …/seed.json` line sits above a
  "Run this fixture" button. Same thing?** → *Not equivalent — confirmed bug in the CLI
  line.* Button posts `fixture: slug` (one dir); the printed command
  (`diagnostics.py:338-341`) has **no `--fixture <slug>`**, and `--seed` doesn't
  restrict fixtures (`evals/runner.py:1793-1804`), so it globs ALL real fixtures and
  crashes in `_load_fixture` (hard-requires `jd.txt`, `162-181`). **Size XS** (append
  `--fixture`); blocked by #15.
- **#12 — Favor the GUI; mention CLI scripts but don't let them compete for
  attention.** → Design principle (folds into #3/#11 + the content cluster).
- **#13 — Any progress indicator beyond "busy" for long tasks? Don't push hard.** →
  eval/tune/bootstrap bar = low-hanging (#10). Grounding-score `annotation_score_grounding`
  (`diagnostics.py:421-509`) blocks on one synchronous `run_grounding_signals()`;
  NLI loops per-item but MiniCheck is one batched call
  (`evals/grounding_signals.py:196, 239-242`) → true % is **document-for-future (M+)**.
- **#14 — How did my runs perform; do we need to schedule work?** → *Excluded from the
  code triage; handled read-only.* See
  [`2026-07-e2e-run-health-review.md`](2026-07-e2e-run-health-review.md): 53 annotations
  saved, **all grounding scores null** (persistence gap), one 0-byte failed run,
  grounding-only rubric coverage — all → v1.0.9, none blocks the tag.
- **#15 — "No anchor JD is saved" — too little info.** → *Confirmed bug, root of the
  broken flow.* The bootstrap worker forces a `.txt` suffix when writing each JD
  (`diagnostics.py:769-775`), but `annotation_collate` builds
  `anchor_src = fixture_dir/"jds"/secure_filename(anchor_name)` **without** the `.txt`
  (`307-308`), so `anchor_src.exists()` is False for browser bootstraps whose JD name
  didn't already end in `.txt` → `jd.txt` never written → since `_load_fixture`
  hard-requires it, **neither "Run this fixture" nor the CLI can ever succeed** on a
  browser-produced fixture. **Size S** (reconcile the suffix + a `jd_written`
  round-trip test). **Fix FIRST** (blocks #11). *(NB: the JD content is not lost — it
  lives at `jds/<descriptive>.txt`; only the expected root `jd.txt` is absent.)*
- **#16 — All tabs need UX love; Quality/Tuning/Annotate especially weak on
  guiding.** → Polish (content cluster).
- **#17 — The assistant would help here but there's no affordance; integrate it, dev
  checkbox checked by default.** → *Feature, small, no backend change.* `assistant.js`
  needs only `currentUser` + `_consumeSSE`; `blueprints/assistant.py:ask()` treats
  `username` as optional. Add the script tag to `dashboard.html`, promote `_consumeSSE`
  (help-modal.js precedent), a `currentUser` shim, port the `assistantModal` block,
  default the dev checkbox checked. **Size S/M.**

## The instructional cluster (#2/#4/#5/#6/#16), grounded once

The dashboard **already faithfully ports the main-app help pattern**: `_DASH_HELP`
(`dashboard.html:816-875`) mirrors `_HELP_REGISTRY` via the shared
`static/help-modal.js` (`cbOpenHelpModal`/`cbHelpSeen`, loaded `dashboard.html:18`),
same `cb_help_seen:` prefix + once-ever auto-open. **The gap is granularity/content,
not plumbing**: only 5 per-*tab* info-circles vs the main app's 18 field-level entries;
granular controls rely on native `title=` tooltips. Fix = author field-level
`_DASH_HELP` entries. **Size S per item, M in aggregate.**

## Confirmed bugs (the actionable core)

1. **#15** — anchor-JD path missing `.txt` reconciliation → `jd.txt` never written →
   fixtures unusable. `diagnostics.py:307-308` (vs writer `769-775`). Root cause; fix
   first. **S.**
2. **#11** — collate CLI string missing `--fixture <slug>` → globs all real fixtures →
   crash / cross-candidate contamination. `diagnostics.py:338-341`. **XS.** Blocked by #15.
3. **#8** — bootstrap skills parser doesn't strip inline `**Category:**` → mangled rep.
   `evals/bootstrap.py:166-219`. **S, LLM-free.**
4. **#7** — `should_omit` vs `verdict=omit` are distinct; checkbox lacks the dropdown's
   tooltip. Missing-affordance + design-Q. **XS + design.**
5. **#1** — no global run-lock (independent per-button `disabled`) → silent second paid
   run. Missing-guard. **S.**
6. **#9** — no localStorage draft persistence; lost labor + no jump-to-item. UX-severity.
   **S / M.**
7. **Run-cancel (owner opted in)** — daemon workers with no abort path
   (`diagnostics.py:421/650/872/1039`); add a cancel endpoint that stops a worker before
   its next paid call. **Landed** — see RUN-LIFECYCLE above for the disconnect-as-cancel
   mechanism (`feat/diagnostics-run-cancel`).

## Architectural flag (separate governance decision — NOT epic bug work)

Single-threaded `app.run()` (`app.py:292`, no `threaded=True`) freezes the whole app
during any diagnostics run. Making it threaded touches the **C-1-sensitive loopback-bind
area**, so it is its **own governance-signed decision**, deliberately kept out of the
epic diagnostics UX work. Surfaced here for the owner; not scoped to a branch.

## Routing summary

Everything here → **v1.0.9** (the UX Cohesion Epic's diagnostics-DX + hardening
thread). Fix order within the epic: **#15 → #11** (unblocks the fixture flow), then the
run-lock + cancel (#1 + lifecycle), the annotate-flow persistence (#9, pairs with the
grounding-persistence gap in the run-health review), #8, #7, then the instructional /
assistant / progress-bar polish (#2–6, #10, #13, #16, #17). The `threaded=True`
architectural flag is a separate owner-gated governance decision.
