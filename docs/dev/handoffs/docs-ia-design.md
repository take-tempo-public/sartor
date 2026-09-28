<!-- provenance: schema=1 session=84995956-f9fb-4656-96ce-262b66cfbf5c branch=feat/docs-ia-design commit=d979884 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-27 -->

# Agent handoff — Epic D sprint D1 close (`feat/docs-ia-design`)

**Branch to create:** `feat/docs-split` (branch off `epic/d-docs-ia`)
**Base branch:** `epic/d-docs-ia`

> **Model for the next session: `/model sonnet`** (RELEASE_ARC Final March prescription:
> Opus for D1/D3, Sonnet for D2/D4).
>
> **Epic cadence (owner decision, 2026-09-27):** Epic D runs on the integration branch
> `epic/d-docs-ia` (created off `main` at `f3dd472`). Each sprint branch merges into it as
> that session's final act, and the whole epic lands as **one PR after D4**. The epic branch
> is **local-only until the owner authorizes a push**.

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

**Stream:** Epic D — `epic/d-docs-ia` (board item 39), documentation + information
architecture.
**Sequencing rule:** strictly sequential — one branch at a time; D2 depends on D1's design.
**Blocked until this stream tags:** Epic E (`chore/release-v1.1.0`) — Epic D lands as one PR,
not a tag.

- ~~Epic C~~ ✓ — merged to `main` as PR #148 (`f3dd472`).
- ~~**`feat/docs-ia-design` (D1)**~~ ✓ ← this branch: audits + research + design doc.
- **`feat/docs-split` (D2)** ← next: the mechanical split, per the design's §2 mapping and
  §6 coupling checklist.
- `feat/user-docs` + `feat/dev-docs` (D3), `feat/docs-assets-enforcement` (D4) ← do not
  start these on D2.

