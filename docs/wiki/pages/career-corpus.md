# Career corpus — the pool sartor writes from

> **Purpose:** the user-facing explanation of the career corpus — what it is, how
> it fills up, and how reviewing it improves your résumés.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the Career corpus tab in `templates/index.html` (`#panelCorpus`,
> `#educationEditorSection`, `#certificationsEditorSection`) + its review/accept
> flow in `static/app.js`; the accept routes in
> `blueprints/corpus/curation.py`; the Education/Certification CRUD in
> `blueprints/corpus/career_assets.py`; the corpus-wide skill suggestion route in
> `blueprints/corpus/skills.py`; mirrors the in-app corpus help.

---

Your **career corpus** is the pool of experience sartor draws from when it writes
a tailored résumé — the roles and bullet points it built from the résumé you
imported. It's yours, it stays on your machine, and it's never shared between
users.

## Building it
Import a résumé and sartor extracts your experience for you (see
[[importing-your-experience]]); you can also add experiences by hand, or mix both.
Each experience holds one or more **titles** (one
official, optional alternates) plus its **bullets**, and you can **tag** things to
organize them.

## Reviewing it
Everything new starts as **pending review**. Accept items one at a time, by role,
or all at once. Reviewing and accepting is worth the few minutes: it's how sartor
learns which of your accomplishments are real and ready to use, which sharpens
every résumé it writes afterwards.

## Skills
Skills are candidate-level, not tied to any one role. Import a résumé and any skills
it lists land here as pending too, ready to accept. If your corpus is still light on
skills, click **Suggest skills from my corpus** — sartor reads your whole career
corpus (no job posting needed) and proposes skills it can point to real evidence for;
each proposal shows up as pending, for you to approve or deny individually. Denying
a suggestion (pending or approved) is reversible — it moves to the collapsible
**Denied / retired skills** section and won't be re-suggested on future passes, but
you can restore it anytime via the Restore button `[synthesis]` (grounded in
[`blueprints/corpus/skills.py:delete_skill`](../../../blueprints/corpus/skills.py),
which soft-tombstones via `is_active=0`, and
[`static/app.js:_denySkill`](../../../static/app.js) which fires the delete, and
[`static/app.js:_renderDeniedSkillRow`](../../../static/app.js) which renders the restore
affordance). This skill-review flow is separate from the job-specific skill suggestions
sartor makes while composing a résumé for a particular posting (see [[tailoring-a-resume]]).

## Education & certifications
Below your roles, dedicated **Education** and **Certifications** sections hold your
degrees and credentials — add, edit, reorder, or remove entries directly; there's no
review step for these since you're typing them yourself rather than sartor extracting
them. Removing one retires it rather than deleting it outright, so nothing is ever
lost by accident `[synthesis]` (grounded in
[`blueprints/corpus/career_assets.py`](../../../blueprints/corpus/career_assets.py),
which soft-retires both entities the same way as everything else in your corpus).

## How it's used
When you tailor to a job (see [[tailoring-a-resume]]), sartor selects and orders
the strongest bullets — plus your accepted skills, education, and certifications —
from your accepted corpus for that posting. Edits you make *inside* a tailored
application affect only that application — your corpus changes only when you edit it
here, or when you accept a clarifying answer as a new bullet.

See [[using-sartor]] for the whole first run, and [[candidate-memory]] for where
clarifying answers are kept.
