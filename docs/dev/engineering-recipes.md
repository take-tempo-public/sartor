# Engineering recipes

> **Purpose:** the how-to for two jobs that recur in this codebase: adding or moving a route
> on a blueprint, and keeping a new or changed module inside the typing and docstring floors.
> It carries only the steps that no single test or config comment already states, and points
> at the file that enforces each rule.
> **Audience:** `dev` — anyone changing Sartor's routes or Python modules, human or agent.
> Read [AGENTS.md](../../AGENTS.md) first; this page assumes its security and prompt rules.
> **Authoritative for:** the order of the steps in the two recipes below. The rules themselves
> live in the files each step cites, and those files win on any disagreement.

Verified against `main` on 2026-10-18. Every claim here was checked against the file it cites
at that commit; a number that has no cite (a count, a version) was measured on that day and is
labelled as such.

## Add or move a route

`app.py` holds no routes. Every route attaches to a blueprint inside
[`register_blueprints`](../../app.py), which `create_app` calls (`app.py:52`, `app.py:87`).

1. **Put it on the blueprint that owns its domain.** One module per domain under
   [`blueprints/`](../../blueprints/); `corpus` is a sub-package whose lone `Blueprint` lives in
   `blueprints/corpus/_bp.py` so the route modules can import it without a cycle. Register a
   new blueprint in `register_blueprints`. The domain blueprints take no `url_prefix`, so a
   moved route keeps its URL (`app.py:58-84`); only the dashboard and assistant carry one
   (`app.py:54-55`).
2. **Read paths from `current_app.config`, never a module global.** `Config` is a frozen
   dataclass whose `as_flask_config()` produces the keys (`config.py:81`, `config.py:212`).
   A request handler reads them per request. A streaming handler reads them into locals
   *before* it defines the generator, because the generator runs after the handler returns and
   must not touch `current_app` (the pattern at `blueprints/analysis.py:147` and `:190`).
3. **Take shared helpers from `web_infra`, and keep it a leaf.** `web_infra` never imports
   `app.py`, a blueprint or `config.py`, so helpers there take an explicit `configs_dir`
   argument and the blueprint passes `current_app.config["CONFIGS_DIR"]`
   (`web_infra/__init__.py:9-14`, enforced by `tests/test_web_infra_is_leaf.py`).
4. **Decide where a helper lives by who calls it.** A helper only the moving routes call moves
   with them. A helper another blueprint also calls stays with the blueprint that owns that
   domain, and the other blueprint imports it. Sibling imports are fine while they stay
   acyclic: `generation` imports `templates`, `templates` imports `applications`,
   `applications` imports `corpus` (`blueprints/generation.py:60`, `blueprints/templates.py:57`,
   `blueprints/applications.py:68`). When an import would close a cycle, make it a
   function-local import, as `blueprints/users.py:306` does. A blueprint cannot import `app.py`.
   Do not leave a second copy of a helper behind.
5. **Guard every filesystem route.** `_safe_username` and `_within` on any route that
   touches a path ([AGENTS.md](../../AGENTS.md) "Security"). The edit hook is
   `scripts/enforcement/guards/route_security_lint.py`; its filesystem-indicator list is at
   `:27-30`, and `CONFIGS_DIR` is deliberately not on it, because a route reaches that only
   through `_safe_username(configs_dir=...)`. The whole-tree check that survives a hook miss is
   `tests/test_route_containment_gate.py`. If the hook false-positives on a partial edit, its
   own message says to include the full route block in the edit (`:32-38`).
6. **Annotate the handler `-> ResponseReturnValue`.** `blueprints.*` is on the strict mypy
   roster, so mypy checks the body. A `TypedDict` passed where a helper expects `dict` needs a
   `cast(...)` at the call site (`blueprints/generation.py:1213` casts a `ContextSet` to
   `dict[str, Any]`); do not retype the helper to fit. An `Any` returned from `json.loads` needs
   one too (`blueprints/diagnostics.py:154`).
7. **Add the module to the egress allowlist only if it imports `anthropic`.** The check is
   exact in both directions: a module that imports it and is missing fails, and so does a
   listed module that stopped importing it (`tests/test_egress_allowlist.py:121`,
   `:218-229`).
8. **Test it on the factory app.** Use the `app` and `client` fixtures
   (`tests/conftest.py:234`, `:252`), which build `create_app(Config(base_dir=tmp_path))`. A
   route resolves names such as `_get_client` from *its own module*, so a stub patches
   `blueprints.<seam>._get_client`, not `app`. For the UX tier, a blueprint that binds
   `_get_client` must be listed in `_GET_CLIENT_BLUEPRINT_MODULES` (`tests/ux/stubs.py:45`);
   `tests/test_ux_stub_coverage.py` fails when it is not, because an unlisted module would
   make a real, billed API call on a machine that has a key.
