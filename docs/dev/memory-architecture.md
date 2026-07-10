# Memory architecture — the `recall/` substrate + the avatar

> **Purpose:** the design for sartor's **Memory** function as a first-class,
> modular subsystem — a reusable retrieval/memory substrate (`recall/`) that
> *feeds* a small-LLM (Haiku) "avatar" which answers user + dev questions from
> the system's own knowledge, with citations.
> **Audience:** agents designing or building the v1.0.7 `feat/doc-assistant`,
> `design/self-documenting-loop`, and WS-4b `wiki/cold-ingest-code` branches —
> and any future project that wants to reuse the substrate.
> **Status:** **Stage 0 + Stage 1 SHIPPED; deeper tiers still design.** The six
> framing decisions below are *decided*. **Stage 0** (the `recall/` skeleton) landed
> Sprint 7.4 (`feat/recall-skeleton`); **Stage 1** (the doc-grounded assistant — S1
> `WikiSource` + S2 `GitGrepSource` + S5-P1 `SessionSource` + the Haiku avatar + the
> user/dev toggle + the SSE chat panel) landed Sprint 7.5 (`feat/doc-assistant`). The
> **Stage 2 vector tier (S3)** is 7.6 (eval-gated); **S4 structure** + **S5 P2–P4** stay
> design only. Read the per-stage notes below for what is built vs. held.
> **Authoritative for:** the tier model, the two cross-cutting planes, the
> hybrid-retrieval decision, and the **reuse/extraction contract**. Defers to
> [`../system-model.md`](../system-model.md) (the seven-function model),
> [`../wiki/pages/llm-wiki-design.md`](../wiki/pages/llm-wiki-design.md)
> (git-as-engine + the wiki query op), and [`RELEASE_ARC.md`](RELEASE_ARC.md)
> §Phase 4.5 / §4.7 for sequencing.
> **Provenance:** distilled from the 2026-06-09 evaluation of Midas-style
> local agent memory (no-LLM ingest, source-turn recall, importance-over-
> recency forgetting) against sartor's needs.

---

## Thesis (four reframes that set the shape)

1. **Retrieval is a *feed*, not an end.** The output of this whole machine is an
   *assembled, bounded, cited context block* for one Haiku turn — never the
   final answer. The small model reads + phrases; trust lives in the
   deterministic layer below it.
2. **Two memory *families*, not one.**
   - **Self-knowledge memory** — what the system knows *about itself*: the
     committed docs/wiki + the code at HEAD.
   - **Interaction memory** — what the avatar remembers *about you*: prior
     turns / sessions / confirmations. This is where the actual Midas pattern
     (no-LLM turn ingest, source-turn recall, importance-over-recency
     forgetting) fits — *not* the corpus.
3. **This is the project's *Memory* function, made first-class.** Per
   [`../system-model.md`](../system-model.md) (Substrate · Production ·
   Evaluation · Operation · **Memory** · Regulation · Governance), we are
   building out Memory as a module; the avatar is an **Operation** surface that
   consumes it. The substrate depends only *inward* (Substrate: git / fs / db),
   never on the avatar or `app.py`.
4. **The avatar is the system's self-knowledge rendered conversational** —
   support agent **+** avatar of the system **+** local guide. A guide is
   grounded in *place* (git@HEAD, zero egress) and *relationship* (interaction
   memory): it knows the terrain and it remembers you.

---

## The stack

```
            ┌─────────────────────────────────────────────────┐
  user ───▶ │  AVATAR   Haiku · persona-by-mode · cites        │  Operation
            └────────────────▲────────────────────────────────┘  (the only LLM)
                             │  assembled · cited · budgeted context  ← THE FEED
            ┌────────────────┴────────────────────────────────┐
            │  ASSEMBLE    token-budget pack, wiki-synthesis-first        │
            ├──────────────────────────────────────────────────┤
            │  RETRIEVE    candidate pool → fuse(RRF) → rerank → top-k    │ ◀─ POLICY plane
            ├──────────────────────────────────────────────────┤   audience scope +
            │  SOURCES (tiers; one common Source interface)     │   progressive disclosure
            │  S1 wiki   S2 git   S3 vector   S4 struct   S5 session     │
            ├──────────────────────────────────────────────────┤ ◀─ PROVENANCE plane
            │  CHUNK + INDEX   deterministic · refresh on .last_ingest_sha│  every Unit carries
            └────────────────▲────────────────────────────────┘   tier·path:line·audience·sha
            ┌────────────────┴────────────────────────────────┐
            │  SUBSTRATE    git@HEAD · docs/wiki · db · fs      │  Substrate
            └─────────────────────────────────────────────────┘
```

