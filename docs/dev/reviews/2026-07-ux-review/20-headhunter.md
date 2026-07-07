# 20 — Headhunter / Coach

> The multi-candidate persona: a recruiter or career coach who tailors résumés on
> behalf of several people. They use the same app as the job seeker, so this
> document focuses on what is *different* — the multi-candidate model, the
> surfaces that matter most to them, and where a single-user product strains at
> agency scale. Friction tagged **[F-xx]** (see
> [40-friction-register.md](40-friction-register.md)); screenshots **📸**.

Persona: *Priya*, a technical recruiter placing SREs and platform engineers. She
runs several candidates at once and needs to move fast without mixing them up.

---

## The core model: one "user" per candidate

sartor. has no first-class notion of a "candidate roster." Each candidate is a
**user** — a username with an isolated corpus, config, and applications. Priya
creates one user per person and switches between them via the **User Selection**
dropdown.

This was verified live: creating a second candidate (`casey`) alongside the first
(`jordan`) produced a fully isolated corpus (casey empty, jordan with 2
experiences) and a picker listing both. The isolation is clean and correct — no
data leaks between candidates.

- *Friction* **[F-08] (headhunter-defining)**: the picker is a **flat
  `<select>` of usernames** with no search, no per-candidate metadata (target
  role, company, pipeline stage), no "who needs attention" view, and no grouping.
  For 3 candidates it's fine; for 30 it doesn't scale. The "user" abstraction is a
  single-job-seeker model lightly repurposed, and a recruiter feels that ceiling
  first.
- *Friction* **[F-05]**: creating a candidate asks for a **username** (a technical
  slug used for the on-disk folder) rather than just the candidate's name. Priya
  has to invent and remember identifiers.

**📸 Screenshot (multi-candidate):** the User Selection dropdown open, showing
"— Select User —", "casey", "jordan" — the entire candidate roster is this list.
Annotate it as the F-08 scaling limit.

---

## Path A — Onboard a candidate

Same as the job seeker's import path, done on someone else's behalf:

1. Create the candidate (user), land on their empty Career corpus.
2. Import their résumé → review the extracted experiences/bullets/titles →
   Accept all.
3. Because Priya is doing this repeatedly, the friction items compound:
   - **[F-02]** skills don't import — she must add each candidate's skills by hand
     or lean on Compose's "suggest skills" every time.
   - **[F-07]** the native `confirm()` on Accept-all is one extra OS popup per
     candidate.

**📸 Screenshot:** a freshly created candidate landing on the empty Career corpus
with the "Go to Career corpus" empty-state framing — the recruiter's repeated
starting point.

---

## Path B — Tailor for a candidate

Identical to the job-seeker wizard (see [10-job-seeker.md](10-job-seeker.md),
Path D). Two notes specific to the recruiter:

- The **Compose** screen is where Priya adds the most value — pinning the bullets
  that match a specific client's must-haves, accepting gap-fill bullets that speak
  to a requirement, and choosing the title the client's ATS expects. The per-role
  fit notes and "Covers: …" gap-fill sublines make it fast to justify choices to a
  candidate.
- The **Analyze** score problem **[F-01]** matters differently here: a recruiter
  is not discouraged by a low "18%," but if she forwards or screenshots the
  analysis to a candidate, a deflated score reads badly. The number needs to be
  defensible.

---

## Path C — Template / brand management

The **Résumé templates** tab is more important to a recruiter than to a job
seeker, because agencies often have a house style:

1. Four bundled ATS-safe templates ship read-only, each with a "who it's for"
   description (e.g. Spacious for "early-career or career-changing candidates").
2. **Upload a `.docx`** to add a house template; uploaded personas are **scoped to
   the current user (candidate)**.
   - *Friction* **[F-16]**: because personas are per-user, a recruiter's house
     template must be **re-uploaded for every candidate**. There's no shared or
     account-level template library. For an agency this is real repeated work.
3. Rename / set default / preview / delete apply only to your own uploads.

**📸 Screenshot (templates):** the Résumé templates tab — the four bundled cards
with descriptions and "ATS-SAFE" badges, the "MY TEMPLATES" section, and the
"UPLOAD .DOCX TEMPLATE" control.

---

## Path D — Candidate memory as interview prep

The **Candidate memory** tab is a natural recruiter tool: it accumulates the Q&A
pairs surfaced during clarifications across all of a candidate's applications.

- Priya can search it, filter to "outcome-rich" answers, and use it as a
  ready-made **interview-prep brief** — the candidate's own words about scope,
  metrics, and ownership.
- **Promote to bullet** lets her fold a strong answer back into the corpus.

*Assessment:* this is quietly one of the best recruiter features — it just isn't
framed as one. Nothing in the UI says "use this to prep your candidate."

**📸 Screenshot (memory as prep):** the Candidate memory tab filtered to
outcome-rich answers, highlighting the measurable-result Q&A ("cut MTTR ~40% …")
as the kind of material a recruiter coaches on.

---

## Path E — Pipeline management (the gap)

Priya's real job is managing a *pipeline* — which candidates are active, which
applications are out, which need follow-up. sartor. has the raw material (per-user
applications with statuses: draft / submitted / interview / rejected / withdrawn)
but no cross-candidate view:

- The **Prior Applications** list is **per selected user only**. There is no
  "all my candidates' applications" dashboard, no "3 interviews this week," no
  sorting by stage across people.
- *Friction* **[F-17]**: a recruiter cannot see their book of business in one
  place. Every status check is "switch user → read list → switch user."

This is not a bug — it's the boundary of the single-user design. It's the clearest
signal of where a "pro / agency" tier would begin.

---

## Headhunter verdict

Everything a recruiter needs for the *tailoring* job is here and often excellent
(Compose, candidate memory, ATS-safe templates, clean per-candidate isolation).
What's missing is everything about *managing many candidates*: a real roster
(F-08), account-level templates (F-16), and a cross-candidate pipeline view
(F-17). The good news is that the data model already supports all of it —
candidates, applications, and statuses exist as structured rows. The gap is
presentation, not architecture. A recruiter-focused "roster + pipeline" surface
layered on the existing model would convert sartor. from "a tool I use per
candidate" into "where I run my desk."
