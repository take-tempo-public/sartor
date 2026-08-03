# Diagnosis — four `call_kind`s in `analyzer.py` never appear in `logs/llm_calls.jsonl`

> **Status:** hypothesis only. Two of the item's four named kinds are already resolved by
> artifact below (proven-working, not proven-broken); the other two remain open pending the
> committed probes and live click-through this branch will run.
> **Branch:** `fix/never-logged-call-kinds`

---

## Symptom

Work item 22 (`docs/dev/work/items/0022-never-logged-call-kinds.md`, filed 2026-07-28):
`recommend_skill`, `suggest_skill`, `recommend_experience_summary`, and
`draft_surgical_refinement` each have a real `call_kind=` call site in `analyzer.py` and a
real Flask route, but none of the four appear in this project's `logs/llm_calls.jsonl`
(4103+ records at filing time), unlike every other `call_kind` in the file. The item poses
two undistinguished explanations — (a) real routes simply never exercised by the traffic
that populated the log, or (b) something prevents the call from completing/logging when
the routes ARE hit — and says it "needs a live click-through per route to tell which."

---

## Observed

_All commands below were run against this checkout, `python -c "..."` one-liners over
`logs/llm_calls.jsonl` / `db/resume.sqlite` / `output/context_*.json`, 2026-08-02, before
any test in this branch had executed (so none of this branch's own runs could have altered
the counts)._

- **O-1 — per-kind census of the full log.** `logs/llm_calls.jsonl` holds 4403 rows
  across 23 distinct `call` values (`json.loads` over every line, `Counter` on `rec["call"]`).
  Counts for the six kinds in scope: `recommend_skill` = **7**, `suggest_skill` = **2**,
  `recommend_experience_summary` = **0**, `draft_surgical_refinement` = **0**,
  `suggest_skill_from_corpus` = **0**, `promote_clarification_to_bullet` = **0**.

