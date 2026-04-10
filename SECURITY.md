# Security Policy

## Scope

Resume Optimizer is a **local single-user tool**. It is not designed to be exposed to the internet or run as a shared service. The threat model assumes the server is running on localhost, accessible only to the person who started it.

If you intend to run this on a shared network or server, additional hardening is required (authentication, TLS, rate limiting, non-debug mode).

## API Key Handling

Your Anthropic API key is sensitive. Follow these rules:

- **Never commit your API key.** The `.api_key` file is in `.gitignore` and must stay there.
- **Use environment variables in shared environments:** `export ANTHROPIC_API_KEY=your-key`
- **Rotate your key immediately** if you suspect it has been exposed. Go to [console.anthropic.com](https://console.anthropic.com/) → API Keys → Revoke and regenerate.
- The `.api_key` file should have restrictive permissions on shared systems:
  ```bash
  chmod 600 .api_key
  ```

## User Data Privacy

All user data (resumes, configs, generated output) is stored locally in:
- `configs/{username}.config` — profile data (name, email, LinkedIn URL)
- `resumes/{username}/` — uploaded resume files
- `output/{username}/` — generated documents and analysis context JSON

These directories are gitignored. **Do not commit them.** The `output/context_*.json` files contain your full resume text and job description — treat them as sensitive.

## Reporting a Vulnerability

If you discover a security issue:

1. **Do not open a public GitHub issue.**
2. Open a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories) on this repository (Security → Advisories → New draft advisory).
3. Include: description of the issue, steps to reproduce, potential impact, and any suggested fix.

We aim to respond within 5 business days and to issue a fix within 30 days of confirmation.

## Known Accepted Risks

| Risk | Severity | Rationale |
|---|---|---|
| `debug=True` in Flask | Low | Local-only tool; debug mode provides useful error output for the single user |
| No authentication | Low | Localhost only; OS-level access controls are the boundary |
| Prompt injection via JD text | Low | Mitigated by system prompt constraints; no sensitive data returned to attacker |
| LinkedIn scraping blocked | Info | Not a security risk; sites may block the scraper, which fails gracefully |

## Security Architecture

Path traversal is prevented in all file-serving routes via:
- `werkzeug.utils.secure_filename()` on all user-supplied filenames and usernames
- `_within(path, parent)` resolved-path containment checks before reading or writing any file
- `_safe_username()` which validates both sanitization and known-user existence before any filesystem operation
