# Agent-coding-practices kit adoption — design + arc (captured 2026-06-23)

> **Purpose:** the settled evaluation + sequenced plan for adopting the lichen
> `agent-coding-practices-kit` (context / documentation / strict-typing practices +
> the `context-structure-review` skill) into sartor. Produced as an
> **evaluation** (no code changed); this doc is the durable record the
> implementation branches execute against, so they re-decide nothing.
> **Audience:** the owner (Robert) reviewing the plan, and any agent implementing a
> phase of it. Precedent for a captured design-doc deliverable:
> [`governance-extraction-design.md`](governance-extraction-design.md).
> **Authoritative for:** the eight adoption decisions (§3), the phase sequencing
> (§4), the temporal map onto the existing roadmap (§5), and the ratchet exit
> criterion (§6). On conflict with an older plan, this doc governs for the
> kit-adoption scope only. Decision index: [`decisions.md`](decisions.md).
> **Source of record (read-only, outside this repo):** the kit lives at
> `C:\Dev\lichen\projects\agent-coding-practices-kit\` — `markdown-for-llm-apps.md`
> (context), `doc-discipline-for-coding-agents.md` (docs),
> `strict-typing-and-style.md` (typing), and `context-structure-review/`. The
> handoff that seeded this evaluation is a Sartor-trimmed synthesis of those.

---

## 0. What this is, in one paragraph

The lichen kit is three practices — **context** (what the agent loads) → **documentation**
(what it records) → **types** (what it can't get wrong) — sharing one premise (structure,
docs, and types are *inputs to agent reliability*, not hygiene) and one method (**mechanism,
not instruction**: judgment lives in AGENTS.md/skills, the mechanizable subset lives in
blocking gates). The handoff framed Sartor as a greenfield "canary" whose AGENTS.md needs
*seeding*. It isn't: Sartor is a mature v1.0.7 repo that already practices ~60% of the kit,
often better than the kit describes (governance charter, hooks-as-mechanism, the AGENTS.md
`@import` design, the self-documenting wiki). So adoption is **reconcile + close specific
deltas + flag what's promotable to `amodal-open`** — not author-from-zero. Sartor is the
**donor**, not the blank canary.

---

## 1. The frame (canary → donor)

The kit's stated end-goal (its §5) is an adoption arc: settle the conventions on Sartor (the
"canary"), then promote them to a shared `amodal-open` location later repos inherit. The
correction this evaluation makes: for the governance philosophy, the hook model, the
`@import` instruction-file design, and the wiki doc-drift loop, **Sartor already holds the
best-in-class version** — so the shared layer is *extracted from* Sartor, and only the
genuinely-missing pieces (strict typing, request-boundary parsing, doc generation) are
*imported from* the kit. Framing chosen (Decision-framing, 2026-06-23): **implement Sartor's
deltas now + flag promotable practices as we go** (don't build the shared layer yet). The
promotable shortlist is §7.

---

## 2. Current-state survey (what's done vs the real gaps)

Verified against `main` at capture (2026-06-23). Legend: ✅ done/exceeded · 🟡 partial ·
❌ gap.

| Kit ask | Sartor today | |
|---|---|---|
| Exclude aggressively (ignore surface) | `.gitignore` covers `.venv`/caches/build/secrets/PII; pip-based, no lockfile to exclude | ✅ |
| One canonical instruction file | `AGENTS.md` canonical (168 lines) + `CLAUDE.md` (190) `@import`s it | ✅ exceeds |
| Copy-pasteable exact commands | AGENTS.md carries the ruff/mypy/pytest + eval loop (pip, not `uv`) | ✅ |
| Progressive disclosure / ≤500-line files | Instruction files small; wiki + recall embody it | ✅ |
| Permission boundaries | Six enforcing PreToolUse hooks (mechanism) | ✅ exceeds |
| Treat instructions as code / audit cadence | governance + `wiki-lint` + `compliance-witness` | ✅ exceeds |
| Doc-drift detection | wiki-freshness hook + `/wiki-self-update` | ✅ exceeds |
| "Why not what" comments | Cultural norm (D5 cite-don't-restate); not *enforced* | 🟡 |
| No commented-out code (ruff `ERA`) | `ERA` not in ruff `select` — evaluated 2026-06-23: 8/8 hits false-positive → stays warn-only per Decision 6 (§4 progress note) | 🟡 |
| Docstring coverage (ruff `D` / `interrogate`) | `D` blocks tree-wide (§6 exit); `interrogate` floor-lock gate at `fail-under = 99` (100% production baseline) | ✅ |
| Generated reference docs | none | ❌ (see Decision 2) |
| OpenAPI from Flask | none | ❌ (see Decisions 1, 2) |
| DoD checklist + PR template | `RELEASE_CHECKLIST` + AGENTS.md close-out + a rich PR template already exist | 🟡 reconcile |
| mypy `--strict` | mypy runs but is **deliberately permissive** (`ignore_missing_imports`, `follow_imports=silent`, no `disallow_untyped_defs`/`warn_unreachable`) | ❌ **big** |
| ruff `ANN`/`D`/`ERA`/`SIM`/`RUF` | only `E,W,F,I,B,UP,S` selected (`S`/bandit already on — kit omits it) | ❌ |
| Pydantic + SQLAlchemy mypy plugins | `pydantic.mypy` enabled 2026-06-23 (mypy green); SQLAlchemy plugin dropped — `db/models.py` uses 2.0 native `Mapped[]` typing, plugin deprecated/unneeded | ✅ |
| Parse at request boundary | **all ~30 body routes do raw `request.json`** across 7 blueprints | ❌ **big** |
| `pydantic-settings` config | `config.py` is a clean typed `frozen dataclass` (path injection, not env parsing) | 🟡 skip (Decision-revision) |
| `ruff format` | lints only; `ruff format --check` not wired | ❌ small |
| `context-structure-review` skill | not installed | 🟡 (Decision 5) |
| Worktree isolation / explicit staging / re-read | branch discipline + concurrent-agent-worktree practice; no `decisions/` dir | ✅ mostly |

**Structural mismatches in the handoff (revisions of record):** (1) `uv` assumption is wrong —
Sartor is pip/setuptools; translate commands (Decision 8 = out of scope). (2) greenfield
framing inverted (§1). (3) don't flatten `CLAUDE.md` to "Follow ./AGENTS.md" — the `@import`
design is better. (4) PR-template/DoD assume a PR-review workflow; Sartor merges locally —
fold DoD into existing checklists. (5) doc-drift SaaS (Dosu/DeepDocs) redundant with the wiki
loop. (6) `pydantic-settings` is low-value churn (`config.py` already typed). (7) markdown
oversized-file gate is a future-guard, not a current fix.

---

## 3. The eight decisions (settled 2026-06-23, owner-gated)

| # | Decision | Resolution | Why |
|---|---|---|---|
| 1 | Flask validation + OpenAPI extension | **spectree** | Least invasive to the 8.3 factory + PX-29 containment gate; Pydantic-native; rendered docs artifact is identical to apiflask's once fed to Fumadocs, and the lighter touch signals better judgment than importing a public-API framework onto an internal seam |
| 2a | HTTP API docs (Layer B) | **Generate from OpenAPI** → Fumadocs (later) | One source of truth; can't drift; spectree emits the spec for free |
| 2b | Python code reference (Layer C) | **Skip the generated site** | Sartor is an app, not a library; the wiki + recall + assistant already navigate internals better than a signature dump. Keep docstrings + the coverage gate |
| 3 | Gate vehicle | **Fold kit gates into `feat/portable-enforcement-core`**; stand up the local pre-commit half **now** (no remote needed), CI-blocking flips on at 8.7 | The tool-agnostic-enforcement decision was already DECIDED (SPLIT, 2026-06-15) and scheduled at 8.7 — the kit's Gate 1 *is* that branch; don't build a parallel pre-commit track |
| 4 | ADRs | **Thin `decisions.md` index** over existing records | Closes the "no single chronological decision log" gap with zero duplication or competing home (cite-don't-restate / D5) |
| 5 | `context-structure-review` packaging | **Committed plugin skill in a root `skills/` dir** | `.claude/skills/` is gitignored → unshipped/unpromotable. Root `skills/` mirrors the `commands/`/`agents/` convention, stays close to the kit format for easy upstream sync, and is committed + promotable |
| 6 | Gate hardness | **Ratchet-then-block** | Hard-block unambiguous gates day one (gitleaks, `ruff format`, mypy on covered modules); strict families (`D`/`ANN`/`--strict`) ratchet warn→block per-module, locking each gain; known-noisy heuristics (oversized-file, any commented-out grep) stay **warn-only forever** (the kit's false-positive→route-around caveat) |
| 7 | mypy `--strict` end-state | **Strict everywhere except a named exempt set** (`tests/`, `evals/`, `scripts/`, `db/migrations/versions`) | Professional default; named + justified exemptions satisfy "audit the escape hatches"; gives the ratchet a finite finish line |
| 8 | `uv` migration | **Out of scope** | Stay pip/setuptools; translate the kit's commands |

Full rationale for Decisions 1, 2, 3, and 5 (the ones that turned on Sartor-specific facts —
Fumadocs consuming OpenAPI, the latent-CI/no-remote state, the component packaging) is in the
conversation of record; the one-line "why" above is the durable summary.

---

## 4. The sequenced arc

Each item tagged **[J]** judgment (→ AGENTS.md/skill) or **[M]** mechanism (→ gate). Every
branch keeps the (latent) gate green at every commit.

**Phase 0 — Documentation-first (this doc + decisions.md + roadmap entries).** Done at capture.
Anchors everything downstream; nothing else starts until the record exists.

**Phase 1 — Cheap mechanizable wins** (~1–2 sessions): `ruff format` normalize + `--check`
wired **[M]**; ruff `ERA` **[M]**; ruff `SIM`/`RUF` (land per-family if noisy) **[M]**; Pydantic
+ SQLAlchemy mypy plugins **[M]**. These ride the local pre-commit half of
`feat/portable-enforcement-core`; unambiguous ones hard-block locally day one (Decision 6).

> **Phase 1 progress — first branch `chore/kit-phase1-pydantic-mypy` (2026-06-23, owner-selected
> "lint+typing wins, defer format" subset).** Landed: **`pydantic.mypy` enabled** (`[tool.mypy]
> plugins`) — mypy stays green ("no issues found in 227 source files"; the plugin ships inside the
> existing `pydantic` dep, so **no new dependency**). **Two Phase-1 items revised against the real
> code:** (1) **ERA dropped, not enabled** — all 8 `ERA001` hits are **false positives** on legitimate
> documentation prose (JSON-shape examples, TypedDict shape docs, `# Section (name)` dividers, an
> `(i)-circle` reference), the exact case **Decision 6** marks *warn-only forever*; enabling it blocking
> would clutter docs with `# noqa: ERA001` and block every future prose comment containing a
> paren/pipe/dict-example, and there is no advisory lane until the 8.7 pre-commit core — so ERA stays
> unenabled (revisit only if that core gains a warn-only lane). (2) **SQLAlchemy mypy plugin dropped** —
> `db/models.py` uses native SQLAlchemy 2.0 typing (`DeclarativeBase` + `Mapped[...]` + `mapped_column`),
> for which `sqlalchemy.ext.mypy.plugin` is deprecated/unneeded; only `pydantic.mypy` applies. **Still
> owed in Phase 1 (own branch):** `SIM`/`RUF` per-family triage (228 hits, of which 117 are
> RUF001–003 ambiguous-unicode false-positives to ignore). (`ruff format` landed on its own branch —
> see the next note.)