**Three module zones, with the reuse seam between them:**

- **`recall/` — the reusable substrate (project-agnostic).** Sources, chunkers,
  indices, retrieval/fusion, assembly, the two planes. Knows nothing about
  résumés. Public surface: `Unit(text, tier, source_id, path|line|page,
  audience, sha, score)`, `Source.refresh(since_sha) / search(query, scope)`,
  `Scope`, `Context`, and one entry point `recall.assemble(query, scope) -> Context`.
- **Project wiring (sartor config).** Source roots (`docs/wiki`, repo HEAD,
  `db/`), the **path→audience** tag rules, enabled tiers, the persona, and the
  `.last_ingest_sha` binding. This is all that changes to point the substrate at
  a different project.
- **The avatar (sartor Operation surface).** A Flask SSE chat route + the
  Haiku call: question + mode → `recall.assemble()` → prompt(persona, context)
  → cited answer. The **only** LLM in the stack — `recall/` is entirely
  deterministic (even the embedder is a static lookup), so the P1 boundary holds
  cleanly: avatar ≈ [`../../analyzer.py`](../../analyzer.py),
  `recall/` ≈ [`../../hardening.py`](../../hardening.py).

---

## Tiers, and how they cover the git-gives / git-doesn't matrix

| Need | Tier that owns it | Cost |
|---|---|---|
| Corpus + citation (`path:line`) | **S2 git** — files on disk, native citation target | free |
| Lexical search (exact) | **S2 `git grep`** | free |
| Map | **S2** `ls-files`/tree **+ S1** wiki `index.md` | free |
| Freshness / provenance | **S2** diff vs `.last_ingest_sha` + `blame` → drives *all* index refresh | free |
| **Vocabulary bridge** | **S1 wiki synthesis** (answer-shaped prose) primary; **S3 vector** for code where the wiki hasn't paraphrased | S1 curated · S3 deferred |
| **Structure** (defs/uses, "what calls X") | **S4 structure index** — `tree-sitter`/`ctags`/`ast` symbol graph | deferred tier |
| **Chunking** (functions/sections, not whole files) | the **Chunk layer** — deterministic, per-filetype | free |

Plus the family the matrix didn't have:

- **S5 — interaction memory.** The avatar's memory of *you*. Same `Source`
  interface, so it enters retrieval/assembly identically to corpus memory: the
  avatar's context becomes "what I know about the system" **+** "what I remember
  about you," both cited, both budgeted. This is the **one genuinely personal
  family** — local, gitignored, user-clearable, never egress.

---

## The two cross-cutting planes (what makes it a *system*, not a pipeline)

- **Provenance / grounding plane.** Every `Unit` is stamped with
  `(tier, source_id, path:line|page, audience, sha)`. Retrieval returns *source
  units*, never rewritten facts; assembly preserves the stamps; the avatar must
  cite them. This single spine unifies Midas source-recall + the wiki's
  `[[citations]]` + the product's own grounding check — a guide *shows you the
  landmark*, it doesn't invent directions.
- **Access / disclosure plane.** An orthogonal filter, not a source:
  - **audience tag** (path-derived: `user` | `dev`) on every Unit;
  - a **user/dev toggle** sets the allowed scope (off → user tier; on → + code
    spans, vectors, structure, tuning, dev docs);
  - **progressive disclosure** is **model-detected**: the avatar judges when a
    question warrants depth and *proposes* going deeper — but **detected depth
    proposes; the access plane disposes** (it only crosses into dev-tier content
    if the toggle/permission allows; never an over-disclosure backdoor);
  - forward-looking: the instant this is multi-user, this plane *is* an
    authorization boundary (provenance-tagging of memories — observation vs
    user-confirmed — lands here too); even local it must never surface
    gitignored PII. Designed as a plane now → a policy change later, not a
    re-architecture.

---

## One turn's journey

`Q + mode + session` → `policy.scope()` sets allowed tiers/tags →
`retrieve()` pulls a bounded pool from S1 (map + vocabulary), S2 (`git grep` →
exact `path:line`), S3 (semantic, if enabled), S4/S5 (later) → fuse (RRF) +
dedup + top-k, each cited → `assemble()` packs wiki-synthesis-first with source
spans attached, within a fixed token budget → **avatar** answers in-persona with
`[[page]]` / `path:line` citations + a model-detected "want the dev detail?"
offer → (later) `session.observe(turn)` ingests the exchange, no LLM.

