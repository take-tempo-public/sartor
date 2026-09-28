# Docs information architecture — D1 design (Epic D)

> **Purpose:** the Epic D design every later Epic D sprint executes against — the target
> `docs/user/` vs `docs/dev/` tree (with a file-by-file mapping that is D2's work order), the
> two onboarding ladders, the link policy for moving docs without rewriting historical
> records, and the doc-governance uplift (publication registry, audience-tag, wordmark,
> banned-words and enumeration-drift lints, the link-check extension, the doc-writing skill).
> **Audience:** `dev`
> **Authoritative for:** the target docs tree and the old→new path mapping; the user and dev
> onboarding ladders; the Epic D link policy (records frozen, live docs rewritten by script,
> the moved-paths map); the design of the Epic D doc lints and the doc-writing skill; the
> explicit-publication rule. It **extends**
> [`documentation-architecture.md`](documentation-architecture.md), which stays authoritative
> for the L0–L3 source chain, the Fumadocs-as-projection model, and the `DOC-STATUS`
> convention. Scope comes from [`RELEASE_ARC.md`](RELEASE_ARC.md) §"Epic D", which governs if
> the two disagree.

Written on `feat/docs-ia-design` (Epic D, sprint D1), 2026-09-27. **Design only:** it moves
no files (D2), writes no user or dev content (D3), and implements no lint (D4). Every design
choice below cites an audit finding or a source; where a choice is the owner's to make, it is
listed under [Open decisions](#open-decisions-for-the-owner) instead of being decided here.

---

## Inputs

| Input | What it is |
|---|---|
| [`reviews/2026-09-docs-ia/10-ux-onboarding.md`](reviews/2026-09-docs-ia/10-ux-onboarding.md) | `ux-onboarding-designer` audit of the user docs (cited **UX-§n**). **Read its correction block first:** its headline "stale hosted site" finding was read from a stale gitignored local build and does not hold. |
| [`reviews/2026-09-docs-ia/20-dx.md`](reviews/2026-09-docs-ia/20-dx.md) | DX-expert audit of the contributor path (cited **DX-nn**) |
| [`reviews/2026-09-docs-ia/30-technical-writer.md`](reviews/2026-09-docs-ia/30-technical-writer.md) | Technical-writer audit against the style guide (cited **TW-§n / TW-Fn**) |
| [`reviews/2026-09-docs-ia/40-research.md`](reviews/2026-09-docs-ia/40-research.md) | Best-practices digest (cited **R-§n**). Only the 11 quotes listed in its "Raw re-check" note were matched against raw HTML, and only those are quoted here. |

### Facts measured by this session (at `88c0011`)

- **Publication follows the header, not a decision.** A fresh
  `python scripts/project_docs_to_mdx.py` printed
  `OK — 42 pages projected to docs-site/content/docs (5 user-tier, 37 dev-tier)`. The 37 dev
  pages include two handoff briefs (`dev-handoffs-epic-b-design-brief`,
  `dev-handoffs-epic-c-design-brief`), a diagnosis dossier
  (`dev-diagnosis-compose-summary-draft-settle-hole`), two reviews, four perf records and
  `dev-v1-0-5-verification`. Separately, `check_doc_frontmatter.PUBLISHED_DOC_FILES` defines
  "published" with its own 15-file list. So "published" currently has two definitions that
  don't agree (DX-05).
- **The projection is gitignored build output.** `.gitignore:134` ignores
  `docs-site/content/docs/*.mdx`. `.github/workflows/docs-deploy.yml:67-72` regenerates it on
  every deploy. A contributor's local copy can therefore sit months stale and look
  authoritative: one audit read a 2026-07-26 copy (UX correction block).
- **Most inbound links to the move candidates come from live docs, not records.** Files
  containing a markdown link to each candidate (`git grep -l "]([^)]*<name>"`):

  | Target | Total | From records |
  |---|---|---|
  | `architecture.md` | 43 | 3 |
  | `walkthrough.md` | 10 | 2 |
  | `install.md` | 6 | 1 |
  | `walkthrough_example.md` | 4 | 1 |
  | `template_authoring.md` | 0 | 0 |

  RELEASE_ARC's "~101 inbound referencing files" for `architecture.md` also counts
  backtick/path mentions (in code, hooks and tests), which D2's C-10 enumeration must grep
  separately.
- **The link checker spends most of its time on per-link syscalls.**
  `python -m cProfile -s cumtime scripts/check_doc_links.py` over 540 files ran 3.51 s total,
  3.24 s of it in `check_links`. Of that, 1.55 s was `Path.resolve()` (4,978
  `nt._getfinalpathname` calls) and 0.62 s was `Path.exists()`, across 2,489 link targets. The
  other two doc checks take 0.43 s (`check_doc_frontmatter`) and 0.67 s
  (`check_doc_single_home`) wall clock. Bare interpreter startup on this box was about
  0.4–0.7 s, so both are mostly startup.

---

## 1. Principles the design applies

1. **Two audiences, one front door each.** `docs/user/` assumes no technical knowledge; every
   other doc is `dev`, as RELEASE_ARC defines it. The dev ladder **starts where the user
   ladder ends**, so a contributor has first run the product as a user (R-§2; DX
   implication 4).
2. **Type before topic.** Each live doc is one Diátaxis form. Diátaxis "identifies four
   distinct needs, and four corresponding forms of documentation"
   ([diataxis.fr](https://diataxis.fr/), raw-verified). The target tree is organized by
   audience, then by ladder rung. Diátaxis type is a **per-doc property** (declared in the
   header, §5.3), not a directory level, because Sartor's doc set is small enough that
   type-named directories would mostly hold one or two files each (TW-§1).
3. **Records are history, not documentation.** Handoffs, ledgers, diagnoses, blast-radius
   dossiers, reviews and perf runs are **frozen in place and never published**. PEP 1 is the
   outside precedent: once a PEP is resolved, "a PEP is considered a historical document
   rather than a living specification"
   ([PEP 1](https://peps.python.org/pep-0001/), raw-verified). Nygard's ADR guidance is the
   supersession half: "keep the old one around, but mark it as superseded"
   ([Nygard](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions),
   raw-verified).
4. **Publication is an explicit decision with one definition** (DX-05, DX implication 2).
5. **Enforcement before discipline (charter C-11).** Every rule in §5 names the mechanism
   that fails closed, or is labelled **unenforced** in the same line.
6. **Incremental adoption.** "Decide on *one* thing … Do that thing. And then repeat"
   ([Diátaxis start-here](https://diataxis.fr/start-here/), raw-verified). D2 moves files
   without rewriting prose, and D3 then rewrites content inside a structure that already
   holds.
7. **Stdlib first.** The existing checks are stdlib-only and already cover most of what an
   offline link checker adds (R-§4). A new binary (Vale, lychee, markdownlint) inside the
   pytest gate either skips when absent, which isn't fail-closed, or becomes a hard
   dependency (charter D-1). §5 therefore specifies native checks. See also
   [Open decision O-5](#open-decisions-for-the-owner).

---

## 2. Target tree

```
README.md                  front door, all audiences (stays; GitHub community-health location)
vision.md                  evaluator-facing why (stays; audience `user`)
ACCESSIBILITY.md           stays; audience `user`+`dev` (currently mis-tagged dev: UX-§3b, TW-§2)
SECURITY.md · CONTRIBUTING.md · CODE_OF_CONDUCT.md · CHANGELOG*.md
                           stay at root (GitHub community-health convention, R-§3)
AGENTS.md · CLAUDE.md      stay at root (agent tool convention; see O-2)

docs/
  user/                    NEW — zero-technical-knowledge product docs (the user ladder)
    README.md              NEW — user index: the ladder, one line per rung
    install.md             ← docs/install.md (user half; maintainer sections → dev, D3)
    walkthrough.md         ← docs/walkthrough.md ("Under the hood" blocks → dev, D3)
    walkthrough-example.md ← docs/walkthrough_example.md
    iterating.md           NEW (D3) — rung 3: second application, refine, Prior Applications,
                           Candidate Memory (UX-§8)
    coaching.md            NEW (D3) — rung 4a: multi-candidate use (UX-§8)
    templates.md           ← docs/template_authoring.md (user half; maintainer half → dev, D3)
  dev/
    README.md              NEW — dev front door: the dev ladder + a routed index
                           (reference · runbooks · designs · templates · records) (DX-07)
    architecture.md        ← docs/architecture.md
    system-model.md        ← docs/system-model.md
    PRODUCT_SHAPE.md       ← docs/PRODUCT_SHAPE.md
    screenshot-capture.md  ← docs/ux/screenshot_capture.md
    <14 live-reference loose docs stay>   (table §2.2)
    archive/               NEW — the 18 finished-design / stale loose docs (table §2.2)
    handoffs/ ledger/ diagnosis/ blast-radius/ reviews/ perf/ excellence-walk/
    flake-rates/ prov/ work/   UNCHANGED — frozen records and machine-read paths
  governance/              UNCHANGED (L0; hooks and scripts read these paths)
  wiki/                    UNCHANGED (L2; wiki SCHEMA governs)
  screenshots/             UNCHANGED (shared assets referenced by both tiers)
  work/                    UNCHANGED (isidium tenant config)
  ux/onboarding_audit_2026-05-25.md    UNCHANGED (record — frozen in place)
  bundled_templates_LICENSE.md         UNCHANGED (legal text; not a doc)
```

**Why records stay where they are rather than moving to `docs/dev/records/`** (DX
implication 1 proposes moving them):
- `handoffs/`, `ledger/`, `diagnosis/` and `blast-radius/` are paths that hooks and scripts
  read: `require-evidence-before-fix`, `require-consumer-enumeration`, `restore-evidence`,
  `verify_doc_template.py` and `print_handoff_pointer.py`.
- Every past handoff pointer names a path under `docs/dev/handoffs/`.

Moving them would rewrite records (breaking principle 3) and re-plumb every gate that reads
them, only to change a directory name. The dev front door (`docs/dev/README.md`) gives the
navigation benefit without the move.

### 2.1 Mapping — live docs outside `docs/dev/`

| Current path | Target | Tier | Diátaxis | Notes |
|---|---|---|---|---|
| `README.md` | stays | user+dev | explanation | Front door; its dev sections (`README.md:235-276`) shrink to links in D3 (TW implication 2) |
| `vision.md` | stays | user | explanation | Fix the stale "C-0…C-6" (`vision.md:94`; charter runs to C-12, TW-F3) in D3 |
| `ACCESSIBILITY.md` | stays | user+dev | reference | Re-tag with the explicit token (UX-§3b) |
| `SECURITY.md` | stays | dev | reference | Also lacks the budget guards `install.md:24-26` sends readers to (TW-F1) — D3 |
| `CONTRIBUTING.md` | stays | dev | how-to | Rung D1 of the dev ladder; fix the `--no-ff` and "latent CI" contradictions (DX-03, DX-11) |
| `CODE_OF_CONDUCT.md` | stays | dev | reference | — |
| `CHANGELOG.md`, `CHANGELOG-archive.md` | stay | dev | reference (record-like) | History; lint-exempt for wordmark (TW implication 4) |
| `AGENTS.md`, `CLAUDE.md` | stay | dev | reference | See [O-2](#open-decisions-for-the-owner) |
| `docs/install.md` | `docs/user/install.md` | user | how-to | Maintainer runbook (`install.md:305-337`) → `docs/dev/` in D3 |
| `docs/walkthrough.md` | `docs/user/walkthrough.md` | user | tutorial | Walkthrough still says Generate always calls Sonnet; `architecture.md` says only when Compose wasn't frozen (TW-F2) — D3 |
| `docs/walkthrough_example.md` | `docs/user/walkthrough-example.md` | user | tutorial | Kebab-case on move |
| `docs/template_authoring.md` | `docs/user/templates.md` | user | how-to | Split; currently has no header and isn't on the site (UX B5) |
| `docs/architecture.md` | `docs/dev/architecture.md` | dev | explanation | 43 link-bearing files; 3 are records → moved-paths map (§3) |
| `docs/system-model.md` | `docs/dev/system-model.md` | dev | explanation | Its wiki twin is tagged `user` (TW-§2); the tier conflict is D3's to settle |
| `docs/PRODUCT_SHAPE.md` | `docs/dev/PRODUCT_SHAPE.md` | dev | explanation | Historical sections → `archive/` in D3 (DX implication 10) |
| `docs/ux/screenshot_capture.md` | `docs/dev/screenshot-capture.md` | dev | how-to | — |
| `dashboard/README.md`, `recall/README.md`, `skills/README.md`, `.githooks/README.md`, `agents/*.md`, `commands/*.md`, `skills/**` | stay | dev | reference | Code-adjacent; the directory is the home. Catalogs generated or checked, not restated (§5.5) |

### 2.2 Mapping — the 32 loose `docs/dev/*.md` files

This follows the DX-07 classification table in
[`20-dx.md`](reviews/2026-09-docs-ia/20-dx.md). Live reference stays in `docs/dev/`.
Process-record and stale docs move to `docs/dev/archive/`, keep their filenames, and get a
superseded/historical banner, which is the only edit permitted to them. Inbound links from
records to these files resolve through the moved-paths map (§3).

- **Stay, live reference (14):**
  - `AGENT_FAILURE_PATTERNS.md`
  - `AGENT_HANDOFF_TEMPLATE.md`
  - `doc-style-guide.md`
  - `documentation-architecture.md`
  - `decisions.md`
  - `RELEASE_ARC.md`
  - `RELEASE_CHECKLIST.md`
  - `GROUNDING_METRIC.md`
  - `memory-architecture.md`
  - `EXTRACTION.md`
  - `keep-ledger.md`
  - `docs-site-deploy.md`
  - `n1-baseline-pipeline.md`
  - `nursery.md`
- **To `archive/`, process records (12):**
  - `COMPOSE_REWRITE_DIAL.md`
  - `app-blueprints-design.md`
  - `avatar-voice-tone-guidance.md`
  - `avatar-citation-format-guidance.md`
  - `board-forge-sync-review.md`
  - `epic-a-chain-design-corrections.md`
  - `gate-window-class-study.md`
  - `governance-extraction-design.md`
  - `handoff-integrity-design.md`
  - `kit-adoption-design.md`
  - `pagedjs-preview-spike.md`
  - `self-documenting-loop-design.md`
- **To `archive/`, stale (6):**
  - `generation-experience-rearchitecture.md`
  - `dependency-triage-pre-v1.1.0.md`
  - `ORCHESTRATION_PLAYBOOK.md`
  - `V1_0_5_VERIFICATION.md`
  - `window-8.5-findings.md`
  - `window-8.5-walkthrough.md`

**D2 must verify two classifications before moving anything.** DX marked
`dependency-triage-pre-v1.1.0.md` and `ORCHESTRATION_PLAYBOOK.md` as "unverified whether
still used". `epic-a-chain-design-corrections.md` (31 inbound) and
`handoff-integrity-design.md` are still cited as the rationale for live rules
(`n1-baseline-pipeline.md`, `AGENTS.md` step 5). Archiving keeps them readable, but D2's C-10
enumeration has to confirm that every live citer is rewritten.

---

## 3. Link policy

1. **Records are never rewritten.** This covers the record directories above, the
   `docs/ux/onboarding_audit_*` file, `docs/dev/archive/**` after its one-time banner, and
   `CHANGELOG*.md` entries. A link inside a record keeps the path that was true when it was
   written.
2. **Live docs are rewritten by script, in the same commit as the move.** D2 gets a
   `scripts/docs_move.py` that takes a mapping (§2.1/§2.2 as data), performs the `git mv`s,
   and rewrites relative links in live docs only. The same commit carries the D2 coupling
   updates (§6). No hand-edited link rewrites.
3. **The moved-paths map keeps records green without rewriting them.** A new committed file,
   `docs/dev/moved-paths.json` (old repo path → new repo path), is written by
   `docs_move.py`. `check_doc_links.py` consults it **only for links originating in a
   record** (the §3.1 path classes). When such a link's target is missing, it resolves through
   the map and passes if the new target exists, including the anchor.

   A link from a live doc to an old path still fails: live docs must be rewritten, and the
   map can't be used to hide that. **Mechanism:** the existing link gate, extended. It fails
   closed.
4. **Projection links follow the map too.** `project_docs_to_mdx.py` already rewrites
   cross-doc links at projection time (`documentation-architecture.md` §"Fumadocs sourcing").
   It will read the same map, so a published record-derived page, if any survives §5.1, never
   links to a dead route.
5. **External links stay unchecked in the gate**, as today. An optional non-gating weekly
   external-link check is possible later; it is not designed here.

---

## 4. Onboarding ladders

**User ladder** (`docs/user/README.md` lists it; the site's "Using Sartor" section follows
this order):

| Rung | Reader's goal | Doc | State today |
|---|---|---|---|
| U0 | "What is this, is it for me?" | `README.md`, `vision.md` | Strong (UX-§8) |
| U1 | Install, see it work (demo mode, `--doctor`) | `user/install.md` | Strong content. The cost anchor is circular: `install.md:571` → `README.md#install`, whose `README.md:160` points back at install (UX finding, verified) — D3 |
| U2 | First tailored résumé | `user/walkthrough.md`, `user/walkthrough-example.md` | Strongest rung (UX-§8) |
| U3 | Iterate: second application, refine, find earlier work | `user/iterating.md` (new) | **Missing.** Prior Applications and Candidate Memory appear in no user doc (UX-§8) |
| U4a | Coach several candidates | `user/coaching.md` (new) | **Missing** beyond README prose (UX-§8) |
| U4b | Custom templates | `user/templates.md` | Exists as a mixed user/maintainer doc with no header (UX B5) |
| — | Accessibility, privacy ("what stays on your machine"), troubleshooting | `ACCESSIBILITY.md`, `README.md` §"What stays on your machine", `user/install.md` §troubleshooting | Linked from the user index, not rungs |

**Dev ladder** (`docs/dev/README.md`; the site's "Building on Sartor" section). It
**begins after U1**: a contributor has seen demo mode work.

| Rung | Goal | Doc |
|---|---|---|
| D0 | Dev install (`[dev]` extras, Playwright) | `CONTRIBUTING.md` (+ the maintainer half of today's `install.md`) |
| D1 | First green gate | `CONTRIBUTING.md` **citing** `scripts/gate.py`. The runtime and the 1.0 GB memory floor are stated once, where the gate prints them (DX-01, §5.5) |
| D2 | Map of the system | `dev/architecture.md`, `dev/system-model.md` |
| D3 | First change | a task index in `dev/README.md` (where prompts / routes / templates / the deterministic boundary live), plus the code rules in `AGENTS.md` |
| D4 | Why the rules are binding | `governance/charter.md`, `governance/enforcement.md`, the hook catalog |
| D5 | Maintainer lane | the owner's session protocol (handoffs, ledger, releases, the N=1 pipeline) — see [O-2](#open-decisions-for-the-owner) |

**The design principle this encodes:** an outside contributor stops at D3 or D4 and is never
routed through D5 by default. Today `CONTRIBUTING.md` tells humans the whole AGENTS contract
applies to them, which pulls them into handoffs and plan markers (DX-02).

---

## 5. Governance uplift (D4 implements)

**One shared corpus pass, not one scan per lint.** A new `scripts/doc_corpus.py` does the
following once per process:
- enumerate tracked `*.md` with `git ls-files` (one subprocess)
- read each file once
- expose the header fields, unfenced lines and the tracked-path set

Consumers:
- `check_doc_links.py`, `check_doc_frontmatter.py` and `check_doc_single_home.py`, refactored
  onto it
- the new lints below

They run as one pytest module in the gate. Two rules follow from the profile under
[Facts](#facts-measured-by-this-session-at-88c0011):
- **Link-target existence is answered lexically**: `posixpath.normpath` against the tracked
  set, falling back to `git check-ignore` only on a miss. This replaces
  `Path.resolve()` + `exists()` per link, which is about 2.2 s of today's 3.2 s `check_links`
  on this machine. The ~2 s saving is **estimated from the profile, not yet measured.** D4
  records before/after timings per the performance-metrics convention.
- **Lazy by scope**: a lint that covers only the user tier filters paths before reading
  bodies. The shared read is eager for the files at least one active lint needs, and the
  reason is recorded at that site in the code: the gate runs every lint every time, so one
  read per file is the minimum.

| # | Lint | Rule | Scope / exclusions | Stage | Fails closed? |
|---|---|---|---|---|---|
| 5.1 | **Publication registry** | One registry (`scripts/doc_registry.py`) lists every published doc with its tier and nav order. `project_docs_to_mdx.py` projects **only** registry entries. `check_doc_frontmatter` checks **all** registry entries. `meta.json` is generated from it with "Using Sartor" / "Building on Sartor" separators. A doc outside the registry is never published, whatever its header says | Registry entries only; records can't be registered (a record-path entry fails the gate) | gate + docs-deploy | Yes |
| 5.2 | **Audience token** | Every registered doc's `**Audience:**` starts with `` `user` ``, `` `dev` `` or both. The projector's path fallback table (`project_docs_to_mdx.py:133-135`) is **deleted**, not grown | Registry entries | gate | Yes. Adds a tier decision for about 14 docs that rely on the fallback today (TW implication 1). These are human decisions made in D2, not mechanical fills |
| 5.3 | **Diátaxis type** | Header gains `**Type:**` (tutorial / how-to / reference / explanation) on `user`-tier docs | User tier only | gate | Yes for presence. Whether the type is *correct* is **unenforced** (judgment) |
| 5.4 | **Wordmark** | Spec per TW implication 4: flag `sartor.` followed by whitespace+lowercase, `'s`, `-`, or a lowercase continuation line. Allow the title form. Skip fenced code, backtick spans and paths | Exclude `docs/wiki/**` and `docs/dev/reviews/**` (item 2, as RELEASE_ARC requires), all record classes, `CHANGELOG*.md`, legal lines | gate | Block on user tier + L1; **warn** on the ambiguous end-of-sentence form. Blocked on [O-1](#open-decisions-for-the-owner) |
| 5.5 | **Enumeration drift** ("code-truth anchors") | A doc that enumerates something code enumerates must match it, or must link to it instead of listing. Initial pairs: gate steps ↔ `scripts/gate.py:_STEPS` (DX-01: four different descriptions); deterministic modules ↔ `tests/test_construction_boundary.py:DETERMINISTIC_MODULES` (TW-F4: lists of 8/7/7/5 against 8); subagent roster ↔ `agents/*.md` (DX-09: 9 listed vs 11); charter clause range ↔ charter headings (TW-F3) | Live docs only; records keep their historical lists | gate | Yes |
| 5.6 | **Banned words (tiered)** | **Block** on the user tier: TW implication 5's list (`simply`, `easy`/`easily`, `obviously`, `seamless(ly)`, `powerful`, `revolutionary`, `sanity check`, `just` + imperative). **Warn** list likewise. Bare `just` is **not** banned (18 user-tier hits, none blaming the reader) | User tier; `<!-- lint-allow -->` regions only in `doc-style-guide.md`'s own "Don't" examples | gate | Block tier yes; warn tier is a report |
| 5.7 | **Jargon-first-use + tracker IDs** | User tier: a closed acronym list (LLM, JD, ATS, API, SSE) must be expanded at or before first use; internal IDs (`PX-\d+`, `C-\d+`, `item \d+`, `Sprint \d`) are blocked | User tier | gate | Yes; header acronym blocks count as the expansion (TW implication 6) |
| 5.8 | **Links** | `check_doc_links.py` plus: the moved-paths map (§3.3); `[[wikilink]]` syntax outside `docs/wiki/` flagged; charter clause anchors (`C-\d+` gets its own heading, so links deep-link and 5.5 can verify them — TW implication 10) | As today (all tracked `.md`) | gate | Yes |
| 5.9 | **Single-home, widened** | Add `docs/wiki/**` vs L1, and shingled near-match of ≥ ~25 tokens | L1 + wiki | gate, **report-only** first, with a reviewed-pairs allowlist | **Unenforced** at first (high false-positive rate, TW implication 8). Stated here so nobody counts it as protection |

**Deliberately not adopted:**
- **Vale, markdownlint and lychee as gate dependencies** (principle 7; R-§4 comparison
  table). If prose-style checking beyond the term lists above is ever wanted, Vale is the
  candidate, run in CI only; that is [O-5](#open-decisions-for-the-owner).
- **A CLAUDE.md size lint.** Claude Code's docs advise to "target under 200 lines per
  CLAUDE.md file" ([Claude Code memory](https://code.claude.com/docs/en/memory),
  raw-verified), and the AGENTS.md + CLAUDE.md pair is about 42 KB always-loaded (DX-04).
  Size is an input to [O-2](#open-decisions-for-the-owner), not something to lint before
  that decision.

### 5.10 The doc-writing skill

It lives in the repo-root `skills/` (the plugin-activation convention). It **orders and
invokes** the rules and restates none of them, so the single home of each rule stays
`doc-style-guide.md` or the lint registry (TW implication 12). Its steps:
1. Pick the tier (`user`/`dev`) and the Diátaxis type.
2. Find the rung it serves (§4). A doc that serves no rung and no reference need is a
   candidate for not being written.
3. Write the P/A/A(+Type) header.
4. Cite instead of restating anything code enumerates (§5.5).
5. Register it (§5.1) if it should be published.
6. Run the corpus lints and fix every block.

Its evaluation plan belongs to D4.

---

## 6. D2 coupling checklist (the split's same-commit obligations)

RELEASE_ARC §D2 already names these; this design fixes their shape:

- **Entry gate:** run `python scripts/wiki_freshness.py` and clear elevated drift with
  `/wiki-self-update` **before** the first move (RELEASE_ARC §D2).
- **Enumeration first (C-10):** `docs/dev/blast-radius/docs-split.md` must enumerate, per
  moved path, every name it goes by:
  - markdown links (counts above)
  - backtick/path mentions in code, hooks, tests and scripts
  - `wiki_relevance.py` entries
  - `PUBLISHED_DOC_FILES`
  - the projector's slug map
  - `AGENTS.md`/`CLAUDE.md` pointers
  - `llms.txt`
- **In the move commit:**
  - `scripts/wiki_relevance.py` classifications (its audit test fails on any unclassified or
    vanished top-level entry)
  - the §5.1 registry (which replaces the projector's path table)
  - the generated two-tier `meta.json`
  - the moved-paths map
  - the scripted live-doc link rewrite
  - `docs/user/README.md` and `docs/dev/README.md` stubs, so the ladders resolve on day one
    even before D3 writes their content
- **Unpublish before the split:** once §5.1 exists, the handoff briefs, the diagnosis and the
  reviews/perf records drop off the site. RELEASE_ARC puts lint implementation in D4, but the
  registry is D2's natural vehicle, because D2 has to touch the projector anyway. See
  [O-4](#open-decisions-for-the-owner).

## 7. Relationship to `documentation-architecture.md`

That doc stays the home of the L0–L3 chain, the projection model and `DOC-STATUS`. This design
supersedes three of its specifics:
- its L1 row that treats `dev/**` as one layer (DX-06), which becomes the §2 kinds
- its `meta.json` "ICP + pillar ordering" claim, which becomes the §5.1 generated two-tier nav
- its "Recommendations / sequencing" status, most of which has shipped (DX-06)

This branch adds a pointer and a dated correction note to that doc's header rather than
rewriting it. Its body rewrite is D3 content.

---

## Open decisions for the owner

These are the owner's calls. This design does not decide them, and D2 shouldn't start until
O-1 and O-4 are settled, because both change D2's commit contents.

- **O-1 — Wordmark in UI copy.** `doc-style-guide.md` declares that it covers "user-facing
  UI copy" (`:9-10`) and says `Sartor` in sentences. But `avatar-voice-tone-guidance.md:942`
  freezes the assistant's identity as lowercase "sartor.", and the shipped string at
  `templates/index.html:1148` reads "Ask how sartor. works". The wiki also has 67 bare `sartor` (TW-§3). The lint (5.4) encodes whichever
  rule is chosen.
- **O-2 — Split `AGENTS.md`?** DX implication 6 proposes two parts:
  - the code rules (universal, for any human or agent)
  - the owner's session protocol (handoffs, ledger, plan markers, pointer checks), moved into
    an owner-lane doc that AGENTS.md links to

  This cuts the ~42 KB always-loaded budget and stops routing outside contributors through D5.
  The constraint it has to respect: AGENTS.md must not become an import shell, because
  non-Claude agents read it raw (AGENTS.md header). Whatever stays must still bind every
  agent.
- **O-3 — Archive the 18 loose docs (§2.2) in D2, or leave them loose and just unpublish?**
  Archiving costs D2 a larger C-10 enumeration (`epic-a-chain-design-corrections.md` alone has
  31 inbound). The payoff is a `docs/dev/` root that is all live reference.
- **O-4 — Pull the publication registry (5.1) and the audience-token requirement (5.2)
  forward into D2?** Recommended: D2 must rewrite the projector's path table anyway, and
  doing both at once avoids touching the projector twice.
- **O-5 — Vale in CI (non-gating) for prose style?** Recommended: no, for v1.1.0. Revisit if
  the term lists in 5.6/5.7 prove insufficient.
- **Also for the owner, outside D1's scope:** three live contradictions DX flags as harmful
  now rather than IA work.
  - `CONTRIBUTING.md:57` and `agents/git-flow.md:19` instruct `git merge --no-ff` locally,
    against AGENTS.md step 4's PR-only flow. The `git-flow` subagent would follow the local
    merge rule.
  - `CONTRIBUTING.md` calls CI "latent".
  - The gate is described as four steps; `scripts/gate.py:72-82` runs six.

  D3 fixes these by default. The owner may prefer an earlier small branch.

## Verification this design carries forward

- **D2 done:** every path in §2.1/§2.2 is either moved or explicitly deferred in D2's
  blast-radius dossier; `python -m scripts.gate` is green, including `test_doc_links.py` with
  the moved-paths map and `test_wiki_relevance_classification.py`; the projector publishes
  only registry entries.
- **D4 done:** each §5 row has a test that fails on a seeded violation (the mutation-probe
  precedent from Epic C's R2); link-check timing is recorded before and after the lexical
  change.
