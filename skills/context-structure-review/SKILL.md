---
name: context-structure-review
description: Audit a repository's markdown and agent-instruction files (AGENTS.md, CLAUDE.md, SKILL.md, READMEs, /docs) against context-engineering best practices — progressive disclosure, just-in-time loading, document structure, instruction-file hygiene, freshness, and secrets hygiene — and produce an actionable findings report. Use this whenever someone asks to review, audit, or sanity-check how a repo or project structures its markdown/context for LLM agents, asks whether their context is "optimized" or their docs are "agent-ready", mentions reviewing AGENTS.md / CLAUDE.md / skills layout, or wants to compare their setup to best practices — even if they don't say the word "audit".
---

# Context Structure Review

Review how a repository structures its markdown and agent-facing instruction files,
measured against current context-engineering best practices, and report concrete,
file-specific findings.

## The one principle that governs how you run this review

**Review frugally. Practice the thing you are auditing.** This skill checks whether a
repo respects the context window as a finite resource — so do not violate that while
running it. Do **not** read every markdown file into context. Most of the signal you
need comes from cheap measurement (line counts, token estimates, headings, lint, file
inventory) that costs almost no context. Gather that first, let it tell you which few
files are worth opening, and read full bodies only for those. Load
`references/criteria.md` only when you need the detailed rationale or thresholds to
justify or explain a specific finding — not up front.

If you find yourself about to `cat` the whole repo, stop: that is the failure mode this
skill exists to catch.

## Phase 1 — Cheap survey (measure, don't read)

Run these against the target repo to build a findings map without spending context on
file bodies. Adapt commands to what's installed; degrade gracefully if a tool is absent.

```bash
# Inventory every agent-facing markdown file
find . -type f \( -name '*.md' -o -name '*.mdc' \) \
  -not -path './node_modules/*' -not -path './.git/*' | sort

# Size each one (flag anything over ~500 lines for the progressive-disclosure check)
find . -name '*.md' -not -path './node_modules/*' -not -path './.git/*' \
  -exec wc -l {} + | sort -rn

# Rough token estimate per file (words * ~1.3). Use tiktoken if available for accuracy.
for f in $(find . -name '*.md' -not -path './node_modules/*' -not -path './.git/*'); do
  printf '%s\t%s words\n' "$f" "$(wc -w < "$f")"; done | sort -t$'\t' -k2 -rn

# Heading skeleton of a flagged file (read structure before prose)
grep -nE '^#{1,6} ' path/to/file.md

# Is there a canonical instruction file, and is it duplicated across tools?
ls -1 AGENTS.md CLAUDE.md .cursorrules .github/copilot-instructions.md 2>/dev/null

# Is the context-exclusion surface configured?
cat .gitignore .claudeignore .aiexclude 2>/dev/null | grep -iE 'node_modules|dist|build|\.lock|\.min\.' || echo "no exclusion entries found"

# Cheap secret scan over bundled markdown (use gitleaks/detect-secrets if present)
grep -rInE '(api[_-]?key|secret|token|password|BEGIN [A-Z]+ PRIVATE KEY)' \
  --include='*.md' . | head -50

# --- Documentation discipline (dimension 7) ---

# Does the repo enforce/generate docs at all? Presence checks, not judgments.
ls -1 .interrogate* pyproject.toml docs/conf.py typedoc.json jsdoc.json mkdocs.yml \
  .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null
grep -rilE 'docstring|definition of done|interrogate|typedoc|sphinx|mkdocstrings' \
  AGENTS.md CLAUDE.md pyproject.toml .pre-commit-config.yaml 2>/dev/null

# HEURISTIC ONLY — likely commented-out code in tracked source. This regex is crude:
# it WILL flag legitimate "leading-comment + assignment" lines and miss many real cases.
# Treat any hit as a prompt to look, never as a verdict. For real enforcement, defer to
# a proper linter rule (ruff `ERA` for Python, eslint no-commented-out-code for JS/TS),
# not this grep. A false positive here is worse than a miss — see Notes on scope.
grep -rInE '^\s*(#|//)\s*(def |class |return |if |for |import |[a-zA-Z_]+\s*=\s*)' \
  --include='*.py' --include='*.ts' --include='*.js' . | head -30
```

Optional, if installed and the repo would benefit:

```bash
markdownlint '**/*.md' --ignore node_modules   # structural lint
gitleaks detect --no-git -v                    # thorough secret scan
```

From Phase 1 you should now have, per file: line count, token estimate, heading
structure, and whether it tripped any cheap flag. **That alone resolves most findings.**

## Phase 2 — Targeted read (only the flagged files)

Open the full body of a file only when Phase 1 flagged it — e.g. an oversized SKILL.md,
an instruction file with no copy-pasteable commands, a doc with a flat or missing
heading structure, or a suspected secret. For each file you open, evaluate it against
the seven dimensions below. Pull the matching section of `references/criteria.md` only if
you need the precise threshold or the rationale to write a defensible finding.

## The seven review dimensions

