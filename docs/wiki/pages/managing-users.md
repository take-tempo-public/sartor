# Managing users — adding and switching

> **Purpose:** the user-facing explanation of using sartor with more than one person
> on a machine — adding a user, switching between them, and how each person's data
> stays separate.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the user selector + new-user form in `templates/index.html`
> (`#userSelect`, `#newUserForm`) driven by `static/app.js` (`loadUsers`,
> `createUser`, `onUserSelect`); the deterministic `create_user` / `list_users` /
> `get_config` routes in `blueprints/users.py`.

---

sartor supports more than one person on the same machine. Each user is a separate
profile with its own corpus, résumés, and settings.

## Adding a user
Use the user dropdown at the top of the app and choose **New user**. Fill in your name
and contact details and create the profile — sartor sets up your own space and starts
your first [[career-corpus]] when you import a résumé (see
[[importing-your-experience]]).

## Switching users
Pick a different name from the same dropdown to switch. sartor loads that person's
profile — their corpus, their settings, their tailored applications — and leaves yours
untouched.

## Everyone's data stays separate
Each user's information is kept apart and **never shared between users** — the same
promise the [[career-corpus]] and [[candidate-memory]] pages make. It all stays on this
machine.

See [[using-sartor]] for the whole first run.