> **Phase 1 progress — second branch `chore/kit-phase1-ruff-format` (2026-06-23, owner-confirmed
> style).** Landed: **`ruff format` applied tree-wide** — 161 of 217 files reformatted (56 already
> clean), pure formatter output (hand-packed collection literals exploded one item per line; no hand
> edits). Proven **prompt-inert**: every `analyzer.py` prompt constant + the `PROMPT_VERSION` /
> `AVATAR_PROMPT_VERSION` *value* + the `_BASE_SYSTEM_PROMPTS` registry are byte-identical pre/post
> (sha256 dump-diff, 31 entries, zero differences) — ruff format never edits inside string literals,
> so **no `PROMPT_VERSION` bump and no paid eval run**. The gate is **wired + hard-blocks day one**
> (Decision 6 / KIT-6): `pyproject.toml` `[tool.ruff.format]` declares the style
> (`quote-style`/`indent-style`; matches defaults so output is unchanged), and
> `.claude-plugin/hooks/ruff-changed.sh` now runs `ruff format --check` on staged Python alongside
> `ruff check`; `.git-blame-ignore-revs` lists the reformat commit so blame skips it. Gate green:
> ruff check . ✓ · mypy (227) ✓ · pytest 1391 passed. **Phase 1 now has one item left:** the
> `SIM`/`RUF` per-family triage named above.

