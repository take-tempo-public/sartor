# Coaching several people

> **Purpose:** how to use one copy of Sartor to tailor résumés for more than one person — a
> career coach, a recruiter, or someone helping friends and family — and how each person's
> information is kept apart.
> **Audience:** `user` — anyone tailoring résumés for other people. No technical knowledge
> assumed.
> **Type:** how-to
> **Authoritative for:** creating and switching between people; what belongs to each person;
> the roster and the cross-person Pipeline view; how people's data is separated. The single-person flow is
> in the [walkthrough](walkthrough.md); later applications for one person are in
> [Iterating](iterating.md).

Sartor calls each person a **user**. Everything you do in the app belongs to whichever user
is selected, so working for several people means creating one user per person and switching
between them.

---

## Adding a person

**How:** in the **User selection** panel at the top, click **New user** and fill in:
- **Full Name** and **Email** (required);
- **Username** (required). It's filled in from the name, and the hint explains it: "this is
  your storage key, edit anytime". It names that person's folders on disk, so something short
  and recognizable works best;
- **Phone**, **LinkedIn** and **Website** (optional).

Click **Create**. The new person starts with an empty career corpus; import their résumé on
the **Career corpus** tab, as in the [walkthrough](walkthrough.md#import-your-existing-résumé-one-time).

## Switching between people

Choose a name from the **-- Select User --** list. Switching takes you to Step 1 for that
person; nothing is lost from the person you left. To pick up an application where you left
off, open it from **Pipeline** and click **Resume in wizard** (see
[Iterating](iterating.md#opening-an-application)).

**Once you have six or more people**, a search box ("Search candidates by name…") appears above
the list. Each result shows the person's latest application and how many applications they
have in each status. Below six, the plain list is quicker, so the search stays hidden.

---

## What belongs to each person

| Belongs to one person | Where you see it |
|---|---|
| Career corpus: roles, bullets, skills, education, summary variants | **Career corpus** tab |
| Candidate memory: their answers to clarifying questions | **Candidate memory** tab |
| Uploaded résumé templates | **Résumé templates** tab, **My templates** |
| Profile details and settings | **⚙ Settings** |
| Their applications and generated files | **Tailor** and **Pipeline** tabs; files under `output/<username>/` |

Shared by everyone: the four bundled templates, and the app itself.

**How the separation works, and its limit.** Each person's information is stored under their
own profile, and when Sartor tailors a résumé it reads only the selected person's corpus and
answers. But there are **no accounts or passwords**. Sartor is a single-user app running on your own
computer, and anyone who can use that computer can select any user. If the people you coach
must not see each other's information, don't share one computer or one copy of Sartor between
them. See [`SECURITY.md`](../../SECURITY.md) for what stays on your machine.

---

## Seeing everyone's applications at once

The **Pipeline** tab shows **every person's** applications together, grouped into five columns
by status: **Draft**, **No response yet**, **Got interview**, **Rejected**, and **Withdrawn**.
Each card starts with the person's name.

**Why you'd use it:** to see at a glance who is waiting to hear back, who has an interview, and
whose drafts are still unfinished.

**How:** click a card. Sartor switches to that person and opens the application's details,
where you can record what happened (**Mark submitted**, then **Got Interview**, **Got
Rejection** or **Withdrew**) and add notes. The details are described in
[Iterating](iterating.md#finding-earlier-applications).

---

## Removing a person

There is **no way to delete a person in the app today**. The only thing you can remove is a
single application, by retiring it (and read the caveat about retiring in
[Iterating](iterating.md#retiring-an-application) first). Tracked as
[item 133](../dev/work/items/0133-no-way-to-delete-a-candidate-profile.md).
