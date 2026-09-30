# Blast radius — dev-docs

> **Branch:** `feat/dev-docs`
> **Status:** enumeration complete for the planned changes. Written before the first content
> edit, 2026-09-30, on `feat/dev-docs` at `f0e1b5f`. Plan: the owner-approved D3 (dev half)
> plan; the owner's decisions are quoted in [Surface](#surface).

---

## Surface

Epic D sprint D3, the dev half (`docs/dev/RELEASE_ARC.md` §"Epic D" D3 bullet;
`docs/dev/docs-ia-design.md` §2.1, §4, O-2; item 127). Owner decisions at kickoff, 2026-09-30:
- **O-2 shape:** the owner's session protocol moves to a new `docs/dev/maintainer-lane.md`.
  `CLAUDE.md` adds `@docs/dev/maintainer-lane.md` next to `@AGENTS.md`, so Claude sessions
  still auto-load it. `AGENTS.md` keeps a `Branch close-out checklist` pointer section, so the
  heading every citer names still resolves.
- **Diagnostics home:** a new published `docs/dev/diagnostics.md`. `dashboard/README.md` is
  corrected and shrunk to a file map plus a link.
- **Roster home:** a new `docs/dev/tooling.md`. `CLAUDE.md` keeps its agent-facing hook bullets
  (completed) and points there.
- **Scope:** one branch, all of it.

What changes:

