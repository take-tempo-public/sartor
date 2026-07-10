# Résumé templates — how your résumé looks

> **Purpose:** the user-facing explanation of templates — what they control, the
> bundled set, and uploading your own.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the Résumé templates tab in `templates/index.html`
> (`#panelPersonas`) + the Step 4 template picker; mirrors the in-app templates
> help. Preview fidelity: `docx_to_persona_html.py` (`extract_persona_style`).

---

A **template** controls how your résumé *looks* — typography, spacing, and layout
— without changing a word of the content. The same tailored content can be rendered
through any template.

## The bundled set
A few ATS-friendly templates ship with the app. **ATS-safe templates are strongly
recommended** so applicant-tracking systems (the software many employers use to
read résumés) can parse yours cleanly. Bundled templates are read-only.

## Your own templates
You can upload your own `.docx` for sartor to reuse as a template — it's scoped to
your user, and you can rename or delete the ones you uploaded. You can do this on
the Résumé templates tab or right inside Step 4 of [[tailoring-a-resume]].

## Choosing one
In Step 4 the preview shows the pages closely matching how they'll print, so you can
compare the look before you generate — sartor reads spacing details (like the gap
around headings and job titles) out of your chosen `.docx` rather than guessing at
them, so the preview reflects that template's actual rhythm, not a generic
approximation `[synthesis]`. See [[using-sartor]] for the whole flow.
