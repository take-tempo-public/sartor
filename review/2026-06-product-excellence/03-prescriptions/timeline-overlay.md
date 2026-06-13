---
status: review-artifact
evidence_sha: c6e0437
graduation: docs/dev/RELEASE_ARC.md post-public section (owner-integrated)
---

# Post-1.1.0 timeline overlay — callback.

> **PROPOSAL — `docs/dev/RELEASE_ARC.md` remains authoritative until the owner
> integrates this via a normal dev branch.** This is a *delta* on the arc's
> post-public section, not a rewrite. It quotes arc anchors by heading and
> proposes insertions after each. Nothing here is canonical; it graduates only
> when the owner folds it into the arc through the normal flow.

Severity anchor: the signed Product Charter
([`../00-interview/product-charter.md`](../00-interview/product-charter.md)).
Honors **C-0** — categorical claims only where a deterministic test enforces
them; mechanism-and-effort language everywhere LLM behavior or human effort is
in play. Honors the **P-3 / D-4 soft-commitments posture**: every prescription
below prefers a **machine-enforced gate** over a recurring human-labor
obligation. Where a lane names a rhythm, the rhythm is a *machine trigger or an
opportunistic prompt*, never a promised SLA.

**Note on the pin.** Evidence is at `c6e0437`; main has since moved past it
(Sprint 6.4 + 6.6 landed). This overlay is written *at the pin* — Phase 5
reconciles any drift. Findings are cited by F-id; **WEAKENED** findings carry
their revised claim from the verification log, not the original wording.

The four lanes below project onto the arc's existing post-public scaffold. Each
entry gives: **arc anchor · proposed milestone · entry gate · exit signal.**

---

## Arc anchor — "## Post-public — the 1.1.x epic series"

> Quoted anchor (RELEASE_ARC.md:818): *"After the v1.1.0 public tag, work
> resumes as the **1.1.x epic series** … These are **scheduled** — distinct from
> the nursery deferred-idea bed. Each heavy lever gets its own design-spike
> before code."*

**PROPOSED INSERTION — a four-lane post-public frame.** The current section
lists 1.1.1 *candidates* and *recurring workstreams* but does not name the
standing **operational lanes** that run *continuously* alongside the epics. Add
a short preamble establishing four lanes — **Maintenance, Community, Extraction,
Compliance-agent** — each sized for a solo owner on the **W-3** agent-station
budget ("a couple hours/week of planning and agent management"). The lanes are
not epics; they are the steady-state envelope the 1.1.x epics execute inside.

---

## Lane 1 — Maintenance (dependency cadence + disclosure handling)

> **Arc anchor — "Recurring / continuing workstreams:"** (RELEASE_ARC.md:841).
> The recurring list names WS-2-full and WS-3 but no dependency or
> security-disclosure cadence. This lane fills that gap **best-effort per D-4**,
> machine-driven so it never becomes a promised human SLA.

**Proposed milestone — `ops/maintenance-lane` (standing, opens at v1.1.0).**
A machine-tended maintenance posture: Dependabot/lockfile drift PRs land on a
fixed cron (the bot proposes; the owner reviews on the W-3 budget), and a
**Private Vulnerability Reporting** intake replaces any day-count promise. This
directly closes the E-2 machine-badge gap (**F-qe-rel-03**, **F-sec-09**:
no Dependabot/lockfile/Scorecard/REUSE/egress-test/PVR at the pin) and the
D-4 SLA violations (**F-qe-rel-08**, **F-sec-07**: SECURITY.md and
CODE_OF_CONDUCT.md still ship hard 5-day / 30-day SLAs — to be softened to
best-effort wording, *not* re-promised on a faster clock). The disclosure
channel itself must first be corrected (**F-sec-11**, CONFIRMED: COC and
`.github/ISSUE_TEMPLATE/config.yml` route reports to the stale `Cooksey/resume`
repo, not `amodal1/callback`) — that correction is a v1.0.7 pre-public item, and
this lane *inherits* the corrected channel.

- **Entry gate:** v1.1.0 tagged **and** the E-2 machine-badge set committed
  (Dependabot + lockfile, OpenSSF Scorecard, REUSE/SPDX, the network-egress
  falsifiability test, PVR enabled). The egress test is load-bearing: it is the
  machine substitute for C-2's prose promise (**F-qe-rel-02** P0, **F-sec-01**)
  and keeps C-2 honest *after* the v1.0.6 Chart.js vendoring (**F-sec-03**,
  **F-docs-02**).
