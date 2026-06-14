# Grounding / hallucination metric — design note

> **Purpose:** so a follow-up agent inherits the framing instead of re-deriving
> it cold. Captures *what* we're measuring, *why* it's tractable here, the
> detector ladder, the calibration dependency (and why it's currently blocked),
> the hard parts, and the deliberately-staged A-now / B-later sequencing.
> **Status:** design approved + re-sequenced by the user 2026-06-05 (insert the
> deterministic slice ahead of the v1.0.5 dashboard/tuning UI — see
> [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4).
> **Authoritative for:** the metric's *design intent* and the A/B split. The
> branch sequence lives in `RELEASE_ARC.md`; the deferred follow-up lives in
> [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md).

---

## The reframe — this is attribution, not open-world factuality

"Hallucination" in callback. has a narrow, *checkable* meaning, unlike general
LLM factuality. It is **faithfulness/attribution**: does each claim in the
generated résumé have support in the candidate's ground-truth corpus? We own
the reference set, so every claim is verifiable against a **closed** source —
this is what makes a real metric achievable.

**The metric's source set is the dynamic union**, not just the original résumé:
`original primary résumé + supplemental résumés + clarification answers`.
[`hardening.compute_iteration_signals`](../../hardening.py) already assembles exactly this
three-source union. `AGENTS.md` ("LLM prompts") notes the generation grounding check **also
widens** to accept first-person typed preview edits — but that widening is **prompt-side**:
typed edits are ground truth for the *model*, not a member of the metric's deterministic
source union. **A metric scored against only the original résumé will over-report** — it
will flag legitimately-clarified facts as fabrication. Score against the union, recomputed
per iteration.

## Hallucination is not one thing — split by class

A flat "rate" hides that these differ in severity *and* detectability. Report
them separately:

| Class | Example | Severity | Detection |
|---|---|---|---|
| 1. Fabricated specifics | invented number / % / $ / date / duration / team-size not in source | **highest** (SYSTEM_PROMPT: "most damaging" — verifiable in any interview) | **deterministic** (cheapest) |
| 2. Fabricated entities | company / title / tool / cert not in source | high | deterministic |
| 3. Unsupported qualitative claims | "led / architected / solely owned" overstating the real role | medium | semantic (NLI) |
| 4. Contradiction | source "contributed to" → output "solely owned" | high (should be ~0) | semantic (NLI contradiction) |

## The detector ladder (cheap → expensive), matching the existing architecture

- **L0 — deterministic typed-specifics check (hot-path-safe).** Extract every
  number / % / $ / date / duration / proper-noun from the output; check
  membership in the source union with **tolerance** (normalize, don't exact-match:
  `~30 → 30+` OK, `~30 → 100+` not; `k8s ≡ Kubernetes`). Catches classes 1+2 with
  near-zero false *negatives* on genuinely-novel specifics. **No LLM, no model
  weights** → safe to run in the hot path and to log per generate call. It is a
  sharper successor to today's [`compute_grounding_overlap`](../../hardening.py)
  `missing_samples` (lossy n-gram overlap). **This is the v1.0.5 branch (A).**
- **L1 — NLI entailment per bullet** vs. the source union. Catches classes 3+4
  that L0 can't see. **Already built**, eval-only:
  [`evals/grounding_signals.py`](../../evals/grounding_signals.py)
  (`nli_entailment_score`, `nli_contradiction_flag`, DeBERTa-v3). Model weight +
  latency → stays out of the hot path.
- **L2 — claim-level verification** (highest fidelity). `minicheck_grounding_score`
  (already in `grounding_signals.py`) + an optional temp-0 Haiku
  "is this claim supported by [source]: yes/partial/no" judge, ideally with
  **claim decomposition** (split each bullet into atomic claims, verify each —
  FActScore-style; tractable because bullets are short). Eval-only.

**Unit of measurement:** per-bullet (optionally per-claim later). It's how
recruiters read, how the L1/L2 scorers already work, and it localizes the failure
for the user / tuner.

**Hot-path discipline (RELEASE_ARC Key Decision #4):** only **L0** (deterministic)
may touch the hot path. L1/L2 run at eval time on the anchor / real suites. This
is exactly why the deterministic slice is the part that ships first and the part
that can become a *per-call* production signal.

## What to report

- **Headline (deterministic, hot-path-safe):** *fabricated-specifics rate* =
  fraction of generated numeric/entity tokens not grounded in source, **severity-
  weighted** (a fake number counts more than a soft verb).
- **Eval-time:** *unsupported-claim rate* (NLI < threshold), *contradiction count*
  (alarm if > 0), and a composite **groundedness score** per generation, tracked
  over `PROMPT_VERSION` so it plugs into the dashboard's existing
  score-over-time-by-prompt-version chart.

## Calibration — and why it is currently blocked

A detector you don't trust is worse than none. The validation set is the Phase 3
**`annotations.json`** human verdicts (supported / fabricated / should-omit /
honest-rewrite) on *real* generated bullets — measure each detector's
precision/recall against those labels (this is literally a v1.0.4 tag criterion:
"annotations validate the automated scorers").

**Blocker (verified 2026-06-05):** there are **no labels yet**.
`evals/fixtures/real/` is empty (`.gitkeep` only); there is no `bootstrap.json` /
`annotations.json` / seed anywhere. The v1.0.4 loop shipped the *machinery*
(`evals/annotation.py`, `evals/bootstrap.py`, `evals/seed_import.py`,
`evals/grounding_signals.py`) but its **live run was never executed** (see
[`PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) cover-letter-tuning entry). *(As of
2026-06-07 that machinery is also driveable from the browser — the `/_dashboard`
console's bootstrap → annotate → "Score grounding" loop — so producing the labels
is now a click-through, not a CLI chore; but until someone actually runs it the
labels still don't exist.)* So:

- **L0 needs no labels to be useful** — a novel number/entity absent from the
  source union is almost certainly fabricated; high precision on the highest-
  severity class with zero model cost. Ship it uncalibrated now; calibration only
  tunes the tolerance bands later.
- **L1/L2 need labels to be *trusted*.** They wait for the annotation corpus.

## Sequencing — A now, B pre-v1.1.0 (user-approved 2026-06-05)

The instinct "metric before we redesign the dashboard + build the tuning
interface" is correct: don't design panels around — or steer a grounding-gated
tuning loop by — a metric you haven't defined. But the binding constraint is the
**missing labels**, not the metric code. So we split:

- **A (now, this v1.0.5 insert — `eval/grounding-metric-l0`):** build L0 (the
  deterministic, label-free, hot-path-safe fabricated-specifics rate) and
  aggregate the *existing* L1/L2 eval-time signals into one reportable
  groundedness signal. This gives the dashboard a **real metric contract** to be
  designed around. Deterministic → lives in `hardening.py` + `evals/`; **no LLM,
  no `PROMPT_VERSION` bump, no new dependency.**
- **B (deferred, pre-v1.1.0 — tracked in PRODUCT_SHAPE §10):** run the loop
  end-to-end on the real corpus (seed → bootstrap → annotate → grounding-score) to
  produce labels, **calibrate** the L0 tolerances + L1/L2 thresholds against them,
  then update the eval suite + the tuning interface to consume the calibrated metric.
  This is the trustworthy cross-class rate. It carries LLM cost + annotation labor,
  which is why it is staged, not done inline. **Note (2026-06-07):** the
  label-*producing* path is no longer CLI-only — the v1.0.5 diagnostics-console
  interactive-completion arc made the whole loop **browser-driven** (`/_dashboard`:
  bootstrap → annotate → "Score grounding" backfill → run eval → A/B; see
  [`evals/README.md`](../../evals/README.md) "The in-browser tuning console"). That
  lowers the friction to *generating* the annotation labels; it does **not** itself
  perform the calibration — measuring each detector's precision/recall against the
  labels is still the open B work.

## The hard parts (don't relitigate these from scratch)

- **Paraphrase / implication is the precision killer.** Source "managed a small
  team" → output "led a 4-person team": deterministic L0 flags "4" as fabricated
  (false positive); the SYSTEM_PROMPT *allows* clear implication; NLI might
  accept it. This tension is unavoidable — it's the reason you calibrate against
  human labels rather than trusting raw detector output. For L0-now, prefer
  **flagging for review over hard-failing**, and keep the tolerance conservative.
- **Normalization / tolerance bands.** `~30 → 30+` OK; `~30 → 100+` not. Numeric
  membership needs ranges, not equality.
- **Entity aliasing.** `k8s ≡ Kubernetes`, `JS ≡ JavaScript`. Needs a
  normalization / synonym layer or L0 false-positives constantly.
- **Decomposition can itself hallucinate.** An LLM claim-splitter (L2) is
  non-deterministic — pin it temp-0 and give it its own small eval, or the
  hallucination metric hallucinates its own claims.

## Testing the metric

- **L0 is deterministic → unit-test it directly**, mirroring the existing
  [`tests/test_hardening.py`](../../tests/test_hardening.py) tests for
  `compute_grounding_overlap` (exact source match → 0 fabrication; novel number
  absent from source → flagged; `~30 → 30+` within tolerance → not flagged;
  `~30 → 100+` → flagged; `k8s` vs `Kubernetes` aliasing → not flagged). **No
  LLM, no Chromium** — these run in the default `pytest`.
- **L1/L2** already have [`tests/test_grounding_signals.py`](../../tests/test_grounding_signals.py).
  Their *calibration* (B) is validated against `annotations.json`, not unit tests.
- The dashboard surfacing (later branch) reuses the `tests/ux/` harness; note that
  branch's UX sentinel is now **unconditional** (see the paged.js note in
  `RELEASE_CHECKLIST.md` and `tests/ux/conftest.py`) — any console error fails.

## Already-built substrate (reuse, don't reinvent)

| Piece | Where | Role |
|---|---|---|
| `compute_grounding_overlap` / `missing_samples` | `hardening.py:511` | proto-L0 (lossy n-gram); sharpen into the typed extractor |
| `compute_iteration_signals` | `hardening.py:739` | already assembles the dynamic source union |
| `_post_generation_metrics` | `evals/runner.py:198` | where eval-time metrics ride along |
| NLI + MiniCheck scorers | `evals/grounding_signals.py` | L1/L2, eval-only, flag-gated (`--grounding-signals`) |
| `annotations.json` contract | `evals/annotation.py` | the calibration labels (not yet populated) |
| score-over-time-by-prompt-version | `/_dashboard` | the trend surface a groundedness score plugs into |
