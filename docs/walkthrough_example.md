# A worked example — Priya applies to Platform

> **Purpose:** one synthetic candidate, one synthetic job
> description, walked through all six wizard steps with the
> actual decisions made at each one. Concrete companion to the
> abstract [`docs/walkthrough.md`](walkthrough.md).
> **Audience:** humans reading the walkthrough who want to see
> what a real run feels like before opening the app; future
> contributors wanting a fixed reference example to compare
> against.
> **Authoritative for:** nothing — this is a teaching artifact.
> The canonical step definitions live in
> [`docs/walkthrough.md`](walkthrough.md); the canonical pipeline
> behavior lives in [`docs/architecture.md`](architecture.md).

Acronyms used (same as the walkthrough): **JD** = job description;
**LLM** = large language model (Anthropic's Claude); **ATS** =
applicant tracking system.

---

## The candidate

**Priya Sharma**, a senior backend engineer with eight years of
experience. Her corpus has three experiences:

| Company | Tenure | Level | Bullets |
|---|---|---|---|
| Helix Logistics (current) | 3 years | Senior | 9 bullets |
| Northwind Foods | 4 years | Mid | 8 bullets |
| Carver Robotics | 2 years | Junior | 6 bullets |

Her bullets cover Python, Postgres, AWS, distributed systems,
incident response, and mentorship. **One bullet at Helix mentions
Kafka in passing** ("Helped migrate the order-event pipeline off
SQS to Kafka") but doesn't say anything about scale or her role
in the migration. **Nothing in any bullet says she led the
migration or grew a team** — those facts are true but never made
it onto a résumé.

She has two summary variants in her corpus:

1. *Technical-depth* — "Senior backend engineer with deep
   expertise in distributed systems and event-driven architecture."
2. *Cross-functional* — "Backend engineer who partners with
   product, data, and SRE to ship reliable platforms at scale."

---

## The job

> **Senior Backend Engineer, Platform — Vertica Logistics**
>
> We're hiring a senior IC to own the platform that powers our
> real-time shipment tracking and routing engine. You'll work in
> Python on a Postgres + AWS stack, with heavy use of Kafka for
> our event backbone. Comfort with Kafka topic design, partition
> strategy, and consumer-lag debugging is essential. You'll
> partner with our SRE and data teams, lead architectural
> reviews, and mentor a team of 6 mid- and junior-level engineers
> on the platform group. We need someone who has led migrations
> of similar scope — moving production systems off legacy queues
> onto Kafka, refactoring monolithic services into event-driven
> ones. Bonus: Kubernetes experience, prior work on logistics or
> supply-chain platforms.
> ... (full posting ~400 words; Kafka is mentioned six times)

**The ATS tell:** Kafka appears six times in the JD body. A
human reading this knows Kafka is the dealbreaker keyword. The
ATS will look for it too.

**The scope claim that needs corroboration:** "lead a team of 6
engineers." Priya does mentor and run architecture reviews, but
her current title doesn't say "manager" and her bullets don't
mention team size.

---

## Setup — import the corpus

Priya opens the **Career Corpus** tab and clicks **+ IMPORT
LEGACY**, uploading her existing `priya_master.docx`.

- **Cost:** ~$0.02 (one Haiku 4.5 call to `extract_experiences()`)
- **Time:** ~10 seconds.

The parsed experience list comes back cleanly. She spot-checks
the bullet count per experience, opens the Helix card, and sees
the Kafka bullet rendered. No edits needed.

> **Lesson:** the corpus is one-time work. The same import will
> power every future application Priya runs through sartor.

---

## Step 1 — Job + Analyze

Priya pastes the Vertica JD into the textarea and clicks
**Analyze**.

- **Cost:** ~$0.04 (one Sonnet 4.6 call to `analyze()`)
- **Time:** ~45 seconds. Long enough to make coffee.

The analysis comes back with three things she pays attention to:

1. **Skill match — strong:** Python ✓, Postgres ✓, AWS ✓,
   distributed systems ✓, mentorship ✓.
2. **Skill match — weak:** Kafka flagged as "mentioned six times
   in the JD; one passing mention in your corpus." Kubernetes
   noted as nice-to-have but absent from her corpus entirely.
3. **Gap — real:** "Team leadership scope is not explicitly
   documented in your master résumé. The JD asks for someone
   who has led a team of 6+; your bullets describe mentorship
   and architecture review but never put a number on it."

> **Lesson:** the gaps section is a *signal*, not a verdict.
> Some gaps are real-but-undocumented (Kafka, team scope); others
> are genuinely absent (Kubernetes — Priya hasn't touched it).
> The first kind goes to Clarify; the second gets left alone.

---

## Gate #1 — enter Clarify

Priya decides:

- **Kubernetes gap?** Real and unfillable — she hasn't used it.
  Don't enter Clarify to fake it.
- **Kafka mention?** Real and underdocumented. Worth Clarify.
- **Team leadership scope?** Real and underdocumented. Worth
  Clarify.

She clicks **Begin Clarify**.

---

## Step 2 — Clarify

The LLM generates four questions. Priya reads them carefully:

1. *"Your Helix bullet mentions migrating off SQS to Kafka. What
   was your specific role — designer, lead implementer,
   reviewer? What was the scale (events/sec, topics, consumers)?
   How long did the migration take?"*
2. *"You describe mentoring junior engineers across multiple
   roles. Have you ever had direct reports, or sat in on
   hiring decisions, or owned a team's roadmap? Roughly how many
   engineers have looked to you as their technical lead at any
   one time?"*
3. *"The JD emphasizes Kafka topic design + partition strategy
   + consumer-lag debugging. Have you done any of these in
   production, even if your bullet doesn't break it out?"*
4. *"The JD mentions Kubernetes as a bonus. Have you touched it
   in any capacity — even adjacent (helm charts, kubectl for
   debugging, etc.)?"*

Priya answers three with specifics and skips the fourth:

- **Q1:** "I was lead implementer. Designed the topic + partition
  scheme (12 topics, 60 partitions on the busiest one, ~8k
  events/sec at peak). Migration took ~6 months including the
  dual-write/cutover phase. Postmortem on initial consumer-lag
  spike led to our current per-consumer lag dashboarding."
- **Q2:** "Currently 6 engineers on the platform team look to me
  as their tech lead — three I helped hire. I own our quarterly
  roadmap and run weekly architecture reviews. No direct reports
  in the HR sense (we're flat) but I'm the de facto lead."
- **Q3:** "Yes — topic design and lag debugging extensively. I
  haven't done multi-region replication or schema-registry work
  beyond evaluating Confluent."
- **Q4:** *(skipped — she's never touched Kubernetes meaningfully)*

She clicks **Submit clarifications**. Cost: ~$0.03 for the
questions; submitting is free.

> **Lesson:** specifics in, specifics out. The numbers she gave
> (60 partitions, 8k events/sec, 6 engineers, 6-month migration)
> will appear nearly verbatim in Step 5's bullets. The blank
> answer doesn't degrade anything — it just means Step 5 won't
> claim Kubernetes.

---

## Step 3 — Compose

The Compose step shows Priya's three experience cards, each with
existing bullets plus LLM-recommended bullets pulled from her
Clarify answers.

**On the Helix card** (most relevant to this JD), she:

- **Pins** her existing Kafka-adjacent bullet. It's the one
  truthful claim she had pre-Clarify; pinning guarantees it
  survives Step 5.
- **Accepts (with edit)** an LLM-proposed bullet:
  > "Led migration of order-event pipeline from AWS SQS to
  > Kafka, designing topic/partition scheme (12 topics, 60
  > partitions, ~8k events/sec peak) and consumer-lag dashboards
  > that became the platform team's standard."
  She tightens "became the platform team's standard" to "still
  in use across the platform group" because the former feels
  self-congratulatory.
- **Accepts** an LLM-proposed bullet about her tech-lead role:
  > "Technical lead for 6-engineer platform team; own quarterly
  > roadmap, weekly architecture reviews, and three hires made
  > under my recommendation."
- **Excludes** her old "Refactored CI/CD scripts in Bash" bullet.
  Not relevant to this JD.

**On the Northwind card** (mid-career, mostly Postgres work), she
leaves most bullets unmarked. The LLM-recommended Postgres-tuning
bullet looks good — she accepts it as-is.

**On the Carver card** (junior years, robotics-adjacent), she
excludes the two clearly-irrelevant bullets about ROS
(Robot Operating System) and CAD pipelines. The remaining four
bullets she leaves unmarked.

**Summary variant:** the LLM proposed a third variant tuned to
this JD:

> *"Senior backend engineer with eight years building event-driven
> platforms; lead architect on a multi-quarter Kafka migration;
> technical lead for a 6-engineer platform team."*

She picks it — it's honest, and it leads with the two pieces the
JD cares most about.

- **Cost:** ~$0.03 total across `recommend_bullets()` (3 cards),
  `recommend_summaries()` (1 call), and `critique_proposal()` on
  each accepted proposal (3 calls × ~$0.005 = $0.015).

> **Lesson:** pinning is a commitment; excluding is a commitment;
> "leave unmarked" is a third valid choice that says "let the
> LLM decide." Priya used all three.

---

## Step 4 — Template

Priya clicks **Modern**. The preview re-renders to two pages, no
LLM call.

The preview shows:

- Page 1: header + new summary + Helix card (4 bullets including
  the two new ones) + Northwind card (5 bullets).
- Page 2: Carver card (4 bullets), education, skills.

Two pages is fine for a senior IC role. If it had been four
pages, she'd go back to Compose and exclude more.

She considers Tech (serif, very engineering-coded) but Vertica's
JD reads cross-functional ("partner with SRE and data teams") —
Modern's blue-accent header feels more right.

> **Lesson:** template choice is a signal. Page count is a
> sanity check on Compose.

---

## Step 5 — Generate

Priya selects `.docx` and clicks **Generate**.

- **Cost:** ~$0.10 (Sonnet 4.6 call to `generate()`)
- **Time:** ~50 seconds.

The preview shows the rendered résumé. She watches the wait;
it's the same kind of pause as Step 1's analyze. The
`grounding_overlap` metric ticks in at the bottom: 0.96
(high — almost every claim in the output traces directly to
her corpus + clarifications).

> **Lesson:** the wait is real and earned — Sonnet is writing,
> not picking. The grounding number is her fabrication detector;
> 0.96 is healthy.

---

## Gate #2 — refine vs. approve

Priya reads the generated résumé carefully. She spot-checks five
specific claims:

1. "60 partitions, ~8k events/sec peak" — traces to Q1 answer. ✓
2. "Technical lead for a 6-engineer platform team" — traces to
   Q2 answer. ✓
3. "Quarterly roadmap ownership" — traces to Q2 answer. ✓
4. "Three hires made under my recommendation" — traces to Q2
   answer. ✓
5. "Consumer-lag dashboards still in use across the platform
   group" — traces to Q1 answer + her tightening edit. ✓

Every claim grounds. The summary feels honest. She declines to
refine and clicks **Download**.

`vertica_priya_2026-05-26.docx` lands in
`output/priya/resume_2026-05-26-1430.docx`. The matching
`context_2026-05-26-1430.json` lands next to it.

> **Lesson:** read it the way an interviewer would. Can you
> defend every claim? Priya can.

---

## Optional — cover letter

The Vertica posting says "no cover letter required." Priya skips
it. Total cost: ~$0.22. Total time: ~12 minutes including
reading and decisions.

---

## What this run cost

| Step | Call | Model | Approx |
|---|---|---|---|
| Setup | `extract_experiences()` | Haiku 4.5 | $0.02 |
| Step 1 | `analyze()` | Sonnet 4.6 | $0.04 |
| Step 2 | `clarify()` | Sonnet 4.6 | $0.03 |
| Step 3 | `recommend_bullets()` × 3, `recommend_summaries()`, `critique_proposal()` × 3 | Haiku 4.5 | $0.03 |
| Step 4 | — | — | $0 |
| Step 5 | `generate()` | Sonnet 4.6 | $0.10 |
| Step 6 | — (approved without refine) | — | $0 |
| **Total** | | | **~$0.22** |

This is the "résumé + clarify" band from
[Cost guidance](../README.md#cost) — squarely in the typical-use
range.

---

## What this example does NOT cover

This worked example shows a clean, happy path. Real applications
sometimes need:

- **A refine pass at Gate #2** (when a claim sounds off and you
  type a natural-language fix). Adds ~$0.10 + another ~50s.
- **A re-Clarify round** (when the first answers expose new
  specifics worth probing). Adds ~$0.03.
- **A genuine "skip Clarify"** (when Step 1 analysis surfaces
  no real gaps — the corpus already covered the JD). Saves
  ~$0.03 and ~30s.
- **A cover-letter generation.** Adds ~$0.05 and ~30s.

The pattern stays the same: every action writes a new
`context_*.json`, nothing is overwritten, and the audit trail
under `output/<user>/` is your record of how each generated
document came to exist.
