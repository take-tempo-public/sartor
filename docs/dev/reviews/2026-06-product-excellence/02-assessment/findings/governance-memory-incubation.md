---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Governance, memory & incubation

> Severity anchors to the SIGNED charter; a gap matters only if it blocks a
> charter clause. Written under C-0: mechanisms and effort, no absolutes, no
> marketing register. Evidence pinned at `c6e0437` (hooks live under
> `.claude-plugin/hooks/` at the pin — the v1.0 plugin migration completed;
> the domain guide's `.claude/settings.json:15-95` registration cite is
> accurate, 96-line file).

## Domain verdict

The *enforced* governance layer is genuinely strong and honestly built: seven
blocker hooks fire PreToolUse with `exit 2`, three witness/state-manager hooks
never block, and the witness/blocker split is clean and self-aware
(wiki-freshness-reminder is the named precedent for a "flag, don't approve"
drift report). The seven-functions self-model, the read-only subagent pattern,
and the governance-extraction design doc are all register-grade strengths worth
affirming. The gaps that bear on the charter are not in the *idea* of the
governance — it is excellent — but in two places where the **written/enforced
governance diverges from the practiced one**: (1) the two live W-1 multi-agent
collisions are still structural in code with no isolation rule written into
governance; and (2) one deterministic enforcer that docs treat as machine-held
(`block-merge-to-main`) does **not** catch the dominant merge direction, making
a "machine-enforced" governance claim convention-only for the common path — the
exact C-0 failure mode this domain exists to catch. Incubation has one
observable readiness condition (`recall/`) and trigger-language for the rest.

---

## Register findings

### F-gov-01 — `block-merge-to-main` does not catch the dominant merge direction (rule treated as machine-enforced is convention-only for the common path)

- **id:** F-gov-01
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-0, E-1, T-C, S-1
- **question-refs:** QB-gov-06
- **coordinate:** v1.0.7 (governance extraction — where this rule graduates to `docs/governance/`)

