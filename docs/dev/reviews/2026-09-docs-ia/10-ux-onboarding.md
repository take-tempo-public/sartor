> **Purpose:** Epic D / D1 opening audit of Sartor's end-user documentation, read cold through a zero-technical-knowledge onboarding lens, to feed the `docs/user/` information-architecture design.
> **Audience:** `dev` — Epic D D1 input
> **Authoritative for:** the state of the in-scope user docs (and their docs-site `.mdx` projections) as of the commit below; deltas against the 2026-05-25 onboarding audit and the 2026-07 UX review's IA section; the onboarding-ladder gap analysis for `docs/user/`. Not authoritative for the docs themselves — the cited canonical docs govern on conflict.

# UX onboarding audit — 2026-09-27

---
type: ux-audit
audited_docs:
  - README.md
  - docs/install.md
  - docs/walkthrough.md
  - docs/walkthrough_example.md
  - vision.md
  - docs/template_authoring.md
  - ACCESSIBILITY.md
  - docs-site/content/docs/*.mdx (non-`dev-*` slugs, excluding api-reference/)
  - docs-site/content/docs/meta.json
commit_sha: 88c0011f19c3822876d2fc1fbccddbf28f89573b
date: 2026-09-27
auditor: ux-onboarding-designer
baseline_audits:
  - docs/ux/onboarding_audit_2026-05-25.md
  - docs/dev/reviews/2026-07-ux-review/00-system-map.md ("Information architecture" section)
---

> **Correction (2026-09-27, D1 invoking session — read before the findings below).**
> Every `docs-site/content/docs/*.mdx` cite in this audit was read from a **stale local
> build artifact**, not from the published site: `*.mdx` there is gitignored
> (`.gitignore:134`, `git ls-files docs-site/content/docs` → `.gitkeep` only), the local
> `index.mdx` was dated 2026-07-26, and `.github/workflows/docs-deploy.yml:67-72`
> regenerates the tree from source on every deploy. Re-running
> `python scripts/project_docs_to_mdx.py` at `88c0011` printed
> `OK — 42 pages projected to docs-site/content/docs (5 user-tier, 37 dev-tier)`, and the
> fresh `index.mdx:146` reads **"Container (Docker or Podman) — not published yet."** So:
> - **The headline finding (§ summary, §3b `index.mdx:147-161` / `install.mdx:238-251`,
>   §6's "stale mdx projection" row, and ladder batch B1) does not hold** — it describes
>   an unregenerated local checkout, not what a reader of the deployed site sees. B1 is
>   void. What survives is a *process* observation for D1: a gitignored projection can sit
>   stale on a contributor's disk and read as authoritative.
> - **The `accessibility.mdx` `audience: ["dev"]` finding (§3b, B2) holds** on the fresh
>   projection (`accessibility.mdx:4`). The fix belongs in the source — the projection is
>   derived from `ACCESSIBILITY.md`'s header / the projector's fallback table — never in
>   the `.mdx`.
> - Findings against source `.md` files (cost anchor, `template_authoring.md`, the ladder
>   gaps) are unaffected by this correction.

Since the 2026-05-25 audit, the maintainer has done most of the recommended work: screenshots exist and are wired into `docs/walkthrough.md` + `docs/install.md`, the Setup-node diagram misclassification is fixed, a worked example (`docs/walkthrough_example.md`) now exists, `vision.md` and `docs/walkthrough.md` both carry acronym blocks, and the mid-wizard/API-error failure modes are documented. **The single highest-leverage remaining problem is that the hosted docs site (`docs-site/content/docs/index.mdx` and `install.mdx`) is stale relative to its own canonical sources** — it tells a first-time reader the container image is "batteries included" and ready to `docker run` (it is not — the current `README.md`/`docs/install.md` both say so explicitly) and recommends the exact API-key-in-shell-history pattern the current `docs/install.md` now warns against. A reader who trusts the hosted site over the raw repo hits a dead end or a security footgun that the source docs already fixed. Second highest-leverage: the per-application cost breakdown that `docs/install.md` and `docs/walkthrough_example.md` both link to (`README.md#install`) no longer exists at that anchor — it was apparently deleted rather than kept current, so the "canonical cost anchor" fix from the last audit regressed.

---

## 1. Diagram Critique

Two Mermaid diagrams total, both in `docs/walkthrough.md` (identically mirrored in `docs-site/content/docs/walkthrough.mdx`).

### Diagram 1 — User flow (`docs/walkthrough.md:42-67`, `flowchart LR`)

- **Clarity verdict:** passable.
- **Scannability:** 11 nodes, 2 decision gates, 1 optional dashed branch — under the one-glance ceiling, reads left-to-right in one sweep.
- **Color & shape semantic load:** four classDefs (`gate`/`llm`/`det`/`opt`). **Fixed since baseline:** the 2026-05-25 audit flagged `S[Setup]` as misclassified `opt` (implying Setup is optional, which it isn't). `docs/walkthrough.md:66` now reads `class S det` — corrected.
- **Decision-point legibility:** both gate diamonds (`docs/walkthrough.md:45-46`, `:51-52`) carry consequence labels ("gaps surfaced"/"looks good", "refine via NL note"/"approve"), not bare yes/no — good pattern, unchanged.
- **Concrete improvement:** `S` (Setup) still shares the `det` classDef with in-wizard steps `P`/`T`/`D`, which visually equates a one-time, pre-wizard action with a repeatable in-wizard step. Give Setup its own shape (e.g. a stadium node) BECAUSE `docs/dev/reviews/2026-07-ux-review/00-system-map.md`'s IA section documents Setup's User Selection panel and the Prior Applications list as sitting *above* the wizard rail, a distinct UI region the diagram currently flattens into the same visual class as the rail itself.

### Diagram 2 — Information flow (`docs/walkthrough.md:96-137`, `flowchart TB`)

- **Clarity verdict:** needs work — same verdict as baseline, only half-addressed.
- **Scannability:** still 12 nodes + 3 subgraphs + 8 cross-subgraph arrows in one TB block; unchanged crowding complaint.
- **Color & shape semantic load:** **Partially fixed** — the baseline's "elevate the Corpus subgraph visually" recommendation landed (`docs/walkthrough.md:132`, `classDef store … stroke-width:3px`), but the second half of that recommendation — an in-diagram caption node, since Mermaid `%%` comments don't render — was not added.
- **Decision-point legibility:** still no gate markers on this diagram; a reader who only sees Diagram 2 still doesn't learn the dual-gate story Diagram 1 tells. Unchanged from baseline.
- **Concrete improvement:** add a `note[/"single source of truth"/]` node inside the `Corpus` subgraph BECAUSE the thickened border alone (`:132`) signals *emphasis* without saying *why* — the prose immediately below (`docs/walkthrough.md:139-144`, "Read this top-down…") is still doing work the diagram should do on its own, exactly the gap the baseline named.

---

## 2. Screenshot Manifest

Baseline recommended 10 screenshots against a doc set with zero. **Nine now exist and are wired in** (`docs/screenshots/*.png`, referenced from `docs/install.md:578` and eight anchors in `docs/walkthrough.md`), following the checklist in `docs-site/content/docs/ux-screenshot-capture.mdx`. One asset was captured but never used: `docs/screenshots/readme_hero_wizard-step1-filled.png` exists on disk but `README.md` contains zero `![…]` image references (confirmed by full-text scan) and the file isn't even copied into `docs-site/content/docs/screenshots/` (9 files there, not 10). The remaining gaps:

| Doc | Anchor / nearest heading | Wizard step | UI state to show | Annotations needed | Priority |
|---|---|---|---|---|---|
| README.md | "How it works" §, after the ASCII step block (`README.md:115`) | hero (all 6) | Wire in the *already-captured* `readme_hero_wizard-step1-filled.png` | Callout on wizard rail + the two human-gate icons | P0 |
| docs-site index.mdx | same anchor, once B1 (below) regenerates the projection | hero | Same asset, copied into `docs-site/content/docs/screenshots/` | Same | P0 |
| docs/walkthrough.md | "Setup" §, after "Once the corpus is populated…" (`docs/walkthrough.md:188-192`) | Setup / cross-application | Application tab showing the **Prior Applications** list and the **Candidate Memory** tab, per `00-system-map.md`'s IA section — currently undocumented in any user doc | Callout naming both regions; note that this is how you resume a second application | P1 |
| README.md | "For coaches & headhunters" § | n/a (multi-candidate) | User-picker/switcher showing 2+ named client profiles | Callout: "each name = a separate persistent career file" | P1 |
| docs/walkthrough_example.md | anywhere in the Compose section | Step 3 | One frame of Priya's actual Helix card (pin/exclude/accept state) — the doc currently has zero images despite being the concrete, narrative doc | none needed, illustrative only | P2 |
| docs/walkthrough.md | Step 6, "Under the hood (refine)" (`docs/walkthrough.md:441-450`) | Step 6, second pass | Before/after diff of a Refine cycle (one screenshot of the note typed, one of the re-rendered result) | Callout on what changed | P2 |
| docs/install.md | "First-run setup for a source install" § (`docs/install.md:210-236`) | pre-wizard | Terminal output of `sartor --setup` (the now-recommended path) — the doc has one screenshot total (the user picker) and none of the CLI flow it spends the most words on | none | P2 |

---

## 3. Readability Pass

### 3a. Jargon-first-use matrix (tracked terms × in-scope prose docs)

Every doc is read standalone, so a term defined in `walkthrough.md` does not count as covering its use in `README.md`. `Y` = defined at first use in that doc; `N` = used, not defined in that doc; `Partial` = named but not explained; `n/u` = term not used in that doc. `template_authoring.md` and `ACCESSIBILITY.md` carry no tracked jargon except `ATS` (checked full text of both).

| Term | README.md | install.md | walkthrough.md | walkthrough_example.md | vision.md | template_authoring.md |
|---|---|---|---|---|---|---|
| JD | **N** (:206, abbreviation never tied to a spelled-out form anywhere in the doc) | Y (:586, adjacent) | Y (:30-32, acronym block) | Y (:16-18) | Y (:8-11) | n/u |
| ATS | Y (:72, :77) | n/u | Y (:30-32) | Y (:16-18) | Y (:8-11) | **N** (used throughout, e.g. :1, :11; no header block exists to house a definition) |
| LLM | **N** (:11, first word in the doc's core-discipline sentence) | **N** (:570) | Y (:30-32) | Y (:16-18) | Y (:8-11) | n/u |
| corpus | Y (:74, descriptive apposition) | **N** (:575) | Y (:171-176, "Why a structured corpus…") | Partial (companion doc, self-declared non-canonical) | **N** (:39, used with zero gloss) | n/u |
| context_set | n/u | **N** (:622) | Y (:401, :522) | Partial (:298-300, filename only) | n/u | n/u |
| Compose | Y (:110) | Y (:589) | Y (step heading + full §) | Partial | n/u | n/u |
| Clarify | Y (:109) | Y (:587) | Y (step heading + full §) | Partial | n/u | n/u |
| refine | Partial (:113, bare word) | Partial (:593, bare word) | Y (:429-450) | n/u (example's own "does NOT cover" list excludes it) | n/u | n/u |
| grounding | Y (:11, concept explained) | n/u | Y (diagram caption + repeats) | Partial (:271-273, metric scored, concept not re-explained) | Y (:177-197 section; casual first use at :59 slightly precedes it) | n/u |
| paged.js | n/u | n/u | Y (:359-362, minimal) | n/u | n/u | n/u |
| Sonnet | **N** (:192, bare model name) | n/u | Y (:209-211) | Partial (assumes walkthrough.md's gloss) | **N** (:165-169, bare) | n/u |
| Haiku | **N** (:192) | n/u | Y (:165-168) | Partial | **N** (:165-169) | n/u |

Fix for every `N` cell: either spell the term out in an adjacent parenthetical at that exact citation, or add the "Acronyms used throughout" block `walkthrough.md`/`vision.md` already use — `README.md` and `template_authoring.md` are the two docs missing that pattern entirely, and they are respectively the *first* and one of the *least-visited* docs a reader hits, which is exactly backwards for jargon load.

### 3b. Individual findings

**README.md:11** — jargon-first-use
> "The core discipline: **the LLM discovers and phrases — it does not invent.**"
Fix: add an acronym block under the H1, matching `vision.md:8-11`'s pattern, before this sentence is the reader's first exposure to "LLM."

**README.md:206** — jargon-first-use
> "paste the JD → analyze fit + ATS warnings"
Fix: README spells out "job description" once (:108) but never writes "(JD)" next to it, so this later shorthand has no anchor in the same document. Tie the abbreviation to the full form at :108.

**README.md:121-186 / docs/install.md:570-571 / docs/walkthrough_example.md:328-330** — cost-not-set
> `docs/install.md:571`: "Total cost: ~$0.05–$0.30 (`[see breakdown](../README.md#install)`)."
> `docs/walkthrough_example.md:328-330`: "This is the 'résumé + clarify' band from `[Cost guidance](../README.md#install)` — squarely in the typical-use range."
Fix: `README.md`'s `## Install` section (:121-186) contains no per-application cost table today — the closest content is "a few cents per run, no subscription" at `README.md:209`, which sits in a different section and isn't a breakdown or a set of bands. Both downstream links promise something that isn't there. Restore a canonical cost paragraph inside `## Install`, built from the real current per-step numbers in `docs/walkthrough.md` (~$0.02 import, ~$0.04 analyze, ~$0.03 clarify, ~$0.03 compose, ~$0.05–$0.15 generate, ~$0.05–$0.15/refine, ~$0.04–$0.08 cover letter) rather than resurrecting the old three-band prose the 2026-05-25 audit was citing (those exact bands are gone from the current doc, so they were evidently the thing that got cut).

**docs/install.md:305-334** — step-skipped (wrong-audience content)
> "## Maintainer: publishing (one-time `[HUMAN]` setup)" … GitHub/PyPI/GHCR console steps, `git tag vX.Y.Z && git push --tags`.
Fix: move to `docs/dev/RELEASE_CHECKLIST.md` (already exists, already on the docs-site nav as `dev-release-checklist`), leave one pointer sentence. BECAUSE this is release-engineering content sitting inside the primary zero-technical-knowledge install guide.

**docs/install.md:668-699** — step-skipped
> "## Verifying the install" — `pip install -e '.[dev]'`, `python -m pytest -q`, `python -m ruff check .`.
Fix: move to `CONTRIBUTING.md`'s dev-loop section. The doc already half-admits this ("pytest and ruff aren't part of the app itself — they're dev-only tooling") but keeps the content anyway as the doc's closing section.

**docs/template_authoring.md:1** — missing-rationale / structural
> (no Purpose/Audience/Authoritative-for header at all — every other in-scope doc has one)
Fix: add the three-line header per `docs/dev/doc-style-guide.md`. While there, split the file: keep the ATS-rules table (:14-25) + role-paragraph order (:27-50) + validation section (:85-95) as the power-user-facing remainder; move "How to add a new bundled template" (:73-84, `scripts/build_bundled_templates.py`, migration file references) to a dev doc — see Rewrite Ladder B5.

**docs-site/content/docs/index.mdx:147-161** — reference drift (stale generated projection)
> "**Container (Docker or Podman) — batteries included** (Chromium + recall index baked in): ```docker run …```"
Fix: this contradicts the current canonical source, `README.md:141-149`: "**Container (Docker or Podman) — not published yet.** … no version tag has been pushed, so the pull fails today." Both files carry the header comment `{/* GENERATED … do not hand-edit. Edit the cited source doc and re-run the projection. */}` — the source was edited, the projection wasn't re-run. This is the single riskiest item in this audit: a first-time reader on the hosted docs site who copies this command gets an unexplained pull failure with no warning that it's expected.

**docs-site/content/docs/install.mdx:238-251** — reference drift, security-relevant
> "**Set your API key** (choose one): - **Environment variable (recommended):**"
Fix: the current canonical source, `docs/install.md:410-417`, actively recommends the *opposite* — `sartor --setup`, specifically because the environment-variable form "goes into your shell history in plaintext" (`docs/install.md:238-253`). Same root cause as the container drift above (stale, unregenerated projection); flagged separately because this one is a security-relevant behavior change, not just a missing caveat. Supporting evidence of the same staleness: `install.mdx:445-456`'s "Chromium not found" / "API key not picked up" troubleshooting entries never mention `sartor --doctor`, which the current `docs/install.md:632-652` leads with.

**docs-site/content/docs/accessibility.mdx:4** — missing-rationale / IA
> `audience: ["dev"]`
Fix: `ACCESSIBILITY.md`'s own header (`ACCESSIBILITY.md:11-13`) states a mixed audience — "anyone evaluating Sartor who relies on assistive technology… contributors landing UI changes" — and every genuinely dev-only doc in the same nav (`architecture`, `product-shape`, `system-model`, `agents`, `claude`, `contributing`, `security`, all three `governance-*`, `ux-screenshot-capture`) carries the identical tag, so this isn't noise, it's a specific mismatch on one page. Per `docs-site/content/docs/index.mdx:237`'s own claim ("the same `user`/`dev` audience plane… is the plane this documentation's navigation gates on"), a wrong tag here risks hiding the one page a screen-reader-dependent evaluator would most want from a `user`-filtered nav view. Retag `["user", "dev"]`.

**ACCESSIBILITY.md:78-80** — placement, not absence
> "(Browser **Back** currently exits the single-page app rather than stepping back a wizard stage — a known limitation slated for the blueprint-split work.)"
Fix: this failure mode IS documented — but only here, in a doc currently mistagged `dev` on the hosted site (see finding above), and never cross-referenced from `docs/walkthrough.md`'s "If something goes wrong mid-wizard" (:488-513), which is where a first-time user would actually look for it. Add a one-line pointer from that section.

---

## 4. Decision-Point Inventory

| # | Trigger | Options | Default / common choice | Consequence of each option | Reversible? |
|---|---|---|---|---|---|
| 1 | Setup — pick or create a user (`docs/walkthrough.md:150-154`) | use existing user · create new user | whichever exists; new users are cheap | isolated `configs/<user>.config`, `resumes/<user>/`, `output/<user>/`; no cross-user sharing | Yes — switch anytime |
| 2 | Setup — corpus population path (`docs/walkthrough.md:156-184`) | `+ Import résumé` · add experiences/bullets manually · do nothing | Import (faster start) | import costs ~$0.02 (one Haiku call); manual entry is free but slow; doing nothing leaves Compose with nothing to recommend | Yes — import is additive; hand-edit anytime |
| 3 | Step 1 — supplemental scrape opt-in (`docs/walkthrough.md:217-220`) | toggle LinkedIn/portfolio fetch on/off (Settings) | off | on adds context to analyze/generate at the cost of one extra network call per URL, cached into the corpus (not re-scraped each analyze) | Yes — toggle per application |
| 4 | Gate #1 — enter Clarify or skip (`docs/walkthrough.md:79-90`, :226-240) | enter Clarify (Step 2) · skip to Compose | skip if the gaps section is empty/irrelevant | skipping is fine when the corpus already covers the JD; entering costs ~$0.03 and materially improves output on real, undocumented gaps | Yes — can return to Clarify after seeing Step 5 output |
| 5 | Step 2 — answer each clarification question (`docs/walkthrough.md:250-281`) | specific answer · vague answer · skip (blank) | specific for true experience; skip for inapplicable | vague answers → vague bullets; a skipped question doesn't degrade output below the no-Clarify baseline | Yes — re-run via `iterate-clarify`, similar cost |
| 6 | Step 2 — run a second Clarify round (`docs/walkthrough.md:262-265`) | iterate-clarify · stop at round 1 | stop | another ~$0.03 + latency; worth it only if round 1 opened new gaps | Yes — additive |
| 7 | Step 3 — per-bullet pin/exclude/leave-unmarked (`docs/walkthrough.md:296-303`) | pin · exclude · leave unmarked | leave unmarked (let ranking decide) | pinned bullets are guaranteed in; excluded are guaranteed out; unmarked compete for slots and may be dropped | Yes — flip any time before Generate |
| 8 | Step 3 — accept/reject/edit an LLM-recommended bullet (`docs/walkthrough.md:298-300`) | accept as-is · accept with edit · reject | accept-with-edit when close, reject when it drifts from truth | accepting folds it into this application; `critique_proposal()` decides whether it persists into the corpus | Yes — reject is non-destructive |
| 9 | Step 3 — reorder bullets within an experience (`docs/walkthrough.md:302-316`) | drag `≡` handle · keyboard Up/Down · "Reset to AI ranking" | AI fit-ranking (default) | order is a real lever, not cosmetic — earlier bullets carry more weight when the generator trims to fit length; a newly-added bullet lands at the end flagged for repositioning | Yes — reset restores AI order per experience |
| 10 | Step 3 — pick a summary variant (`docs/walkthrough.md:301, 306-307`) | existing variant · LLM-proposed variant · write your own | pick the LLM variant if honest | the summary is the first thing a recruiter reads | Yes — switch before Generate |
| 11 | Step 4 — choose template (`docs/walkthrough.md:348-355`) | Classic · Modern · Spacious · Tech · upload own `.docx` | pick by field signal | all four bundled are ATS-safe; uploads show "ATS · unverified" (no introspection) | Yes — free re-render, no LLM call |
| 12 | Step 5 — choose output format (`docs/walkthrough.md:387-391`) | `.docx` · `.pdf` · `.md` | `.docx` for most portals | `.pdf` needs the one-time Chromium install; `.md` is portable/version-control-friendly | Yes — regenerate in another format, ~$0.05–$0.15 |
| 13 | Gate #2 — refine or approve (`docs/walkthrough.md:429-450`) | write a natural-language Refine note and re-run · approve and Download | approve if every claim grounds | each Refine is ~$0.05–$0.15 and writes a new child `context_*.json` (audit trail preserved); approve makes no further LLM call | Yes — refine indefinitely, nothing overwritten |
| 14 | Post-Gate #2 — generate a cover letter or not (`docs/walkthrough.md:464-486`) | click `+ Generate cover letter` · skip | skip (~a third of applications don't ask for one, per `vision.md:272-279`) | cover letter is generated against the *finalized* résumé, ~$0.04–$0.08, full refine parity | Yes — generate later from the same Download screen |

---

## 5. Worked Example Specification

`docs/walkthrough_example.md` already exists (Priya Sharma / Vertica Logistics), fulfilling the 2026-05-25 audit's B7 recommendation. Checked against that audit's own required-content list:

- Synthetic JD shape ✓ (senior IC role, Kafka mentioned six times as the ATS-tell, "lead a team of 6" as the corroboration-needing scope claim).
- Synthetic corpus shape ✓ (3 experiences, 6–9 bullets each, one Kafka-in-passing bullet, no team-size bullet).
- Decisions walked ✓ for: one bullet pin (Helix Kafka bullet), one exclude (CI/CD Bash bullet, ROS/CAD bullets), one proposal accept (Postgres-tuning bullet), one proposal edit (tightened "became the platform team's standard" wording), one Clarify answer that surfaces a number (60 partitions / 8k events/sec / 6 engineers).
- **Not covered, and explicitly disclaimed as such** (`docs/walkthrough_example.md:334-352`, "What this example does NOT cover"): a genuine **skip-Clarify** branch, and a Gate #2 **refine** pass. These are exactly the two decisions the original spec required modeling *both branches* of — the shipped example only walks the "enter Clarify, approve without refining" happy path.

**Recommendation:** rather than write a second full synthetic candidate, extend the existing doc (or add a short companion section) with:
- **A skip-Clarify beat.** A second, brief synthetic JD/corpus pairing (or a counterfactual paragraph off the existing Priya corpus) where Step 1's gap section comes back empty/irrelevant, so Gate #1 goes straight to Compose. Lesson to teach: "skip is the *correct*, not the lesser, choice when the corpus already covers the posting."
- **A refine beat.** Take Priya's own generated résumé and walk one Refine cycle — a note like "shorten the Northwind bullets," the re-generate cost (~$0.05–$0.15), and a spot-check of what changed. Lesson to teach: this is the "iterating" rung of the onboarding ladder (see §8) and today has zero worked demonstration anywhere in the doc set.
- **Recommended location:** append both as new `##` sections in `docs/walkthrough_example.md` rather than a new file — the existing doc's own framing ("What this example does NOT cover") already anticipates exactly this follow-up.

