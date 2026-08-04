# Blast radius — `feat/consumer-enumeration-gate`

> **Branch:** `feat/consumer-enumeration-gate`
> **Status:** enumeration complete — every consumer below decided before the first
> production edit.

This branch introduces the consumer-enumeration gate (charter **C-10**). It is itself a
change to shared contracts, so it is its own first subject: this dossier was written
*before* any code edit, using the same template the gate demands.

---

## Surface

Four surfaces are changed by this branch:

1. `scripts/enforcement/adapters/claude_hook.py` — `_GUARD_NAMES` + `dispatch()`
   (guard registry; a **6th** guard joins the five).
2. `scripts/enforcement/evidence.py` — `_substantive()` promoted to public
   `substantive()` so the new guard can reuse it instead of duplicating it.
3. `docs/dev/AGENT_HANDOFF_TEMPLATE.md` — a new binding rule **inside the existing
   `## Binding rules` `<!-- verbatim -->` section**, i.e. a change to that section's
   canonical text.
4. `scripts/wiki_relevance.py` — a new `IRRELEVANT_PREFIXES` entry for the
   `docs/dev/blast-radius/` directory this branch creates.

---

## Enumeration

Commands run, verbatim, with their counts. All run on this branch at `0bc01e1`
(`git diff main` empty at enumeration time).

```
grep -rn "_substantive|substantive" --include=*.py .            -> 5 hits, 4 real
grep -rn "enforcement\.evidence" --include=*.py .               -> 3 importers
grep -rn "_GUARD_NAMES|_GUARD_ORDER|claude_hook.dispatch" --include=*.py .
                                                                 -> 16 hits / 6 files
grep -rn "wiki_relevance|is_wiki_relevant|filter_relevant" --include=*.py --include=*.sh --include=*.yml .
                                                                 -> 3 consumers + own tests
grep -rn "from scripts.enforcement.guards import" scripts/ tests/ -> 4 importers
```

Ledger sweep for handoffs that could be re-validated against an amended template
(`docs/dev/ledger/*.jsonl`, all shards, `generated` minus `consumed`):

```
handoffs GENERATED but never CONSUMED: 7
  docs/dev/diagnosis/eval-judge-parse-failure.md
  docs/dev/handoffs/chore-dependabot-docs-site.md
  docs/dev/handoffs/chore-dependabot-group-a.md
  docs/dev/handoffs/docs-v110-endgame-scope.md
  docs/dev/handoffs/fix-extract-experiences-telemetry-pollution.md
  docs/dev/handoffs/fix-merge-suggestions-render-cap.md
  docs/dev/handoffs/refactor-css-cascade-collapse.md
```

First-party Python import fan-in (AST walk over `git ls-files '*.py'`, counting
non-test importers) — the measurement the registry is built from, not intuition:

```
 27 db/models.py            20 db/session.py         15 web_infra/__init__.py
 14 ui_pages/selectors.py   13 analyzer.py           13 hardening.py
 12 ui_pages/base.py        12 recall/models.py      10 guards/result.py
  9 scripts/enforcement/gitutil.py                    8 json_resume.py
  8 db/build_context.py      8 blueprints/corpus/_bp.py
```

---

## Consumers

### Surface 1 — the guard registry (`_GUARD_NAMES` / `_GUARD_ORDER`)

| # | Site | Decision |
|---|---|---|
| 1 | `scripts/enforcement/adapters/claude_hook.py:50` `_GUARD_NAMES` | **Update** — add `require-consumer-enumeration` |
| 2 | `scripts/enforcement/adapters/claude_hook.py:69` `dispatch()` | **Update** — add routing branch |
| 3 | `scripts/enforcement/adapters/claude_hook.py:19` module docstring ("the five Edit\|Write guards") | **Update** — prose now says six |
| 4 | `scripts/enforcement/adapters/claude_dispatcher.py:41` `_GUARD_ORDER` | **Update** |
| 5 | `scripts/enforcement/adapters/claude_dispatcher.py:3-9,38-40` docstrings ("all five") | **Update** |
| 6 | `hooks/edit-write-dispatcher.sh:2-6` comment ("the five Edit/Write guards") | **Update** |
| 7 | `tests/test_enforcement_core.py:830` `test_guard_order_is_exactly_the_five_edit_write_guards` — **exact set equality** | **Update** — set + test name + class docstring |
| 8 | `tests/test_governance_hooks_gate.py:108` `DISPATCHED_GUARD_NAMES` frozenset | **Update** |
| 9 | `tests/test_governance_hooks_gate.py:262` `test_dispatcher_guard_list_is_exactly_the_five` — **exact set equality** | **Update** — set + test name |
| 10 | `tests/test_evidence_gate.py:202,229` — membership (`in`), not equality | **No change** — membership assertions stay true |
| 11 | `scripts/enforcement/adapters/git_hook.py:27-34` guard imports | **Deliberately excluded** — see Deferred |
| 12 | `scripts/enforcement/ci_backstop.py:31` | **No change** — imports `block_secrets` only |

