# Using sartor — a first-run guide

> **Purpose:** the user-facing front door to *using* sartor — what it does for
> you, the path through your first résumé, and where to find help inside the app.
> The hub for the per-surface guides below.
> **Audience:** `user` — anyone using the app to tailor a résumé; no technical
> background assumed.
> **Grounding:** describes the shipped UI — the wizard in `templates/index.html`
> + `static/app.js`, and the in-app help copy in `static/app.js` (`_HELP_REGISTRY`).
> The "approve once, no surprises" framing reflects the Compose-authors /
> deterministic-Generate re-architecture — see
> [`docs/dev/generation-experience-rearchitecture.md`](../../../docs/dev/generation-experience-rearchitecture.md)
> and [[frontend-wizard]]. The no-fabrication promise is the one in
> [`../overview.md`](../overview.md).

---

## What sartor does for you

sartor tailors your résumé — and, if you want, a cover letter — to a specific
job. It works from a **career corpus** it builds out of résumés you already have,
so nothing is locked in a file you hand-edit for every application. You paste in a
job posting; sartor reads it, asks a few sharp questions, then **drafts and shows
you everything before it's final** — the bullets, the summary, even a suggestion
for anything the job asks for that your corpus doesn't cover yet — so you approve
the actual content once, and every later step (template, generate, download) shows
exactly what you approved. No invented titles, numbers, or dates, and no surprise
rewrite at the end. It runs on your own machine; your career data stays there,
apart from the calls to the AI that does the writing. (See
[`../overview.md`](../overview.md) for the promise behind that.)

## Your first run, end to end

1. **Add yourself as a user** and **import a résumé.** Lead with your name — sartor
   derives a username for you, editable if you'd rather pick your own. Importing
   builds your first career corpus, so you don't start from a blank page (see
   [[importing-your-experience]]). An ATS-friendly résumé (plain text, clear
   month/year dates) reads best.
2. **Review your [[career-corpus]].** Everything starts as *pending review*;
   accept items one at a time, by role, or all at once. Reviewing sharpens future
   résumés.
3. **Tailor to a job.** Paste the job description and let sartor analyze it
   against your corpus, then approve what it drafts at Compose — see
   [[tailoring-a-resume]] for all six steps.
4. **Pick a template and generate.** Choose how it looks (see
   [[resume-templates]]); Generate assembles exactly what you approved, you
   preview it live and edit in place (see [[editing-and-refining]]), and download
   when ready (see [[downloading-your-documents]]) — plus an optional cover letter
   (see [[cover-letters]]).

Anything sartor learns about you along the way is kept in your
[[candidate-memory]].

## Finding help inside the app

Every significant section has a small **“i”** you can click for a plain-language
explanation — the same guidance these pages carry. The very first time you use
sartor, a short welcome and a few one-time tips walk you through the path above —
including a note explaining why a brand-new profile lands straight on Career corpus
instead of the Tailor wizard (there's nothing to tailor yet) — and each appears once,
always re-openable from its **“i”**. Returning users aren't walked through
onboarding again.

## The guides

- [[tailoring-a-resume]] — the six-step Tailor wizard.
- [[importing-your-experience]] — getting your history in: import, online profiles, by hand.
- [[career-corpus]] — the pool of experience sartor writes from.
- [[resume-templates]] — how your résumé looks.
- [[cover-letters]] — generating a cover letter to match.
- [[editing-and-refining]] — editing a draft and refining it.
- [[downloading-your-documents]] — formats and saving your files.
- [[managing-users]] — using sartor with more than one person.
- [[candidate-memory]] — what sartor remembers across applications.
- [[recruiter-pipeline-tab]] — the cross-candidate Pipeline board, for tracking
  more than one candidate's applications at once.
- [[using-the-assistant]] — the built-in assistant that answers from these guides.
- [[troubleshooting]] — when something goes wrong.
