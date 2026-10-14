# Blast radius — recurrence-guardrails

> **Branch:** `fix/recurrence-guardrails`
> **Status:** enumeration complete for the planned edits. A surface not named here is not
> approved by this dossier; add it here first (C-10).

---

## Surface

Gated surfaces this branch edits (registry: `scripts/enforcement/blast_radius.py`):

- `docs/dev/prov/SPEC.md` (§3: document the `compacted` and `plan-archived` events and the
  trunk-spool rule).
- `docs/wiki/SCHEMA.md` (only if the "prefer symbols" cite rule becomes "no bare line cites";
  decided when `scripts/wiki_cites.py` lands).

Ungated surfaces whose consumers still matter:

- `scripts/enforcement/guards/interrogative_witness.py`: `record_prompt`, `decide`,
  `claude_check`, and the state-file shape (`prompt_seq`, `interrogative`, `witnessed`, plus
  new `armed_seq` and `paused_batch`).
- `scripts/enforcement/adapters/prompt_witness_hook.py`: passes more of the payload to
  `record_prompt`.
- `scripts/enforcement/adapters/claude_context_hook.py`: `_ledger_shard`,
  `record_compaction`, `compaction_count`.
- `scripts/enforcement/plan_gate.py`: the `plan-archived` write (`:276-292`).
- New (built): `scripts/enforcement/ledger_spool.py`, with two importers outside tests
  (`claude_context_hook.py`, `plan_gate.py`); `tests/test_ledger_spool.py`.
- New: `scripts/wiki_cites.py`,
  `tests/_controls.py`, `tests/test_xfail_controls_gate.py`, `tests/test_wiki_cites.py`.
- `agents/wiki-grounding-auditor.md` (`model:` and method), `commands/wiki-self-update.md`.

`scripts/enforcement/gitutil.py` (gated, 9 importers) is **read, not edited**:
`git_branch` is called as it is. If that changes, this dossier gets a row first.

---

## Enumeration

Run on `main` @ `d9f1b8f` plus this branch's first commit, with
`git grep -In -e <pattern> -- . ':!docs/dev/handoffs' ':!docs/dev/ledger' ':!docs/wiki/log.md'`
and the work-item directory excluded (records, not consumers). Names searched per surface:

| Surface | Patterns | Non-record hits |
|---|---|---|
| ledger writers | `record_compaction`, `compaction_count`, `_ledger_shard` | 42 lines: 10 in `claude_context_hook.py`, 22 in `tests/test_c12_disclosure_gate.py`, 1 each in `tests/conftest.py` and `tests/test_verify_doc_template.py`, 8 prose lines in `docs/dev/` |
| `plan-archived` | `plan-archived` | 22 lines: code in `plan_gate.py:281`; tests `tests/test_plan_approval_scoping.py:638`, `tests/test_verify_doc_template.py:297,331`; the rest is CHANGELOG, diagnoses and blast-radius prose |
| ledger dir path | `dev/ledger`, `"ledger"` over `*.py *.mjs *.json *.yml *.toml` | `scripts/doc_registry.py:33`, `claude_context_hook.py:158`, `plan_gate.py:289`, `scripts/flake_rates.py:94` (comment), `scripts/verify_doc_template.py:15,281`, `scripts/wiki_relevance.py:8,46`; tests: `test_c12_disclosure_gate`, `test_n1_pipeline`, `test_plan_approval_scoping`, `test_verify_doc_template`, `test_wiki_relevance_classification` |
| `compacted` string | `"compacted"`, `` `compacted` `` | `claude_context_hook.py:162,170,174,192,197`; `docs/governance/charter.md:332`; `docs/dev/n1-baseline-pipeline.md:226,284`; tests `conftest.py:75`, `test_c12_disclosure_gate.py:160,244`, `test_verify_doc_template.py:274,276` |
| witness | `record_prompt`, `interrogative_witness`, `SARTOR_WITNESS_STATE_DIR` | 48 lines: `claude_hook.py:56` (route), `prompt_witness_hook.py:6,31,41,42`, `interrogative_witness.py`, `tests/conftest.py:64,66`, `tests/test_interrogative_witness.py`, `tests/test_governance_hooks_gate.py:420,425`, `tests/test_enforcement_coverage.py:54,131`, `docs/governance/enforcement.md:142,158`, wiki `consistency-tracks-enforcement.md:138-139` and `governance-extraction.md:151,154` |
| wiki auditor | `wiki-grounding-auditor`, `claude-haiku-4-5-20251001` | `CLAUDE.md:216,234-235`, `docs/dev/tooling.md:112`, `docs/dev/decisions.md:52` (PX-47b), `commands/wiki-self-update.md:2,19,77-78`, `docs/wiki/SCHEMA.md:159`, `scripts/enforcement/blast_radius.py:112`, `agents/*.md` |
| `ControlFailed` | `ControlFailed` | the two test files only; 0 other code consumers |