1. **`AGENTS.md`**:
   - `:201-233` (the "Mandatory steps have no escape hatch" paragraph and the "Branch close-out
     checklist" steps 0–5) moves to `docs/dev/maintainer-lane.md`. The general hatch rule and a
     pointer section named "Branch close-out checklist" stay.
   - The "four steps" wording at `:274` is replaced by a citation of `scripts/gate.py`.
   - The header's "Authoritative for" is revised.
2. **`scripts/wiki_relevance.py`** (gated): `KNOWN_RELEVANT_TOP_LEVEL` gains the three new
   `docs/dev/` root files, `maintainer-lane.md`, `diagnostics.md` and `tooling.md`.
   `tests/test_wiki_relevance_classification.py:66` fails on any unclassified entry.
3. **`scripts/doc_registry.py`** `PUBLISHED` gains the same three files at the `dev` tier. It is
   not gated.
4. **Section moves by hand** (`docs_move.py` is whole-file only). `docs/dev/PRODUCT_SHAPE.md`
   §1, §6.1, §7, §9 and §10 go to `docs/dev/archive/PRODUCT_SHAPE-history.md`, a record.
5. **Prose-only edits** to live docs and to comments/docstrings in code:
   - CONTRIBUTING, `agents/git-flow.md`, `.githooks/README.md`
   - the `ci.yml:64` comment and the `ci_backstop.py:13-16` docstring
   - the `print_handoff_pointer.py:2-3` docstring
   - CLAUDE.md, README, vision
   - `docs/dev/{README,architecture,system-model,documentation-architecture}.md`
   - the `enforcement.md` status facts
   - `dashboard/README.md`

   No behavior changes.

---

## Enumeration

Run 2026-09-30 on `feat/dev-docs` at `f0e1b5f`.

**Live set.** The live set is `git ls-files` minus these record classes:
- `docs/dev/{handoffs,ledger,diagnosis,blast-radius,reviews,perf,excellence-walk,flake-rates,archive,work}/`
- `CHANGELOG*`
- `docs/wiki/log.md`, `evals/TUNING_LOG.md`, `docs/governance/compliance-log.md`

These records are never rewritten (docs-ia-design §3.1).

```
git ls-files | grep -v -E '<record classes>' | xargs grep -l 'AGENTS\.md'        → 73 files
... | xargs grep -n -E 'Branch close-out|Mandatory steps have no'                → 9 hits
... | xargs grep -n -E 'AGENTS(\.md)?.{0,60}(close-out|[Ss]tep [0-9]|pre-close|Mandatory|escape hatch|Branch before|checklist)'
                                                                                  → 11 hits
grep -n 'AGENTS' scripts/print_handoff_pointer.py docs/governance/{enforcement,charter}.md
grep -rn 'AGENTS\.md#' (whole tree)                                               → 0 hits
python: scripts.enforcement.blast_radius GATED / GATED_PREFIXES                   → only
        scripts/wiki_relevance.py and docs/dev/AGENT_HANDOFF_TEMPLATE.md touch this change
```

The other 60-odd live files that mention AGENTS.md cite **code-rule** sections:
- "LLM prompts", "Architecture at a glance", "Key patterns", "What NOT to do";
- the security gate and the deterministic boundary;
- the file as a whole.

None of those sections move, so those citers need no change. This covers the wiki pages, the
agents/commands/skills, the tests, `analyzer.py` and `hardening.py`.

**Negative results:**
- No test or script opens AGENTS.md and asserts its text.
- No `AGENTS.md#` anchor exists anywhere.
- No test asserts that AGENTS.md steps 0–5 equal the template's verbatim block. The two are
  hand-synced, and they already differ at step 1.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `AGENTS.md:201-233` | update | The moved content leaves. A pointer section with the same heading text stays, and so does the general hatch rule. |
| 2 | `CLAUDE.md:16` (`@AGENTS.md`) | update | Add `@docs/dev/maintainer-lane.md` so Claude sessions keep the protocol in context (charter F-gov-05, `charter.md:47-51`: "preserves agent rule-access via `@import` … or an explicit canonical pointer"). |
| 3 | `scripts/wiki_relevance.py` `KNOWN_RELEVANT_TOP_LEVEL` | update | Classify the 3 new `docs/dev/*.md` files (gated surface). |
| 4 | `scripts/doc_registry.py` `PUBLISHED` | update | Register the 3 new dev-tier docs. |
| 5 | `docs/governance/charter.md:206` ("`AGENTS.md`'s close-out step 4") | no change | It still resolves through the pointer section. Its "step 4" was already wrong before this branch (the rule is step 5); see Deferred. |
| 6 | `docs/governance/charter.md:466-467` ("`AGENTS.md` "Branch close-out checklist"") | no change | The pointer section keeps that heading resolvable. No charter amendment is needed. |
| 7 | `docs/governance/enforcement.md:126` ("tribal (AGENTS.md)") | update | Factual location update to the maintainer-lane doc. The classification (tribal) is unchanged. |
| 8 | `docs/dev/AGENT_HANDOFF_TEMPLATE.md:40,140` | no change | Both cite AGENTS.md's close-out heading or step 0, and the pointer keeps both resolvable. The file is gated and editing it can block in-flight handoffs, so the cost isn't worth a pointer hop. |
| 9 | `scripts/print_handoff_pointer.py:2-3` (docstring) | update | Cite `docs/dev/maintainer-lane.md` step 5. |
| 10 | `docs/dev/README.md:17,21` (rung 6, "moves … when AGENTS.md is split") | update | Point at the new doc. The whole README is rewritten in this branch (C7). |
| 11 | `CONTRIBUTING.md:11,34,44` | update | Route humans to the code rules, not D5 (DX-02). The `:58` `--no-ff` rule, the `:114` "latent" wording and the `:34-35,83` restated gate steps are item 127. |
| 12 | `agents/git-flow.md:3,19,23` | update | Item 127: `--no-ff` becomes the PR flow. `:23` still cites the retired `.claude-plugin/hooks/` path (item 54). |
| 13 | `.githooks/README.md:64` | update | Its `git merge --no-ff` example contradicts the PR-only flow. |
| 14 | `hooks/check-plan-approved.sh:65` (comment, AGENTS.md "Branch before code changes") | no change | That section stays in AGENTS.md. |
| 15 | `docs/wiki/pages/code-module-map.md:153` ("named by `AGENTS.md` step 4") | deferred to close-out wiki pass | The wiki is edited only through `/wiki-self-update` (author ≠ auditor). |
| 16 | `docs/dev/RELEASE_ARC.md:699-721,1349,1766` | no change | Plan-of-record prose, and AGENTS.md "close-out" still resolves. |
| 17 | `docs/dev/RELEASE_CHECKLIST.md:2236` | no change | A dated ledger entry; the pointer resolves. |
| 18 | `docs/dev/docs-ia-design.md:228,445` | no change | A dated design; it describes the state at D1. |
| 19 | `docs/dev/handoff-integrity-design.md:216` | no change | A dated design (a live exception per O-3a) that describes its own rollout. |
| 20 | `.github/workflows/ci.yml:64`, `scripts/enforcement/ci_backstop.py:13-16` ("latent") | update | Comment/docstring only; contradicts `enforcement.md:37` ("CI is live, not latent"). |
| 21 | `README.md:235-276,292`, `vision.md:94` | update | §2.1 rows: the dev sections become links; the stale "C-0…C-6" / "D-1…D-6" become a citation of the charter. |
| 22 | `docs/dev/architecture.md:98-100,208,297-331,812-816` | update | Module-map refresh plus the item-20 labels. |
| 23 | `docs/dev/PRODUCT_SHAPE.md` §1, §6.1, §7, §9, §10 → `docs/dev/archive/PRODUCT_SHAPE-history.md` | update | A §2.1 row. Inbound links to moved anchors are checked with `check_doc_links.py` after `git add`. |
| 24 | `dashboard/README.md:21-22,139,192` | update | Fix "Four tabs" / "drawer", then add a link to `docs/dev/diagnostics.md`. |
| 25 | `docs/wiki/pages/diagnostics-console.md:113-114` | deferred to close-out wiki pass | Same reason as #15. |

---

## Deferred

- **`docs/governance/charter.md:206` says "step 4" but means step 5.** It was wrong before this
  branch. Fixing it is a charter text edit, which is the owner's call under the amendment
  ceremony (`charter.md:453+`). It goes to the carry-forward ledger rather than being edited
  here.
- **The template's verbatim close-out step 1 (`ruff check . + mypy . + pytest`) disagrees with
  AGENTS.md step 1 (`python -m scripts.gate`).** Editing a verbatim block can block a handoff
  already in flight (`blast_radius.py` template entry), so it goes to the ledger.
- **`db/build_context.py:92` stale comment** (carried over from `user-docs`). This branch doesn't
  touch that file, so it stays deferred.
- **Records** (~330 AGENTS.md hits across the record classes above) are frozen per
  docs-ia-design §3.1. `AGENTS.md:NNN` line cites in them will drift. `check_doc_links.py`
  checks only that the cited file exists (`scripts/check_doc_links.py:34-37`), so the gate
  stays green.

---

## Verification

- `git add` then run `python scripts/check_doc_links.py`, `scripts/check_doc_frontmatter.py`
  and `scripts/check_doc_single_home.py`. The single-home check fails if a moved paragraph is
  left duplicated in AGENTS.md.
- `pytest tests/test_wiki_relevance_classification.py tests/test_doc_links.py tests/test_doc_frontmatter_gate.py tests/test_verify_doc_template.py`.
- Re-run the Enumeration greps after the edits. Expect only the pointer section to match
  `Branch close-out` in AGENTS.md, and 0 live hits for `merge --no-ff`, "latent until" or
  "four steps".
- Full `python -m scripts.gate` at close-out, reading the log for 0 RERUN.

---

## Addendum (during C1)

- `scripts/enforcement/guards/block_merge_to_main.py:101`: the block message's hatch example
  still says `git merge feature-branch --no-ff`. **No change.** The message leads with the
  PR-only rule (`:95-98`), and the example shows the hatch syntax for an owner-directed
  exception. The tests (`tests/test_enforcement_core.py:275+`), `hooks/cleanup-plan-on-merge.sh:34`
  and `tests/test_plan_approval_scoping.py` use `--no-ff` as a real merge form the guard and
  the witness must catch. That is behavior, not a doc claim.
- The `agents/git-flow.md:23` claim is narrowed to what the guard's regexes match
  (`_MERGE_MAIN_RE` / `_PUSH_MAIN_RE`, `block_merge_to_main.py:90-92`). `gh pr merge` is not
  hook-gated.
- **Item 127 verification scan.** The scan runs over live `*.md`/`*.yml` from `git ls-files`.
  - **Excluded:** the record classes, plus the dated plan/design docs `RELEASE_ARC`,
    `RELEASE_CHECKLIST`, `docs-ia-design` and `handoff-integrity-design`. Those docs describe
    the defect historically.
  - **Patterns** (case-insensitive): `git merge --no-ff`, `latent until`, `same four steps`,
    `four steps below`.
  - **Result:** 9 hits at `f0e1b5f`, 0 on this branch.
  - **Widened scope:** the scan also found `latent` wording in `.github/dependabot.yml:9`,
    `docs-deploy.yml:11` and `scorecard.yml:7`, plus the `ci.yml:51` four-steps comment.
    All are fixed in the same commit. `gh run list` shows docs-deploy (2026-09-28) and
    scorecard (2026-09-29) running on `main`.