> **Phase 1 progress — third branch `chore/kit-phase1-sim-ruf-triage` (2026-06-24, owner-confirmed).
> Phase 1 is now COMPLETE.** Landed: the **`SIM` + `RUF` families enabled whole** (`select += ["SIM",
> "RUF"]` — forward-protective, "add the family to select" per §4) with the documented noise carved
> out. Of the 228 raw hits: **117 ambiguous-unicode (RUF001/2/3) ignored** (em-dash/smart-quotes in
> prompt + UI copy — the exact Decision-6 "known-noisy heuristic stays ignored" case; crucially this
> means **no prompt string is edited**, so `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` stay untouched and
> no eval run is owed); **SIM905 ignored** (1 hit — the `hardening.STOP_WORDS` compact `.split()`, whose
> fix is a strictly-worse ~110-element literal); **RUF059 carved out in `tests/**`** (18 hits —
> idiomatic unused tuple-unpack, matching the existing S-family test carve-outs). The remaining **110
> were fixed**: 41 auto (`ruff check --fix`, no `--unsafe-fixes` — RUF100 unused-noqa ×33, SIM300 ×3,
> RUF022 ×3, RUF023 ×1 on `analyzer._StreamDone.__slots__` (prompt-inert), SIM114 ×1) + 32 by hand
> (SIM115 ×16 → `Path(...).read_text/write_text`, RUF012 ×7 → `ClassVar[...]`, SIM117 ×4 combined-`with`,
> SIM105 ×4 → `contextlib.suppress`) + 1 `# noqa: RUF022` on `db/models.py:__all__` (preserves the
> curated domain grouping). All enabled families **hard-block day one** via the existing
> `ruff-changed.sh` `ruff check` arm (Decision 6 — these are unambiguous, not ratcheted). **ERA stays
> rejected** (warn-only-forever; not re-proposed). Gate green: ruff check . ✓ · ruff format --check (217)
> ✓ · mypy (227) ✓ · pytest 1390 passed + 1 flaky (Compose load-race, passes isolated). **Phase 1 done;
> next kit work is Phase 2 (strictness ratchet) at owner direction.**

**Phase 2 — Strictness ratchet** (~3–5 sessions; this is WS-2-full made concrete): ruff `ANN`
**[M+J]**; ruff `D` + pinned `google` pydocstyle convention **[M+J]**; `interrogate` coverage
gate at measured-current, ratcheted up **[M]**; mypy `--strict` + `warn_unreachable`, per-module
overrides keep green, tightened module-by-module toward the Decision-7 end-state **[M+J]**. The
big item; `analyzer.py` (3,648 lines) and `applications.py` (1,847) are each likely their own
tightening branch. **Tracked by a per-module coverage surface + the §6 exit criterion.**

> **Phase 2 #1 — `ANN` enabled (`chore/kit-phase2-ruff-ann`, 2026-06-24).** `select += ["ANN"]`;
> the Decision-7 exempt set carved in `per-file-ignores` (`tests/**`, `evals/*`, net-new
> `scripts/**`; `db/migrations/versions` already extend-excluded). The measured production
> surface was small + even — **60 hits across 18 files**, no monster module (`analyzer.py` 2,
> `applications.py` 5, so neither needed deferral) — so `ANN` landed **complete across the whole
> production tree in one branch**. All 60 **hand-fixed** (0 safe autofixes — ANN's autofix is
> `--unsafe-fixes`-only, unused per Phase-1 discipline): SSE `stream`/`worker` →
> `Iterator[str]`/`None`, routes → `ResponseReturnValue`, serializers/loaders → the `db.models`
> row types + `Session` (via `TYPE_CHECKING` blocks), docx plumbing → `Paragraph`/`Run`/`CT_NumPr`.
> **`ANN401`** (11) typed case-by-case (`Session`/`Anthropic`/`Experience`/`object`/concrete
> unions) + one **targeted `# noqa: ANN401`** on the SQLAlchemy `connect`-event listener (DBAPI /
> pool objects are dynamically typed at that boundary). A few typing-driven, behavior-preserving
> body touches followed (bare-`tuple` returns where slots are correlated/polymorphic; one
> `subject` union split; one `safe_user` `resolved` temp) — all surfaced because annotating a
> body makes mypy check it. **Per-module tracking (this family): `ANN` now blocks everywhere
> except the Decision-7 exempt set — full production coverage, the §6 exit-criterion shape for
> `ANN`.** Hard-blocks day one via `ruff-changed.sh` (Decision-6 — unambiguous, not ratcheted).
> No prompt edited → no `PROMPT_VERSION` bump, no eval run. Gate green: ruff check . ✓ · ruff
> format --check (217) ✓ · mypy (227) ✓ · pytest 1391 passed. **Remaining Phase 2: `D` + google
> pydocstyle, `interrogate` coverage gate, mypy `--strict` — each its own later branch.**