**Do not start on D2:** any content rewrite (D3 — including the three contradictions in the
design's Open-decisions section, unless the owner pulls them forward), and any lint beyond
what the owner decides under O-4 (D4).

**D2 is gated on two owner decisions.** Resolve **O-1** (wordmark in UI copy) and **O-4**
(pull the publication registry + audience token into D2) with the owner **before** the first
move — both change D2's commit contents (`docs/dev/docs-ia-design.md` §"Open decisions for the
owner"). O-2, O-3 and O-5 also bear on D2/D3; surface all five together at kickoff.

---

## What just landed on `epic/d-docs-ia`

Commits on `feat/docs-ia-design` (merged into `epic/d-docs-ia` as this session's final act,
with the owner's confirmation):
- `88c0011` — consumed the Epic C handoff (ledger row for session `84995956`); item 39
  `blocked` → `open`.
- `d979884` — the D1 deliverables:
  - [`docs/dev/docs-ia-design.md`](../docs-ia-design.md) — the design. Its §2 mapping is D2's
    work order, §3 the link policy (records frozen; `docs/dev/moved-paths.json`), §5 the lint
    design, §6 the D2 coupling checklist.
  - [`docs/dev/reviews/2026-09-docs-ia/`](../reviews/2026-09-docs-ia/10-ux-onboarding.md) —
    UX-onboarding, DX, technical-writer audits + research digest. **The UX audit's headline
    finding is void** (it read stale gitignored `.mdx` build output) — see the correction
    block at its top.
  - `docs/dev/documentation-architecture.md` — header pointer + dated correction of four
    drifted claims.
- The close-out commit — this handoff, the `docs/wiki/log.md` verified-no-edit entry, and
  `scripts/wiki_relevance.py` classifying `docs/dev/docs-ia-design.md` (relevant, like its
  sibling `documentation-architecture.md`) — the first gate run failed on exactly that
  (`tests/test_wiki_relevance_classification.py:91`). C-10 dossier:
  `docs/dev/blast-radius/docs-ia-design.md` (no behaviour change: the path already
  defaulted to relevant).

Gate: `python -m scripts.gate` on the close-out tree — result recorded in the close-out commit
message. Docs only; no production code, no prompt, no dependency changed.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Authoritative home: `docs/dev/work/BOARD.md` (regenerated this session). **Header: "Open 22 /
10 ceiling -- OVER".** The reduction sprint is **overdue** — the owner chose D1 first this
session; the question stands for after D2 or sooner.

`## Open` (top-level, 20):
- **50** — C-7/C-10 hooks don't travel to non-Claude-Code agents.
- **98** — Wiki freshness measures checkpoint-staleness, not page-staleness.
- **99** — install.md documents two never-published distribution paths (D3 touches this doc).
- **105** — Corpus import produces no education entries.
- **106** — Compose bullet-text edits don't reach an already-frozen application.
- **107** — First run offers no account-naming step.
- **111** — `check-plan-approved.sh` ~2 s/edit, 8–21 s/retire on Windows/MSYS.
- **112** — Dashboard Since filter raises TypeError (naive vs offset-aware dates).
- **115** — UX-8 test needs a `getComputedStyle` assertion.
- **116** — "Run this fixture" help bubble never verified to open in a browser.
- **117** — No server-side single-flight lock for paid diagnostics runs.
- **118** — Redaction misses quoted-key header forms and Basic auth.
- **119** — Run lock has no owner; three `acquire()` sites ignore its result.
- **120** — Declined run leaves its button pulsing.
- **121** — `run_detail` reads the whole log per modal open; non-object line → 500.
- **122** — Weak C3 test assertions.
- **123** — `verify-binary-on-path` blocks shell brace groups.
- **124** — Recurrence: agents invoke bare `ruff` and get hook-blocked.

Plus `## Blocked` (4), `## Deferred` (9, incl. **113** — 18 console-UX findings awaiting owner
triage), `## Watching` (45), `## Epics` (6; **39 now `open`**). Full detail: `BOARD.md`.

**New this session — unfiled, capture in your branch (not a standalone post-merge branch):**
- **Merged epics 37 and 38 still read `status = "blocked"`** (`docs/dev/work/items/0037-*.md`,
  `0038-*.md`), with `blocked_on` naming the epic before them. Closing an epic needs a
  `verified_by` artifact (C-11 closure bar) — the owner should say what counts (the merge PR?
  `#128` / `#148`). Left untouched here: not D1's scope.
- **Gitignored docs-site projection reads as authoritative when stale** — an audit agent cited
  a 2026-07-26 local `docs-site/content/docs/*.mdx` as the live site. The D1 design's §5.1
  registry doesn't prevent a stale local copy; a candidate mechanism for D2/D4 is the
  projector clearing and restamping the tree (source commit in each file's frontmatter), so a
  stale copy is visibly stale.
- **Three live contradictions** (design §"Open decisions", last bullet): `CONTRIBUTING.md:57`
  and `agents/git-flow.md:19` instruct a local `git merge --no-ff` (against AGENTS.md step 4);
  CONTRIBUTING calls CI "latent"; docs describe the gate as four steps vs six in
  `scripts/gate.py:72-82`. D3 fixes by default; the `git-flow` one is live-harmful if that
  subagent is dispatched before then.
- **Stray processes predating this session** (seen via `Get-Process` at close-out):
  several `python3.13` processes started 2026-09-18 → 09-25, ~0 MB working set. Not this
  session's; left for the owner.

---

## Recurrences observed this session → guardrail authored

1. **Interrogative-witness pause fired on the main agent after subagent hand-backs** (4×
   this session: each Edit/Write following a hand-back or task notification, with no new
   user prompt). Recognized as a recurrence: the Epic C terminal handoff records the same
   ("re-armed by task notifications / subagent hand-backs"). **No mechanism authored** — the
   witness is fail-open by design (item 87, C-0) and the cost is one re-run per hand-back;
   changing its arming rule is a hook change outside D1's scope. Surfaced to the owner in the
   close-out summary.
2. **A new top-level doc landed without a wiki-relevance classification** — the same
   failure `docs/dev/epic-a-chain-design-corrections.md:262` records. **Mechanism already
   exists and failed closed:** `tests/test_wiki_relevance_classification.py` blocked the
   gate; fixed on this branch. D2 moves many top-level docs — its §6 coupling checklist
   already lists this file.
3. **An agent treated a derived artifact as the source** (the UX auditor citing gitignored,
   months-stale `.mdx` build output as the published site). Recognized as a member of a known
   class — verify against the durable source, not a copy
   (`feedback-verify-against-durable-docs`). **No mechanism authored** — the candidate
   (projector restamps/clears the tree) is D2/D4 implementation work, filed above as an
   unfiled carry-forward. Caught here by the invoker's spot-check, not by a gate. Surfaced to
   the owner.

---

## What this branch should build

D2 — the mechanical split, per `docs/dev/RELEASE_ARC.md` §"Epic D" (D2 bullet) and
`docs/dev/docs-ia-design.md` §2, §3, §6:

1. **Owner kickoff:** settle O-1 and O-4 (and surface O-2, O-3, O-5) before any move.
2. **Entry gate:** `python scripts/wiki_freshness.py`; clear elevated drift with
   `/wiki-self-update` first (RELEASE_ARC §D2).
3. **C-10 dossier first:** `docs/dev/blast-radius/docs-split.md` enumerating every name each
   moved path goes by (design §6 list) — before the first `git mv`.
4. **`scripts/docs_move.py`** — mapping-as-data (design §2.1/§2.2), `git mv`, live-doc link
   rewrite, writes `docs/dev/moved-paths.json`.
5. **`scripts/check_doc_links.py`** — consult the moved-paths map for links originating in
   record paths only (design §3.3).
6. **Same-commit coupling** (design §6): `scripts/wiki_relevance.py`, the projector
   (`scripts/project_docs_to_mdx.py` — path table or, per O-4, the registry), two-tier
   `meta.json`, `docs/user/README.md` + `docs/dev/README.md` stubs.

Scope is bounded to Epic D, D2 in `docs/dev/RELEASE_ARC.md` and the D1 design's §2/§3/§6. Do
not expand beyond what is listed there.

---

## First move

Create branch `feat/docs-split` off `epic/d-docs-ia`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

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
