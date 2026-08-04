# Blast radius — <branch-slug>

<!--
  Copy me to docs/dev/blast-radius/<branch-slug>.md, where <branch-slug> is your branch
  name minus the `<type>/` prefix. The `require-consumer-enumeration` hook looks for
  exactly that path and will not let you edit a gated surface until `## Consumers`
  below both (a) has real content and (b) NAMES the file you are trying to edit.

  Copying this file is NOT enough — every placeholder line here is italic, and the gate
  ignores italic lines on purpose. You have to actually write something.

  The one rule that matters: ENUMERATE BEFORE YOU EDIT, NOT AFTER.
  An enumeration written after the change is a description of what you did. Written
  before, it is the thing that tells you the change is bigger than you thought. That
  ordering is the entire mechanism.

  What counts as a consumer is decided by grep, not by memory. `scripts/enforcement/
  blast_radius.py` lists why each surface is gated — read your surface's entry first;
  it usually names the consumer class you are about to miss.
-->

> **Branch:** `<type>/<slug>`
> **Status:** _enumeration in progress / complete — say which, plainly_

---

## Surface

<!--
  WHAT you are changing, precisely. Not "the corpus code" — the exact file, and the
  exact symbol/column/section within it. A vague surface produces a vague enumeration.
-->

_(Name each file, and the symbol or section inside it that actually changes.)_

---

## Enumeration

<!--
  THE RECEIPT. Paste the exact commands you ran and their counts.

  "Grep-complete" means the search was over the whole tree, not the directory you
  happened to be in — and that you searched for every NAME the thing goes by: the
  symbol, its string form, its alias/re-export, the column name in raw SQL, the
  selector in a template. A rename you did not grep for is a consumer you did not find.

  Include the negative results too. "0 hits in static/" is a finding.
-->

_(Commands, verbatim, with counts. If you cannot paste a command, you did not run one.)_

---

## Consumers

<!--
  ONE ROW PER SITE. Every site gets an explicit decision BEFORE the first edit —
  "update", "no change (why)", or "deferred (see below)". A site you left out of this
  table is a site you have not decided about.

  The gate requires this section to name the file you are editing. That is not
  bureaucracy: a dossier that does not mention your surface is a dossier for some other
  change, and rubber-stamping across surfaces is the exact failure mode being blocked.
-->

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | _`path/to/file.py:123`_ | _update / no change / deferred_ | _why_ |

---

## Deferred

<!--
  SITES YOU DELIBERATELY DID NOT TOUCH, AND WHY.

  This section is the difference between a scoped change and a forgotten one. A site
  excluded WITH a written reason is a decision; the same site excluded silently is a
  bug someone else will find later. See docs/dev/diagnosis/compose-unawaited-reloads.md
  Fact 5 for the shape — 3 sites excluded because reaching them required a materially
  larger change, recorded rather than quietly skipped.

  If you defer something that leaves a real gap, file it as a carry-forward ledger item
  too — this file is evidence, not a tracker.
-->

_(Nothing deferred, or: the sites, each with its reason.)_

---

## Verification

<!--
  HOW YOU WILL KNOW THE ENUMERATION WAS COMPLETE — not that the change works.

  Prefer something that fails loudly if you missed a site: a test that exercises each
  consumer, an exact-set assertion, a type check that catches a signature drift. "The
  suite is green" is weak evidence when the missed consumer had no test in the first
  place.
-->

_(How a missed consumer would surface, and what you ran.)_
