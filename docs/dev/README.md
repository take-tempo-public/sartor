# Building on Sartor

> **Purpose:** the front door for contributors: the dev ladder (what to read, in order) and a
> routed index of everything else under `docs/dev/`.
> **Audience:** `dev` — anyone changing Sartor's code or docs, human or agent. It assumes
> you've already installed Sartor and seen demo mode work ([Using Sartor](../user/README.md)).
> **Authoritative for:** the order of the dev docs and where each kind of dev doc lives. Each
> linked doc is the home of its own content.

## The dev ladder

1. **Dev install:** [CONTRIBUTING](../../CONTRIBUTING.md).
2. **Your first green gate:** `python -m scripts.gate`. [`scripts/gate.py`](../../scripts/gate.py)
   is the single definition of what it runs.
3. **A map of the system:** [architecture](architecture.md) and the
   [system model](system-model.md).
4. **Your first change:** the code rules in [AGENTS.md](../../AGENTS.md).
5. **Why the rules are binding:** the [charter](../governance/charter.md) and
   [enforcement](../governance/enforcement.md).
6. **The maintainer lane** (handoffs, the provenance ledger, releases, the N=1 pipeline): in
   [AGENTS.md](../../AGENTS.md) for now. It moves to its own doc when AGENTS.md is split.

## Where things live

- **Reference and design, still maintained:** the loose `*.md` files in this directory, for
  example [RELEASE_ARC](RELEASE_ARC.md), [decisions](decisions.md) and the
  [docs IA design](docs-ia-design.md).
- **Records** (frozen history; never rewritten, never published): [`handoffs/`](handoffs/),
  [`ledger/`](ledger/), [`diagnosis/`](diagnosis/), [`blast-radius/`](blast-radius/),
  [`reviews/`](reviews/), [`perf/`](perf/), [`excellence-walk/`](excellence-walk/),
  [`flake-rates/`](flake-rates/), and [`archive/`](archive/) for retired designs.
  [`scripts/doc_registry.py`](../../scripts/doc_registry.py) is the single home of this list.
- **Where moved docs went:** [`moved-paths.json`](moved-paths.json).
- **Work tracking:** [`work/`](work/).
