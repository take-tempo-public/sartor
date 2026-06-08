<!--
  TEMPORARY / UNTRACKED handoff prompt (output/ is gitignored).
  Paste the section below into a fresh agent to continue the "excellence walk."
  Companion temp docs (read both): output/_dev-notes/excellence-walk.md +
  output/WALKTHROUGH_SPRINT_PLAN_2026-06-07.md.
-->

# Handoff — continue the "excellence walk" toward a polished, production-grade callback.

You are picking up a **partnered, form-finding effort** (not a build task yet) to
bring callback. to a *polished production codebase* and fold that work into the
march to **v1.1.0**. Your job this session is to **review where we are in the
larger context, then keep walking the open threads** — capturing as you go.
Match the working style below; the prior agent set a bar, meet or beat it.

## How this started (the larger context — don't lose it)

The user opened by asking the prior agent to assess the project against five
descriptors/questions. That assessment (evidence-based, in the codebase) led to a
shared direction and a decision to **walk five deeper questions** one at a time,
in **form-finding partnership mode**, capturing everything in a durable temp doc.
You are continuing that walk. Start by re-grounding in the first ~5 exchanges'
intent, not just the most recent thread.

**The five questions (the spine of the walk):**
1. Describe our architecture & scaffolding to a well-informed layman.
2. Is the code consistent?
3. Every NON-dependency download to run (a) the basic tool and (b) the full eval
   suite — what & why.
4. Are docs too big / well-sized / linked / self-described / discoverable by
   humans *and* LLMs? Restructure for context-management? Would Karpathy's
   "LLM-wiki" fit? Re-answer assuming we build a codebase/docs Q&A assistant.
5. A descriptive "state of the work" portion (positive / negative / ambiguous,
   labeled) for showing this to others as a product and as a work.

Alongside the questions, an **engineering backlog** emerged: **WS-1** decompose
`app.py` (6,290 LOC / 75 routes) into Flask blueprints; **WS-2** strict typing +
typed `context_set`; **WS-3** recurring test-suite design pass; **WS-4** an
LLM-wiki knowledge architecture (now the active thread).

## Documents to read before any tool call (in this order)

1. **`output/_dev-notes/excellence-walk.md`** — the LIVE capture of THIS walk:
   the assessment (Part A / Q5 = done), the WS-1..WS-4 backlog, the 5-question
   research agenda (Part C), the deep WS-4 design work, the decisions log, and
   "What's next." **Read this first and in full.**
2. **`output/WALKTHROUGH_SPRINT_PLAN_2026-06-07.md`** — the prior session's
   **v1.0.5 → v1.1.0 release/sprint plan** (24 walk-through findings → sequential
   one-branch sprints V5-A/V5-B → 6.1–6.5 → PV [v1.0.7] → REL [v1.1.0]). This is
   the release context the excellence stack must fold into.
3. `docs/dev/RELEASE_ARC.md` + `docs/dev/RELEASE_CHECKLIST.md` — the authoritative
   in-repo release sequence/state (trust these over any memory).
