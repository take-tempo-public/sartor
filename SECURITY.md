# Security Policy

## Scope

callback. is a **single-tenant, local-first tool**. It runs on your
machine, against your data, with one user (you). The threat model
assumes the server is running on localhost, accessible only to the
person who started it.

If you intend to run this on a shared network or server, additional
hardening is required (authentication, TLS, rate limiting, non-debug
mode). The current architecture does not support multi-user
operation and there are no plans to add it.

## Threat model

**In scope:**
- Local filesystem boundaries: `_safe_username()` + `_within()`
  enforce that file-touching routes only read/write paths owned by
  a known user under the expected parent directory. The
  `route-security-lint` PreToolUse hook enforces these helpers on
  every Edit/Write to `app.py`.
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
  compromised, callback. is the least of your problems.

**What this tool does NOT do** (and never will, by design):
- No telemetry / analytics / error reporting to any external
  service.
- No HTTP calls beyond (a) the Anthropic API, (b) the URL scraper
  for LinkedIn / portfolio URLs (best-effort, fails gracefully),
  and (c) any URL you explicitly paste as a job description.
- No background updates / auto-installs / phone-home.
- No cross-candidate insights — the corpus and applications live
  only on your machine; the tool literally cannot compare you to
  other users because it cannot see them.

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

If you discover a security issue:

1. **Do not open a public GitHub issue.**
2. Open a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories)
   on this repository (Security → Advisories → New draft advisory).
3. Include: description of the issue, steps to reproduce, potential
   impact, and any suggested fix.

We aim to respond within 5 business days and to issue a fix within
30 days of confirmation.

## Known accepted risks

| Risk | Severity | Rationale |
|---|---|---|
| Flask debug mode on by default | Low | Local-only tool; debug mode provides useful error output for the single user. Set `FLASK_DEBUG=0` to disable. |
| No authentication | Low | Localhost only; OS-level access controls are the boundary. |
| Prompt injection via JD text | Low | Mitigated by system-prompt constraints; no sensitive data returned to attacker. |
| LinkedIn / portfolio scraping blocked | Info | Not a security risk; sites may block the scraper, which fails gracefully. |
| Flask sessions disabled | Info | No login state to protect; no cookies issued. |
| JSON logs contain LLM responses | Info | `logs/llm_calls.jsonl` is sensitive; gitignored; lives only on your machine. |

## Security architecture

Path traversal is prevented in all file-serving routes via:

- `werkzeug.utils.secure_filename()` on all user-supplied filenames
  and usernames
- `_within(path, parent)` resolved-path containment checks before
  reading or writing any file
- `_safe_username()` which validates sanitization AND known-user
  existence before any filesystem operation

Enforcement is mechanical: the `route-security-lint` PreToolUse
hook in `.claude-plugin/hooks/` blocks Edit/Write operations on
`app.py` that touch the filesystem without `_safe_username()` and
`_within()` calls. This guarantees future routes inherit the
pattern.
