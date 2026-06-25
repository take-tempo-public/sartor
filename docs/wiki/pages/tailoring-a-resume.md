# Tailoring a résumé — the Tailor wizard

> **Purpose:** the user-facing walk through the six-step Tailor wizard — from
> pasting a job to downloading a tailored résumé and cover letter.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the six wizard steps in `templates/index.html` (`#panelJD` …
> `#panelOutput`) driven by `static/app.js` (`_WIZARD_PANELS`, `_wizardRender`);
> mirrors the in-app step help.

---

Open **Tailor**, pick yourself as the user, and work top to bottom. The numbered
steps along the top let you move back and forward at any time.

## Step 1 — Job description & analysis
Paste the full text of the job, then click **Analyze**. callback reads the posting
and weighs it against your [[career-corpus]] to find the experience that fits this
role best, and shows you its read of the job.

## Step 2 — Clarify (optional, but worth it)
callback asks a few short questions to draw out experience your résumé didn't spell
out and to pin down anything vague. Your answers become new candidate bullet points
— added to your corpus to accept now or review later — and keep the draft grounded
in fact. Prefer to move on? Click **Skip**.

## Step 3 — Compose
Here callback proposes the résumé for this job: the title it chose for each role
and the bullet points it selected and ordered (including any from your clarifying
answers). **Pin** a bullet to force-include it, **exclude** ones you don't want, or
open **find more** to pull others from your corpus. Edits here affect this
application only.

## Step 4 — Template
Choose how it looks. Pick a template and the preview shows the pages exactly as
they'll print — same words, different typography. You can also upload your own
`.docx` for callback to reuse (ATS-safe strongly recommended). See
[[resume-templates]].

## Step 5 — Generate
Choose your output format and click **Generate**. callback writes the final,
tailored résumé — usually 30–60 seconds.

## Step 6 — Preview, edit & download
Your finished résumé appears in an editable preview. Fix wording in place (see
[[editing-and-refining]]) — those edits become the starting point for your next
iteration. **Editing here changes the document text only; it does not change your
[[career-corpus]].** Download when ready (see [[downloading-your-documents]]), and
generate an editable **cover letter** from the same job and résumé if you want one
(see [[cover-letters]]).

Everything callback writes stays **grounded in your real history** — see
[`../overview.md`](../overview.md). Back to [[using-callback]].
