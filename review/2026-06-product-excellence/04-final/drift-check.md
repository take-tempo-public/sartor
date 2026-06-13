---
status: review-artifact
evidence_sha: c6e0437
drift_checked_against: a0a1cb2
graduation: none (drift reconciliation; folds into the final assessment)
---

# Drift check -- findings register vs current main

> Reconciles the 81 pinned findings (evidence at c6e0437) against current
> main (a0a1cb2, 15 commits ahead: Sprint 6.4 corpus-first IA + Sprint 6.6
> B.4/B.5 corpus-item work + the WS-4b wiki code cold-ingest). Method: a
> finding whose evidence path is NOT in the c6e0437..main name-only diff is
> STILL-VALID by construction (counted, not belabored). Every finding whose
> evidence path DID change was re-read at `git show main:<path>` and
> reclassified with evidence at a0a1cb2. Severity language follows the SIGNED
> charter (C-0: mechanism/effort, no LLM-behavior absolutes, no marketing).

---

## Summary

73 still-valid (by construction) / 8 changed -> breakdown of the 8:
4 STILL-VALID (the change touched the evidence file but not the finding's
claim), 1 PARTLY-ADDRESSED (F-vision-06), 3 SUPERSEDED (the WS-4b wiki
findings whose condition the cold-ingest dissolved: F-docs-08 and F-docs-10;
F-docs-07 / F-docs-09 / F-gov-06 were brushed but stay STILL-VALID,
strengthened). No P0/P1 FIX finding was resolved by the 15 commits -- the
actionable spine (egress test, CDN vendoring, blueprint boundary gate, the
SLA softening, the doc-claim corrections) is untouched. The 15 commits are
corpus-item feature work + the wiki ingest, not the PX remediation set; no
PX-01..09 item has landed.

The headline drift: the WS-4b ingest advanced the sentinel honestly and
caught a different class of drift (stale symbols, route count, diagram
labels) -- but it did NOT independently surface the egress/CDN/scraper drift
the review found; it documented those surfaces neutrally (see the
wiki-ingest-impact paragraph).

---

## Changed findings (evidence path in the c6e0437..main diff)

| F-id | Status | What changed on main + evidence at a0a1cb2 |
|---|---|---|
| F-vision-03 | STILL-VALID | Evidence files `db/models.py` + `docs/PRODUCT_SHAPE.md` both changed, but neither touched this finding. The outcome funnel (status/sent_at/outcome_at; status IN draft/submitted/interview/rejected/withdrawn) was already shipped at the pin and is unchanged at `db/models.py:652-667`; the diff added corpus tables elsewhere. PRODUCT_SHAPE still carries the contradicting "(Future v2) Mark sent + outcome" at :133, :392-393, :453-455, :572-578 -- none in the PRODUCT_SHAPE diff. The shipped-code-vs-"(Future v2)"-docs contradiction persists. |
| F-vision-06 | PARTLY-ADDRESSED | The disposition-drift half is resolved in `docs/PRODUCT_SHAPE.md`: the Skill row is now "exists (B.5, v1.0.6)", the SkillGroupItem/"clusters" framing explicitly dropped (:8-19, :28-41). BUT the finding's cited evidence is `vision.md:222-229` (the Learnings section), and `vision.md` is UNCHANGED in the diff -- vision.md Learnings still drift from the now-updated PRODUCT_SHAPE disposition. The doc-to-doc gap is narrower but still open. |
| F-eval-02 | STILL-VALID | `evals/TUNING_LOG.md` changed (added a 2026-06-13 B.5 corpus-mode entry), but `evals/fixtures/real/` is still .gitkeep-only and the new entry is synthetic/legacy-mode work, not real-loop calibration. L1/L2 remain uncalibrated; the entry corroborates the gap ("no paid smoke run ... synthetic suite is legacy-mode ... byte-identical"). |
| F-docs-07 | STILL-VALID (KEEP, strengthened) | `docs/wiki/SCHEMA.md` changed -- ADDED a machine-parseable Audience-tag convention; the cold-ingest applied the one-grounding-rule + [synthesis] tagging + bidirectional backlinks across all 24 pages. The KEEP claim ("grounding rule + cite/backlink/synthesis convention genuinely practiced") is reaffirmed at larger scale, not weakened. |
| F-docs-08 | SUPERSEDED | The KEEP premise -- `.last_ingest_sha` left at the sentinel rather than falsely advanced -- no longer holds: the WS-4b code pass ran and honestly advanced the sentinel -> 9816b45851acf5aac3e4249e14bdd8664a8fab29 (real 40-char HEAD SHA; `log.md` records "this is the code pass"). The honesty discipline held through the transition; the specific sentinel-state described is gone. |
| F-docs-09 | STILL-VALID (KEEP) | `docs/wiki/SCHEMA.md` changed but only added the Audience-tag section (which references the D5 access-plane "referenced, not restated"); the @import safety-condition record (SCHEMA D5 + `governance-extraction.md:27-52`) is intact. KEEP affirmation unaffected. |
| F-docs-10 | SUPERSEDED | The WATCH premise -- "WS-4b code cold-ingest untested; grounding at module scale + rot-detection never fired" -- is resolved by execution. The cold pass RAN (16 new code pages, path:line-grounded, per-page adversarial /wiki-audit), the grounding rule held at module scale, and rot/drift detection DID fire: caught `app.py` route count 75->92, a 2nd raw-LLM call site (check_refinement_scope bypassing _call_llm), the _emit_call_log JSON key, CandidateInfo.linkedin_url/website_url (not links), and folded two diagram drifts (pipeline.mmd "INTERVIEW"->"CLARIFYING QUESTIONS", data-flow.mmd cover-letter node). Gate green (pytest 1169/1169, docs-only). |
| F-gov-06 | STILL-VALID (KEEP, demonstrated) | `docs/wiki/.last_ingest_sha` + `log.md` changed: the witness-class freshness reminder + honest sentinel -- the "working amendment-ceremony precedent" the finding affirms -- is now demonstrated end-to-end (sentinel honestly retired -> real SHA; log.md notes the commit-time freshness reminder "goes live"). KEEP holds, strengthened by a completed cycle. |

