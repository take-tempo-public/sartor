```toml
schema = 1
id = 176
kind = "item"
title = "Fold the still-useful facts from memory that have no repo home into the docs that should hold them"
status = "deferred"
decision_owner = "user"
blocked_on = "owner chose on 2026-10-18 to defer these 44 fold-ins to a later session; nothing here is started"
refs = [
  "docs/dev/work/items/0007-px46-memory-consolidation.md",
  "docs/dev/engineering-recipes.md",
  "docs/dev/AGENT_FAILURE_PATTERNS.md",
  "commands/wiki-self-update.md",
  "evals/README.md",
  "CONTRIBUTING.md",
]
summary = "44 memory files hold facts with no repo home, plus leftovers of 69 deleted ones; fold them into docs."
```

Item 7's sweep (2026-10-18) classified 222 memory files. **44 of them were marked FOLD**: each holds a still-true, useful
fact that no repo document states. The owner chose to defer folding them, so those 44 files **stay in memory untouched**
until this item is worked. It also holds the small unhomed remainders of the 69 files that item 7 deleted, so deleting
them lost nothing silently, and the 9 files that were trimmed to their remainder instead of deleted.

**Rules for whoever works this.** Re-verify each fact against the code before writing it down (several memories were
wrong about paths, counts and line numbers when audited). Follow `skills/doc-writing/SKILL.md` for any doc. A fold into
`AGENT_HANDOFF_TEMPLATE.md`, `blast-radius/TEMPLATE.md` or any file in `scripts/enforcement/blast_radius.py`'s gated
list needs a consumer dossier first (charter C-10). Delete a memory file only after its fact is homed and the owner
approves the row.

## The 44 FOLD files and their proposed targets (agent proposals, not decisions)

- (S1) FOLD (12): ab-fix, attribute-the-subject, measure-the-ordinary-case, trace-fix-design, check-for-superseding, trace-stated-mechanism, verify-handoffs-sequencing, verify-rollup -> ONE new AGENT_FAILURE_PATTERNS.md section (e.g. 5g); enumerate-by-class -> blast-radius/TEMPLATE.md; corpus-mode-eval-coverage -> evals/README.md (re-verify premise first); no-baked-in-absolute-paths -> CONTRIBUTING.md; project-docs-not-personal -> doc-style-guide.md
- (S2) FOLD (2): project-ci-infrastructure-sprint-sequence -> item 0003 Updates (enforce_admins rationale); project-handoff-integrity-kit -> AGENT_HANDOFF_TEMPLATE.md (no markdown links inside verbatim sections)
- (S3) FOLD (8): alembic-downgrade-then-seed-needs-stamp, app-loggers-silent-under-pytest, cpu-saturation-flake-repro, deterministic-capability-probes-for-rival-hypotheses -> engineering-recipes.md (needs header edit: currently "authoritative for the two recipes"); capture-screenshots-demo-state -> screenshot-capture.md; claude-allow-main-edits-scope -> AGENTS.md:201 (+CLAUDE.md:104); dark-factory-research -> item 0097 Updates or archive appendix; eval-harness-auth-and-cost -> evals/README.md cost section
- (S4) FOLD (8): flask-test-client-sse-drain-required + function-local-import-defeats-module-patch + model-upgrade-playbook -> engineering-recipes.md (Test-writing traps / Bump a model pin); gate-from-powershell-hits-wsl-bash -> CONTRIBUTING.md Quick start; handoff-template-verbatim-drift-found -> AGENT_HANDOFF_TEMPLATE.md header; hook-manual-testing -> tooling.md "Hand-testing a guard"; n1-pipeline-no-review-only-stage -> n1-baseline-pipeline.md; openssf-scorecard-hardening -> doc-style-guide.md:122-125
- (S5) FOLD (14): prescription-metrics-can-restale->AFP 5e line; preserve-cross-item-evidence, pytest-in-process-loop-and-mutation-plugins, sandbox-ux-walkthrough-method (needs rewrite around SARTOR_HOME), tests-package-conftest-import -> engineering-recipes.md Testing recipes; rerun-masking-chronic-flake->flake-rates/README.md; review-charter-clause-location->charter.md "What this is"; subagent-pretooluse-agent-id->item 0169 Updates (peer hand-backs still arm witness, seen 3x 2026-10-16); user-docs-verify-against-live-labels->skills/doc-writing/SKILL.md; wiki-auditor-has-no-bash + wiki-scribe-cannot-create-pages + wiki-scribe-head-vs-working-tree -> commands/wiki-self-update.md gotchas block; wiki-checkpoint-ratchet-defect->item 0098 (unchosen option); wiki-freshness-detect-vs-correct->item 0065 Updates

