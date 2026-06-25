# Using callback — a first-run guide

> **Purpose:** the user-facing front door to *using* callback — what it does for
> you, the path through your first résumé, and where to find help inside the app.
> The hub for the per-surface guides below.
> **Audience:** `user` — anyone using the app to tailor a résumé; no technical
> background assumed.
> **Grounding:** describes the shipped UI — the wizard in `templates/index.html`
> + `static/app.js`, and the in-app help copy in `static/app.js` (`_HELP_REGISTRY`).
> The no-fabrication promise is the one in [`../overview.md`](../overview.md).

---

## What callback does for you

callback tailors your résumé — and, if you want, a cover letter — to a specific
job. It works from a **career corpus** it builds out of résumés you already have,
so nothing is locked in a file you hand-edit for every application. You paste in a
job posting; callback reads it, asks a few sharp questions, helps you pick the
real accomplishments that fit, then writes a tailored draft **grounded in what's
actually true about you** — no invented titles, numbers, or dates — and renders it
to Word or PDF. It runs on your own machine; your career data stays there, apart
from the calls to the AI that does the writing. (See
[`../overview.md`](../overview.md) for the promise behind that.)

## Your first run, end to end

1. **Add yourself as a user** and **import a résumé.** callback builds your first
   career corpus from it, so you don't start from a blank page (see
   [[importing-your-experience]]). An ATS-friendly résumé (plain text, clear
   month/year dates) reads best.
2. **Review your [[career-corpus]].** Everything starts as *pending review*;
   accept items one at a time, by role, or all at once. Reviewing sharpens future
   résumés.
3. **Tailor to a job.** Paste the job description and let callback analyze it
   against your corpus — see [[tailoring-a-resume]] for the six steps.
4. **Pick a template and generate.** Choose how it looks (see
   [[resume-templates]]), generate, preview, edit in place (see
   [[editing-and-refining]]), and download (see [[downloading-your-documents]]) —
   plus an optional cover letter (see [[cover-letters]]).

Anything callback learns about you along the way is kept in your
[[candidate-memory]].

## Finding help inside the app

Every significant section has a small **“i”** you can click for a plain-language
explanation — the same guidance these pages carry. The very first time you use
callback, a short welcome and a few one-time tips walk you through the path above;
each appears once and is always re-openable from its **“i”**. Returning users
aren't walked through onboarding again.

## The guides

- [[tailoring-a-resume]] — the six-step Tailor wizard.
- [[importing-your-experience]] — getting your history in: import, online profiles, by hand.
- [[career-corpus]] — the pool of experience callback writes from.
- [[resume-templates]] — how your résumé looks.
- [[cover-letters]] — generating a cover letter to match.
- [[editing-and-refining]] — editing a draft and refining it.
- [[downloading-your-documents]] — formats and saving your files.
- [[managing-users]] — using callback with more than one person.
- [[candidate-memory]] — what callback remembers across applications.
- [[using-the-assistant]] — the built-in assistant that answers from these guides.
- [[troubleshooting]] — when something goes wrong.
