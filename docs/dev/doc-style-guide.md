# Documentation style guide — how Sartor's docs are written

> **Purpose:** the *writing* contract for every doc in this repo — the wordmark
> rule, the no-disparagement rule, voice and tone, and claims discipline in prose.
> It is the sibling of
> [`documentation-architecture.md`](documentation-architecture.md), which governs
> how docs are **organized and published** (the L0→L3 chain, the Fumadocs
> projection, the merge=publish gate) but says nothing about how they **read**.
> **Audience:** `dev` — humans and AI agents authoring or editing any `.md` in
> this repo, plus user-facing UI copy.
> **Authoritative for:** the `sartor.` wordmark rule; the no-disparagement rule;
> the documentation voice; prose-level claims discipline. It **defers** to
> [`../governance/charter.md`](../governance/charter.md) (C-0 claims discipline
> governs on conflict) and to [`../wiki/SCHEMA.md`](../wiki/SCHEMA.md) for the
> wiki's own page contract.

---

## Context

The docs are the product's first surface — a public README, a hosted docs site, an
in-app assistant that quotes them. Two failures in July 2026 showed the writing
needed a contract of its own, not just a publishing one:

- The README opened by characterizing *other* products ("Generic AI résumé tools
  pad a history…"). The project's whole claim is that it doesn't assert what it
  can't ground — and the first sentence a reader met was an ungrounded claim about
  someone else's software.
- The public README carried a REUSE badge that rendered **`unregistered`** — a
  placeholder shipped as if it were a status.

Both are the same failure at different scales: saying more than we know. This guide
is where the prose-level version of that discipline lives.

---

## 1. The wordmark rule

**`sartor.`** — all lowercase, with the trailing period — is the **wordmark**. It
is a piece of visual identity, not a noun you can drop into a sentence.

| Context | Form | Example |
|---|---|---|
| Wordmark standing alone | `sartor.` | the logo; the app's top-bar chrome; a doc title where the name stands by itself — `# Vision — sartor.` |
| Anywhere inside prose | `Sartor` | "Sartor is a local-first app…", "Sartor's design rule", "why Sartor exists" |
| Code, paths, identifiers | as written | `sartor.py`, `meta.sartor`, `pip install sartor` |

The reason is readability: `sartor.` mid-sentence reads as a sentence that ended
early, and it collides with the following period when the name lands at the end of
one. Headings may keep the wordmark where the name stands alone; a heading that
reads as a phrase takes `Sartor` like any other prose.

*Status:* the user-facing doc surface (README · vision · install · walkthrough ·
architecture · system-model · PRODUCT_SHAPE · CONTRIBUTING · SECURITY ·
ACCESSIBILITY · AGENTS · CLAUDE) was swept to this rule on 2026-07-13. The
`docs/wiki/` pages and the `docs/dev/reviews/` archive still carry in-sentence
wordmarks — a mechanical follow-up, tracked in the carry-forward ledger; fold the
fix in whenever one of those files is next edited.

## 2. Describe only what Sartor does and doesn't do

**Never characterize other products, categories, or "generic tools"** — favorably
or unfavorably. Not by name, not by implication.

This is not only manners. A claim about a competitor is a claim we cannot ground,
made in a project whose central discipline is that ungrounded claims don't ship
(charter **C-0**). It also ages badly: the category moves, and the swipe stays in
the README.

State the **problem from the candidate's side**, then what Sartor does about it.

> **Don't:** Generic AI résumé tools pad a history with claims that fall apart in
> an interview, and emit formats that ATS choke on. Sartor is the opposite bet.
>
> **Do:** A padded history makes claims that fall apart in an interview. A résumé
> an automated screener (ATS) can't read never reaches a human. Sartor addresses
> both: it only asserts what it can trace to the candidate's real history, and its
> bundled templates are ATS-safe by default.

The "Do" version says strictly more about *our* product, and nothing we can't back.

## 3. Voice and tone

The house voice is a **knowledgeable colleague explaining their own work**:
precise, plain, unhurried, never selling. Two external references anchor it —
[Google's developer-documentation style guide (tone and content)](https://developers.google.com/style/tone)
and [Apple's Human Interface Guidelines on writing](https://developer.apple.com/design/human-interface-guidelines/writing).

**Do**

- **Lead with the benefit, then the action** (Apple). "To keep your data local, run
  it with `-p 127.0.0.1:5000`" — not the reverse order.
- **Be concise, and cut adjectives.** Adjectives and adverbs usually smuggle in an
  assumption about the reader's context.
- **Write for a global audience** — plain words, standard grammar, no idiom.
- **Read it aloud.** If you wouldn't say it to a colleague, rewrite it.
- **Define the voice once, vary the tone by context** (Apple). An error message and
  a vision doc are the same voice at different temperatures.

**Don't**

- **"Simply", "just", "easy", "obviously".** They tell a stuck reader the failure is
  theirs. This applies to UI copy and error messages above all.
- **Buzzwords, jargon-before-definition, pop-culture references, exclamation marks.**
  Expand an acronym on first use in each doc (ATS, SSE, JD).
- **Hype.** "Powerful", "seamless", "revolutionary" — if the thing is good, show the
  mechanism instead.
- **Figurative or ableist phrasing** ("choke on", "cripple", "sanity check", "blind
  to"). Say the literal thing.

## 4. Claims discipline in prose

The charter's **C-0** applies to sentences, not just code:

- **State what's verified, what's partial, and what isn't built** —
  [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) is the worked example: it names the
  machine-checked taxonomy *and* the known gaps, and makes no conformance claim.
- **No aspirational present tense.** If it isn't built, don't describe it as though
  it is. Use the `DOC-STATUS` flag convention
  ([`documentation-architecture.md`](documentation-architecture.md)) to mark a doc
  as `PARTIAL` rather than quietly overstating it.
- **A badge is a claim.** A badge that renders a placeholder (`unknown`,
  `unregistered`, a 404) is a **failing badge**, not a cosmetic issue — it asserts a
  status nobody checked. Verify what a badge renders, not just that the URL is
  well-formed. Never add a badge for a status that doesn't exist yet.
- **Cite, don't restate.** Point at the canonical home rather than copying its
  content; a copy drifts, a pointer doesn't.

---

## Applying this

- Human contributors: [`CONTRIBUTING.md`](../../CONTRIBUTING.md) points here.
- AI agents: [`AGENTS.md`](../../AGENTS.md) points here — read this before writing
  docs or UI copy.
- There is **no automated gate** for voice (`ruff` can't hear tone). The wordmark
  rule and the no-disparagement rule are the two mechanically checkable parts; if
  either regresses in practice, a `scripts/` lint is the natural next step, not a
  stricter prose review.