## Unhomed leftovers from the files deleted in batch B

Each line below is a fact or piece of advice that had no (or only a partial) repo home when its memory file was deleted.
The refuters judged them low value; they are listed so the call is the owner's, not an accident. **Two are not
verified facts:** the `55 min` and `~90 min` gate-runtime figures under `reference-gate-memory-preflight-built` have no
source, and the repo's own measurement (`scripts/gate.py:113-116`) says the non-UX run was stopped by hand at about 37
minutes. They are listed so nobody mistakes them for measurements.

- `reference-alembic-batch-parent-fk-cascade`: Symptom detail: PX-02's first cut surfaced as an order-dependent full-suite failure (passes alone, fails after a prior in-process alembic run) blanking TestMigrationBackfill; the repo records only the deterministic downgrade-seed-upgrade repro
- `reference-avatar-citation-format-built`: Live-validation METHOD detail (python heredoc via blueprints.assistant helpers, 'NOT a committed script') is only partly recorded (TUNING_LOG says 'in-process'); low value, the 5/5 result is recorded.
- `reference-avatar-citation-format-built`: cp1252 console showing U+FFFD for em-dashes in piped output is harmless because SSE is ASCII-escaped json.dumps (generic Windows gotcha; separate memory covers cp1252).
- `reference-bash-to-python3-path-gotchas-windows`: Trivia of the deleted `_native_path()` helper: `cygpath -m ""` exits 1 ('can't convert empty path'; I re-ran it, confirmed) and `cygpath -m` is idempotent on C:\ paths (confirmed). Searched repo for 'empty path'/'idempotent' near cygpath: no hit. Helper no longer exists, so low value.
- `reference-bash-to-python3-path-gotchas-windows`: The generic lesson 'a broad `except OSError: pass` hid both defects; temporarily print the exception' is only shown as what was done in the diagnosis, not stated as a rule (PARTIAL).
- `reference-consumer-enumeration-gate-c10`: Imperative 'Before writing or repeating "X is gated", read GATED / GATED_PREFIXES / ACKNOWLEDGED_NOT_GATED in blast_radius.py' - the falsification is recorded (model-pricing-rates.md:65) but the rule as an instruction is not; also work item 0174 line 80 still carries the wrong claim uncorrected.
- `reference-deterministic-generate-built`: That approved_composition therefore carries forward into the child context so preview-after-generate finds it is an implication of the deep-copy line, not stated anywhere (derivable by reading one line).
- `reference-doc-assistant-vector-built`: Keep script logging ASCII because em-dashes mangle in the Windows cp1252 console (generic; scripts/vector_index_probe.py carries no such note; covered by the windows-shell-gotchas memory).
- `reference-driving-the-app-outside-the-ux-suite`: Generalized rule 'any measurement whose expected value could legitimately be zero needs a positive synchronization signal, not a quiescence heuristic' is only implicit in the bench_corpus_scale.py comment (concrete case homed; abstraction not).
- `reference-eval-results-dir-heterogeneous-files`: Generic advice: test eval-results consumers once against the real unmonkeypatched evals/results/ directory because synthetic fixtures cannot reproduce shapes you do not control (only the item-32 incident narrative holds it)
- `reference-gate-memory-preflight-built`: Memory's figure that the full gate including UX took 55 min under the same thrashing conditions: searched git grep for '55 min', '38 min', '55-minute' across tracked files, found none; repo says the non-UX measurement was stopped by hand at ~37 minutes, not completed.
- `reference-gate-memory-preflight-built`: Advice that a ~1.2 GB pass is marginal and to expect ~90 min gate: only the 1.21 GB kill observation is homed; the '~90 min' gate length has no source (handoffs say 'more than 25 minutes').
- `reference-gate-result-file-and-hookspath`: Workaround for the merge-guard heredoc block ('use the Write tool and run the file, not python - <<EOF') is not stated next to block_merge_to_main.py's known-limit note; CLAUDE.md gives the Write-and-run workaround only for block-doubled-backslash / block-long-bash-command.
- `reference-git-grep-self-match-test-gotcha`: General lesson 'any test that greps the real tree for a sentinel must build it at runtime' is stated only for this one test (comment), not as a gated rule; trivial and derivable from the comment.
- `reference-github-status-incident-diagnosis`: The abstraction (a reusable 5-step 'our fault or GitHub's?' recipe) exists only as the worked example in the diagnosis, not as a how-to; every constituent step/evidence is in that dossier.
- `reference-kw3-tour-and-education-help`: Owner decision: panel-level (i) icons ONLY, no tab-button _initTabHelp was built (low value; the code simply has none)
- `reference-list-applications-n-plus-1`: Why the after_cursor_execute guard is clean: per-request init_db() is process-cached (zero SQL on the migrated tmp DB) - only the PRAGMA-on-raw-cursor half is evident in db/session.py; init_db caching is evident at db/session.py:149 but the testing implication is not stated.
- `reference-monitor-silence-is-not-success`: Positive finding that `gh pr checks --json ... --jq` works with no system jq (verified 2026-08-04 per memory); the repo instead chose to avoid even gh --jq. Superseded design choice, so low residual value.
- `reference-per-session-hook-state-kills-orchestrated-runs`: Generalized design lesson 'per-session mutable hook state is unsafe under orchestration because session is the wrong granularity; key on the conversation or fail toward allowing' - only the concrete fix and fail-open note are in the repo, the abstraction is not.
- `reference-playwright-beforeunload-and-drawer-stacking`: Advice: any new control in the Settings drawer that opens a dialog should be click-tested, not only keyboard-tested; Playwright's call log names the interceptor ('<aside id=settingsDrawer> subtree intercepts pointer events'). Heuristic only, partly implied by the CSS comment.
- `reference-scroll-spy-hardening-mechanics`: Measured detail 'observed: 2/5 failures with a 150ms delay' (the evidence the fixed delay was flaky) is in no repo file; the test comment says only 'genuinely flaky'.
- `reference-settle-wait-vs-deliberate-racers`: Generic 'how to apply' (grep all test call sites for patterns that hold/delay part of the same async cascade AND run the FULL suite, since a green single-file run is not evidence): the incident is homed but the extracted rule is only covered by the generic C-10 consumer-enumeration clause; ui_pages page objects other than selectors.py are not in blast_radius.py's gated registry (scripts/enforcement/blast_radius.py:215 exempts ui_pages/base.py).
- `reference-smooth-scroll-survives-navigation`: The abstract triage heuristic 'when a UX scroll position moves with no API write in the spy timeline, suspect a surviving smooth animation and decode y against scrollHeight - innerHeight first' appears only as concrete decoded examples in the dossier.
- `reference-ux-compose-ready-wait`: Per-attempt instrumentation counts (page-request listener 60/60, heavy server log 150/150, light server log 200/200) are in no repo file - CHANGELOG says only 'three separate instrumentation attempts'.
- `reference-wiki-freshness-single-branch-threshold`: Measurement: recomputing the 79-file window under the new classifier gave 12 wiki-relevant files. Not in the repo (diagnosis states only 'materially lower'); one-off verification number.
- `reference-wiki-freshness-single-branch-threshold`: Advice to run `python scripts/wiki_freshness.py` early after scoping a large mechanical branch (not at final gate). Close-out step covers the per-branch case; the 'early' timing advice is prose only (low value).

## Files trimmed to their unhomed remainder instead of deleted

- `project-verify-dont-assume-enforcement-gap`: trimmed to the unhomed remainder; rest homed in docs/dev/handoffs/feat-consumer-enumeration-gate.md, scripts/enforcement/guards/verify_binary_on_path.py
- `reference-docs-site-build-check`: trimmed to the unhomed remainder; rest homed in .github/workflows/docs-deploy.yml, docs/dev/handoffs/docs-assets-enforcement.md, scripts/check_docs_site_mermaid.py, scripts/project_docs_to_mdx.py
- `reference-help-pattern-primitive`: trimmed to the unhomed remainder; rest homed in CHANGELOG.md, static/app.js
- `reference-march-session-model-rules-drift`: trimmed to the unhomed remainder; rest homed in docs/dev/RELEASE_ARC.md
- `project-deterministic-ci-wait-governance`: trimmed to the unhomed remainder; rest homed in scripts/ci_wait.py
- `reference-native-checkbox-css-gotcha`: trimmed to the unhomed remainder; rest homed in static/style.css, ui_pages/corpus.py
- `reference-npm-override-vs-bump-and-ts-esm-detection`: trimmed to the unhomed remainder; rest homed in CHANGELOG.md, docs-site/package.json
- `reference-f01-keyword-cleaning-built`: trimmed to the unhomed remainder; rest homed in CHANGELOG.md, hardening.py
- `reference-sartor-rename-recruiting-pun`: trimmed to the unhomed remainder; rest homed in CHANGELOG.md, templates/index.html

## Updates

### 2026-10-18 - filed during `chore/memory-consolidation` (item 7)

Filed from the sweep and the adversarial read recorded in item 7. Nothing in this item is started.
