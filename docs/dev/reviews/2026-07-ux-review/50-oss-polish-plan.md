# 50 — Open-Source Polish Plan

> The plan to take sartor. from "impressive and working" to "a polished
> open-source product" for its three audiences. It sequences the fixes from the
> [friction register](40-friction-register.md) into waves, each with a clear
> goal, and frames what to protect along the way. Nothing here is a code change
> in this branch — it's the roadmap.

## What "polished" means here

sartor. is already unusually complete: a coherent tailoring pipeline, real
grounding discipline, honest WYSIWYG output, a cited assistant, a full eval/
observability stack, and an AI-native contributor harness. The gap to "polished
OSS product" is not features — it's **the last mile of trust and legibility** for
each audience:

- **Job seekers** need the first two screens (Analyze, first-run) to feel
  *encouraging and clear*, not intimidating, and the basics (skills, downloads) to
  just work.
- **Headhunters** need the single-user model to grow a **roster and pipeline**
  surface so it becomes "where I run my desk."
- **Technical users** need a **clean on-ramp** — try it without spending, a working
  setup path, docs that separate "use / run / develop," and facts that match the
  code — so the project's real depth reads as a strength, not a maze.

## The strengths to protect (do not regress)

Any polish work must preserve what already works, because these are the reasons to
choose sartor. over a template tool:

1. **Grounding discipline** — the output tailors to the target without inventing
   facts; the eval `fabricated_specifics` metric backs this up (0.00–0.05 in a live
   smoke run). Keep the no-invention rule and its worked examples.
2. **The Compose screen** — per-role fit notes, ranked bullets, and gap-fill with
   "Covers: …" sublines. This is the product's best moment.
3. **Honest WYSIWYG preview** — "exactly what the PDF render uses." Keep the
   preview == download guarantee.
4. **Deterministic, reproducible Generate** — same composition, same document.
5. **The doc-grounded assistant** — cited, honest, queryable. A trust anchor for
   all three personas.
6. **Local-first + audit trail** — data stays on the machine; nothing is
   hard-deleted. This is a core promise; keep it.

---

## Wave 0 — Correctness & trust (launch blockers)

