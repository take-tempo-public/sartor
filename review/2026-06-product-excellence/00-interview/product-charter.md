---
status: review-artifact — DRAFT v0.3 (owner charter-review notes applied), awaiting signature
evidence_sha: c6e0437
graduation: docs/governance/charter.md (v1.0.7, on owner approval)
---

# Product Charter — callback.

> Distilled from the discovery interview
> ([interview-record.md](interview-record.md)). v0.2 incorporates an
> adversarial trace-check (every claim audited against the owner's
> recorded words) and a code-level egress audit at `c6e0437`.
>
> **Source labels — the epistemic contract:**
> - *unmarked* — owner-voiced; the footnote names the answer.
> - **⚠** — reviewer synthesis or proposal: confirm, edit, or strike.
> - **📄** — imported from repo docs/code, never said in the interview:
>   confirmed only by your signature.
>
> This document is the severity rubric for the entire review: a gap is a
> gap only if it blocks something stated here.

## Preamble — what callback. is

**P-1.** callback. replaces the copy-paste-and-edit lifecycle of Word-doc
resumes. It harvests career history, experience, skills, and summaries
from the unstructured documents a user already has, builds a grounded
corpus of their professional experience, and generates job-specific
resumes — ATS-parseable and human-readable — with human checks at every
step, because it's the user's information. *(Q1)*

**P-2.** Identity: **local and yours.** It runs locally on the user's
machine; the user's data stays there, under their control. The reasons
are privacy, personal control, **own not rent**, and refusing to
incentivize surveillance by creating a data honeypot. The values are
trust, user control, and user capability — stated plainly, without
marketing language. *(R2-4.1, Q11)*

**P-3.** Posture: an **open source project executed with the best of
intentions — including significant effort in diligence — but no
guarantees.** When issues are raised, the owner tries to get to them as
soon as possible. The project is more than transparent: effort goes into
sourcing and describing every part of itself, and the app includes a
support agent (the doc-grounded assistant, v1.0.7) that can help a dev or
agent-savvy user understand whatever it knows about itself — how it
works, what it's been, what it hopes to be, and how it tries to respect
the user. Commitments stay soft so the project never becomes an
obligation that consumes its owner. *(posture directive; charter-review
notes 2026-06-12)*

**P-4.** It earns its keep **when a user gets an interview for a job
where callback. wrote the resume.** Interviews are the reward and the
measure. *(Q1, Q8)*

**P-5.** Kill conditions the owner respects: the LLMs cannot be grounded
well enough to do the job effectively; or the project is superseded by
open projects that do this better. *(Q2)*

**P-6.** Horizon: five years out, callback. is a maintained tool real
people use, a portfolio exhibit, and — at first — a seedbed whose
incubated systems graduate outward, after which it becomes a digest and
test bed for them. Post-v2.x.x the codebase is intended to be fairly
stable: bugfixes and small feature sprints, with continuing polish
between v1.1.0 and then. *(Q3, Q1)*

## Claims discipline (how this charter and the public docs speak)

**C-0.** ⚠ *(reviewer synthesis from R2-4.2/R2-4.4 + posture directive —
confirm or strike)* Categorical ("never / only / always") claims are made
**only where a deterministic test can enforce them by construction**
(network egress, module boundary, shipped-template properties). Anywhere
a claim depends on LLM behavior, we describe **mechanisms and effort**,
never absolutes. "We do our best, and here is exactly how" outranks "we
guarantee."

## Constitutional clauses

*Each is owner-voiced or machine-enforceable. Amendment mechanics are
proposed at the end (⚠).*

**C-1. Local and yours.** callback. is a tool that is **local and under
the control of a single unauthenticated user.** All user artifacts stay
on the user's disk, under the user's control, never uploaded; there is no
hosted service. The program leaks nothing outside itself; the machine and
the interface are the user's domain. Use cases are left open, not
enumerated. *(R2-4.1, Q1, Q11; charter-review notes)* 📄 *Implementation
detail enforced in code: the server binds to 127.0.0.1 only.*

