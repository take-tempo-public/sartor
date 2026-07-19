# Generation-experience re-architecture — design + decision record

> **Purpose:** the single durable, in-repo home for the "unusable" remediation
> re-architecture — the owner's binding behavior spec, every locked decision, the
> full reasoning thread behind those decisions, the build sequence, and the
> current state. A fresh agent should be able to continue this work from THIS
> file alone (plus git history), with nothing machine-local required.
>
> **Status (2026-07-06):** branch `fix/compose-frozen-composition` (Option B — one
> cohesive branch, off `main` `64958d3`). Phases 1 + 2 + 3 + 4 committed + gate-green;
> only **Phase 5 (validation + docs)** remains. Phase 4 (deterministic Generate) has
> landed, so the branch is now usable END TO END — mergeable once Phase 5 validation
> is done.
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
- **Validate corpus-mode changes deterministically** on a saved corpus
  `context_*.json` from a local read-only clone + one real `generate()` (use
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
3. **Compose authors gap-fill bullets** (Sonnet + accept/retire). *(DONE — §5.)*
4. **Generate becomes deterministic** (corpus-mode) + preview/download read the frozen
   composition + refinement routes back to Compose. *(DONE — §5.)*
5. **Validation + durable docs.** *(DONE — §6; live replay on the robert corpus
   2026-07-06, TUNING_LOG "Compose-frozen-composition" entry, CHANGELOG entry,
   byte-identity unit tests in `tests/test_corpus_mode_prompt.py`.)*

**Deferred to LATER branches (NOT this branch):** loop-back for new content (D1/D6),
LLM-assisted surgical refinement, WYSIWYG-as-source-of-truth (D4), corpus
enrichment / offer-edited-bullets-to-corpus (D5/D6), clarifications-persistence /
cross-JD drafting reuse (D5) — **DONE 2026-07-08, see §8(c)**. This branch's drafting
MAY read existing clarifications as a source, but does not build new persistence.

---

## 5. Current state — Phases 1 + 2 + 3 (DONE, committed, gate-green)

Branch `fix/compose-frozen-composition` off `main` `64958d3`. Gate at each commit: ruff
· ruff format · mypy (246) · pytest (1442 non-ux) · compose UX.

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

### Phase 3 — Compose authors gap-fill bullets (Sonnet + accept/retire) — committed
- `analyzer.py`: `DRAFT_GAP_FILL_SYSTEM_PROMPT` (grounded evidence-or-nothing +
  bullet-shape rules) + `draft_gap_fill_bullets()` (**Sonnet**; structure from
  `suggest_skills`, model wiring from `draft_positioning_summary`) + `DraftGapFillResponse`
  + registry entry. `PROMPT_VERSION 2026-07-06.2 → 2026-07-06.3` (a NEW per-call
  template; generate prompt UNCHANGED → legacy `--suite synthetic` byte-identical, guarded
  by `TestGapFillPromptInvariance`). Session-free: the ROUTE validates experience
  ownership, coerces `pattern_kind`, keys, and dedups.
- `corpus_to_json_resume.py`: the **pending-leak guard** on the single `active_bullets`
  choke point — `b.is_active and (not b.is_pending_review or b.id in accepted_generated_ids)`.
  A pending+active bullet renders only when accepted for THIS app; it no longer leaks into
  other apps' default all-active render. **Intended behavior change** for any pre-existing
  pending+active bullet (e.g. promoted-clarification bullets); no test seeded one expecting
  it to render, so nothing broke (re-verify on the Phase-5 robert replay).
- `hardening.py`: `ContextSet.llm_gap_fill_proposals: list` (`total=False`).
- `blueprints/applications.py`: `POST /draft-gap-fill` (clone of `/draft-summary`; stages
  the JD, calls the drafter, normalizes route-side, ALWAYS writes the key so `has_gap_fill`
  flips) + `POST /gap-fill-decide` (accept → a `Bullet` `source='llm_proposed:<key>'`,
  `is_pending_review=1` + id into `accepted_generated_bullet_ids` + a pending `ProposalReview`
  keyed to `ctx["application_run_id"]`, commit-then-write, idempotent on the source key;
  retire → drop the transient proposal). GET `get_application_composition` surfaces
  per-experience `gap_fill_proposals`, `accepted_generated` per bullet, and top-level
  `has_gap_fill`. **Correctness note:** an iteration-0 `ApplicationRun` DOES exist at Compose
  (`ctx["application_run_id"]`, written at `/api/analyze`) — the accept ledger uses it
  directly (the design-doc §3.1 aside "ApplicationRun doesn't exist at Compose time" is true
  only in the narrow no-new-DB-column sense).
- `static/app.js` + `style.css` + `ui_pages/selectors.py`: per-role "Suggested for this JD"
  lane (accept/retire, modeled on the Skills pending lane); auto-fires once per app
  (`_gapFillFiredForApp` + the server `has_gap_fill` flag — no Regenerate, so a retired
  proposal never reappears); accepted bullets join the visible set; **`accepted_generated_bullet_ids`
  rides `_collectCompositionState` on every save** (the clobber-invariant fix — the POST
  rebuilds overrides wholesale + freezes on continue).
- Tests: `tests/test_draft_gap_fill.py` (short-circuit + route) + `tests/test_gap_fill_decide.py`
  (accept creates Bullet+ledger, idempotent, foreign→400, retire drops) +
  `tests/test_corpus_to_json_resume.py::TestPendingLeakGuard` (excluded-by-default,
  renders-when-accepted, byte-identical default, freeze-includes-accepted) +
  `tests/test_corpus_mode_prompt.py::TestGapFillPromptInvariance` (byte-identity guard) +
  `tests/ux/regression/test_20260706_compose_gap_fill.py` + `fake_draft_gap_fill_bullets`.

**Deferred to LATER branches (documented extension points):** ~~a "Regenerate gap-fill" button
(needs a `retired_gap_fill_keys` set)~~ — **DONE 2026-07-08 on `feat/regenerate-gap-fill`**, see
§6 (d) below; loop-back-to-Compose banner for newly-generated content;
the corpus-enrichment "save to corpus" offer beyond the free `is_pending_review=1` pending row
(the existing pending-review APPROVE already covers D6(c)).

### Phase 4 — Generate becomes deterministic (corpus-mode) — committed
- **No corpus/legacy branch existed** before this — both modes called the résumé LLM
  `generate()` → `generate_resume(markdown)`, and `approved_composition` had ZERO readers.
  Phase 4 ADDS a corpus-deterministic branch gated on `_frozen_composition(context_set)`
  (`approved_composition` present + content + `career_corpus`); legacy (no `career_corpus`)
  and pre-freeze corpus contexts fall through UNCHANGED → `--suite synthetic` byte-identical.
- `blueprints/generation.py`: `run_generation` + `run_generation_stream` — when frozen,
  `_assemble_from_frozen_composition` builds the generate()-shaped result WITHOUT the résumé
  LLM (résumé body = the frozen doc; `resume_content` = a deterministic `json_resume_to_markdown`
  view; audit `selected_bullets` synthesized from `meta.sartor.work_provenance`); the résumé
  renders DIRECTLY from the doc via `generate_resume_from_json_resume` (download == preview ==
  `approved_composition`, no markdown round-trip). The COVER LETTER stays an LLM call
  (`generate_cover_letter_against_resume`, only when opted in). The `_apply_*` context patches
  are skipped in the frozen path (the freeze already resolved them).
- `json_resume.py`: `json_resume_to_markdown(doc)` — deterministic inverse of
  `md_to_json_resume` (round-trips; no LLM/clock). `generator.py`:
  `generate_resume_from_json_resume(doc, fmt, …)` renders a pre-built doc through the same
  writers (`_write_docx_from_json_resume` / `_render_pdf_from_json`), skipping the markdown parse.
- `blueprints/templates.py` `preview_application_html`: serves `approved_composition` when
  present (over `last_generated_json_resume`), UNLESS the user hand-edited (`edited_resume_text`
  → the edit wins, D6(a)). So preview == deterministic assemble == download, template-invariant.
- `static/app.js` + `style.css`: in corpus mode, `submitRefinement` routes BACK to Compose
  (`wizardGoTo(3)` + an explaining `.compose-loopback-banner` rendered from a flag so it
  survives the re-render cascade) instead of an LLM full-regenerate — the design's minimal
  loop-back (owner-approved). Legacy refine keeps the LLM regenerate.
- Tests: `tests/test_deterministic_generate.py` (serializer round-trip; `_frozen_composition`
  gate; `_assemble_from_frozen_composition`; route: zero `generate`/`generate_streaming` LLM
  calls in corpus mode, download == `approved_composition`, cover letter stays LLM, legacy +
  pre-freeze fall back to LLM) + `test_live_preview_route.py::TestApplicationPreviewApprovedComposition`
  (preview serves the frozen doc over corpus; hand-edit wins). Gate: ruff · mypy (247) ·
  pytest (1458 non-ux + 76 ux).

**Deferred to LATER branches:** SURGICAL refinement (a scoped single-item change / grounded
re-phrasing) + the richer loop-back-with-accept/retire banner — **DONE 2026-07-08 on
`fix/surgical-refinement-and-loopback`, as-built in §8**; WYSIWYG-as-source (D4) — **DONE
2026-07-08 on `feat/wysiwyg-source-of-truth`, as-built in §9**; clarifications→corpus
persistence (D5). This branch's refine is the minimal route-to-Compose (superseded by §8's
scoped proposal + richer banner).