**All other 73 findings: STILL-VALID by construction** -- their evidence
paths (`vision.md`, `SECURITY.md`, `README.md`, `CODE_OF_CONDUCT.md`,
`llms.txt`, `.github/workflows/ci.yml`, `pyproject.toml`, `LICENSE`,
`static/axe.min.js`, `dashboard/templates/dashboard.html`, `scraper.py`,
`evals/runner.py`, `docs/dev/memory-architecture.md`,
`docs/governance/charter.md`, `system-model.md`, the 0007 outcome migration,
etc.) are NOT in the c6e0437..main change set. Spot-checks confirm the
substance survives where the change set brushed a file without touching the
finding: F-vision-05/F-sec-03/F-docs-02 (Chart.js still cdn.jsdelivr.net at
`dashboard/templates/dashboard.html:15`, file unchanged); F-docs-04 (scraper
still no runtime caller -- only a `hardening.py:1012` comment references it);
F-expa11y-02 (`_get_client()` at `app.py:87-95` still passes an empty key
with no AuthenticationError guard); F-sec-02 (app.run(debug=..., port=5000)
at `app.py:8193`, still no host=); F-eval-01 (`_dropoffPick` at
`static/app.js:5474`, still no bullet-count instrumentation); F-eval-09 (hot
path still keyword_overlap, not compute_fabricated_specifics); F-arch-05 (the
two new corpus prompts recommend_skills/suggest_skills were added correctly
INSIDE `analyzer.py`, PROMPT_VERSION bumped 2026-06-11.1 -> 2026-06-12.2 in
the same commit -- the boundary held).

---

## PX-landed list

**None of PX-01..PX-09 has landed at a0a1cb2.** Verified directly:

- **PX-01 (vendor Chart.js, drop the CDN):** NOT landed. `dashboard/templates/dashboard.html:15` still loads chart.js@4.4.0 from cdn.jsdelivr.net (SRI was already present at the pin; still a runtime third-party CDN fetch). File unchanged in the diff. -> F-vision-05, F-sec-03, F-docs-02 STILL-VALID.
- **PX-02 (re-wire / retire the dead scraper):** NOT landed. `scraper.py` unchanged; fetch_url_content/fetch_profile_content still have no runtime caller (only a comment in `hardening.py:1012`). The cold-ingest even re-documents the scraper as live. -> F-docs-04 STILL-VALID.
- **PX-03 (reconcile egress enumeration to two classes; drop the phantom JD-URL fetch):** NOT landed. `SECURITY.md`, `README.md`, `vision.md` unchanged. -> F-sec-04, F-docs-01 STILL-VALID.
- **PX-09 (no-invention doc wording -- soften the C-0-barred absolutes):** NOT landed. `vision.md:50`, `llms.txt:4` unchanged; `overview.md` changed only its Audience tag (the "without inventing anything" / "may not fabricate" framing at :19/:26-27 is byte-unchanged). -> F-vision-02, F-docs-03 STILL-VALID.

**Sprint 6.4 / 6.6 items the question flags (these DID land -- as product work, not PX remediations):**