---

## 6. Failure-Mode Coverage

| Failure mode | Covered? (doc:line if yes, "no" if not) |
|---|---|
| Anthropic API error mid-call (4xx/5xx/network drop) | yes — `docs/install.md:621-630` |
| Anthropic rate-limit (429) | yes — folded into the same entry, `docs/install.md:625-628` |
| Anthropic billing cap exceeded | yes — same entry, `docs/install.md:627-628` |
| API key not picked up | yes — `docs/install.md:644-652` (source); **stale/incomplete in the mdx projection**, `install.mdx:450-456` (no `--doctor` mention) |
| Missing Chromium / PDF button greyed out | yes — `docs/install.md:632-642`, incl. macOS 12 floor | 
| Playwright missing system libs (Linux) | yes — `docs/install.md:536-545` (concrete `apt install` line; baseline flagged this as only "partial," now fixed) |
| Port 5000 conflict | yes — `docs/install.md:654-658` |
| Malformed JSON / generation retry failure | yes — `docs/install.md:614-619` (commit-SHA reference the baseline flagged has been removed — fixed) |
| Mid-wizard tab close / resume later | yes — `docs/walkthrough.md:488-513` |
| Re-opening the app and continuing yesterday's wizard | yes — same section, `docs/walkthrough.md:497-499` |
| Parser produces wrong/scrambled output on import | partial — `docs/walkthrough.md:179-184` covers *bad extraction*, not an outright parse *failure/crash* on a malformed or scanned file |
| Browser Back exits the wizard instead of stepping back | yes, but **misplaced** — `ACCESSIBILITY.md:78-80` only; absent from `docs/walkthrough.md`'s own "If something goes wrong" section, and the hosted page is mistagged `dev` (see §3) |
| Demo mode / real-key interaction confusion | yes — `README.md:165-179`, `docs/install.md:275-303` |
| Disk full during generate (output/logs/db growth) | no |
| Switching users mid-wizard | no |
| Two terminals/processes against the same SQLite corpus | no |
| Alembic migration failure on an existing/older `db/resume.sqlite` | no (new candidate this pass — not in the 2026-05-25 list) |
| Two-terminal / concurrent-write corpus corruption | no |