---

## Resolved design decisions (2026-06-09)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Hybrid retrieval** — prebuilt base + agentic drill-down; **lightweight base at Stage 1** (wiki-map/lexical + `git grep`, no vectors) | Deterministic, citeable, evaluable, *and* it builds the reusable asset; agentic-only under-delivers on the vocabulary gap + citations and builds nothing reusable; pure-prebuilt needs more upfront substrate than the cheap tiers require. |
| 2 | **Author the `audience:` tag once, where the boundary is already being drawn** — add the convention to the wiki SCHEMA **before** the 6.5 education sweep; blanket path-rules for code/`docs/dev`/`evals` (dev) | The tag the access plane needs is the same boundary **governance-extraction** and the 6.5 user/dev split already draw. Author once → three beneficiaries. The memory system gives the doc-restructuring a *consumer* that says *where* to draw the line (where the avatar must refuse). |
| 3 | **Fold structure metadata into the chunker first**; stand up a separate **S4** symbol-index tier only if call-graph navigation is demanded | ~70% of the value (structure-aware chunks improve S3 + let the avatar say *where* code is) at a fraction of the cost; eval-gated. |
| 4 | **Model-detected** progressive disclosure, **gated by the access plane** | The avatar guides (proposes depth) without becoming an over-disclosure backdoor (the plane authorizes). |
| 5 | **Interaction memory (S5) progressively** — P1 (session buffer) in v1.0.7 Stage 1; **P2–P4 gated on the retention/forgetting policy** (open) | A local guide remembers you. Each step is the same `Source` interface, so it enters the existing fusion without re-architecting. |
| 6 | **Modular `recall/` in-repo from day one + a documented extraction contract**; physical extraction deferred to second-use | Don't pre-abstract; *do* hold a clean seam and make it a contract future agents build against (see below). |

### S5 staircase (the progressive build for interaction memory)