---

## 6. Remaining work — Phase 5 (DONE 2026-07-06; sections below kept as as-built reference)

> Phase-5 exit evidence: live corpus-mode replay on a local read-only robert corpus clone
> (0 résumé-body LLM calls; download == frozen == preview), the
> `evals/TUNING_LOG.md` "Compose-frozen-composition" entry, the CHANGELOG entry,
> and the legacy byte-identity unit tests (`tests/test_corpus_mode_prompt.py`).
> The **LATER-branch remainder** is now fully landed — (a) surgical refinement +
> loop-back banner **DONE 2026-07-08** on `fix/surgical-refinement-and-loopback`
> (as-built in §8); (b) WYSIWYG-as-source D4 **DONE 2026-07-08** on
> `feat/wysiwyg-source-of-truth` (as-built in §9); (c) clarifications→corpus D5
> **DONE 2026-07-08** on `feat/clarifications-to-corpus` (as-built in §10);
> (d) regenerate-gap-fill **DONE 2026-07-08** on `feat/regenerate-gap-fill`
> (as-built below) — see the RELEASE_CHECKLIST carry-forward ledger for the
> Resolved entry.

### Phase 3 — Compose authors gap-fill bullets (Sonnet + accept/retire) — DONE (as-built in §5)
> The original plan is retained below as the as-built reference; see §5 for what shipped.

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

