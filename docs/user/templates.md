# Résumé templates

> **Purpose:** how to choose a résumé template, and how to use your own Word document as
> one, including the rules a template must follow so screening software can still read the
> résumé it produces.
> **Audience:** `user` — anyone choosing or uploading a résumé template. No technical
> knowledge assumed.
> **Type:** how-to
> **Authoritative for:** the ATS rule set every template (bundled or uploaded) should follow;
> what the bundled templates are for; how uploading your own works and what Sartor checks.
> How the bundled templates are built and how to add one is maintainer material, in
> [`docs/dev/bundled-templates.md`](../dev/bundled-templates.md).

A template controls how your résumé **looks**: fonts, sizes, spacing, alignment. It never
changes what your résumé **says**. The content comes from what you approved in Compose, and
the same content can be shown in any template.

---

## Choosing a bundled template

Sartor ships four templates. All four are built to be read reliably by applicant tracking
systems (ATS), the software many employers use to read incoming résumés.

| Template | Typeface | A good fit when |
|---|---|---|
| **Classic** | Arial | You want the safest, most conventional choice. It's also the fallback. |
| **Modern** | Calibri, small-caps headings | You want a slightly more contemporary look for most roles. |
| **Spacious** | Arial, generous spacing | You're early in your career or changing fields, and have less to fit on the page. |
| **Tech** | Georgia, centered name, underlined headings | You're applying for engineering, data or AI roles. |

**Where to choose:** in the wizard's **Step 4 — Template**, click a template card. The
preview on the right redraws right away, with no AI call and no cost. You can also browse
them on the **Résumé templates** tab.

**What to check:** the page count in the preview, and whether the style suits your field.
If a mid-career résumé previews at five pages, go back to Compose and exclude some bullets
rather than looking for a smaller template.

---

## Using your own Word template

**Why you'd do it:** to keep a look you already have, such as a résumé design you've used
before.

**How:**
- In **Step 4**, click **+ Upload .docx**, or
- on the **Résumé templates** tab, under **My templates**, click **UPLOAD .DOCX TEMPLATE**.
  You can give it a display name first.

Uploaded templates belong to the user who uploaded them; other users on the same machine
don't see them. You can rename or delete your own uploads, but not the bundled four.

**What to expect:**
- Your template shows an **ATS · unverified** badge. Sartor can't inspect an arbitrary Word
  file closely enough to promise it's ATS-safe, so follow the rules below.
- **Fonts.** Sartor's output uses one of three fonts: Arial, Calibri or Georgia. If your
  template uses another font, the résumé Sartor produces uses the closest of those three
  instead. The app doesn't show a notice when this happens yet.
- The downloaded `.docx` can differ slightly in styling from the preview; the `.pdf`
  download matches the preview.

---

## The ATS rules every template should follow

These apply to the bundled templates and to anything you upload. They exist so that an ATS
reading your résumé finds every section and every bullet, in order.

| Rule | Why |
|---|---|
| Single column only | Multi-column layouts can be read line by line across the columns, mixing them up |
| No tables, text boxes, headers/footers, or images | Any of these can scramble the reading order or be dropped entirely |
| Fonts: Arial, Calibri, or Georgia | Unusual fonts may not be available to the reader, and a substitute changes line widths |
| 10–12pt body, 12–16pt headings | Smaller text risks misreading; larger is unusual for a résumé |
| Standard section headings: Experience, Education, Skills, Projects, Certifications, Publications | Screening software looks for these words to find each section |
| Bullet glyphs: `-` or `•` only | Other symbols may show up as boxes or disappear |
| Dates aligned right with a tab stop, not a table cell | Tab-aligned dates are read as part of the same line |
| Page margins 0.5–1.0 inch | Margins outside this range look unusual to some systems |

**What Sartor checks for you.** After every generation, Sartor reads its own `.docx` back the
way a simple screening parser would, and counts whether every section and bullet it wrote
comes back out. The result is shown per version of the application, as **ATS: pass**,
**warning** or **fail**, in the application's details on the **Pipeline** tab (see
[Iterating](iterating.md#finding-earlier-applications)).

This check is best-effort, not a certification. Real screening systems can't be tested
without commercial access, so a pass means no gross problems were found (lost sections,
scrambled bullets), not that any particular employer's system will accept the file.
