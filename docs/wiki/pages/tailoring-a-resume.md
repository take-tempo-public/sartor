# Tailoring a résumé — the Tailor wizard

> **Purpose:** the user-facing walk through the six-step Tailor wizard — from
> pasting a job to downloading a tailored résumé and cover letter.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the six wizard steps in `templates/index.html` (`#panelJD` …
> `#panelOutput`) driven by `static/app.js` (`_WIZARD_PANELS`, `_wizardRender`,
> `_renderAnalysis`, `loadComposition`, `_renderGenerateStepCopy`,
> `_refreshLiveEditPreview`, `_submitSurgicalRefinement`); mirrors the in-app step
> help. The Compose/Generate mechanics are the user-facing view of
> [`docs/dev/generation-experience-rearchitecture.md`](../../../docs/dev/generation-experience-rearchitecture.md)
> (see [[frontend-wizard]] for the developer's account).

---

Open **Tailor**, pick yourself as the user, and work top to bottom. The numbered
steps along the top let you move back and forward at any time.

## Step 1 — Job description & analysis
Paste the full text of the job, then click **Analyze**. sartor reads the posting
and weighs it against your [[career-corpus]] to find the experience that fits this
role best. The result leads with a coverage score and a short "Where to Focus"
verdict — the handful of things most worth your attention — with the full
keyword-by-keyword breakdown tucked behind a "Show full analysis" toggle for
whenever you want it `[synthesis]`.

## Step 2 — Clarify (optional, but worth it)
sartor asks a few short questions to draw out experience your résumé didn't spell
out and to pin down anything vague. Your answers become new candidate bullet points
— added to your corpus to accept now or review later — and feed the drafting sartor
does at Compose, keeping it grounded in fact. Prefer to move on? Click **Skip**.

## Step 3 — Compose: everything is drafted and reviewed here
This is where sartor writes. On arrival it drafts the title and bullet points for
each role (including any from your clarifying answers), a two-sentence
**positioning summary**, and — for anything the job asks for that your corpus
doesn't cover — grounded new bullet suggestions to fill the gap, each shown for you
to **accept** or **retire**. **Pin** a bullet to force-include it, **exclude** ones
you don't want, or open **find more** to pull others from your corpus. Nothing here
is invented out of thin air — every drafted bullet and every summary traces back to
your résumé, your corpus, or an answer you gave. Edits here affect this application
only.

When you click **Save and continue**, everything you've approved is **locked in** —
that exact content is what the rest of the wizard shows you, with no more rewriting
behind the scenes. **No surprises**: what you approve here is what you'll download.

## Step 4 — Template
Choose how it looks. Pick a template and the preview shows the pages exactly as
they'll print, with the content you approved at Compose — switching templates never
changes the words, only the typography. You can also upload your own `.docx` for
sartor to reuse (ATS-safe strongly recommended). See [[resume-templates]].

## Step 5 — Generate
Choose your output format and click **Generate**. Once you've saved and continued
from Compose, this step is a fast, honest assembly of exactly what you approved —
no further rewriting, so it's usually near-instant. (If you jump here without going
through Compose first, sartor still writes the résumé for you at this step, the
way earlier versions worked — the wizard tells you plainly which of the two is
about to happen.) `[synthesis]`

## Step 6 — Preview, edit & download
Your finished résumé appears in an editable preview that updates **as you type** —
what you see is what Download produces. Fix wording in place (see
[[editing-and-refining]]) — those edits become the starting point for your next
iteration. **Editing here changes the document text only; it does not change your
[[career-corpus]].** Ask for a change instead of editing directly and sartor
proposes one **specific, targeted** change and routes you back to Compose to
accept or retire it — never a silent full rewrite. Download when ready (see
[[downloading-your-documents]]), and generate an editable **cover letter** from the
same job and résumé if you want one (see [[cover-letters]]).

Everything sartor writes stays **grounded in your real history** — see
[`../overview.md`](../overview.md). Back to [[using-sartor]]; the developer's view
of these same six steps is [[frontend-wizard]].

Tracking applications for more than one candidate? See the
[[recruiter-pipeline-tab]] for a status board across everyone at once.
