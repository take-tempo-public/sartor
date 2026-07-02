# v1.0.8 gated test window — E2E walkthrough runbook (Sprint 8.5)

> **Purpose:** the owner-driven runbook for the v1.0.8 **gated test window**
> (RELEASE_ARC §"Gated test window + correction"). Drives the whole product +
> the dev surfaces on the **decomposed** code (8.3a–h: `app.py` → zero routes,
> all 93 routes on domain blueprints) to surface integration issues the refactor
> may have introduced and the so-far-unexercised real-data paths.
> **Audience:** the owner running the walk; the agent triaging the harvest.
> **Companion:** findings land in [`window-8.5-findings.md`](window-8.5-findings.md)
> (the one numbered backlog 8.6 burns). The user-flow detail lives in the
> user-facing [`docs/walkthrough.md`](../walkthrough.md) — this runbook adds the
> **dev-side + post-split + R2-live** coverage, it does not duplicate the user steps.

---

## Where this runs + where evidence lives

- **Run it in the separate clone `C:\Dev\sartor-e2e`** (user `cooksey`), against a
  real corpus — NOT the main `C:\Dev\sartor` repo. Run evidence (screenshots,
  notes, `output/`) **stays in that clone**; it is **never** committed to the main
  repo (memory `project-e2e-instance-location`). Only the *triaged, PII-free* finding
  text is carried back into `window-8.5-findings.md`.
- The PV-1 paid eval loop (seed→bootstrap→annotate→collate→eval) is run *separately*
  from the main clone by the agent (cost-before-spend); its annotate step is your
  browser work. See [`window-8.5-findings.md`](window-8.5-findings.md) §PV-1.

## Expectation

Per the arc: *"this is where the significant, so-far-unexercised integration issues
surface."* This is the first time the full app + the v1.0.7 assistant + the diagnostics
console run on the post-blueprint route surface, and the first real-data eval loop. Treat
**anything that feels off** as a finding — capture first, triage later. Do **not** fix
on this walk (fixes are 8.6).

---

## Pre-flight

- [ ] `git -C C:\Dev\sartor-e2e log --oneline -1` is at (or rebased onto) the 8.4 merge
      `1f69f9c` or this 8.5 branch.
- [ ] `python app.py` starts clean; browser opens **once** (the 7.8b reloader fix); no
      stray windows on reload.
- [ ] `.api_key` present; a real corpus exists for `cooksey` (configs/ + db/).

## Part A — User flow on the decomposed code (the six wizard steps)

Drive the full flow per [`docs/walkthrough.md`](../walkthrough.md). At each step note
anything that regressed vs v1.0.7. Specifics to verify on the split:

- [ ] **Setup / smart landing** — selecting a user lands on the right tab (empty corpus →
      Corpus; non-empty → Tailor/Applications). New-user → corpus import, not JD entry.
- [ ] **Step 1 Job + Analyze — R2 STREAMING VERIFIED LIVE.** Paste a JD, Analyze, and
      confirm the analysis **renders incrementally token-by-token** (SSE
      `/api/analyze/stream`, now `blueprints/analysis.py`), not a single 90s blocking
      wait. This is the explicit R2 acceptance for the tag.
- [ ] **Step 2 Clarify** — questions generate; answers merge by id; a 2nd clarify round
      adds bullets (KW4 regression watch).
- [ ] **Step 3 Compose** — recommend fires; positioning + skills + experience cards render;
      drag/keyboard reorder autosaves; title pin + positioning pin persist; **browser
      Back/Forward traverse wizard steps** (PX-22).
- [ ] **Step 4 Template** — persona picker + live preview (paged.js, Chromium-free).
- [ ] **Step 5 Generate** — streamed generation; grounding holds (no invented facts/dates).
- [ ] **Step 6 Download** — docx matches the template; download == preview; step-6 edits
      reflected (V5-B #9/#10 watch).
- [ ] **Cover letter** (optional) — tone reads right (PV-3 is a later tune; just note tone).
- [ ] **Outcome / B.8 funnel** — submit → mark interview/rejection; the Applications block
      updates live; candidate memory populates after clarify/interview (KW7 watch).

## Part B — The doc-grounded assistant (v1.0.7)

- [ ] Open via the **top-bar magnifier** (`#assistantPill` → `#assistantModal`); answers
      stream with **numbered footnote citations** that resolve to a "Sources" key and link
      to GitHub (scheme B, 7.8d).
- [ ] Works **with no user selected** (7.8c) — ask "how does sartor. work?" first-run.
- [ ] Ask several "how do I…" questions (downloads, editing, cover letters, multi-user,
      import, troubleshooting). **Expect refusals / thin answers** — the wiki only has ~6
      `audience: user` pages today; every such gap is a finding for **8.6a**
      (`docs/assistant-wiki-coverage`), not a bug. Log which questions the avatar can't answer.

## Part C — Diagnostics console (dev surface, `/_dashboard`)

Reachable only via localhost. Now backed by `blueprints/diagnostics.py` (9 routes, 5 SSE).

- [ ] **Dashboard loads**; trends/heatmap/failure-mode panels render; help (i)-circles open.
- [ ] **Eval tab** — a `--suite synthetic --subset smoke` run streams (SSE `eval_run_stream`).
- [ ] **Tuning tab** — the tune run streams (`tune_run_stream`).
- [ ] **Annotation tab** — this is the PV-1 human-labeling surface. Loading a bootstrap
      fixture, entering verdicts, saving, scoring, and collating all work (drives
      `annotation_*` routes). You'll use this for real in the PV-1 loop.

## Part D — Post-split route-surface smoke (the refactor regression check)

The split moved every route to a domain blueprint with **byte-identical URLs**. Spot-check
that each domain still responds (one action per seam is enough):

- [ ] analysis · generation · corpus (experiences/summaries/skills/tags/curation/proposals)
      · templates/personas · applications · users/config · diagnostics · assistant.
- [ ] Watch for: 404/500 on a moved route, a dropped `_within`/`_safe_username` guard
      surfacing as a traversal/permission oddity, an SSE route that doesn't stream, or a
      config/path that reads the wrong directory post-`create_app(Config)`.

---

## KW-capture template (copy a row per finding)

Number findings `KW#` (kept distinct from the v1.0.6 KW1–KW13 and the `F-<domain>-<n>`
register). Capture first; the agent buckets + severities them into
[`window-8.5-findings.md`](window-8.5-findings.md). **Keep finding text PII-free.**

| KW# | Finding (what you saw / expected) | Area (step/seam) | Severity | → bucket |
|---|---|---|---|---|
| KW… | | | | 8.6 / 8.6a / 8.7 / defer |

Severity guide: **HIGH** = blocks the flow / data loss / security; **Med** = degraded UX or
a real-but-survivable defect; **Low** = copy/polish. Bucket guide: **8.6** = correction
sprint (most defects); **8.6a** = assistant doc-coverage gap; **8.7** = public-prep
(screenshots/badges/CI); **defer** = conscious v1.0.9+.
