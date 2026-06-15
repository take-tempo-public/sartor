# Career corpus — the pool callback writes from

> **Purpose:** the user-facing explanation of the career corpus — what it is, how
> it fills up, and how reviewing it improves your résumés.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the Career corpus tab in `templates/index.html` (`#panelCorpus`)
> + its review/accept flow in `static/app.js`; mirrors the in-app corpus help.

---

Your **career corpus** is the pool of experience callback draws from when it writes
a tailored résumé — the roles and bullet points it built from the résumé you
imported. It's yours, it stays on your machine, and it's never shared between
users.

## Building it
Import a résumé and callback extracts your experience for you; you can also add
experiences by hand, or mix both. Each experience holds one or more **titles** (one
official, optional alternates) plus its **bullets**, and you can **tag** things to
organize them.

## Reviewing it
Everything new starts as **pending review**. Accept items one at a time, by role,
or all at once. Reviewing and accepting is worth the few minutes: it's how callback
learns which of your accomplishments are real and ready to use, which sharpens
every résumé it writes afterwards.

## How it's used
When you tailor to a job (see [[tailoring-a-resume]]), callback selects and orders
the strongest bullets from your accepted corpus for that posting. Edits you make
*inside* a tailored application affect only that application — your corpus changes
only when you edit it here, or when you accept a clarifying answer as a new bullet.

See [[using-callback]] for the whole first run, and [[candidate-memory]] for where
clarifying answers are kept.
