# Generation-experience re-architecture — design + decision record

> **Purpose:** the single durable, in-repo home for the "unusable" remediation
> re-architecture — the owner's binding behavior spec, every locked decision, the
> full reasoning thread behind those decisions, the build sequence, and the
> current state. A fresh agent should be able to continue this work from THIS
> file alone (plus git history), with nothing machine-local required.
>
> **Status (2026-07-06):** branch `fix/compose-frozen-composition` (Option B — one
> cohesive branch, off `main` `64958d3`). Phases 1 + 2 committed + gate-green;
> Phases 3–5 remain (owner checkpointed for a fresh session). **Does NOT merge
> until Phase 4 lands.**
>
> **Companions:** `docs/dev/RELEASE_CHECKLIST.md` Carry-forward ledger
> ("Generation-experience re-architecture — deferred remainder"); the approved
> plan file `~/.claude/plans/branch-to-create-fix-compose-frozen-com-flickering-stallman.md`
> (machine-local — this doc supersedes it as the durable home);
> `docs/governance/charter.md` (C-3 no-invention, C-6 deterministic boundary).

---

## 0. North star + the one-sentence framing

**NO SURPRISES.** Content is authored and approved ONCE at Compose; every
downstream surface (Template preview, assemble, preview, download) shows exactly
that. What you see is what you download and submit.

The owner's own one-sentence framing of the whole move: **we are relocating
`generate()`'s content authoring to the Compose stage.** Today one Sonnet
`generate()` call does all content work (selects bullets, proposes new ones,
writes the summary, composes skills). The re-architecture moves that *authoring*
pass to Compose — where the user reviews/accepts/retires it — and leaves Generate
as a **deterministic assembler** that lays the frozen, approved content into the
chosen template. The cover letter stays an LLM call.

---

## 1. Locked owner decisions (D1–D6) — binding, do NOT re-litigate

- **D1 — Content authored at Compose; Generate = DETERMINISTIC ASSEMBLY.** All LLM
  content creation (bullets, gap-fill bullets, summary, skills) happens ONCE at
  Compose. The later Generate/Assemble step does only *small tunings from
  refinements*, never a full rewrite. **Loop-back invariant:** any newly-generated
  content — from a refinement OR newly-entered clarifying answers — routes the user
  BACK to Compose to re-approve it, with a banner explaining why. Cover letter
  remains an LLM call.
- **D2 — Compose auto-drafts EVERYTHING on arrival** (corpus recommendations +
  gap-fill bullets + summary + skills), ready to curate.
- **D3 — One HTML/CSS source of truth for preview + PDF + .docx.** PDF is the exact
  WYSIWYG format; .docx is derived from the same JSON-Resume/HTML model. *(Render
  side already DONE in `fix/single-render-engine` — download == preview. The
  remaining D3 work is that Generate stops being an LLM call and deterministically
  assembles the frozen composition.)*
- **D4 — In-app WYSIWYG editing.** Edits made in the app ARE the document; preview
  and download always match.
- **D5 — Clarifications persist to the corpus** as reusable candidate facts that
  future JD runs draw on, and feed Compose drafting.
- **D6 — Content-provenance rule** (closes the user-intervention loop; enriches the
  corpus from real applications): (a) the user's own hand-edits apply DIRECTLY (no
  re-approval — WYSIWYG, they're looking at them); (b) LLM-created NEW content
  routes BACK to Compose as accept/retire proposals + banner, and only accepted
  items re-freeze into the composition; (c) accepted-new and meaningfully-edited
  bullets are OFFERED (user decides each) as pending-review corpus items.

**Target stage-contract (invariant):** the *approved composition* is the single
content contract — authored + approved ONCE at Compose, frozen, then rendered
DETERMINISTICALLY by every downstream surface. Nothing downstream invents or drops
content; new content always re-enters through Compose. Stages: 1 Choose user ·
2 JD+Analyze (LLM) · 3 Clarify (confirmed truths, reused as drafting source) ·
4 Compose (authors + freezes the composition) · 5 Template (pure presentation of
the frozen composition, no LLM) · 6 Generate (deterministic assembly) · 7 Download
(== preview; in-app edits both ways; clarifications→corpus).

