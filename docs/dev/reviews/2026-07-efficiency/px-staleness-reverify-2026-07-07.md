---
status: review-artifact
evidence_sha: 6071478
graduation: none (action layer; feeds RELEASE_ARC / RELEASE_CHECKLIST via normal dev branches)
---

# PX staleness re-verify — 2026-07-07

> **Purpose.** Pre-build staleness re-verification of the 7 prescriptions flagged
> as possibly stale in the 2026-07 efficiency review
> ([`prescriptions.md`](prescriptions.md)) before their branches land: PX-38, PX-39,
> PX-43, PX-45, PX-47, PX-51, PX-55. Run 2026-07-07 at HEAD `6071478` on branch
> `chore/px-staleness-reverify`, per **Phase 0** of the owner-approved big-push plan
> (see [`RELEASE_ARC.md`](../../RELEASE_ARC.md) §Phase 4.8, "Big-push scope brief").
> Each of the 7 was independently re-verified against HEAD (not against the review's
> own line-number cites) by a dedicated verifier agent; this file is the durable
> record of those 7 dispositions.

**Verdict legend** (single verdict used throughout this run):

- **PARTIALLY_STALE** — the underlying premise/problem still holds (nothing here was
  refuted), but something about the prescription's *as-written* scope has drifted since
  the review's `4196d0c` evidence pin — shifted line-number cites, a sub-item already
  landed by an intervening branch, a count/measurement that needs re-taking, or a framing
  that overstated the fix's size. Each row below carries a `revised_scope` that is the
  corrected version to build against, not a rejection of the prescription.

## Summary

| PX-id | Verdict | Disposition |
|---|---|---|
| PX-38 | PARTIALLY_STALE | N+1 confirmed still present; every cited line shifted; widen scope to also selectinload `Experience.summary_items` (a third query family the original finding missed). |
| PX-39 | PARTIALLY_STALE | Baseline still un-landed; must NOT restate the 4.6-era 69.7s/84.6s numbers as current — Sonnet-5 upgrade + frozen-composition both post-date the pin; re-scope to a fresh, model/path-segmented measurement. |
| PX-43 | PARTIALLY_STALE | All 5 CI-hygiene sub-items confirmed still open exactly as prescribed; only 2 of 5 cites drifted by +6 lines (ruff-format-pin insertion) — cite-freshness fix only, no scope change. |
| PX-45 | PARTIALLY_STALE | 2 of 3 legs (CLAUDE.md trim, AGENTS.md boundary-list dedup) unchanged; the cache-miss leg is understated — 14 override call sites now exist (not 11), incl. 2 new gap-fill prompts — needs recount before landing. |
| PX-47 | PARTIALLY_STALE | 3 of 4 legs still open (plugin.json bump, CLAUDE.local.md refresh, model-pin convention); settings.local.json prune is already DONE — drop that sub-item; model-pin re-scoped to an explicit owner decision (no dated Sonnet-5 snapshot exists on the API). |
| PX-51 | PARTIALLY_STALE | Real, self-documented duplicate-cascade problem confirmed, but original framing overstated (~780 lines / ~20% shrink) — true duplicate span is ~181 lines (14-17 selector groups); re-scope to a precise selector-level collapse, not a block merge. |
| PX-55 | PARTIALLY_STALE | Wrapper script still needed, but must widen from a 3-command to a 4-command gate (`ruff check` + `ruff format --check` + `mypy` + `pytest`) — CI and the pre-commit hook already both enforce format-check; the docs the wrapper centralizes are already stale on this point. |

**Additional Phase-0 measurement (mypy-strict re-baseline).** mypy `--strict`
re-measure (2026-07-07, HEAD `6071478`): **2821 errors / 126 of 248 files** —
this count includes `tests/`, unlike the ratcheted production-module figure. The
production-module ratchet number must be normalized per the
`[[tool.mypy.overrides]]` per-module ratchet methodology (`pyproject.toml`) at
the v1.0.9 `chore/mypy-strict` branch (Phase 6 of the big-push plan), where the
whole-tree
figure gets decomposed back into the per-module ratchet convention. **This
replaces the stale "146 errors / 18 modules" figure currently cited in
`RELEASE_ARC.md` §v1.0.9** — that figure was a per-module-ratchet count under a
different methodology and is not directly comparable to this whole-tree,
tests-included number; do not diff them naively.

---

## PX-38 — Fix the Compose-route N+1 + the is_active index gap

**Verdict:** PARTIALLY_STALE

### Evidence

Core N+1 confirmed still present at HEAD in blueprints/applications.py:get_application_composition, but every cited line number has shifted and one in-scope query family was missed by the original finding.

