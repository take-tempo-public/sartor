# Building on Sartor

> **Purpose:** the front door for contributors: the dev ladder (what to read, in order) and a
> routed index of everything else under `docs/dev/`.
> **Audience:** `dev` — anyone changing Sartor's code or docs, human or agent. It assumes
> you've already installed Sartor and seen demo mode work ([Using Sartor](../user/README.md)).
> **Authoritative for:** the order of the dev docs and where each kind of dev doc lives. Each
> linked doc is the home of its own content.

## The dev ladder

Most contributors stop at rung D4. D5 is the owner's lane: you don't need it to send a pull
request.

| Rung | Your goal | Read |
|---|---|---|
| **D0** | A dev install (the `[dev]` extras, Chromium for Playwright) | [CONTRIBUTING](../../CONTRIBUTING.md) "Quick start" |
| **D1** | Your first green gate | `python -m scripts.gate`. [`scripts/gate.py`](../../scripts/gate.py) is the single definition of what it runs; it prints the memory floor and each step as it goes |
| **D2** | A map of the system | [architecture](architecture.md) (pipeline, module map, persistence, LLM routing) and the [system model](system-model.md) (the seven functions and the one law) |
| **D3** | Your first change | the code rules in [AGENTS.md](../../AGENTS.md), then the [task index](#where-to-make-a-change) below |
| **D4** | Why the rules are binding | the [charter](../governance/charter.md), [enforcement](../governance/enforcement.md) (which rules are machine-checked) and the [tooling roster](tooling.md) (what will block you) |
| **D5** | The maintainer lane | [maintainer-lane](maintainer-lane.md) (handoffs, the provenance ledger, the close-out checklist), [releasing](releasing.md), the [N=1 pipeline](n1-baseline-pipeline.md) |

## Where to make a change

| You want to change… | It lives in | Read first |
|---|---|---|
| a prompt or an LLM call | `analyzer.py`: every LLM call; the persona constants such as `SYSTEM_PROMPT` | AGENTS.md "LLM prompts" (the `PROMPT_VERSION` bump rule) |
| a route | `blueprints/`, one module per domain | AGENTS.md "Security" (`_safe_username` + `_within` on every filesystem route) |
| deterministic processing | `hardening.py`, `parser.py`, `generator.py` and the rest of AGENTS.md's deterministic list | AGENTS.md "Architecture at a glance": no LLM calls there |
| the corpus schema | `db/models.py` + a new `db/migrations/` revision | [architecture](architecture.md) "Persistence model"; the `require-consumer-enumeration` guard ([tooling](tooling.md)) |
| a résumé template | `personas/bundled/` | [bundled templates](bundled-templates.md) |
| the wizard UI | `static/app.js`, `templates/index.html`; page objects in `ui_pages/` | [architecture](architecture.md) module map; AGENTS.md "Frontend config persistence" |
| the diagnostics console | `dashboard/`, `blueprints/diagnostics.py` | [diagnostics](diagnostics.md) |
| an eval, a rubric, a fixture | `evals/` | [`evals/README.md`](../../evals/README.md), [grounding metric](GROUNDING_METRIC.md) |
| a doc | the doc's own home (`docs/user/`, `docs/dev/`) | the [doc style guide](doc-style-guide.md); [documentation architecture](documentation-architecture.md) for how docs get published |

## Where things live

**Reference** (still maintained; each is the home of its subject):
- [architecture](architecture.md), [system model](system-model.md) and
  [product shape](PRODUCT_SHAPE.md): the system, and the data model it converges toward
- [memory architecture](memory-architecture.md): the `recall/` substrate and the doc assistant
- [grounding metric](GROUNDING_METRIC.md): the no-invention metric and its calibration plan
- [diagnostics](diagnostics.md): the diagnostics console, tab by tab
- [tooling](tooling.md): hooks, guards, commands, subagents, skills
- [keep ledger](keep-ledger.md): the do-not-regress catalogue for eval and governance
- [agent failure patterns](AGENT_FAILURE_PATTERNS.md): what agents get wrong here, and how
  to avoid it
- [doc style guide](doc-style-guide.md) and [documentation architecture](documentation-architecture.md):
  how docs are written, and how they are published
- [extraction](EXTRACTION.md): when an in-repo system is ready to become its own project

**Runbooks** (step by step):
- [releasing](releasing.md): the publishing setup and the release trigger
- [docs-site deploy](docs-site-deploy.md): the hosted docs site and its CI deploy
- [screenshot capture](screenshot-capture.md): regenerating the documentation screenshots
- [bundled templates](bundled-templates.md): changing or adding a bundled résumé template
- [maintainer lane](maintainer-lane.md): starting and closing a branch in the owner's lane

**Plans and designs** (the plan of record, plus designs that are still live specs):
- [RELEASE_ARC](RELEASE_ARC.md): the branch sequence and acceptance criteria
- [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md): what must be true before a release, and the
  carry-forward ledger
- [work board](work/BOARD.md): every open work item ([schema](work/SCHEMA.md))
- [decisions](decisions.md): one line per architectural decision, pointing at its record
- [nursery](nursery.md): possible future features, "good idea, not now"
- [docs IA design](docs-ia-design.md): the docs tree, ladders, link policy and planned lints
- [N=1 pipeline](n1-baseline-pipeline.md), [Epic A chain-design corrections](epic-a-chain-design-corrections.md)
  and [handoff integrity design](handoff-integrity-design.md): live specs for the pipeline
  envelope and for charter C-9

**Templates** (copy these; don't edit them casually, since hooks and scripts read them):
- [handoff template](AGENT_HANDOFF_TEMPLATE.md)
- [diagnosis dossier](diagnosis/TEMPLATE.md) (the `require-evidence-before-fix` guard, C-7)
- [blast-radius dossier](blast-radius/TEMPLATE.md) (the `require-consumer-enumeration` guard,
  C-10)

**Records** (frozen history; never rewritten, never published): [`handoffs/`](handoffs/),
[`ledger/`](ledger/), [`diagnosis/`](diagnosis/), [`blast-radius/`](blast-radius/),
[`reviews/`](reviews/), [`perf/`](perf/), [`excellence-walk/`](excellence-walk/),
[`flake-rates/`](flake-rates/), and [`archive/`](archive/) for retired designs.
[`scripts/doc_registry.py`](../../scripts/doc_registry.py) is the single home of this list.
Where moved docs went: [`moved-paths.json`](moved-paths.json).