---

## 2. Owner's binding behavior spec (reproduced verbatim)

> This is the owner's "desired behavior — the tailor process" spec, pasted into the
> session as the binding source. OWNER BEHAVIOR is binding; IMPL NOTES are
> assistive (verify against current code — reference symbols, not line numbers; the
> repo moved after the 2026-07-06 branches). Legend: ✓ shipped · ◻ owed.

**Guiding principle: NO SURPRISES.** Content is authored and approved ONCE at
Compose; every downstream surface shows exactly that. What you see is what you
download and submit.

### Global constraints (non-negotiable)
- **LLM-call boundary (charter C-6):** ALL LLM calls live in `analyzer.py`. The
  deterministic modules (`hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py`,
  `docx_to_persona_html.py`) must NEVER call an LLM. Content DRAFTING is an analyzer
  call; ASSEMBLY is deterministic.
- **`context_set` is the JSON contract** between every stage (`hardening.py`
  `save_iteration_context` writes a timestamped child; `parent_context_path` chains
  the audit trail). The "frozen composition" is a field on this contract.
- **`PROMPT_VERSION`** in `analyzer.py` bumps in the SAME commit as any prompt change.
- **Grounding (charter C-3):** generated bullets/summary must trace to résumé +
  clarifications + typed edits; the no-invention rule is enforced in the generate
  prompt. Gap-fill/generated content is a REVIEWABLE proposal (retire), never
  silently canonical.
- **Validate corpus-mode changes deterministically** on a saved
  `../sartor-e2e/output/robert/context_*.json` + one real `generate()` (use
  `/sartor:replay`). `--suite synthetic` is LEGACY-only and does not cover
  corpus-mode.
- Security on every new Flask route: `_safe_username()` + `secure_filename()` +
  `_within()` (route-security-lint hook enforces).

### Stage 1 — Choose the user
OWNER: pick the candidate. IMPL ✓: `onUserSelect()` in `static/app.js`.

### Stage 2 — Enter the JD and analyze
OWNER: paste JD, run analysis. IMPL ✓: `runAnalysis()` → `analyze`/
`analyze_streaming` (Sonnet). Writes the first `context_set`.

### Stage 3 — Clarify or skip
OWNER: clarify works for QUESTIONS; its role for bullets/summaries is uncertain.
Clarifying answers are CONFIRMED TRUTHS that must feed content drafting at Compose.
IMPL: `clarify` / `iterate_clarify`. Clarifications persist candidate-scoped in the
`clarification` table (incl. `is_promoted_to_bullet`), already reused in `clarify`
via `prior_clarifications`. ◻ OWED: feed them into Compose CONTENT DRAFTING
(summary/skills/gap-bullets), and offer promote-to-corpus
(`promote_clarification_to_bullet` in analyzer + `blueprints/corpus/proposals.py`).

### Stage 4 — Compose = the content verification stage. ALL content drafted + presented here.
OWNER:
- Bullets are the RECOMMENDED bullets — from corpus OR generated where the JD needs
  coverage the corpus lacks.
- Each item has **pin / exclude / retire** (retire = reject a *generated*
  bullet/summary).
- **Skills, summary, everything** is here, drafted and shown for review.
- On "continue," the approved content is FROZEN.
IMPL:
- ✓ Corpus recommendations exist: `recommend_bullets` (Haiku) → `ctx["llm_recommendations"]`
  by `recommend_application_bullets`; RECOMMEND prompt generous/metric-first. The
  Compose GET (`get_application_composition`) renders the scored card (metrics floated
  via the `has_outcome` +1.5 score in `db/build_context.py`).