9. **When you move a block, prove the URL map did not change.** Before and after the move,
   print `sorted((r.rule, tuple(sorted(r.methods - {"HEAD", "OPTIONS"}))) for r in
   create_app(Config(base_dir=tmp)).url_map.iter_rules())` and diff the two. It read 125 rules
   on 2026-10-18. Only the endpoint names gain a `<blueprint>.` prefix; the frontend uses fixed
   URLs, so that is invisible to it.
10. **Edit large blocks by script, with asserted counts.** Replace exact code tokens (a bare
    `OUTPUT_DIR` also appears in comments and docstrings), assert how many replacements you
    expect, and after a move re-run `ruff check` for imports that only the moved routes used.
    On Windows, `Path.write_text` writes CRLF; write bytes if the file is LF, or later exact
    edits stop matching.

## Keep the typing and docstring floors green

The ratchets for these are finished. What remains is what a new or changed module has to
satisfy, and each item below is enforced somewhere that will tell you.

- **Typing.** A new `.py` outside `tests/` must be covered by the strict roster in
  `pyproject.toml` (the override block that carries `disallow_untyped_defs`, `pyproject.toml:485`).
  `tests/test_mypy_strict_roster_gate.py` fails if it is not, even though `mypy .` would pass.
  `strict` is not a per-module mypy option (`pyproject.toml:408`; on mypy 2.3.0,
  `"strict" in mypy.options.PER_MODULE_OPTIONS` is `False`), so the roster spells out the
  component flags. **To measure a module before rostering it, run
  `python -m mypy --strict --warn-unreachable <file>`:** `--strict` alone does not enable
  `warn_unreachable` (it is absent from `python -m mypy --help`'s `--strict` list), and the
  roster does.
- **Annotations.** `ANN` is selected for production code and waived for `tests/**`
  (`pyproject.toml:263`, `:293`). Measure production only before sizing a change; a tree-wide
  `--statistics` is dominated by the exempt trees.
- **Docstrings.** `D` with the google convention (`pyproject.toml:331`) blocks everywhere
  outside `tests/**`, and no per-module waiver remains (the comment above `:331` says when to
  bring one back). `interrogate` adds a floor on public-API coverage
  (`pyproject.toml:346-376`, `fail-under = 99`; `tests/test_docstring_coverage_gate.py`
  re-runs the same configuration). It counts public classes that `D101` misses, such as
  attribute-only and pydantic-model classes, so a clean `ruff check` does not mean a clean
  floor. Raise `fail-under` when coverage rises; never lower it.
- **Seeing a waived rule's true count.** Ruff can only *ignore* per file, not select per
  file, so a ratchet lists the modules still waived. A plain `ruff check` then reports zero
  for a waived module. To see the debt, clear the waivers for that run:
  `python -m ruff check <module> --select D101,D102,D103,D105,D107 --config
  "lint.per-file-ignores={}" --statistics` (it prints nothing when the module is clean).
  Delete the module's `per-file-ignores` line once it is clean.
- **The ruff version and its format check go together.** Ruff is exact-pinned
  (`pyproject.toml:106-113`) because it does not promise formatter-output stability across
  patch releases. Never add a `ruff format --check` step without the exact pin. Bump ruff as
  one commit: upgrade, `python -m ruff format .`, re-pin.
- **Commit-time ruff.** The commit guard checks the *staged* files, read before your command
  runs (`scripts/enforcement/guards/ruff_changed.py:84`). Observed 2026-10-17: formatting,
  staging and committing in one command was blocked, because the index still held the
  unformatted file ([the model-pricing-rates handoff](handoffs/model-pricing-rates.md),
  "Recurrences" row 3). Run `python -m ruff format <files>` and `git add` as one command,
  then `git commit` as the next. On a machine where `ruff` is not on `PATH`, use
  `python -m ruff` (the gate does: `scripts/gate.py`).
- **Proving a typing, docstring or formatting change left the prompts alone.** These changes
  are prompt-inert, so they need no `PROMPT_VERSION` bump and no paid eval, but the claim is
  worth proving for `analyzer.py` and any module that defines a prompt constant. Parse
  `HEAD:<file>` and the working copy with `ast`, take every top-level assignment whose name
  ends in `_PROMPT`, `_RULES_BLOCK` or `PROMPT_VERSION` (plus `_BASE_SYSTEM_PROMPTS`), hash
  `ast.dump(node.value)` for each, and compare the two maps. On 2026-10-18 this found 22
  names in `analyzer.py`; re-derive the set, do not trust that count. A documented module can
  hold a prompt of its own (`onboarding/extract_experiences.py` defines one), so check the
  files you touched, not only `analyzer.py`. Nothing in the repo runs this comparison for
  you; it is a step you do, and it is **unenforced**.
