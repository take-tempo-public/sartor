---
name: doc-writing
description: Write or substantially revise a Sartor doc (anything under docs/user/ or docs/dev/, the root README/vision/ACCESSIBILITY/CONTRIBUTING, or a published page) in the order the docs IA requires: tier and type, ladder rung, header, cite-don't-restate, registration, then the doc lints until no block remains. Use whenever someone asks to write, add, draft, restructure or publish documentation or a guide in this repo — even if they don't say "skill". Not for code comments, CHANGELOG entries, handoffs or work items, which have their own templates.
---

# Writing a Sartor doc

This skill **orders and invokes** the doc rules. It restates none of them: each rule's single
home is named at the step that uses it, and that home governs. If a step here ever disagrees
with the home it cites, the home wins, and this file is the one to fix.

Read [`docs/dev/doc-style-guide.md`](../../docs/dev/doc-style-guide.md) before you write a
sentence. It is the voice, the wordmark rule and the claims discipline for prose.

## The order

Do these in order. Skipping ahead is how a doc ends up in the wrong tier, restating a list
that drifts, or published without a header.

1. **Pick the tier and the Diátaxis type.**
   - Tier: `user` (someone using Sartor) or `dev` (someone building on it). The tier decides
     the directory (`docs/user/` or `docs/dev/`) and the nav section.
   - Type: tutorial, how-to, reference or explanation. The design's reasoning for each
     existing doc is in [`docs/dev/docs-ia-design.md`](../../docs/dev/docs-ia-design.md) §2.
   - One doc, one tier, one type. A doc that wants two is two docs.

2. **Find the rung it serves.** The user ladder is in
   [`docs/user/README.md`](../../docs/user/README.md); the dev ladder (D0–D5) is in
   [`docs/dev/README.md`](../../docs/dev/README.md). A doc that serves no rung and no
   reference need is a candidate for **not being written**. Say so to the person asking
   before you write it.

3. **Write the header.** Purpose, Audience (opening with the tier token), Authoritative-for,
   and, on the user tier, Type. The field-by-field contract and how each field is published
   is [`docs/dev/documentation-architecture.md`](../../docs/dev/documentation-architecture.md)
   §"Fumadocs sourcing". Copy the shape from a neighbor in the same directory.

4. **Cite, don't restate, anything code enumerates.** Gate steps, deterministic modules,
   subagents, hooks, guards, commands, skills, charter clauses: link to the code or the one
   page that lists them (`scripts/gate.py`, `tests/test_construction_boundary.py`,
   [`docs/dev/tooling.md`](../../docs/dev/tooling.md),
   [`docs/governance/charter.md`](../../docs/governance/charter.md)). A count or a list
   copied into prose is the drift lint 5.5 exists to catch.

5. **Register it if it should be published.** Add an entry to `PUBLISHED` in
   [`scripts/doc_registry.py`](../../scripts/doc_registry.py) with its tier, in nav order. A
   doc outside the registry is never published, whatever its header says. To move an
   existing doc, use `python scripts/docs_move.py`, which rewrites live links and records the
   move for records.

6. **Run the lints and fix every block.**
   ```bash
   python scripts/doc_lints.py           # §5 lints; --report adds the single-home report
   python scripts/check_doc_frontmatter.py
   python scripts/check_doc_links.py
   python scripts/check_doc_single_home.py
   ```
   Fix every `BLOCK`. Read every `warn` and decide; a warning is a prompt to reread the
   sentence, not a defect. What each rule checks, and its known limits, is in the
   `scripts/doc_lints.py` module docstring. `tests/test_doc_lints.py` runs the same lints in
   the gate, so a block you leave fails the PR.

7. **If it's a new skill, hook, guard, command or subagent**, add its row to
   [`docs/dev/tooling.md`](../../docs/dev/tooling.md) in the same change. The roster lint
   fails until you do.

## Evaluation plan

How to tell whether this skill makes docs better, rather than just longer. **Not yet run**
(D4 wrote the plan; running it costs agent sessions, so it is the owner's call when).

- **Task set.** Six writing tasks covering both tiers and all four types. Two examples:
  "add a user how-to for retiring an application" and "add a dev reference for the doc
  corpus". Each runs from a clean branch.
- **Arms.** Each task runs twice in fresh sessions: once with this skill loaded and once
  without it (baseline), same model, same prompt.
- **Deterministic measures**, per draft, with no LLM judge:
  - blocks on the **first** `doc_lints.py` run, and blocks left at hand-back;
  - whether `check_doc_frontmatter.py` passes;
  - whether the doc is registered when it should be;
  - whether any code-enumerated list is restated rather than cited.
- **Pass bar.** The skill arm hands back zero blocks on every task, and it has fewer
  first-run blocks than the baseline on at least five of the six tasks. If the baseline
  already scores zero everywhere, the skill isn't earning its context cost, and that is a
  finding too.
- **Trigger check.** Write five prompts that should load the skill ("document the Pipeline
  tab") and five that shouldn't ("fix this test", "write the CHANGELOG entry"). Check the
  description loads it for the first set only.
