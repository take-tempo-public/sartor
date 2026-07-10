# Cover letters — generating one to match

> **Purpose:** the user-facing explanation of generating a cover letter — when to do
> it, what it's based on, and how to edit and download it.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the cover-letter tab + controls in `templates/index.html`
> (`#tabCoverLetter`, `#btnGenerateCover`, `#coverLetterPreview`) driven by
> `static/app.js` (`runGenerateCoverLetter`); the `run_generate_cover_letter` and
> `download_edited` routes in `blueprints/generation.py`,
> `analyzer.generate_cover_letter_against_resume`, and the deterministic
> `generator.generate_cover_letter` (format + persona-font matching).

---

A cover letter is **optional** — sartor writes one only if you ask. You generate it in
**Step 6**, after your résumé is ready, from the same job posting and your finalized
résumé.

## Generating it
On the **Cover letter** tab, click **Generate**. sartor writes a letter that draws on
the job and the résumé you just tailored, so it stays consistent with the document
you're sending and **grounded in your real history** — never invented. It's quicker than
generating a résumé.

## Editing and downloading
The letter appears in an editable preview, just like the résumé — fix wording in place
(see [[editing-and-refining]]), choose a format (Word, PDF, or Markdown), and download
it from its own button. A Word or PDF cover letter picks up the same look (font and
styling) as the résumé template you chose, so the two match. The cover letter and
résumé download separately, so you can send one or both — see
[[downloading-your-documents]].

For where the cover letter fits in the whole flow, see [[tailoring-a-resume]].