> **Phase 2 #2 — mypy `--strict` on leaf modules (`chore/kit-phase2-mypy-strict-leaves`, 2026-06-24).**
> First rung of the module-by-module `--strict` ratchet: a new per-module `[[tool.mypy.overrides]]`
> block brings `scraper`, `json_resume`, `pdf_render` — the deterministic, LLM-free P1-Hardening
> leaves — to the full `--strict` preset + `warn_unreachable`, while the global mypy config stays
> permissive. **Config gotcha:** `strict` is **not** in `mypy.options.PER_MODULE_OPTIONS`, so it
> can't be set inside an override; the preset is spelled out as its per-module-capable component
> flags (`disallow_untyped_defs` / `disallow_incomplete_defs` / `disallow_untyped_calls` /
> `disallow_untyped_decorators` / `disallow_any_generics` / `disallow_subclassing_any` /
> `check_untyped_defs` / `warn_return_any` / `strict_equality` / `extra_checks`) + `warn_unreachable`.
> The three leaves are pure (stdlib / 3rd-party imports only, no intra-project calls), so strict
> treatment surfaced **no cross-module cascade** — only one `disallow_any_generics` hit
> (`scraper.fetch_profile_content(config: dict)` → `dict[str, Any]`); the other two were already
> strict-clean. **Per-module tracking (this family): 3 production modules at full strict, the rest
> still permissive (no override = permissive); the ratchet tightens module-by-module toward the §6
> exit criterion.** The committed `mypy .` gate is the per-module block (Decision-6 — once the
> override lands, any strict regression in these three fails the gate). No prompt edited → no
> `PROMPT_VERSION` bump, no eval run. Gate green: ruff check . ✓ · ruff format --check (217) ✓ ·
> mypy (227) ✓ · pytest 1390 passed / 1 known-flaky (the tracked Compose-load UX race
> `test_pointer_drag_reorders` — intermittent on both this branch + the clean tree, not code-caused;
> RELEASE_CHECKLIST ledger #3). **Remaining Phase 2: `D` + google pydocstyle, `interrogate`
> coverage gate, larger-module `--strict` (`analyzer.py` / `applications.py`) — each its own later
> branch.**

> **Phase 2 #3 — ruff `D` (pydocstyle/google) enabled + first ratchet rung
> (`chore/kit-phase2-ruff-d`, 2026-06-24).** `select += ["D"]` +
> `[tool.ruff.lint.pydocstyle] convention = "google"`. Two-kind family, handled per its shape:
> the **content** rules (D205/D209/D301/D4xx) are mechanical → swept tree-wide so they block
> everywhere day one (their §6 shape — no per-module deferral); the **missing-docstring** rules
> (the only codes that appear: D101/D102/D103/D105/D107) **ratchet per-module** via a new
> `per-file-ignores` block. **GOTCHA — ruff has no per-file `select`/un-ignore**, only per-file
> *ignore*, so a per-module ratchet of a globally-selected rule must list the **not-yet-done**
> modules (the inverse of the mypy `--strict` override, which lists the **done** modules); the
> list **shrinks** as modules are documented → §6 exit = block empty. 16 entries cover the 27
> undocumented files; `ui_pages/**` is a safe directory glob (closed 12-file POM, **53% of the
> remaining docstring debt** — its branch is the large one), but `recall/`/`onboarding/`/
> `blueprints/` use **per-file** (those trees hold already-clean files a dir-glob would
> over-exempt). **Measured (production, google):** 416 D total — content 248 (105 safe autofix
> D209/D411/D412; **143 hand** — D205 is **100% hand-fix in ruff 0.15.12**, the handoff's
> "~240 auto" estimate was wrong) + missing-docstring 168/28 files. **No D100/D104/D106** (google
> doesn't enable module/package docstrings) and **no D401** imperative-mood churn (not in the
> google subset). **First documented module: `hardening.py`** — its 10 D101 hits were its 10
> public TypedDict classes (`CandidateInfo` … `ContextSet`, the `context_set` contract); now fully
> `D`-clean + the google-style reference. PROMPT-SAFE (docstrings ≠ prompt constants; analyzer
> prompt-constant sha256 byte-identical pre/post → no `PROMPT_VERSION` bump, no eval). `D`
> hard-blocks day one (KIT-6); no `ruff-changed.sh` edit (inherits `select`); no dep/version change.
> Gate green: ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest. **Per-module
> tracking (this family): hardening.py at full `D`; 27 modules still carry the missing-docstring
> waiver; content rules block tree-wide.** **Remaining Phase 2: the rest of the `D` ratchet
> (drain the 27, ~26 branches/units — ui_pages is the big one), `interrogate` coverage gate,
> larger-module `--strict` (`analyzer.py` / `applications.py`) — each its own later branch.**

> **Phase 2 #3 ratchet — unit 2, `recall/` batch drained (`chore/kit-phase2-ruff-d-recall`,
> 2026-06-24).** Second rung of the `D` missing-docstring ratchet: documented the **6 `recall/`
> modules** (`memory_source` · `models` · `sources/{git_grep,session,vector,wiki}_source`) and
> removed their six entries from the `per-file-ignores` ratchet block (**16 → 10 entries**).
> All 6 hits were **constructor docstrings** — five `__init__` (D107) + one `Unit.__post_init__`
> (D105); each got a single-line prose docstring matching the modules' existing
> `refresh`/`search`/`observe` style (no `Args:` section — google doesn't require one and it
> would diverge from the local style). Measured the true debt by **bypassing the ratchet**:
> `ruff check recall/ --select D --config "lint.per-file-ignores={}"` (the inverse-list ratchet
> means a plain `ruff check recall/` reports 0 — the waiver hides it; clearing per-file-ignores
> exposes the real count). PROMPT-SAFE (no prompt constants in `recall/`, not `analyzer.py` → no
> sha256 dump, no `PROMPT_VERSION` bump, no eval). No dep/version/`ruff-changed.sh` change. Gate
> green: ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest 1390 passed / 1
> known-flaky (ledger #3 Compose-load race — title-add member `test_add_title_then_pin_persists`
> recurred, passed clean isolated; branch touches no Compose code). **Per-module tracking: `hardening.py` +
> the 6 `recall/` modules at full `D`; 21 modules still carry the missing-docstring waiver.**
> Remaining ratchet units (smallest first): `config.py` (6) · small-blueprints trio (7) ·
> `onboarding/` (14) · `db/models.py` (20) · `analyzer.py` (16) · last `ui_pages/**` (89).