Negative results: `git grep -n "dev/ledger" -- .githooks .github scripts/gate.py` returns 0
lines, so no git hook, workflow or gate step reads the ledger directory.
`tests/test_n1_pipeline.py:445` asserts `"docs/dev/ledger" not in script_src` for the n1
workflow script, so the helper must not be referenced from `.claude/workflows/n1-baseline.mjs`.

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/enforcement/adapters/claude_context_hook.py:153-158` `_ledger_shard` | update | Route through the new helper; returns the tracked shard on a branch, the untracked spool on trunk. |
| 2 | `claude_context_hook.py:161-170` `compaction_count` | update | Must count both locations, else the C-12 notice and the threshold notice read 0 after a trunk compaction (fail-open silently). |
| 3 | `claude_context_hook.py:173-226` `record_compaction` | update | Writes through the helper. Field set unchanged. |
| 4 | `scripts/enforcement/plan_gate.py:276-292` | update | Same helper. `branch or "unknown"` already maps an unreadable branch to `"unknown"`, which the helper treats as trunk. |
| 5 | `scripts/verify_doc_template.py:221-250,281` `read_ledger` | no change | Reads `docs/dev/ledger/*.jsonl` only. The spool is deliberately outside it: a spool row is never joined into provenance reads. |
| 6 | `tests/test_c12_disclosure_gate.py:157-306` | no change (as built) | Hardcodes `tmp_path/docs/dev/ledger/<sid>.jsonl`; these tests run on a tmp dir that is not a git repo (branch `""`), which the helper keeps on the tracked shard, so all 27 pass unedited. See Deferred 1. |
| 7 | `tests/test_verify_doc_template.py:294-372` `_LEDGER_APPEND_WRITERS` | update | The helper opens the file for append; register it, pin `newline="\n"`, and add the spool dir to the CR-byte scan. |
| 8 | `tests/test_plan_approval_scoping.py:638` | no change | Reads the receipt from the tracked shard on a feature branch; stays true. Verify, don't assume. |
| 9 | `tests/conftest.py:69-80` `_no_live_session_id` | no change | Still deletes `CLAUDE_CODE_SESSION_ID`. Add the spool dir to the autouse isolation if a test can reach the real one. |
| 10 | `docs/dev/prov/SPEC.md` §3 | update | Add `compacted`, `plan-archived`, and the trunk spool. Closes item 55's drift for these two events. |
| 11 | `docs/dev/ledger/README.md:3-8` | update | Stale "exclusively by verify_doc_template". |
| 12 | `docs/dev/n1-baseline-pipeline.md:225-233,284` | no change | Says a branch-time gate run can gain a `compacted` receipt. Still true on a branch. |
| 13 | `docs/governance/charter.md:332` | no change | Cites the receipt as durable; the spool is durable local state and the branch rows stay committed. Re-read at the edit. |
| 14 | `scripts/wiki_relevance.py:8,46` | no change for the ledger | `docs/dev/ledger/` is process churn. The spool is outside `docs/`. **But see row 34.** |
| 15 | `scripts/doc_registry.py:33` | no change | Record prefix; unaffected. |
| 16 | `interrogative_witness.py:132-151` `record_prompt` | update | Takes the extra payload facts; skips arming on a non-human turn; keeps counting `prompt_seq`. Signature stays backward compatible (new args optional). |
| 17 | `interrogative_witness.py:176-198` `decide` | update | Adds batch-sibling blocking. Every failure path still allows. |
| 18 | `prompt_witness_hook.py:38-46` | update | Passes `payload` to `record_prompt`; stays always-exit-0. |
| 19 | `claude_hook.py:56`, `claude_dispatcher.py:52-66` | no change | Routing and ordering untouched; the witness still runs last. |
| 20 | `tests/test_interrogative_witness.py` | update | New cases listed in the plan; existing lifecycle tests keep their `record_prompt(session, prompt, env)` calls. |
| 21 | `tests/test_governance_hooks_gate.py:420-430`, `tests/test_enforcement_coverage.py:54,131` | no change | Wiring and Claude-only classification; re-run. |
| 22 | `docs/governance/enforcement.md:158-169` | update | Names task-notifications and the batch case; drops "only the hand-back". |
| 23 | `docs/wiki/pages/consistency-tracks-enforcement.md:138-139`, `governance-extraction.md:151,154` | no change unless the sentence about re-arming is quoted | Verify at wiki update; the scoped `/wiki-self-update` covers it. |
| 24 | `agents/wiki-grounding-auditor.md:4` | update | `model: claude-sonnet-5` (owner decision, 2026-10-14). |
| 25 | `CLAUDE.md:228-241` (Model-pin convention) | update | The note says three dated Haiku pins; after this branch two. Also says "do not re-pin the split": this is a deliberate model change for a stated reason, so reword rather than leave a contradicting note. |
| 26 | `docs/dev/decisions.md:52` (PX-47b) | update | Records "the 3 Haiku subagents". Append a dated line; do not rewrite the decision. |
| 27 | `docs/dev/tooling.md:112` | update | Table row names the auditor's model. |
| 28 | `commands/wiki-self-update.md:2,19,77-78,117-123` | update | Description and body say "Haiku diff-pass" and "(Haiku, read-only)"; add the cite-check step and the review step; the cost note changes. |
| 29 | `docs/wiki/SCHEMA.md:159` | no change unless the cite rule changes | Gated; touched only with an added row here. |
| 30 | `tests/test_n1_pipeline.py:831` `test_frontmatter_pins` | no change | Pins the n1 agents only, not the wiki auditor. Verify by running it. |
| 31 | `tests/test_wiki_relevance_classification.py:170-243` | update | The path-token regex and resolver move into `scripts/wiki_cites.py` and this test imports them. Behavior must be identical; its own tests are the check. |
| 32 | `tests/test_regenerate_cover_letter.py:61-67`, `tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py:70-76` | update | Import `ControlFailed`/`_control` from `tests/_controls.py` instead of defining them. |
| 33 | `scripts/gate.py` | no change (decided while building) | The check is a pytest test (`tests/test_wiki_cites.py::TestTheRealTree`), which the gate's `pytest -m "not ux"` step and CI already run, the same way `tests/test_wiki_freshness_gate.py` rides it. A separate step would run it twice. Deviation from the plan, recorded here. |
| 34 | `scripts/wiki_relevance.py` `RELEVANT_OVERRIDES` (gated helper, the classifier behind the merge-blocking freshness gate) | update | `docs/wiki/SCHEMA.md` now cites `scripts/wiki_cites.py`, so `test_relevant_overrides_equal_wiki_cited_mixed_files` requires the override: found by staging the new file and running that test (it passed while the file was untracked). One entry, sorted; no classification logic changes. |
| 35 | `docs/wiki/SCHEMA.md` "Grounding for code claims" (gated) | update | One sentence naming the mechanical enforcement. Its consumers (registry: the scribe, the auditor, `/wiki-lint`) read the cite rule; the rule itself ("prefer a symbol") is unchanged, so no reader's behavior is contradicted. |
| 36 | `agents/wiki-grounding-auditor.md` method | update | Four checks the logged misses show were skipped (branch claims, negative claims, intent, placement), and bare line cites as a finding. Read by `commands/wiki-self-update.md` only. |

---

## Deferred

1. **Trunk detection in a non-git temp dir.** The existing c12 tests call
   `record_compaction` with `cwd` = a plain `tmp_path`, where `git_branch` returns `""`. As
   built: only the names `main`, `master` and `HEAD` spool, so `""` (no repo, or `git` failed)
   keeps the tracked shard. A real repo where `git` fails therefore keeps today's behavior, a
   declared limit. `plan_gate` reports a detached HEAD as `""` and so also stays tracked.
2. **Rows already written.** Nothing is migrated. There was no stray row at the start of this
   session (`git status` clean on `main` @ `d9f1b8f`, per the session-start snapshot); the one
   untracked file now is this session's own consumed-ledger file, which the first commit
   carries as `docs/dev/prov/SPEC.md` §5 step 3 requires.
3. **A subagent-written row on trunk** takes the same path (same `payload`); no special case.
4. **The `trigger` field is always `"unknown"`** (item 85). Out of scope.
5. **The Compose-scope and Bash-run edits outside the Edit|Write gates** carried in the handoff.
   Out of scope.

---

## Verification

- A test enumerates the writers: any module that opens a file under `docs/dev/ledger` for
  append must go through the helper (extends `_LEDGER_APPEND_WRITERS`). A site I did not list
  surfaces as that test failing.
- The witness consumers fail closed in `tests/test_interrogative_witness.py`; the c12 suite and
  `tests/test_enforcement_core.py`'s dispatcher cases are re-run unchanged.
- `python -m scripts.wiki_cites` over the whole tree after the edit, and `check_doc_links`.
- Re-run the grep table above after the last edit and diff the counts against this file.
