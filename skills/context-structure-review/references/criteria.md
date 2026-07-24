# Review Criteria — detailed thresholds and rationale

Load the section you need to justify a specific finding. You do not need to read this
whole file to run a review; the SKILL.md procedure is sufficient for most findings.

## Contents
- [Why this matters (the shared rationale)](#why-this-matters)
- [1. Progressive disclosure](#1-progressive-disclosure)
- [2. Just-in-time loading](#2-just-in-time-loading)
- [3. Document structure](#3-document-structure)
- [4. Instruction-file hygiene](#4-instruction-file-hygiene)
- [5. Freshness / living-doc discipline](#5-freshness)
- [6. Secrets & least privilege](#6-secrets--least-privilege)
- [7. Documentation discipline (code repos only)](#7-documentation-discipline)

---

## Why this matters

Context is a finite, *degrading* resource. Three findings from the long-context
literature drive every criterion here:

- **Lost-in-the-middle** (Liu et al., Stanford, TACL 2024): attention is U-shaped —
  strong at the start and end of context, weak in the middle. Accuracy on buried
  information can drop 30%+.
- **Context rot** (Chroma, 2025): across 18 frontier models, output quality degrades as
  input length grows *even when the window is far from full*. Degradation is continuous,
  not a cliff.
- Past roughly 50% context fill, the U-shape gives way to recency bias (recent > middle
  > early), so anything important buried mid-file is doubly disadvantaged.

The practical consequence: more loaded tokens is not better. The target is the smallest
set of high-signal tokens that accomplishes the task. Every criterion below is a way of
checking whether the repo respects that, or fights it.

---

## 1. Progressive disclosure

**What good looks like.** Specialized knowledge is tiered: a thin entry point carries
just enough to decide whether to engage, the body carries what's needed to act, and
detail sits in references loaded only when required. For skills: metadata (name +
description) stays tiny (~tens of tokens) so many skills can coexist cheaply; the
SKILL.md body loads on trigger; reference files load on demand.

**Thresholds.**
- SKILL.md or a primary instruction file over ~500 lines / ~5,000 tokens → flag for
  splitting into an index plus references.
- Reference files over ~300 lines → should carry a short table of contents so the agent
  can jump to one section instead of loading all of it.
- Mutually exclusive or rarely co-used material living in one file → split, so loading
  one path doesn't drag in the others.

**Poor signal.** A single 1,200-line CLAUDE.md holding setup, architecture, style,
domain knowledge, and edge cases all at once — every consumer pays for all of it on
every load.

**The authoring test that doubles as an audit lens.** Sort each piece of content into:
must-know-to-decide (→ summary/metadata), must-follow-to-do (→ body), needed-only-when-
unusual (→ reference). Content in the wrong tier is the finding.

---

## 2. Just-in-time loading

**What good looks like.** The repo holds lightweight references (paths, identifiers,
short summaries) and resolves them to full content at runtime, rather than pre-inlining
bulk. The exclusion surface is configured so agents never burn context on machine
artifacts.

**Checks.**
- Is there a `.gitignore` / `.claudeignore` / tool-specific ignore that covers
  `node_modules`, `dist`/`build`, lock files, minified assets, and binaries? Excluding
  these alone can cut an agent's context consumption by a large margin on a typical repo
  — it is usually the highest-leverage, lowest-effort fix available.
- Are large bodies of reference inlined into an always-loaded file when a pointer would
  do? Prefer "see `references/x.md`" over pasting x.

**Poor signal.** An AGENTS.md that pastes the full schema, the full API surface, and a
long changelog inline — all of which the agent could fetch on demand if and when needed.

---

## 3. Document structure

**What good looks like.** Headings form a clean, shallow hierarchy the model can use as
a map (effectively an AST). Each section carries one idea. Descriptive headings double
as retrieval keys. Tables, code blocks, and lists stay intact as atomic units. Markdown
is clean — no HTML cruft inflating the token count.

**Checks.**
- Heading skeleton (`grep -nE '^#{1,6} '`): is there structure at all, or a wall of
  prose? Are headings descriptive ("Token budget per agent") or generic ("Notes")?
- Are load-bearing constraints near the top or bottom of long files, or buried in the
  middle where attention is weakest?
- Do tables or code blocks get fragmented by mid-block headings or splits?
- Is there leftover HTML, tracking markup, or conversion artifacts? Clean markdown is
  both easier for the model to parse and materially cheaper in tokens than HTML-laden
  equivalents.

**Poor signal.** A 400-line doc with three top-level headings and the critical
"never deploy without X" rule sitting in paragraph 22 of section 2.

---

## 4. Instruction-file hygiene

**What good looks like.** One canonical instruction file (AGENTS.md is the cross-tool
open standard; CLAUDE.md and others can point to it or be generated from it). It started
small and grew from real usage. Commands are exact and copy-pasteable. Monorepos use
nested files so each subproject ships scoped context (the agent reads the nearest file
to what it's editing). Risky operations carry explicit permission boundaries.

**Checks.**
- Multiple instruction files with overlapping-but-diverging content → drift risk; flag
  and recommend a single source with the others pointing to or symlinked from it.
- Commands like "run the usual tests" or "lint as normal" → not copy-pasteable; flag.
  Good: `uv run pytest tests/unit/test_handlers.py`.
- A file that has ballooned well past its useful core → recommend trimming to the
  high-signal essentials and moving the rest to references.
- No statement of which operations are safe to do unprompted vs. which need approval
  (installs, pushes, infra/permission/delete operations) → flag for addition.

**Poor signal.** `CLAUDE.md`, `AGENTS.md`, and `.cursorrules` that each say *almost* the
same thing but have drifted, so the agent's behavior depends on which one its tool reads.

---

## 5. Freshness

**What good looks like.** Instruction and reference files are dated, source-attributed
where they cite external facts, versioned in the repo, and reviewed when processes
change. Stale instructions are actively worse than none — an agent will follow a command
that no longer works and waste a loop discovering that.

**Checks.**
- Do reference docs that cite tools, versions, or external standards carry a date or
  "current as of"? Undated factual reference is a freshness risk.
- Does anything generated from a canonical source (e.g. a distributed/derived instruction
  file) appear out of sync with that source?
- Are there commands or paths that reference tools/dirs that no longer exist in the repo?

**Poor signal.** A setup section referencing a package manager or build step the repo
migrated away from two refactors ago.

---

## 6. Secrets & least privilege

**What good looks like.** No secrets, credentials, tokens, or PII embedded in bundled
markdown or reference files. Any permission guidance grants the minimum needed.

**Checks.**
- Grep / gitleaks / detect-secrets over markdown turned up nothing that looks like a key,
  token, private key block, or password.
- Reference files don't contain personal data unless explicitly required and authorized.
- Permission guidance doesn't hand an agent broad standing authority where scoped,
  per-action approval would do.

**Poor signal.** An example in a SKILL.md that pastes a real API key "for illustration",
or a reference file with a real connection string.

---

## 7. Documentation discipline

**Applies to code repositories only.** Mark `n/a` for prose/conceptual artifacts (field
guides, decision logs, a typed-contract corpus). The practices below are tuned to
generated reference docs and docstring coverage, which have no meaning for a philosophical
artifact — and "comment the why, not the what" can invert where the *what* is the point.
For the rationale and the copy-paste enforcement blocks, see
`doc-discipline-for-coding-agents.md` in the external agent-coding-practices kit (path
recorded in `CLAUDE.local.md`); this section is the audit lens only.

**What good looks like.** Inline documentation captures intent, not mechanics: docstrings
on public APIs, the *why* behind non-obvious decisions, business rules and gotchas — and
nothing that merely restates the code. Reference docs are generated *from* docstrings
(Sphinx/autodoc, TypeDoc, JSDoc, rustdoc, godoc, OpenAPI) and built in CI so they cannot
drift. Doc updates are part of Definition of Done, mirrored in the PR template, and the
mechanizable parts are backed by gates rather than trusted to the agent.

**Checks (enforcement presence, not per-symbol coverage).**
- Is there a docstring-coverage gate (`interrogate`, `docstr-coverage`) and a style check
  (`pydocstyle`/PEP 257, `ruff` D-rules)? Coverage of individual symbols is the tool's
  job; the audit checks whether the gate *exists*.
- Are reference docs generated from source and built in CI, or hand-maintained in
  parallel (drift risk)?
- Does AGENTS.md state a documentation-linkage rule (user-visible change ⇒ docs update)
  and pair prohibitions with concrete alternatives, rather than warning-only?
- Is there a Definition-of-Done checklist, and does the PR template mirror it?
- Commented-out code and parrot comments: flag for a *proper linter rule*, not this
  skill's heuristic grep. Report "no lint rule enforces this" as the finding; do not
  report individual grep hits as findings — the grep over-flags and under-catches, and a
  false positive erodes trust in the whole gate.

**Why it matters for agents.** This is not hygiene. Stale or wrong docs and defective
commented-out code feed straight back into the agent's context and degrade its output —
one study measured commented-out defects driving generated-defect rates materially higher.
Documentation quality is an input to agent reliability, so the audit weights *enforcement*
(gates that hold) over *aspiration* (rules in a file nobody checks).

**Poor signal.** An AGENTS.md that says "always document your code" with no coverage gate,
no generator, no DoD, and a repo full of `# TODO: old approach` commented-out blocks.

---

## A note on calibration

Distinguish a structural finding (the layout makes an agent load or miss information) from
a matter of taste (you'd have phrased it differently). Only the former belongs in the
report. When every dimension comes back negative, suspect the reviewer measured
preference rather than practice, and re-check against the thresholds above.
