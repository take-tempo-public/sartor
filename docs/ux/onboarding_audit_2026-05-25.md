---
type: ux-audit
audited_docs:
  - README.md
  - docs/install.md
  - docs/walkthrough.md
  - vision.md
commit_sha: b593bbb51590e3681ed8341c8c2a348bf81c3b13
date: 2026-05-25
auditor: ux-onboarding-designer
---

# UX onboarding audit — 2026-05-25

A first-time user can install sartor. and complete a generation, but the path between "app is running" and "first useful résumé" is overloaded with jargon (corpus, context_set, grounding, ATS, Sonnet/Haiku, paged.js) introduced before it's earned, and the cost framing flips between "$0.05–$0.10" (README short band), "$0.05–$0.30" (install), and "$0.30–$0.50" (README long band) without a single canonical anchor. **The single highest-leverage improvement is to write one canonical "what one application costs and why" paragraph in README.md and link to it from install.md and walkthrough.md** — that single anchor resolves three downstream readability issues, sets honest expectations before the user even opens the wizard, and aligns the cost-conscious mental model the rest of the doc set already assumes.

Adjacent to that, the doc set has no synthetic worked example. A new user has to imagine what a JD-plus-corpus run actually feels like from prose alone. The Rewrite Ladder treats both as B1.

---

## Diagram Critique

The doc set under audit contains **two** Mermaid diagrams, both in `docs/walkthrough.md`. (`README.md`, `docs/install.md`, and `vision.md` ship zero diagrams. The four diagrams in `docs/architecture.md` and `docs/diagrams/*.mmd` are dev-facing and out of scope for this audit.)

### Diagram 1 — User flow (`docs/walkthrough.md:36–60`, `flowchart LR`)

- **Clarity verdict:** good — the LR shape matches the wizard rail at the top of the app, and the dual-gate amber colors visually pop the load-bearing review checkpoints.
- **Scannability:** 11 nodes, 2 decision gates, 1 optional branch. Just under the cognitive ceiling for a single-glance diagram. Reads in one sweep.
- **Color + shape semantic load:** four classDefs (`gate`, `llm`, `det`, `opt`) doing four jobs — appropriate. The legend immediately below (`docs/walkthrough.md:62–63`) is load-bearing and well-placed.
- **Decision-point legibility:** both diamonds are labeled with the consequence ("gaps surfaced" / "looks good", "refine via NL note" / "approve") rather than just yes/no — this is the right pattern. The "refine via NL note" loop back from G2 → Gen is the single most important arrow in the diagram and it lands.
- **Concrete improvement:** the "Setup" node `S([Setup<br/>user + corpus])` is classed `opt` (purple-dashed) but Setup is **not optional** for a first-time user — they must pick a user and (effectively) import a corpus before Step 1 will be useful. Reclass `S` as its own neutral style or as `det`. BECAUSE classifying a required step as optional misleads a first-time reader at exactly the moment they're scanning for "what's mandatory."

### Diagram 2 — Information flow (`docs/walkthrough.md:81–123`, `flowchart TB`)