- **P1 — session buffer.** Remember the current conversation's turns. Trivial; ships with the assistant.
- **P2 — durable session recall.** Persist past sessions; retrieve relevant prior turns via `recall` (lexical, then vector). Source-turn recall (Midas's auditable form).
- **P3 — importance + forgetting.** The full Midas pattern: no-LLM importance scoring, keep the important, let recency fade.
- **P4 — provenance-tagged memory.** Tag each memory *observation* vs *user-confirmed*, so the avatar knows how much to trust it (and whether it may drive an action).

---

## Staged, eval-gated build

- **Stage 0 — the skeleton (free, do first).** Define `Unit` / `Source` / `Scope`
  / `Context` + the two planes. *Getting these seams right is the "reusable,
  prepared to develop further" deliverable* — more important than any one tier.
- **Stage 1 — free tiers ship the assistant. DONE 2026-06-16 (`feat/doc-assistant`,
  7.5).** S1 wiki + S2 `git grep` + assemble + the avatar with the user/dev toggle +
  model-detected disclosure + S5 P1 (session buffer). **Zero new deps.** The concrete
  tiers live in `recall/sources/` (generic + injected — roots/audience passed from the
  wiring layer, kept project-agnostic by `test_recall_sources_no_hardcoded_roots`); the
  avatar (`analyzer.avatar_answer_streaming`, its own `AVATAR_PROMPT_VERSION`) honors C-6;
  the SSE route is `blueprints/assistant.py` (`POST /api/assistant/ask`) + a collapsible
  in-app panel. **Decisions (owner-confirmed):** avatar in `analyzer.py` (D1=A);
  sources parameterized in `recall/sources/` (D2=Y); minimal in-shell UI panel.
- **Stage 2 — eval-gated semantics. DONE 2026-06-16 (`feat/doc-assistant-vector`, 7.6).**
  S3 vector via **`model2vec` static embeddings + a rebuildable numpy `.npy` sidecar** (the
  lightest path: numpy + tokenizers + a ~30 MB static table — no onnxruntime, no torch;
  escalate to `fastembed`/bge only if eval shows static isn't enough). Shipped as
  `recall.VectorSource` (brute-force cosine; the embedder is *injected* so `recall/` never
  imports `model2vec` — embedder-agnostic + extractable); the wiring + the one-time model
  download + the build (`scripts/build_vector_index.py`) live in the project layer. The
  rebuild is **incremental ($0 on unchanged)** via per-chunk content-hash reuse (subsumes
  the `.last_ingest_sha` diff, robust to a stale checkpoint). **The eval gate was a
  deliberate OWNER OVERRIDE** (2026-06-09 re-cut made it eval-gated/conditional; built ahead
  of the formal v1.0.8 labeled eval because the landed Stage-1 assistant tested *too literal
  / lacking semantic flexibility*; a probe corroborates — `evals/TUNING_LOG.md` — and the
  judge-scored before/after eval is owed at v1.0.8). The light embedder keeps the
  public-release dependency footprint acceptable. **`numpy` + `model2vec` are now hard deps**
  (the `recall/sources/` stdlib boundary test relaxed to admit `numpy` only).
- **Stage 3 — depth.** S4 structure index ("what calls X") — **same eval-gated, in-epic
  treatment as Stage 2** (pull into v1.0.7 if dev call-graph questions justify it). S5
  **P2–P4** (durable cross-session memory → forgetting → provenance tags) is **HELD** —
  eligible to pull into v1.0.7 *only once its retention / forgetting / "clear my data"
  policy is resolved* (the open question below); until then it stays post-v1.1.0. The
  interfaces already hold its slot. (S5 **P1** session buffer ships in Stage 1.)

> **Storage note.** The vector index is *derived + rebuildable* → it belongs in
> a **sidecar**, NOT in `db/resume.sqlite` (which carries the user's real corpus
> PII and would inherit migrations). 7.6 shipped this as a gitignored
> `db/vector_index/` directory — `embeddings.npy` (the float32 matrix) + `chunks.json`
> (parallel metadata) + the saved model — with brute-force cosine (fine at the current
> ~3k chunks). Reach for a BLOB table or the `sqlite-vec` extension only if you outgrow
> brute force or want SQL-native KNN.

---

## Reuse boundary / extraction contract

The modularity is a **design invariant**, documented here as a contract future
agents build against (the way [`../../AGENTS.md`](../../AGENTS.md) governs):

- **Public surface:** one entry point `recall.assemble(query, scope) -> Context`;
  the `Source` / `Unit` / `Scope` / `Context` types are the whole API. Project
  specifics are injected via config, never imported by `recall/`.
- **Dependency rule (hard):** `recall/` may import stdlib + light libs, **never**
  [`../../app.py`](../../app.py), [`../../analyzer.py`](../../analyzer.py), or the
  sartor DB models. This mirrors the P1 determinism boundary the repo already
  enforces with hooks. **Built** (Sprint 7.4): a static AST-walk test —
  [`../../tests/test_recall_boundary.py`](../../tests/test_recall_boundary.py) —
  fails the build on any forbidden import (`app`/`analyzer`/`db`/`flask`/`anthropic`,
  including lazy/`TYPE_CHECKING` imports) and, for `recall/sources/`, on any
  hardcoded sartor-specific path/symbol literal (`test_recall_sources_no_hardcoded_roots`)
  — the boundary is enforced by construction, not merely a hook-mirrored convention.
- **Extraction readiness:** lifting `recall/` into a standalone package should be
  **packaging only** — *if* the boundary above stays clean. Every PR touching the
  avatar or memory must respect the seam; that discipline is the cost of keeping
  extraction free.

---

## Still genuinely open

- Chunk granularity for code (symbol vs sliding window) + whether the structure
  metadata in #3 is enough or S4 is needed sooner.
- Exactly where the `audience:` tag is *authored* in the mixed wiki today (ties
  to **governance-extraction**'s open sub-decisions).
- The `recall/` package name (placeholder).
- S5 retention / forgetting / "clear my data" policy (privacy-sensitive) — **this is the
  gate on pulling S5 P2–P4 into v1.0.7**; until it's resolved, P2–P4 stays post-v1.1.0.

## Related

- [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.5 (WS-4b feeds S1 + owns the
  `audience:` tag) / §4.7 (`feat/doc-assistant`, `self-documenting-loop`).
- [`../wiki/pages/llm-wiki-design.md`](../wiki/pages/llm-wiki-design.md) —
  git-as-engine, the query op, the "unreliable narrator" grounding guard.
- [`../system-model.md`](../system-model.md) — the seven-function model this
  realizes the **Memory** function of.
- [`nursery.md`](nursery.md) — looser deferred ideas.