> **Phase 2 #3 ratchet — unit 3, `config.py` drained (`chore/kit-phase2-ruff-d-config`,
> 2026-06-24).** Third rung of the `D` missing-docstring ratchet: documented `config.py` (the
> typed `Config` frozen dataclass) and removed its entry from the `per-file-ignores` ratchet
> block (**10 → 9 entries**). All 6 hits were **D102 (undocumented-public-method)** on the six
> derived-root `@property` accessors (`configs_dir` · `resumes_dir` · `output_dir` ·
> `annotation_root` · `personas_dir` · `bundled_personas_dir`); each got a single-line
> google-style docstring (noun phrase + the `<base>/…` path, no `Args:`/`Returns:` — matching
> the module's existing `ensure_dirs`/`as_flask_config` style). The class + module docstrings +
> the two real methods were already documented (no D101/D103/D105/D107). Measured the true debt
> by bypassing the ratchet: `ruff check config.py --select D101,D102,D103,D105,D107 --config
> "lint.per-file-ignores={}" --statistics` (a plain `ruff check config.py` reports 0 — the
> inverse-list waiver hides it). PROMPT-SAFE (`config.py` holds no prompt constants, not
> `analyzer.py` → no sha256 dump, no `PROMPT_VERSION` bump, no eval). No dep/version/
> `ruff-changed.sh` change. Gate green: ruff check ✓ · ruff format --check (217) ✓ · mypy (227)
> ✓ · pytest 1390 passed / 1 known-flaky (ledger #3 Compose load-race — a **new member**,
> `test_happy_path_through_template_preview` `experience_card_count()==0`, passed clean isolated
> 1/1; branch touches no Compose code). **Per-module tracking: `hardening.py` + the 6 `recall/`
> modules + `config.py` at full `D`; 20 modules still carry the missing-docstring waiver.**
> Remaining ratchet units (smallest first): small-blueprints trio (7) · `onboarding/` (14) ·
> `analyzer.py` (16) · `db/models.py` (20) · last `ui_pages/**` (89).

> **Phase 2 #3 ratchet — unit 4, small-blueprints trio drained
> (`chore/kit-phase2-ruff-d-blueprints`, 2026-06-25).** Fourth rung of the `D`
> missing-docstring ratchet: documented the **3 small blueprint route modules**
> (`blueprints/users.py` · `blueprints/generation.py` · `blueprints/corpus/curation.py`) and
> removed their three entries from the `per-file-ignores` ratchet block (**9 → 6 entries**).
> All 7 hits were **D103 (undocumented-public-function)** on **Flask route handlers** — a new
> genre vs the prior units' TypedDicts / `@property` accessors / constructors:
> `list_users` · `create_user` · `get_config` · `update_config` (users) · `download_file`
> (generation) · `upload_resume` · `list_resumes` (corpus/curation). Each got a single-line
> google-style summary of the HTTP action (method + path already live in the decorator; no
> `Args:`/`Returns:` — matching the already-documented siblings `fetch_profile` /
> `download_edited` / `list_corpus_duplicates`), inserted **above** any existing
> leading/mid-body comment so the guards stay byte-identical. The docstring edits were
> anchored **inside** each body (not on the `@…route` decorator), so `route-security-lint`
> saw no route definition in the diff. Measured the true debt by bypassing the ratchet:
> `ruff check <mods> --select D101,D102,D103,D105,D107 --config "lint.per-file-ignores={}"`
> (a plain `ruff check` reports 0 — the inverse-list waiver hides it). PROMPT-SAFE (none of
> the three modules hold prompt constants — all prompts live in `analyzer.py`; `download_file`
> is a pure file route → no sha256 dump, no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no
> eval). No dep/version/`ruff-changed.sh` change. Gate green: ruff check ✓ · ruff format
> --check (217) ✓ · mypy (227) ✓ · pytest 1391 passed (the ledger #3 Compose load-race did
> **not** fire this run — clean full suite). **Per-module tracking: `hardening.py` + the 6
> `recall/` modules + `config.py` + the small-blueprints trio at full `D`; 6 entries / 17
> modules still carry the missing-docstring waiver.** Remaining ratchet units (smallest
> first): `onboarding/` (14) · `analyzer.py` (16) · `db/models.py` (20) · last `ui_pages/**` (89).

> **Phase 2 #3 ratchet — unit 5, `onboarding/` trio drained
> (`chore/kit-phase2-ruff-d-onboarding`, 2026-06-25).** Fifth rung of the `D` missing-docstring
> ratchet: documented the **3 `onboarding/` modules** (`review_cli.py` · `corpus_import.py` ·
> `extract_experiences.py`) and removed their three entries from the `per-file-ignores` ratchet
> block (**6 → 3 entries**). 14 hits spanning every prior genre at once: `review_cli.py` (10 —
> 1 D107 `__init__` + 8 D102 `ReviewSession` methods + 1 D103 `main`), `corpus_import.py` (2 —
> D102 `ImportReport.merge` + D103 `main`), `extract_experiences.py` (2 — D101 on the
> `ExtractedBullet` / `ExtractedExperience` TypedDicts). Each got a single-line google-style
> summary inserted as the first body line (above any leading comment) so surrounding logic stays
> byte-identical. **NEW gotcha vs the prior units (all of which were prompt-free):** this is the
> first ratchet unit where a documented module **also holds an LLM prompt constant** —
> `EXTRACT_EXPERIENCES_SYSTEM_PROMPT` at `extract_experiences.py:69-90`, passed to
> `analyzer._parse_or_retry(system_prompt=…)` at `:134`. `onboarding/` is **not** in the
> deterministic-boundary exempt set (`hardening`/`parser`/`generator`/`scraper`/`json_resume`/
> `corpus_to_json_resume`/`pdf_render`), so it may legitimately hold LLM calls + prompts. None of
> the 14 documented symbols **is** the prompt string, so docstrings can't touch it — but proven,
> not asserted: sha256 of the constant byte-identical pre/post
> (`268b76229e24fec6744343f971b567d17b62f812bd2515062eec90039ecd1aa2`, len 2553) + a
> `git diff` that never enters the 69-90 block ⇒ no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump,
> no eval. Measured the true debt by bypassing the ratchet
> (`--config "lint.per-file-ignores={}"`; a plain `ruff check` reports 0). No dep/version change.
> Gate green: ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest 1390 passed / 1
> flaky — the ledger #3 Compose load-race **did** fire this run (bullet-load mode,
> `test_20260604_bullet_drag_reorder`); passed on isolated re-run → confirmed flake, not a
> regression. **Per-module tracking: `hardening.py` + the 6 `recall/` modules + `config.py` + the
> small-blueprints trio + the `onboarding/` trio at full `D`; 3 entries / 14 modules still carry
> the missing-docstring waiver.** Remaining ratchet units (smallest first): `analyzer.py` (16) ·
> `db/models.py` (20) · last `ui_pages/**` (89).

> **Phase 2 #3 ratchet — unit 6, `db/models.py` drained
> (`chore/kit-phase2-ruff-d-models`, 2026-06-25).** Sixth rung of the `D` missing-docstring
> ratchet: documented `db/models.py` (all **20 D101 hits — every undocumented ORM class**,
> `Base` + `Candidate` … `Engagement`) and removed its entry from the `per-file-ignores` ratchet
> block (**3 → 2 entries**). The prompt-free, single-genre analogue of the unit-1 `hardening.py`
> TypedDict pass — pure-D101, and the 10 model classes already documented (`Tag`, `Skill`, the
> `SummaryItem` family, `Clarification`, …) set the house style: single-line descriptive
> noun-phrase summaries, no `Args:`. `Base`'s bare `pass` body was replaced by its docstring (the
> only deleted line; PIE790 is not in `select`, so a redundant `pass` would not lint either way).
> **PROMPT-SAFE the easy way (GOTCHA-4 grep-first):** `db/models.py` is pure SQLAlchemy, so a grep
> for `(_PROMPT|_RULES_BLOCK|PROMPT_VERSION|SYSTEM_PROMPT|AVATAR_)` returns **0** — no prompt
> constant exists to perturb, so no sha256 dump is needed and there is no `PROMPT_VERSION`/
> `AVATAR_PROMPT_VERSION` bump, no eval run. Measured the true debt by bypassing the ratchet
> (`--config "lint.per-file-ignores={}"`). No dep/version/hook change. Gate green: ruff check ✓ ·
> ruff format --check (217) ✓ · mypy (227) ✓ · pytest 1389 passed / 2 flaky — the ledger #3
> Compose load-race fired its **strongest datapoint yet** (two members at once: bullet-load
> `test_20260604_bullet_drag_reorder` + title-add `test_20260611_compose_add_title`; the latter
> measured at 4/6 passing isolated, ~33 % fail, and passing on a `git stash`'d clean tree — both
> proven flaky and code-independent, ledger #3). **Per-module tracking: `db/models.py` now at full
> `D`; 2 entries / 13 modules still carry the missing-docstring waiver** (`analyzer.py` + the
> 12-file `ui_pages/**` glob). Remaining ratchet units (smallest first): `analyzer.py` (16 —
> GOTCHA-4 territory, holds the 16 prompt constants → sha256-prove them) · last `ui_pages/**` (89).

> **Phase 2 #3 ratchet — unit 7, `analyzer.py` drained
> (`chore/kit-phase2-ruff-d-analyzer`, 2026-06-25).** Seventh rung — the GOTCHA-4
> prompt-home unit. Documented `analyzer.py`'s 16 D-flagged symbols and removed its entry
> from the `per-file-ignores` ratchet block (**2 → 1 entry**). **Clarification of the two
> easily-conflated "16"s:** the 16 *D-flagged symbols* are **14 D101 Pydantic response-model
> classes** (`AnalyzeResponse`/`GenerateResponse`/`ClarifyResponse`/`Recommend*`/`GenerateCorpus*`/
> `CoverLetterOnlyResponse`/`CritiqueResponse`/`PromoteBulletResponse`) **+ 1 D102** (the
> `ClarifyResponse.enforce_composition_rules` validator) **+ 1 D107** (`LLMResponseError.__init__`)
> — a DIFFERENT set from the module's prompt-string constants. The response models got single-line
> google summaries naming which call's `_parse_or_retry` shape each validates (the `*_REQUIRED_KEYS`
> frozensets above each model are the source); three siblings (`HiddenQualityItem`,
> `AnalyzeExtractionResponse`, `AnalyzeSynthesisResponse`) were already the in-file exemplars.
> **PROMPT-SAFE (GOTCHA-4 done the hard way):** docstrings on Pydantic classes never touch a
> `NAME = """…"""` literal, but `analyzer.py` IS the prompt home, so proved it — sha256 of every
> prompt constant (the 11 `_BASE_SYSTEM_PROMPTS` registry values + `AVATAR_SYSTEM_PROMPT` +
> `_COVER_LETTER_RULES_BLOCK`) + both version strings, HEAD vs branch → **byte-identical** (diff
> empty); no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval run. No dep/version/hook change.
> Gate green: ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest 1389 passed / 2
> flaky — the ledger #3 Compose load-race fired a **new member pair** (title-add
> `test_add_title_then_pin_persists` + no-recommendations-order
> `test_no_recommendations_order_persists_on_reload`), both passing isolated (2/2) → confirmed
> flake, code-independent (branch touches no Compose code). **Per-module tracking: `analyzer.py`
> now at full `D`; 1 entry / 12-file `ui_pages/**` glob is all that remains** — the LAST/LARGEST
> unit (89), reserved for its own dedicated branch that reaches the §6 exit (block empty → `D`
> blocks everywhere outside the KIT-7 exempt set).

