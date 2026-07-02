# Downloading your documents — formats and saving

> **Purpose:** the user-facing explanation of downloading your tailored résumé and
> cover letter — the formats on offer, what PDF needs, and what "download with my
> edits" does.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the Step 6 output panel in `templates/index.html` (`#panelOutput`)
> and its download buttons (`#btnDownloadResume`, `#btnDownloadCover`) driven by
> `static/app.js` (`downloadResume`, `downloadCoverLetter`); the deterministic
> download + render path in `blueprints/generation.py` (`download_file`,
> `download_edited`), `generator.py`, and `pdf_render.py`.

---

When your tailored résumé is ready in **Step 6**, you save it to your computer in the
format you choose. If you also generated a cover letter (see [[cover-letters]]), it
downloads the same way, from its own tab.

## Choosing a format
sartor can write your document as **Word (`.docx`)**, **PDF**, or **Markdown
(`.md`)**. You pick the résumé format back in **Step 5** before generating, and the
cover letter has its own format buttons in Step 6. Word is the safe default for most
applications; Markdown is plain text you can paste anywhere.

## PDF needs one extra thing
PDF output is rendered through a bundled headless browser (Chromium), which is an
**optional, one-time download** (`python -m playwright install chromium`). Word,
Markdown, and the on-screen preview don't need it — if you only ever download Word or
Markdown, you can skip it entirely. (See [[troubleshooting]] if a PDF download reports
that Chromium is missing.)

## Downloading with your edits
If you fixed wording in the preview (see [[editing-and-refining]]), the Download button
rebuilds the file **from your edited text**, so the document you save matches exactly
what you see on screen — your edits are never left behind.

How the document *looks* is a separate choice — see [[resume-templates]]. For the whole
path from job posting to download, see [[tailoring-a-resume]].