- Experience query, no selectinload: blueprints/applications.py:962-969 (was 898-903 at the F-run-06 pin) — `session.query(Experience).filter_by(candidate_id=candidate.id)...all()`, no `.options(selectinload(...))`.
- Per-experience `.bullets` lazy load: blueprints/applications.py:976 (`for b in exp.bullets:`) — was cited at :913.
- Per-bullet `.tag_links` lazy load: blueprints/applications.py:994 (`"tags": _tag_list(b.tag_links)`) — was cited at :916.
- Per-experience `.titles` lazy load: blueprints/applications.py:1031 (`for t in exp.titles:`) — was cited at :965.
- Per-title `.tag_links` lazy load: blueprints/applications.py:1044 (`"tags": _tag_list(t.tag_links)`).
- NEW (uncaptured by F-run-06) per-experience query in the SAME function, pre-dating the pin (B.4/Sprint 6.6, confirmed unchanged by `git diff 4196d0c HEAD -- blueprints/applications.py`): blueprints/applications.py:1087-1098, `session.query(ExperienceSummaryItem).filter_by(experience_id=exp.id, is_active=1)...` runs unconditionally per experience — a third per-experience query family the "mirror list_applications" selectinload fix as scoped won't cover unless the chain also adds `selectinload(Experience.summary_items)`.
- Relationships confirmed real (selectinload is viable): db/models.py:110-125 (`Experience.titles`, `Experience.bullets`, `Experience.summary_items`), :156 (`ExperienceTitle.tag_links`), :195 (`Bullet.tag_links`).
- `git diff 4196d0c HEAD -- blueprints/applications.py` shows the frozen-composition rework (a7a4d87/ad71833/ec64594, merged 0a18876) inserted two new helper functions (`_read_summary_draft`, `_read_gap_fill`, ~54 lines) before `get_application_composition` and added new per-experience reads inside it (`gap_fill_by_exp.get(exp.id, [])`, `b.id in accepted_generated_ids`) — these are O(1) dict/set lookups against an already-parsed context dict, NOT new DB queries, so they don't add new N+1s themselves; they only pushed the pre-existing cites downward.
- is_active index gap (F-run-10) unchanged: `git diff 4196d0c HEAD -- db/models.py` is empty. db/models.py:774 `Index("ix_application_candidate_status_updated", "candidate_id", "status", "updated_at")` still omits is_active; blueprints/applications.py:149,152,155 (list_applications default path) still filters candidate_id + status + is_active — cite is accurate as-is, no revision needed.
- Already-fixed mirror pattern still present/unchanged: blueprints/applications.py:146-162 (`selectinload(Application.runs)` + one grouped ProposalReview count query) — the pattern to mirror is intact.
- No test currently guards get_application_composition's query count (`tests/test_application_routes.py:258-291` has the pattern only for list_applications; grep for `get_application_composition` in tests/ hits only the unrelated route-containment gate) — confirms the fix + guard test are still un-landed.
- New freeze/gap-fill routes checked for new N+1s: `draft_application_gap_fill` (blueprints/applications.py:2016-2130) and `gap_fill_decide` (:2134-2296) each issue a single, non-looped Experience/Bullet query — no N+1 introduced. `draft_application_summary` (:1899-2000) reads career facts from the in-memory context dict (`_career_facts_synopsis`), no DB loop.
- Related but out-of-scope: `corpus_to_json_resume.build_json_resume_from_corpus` (corpus_to_json_resume.py:176-181 Experience query no selectinload, :241 per-experience `exp.bullets`, :213-217 conditional per-experience `_resolve_chosen_experience_summary_text` query at :550-554) carries the same anti-pattern class and pre-dates the pin (confirmed present in `git show 4196d0c:corpus_to_json_resume.py`), but the new `freeze_approved_composition` wrapper (corpus_to_json_resume.py:339-376), called from `save_application_composition` on every freeze (blueprints/applications.py:1601-1609), now invokes it on a new, more frequent call path. Distinct function/route from get_application_composition — not required for PX-38 to land, flagged only as a candidate follow-on.

### Revised scope

Build perf/compose-selectinload as prescribed (selectinload chain on get_application_composition's Experience query + add is_active to the composite index + an N+1 guard test mirroring tests/test_application_routes.py:258-291's after_cursor_execute pattern), but with two corrections to scope before landing:

1. Re-anchor the finding's cites to HEAD: Experience query at blueprints/applications.py:962-969 (not 898-903); per-experience `.bullets`/`.tag_links` at :976/:994 (not :913/:916); per-experience `.titles`/`.tag_links` at :1031/:1044 (not :965). The selectinload chain needed is `.options(selectinload(Experience.bullets).selectinload(Bullet.tag_links), selectinload(Experience.titles).selectinload(ExperienceTitle.tag_links))`.

2. Widen the fix by one query family: also selectinload `Experience.summary_items` (or restructure the per-experience `ExperienceSummaryItem` query at blueprints/applications.py:1087-1098) — this pre-existing, unconditional per-experience query wasn't in F-run-06's evidence but is in the same function and same O(E) class; landing only the bullets/titles selectinload chain would leave one N+1 site behind and the guard test would need to assert on the FULL corrected count, not a partial one.

The db/models.py:774 index fix needs no revision — cite and premise both hold unchanged at HEAD.

Optionally note (not required for this branch): corpus_to_json_resume.build_json_resume_from_corpus has the same anti-pattern class and is now reached more often via the new freeze path — worth a future PX row, out of this branch's stated scope.

### Notes

Read docs/dev/reviews/2026-07-efficiency/prescriptions.md:49 (PX-38 row) and findings/b-runtime.md:64-71 (F-run-06) + :94-99 (F-run-10) for the original claims. Verified against HEAD (working tree, branch docs/ux-review-2026-07, no relevant uncommitted changes) via Read on blueprints/applications.py, corpus_to_json_resume.py, db/models.py, plus `git diff 4196d0c HEAD -- blueprints/applications.py` / `-- db/models.py` / `-- corpus_to_json_resume.py` to separate what the frozen-composition rework (a7a4d87/ad71833/ec64594, merge 0a18876) actually touched from what merely shifted. The other four post-pin branches listed in the task (sonnet-5 model upgrade, ruff-format-pin, compose-settle-bg-reload, docs/ux-review-2026-07) don't touch blueprints/applications.py, corpus_to_json_resume.py, or db/models.py and are irrelevant to this prescription.

