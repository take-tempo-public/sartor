<!-- provenance: schema=1 session=01ff2090-676f-46cf-849c-b261a2c4c7e2 branch=fix/b1-stale-template-companions commit=2807979 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-12 -->

# Handoff — B1a closed (stale imported-template companions fixed; refuter F1 applied, F2 deferred as item 88); B1b is next

> **The single most important thing this handoff carries forward:** B1a's sprint
> content is done and staged (not yet committed — that is the finalize stage's
> job, not this closer's). This closer applied exactly one confirmed refuter
> finding (F1 — a docstring/implementation contract mismatch in
> `companion_stamp_is_current`), filed one deferred finding (F2, item 88), and
> found + filed a second, unrelated discrepancy while writing this very handoff
> (item 89 — the pipeline's own closer prompt does not match the epic's declared
> cadence). **This closer did not observe how the refuter/judge stage that
> produced F1/F2 actually ran** — that disposition arrived as this stage's task
> input, not as something witnessed. Flagged, not asserted (C-12).

**Branch to create:** `fix/b1-education-render` (branch off `epic/b-render-ats`;
sprint B1b — name and scope fixed in
`docs/dev/handoffs/epic-b-design-brief.md` row 2, do not rename)
**Base branch:** `epic/b-render-ats` — **cut fresh off the epic tip AFTER this
branch (`fix/b1-stale-template-companions`) fast-forward-merges in.** At
handoff-writing time the epic branch is still at `247c810` (pre-B1a); this
branch's own gate #1, finalize commit, gate #2, and ff-merge have not
happened yet and are NOT this closer's to run (§11.9).

---

## Documents to read before any tool call (in this order)
<!-- verbatim -->

1. `docs/dev/RELEASE_ARC.md` — authoritative branch sequence,
   architectural decisions, and acceptance criteria for v1.0.2 → v1.1.0.
   The durable plan. Do not deviate without user sign-off.
2. `docs/dev/RELEASE_CHECKLIST.md` — what is open, closed,
   and deferred per release. Before proposing anything, check here first.
3. `docs/dev/AGENT_FAILURE_PATTERNS.md` —
   failure patterns to avoid. Read in full before writing any code.
   **§5f ("Guessing the mechanism") is the expensive one — it is why the
   Binding-rules block below exists.**
4. `docs/governance/charter.md` — the binding
   constitution. **C-7 (evidence before mechanism) and C-8 (durable before
   deep) are enforced by hooks, not by your judgment.**
5. `docs/architecture.md` — module map and LLM routing
   boundary. The deterministic / LLM split is load-bearing.
6. `evals/TUNING_LOG.md` — baseline floors and
   prompt change history.
7. **If this branch is a `fix/*`:** its diagnosis dossier at
   `docs/dev/diagnosis/<branch-slug>.md`, if one exists. It is the durable
   evidence record — what was **observed**, what was **falsified** (do not
   re-chase those; each one cost real money to kill), and what is still only
   **inferred**. The `restore-evidence` SessionStart hook replays it into your
   context automatically, including after a compaction.

---

## Where we are in the arc

**Epic-specific reading, on top of the numbered list above (do not expect it
restated here):** `docs/dev/handoffs/epic-b-design-brief.md` (standing
context — read in full; **§"Close-out intervals" is the source of the item-89
discrepancy below — read it and `.claude/workflows/n1-baseline.mjs:441-446`
side by side before picking a handoff format for YOUR close-out**),
`docs/dev/n1-baseline-pipeline.md` (pipeline contract + runbook — step 0a is
binding), `docs/dev/diagnosis/b1-stale-template-companions.md` +
`docs/dev/blast-radius/b1-stale-template-companions.md` (this sprint's C-7/C-10
dossiers — read for the mechanism B1b's own education-rendering fix will sit
beside), `docs/dev/work/items/0084-build-n1-baseline-pipeline.md` (all
pipeline first-run evidence, including the three item-84 fixes this branch
carries), and `docs/dev/work/items/0089-sprint-brief-template-not-wired-into-n1-pipeline.md`
(the handoff-template discrepancy this closer found and did not fix).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics,
A→E, strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first
(A–C), docs after (D), release last (E).
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build, merged
  `31d2574` (PR #125). BUILT, then run.
- ~~`docs/epic-b-briefs`~~ ✓ — Epic B design brief + B1a sprint brief, merged
  `5b8bafc` (PR #126).
- ~~`fix/n1-args-guard-hardening`~~ ✓ — refuter fixes mutant-verified, C-11
  CRLF gate, runbook step 0a. ff-merged into the epic branch, pruned.
- ~~`feat/interrogative-prompt-witness`~~ ✓ — item 87's two witness hooks
  built, live-fired, closed. ff-merged into the epic branch, pruned.
- **`epic/b-render-ats`** ← the epic umbrella, still at `247c810`, UNMERGED
  and staying that way until the epic close.
- **`fix/b1-stale-template-companions`** ← **this branch, sprint B1a.**
  Carries THREE item-84 pipeline-infrastructure commits found live during
  this run's own preflight/first-agent-spawn attempts (`acdb737`, `c433c35`,
  `2807979` — see "What just landed" below), plus the sprint's own content
  (staged, **not yet committed** — commit is the finalize stage's job).
- **`fix/b1-education-render`** ← **next: yours.** Sprint B1b. Cut it fresh
  off the epic tip **after** this branch's ff-merge (not before).
- `feat/ats-conformance` ← B2, after B1b. Not started; Sonnet implementer
  per the model table.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on this branch:** B2's scope
(`feat/ats-conformance` — ATS date formatting, month hard-block, approved
fonts; `epic-b-design-brief.md` row 3); pre-authoring B2's own sprint brief
(each run's closer writes the next); widening N past 1 (owner decision,
§16.7); retiring or merging `AGENT_HANDOFF_TEMPLATE.md` or
`EPIC_SPRINT_BRIEF_TEMPLATE.md`; **fixing item 89's `n1-baseline.mjs`
discrepancy** — that is a change to the pipeline mechanism itself, mid-epic,
which is a scope change under §11.6.5 (flag-stop territory, owner decides);
the watching-bucket triage (43 items now — this is at least the EIGHTH
handoff flagging it, per the predecessor's own count of seven).

---

## What just landed on `epic/b-render-ats`

**Nothing yet — `epic/b-render-ats` is untouched at `247c810`.** This handoff
is written pre-PR, per the close-out checklist's own ordering (handoff before
merge). Everything below is on `fix/b1-stale-template-companions`, branched
off that same `247c810` epic tip.

**Three item-84 pipeline-infrastructure commits, already on this branch
before this closer was invoked** (reconstructed from `git log` + commit
messages per C-12 — this closer did not witness them happen):

- `acdb737` — recorded the item-87×hook_block PAUSE interaction found in this
  run's own preflight (a benign, self-clearing witness pause reaching the
  implementer's first Edit was mis-surfaced as `kind:"hook_block"`, which
  the escalation primitive short-circuits to a stop with no reviewer).
- `c433c35` — run 3 result: the pipeline spawned a real agent for the first
  time; the implementer completed the full B1a sprint (7 files, 771
  insertions, staged), then the run died at the refuter spawn (`agent type
  'n1-refuter' not found`) — bare-name `agentType` dispatch falsified, not
  merely untested.
- `2807979` — namespaced the `agentType` dispatch to `sartor:n1-refuter` /
  `sartor:n1-judge` (matching the plugin-namespace convention CLAUDE.md
  already documents), added a deterministic
  `unregistered_agent_types()` check plus a live probe script
  (`.claude/workflows/n1-agent-probe.mjs`) wired into runbook step 0a.

**The B1a sprint content itself** — the diff this closer inherited staged,
matching `c433c35`'s own "7 files, 771 insertions" count exactly:

- `docx_to_persona_html.py` — new `skeleton_version()` (cached SHA-256 of the
  shipped HTML skeleton); `.persona.json` sidecar gains a `skeleton_version`
  key; `companion_stamp_is_current` gains the stamp comparison; new public
  `resolve_companion_html(docx_path)` entry point (generate when absent,
  regenerate when owned-and-stale, return unchanged otherwise).
- `blueprints/templates.py` (3 sites: `preview_application_html`,
  `preview_edited_html`, the corpus preview) + `generator.py` (1 site,
  `_render_pdf_from_json`) — all four route through `resolve_companion_html`
  in place of the old resolve-then-generate pair that never reconsidered an
  *existing* companion.
- `tests/test_docx_to_persona_html.py` — new regression coverage (stale
  companion refreshes; bundled hand-authored companions are never touched;
  current companions are not needlessly regenerated).
- `docs/dev/diagnosis/b1-stale-template-companions.md` +
  `docs/dev/blast-radius/b1-stale-template-companions.md` — the C-7/C-10
  dossiers (root cause proven live; consumer enumeration complete before the
  first edit, per the diagnosis dossier's own falsification experiment).
- `CHANGELOG.md` entry.

**This closer's own additions**, applying the refuter/judge disposition
received as this stage's task input:

- **F1 (CONFIRMED, fixed).** `companion_stamp_is_current` tested sidecar
  *readability* (`_read_sidecar` returns `None` for both an absent sidecar
  AND an unreadable/malformed one) where its own docstring claimed
  *presence* was the ownership test. Corrected the `None` arm to
  `return not sidecar.exists()`: absent (a hand-authored bundled companion)
  stays protected; present-but-unreadable (ours — the module owns every
  sidecar it has ever written) is now treated as stale and left to
  self-heal on the next resolve, instead of silently freezing forever.
  Docstring rewritten to state presence-not-readability explicitly. New
  test `test_unreadable_sidecar_is_treated_as_stale_not_bundled`
  (parametrized: truncated JSON + valid-but-non-dict JSON) in
  `tests/test_docx_to_persona_html.py`. **24/24 tests pass, zero reruns**;
  targeted `ruff check` / `ruff format --check` clean on the two touched
  files. This is a targeted sanity check only — **not the real gate**; this
  closer does not run `python -m scripts.gate` (§11.9).
- **F2 (CONFIRMED, deferred as work item 88).** The four
  companion-resolution call sites (3 preview routes +
  `_render_pdf_from_json`) have no integration test asserting each passes
  the *refreshed* companion, only a resolved one — today the wiring is
  verified by a manual `git grep` in the blast-radius dossier. Deferred,
  not fixed: closing it properly is a test-architecture decision (the real
  PDF tests are Playwright-gated and skip in the default suite) outside
  B1a's brief, per the judge's own rationale reproduced in item 88.
- `docs/dev/work/BOARD.md` regenerated (`python -m scripts.work_items
  check` → OK, 89 files).
- **New finding, filed as work item 89 (not a fix, a disclosure).**
  `.claude/workflows/n1-baseline.mjs:441-446` (the closer role's own
  hardcoded prompt) unconditionally directs every closer — sprint or epic —
  to the full `AGENT_HANDOFF_TEMPLATE.md` + `verify_doc_template.py`
  ceremony. `epic-b-design-brief.md`'s own owner-approved "Close-out
  intervals" section declares a **lighter** `EPIC_SPRINT_BRIEF_TEMPLATE.md`
  for intra-epic sprint transitions, deferring the full ceremony to the
  epic close. This closer's own task instructions matched the `.mjs` script
  verbatim, so this closer followed them — the more conservative reading
  (more ceremony, not less), and not a violation of either source — and
  filed the discrepancy rather than silently resolving it one way. Full
  citation of both sources, and why no mechanism was authored, is in item
  89.
- **Scoped wiki self-update** (hand-authored by this closer — no
  scribe/auditor pair spun up for a one-paragraph factual correction, per
  §11.8 judgment on proportionality): `wiki-relevant paths in this diff = 3`
  (`docx_to_persona_html.py`, `blueprints/templates.py`, `generator.py`).
  [`document-rendering`](../../wiki/pages/document-rendering.md)'s
  PDF-companion-resolution paragraph named
  `pdf_render.py:html_template_path_for` as *the* resolver; this branch's
  own routing change makes that stale (`resolve_companion_html` is now the
  entry point; `html_template_path_for` is an internal existence check it
  calls). Corrected in place with a pointer to the diagnosis dossier. 9
  other pages citing the three changed files, or the specific new/changed
  symbols by name, checked and verified no further edit needed (full
  citation list in `docs/wiki/log.md`'s new entry). `.last_ingest_sha` **not
  advanced** — 14/75 drift, under both the block threshold and the epic's
  own 40-file deferral margin, so the full pass correctly stays deferred to
  the epic close.

**What this closer did not observe (C-12 disclosure, stated plainly rather
than filled in).** The refuter/judge stage that produced F1/F2's disposition
ran before this closer was invoked. This closer received the disposition as
typed task input (a judge-decision citing specific code lines and docstring
text, internally consistent with the diff actually inherited) and did not
witness how that review executed — whether via the now-namespace-fixed
`n1-baseline.mjs` (a fourth pipeline run) or a differently-orchestrated
equivalent. The ledger/journal is the authoritative record for that stage;
this closer has not read it and is not asserting a mechanism it did not see.

**Gate status:** the real gate (`python -m scripts.gate`) has **not** run
against this tree and is **not** this closer's to run. Per the corrected
ordering (`docs/dev/epic-a-chain-design-corrections.md` §2 / §11.9.4), gate
#1 and the step-6 accounting assertion belong to the orchestrating session,
next; the commit belongs to the finalize stage after that; gate #2 runs
against the committed tree before the ff-merge.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m
scripts.work_items board --write`). Re-derived from the board as regenerated
at this branch's close (`python -m scripts.work_items check` → OK, 89 files),
not copied from the previous handoff.

**Open — 1 top-level item + 2 open epics (unchanged):** **50** (C-7/C-10
enforced by Claude Code hooks only — prose binds other agents). Epics **19**
and **36** open — **Epic A's item 36 `status` was never flipped `closed` —
this is at least the EIGHTH handoff flagging it** (the predecessor recorded
"seventh"; still unresolved; this closer did not investigate why, it is not
this branch's scope).

**Blocked — 3 top-level (unchanged):** **3** ([HUMAN] GitHub toggles), **5**
(grounding-score persistence gap), **8** (Compose rewrite latitude,
evidence-gated on the PX-39 run), plus the Epic B–E epics **37, 38, 39, 40**;
**9**, **10** are epic-nested.

**Deferred (7, unchanged):** **4, 7, 24, 25, 41, 42, 43** — see `BOARD.md`
for one-line detail.

**Watching — 43 top-level (was 41; +2 this session — 88, 89 newly filed):**
2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 58, 59, 60, 61, 62, 63,
64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83,
84, 85, **88, 89**. **The reduction-sprint flag stands — at least an eighth
handoff flagging it, still not scheduled.**

- **Item 84 stays `watching`** — this session's own contribution to its
  evidence trail (the namespace fix + the live probe script) is already
  recorded in commits `acdb737`/`c433c35`/`2807979`, which predate this
  closer's invocation; not re-narrated here beyond the citation above.
- **Items 88 and 89 are new this session** — both filed by this closer, both
  `agent`-owned, both `watching` (neither blocks forward progress; both are
  disclosed gaps, not defects).

---

## Recurrences observed this session → guardrail authored

**Two recurrences recognized. No new mechanism authored for either — one
because the existing mechanism already fired correctly, one because the only
available mechanism-fix is itself an out-of-scope change under §11.6.5.**

1. **Wiki citation drift (`document-rendering.md`'s PDF-companion-resolution
   claim) — recognized as a member of the existing doc/mechanism-drift class
   already populated on this board (items 54, 65, 81, 82, 86).** No new
   mechanism authored, none needed: the existing AGENTS.md pre-close
   wiki-relevance-check discipline (the same one every closer runs) IS the
   mechanism, and it worked — it is what directed the check that found and
   fixed this drift before it went unnoticed. Recorded here as the mechanism
   working, not as a gap, per the same framing the predecessor handoff used
   for its own items 2 and 3.
2. **`epic-b-design-brief.md`'s declared lighter per-sprint handoff cadence
   vs. `n1-baseline.mjs`'s hardcoded full-ceremony closer prompt (item 89,
   new) — recognized as the same doc/mechanism-drift class from a different
   angle: a design intent that was never wired into the pipeline code that
   is supposed to enact it.** No mechanism authored on this branch: editing
   `n1-baseline.mjs` mid-epic-run, on a sprint's own closing turn, is itself
   a scope change to the pipeline mechanism under active test — matching
   `docs/dev/epic-a-chain-design-corrections.md` §11.6.5 ("a C-11 recurrence
   whose fail-closed mechanism would be a new enforcement surface — that is
   itself a scope change, and the owner decides") close enough to treat as
   that clause rather than improvise around it. Filed as item 89; surfaced
   in "What just landed" above and here, per C-11's explicit allowance for
   "no mechanism authored, stated plainly why."

---

## What this branch should build

**This branch's own work is complete — see "What just landed" above. The
NEXT branch (B1b, `fix/b1-education-render`):**

1. **Cut `fix/b1-education-render` off `epic/b-render-ats`'s tip**, after
   this branch's ff-merge lands (not before — record the real base sha in
   this brief's own successor, the same discipline `epic-b-b1a-brief.md`
   used).
2. Per `docs/dev/RELEASE_ARC.md` §"Epic B" (B1, second bullet,
   `RELEASE_ARC.md:1899-1911`) and `docs/dev/handoffs/epic-b-design-brief.md`
   row 2 (Sprint → pipeline-run mapping table):
   - **Verify the repro live FIRST, before touching any code.** The reported
     docx education-rendering behavior is stated to conflict with the code
     trace — the docx writer allegedly reads only institution + area, never
     `studyType` (cited at `generator.py:883-896` in RELEASE_ARC; **this
     closer did not independently re-verify that citation** — re-check it
     against HEAD before trusting it, per C-7/C-12, exactly as the sprint's
     own scope description instructs).
   - Then render `studyType` in the `classic`/`spacious` skeletons, the docx
     education block, and the markdown round-trip.
   - Render-both — **never flip** the documented `area`/`studyType`
     inversion without a data audit. Cite per `epic-b-design-brief.md`'s own
     re-anchor: `corpus_to_json_resume.py:909-932` (RELEASE_ARC's
     `855-878` is stale, per that brief's "Cite-drift note").
   - Close the docx font-name capture gap: `_capture_proto` captures
     bold/size but not `run.font.name` (`generator.py:498-514`).
3. **First move is the diagnosis dossier's `## Observed` section, never the
   fix** — this is a `fix/*` branch, so `require-evidence-before-fix` blocks
   production edits until it exists. "Verify the repro live first" above IS
   that first-artifact requirement, not optional framing.

**Explicitly OUT of scope:** everything in B2 (`feat/ats-conformance` — ATS
`MM/YYYY` date formatting, month hard-block + corpus badge + import-path
surfacing, approved-fonts list, structural ATS tests); any refactor beyond
what is listed above; pre-authoring B2's own sprint brief (that run's closer
writes it, per the same "inter-sprint handoff under test" discipline this
handoff itself follows).

Scope is bounded to §"Epic B — `epic/b-render-ats`" (B1, second bullet) in
`RELEASE_ARC.md` plus `docs/dev/handoffs/epic-b-design-brief.md` row 2. Do
not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py`) and
stamp it consumed, then execute runbook step 0a — the batched preflight
question set (confirm the run opt-in with the owner plus every other decision
this reading surfaces, in ONE message) — **before creating any branch or
touching any code.** The branch cut (`fix/b1-education-render` off
`epic/b-render-ats`) happens only after that go-ahead, **and only after**
this branch's own ff-merge has actually landed on the epic branch — verify
`git log epic/b-render-ats` shows this branch's commits before cutting, do
not assume it from this handoff's own prose. The plan-marker ceremony may
precede your first edit (one blocked edit flushes a stale stamp — see memory
`reference-flush-stale-plan-stamp-on-branch-not-main`; **never hand-create
the marker**). Your first Edit/Write of each turn may also draw the item-87
witness PAUSE — re-run the identical call; that is its designed rhythm,
distinct from any hook block that names a different guard.

---

## Binding rules — no discretion (copy verbatim — MANDATORY in every handoff)
<!-- verbatim -->

**These are not heuristics, and your judgment does not decide whether they apply
today.** Each one exists because an agent decided it did not apply, and was
expensively wrong. Read them as prohibitions, not as advice.

**1. Evidence before mechanism (charter C-7). If you did not SEE it, you did not
find it.**
- For a defect you cannot reproduce on demand, **the first commit on this branch
  is the instrument or the reproduction — never the fix.** The
  `require-evidence-before-fix` hook blocks production edits on a `fix/*` branch
  until `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section. There is no escape hatch. `docs/**`, `tests/**` and `*.md` stay
  writable, so the way through is always open: **write down what you saw.**
- **Reading code and finding a plausible mechanism is a HYPOTHESIS.** Put it under
  `## Inferred` and label it as unproven. A fix for a real defect that isn't
  **the** defect still leaves the bug — and plausibility is exactly what makes you
  skip the check.
- **Never scope an instrument to the theory you are testing.** It will confirm
  your theory by hiding its rivals. Capture wider than you think you need.
- **Green CI is not evidence if the test needed a retry.** `pytest-rerunfailures`
  reports a fail-fail-pass as a bare `PASSED` with **no traceback anywhere in the
  log**.
- If you are not certain **from evidence**, say **"I have not verified this"** and
  **stop**. That sentence is always cheaper than the alternative.

**2. Durable before deep (charter C-8). The context window is not a store.**
- Write a hard-won fact — a measurement, a falsified hypothesis, an observed
  artifact — to its durable home **in the turn you learn it.** Not at close-out.
  The pre-close sweep *reconciles*; it must not *discover*.
- **Compaction is an unannounced data-loss event.** After one, reconcile against
  the repo and git — never continue from a summary as though it were the evidence.
- **A thin context is a handoff trigger, not a push-harder trigger.**

**3. Hooks are not obstacles (see `feedback_hook_discipline`).**
- **NEVER** bypass a hook on your own initiative. Never hand-create the file a hook
  checks for. Never skip a step that has no escape hatch. Escape hatches
  (`CLAUDE_ALLOW_MAIN_EDITS=1`, `CLAUDE_CONFIRM_MERGE=1`) are legitimate **only when
  the user explicitly directs their use** — never on your own judgment.
- If a hook blocks you: **surface the hook name and its message, and STOP.**

**4. Do not declare done. Verify done.** "Done" is the *output* of the pre-close
sweep, not an announcement. See the close-out checklist below.

**5. Corrupted input is a blocked gate (charter C-9).** Damaged, truncated, or
fingerprint-mismatched input is a blocked gate — surface it as your **first
output** and **STOP**; never silently reconstruct, however confident the
reconstruction feels. A `blocked` result from
`scripts/verify_doc_template.py --event consumed` on a handoff you're
consuming is exactly this case — three of the four confirmed silent
handoff-corruption events this rule exists for were an agent reconstructing
damaged text instead of saying so (see
`docs/dev/handoff-integrity-design.md` §2).

**6. Enumerate consumers before changing a contract (charter C-10).** Before
implementing any change to a **schema, a shared contract, or a widely-consumed
helper**, enumerate its consumers **grep-complete** — the whole tree, and every
name the thing goes by (symbol, string form, re-export, raw-SQL column, template
selector) — and **decide-and-document each site before the first edit.**
- **The ordering is the mechanism.** An enumeration written afterwards is a
  description of what you did. Written first, it is the thing that tells you the
  change is bigger than you thought.
- **A site you skip deliberately gets a written reason** under `## Deferred`. The
  same site skipped silently is a defect the next person finds.
- **Treat any hand-maintained consumer list as stale until you re-derive it** — it
  rots in *both* directions, naming sites already fixed and omitting sites that
  are not.
- The `require-consumer-enumeration` hook blocks edits to a gated surface (registry:
  `scripts/enforcement/blast_radius.py`) until
  `docs/dev/blast-radius/<branch-slug>.md` has a `## Consumers` section naming that
  surface. There is no escape hatch. That dossier's directory and `tests/**` stay
  writable, so the way through is always open: **write down who consumes it.**

---

## Hard constraints (copy verbatim — do not shorten)
<!-- verbatim -->

- Branch before any code edit (`require-feature-branch` hook enforces this)
- Quality gate before every commit: `ruff check .` + `mypy .` + `pytest`
- Every new Flask route: `_safe_username()` + `_within()` + `secure_filename()`
  — `route-security-lint` hook enforces this on `app.py` edits
- No LLM calls in `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, or `pdf_render.py`
- `PROMPT_VERSION` must bump in the same commit as any prompt change
- New dependency = `pyproject.toml` entry + `CHANGELOG.md` entry
- If a hook blocks you: surface the hook name + error, do not bypass,
  wait for authorization
- Do not merge to `main` without explicit user confirmation
- One branch per session — close, merge, hand off before starting the next
- Capture-before-merge: land ALL of this branch's docs / memory / CHANGELOG /
  RELEASE_ARC-CHECKLIST / tracked-deferred / flaky-test captures **before** the merge.
  Never merge then open a follow-up branch for a one-file doc/memory edit — it
  re-triggers the `--no-ff` `.approved` marker-wipe ceremony. If a small item surfaces
  after you'd otherwise merge, the sweep isn't finished: fold it in and re-gate.

---

## Branch close-out checklist (do in this order before closing the window)
<!-- verbatim -->

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified; **this session's
   own `consumed`-event provenance-ledger file** (`docs/dev/ledger/<session>.jsonl`,
   written on `main` at session start when the incoming handoff pointer was
   consumed) **committed on this branch** — folded into an early commit, never
   left untracked and never given its own dedicated branch/PR (see
   `docs/dev/prov/SPEC.md` §5 step 3); **wiki-relevance check** — if this branch's
   own diff touches any path `scripts/wiki_relevance.py` (`is_wiki_relevant()`)
   classifies as wiki-relevant, run a scoped `/wiki-self-update` against just this
   branch's own diff and commit the wiki edit now, before opening the PR (same
   "committed before merge" discipline as memory/CHANGELOG, never a follow-up PR);
   if the touched file needed no page edit, say so explicitly rather than silently
   skipping the check; **any dev server or
   long-lived background process started this session terminated** before closing the
   window (check with `tasklist`/equivalent — an agent's own orphaned processes are
   exactly the failure mode carry-forward ledger item 20 documents). "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Write the next-agent handoff at `docs/dev/handoffs/<branch-slug>.md` from
   this template (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), stamped per
   `docs/dev/prov/SPEC.md` §1, then validate it:
   `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>`. A
   `failed` result is authoring corruption in the handoff itself — fix the
   file, don't silence the check. **Do this ON THIS BRANCH, BEFORE the
   merge** — this is exactly what the Capture-before-merge hard constraint
   above already requires (the handoff is one of this branch's own docs),
   and `require-feature-branch` blocks writing it on `main` once this
   branch is gone, so there is no compliant way to do this step after
   merging.
3. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean); the handoff file from step 2
   must be committed by this point too (its own commit or folded into this
   one — either way, both must exist before step 4)
4. **Land it through the PR channel — a local `git merge` to `main` is NEVER
   the flow.** `main` carries branch protection requiring a pull request plus
   six passing status checks (`strict: true`), so a local merge is rejected
   outright for a non-admin and, for an admin, silently bypasses those six
   checks. Squash and rebase merges are both disabled on the repo, leaving
   **merge commit** as the only method — deliberately: a squash rewrites SHAs
   and orphans the local commits it replaces (it already produced one zombie
   commit, `9f3c800`, before this was understood). Ask the user to confirm,
   then: `git push -u origin <branch>` → open the PR (`gh pr create`, or hand
   the user the URL) → **wait for the required checks with
   `python -m scripts.ci_wait <n>`** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **`scripts/ci_wait.py` is the single definition of "the PR is green" — never
   hand-roll a watcher, a poll loop, or a `gh pr checks … | jq` one-liner.** It
   exits **0** only when every required check passed *and* no test needed a
   retry; **3 = green-after-retries** (charter C-7 rule 3 — stop and look, do
   not merge on it reflexively), **1** a failing required check plus its log
   tail, **8** the deadline expiring, **2** a wrapper error. Two hand-rolled
   30-minute watches once ran to completion emitting *nothing* while a required
   check was already red — that silence is the failure this replaces.
   **Pushing is outward-facing on a public repo:** state what will become
   public — including any commits already on your local `main` that the remote
   does not have, since they ride along — and get explicit confirmation before
   the first push.
5. Prune the merged branch(es) with the user's OK — **but regenerate the
   pointer FIRST**, because it must cite `main`, and pruning a branch a
   pointer still names leaves the next session with an unresolvable
   reference (a correct C-9 halt, but a wasted first move). After the
   `pull --ff-only` in step 4: generate the one-line pointer with
   `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`). Then prune
   (`git branch -d <branch>`; the remote copy is auto-deleted on merge).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
