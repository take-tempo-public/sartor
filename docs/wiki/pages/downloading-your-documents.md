# Downloading your documents — formats and saving

> **Purpose:** the user-facing explanation of downloading your tailored résumé and
> cover letter — the formats on offer, what PDF needs, and what "download with my
> edits" does.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the Step 6 output panel in `templates/index.html` (`#panelOutput`)
> and its download buttons (`#btnDownloadResume`, `#btnDownloadCover`) driven by
> `static/app.js` (`downloadResume`, `downloadCoverLetter`); the download + render
> path in `blueprints/generation.py` (`download_file`, `download_edited`), and the
> single shared renderer in `generator.py` (`_write_docx_from_json_resume`) and
> `pdf_render.py`.

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
Markdown, you can skip it entirely.

**Before offering the download, sartor. checks if PDF will work** (see
[[machine-capability-preflight]]). When Chromium isn't installed, the PDF button in Step 5
(and Step 6's cover letter button) appears greyed out with an explanation — either run
`sartor --setup` to install Chromium, or use DOCX or Markdown instead `[synthesis]`. The
live preview stays available and already shows exactly what PDF would produce. Run
`sartor --doctor` anytime to check what's ready on your machine before you generate.

**On macOS 12 and earlier,** PDF output is unavailable — current Chromium releases don't
support those versions. DOCX, Markdown, and the live preview all work; use those instead
`[synthesis]`.

## What you download matches what you saw
Whatever format you choose, the download is built from the **same structured
document** that produced the on-screen preview — so the Word file you save has the
same sections and content as what you reviewed, not a second, independently-parsed
copy `[synthesis]`. If your download starts, but seems to hang or never appears, it's
following a normal browser download link rather than a pop-up, so check your browser's
download manager or downloads folder before assuming it failed.

## Downloading with your edits
If you fixed wording in the preview (see [[editing-and-refining]]), the Download button
rebuilds the file **from your edited text**, so the document you save matches exactly
what you see on screen — your edits are never left behind.

How the document *looks* is a separate choice — see [[resume-templates]]. For the whole
path from job posting to download, see [[tailoring-a-resume]].

## Related

- [[machine-capability-preflight]] — how Sartor checks whether PDF rendering is available on your machine.
- [[document-rendering]] — the technical side of how documents are built and rendered.
- [[troubleshooting]] — what to do if PDF output is unavailable or other errors occur.
