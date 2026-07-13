# Security Policy

> **Purpose:** the threat model, accepted risks, and security guardrails
> for a local-first single-tenant tool. What is in scope to protect
> against, what is explicitly out of scope, how API keys flow, what
> never leaves the machine.
> **Audience:** humans considering deploying Sartor in a non-default
> tenancy model; contributors landing changes that touch routes, file
> I/O, or LLM call paths.
> **Authoritative for:** the `_safe_username` + `_within` route gates;
> what user-data files MUST stay gitignored; how to report a
> vulnerability. Sibling docs: [`CLAUDE.md`](CLAUDE.md) (contract),
> [`CONTRIBUTING.md`](CONTRIBUTING.md) (workflow).

## Scope

> **Canonical rule home.** The binding rules behind this policy — C-1 (local,
> single-tenant), C-2 (egress: exactly two sanctioned classes), the
> `_safe_username` / `_within` route gate, and the D-4 no-SLA commitment — live
> once in [`docs/governance/`](docs/governance/) (`charter.md` + `enforcement.md`).
> This document keeps the threat model, the accepted-risk register, and the
> operational detail; on any conflict the governance home governs.

Sartor is a **single-tenant, local-first tool**. It runs on your
machine, against your data, with one user (you). The threat model
assumes the server is running on localhost, accessible only to the
person who started it.

If you intend to run this on a shared network or server, additional
hardening is required (authentication, TLS, rate limiting, non-debug
mode). The current architecture does not support multi-user
operation and there are no plans to add it.

## Threat model

*Canonical: the two-class egress enumeration below is charter **C-2**; the
single-unauthenticated-user boundary is **C-1**.*

**In scope:**
- Local filesystem boundaries: `_safe_username()` + `_within()`
  enforce that file-touching routes only read/write paths owned by
  a known user under the expected parent directory. The
  `route-security-lint` PreToolUse hook enforces these helpers on
  every Edit/Write to `app.py` and the route-bearing blueprint
  modules under `blueprints/`.
- Path-traversal prevention: `werkzeug.utils.secure_filename()` on
  all user-supplied filenames; resolved-path containment via
  `_within(path, parent)`.
- API key handling: read from `.api_key` (gitignored) or
  `$ANTHROPIC_API_KEY`; never logged, never sent anywhere except
  to the Anthropic API.
- Prompt injection from job descriptions: mitigated by the
  system-prompt persona constraints in `analyzer.py`; the LLM
  returns structured JSON, not free-text that's executed.

**Out of scope (explicit non-goals):**
- Multi-user authentication / authorization. Not implemented;
  localhost is the boundary.
- TLS / CSRF / rate-limiting. Not implemented; same boundary.
- Sandbox isolation between user data on the same machine. The
  filesystem permissions of the OS are the boundary.
- Recovery from a compromised local machine. If your machine is
  compromised, Sartor is the least of your problems.

**What this tool does NOT do** (and never will, by design):
- No telemetry / analytics / error reporting to any external
  service.
- No HTTP calls beyond (a) the Anthropic API and (b) the optional
  profile/website scraper for the LinkedIn / portfolio URLs you
  provide (best-effort, fails gracefully). Job descriptions are
  always pasted text — a JD URL is stored as provenance only and
  is never fetched.
- No background updates / auto-installs / phone-home.
- No cross-candidate insights — the corpus and applications live
  only on your machine; the tool literally cannot compare you to
  other users because it cannot see them.

## Bundled third-party assets

Sartor vendors a small set of third-party files into the repo
so that the runtime stays offline-capable. None of these phone
home, none of these send data to third-party servers; each runs
locally — in your browser, the preview iframe, or (for the
test-tier asset) the local test runner.