**C-2. Egress.** No diagnostics or telemetry **leave the machine, ever**.
The traffic is to the LLM provider the user configures — today
Anthropic; in the near future, whichever provider the user picks,
including their own local models. *(R2-4.3, R2-1, Q10)*
The sanctioned egress classes are exactly two: **(a)** the configured LLM
provider, and **(b)** the optional profile/website scrape when the user
has provided LinkedIn/portfolio URLs. JDs are always pasted text — no
JD-URL fetch exists or is wanted. *(post-charter rulings, 2026-06-12)*
Because the destination set is enumerable, this clause is
machine-verifiable — and **was verified at `c6e0437`**: every LLM call
routes to the configured provider; no analytics, error reporting, or
phone-home exists; fonts and paged.js are vendored. By the same
enumeration, callback. cannot submit applications or send anything on the
user's behalf — no such destination exists. Four code/doc realities,
**all ruled 2026-06-12**:
- **(i) RULED — fix, v1.0.6.** The diagnostics dashboard loads Chart.js
  from a CDN at runtime (`dashboard/templates/dashboard.html:15`) — a
  confirmed violation of the no-CDN promise. Prescription PX-01: vendor
  it.
- **(ii) RULED — sanctioned power-user opt-in.** The eval-grounding
  scorers download ~3.2GB of model weights from huggingface.co on first
  use. Governed by D-6 (per-system bundling + progressive disclosure);
  named in PRIVACY/SECURITY docs as the tuning system's opt-in install.
- **(iii) RULED — regression, fix v1.0.6.** The profile/website scrape
  *should* work when URLs are provided; it is dead code at `c6e0437`.
  Prescription PX-02: re-wire.
- **(iv) RULED — docs fix, v1.0.6.** No JD-URL fetch exists; `jd_url` is
  provenance metadata. Prescription PX-03: correct
  SECURITY.md/vision/README to the two-class enumeration.

**C-3. Grounding mechanisms; grounded synthesis is the feature.**
callback. does its best to keep the LLM grounded in real experience:
grounding rules in the prompts 📄 *(with worked OK/NOT-OK examples — repo
detail)*; clarifying questions that extend ground truth into undocumented
areas; human review at each step; corpus approvals for LLM-generated
bullets; and a candidate memory that helps the LLM hallucinate less as it
learns the user's documented experience. **Grounded synthesis is the
feature**: abstracting useful bullets from corpus + clarifications toward
a specific JD is what clarification is *for*; the violation is asserting
beyond that ground, not synthesizing within it. Usability is protected
from purity — grounding tightening that suppresses useful grounded
synthesis is treated as a regression (see lead AL-1). *(R2-4.2, R2-4.4,
Q1)*

**C-4. The candidate stays in control.** Human checks along the way — at
every step — because it's the user's information; the user can edit
anything before using it. *(Q1, R2-3)*

**C-5. Everything callback. ships is ATS-safe.** All the time. Users who
want non-ATS output edit the document they produced — callback. doesn't
need to solve every problem. 📄 *Mechanics: single-column, plain-bullet,
standard-font bundled templates; non-ATS templates retired.* *(R2-3)*

**C-6. The deterministic–LLM boundary.** Inviolable: deterministic
modules make no LLM calls; one module owns all LLM calls. *(Q10)*
📄 *As enforced today: `hardening.py`, `parser.py`, `generator.py`,
`scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`,
`pdf_render.py` are LLM-free; `analyzer.py` is the sole caller with every
call kind named, model-assigned, cost-logged, prompt-versioned; routes
proxy.*

## Defaults

*Binding until changed; changeable in normal flow with a written
rationale.*

**D-1.** Minimal dependencies (~8) — negotiable. *(Q10)* 📄 *Mechanics
per CONTRIBUTING: new dep = pyproject + CHANGELOG + "couldn't reasonably
be done in pure Python or an existing dep."*

**D-2.** Anthropic as the sole LLM client — a default with a **planned
amendment**: provider-agnostic + local-model capability post-public. When
built: metric a couple of open-source models for the various purposes,
describe their performance, leave instructions and tooling for dev users
to validate their own choices. No hard refusal floor; the user owns the
decision. C-2's wording amends by ceremony then. *(R2-7, Q1, Q10)*

**D-3.** No accounts, no auth — the current shape, explicitly negotiable.
*(Q10, R2-4.1)*

