# Documentation audit — v1.0.0 pre-release pass

> **Purpose:** capture the research findings + per-doc audit
> recommendations BEFORE any rewrite commits land. Reviewable in
> isolation so direction can be agreed before content changes.
> **Audience:** the user reviewing this pass; future contributors
> wondering why the docs look the way they do.
> **Authoritative for:** the recommended doc-graph structure, the
> retire-or-rewrite call on `vision.md`, the README rewrite shape.
> **NOT authoritative for:** prose of the rewrites themselves —
> those land in their own commits after this audit is approved.

---

## 1 — Research: how comparable projects organize docs

Surveyed three open-source projects with similar scope and
tenancy story (local-first, single-user, BYO API key, LLM-powered,
single-maintainer roots):

### [aider](https://github.com/Aider-AI/aider) — Python LLM pair-programmer

**README structure:** logo + headline ("AI Pair Programming in
Your Terminal") + tagline → Features (10 bulleted icons) →
Getting Started → More Information (links to aider.chat/docs) →
Community → About.

**Doc set:** README · CONTRIBUTING.md · HISTORY.md (their
CHANGELOG) · LICENSE. **No vision file.** Vision is implicit in
the README's first paragraph and Features list. Detailed docs
live on a separate static site (aider.chat/docs).

### [llm](https://github.com/simonw/llm) — Simon Willison's LLM CLI

**README structure:** one-sentence description → bulleted
capabilities list → "Quick start" → "More background on this
project" (links to blog posts that explain the why) →
"Contents" (extensive table of contents linking to docs site).

**Doc set:** README · AGENTS.md (modern equivalent of CLAUDE.md
— see below) · CHANGELOG.md · CONTRIBUTING (via footer) ·
LICENSE. **No vision file.** Background lives in blog posts on
simonwillison.net, linked from README.

### [continue.dev](https://github.com/continuedev/continue) — code agent platform

**README structure:** tagline → "How it works" → Install CLI →
Contributing → License. Notably short.

**Doc set:** README · CONTRIBUTING.md · CODE_OF_CONDUCT.md ·
SECURITY.md · CLA.md. **No vision file.** Their docs site
(docs.continue.dev) handles deeper material.

### Patterns common to all three

1. **No `vision.md`.** Vision is communicated via the README's
   opening + features list, or via linked external prose (blog
   posts). None of the three ships a separate file dedicated to
   "what this is for."
2. **README is the entry point** and stays brief — typically
   200-400 lines. Detailed walkthroughs, tutorials, and
   reference material live on a docs site or in a `docs/`
   directory, NOT inline in the README.
3. **CHANGELOG / HISTORY** is a separate file consistently
   referenced from the README via badge or link.
4. **CONTRIBUTING.md** is referenced from the README in the
   contributing section. Brief — points at the dev loop, code
   style, where to file PRs.
5. **AGENTS.md** is the tool-agnostic emerging convention for
   "what AI agents need to know about this codebase." Equivalent
   to our `CLAUDE.md`. simonw/llm uses AGENTS.md; aider does
   not yet have one. Either name is fine; AGENTS.md is more
   portable across LLM tooling but CLAUDE.md is Anthropic-native.

---

## 2 — Audit: current state per doc

Walk every top-level doc, identify debris and stale sections,
recommend an action.

### `README.md` — **REWRITE (substantial)**

**Current state:** ~350 lines. The recent Doc Map blockquote +
"What gets saved" + "Cost guidance" sections (from `319ae1b`) are
correct. The user's local-edit added the better title
("callback.") and an honest billing note. **But the body
(lines 17–158) is stale:**

- **Workflow diagram** at line 19 — references the OLD 4-stage
  flow ("Select User → Upload Resume → Paste JD → Review →
  Download"). The actual app has a 6-step wizard with different
  stage names (Job + Analyze → Clarify → Compose → Template →
  Generate → Download).
- **"Using the App" section** (lines 106–158) — 6 sub-sections
  walking through the OLD UI. References "Human Gate #1 / #2"
  which still exist but are now part of a six-step wizard, not
  the only structure. Mentions configuration fields that exist
  but now read as outdated copy.
- **"File Structure"** block (lines 162–202) — pre-DB-era. Says
  "context_{timestamp}.json" + "Generated documents" but doesn't
  mention `db/resume.sqlite`, the corpus model, persona
  templates, or the eval harness.
- **"Architecture Notes" section** (~line 311) — overlaps with
  `docs/architecture.md` (which is newer and authoritative).
  Redundant.

**Action:** rewrite the body. Keep the (recent, clean) header,
Doc Map, "What gets saved," and Cost guidance sections. Replace
Workflow + Using the App + File Structure + Architecture Notes
with:

  - Tagline (one sentence) — already present
  - 2-3 sentence intro — partially present
  - "What you can do with it" — 5-6 bullet features
  - Quick start — already present
  - The 6-step wizard at a glance — one-paragraph + ASCII diagram
  - "Read these next" → Doc Map (already present)
  - Cost guidance — already present
  - "What gets saved" — already present
  - License + threat-model link — partial; tighten
  - Contributing pointer — short, link to CONTRIBUTING.md

Target: ~150 lines. The current 350 is over-budget for a
v1.0.0 README in this scope class.

### `vision.md` — **RETIRE (recommended) or full REWRITE**

**Current state:** the Purpose header (from `1bc762b`) is fine.
The body is the original project-brief markdown from before any
code shipped:

- **"## Role"** — the hiring-manager persona paragraph that IS
  the `analyzer.py:SYSTEM_PROMPT`. It belongs in code, not in
  this file. (And the canonical version is in code; the vision
  copy may have drifted.)
- **"## App"** items 1-9 — project-plan imperatives ("read and
  analyze the following website…", "save the resume in a
  resumes folder with a subdirectory for each user"). These
  describe how the project was bootstrapped. None of it is
  load-bearing now; the code IS the answer.
- **"### Step 1"** items 1-13 — pre-pipeline backlog. Items
  1-5 are now `analyze()` + `clarify()` calls. Items 6-8 are
  the comparison + JD-keyword work. Items 12-13 are
  `generate()`. The contemporary truth lives in
  `docs/architecture.md` + `analyzer.py`.
- **"## Resume" / "## Cover Letter" / "##"** — output rules
  that are now in the SYSTEM_PROMPT and in `vision.md`'s ATS
  rules. The vision-copy version has minor drift.

**The unique value in vision.md today:** zero. Every line is
either (a) duplicated in code, (b) duplicated in PRODUCT_SHAPE
/ architecture / CLAUDE, or (c) a project plan that has long
since shipped.

**Two options:**

- **Retire (recommended).** Delete the file. Move any lines
  that aren't already in code or other docs into either the
  relevant SYSTEM_PROMPT docstring or PRODUCT_SHAPE.md.
  Justification: none of the three comparable projects ships
  a vision.md; ours doesn't communicate anything that isn't
  better-expressed elsewhere.
- **Full rewrite.** Reduce vision.md to a 30-line "Why this
  exists" + roadmap pointer. Pattern after simonw's blog-post
  approach: the file says "callback. answers the question
  'what résumé should I send for this specific job?'
  honestly, locally, without sending your career history to
  anyone's servers." Plus a pointer to PRODUCT_SHAPE for the
  architectural answer.

**My recommendation: rewrite.** Retiring loses the historical
record + the principle of "we always knew where we were going."
The 30-line version is cheaper to maintain than no file at all.

### `CLAUDE.md` — **MINOR REFRESH**

**Current state:** Just had its Purpose header added (`1bc762b`)
and got the user's local touch-up ("callback." in the title).
The "File Map" section overlaps with `docs/architecture.md`'s
module map. The "Architecture at a Glance" section is mostly
duplicated by `docs/architecture.md`.

**Action:** keep CLAUDE.md as the LLM-agent-facing contract.
Trim "Architecture at a Glance" and "File Map" sections to
brief pointers + link to `docs/architecture.md`. The deep
material lives there now; CLAUDE.md is for the "what NOT to
do" rules and pattern enforcement.

Target: ~150 lines (currently ~250). Removing duplication is
the main work.

### `CONTRIBUTING.md` — **MINOR REFRESH**

**Current state:** Has the Purpose header. Good shape. References
CLAUDE.md and `docs/architecture.md` (the latter added in
`9d36761`). The dev loop section is current.

**Action:** spot-check for the `python -m playwright install
chromium` step (Playwright wasn't in this loop when CONTRIBUTING
was first written). Confirm the "no LLM dependencies without
prompt-version bump" rule is stated.

Target: keep at ~150 lines; minor additions.

### `SECURITY.md` — **NO REWRITE NEEDED**

**Current state:** Has the Purpose header. Body was refreshed
recently for v1.0 release (commit `e880451`). User-relevant
content is surfaced near the top.

**Action:** spot-check for `paged.js` mention (a new vendor
file under `static/vendor/` shipped in `8b6d508`). Add one
line: "third-party JS bundled: `static/vendor/paged.polyfill.js`
v0.4.3 (MIT), used by the in-browser preview only. No data
sent to or received from third-party servers."

### `docs/PRODUCT_SHAPE.md` — **NO REWRITE NEEDED**

**Current state:** Recently freshened (commits `1bc762b`,
`59032d3`). §10 deferred-items captures the v1.0 → v1.x split
honestly. The asymmetry matrix is still accurate (Bullet has
full Corpus-Item treatment; SummaryItem joined it; others
remain "second-class" awaiting v1.1).

**Action:** none for v1.0.0. If we retire vision.md per the
recommendation above, add one line to §1 capturing the
"hiring-manager persona" intent that vision.md used to hold.

### `docs/RELEASE_CHECKLIST.md` — **MINOR REFRESH or RETIRE**

**Current state:** Has the Purpose header. Body is from the
release-readiness arc that just landed in v1.0.0. Sections
A.1 / A.2 / A.3 / A.4 / C.1 / C.4 / C.5 / etc. are all SHIPPED.
The doc is now historical.

**Action:** either
  (a) Refresh to be a clean v1.0.1 / v1.1 release-readiness
      checklist (most items DONE; remaining items are the
      §10 deferred set from PRODUCT_SHAPE);
  (b) Retire and let PRODUCT_SHAPE §10 + CHANGELOG be the
      forward-looking truth.

**Recommendation:** refresh, but keep it short. The checklist
shape is genuinely useful for the next release cut. Move
v1.0.0-specific completed items into an archive section at
the bottom; rewrite the active list against v1.0.1 scope.

### `docs/architecture.md` — **NO REWRITE NEEDED**

Just shipped (`9d36761`). Current and well-cross-linked.

### `docs/install.md` — **NO REWRITE NEEDED**

Just shipped (`319ae1b`). Current.

### `docs/PERF_ANALYZE.md` — **NO REWRITE NEEDED**

Recent audit doc (`2ace8b3`). Self-contained; not a top-level
nav doc.

### `docs/DOC_AUDIT.md` (this file) — **TEMPORARY**

Lives for the duration of the v1.0.0 doc rewrite. Once the
rewrites in Docs C land, this file can be deleted (its findings
are encoded in the rewrites) OR archived as a one-time release
artifact. **Recommendation: archive** under
`docs/archive/2026-05-25_doc_audit.md` so future contributors
can see the reasoning behind the v1.0.0 doc shape.

### `CHANGELOG.md` — **NO REWRITE NEEDED**

Keep-a-Changelog format, current through `beb8a2a`. Add the
docs commits to `[Unreleased]` or leave them inside `[1.0.0]`
depending on commit timing.

---

## 3 — Recommended doc graph

```
                 ┌────────────────────────────┐
                 │     README.md              │  ← entry point
                 │  (~150 lines, user-facing) │
                 └──────────────┬─────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
docs/install.md          CLAUDE.md / AGENTS.md     docs/architecture.md
(humans installing)      (LLM contract;           (humans + LLMs
                          ~150 lines)              learning the code)
       │                        │                        │
       └──────► SECURITY.md ◄───┘                        │
                (threat model)                           ▼
                                                docs/diagrams/*.mmd
                                                (4 Mermaid sources)

       Sibling roadmap docs (not in primary nav):
       ─ docs/PRODUCT_SHAPE.md   product intent + v1 → v2 ladder
       ─ docs/PERF_ANALYZE.md    latency audit + recommendations
       ─ docs/RELEASE_CHECKLIST.md   active release punch list
       ─ vision.md (RETAIN-LITE)    one-page "why this exists"

       Reference (not nav):
       ─ CHANGELOG.md
       ─ CONTRIBUTING.md
       ─ CODE_OF_CONDUCT.md
       ─ LICENSE
```

**Doc Map blockquote in README** lists six docs in this order:
1. `vision.md` (why) — if we keep it
2. `docs/install.md` (how to install)
3. `docs/architecture.md` (how the code is shaped)
4. `CLAUDE.md` (LLM-agent contract)
5. `CONTRIBUTING.md` (how to PR)
6. `SECURITY.md` (threat model)

Plus a one-line note under it: "Each doc opens with a
`Purpose / Audience / Authoritative for` block." (already there)

---

## 4 — Action items for the docs rewrite commits

After this audit lands and the user signs off, the rewrite work
breaks into ~3 commits:

**Commit B1 — vision.md + README rewrites**
- vision.md: shrink to ~30 lines covering "why this exists" +
  pointer to PRODUCT_SHAPE for the deeper how. Move the
  hiring-manager persona prose into `analyzer.py:SYSTEM_PROMPT`'s
  docstring if it's not already there verbatim.
- README.md: rewrite Workflow + Using the App + File Structure
  + Architecture Notes per §2 above. Keep header, Doc Map,
  "What gets saved," Cost guidance. Target ~150 lines.

**Commit B2 — CLAUDE.md + RELEASE_CHECKLIST refresh**
- CLAUDE.md: trim Architecture at a Glance + File Map. Replace
  with brief pointer to `docs/architecture.md`.
- RELEASE_CHECKLIST.md: archive v1.0.0-completed sections;
  rewrite active list against v1.0.1 scope.

**Commit B3 — SECURITY + CONTRIBUTING + cross-link cleanup**
- SECURITY.md: add the paged.js bundled-vendor note.
- CONTRIBUTING.md: add the Playwright install step.
- Reconcile Doc Map references across all docs (uniform order,
  uniform short titles, consistent punctuation).

**Commit B4 — archive this audit**
- Move `docs/DOC_AUDIT.md` → `docs/archive/2026-05-25_doc_audit.md`.

---

## 5 — Open questions for the user

Before the rewrite commits, three calls to make:

1. **Retire or rewrite-lite for `vision.md`?** Recommendation:
   rewrite-lite (~30 lines). Confirm or override.
2. **CLAUDE.md or AGENTS.md?** Recommendation: keep CLAUDE.md
   (the project is Anthropic-native; CLAUDE.md is auto-loaded
   by the Claude Code CLI; switching to AGENTS.md would lose
   that). Confirm or override.
3. **Archive vs delete this audit doc after rewrites land?**
   Recommendation: archive. Confirm or override.