---

## PX-39 — Establish a real-corpus latency baseline; retire legacy-population numbers

**Verdict:** PARTIALLY_STALE

### Evidence

docs/dev/reviews/2026-07-efficiency/prescriptions.md:50 (PX-39 row: cites split-era p50/p95 69.7s/84.6s as "current", cache-healthy note) — docs/dev/reviews/2026-07-efficiency/verification-log.md:87-90 (F-run-03 WEAKENED: those numbers computed by the verifier at evidence_sha 4196d0c, 2026-07-03) — docs/dev/reviews/2026-07-efficiency/verification-log.md:24-27 (F-run-02 WEAKENED: "0 misses in 30d" also dated to the same pin) — git log shows chore/upgrade-sonnet-5-model merged ad1353a AFTER the pin (8f2c940 "upgrade Sonnet-tier LLM calls 4.6 -> Sonnet 5", 2026-07-05) and fix/compose-frozen-composition merged 0a18876 2026-07-06, both post-dating 4196d0c — analyzer.py:662-663 (SONNET_MODEL = "claude-sonnet-5", was 4.6 at the pin) — analyzer.py:1205-1206 (thinking disabled only on Sonnet path — a real behavioral change vs the 4.6-era numbers) — analyzer.py:1219-1235 (_emit_call_log records "model" alongside "call", so the population split IS distinguishable in logs/llm_calls.jsonl) — blueprints/generation.py:722-754 and :986-1057 (deterministic zero-LLM assemble fires ONLY when `_frozen_composition(context_set)` is non-None; else falls through to the unchanged `generate()`/`generate_streaming()` LLM call) — static/app.js:7198-7202 (only the Compose "Save-and-continue" action posts `freeze:true`; not every corpus-mode Generate necessarily goes through it) — scripts/perf_baseline.py:61-63,74 (groups by whatever `r.get("call")` string appears — new call kinds like draft_summary/draft_gap_fill need no script change, they'll just show up) — docs/dev/perf/PERFORMANCE_HISTORY.md:14-16 (telemetry-source line untouched since the pin: still "1,824 LLM calls ... 2026-05-06 -> 2026-06-02") and :98-100 (explicit standing caveat: "the two-pass split itself has only been measured on synthetic fixtures so far; the real-corpus projection is inference, not yet measurement" — the exact gap PX-39 targets, still open) and :213-226 (documents the precedent pattern "cache broken by split #2 [...] cache reclaimed" — i.e. a model/version swap causing a transient cache reset is already the project's own established narrative pattern) — direct inspection of local logs/llm_calls.jsonl at HEAD (gitignored, not a git cite, but the actual file scripts/perf_baseline.py reads): "generate" call_kind still fires under model="claude-sonnet-5" as late as 2026-07-07T14:08:41Z, i.e. well after the frozen-composition merge — confirming the fallback LLM path is live, not retired; and the 2026-07-06T21:47:33Z model-cutover row shows cache_read_input_tokens=0/cache_creation_input_tokens=5633 on that call — a fresh cache-miss coincident with the Sonnet-5 switch, contradicting a flat "0 misses in 30d" framing if measured today — docs/dev/RELEASE_CHECKLIST.md (commit 56d8c64, "Eval baseline stale vs production model (Sonnet 5)") shows the project already tracks a SIBLING re-baselining obligation for eval-quality after this same model swap, but nothing analogous yet exists for the perf/latency baseline PX-39 is scoped to produce.

### Revised scope

Keep the underlying prescription (a scripts/perf_baseline.py-driven real-corpus latency baseline + PERFORMANCE_HISTORY.md population-label update is still un-landed and still needed — nothing in the four post-pin branches did this work), but land it re-scoped, not as originally written:

1. Do NOT restate 69.7s/84.6s (analyze split-pair p50/p95) as "current" — those were measured under Sonnet 4.6 (pin 4196d0c, 2026-07-03), before chore/upgrade-sonnet-5-model (merged 2026-07-05) and fix/compose-frozen-composition (merged 2026-07-06). Capture a FRESH real-corpus p50/p95 under production Sonnet 5, and label the 4.6 split-era numbers as a third defunct population (pre-split ended 2026-06-01 · split+Sonnet-4.6 2026-06-01→2026-07-05 · split+Sonnet-5 2026-07-05→) in PERFORMANCE_HISTORY.md so future readers don't anchor alarms on either retired era. The "model" field already logged per call (analyzer.py:1225) makes this segmentation mechanical — no code change needed, just a query change.

2. Drop the framing "corpus-mode Generate became deterministic (zero resume-body LLM calls)" as a blanket premise — it's true ONLY on the frozen-composition path (blueprints/generation.py:726-754 / :989-1057, gated on Compose's explicit "Save-and-continue" freeze, static/app.js:7202). Legacy contexts and pre-freeze corpus contexts still call the LLM `generate()`, and the live log confirms `generate` calls still recorded post-merge. The baseline must keep measuring `generate` latency/cache — ideally segmented into "frozen/deterministic" (should show 0 resume-body LLM calls, cover-letter-only) vs "fallback/LLM" (should track the historical curve) — rather than assuming the call kind is retiring uniformly.