- ✓ Summary drafting helper exists: `recommend_summary` (Haiku) — [NOTE: at spec-time
  this was a *selector* of a pre-written SummaryItem, NOT a prose drafter; Phase 2
  added the real Sonnet drafter — see §6]. Summary resolution chain:
  `corpus_to_json_resume._resolve_chosen_summary_text` (pin > recommendation >
  first-active `SummaryItem` > `candidate.profile_text`). Skills universe:
  `_collect_skills` (filters `is_pending_review=0`).
- ◻ OWED (the FOUNDATION): Compose must AUTO-DRAFT everything on arrival — corpus
  recs + **generated gap-fill bullets** (grounded proposals w/ retire) + **summary** +
  **skills** — and on "Save and continue" FREEZE a canonical **approved-composition
  object**. Today the rich scored card is recomputed live and thrown away after the
  GET; the frozen object did not exist. It's the prerequisite for a deterministic
  Generate.
- FROZEN COMPOSITION shape (design with owner; extend `composition_overrides` or a
  sibling field): per-role { ordered bullet ids (corpus + accepted-generated), chosen
  title id, role intro }, plus candidate-level { summary text, skills list }. Existing
  override keys to build on: `pinned`, `excluded`, `added`, `bullet_order`,
  `pinned_title_ids`.
- DATA MODEL: `Bullet`/`SummaryItem`/`Skill` carry `is_active`, `is_pending_review`,
  `source`, `has_outcome`. Generated content = `source='llm_proposed:<hash>'`; retire =
  `is_active=0`. `proposal_review` (application_run_id, bullet_id, original_text,
  user_edited_text, decision) is the review ledger — reuse it for accept/retire.
- EDGE CASES: a role with NO corpus fit (Compose still shows it, may offer a gap-fill
  proposal — never a silent empty role); near-duplicate bullets (RECOMMEND already
  de-dups; keep the metric phrasing); a metric bullet the user RETIRED must not
  reappear.
- ACCEPTANCE: every role with any relevant content shows ≥2 strong bullets incl.
  metrics; a real summary and skills are present and editable; nothing shown at
  Compose silently disappears downstream.

### Stage 5 — Template = pure presentation
OWNER: load the Compose-approved content into each preview template, so the user
sees THEIR chosen content in the template they're choosing. No content changes — only
look. IMPL: preview route `preview_application_html` (`blueprints/templates.py`) →
`render_html_string` with the persona `.html` companion.
- ✓ (Branch 1) render engine unified — download == preview.
- ◻ OWED: render the FROZEN composition (not a re-narrowed live recompute). Today the
  pre-generate preview re-applies recommendation narrowing in
  `corpus_to_json_resume.build_json_resume_from_corpus`; once the frozen composition
  exists, render THAT, so switching templates never changes content.
- ACCEPTANCE: switching templates changes only styling; content is byte-identical
  across templates and equals the Compose-approved set.

### Stage 6 — Generate = a composing event, NOT a rewrite
OWNER: combine recommendations + Compose curation, mapped into the chosen template — a
deterministic ASSEMBLY. Small changes after are fine. Today's end-stage "refinement"
regenerates EVERYTHING (a rewrite) — unacceptable; it must be surgical.
IMPL:
- CURRENT: `generate()` (Sonnet) emits the whole résumé as one `resume_content`
  markdown string + `selected_bullets` + `proposed_new_bullets` + `cover_letter_content`.
  STILL an LLM rewrite. Refinement re-runs the full `generate()` via `run_generation`
  (`blueprints/generation.py`).
- ◻ OWED (own branch, after the foundation): replace the résumé-body generate with a
  DETERMINISTIC assembly of the frozen composition → JSON Resume → single render
  engine. Reuse `generator._write_docx_from_json_resume` + `json_resume.md_to_json_resume`
  + `corpus_to_json_resume`. **The COVER LETTER stays an LLM call**
  (`generate_cover_letter`).