- **Exit signal:** none — this lane is *standing*. Its health signal is
  green-by-default: Scorecard score does not regress, the egress test stays in
  the required check set, and no dependency PR sits unreviewed past one W-3
  cycle. If the owner's review budget is the bottleneck, that is surfaced by the
  bot backlog, not by a missed promise.

---

## Lane 2 — Community (triage rhythm, contribution ladder, good-first-issue)

> **Arc anchor — "## Post-public — the 1.1.x epic series"** preamble
> (RELEASE_ARC.md:818-824). The arc has no community-intake model; for a
> governance-heavy single-owner repo this needs explicit, soft framing.

**Proposed milestone — `ops/community-lane` (standing, opens at v1.1.0).**
A triage *rhythm* (not an SLA): issues are labeled on the W-3 cadence; the
owner's posture is **P-3** — "tries to get to them as soon as possible," with
**no response-time promise** (D-4). The contribution ladder mirrors the
charter's **A-2** continuum: *user* (files an issue / repro) → *power-user*
(annotation/eval contributions, no code) → *dev* (PRs against the
quality gate). **Good-first-issue means something specific in this repo:** a
task whose acceptance is **machine-decidable by the existing gates** — the
ruff + mypy + pytest bar, the `route-security-lint` / `block-secrets` /
`require-feature-branch` hooks, and (once it lands) the C-6 boundary test
(**F-arch-01**, **F-qe-rel-04**: the deterministic/LLM boundary holds by
convention at the pin, with no gate that fails on an LLM import — a
good-first-issue is *only* "good first" once a contributor can self-verify it
without owner adjudication). A contributor-facing note must state that the UX /
a11y / PDF tiers **silently skip without Chromium** (**F-qe-rel-01** P0,
CONFIRMED): a "passing" local `pytest` does not exercise them, so the
contribution ladder points contributors at the dedicated CI job as the real
gate, not their local run.

- **Entry gate:** GitHub repo live (the v1.1.0 release event) **and** the
  disclosure/issue channels point at the canonical repo (**F-sec-11** fixed)
  **and** at least the a11y + UX CI job runs as a required check (**F-qe-rel-01**
  remediation) so good-first-issues are machine-decidable.
- **Exit signal:** none — standing. Health signal: the good-first-issue label is
  never applied to a task that a contributor cannot self-verify against a
  committed gate (i.e., the label tracks enforcement, not owner goodwill).

---

## Lane 3 — Extraction milestones (per incubating system)

> **Arc anchor — "*(WS-1 (the monolith split) and the doc-grounded assistant are
> not here — they moved pre-public …)*"** (RELEASE_ARC.md:849-850). The arc
> notes what moved *out* of post-public but does not give the **extraction
> machinery** for the systems the charter (**W-4**) marks for graduation. This
> lane supplies per-system **entry gate + exit signal**, cross-referenced to the
> sibling [`extraction-playbook.md`](extraction-playbook.md).

