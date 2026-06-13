---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Discovery Interview Record

> Owner interviewed as customer (agency model), per review plan Phase 1.
> Answers preserved near-verbatim (original wording kept, including informal
> phrasing); interviewer annotations appear only in *Tensions noted* and
> *Signals* sections. The Product Charter distills ONLY from this record.

- **Interviewee:** owner (amodal1)
- **Format:** live, two rounds, cluster batches
- **Round 1 batch 1 (clusters 1–4):** asked + answered 2026-06-12/13
- **Round 1 batch 2 (clusters 5–8):** asked + answered 2026-06-12
- **Round 2 (tensions + follow-ups):** asked + answered 2026-06-12 (R2-12
  continued as live discussion); informed by the
  [round-2 verification brief](round2-verification-brief.md)
- **Charter:** v0.3 SIGNED 2026-06-12 (Robert Cooksey) — all sign-off
  items confirmed inline except M-2's interview-criterion framing, which
  carried no inline word and is treated as confirmed by the signature.
  **Phase 1 closed.**

> **Redaction note (2026-06-12):** at the owner's direction, references to
> out-of-scope external work that surfaced conversationally during the
> interview were removed from this record and all review artifacts; affected
> passages were cut or generalized and the review branch history rewritten to
> match. The removals alter no in-scope product decision.

---

## Round 1 — Batch 1

### Cluster 1 — Purpose & identity

**Q1. In your own words — not vision.md's — what is callback. when it's
*finished*? What's the moment it earns its keep for a user?**