1. **Progressive disclosure** — Is large/specialized knowledge tiered, or dumped in one
   file? Flag any SKILL.md or instruction file over ~500 lines / ~5k tokens that should
   become a thin entry point plus references. Skill metadata should be small enough to
   sit in context cheaply.
2. **Just-in-time loading** — Does the repo reference content for on-demand loading
   rather than inlining bulk? Is the exclusion surface configured so agents never read
   `node_modules`, build output, lock files, or binaries? (Missing exclusions is one of
   the highest-impact, easiest fixes.)
3. **Document structure** — Descriptive headings that work as retrieval keys; one idea
   per section; load-bearing constraints near the top or bottom, not buried mid-file;
   tables and code blocks kept as atomic units; clean markdown without HTML cruft.
4. **Instruction-file hygiene** — One canonical AGENTS.md (or CLAUDE.md) rather than
   drifting duplicates; commands that are exact and copy-pasteable (not "run the usual
   tests"); concise rather than sprawling; nested files used where a monorepo needs
   scoped context; explicit permission boundaries for risky operations.
5. **Freshness / living-doc discipline** — Are instruction and reference files dated,
   source-attributed, and plausibly current? Stale instructions are worse than none.
   Flag drift between a canonical file and anything generated from it.
6. **Secrets & least privilege** — No secrets, credentials, or PII in bundled markdown;
   permission guidance scoped to the minimum needed.
7. **Documentation discipline** (code repos only) — Are docstrings on public APIs
   required and their coverage gated in CI? Are reference docs generated *from* source
   (Sphinx/TypeDoc/etc.) rather than hand-maintained in parallel? Does the repo forbid
   commented-out code and parrot comments, and tie doc updates to a Definition of Done /
   PR template? Flag missing enforcement, not individual missing docstrings — the latter
   is the coverage tool's job, not yours. **Scope:** this dimension applies to code
   projects (e.g. Sartor). It does NOT apply to prose/conceptual artifacts — a field
   guide or a typed-contract corpus has no "docstring coverage," and "comment the why,
   not the what" can invert when the *what* is the artifact's whole point. Skip this
   dimension for non-code artifacts rather than forcing it.

See `references/criteria.md` for thresholds, rationale, and what a good vs. poor example
of each dimension looks like. Read it per-dimension as needed, not all at once.

## Output: the findings report

ALWAYS produce the report in this structure:

```markdown
# Context Structure Review — <repo or scope>

## Summary
<2-4 sentences: overall posture, the single highest-impact fix, and what's already strong.>

## Scorecard
| Dimension | Status | Note |
|-----------|--------|------|
| Progressive disclosure | ✓ / ⚠ / ✗ | one line |
| Just-in-time loading | ✓ / ⚠ / ✗ | one line |
| Document structure | ✓ / ⚠ / ✗ | one line |
| Instruction-file hygiene | ✓ / ⚠ / ✗ | one line |
| Freshness | ✓ / ⚠ / ✗ | one line |
| Secrets & least privilege | ✓ / ⚠ / ✗ | one line |
| Documentation discipline | ✓ / ⚠ / ✗ / n/a | one line (n/a for non-code artifacts) |

## Findings
<Ordered by impact. For each:>
- **[severity] file:line — short title.** What's wrong, why it costs context or
  reliability, and the concrete fix. Severity ∈ {blocker, improvement, nit}.

## Suggested order of work
<A short, sequenced list — biggest context savings first.>
```

Rules for the report: every finding names a real file (and line where it applies), states
the fix concretely enough to act on without re-deriving it, and explains the cost in
terms of context or reliability rather than style preference. Lead with the change that
reclaims the most context for the least effort — usually exclusion config or splitting
one oversized file. Praise what's already right; an all-negative audit is usually a sign
you measured taste, not practice.

## Notes on scope

- This skill reviews **structure**, not prose quality. Don't rewrite content; flag where
  structure undermines how an agent loads or finds it.
- It is repo-agnostic. The first target is typically a single project; the same pass
  works on a multi-repo or monorepo by running Phase 1 per package and noting nesting.
- It builds on open standards (AGENTS.md, the Agent Skills format) and commodity tools
  (markdownlint, gitleaks, tiktoken) on purpose: the review leans on others' work and
  imposes no framework of its own.
- **The Phase 1 commands are signal, not verdicts.** Several are deliberately crude
  heuristics — especially the commented-out-code grep, which over-flags (e.g. a comment
  immediately above an assignment) and under-catches. Use a hit to decide *what to read*,
  then judge it in Phase 2. Never emit a finding straight from a grep. Where a repo wants
  real enforcement of these, point it at a proper linter (ruff `ERA`, eslint
  no-commented-out-code) rather than this skill's heuristics — a false positive in an
  enforced gate trains people to ignore it, which is worse than the gap it closed.
- **Documentation discipline (dimension 7) is code-only.** Mark it `n/a` for conceptual
  or prose artifacts. The code-oriented best practices it checks do not transfer to a
  field guide or a typed-contract corpus, and a documentation discipline for those is a
  separate, unsolved question — don't fabricate one by stretching this dimension.
