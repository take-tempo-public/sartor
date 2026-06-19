# Tuning the callback. Assistant — Citation & Reference Formatting (Polish Follow-on)

> **What this is.** A **focused follow-on** to [`avatar-voice-tone-guidance.md`](avatar-voice-tone-guidance.md) — not a second full package. The voice/tone tuning landed well (owner, 2026-06-19: *"much better than it was"*); what remains is a single, well-diagnosed surface problem: the assistant's **citations and references render inconsistently**, mixing three bracket/parenthesis conventions in the same sentences. This brief captures the owner's testing feedback, the verified root-cause diagnosis, the design decision the implementation sprint must make (posed as clarifying questions with provisional recommendations, the same way the parent guidance posed its Part 2 questions), the lever map, and per-cause requirements + acceptance signals. It does **not** change any code or prompt — that is the next sprint, on its own branch.

> **Audience:** dev / the agent that executes the citation-format polish sprint.
> **Parent:** [`avatar-voice-tone-guidance.md`](avatar-voice-tone-guidance.md) (the L1–L5 lever framing, the P0 prime directive, and the avatar-eval discipline all carry over).
> **Anchors verified at** HEAD `7ec0f92` (main at this branch's point). Re-verify line numbers at execution time — they drift.

---

## Executive Summary

**P0 is unchanged and governs here too: grounding and honesty outrank charm, always.** This work is a *readability* fix, but its acceptance bar is a *grounding* bar — a citation the reader cannot resolve, or a "Sources" footer that overstates what actually grounded the answer, is a P0 problem, not a cosmetic one. The goal is that **every reference the avatar shows is consistent, self-describing, and honestly tied to what it used.**

The owner's test (a Dev-mode "where should I start?" answer) shows three conventions colliding in the same sentences:

1. **markdown links** — `` [`architecture.md`](docs/architecture.md) ``
2. **plain parentheticals** — `(pipeline, persistence, data-flow, LLM routing)`
3. **numeric citation markers** — `[4]`, `[5]`, `[8]`

…over a 16-entry comma **"Sources:"** footer the `[N]` markers don't resolve to. The brackets are doing three jobs at once, and the numbers point at nothing the reader can follow.

**Recommended direction (provisional): commit fully to the design the voice/tone work already chose — self-describing single-bracket inline citations (`[deterministic-llm-boundary]`, `[analyzer.py:34]`), no `[N]`, no markdown links — and make the "Sources" footer honestly reflect what was cited.** The single highest-leverage change is **not** a prompt rule (one already exists and is being ignored) but the **context renderer** that hands the model numbered units — it is teaching the model the `[N]` habit by example.

---

## The feedback (owner, 2026-06-19)

> *"It's much better than it was, but note the inconsistency and confusing way of using brackets and parentheses in the response below."*

The example answer (Dev mode, question *"where should i start to understand the project architecture, conventions, etc.?"*) rendered, e.g.:

> Start with `` [`architecture.md`](docs/architecture.md) `` for a fast system tour — it has the module map and four Mermaid diagrams (pipeline, persistence, data-flow, LLM routing) `[4]`. …

and closed with a footer:

> Sources: AGENTS.md:16, …excellence-walk.md:421, deterministic-llm-boundary, AGENTS.md:34, system-model.md:1, … (16 entries) · context truncated

Two things read as unfinished: the **brackets/parens are inconsistent**, and the **`[N]` markers don't map to anything** the footer presents (it is an unordered comma list, not a numbered key).

---

## Verified diagnosis (read-only trace at HEAD `7ec0f92`)

Three distinct, independent mechanical causes — all **server / prompt-side**; the browser renders the answer body as raw text and changes nothing.

### C1 — numeric `[N]` citations (the `[4]`/`[5]`/`[8]`)
`analyzer.py:1538` `_render_recalled_context` builds the model's context block as one line per unit:
```python
lines = [f"[{i}] {u.citation}: {u.text}" for i, u in enumerate(context.units, start=1)]
```
So the model **sees** `[1] [[slug]]: …`, `[2] path:line: …`, and mirrors that leading number — emitting `[4]`/`[5]` instead of the unit's actual citation. The `AVATAR_SYSTEM_PROMPT` rule forbidding exactly this (`analyzer.py:533`, *"Put ONLY the slug or path:line inside the brackets"*) is losing to the numbered presentation. **A prompt-only fix is fragile while the input keeps modeling `[N]`.**

### C2 — markdown links (`[text](path)`)
The model invents markdown links for file names; **no code generates or requests them**. The answer body is written with `textContent` (`static/assistant.js:43`; `#assistantAnswer` is a plain `white-space:pre-wrap` div, no markdown renderer), so they show as **raw markdown** — brackets + backticks + parens — not clickable links. They also violate the prompt's *"never wrap a phrase, sentence, or link text in brackets"* rule (`analyzer.py:533`). Dev-mode answers, which lean on file references, amplify this.

### C3 — the "Sources:" footer is the whole retrieved set, not what was cited
`analyzer.py:1595` emits `"citations": [u.citation for u in context.units]` — **every retrieved unit** (16 here), independent of what the answer actually used. The client (`static/assistant.js:69–79` `_renderAssistantSources`) dedups and strips `[[ ]]`, then comma-joins. The result is **not a numbered map**, so a body marker `[4]` is literally unresolvable; and the footer **overstates grounding** by listing context the answer may never have touched — a P0 honesty concern, not just clutter.

*(One consequence worth calling out: because `[N]` indexes the model's view of the units and the footer is a deduped/reordered list, a marker like `[4]` cannot be checked against its source at all — switching to self-describing `[slug]`/`[path:line]` is what makes a misattribution visible.)*

---

## The core design decision (clarifying questions — provisional recs, owner locks at execution)

**Q-CITE-1 — which citation model?** *(headline decision; everything else follows)*
- **(A) Self-describing inline cites — provisional recommendation.** Body cites `[deterministic-llm-boundary]` / `[analyzer.py:34]` at sentence end; the footer is the **deduped set actually cited**, honestly labeled. No `[N]`, no markdown links. This is already the voice/tone work's stated intent and the smallest coherent change.
- **(B) True numbered footnotes.** Body uses `[1]`/`[2]`; the footer becomes a **numbered `[n] → citation` key** that resolves. Legitimate, but it requires the numbers to be stable and correct end-to-end and a richer footer renderer — more surface, more ways to drift.

**Q-CITE-2 — render markdown, or stay plain text?**
- **Provisional: stay plain text and stop the model emitting markdown links** (forbid them harder + remove the numbered-unit precedent so the model stops decorating). Rationale: clickable links + bracket citations re-introduce bracket overload; the citations already name the file. *(If clickable file links are wanted as a feature, that is a deliberate L3 rendering change — render a constrained markdown subset — and must be decided as such, not left to the model to improvise.)*

**Q-CITE-3 — footer = cited-only, or retrieved-with-honest-label?**
- **Provisional: footer reflects the set actually cited in the answer** (parse the body's emitted `[slug]`/`[path:line]` tokens, or have the model return its used citations), so the footer can't overstate grounding. If a "retrieved but unused" list is ever shown, it must be **labeled as such** — never implied to be what grounded the answer.

**Q-CITE-4 — dev vs user citation density.** Dev mode legitimately cites more `[path:line]`; confirm the target keeps dev answers dense-but-clean and user answers wiki-slug-first (consistent with the parent guide's user/dev register split). *Provisional: yes, no change to the split; the fix is format consistency, not density.*

---

## Lever map (extends the parent's L1–L5)

| Lever | Location | Role in this work |
|---|---|---|
| **Context renderer** (the key new lever) | `_render_recalled_context` — `analyzer.py:1538` | **C1's root.** Drop or relocate the leading `[{i}]` so no numeric-citation precedent leaks into the model's view (e.g. number with a different delimiter, or don't number at all). A per-call prompt template → **bumps `AVATAR_PROMPT_VERSION`.** |
| **L1** `AVATAR_SYSTEM_PROMPT` | `analyzer.py:526` (cite rules at `:533`) | Tighten/clarify: forbid `[N]` and markdown links by worked example, not just prose; add an OK/NOT-OK pair. Bumps `AVATAR_PROMPT_VERSION`. |
| **L3** UI render + footer | `static/assistant.js:43` (body), `:69–79` (`_renderAssistantSources`), `templates/index.html` | **C2/C3.** Decide markdown-render vs plain (Q-CITE-2); make the footer reflect cited set / a numbered key (Q-CITE-1/3). |
| `citations` payload | `analyzer.py:1595` | **C3.** Source of the footer set — change from "all retrieved" to "actually cited" (or numbered key) per Q-CITE-1/3. |
| **L5** dev-mode | `analyzer.py:534` | No change expected; noted because dev answers amplify C2. |

**Version discipline (carried from the parent):** any change to the context renderer, `AVATAR_SYSTEM_PROMPT`, or the per-turn scaffold **bumps `AVATAR_PROMPT_VERSION` (`analyzer.py:290`) in the same commit**; the avatar stays out of `_BASE_SYSTEM_PROMPTS`; `PROMPT_VERSION` (résumé) is untouched.

---

## Requirements + acceptance signals

Extend the existing LLM-free deterministic checks in [`tests/test_avatar_streaming.py`](../../tests/test_avatar_streaming.py) (which already scans model output for banned phrases, no-URL, cite-membership, etc.):

- **R1 (C1) — no numeric citation markers.** The avatar's answer text contains no `[\d+]` token. *Acceptance:* a scanner over a fixture answer asserts zero `[N]` matches; the context renderer no longer presents a `[{i}]`-prefixed unit line (unit-test the renderer output directly).
- **R2 (C2) — no markdown links.** The answer text contains no `](` substring (markdown-link tell). *Acceptance:* scanner asserts zero `](`; if Q-CITE-2 chooses to render markdown instead, this flips to a render-side test that the link resolves and the citation is not also bracketed.
- **R3 (C3) — every shown reference is honest.** Under scheme A: every inline `[slug]`/`[path:line]` resolves to a footer entry, and the footer contains no citation the body did not use (or a clearly-labeled "also retrieved" section). Under scheme B: every body `[n]` resolves to a numbered footer entry. *Acceptance:* a resolver test pairing body markers ↔ footer entries.
- **R4 — grounding not regressed.** The existing cite-membership / no-fabrication checks stay green; re-run the parent guide's §6.3 Haiku spot-check matrix and confirm no new drift (the parent already noted the model's Haiku citation-format/line-approximation fragility — this work should *reduce* it). Fold the result into the **owed v1.0.8 labeled avatar eval** (carry-forward ledger), which quantifies cite-membership.

**Non-goals:** no change to retrieval, ranking, the token budget, the user/dev access boundary, or the résumé pipeline; no new dependency; not a voice/tone change (the parent owns that).

---

## How this lands

- **Its own branch**, sequenced after the v1.0.7 tag (this is a v1.0.8-band polish; it is **not** a blocker for the 7.9 tag). One contained branch: context renderer + `AVATAR_SYSTEM_PROMPT` + the L3 footer/render decision + deterministic tests + `AVATAR_PROMPT_VERSION` bump + CHANGELOG.
- **Owner locks Q-CITE-1…4 first** (provisional recs above), the way the parent guide's Part 2 questions were locked in a dedicated session.
- **Validate live** with the parent's in-process method (the `blueprints.assistant` helpers + an old-vs-new prompt comparison) plus the deterministic R1–R3 checks; record before/after in [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md).
