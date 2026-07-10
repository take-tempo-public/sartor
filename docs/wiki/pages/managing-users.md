# Managing users — adding and switching

> **Purpose:** the user-facing explanation of using sartor with more than one person
> on a machine — adding a user, switching between them, and how each person's data
> stays separate.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the user selector + new-user form in `templates/index.html`
> (`#userSelect`, `#newUserForm`) driven by `static/app.js` (`loadUsers`,
> `createUser`, `onUserSelect`, `_slugify`); the deterministic `create_user` /
> `list_users` / `get_config` / `candidate_roster` routes in `blueprints/users.py`.

---

sartor supports more than one person on the same machine. Each user is a separate
profile with its own corpus, résumés, and settings.

## Adding a user
Use the user dropdown at the top of the app and choose **New user**. The form leads
with your full name — type it and sartor derives a username automatically (you can
still edit the username by hand if you want a different one). Fill in your contact
details and create the profile — sartor sets up your own space and starts your first
[[career-corpus]] when you import a résumé (see [[importing-your-experience]]).

## Switching users
Pick a different name from the same dropdown to switch. sartor loads that person's
profile — their corpus, their settings, their tailored applications — and leaves yours
untouched. Once you have several people set up, a searchable list of candidates appears
above the dropdown so you can find someone by name instead of scrolling a plain list —
it's just a faster way to reach the same dropdown underneath, so nothing about switching
changes `[synthesis]` (grounded in
[`static/app.js`](../../../static/app.js)'s `loadCandidateRoster`, which shows the
search list once there are several candidates on the machine, and
[`blueprints/users.py:candidate_roster`](../../../blueprints/users.py)).

## Settings stay honest about where your data lives
Before you've imported anything or touched your Career corpus, the Settings drawer's
Skills / Certifications / Education fields are where that information lives. The moment
you do either, your [[career-corpus]] becomes the real home for that data, and Settings
replaces those fields with a pointer to the Career corpus tab instead of a second,
silently-stale copy — grounded in `needs_onboarding` on
[`blueprints/users.py:get_config`](../../../blueprints/users.py), which the Settings
drawer reads to decide which state you're in.

## Everyone's data stays separate
Each user's information is kept apart and **never shared between users** — the same
promise the [[career-corpus]] and [[candidate-memory]] pages make. It all stays on this
machine.

## Coverage gap
This page doesn't yet cover the read-only **Pipeline** tab (a cross-candidate view of
every candidate's applications by status) that appears alongside the searchable
candidate list once you're managing more than one person — flagged for a follow-up pass
rather than added here speculatively.

See [[using-sartor]] for the whole first run.