> callback is a replacement for maintaining word documents that get copy and
> pasted into new word documents and edited for each job from one document to
> another. callback uses canonical resumes to source career history,
> experience, skills, and summaries to elucidate roles. It harvests from what
> you've already captured in unstructured documents and creates a grounding
> body of your professional experience, and uses that to generate job
> description resumes — helping the user to put their best foot forward when
> creating resumes that are largely screened by ai in ATS systems and
> scrutinized by humans to identify strong candidates. callback tries to
> reduce the document to document work, assist in building strong job
> appropriate resumes in ATS and human friendly formats that are grounded in
> real experience, and helping the user to source experience and skills not
> captured in their resume and to integrate that into their career corpus
> (always with human checks along the way — it's their information). It is
> local and open, so it runs off the user's machine and the only data egress
> is the llm calls which will be capable of integrating with local llms in
> v2.x.x. The goal is to have it functionally complete for v1.1.0 but there
> will be continuing iterations as we polish and refine. I would hope that
> the entire codebase is fairly stable with bugfixes and small feature
> sprints after v2.x.x. **It earns its keep by getting a user an interview
> for a job where callback wrote the resume.**

**Q2. What would make you kill the project entirely?**

> if the llms could not be grounded well enough to do their jobs
> effectively. superseded by other open projects that do what we do better.

**Q3. Five years out, which is callback.? (a) maintained tool, (b) portfolio
exhibit, (c) seedbed for extracted systems, (d) other.**

> a+b+c (for the beginning, then a digest and test bed for those systems)

### Cluster 2 — Audience

**Q4. Who actually clones this repo? Rank: (a) job seekers, (b) engineers/
hiring managers evaluating the owner, (c) builders wanting the patterns,
(d) contributors.**

> a + maybe occasional b + c + maybe d but i doubt it + a possible business
> audience for headhunters, professional coaches etc.

**Q5. For your #1 audience: the single thing they must experience in their
first 15 minutes?**

> they should be able to create a new user, import their resume, paste a job
> description, maybe have clarifying questions (a few minute slow down), add
> a template and download a resume with a surprisingly good quality (at
> least as good as you would have done but faster and with things you
> weren't thinking of)

**Q6. An audience you're explicitly NOT serving that people might assume
you are?**

> plugging directly into ATS with structured data. all the pieces exist but
> the industry has serious gaps. so regardless of our structuring data in a
> way that ATS back-of-the-house systems want and need, we must go through a
> step where we structure cleanly as best we can so the HR systems can imply
> that structure. I hope to find a path around this blocker in the future.

### Cluster 3 — Success criteria

**Q7. 90 days after v1.1.0: what numbers or events make it a success?**

> 100 stars and positive feedback would be a good start. social media posts
> about the project. positive social sharing. it's for a mildly technical
> audience due to the llm set-up requirement. you have to copy a key that
> most users haven't heard of or don't have

**Q8. Cheapest honest signal that the product genuinely works?**

> interviews. interviews are the reward and the measure.

**Q9. Local-first means no telemetry — how will you KNOW any of the above
happened? What feedback channel is acceptable?**

> an opt-in local telemetry system that digests data to scrub for pii,
> fingerprints the configuration, and exports data about quality of resumes
> generated, maybe a package structure if user is tracking
> submitted/rejected/interview. the user is not incentivized for this and we
> want to respect what we built this for for ourselves anyway. we need to
> find a new way of respectfully addressing user data and personal
> ownership of data

### Cluster 4 — Constraints

**Q10. Inviolable vs negotiable:**

> - local-first/no telemetry — **inviolable**
> - single-tenant/no auth — **negotiable**
> - minimal deps (~8) — **negotiable**
> - Anthropic-only LLM — **this will go away** for provider agnostic and
>   local capability
> - ATS-safe/standard fonts — **negotiable but only if explicitly flagged**
>   (for non-ats customers (execs, referral, small business))
> - deterministic-vs-LLM module boundary — **inviolable**

**Q11. The real reason for local-first?**

> privacy, personal control, own not rent, don't incentivize surveillance
> with data honeypot

**Q12. Accessibility: what bar will you commit to publicly at v1.1.0?**

> push me on this. the bar should be very high and any cert quality badges
> we can add are helpful and create external inviolable measures to keep us
> honest

---

## Tensions noted (to revisit in Round 2)

- **T1 — telemetry.** Q10 declares "local-first/no telemetry — inviolable";
  Q9 proposes an opt-in, PII-scrubbed, locally-digested export of quality/
  outcome data. Likely reconcilable (user-initiated export ≠ telemetry) but
  the constitution needs exact wording for what egress is permissible, who
  initiates, and what "opt-in" structurally requires.
- **T2 — single-tenant.** vision.md frames single-tenant/no-auth as a core
  constraint; Q10 marks it negotiable and Q4 introduces a business audience
  (headhunters, coaches) no repo doc acknowledges. Multi-client use by a
  coach strains single-tenant assumptions (data partitioning, consent for
  other people's career data). *(Resolved at R2-2.)*
- **T3 — provider-agnostic.** Q10: Anthropic-only "will go away" (v2.x local
  LLMs per Q1). Current eval/grounding/tuning apparatus is calibrated
  against Sonnet/Haiku behavior; provider-agnosticism has eval-system
  consequences no doc yet addresses.
- **T4 — ATS-safety escape hatch.** Q10 allows non-ATS-safe output if
  "explicitly flagged" for exec/referral/small-business audiences — vision.md
  currently states templates that aren't ATS-safe are retired. Constitution
  needs the flag semantics.
- **T5 — a11y bar.** Q12 invites being pushed upward ("external inviolable
  measures to keep us honest") — the current gate (axe serious/critical, 9
  panels) is far below a certifiable WCAG 2.1/2.2 AA claim. Round 2 carries
  a concrete proposal.

## Signals (load-bearing facts not currently in repo docs)

- S1: Success-defining outcome metric: **an interview from a
  callback-written resume** (Q1, Q8).
- S2: Kill conditions exist and are respected: grounding infeasibility;
  superseded by better open projects (Q2).
- S3: Five-year identity: tool + portfolio + seedbed, with seedbed becoming
  "digest and test bed" for extracted systems (Q3).
- S4: *(withdrawn per the redaction note; the in-scope ruling it pointed to
  is recorded at R2-2.)*
- S5: First-run bar: new user → import resume → paste JD → (clarify) →
  template → download, with "surprisingly good" output — within ~15 minutes
  (Q5).
- S6: Direct ATS integration is explicitly out of scope; clean implied
  structure is the deliberate compromise (Q6).
- S7: 90-day success: ~100 stars + positive social sharing; audience
  acknowledged as mildly technical due to API-key friction (Q7).
- S8: Q9 sketches a data-ownership-respecting feedback channel as a future
  design problem ("a new way of respectfully addressing user data").
- S9: v1.1.0 = "functionally complete"; stability hoped for after v2.x.x
  (Q1) — implies a v2 arc (provider-agnostic, local LLMs) already shapes
  current architectural decisions.

---

## Round 1 — Batch 2

### Cluster 5 — Portfolio vs. function

**Q13. One place you'd accept ugliness-for-correctness; one place you'd
accept incompleteness-for-elegance.**

> I'd accept ugly for correctness in the grounding and improvement tools.
> i'd accept incomplete for elegance (already am) in the user capabilities
> area

**Q14. The sentence in a senior engineer's head when they close the tab,
and the 2–3 exhibits that must form it.**

> whoa this is robust. eval/tuning loop, grounding performance of
> generations, wiki memory + documentation w/git

**Q15. Your own instinct: where is the product furthest below your own
bar?**

> clear understanding and communication of the grounding/tuning/clarify
> pipelines and having those processes documented and explainable to users
> as to how the system works, how we tune it, and how they can tune it
> themselves through the user interface and through the diagnostics

### Cluster 6 — Release confidence

**Q16. What scares you most about going public; which single post-release
failure would hurt most?**

> pii leak, glaring misses revealing amateurish planning and execution,
> being unusable

**Q17. What evidence would you need in hand to push the v1.1.0 tag with
confidence? Does the tag wait for real-data eval fixtures?**

> we haven't fully exercised that system yet. i want to use the system
> myself for a bit. apply to jobs and have no bugs, get interviews. i also
> want to be able to tune and annotate and exercise those systems
> confidently and see clear understandable metrics

**Q18. Post-1.1.0 maintenance, honestly: hours/week, response promise,
solo or co-maintainers?**

> the agent-station product will have dedicated agent for this with github
> supported architecture. i hope that it will take less of my attention
> going forward but still a couple hours a week of planning and agent
> management

### Cluster 7 — Governance appetite

**Q19. How much process when it's just you plus agents? Where is current
ceremony too heavy / too light?**

> it's significantly accelerated the process due to far less thrash and
> churn over mistakes and misalignments, avoiding steps etc. remember that
> governance is more for my projects than just the mechanisms of code
> maintenance etc. governance is constitution building

**Q20. Which of your own rules do you break most often? Any rule kept out
of inertia?**

> i often kick off multiple agents to do different levels of work
> simultaneously (one agent executing a sprint while i long range plan or
> ideate with another). it steps on governance and we have built tooling
> to adapt

**Q21. What's constitutional vs everyday-changeable, and who enforces?
Does "external inviolable measures" generalize beyond a11y?**

> yes. what things is part of the things we need to solve. this approach
> will graduate out to a governance project of its own eventually

### Cluster 8 — Extraction ambitions

**Q22. Per incubating system: ship as product / publish as pattern / keep
internal, and horizon.**

> - (a) recall/ memory substrate — **ship as product**
> - (b) governance rulebook + compliance agent — **ship as product**
> - (c) grounding metric three-tier pattern — **in research**
> - (d) LLM-wiki + self-documenting loop — **included in memory system +
>   ship as product**
> - (e) doc-grounded assistant — **ship as product but as part of operator
>   product stack. this is the agent part of a product that knows itself.
>   memory supplies with context, governance directs its posture and guides
>   behavior constitutionally and with guardrails, and this is the llm who
>   occupies that space and can interact with users and devs about it.**

**Q23. An extraction trigger you'd trust?**

> as it grows, conscientiously modularize system until it is mature enough
> (not sure best metric here) or is forced by need on another project or
> personal attention time warrants its breakout

*(Interviewer note: a sub-question was carried to Round 2 and resolved
there as out of scope.)*

**Q24. Extracted system's relationship back to callback.: dependency or
frozen copy?**

> hopefully re-introduced and replace later, but not necessary. depends on
> what the friction of the process reveals

**Closing directive (owner, unprompted):**

> thanks for picking up the commitment on accessibility and pushing that.
> please do so for any other areas that have such badging and strong
> external measures

---

## Tensions noted — batch 2 additions (for Round 2)

- **T6 — external channels unresolved.** The business/coach channel (Q4)
  and its relationship to agent-station (Q18) and the operator product
  stack (Q22e) were undefined. *(Resolved R2-2 + R2-8: the channel is out
  of this project's scope and stays undocumented; agent-station recorded
  at R2-8.)*
- **T7 — practiced vs written working model.** Q20: the owner routinely
  runs multiple agents at different altitudes simultaneously, which "steps
  on" the written one-branch-per-session governance; tooling has adapted.
  The constitution must encode the REAL model (multi-altitude parallelism
  with isolation rules), not the on-paper one it contradicts.
- **T8 — maintenance depends on an unbuilt product.** Q18's post-public
  maintenance story routes through "agent-station," whose status/horizon is
  unknown to this review. Needs a fallback posture if agent-station isn't
  ready when v1.1.0 ships.
- **T9 — tag criteria vs "functionally complete."** Q17's confidence
  evidence (personal real-world use, interviews won, tuning loop exercised
  with clear metrics) and Q15's explainability gap are not written tag
  criteria anywhere in RELEASE_ARC. Decide explicitly whether they gate
  v1.1.0.

## Signals — batch 2 additions

- S10: Reader-reaction north star: **"whoa, this is robust"**; the three
  exhibits: eval/tuning loop, grounding performance of generations,
  wiki/memory + documentation with git (Q14).
- S11: Owner's self-identified weakest area: explainability of the
  grounding/tuning/clarify pipelines — to users, through UI + diagnostics +
  docs (Q15).
- S12: Ranked fears: PII leak; glaring misses revealing amateurish planning
  and execution; being unusable (Q16).
- S13: Tag-confidence evidence: owner uses the product for real
  applications with no bugs and gets interviews; tuning/annotation systems
  exercised confidently with clear, understandable metrics (Q17).
- S14: **agent-station**: a planned product providing a dedicated
  GitHub-architecture maintenance agent; owner's steady-state budget is a
  couple hours/week of planning + agent management (Q18).
- S15: Governance verdict: ceremony has NET-ACCELERATED development (less
  thrash/churn); governance is constitution building spanning the owner's
  projects, not just code-maintenance mechanics (Q19).
- S16: Most-broken rule: simultaneous multi-altitude agent sessions;
  adaptation tooling exists and grows (Q20) — this review running parallel
  to dev is itself an instance.
- S17: The constitutional/everyday boundary is explicitly delegated to this
  review to propose; the governance approach "graduates out" to its own
  project eventually (Q21).
- S18: **Operator product stack** triad (Q22e): memory supplies context;
  governance directs posture constitutionally with guardrails; the
  operator/assistant is the LLM occupying that space, interfacing with
  users and devs — "the agent part of a product that knows itself."
- S19: Extraction triggers: conscientious continuous modularization until
  maturity (metric TBD — review to propose), OR second-project need, OR
  personal-attention economics; post-extraction reintegration hoped-for but
  optional (Q23, Q24).
- S20: Standing directive: pursue badge-able, strong external measures in
  EVERY area that has them, not just accessibility (closing).

---

## Round 2 — Questions (asked 2026-06-12; answers pending)

Derived from tensions T1–T9 plus the verification fan-out (contradictions
C1–C11, arc misalignments A1–A7, absences M1–M8, badge research — see
[round2-verification-brief.md](round2-verification-brief.md)).

- **R2-1 (T1, C1, C10) — Egress clause.** SECURITY.md promises no telemetry
  "(and never will, by design)". Does the Q9 export survive only as
  user-initiated, locally-assembled, file-on-disk, never auto-transmitted?
  Proposed canonical egress enumeration (3 classes today: Anthropic API,
  opt-in profile scrape, pasted-JD fetch) with export as a NON-network
  file act — confirm or amend, and give the exact sentence you'd put in
  SECURITY.md.
- **R2-2 (T2, T6, C2, C5) — Tenancy + business channel.** A coach with 10
  clients on one machine: 10 users (multi-tenant — three docs say never) or
  one operator with 10 corpora? Whose consent governs a client's data? Does
  the coach use case ship in callback. at all? Does "one person, one
  machine, one job at a time" survive as the identity sentence?
- **R2-3 (T4, C4) — ATS-safety flag.** vision.md: "ATS-safety is the
  product"; non-ATS templates "don't ship." For exec/referral: do non-ATS
  templates ship BUNDLED behind a visible flag, or only user-uploaded?
  Flag mechanics (badge wording, confirmation step)?
- **R2-4 (C8) — Two-tier constitution.** Proposed: constitutional tier
  (amendment = deliberate ceremony) vs defaults tier (changeable in normal
  flow). Which constraints land where, and what is the amendment ceremony?
- **R2-5 (T9, A1, M3, C6) — Written tag evidence + success measures.**
  Should these become WRITTEN v1.1.0 criteria: N real applications with
  zero release-blocking bugs; ≥1 interview from a callback-written resume;
  tuning/annotation loop exercised by you with at-a-glance metrics? Which
  are hard gates vs weighed evidence (interviews depend on the market)?
  Does vision.md gain the outcome-level goal, and do the 90-day measures
  (stars, sharing) go in a public doc or the private charter?
- **R2-6 (A2) — Two first-run bars.** Split the criterion: fresh-clone
  skip-clarify smoke < 5 min AND clarify-inclusive real first run ~15 min
  with a quality clause. What evidence proxy for "surprisingly good"
  (e.g., owner-blind A/B vs a hand-tailored resume)?
- **R2-7 (T3, C3, A3) — Provider-agnostic eval story.** Timing: 1.1.x
  (PRODUCT_SHAPE) or v2.x (you)? When it lands: per-provider re-baseline +
  per-model grounding floors, a provider-agnostic judge, or ungated
  caveat-emptor? Given the Q2 kill condition, is there a minimum capability
  bar below which local models are refused?
- **R2-8 (T8, C9, A4, M4) — Maintenance fallback.** agent-station status/
  horizon? Does it conform to CONTRIBUTING's identity pathway (Actions
  GITHUB_TOKEN → GitHub App, no per-agent PATs)? If it isn't ready at
  v1.1.0: fallback posture (response promise, triage cadence, hours), and
  should a minimal GitHub-ops item be added to Phase 5?
- **R2-9 (A6, Q15) — Explainability bar.** What artifact closes Q15: a
  user-facing "how callback grounds, clarifies, tunes" page; a lay metrics
  legend in diagnostics; a comprehension walkthrough with a non-technical
  reader? Written tag criterion at v1.0.6 or v1.0.7?
- **R2-10 (A5) — Governance→assistant wiring.** Should the v1.0.7
  assistant include a governance-posture interface (even a stub reading the
  extracted constitution) so the operator-stack triad extracts cleanly — or
  is that explicitly deferred to the standalone governance project?
- **R2-11 (T7, C7) — Codify the real working model.** Name the isolation
  rules your adaptation tooling actually enforces between parallel agents
  (worktrees, branch locks, who touches main-adjacent global state), so the
  constitution codifies multi-altitude parallelism and retires
  CONTRIBUTING's "Future:" framing. (Live evidence this session: the
  worktree-blind branch hook; a concurrent merge wiping the global
  plan-approval marker.)
- **R2-12 (T5, C11, A7, S20) — A11y commitment + badge set.** Proposal:
  commit publicly to WCAG 2.2 AA, full-app scope, at v1.1.0 — CI-enforced
  (Chromium-in-CI fix so the gate actually runs; axe widened to all
  WCAG-tag violations with a justified allowlist; keyboard-path, focus,
  reflow tests), 2–4 h/release manual NVDA pass logged, ACCESSIBILITY.md
  conformance statement via WCAG-EM. Gating question: does 2.2 AA gate the
  v1.1.0 tag, or stage it (axe-clean claim at v1.1.0 → full 2.2 AA at
  1.1.x)? And approve/trim the six-measure v1.1.0 badge set (OpenSSF Best
  Practices passing; Scorecard + badge; REUSE; Private Vulnerability
  Reporting; lockfile + Dependabot; egress-falsifiability test +
  PRIVACY.md)?

---

## Round 2 — Answers (2026-06-12)

**R2-1 — Egress clause: Q9 RECANTED; the docs stand.**

> the docs are right, it's not worth it. the responsibility for the data of
> others and possibly leaking pii. i'd rather just avoid it. i know what
> i'm leaving on the table.

Resolution: the categorical no-telemetry promise stands unqualified; no
export feature, opt-in or otherwise. The Q7 90-day success measures are
accepted as largely unobservable by design. T1/C1 **closed**. (C10's
enumeration mismatch — vision.md/README count two egress classes,
SECURITY.md three — remains a doc-consistency fix for the charter.)

**R2-2 — Tenancy: single-tenant stands; multi-client use is out of scope.**

> The tool doesn't do those things. Customers may do these things with
> callback … but the data relationship is between the headhunter/resume
> specialist and their clients. … i don't need [the project] involved and
> [it] should seek to stay out of those situations.

Resolution: "one person, one machine, one job at a time" survives as the
identity sentence. What operators do with open tooling on their own
machines is their own data relationship; callback. neither builds nor
documents a multi-client mode, deliberately. The owner further directed
that external context surfaced in Q4 remain entirely unreferenced in
project artifacts (see redaction note). T2/C2/C5 **closed**.

**R2-3 — ATS-safety: stands, categorical.**

> ATS friendly it is. all the time. those users can edit the document they
> produce if they want non-ATS. i don't need to solve every problem.

Resolution: no flag, no bundled non-ATS templates; vision.md's "ATS-safety
is the product" and the retirement rule stand as written. T4/C4 **closed**.

**R2-4 — Two-tier constitution: proposal rejected as offered.**

> No. revisit given the answers in this batch. Give me the guidelines you
> see enforced in vision so that I can be grounded

Grounded enumeration delivered in chat; owner's final answers below in
*Round 2 — Continued*. **Resolved there.**

**R2-5 — Written tag evidence: ACCEPTED; N open.**

> perfect. that N number? 10, 20? what makes sense

Reviewer recommended N=10 with a composition matrix (≥3 clarify-inclusive,
≥2 iteration chains, ≥2 cover letters, ≥2 templates, both formats, ≥1
prior-app reuse). Owner: **"yes"** (Round 2 — Continued). **Closed.**

**R2-6 — Two first-run bars: AGREED.**

Smoke bar (fresh clone, skip-clarify, < 5 min) + experience bar (~15 min
including clarify, quality evidenced by owner-blind comparison vs a
hand-tailored resume). A2 **closed**.

**R2-7 — Provider-agnostic eval story:**

> When that's built, we'll seek a couple open source models to metric for
> the various purposes. describe their performance, leave instructions to
> dev users how to do this with tooling and leave to them to validate
> their choices.

Resolution: benchmark a small set of OSS models per call-kind; publish
performance descriptions; ship validation tooling + instructions; users
validate their own model choices — no hard refusal floor. Timing stays
as-arc (post-public; epoch decided on arrival). T3/C3/A3 **direction set**.

**R2-8 — agent-station:**

> i plan to parallel build the agent-station next week. integrating this
> project into github (v.1.1.0) is a canary for that build and the first
> project to run through and test set-up, and build template containers,
> build out Github CI...

Resolution: callback.'s v1.1.0 GitHub integration is agent-station's canary
project — GitHub-ops infrastructure (CI build-out, template containers,
set-up flow) gets built as part of that run. Conformance to CONTRIBUTING's
identity pathway (GITHUB_TOKEN → GitHub App, no per-agent PATs) noted as an
open design detail for that build, not a callback. blocker. T8/C9/A4
**direction set**.

**R2-9 — Explainability bar:**

> a user-facing "how callback. grounds, clarifies, and tunes" page (the
> wiki's reserved user section), a lay metrics legend in diagnostics, and
> the plans we already have in place for the diagnostics page. 1.0.7

Resolution: three artifacts; written tag criterion at **v1.0.7**. A6
**closed**.

**R2-10 — Governance→assistant: YES, at assistant build time.**

> we should definitely consider governance for this assistant to be
> implemented at build assistant time. it will be how we tune the assistant
> and manage what it is, how it acts, and what it can/can't do

Resolution: the v1.0.7 assistant design includes its governance interface —
posture, capabilities, and guardrails read from the extracted constitution;
governance is the assistant's tuning/management mechanism. A5 **closed** →
feeds a prescription.

**R2-11 — Multi-agent stance: update the docs to the real model.**

> This session is inside claude code building callback. those guidances are
> for callback. but we have already moved to multi-agent since that
> writing. we should clean that up and update our multi-agent stance and
> documentation

Resolution: CONTRIBUTING's "Future:" framing and the serial-session
assumptions are stale. The constitution codifies multi-altitude parallelism
with isolation rules (review to propose: worktree-per-session, global-state
ownership, branch ownership). T7/C7 **closed** → feeds prescriptions.

**R2-12 — A11y commitment + badge set: IN DISCUSSION.**

> we need to go back and forth on this one for a second i think

Reviewer posture options + recommendation delivered in chat; owner's
partial answers and the governing posture directive below in *Round 2 —
Continued*; right-sized soft proposal pending.

---

## Round 2 — Continued (2026-06-12)

**R2-4.1 — Identity sentence REJECTED; "single-tenant" demoted.**

> Do we need one person, one machine, one job at a time? I don't think so.
> This seems to paint us into a corner without actually saying anything
> about what we care about. **Local and yours** is much closer to what we
> provide, though I suspect, if we stayed very close to what we actually do
> without marketing language, it would be better. single-tenant isn't
> necessary. my partner and i can use the same installation on a shared
> computer. it's about trust and giving you control and capability.

Resolution: identity language = **"local and yours"** — plain, factual,
no marketing. Single-tenancy is NOT a value: household sharing of one
installation is normal and fine (the user picker already supports multiple
local profiles). The values underneath are **trust, user control, user
capability**. The docs' terminal "single-tenant by design / we won't"
language is overstated → charter + prescription. (Interplay with R2-2
preserved: the commercial multi-client scenario stays out of scope — the
trust model is people who share a machine trust each other; nothing is
built for managing third parties' data.)

**R2-4.2 — "LLM cannot invent" is a bold claim; describe the mechanism,
not an absolute.**

> "LLM cannot invent" is a bold claim. We do our best to keep the llm
> grounded in real experience, we use questions to assist with grounding
> in undocumented areas, and we use human review for each step and the
> corpus approvals for llm generated bullets. And these help the llm
> hallucinate less as it learns more about your experience as documented
> in your career corpus and candidate memory

Resolution: grounding clauses describe mechanisms and effort (defense
layers, clarifying questions, per-step human review, corpus approvals,
candidate memory) — never absolutes about LLM behavior.

**R2-4.3 — Egress: categorical, in the owner's words.**

> no no diagnostics or telemetry, no d or t that LEAVE YOUR MACHINE. the
> only traffic is to the llm provider, which can be you or whichever one
> you pick (in the near future)

Resolution: categorical no-egress of diagnostics/telemetry; primary
traffic = the LLM provider the user configures ("which can be you" — local
models). NOTE: the owner's enumeration again omits the two opt-in fetch
classes (profile scrape; pasted-JD URL fetch) that exist in code and
SECURITY.md — flagged for explicit confirmation in the charter.

**R2-4.4 — "No invention, ever" is overstated; usability over purity.**

> i think no invention ever is over-stated and may actually prevent our
> llm from generating useful bullet points abstracted from the user
> clarification steps combined with existing corpus towards a specific JD.
> i've already noticed a significant reduction in suggested bullets, which
> is one of the main features of clarification (IMHO). we have to be
> careful not to give up usability in pursuit of perfection and purity

Resolution: **grounded synthesis is the feature** — abstracting useful
bullets from (corpus + clarifications) toward a specific JD is exactly
what clarification exists for; the violation is asserting beyond that
ground, not synthesizing within it. The constitution must protect
usability from purity.

**→ Assessment lead AL-1 (Phase 3, domain 5):** owner reports a
*significant reduction in suggested bullets* — a suspected
over-suppression regression from grounding tightening. Investigate
against recent prompt changes (PROMPT_VERSION history) and eval data.

**R2-5 (continued):** N=10 + composition matrix — **"yes."**

**R2-12.2 — Scope: the power-user continuum.**

> think power-user more than professional dev for this. it isn't that
> users and devs are separate. some users are also devs. devs may want to
> alter code and tune and annotate. some power users will learn to tune
> and annotate and such for themselves but never write code.

Resolution: diagnostics/tuning surfaces are power-user surfaces, in scope
for the a11y bar; audience is a continuum (user → power-user → dev), not
separate populations.

**R2-12 cost challenge:**

> 4-6 days of agent work for an accessibility scan?!?!?!?!

Reviewer clarified: the scan itself is hours (axe widening + CI fix); the
estimate covered new test-suite construction + evaluation ceremony;
remediation unknown until the widened scan runs.

**R2-12 — screen-reader consideration (owner push):**

> is this considerate of screen readers. i am very aware of their failures

Reviewer conceded the trimmed package leaned on automation, which is
near-blind to SR experience. Code check found the app already has a
deliberate SR architecture (hidden aria-live region + `_announce()` at
every async completion — index.html:18, app.js:591/795/1124/1226/1632/
1695@c6e0437) — and three likely gaps: no keyboard alternative to bullet
drag-reorder; follow-up-question arrival auto-scrolls but may not move
focus; preview-iframe navigability unknown.

**R2-12 — check-class completeness (owner push):**

> but checks for things like back arrow functionality, all elements being
> appropriately named, labeled, etc. tab ordering proper...

Reviewer mapped the classes: naming/labeling = widened axe + a strict
non-placeholder accessible-name assertion (axe alone under-tests names);
tab ordering = NOT checkable by axe — registry-driven keyboard traversal
asserting focus order per panel (ui_pages/ carries expected order); back
arrow = behavioral: code check confirmed ZERO History API usage in app.js
@c6e0437 (browser Back exits the SPA and discards wizard state; arc defers
wizard back-nav to v1.0.8 as polish — severity re-rated by this review).

**R2-12 — RESOLUTION: owner answered "agreed."**

The locked package (soft-commitments posture): machine-checked taxonomy in
CI, free forever — names/labels (axe + strict assertion), tab order
(registry-driven traversal), keyboard completeness (every action reachable
incl. a reorder alternative, no traps, Escape/focus-return), focus on
dynamic content, live-region announcements at every async completion,
back/history behavior, reflow/zoom, contrast — plus ONE bounded deep NVDA
walkthrough pre-public (one-time, v1.0.7 hardening; opportunistic passes
after major UI changes); ACCESSIBILITY.md as an honest status page (SR
feedback privileged; no conformance claim, no tag gate, no recurring
manual-audit promise); badge set filtered to machine-run measures
(Scorecard, REUSE lint, Dependabot + lockfile, egress test) + one-time PVR
setup with SECURITY.md's 5-day promise softened to best-effort; OpenSSF
Best Practices optional/later. Estimated one-time cost ~2–3 days of agent
work; zero recurring owner obligation. Diagnostics in scope (power-user
surface, R2-12.2).

## Assessment leads (carried to Phase 3)

- **AL-1 (domain 5):** owner-reported significant reduction in suggested
  bullets — suspected over-suppression from grounding tightening (R2-4.4).
- **AL-2 (domain 3):** bullet drag-reorder appears keyboard-inaccessible —
  drag affordances in style.css:2188 with no reorder keydown path found in
  app.js @c6e0437 (WCAG 2.1.1 candidate on a core feature).
- **AL-3 (domain 3):** zero History API usage in app.js — browser Back
  exits the app and discards expensive wizard state; cheap interim =
  beforeunload guard; real fix = arc's v1.0.8 back-nav item, severity
  re-rated (a11y + data loss, not polish).
- **AL-4 (domain 6):** CONFIRMED violation of the no-CDN promise
  (vision.md L89-93, SECURITY.md): dashboard/templates/dashboard.html:15
  loads Chart.js 4.4.0 from cdn.jsdelivr.net at runtime on every
  /_dashboard open (SRI-pinned, but real third-party egress). Fix: vendor
  into static/vendor/ like paged.polyfill.js.
- **AL-5 (domains 2/6):** scraper egress class is DEAD CODE @c6e0437 —
  scraper.py:46 has no runtime caller (tests only); SECURITY.md/vision
  document egress the app cannot produce. Decide: rewire or remove; fix
  docs. Related: jd_url is stored metadata, NEVER fetched — the
  SECURITY.md "pasted-JD URL fetch" class does not exist in code.
- **AL-6 (domain 6):** eval-grounding scorers download ~3.2GB from
  huggingface.co on first use, triggerable from localhost app routes
  (app.py:6261/6465/~6671 @c6e0437); opt-in extras, degrades gracefully —
  but fits no documented egress class; needs an explicit opt-in carve-out
  or offline-mode + pre-seeded cache.
- **AL-7 (domain 7):** egress documentation drift — owner's spoken
  enumeration ("only traffic is to the llm provider") is closer to code
  truth than SECURITY.md's three-class list; vision/README/SECURITY
  disagree with each other AND with code. One canonical enumeration
  needed (charter C-2 carries the draft).

## Post-charter rulings (owner, 2026-06-12)

**AL-4 (Chart.js CDN):** owner asked whether a fix is included → review is
witness-only; fix delivered as an early prescription scheduled for v1.0.6
(vendor `chart.umd.min.js` into `static/vendor/`).

**AL-5/AL-7 (scraper + jd_url):**

> we don't have a JD url option anywhere. we only paste JDs and we should
> be scraping linkedin and website if provided. it sounds like those are
> now broken and need to be fixed. that sounds like a mess around the
> links. thank you for sorting. please be sure those are scheduled in
> 1.0.6

Ruling: the profile/website scrape is a REGRESSION (should work when URLs
are provided) — re-wire scheduled v1.0.6. No JD-URL feature exists or is
wanted; JDs are always pasted; SECURITY.md/vision/README corrected to
match. Charter C-2(iii)/(iv) resolved.

**AL-6 (HF model downloads):**

> a super-user tuning their prompts makes that download, yes. we should
> bundle the tools that must be installed for different systems (tuning
> and the hugging face models, dev work and chromium). things that a user
> never needs to do, they shouldn't have to see. then progressive
> documentation of tool install for various systems, threaded for
> completeness.

Ruling: sanctioned power-user opt-in egress. New design principle —
**per-system tool bundling with progressive disclosure**: capabilities
requiring extra installs are packaged per system (tuning → grounding-
scorer models; dev → Chromium; …), invisible to users who never enter
that system, with progressive, threaded install documentation. Charter
C-2(ii) resolved; becomes charter D-6 + feeds domain 7 and the Sprint 6.5
install-guide work.

**Posture directive (governs the whole charter and all prescriptions):**

> let's step back now from hard commits. this is a single dev project and
> only one of many. reflect on all of this and make soft commits and best
> efforts. and what we do to try to do that. and be transparent about it.
> this is a personal project that i hope helps others, but i don't want it
> to become my life due to over-zealous commitments. Do our best, willing
> to accept feedback and help.

Resolution: **best effort + transparency, not contractual commitments.**
No SLAs, no per-release human-labor promises, no claims that create
obligations. Machine-enforced gates (CI) are fine — they cost nothing
recurring; human-promise measures get "best effort" wording. Existing doc
promises that violate this (e.g., SECURITY.md's 5-business-day response)
get softened → prescription.

## Signals — Round 2 continued additions

- S21: **Soft-commitments posture** — personal project, one of many; best
  effort + transparency; accepts feedback and help; must not become the
  owner's life. Governs all external measures and doc promises.
- S22: **Power-user continuum** — user → power-user → dev is one audience
  spectrum; tuning/annotation are power-user capabilities, not dev-only.
- S23: **"Local and yours"** replaces person-count identity language; the
  values are trust, user control, user capability; household sharing is
  in-model.
- S24 *(interviewer synthesis, pending owner confirmation in charter)*:
  **falsifiable-absolutes principle** — categorical claims only where a
  test can enforce them by construction (egress, module boundary);
  effort-language wherever a claim depends on LLM behavior.
