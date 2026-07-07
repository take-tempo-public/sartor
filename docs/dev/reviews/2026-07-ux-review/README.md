# sartor. — Full UX Review (three personas), 2026-07-07

> **What this is.** A complete, browser-driven UX study of sartor. walked from
> its three target users — **job seeker**, **headhunter**, **technical user
> (self-hoster / contributor)** — covering every user-facing path and tool,
> plus the evals and diagnostics surface. It documents each flow as a
> task-outline from the persona's point of view, maps where a user could get
> confused, proposes remediations, and lays out a plan for polishing sartor.
> into an open-source product.
>
> **What this is not.** No code was changed. This is a study, documentation,
> and planning artifact. Every friction claim was adversarially verified
> against the code before it was written down; a claim that could not be
> grounded was dropped or downgraded (see the register's verdict column).

## Method

- A fully **sandboxed instance** of the real app was launched from an external
  script (temp `base_dir` + temp SQLite DB), so real user data in
  `configs/` / `resumes/` / `output/` was never touched. Real Anthropic API
  calls were left enabled for one full pass so the LLM behavior is genuine, not
  stubbed.
- The three personas were driven live in headless Chromium (Playwright),
  seeding a synthetic candidate from `evals/fixtures/synthetic/sre-mid-level/`
  (an SRE résumé + a matching JD). ~40 screenshots were captured as evidence.
- The LLM-call telemetry (`logs/llm_calls.jsonl`) and the `/_dashboard` console
  were read to ground the "evals and diagnostics" section in real numbers.
- Friction claims were verified in parallel against the codebase (an
  adversarial "try to refute it" pass) before landing in the register.

## The documents

| File | What it covers |
|---|---|
| [00-system-map.md](00-system-map.md) | The whole system at a glance: IA, the 6-stage pipeline, every LLM call kind (and which steps are deterministic), the full route/tool inventory, the data model, and where each persona enters. |
| [10-job-seeker.md](10-job-seeker.md) | The primary persona. Task-outline of every path — first run, corpus import + curation, the wizard, output/refine/cover-letter, applications, candidate memory, settings, the assistant — with per-step "what the user sees / thinks" and friction. |
| [20-headhunter.md](20-headhunter.md) | The multi-candidate persona: the one-user-per-candidate model, template management, candidate memory as interview prep, and where the single-user product strains at agency scale. |
| [30-technical-user.md](30-technical-user.md) | The self-hoster / contributor: fresh-clone setup, the `/_dashboard` diagnostics console, the eval harness + tuning loop, the Claude-Code plugin, the wiki/governance system, and the contribution path. |
| [40-friction-register.md](40-friction-register.md) | The consolidated, prioritized friction table — every issue, its severity, the persona(s) it hits, a remediation, and its verification verdict. The actionable core. |
| [50-oss-polish-plan.md](50-oss-polish-plan.md) | The plan: what to fix before a public launch, sequenced into waves, framed for job seekers, headhunters, and the technical users who will make it their own. |

## Screenshot suggestions

Screenshot suggestions are embedded inline in each persona document, marked
**📸 Screenshot:** with a precise description a future model (or a human) can
reproduce. They are suggestions for the eventual published docs / landing page,
not attached captures.

## Headline findings

1. **The product is genuinely strong.** The corpus → analyze → compose → template
   → generate flow is coherent, the grounding discipline is real (the generated
   résumé tailored to the target company without inventing facts), the live
   WYSIWYG preview is honest ("exactly what the PDF render uses"), and the
   doc-grounded assistant answers with real citations. This review is about the
   last mile of polish, not a rescue.
2. **The Analyze screen is the biggest single friction.** It is a dense wall of
   analysis, and its headline "Keyword Match Score" (18% for a strong match) is
   deflated by counting the hiring company's own name and generic words as
   "missing keywords." A qualified candidate could be discouraged at the first
   gate. See F-01.
3. **Skills have two homes and neither is filled by import.** Import populates
   experiences/bullets/titles but not skills; skills then live in two disconnected
   places (flat profile config vs. structured corpus). See F-02 / F-03.
4. **The final "Generate" is deterministic — a strength worth surfacing.** The
   LLM cost is front-loaded into Analyze and Compose; Generate just assembles the
   frozen composition. This makes output reproducible, but users aren't told.
5. **The "user" abstraction is a single-job-seeker model.** It works, but a
   headhunter managing a roster hits a flat username dropdown with no search or
   status. See F-08.

See [40-friction-register.md](40-friction-register.md) for all findings.