**D-4.** **Commitments hygiene.** Public docs make no response-time SLAs
and no recurring human-labor promises; existing promises that exceed this
(e.g., SECURITY.md's 5-business-day vulnerability response) are softened
to best-effort wording. Machine-enforced gates are exempt — they don't
tax the owner's life. *(posture directive)*

**D-6. Per-system tool bundling, progressively disclosed.** Capabilities
that require extra installs are bundled per system — the tuning system
(grounding-scorer models), dev work (Chromium), and so on. Things a user
never needs to do, they shouldn't have to see; install documentation is
progressive and threaded for completeness. *(post-charter ruling,
2026-06-12)*

**D-5.** 📄 *Repo-imported defaults — confirmed only by your signature:*
open-standards mechanics (JSON Resume as canonical intermediate; standard
fonts, offline rendering; MIT-compatible licensing with vendored headers
preserved and upstreams credited) and auditable iterations (each
generation writes a new timestamped child context; the parent chain is
the audit trail). Neither was discussed in the interview.

## External measures

**E-1.** Pursue badge-able, strong external measures in **every** area
that has them — tempered by P-3/D-4: machine-run measures preferred
(they keep themselves honest); human-promise measures stay best-effort.
*(Q12, closing directive S20)*

**E-2.** The agreed accessibility + badges package *(R2-12, "agreed")*:
- Machine-checked taxonomy in CI, free forever: names/labels (widened axe
  + strict non-placeholder accessible-name assertion) · tab order
  (registry-driven keyboard traversal) · keyboard completeness (every
  action reachable — including a bullet-reorder alternative — no traps,
  Escape/focus-return) · focus on dynamic content · live-region
  announcements at every async completion · back/history behavior ·
  reflow/zoom · contrast.
- One bounded deep NVDA walkthrough pre-public (one-time, v1.0.7
  hardening); opportunistic passes after major UI changes.
- ACCESSIBILITY.md as an honest status page; screen-reader feedback
  treated as priority bugs; **no conformance claim, no tag gate, no
  recurring manual-audit promise**.
- Badges: machine-run set (OpenSSF Scorecard, REUSE lint, Dependabot +
  lockfile, network-egress falsifiability test) + one-time Private
  Vulnerability Reporting setup; OpenSSF Best Practices optional/later.
- Diagnostics surfaces in scope — they are power-user surfaces. *(R2-12.2)*

## Audience

**A-1.** Primary: job seekers tailoring resumes — a mildly technical
audience for now (API-key setup is acknowledged friction). *(Q4, Q7)*

**A-2.** One audience on a continuum: **user → power-user → dev**. Power
users learn to tune and annotate without writing code; devs alter code.
Capabilities, surfaces, and docs serve the continuum, not two separate
populations. *(R2-12.2, Q15)*

**A-3.** Builders who want the patterns (eval loop, wiki/memory,
governance) — affirmed without hedge in the owner's ranking. *(Q4)*

**A-4.** Occasional: engineers and hiring managers reading the repo as
evidence of craft. The reaction sought: **"whoa, this is robust"** — earned
by three exhibits: the eval/tuning loop, grounding performance of
generations, and the wiki/memory + documentation-with-git system. *(Q4,
Q14)*

**A-5.** Wanted but blocked by the industry: direct structured-data
submission into application systems. User-facing application systems do
not accept structured formats even though their back-ends digest into
them — an industry breakage confirmed by prior research. That is why
callback. standardizes on JSON Resume internally and plans to integrate
industry-standard descriptors for resume data into that format: clean
implied structure today, ready if a direct path ever opens. *(Q6;
charter-review notes)*

## Severity inputs (how the review weighs findings)

**S-1.** Ranked release fears: **PII leak** first; then glaring misses
revealing amateurish planning and execution; then being unusable. *(Q16)*

**S-2.** Quality trade-offs: ugly-for-correctness is acceptable in the
grounding and improvement tools; incomplete-for-elegance is acceptable
(and already practiced) in the user-capabilities area. *(Q13)*

**S-3.** The owner's self-named furthest-below-bar area: clear
understanding and communication of the grounding/tuning/clarify
pipelines — documented and explainable to users, through the UI and the
diagnostics. *(Q15)*

## Success measures & release evidence

**M-1.** Success is interviews (P-4) — knowable to the user, and locally
usable by the user's own instance for outcome-informed tuning on their
personal corpus; the project as a whole accepts that, by C-2, it cannot
observe its own aggregate success. *(Q8, R2-1; charter-review notes)*

**M-2.** v1.1.0 tag evidence (written, self-imposed criteria): *(Q17,
R2-5 "perfect"/"yes", R2-6)*
- ≥10 real applications submitted via callback. with zero
  release-blocking bugs, spanning: ≥3 with a clarify round, ≥2 with
  iteration after first generate, ≥2 with cover letters, ≥2 distinct
  templates, both output formats, ≥1 prior-app resume reuse.
- The tuning/annotation loop exercised end-to-end by the owner with
  metrics readable at a glance.
- ≥1 interview from a callback-written resume — written criterion,
  ⚠ weighed as evidence rather than a hard gate (market-dependent; this
  split was the reviewer's framing, accepted in your "perfect" — confirm).
- Two first-run bars: fresh-clone skip-clarify smoke < 5 min; full
  clarify-inclusive first run ~15 min, quality evidenced by an
  owner-blind comparison against a hand-tailored resume.
- Explainability artifacts shipped (v1.0.7 criterion): the user-facing
  "how callback. grounds, clarifies, and tunes" wiki page; a lay metrics
  legend in diagnostics; the planned diagnostics improvements. *(R2-9)*

**M-3.** 90-day post-public hopes (not gates; largely unobservable by
design, accepted): ~100 stars, positive social sharing. *(Q7, R2-1)*

## Working model (constitution-adjacent)

**W-1.** Multi-altitude agent parallelism is the real working model; the
serial-session framing in current docs is stale and gets updated, with
isolation rules (⚠ reviewer to propose: worktree-per-session,
global-state ownership, branch ownership) becoming written governance.
*(Q20, R2-11)*

**W-2.** Governance is constitution building — it spans the owner's
projects, has measurably accelerated work, and graduates outward to its
own project eventually. The operator-stack triad — memory supplies
context; governance directs posture, constitutionally and with
guardrails; the operator LLM occupies that space — is the extraction
architecture, and the v1.0.7 assistant gets its governance interface at
build time: it is how the assistant is tuned, managed, and bounded.
*(Q19, Q21, Q22e, R2-10)*

**W-3.** Maintenance: agent-station (build starting the week after
2026-06-12) runs post-public operations; callback.'s v1.1.0 GitHub
integration is its canary project — set-up flow, template containers,
GitHub CI build-out. Owner budget: a couple hours/week of planning and
agent management. *(Q18, R2-8)*

**W-4.** Extraction discipline: conscientiously modularize in place until
a system is mature, a second project needs it, or attention economics
warrant breakout; re-introduction after extraction is hoped for but
friction-dependent. Intents: recall/memory → product; governance rulebook
+ compliance agent → product; LLM-wiki + self-documenting loop → inside
the memory product; doc-grounded assistant → product within the operator
stack; grounding-metric three-tier pattern → still research. *(Q22, Q23,
Q24)*

## Tensions accepted

**T-A.** Success is measured by interviews, and C-2 keeps outcomes
invisible to the project — but not to the user's own instance: outcomes
are captured locally for the single user, enabling strong tuning on one
person's personal corpus, **which is worth more than being pretty good on
everyone's.** The trade is deliberate: per-user excellence over
population averages; the project itself simply never learns its own
aggregate success. *(R2-1; charter-review notes)*

**T-B.** Grounding strictness trades against usefulness; direction set
(C-3: synthesis within ground = feature) and the current balance is
suspected over-tight (lead AL-1).

**T-C.** External "inviolable measures" (Q12) vs soft commitments:
resolved by E-1/D-4 — machine-enforced measures may be inviolable;
human-promise measures stay best-effort. *(R2-12 resolution)*

**T-D.** "Functionally complete at v1.1.0" rides on machinery never yet
exercised on real data (admitted on both sides); M-2 exists to close
exactly that gap before the tag.

## ⚠ Amendment ceremony (reviewer proposal — confirm, edit, or strike)

Amending a constitutional clause requires: a dated amendment entry in
this document with rationale; a CHANGELOG entry; explicit owner sign-off
at merge; and — once it exists — a flag in the compliance agent's next
drift report (witness, not approver). Defaults change in normal branch
flow with a written rationale line.

---

## Sign-off

Open items to settle by editing above, then sign:
1. C-0 claims discipline — confirm or strike.
2. ~~C-2 (i)–(iv)~~ — **ruled 2026-06-12** (fix Chart.js v1.0.6; HF
   downloads = sanctioned power-user opt-in under D-6; scrape re-wired
   v1.0.6; jd_url docs corrected v1.0.6). Glance at the final two-class
   wording.
3. D-5 repo-imported defaults — keep, edit, or drop.
4. M-2 interview-criterion framing (weighed vs hard gate) — confirm.
5. Amendment ceremony — confirm, edit, or strike.

- [ ] Signed: ______________________  Date: ____________

Once signed, this charter is the review's severity anchor and the
graduation source for `docs/governance/charter.md` in v1.0.7.