**Priority to add next:** the Browser-Back mismatch is the cheapest, highest-value fix (one sentence + a fixed audience tag, no new content to author) and directly serves a user population (assistive-tech / keyboard-only) the project has explicitly committed to taking seriously. After that, disk-full and concurrent-process/migration failures are the two failure modes most likely to produce silent data loss rather than a visible error — worth a short "known sharp edges" paragraph even without full remediation, per the project's own "declare the gap" discipline.

---

## 7. Rewrite Ladder

### B1 — Regenerate the stale docs-site projections (S)
- **Scope:** `docs-site/content/docs/index.mdx`, `docs-site/content/docs/install.mdx` (re-run `scripts/project_docs_to_mdx.py` against current `README.md` / `docs/install.md`).
- **Summary:** closes the container "not published yet" drift and the API-key-in-shell-history drift.
- **Size:** S (mechanical regeneration, no prose judgment).
- **Depends on:** none.
- **Why B1:** highest-severity, purely mechanical, zero content decisions — should land before anything else touches these two files so later edits aren't clobbered by a bulk regeneration.

### B2 — Fix `accessibility.mdx` audience tag + add `template_authoring` to the docs-site (S)
- **Scope:** `docs-site/content/docs/accessibility.mdx` frontmatter (or whatever upstream mapping drives it), `docs-site/content/docs/meta.json`, a new `template-authoring.mdx` projection.
- **Summary:** retag accessibility as mixed `["user","dev"]`; add the currently-absent template-authoring page to the nav.
- **Size:** S.
- **Depends on:** none.
- **Why B2:** config-only, independent of B1, closes two concrete IA gaps (a hidden a11y page, a missing power-user doc).

