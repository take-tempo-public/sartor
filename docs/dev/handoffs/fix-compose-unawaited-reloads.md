<!-- provenance: schema=1 session=e8c355d9-e540-4705-b860-77c838442287 branch=fix/compose-unawaited-reloads commit=8681aa3 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-18 -->

# fix/compose-unawaited-reloads handoff — 2026-07-18

**Branch to create:** `<!-- pick per whatever the owner wants next -->` (branch off `main`)
**Base branch:** `main`

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

**Stream:** `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" numbered
sequence, step 3.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this step.

- ~~`docs/v110-plan-reconciliation`~~ ✓ — step 1
- ~~`fix/plan-approval-hook-scope`~~ ✓ — step 2 — scoped `check-plan-approved`'s marker per-project
- **`fix/compose-unawaited-reloads`** ← this branch — step 3, DONE
- `refactor/css-cascade-collapse` (PX-51) ← still the actual next numbered-sequence
  step — do not start it on this branch
- The overdue reduction sprint (ledger now at **15 open**, further over the
  ~8–10 ceiling than the last handoff — see below) is still a live candidate
  for "what's next," per two prior handoffs' own recommendation, now stronger

Do not treat this handoff as authorizing `refactor/css-cascade-collapse` or
the reduction sprint by default — the owner picks the next branch.

---

## What just landed on `main`

**Not yet merged as of this handoff** — `fix/compose-unawaited-reloads` is
still open, branched off `main` at `8681aa3` (the tip of
`fix/handoff-pointer-verification`'s own merge).

**The defect:** `fix/ci-first-linux-run` (`be48fec`, 2026-07-12) awaited
`loadComposition()` at the 5 auto-arrival-cascade call sites so the settle
gate (`data-compose-bg-pending`/`data-compose-ready`) can't read terminal
mid-repaint. The **user-action-triggered** call sites were deliberately left
un-awaited (out of that branch's scope) and tracked as a Carry-forward ledger
row — separately investigated and exonerated as the cause of the one known
chronic flake (`compose-summary-draft-settle-hole`), so this was a latent
consistency defect, not an active symptom.

**The fix:** re-derived the live call-site map directly from `static/app.js`
rather than trusting the ledger's own prose (it had gone stale — named an
already-fixed "add-title" site, omitted two real sites). Added `await` at the
9 actually-open call sites across 6 already-`async` functions
(`_acceptRefinementProposal` ×4, `_togglePositioningPin`, `_fireSuggestSkills`,
`_reviewPendingSkill`, `_decideGapFill`, `_addComposeRoleIntro`) — mechanical,
no signature changes. 3 sites excluded as a materially larger, differently-shaped
change (non-`async` intermediate call frames, mixed direct-click/chained-async/
browser-Back-Forward triggers) — filed as its own carry-forward row.

**Evidence, per charter C-7:** `docs/dev/diagnosis/compose-unawaited-reloads.md`.
Worth reading in full for the methodology, not just the result — the first
falsification attempt (checking DOM row-absence) turned out to be a **broken
instrument**: `loadComposition()` synchronously wipes `#composeList` to a
loading placeholder before its first internal `await`, so row-absence is true
in both the buggy and fixed code and can't distinguish them. Corrected by
checking the actual settle-gate contract (`Compose.SETTLED` selector —
`data-compose-ready` presence at the exact instant `data-compose-bg-pending`
clears, captured inside one `MutationObserver` tick to remove all
Python/Playwright round-trip timing risk). That test
(`tests/ux/regression/test_20260718_compose_unawaited_reloads.py`) failed
deterministically on unmodified HEAD and passed after the fix, no retry.

**Also fixed (unplanned, found while gating):** a pre-existing broken
cross-document link on `main`, unrelated to this branch's diff —
`docs/dev/handoffs/fix-handoff-pointer-verification.md:303` cited
`diagnosis/handoff-pointer-verification.md` with a relative path that only
resolves correctly from `docs/dev/AGENT_HANDOFF_TEMPLATE.md`'s own location,
not from `docs/dev/handoffs/`. It was blocking `test_no_broken_cross_document_links_or_cites`
(a mandatory, no-hatch gate step), so a one-line docs-only correction landed
here rather than being deferred. **The template itself was deliberately NOT
touched** — the real fix (a citation form that survives being copied to any
directory depth) is a design decision on a governance-adjacent doc, filed as
its own new carry-forward row rather than made solo mid-branch.

`python -m scripts.gate` equivalent run in batches (the still-open "gate
unrunnable in one shot" ledger item, unchanged by this branch — the full
non-ux `pytest -m "not ux"` run alone took 605s and still had to move to a
background task): ruff check ✓, ruff format --check ✓ (no reformats needed),
mypy ✓ (328 files incl. the new test, 0 issues), pytest — 2027 passed + 1
skipped (non-`ux`, after the doc-link fix above), `ux` tier split
regression/a11y/flows: 110 + 4 + 7 passed, all green including the
already-characterized `test_restore_scroll_y_loses_to_post_restore_growth`
scroll-flake (clean this run — see [[project-ux-scroll-flake-chip0]]).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger
(`#### Open`); this is the required one-line-each mirror. **15 open, further over the ~8–10
ceiling than the prior handoff (14)** — this branch resolved 1 item and added 2 new ones (both
found while doing this branch's own work, not scope creep: the 3 excluded call sites, and the
handoff-template link defect found while gating).

