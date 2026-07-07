# 10 — Job Seeker

> The primary persona. This walks every path a job seeker touches, as a
> task-outline: what the step does, what the user sees and thinks, and where
> friction shows up. Friction items are tagged **[F-xx]** and detailed in
> [40-friction-register.md](40-friction-register.md). Screenshot suggestions are
> marked **📸**.

Persona: *Jordan*, a mid-level SRE. Has an existing résumé, wants to tailor it to
a specific "Senior SRE" posting and download a polished document.

---

## Path A — First run

**Goal:** get from "never seen this" to "ready to work."

1. **Land on the app.** No users exist yet. Jordan sees the Tailor tab with a
   "USER SELECTION" panel and an empty dropdown, and an auto-opened **"Welcome to
   sartor"** modal that explains the corpus idea in three sentences and points out
   the per-section "(i)" help. *Clear, friendly, sets the mental model.* Closes it
   with "Got it."
2. **Create a user.** Clicks "New user," fills a **username** (required) plus
   optional name/email, clicks Create.
   - *Friction* **[F-05]**: "username" is a technical identifier (used for the
     on-disk folder). A job seeker thinks in terms of their name, not a username.
     Low-stakes but slightly jarring as the very first input.
3. **Auto-routing.** Because the corpus is empty, the app lands Jordan on the
   **Career corpus** tab (not the wizard) and arms a first-run tour. *This is the
   right call — you can't tailor from nothing — but the jump from "I just made an
   account on the Tailor tab" to "now I'm on a different tab" is unexplained in the
   moment.* **[F-06]**

**📸 Screenshot (welcome):** The dark landing with the amber-bordered "Welcome to
sartor" modal centered, "Got it" button bottom-right. **📸 (empty corpus):** The
Career corpus tab with the violet onboarding banner, "+ ADD EXPERIENCE / + Import
résumé / Find duplicates" toolbar, and the empty "SUMMARY VARIANTS" and "SKILLS"
sections reading "No … yet."

---

## Path B — Import a résumé into the corpus

**Goal:** turn an existing résumé into structured, editable corpus material.

1. **Click "+ Import résumé"** and choose a `.docx` / `.pdf` / `.md`. A real
   Haiku extraction runs (5–20 s) and parses the file into experiences.
2. **Review the result.** The corpus fills with experience cards (Jordan's import
   produced 2 roles, 9 bullets, 2 titles), and a status line reports "ADDED 2
   EXPERIENCE(S), 0 MERGED, … 9 BULLET(S) — NOW PENDING REVIEW BELOW." The
   onboarding banner shows "9 bullets + 2 titles pending review."
   - *Friction* **[F-02]**: the import extracts experiences/bullets/titles (and a
     summary variant if the résumé has a summary section) but **not skills**. The
     SKILLS section stays "No skills yet," even though the résumé listed them. A
     job seeker reasonably expects their skills to import.
3. **Expand a card** to see the extracted bullets, each tagged OUTCOME /
   NO-OUTCOME and PENDING, with per-bullet Accept / Retire / +tag, plus TITLES and
   ROLE INTRO VARIANTS sub-sections. *This is a genuinely powerful editing surface
   — everything is structured and inline-editable.*