**Finding.** `block-merge-to-main.sh` (the deterministic encoding of the
"always confirm before merge to main" rule, charter-adjacent and in
`feedback_git_merge_confirm` memory) only blocks command strings where the
literal token `main`/`master` appears on the line: `git merge ... (main|master)`
or `git push ... origin (main|master)` (`block-merge-to-main.sh:13-18`@c6e0437).
The standard documented merge flow — checkout main, then `git merge <feature>
--no-ff` (AGENTS.md close-out step 3; RELEASE_ARC merge ceremony) — carries only
the *feature* branch name on the merge line and is **not** matched. Verified
statically: of `git merge feat/x --no-ff`, `git checkout main; git merge feat/x`,
and `git merge main --no-ff`, only the last (the rarer "merge main INTO a
branch" direction) is blocked. So the rule the system-model files under
**Regulation** ("enforced by machines rather than by vigilance",
system-model.md:97-101) is, for the dominant direction, vigilance-only. Under
C-0 this is the cardinal seam: a categorical "we always confirm before merge"
posture is only honest where a deterministic test enforces it by construction.
Two safe fixes (witness-class, no behavior risk): detect *current branch ==
main/master at merge time* rather than parsing the command string, or match
`git merge` while HEAD is main regardless of the named branch.

**Evidence:** `.claude-plugin/hooks/block-merge-to-main.sh:13-18,26-31`@c6e0437;
static regex test (this session) — `git merge feat/x --no-ff` PASSES the guard.

---

### F-gov-02 — The two live W-1 collisions are still structural in code; no isolation rule is written into governance

- **id:** F-gov-02
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** W-1, R2-11
- **question-refs:** QB-gov-01
- **coordinate:** v1.0.7 (governance extraction)

**Finding.** Both R2-11 collisions persist at the pin. (a) **Global plan
marker:** the approval marker and *all* plan `.md` files live at a single global
path `$HOME/.claude/plans/` with no per-session/per-worktree scope
(`check-plan-approved.sh:6-7`, `mark-plan-approved.sh:5`,
`cleanup-plan-on-merge.sh:20-28`@c6e0437). `cleanup-plan-on-merge.sh:23-24`
deletes *every* `*.md` plan file and the marker on any successful merge in any
session; `check-plan-approved.sh:37-38` invalidates an existing approval the
moment a *second* session writes a newer plan file. A concurrent session is thus
exposed to having its approval wiped or its plan files deleted by an unrelated
session's merge — the precise hazard R2-11 named. (b) **Branch detection:** the
`require-feature-branch.sh:36` `git rev-parse --abbrev-ref HEAD` check is, on
verification, correctly *worktree-local* (returns the worktree's own branch when
run from inside it — tested in a sandbox), so the "worktree-blind" framing
overstates (b); the residual is that no isolation rule (worktree-per-session,
global-state ownership, branch ownership) is **written as governance** anywhere.
The collision that is genuinely structural is (a), the global marker. Honest
mitigant worth recording: `cleanup-plan-on-merge.sh:11-16` only fires on Bash
`git merge --no-ff` with git's "Merge made by" string — PowerShell merges (the
owner's actual workflow per `project-plan-approved-marker` memory) don't trigger
the auto-wipe, which lowers the *frequency* of the (a) collision but does not
close it.

**Evidence:** `check-plan-approved.sh:6-7,37-38`;
`cleanup-plan-on-merge.sh:20-28`; `require-feature-branch.sh:36`@c6e0437;
sandbox test (this session) confirming `rev-parse --abbrev-ref HEAD` is
worktree-local and the global marker path is single-instance.

---

### F-gov-03 — Serial-session framing ("one branch per agent session") still in force across RELEASE_ARC + AGENTS.md + CONTRIBUTING; the real parallel model is uncodified

- **id:** F-gov-03
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** W-1
- **question-refs:** QB-gov-02
- **coordinate:** v1.0.7 (governance extraction)

**Finding.** R2-11 directed retiring the stale serial framing and codifying
multi-altitude parallelism with isolation rules. At the pin the serial framing
is still authoritative in three places: RELEASE_ARC.md:863 "One branch per agent
session — close, merge, hand off before starting the next" (listed under "Hard
constraints, all phases"); RELEASE_ARC.md:390 "strictly sequential, one branch
per session"; and the AGENTS.md close-out checklist is written wholly in the
single-closing-agent voice. CONTRIBUTING.md:219 still titles its multi-agent
section **"Future: multi-agent identity"** — but note this section is narrowly
about *identity/auth* (GITHUB_TOKEN → GitHub App), not the
serial-vs-parallel *isolation* question; the QB-gov-02 cite of CONTRIBUTING:219
lands on a real "Future:" but a different topic than the isolation one. No doc
codifies worktree-per-session / global-state-ownership / branch-ownership as
written governance. This review is itself a parallel worktree instance, so the
docs contradict the practice daily (domain-guide S16).

**Evidence:** `docs/dev/RELEASE_ARC.md:390,863`@c6e0437;
`CONTRIBUTING.md:219-221`@c6e0437; AGENTS.md close-out checklist (serial voice).

---

### F-gov-04 — Seven enforced blocker hooks are real and honestly separated from witness/tribal rules (KEEP)

- **id:** F-gov-04
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** C-0, E-1, T-C
- **question-refs:** QB-gov-06
- **coordinate:**

**Finding.** Verified: seven PreToolUse blocker hooks each use `exit 2`
(check-plan-approved ×2, require-feature-branch, block-secrets ×3,
validate-context ×2, route-security-lint, block-merge-to-main, ruff-changed) and
are registered in `.claude/settings.json` (96-line file). The three
witness/state-manager hooks (wiki-freshness-reminder, mark-plan-approved,
cleanup-plan-on-merge) contain zero `exit 2` — the witness/blocker split is
clean. The four tribal-only rules (PROMPT_VERSION bump-in-same-commit, new-dep →
pyproject+CHANGELOG, close-out pre-sweep, handoff reproduction) are confirmed to
have **no** hook — prose-only in AGENTS.md/RELEASE_ARC. This honest separation —
machine-categorical where a test enforces, effort-language everywhere else — is
exactly C-0 applied to *process* and should be affirmed so it is not churned in
the v1.0.7 extraction. (The unenforced tribal rules are the WATCH below, not a
defect — the charter's D-4/P-3 posture keeps human-promise governance
best-effort.)

**Evidence:** `exit 2` counts per hook (this session); `.claude/settings.json`
hooks block@c6e0437; AGENTS.md:41,96 (PROMPT_VERSION prose-only).

---

### F-gov-05 — Governance-extraction design doc is register-grade: extract-don't-restate, one canonical home, `@import` named as the load-bearing safety condition (KEEP/BOOST)

- **id:** F-gov-05
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** W-2, C-0
- **question-refs:** QB-gov-05
- **coordinate:** v1.0.7 (governance extraction — this is the charter's own graduation vehicle)

**Finding.** `docs/wiki/pages/governance-extraction.md`@c6e0437 settles exactly
what QB-gov-05 asks: prescriptive/Governance content is **lifted into one
canonical home and stated once** (overriding an earlier register-in-place lean —
DRY applied to governance, one rule one place), each mixed doc keeps its
descriptive content plus a pointer, and the **critical constraint** is named
explicitly: AGENTS.md/CLAUDE.md are harness-auto-loaded, so extraction MUST
preserve agent rule-access via `@import` or canonical pointer "or every future
agent loses its guardrails" — the load-bearing safety condition. The doc also
honors the wiki grounding rule it lives under (references not restatement,
`[synthesis]` tags, `[[backlinks]]`). Three implementation sub-decisions remain
open (home name/location, per-doc boundaries, AGENTS.md shape), tracked against
RELEASE_ARC §4.5 and resolved at the v1.0.7 design session. Design complete,
build deferred to a gated branch — the design-precedes-code discipline the
product map flags as a BOOST. No `docs/governance/charter.md` home exists at the
pin (expected — it is the charter's v1.0.7 graduation target).

**Evidence:** `docs/wiki/pages/governance-extraction.md` (full)@c6e0437;
`docs/dev/RELEASE_ARC.md` v1.0.7 tag criteria (governance extraction landed,
`@import` preserved).

---

### F-gov-06 — Witness-class freshness reminder + honest sentinel are the working precedent for the amendment-ceremony "witness not approver" (KEEP)

- **id:** F-gov-06
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** C-0 (amendment ceremony), E-1, W-2
- **question-refs:** QB-gov-07
- **coordinate:**

**Finding.** The amendment ceremony exists today only in the charter (charter
L338-344), which lives in `review/` and has not graduated to
`docs/governance/charter.md` (expected; it graduates in v1.0.7). No compliance
agent exists in the repo at the pin — the charter names it as a future
"witness, not approver." The *precedent* it will be built on is real and
well-formed: `wiki-freshness-reminder.sh` always exits 0, emits a `systemMessage`
nudge, and is honestly silent while `docs/wiki/.last_ingest_sha` is the sentinel
("no code ingest yet" — confirmed, no false code-pass claim); `/wiki-lint` is
the doc-vs-code drift report. This is a genuine "flag, don't approve" mechanism
ready to be pointed at amendment-ceremony violations once governance is
extracted. Affirm it so the v1.0.7 build inherits the pattern rather than
reinventing it.

**Evidence:** `.claude-plugin/hooks/wiki-freshness-reminder.sh:1-16,55`@c6e0437
(always exit 0, sentinel-silent); `docs/wiki/.last_ingest_sha`@c6e0437
(sentinel); charter L338-344 (amendment ceremony, witness-not-approver).

---

### F-gov-07 — `check-plan-approved` prints a hand-create-the-marker hint that contradicts the "never hand-create" governance rule (DEBUFF)

- **id:** F-gov-07
- **disposition:** DEBUFF
- **leverage:** P2
- **charter-trace:** C-0 (no-escape-hatch / hook discipline), W-2
- **question-refs:** QB-gov-06
- **coordinate:** v1.0.7 (governance extraction)

**Finding.** `check-plan-approved.sh:31-33`@c6e0437 prints, on block, the hint
"for simple tasks run: `New-Item -Force -ItemType File ...\.claude\plans\.approved`"
— i.e. the enforcer itself instructs the agent to **hand-create the very marker
it checks**. This directly contradicts the project's own hard rule
(`project-plan-approved-marker` memory: "ONLY ExitPlanMode creates it — never
hand-create it"; `feedback_hook_discipline`: "no hand-creating the checked file";
AGENTS.md "you NEVER hand-create the file a hook checks for to unblock
yourself"). It is exactly the escape-hatch-on-initiative pattern the domain-guide
DEBUFF rubric and the charter's "no escape hatch" paragraph exist to retire. The
hint legitimizes, in the tooltip, the bypass that the constitution forbids. Fix
is a one-line copy change: route the user to ExitPlanMode only, or qualify the
hint as "owner-directed override only," consistent with how
`require-feature-branch`/`block-merge-to-main` document their hatches as explicit
opt-ins rather than casual suggestions.

**Evidence:** `.claude-plugin/hooks/check-plan-approved.sh:31-33`@c6e0437 (the
`New-Item -Force` hint); contradicts AGENTS.md no-hand-create rule +
`project-plan-approved-marker`/`feedback_hook_discipline` memory.

---

### F-gov-08 — No W-4 maturity metric for four of five incubants; only `recall/` has an observable extraction-readiness condition (FIX/WATCH)

- **id:** F-gov-08
- **disposition:** FIX
- **leverage:** P2
- **charter-trace:** W-4
- **question-refs:** QB-gov-03
- **coordinate:**

**Finding.** W-4 names the extraction trigger set (maturity / second-project need
/ attention economics) but leaves the *maturity metric* "TBD — review to
propose." At the pin exactly one of the five incubants has an observable
readiness signal: `recall/` carries an explicit **extraction-readiness
condition** — "lifting `recall/` into a standalone package should be *packaging
only* — *if* the boundary [no import of app.py/analyzer.py/DB models] stays
clean" (`docs/dev/memory-architecture.md:216-219`@c6e0437), a structural,
checkable gate (candidate for its own boundary-lint). The other four (governance
rulebook + compliance agent; LLM-wiki self-documenting loop; doc-grounded
assistant; grounding-metric three-tier pattern) have only trigger-language, no
per-system readiness signal. This is a real W-4 gap, but it is **not v1.1.0
blocking** — extraction is a post-v2 horizon (P-6), and the absence is honestly
acknowledged in the charter. Proposing one observable readiness signal per
incubant (mirroring the `recall/` boundary-clean condition) is the BOOST the
rubric describes.

**Evidence:** `docs/dev/memory-architecture.md:216-219`@c6e0437 (recall/
extraction-readiness); charter W-4 ("maturity metric TBD — review to propose");
no readiness signal found for the other four incubants (grep, this session).

---

### F-gov-09 — Read-only subagents (prompt-archaeologist / tune-drafter / git-flow ask-first) are the compliance-agent precedent (KEEP)

- **id:** F-gov-09
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** W-2, C-4
- **question-refs:** QB-gov-04 (precedent leg)
- **coordinate:**

**Finding.** `prompt-archaeologist.md`@c6e0437 carries `tools: [Read, Grep,
Glob]` and states "Does NOT apply the diff — review and apply manually" /
"Do NOT edit the file — output the diff ... for the human to review"; tune-drafter
follows the same diagnose-don't-mutate contract; git-flow asks before every
visible act. A compliance agent that *witnesses* without merging therefore has
three in-repo precedents, and the human-gate-on-promote discipline (C-4) is
already practiced. This is the W-2 operator-stack triad's governance leg in
embryo — affirm it so the v1.0.7 compliance agent inherits the read-only
contract rather than being granted write authority.

**Evidence:** `.claude-plugin/agents/prompt-archaeologist.md:1-9,30-40`@c6e0437
(tools Read/Grep/Glob; "Does NOT apply the diff"); agents dir listing@c6e0437.

---

### F-gov-10 — Operator-stack triad: memory→context leg is richly designed, but governance→posture (assistant's build-time governance interface) is not yet captured in any design artifact (WATCH)

- **id:** F-gov-10
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** W-2, A-2, A-4, R2-10
- **question-refs:** QB-gov-04
- **coordinate:** v1.0.7 (doc-grounded assistant design)

**Finding.** R2-10/W-2 direct that the v1.0.7 assistant gets its **governance
interface at build time** — "how we tune the assistant and manage what it is,
how it acts, and what it can/can't do," read from the extracted constitution.
At the pin the **memory→context** leg of the triad is thoroughly designed
(`docs/dev/memory-architecture.md` — the AVATAR/ASSEMBLE/RETRIEVE/SOURCES stack
with a POLICY plane scoped to *audience + progressive disclosure*, and PROVENANCE
plane), and the assistant is well-specified as retrieving over the wiki with
citations (PRODUCT_SHAPE §11.4; RELEASE_ARC v1.0.7 tag criteria). But the
**governance→posture** leg — the assistant's persona/capabilities/guardrails read
*from the extracted constitution* at build time — is not yet captured in a design
artifact: the POLICY plane is audience-scoping, not the constitutional governance
interface R2-10 named, and governance-extraction.md describes the canonical home
without wiring the assistant to it. This is design-stage (v1.0.7 is unbuilt), so
WATCH not FIX — but it is the one R2-10 directive with no design home yet, worth
flagging so the assistant design session closes it rather than shipping an
assistant that retrieves memory but reads no governance.

**Evidence:** `docs/dev/memory-architecture.md:40-70` (memory/avatar stack,
POLICY plane = audience scope)@c6e0437; `docs/PRODUCT_SHAPE.md:725-730`
(assistant = wiki retrieval + citations)@c6e0437; no governance→assistant
interface artifact found (grep, this session); charter W-2/R2-10.

---

## Appendix (beyond the register cap)

### F-gov-A1 — Agent-station (W-3 maintenance canary) is untracked in any repo doc, with no fallback posture (WATCH)

- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** W-3, D-4 ·
  **question-refs:** QB-gov-08

The post-public maintenance story (W-3) routes through *agent-station*, an
unbuilt product whose canary is v1.1.0's GitHub integration. Grep finds **zero**
mentions of "agent-station" or "canary" in any repo doc at the pin
(`docs/**`); the dependency lives only in the charter (W-3) and interview record
(R2-8). No fallback posture is documented for "what if agent-station slips."
This is correctly out of v1.1.0 scope (post-public lane, couple-hours/week
owner budget) and the charter's D-4 soft-commitments posture absorbs the risk —
hence WATCH/P3 — but the dependency is invisible to anyone reading only the repo.
Evidence: grep for `agent-station|canary` over `docs/**`@c6e0437 returns empty;
charter W-3; product-map §3 post-public lanes (which carries it).

### F-gov-A2 — Planning-doc sprawl as load-bearing memory; one truth-source flagged STALE by the memory index itself (WATCH)

- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** W-2, C-0 ·
  **question-refs:** (relates QB-gov-03 sequencing source)

Sequencing truth lives across RELEASE_ARC + RELEASE_CHECKLIST + PRODUCT_SHAPE
§10/§11 + nursery + memory notes with cross-refs and "moved 2026-06-12"
annotations; the agent memory index itself flags `roadmap-v1.0.2-v1.1.0.md` as
STALE ("trust RELEASE_ARC.md, not this memory"). This is the product-map
DEBUFF-7 candidate; in my domain it bears on W-2 (governance as the
single-source-of-truth discipline) — the governance-extraction "one rule, one
home" principle (F-gov-05) is the eventual structural fix for the *rule* sprawl,
but the *sequencing* sprawl is outside that extraction's scope and remains
triangulation-dependent. Not v1.1.0-blocking. Evidence: memory index STALE
pointer; product-map DEBUFF-7; RELEASE_ARC "Reference documents" table@c6e0437.