### B3 — Restore the canonical cost-anchor paragraph (S/M)
- **Scope:** `README.md` (`## Install` section).
- **Summary:** add a real per-application cost paragraph at the anchor `docs/install.md` and `docs/walkthrough_example.md` already link to, using current per-step numbers.
- **Size:** S/M.
- **Depends on:** none.
- **Why B3:** closes the most-cited still-open readability gap; no diagram or IA dependency.

### B4 — Move maintainer/dev content out of `docs/install.md` (M)
- **Scope:** `docs/install.md` (remove "Maintainer: publishing" and "Verifying the install"), `docs/dev/RELEASE_CHECKLIST.md`, `CONTRIBUTING.md`.
- **Summary:** relocate the two dev-audience sections, leave one-line pointers.
- **Size:** M.
- **Depends on:** B1 (same file — land after the regeneration pass to avoid a merge conflict on the projected `.mdx`).
- **Why this order:** B1 is a mechanical whole-file regeneration; sequencing a hand-edit after it avoids the regeneration silently reverting it.

### B5 — Split `docs/template_authoring.md`, add its missing header (S/M)
- **Scope:** `docs/template_authoring.md`, a new dev doc for "How to add a new bundled template."
- **Summary:** add the Purpose/Audience/Authoritative-for header; move the maintainer-only build/migration section out.
- **Size:** S/M.
- **Depends on:** B2 (the docs-site page should exist before its content gets split, so the split lands on the already-published page rather than needing a second projection pass).