- **O-2 — the 9 non-zero rows are not from this checkout's own traffic; the file is
  append-only and they violate append order.** Walking the file by physical line index and
  comparing each row's `timestamp` field: the first row timestamped `>= 2026-07-28` sits at
  line index 4066 (`ts=2026-07-28T21:08:44.880349+00:00`). The 9 `recommend_skill` /
  `suggest_skill` rows sit at line indexes 4214–4230, each carrying a `2026-07-09` or
  `2026-07-11` timestamp — i.e. they were **appended after** line 4066 despite carrying
  earlier timestamps. Scanning the entire file for `timestamp[n+1] < timestamp[n]` (an
  append-order violation) finds exactly **one**, at line index 4103, where the timestamp
  drops from `2026-07-28T23:09:14.914832+00:00` to `2026-07-06T18:18:24.025872+00:00`. The
  contiguous block starting at line 4103 contains exactly **128 rows** with
  `timestamp < 2026-07-28` (range `2026-07-06T18:18:24` → `2026-07-11T09:12:25`), broken
  down by kind: `draft_summary`=29, `analyze_extraction`=17, `analyze_synthesis`=17,
  `recommend`=16, `clarify`=14, `draft_gap_fill`=13, `recommend_skill`=7, `generate`=4,
  `iterate_clarify`=4, `draft_summary_retry`=3, `suggest_skill`=2,
  `generate_cover_letter`=1, `draft_gap_fill_retry`=1 (sums to 128). This 128-row count and
  date range match closed item 6's own closure narrative verbatim
  (`docs/dev/work/items/0006-*.md` / `BOARD.md` closed-17 entry 6: "Zero new spend, 128
  records copied from owner's E2E clone"). All 9 `recommend_skill`/`suggest_skill` rows are
  fully contained inside this 128-row imported block. Each of the 9 carries
  `status="ok"`, `model="claude-haiku-4-5-20251001"`, `input_tokens` 2243–12506,
  `output_tokens` 130–4075 (values read directly off the rows, not summarized), and
  `prompt_version="2026-07-08.4"` — the same string as `analyzer.py:393`'s current
  `PROMPT_VERSION`.

- **O-3 — the shared telemetry funnel, read directly.** `_parse_or_retry`
  (`analyzer.py:1425`) calls `_call_llm` (`:1451`), which calls `_call_llm_streaming`
  (`:1143`). `_call_llm_streaming`'s `finally:` block is at `:1249`; it calls
  `_emit_call_log` at `:1253` unconditionally, including on the `except Exception:` path at
  `:1246-1248` (which sets `status="error"` then re-raises). `_emit_call_log` is defined at
  `:468-475`; its only failure mode is a caught `OSError` on the file write, logged via
  `logger.warning` at `:474-475` — i.e. the code path to attempt the write was still
  reached. A repo-wide-scoped grep, `grep -c "client.messages.create" analyzer.py`, returns
  `0` — no direct-client-call bypass exists anywhere in the file (this is the exact shape
  item 21 found and fixed for `check_refinement_scope`; item 21's fix removed the last
  instance).

- **O-4 — each of the four call sites, current line numbers (verified by symbol, not by
  the item's filed line numbers, which have drifted).** `recommend_experience_summaries`
  (`def` at `analyzer.py:3414`) emits `call_kind="recommend_experience_summary"` at
  `analyzer.py:3513`, via `_parse_or_retry` at `:3508-3518`. `recommend_skills`
  (`def` at `:3667`) emits `call_kind="recommend_skill"` at `:3734`
  (`_parse_or_retry` `:3729-3739`). `suggest_skills` (`def` at `:3892`) emits
  `call_kind="suggest_skill"` at `:3957` (`_parse_or_retry` `:3952-3962`).
  `draft_surgical_refinement` (`def` at `:4479`) emits `call_kind="draft_surgical_refinement"`
  at `:4544` (`_parse_or_retry` `:4539-4549`). The item's filed `refs` are
  `["analyzer.py:3712", "analyzer.py:3935", "analyzer.py:3491", "analyzer.py:4522"]` —
  each is exactly 22 lines below the corresponding current `call_kind=` line.

- **O-5 — database census, this machine.** `select count(*) from experience_summary_item`
  against `db/resume.sqlite` returns **0**, against `select count(*) from experience` = 28,
  `select count(*) from candidate` = 6, `select count(*) from application` = 64. There is no
  role, on any candidate, with even one `ExperienceSummaryItem` row, let alone the ≥2
  active variants `recommend_experience_summaries` requires before it stops
  auto-picking and calls the LLM (see `## Inferred` below for what that gate does).

- **O-6 — context-file census, this machine.** Across all 126 files matching
  `output/**/context_*.json` (`json.load` each, tally key presence): `approved_composition`
  appears in **0** of 126 files. `composition_overrides` appears in 57;
  `llm_summary_recommendation` in 43; `llm_recommendations` in 24. Neither
  `llm_skill_recommendations` nor `llm_experience_summary_recommendations` appears in any
  of the 126 files either.

- **O-7 — telemetry log path resolution, this checkout.** `analyzer.LOG_PATH.resolve()` and
  `dashboard.routes.LLM_LOG.resolve()`, printed from a live Python process, both equal
  `C:\Dev\sartor\logs\llm_calls.jsonl` — the same file.

- **O-8 — the inventory of `call_kind=` literals is repo-wide, not `analyzer.py`-only.**
  `grep -rn 'call_kind="extract_experiences"'` finds exactly one hit,
  `onboarding/extract_experiences.py:170` — outside `analyzer.py` entirely. Full list of
  `call_kind="..."` literals inside `analyzer.py` (`grep -n 'call_kind="'`): `analyze_extraction`
  (×2, `:1552`, `:1715`), `analyze_synthesis` (×2, `:1571`, `:1740`), `avatar_answer`
  (`:1889`), `clarify` (`:2017`), `iterate_clarify` (`:2157`), `generate` (×2, `:2638`,
  `:2686`), `generate_cover_letter` (`:2839`), `check_refinement_scope` (`:2883`),
  `critique_proposal` (`:3022`), `recommend` (`:3121`), `recommend_summary` (`:3283`),
  `recommend_experience_summary` (`:3513`), `recommend_skill` (`:3734`), `suggest_skill`
  (`:3957`), `suggest_skill_from_corpus` (`:4058`), `promote_clarification_to_bullet`
  (`:4151`), `draft_summary` (`:4262`), `draft_gap_fill` (`:4394`),
  `draft_surgical_refinement` (`:4544`) — 19 literals, 21 call sites (two duplicated: the
  analyze pair each fire from two branches of the same function).

- **O-9 — two call kinds beyond the item's four have zero rows in the log:**
  `suggest_skill_from_corpus` (`analyzer.py:4058`, function `suggest_skills_from_corpus`
  def `:3982`) and `promote_clarification_to_bullet` (`analyzer.py:4151`) — both confirmed
  0 in the O-1 tally.

- **O-10 — the UX stub harness's coverage of these four, read directly.**
  `tests/ux/stubs.py::install_llm_stubs` (`def` at `:402`, body ends `:444`) contains
  `monkeypatch.setattr(analyzer, "recommend_experience_summaries", fake_recommend_experience_summaries)`
  at `:438-440`, `monkeypatch.setattr(analyzer, "recommend_skills", fake_recommend_skills)`
  at `:443`, `monkeypatch.setattr(analyzer, "suggest_skills", fake_suggest_skills)` at
  `:444`. No line in this function references `draft_surgical_refinement`.
  `blueprints/applications.py:2584` catches `anthropic.APIConnectionError`;
  `:2587` catches `LLMResponseError`. No other exception type is caught between
  `_get_client()` (`:433` under `install_llm_stubs`, patched to `lambda: None`) and the
  `draft_surgical_refinement(...)` call at `:2578-2583`.

- **O-11 — the corpus blueprints' `_get_client` binding, read directly.**
  `blueprints/corpus/skills.py:29` and `blueprints/corpus/proposals.py:22` each import
  `_get_client` at module load time. `install_llm_stubs` patches `_get_client` on
  `analysis_bp_mod` (`:417`), `generation_bp_mod` (`:421`), `diagnostics_bp_mod` (`:427`),
  and `applications_bp_mod` (`:433`) — grepping the function body for `corpus` finds no
  matching `monkeypatch.setattr` line.

- **O-12 — the log's existing synthetic-row contamination, measured directly.** Of the 4403
  rows, 3132 have `latency_ms == 0` **and** `input_tokens == 100` **and**
  `output_tokens == 50` (a constant, non-billed shape) **and** `call == "extract_experiences"`
  — 3132/4403 = 71.1% of the entire file. This matches open item 33
  (`docs/dev/work/items/0033-*.md`, status `watching`), filed as
  `tests/test_extract_experiences.py` writing fake rows into the real log; the item's own
  text does not state a magnitude.

- **O-13 — environment at time of this census.** `SARTOR_DEMO` unset in this shell.
  `.api_key` present at repo root (108 bytes, last modified 2026-04-02). Baseline
  `wc -l logs/llm_calls.jsonl` = **4403** lines, recorded here before this branch runs any
  test or gate, so later diffs have a clean starting point.

---

## Falsified

Nothing chased and killed yet — this is the first-pass census. Tier 1/2/3 below are the
falsification experiments; their results will be appended here as they run (a hypothesis
that dies belongs here, not silently dropped).

---

## Inferred

**I-1 — explanation (b) is structurally dead for all four kinds (hypothesis pending Tier
1/2 execution, not yet proven by a passing/failing test).** O-3 shows every one of the four
call sites reaches `_emit_call_log` through the same funnel every other logged call kind
uses, including on exceptions. Nothing SEEN yet proves the funnel executes correctly for
these specific four call sites at runtime — O-3 is a code read, not an execution. Tier 1
(a fake-client capability probe through the real funnel) is the experiment that turns this
from inference into observation.

**I-2 — each of the four short-circuits BEFORE the LLM call under conditions this codebase
has apparently never satisfied (hypothesis, from a code read of the four function bodies,
not yet executed).**
- `recommend_experience_summaries` auto-picks single-variant roles with no LLM call and
  returns early at `analyzer.py:3483-3484` (`if not multi: return {...}`) whenever no role
  has ≥2 active `ExperienceSummaryItem` rows. O-5 shows that condition — zero
  `ExperienceSummaryItem` rows on this machine at all — has held for every row this
  database has ever contained.
- `recommend_skills` returns early at `:3697-3705` for 0 or 1 skills.
- `suggest_skills` returns `{"proposals": []}` at `:3919-3920` when `career_corpus` is
  empty.
- `draft_surgical_refinement` returns a `default` dict (no LLM call) at `:4513-4514`
  whenever the note is blank, OR `approved_composition` is missing/not a `dict`, OR
  `jd_text` is empty. O-6 shows `approved_composition` has never appeared in any context
  file this machine has produced — Compose's freeze step
  (`blueprints/applications.py:1719-1721`) has apparently never executed here.
- All four additionally short-circuit under `_demo_mode_active()` before ever reaching the
  client.

**I-3 — the gap for `recommend_experience_summary` / `draft_surgical_refinement` is most
likely explanation (a) (never exercised in a way that satisfies the gate), not (b) (funnel
broken) — but this is not yet PROVEN.** The gap: what would have to be SEEN to know, rather
than infer, this: (1) a committed probe proving the funnel emits for these two kinds when
their gates ARE satisfied (Tier 1), (2) the same proven through the real Flask route (Tier
2), (3) a live run against a manufactured gate-satisfying state producing a real priced row
(Tier 3). None of the three has run yet.

**I-4 (forward-looking, not yet executed) — O-10's stub gap is the same shape item 21 fixed
for `check_refinement_scope`, but is currently LATENT, not leaking.** Under
`install_llm_stubs`, `_get_client()` returns `None`
(`blueprints/applications.py`, patched at `tests/ux/stubs.py:433`). If any UX test ever
reached `POST /draft-refinement` with a satisfied gate, `draft_surgical_refinement(None,
...)` would call `.messages.stream()` on `None` inside `_call_llm_streaming`
(`analyzer.py:1143`), raising `AttributeError` — not `APIConnectionError` or
`LLMResponseError`, so the route's exception handling (O-10) would not catch it, producing
a 500 and a `status="error"` telemetry row. Whether any current UX test actually reaches
this state is not yet confirmed by execution — inferred from the route/frontend dispatch
read, not observed running.

**I-5 (forward-looking) — O-11's corpus `_get_client` gap is worse in kind: not latent
exception-handling risk but a real, billed API call, if ever exercised under a UX test with
a valid `.api_key` present** (as O-13 confirms this machine has). Not yet confirmed by
execution — no current UX test appears to reach these corpus routes (inferred from a grep
of `tests/ux/`, not exhaustively verified here).

---

## Falsification

**Rival hypotheses this instrument must not hide by being scoped too narrowly to the
item's own theory** ("never scope an instrument to the theory you are testing — it will
confirm your theory by hiding its rivals"):

| | rival | closed by |
|---|---|---|
| b1 | the funnel doesn't actually emit for these call kinds at runtime | Tier 1 |
| b2 | the route never reaches the analyzer function even under the right user action (staging bug, early 4xx, uncaught exception) | Tier 2 |
| b3 | the frontend never issues the request despite the UI state being correct | Tier 3 (live) |
| b4 | the row lands in a different file than expected | **closed by O-7** — both resolution paths land on the same file in this checkout |
| b5 | rows were emitted and later deleted | **not closeable from this evidence** — `logs/` is gitignored (no git history) and has been hand-edited twice already (item 21 removed 10 synthetic rows; item 33's own session removed 9). Recorded as a bound on every conclusion below, not falsified. |
| b6 | the gap is a property of a whole *class* of calls, not specifically these two kinds | Tier 1's repo-wide inventory gate (O-8 already found two more members of this class: `suggest_skill_from_corpus`, `promote_clarification_to_bullet`) |

**The experiments, stated so each can fail, run in order:**

1. **Tier 1 — inventory-complete capability probe** (`tests/test_call_kind_telemetry.py`,
   next commit). An AST walk collects every `call_kind="<literal>"` in the repo (closing
   b6) and asserts it against an explicit expected set. A per-kind probe drives each real
   analyzer entry point that has zero log rows, with a context that satisfies its gate,
   against a fake client — asserting exactly one `_emit_call_log` row lands.
   - **If any probed kind fails to emit a row:** b1 is confirmed LIVE for that kind — this
     IS the defect, stop here, the fix cites this test.
   - **If all probed kinds emit correctly:** b1 is dead for those kinds. Proceed to Tier 2.

2. **Tier 2 — route reachability** (`tests/test_call_kind_route_telemetry.py`, next
   commit), for `recommend_experience_summary` and `draft_surgical_refinement` only (the
   two O-1 shows are genuinely unlogged; O-2 already resolves the other two by artifact).
   Drives the real Flask route with a fake client injected at the
   `blueprints.applications._get_client` seam, staging DB/context state that satisfies each
   gate (real `ExperienceSummaryItem` rows; a real `freeze_approved_composition` output,
   not hand-written).
   - **If either route fails to reach the analyzer / produce a row:** b2 confirmed for that
     kind — route-level defect, filed as a **new** item, not fixed on this branch.
   - **If both succeed:** b2 dead. Proceed to Tier 3.

3. **Tier 3 — live click-through** against a real `python app.py`, manufacturing the
   gate-satisfying state in the UI for both remaining kinds (state that, per O-5/O-6, has
   never existed on this machine before).
   - **If both produce a real priced row in `logs/llm_calls.jsonl`, visible in
     `/_dashboard` with no aggregator change:** explanation (a) is CONFIRMED for both — the
     routes are real and correct, simply never previously exercised in a state that fires
     the call. Item 22 closes with this resolution, `analyzer.py` unchanged.
   - **If the UI fires the request but no row appears:** b4/b5 — **stop, do not attempt a
     fix**, widen the instrument (check both log path resolutions live, check for a
     write-time exception) and report rather than guess.
   - **If the UI state cannot be made to issue the request at all despite a satisfied
     backend gate:** b3 confirmed — a real frontend defect, filed as a **new** item.

Each outcome will be appended to this section, dated, as it actually runs — this is the
pre-registration, not the result.

---

## The fix

_Not written yet — pending the Falsification experiments above. Expected outcome per the
pre-branch evidence: no `analyzer.py` change; `tests/ux/stubs.py` gains a
`draft_surgical_refinement` stub (I-4, prophylactic — see `## Acceptance bar`)._

---

## Acceptance bar

- Tier 1's per-kind probes and inventory gate pass, first attempt, no reruns.
- Tier 2's two route-level probes pass, first attempt, no reruns.
- Tier 3 produces two real priced rows (`recommend_experience_summary`,
  `draft_surgical_refinement`) in `logs/llm_calls.jsonl`, each with non-zero
  `input_tokens`/`output_tokens`/`latency_ms` and a `model` matching a
  `hardening.MODEL_PRICING` key, both visible in `/_dashboard`'s cost-by-call-kind and
  reliability tables with **no aggregator code change** (mirrors item 21's bar).
- `wc -l logs/llm_calls.jsonl` before vs. after every test run in this branch (Tier 1 and
  Tier 2 specifically) shows **zero** added rows — any test driving the real
  `_call_llm_streaming` redirects both `analyzer._emit_call_log` and `analyzer.LOG_PATH` via
  an autouse fixture (this exact pollution has happened twice already in this repo: item 21,
  item 33).
- `python -m scripts.gate` green, zero reruns (a rerun-masked PASS is not evidence — C-7).
- Item 22's filing corrected: stale `refs` refreshed to current line numbers (O-4), and its
  four-kind list narrowed to the two actually-unlogged kinds, with a note on the two
  resolved-by-artifact kinds and the two additional unlisted kinds (O-9).
