# Editing and refining your résumé

> **Purpose:** the user-facing explanation of changing a generated résumé — editing
> the text in place, asking sartor to refine it, and how a refinement request is
> reviewed before it changes anything.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the editable preview + edit drawer + refinement-scope modal in
> `templates/index.html` (`#resumePreview`, `#editDrawer`, `#refinementInput`,
> `#refinementScopeModal`) driven by `static/app.js` (`openEditDrawer`,
> `submitRefinement`, `_submitSurgicalRefinement`, `_showRefinementScopeModal`,
> `_wireLiveEditPreview`, `runIterateClarify`); the routes
> `blueprints/generation.py:save_edits`, `blueprints/generation.py:validate_refinement`,
> and `blueprints/templates.py:preview_edited_html`; the surgical-refinement routes
> `blueprints/applications.py:draft_application_refinement`,
> `blueprints/applications.py:accept_application_refinement`, and
> `blueprints/applications.py:draft_application_gap_fill`.

---

Once sartor generates your résumé in **Step 6**, the result isn't fixed — you can
shape it two ways: edit the words yourself, or ask sartor to refine it for you.

## Editing the text yourself
The preview is editable. Click into it (or open the edit drawer) and fix wording
directly. As you type, the styled page preview alongside it updates too, so what you
see there tracks what Download would actually produce — it no longer waits for a
refine or an explicit save to catch up `[synthesis]`. Your edits become the **starting
point for the next version**, so nothing you change is lost when you regenerate or
refine. **Editing here changes the document text only — it does not change your
[[career-corpus]].**

## Asking sartor to refine
Type a short instruction in the refinement box — "tighten the summary", "lead with the
data role" — and click **Refine**. sartor first checks the request doesn't quietly
change a fact rather than just wording; if it looks like it might (for example, asking
to add a number or a claim that isn't already true about you), a small dialog explains
the concern and lets you **cancel** or **proceed anyway** — this never silently blocks
a correction you actually want to make `[synthesis]`.

Once through that check, sartor doesn't rewrite the whole résumé — it drafts **one
targeted change** (a sharpened bullet, or a new positioning summary) grounded in your
real history, and takes you back to **Compose** to **accept** or **retire** it. Accepting
folds the change into your approved content the same way any Compose edit does; from
there, generating again rebuilds the document from your approved composition
`[synthesis]`. You can also ask **follow-up questions** to draw out more detail, the
same way Clarify did earlier; those answers are kept in your [[candidate-memory]].

## Refreshing suggested bullets in Compose
While you're in Compose, sartor may suggest extra bullets for roles that look thin —
these are optional, marked so, and you choose to accept or ignore each one (see
[[career-corpus]]). If you want a fresh set, a **Regenerate suggestions** control
drafts new ones; any suggestion you've already dismissed stays dismissed even after
you regenerate.

## How versions build on each other
Each refinement starts from the latest approved content — your edits and accepted
changes first. That's why small fixes stick: sartor carries them forward instead of
starting over. When the wording is right, download it — see
[[downloading-your-documents]].

Back to [[tailoring-a-resume]].