### Phase 4 — Generate becomes deterministic (the core-pipeline change; riskiest) — DONE (as-built in §5)
> The original plan is retained below as the as-built reference; see §5 for what shipped.
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
- Corpus-mode validation on a local read-only robert corpus clone (`context_*.json`): assemble → 0
  résumé-body LLM calls; assembled doc == frozen composition == preview; summary + gap-fill
  present + grounded. Record in `evals/TUNING_LOG.md`.
- Legacy synthetic eval (`python evals/runner.py --suite synthetic`) unchanged /
  byte-identical (corpus-mode-only changes; prove with a unit test).
- `CHANGELOG.md`; RELEASE_CHECKLIST ledger update; memory.
- Keep THIS doc current (it is the durable home).

### (d) Regenerate gap-fill affordance + durable retirals — DONE 2026-07-08 (`feat/regenerate-gap-fill`)
> LATER-branch remainder item (d), landed in Train 3 alongside (a)
> `fix/surgical-refinement-and-loopback` (see `RELEASE_ARC.md` Phase 3b). Scope was
> deliberately narrow — this item only, not (a)/(b)/(c).

- **`composition_overrides.retired_gap_fill_keys`** (list of the existing stable
  `sha256(eid|text)[:12]` key) — the durable retiral set §5 Phase 3 flagged as a
  missing extension point. `/gap-fill-decide` (retire) writes it directly
  alongside dropping the transient `llm_gap_fill_proposals` entry; it rides
  `_collectCompositionState()`'s wholesale rebuild on every `/composition` save
  like every other override key, so a save between decides never silently drops
  it (the same clobber invariant `accepted_generated_bullet_ids` already
  follows).
