# Editing and refining your résumé

> **Purpose:** the user-facing explanation of changing a generated résumé — editing
> the text in place, asking sartor to refine it, and how your edits carry into the
> next version.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the editable preview + edit drawer in `templates/index.html`
> (`#resumePreview`, `#editDrawer`, `#refinementInput`) driven by `static/app.js`
> (`openEditDrawer`, `submitRefinement`, `runIterateClarify`); the deterministic
> `save_edits` route + the draft-precedence selection in `blueprints/generation.py`.

---

Once sartor generates your résumé in **Step 6**, the result isn't fixed — you can
shape it two ways: edit the words yourself, or ask sartor to refine it for you.

## Editing the text yourself
The preview is editable. Click into it (or open the edit drawer) and fix wording
directly. Your edits become the **starting point for the next version**, so nothing you
change is lost when you regenerate or refine. **Editing here changes the document text
only — it does not change your [[career-corpus]].**

## Asking sartor to refine
Type a short instruction in the refinement box — "tighten the summary", "lead with the
data role" — and sartor rewrites the draft with that in mind, still grounded in your
real history. You can also ask **follow-up questions** to draw out more detail, the same
way Clarify did earlier; those answers are kept in your [[candidate-memory]].

## How versions build on each other
Each refinement starts from the latest text — your edits first, then the last generated
draft. That's why small fixes stick: sartor carries them forward instead of starting
over. When the wording is right, download it — see [[downloading-your-documents]].

Back to [[tailoring-a-resume]].
