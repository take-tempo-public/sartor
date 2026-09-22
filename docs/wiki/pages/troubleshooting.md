# Troubleshooting — when something goes wrong

> **Purpose:** the user-facing guide to errors — where sartor shows them, and the
> handful of common ones with what to do.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the status pill + error modal in `templates/index.html`
> (`#statusPill`, `#errorModal`) driven by `static/app.js` (`reportError`); the API-key
> lookup in `web_infra/clients.py` (`_get_client`); the PDF/Chromium requirement in
> `pdf_render.py` + `docs/install.md`; the date-grounding note in
> `blueprints/generation.py` (`_check_date_grounding`).

---

When something fails, sartor tells you — it doesn't fail silently.

## Where errors show up
The **status pill** at the top of the app turns red when something goes wrong. Click it
(or the error panel opens on its own) to read the details, with a **Copy** button so you
can keep the message or paste it when asking for help.

## Common things and what to do

Before diving into specifics, try **`sartor --doctor`** — it runs instantly without
downloading anything and reports Python version, OS, whether an API key is found, whether
PDF output can render, and whether the assistant's semantic search is built
(see [[machine-capability-preflight]]). It will tell you which optional features are
available and which need setup.

- **"Chromium not found" or the PDF button is greyed out.** Run `sartor --doctor`
  first — it says definitively whether Chromium is installed (see `preflight.py:chromium_capability`).
  [synthesis] On macOS 12, PDF output is unavailable because current Playwright releases
  ship no Chromium build for it — running the install command will not help. Sartor
  greys the PDF button out, with a note saying why, rather than offering an option it
  cannot deliver — the button stays visible so you can see it exists; use Word or Markdown
  output, or the live in-browser preview, which need no Chromium (see
  [[downloading-your-documents]]).
- **An API-key or authentication error.** sartor needs an Anthropic API key for the AI
  writing. Run `sartor --doctor` to check whether a key is found and where it came from
  (see `preflight.py:api_key_capability`). If missing, `sartor --setup` prompts for one
  without echoing it and writes it with owner-only permissions, so it never reaches
  your shell history — this is the recommended way. Alternatively, set the
  `ANTHROPIC_API_KEY` environment variable or create a `.api_key` file in the repo
  root. See `docs/install.md` §"API key" for details.
- **"Where did my data go?" — resumes, templates, and generated files.** Your data lives in
  a data directory (containing `configs/`, `resumes/`, `output/`, and the corpus database).
  [synthesis] The location depends on how you installed sartor: if you cloned the repo or ran
  `pip install -e .` (editable), it's at the repo root; if you ran `pip install sartor`
  (non-editable wheel), it's in your OS user-data folder (`%LOCALAPPDATA%\sartor` on
  Windows, `~/.local/share/sartor` on Linux, `~/Library/Application Support/sartor` on
  macOS). You can override the location by setting the `SARTOR_HOME` environment variable
  to any path you prefer (see `config.py:_default_base_dir`).
- **A "date check" note on your résumé.** sartor flags a date in the generated résumé
  that doesn't match your corpus and asks you to verify it before sending; your corpus
  dates were **not** changed. Read the note and confirm the dates are right.

If a step just errors out, it may be a temporary network hiccup — try it again. If it
keeps happening, the error panel's **Copy** button gives you the exact message to share
when reporting it. See [[using-sartor]] for the basics.
