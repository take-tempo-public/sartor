# Machine capability preflight

> **Audience:** `dev`
> **Concept:** before runtime failures, ask what capabilities this machine has —
> Python floor, OS version, Chromium (PDF), the vector index, and the API key — via
> a deterministic, tri-state probe suite with no network/LLM/browser launch.
> **Sources:** [`preflight.py`](../../../preflight.py), [`app.py`](../../../app.py),
> [`blueprints/users.py`](../../../blueprints/users.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The motivation (why this module exists)

Items 100/102/103/104 documented four symptoms of one absence: the codebase had
no way to ask "is this capability actually available *here*?" before committing to
a path. Each symptom surfaced instead as a *runtime* failure, one at a time.
The worst case (item 100 on macOS 12.7.4) was five consecutive failures before
a `--log-level=debug` run finally revealed "unsupported macOS version"
(`docs/dev/work/items/0100-install-prereqs-no-version-floors.md`). The preflight
module answers these questions up front, cheaply, and — where it cannot — says so
rather than guessing.

## The design: tri-state probes

Every probe returns `Capability` with an `ok` field that is **tri-state**: `True`
(available), `False` (unavailable), or `None` (could not determine). This is
deliberate and load-bearing [`preflight.py:preflight.Capability`](../../../preflight.py).

Collapsing unknown into either boolean is how a preflight starts lying: unknown
treated as `False` hides a feature that works; unknown treated as `True` reproduces
the very bug the probe exists to prevent. The resolution of unknown — which way to
lean — is made *at the call site*, where the cost of being wrong is known
`[synthesis]`. The codebase makes that decision in exactly one place today — see
"PDF gating in the app shell" below for which way it leans and why.

## Probes and their consumers

**Python runtime:** [`python_capability()`](../../../preflight.py)
checks `sys.version_info` against `PYTHON_FLOOR` (3.11+, mirrored from `pyproject.toml`)
— returned as `Capability` with either the current version or the floor + remedy.
Consumed by `--doctor`, and by `run_doctor()`, which exits 1 only if Python is too old
(everything else is a warning).

**OS version:** [`os_capability()`](../../../preflight.py) reports the system and
version. It **deliberately asserts only floors this project measured** — currently,
macOS 13.0+ (the container-path Podman `applehv` backend requirement and
Playwright-Chromium support floor, both items 100/103). For Windows and Linux,
it reports "no measured floor" rather than inventing one [`preflight.py:os_capability`](../../../preflight.py).

**Chromium (PDF output):** [`chromium_capability()`](../../../preflight.py)
checks **both** chromium artifacts because they are genuinely different files and the
PDF path needs one you would not guess by name. `render_pdf()` calls
`p.chromium.launch()` with no `headless` argument and takes the headless default,
needing `chromium_headless_shell-<rev>`; `chromium.executable_path` names the headed
`chromium-<rev>`. A probe that stats only the headed path reports "available" for a
partial install that cannot render a PDF — and chromium is five artifacts, so partial
is real. The two-artifact check catches this [`preflight.py:chromium_capability`](../../../preflight.py).

The cost discipline: the probe reads `driver/package/browsers.json` directly and stats
two marker files instead of calling the Playwright API. Measured on this machine
(2026-09-03) — `docs/dev/diagnosis/install-onboarding-preflight.md` O-5:
- browsers.json + 2 stats (the probe):  **8.4 ms**
- `sync_playwright()` + `chromium.executable_path`:  **~2912 ms** (the API path)
- real `launch() + close()`: **14369 ms** with Chromium present, **324 ms** without
  (it fails fast) — the probe's two arms, not headed vs headless

The Playwright API path is slow because entering `sync_playwright()` spawns a Node
driver process. Reading the *driver's own* `browsers.json` directly is ~350x cheaper
and checks *more* (both artifacts). Anything in this module that reaches for the
Playwright API is a regression, not a cleanup [`preflight.py` module docstring](../../../preflight.py).

**Semantic recall index:** [`vector_index_capability()`](../../../preflight.py)
checks for the presence of `embeddings.npy`, `chunks.json`, and `model/` in `db/vector_index/`.
This is a degraded-feature case: the assistant runs on lexical tiers without this
`[synthesis]`. Consumed by `--doctor` and `--setup` (the setup step rebuilds it if missing).

**API key:** [`api_key_capability()`](../../../preflight.py)
mirrors the app's own resolution order — `ANTHROPIC_API_KEY` env var first, then
`.api_key` file. The value **is** read (testing "is there a non-blank key here" requires
looking at it); what is guaranteed is narrower and is the part that matters — it never
reaches `detail`, `remedy`, a log, or a return value, so nothing a caller can print
carries it [`preflight.py:api_key_capability`](../../../preflight.py). Consumed by `--setup`,
which prompts via `getpass` (no echoing, no shell history) when a key does not resolve
and stdin is a tty.

**Container engine:** [`container_capability()`](../../../preflight.py)
checks whether `podman` or `docker` is on `PATH`. Deliberately does not run
`podman info` to test the machine is *started* — that can hang on a broken VM,
and the failure it would catch is better reported by Podman itself than guessed here
`[synthesis]`. Only needed for the container install path.

## Consumers and dispatch

**`sartor --doctor`** (item 100) — calls [`run_doctor()`](../../../preflight.py),
which calls [`probe_all()`](../../../preflight.py), formats the results, and prints them
with remedies grouped at the end.

**`sartor --setup`** (item 104) — calls [`_run_setup()`](../../../app.py) which:
- First calls [`_prompt_for_api_key()`](../../../app.py) — only if `api_key_capability().ok` is falsy
  and stdin is a tty (refusal guards: never re-prompts a working key, never blocks on
  non-interactive stdin).
- Then subprocess-runs `python -m playwright install chromium` and `scripts.build_vector_index`.
- Reports degraded features separately (item 102): if Chromium fails but the index succeeds,
  the user learns they have working search but no PDF `[synthesis]`.

**PDF gating in the app shell** — [`blueprints/users.py:index()`](../../../blueprints/users.py)
calls [`pdf_available()`](../../../preflight.py), which returns a boolean. This is the one
call site where unknown is resolved: it leans `True` (available). The asymmetry: a false
"unavailable" hides the feature from every user with no way to discover it should be there;
a false "available" merely restores today's behavior — the PDF attempt fails with an error
the route already surfaces. The unknown case exists precisely because the probe reads an
*internal* Playwright layout, so a future Playwright reshuffle must degrade to today's
behavior, not to silent blackout [`preflight.py:pdf_available`](../../../preflight.py).

## Determinism and stated limits

**Deterministic by construction:** no LLM call, no network, no browser launch, no new
dependency (charter D-1). Every probe is filesystem/stdlib only
([`preflight.py`](../../../preflight.py) module docstring). Note this is a *property of
the module*, not membership in the C-6 boundary: `AGENTS.md`'s enumerated
deterministic-boundary list names eight modules and `preflight.py` is not one of them
`[synthesis]`.

**Stated limits (C-0):**
- The `INSTALLATION_COMPLETE` sentinel checked by `chromium_capability()` is an internal
  Playwright layout detail, not a documented API. If Playwright stops using it,
  the probe degrades to `None` rather than guessing.
- The 0o600 file mode used by [`_write_api_key()`](../../../app.py) is largely inert on
  Windows — the ACL is the real control there, and this does not attempt to set one.

## Related

- [[document-rendering]] — the Chromium path that uses the capability probe.
- [[downloading-your-documents]] — user-facing PDF format choice and what PDF needs.
- [[troubleshooting]] — where Chromium-missing errors surface to users.
- [[non-dependency-downloads]] — the Chromium and model weights downloads this probes for.
- [[code-module-map]] — where `preflight.py` sits in the module tree.