### B6 — Wire in the orphaned hero screenshot + document Prior Applications / Candidate Memory (M)
- **Scope:** `README.md`, `docs/walkthrough.md` (Setup section).
- **Summary:** insert the already-captured hero image; add 2-3 sentences naming the Prior Applications list and Candidate Memory tab so returning users have an in-app path back to earlier work, not just the filesystem trail.
- **Size:** M.
- **Depends on:** B1 (so the new README image survives the docs-site regeneration rather than needing a second sync pass).

### B7 — Second worked-example beat: skip-Clarify + refine loop (L)
- **Scope:** `docs/walkthrough_example.md`.
- **Summary:** add the two decision branches the shipped example explicitly opts out of, closing the "iterating" rung of the onboarding ladder (see §8).
- **Size:** L.
- **Depends on:** B3 (should cite the corrected canonical cost figures, not re-derive its own).

---

## 8. Onboarding Ladder & docs-site IA (additional lens)

**Rung 1 — First run.** `docs/install.md` (+ its `.mdx`, once B1 lands), demo mode, `sartor --doctor`. Solid content, actively maintained (security-conscious API-key guidance, concrete Linux deps fallback, macOS 12 floor documented). The only real problem is that the *hosted* copy of this rung currently contradicts the *canonical* copy (§3, §7 B1).