- **"Regenerate suggestions"** (`static/app.js` `_renderGapFillControls` +
  `_fireDraftGapFill(btn)`) — an always-visible control above the per-role
  gap-fill lanes (once experiences exist), re-calling the SAME
  `POST /draft-gap-fill` route the once-only auto-fire uses. It is a THIRD
  context-writing firing path (alongside the summary draft + skills
  recommend) and serializes through the same `data-compose-bg-pending`
  counter, per the bgDraftFiring clobber-class precedent.
- **Route-level exclusion filter** (`draft_application_gap_fill`, deterministic,
  route-side — the analyzer stays session-free, unchanged): a fresh draft's
  normalized proposals are filtered against (1) the durable
  `retired_gap_fill_keys` set and (2) any key already realized as an accepted
  `Bullet.source` (`llm_proposed:<key>`) for this candidate — so a Regenerate
  never resurfaces a proposal the user already decided on, retired OR accepted.
  The guarantee is enforced by exact key match (not by asking the LLM to avoid
  the content), so it holds regardless of model behavior. `PROMPT_VERSION` is
  UNCHANGED (`2026-07-06.3`) — `DRAFT_GAP_FILL_SYSTEM_PROMPT` was not touched;
  `TestGapFillPromptInvariance` (extended with `retired_gap_fill_keys`) still
  proves the legacy generate() prefix is byte-identical.
- **Presence-semantics interaction (the load-bearing design decision):** the
  once-only AUTO-FIRE latch (`has_gap_fill` = key presence, not list
  non-emptiness) is UNCHANGED — it still fires the silent background draft at
  most once per application. Regenerate is a SEPARATE, explicit, user-triggered
  call to the identical route that deliberately bypasses that latch (by design,
  not a bug) — durability against resurfacing a decided-on proposal comes from
  `retired_gap_fill_keys` (+ the accepted-Bullet check), not from the latch.
- Tests: `tests/test_regenerate_gap_fill.py` (`TestDraftGapFillExcludesRetired`,
  `TestDraftGapFillExcludesAccepted`, `TestGapFillDecideRetirePersistsKey`,
  `TestPostCompositionRetiredGapFillKeys` incl. an explicit clobber-invariant
  regression), `tests/ux/regression/test_20260708_compose_gap_fill_regenerate.py`
  (button visibility + retire→regenerate→no-resurface, incl. across a reload
  and a Save-and-continue POST body assertion).
- Validation: real-LLM regenerate cycle on a sandbox context (retire → regenerate
  → confirm the retired key never resurfaces) — see `evals/TUNING_LOG.md`
  "regenerate-gap-fill" entry for the transcript + actual telemetry cost.

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

---

## 8. LATER branch — item (a): surgical refinement + richer loop-back — DONE 2026-07-08