- **Clarity verdict:** mixed. The three-subgraph layout (You / Corpus / System) is conceptually right but visually crowded — 12 nodes plus 3 subgraph containers plus 8 cross-subgraph arrows in a single TB block.
- **Scannability:** the eye doesn't know where to start. The prose hint immediately after (`docs/walkthrough.md:125` "Read this top-down: the corpus in the middle is the load-bearing artifact") is doing work the diagram should do on its own.
- **Color + shape semantic load:** three classDefs (`user`, `store`, `out`) — clean mapping, but the visual weight of `K1`/`K2` in the middle subgraph isn't elevated despite the prose calling them "load-bearing."
- **Decision-point legibility:** no decision diamonds — appropriate for an information-flow diagram. But also no human-gate markers, which means it loses the dual-gate story the User Flow diagram tells. A reader looking only at Diagram 2 would not know there are human review points.
- **Concrete improvement:** thicken the `K1` / `K2` Corpus subgraph (e.g., a `stroke-width: 3px` classDef variant or a `[[double-bordered]]` shape) and add a one-line caption *inside* the diagram (`%%` Mermaid comment doesn't render — use a node like `note[/"corpus = single source of truth"/]`). BECAUSE the prose currently has to explain what the diagram should be self-evidently showing. Alternative: split into two simpler diagrams (inputs→corpus, corpus→outputs) — though that may be over-investment for one walkthrough.

---

## Screenshot Manifest

There are zero screenshots in the four audited docs today. The wizard is dense and unfamiliar enough that prose-only is leaving load-bearing detail unanchored. Recommended 10 captures, all from `docs/walkthrough.md` (the only doc where step-level prose currently exists). README and install.md should embed at most 1 hero screenshot between them; vision.md does not need any.

| Doc | Anchor | Wizard step | UI state to show | Annotations needed | Priority |
|---|---|---|---|---|---|
| README.md | "The wizard at a glance" §, after the ASCII block (line ~109) | All 6 (hero) | A single full-app screenshot showing the wizard rail at top, Step 1 active, the analysis panel populated | Callout: wizard rail (the six numbered chips); callout: human gate icons | P0 |
| docs/install.md | "First-run walkthrough" §, after step 1 (line ~184) | Setup (pre-wizard) | User picker dropdown open, showing default + one created user | Arrow to "+ Create user" affordance | P1 |
| docs/walkthrough.md | "Setup (before the wizard)" §, after "Import your existing résumé" (line ~144) | Setup | Career Corpus tab with `+ IMPORT LEGACY` button highlighted, before any import | Callout on the button; sidebar showing empty experience list | P0 |
| docs/walkthrough.md | "Step 1 — Job + Analyze" §, after "What you see" (line ~169) | Step 1 | Two-panel layout: JD textarea on left (with sample JD text), empty analysis panel on right | Callout on "Analyze" button | P0 |
| docs/walkthrough.md | "Step 1 — Job + Analyze" §, after "Verify before continuing" (line ~195) | Step 1 | Same screen post-analyze: filled analysis panel with skill matches, gaps, ATS warnings | Annotations on each subsection (match summary / gaps / ATS warnings) — this is Human Gate #1 | P0 |
| docs/walkthrough.md | "Step 2 — Clarify" §, after "What you see" (line ~206) | Step 2 | Three of the 3–5 clarification questions visible, one with a partially typed answer | Callout: "your answer becomes legitimate source for Step 5" | P1 |
| docs/walkthrough.md | "Step 3 — Compose" §, after "What you see" (line ~248) | Step 3 | One experience card expanded with pinned bullets, excluded bullets, and one LLM-recommended bullet visible | Callouts on pin / exclude / accept / reject affordances; summary variant picker visible | P0 |
| docs/walkthrough.md | "Step 4 — Template" §, after "What you see" (line ~293) | Step 4 | Four template cards in a row, Modern selected, live preview pane showing first page of rendered résumé | Callout: ATS-safety badge on each card; "Page 1 of N" counter | P1 |
| docs/walkthrough.md | "Step 6 — Download" §, after "What you see" (line ~366) | Step 6 | Generated résumé preview on left, Refine textarea with sample note ("emphasize the team-lead role"), Download + Generate cover letter buttons | Callouts on Refine flow and on the dual download/cover-letter affordances | P0 |
| docs/walkthrough.md | "Optional — Generate cover letter" § (line ~403) | Cover letter | Cover letter preview pane after first generation, refine textarea visible | Note that refine parity with résumé flow | P2 |

Target: 10 screenshots. The five P0 captures (hero + Corpus import + Step 1 pre-analyze + Step 1 post-analyze + Compose + Download) are the spine; the rest are progressive disclosure.

---

## Readability Pass

**README.md:3** — jargon-first-use
> "... deterministic Python tools handle all mechanical work; the LLM handles analysis and writing."
Fix: "LLM" appears here for the first time in the whole doc set's entry-point doc, and README never defines it (the term is used five times). Spell it out on first use: "... the LLM (large language model — Anthropic's Claude, in sartor.'s case) handles analysis and writing." BECAUSE the README is the first doc a candidate reads, and LLM is exactly the kind of "every technologist knows it" abbreviation that excludes the career-changer / junior-candidate audience sartor. is trying to serve.

**README.md:5** — passive-voice-in-teaching-moment
> "Runs locally. LLM calls to Anthropic (without a proxy that would force API billing without monthly credits)"
Fix: rewrite as direct second-person: "sartor. runs on your machine. Every LLM call hits Anthropic's API directly — there's no sartor.-operated proxy, so your Anthropic billing reflects your real usage, not a markup." BECAUSE the parenthetical's double-negative ("without a proxy that would force ... without monthly credits") forces the reader to unpack two negations before they land on the actual benefit.

**README.md:75–77** — cost-not-set
> "Résumé only, no iteration, no clarify — ~$0.05 – $0.10 / Résumé + clarify + 1-2 refine iterations — ~$0.15 – $0.25 / Full loop with iterate-clarify + multiple refines + cover letter — ~$0.30 – $0.50"
Fix: this is the canonical cost paragraph and it needs to be the canonical cost paragraph everywhere. Add an anchor `<a name="cost"></a>` here, then change `install.md:23–24` and `walkthrough.md` per-step cost numbers to link to it ("see [Cost guidance](../../README.md#install) for the per-call breakdown"). BECAUSE the install.md "first generation is ~$0.05–$0.30" framing doesn't match either of the three README bands; a first-time reader who compares the two pages will distrust both.

**README.md:99** — jargon-first-use
> "A single application moves through six steps. The first three are corpus + analysis (cheap or free)."
Fix: "corpus" appears here for the first time without a definition. Before this sentence, insert: "Your **corpus** is the pool of every bullet, summary, and experience you've ever written — sartor. mines it for what fits this specific JD. (Imported once, reused across every application.)" BECAUSE "corpus" is core vocabulary the reader will encounter eight more times before reaching the walkthrough's definition site.

**README.md:102** — jargon-first-use
> "1. Job + Analyze    — paste JD, run analyze; LLM reports skill match + ATS warnings"
Fix: "JD" and "ATS" both first appear here, both undefined in README. Spell them out on first use: "paste the job description (JD), run analyze; the LLM reports skill match + ATS (applicant tracking system — résumé-parsing software employers run on incoming files) warnings." BECAUSE these are job-search abbreviations that feel universal to professional users but are invisible to the early-career and career-changer candidates sartor. wants to help; the walkthrough defines them at line 28, but the README is read first and stands alone.

**README.md:111** — buried-decision
> "Two human review gates are required: the post-analyze review (step 1→2) and the post-generation refinement (step 6)."
Fix: pull this up as its own subsection heading ("### The two human review gates") above the ASCII wizard block. BECAUSE the gates are the most load-bearing UX claim in the whole product (sartor. is the kind of tool that pauses for you to think) and burying them in a paragraph after the step diagram inverts the priority.

**docs/install.md:23–24** — cost-not-set
> "The first generation is ~$0.05–$0.30 in API spend; budget guards documented in [`SECURITY.md`](../../SECURITY.md)."
Fix: replace the inline range with a link to the canonical README anchor (see the README:75 fix above). The "$0.05–$0.30" range here straddles three of README's four bands — it's not wrong, it's incomparable. BECAUSE one canonical answer is more trustworthy than three mostly-consistent ones.

**docs/install.md:174–180** — reference-voice-where-teaching-voice-belongs
> "For the full screen-by-screen guide — including user-flow and information-flow Mermaid diagrams ... see [`docs/walkthrough.md`](../walkthrough.md). The summary below is just enough to get a first generation working."
Fix: the install doc's "First-run walkthrough" subsection should be teaching-voiced ("By the end of these eight steps you'll have your first tailored résumé"), not reference-voiced ("For the full screen-by-screen guide ... see"). Lead with the outcome, link to walkthrough.md *after* the steps for "next, learn what each step is actually doing." BECAUSE the reader is in install-and-do mode at this exact point; they don't want a cross-reference before they've finished installing.

**docs/install.md:220–224** — missing-rationale
> "'Generation fails with AI generation response was malformed after retry.' The LLM occasionally emits raw control characters in the JSON response. The parser tolerates this since `2d7c564` (added `strict=False`)."
Fix: drop the commit SHA — a first-time user has no use for it. Rewrite as: "Rare. If you hit this on current `main`, file an issue with the `detail:` field attached. We added tolerance for the common case (`strict=False` JSON parsing) but new failure modes occasionally surface." BECAUSE referencing a commit hash in a user-facing troubleshooting entry signals "this doc was written for developers" and is exactly the kind of thing that erodes trust in the user-facing docs.

**docs/walkthrough.md:1** — missing-rationale
> "# Using sartor. — screen-by-screen walkthrough"
Fix: under the H1, before the Purpose/Audience block, add a one-sentence orienting line: "By the end of this doc you'll know what each of the six wizard steps does, what it costs, and what to look for before you click forward." BECAUSE the existing Purpose block is reference-voiced ("Authoritative for: the canonical step-by-step user flow ...") and doesn't tell a first-time reader what they'll get from reading it.

**docs/walkthrough.md:62–63** — jargon-first-use
> "**Legend:** blue = LLM call fires here · green = deterministic (no LLM) · amber = human review gate · purple-dashed = optional path."
Fix: "deterministic (no LLM)" is the first place the reader is asked to internalize this distinction without any pre-context for why it matters. Add a sentence: "sartor.'s design rule is *LLM only for fuzzy work*; everything else (parsing, rendering, file I/O) is plain Python you can trace line-by-line." BECAUSE deterministic-vs-fuzzy is the single most important conceptual frame in the whole product, and it deserves more than a legend gloss on first introduction.

**docs/walkthrough.md:151** — jargon-first-use
> "**Under the hood:** [`/api/upload`](../../app.py) runs `parser.py` deterministically (no LLM) to extract text, then one Haiku 4.5 call to `extract_experiences()` parses the text into structured experiences ..."
Fix: "Haiku 4.5" first-use needs a parenthetical: "Haiku 4.5 (Anthropic's small + fast model — sartor. uses it for selection and parsing; the larger Sonnet model handles writing)". Same for "Sonnet 4.6" at line 178. BECAUSE the model names are mentioned eight times across the walkthrough but the cost / latency / role distinction is never explicitly drawn until the reader has already seen both names multiple times.

**docs/walkthrough.md:170** — paragraph-bloat
> "**Latency:** ~30–60s. This is the slowest call in the pipeline; it reads the JD plus your full master résumé plus any supplemental documents (LinkedIn scrape, portfolio URLs if you opted in)."
Fix: callout the 30–60s number on its own line and move the "why it's slow" rationale below: "**Latency:** ~30–60s — the slowest call in the pipeline. (It re-reads the JD + your full master résumé + any LinkedIn / portfolio scrape on every analyze call.)" BECAUSE a first-time user staring at a spinner for a minute will distrust the app unless they were primed for it; the latency number deserves its own visual beat.

**docs/walkthrough.md:229–232** — missing-rationale
> "**Why the questions feel pointed:** the system prompt for `clarify()` is a hiring-manager-as-interviewer persona — it's written to dig for specifics (numbers, scale, ownership scope), not to fish for vague claims."
Fix: this is good — keep it. But add a one-line consequence: "If a question feels uncomfortably specific, that's the point: a vague answer here produces a vague bullet at Step 5." BECAUSE the "why pointed" explanation is currently mechanical; the consequence framing is what tells the user how to interact with it.

**vision.md:31, 52, 262** — jargon-first-use
> vision.md uses LLM (first at line 31: "Nothing leaves it except the LLM API calls..."), ATS (first at line 52: "ATS-safe output by default..."), and JD (first at line 262: "structured JD fields") without ever defining any of them.
Fix: vision.md is the highest-priority doc for "should I use this" decisions and currently has zero acronym definitions. On each first-use site, add a parenthetical: "LLM (large language model)" at :31; "ATS (applicant tracking system — résumé-parsing software employers run on incoming files)" at :52; "JD (job description)" at :262. Alternative pattern: add a one-line acronym block under the H1 before the body, the way `docs/walkthrough.md:28` already does. BECAUSE vision.md is where a career-changer evaluator decides whether the project is for them; tripping over three undefined abbreviations in the first half-screen of reading is a high-cost trust hit on exactly the wrong audience.

**vision.md:23–25** — reference-voice-where-teaching-voice-belongs
> "sartor. answers one question, honestly: 'What résumé and (optional) cover letter should I send for this specific job?'"
Fix: this is the strongest opening sentence in the whole doc set — keep it verbatim. But the surrounding "Audience: humans evaluating whether to use or contribute" Purpose block is reference-voiced and reads cold before the punch. Move the one-question quote above the Purpose block as the literal first content after the H1. BECAUSE the punch belongs on the first screen the reader sees, not after they've scrolled past a Purpose/Audience metadata block.

**vision.md:256–264** — step-skipped
> "The analyze step is the latency floor ... See `docs/PERF_ANALYZE.md` for the audit."
Fix: the audited doc set lists `docs/PERF_ANALYZE.md` as a referenced doc, but it's a dev-facing artifact (audit, not user-facing prose). Either soft-gate the link with "(dev-facing)" or drop it. BECAUSE a user-facing vision doc shouldn't dump readers into a perf audit without warning.

---

## Decision-Point Inventory

Decision points a first-time user must navigate, in chronological wizard order.

| # | Trigger | Options | Default / common choice | Consequence of each option | Reversible? |
|---|---|---|---|---|---|
| 1 | Setup — pick or create a user (Setup, pre-wizard) | Use default user · create new user | Default user (single-tenant assumption) | New user creates isolated `configs/<user>.config`, `resumes/<user>/`, `output/<user>/`. No cross-user data sharing. | Yes — switch users anytime; nothing deleted. |
| 2 | Setup — corpus import path | + IMPORT LEGACY (upload existing résumé) · enter experiences/bullets manually · do nothing | IMPORT LEGACY (faster start) | Import costs ~$0.02 (one Haiku call) and produces a structured corpus you can edit. Manual entry is free but slow. Doing nothing means Step 3 (Compose) has nothing to recommend. | Yes — import is additive; you can re-import or edit by hand. |
| 3 | Step 1 — supplemental scraping opt-in | Toggle LinkedIn URL scrape on/off · toggle portfolio URL scrape on/off | Off (privacy default per SECURITY.md) | Scraping adds context to analyze + generate at the cost of one extra network call per URL. | Yes — toggle per application. |
| 4 | Step 1 → 2 (Human Gate #1) | Enter Clarify · skip straight to Compose | Skip if analyze surfaced no real gaps; enter Clarify if it did | Skipping is fine when corpus already covers the JD. Entering Clarify costs ~$0.03 but materially improves Step 5 output when there's a real-but-undocumented experience. | Yes — you can backtrack and run Clarify after seeing Step 5 output. |
| 5 | Step 2 — answer each clarification question | Answer with specifics · answer vaguely · skip (leave blank) | Answer specifics for true experience; skip for inapplicable questions | Vague answers produce vague bullets; skipped questions don't degrade output below the no-clarify baseline. | Yes — re-run clarify via iterate-clarify, ~$0.03. |
| 6 | Step 2 — run iterate-clarify (second round) | Yes (your first round opened new gaps) · no | No (most applications) | Each iteration is another ~$0.03 + Sonnet latency. Worth it when first answers expose new specifics worth probing. | Yes — additive. |
| 7 | Step 3 — pin/exclude each bullet | Pin · exclude · leave unmarked | Leave unmarked (let Step 5 decide) | Unmarked bullets compete for slots; pinned bullets are guaranteed in output; excluded bullets are guaranteed out. | Yes — flip pins/excludes any time before Step 5. |
| 8 | Step 3 — accept/edit/reject LLM-recommended bullets | Accept (use as-is) · edit then accept · reject | Reject if the recommendation drifts from truth; accept-with-edit when close | Accepting folds the bullet into this application; `critique_proposal` decides whether it persists into corpus. | Yes — reject is non-destructive. |
| 9 | Step 3 — pick summary variant | Use existing variant · pick LLM-proposed variant · write your own | Pick the LLM variant tuned to this JD if it's honest | The summary is the first thing a recruiter reads — own this choice. | Yes — switch variants before Step 5. |
| 10 | Step 4 — choose template | Classic · Modern · Spacious · Tech · upload own | Pick by field signal (Tech serif vs. Classic sans-serif) | All four bundled are ATS-safe; uploaded templates are marked "ATS · unverified." | Yes — re-render is free (no LLM). |
| 11 | Step 5 — choose output format | .docx · .pdf · .md | .docx for most employer portals; .pdf for direct-attach scenarios | .pdf renders via Playwright + Chromium (one-time 150 MB binary). .md is for portability / version control. | Yes — re-generate with a different format, ~$0.05–$0.15 per regenerate. |
| 12 | Step 6 (Human Gate #2) — refine vs. approve | Write a NL refinement note and re-Refine · approve and Download | Refine if any claim feels off; approve when grounded and honest | Each Refine is ~$0.05–$0.15 and writes a new child context file (audit trail preserved). Approve produces no further LLM call. | Yes — re-Refine indefinitely; nothing is overwritten. |

---

## Worked Example Specification

sartor. would benefit from one synthetic worked example threaded through the walkthrough — a single fictional candidate and JD that anchor every step's prose with a concrete instance. Specs only below; the prose is out of scope for this audit.

### Synthetic JD shape

- Title: senior individual-contributor role (e.g., "Senior Backend Engineer, Platform").
- Length: ~400 words, the median of real JD intake.
- Must-haves: a stack the synthetic candidate clearly has (Python + Postgres + AWS).
- Nice-to-haves: a stack the candidate touched but didn't write down (Kafka, Kubernetes).
- ATS-tell: a high-frequency keyword (e.g., "Kafka" mentioned 4–6 times in the JD body).
- One scope claim that needs corroboration ("led 6+ engineers"), to make Clarify earn its keep.

### Synthetic corpus shape

- 3 experiences: Current Co (3yr, senior), Previous Co (4yr, mid), Earlier Co (2yr, junior).
- ~8 bullets per experience; mixture of (a) strongly relevant, (b) marginally relevant, (c) clearly irrelevant.
- 2–3 summary variants written at different angles (technical depth vs. ownership scope vs. cross-functional).
- One bullet that mentions Kafka in passing (so Clarify can dig into it).
- One scope claim NOT in any bullet (so Clarify produces real value when answered).

### Decisions to walk through

1. **Setup:** import the corpus (~$0.02 Haiku call). Show the parsed experience list.
2. **Step 1:** paste JD, click Analyze (~$0.04 Sonnet). Reader sees: skill match ✓ Python/AWS, ✗ Kafka highlighted, gap = "team leadership scope not documented."
3. **Gate #1:** enter Clarify (the gap is real).
4. **Step 2:** 4 questions appear; reader answers 3 with specifics, leaves 1 blank because it doesn't apply.
5. **Step 3:** reader pins the Kafka-adjacent bullet, excludes 2 clearly irrelevant ones, accepts an LLM-proposed bullet that rewrites the leadership claim using the Clarify answer, picks the "ownership scope" summary variant.
6. **Step 4:** picks Modern template; live preview shows 2-page output.
7. **Step 5:** generates as .docx (~$0.10). Reader sees the final bullet list rendered.
8. **Gate #2:** spot-check passes — every claim traces to corpus + clarifications. Approves and downloads.
9. **Optional cover letter:** declines (the JD didn't ask).

### Lessons each step should teach

- **Setup:** corpus is one-time work; the same import powers every future application.
- **Step 1:** the "gaps" section is a signal, not a verdict — *real* gaps go to Clarify; irrelevant ones get ignored.
- **Step 2:** specifics in, specifics out; vague in, vague out.
- **Step 3:** pinning is a commitment, excluding is also a commitment; "leave unmarked" is fine and means "let the LLM decide."
- **Step 4:** template choice is a signal about your field; the page count is a sanity check on Step 3.
- **Step 5:** the wait is real and earned; the grounding metric is your fabrication detector.
- **Gate #2:** read the output the way an interviewer would read it — can you defend every claim?

### Recommended location

A new file `docs/walkthrough_example.md` referenced from `docs/walkthrough.md`'s "How to read this doc" intro: *"For a single synthetic candidate + JD threading through all six steps, see [walkthrough_example.md](../walkthrough_example.md)."*

Reasons for a separate file over inline interleaving: keeps the canonical walkthrough abstract (suits any reader's situation); allows the worked example to evolve independently as the wizard changes; mirrors the architecture-doc pattern of *abstract diagrams in one file, concrete sequences in sibling files*.

---

## Failure-Mode Coverage

| Failure mode | Covered? doc:line if yes / "no" if not |
|---|---|
| Stale UI after restart (browser cache) | yes — install.md:211–217 |
| ModuleNotFoundError after partial install | partial — install.md:269–271 (says "re-run pip install -e .") but doesn't name the symptom |
| Missing Chromium binary | yes — install.md:226–229 |
| API key not picked up | yes — install.md:231–237 |
| Port 5000 conflict | yes — install.md:239–243 |
| "Where is my data" question | yes — install.md:245–249 + README.md:50–67 |
| Generation returns malformed JSON after retry | yes — install.md:219–224 (but with a commit SHA that doesn't belong — see Readability Pass) |
| Anthropic API returns 4xx/5xx mid-call | no |
| Network drop during the 30–60s analyze or generate call | no |
| Anthropic rate-limit hit (429) | no |
| Anthropic monthly budget cap hit | no — budget guidance points to console.anthropic.com but the *symptom* in sartor. is undocumented |
| Mid-wizard tab close (does state persist?) | no — implicit in `context_set` files but never said |
| Re-opening the app and continuing yesterday's wizard | no — never explained |
| Parser fails on imported résumé (bad PDF, scanned PDF, complex .docx) | no |
| Playwright Chromium fails to install on Linux due to missing system libs | partial — install.md:155–157 mentions "follow on-screen instructions" but no concrete `apt install` fallback |
| Disk full during generate (output dir + logs + db growing) | no |
| Switching users mid-wizard | no |
| Two terminals running `python app.py` against the same configs | no |

### Priority order

1. **Anthropic API errors (rate-limit, 4xx/5xx, network drop):** the most likely failure for an active user. sartor. needs at least one paragraph in `install.md#troubleshooting` covering *what the user sees* in the UI when an API call fails partway through (current behavior: opaque error toast or no feedback). Tier 1.
2. **Mid-wizard state recovery (tab close, re-open tomorrow):** the most likely surprise for a returning user. The `context_set` audit trail makes recovery genuinely robust, but the doc never says so. One paragraph in `walkthrough.md`. Tier 1.
3. **Parser failure on imported résumé:** the most likely first-impression failure (Setup step). At least a sentence in `walkthrough.md#setup` saying "if extraction looks wrong, edit experiences/bullets manually in the Corpus tab." Tier 2.
4. **Linux Playwright system-deps fallback:** a known sharp edge on Ubuntu LTS. A concrete `apt install` line (or pointer to Playwright's own fallback CLI) in `install.md#linux`. Tier 2.
5. **Switching users / two-terminal collisions:** edge cases. One sentence each, deferred. Tier 3.

---

## Rewrite Ladder

Sequenced commit batches. Each is independently committable; no batch depends on a later one.

### B1 — Canonical cost anchor + jargon first-use definitions (S)

- **Scope:** README.md only.
- **One-line summary:** add an HTML anchor at the cost paragraph; define LLM, JD, ATS, and corpus on first use; tighten the line-5 billing disclaimer.
- **Estimated commit size:** S (6–8 line edits, no new sections).
- **Depends on:** nothing.
- **Why this order:** unblocks B2 and B3 (both link back to the cost anchor). The acronym + corpus definitions are small edits but remove four jargon-first-use issues in one pass — the README is the entry-point doc and stands alone for every reader who never opens walkthrough.md.

### B2 — install.md cost + voice + troubleshooting cleanup (M)

- **Scope:** docs/install.md.
- **One-line summary:** replace inline cost range with link to README anchor; flip "First-run walkthrough" intro from reference-voice to teaching-voice; drop the commit SHA from the JSON-malformed troubleshooting entry; add an Ubuntu-specific Playwright deps note.
- **Estimated commit size:** M (4 distinct edits, ~30 lines total).
- **Depends on:** B1 (anchor target).
- **Why this order:** install.md is the most-trafficked first-time doc; getting it consistent with README before the walkthrough changes makes the install→walkthrough handoff coherent.

### B3 — walkthrough.md voice + jargon-introduction pass (M)

- **Scope:** docs/walkthrough.md.
- **One-line summary:** add orienting H1 sub-line; expand the "deterministic vs. fuzzy" legend gloss into a 2-sentence sidebar; add Sonnet/Haiku role parenthetical on first use; add a one-line consequence after the "why pointed" explanation in Step 2; fix the Setup-node `opt` misclassification in the User Flow diagram.
- **Estimated commit size:** M (5 distinct edits + 1 diagram edit, ~40 lines total).
- **Depends on:** B1 (linking cost anchor where per-step cost numbers appear).
- **Why this order:** the walkthrough is the single most load-bearing user-facing doc — fix its readability before adding to it (B4–B6).

### B4 — Failure-mode coverage expansion (M)

- **Scope:** docs/install.md (Troubleshooting §) + docs/walkthrough.md (new "If something goes wrong mid-wizard" subsection).
- **One-line summary:** add Tier 1 failures from the audit (API 4xx/5xx, network drop, mid-wizard state recovery, parser failure on import); add Tier 2 Linux Playwright deps fallback.
- **Estimated commit size:** M (~5 new troubleshooting entries + 1 new subsection, ~60 lines).
- **Depends on:** B2 (so troubleshooting tone is consistent with the voice fix); does NOT depend on B3.
- **Why this order:** failure-mode coverage is a content addition, not a voice fix — separable from B3 and good as a focused review pass.

### B5 — vision.md punch-first + jargon first-use + dev-link soft-gating (S)

- **Scope:** vision.md.
- **One-line summary:** move the "one question, honestly" quote above the Purpose block; define LLM, ATS, JD on first use (or add an acronym block under the H1); soft-gate the PERF_ANALYZE.md link as "(dev-facing)" or drop it; minor copy edits.
- **Estimated commit size:** S (3–4 edits, ~15 lines).
- **Depends on:** nothing.
- **Why this order:** standalone polish; can land any time after B1 but conceptually belongs after the user-facing docs (B2–B4) are settled. Mirrors B1's acronym discipline so vision.md stands alone the way README does.

### B6 — Information-flow diagram tightening (S)

- **Scope:** docs/walkthrough.md, Diagram 2 only.
- **One-line summary:** elevate the Corpus subgraph visually (stroke-width or doubled-border); add a one-node caption inside the diagram so the prose doesn't have to do the diagram's job.
- **Estimated commit size:** S (1 diagram edit, ~10 lines of Mermaid).
- **Depends on:** B3 (B3 already touches the User Flow diagram; coherent to land this in a separate, isolated commit).
- **Why this order:** small, low-risk; deferring lets the diagram changes get their own focused review.

### B7 — Worked-example specification commit (M)

- **Scope:** new file `docs/walkthrough_example.md` (per the Worked Example Specification above), plus a one-line "see also" pointer from `docs/walkthrough.md`.
- **One-line summary:** add a single synthetic-candidate + synthetic-JD walkthrough that threads through all 6 steps with concrete decisions, costs, and outcomes.
- **Estimated commit size:** M (one new file ~150–250 lines, plus a 1-line link from walkthrough.md).
- **Depends on:** B3 (the walkthrough's voice and jargon decisions set the precedent the example should match).
- **Why this order:** highest-value content addition, but it sits on top of all the readability fixes — write the example using the cleaned-up voice rather than the current one.

### B8 — Screenshot capture pass (L)

- **Scope:** all four docs per the Screenshot Manifest above.
- **One-line summary:** capture the 10 manifest screenshots from a fresh-state app run; place them at the anchors specified; add `alt` text matching the annotations column.
- **Estimated commit size:** L (10 image files + 10 markdown insertions across 3 docs).
- **Depends on:** B3 + B7 (the walkthrough's structure and example should be settled before the visuals lock in).
- **Why this order:** last, because images are the most expensive to redo and changes to surrounding prose can invalidate captures.

---

End of audit.