- ◻ OWED: SURGICAL refinement — a scoped, single-item change (or a "genuinely stronger
  bullet for this role" that proposes grounded new phrasings), NOT a whole-doc
  regenerate.
- ACCEPTANCE: assembling the résumé makes ZERO résumé-body LLM calls (check
  `logs/llm_calls.jsonl`); a refinement touches only the targeted item.

### Stage 7 — Download and review
OWNER:
- Download is EXACTLY what you see (download == preview == composition).
- If the user edits the content directly, the preview reflects it.
- Follow-up + clarifying questions are preserved in the corpus for future LLMs /
  future JD matching / generating JD-appropriate bullets.
IMPL:
- ✓ (Branch 1) one render engine: `.docx` derives from the same `md_to_json_resume`
  doc as preview/PDF (`_write_docx_from_json_resume`); PDF is exact WYSIWYG.
- ◻ OWED (D4, own branch): in-app WYSIWYG editing so edits ARE the document. Current
  edit surface is `#resumePreview` (contenteditable, read via `_readEditorText`) →
  `/api/download-edited` (`blueprints/generation.py` → `generate_resume`). Make the
  edited content the single source that both preview and download read.
- ◻ OWED (D5): persist clarifications to the corpus as reusable facts; feed them into
  Compose drafting for future JDs.

### Cross-cutting rules
- **Loop-back to Compose (D1):** if new clarifying questions are entered — or a
  refinement generates new content — push BACK to Compose after generating it, and
  TELL the user why, so new content is re-verified before it reaches the document. IMPL
  ◻: route the wizard to Compose (`wizardGoTo(3)`) with an explaining banner; surface
  new items as accept/retire proposals; only accepted items re-freeze.
- **Content provenance (D6) — who created it decides the path:** user's OWN hand-edits
  apply DIRECTLY (no re-approval — WYSIWYG); LLM-created NEW content routes BACK to
  Compose (accept/retire), then re-freezes. IMPL ◻: distinguish edit provenance in the
  front end; hand-edits mutate the composition in place; LLM proposals go through the
  Compose accept/retire gate (`proposal_review`).
- **Corpus enrichment — close the loop (D5/D6):** accepted-new and meaningfully-edited
  bullets are OFFERED (user decides each) to save back to the corpus for future JDs —
  never silently canonical. With persisted clarifications, every real application
  enriches the corpus. IMPL ◻: on accept/edit, offer "save to corpus" → write a
  pending-review `Bullet` (`is_pending_review=1`, `source='application:<id>'`); reuse
  `promote_clarification_to_bullet` for clarifications.
- **Output-format rule (D3):** one source of truth for preview + PDF + .docx; PDF is
  exact WYSIWYG, .docx derived from the same model, all three match. No divergent render
  engines. IMPL ✓: shipped in `fix/single-render-engine`. Keep it — do not reintroduce a
  second markdown-parsing docx path.

### "Done" looks like
- Compose is the single place all content is authored, drafted, approved, and FROZEN.
- Template is presentation-only over the frozen composition.
- Generate is a cheap DETERMINISTIC assembly — zero résumé-body LLM calls.
- Refinements are surgical; anything genuinely new loops back to Compose with a banner.
- Preview == download == what the user edits. No surprises.
- Clarifications + accepted edits flow back into the corpus for next time.

### What's already shipped (2026-07-06, on main) vs owed
✓ SHIPPED: one render engine (download==preview==import); non-canonical Summary/Skills
titles rescued; anti-starvation bullet floor + generous/metric-first RECOMMEND +
2-sentence Summary + first-class Skills (`PROMPT_VERSION 2026-07-06.1`; robert
roles-with-bullets 3/8→8/8); in-app refinement-scope modal; "Start new tailoring" reset.
◻ OWED (this spec's target): frozen composition → deterministic assemble → surgical
refine + loop-back → WYSIWYG → clarifications→corpus. Generate is STILL an LLM call today.

---

## 3. Design decisions + the reasoning thread (why these choices)

These were worked out interactively with the owner during planning. Recorded here so
they are never re-litigated or lost.

### 3.1 The frozen-composition shape → RESOLVED SNAPSHOT + provenance ids
Three candidate shapes were weighed:
- **(A) Resolved snapshot** — freeze the fully-resolved JSON-Resume document (resolved
  bullet/summary/skills text in final order) as a sibling `approved_composition` key.
- **(B) ID pointers + summary text** — the owner spec's literal field list (ordered
  bullet ids + title id + role intro + summary TEXT + skills list).
- **(C) Minimal / defer** — add only the drafted summary; keep live id-resolution.

**Chosen: A-extended — a resolved snapshot that ALSO carries the provenance ids.**
Reasoning (this is the decisive point): today the preview reads **live DB** while
generate reads the **frozen `career_corpus`**, and the two resolvers *already diverge*
(the preview ignored `bullet_order`; generate honored it — so the same composition could
render differently in preview vs the résumé). Freezing only ids re-introduces that
divergence downstream and lets a later corpus-row edit silently change an
already-approved application — a SURPRISE. Freezing the resolved TEXT once, with the ids
alongside in `meta.sartor` for provenance / corpus-enrichment (D6), makes *preview ==
template == assemble == download* true by construction, reuses the existing resolver
(`build_json_resume_from_corpus`) as the single producer (less new code than a bespoke
id-object), and literally contains the owner's field list. It is immune to later corpus
edits (a value snapshot). Storage: a sibling `approved_composition` key on the context
JSON (no DB migration — `ApplicationRun` doesn't exist at Compose time; DB durability is
the deterministic-assemble branch's job).

### 3.2 Summary drafting model → SONNET (not Haiku)
The 2-sentence summary MUST move out of Generate to Compose (D1 — once Generate is
deterministic there's no LLM left to write it, and the user must review it before it
freezes). It becomes a *dedicated Compose-time drafting call* that fires after Clarify
(NOT folded into `analyze()` — analyze runs before Clarify, so it couldn't use
clarification answers (D5), and adding a field would churn the analyze→generate cache).
Model choice = **Sonnet**: "weak summaries" was one of the owner's two original
MUST-SOLVE complaints, the summary is the marquee top-of-résumé line, and Sonnet is the
tier that produces the good version today — Haiku risks regressing exactly that. It is a
2-sentence output firing once on Compose arrival, so the cost is small; a one-line model
flip to Haiku remains available if Compose latency ever warrants.

### 3.3 Moving generate's authoring to Compose → couples with "Generate becomes deterministic"
Once Compose authors everything, Generate MUST stop authoring in the same step —
otherwise Compose freezes content and Generate re-writes it, which is the exact surprise
being killed. So "Compose authors everything" and "Generate becomes deterministic" are
two sides of one move and land together.

### 3.4 Option A vs B (branch shape) → owner chose B (ONE cohesive branch), rework-free
The **rework-free rule**: touch `generate()` exactly ONCE — straight to deterministic —
or the work is re-authored. A tempting intermediate ("Generate still calls the LLM but is
told to emit the frozen summary verbatim") is a HALF-STEP that gets thrown away when
Generate later goes fully deterministic — explicitly rejected. That leaves only two
rework-free shapes:
- **One branch (Option B, CHOSEN):** frozen contract + Compose authors everything
  (summary + gap-fill bullets, accept/retire) + Generate goes fully deterministic — all
  in one branch. Cohesive, nothing re-authored; the largest single branch in the arc.
- **Two branches (foundation, then authoring):** was equally rework-free (Branch 1 =
  frozen object + preview renders it, generate untouched; Branch 2 = author everything +
  deterministic generate touched once). The owner chose the single cohesive branch.

### 3.5 The three owner questions (all YES; all map to LATER branches)
1. *"Extra questions at Generate → improve summary/bullets → back to Compose?"* — YES.
   That's the loop-back invariant (D1/D6): new clarifying answers feed the authoring pass
   and any newly-generated content routes back to Compose with a banner for accept/retire
   before it reaches the document. LATER branch (`fix/surgical-refinement-and-loopback`);
   interim: refinement routes back to Compose.
2. *"Direct edits to the generated file → corpus-for-review, or only WYSIWYG?"* — BOTH,
   user-controlled: hand-edits apply directly to the document immediately (WYSIWYG, no
   re-approval); separately a meaningfully-edited bullet is OFFERED to save back to the
   corpus as a pending-review item, per item. Never silently canonical. LATER branches
   (WYSIWYG D4 + corpus enrichment D5/D6).
3. *"Can Compose draw on the existing corpus + prior answered questions from OTHER JDs?"*
   — YES (D5). The corpus is inherently cross-JD; clarifications persist candidate-scoped,
   so a fact confirmed for JD-A is available for JD-B. Feeding prior clarifications into
   Compose *drafting* is the D5 branch (today they're reused only when *asking* more
   questions). This branch's summary draft already reads existing clarifications as a
   source.

---

## 4. Build sequence — five internal phases (one branch)

Phase 1 is pure-deterministic (no LLM) and testable first — everything consumes it.
Phases 2–3 add the Compose authoring (LLM in `analyzer.py`). Phase 4 flips Generate to
deterministic once the frozen content is complete (touched once). Commit at each phase
boundary so the branch is checkpoint-able across sessions.

1. **Frozen composition contract** — the `approved_composition` snapshot + resolver +
   freeze-on-continue. *(DONE — §5.)*
2. **Compose authors the summary** (Sonnet). *(DONE — §5.)*
3. **Compose authors gap-fill bullets** (Sonnet + accept/retire). *(TODO — §6.)*
4. **Generate becomes deterministic** (corpus-mode) + preview/download read the frozen
   composition + refinement routes back to Compose. *(TODO — §6.)*
5. **Validation + durable docs.** *(TODO — §6; this doc is part of it.)*

**Deferred to LATER branches (NOT this branch):** loop-back for new content (D1/D6),
LLM-assisted surgical refinement, WYSIWYG-as-source-of-truth (D4), corpus
enrichment / offer-edited-bullets-to-corpus (D5/D6), clarifications-persistence /
cross-JD drafting reuse (D5). This branch's drafting MAY read existing clarifications as a
source, but does not build new persistence.

---

## 5. Current state — Phases 1 + 2 (DONE, committed, gate-green)

Branch `fix/compose-frozen-composition` off `main` `64958d3`. Gate at each commit: ruff
· mypy (243) · pytest (1422 non-ux) · compose UX (8).

### Phase 1 — frozen `approved_composition` contract — commit `a7a4d87`
- `hardening.py` `ContextSet`: `approved_composition: dict` + documented the new
  `composition_overrides` keys (`summary_text`, `summary_text_edited`,
  `accepted_generated_bullet_ids`).
- `corpus_to_json_resume.py`: `build_json_resume_from_corpus` is now the SOLE producer —
  honors `composition_overrides.bullet_order` (kills the preview↔generate order
  divergence), folds `accepted_generated_bullet_ids` into the per-role set, resolves
  `basics.summary` from `composition_overrides.summary_text` (source "drafted"/"edited"),
  and emits `meta.sartor` provenance (`work_provenance` [experience_id, title_id,
  role_intro_id, order-aligned `highlight_ids`], `skill_ids`,
  `accepted_generated_bullet_ids`). New `freeze_approved_composition()` stamps
  `meta.sartor.frozen`. A `context_data` param lets the freeze path read in-memory
  overrides not yet written to disk (no double write). `_collect_skills` now returns
  `(skills, ordered_ids)`.
- `blueprints/applications.py`: `save_application_composition` persists the new keys and,
  on the explicit Save-and-continue (`freeze:true`), writes the `approved_composition`
  snapshot (never on the debounced autosave).
- Tests: `tests/test_corpus_to_json_resume.py` (+10) and `tests/test_composition_summary.py`
  (+4). Default path byte-identical (all new keys optional/absent).

### Phase 2 — Compose authors the 2-sentence summary — commit `ad71833`
- `analyzer.py`: `DRAFT_SUMMARY_SYSTEM_PROMPT` (grounded, no-invention, worked OK/NOT-OK) +
  `draft_positioning_summary()` (**Sonnet**) + `DraftSummaryResponse` + registry entry in
  `_BASE_SYSTEM_PROMPTS`; short-circuits (no LLM) with no JD. `PROMPT_VERSION 2026-07-06.1
  → 2026-07-06.2` (a NEW per-call template; the generate prompt is unchanged, so the
  analyze→generate cache + legacy `--suite synthetic` path stay byte-identical).
- `blueprints/applications.py`: `POST /api/applications/<id>/draft-summary` (stages the
  source positioning via `_resolve_chosen_summary_text` + a grounded career synopsis
  `_career_facts_synopsis` + the JD; persists into `composition_overrides.summary_text`,
  edited=False, a fresh draft). GET `get_application_composition` surfaces
  `summary.drafted_text` / `drafted_edited` / `has_draft` (via new `_read_summary_draft`).
- `static/app.js` + `static/style.css` + `ui_pages/selectors.py`: the positioning card
  ALWAYS renders in Compose with an editable drafted-summary `<textarea id="composeSummaryDraft">`
  + Regenerate (`_fireDraftSummary`) + Retire (`_retireDraftSummary`); auto-drafts once per
  application (guarded by `_draftSummaryFiredForApp` against a legitimately-empty re-loop);
  `summary_text` + `summary_text_edited` ride along in `_collectCompositionState` (clobber
  invariant); `saveCompositionThenNext` sends `freeze:true`.
- Tests: `tests/test_draft_summary.py` (short-circuit + route: persist/regen/GET-surface/
  404/400) + `tests/ux/regression/test_20260706_compose_summary_draft.py` (auto-fill, edit
  persists across reload, retire) + `fake_draft_positioning_summary` in `tests/ux/stubs.py`
  (returns non-empty so `has_draft` flips — no re-loop, same lesson as
  `fake_recommend_summaries`).

Mechanics reference (durable): the memory `reference-frozen-composition-mechanics`.

---

## 6. Remaining work — Phases 3, 4, 5 (TODO)

### Phase 3 — Compose authors gap-fill bullets (Sonnet + accept/retire)
Model it on the proven "propose grounded new items → accept/retire" pattern
(`analyzer.suggest_skills` + `promote_clarification_to_bullet`; `proposal_review` ledger).
- `analyzer.py`: `DRAFT_GAP_FILL_SYSTEM_PROMPT` + `draft_gap_fill_bullets()` (**Sonnet**) +
  a response model + registry. For JD essential/preferred requirements NOT covered by
  existing corpus bullets, draft GROUNDED candidate bullets (traceable to résumé +
  clarifications — charter C-3; no invention), each targeting an experience. Returns
  proposals, not silent inserts. Short-circuit with no JD.
- Route + persistence (`blueprints/applications.py` or `blueprints/corpus/proposals.py`):
  a draft route (fires on Compose arrival — D2) writes transient proposals (e.g.
  `ctx["llm_gap_fill_proposals"]`). ACCEPT → create a `Bullet` row
  (`source='llm_proposed:<hash>'`, `is_pending_review=1`, attached to its experience) +
  add its id to `composition_overrides.accepted_generated_bullet_ids`; RETIRE → drop
  (never persist). Reuse `proposal_review` as the review ledger (no migration).
- **Resolver pending-leak guard (IMPORTANT):** accepted gap-fill bullets are
  is_pending_review=1. `build_json_resume_from_corpus` currently filters only `is_active`
  (NOT `is_pending_review`) — so a pending-but-active bullet would leak into OTHER apps'
  default all-active render. Add: exclude is_pending_review bullets from the default set
  UNLESS the id is in `accepted_generated_bullet_ids` (this app). Verify current behavior
  first (does any test seed a pending-active bullet expecting it to render?) + add a
  regression test.
- `static/app.js` + selectors: render gap-fill proposals in the Compose experience cards
  (or a per-role "suggested for this JD" lane) with accept/retire; accepted ids ride along
  in `_collectCompositionState` as `accepted_generated_bullet_ids`. A retired bullet must
  never reappear (owner edge case). Add a UX stub `fake_draft_gap_fill_bullets` + a UX
  regression.
- Tests: drafting grounded (no fabricated specifics); accept adds to composition + a
  pending corpus row; retire drops; retired never re-appears.

### Phase 4 — Generate becomes deterministic (the core-pipeline change; riskiest)
- `blueprints/generation.py`: in **corpus-mode**, `run_generation` /
  `run_generation_stream` no longer call the résumé-body LLM — they
  `freeze_approved_composition` (or read the already-frozen `approved_composition`) and
  **deterministically assemble** it → JSON Resume → single render engine
  (`corpus_to_json_resume` / `json_resume.md_to_json_resume` /
  `generator._write_docx_from_json_resume` / `pdf_render`). **Cover letter stays an LLM
  call** (`generate_cover_letter`). **Legacy (file-based) mode keeps the LLM `generate()`
  path unchanged** — so `--suite synthetic` stays valid and byte-identical.
- `analyzer.py`: the corpus-mode résumé-body authoring in `_build_generate_prompt` (rule
  #1 summary / rule #9 skills) is no longer used in corpus mode (the assembler emits the
  frozen text). Keep the legacy-path rules intact.
- `blueprints/templates.py` `preview_application_html`: serve `approved_composition` when
  present (like `last_generated_json_resume`) so preview == the frozen curated set,
  template-invariant (Stage 5 acceptance).
- **Refinement / iteration (interim handling; full surgical + loop-back = LATER branch):**
  corpus-mode generate is deterministic, so the current LLM full-regenerate refinement
  (which the owner called "unacceptable") is removed; the in-app refinement modal instead
  routes the user BACK to Compose to adjust + re-approve content (minimal loop-back). Basic
  edit-and-download (`/api/save-edits` → `/api/download-edited`) stays as-is
  (WYSIWYG-as-source is deferred to D4).
- Tests: a corpus-mode assemble makes **ZERO résumé-body LLM calls** (assert against
  `logs/llm_calls.jsonl`); preview == download == `approved_composition`; cover letter
  still calls the LLM; legacy generate unchanged.

### Phase 5 — validation + durable docs
- Corpus-mode validation on `../sartor-e2e/output/robert/context_*.json`: assemble → 0
  résumé-body LLM calls; assembled doc == frozen composition == preview; summary + gap-fill
  present + grounded. Record in `evals/TUNING_LOG.md`.
- Legacy synthetic eval (`python evals/runner.py --suite synthetic`) unchanged /
  byte-identical (corpus-mode-only changes; prove with a unit test).
- `CHANGELOG.md`; RELEASE_CHECKLIST ledger update; memory.
- Keep THIS doc current (it is the durable home).

---

## 7. Constraints + close-out (this branch)

- Charter C-6 (no LLM in the deterministic modules) + C-3 (grounding / no invention).
- Every new Flask route: `_safe_username()` + `_within()` + `secure_filename()`.
- `PROMPT_VERSION` bumps in the same commit as any prompt change (corpus-mode-only changes
  still bump for attribution; prove the legacy path byte-identical).
- Validate corpus-mode DETERMINISTICALLY on the robert context + one real `generate()` via
  `/sartor:replay` — NOT `--suite synthetic` (legacy-only).
- **Does NOT merge until Phase 4 lands** — the branch is only usable end-to-end once
  Generate assembles the frozen composition. One branch; commit at phase boundaries; if it
  spans sessions, hand off mid-branch (do NOT merge partial).
- **Local ruff gotcha:** installed ruff 0.15.12 makes `ruff format --check .` flag 5 files
  NOT touched by this branch (`docx_to_persona_html.py` + 4 tests) — a version/style
  artifact, not this branch's drift. Stage only your own (format-clean) files; the
  `ruff-changed` commit hook only checks STAGED files, so this doesn't block. Flag it at
  close-out (a ruff-pin / re-format decision, its own item).