- **F-expa11y-10 corpus-first IA -- LANDED (the IA half).** `templates/index.html:46-58` ships the Sprint-6.4 tab order (Career corpus = tab 1, corpus-first button order, smart `_landingTab()` landing). The WATCH ("corpus-first IA unbuilt at the pin") is resolved for the IA; the two M-2 fresh-clone first-run bars remain a v1.1.0 item. Feature delivery, not a PX-id.
- **F-vision-06 corpus ladder -- PARTLY landed in PRODUCT_SHAPE** (Skill shipped B.5/v1.0.6; clusters dropped), but `vision.md` Learnings still drift (see table).
- **F-vision-03 outcome funnel -- already shipped at the pin** (status/sent_at/outcome_at); docs still mislabel it "(Future v2)". No change at main.

The 15 commits are corpus-item features (B.4 ExperienceSummaryItem, B.5
Skill-as-Corpus-Item), the corpus-first landing IA, and the WS-4b wiki
cold-ingest -- none a PX remediation. The PX spine for v1.0.6 (CDN vendor +
egress-doc corrections), v1.0.7 (SLA softening, no-invention wording, egress
test), and v1.0.8 (blueprint boundary gate) remains entirely open.

---

## Wiki-ingest impact (WS-4b cold pass, now merged at a0a1cb2)

The WS-4b code cold-ingest ran for real between the pin and main, and it
materially changes the standing of two of the four wiki findings the charter
flagged for this workstream -- while leaving the egress/CDN/scraper drift the
product review found untouched.

**F-docs-08 (sentinel honesty): SUPERSEDED.** The finding praised the
sentinel being left unadvanced rather than falsely bumped. The code pass has
now honestly advanced it: `docs/wiki/.last_ingest_sha` went from the
"# no code ingest yet ..." sentinel to the real 40-char HEAD SHA
9816b45851acf5aac3e4249e14bdd8664a8fab29, with `log.md` recording the
rationale ("this is the code pass, so the checkpoint now carries a real SHA
and the commit-time freshness reminder goes live"). The honesty discipline
held through the transition; the state the finding described no longer exists.

**F-docs-10 (WS-4b untested at scale; rot-detection never fired):
SUPERSEDED.** The cold pass exercised exactly what the WATCH said was
unproven. Sixteen new pages/ were authored one-agent-per-page and re-verified
by a different adversarial grounding auditor per page; every code claim is
path:line-grounded per SCHEMA.md's one grounding rule; the gate stayed green
(pytest 1169/1169, docs-only). Critically, the rot/drift detection that had
never fired, fired -- it caught the `app.py` @app.route count drifting 75->92,
a second raw-LLM call site (check_refinement_scope) that bypasses the
_call_llm funnel, a wrong telemetry JSON key (call vs call_kind), the
CandidateInfo linkedin_url/website_url symbols (architecture-doc said links),
and a stale scraper entrypoint name (scrape_url() vs the real
fetch_url_content/fetch_profile_content), and folded two Mermaid diagram
drifts into pipeline.mmd + data-flow.mmd. So the grounding rule and rot
detection both held at module scale -- the finding's open risk is discharged
by evidence.

**Did the ingest independently surface the egress/CDN/scraper drift the
review found? No.** This is the load-bearing reconciliation point. The
cold-ingest read `scraper.py` and `dashboard/` and documented both surfaces
-- but neutrally, as implementation facts, not as charter/claim
contradictions:

- It records `scraper.py` as a live module ("Best-effort URL / portfolio
  text fetch") in `code-module-map.md:68`, and flagged only a symbol-name
  drift (scrape_url() vs the real symbols) -- it did NOT note that the
  scraper is dead code with no runtime caller, the substance of F-docs-04 /
  PX-02. If anything the page reinforces the "docs describe a live scrape"
  problem the review found.
- It records "Chart.js from CDN, lazy-init on open" in
  `diagnostics-console.md:67` as a benign detail -- it did NOT flag the
  contradiction with the "no external CDN at runtime" / C-2 no-egress claims
  in SECURITY.md / vision.md (F-vision-05 / F-sec-03 / F-docs-02 / PX-01).
- It says nothing reconciling the SECURITY.md three-class vs README/vision
  two-class egress enumeration (F-sec-04 / F-docs-01 / PX-03).

The ingest's rot detection is scoped to code-vs-code / doc-vs-symbol
consistency (does the wiki's path:line claim match HEAD), not to
cross-document claim consistency (does a security/privacy assertion in
SECURITY.md match the code's actual egress behavior). The egress/CDN/
scraper-deadness drift lives in the second class, which the product review --
not the ingest -- is the instrument for. The two findings the ingest did
resolve (F-docs-08, F-docs-10) are squarely within its first class. Net: the
ingest is a complementary, narrower drift detector that confirms its own
workstream's findings while leaving the product review's egress spine fully
load-bearing and unaddressed.
