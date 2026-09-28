> **Purpose:** Best-practices digest, with fetched-and-quoted citations, on end-user onboarding docs, contributor/agent onboarding docs, open-source docs IA frameworks, and docs-governance-as-code tooling — the external-evidence input to the Epic D docs information-architecture design.
> **Audience:** `dev` — Epic D D1 input
> **Authoritative for:** what the cited external sources say (as fetched 2026-09-27) and this digest's applicability notes for Sartor; NOT authoritative for any Sartor design decision (the D1 design doc owns those).

# Docs IA research digest (Epic D / D1)

## Method and citation discipline

- Every citation below was fetched this session (2026-09-27) with a web-fetch tool. Each
  entry gives URL, page title, and a short quote.
- **Stated limit (C-0):** the fetch tool returns the page through a summarizing model, which
  was asked for verbatim sentences. Quotes are what that tool returned inside quotation marks;
  they were not diffed against raw HTML. Before any quote is promoted into a normative Sartor
  doc, re-open the URL and confirm the wording.
- **Raw re-check (2026-09-27, D1 invoking session).** The 11 quotes the D1 design doc relies
  on were re-fetched as raw HTML (`urllib`, tags stripped, whitespace/case/emphasis
  normalized) and substring-matched: **11/11 OK** — Diátaxis "four corresponding forms of
  documentation" and "Do that thing. And then repeat."; Claude Code memory "target under 200
  lines per CLAUDE.md file" and "Claude treats them as context, not enforced configuration";
  agents.md "README.md files are for humans"; PEP 1 "a PEP is considered a historical document
  rather than a living specification"; Nygard "keep the old one around, but mark it as
  superseded"; GitHub community-health "the root of the repository, the"; Write the Docs
  "Accept (some) Repetition"; lychee "Only check local files and block network requests";
  Vale installation "winget install". Every other quote below remains summarizer-returned
  and unchecked against raw HTML.
- Anything not fetched, or fetched without usable content, is listed under
  **Unverified — not cited** at the end and is not relied on.

---

## 1. End-user onboarding documentation

### Key practices

1. **Write for what the reader is missing, not what the author knows.** Google's course
   frames documentation as a gap: "good documentation = knowledge and skills your audience
   needs to do a task − your audience's current knowledge and skills." It names the main risk
   for expert authors: "the curse of knowledge, which means that their expert understanding of
   a topic ruins their explanations to newcomers." For non-specialists it advises "simple words
   over complex words; avoid obsolete or overly-complex English words."
   — <https://developers.google.com/tech-writing/one/audience>, "Audience" (Technical Writing One)