**Two exact-set-equality assertions (#7, #9) would have failed the gate had they not
been found first.** This is precisely the class of miss C-10 exists to prevent — my own
plan named only one test file; the grep found three.

### Surface 2 — `evidence.py::_substantive`

| # | Site | Decision |
|---|---|---|
| 1 | `scripts/enforcement/evidence.py:72` definition | **Update** — rename to `substantive()` |
| 2 | `scripts/enforcement/evidence.py:105,108` (`has_observed_evidence`) | **Update** — call the new name |
| 3 | `scripts/enforcement/evidence.py:119` (`replay_text`) | **Update** |
| 4 | `tests/test_evidence_gate.py:33` import block | **No change** — imports `branch_slug`, `diagnosis_path`, `has_observed_evidence`, `replay_text`, `section`, `template_text`; never `_substantive` (verified by reading the import list, not assumed) |
| 5 | `scripts/check_doc_single_home.py:37` | **No change** — the word "substantive" in prose, not a reference |

### Surface 3 — `AGENT_HANDOFF_TEMPLATE.md`'s verbatim section

Consumers are every handoff re-validated against the template by
`scripts/verify_doc_template.py`. **Verified empirically, not assumed:**
`run_checks()` (`:211`) runs structural + verbatim, and `--event consumed` (`:321`)
gates its `consumed`-vs-`blocked` outcome on that same `passed` flag. So amending the
canonical text of a `<!-- verbatim -->` section **would** block a stale handoff.

| # | Site | Decision |
|---|---|---|
| 1 | `docs/dev/handoffs/chore-v11-march-kickoff.md` | **Safe** — already consumed this session (`de30c6a5f788`), never re-consumed |
| 2 | The 7 generated-but-never-consumed docs listed above | **Safe, deliberately** — all belong to branches merged long ago; the pointer chain has moved past them and nothing will consume them. Not retro-fitted. |
| 3 | This branch's own new handoff | **Written from the amended template** — so it validates against it by construction |
| 4 | `docs/dev/AGENT_HANDOFF_TEMPLATE.md` structural headings | **No change** — rule 6 goes *inside* the existing `## Binding rules` body; no new `##` heading, so the structural-heading check is untouched |

### Surface 5 — `scripts/enforcement/blast_radius.py` (the registry itself)

Added mid-branch **because the gate blocked the edit that needed it.** Tightening
`ACKNOWLEDGED_NOT_GATED` is a change to what the gate fires on, i.e. a contract change,
and the dossier did not yet name this file. That block was the guard working, on its
author, unprompted — recorded here rather than smoothed over.

Enumeration: `grep -rn "blast_radius" --include=*.py --include=*.sh --include=*.md
--include=*.json .` → 2 consumer files (the rest are self-references inside the module
and prose mentions).

| # | Site | Decision |
|---|---|---|
| 1 | `scripts/enforcement/guards/require_consumer_enumeration.py:54` — `from …blast_radius import Surface, classify` | **No change** — only `Surface` and `classify()` are consumed; both signatures are untouched by a registry-membership edit |
| 2 | `tests/test_blast_radius_classification.py:31` — imports the module and reads `GATED`, `GATED_PREFIXES`, `ACKNOWLEDGED_NOT_GATED`, `FAN_IN_THRESHOLD`, `classify` | **Update** — `test_no_stale_acknowledgements` is what rejected the two bad entries; it passes once they are removed. No test edit needed, only the registry. |
| 3 | `scripts/enforcement/blast_radius.py:167` — its own `GATED` self-entry | **No change** — the module gates itself on purpose |

### Surface 4 — `wiki_relevance.py`

| # | Site | Decision |
|---|---|---|
| 1 | `scripts/wiki_relevance.py:40` `IRRELEVANT_PREFIXES` | **Update** — add `docs/dev/blast-radius/` (process record, never a wiki source) |
| 2 | `tests/test_wiki_relevance_classification.py:105` stale check | **Satisfied** — the prefix's directory exists as of this branch |
| 3 | `tests/test_wiki_relevance_classification.py:70-93` offenders check | **Satisfied** — the new `docs/dev/` child is now classified, not an unreviewed gap |
| 4 | `scripts/wiki_freshness.py:47` (merge-blocking gate) | **Benefits** — dossiers no longer count as wiki drift |
| 5 | `hooks/wiki-freshness-reminder.sh:56` | **Benefits** — same |

**Without site 1, the new directory would have counted as wiki drift and could have
tripped a merge-blocking gate** — the fourth recurrence of the exact false-positive
shape `docs/dev/diagnosis/wiki-freshness-relevance-classification.md` was written to end.

---

## Deferred

Sites deliberately **not** changed, each with its reason — the
`compose-unawaited-reloads.md` Fact-5 shape.

- **`scripts/enforcement/adapters/git_hook.py` — the new guard is not added to the
  git-native path.** Precedent: `require_evidence_before_fix` is *also* absent there
  (`git_hook.py:27-34` imports six guards, not seven). Dossier-style guards gate the
  *authoring* moment, which only the editor sees; by pre-commit the edit already
  exists, so blocking there punishes without preventing. Matching the C-7 precedent
  deliberately rather than diverging from it.
- **`scripts/enforcement/ci_backstop.py`** — scans tracked files for secrets; there is
  no server-side artifact for "was a dossier written first," so no backstop is possible.
  Stated as a known limit rather than papered over (C-0).
- **The 7 unconsumed handoffs** — not retro-fitted to the amended template (above).
- **Non-Python fan-in** — JS (`static/app.js`), templates, and CSS get no computed
  offenders check; those surfaces are curation-only. Recorded as a known limit in the
  module docstring.

---

## Verification

- `python -m scripts.gate` green (ruff → ruff format → mypy → pytest).
- The two exact-set-equality tests (#7, #9 above) pass with six guards.
- Live end-to-end: an `Edit` to a registered surface with no dossier is blocked with a
  message naming the dossier path; filling `## Consumers` unblocks the same edit.
- `python scripts/verify_doc_template.py` on this branch's handoff against the amended
  template returns `generated`, not `failed`.
- `scripts/wiki_freshness.py` does not count `docs/dev/blast-radius/` files.