> **Phase 2 #3 ratchet — unit 8, `ui_pages/**` drained — RATCHET COMPLETE / §6 EXIT for `D`
> (`chore/kit-phase2-ruff-d-ui-pages`, 2026-06-25).** The LAST and LARGEST unit, and the one that
> **empties the ratchet block** → the **§6 exit criterion for the `D` family is reached**: with no
> per-module `D` waiver left, `D` (including the missing-docstring codes D101/D102/D103/D105/D107)
> blocks EVERYWHERE outside the KIT-7 exempt set (`tests/**` · `evals/*` · `scripts/**` ·
> `db/migrations/versions`). Documented all **89 D-flagged symbols across the 12-file Playwright
> Page-Object-Model** — 20 D101 (the POM page classes + `selectors.py` registry classes), 68 D102
> (page-action + selector-builder methods), 1 D107 (`base.BasePage.__init__`) — with single-line
> google summaries naming the surface each POM/selector drives (the units 1–7 google-style exemplars
> + the already-documented `ui_pages` siblings set the house style). **Pure-mechanical, zero GOTCHA-4
> risk:** `ui_pages/` is a test driver, so the prompt-constant grep
> `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|anthropic|_call_llm)` over the 12 files returned
> **0** — no prompt to perturb, no sha256 dump needed (unlike unit 7's prompt-home proof). Removed the
> single `"ui_pages/**"` `per-file-ignores` line **and** rewrote the ratchet-block comment to record
> the exit (so a future reader sees why no ratchet entry remains). **§6-exit proof:** with
> `per-file-ignores` fully cleared, `ruff check . --select D101,D102,D103,D105,D107` reports 1417
> hits — **all in `tests/` (1406) · `scripts/` (10) · `evals/` (1)**, zero in any production module
> or `ui_pages`; the committed `ruff check .` stays green. PROMPT-SAFE (docstrings ≠ prompt
> constants; grep-0 confirms none here) → no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval
> run. No dep/version/`ruff-changed.sh` change (bare `ruff check` inherits `select`). Gate green:
> ruff check ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest **1390 passed / 1 flaky** — the
> ledger #3 Compose **bullet-load** race
> (`test_20260604_bullet_drag_reorder::test_pointer_drag_reorders`, `bullet_texts()[0]` IndexError)
> fired in the full suite and again **1/2 on isolated re-run** → confirmed code-independent flake
> (branch touches no Compose/frontend code; docstrings are runtime-inert), ledger #3. **Per-module
> tracking: the ruff-`D` ratchet is COMPLETE — every production module is at full `D`; the
> `per-file-ignores` `D` block is empty (only the permanent KIT-7 exempt set remains). Remaining
> Phase 2: the `interrogate` coverage gate (not installed → baseline/setup branch) + larger-module
> mypy `--strict` (`analyzer.py` / `applications.py`) — each its own later branch.**

> **Phase 2 #2 ratchet — rung 2, `blueprints.applications` (`chore/kit-phase2-mypy-strict-applications`,
> 2026-06-25).** Second rung of the per-module mypy `--strict` ratchet (the first since the three
> pure leaves seeded it in #2): added `"blueprints.applications"` to the existing strict override's
> `module` list — now `["scraper", "json_resume", "pdf_render", "blueprints.applications"]` — and
> rewrote the block comment so the roster reads as the general §6 tracking surface recording **two
> cohorts**: the deterministic LLM-free leaves (rung 1) and the first **non-leaf route/seam** module
> (rung 2). **Key insight (why the larger module was NOT the feared heavy branch):** `applications.py`
> is ~2,100 LOC and calls across seams + into `analyzer`, yet `--strict` + `warn_unreachable` surfaced
> **no `disallow_untyped_calls`/`disallow_untyped_defs` cascade** — because Phase-2 #1 (`ANN`) had
> already annotated every production `def`, so the only remaining strict surface was **13 errors**:
> **12 bare-generic `type-arg`** (parametrized, predominantly value-type `dict[str, Any]`; one
> `list[ApplicationRun]`) + **1 `no-any-return`** (`_parse_ats_status` → `cast("str | None", …)`, a
> runtime no-op; `cast` added to the existing `from typing import` line). Measured the surface
> read-only **before** editing with `python -m mypy --strict --warn-unreachable blueprints/applications.py`
> (the exact override preset — note plain `--strict` omits `warn_unreachable`, so include it to match)
> = 13; confirmed identical after the override + fixes via the authoritative whole-tree `mypy .` (227,
> green — no delta beyond the mapped 13). **GOTCHA carried from the leaves:** `strict` is still not a
> per-module option, so the preset stays spelled-out as component flags (reused the rung-1 block
> verbatim). **The one judgment call — `_load_application_owned` → `tuple[Any, Any]`, not the precise
> type:** `disallow_any_generics` only requires the generic be *parametrized*, and `--strict` does NOT
> include `disallow_any_explicit`, so `tuple[Any, Any]` passes while preserving the untyped
> unpack-then-check contract exactly; the precise `tuple[Application | None, Candidate | None]` would
> force a None-narrowing change at its **9 in-module callers** (+ 2 permissive `templates.py` ones) — a
> separate None-safety pass the `ANN` branch already deferred and the docstring documents, out of
> scope for a one-module typing rung. **PROMPT-SAFE the easy way (GOTCHA-4 grep-first):**
> `blueprints/applications.py` holds no prompt constants — a grep for
> `(SYSTEM_PROMPT|PROMPT_VERSION|AVATAR_|_RULES_BLOCK|_BASE_SYSTEM_PROMPTS)` matched only docstrings +
> `anthropic` exception types (the prompts live in `analyzer.py`; this module *calls* `analyzer.recommend_*`),
> so no sha256 dump, no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump, no eval. No dep/version/hook
> change. Gate green: ruff ✓ · ruff format --check (217) ✓ · mypy (227) ✓ · pytest **1389 passed / 2
> flaky** — the ledger #3 Compose load-race fired a two-member pair
> (`test_keyboard_reorder_persists_and_reset_reverts` + `test_no_recommendations_order_persists_on_reload`,
> both `bullet_texts()[0]` IndexError); both passed clean on isolated re-run (2/2) → confirmed flake,
> code-independent (branch is annotations + mypy-config only, runtime-inert). **Per-module tracking: 4
> production modules now at full strict; the rest permissive. Remaining Phase 2: the `interrogate`
> coverage gate (baseline/setup branch) + larger-module mypy `--strict` (`analyzer.py`, the prompt
> home — sha256 ceremony owed there).**

> **Phase 2 #2 ratchet — rung 3, `analyzer.py` (`chore/kit-phase2-mypy-strict-analyzer`, 2026-06-25).**
> Third rung — the prompt-home large module (~3,800 LOC; the sole LLM-call site). Added `"analyzer"` to
> the strict override's `module` list — now `["scraper", "json_resume", "pdf_render",
> "blueprints.applications", "analyzer"]` — and extended the block comment to a **third cohort**.
> **This closes the larger-module `--strict` commitment** (rung 1 = the leaves, rung 2 =
> `applications.py`; `analyzer.py` was the only large module left). **Same key insight as rung 2 —
> NOT the feared heavy branch:** `ANN` (Phase-2 #1) had pre-typed the whole call graph, so `--strict`
> + `warn_unreachable` surfaced **no `disallow_untyped_calls`/`disallow_untyped_defs` cascade** — only
> **47 errors, ~91% mechanical**: **43 bare-generic `type-arg`** (parametrized `dict[str, Any]` /
> `list[dict[str, Any]]` — all JSON-object dicts with string keys), **2 `no-any-return`**
> (`cast("dict[str, Any]", …)` on `_parse_or_retry`'s validated `data` + `check_refinement_scope`'s
> `json.loads`, runtime no-ops; `cast` added to `from typing import`), and **2 `warn_unreachable`** —
> the only non-mechanical judgment calls. **The 2 unreachable resolutions:** (1) the `elif
> isinstance(recommendations, list)` branch in `_stable_user_prefix` was dead because the `ContextSet`
> TypedDict types `llm_recommendations` as bare `dict` → widened the local to `recommendations: object`
> so both documented dispatch branches (persisted JSON ships it dict-keyed-by-exp-id OR as a list) stay
> reachable — **zero runtime change**; (2) `clarify_iteration`'s `(...).get("keyword_overlap", {}) or
> {}` final fallback is dead because the all-required TypedDict types the chain always-truthy, but
> persisted context JSON can be partial/null at runtime → kept the deliberate `or {}` defense behind a
> scoped `# type: ignore[unreachable]` with a comment (removing it would be a behavior change, out of
> scope for a typing rung). Measured read-only **before** editing
> (`python -m mypy --strict --warn-unreachable analyzer.py` = 47); whole-tree `mypy .` (227) green
> after. **PROMPT-SAFE the GOTCHA-4 way (sha256, NOT grep-0):** unlike `applications.py`, `analyzer.py`
> IS the prompt home, so the grep-0 shortcut doesn't apply — dumped sha256 of all **15** prompt
> constants (the 11 `_BASE_SYSTEM_PROMPTS` values + `AVATAR_SYSTEM_PROMPT` + `_COVER_LETTER_RULES_BLOCK`
> + `PROMPT_VERSION` + `AVATAR_PROMPT_VERSION`) HEAD-vs-branch → **byte-identical** (also re-verified
> after `ruff format` wrapped one long signature), so no `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` bump,
> no eval. No dep/version/hook change. Gate: ruff ✓ · ruff format --check (217) ✓ · mypy (227) ✓ ·
> pytest — the ledger #3 Compose bullet-load race **fired on the pre-commit run** (**1389 passed / 2
> failed**: `test_keyboard_reorder_persists_and_reset_reverts` + `test_pointer_drag_reorders`), both
> **passed clean isolated** (1/1, 2/2); an earlier same-session full run on the **identical** code was
> clean (1391/0) — the same-code fire-then-clean alternation is itself proof of code-independence (the
> branch is annotations + config + docs, runtime-inert for Compose). **Per-module tracking: 5
> production modules now at full strict; the rest permissive. Remaining Phase 2: only the `interrogate`
> coverage gate (baseline/setup branch) — the larger-module mypy `--strict` commitment is now
> COMPLETE.**
>
> **Progress (2026-06-25, `chore/kit-phase2-interrogate`):** Phase 2 #4 — the `interrogate`
> docstring-**coverage** floor-lock gate — LANDED, the **final Phase 2 implementation sub-item**.
> `interrogate>=1.7,<2.0` added to the `dev` extra (a real new dependency → CHANGELOG); a new
> `[tool.interrogate]` block scopes to production (KIT-7 exempt set excluded; `ui_pages/**` IN,
> matching the `D` surface; single-underscore semiprivate helpers excluded for coherence with `D`'s
> public-only scope, so a helper-only module like `web_infra/` contributes zero counted symbols) and
> records `fail-under = 99`. The gate is a **pytest floor-lock ratchet**
> (`tests/test_docstring_coverage_gate.py`, mirroring `test_route_containment_gate.py`): it re-runs
> the bare interrogate CLI via subprocess (single source of truth = `[tool.interrogate]`; no
> `import interrogate`, so no mypy/stub coupling and robust to API drift) and asserts exit 0; skips
> when interrogate is absent (default `pytest` stays green), has teeth in CI. KIT-6 "warn-start": the
> floor locks measured-current; "ratchet up later" = raise `fail-under` in a future branch.
> interrogate surfaced two undocumented public classes (`onboarding`'s `Color` + `ExtractResponse`)
> that google's `D101` blind-spots (attribute-only / pydantic-model classes); both were documented,
> taking production coverage 99.5% → **100%**, so `fail-under = 99` locks a fully-documented baseline
> with ~1 pt headroom (not a brittle exact 100). Owner-directed add-on: a docstring-only pass documented
> the **50** below-public-bar internals interrogate surfaces at maximal scope (`_`-helpers / nested
> SSE-worker closures / private methods, ~20 files; maximal-scope coverage now 100% too) + the 5 empty
> `tests/**/__init__.py` markers — the gate stays public-API-scoped (ignore flags unchanged; KIT-7 keeps
> `tests/` D-exempt). `analyzer.py` re-verified PROMPT-SAFE (15 constants sha256-identical).
> No prompt/route/version change → no eval. Teeth
> verified (floor temporarily 100 vs 99.5% → red, green again at 99). Gate: ruff ✓ · ruff format
> --check (218) ✓ · mypy (228) ✓ · pytest. **Phase 2 of the kit-adoption arc is now COMPLETE** —
> `ANN` (#1) + mypy `--strict` larger-module (#2) + `D` (#3) + `interrogate` (#4) all landed. The §6
> `--strict`-family exit (`app.py`, the rest of `blueprints/**`, `db/`, `hardening.py`, `parser.py`,
> `generator.py`, …) remains a longer post-public ratchet, and (3)'s skills/hooks-packaging coherence
> rides 8.7 `feat/portable-enforcement-core`.

**Phase 3 — Request-boundary typing + OpenAPI** (~4–6 sessions): pick is settled (spectree,
Decision 1); convert ~30 endpoints to parse `request.json` into Pydantic models, blueprint by
blueprint, each reconciled with `_safe_username`/`_within` + the PX-29 containment gate **[M+J]**;
emit the OpenAPI spec **[M]**. **Lighter than the handoff's plan** — Sphinx/mkdocstrings are out
(Decision 2b); the Fumadocs *rendering* of the spec is a separate later project.

**Phase 4 — DoD + governance reconcile** (~1 session): extend the existing PR template +
AGENTS.md "Key patterns" with only the net-new DoD lines (docstrings/docs-build, no
commented-out code, comments-updated-in-same-change, decision-recorded) **[J]**; seed/maintain
`decisions.md` **[J]**.

**Phase 5 — Skill + promotable flagging** (~1 session): install `context-structure-review` in a
root `skills/` dir (Decision 5) **[M+J]**; record the §7 promotable shortlist **[J]**.

Estimate: a v1.0.8-scale arc (~10–15 sessions). Real cost concentrates in Phase 2d (mypy
`--strict`) and Phase 3 (spectree boundary). Everything else is hours or reconcile-don't-build.

---

## 5. Temporal map (how the arc threads the existing roadmap)

The kit-adoption arc is **not free-floating** — it overlays planned work:

- **Now / current window:** Phase 0 (done) → Phase 1 quick wins → Phase 2 ratchet begins →
  Phase 3 boundary refactor. The local pre-commit gates run today (no remote needed).
- **At 8.7 (`feat/portable-enforcement-core` + `release/public-prep`):** the kit's gates fold
  into the shared enforcement core; **CI-blocking activates when the GitHub remote lands**
  (today there is no remote — `ci.yml` is committed but dormant); hooks re-home out of
  `.claude-plugin/` and the `commands/ agents/ skills/ hooks/` families reach the clean
  four-parallel end-state. See `RELEASE_CHECKLIST.md` 8.7 + Carry-forward ledger.
- **WS-2-full (recurring):** the Phase 2 strict ratchet *is* WS-2-full; the full strict
  end-state lands across the v1.0.8 tail → 1.1.x.
- **Post-8.7 (separate project):** Fumadocs renders the OpenAPI spec + the wiki markdown into
  the public docs site (`sartor-docs.taketempo.com`).

---

## 6. The ratchet exit criterion (coherence teeth)

The cautionary example is in-repo: the hooks split-home (scripts in `.claude-plugin/hooks/`,
wiring in `settings.json`) has been a decided-but-unexecuted half-migration since 7.1 — *fine
because it's tracked*. A strict ratchet with no tracking + no finish line is how you get a
*permanent* half-strict codebase. So the ratchet is bounded, not open-ended:

- **Tracking surface:** a per-module coverage record (which modules are at full strict / `D` /
  `ANN`, which still carry an override).
- **Exit criterion (done):** no module carries a strictness override **except** the named exempt
  set (`tests/`, `evals/`, `scripts/`, `db/migrations/versions`; Decision 7). When the only
  remaining overrides are those four, the ratchet is complete and the gate blocks everywhere
  non-exempt.

---

## 7. Promotable to `amodal-open` (the "flag" half of the framing)

Extraction candidates — practices Sartor already does best, to seed the shared layer later
(do **not** build the shared layer in this arc):

- The **governance philosophy** (charter C-0…C-6 / D-1…D-6 / W-1 + amendment ceremony).
- The **hooks-as-mechanism** model (post-8.7 shared enforcement core = the cleanest form).
- The **AGENTS.md `@import` + layered-overrides** instruction-file design.
- The **wiki doc-drift loop** (`/wiki-self-update` + `wiki-lint` + author≠auditor).
- The **eval-gate discipline** (`PROMPT_VERSION` attribution, the smoke-gate exit-2 contract).
- The **`.pre-commit-config.yaml`** the kit adds (the single most directly-inheritable artifact).

---

## 8. Open / owner-gated items

- Scheduling: the arc consolidates with `feat/portable-enforcement-core` (8.7) + WS-2-full; the
  pre-public phases (1–3) can begin in the current window at owner direction.
- spectree OpenAPI 3.1 + Pydantic v2 output to re-verify when Phase 3 starts (perishable).
- Fumadocs spec enrichment (per-route summaries/descriptions/examples) is budgeted into the
  later Fumadocs documentation pass, not this arc.
- Stale-doc fix owed (not this branch's scope): `CLAUDE.md:83` says the tool-agnostic-enforcement
  decision is "pending the v1.0.7 governance pass" — it was DECIDED 2026-06-15; what's pending is
  *implementation* at 8.7. Fix next time `CLAUDE.md` is touched.