- **`static/vendor/paged.polyfill.js`** — [paged.js](https://pagedjs.org/)
  v0.4.3, MIT-licensed. Loaded only by the in-browser preview
  iframe to render real Letter-sized page boundaries. The PDF
  render path (Playwright + Chromium) does NOT use this file;
  it handles `@page` CSS natively. Original copyright notice
  preserved at the top of the bundled file.
- **`static/vendor/chart.umd.min.js`** — [Chart.js](https://www.chartjs.org/)
  v4.4.0, MIT-licensed. Loaded by the diagnostics dashboard
  (`/_dashboard`); charts lazy-init on detail-open. Vendored
  (not fetched from a CDN) so the dashboard stays offline-capable;
  the byte content is the SHA-384-pinned 4.4.0 build. Original
  MIT notice preserved at the top of the bundled file.
- **`personas/bundled/*.html`** — Jinja2 résumé templates,
  some adapted from community jsonresume.org themes. Attribution
  + MIT license preserved in the header of each adapted file.
- **`personas/bundled/*.docx`** — generated programmatically by
  `scripts/build_bundled_templates.py`; not vendored from any
  upstream.
- **`tests/ux/a11y/vendor/axe.min.js`** — [axe-core](https://github.com/dequelabs/axe-core)
  v4.10.2, **MPL-2.0** (not MIT). **Test-tier only** — injected by
  the `pytest -m a11y` accessibility gate via Playwright; never
  loaded at runtime. Full notice preserved at the top of the file;
  see [`tests/ux/a11y/vendor/README.md`](tests/ux/a11y/vendor/README.md).

The repository's top-level `LICENSE` is MIT; the vendored assets
above carry their own licenses (MIT for paged.js / Chart.js;
**MPL-2.0** for the test-tier axe-core). A machine-readable
REUSE/SPDX manifest declaring this mix (PX-26) is committed at
[`REUSE.toml`](REUSE.toml) — a wildcard MIT annotation plus the one
axe-core MPL-2.0 override — with the full license texts under
[`LICENSES/`](LICENSES/). It resolves as a passing
[REUSE status badge](README.md) once the repo is pushed + promoted
public (the `reuse.software` API needs a public remote to check
against; the manifest itself is correct today and can be verified
locally with `pip install reuse && reuse lint`).

No external CDN is loaded at runtime. Every static asset in the
preview / generated output ships from the local repo.

## API key handling

Your Anthropic API key is sensitive. Follow these rules:

- **Never commit your API key.** The `.api_key` file is in
  `.gitignore` and must stay there.
- **Use environment variables in shared environments:**
  `export ANTHROPIC_API_KEY=your-key`
- **Rotate your key immediately** if you suspect exposure. Go to
  [console.anthropic.com](https://console.anthropic.com/) → API
  Keys → Revoke and regenerate.
- The `.api_key` file should have restrictive permissions on
  shared systems:
  ```bash
  chmod 600 .api_key
  ```

## User data residency

All user data stays on your machine in:

- `configs/{username}.config` — profile data (name, email,
  LinkedIn URL, portfolio URLs, notes)
- `resumes/{username}/` — uploaded source résumés
- `output/{username}/` — generated documents + analysis context
  JSON chains
- `db/resume.sqlite` — the structured corpus + applications +
  iteration history
- `logs/llm_calls.jsonl` — LLM telemetry (request bodies + responses)

All of these directories are gitignored. **Do not commit them.**
The `output/context_*.json` chain and `logs/llm_calls.jsonl`
contain your full résumé text, every job description you've
analyzed, and the LLM's responses including your candidate
identity — treat them as sensitive on disk.

## Reporting a vulnerability

*The best-effort, no-guaranteed-timeline posture below is charter **D-4**
(commitments hygiene): public docs make no response-time SLAs.*

If you discover a security issue:

1. **Do not open a public GitHub issue.**
2. Open a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories)
   on this repository (Security → Advisories → New draft advisory).
3. Include: description of the issue, steps to reproduce, potential
   impact, and any suggested fix.

This is a solo, best-effort project: I aim to acknowledge reports
and ship fixes as quickly as I can, but I can't promise a fixed
timeline.

## Known accepted risks

| Risk | Severity | Rationale |
|---|---|---|
| Flask debug mode on by default | Low | Local-only tool; debug mode provides useful error output for the single user. Set `FLASK_DEBUG=0` to disable. |
| No authentication | Low | Localhost only; OS-level access controls are the boundary. |
| Prompt injection via JD text | Low | Mitigated by system-prompt constraints; no sensitive data returned to attacker. |
| No `Content-Security-Policy` header | Low | Localhost-only tool; no third-party content is loaded (all assets are local). Confirmed v1.0.1: no `eval`, `new Function`, or string-form timer in `app.js` or `paged.polyfill.js`. The "CSP unsafe-eval" dev-console message observed 2026-05-26 was a downstream symptom of the sandboxed-iframe bug (resolved 2026-05-27); it was Chrome surfacing the `sandbox` block as a CSP-style error, not a server CSP violation. Add a real `Content-Security-Policy` header before any networked deployment. |
| LinkedIn / portfolio scraping blocked | Info | Not a security risk; sites may block the scraper, which fails gracefully. |
| Flask sessions disabled | Info | No login state to protect; no cookies issued. |
| JSON logs contain LLM responses | Info | `logs/llm_calls.jsonl` is sensitive; gitignored; lives only on your machine. |

## Error-detail disclosure policy

Several 5xx route handlers (`list_bundled_personas`,
`list_user_personas`, `list_experiences`, `list_summary_items`,
`list_applications`, `recommend_application_bullets`) wrap their
body in `try / except` with `logger.exception` and respond via
the `_error_detail_payload()` helper in
[`web_infra/http.py`](web_infra/http.py) (it moved out of `app.py`
in the 8.3a blueprint-split foundation; the routes import it).

The helper's behavior is **gated on `current_app.debug`** (the
same Flask flag, read via Flask's request-context proxy now that
the helper lives outside `app.py`):

- **Debug mode** (Flask's default for `python app.py` —
  controlled by `FLASK_DEBUG` defaulting to `1`): the response
  body includes a `detail` field with the exception class, the
  exception message, and the last 3 traceback frames. This is
  load-bearing for the dev-console smoke-debugging workflow —
  the developer opens dev tools, sees the response body, copies
  the traceback into a bug report without needing terminal
  access. Acceptable risk given local-only access.

- **Production mode** (`FLASK_DEBUG=0`): the `detail` field is
  suppressed. The response body returns only the generic
  `"error"` message plus a `request_id` (8 hex chars). The full
  traceback continues to land in the server log via
  `logger.exception()`, tagged with the same `request_id` so
  support can correlate (`grep <request_id> logs/`) without
  exposing internals to the response body.

**Why this is documented and not "just remove the detail":**
the application is positioned as local-first single-user, but
the same code paths may run behind reverse proxies or in
container deployments where leaking class names + paths to
unauthenticated callers would be a legitimate information-
disclosure issue. The gate is the contract; the gate's
mechanism is `current_app.debug`; turning debug off
(`FLASK_DEBUG=0`) in any non-local deployment is the operator's
responsibility.

If you intentionally want richer 5xx detail in a non-debug
deployment (e.g., a private staging environment with trusted
callers only), don't enable `unsafe-eval` or remove the gate —
instead set `FLASK_DEBUG=1` for that environment with a
documented rationale, or add a dedicated `SARTOR_VERBOSE_5XX`
flag that the helper consults. Don't drift the behavior
silently.

## Security architecture

*Canonical: the route guard pair is charter **C-1**; what is gate vs witness is in
[`docs/governance/enforcement.md`](docs/governance/enforcement.md).*

Path traversal is prevented in all file-serving routes via:

- `werkzeug.utils.secure_filename()` on all user-supplied filenames
  and usernames. Config filenames are canonicalized through it
  inside `_load_config()` / `_save_config()`, so a username resolves
  to its sanitized on-disk name even for a raw caller (e.g. `josé` →
  `jose`). Normal-flow users are already canonical — `create_user`
  sanitizes at creation — so only a hand-seeded raw-name config file
  would resolve differently.
- `_within(path, parent)` resolved-path containment checks before
  reading or writing any file
- `_safe_username()` which validates sanitization AND known-user
  existence before any filesystem operation

Enforcement is mechanical: the `route-security-lint` PreToolUse
hook in `.claude-plugin/hooks/` blocks Edit/Write operations on
`app.py` and the route-bearing blueprint modules under
`blueprints/` that touch the filesystem without `_safe_username()`
and `_within()` calls. (The read-only `dashboard/` diagnostics
surface is excluded by design — its routes are localhost-gated and
take no user-supplied path, so the user-path guards do not apply.)
This guarantees future routes inherit the pattern. The check itself
lives once in `scripts/enforcement/guards/route_security_lint.py`
and also runs as an opt-in native git `pre-commit` hook
(`.githooks/`, see `.githooks/README.md`) — enforcement is not
contingent on using the Claude Code plugin.