**Proposed milestone — extraction tracking, one row per W-4 incubant.** W-4
names the discipline ("modularize in place until a system is mature, a second
project needs it, or attention economics warrant breakout") and five intents.
The arc has no place that pairs each with a falsifiable readiness signal —
**F-gov-08** (CONFIRMED-class FIX): *no W-4 maturity metric exists for four of
five incubants; only `recall/` has a readiness condition.* This lane closes that
gap by giving each a **mechanism-based entry gate** (what makes it ripe) and an
**exit signal** (what proves it graduated), per the playbook's contract.

| Incubant (W-4) | Entry gate (ripe to extract) | Exit signal (graduated) |
|---|---|---|
| **recall / memory → product** | The only one with a stated readiness condition today (`memory-architecture.md`, per F-gov-08); extract when the `recall/` package's staged build is eval-passing **and** a second project needs it. | `recall/` lives as its own repo/package; callback. consumes it as a dependency; the re-introduction friction (W-4) is logged. |
| **governance rulebook + compliance agent → product** | After the v1.0.7 governance extraction lands one canonical constitution (**F-gov-05**, KEEP) **and** the compliance agent has a standing pilot (Lane 4). | The rulebook + agent run against a *second* repo; callback. becomes one of its monitored projects. |
| **LLM-wiki + self-documenting loop → inside the memory product** | After the v1.0.7 self-documenting loop runs autonomous/bounded/cost-aware and the wiki cold-ingest proves out (WS-4b). | The loop is a `recall/`-internal capability, not a callback.-local skill set. |
| **doc-grounded assistant → product within the operator stack** | After v1.0.7 ships the assistant answering from the wiki with citations (Haiku, user's key). | The assistant generalizes across the operator stack; callback. is one consumer. |
| **grounding-metric three-tier pattern → still research** | **No extraction gate — research, per W-4.** Becomes extractable only if the v1.0.7 PV-2 calibration (**F-eval-02**, CONFIRMED: real loop never exercised, L1/L2 uncalibrated at the pin) yields a transferable, calibrated detector. | N/A until research matures; tracked as research, not scheduled extraction. |

- **Per-system entry gate:** as tabled — each is a *mechanism* (a passing build,
  a second consumer, a proven loop), never a calendar date or an owner promise.
- **Per-system exit signal:** the system runs *outside* callback. and callback.
  consumes it back (W-4's "re-introduction is hoped for but friction-dependent"
  — the friction is logged, not promised away).

---

## Lane 4 — Compliance-agent (design now → pilot v1.0.7 → standing v1.1.x)

> **Arc anchor — "## Hard constraints (all phases)"** (RELEASE_ARC.md:854-863).
> The arc's hard constraints are enforced by seven blocker hooks
> (**F-gov-04**, KEEP: seven real exit-2 blockers, honestly separated from three
> witness rules). The compliance agent is the **witness** layer that watches the
> rules the hooks cannot reach — it does not block; it reports. This lane gives
> it a build path that honors **C-0 / D-4**: a *witness, not an approver*.

**Proposed milestone — the compliance-agent lane, three stages.**

1. **Design now (this review).** The design artifact is the sibling
   [`compliance-agent-design.md`](compliance-agent-design.md); the read-only
   subagent precedent already exists (**F-gov-09**, KEEP: `prompt-archaeologist`
   is read-only). The agent's governance interface is built at v1.0.7 assistant
   build time (**W-2**: "the v1.0.7 assistant gets its governance interface at
   build time").
2. **Pilot at v1.0.7.** The agent runs *witness-only* against the freshly
   extracted canonical constitution (**F-gov-05**). Its first standing targets
   are the gaps the hooks structurally miss: the block-merge hook passes the
   dominant feature-merge direction unblocked (**F-gov-01**, CONFIRMED —
   convention-only for the common path); the parallel-session isolation rules
   are uncodified in production governance (**F-gov-02**, **F-gov-03**,
   CONFIRMED — serial-session framing still authoritative, W-1 collisions
   structural in code); and the `check-plan-approved` hook prints a
   hand-create-the-marker hint that contradicts the never-hand-create rule
   (**F-gov-07**, DEBUFF). The agent flags these in a drift report; it does not
   edit or block.
3. **Standing at v1.1.x.** The agent becomes a recurring **witness** in the
   amendment ceremony (charter: "a flag in the compliance agent's next drift
   report (witness, not approver)") and a Lane-3 extraction candidate (the
   governance rulebook + agent → product).

- **Entry gate:** v1.0.7 governance extraction landed (one canonical
  constitution to lint against — **F-gov-05**) **and** the agent's governance
  interface built at assistant build time (**W-2**). The pilot may not begin
  before there is a single home for the rules; linting scattered rules would
  re-create the drift the extraction exists to remove.
- **Exit signal (per stage):** *design* → the design + agent definition merged;
  *pilot* → at least one real drift report produced against the v1.0.7
  constitution covering the F-gov-01/02/03/07 gaps; *standing* → the agent is
  named in the amendment ceremony as the witness and is a tracked Lane-3
  extraction candidate. The agent never gains approver authority — that would
  violate the C-0 / D-4 witness-not-approver posture and is an explicit
  non-goal.

---

## Cross-lane note — soft-commitments posture (P-3 / D-4)

Every rhythm above is a **machine trigger** (a cron, a required CI check, a
passing build, a drift report) or an **opportunistic prompt** (the owner reviews
on the W-3 budget). **No lane proposes a recurring human-labor obligation as a
hard commitment.** Where the charter's external measures (**E-1**) want
inviolability, only the *machine-run* measures are inviolable (the egress test,
the badges, the CI gates); the *human-promise* measures stay best-effort
(**T-C** resolution). This is the same line the charter draws and the same line
the seven blocker hooks vs. three witness rules already encode
(**F-gov-04** / **F-gov-06**, KEEP).