**📸 Screenshot (after import):** The corpus with two experience cards ("Holden
Networks · Site Reliability Engineer · 5 bullets · 5 pending" and "Stratford
Analytics · Production Engineer · 4 bullets · 4 pending") and the pending banner.
**📸 (card expanded):** One card open showing COMPANY/LOCATION/START/END fields,
the TITLES row with OFFICIAL + PENDING chips, and the BULLETS list with green
OUTCOME / amber NO-OUTCOME chips and Accept/Retire per row.

---

## Path C — Curate the corpus

**Goal:** confirm the imported material and shape it.

1. **Accept all pending.** The banner's "Accept all pending" clears the PENDING
   flags across all roles.
   - *Friction* **[F-07]**: this is gated behind a **native browser `confirm()`
     dialog** ("Accept every pending item across all roles?") — and the code
     itself notes the action "isn't itself destructive" (`app.js:4507-4519`).
     Native `confirm()` is actually the app's *consistent* pattern for high-stakes
     actions (~10 call sites), so the friction is twofold: these OS dialogs clash
     with the otherwise custom-styled modal aesthetic, and gating a
     non-destructive bulk-accept behind one adds a stop where none is needed.
2. **Ready state.** With zero pending, the banner flips to "✓ Your career corpus
   is ready" and offers a **"Start tailoring →"** CTA that jumps to the Tailor tab.
   *Excellent hand-off — the app tells you you're done and where to go next.*
3. **Other curation surfaces on this tab** (all optional, all no-LLM unless noted):
   - **Summary variants** — add/edit/retire candidate-level positioning summaries.
   - **Skills editor** — add skills, and Approve/Deny skills that Compose
     suggested. *Empty after import (see F-02).*
   - **Find duplicates / Merge suggestions** — deterministic duplicate-role
     detection; "Merge into one / Keep separate." (Not triggered by a single
     import; appears with overlapping roles.)
   - **Tags** — link role/domain/skill/tech tags to bullets, titles, skills.
   - **Retire / Show retired** — soft-hide anything; nothing is destroyed.

**📸 Screenshot (ready):** The banner in its green "✓ Your career corpus is
ready" state with the "Start tailoring →" button.

---

## Path D — The wizard

The core loop. Each step is a task with a clear "what it does / what Jordan
thinks."

### Step 1 — Job + Analyze

1. **Paste the JD** into the textarea, click **Analyze**. A ~40 s Sonnet call
   (the pipeline's latency bottleneck) produces the analysis.
2. **Read the analysis.** Jordan sees: a **Keyword Match Score** (a big
   percentage), ESSENTIAL SKILLS chips, HIDDEN QUALITIES SOUGHT, KEYWORDS MATCHED
   (green) vs KEYWORDS MISSING (red), a Strengths/Gaps comparison, per-experience
   SUGGESTIONS, KEYWORD PLACEMENT SUGGESTIONS, and an OVERALL STRATEGY.
   - *Friction* **[F-01] (highest priority)**: the score read **18%** for a strong
     SRE-to-SRE match, and the "KEYWORDS MISSING FROM RESUME" set included
     **"lattice" and "lattice cloud" — the hiring company's own name** — plus
     generic tokens like "hiring / drive / serving." Counting the employer's name
     and filler words as "missing" deflates the headline number. A qualified
     candidate meeting a scary "18%" at the very first gate is the single most
     likely place to lose trust or bail.
   - *Friction* **[F-12]**: the analysis is a dense, long wall of chips and prose.
     It is impressive and genuinely useful, but there is no progressive
     disclosure — everything is expanded at once. First-timers may not know what to
     do with it.
3. **Move on.** Two CTAs: **"Continue to Clarify →"** (which auto-fetches the
   clarify questions in one action) or **"Skip to Compose →"**.

**📸 Screenshot (analysis):** The full Analysis panel — the amber "KEYWORD MATCH
SCORE: 18%" bar at top, the chip clouds (ESSENTIAL SKILLS, KEYWORDS MATCHED green
/ KEYWORDS MISSING red — with "lattice cloud" visibly among the red), and the
long SUGGESTIONS / OVERALL STRATEGY prose below. Annotate the "lattice cloud" chip
as the F-01 evidence.

### Step 2 — Clarify

1. **Questions appear** (Jordan got 5), each a targeted probe ("Have you worked
   with distributed tracing…?", "…have you defined SLOs…?"), tagged
   EXPERIENCE_PROBE / CONTEXT / SCOPE.
2. **Answer freely, or skip.** Answers persist to **Candidate memory** and widen
   the grounding allowance (the app may cite them). *This is a smart way to pull
   out résumé-absent facts.*
3. **Submit** → the app advances to Compose and fires the recommend cascade.

**📸 Screenshot (clarify):** The Clarify panel with 4–5 question cards, each a
label + textarea, and the "Submit answers" / "Skip" controls.

### Step 3 — Compose

The strongest screen in the product.

1. **Positioning card** — a drafted, editable 2-sentence summary tailored to this
   JD, with Regenerate / Retire. (It "freezes" when you continue.)
2. **Per-experience cards** — each opens with a plain-language **fit note**
   ("Direct match on Kubernetes (EKS), control-plane reliability ownership,
   incident leadership … — all core JD requirements"), a **title picker** for this
   résumé, and **RECOMMENDED BULLETS** ranked by fit with PIN / EXCLUDE, a fit
   score, and drag-to-reorder.
3. **Gap-fill lane** — "SUGGESTED FOR THIS JD": grounded NEW bullets for
   requirements the corpus doesn't yet cover, each with a **"Covers: …"** line
   naming the requirement it addresses, and Accept / Retire. *The "Covers:"
   explanation is exemplary UX — it makes an AI suggestion legible.*
4. **Skills card** — recommend/suggest/drop skills for this JD. *Absent for Jordan
   because the corpus has no skills (F-02) — a visible downstream cost of the
   import gap.*
5. **Continue** → "Save and continue to Template."

- *Friction* **[F-13]**: Compose can present a lot at once (recommended bullets +
  a 4-item gap-fill lane per role + titles + skills + positioning). It is well
  organized, but a first-timer may not realize the gap-fill bullets are *optional
  suggestions* rather than things they must act on.

**📸 Screenshot (compose):** One experience card fully expanded — the italic fit
note, the title radio row, 4–5 RECOMMENDED bullet rows with PIN/EXCLUDE + score
chips, and below them the "SUGGESTED FOR THIS JD" gap-fill lane with "Covers:…"
sublines and Accept/Retire. This is the screen that best sells the product.

### Step 4 — Template

1. **Pick a template.** Four bundled ATS-safe options (Classic, Modern, Spacious,
   Tech), each with a one-line "who it's for" description, plus ALL/BUNDLED/MINE
   filters and "+ Upload .docx."
2. **Live WYSIWYG preview.** The right pane renders the actual résumé paginated as
   Letter pages, labeled "WYSIWYG — THIS HTML IS EXACTLY WHAT THE PDF RENDER USES."
   *Honest and reassuring; the content is real, tailored, and readable.*
3. **Continue to Generate.**

**📸 Screenshot (template):** The split view — template list on the left (Classic
selected, "ATS-SAFE" badges), and the live preview on the right showing "Jordan
Rivera," the SUMMARY, and EXPERIENCE with real bullets, "Page 1 of 1."

### Step 5 — Generate

1. **Choose format** (DOCX / PDF / Markdown) and click Generate. On the happy path
   this is **deterministic assembly** of the frozen composition — fast, no LLM for
   the résumé body (a legacy fallback still calls the LLM if no frozen composition
   exists; the cover letter is always a separate call).
   - *Opportunity* **[F-09]**: the reproducibility and speed are a genuine strength
     but are never surfaced. A one-liner ("assembled exactly from your approved
     composition — same every time") would build trust.

**📸 Screenshot (generate):** The compact Generate panel — the format toggle
(DOCX highlighted) and the Generate button, with the wizard rail showing steps
1–5 green.

### Step 6 — Download / refine / cover letter

1. **Preview the output** in an iframe (résumé tab), with an "Edit before
   downloading" drawer for inline tweaks.
2. **Download résumé** in the chosen format.
   - *Friction* **[F-10]**: the panel itself warns that Chrome may silently block a
     second download without a fresh gesture, with a manual workaround, and notes a
     future server-side fix. Honest, but it means the very last step (getting the
     file) can quietly fail.
3. **Refine** — a scoped content adjustment box ("make the tone more formal,"
   "emphasize cloud experience"); a scope check flags fact-changing edits.
4. **Generate cover letter** — a focused Sonnet call renders a business-letter
   cover letter styled to the chosen template, with its own DOCX/PDF/Markdown
   picker.
5. **Get follow-up questions** (iterate-clarify) — post-generation interview
   questions driven by drift signals, to feed another iteration.
6. **"What changed?"** — a modal summarizing changes made + proofread notes.
7. **Mark submitted** — moves the application's lifecycle status.

- *Friction* **[F-14]**: editing the preview and then clicking Refine or the
  follow-up questions triggers a **"You edited the preview"** gate modal ("Use
  edits as baseline / Discard / Cancel"). The concept (first-person edits are
  ground truth) is sound, but the modal appears at a moment the user may not
  associate with "editing," and its wording is dense.

**📸 Screenshot (output):** The Step-6 panel — RÉSUMÉ / COVER LETTER tabs, the
live preview, the "Download résumé / + Generate cover letter / What changed?" row,
the Chrome-download caveat text, and the DOCUMENT REFINEMENT box with Refine / Get
follow-up questions. **📸 (edit gate):** the "You edited the preview" modal.

---

## Path E — Applications tracker

**Goal:** manage tailoring runs over time.

1. **See prior applications** on the Tailor tab (above the wizard): each card
   shows title, status (DRAFT/…​), iteration count, age, "Mark submitted," and
   "Retire," with a status filter and "Show retired."
   - *Friction* **[F-15]**: applications show a **null company** and a generic
     title ("Senior Site Reliability Engineer") because the JD's company ("Lattice
     Cloud") isn't auto-extracted onto the application. The tracker is less useful
     when cards can't be told apart by employer.
2. **Open a card** → detail modal with **editable title/company**, notes
   (save-on-blur), iteration history, and **"Resume in wizard."**
3. **Resume in wizard** restores the full Step-6 state with the generated résumé
   and a "Resumed from prior application" badge. *This works well — you land
   exactly where you left off.*

**📸 Screenshot (app detail):** the detail modal with editable Title/Company
inputs, the Notes area, and the "Resume in wizard" button.

---

## Path F — Candidate memory

**Goal:** reuse facts surfaced during clarifications.

1. **Browse Q&A pairs** accumulated across every application, with search, a kind
   filter, and "outcome-rich only" / "show promoted" toggles.
2. **Promote to bullet** — turn a strong answer into a new pending corpus bullet.
   *A genuinely clever loop: interview answers become durable résumé material.*

**📸 Screenshot (memory):** the Candidate memory tab with two EXPERIENCE_PROBE
Q&A cards (one carrying a green OUTCOME chip) and "Promote to bullet" buttons.

---

## Path G — Settings / profile

1. **Open Settings** (top-bar pill) → a right drawer with the profile: name,
   email, phone, LinkedIn, website, **skills**, **certifications**, **education**,
   notes ("directives for the LLM"), portfolio URLs, plus **Save config** and
   **Fetch profile content** (opt-in scrape of your links for extra context).
   - *Friction* **[F-03]**: **skills** here (flat, comma-separated) look like a
     *second* skills home next to the structured corpus Skills editor — but they
     are asymmetric. The flat field is a **one-time seed**: on a user's first
     analyze (before any corpus Skill row exists) it is imported into corpus Skill
     rows (`onboarding/corpus_import.py:178-191`); after that the **corpus is
     authoritative** and the flat field goes inert. So a user who later edits
     Skills in this drawer, expecting it to affect output, is editing a dead
     control. Two visible homes, only one of them live.
   - *Friction* **[F-04]**: **certifications** and **education** are editable *only*
     here as flat free text — there is **no structured corpus panel/CRUD** for
     them, unlike experiences and skills. (Backing DB tables do exist and are read
     for context; they're just not surfaced as a corpus editor.) Sitting in a
     "profile" drawer away from the corpus makes them easy to forget.

**📸 Screenshot (settings):** the Settings drawer open over the Candidate memory
tab, showing the PROFILE fields (Name filled, SKILLS/CERTIFICATIONS/EDUCATION as
empty placeholders) and the "Fetch profile content" button.

---

## Path H — The doc-grounded assistant

1. **Open the assistant** (magnifier pill) → a modal: "Ask how sartor works or how
   to use it, and I'll answer from the project's own docs and code — with
   citations." A **Dev mode** toggle adds technical depth.
2. **Ask a question** → a streamed answer with **inline numbered citations**
   ([1][2]…) that are clickable links, a **Sources** key listing each cited page,
   and a "report it on the project's GitHub" fallback.
   *A standout feature — grounded, cited, honest about what it knows. Valuable to
   every persona, and a strong trust signal.*

**📸 Screenshot (assistant):** the "Ask the assistant" modal with the question
filled, the multi-paragraph answer carrying inline [1][2][3] links, and the
"SOURCES: [1] using-sartor · [2] career-corpus · [3] tailoring-a-resume · [4]
docs/walkthrough.md:151" key beneath it.

---

## Path I — Help + tour (cross-cutting)

- Every panel header carries an **"(i)"** that opens a shared help modal with a
  focused explanation of that panel.
- A **first-run tour** fires each wizard step's help once-ever for a brand-new
  user.
- *Assessment:* the help system is thorough and well-built (one shared modal
  primitive, per-panel content, seen-once memory). The risk is the opposite of
  most apps — there is a *lot* of guidance, and combined with the density of
  Analyze and Compose it can feel like a firehose on the first pass. This argues
  for tightening the primary screens (F-01, F-12) rather than adding more help.

---

## Job-seeker verdict

The end-to-end job is real and good: Jordan imported a résumé, tailored it to a
specific job with grounded, explained suggestions, previewed exactly what would
download, and got a strong résumé and cover letter — without the app inventing
anything. The friction is concentrated at **two moments**: the **Analyze gate**
(a scary, deflated score in a wall of text) and the **skills gap** (not imported,
two homes). Fix those two and the first-run experience goes from "impressive but
intimidating" to "trustworthy and smooth."