2. **Keep learning separate from doing.** Diátaxis splits a tutorial ("to help the pupil
   acquire basic competence"; it "eliminates the unexpected" and follows "a single line")
   from a how-to guide ("to help the already-competent user perform a particular task
   correctly"; it "will typically fork and branch, describing different routes").
   — <https://diataxis.fr/tutorials-how-to/>, "The difference between a tutorial and how-to guide"

3. **Progressive disclosure.** NN/g defines it as a strategy that "defers advanced or rarely
   used features to a secondary screen, making applications easier to learn and less
   error-prone": "Initially, show users only a few of the most important options," then
   "Offer a larger set of specialized options upon request." For beginners it "helps novice
   users avoid mistakes and saves them the time they would have spent contemplating features
   that they don't need."
   — <https://www.nngroup.com/articles/progressive-disclosure/>, "Progressive Disclosure"

4. **Put help where it's needed; don't lean on up-front tutorials.** NN/g's onboarding study
   found "tutorials didn't improve task performance". It recommends to "avoid creating app
   onboarding whenever possible and instead spend your resources making the UI more usable,"
   and to "highlight features while the user is in the app, through contextual help."
   — <https://www.nngroup.com/articles/mobile-app-onboarding/>, "Mobile-App Onboarding: An Analysis of Components and Techniques"

5. **A short first path to value, plus a real troubleshooting page.** The Good Docs Project's
   quickstart "introduces your users to your application for the first time" and focuses on
   "the **primary feature** of the application". It warns "Lengthy quickstarts can overwhelm
   users". The suggested sections are Overview, Before You Begin, Install, Steps and Next
   Steps. Its troubleshooting template captures "a list of common problems (referred to as
   symptoms) experienced by users, an explanation of the causes, and steps to resolve the
   issue."
   — <https://www.thegooddocsproject.dev/template/quickstart>, "Quickstart Guide";
   <https://www.thegooddocsproject.dev/template>, "The Good Docs Project Templates"

6. **Readers skim.** Write the Docs: "Structure content to help readers identify and skip over
   concepts which they already understand or are not relevant to their immediate questions";
   and "Consider incorrect documentation to be worse than missing documentation."
   — <https://www.writethedocs.org/guide/writing/docs-principles/>, "Documentation principles"

### Applicability to Sartor

- `docs/user/` should open with **one** single-track tutorial: install, first resume, first
  tailored output. It should offer no choices and fence off anything unexpected, per (2).
  Branching material, such as a second resume, a cover letter or another model setting,
  belongs in separate how-to pages.
- The user audience has zero technical knowledge. The curse-of-knowledge risk (1) is highest
  on install, API-key setup and "what is local-first" pages. Terms like "venv", "PATH",
  "API key" and "localhost" each need a definition or a link before first use. Sartor already
  has the `sartor:ux-onboarding-designer` subagent ("jargon-before-definition" audit), which
  can check this.
- (4) argues for in-app contextual help over a docs-first tour. Sartor already has an in-app
  help primitive (`_HELP_REGISTRY`, per project memory). User docs can then be the
  *reference/how-to* fallback rather than the onboarding itself. Link the two; don't
  duplicate them (Sartor's own single-home rule, D5).
- A user-facing **troubleshooting** page keyed by symptom (5) fits a local app whose
  failures are environmental: Python missing, key missing, port busy.
- (6) "incorrect worse than missing" supports gating `docs/user/` more strictly than
  `docs/dev/`, for example by requiring each user page to be tied to a UX-suite screenshot
  or test.
- No conflicts with Sartor's constraints. These are content practices, not tooling.

---

## 2. Developer-experience onboarding (humans and AI agents)

### Key practices

1. **CONTRIBUTING is a distinct file from README.** "Whereas READMEs help people *use* the
   project, contributing docs help people *contribute* to the project."
   — <https://opensource.guide/how-to-contribute/>, Open Source Guides "How to Contribute to Open Source"

2. **GitHub surfaces CONTRIBUTING at the point of contribution.** Guidelines may include
   "Steps for creating good issues or pull requests", "Links to external documentation,
   mailing lists, or a code of conduct" and "Community and behavioral expectations". People
   opening an issue or PR are pointed to the file, and it gets a Contributing tab and a
   sidebar link.
   — <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors>, "Setting guidelines for repository contributors"

3. **Label entry-level work.** "apply the `good first issue` label to issues in your public
   repository so that people can find them when searching by labels"; "adding the
   `good first issue` label can increase the likelihood that your issues are surfaced."
   — <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/encouraging-helpful-contributions-to-your-project-with-labels>, "Encouraging helpful contributions to your project with labels"

4. **An explicit contributor ladder.** The CNCF template: "This contributor ladder outlines
   the different contributor roles within the project, along with the responsibilities and
   privileges that come with them". Members "generally start at the first levels of the
   'ladder' and advance up it as their involvement in the project grows." Roles run from
   Community Participant through Contributor, Organization Member and Reviewer to Maintainer.
   — <https://github.com/cncf/project-template/blob/main/CONTRIBUTOR_LADDER.md>, "Contributor Ladder Template"

5. **Measure responsiveness as a newcomer signal.** CHAOSS Time to First Response: "The first
   response is often crucial as it signals to contributors that the community is active and
   engaging"; "Timely responses can enhance the onboarding experience for new contributors and
   improve retention." It excludes bot responses.
   — <https://chaoss.community/kb/metric-time-to-first-response/>, "Metric: Time to First Response - CHAOSS"

6. **AGENTS.md is agent-facing and separate from README.** "A simple, open format for guiding
   coding agents". "README.md files are for humans: quick starts, project descriptions, and
   contribution guidelines". It is "just standard Markdown. Use any headings you like". In
   nested layouts, "Agents automatically read the nearest file in the directory tree, so the
   closest one takes precedence".
   — <https://agents.md/>, "AGENTS.md"

7. **Agent instruction files are context, not enforcement, and size matters.** Claude Code
   docs: "Claude treats them as context, not enforced configuration. To block an action
   regardless of what Claude decides, use a PreToolUse hook instead." They set a size target:
   "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce
   adherence." And on imports: "CLAUDE.md files can import additional files using
   `@path/to/import` syntax", though "imported files still load and enter the context window
   at launch." The docs also say when AGENTS.md is read directly: "By default, Claude reads
   `AGENTS.md` only when you have no `CLAUDE.md` in your working directory or above it."
   — <https://code.claude.com/docs/en/memory>, "How Claude remembers your project"

8. **Other agents read the same file.** GitHub Copilot agent instructions accept "`AGENTS.md`,
   `CLAUDE.md`, or `GEMINI.md`" and prioritize "the nearest `AGENTS.md` file in the directory
   tree". Path-scoped `.instructions.md` files "apply to requests made in the context of files
   that match a specified path."
   — <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>, "Adding repository custom instructions for GitHub Copilot"

### Applicability to Sartor

- Sartor already follows (1), (2) and (6)–(8) structurally: root `CONTRIBUTING.md`, a
  tool-agnostic `AGENTS.md`, and a `CLAUDE.md` that `@`-imports it. The IA question is
  **size and placement**, not existence.
- Source (7) gives a concrete, cited adherence budget (under 200 lines per file, and imports
  still load at launch). Sartor's `AGENTS.md` + `CLAUDE.md` pair is well above that. A D1
  design could move reference-grade detail into `docs/dev/` pages loaded just-in-time and
  keep the entry files as short routing documents. Sartor's own "do not let this file become
  a pure import shell" rule for AGENTS.md still stands: non-Claude agents read it raw. So the
  trim has to keep the guardrails inline and move only reference detail.
- (7)'s "context, not enforced configuration" matches Sartor's C-11 (a gate, not a note).
  The D1 IA can cite it as external support for keeping enforcement in hooks and the gate,
  not in prose.
- Nested `AGENTS.md` (6) is available if `docs/user/` ever needs agent rules of its own. For
  example, "user docs: no jargon; no dev paths". It costs one more file that all agents read,
  so that is the tradeoff.
- A contributor ladder (4) and `good first issue` (3) are community-scale practices. For a
  solo-maintained repo, a short "your first contribution" how-to in `docs/dev/` is the
  proportionate version. Recommending a full ladder would describe governance that doesn't
  exist (C-0).
- Time-to-first-response (5) needs GitHub API data. It is out of scope for a pytest gate and
  is noted only as a possible later metric.

---

## 3. Open-source docs conventions and IA frameworks

### Key practices

1. **Diátaxis: four needs, four forms.** "Diátaxis identifies four distinct needs, and four
   corresponding forms of documentation - *tutorials*, *how-to guides*, *technical reference*
   and *explanation*."
   — <https://diataxis.fr/>, "Diátaxis"
   Reference vs explanation: "Reference is what a user needs in order help apply knowledge and
   skill, while they are working"; "Explanation is what someone will turn to to help them
   acquire knowledge and skill - 'study.'"
   — <https://diataxis.fr/reference-explanation/>, "Reference and explanation" (Diátaxis)

2. **Adopt Diátaxis one change at a time.** "Decide on *one* thing you could do to it right
   now, however small, that would improve it. Do that thing. And then repeat."
   — <https://diataxis.fr/start-here/>, "Start here - Diátaxis in five minutes"

3. **Good Docs Project templates** cover the same forms plus community docs. A "how-to is a
   concise set of numbered steps to do one task with the product". The Contributing Guide
   "tells users how they can contribute to your open source project and join the community".
   The README template gives "information users need to know about your project." Templates
   for changelogs, glossaries, style guides and user personas are also listed.
   — <https://www.thegooddocsproject.dev/template>, "The Good Docs Project Templates"

4. **GitHub community-health files and their locations.** Supported files include
   CODE_OF_CONDUCT, CONTRIBUTING, SECURITY ("gives instructions on how to report a security
   vulnerability") and SUPPORT ("lets people know about ways to get help with your project").
   Apart from templates and FUNDING, these may sit in "the root of the repository, the
   `.github` folder, or the `docs` folder."
   — <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file>, "Creating a default community health file"
   The community profile checklist "checks to see if a project includes recommended community
   health files, such as README, CODE_OF_CONDUCT, LICENSE, or CONTRIBUTING, in a supported
   location."
   — <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories>, "About community profiles for public repositories"

5. **Docs-as-code.** "Documentation as Code (*Docs as Code*) refers to a philosophy that you
   should be writing documentation with the same tools as code". The tools named are issue
   trackers, version control, plain-text markup, code reviews and "Automated Tests".
   — <https://www.writethedocs.org/guide/docs-as-code/>, "Docs as Code"

6. **Some repetition is acceptable.** "Accept (some) Repetition In Documentation." ("ARID")
   — <https://www.writethedocs.org/guide/writing/docs-principles/>, "Documentation principles"

7. **Historical records are frozen; current truth lives elsewhere.** PEP 1: "PEPs are no longer
   substantially modified after they have reached the Accepted, Final, Rejected or Superseded
   state. Once resolution is reached, a PEP is considered a historical document rather than a
   living specification," and "Formal documentation of the expected behavior should be
   maintained elsewhere".
   — <https://peps.python.org/pep-0001/>, "PEP 1 – PEP Purpose and Guidelines"
   Nygard on ADRs: when a decision is reversed, "keep the old one around, but mark it as
   superseded"; "It's still relevant to know that it _was_ the decision, but is _no longer_
   the decision."
   — <https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions>, "Documenting Architecture Decisions"

### Applicability to Sartor

- **The user/dev split is a different axis from Diátaxis.** Audience (`user` vs `dev`) is
  one axis; form (tutorial / how-to / reference / explanation) is another. A D1 design can
  use audience as the top-level directory and Diátaxis as a front-matter field or
  subdirectory within each. That makes "user tutorial" and "dev reference" both addressable
  without a 4×2 directory explosion. Adopting it incrementally (2) fits Sartor's
  small-branch cadence better than a big-bang restructure.
- **Two record classes, two regimes.** (7) is direct external precedent for Sartor's rule that
  handoffs, ledgers, diagnoses and reviews are never rewritten. The IA should split *living*
  docs (maintained, linted, published) from *records* (frozen at resolution, superseded by a
  new record, excluded from content lints). "Maintained elsewhere" is Sartor's single-home
  rule.
- (4): `SECURITY.md` and `CONTRIBUTING.md` at root already satisfy GitHub's location rule. A
  `SUPPORT.md` is optional; for the user audience it could point to `docs/user/`
  troubleshooting. Moving these files into `docs/` is allowed by GitHub but would split them
  from the root files agents read first. Not recommended without a reason.
- (6) ARID sits in tension with Sartor's D5 single-home gate. The existing
  `check_doc_single_home.py` already allows short repetition (exact-duplicate paragraphs over
  a length threshold only), which is consistent with ARID. Keep that threshold behaviour.
- (5) Docs-as-code "Automated Tests" is what Sartor's pytest-ridden doc gates already are
  (`scripts/check_doc_frontmatter.py`, `check_doc_links.py`, `check_doc_single_home.py`).

---

## 4. Docs-governance-as-code

### Key practices

1. **Vale: prose linter with style packages.** "Vale is a command-line tool that brings
   code-like linting to prose." It is "cross-platform (Windows, macOS, and Linux), written in
   Go". Its package registry is "a collection of pre-packaged, Vale-compatible style guides and
   configurations."
   — <https://docs.vale.sh/>, "Introduction" (Vale docs)
   Packages are installed by listing them under `Packages` in `.vale.ini` and running
   `vale sync`.
   — <https://github.com/vale-cli/packages>, "vale-cli/packages"
   On Windows it installs via `choco install vale`, `scoop install vale` or
   `winget install -e --id errata-ai.Vale`, or from "Archives of precompiled binaries".
   — <https://docs.vale.sh/topics/installation>, "Installation" (Vale docs)

2. **Vale scopes rules by path glob and has several ways to handle false positives.**
   - Path scoping: "A section header is a glob matched against a file's path as Vale was
     given it". A rule is switched per section with `NO` (e.g. `Microsoft.Contractions = NO`),
     and `MinAlertLevel` takes "suggestion, warning, or error".
     — <https://docs.vale.sh/topics/.vale.ini.md>, ".vale.ini" (Vale docs)
   - Vocabulary: "Entries in `accept.txt` are added to every exception list in all styles";
     "Entries in `reject.txt` are automatically added to an existence rule (`Vale.Avoid`)".
     — <https://docs.vale.sh/keys/vocabularies.md>, "Vocabularies" (Vale docs)
   - Front matter: "Only string-valued fields are linted; a list or a nested map is left alone,"
     and a field can be excluded "by naming its scope in `IgnoredScopes`."
     — <https://docs.vale.sh/formats/front-matter.md>, "Front Matter" (Vale docs)
   - MDX: "Vale v3.18.0 and later has native MDX parsing capabilities", with inline
     suppression `{/* vale off */}` … `{/* vale on */}`.
     — <https://docs.vale.sh/formats/mdx.md>, "MDX" (Vale docs)

3. **markdownlint: structural Markdown rules.** "A Node.js style checker and lint tool for
   Markdown/CommonMark files", with rules like MD001 (heading-increment). Inline suppression
   uses `<!-- markdownlint-disable MD001 MD005 -->`, `<!-- markdownlint-disable-line -->` and
   `<!-- markdownlint-disable-file -->`, and it supports custom rules.
   — <https://github.com/DavidAnson/markdownlint>, "markdownlint"
   Its CLI is "configuration-based and prioritizes speed and simplicity". It is installed
   with "npm install markdownlint-cli2 --save-dev" or via a Docker image. Path exclusion uses
   an `ignores` "Array of Strings defining glob expressions to ignore when linting", plus a
   `gitignore` option.
   — <https://github.com/DavidAnson/markdownlint-cli2>, "markdownlint-cli2"

4. **A pure-Python markdownlint-family option exists.** PyMarkdown is "a Markdown linter"
   that needs Python 3.10 or later and installs with `pip install pymarkdownlnt`. Of its 46
   built-in rules, about 44 derive from Markdown Lint, adjusted "to follow the Markdown
   specifications more closely".
   — <https://github.com/jackdewinter/pymarkdown>, "PyMarkdown"

5. **lychee: link checking with an offline mode.** "A fast, async, stream-based link checker
   written in Rust". `--offline` will "Only check local files and block network requests";
   `--exclude-path` will "Exclude paths from getting checked"; `--include-fragments` enables
   "the checking of fragments in links". It supports a `.lycheeignore` file and a
   `.lycheecache` response cache. Windows installs are `scoop install lychee`,
   `winget install --id lycheeverse.lychee` and `choco install lychee`.
   — <https://github.com/lycheeverse/lychee>, "lycheeverse/lychee";
   <https://lychee.cli.rs/guides/cli/>, "Command-line flags" (lychee docs)

6. **Front-matter validation at the site-build layer.** Fumadocs MDX validates front matter
   with "Standard Schema compatible libraries, including Zod" at build time. The schema
   function can receive "the original file path" (`ctx.path`), so validation can depend on
   location.
   — <https://fumadocs.dev/docs/mdx/collections>, "Collections" (Fumadocs)

7. **Scoping lint away from historical content.** Both mature tools scope by path rather than
   by editing old files: Vale's glob sections with `= NO` (2), and markdownlint-cli2's
   `ignores` (3). PEP 1 and Nygard (§3.7) treat resolved records as frozen historical
   documents. Together these support exclusion **by path class**, not by in-file suppression
   comments. An in-file comment would be a rewrite of the record.

### Applicability to Sartor

- **Sartor's existing gate is already native Python.** It is stdlib-only, pytest-ridden and
  offline: `check_doc_frontmatter.py` checks headers, `check_doc_links.py` checks relative
  links, `#fragment` anchors and cites, and `check_doc_single_home.py` checks duplicates.
  - That already covers most of what lychee `--offline` does for local links and anchors, at
    zero install cost.
  - It already scopes by an **explicit reviewed registry** (`PUBLISHED_DOC_FILES`), not by
    directory sweep. That is the same "scope by path class" pattern (7) implies.
  - D1 should extend that registry model to `docs/user/**` and `docs/dev/**` living docs,
    with records directories (`handoffs/`, `ledger/`, `diagnosis/`, `reviews/`) as a named
    excluded class. Do not add per-file suppression comments to records: that is a rewrite.
- **External binaries sit awkwardly in a pytest gate.** Vale and lychee are single binaries
  (Go and Rust); markdownlint needs a Node runtime. Inside pytest they would run as
  subprocesses, and a missing binary forces a choice:
  - **skip-if-absent**, which is fail-open and conflicts with C-11's "fails closed";
  - or **hard-require it on every contributor machine**, a new dependency that needs D-1
    justification plus a `CHANGELOG.md` entry.
  - A CI-only job avoids both but moves the check out of `python -m scripts.gate`, the
    single definition of "gate green".
- **Vale's real value is the prose-style layer that Sartor lacks.** That is
  `docs/dev/doc-style-guide.md`'s wordmark rule, no-jargon-before-definition in
  `docs/user/`, and banned terms. Two cheaper ways to get it:
  - A **native Python term check**: a `reject.txt`-style list applied to `docs/user/**`. It
    covers the high-value 80% (wordmark misuse, jargon list) with no dependency.
  - Adopt Vale later, only if rule count or readability metrics outgrow that.
  - If Vale is adopted: `vale sync` fetches packages over the network (per (1)). For an
    offline, reproducible gate, commit the synced `StylesPath` rather than syncing in CI.
    This is an inference from the documented `sync` behaviour, not a documented Vale
    recommendation.
- **Front matter (6).** Fumadocs will reject invalid front matter at site build (Node, CI).
  The Python gate should check the same fields earlier and on Windows. One schema, two
  enforcers, so the zod schema and the Python field list must be derived from a single
  source (Sartor's single-home rule). `scripts/project_docs_to_mdx.py` already projects
  headers into front matter and is the natural place for that source.
- **Managing false positives.** Every mechanism cited above has one: Vale vocab and
  `MinAlertLevel`, markdownlint inline and `ignores`, lychee `.lycheeignore`. Sartor's
  existing idiom is a narrow, documented allowlist keyed by exact (file, target) pairs, as in
  `check_doc_links.py`'s `_TEMPLATE_QUOTE_LINKS`. That is stricter than a regex ignore file,
  and D1 should keep it: every exemption carries a reason in code.
- **External URL checking** is the one thing the native checker doesn't do. It needs
  network access and is flaky by nature, so it doesn't belong in the pytest gate. If wanted,
  a scheduled or label-gated lychee CI job with `--cache` is the proportionate place.

---

## Candidate lint tooling comparison

| Tool | Install footprint | Windows support (per fetched source) | Offline behaviour | Fit for Sartor |
|---|---|---|---|---|
| **Native Python check** (existing `scripts/check_doc_*.py` pattern) | None beyond the existing Python toolchain (stdlib-only today) | Runs wherever the gate runs (already on the Windows dev machine) | Fully offline | **Best fit** for structure, header/front-matter, local links/anchors, single-home, term lists. Rides `python -m scripts.gate` and fails closed. Cost: rules are hand-written and maintained in-repo. |
| **Vale** | Single Go binary (choco / scoop / winget / release archive); packages fetched by `vale sync` | Stated cross-platform incl. Windows | Linting runs on local files; `sync` needs network (commit synced styles for reproducibility — inference, see §4) | Strongest for **prose style** (packages, vocab, per-glob scoping, native MDX). New external dependency. Needs D-1 justification and a missing-binary policy that doesn't fail open. Candidate for a later phase. |
| **markdownlint (cli2)** | Node.js runtime + npm package (or Docker) | Node-based; Windows not explicitly stated on fetched pages | Local files only | Structural Markdown rules largely overlap what a Python check or **PyMarkdown** (`pip install pymarkdownlnt`, ~44 markdownlint-derived rules) can do without adding Node to the Python gate. Weak fit given minimal-deps. |
| **lychee** | Single Rust binary (scoop / winget / choco) | Windows installers listed | `--offline` mode checks local files only; online mode needs network (`--cache` available) | Local-link checking duplicates `check_doc_links.py`. Only unique value is **external URL** checking, which belongs in a scheduled/label-gated CI job, not the pytest gate. |

---

## Unverified — not cited

- `https://www.gov.uk/guidance/content-design/writing-for-gov-uk` → redirect; the redirect
  target and the "writing guidelines" page were fetched but returned only a section index.
  The "use clear language" sub-page returned **404**. No GOV.UK plain-English claim is
  relied on.
- `https://github.com/joelparkerhenderson/architecture-decision-record`: fetch failed
  ("socket hang up").
- `https://adr.github.io/` was fetched, but it does **not** address immutability or
  superseding records, so it is not cited for that claim. Nygard's post is cited instead.
- `https://vale.sh/docs/topics/config` and `https://docs.vale.sh/topics/vocab` returned 404 or
  redirects. The correct pages (`.vale.ini.md`, `keys/vocabularies.md`) were fetched and are
  the ones cited.
- The web-search result snippets on excluding archival docs from markdownlint (a GitHub PR on
  `jcasnellie69/homelab-config`, `thedocumentation.org` markdownlint-cli ignoring files) were
  **not fetched** and are not relied on.
- Vale's offline/privacy behaviour during linting is **not stated** on any fetched page. The
  "local files" characterization in the table is an inference from its CLI design, labelled
  as such.
- markdownlint-cli2's minimum Node.js version and explicit Windows support were **not stated**
  on the fetched pages.