3. Revise "record the cache-healthy state (0 misses in 30d)" to instead narrate the Sonnet-5 cutover as an expected one-time cache reset (mirroring the project's own documented "cache broken by split #2 -> reclaimed" precedent, PERFORMANCE_HISTORY.md:219-220) followed by a post-cutover healthy read — not a flat "0 misses" claim, which a straight 30-day window would now falsify.

4. While doing the pass, also fold in the call kinds added since the pin (draft_summary, draft_gap_fill from the frozen-composition Phase 3/4 work, and avatar_answer if not already covered) into the same PERFORMANCE_HISTORY.md table refresh — perf_baseline.py already surfaces them for free.

Everything else about the row (Landing = existing scripts/perf_baseline.py refresh @ v1.1.0-gate, COORDINATE) still stands; this is a scope/premise correction, not a re-scope-from-scratch or a drop.

### Notes

The other three post-pin branches (chore/ruff-format-pin, fix/compose-settle-bg-reload, docs/ux-review-2026-07) don't bear on PX-39 — they're orthogonal to LLM latency telemetry. Only chore/upgrade-sonnet-5-model and fix/compose-frozen-composition are load-bearing for this row's staleness. Note there is already a sibling ledger item (docs/dev/RELEASE_CHECKLIST.md, added by commit 56d8c64) tracking an eval-QUALITY baseline refresh after the same Sonnet-5 swap — worth cross-referencing when this PX-39 branch lands so the two "post-model-swap re-baseline" obligations (quality vs latency) don't drift apart or get conflated.

---

## PX-43 — CI hygiene batch: concurrency group, setup dedup, retention, fail-fast + arm64 decisions

**Verdict:** PARTIALLY_STALE

### Evidence

Prescription row: docs/dev/reviews/2026-07-efficiency/prescriptions.md (PX-43 line, `awk` match) — 5 sub-items: concurrency group, eval-smoke setup dedup, artifact retention-days, fail-fast decision, arm64-QEMU decision. Findings cited: docs/dev/reviews/2026-07-efficiency/findings/d-tests-ci.md:47-94 (F-tci-04/06/07/08/10).

At HEAD (confirmed via `git log --oneline 4196d0c..HEAD -- .github/workflows/` → only one touching commit, e7c8f7c "chore(ruff): pin ruff==0.15.12 + add whole-tree `ruff format --check` CI gate"; docker.yml and release.yml untouched since the pin):

- F-tci-04 (concurrency group) — STILL OPEN. `grep -rn concurrency .github/workflows` → no hits. .github/workflows/ci.yml is now 73 lines (was 67 at the finding's cite); still zero `concurrency:` block anywhere in the tree.
- F-tci-06 (eval-smoke duplicates quality's setup) — STILL OPEN, but the finding's cite (`ci.yml:24-28` vs `:52-56`) is now stale by +6 lines: the ruff-format-pin commit inserted a 6-line `Ruff (format check)` step at ci.yml:38-42 (read at HEAD). The duplicate blocks are now at ci.yml:24-33 (quality: `Set up Python` + `Install package with dev extras`) and ci.yml:58-67 (eval-smoke: identical two steps, job still `needs: quality` at ci.yml:54).
- F-tci-07 (fail-fast:false, no recorded decision) — STILL OPEN, unaffected by the shift: ci.yml:16-17 (`fail-fast: false` in the quality matrix strategy), no adjacent comment stating a rationale.
- F-tci-08 (arm64-QEMU, no recorded trade-off decision) — STILL OPEN, cite unchanged: docker.yml:28-30 (`# arm64 emulation so mac / Apple-Silicon users get a native image too.` + setup-qemu-action@v3 + setup-buildx-action@v3) and docker.yml:53 (`platforms: linux/amd64,linux/arm64`). Verified via `git blame` that this comment predates the review pin (commit 46f6d0e, 2026-07-02) — it states WHY arm64 is built, not a considered decision to accept QEMU's 3-5x build-time cost, so the finding's ask (a recorded trade-off decision) is still unmet.
- F-tci-10 (artifact retention-days) — STILL OPEN, cite unchanged: release.yml:53-56 (`actions/upload-artifact@v4`, no `retention-days:` key); `grep -rn retention-days .github/workflows` → no hits anywhere.

The only CI change since the pin (chore/ruff-format-pin, 2026-07-06) is orthogonal to all 5 PX-43 sub-items — it added a lint-adjacent gate, not a concurrency/setup/retention/fail-fast/arm64 change.

### Revised scope

Build PX-43 exactly as prescribed — none of its 5 sub-items have landed. Only the evidence cites need a small revision before the branch starts, to account for the ruff-format-pin insertion in ci.yml: cite the eval-smoke/quality duplicate-setup blocks as ci.yml:24-33 (quality) vs ci.yml:58-67 (eval-smoke) — not the prescription's stale `:24-28`/`:52-56` — and cite the "no concurrency: anywhere" claim against the current 73-line ci.yml, not `:1-67`. fail-fast (ci.yml:16-17), arm64-QEMU (docker.yml:28-30,53), and retention-days (release.yml:53-56) cites are unchanged and still accurate. No scope drop; this is a cite-freshness note only.

### Notes

Re-verified per-item at HEAD rather than trusting the prescription/finding file's own line numbers, per task instructions. docker.yml and release.yml have had zero commits since the review pin (4196d0c), so their two sub-item cites are untouched. ci.yml has had exactly one intervening commit (chore/ruff-format-pin, unrelated to CI hygiene), which shifts two of the five sub-item cites by +6 lines without changing their substance. None of the other landed branches in this window (fix/compose-frozen-composition, chore/upgrade-sonnet-5-model, fix/compose-settle-bg-reload, docs/ux-review-2026-07) touch .github/workflows/* at all.

---

## PX-45 — Agent-contract trim & accuracy pass (CLAUDE.md catalogs + AGENTS.md corrections)

**Verdict:** PARTIALLY_STALE

### Evidence

Pin 4196d0c..HEAD touched CLAUDE.md 0 times, AGENTS.md 1 time (adb988c, unrelated one-line docx-renderer wording swap at what is now AGENTS.md:103 — verified via `git show adb988c -- AGENTS.md`; `git diff --stat 4196d0c HEAD -- CLAUDE.md AGENTS.md` = only "AGENTS.md | 1 insertion(+), 1 deletion(-)"). Catalog-trim premise (F-adx-06) still holds byte-for-byte: CLAUDE.md skill catalog is CLAUDE.md:101-148 (12 `/sartor:*` entries) and subagent catalog CLAUDE.md:150-190 (9 entries) — read in full at HEAD; `ls commands/` (12 files) and `ls agents/` (9 files) match exactly, so no drift from new commands/agents since the pin. Boundary-list dup (F-adx-09) still holds at the SAME cited lines: `AGENTS.md:50` and `AGENTS.md:166` both still read "hardening.py, parser.py, generator.py, scraper.py, json_resume.py, corpus_to_json_resume.py, pdf_render.py, docx_to_persona_html.py are deterministic" verbatim (grep confirmed). Cache-miss claim (F-run-07) is where the premise breaks: AGENTS.md:113 is unchanged text ("calls that override it (like clarify / clarify_iteration) pay one extra cache-miss ... "). But analyzer.py grew +293/-22 lines since the pin (`git diff --stat 4196d0c HEAD -- analyzer.py`), all from fix/compose-frozen-composition + generation-richness + sonnet-5-upgrade work landing AFTER the pin. Re-enumerating actual override call sites at HEAD (`grep -n "system_prompt=_resolve_system_prompt\|system_prompt=AVATAR_SYSTEM_PROMPT" analyzer.py`) finds 14, not 11/12: analyzer.py:1515 (analyze→EXTRACTION), :1673 (analyze_streaming→EXTRACTION), :1840 (avatar_answer_streaming→AVATAR), :1966 (clarify→CLARIFY, already documented), :2104 (clarify_iteration→CLARIFY_ITERATION, already documented), :2956 (critique_proposal→PROPOSAL_CRITIQUE), :3053 (recommend_bullets→RECOMMEND), :3213 (recommend_summaries→RECOMMEND_SUMMARIES), :3439 (recommend_experience_summaries→RECOMMEND_EXPERIENCE_SUMMARIES), :3658 (recommend_skills→RECOMMEND_SKILLS), :3801 (suggest_skills→SUGGEST_SKILLS), :3892 (promote_clarification_to_bullet→PROMOTE_CLARIFICATION), :3991 (draft_positioning_summary→DRAFT_SUMMARY — NEW, added by fix/compose-frozen-composition Phase 2, ec64594/ad71833), :4114 (draft_gap_fill_bullets→DRAFT_GAP_FILL — NEW, added by fix/compose-frozen-composition Phase 3, ec64594). Grepped AGENTS.md for any mention of these two new prompts/functions — zero hits, confirming the doc gap is now wider than at review time.

### Revised scope

Build PX-45 as scoped for two of its three legs, revise the third: (1) CLAUDE.md catalog trim — compress CLAUDE.md:101-148 (skill catalog) and CLAUDE.md:150-190 (subagent catalog) to a compact pointer list, fold the compliance-witness-only unique facts (cap default 12, log path `docs/governance/compliance-log.md`, FLAG/WATCH/AFFIRM taxonomy, tool-grant-is-enforcement rationale) into `commands/compliance-witness.md` + `agents/compliance-witness.md` frontmatter, keep a one-line fresh-clone/pre-reload fallback note — unchanged from the prescription, same line ranges. (2) AGENTS.md boundary-list dedup — replace the verbatim list at AGENTS.md:166 with a pointer back to AGENTS.md:50 — unchanged, same line numbers. (3) Cache-miss doc fix — REVISE the target: do not word it as "all 11 override sites" (stale — that count and the finding's cited analyzer.py line numbers both predate fix/compose-frozen-composition). At HEAD there are 14 total system_prompt-override call sites in analyzer.py, 12 of them undocumented in AGENTS.md:113 (clarify/clarify_iteration are the only 2 already named). The fix must (a) update AGENTS.md:113's language to state the general pattern (every named `_resolve_system_prompt(...)`/literal-persona override pays the extra system-block cache-miss) rather than hardcoding a stale count, or (b) if an exact count is wanted, state 14 (12 undocumented) and re-derive call-site line numbers fresh via `grep -n "_resolve_system_prompt\|AVATAR_SYSTEM_PROMPT" analyzer.py` at implementation time rather than reusing the finding's now-shifted cites — and explicitly include the two new Phase-2/3 gap-fill prompts (draft_positioning_summary/DRAFT_SUMMARY_SYSTEM_PROMPT, draft_gap_fill_bullets/DRAFT_GAP_FILL_SYSTEM_PROMPT) that didn't exist at the review pin.

### Notes

CLAUDE.local.md (F-adx-08, a different finding not in PX-45's scope) was also unaffected by the post-pin branches — not verified further since out of scope for this task. The AGENTS.md:103 one-line change from adb988c (in the "Document generation" section, `_write_docx()` -> `_write_docx_from_json_resume()`) is cosmetic/unrelated and does not itself stale anything in PX-45.

---

## PX-47 — Config-drift micro-batch

**Verdict:** PARTIALLY_STALE

### Evidence

Row: docs/dev/reviews/2026-07-efficiency/prescriptions.md:55. Finding basis: docs/dev/reviews/2026-07-efficiency/findings/a-process-dx.md:1-4 (evidence_sha: 4196d0c), :36-41 (F-adx-03), :43-48 (F-adx-04), :50-55 (F-adx-05), :79-84 (F-adx-08).

(1) plugin.json bump — NOT DONE. .claude-plugin/plugin.json:4 = "1.0.6" (unchanged since pin; `git show 4196d0c:.claude-plugin/plugin.json` is byte-identical). pyproject.toml:7 = "1.0.7" (also unchanged since pin). CHANGELOG.md:14 `## [Unreleased]` still sits above CHANGELOG.md:1597 `## [1.0.7]`, now with 4 more merged-but-unreleased branches piled on top (fix/compose-frozen-composition, chore/upgrade-sonnet-5-model, chore/ruff-format-pin, fix/compose-settle-bg-reload — none of their diffs touch .claude-plugin/plugin.json, confirmed via `git show <merge> --stat` for 7071f54/0a18876/71b5436).

(2) Model-pin convention — PARTIALLY addressed, not unified. chore/upgrade-sonnet-5-model (merge ad1353a, 2026-07-05, inside the post-pin window) re-pinned all 6 Sonnet subagents: agents/compliance-witness.md:4, agents/git-flow.md:4, agents/headhunter.md:4, agents/prompt-archaeologist.md:4, agents/tune-drafter.md:4, agents/ux-onboarding-designer.md:4 all now read `model: claude-sonnet-5` (was `claude-sonnet-4-6`, per `git show ad1353a --stat`). But the 3 Haiku subagents (agents/eval-judge.md:4, agents/wiki-grounding-auditor.md:4, agents/wiki-scribe.md:4) still pin the dated snapshot `claude-haiku-4-5-20251001`, matching analyzer.py:663 (`HAIKU_MODEL = "claude-haiku-4-5-20251001"`), while Sonnet uses the undated alias `claude-sonnet-5` (analyzer.py:662, `SONNET_MODEL = "claude-sonnet-5"`). The 3-dated-vs-6-undated split F-adx-05 flagged still exists byte-for-byte, just with a newer alias value. New fact not available to the original finding: per the claude-api skill's model catalog, Sonnet 5 has **no dated snapshot ID** — its "Full ID" column is "—" (alias-only), unlike Haiku 4.5's `claude-haiku-4-5-20251001`. So "apply one convention" as originally scoped (implying pin Sonnet to a dated snapshot like Haiku) is not currently achievable on the Anthropic API surface.

(3) CLAUDE.local.md refresh — NOT DONE. Both facts F-adx-08 flagged are still wrong at HEAD: CLAUDE.local.md:12 still reads "/c/Dev/callback" (stale pre-rename path); CLAUDE.local.md:29 still reads "...moves to .claude-plugin/ once Step 4 lands" even though that migration already landed — confirmed `.claude/hooks/` does not exist (`ls` → No such file or directory) and `check-plan-approved.sh` lives at `.claude-plugin/hooks/check-plan-approved.sh` (present, confirmed via `ls .claude-plugin/hooks/`).

(4) settings.local.json prune — DONE, as the task description states. .claude/settings.local.json (gitignored per .gitignore:98, untracked, mtime 2026-07-07 08:31) now has 42 allow-entries with zero "callback" substring matches (grep confirmed), down from the ~63 entries / 9 stale-path hits F-adx-04 cited at the pin.

### Revised scope

Drop sub-item (4) — settings.local.json pruning is already complete (verified: 0 stale-path entries remain at HEAD). Keep and re-scope the other three:
- (1) plugin.json: bump .claude-plugin/plugin.json:4 to match pyproject.toml:7 (currently 1.0.7) — unchanged mechanically, but note the drift has widened since the pin (4 more branches merged into CHANGELOG's [Unreleased] with no version bump anywhere).
- (3) CLAUDE.local.md: fix CLAUDE.local.md:12 (`/c/Dev/callback` → a generic/current path per the no-baked-in-absolute-paths convention) and CLAUDE.local.md:29 (drop the "once Step 4 lands" future-tense framing — the hook has lived at `.claude-plugin/hooks/check-plan-approved.sh` since 0da3739/1cf4cf6).
- (2) Model-pin convention: re-scope from "apply one convention across all 9 subagents" to an explicit decision, since a dated Sonnet-5 snapshot ID does not exist (confirmed against the Anthropic model catalog — only `claude-sonnet-5`, alias-only). Either (a) document in CLAUDE.md/AGENTS.md that the dated-vs-undated split is intentional and provider-imposed (3 Haiku dated because a dated ID exists; 6 Sonnet undated because none does), to revisit if/when Anthropic ships a dated Sonnet-5 snapshot, or (b) flip the 3 Haiku agents to the undated alias `claude-haiku-4-5` for true uniformity — this is a product/risk-tolerance call for the owner, not a mechanical re-pin, and should not be done silently.

### Notes

Sequencing note: chore/upgrade-sonnet-5-model (2026-07-05) landed inside the post-pin window this task lists and already did the "6 subagents re-pinned" work the task description credits it with — confirmed via `git show ad1353a --stat` touching all 6 agents/*.md files. Neither fix/compose-frozen-composition, chore/ruff-format-pin, nor fix/compose-settle-bg-reload touch any of the four PX-47 surfaces (plugin.json, agents/*.md, CLAUDE.local.md is gitignored so untouched by any commit, settings.local.json is gitignored/untracked). The current branch docs/ux-review-2026-07 also does not touch any of the four surfaces (only docs/dev/generation-experience-rearchitecture.md, 13 lines).

---

## PX-51 — Collapse the style.css duplicate cascade layer

**Verdict:** PARTIALLY_STALE

### Evidence

Prescription/finding: docs/dev/reviews/2026-07-efficiency/prescriptions.md:57 (PX-51 row, cites "Merge the ~780-line restyle block into the primary definitions (~20% file shrink)... static/style.css:3019-3789 vs 157,170,183,210,300"); docs/dev/reviews/2026-07-efficiency/findings/b-runtime.md:80-85 (F-run-08).

File-size drift: `git show 4196d0c:static/style.css | wc -l` = 3789 at the pin; `static/style.css` at HEAD = 3848 lines (+59, matching the task's stated frozen-composition delta). `git diff 4196d0c HEAD -- static/style.css` = exactly 2 hunks: +14 at old-line 1033 (new `.wizard-rail-actions`, lands well before the restyle block) and +45 at old-line ~3300 (new `.positioning-draft`/`.gap-fill-lane`/`.compose-loopback-banner`, lands inside the tail region but PAST the true duplicate zone, at what is now style.css:3317-3400ish).

Restyle-block boundary shift: at the pin the marker comment "/* ---- Tab nav (.top-tabs) — restyle on top of existing rules ---- */" sat at old-line 3018 (`.top-tabs` at 3019) running to EOF 3789 (~771 lines). At HEAD the same comment is static/style.css:3032 (`.top-tabs` at 3033), still running to EOF 3848 (~817 lines) — the block moved down but did not shrink; it grew by ~46 lines.

Duplicate-selector census at HEAD (full-file, comment-stripped parse, verified line-accurate): 17 distinct selector-groups appear 2+ times. 14 of them cross the restyle-block boundary and are the ones F-run-08 names/implies: `.cb-main` 157/3066, `.cb-panel` 170/3074, `.panel-header` 183/3088, `.panel-header::after` 194/3110 (self-documented at style.css:3107-3109: "This redesign rule overrides the legacy `.panel-header::after` size above (same specificity, later in the cascade)" — confirms the later-rule-wins footgun is live and in-code-acknowledged), `.panel-body` 210/3114, `.cb-btn`+`:hover`/`:active`/`:disabled` 300,314,318,321 / 3119,3143,3153,3160, `input,select,textarea`(+`:focus`) 233,246/3191,3206, `.top-tabs` 1307/3033, `.top-tab-btn`(+`:hover`) 1314,1329/3042,3057. These all sit within style.css:3032-3212 (~181 lines) — i.e. the true duplicate sub-span ends at the `input:focus` override (style.css:3206-3211), well before EOF.

Everything from style.css:3213 (":focus-visible" / "Wizard step header" comment) through 3848 (~635 lines) — Wizard step header 3216, Summary-variants editor β.6e 3250, Positioning card β.6c 3304, the generation-experience re-architecture additions 3317-3400ish (incl. the +45 new lines from fix/compose-frozen-composition), B.4 per-role intro picker 3401, live preview β.4 3477, analysis section labels 3497-3554, reduced-motion 3554, and the Step-4-Template v1.0 redesign chooser/preview columns 3562-3848 — contains ZERO further matches in the duplicate census; it is unique, non-restated CSS for later-landed features, not part of the cascade-duplication problem.

A separate, smaller duplicate cluster exists entirely outside F-run-08's cited span: `.compose-row.pinned` 1211/2257, `.compose-row.pinned::before` 1219/2263, `.compose-row.excluded` 1227/2271 (between the "Workstream E" ~1211 and "Workstream G+I" ~2257 sections) — same later-rule-wins pattern, not covered by PX-51's current citation.

### Revised scope

Keep the branch (refactor/css-cascade-collapse @ v1.1.0-gate) but re-scope it from "merge the ~780-line tail block into primary defs, ~20% shrink" to a precise selector-level collapse: target only static/style.css:3032-3212 (~181 lines at HEAD) where 14 selector-groups literally restate earlier definitions at ~157-341 and ~1307-1330 (full list in evidence). For each pair, delete the shadowed (non-winning) copy — per cascade order at equal specificity that's the EARLIER (primary-section) declaration, since the later restyle-block copy is what's actually rendering — and relocate the winning rule to the primary location; do not touch style.css:3213-3848, which is unique non-duplicate feature CSS (β.6e/β.6c/B.4/live-preview/analysis-labels/Step-4-redesign, plus the fix/compose-frozen-composition additions) that a literal "collapse the tail block" reading would wrongly delete or reorder. Also fold in, or explicitly flag as a follow-up in the same PX, the smaller pre-existing duplicate trio at style.css:1211-1230 vs 2257-2276 (`.compose-row.pinned`/`::before`/`.excluded`) — same footgun class, currently outside PX-51's citation. Restate the size claim: realistic shrink is bounded by roughly the ~181-line duplicate sub-span minus whichever single copy of each pair is kept — low-single-digit percent of the 3,848-line file, not "~780 lines / ~20%". Keep the UX-tier + screenshot-capture gate as prescribed; nothing about it is stale. None of the other post-pin branches (Sonnet-5 upgrade, ruff-format pin, compose-settle-bg-reload) touch static/style.css, so they don't affect scope beyond the frozen-composition CSS accounted for above.

### Notes

Verified read-only per instructions; no files edited. Used `git show 4196d0c:static/style.css` to reconstruct pin-era line numbers and `git diff 4196d0c HEAD -- static/style.css` to isolate exactly what landed since. The prescription's underlying premise (a real, self-documented later-rule-wins duplicate cascade) is confirmed and, if anything, the true duplicate count (14-17 selector-groups) is larger than the "7+" the finding named — but the LANDING's size/boundary framing ("~780-line block to EOF", "~20% shrink") was already an overstatement at the pin (most of that span was always unrelated feature CSS, not duplicate content) and has only gotten more misleading since, because fix/compose-frozen-composition's +45 new CSS lines landed inside that same "tail to EOF" span without adding any further duplication — reinforcing that the span is not homogeneous duplicate content and shouldn't be scoped as a single block.

---

## PX-55 — Unified quality-gate wrapper script

**Verdict:** PARTIALLY_STALE

### Evidence

Prescription row: docs/dev/reviews/2026-07-efficiency/prescriptions.md:59. Cited finding: docs/dev/reviews/2026-07-efficiency/findings/a-process-dx.md:100-105 (F-adx-11, metric cites AGENTS.md:95 + ci.yml:36,39,42 as "3 separate commands").

Verified at HEAD (6071478, branch chore/px-staleness-reverify):
- No unified script exists: scripts/ has the same 7 utilities as at the review pin 4196d0c (build_bundled_templates.py, build_vector_index.py, capture_screenshots.py, export_corpus_seed.py, perf_baseline.py, smoke_phase_b1.py, vector_before_after_eval.py + __init__.py) — `git diff --stat 4196d0c..HEAD -- scripts/` is empty. Premise holds.
- CI (.github/workflows/ci.yml) gained a 4th gate step on 2026-07-06 (chore/ruff-format-pin, commit e7c8f7c/7071f54): ruff check . (ci.yml:36), ruff format --check . (ci.yml:42, new), mypy . (ci.yml:45, shifted from :39), pytest (ci.yml:48, shifted from :42). `git diff 4196d0c..HEAD -- .github/workflows/ci.yml` shows only this addition.
- AGENTS.md still documents only the 3-command triad, unchanged since the pin: close-out checklist AGENTS.md:95 ("`python -m ruff check .` + `python -m mypy .` + `python -m pytest`") and Testing section AGENTS.md:139-141 (`ruff check .` / `mypy .` / `pytest`, no format-check). `git diff 4196d0c..HEAD -- AGENTS.md` shows zero change to either passage (only an unrelated Document-generation line changed).
- CONTRIBUTING.md is byte-identical since the pin (`git diff 4196d0c..HEAD -- CONTRIBUTING.md` empty): sanity-check block CONTRIBUTING.md:34-36 and PR checklist CONTRIBUTING.md:86-89 list only ruff check/mypy/pytest (plus a separate `pytest -m ux` checklist line at :89), and CONTRIBUTING.md:95 asserts "CI runs `ruff` + `mypy` + `pytest` on every PR" — now factually incomplete, since CI also runs `ruff format --check .`.
- The pre-commit `ruff-changed` hook (.claude-plugin/hooks/ruff-changed.sh:22,32) already runs BOTH `ruff check` and `ruff format --check` on staged files (predates this review, Kit-adoption Phase 1) — so the local commit-time gate and the CI whole-tree gate are now both 2-part-ruff, while the docs a wrapper would centralize still describe 1-part-ruff.
- No `ruff format` reference exists anywhere in AGENTS.md, CLAUDE.md, or CONTRIBUTING.md (grep for "ruff format" across the repo hits only ci.yml, the ruff-changed hook, pyproject.toml, CHANGELOG.md, and dev-design docs — never the three prescribed invocation sites).

### Revised scope

Build the wrapper as prescribed (still needed — no script exists), but widen it from a 3-command to a 4-command gate: `ruff check .` + `ruff format --check .` + `mypy .` + `pytest`, matching what CI (ci.yml:36,42,45,48) and the ruff-changed commit hook already independently enforce. Update the invocation sites to call the wrapper instead of raw commands: AGENTS.md:95 (close-out checklist) and AGENTS.md:139-141 (Testing section), CONTRIBUTING.md:34-36 (sanity-check block), :86-89 (PR checklist — keep `pytest -m ux` as a separate, explicitly-not-CI-covered checklist line since CI has no Chromium install), and :95 (fix the now-stale "CI runs ruff + mypy + pytest" claim to include format-check). Do not fold `pytest -m ux` into the wrapper's default invocation — CI doesn't install Chromium, so a default run must stay parity with plain `pytest` (self-skips UX tier); expose UX-tier as an opt-in flag if desired. Correct the finding's own evidence cite from ci.yml:36,39,42 to ci.yml:36,42,45,48 in any restated finding/register text.

### Notes

Sized-not-to-preempt note (ledger #5's portable core) in the prescription still applies unchanged — no conflicting work landed. This is a genuine widening, not a full re-scope: the wrapper's shape (one scripts/ file, invoked from 3 doc sites + CI) is unaffected; only the command count/cites inside it need updating, plus CONTRIBUTING.md:95 has accrued its own small independent doc-drift since the pin that the fix should sweep up while it's in the file anyway.

---
