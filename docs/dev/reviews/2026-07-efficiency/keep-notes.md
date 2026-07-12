---
status: review-artifact
evidence_sha: 4196d0c
graduation: none (affirm-and-protect ledger; no code/prompt/config change)
---

# Keep notes — PX-56 affirm-and-protect ledger

> **Purpose.** PX-56's Landing is `docs/efficiency-keep-notes` — a do-not-regress record
> for four BOOST/KEEP findings from the 2026-07 efficiency review
> ([`prescriptions.md`](prescriptions.md) PX-56 row: F-run-04 BOOST, F-run-05 KEEP,
> F-tci-11 KEEP, F-doc-10 conditional KEEP). These are not action items — they are
> **things already working that a future change could accidentally undo**. Read before
> "fixing" any of the four surfaces below; the fix is very likely to be "don't."

---

## 1. Haiku call kinds' zero-error record (F-run-04, BOOST)

**What's working:** across 2,118 Haiku calls, **0 errors**. All 5 error rows in the
telemetry sample are Sonnet (3 `analyze`, 2 `generate`). Sonnet also carries 91.3% of
spend ($32.08 of $35.14; Haiku is $2.51 / 7.1%).

**Evidence:** `logs/llm_calls.jsonl` cost-by-model aggregation; error rows at lines 79,
241, 242, 375, 920 (all Sonnet).

**Do not regress by:** routing more structured-selection work to Sonnet "to be safe" —
the data says the opposite. **Consider instead:** when a new call kind is a bounded,
structured-selection task (picking among existing options, not synthesizing new prose —
the same shape as `recommend_bullets` / `clarify` / `critique_proposal`), Haiku is the
evidence-backed default, not a downgrade. This is an operational observation, not a
mandate — a call that needs open-ended synthesis still belongs on Sonnet.

---

## 2. Eval anchoring on old prompt versions is deliberate (F-run-05, KEEP)

**What's working:** 28.3% of all logged calls (835/2,955) still carry the
`2026-05-24.4` prompt-version baseline; the latest (`2026-07-01.1`) is only 1.6% of
traffic. This is **not** telemetry rot — the eval suite's `baseline_v1.json` and
`TUNING_LOG.md` intentionally anchor scores to a fixed prompt version so score deltas
are attributable to a specific prompt change, not to whichever version happened to be
live when a synthetic run fired.

**Evidence:** `logs/llm_calls.jsonl` `Counter(prompt_version)`;
`docs/dev/perf/PERFORMANCE_HISTORY.md:14-16`.

**Do not regress by:** "cleaning up" old `prompt_version` strings out of the baseline or
treating a low-percentage current-version share as a bug to fix by force-bumping
telemetry. **Watch for the real risk this masks:** a stale baseline can also hide a
genuinely dead code path (a call kind nobody exercises anymore). If a `prompt_version`
cluster stops appearing in `logs/llm_calls.jsonl` entirely across a release, that's worth
checking — but a *minority* share, as seen here, is the eval harness working as
designed.

---

## 3. Linux-only CI is a decision with a revisit trigger (F-tci-11, KEEP)

**What's working:** `.github/workflows/ci.yml:15` runs `ubuntu-latest` only, despite
Windows being the primary dev machine (per `CLAUDE.local.md`). Windows-specific issues
(cp1252 console encoding, path separators — e.g. the EV-3 `UnicodeEncodeError`) have so
far been caught locally, not in CI, and a Windows runner costs 2-3x a Linux one.

**Evidence:** `.github/workflows/ci.yml:15` (`runs-on: ubuntu-latest`);
`docs/dev/RELEASE_CHECKLIST.md` window-8.5 EV-3 note.

**Do not regress by:** silently letting this drift into "we just never got around to
Windows CI" — it is a **recorded decision**, not an oversight. **Revisit trigger:**
public user feedback surfacing a real Windows-only bug CI would have caught pre-public
promotion (repo → public, tracked separately in the RELEASE_CHECKLIST ledger) is the
signal to add a Windows job, not a recurring "should we" debate.

---

## 4. Charter D-5's re-affirmation is owed after the 8.6 wiki ingest (F-doc-10, conditional KEEP)

**What's working:** the D-5 cite-don't-restate discipline is holding under real drift
pressure — the 2026-06-16 self-documenting-loop run touched 47 changed sources and
produced exactly 1 affected wiki page, which is why 119 commits of ingest lag did not
corrupt the wiki's contract layer.

**Evidence:** `docs/wiki/log.md:322-331`; `docs/wiki/SCHEMA.md:33-48`;
`docs/wiki/pages/deterministic-llm-boundary.md:18-24` (exemplar page demonstrating the
discipline in practice).

**Status update (this branch, 2026-07-11):** the scheduled 8.6 wiki catch-up ingest this
finding's KEEP was conditioned on has **landed**, in two steps — per
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md) (`docs/wiki-v109-refresh`,
2026-07-10), `.last_ingest_sha` advanced `3561657` → `e785e539` and `/wiki-lint` passed
clean; a subsequent v1.0.9 pre-merge refresh (commit `409d327`) advanced it again
`e785e539` → `c8899fd`, the value at `docs/wiki/.last_ingest_sha` as of this writing.
**The re-affirmation this row calls for is therefore now due, not merely scheduled** —
a follow-up `/compliance-witness` or `/wiki-audit` pass should confirm D-5 discipline
still holds post-ingest (same one-page-per-many-sources ratio, no bare-line cites
reintroduced) before this KEEP is re-closed as re-affirmed.

**Do not regress by:** assuming a large ingest pass is automatically safe for D-5
because a *small* one was. The discipline held at 47:1; a 119-commit catch-up ingest is
a much larger single pass and deserves its own confirmation, not an inherited pass grade.

---

## Notes

- This file is a durable record, not a PX action row — it closes the PX-56 line item in
  [`prescriptions.md`](prescriptions.md) by existing, not by scheduling further work.
- Companion: [`px-staleness-reverify-2026-07-07.md`](px-staleness-reverify-2026-07-07.md)
  re-verified the 7 possibly-stale PX rows at HEAD `6071478`; this file was not itself
  re-verified line-by-line at a later HEAD beyond the item-4 status update above, since
  the underlying observations (Haiku error rate, prompt-version mix, CI platform choice)
  are historical telemetry/decision facts, not live code state.