1. `--reruns 2` on the `ux` CI tier is a masking policy — fix landed; the reruns-policy
   question itself is deliberately left open until a real post-fix CI sample exists.
2. The quality gate is unrunnable by an agent in one shot (~13 min vs. a 10-command shell cap)
   — a governance hole. (Hit again this session — the non-`ux` batch alone took 605s and had
   to move to a background task — direct, repeated confirmation this item is still real.)
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only 30-second
   Settings toggle, not automatable.
4. `test_corpus_reload_preserves_scroll_position` (and sibling scroll-restore tests) — a real
   ~10–20% flake, measured not fixed. Ran clean this session (part of the `ux` tier's full
   green run).
5. `chore/scrub-local-eval-paths` parked branch — 2 commits, unmerged, gate re-verification
   incomplete (not failed).
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` (~107 files, agent-regenerated) —
   user-facing surface already swept; this remainder deliberately deferred.
7. **NEW.** 3 `loadComposition()` sites excluded from this branch's fix
   (`static/app.js:6549,6606,6932` — `_resumeIntoStep6`, `_resumeIntoPreGenerateStep`,
   `wizardGoTo`) need their own pass — non-`async` intermediate call frames plus a
   browser-Back/Forward trigger make this a design decision, not a mechanical `await` add.
8. **NEW.** `AGENT_HANDOFF_TEMPLATE.md`'s own "Branch close-out checklist" verbatim block has a
   relative link that breaks every time it's copied into an actual `docs/dev/handoffs/<slug>.md`
   file (one directory deeper than the template's own location). Fixed the one instance this
   branch's gate run tripped over; the template itself needs a citation-format decision before
   every future handoff stops reproducing the same broken link.
9. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; left open only for the still-blocked
   `[HUMAN]` Trusted Publisher prerequisite.
10. In-app rendered citation viewer — deliberately deferred; build only if real friction shows
    up (GitHub links suffice for now).
11. Grounding/hallucination metric calibrated layers (L1/L2) — no labeled real data yet;
    scheduled as v1.0.7 Sprint PV-2.
12. Agent-coding-practices kit-adoption staged commitments — cross-cutting deferrals
    (mypy-strict ratchet exit, gate-hardness ratchet-then-block, etc.) kept in one tracked home.
13. 2026-07 efficiency review PX-37..PX-56 aggregate — drains via per-PX-coordinated individual
    branches per `RELEASE_ARC.md` "v1.1.0 close-out — reconciliation."
14. UX round-2 remediation — Wave A (six decision-free findings) landed on
    `fix/round2-quick-wins`; the design-heavy remainder (state-communication unification, etc.)
    is still open.
15. `docs/governance/enforcement.md` (and several memory files) cite "charter W-1" (the
    parallel-session working model) as an existing clause — it does not exist in
    `docs/governance/charter.md` (only C-0…C-9, D-1…D-7). Needs an owner-directed amendment
    ceremony to write the actual clause and reconcile the dangling citations.

**Reduction sprint is now more overdue than at the last handoff, not less** — two consecutive
branches have each (correctly, per their own scope) left the ledger net-flat-or-growing rather
than draining it, because each found and filed its own genuinely-new items rather than closing
old ones. Strongly consider the reduction sprint as the very next branch, ahead of
`refactor/css-cascade-collapse`.

---

## What this branch should build

This handoff exists solely to record `fix/compose-unawaited-reloads` and hand off cleanly —
it does not mandate a deliverable itself. Per `RELEASE_ARC.md`'s ordered sequence, the next
candidate is **step 4, `refactor/css-cascade-collapse`** (PX-51), unless the owner prefers to
run the overdue reduction sprint first (see the note above) or names something else entirely.

Scope is bounded to whatever the owner confirms next — do not treat this handoff as
authorizing any specific branch by default.

---

## First move

Create branch `<!-- branch-name -->` off `main`, write a plan at `~/.claude/plans/<slug>.md`,
and show it to the user before touching any code. **Do not code first.**

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

> **Deliberate, user-approved deviation from byte-for-byte (2026-07-18):** step 5's
> citation link below reads `../diagnosis/handoff-pointer-verification.md`, not
> `diagnosis/handoff-pointer-verification.md` as `AGENT_HANDOFF_TEMPLATE.md` itself
> has it. The template's own copy is only correct relative to the template's OWN
> location (`docs/dev/`); reproduced byte-for-byte into `docs/dev/handoffs/<slug>.md`
> (one directory deeper) it 404s — confirmed by `test_no_broken_cross_document_links_or_cites`
> against the previous handoff that copied it unfixed. Asked the user how to handle this
> specific instance; they chose "fix the link here, accept the verbatim mismatch" over
> "keep it broken" or "fix the template now." Consequence, expected and accepted:
> `scripts/verify_doc_template.py --event generated` reports `FAILED — verbatim section
> does not match template` for this section (sha256 `a798b64e7b24` vs. template's
> `a25f30362820`) — that mismatch is this one intentional character, not corruption. The
> template itself is unchanged; see the new Carry-forward ledger row for the real fix.

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified. "Done" is the output
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
4. Ask user to confirm merge to `main`; execute merge after confirmation
5. Prune merged branch(es) with the user's OK. Generate the one-line
   pointer with `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   [`diagnosis/handoff-pointer-verification.md`](../diagnosis/handoff-pointer-verification.md)).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