**Rung 2 — First tailored résumé.** `docs/walkthrough.md` + `docs/walkthrough_example.md`. The best-documented rung in the set: screenshots, an acronym block, a concrete worked example, per-step cost/latency, and an explicit "why" for every non-obvious design choice (Haiku vs. Sonnet, why refine is edit-aware, why cover letter is detached). No structural changes recommended beyond the readability items in §3.

**Rung 3 — Iterating.** The weakest rung. `docs/walkthrough.md:488-513` covers *recovery* (tab close, next-day return) but not *iteration as strategy* — running a second application against the same corpus, when to re-Clarify, what a refine cycle actually feels like. The one worked example that could show this explicitly declines to (§5). The in-app **Prior Applications** list and **Candidate Memory** tab — both confirmed to exist by `docs/dev/reviews/2026-07-ux-review/00-system-map.md`'s IA section — are never named in any user-facing doc; a first-time user finishing their first résumé has no documented way to find their way back to it, or to a second one, except by reading the filesystem-path table at `docs/walkthrough.md:516-529`.

**Rung 4 — Advanced.** Splits in two, both thin:
- *Coach / multi-candidate* — `README.md`'s "For coaches & headhunters" section is prose-only: no walkthrough, no screenshot, no docs-site page of its own. Given the README explicitly names this as one of three core audiences (not a footnote), this is a real gap, not scope creep.
- *Power user* — `docs/template_authoring.md` is the one candidate doc for this rung and it isn't on the hosted docs site at all (§2, §3, B2/B5), has no standalone header, and is roughly half maintainer-only content. The diagnostics dashboard (`/_dashboard`) is correctly and deliberately gated to "for maintainers" language today (`docs/walkthrough.md:543-547`) — that's a defensible current scope line, not a bug, and isn't flagged here as something to open up.