Branch `fix/surgical-refinement-and-loopback` off `main` (post Trains 1+2 UX-review
remediation). Replaces the Phase 4 interim ("route to Compose, tell the user to redo
it themselves") with an actual scoped proposal.

- `analyzer.py`: `DRAFT_SURGICAL_REFINEMENT_SYSTEM_PROMPT` + `draft_surgical_refinement()`
  (**Sonnet**) + `DraftSurgicalRefinementResponse` + a `_current_composition_block(doc)`
  helper (mirrors `_corpus_block`'s role for `draft_gap_fill_bullets`) that renders the
  CURRENT frozen `approved_composition` — summary + per-role bullets with their real
  corpus ids — so the model can name the EXACT item a note refers to. Given a free-text
  note, proposes exactly ONE of: `"bullet"` (sharpen an EXISTING bullet via
  `supersedes_bullet_id`, or a genuinely stronger NEW bullet where the corpus is silent),
  `"summary"`, or `"none"` (a broad "rewrite everything" ask — no single scoped target,
  so nothing is proposed and the plain loop-back copy renders instead). Grounded: every
  claim must already appear in `<current_resume>`/`<clarifications>` — reframing, never
  inventing. Short-circuits WITHOUT an LLM call when there's no note, no frozen
  composition, or no JD. `PROMPT_VERSION 2026-07-06.3 → 2026-07-08.1` (a NEW per-call
  template; the generate prompt is unchanged, so legacy + `--suite synthetic` stay
  byte-identical — proven by the short-circuit unit tests, mirroring the Phase 2/3
  precedent rather than a bespoke invariance test).
- `blueprints/applications.py`: `POST /api/applications/<id>/draft-refinement` is a PURE
  READ — stages the note + JD, calls the analyzer, then re-validates every id the model
  returned against the candidate's own corpus (a foreign experience/bullet id downgrades
  the proposal to `null` rather than risking a foreign write), and returns the proposal.
  Nothing is persisted — unlike the gap-fill/summary drafts, there is no ctx write at this
  step, so a proposal the user never acts on leaves zero trace. `POST
  /api/applications/<id>/accept-refinement` applies an accepted proposal (the client
  echoes the full proposal back, never trusted blindly — re-validated again server-side):
  `"bullet"` creates a pending `Bullet` (`source='llm_proposed:refine:<key>'`,
  `is_pending_review=1`, idempotent on that source key like `gap_fill_decide`), folds its
  id into `composition_overrides.accepted_generated_bullet_ids`, and — when the proposal
  named a `supersedes_bullet_id` — folds THAT bullet into `composition_overrides.excluded`
  too, so the composition gains exactly ONE net item (the "scoped single-item change" the
  spec calls for); `"summary"` persists straight into `composition_overrides.summary_text`
  (mirrors `/draft-summary`'s persist). **Zero changes to `corpus_to_json_resume.py`** —
  both cases reuse override keys the resolver already honors (`accepted_generated_bullet_ids`
  / `excluded` / `summary_text`), so there was no new resolver surface to build or test.
  RETIRE never reaches the server (nothing was written for a proposal the user hasn't
  accepted yet) — the Compose banner dismisses it client-side.
- `static/app.js` + `static/style.css`: `submitRefinement()`'s corpus-mode path now runs
  the SAME fact-scope check (`/api/validate-refinement` + `_showRefinementScopeModal`) the
  legacy full-regenerate path always ran — previously skipped in corpus mode since there
  was no LLM call to gate — then drafts the proposal and routes to Compose with both the
  note and the proposal stashed (`_composeRefinementProposal`, alongside the existing
  `_composeLoopbackNote`). `_renderComposeLoopbackBanner(data)` renders the actual proposed
  change (old text struck through when superseding, then the new text, plus the model's
  rationale) with Accept/Retire, falling back to the prior plain "adjust it yourself" copy
  when the model returned `"none"`. Both proposal state flags are purely client-side
  (mirrors how `_composeLoopbackNote` already worked) — a page reload mid-review loses the
  pending proposal, same as it already lost the pending note.
- Tests: `tests/test_draft_surgical_refinement.py` (short-circuit — no note / no frozen
  composition / no JD; route normalization + ownership re-validation for foreign ids),
  `tests/test_accept_refinement.py` (bullet accept with/without supersede, idempotency,
  summary accept, validation), `tests/test_demo_mode.py::test_draft_surgical_refinement`
  (demo mode proposes nothing — same grounding-safety posture as `draft_gap_fill_bullets`).
- Real-LLM validation: one scoped refinement against a live sandbox application — see
  `evals/TUNING_LOG.md` "surgical-refinement-and-loopback" entry for the transcript,
  the proposal shape returned, and the telemetry cost.

**All four LATER-branch remainder items are now DONE** — (b) WYSIWYG-as-source (D4)
in §9, (c) clarifications→corpus (D5) in §10, (d) regenerate-gap-fill in §6 (the
as-built subsection below the Phase 5 record).

---

## 9. LATER branch — item (b): WYSIWYG as source of truth — DONE 2026-07-08

Branch `feat/wysiwyg-source-of-truth` off `fix/surgical-refinement-and-loopback` @
`1200b66` (Train 3, lane (b) — built after §8's item (a) landed on this branch's base).
Closes the gap between D4's acceptance bar ("preview and download always match") and
what shipped through Phase 4: the styled Step-6 iframe only ever picked up an in-app
edit AFTER `/api/save-edits` ran (gated behind the "Use edits as baseline" modal, which
only fires right before a refine/iterate action). Between typing an edit and that
unrelated action, `/api/download-edited` (which reads `#resumePreview` /
`#coverLetterPreview` directly) already produced the new content while the visible
preview kept showing the old — preview != download, exactly the surprise D4 exists to
kill.

- **`POST /api/applications/<id>/preview-edited` (new route, `blueprints/templates.py`)**
  — the preview-side twin of the existing `/api/download-edited`: content in, rendered
  HTML out, NOTHING written to context or the DB. Résumé content renders through the
  same `md_to_json_resume(_normalize_markdown(...))` → `render_html_string` pipeline
  `save_edits` already uses to recompute its cache; cover-letter content renders through
  `render_cover_letter_html` — the identical deterministic pipelines the CACHED preview
  routes use, just applied to live POSTed text instead of a stored snapshot. Persona
  resolution + ownership mirror `preview_application_html` (`_load_application_owned` +
  an explicit `_safe_username` recheck + an explicit `_within(PERSONAS_DIR)` recheck on
  the resolved template path — belt-and-suspenders, satisfies `route-security-lint`).
- **`static/app.js`**: `_wireLiveEditPreview` / `_refreshLiveEditPreview` wire a
  debounced (300ms — the same cadence as Compose's `_scheduleCompositionSave`) `input`
  listener on both editors. On fire, POSTs the live editor text to the new route and
  swaps the relevant iframe's `srcdoc` (`outputPreviewFrame` / `coverPreviewFrame`),
  gated on `_composeApplicationId != null` (legacy file-based mode has no styled
  iframe). The EXISTING edit-detection modal (`#editModal`, F-14's "Your edits aren't
  saved yet" copy) and its `/api/save-edits` persistence path are **completely
  unchanged** — this route never touches `edited_resume_text`, so the modal's copy
  stays accurate (a deliberate scope decision: a live, non-persisting preview refresh
  sidesteps the "discard must also clear a stale auto-save" correctness problem a
  persisting auto-save would have introduced; see the `feat/wysiwyg-source-of-truth`
  branch discussion below for why that alternative was rejected).
- **Cover-letter preview precedence fix** (`preview_cover_letter_html`,
  `blueprints/templates.py`): a real, independent bug found while implementing this —
  the route read `last_generated_cover_letter` unconditionally and NEVER checked
  `edited_cover_letter_text`, even though `save_edits` has persisted that field since
  Phase 1. A saved cover-letter edit was invisible to the styled preview forever. Fixed
  to mirror the résumé preview's existing `edited_resume_text` precedence (D6(a)).
- **DB durability fix** (`_persist_edited_text_to_db`, `blueprints/generation.py`): a
  second independent gap found in the same pass — `ApplicationRun.edited_resume_text` /
  `edited_cover_letter_text` exist on the model (its class docstring literally says
  "the frozen corpus snapshot plus every generated **and edited** artifact") and are
  already READ by `_build_resume_state` (the degraded-mode Step-6 rehydrate when the
  on-disk context file is gone) and `get_application`'s `has_edits` flag — but were
  never WRITTEN anywhere in the codebase. `save_edits` now mirrors a corpus-backed edit
  onto both columns (best-effort, mirrors the sibling `_persist_run_persona` — a DB
  hiccup never fails the save, since the context file is already the primary,
  already-persisted source). Without this, resuming an application after its context
  file was cleaned up silently reverted Step 6 to the un-edited AI text.
- **Design decision — ephemeral live-render over a new auto-save.** The alternative
  considered was debouncing a call to the EXISTING `/api/save-edits` (persisting on
  every pause in typing, not just before refine/iterate). Rejected: once an edit
  auto-persists outside the explicit gate, "Discard edits" in that gate must ALSO
  revert the persisted `edited_resume_text` / DB row (not just the DOM) or a discarded
  edit would keep permanently overriding a later Compose re-freeze — a correctness
  regression this branch does not want to own. Rendering live content ephemerally (no
  persistence at all until the user explicitly picks "Use edits as baseline", exactly
  as before) reaches the same acceptance bar — preview always matches what Download
  would produce — without touching the save/discard semantics at all.
- Tests: `tests/test_live_preview_route.py::TestPreviewEditedRoute` (renders résumé /
  cover-letter content matching the editor; matches the PERSISTED WYSIWYG preview for
  identical input — the transitive download==preview proof, since
  `TestApplicationPreviewWysiwyg` already proves the persisted path == download; nothing
  persisted; validation / ownership / 404s) +
  `TestCoverLetterPreview::test_edited_text_wins_over_last_generated` +
  `tests/test_app_iteration.py::TestSaveEditsRoute` (DB row persists for a corpus-backed
  save, a foreign/missing run row doesn't fail the save, a legacy context with no
  `application_run_id` skips the DB write entirely).
- No prompt text changed anywhere in this branch — `analyzer.py` is untouched;
  `PROMPT_VERSION` stays at `2026-07-08.1` (item (a)'s value). No real-LLM validation
  run — there is no live prompt path in this branch's diff to validate.

**All four LATER-branch remainder items are now DONE** — (a) surgical refinement
in §8, (c) clarifications→corpus (D5) in §10, (d) regenerate-gap-fill in §6 (the
as-built subsection below the Phase 5 record).

---

## 10. LATER branch — item (c): clarifications persist to the corpus for cross-JD reuse — DONE 2026-07-08 (`feat/clarifications-to-corpus`)

Branch `feat/clarifications-to-corpus` off `feat/wysiwyg-source-of-truth` (Train 3,
lane (c) — built after §8's item (a) and §9's item (b) landed on this branch's
base). D5, the last of the four LATER-branch remainder items from §4/§6 to land
on its own branch — item (d) regenerate-gap-fill shipped in parallel (Train 3
lane (d)), as-built in §6 above.

**Scope, exactly as bounded by §2 Stage 3 / §3.5 point 3:** feed the
candidate's confirmed clarifications from OTHER applications into Compose
CONTENT DRAFTING (summary / gap-fill / skills) — NOT into `clarify()`'s
question-asking (out of scope; `clarify()` itself still does not read prior
clarifications, only `clarify_iteration` does, and only within the SAME
application). Promote-to-corpus already existed
(`analyzer.promote_clarification_to_bullet` +
`blueprints/corpus/proposals.py`) — not this branch's job.

**Mechanism decision — direct injection via the SAME `<clarifications>`-family
block, not corpus-mediated through promotion.** §3.5 point 3 already treats
`draft_positioning_summary`'s `<clarifications>` block as a legitimate
grounding source; D5 widens that established pattern to a second,
distinctly-named `<prior_clarifications>` block, populated from the
`clarification` table's cross-application rows (the table is candidate-scoped
by design — see `Clarification`'s docstring), rather than requiring each fact
be promoted to a `Bullet` first. The promote-to-corpus path is a SEPARATE,
already-shipped, user-gated action — D5 doesn't route through it.

**Staging point — `db.build_context.build_context_set_from_db`, once, at
context-build time.** A new `_prior_clarifications_for_candidate()` helper
queries `clarification` by `candidate_id` (capped at 40, most-recent-first)
and writes the result onto `context_set["prior_clarifications"]`
(`hardening.PriorClarification`, `total=False`). The just-created
`Application` row can't own any existing row yet, so no origin filter is
needed. Corpus-mode only (legacy file-based contexts never populate it — the
default path stays byte-identical). Every downstream reader — the three
drafting calls AND the grounding metric — only ever reads `context_set`, so
neither needs live DB access.

**Compose drafting — two DIFFERENT grounding postures, on purpose:**
- `draft_positioning_summary` and `suggest_skills` treat `<prior_clarifications>`
  as FULL grounding source material (their GROUNDING rule / worked examples
  widened to say so explicitly) — a confirmed fact from an earlier application
  is real evidence for this one. `suggest_skills`'s evidence shape already
  supported this with zero schema change (`evidence.bullet_id`/`experience_id`
  both `null` when the evidence is a clarification quote, vs populated when
  it's a corpus row).
- `draft_gap_fill_bullets` keeps `<prior_clarifications>` CONTEXT-only — its
  GROUNDING rule (bullet evidence must cite `<career_corpus>`) is UNCHANGED.
  The real-LLM validation below confirms this holds under a live model, not
  just in prompt text.

**Grounding metric widened to match — justified, not left to drift.**
`hardening.assemble_source_union` (the deterministic 3-source grounding
check shared by `compute_iteration_signals` and the eval-time L0 check) now
also folds in `prior_clarifications` answers. Once Compose drafting can
legitimately cite a cross-JD fact, the metric MUST see the same union the
prompt does, or it over-reports correctly-grounded content as fabrication —
this is the same reasoning that motivated the original clarifications carve-out
(AGENTS.md "LLM prompts"). The legacy `generate()` prompt is untouched, so
`assemble_source_union`'s behavior on any context without `prior_clarifications`
(every pre-D5 / legacy context) is unchanged.

**`PROMPT_VERSION 2026-07-08.1 → 2026-07-08.2`** — the three Compose drafting
system prompts (`DRAFT_SUMMARY_SYSTEM_PROMPT`, `DRAFT_GAP_FILL_SYSTEM_PROMPT`,
`SUGGEST_SKILLS_SYSTEM_PROMPT`) changed text; the legacy résumé-body `generate()`
prompt did not. (This branch landed last in the Train 3 chain, after item (a)'s
own prompt-template addition had already bumped `PROMPT_VERSION` to
`2026-07-08.1` — see §8 — so this is the SECOND bump of the day, to `.2`, to
keep the two independent prompt changes separately attributable.)

**Validation — real-LLM, end to end, on a throwaway sandbox candidate (not
`--suite synthetic`, which is legacy-only and doesn't cover corpus mode; see
§2 Global constraints).** Full scenario + numbers: `evals/TUNING_LOG.md`
"D5 clarifications-to-corpus" entry and the CHANGELOG `[Unreleased]` entry.
Headline: answering a clarification under a Platform Engineer JD and then
running a Senior SRE JD for the same candidate produced a positioning summary
that wove in the cross-JD fact, 3 skill proposals evidenced ONLY by the
clarification (correctly `bullet_id`/`experience_id: null`), ZERO gap-fill
bullets fabricated from the clarification alone (the corpus-evidence boundary
held), and zero leak into a second, unrelated candidate's context. 9 real
calls, $0.1111 total.

**Deterministic tests:** `tests/test_build_context_db.py::TestPriorClarifications`,
`tests/test_hardening.py::TestAssembleSourceUnion` (the two new cases),
`tests/test_draft_summary.py::TestDraftSummaryPriorClarifications`,
`tests/test_draft_gap_fill.py` (`test_prompt_includes_prior_clarifications`),
`tests/test_suggest_skills.py` (`test_prior_clarifications_render_in_prompt`).