*Goal: nothing shown to a user is misleading, and a fresh clone actually runs.*
These are the [P0s](40-friction-register.md#p0--fix-before-a-public-launch).

- **F-01 — Fix the keyword score.** Strip the hiring company + a JD-boilerplate
  stoplist before scoring (`hardening.py:238-245/353-392`), and reframe the number
  so a strong candidate never sees a scary, deflated percentage at the first gate.
  *Highest-leverage single fix in this review.*
- **F-02 — Import skills.** Extract a skills list during résumé ingest and create
  pending Skill rows, so the corpus is complete after import.
- **F-24 / F-25 / F-26 — Make setup real.** Add `[dev]` to the documented verify
  step, put `sartor --setup` in every OS path, and fix the `pyproject.toml`
  `py-modules` omission so a built wheel imports and runs (this also unblocks the
  release/PyPI gate).
- **F-11 — Reconcile evals with the shipped path.** Either eval the
  compose→freeze→assemble path or clearly document that the `generate` rubric
  measures the fallback path, so quality claims are honest.

**Exit criteria:** a new user's first analysis shows a defensible score; import
yields a complete corpus (incl. skills); `git clone && pip install -e '.[dev]' &&
sartor --setup && sartor` works end-to-end and a built wheel runs; eval scope is
documented.

## Wave 1 — First-run delight (job seeker)

*Goal: the primary persona's first session feels guided and trustworthy.*

- **F-12 — Calm the Analyze screen.** Progressive disclosure: a short verdict + top
  3 actions first, deep analysis behind "show details."
- **F-03 / F-04 — Resolve the skills/education/certifications homes.** One obvious
  place per section; retire or make-live the inert flat Skills field; give
  education/certifications a corpus editor or clearly co-locate them.
- **F-15 — Capture company + role onto applications** so the tracker is usable.
- **F-10 — Ship server-side download** so the final step never silently fails.
- **F-06 / F-05 / F-09 (light touches)** — a transition line after user creation, a
  display-name-first user form, and a one-liner selling the reproducible Generate.

**Exit criteria:** a first-time job seeker can go import → tailor → download without
confusion, and the analysis reads as encouragement, not a grade.

## Wave 2 — Recruiter tier (headhunter)

*Goal: turn the repurposed single-user model into a real multi-candidate tool.*
The data model already supports all of this — the work is presentation.

- **F-08 — Candidate roster.** A searchable roster showing each candidate's target
  role/company and pipeline stage, replacing the flat username `<select>`.
- **F-17 — Cross-candidate pipeline view.** One dashboard of all candidates'
  applications by status ("3 interviews this week").
- **F-16 — Account-level templates.** A shared house-template library instead of
  per-candidate re-uploads.
- **Frame candidate memory as interview prep** (copy + placement), since it already
  is one.

**Exit criteria:** a recruiter with 20 candidates can find who needs attention,
apply a house style once, and prep from candidate memory — without user-switching
gymnastics.

## Wave 3 — Contributor on-ramp (technical)

*Goal: the project's depth is approachable, and nothing in the docs lies.*

- **F-19 — Demo mode.** A canned, key-free path through analyze → compose → output
  so anyone can see the product before spending. The biggest single adoption lever
  for an OSS launch.
- **F-21 — Split the README audiences** into "Use / Run / Develop," scoping the
  Claude-Code plugin as Claude-specific.
- **F-06d / F-22 / F-20 — Truth-in-docs sweep.** Relabel the reliability tile, fix
  the model-routing drift, regenerate the stale eval cost estimate.
- **F-27 — README polish bundle** (git prereq, define "witness metric," soften the
  "5 minutes" claim, surface Install for the technical reader).

**Exit criteria:** a developer can evaluate sartor. in 5 minutes without a key, get
it running from docs that work, and find the "develop/extend" path without wading
through the product pitch.

## Wave 4 — Aesthetic & interaction polish (P2)

- **F-07** migrate high-stakes confirmations to the app's own modal; drop the
  confirm on non-destructive bulk-accept.
- **F-23** collapse the User Selection + applications panels during an active
  tailoring session so the wizard owns the viewport.
- **F-13 / F-14 / F-18** gap-fill "optional" affordance; smarter edit-gate trigger +
  copy; document dev-friendly run flags.

---

## Open-source readiness checklist

Beyond the friction fixes, a public launch wants:

- [ ] **Demo mode** (F-19) — try-before-key. *Adoption-critical.*
- [ ] **Working setup + built-wheel smoke** (F-24/25/26) — the release gate passes.
- [ ] **A landing narrative** built from the strong screens — use the **📸**
  screenshot suggestions in [10-job-seeker.md](10-job-seeker.md) (Compose, Template
  WYSIWYG, the cited assistant) as the hero shots; avoid leading with the dense
  Analyze screen until F-01/F-12 land.
- [ ] **Audience-split README** (F-21) with a 60-second "what is this + one GIF."
- [ ] **Contribution path** that names the minimal loop (branch → ruff/mypy/pytest →
  PR) before the governance/wiki/plugin depth.
- [ ] **A short SECURITY/privacy statement** foregrounding local-first + "your data
  stays on your machine" (already true; make it prominent — it's a differentiator).
- [ ] **Truth-in-docs** (F-06d/F-20/F-22) so the first technical reader trusts the
  numbers.

## Suggested sequencing

Wave 0 is non-negotiable before any public link. Waves 1 and 3 can run in parallel
(different surfaces, different personas) and together make the "launch" version.
Wave 2 (recruiter tier) is the natural **v-next** theme and the clearest path to a
differentiated audience beyond individual job seekers. Wave 4 is continuous polish.

## How to measure it worked

- **Job seeker:** first-run completion rate (import → download) up; the Analyze
  screen no longer the drop-off point; qualitative "the score made sense."
- **Headhunter:** a recruiter can manage N>10 candidates without user-switching
  friction; time-to-tailor per candidate down after the roster lands.
- **Technical:** time-from-clone-to-running down; demo-mode → key conversion; PRs
  from new contributors that don't stumble on the doc/setup gaps above.

The eval harness and `/_dashboard` already give the project the instrumentation to
watch generation quality through all of this — once F-11 is reconciled, they can be
trusted as the regression net while the UX is polished.