4. `vision.md` + `docs/PRODUCT_SHAPE.md` — the prescriptive product direction
   (relevant to WS-4's "constitutional layer" idea).
5. `docs/architecture.md` + `AGENTS.md` — module map + the deterministic/LLM
   boundary + the agent contract.

Both temp docs are in `output/` (**gitignored, intentional**) — they are durable
*scratch*, to be integrated into `docs/dev/` in a later pass. Do not commit them.

## Where the walk stands

- **Q5 / Part A:** DONE (the labeled assessment).
- **Q4 / WS-4:** deeply explored. **Decided:** adopt the LLM-wiki *now*
  (git-as-engine: code at HEAD is the source, `git diff <sha> HEAD` drives
  incremental ingest; ops as Claude Code skills adapted from `kfchou/wiki-skills`;
  committed `docs/wiki/` + root `llms.txt`). **`raw/` reframed** as the
  *constitutional* layer (prescriptive sources — vision/principles/direction —
  with mechanized edit friction), which unlocks **vision-alignment auditing**.
  Integration & Migration design captured, incl. a first-pass doc classification
  and 10 open migration questions — **led by the prescriptive/descriptive split
  of mixed docs** (AGENTS/CONTRIBUTING/SECURITY/PRODUCT_SHAPE/RELEASE_ARC).
- **Q1, Q2, Q3:** NOT yet walked (Q3's factual research is mostly gathered in the
  capture). **WS-1/WS-2/WS-3:** scoped, parked.
- A post-v1.1.0 **codebase/docs Q&A assistant** is a confirmed goal; new docs
  (esp. the v1.0.6 "6.5 education sweep") should be authored to feed it.

## Your work this session (the user's four phases)

1. **Finish walking each thread** (the 5 questions + the WS items) until we have a
   decent understanding of *where we are, what we want to do and why, and roughly
   how.*
2. **Process next steps per thread** until we're satisfied there's enough mapping
   to integrate into sprint planning — **tracking everything in the temp docs as
   you go.**
3. **Integrate the temp-doc captures into the existing product-planning docs**
   (`RELEASE_ARC.md` / `RELEASE_CHECKLIST.md` / `PRODUCT_SHAPE.md` / etc.).
4. **Execute the sprint planning** (decompose into the one-branch-per-session
   sprints, per the established method).

Phases 1–2 are this-session likely; 3–4 are downstream and need user sign-off.
Do NOT jump ahead to building/integrating before the mapping is good enough.

## Working style (match this — it's why the prior session went well)

- **Form-finding partnership, not jump-to-solve.** Source openings together; ask
  clarifying & disambiguating questions; don't execute handed decisions blindly.
- **Reason about dependencies** — what each decision opens/closes downstream.
  Recommend a path, but the user decides.
- **One thread at a time; the user steers order.**
- **Capture continuously.** The temp doc is LIVE — write decisions the moment
  they're made, don't batch. Don't claim a capture you didn't make.
- **Ground claims in evidence/research; reuse over reinvention** (e.g. WS-4 reuses
  `kfchou/wiki-skills`, not a from-scratch build).

## Hard constraints / operational gotchas

- **Branch before any edit** (`require-feature-branch` hook; we are on
  `docs/excellence-walk`). Do not edit on `main`.
- **The plan-approval hook** (`check-plan-approved`) gates edits behind a global
  marker `~/.claude/plans/.approved` that **gets wiped on every merge to main**;
  when it blocks you, surface it and (with user OK) refresh it via
  `New-Item -Force -ItemType File "$env:USERPROFILE\.claude\plans\.approved"`.
  **Never bypass a hook without explicit user sign-off** — surface name + error,
  ask first.
- **Do not commit the temp docs** (gitignored by design). No code changes are
  expected during the walk; if any are made, full gate (`ruff`+`mypy`+`pytest`)
  and ask before merge to `main`.
- **Check git state first** and **don't touch other agents' in-flight branches.**
- **WS-1 (blueprints) must NOT be interleaved** with the active sprint stream — it
  rewrites `app.py`/routes that nearly every sprint branch touches (merge-conflict
  hell). Keep it parked until release churn settles.
- Relevant memories: `excellence-walk-llm-wiki`, `feedback-form-finding-vs-tending`,
  `feedback-maintain-durable-docs-inline`, `feedback_hook_discipline`,
  `feedback-verify-against-durable-docs`.

## First move

Read the two temp docs + the durable release docs above. Then **reflect the
larger-context state back to the user** (the 5 questions, the WS backlog, what's
decided vs. open, how it folds into v1.1.0) and **confirm which thread to walk
next** and the pace. Do not build. Capture as you go.

## Sequencing note (already analyzed — carry it)

This work does **not** gate or threaten the **v1.0.5 tag**; the wiki's only clock
is **Sprint 6.5** (v1.0.6), comfortably after the tag. The excellence stack folds
into the march to v1.1.0 at known joints: **WS-4** substrate in the
v1.0.5-tag → 6.5 window; **WS-2** absorbs/expands the plan's **PV-4** type scan
(v1.0.7); **WS-1** is net-new and needs its own deliberately-placed slot (low
app.py-churn window). Recommend the user **continues the sprint schedule to the
v1.0.5 tag unpaused.**
