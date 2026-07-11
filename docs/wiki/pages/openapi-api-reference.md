# OpenAPI spec emission (spectree Layer B)

> **Audience:** `dev`
> **Concept:** the spectree-based OpenAPI wiring that turns five read-only GET
> routes into a generated, versioned API spec — a scoped documentation aid, not
> a request/response validation layer.
> **Sources:** [`web_infra/openapi.py`](../../../web_infra/openapi.py),
> [`scripts/generate_openapi_spec.py`](../../../scripts/generate_openapi_spec.py),
> [`blueprints/users.py`](../../../blueprints/users.py),
> [`blueprints/corpus/experiences.py`](../../../blueprints/corpus/experiences.py),
> [`blueprints/applications.py`](../../../blueprints/applications.py),
> [`.github/workflows/docs-deploy.yml`](../../../.github/workflows/docs-deploy.yml).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What this is (and isn't)

"Layer B" of the kit-adoption spectree wiring adds machine-readable OpenAPI
documentation over a deliberately small slice of the route surface — **five**
read-only `GET` routes out of **117** total (`grep -rE "@[a-zA-Z_]+\.route\("
blueprints/ dashboard/ app.py` `[synthesis]`) — without touching the other 112
routes or adding request-side validation anywhere. Every decorated route also
passes
`skip_validation=True`
([`web_infra/openapi.py`](../../../web_infra/openapi.py) module docstring), so
the response models below are a **documentation aid**, not a runtime contract:
an under-specified or slightly-wrong model cannot 500 a real request
`[synthesis]`. This is a narrower, additive scope than "the route surface has
OpenAPI validation" — see [[route-surface]] for the full route inventory this
sits alongside.

## `web_infra/openapi.py` — the shared `spec` instance

One module-level `SpecTree("flask", ...)` instance,
[`web_infra/openapi.py:spec`](../../../web_infra/openapi.py), decorated onto
route functions via `@spec.validate(resp=..., skip_validation=True, tags=[...])`.
Two config choices matter:

- **`mode="strict"`** — spectree's default ("normal") mode would also collect
  every *undecorated* route with an empty/schema-less entry, misrepresenting
  the other 112 routes as "documented" (the module docstring's own estimate,
  written when the route count was lower, says "~85" — the wiki cites the
  live-verified count instead `[synthesis]`). `strict` mode restricts spec
  collection to only the routes this `spec` instance actually decorates
  `[synthesis]`.
- **`annotations=False`** — opts out of spectree's function-signature-driven
  validation mode; every decorated route passes `resp=`/`skip_validation=`
  explicitly rather than typed view-function params, which also silences a
  `skip_validation`-vs-`annotations` warning that mode emits by default.

Response models follow a **permissive-base convention**
([`web_infra/openapi.py:_PermissiveModel`](../../../web_infra/openapi.py),
`extra="allow"`) — the module docstring is explicit that this mirrors
`analyzer.py`'s `_LLMResponse` pattern but must **not reuse** those LLM-response
models: these describe deterministic route JSON, not LLM output. Two response
shapes are **unions** (bare array on success vs. a discriminated
`{..., "needs_onboarding": true}` object) —
[`ExperiencesListResponse`](../../../web_infra/openapi.py) and
[`ApplicationsListResponse`](../../../web_infra/openapi.py) — modeled as
`RootModel[list[Item] | NeedsOnboarding]`; an imperfect union is safe by
construction because of `skip_validation=True` `[synthesis]`.

`web_infra/openapi.py` makes no LLM calls and is P1-deterministic by its own
docstring (charter C-6) — it is not, however, one of the eight modules AGENTS.md
names as the canonical deterministic floor (see [[deterministic-llm-boundary]]);
it is a `web_infra/` leaf module instead (see [[code-module-map]]).

## The five decorated routes

Exactly these, one `@spec.validate(...)` call site each, `tags=["users"|"corpus"|"applications"]`:

| Route | Handler | Response model |
|---|---|---|
| `GET /api/users` | [`blueprints/users.py:list_users`](../../../blueprints/users.py) | `UsersListResponse` (bare `jsonify(users)` array) |
| `GET /api/users/<username>/config` | [`blueprints/users.py:get_config`](../../../blueprints/users.py) | `UserConfigResponse` |
| `GET /api/users/<username>/experiences` | [`blueprints/corpus/experiences.py:list_experiences`](../../../blueprints/corpus/experiences.py) | `ExperiencesListResponse` (union) |
| `GET /api/users/<username>/applications` | [`blueprints/applications.py:list_applications`](../../../blueprints/applications.py) | `ApplicationsListResponse` (union) |
| `GET /api/applications/<application_id>` | [`blueprints/applications.py:get_application`](../../../blueprints/applications.py) | `ApplicationDetail` |

`ApplicationDetail.resume_state` is left as a permissive `dict[str, Any]`
rather than fully modeled — `_build_resume_state`'s keys legitimately vary by
which wizard step is furthest reached, so the model is a first approximation,
not a contract `[synthesis]`. Every decorated route still runs its normal
`_safe_username` / `_within` security gate unchanged (see [[route-surface]]) —
spectree decoration is additive and does not touch the request-handling body,
by design (the module docstring calls out that adding request-side validation
would require rewriting route bodies to read `request.context.json` instead of
`request.json` — "the exact edit class that once dropped `_within` in the 8.3
blueprint split," per `tests/test_route_containment_gate.py` — so Phase 1
deliberately stays response-only).

## The generator: `scripts/generate_openapi_spec.py`

A standalone, deterministic script (no LLM, no network) that turns the
decoration into an actual JSON artifact:

- [`scripts/generate_openapi_spec.py:build_spec`](../../../scripts/generate_openapi_spec.py)
  builds its **own** `create_app(Config(base_dir=<tempdir>))` instance (never
  touches real `configs/`/`resumes/`/`output/`), calls `spec.register(app)` on
  it, and reads the cached `spec.spec` dict inside an app context — no HTTP
  server, no network call.
- [`scripts/generate_openapi_spec.py:main`](../../../scripts/generate_openapi_spec.py)
  self-checks that all five expected paths
  ([`scripts/generate_openapi_spec.py:_EXPECTED_PATHS`](../../../scripts/generate_openapi_spec.py))
  are present, then writes sorted, pretty-printed JSON to
  `docs-site/openapi.json` — a **gitignored build artifact**, not a second
  source of truth (`.gitignore` "docs-site/openapi.json is FULLY GENERATED by
  scripts/generate_openapi_spec.py").

## CI wiring (Phase 2 — rendering, out of wiki scope)

[`.github/workflows/docs-deploy.yml`](../../../.github/workflows/docs-deploy.yml)
runs `python scripts/generate_openapi_spec.py` as a step ("Generate OpenAPI
spec") before the Fumadocs build, explicitly ordered before the Node-side
"Generate API reference docs" step (`docs-site/scripts/generate-api-docs.mjs`,
which reads `docs-site/openapi.json` and projects it into MDX via
`fumadocs-openapi`). That rendering step and everything under `docs-site/` is
an **L3 projection** of this JSON, not a wiki source — out of scope here per
[`SCHEMA.md`](../SCHEMA.md)'s source model; see
[`docs/dev/documentation-architecture.md`](../../dev/documentation-architecture.md)
for the L0–L3 layering (cited, not restated — D5).

## Related

- [[route-surface]] — the full `blueprints/` route inventory; these five
  routes are a subset, unchanged in behavior by this decoration.
- [[code-module-map]] — where `web_infra/openapi.py` sits among the
  `web_infra/` leaf modules.
- [[deterministic-llm-boundary]] — the P1 boundary this module satisfies by
  its own docstring, without being one of the eight AGENTS.md-named modules.
- [[consistency-tracks-enforcement]] — `mode="strict"` + the 5-path self-check
  in `generate_openapi_spec.py` are another instance of "consistency tracks
  enforcement": the spec can't silently over- or under-claim coverage.