**docs-site nav shape (`docs-site/content/docs/meta.json:4-41`).** The flat page list interleaves all four rungs above with 27 of 36 total pages that are dev-tagged content (`architecture`, `product-shape`, `system-model`, three `governance-*`, `agents`, `claude`, `contributing`, `security`, `ux-screenshot-capture`, plus 15 `dev-*`-slugged pages, plus `accessibility` mistagged — §3). Concretely: the very next page after `walkthrough-example` in the nav order is `architecture` (`meta.json:8-9`), a developer-facing module map, before a first-time reader ever reaches `security` or `accessibility` (`meta.json:18-19`). For a zero-technical-knowledge audience, the ladder is interrupted immediately after rung 2.

**Recommendation for the `docs/user/` target tree** (input to D1, not a mandate):

```
docs/user/
  install.md            (moved from docs/install.md, trimmed per B4)
  walkthrough.md         (moved from docs/walkthrough.md)
  walkthrough_example.md (moved from docs/walkthrough_example.md, extended per B7)
  coaching.md            (NEW — rung 4a, currently only prose in README.md)
  template_authoring.md  (moved + split per B5 — rung 4b)
README.md                (stays at root — front door, all three audiences)
vision.md                (stays at root — evaluator-facing, dual-audience by its own header)
ACCESSIBILITY.md         (stays at root; fix its audience tag regardless of path — §3)
```

Pairing this with a docs-site nav change — group the sidebar into "Using Sartor" (the `docs/user/` set) vs. "Building on Sartor" (everything currently dev-tagged) rather than one flat list — would resolve the interleaving problem above without moving any content twice.
