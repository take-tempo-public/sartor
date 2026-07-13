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
- **"Chromium not found" when downloading a PDF.** PDF output needs a one-time browser
  download — run `python -m playwright install chromium`. Word and Markdown downloads
  don't need it (see [[downloading-your-documents]]).
- **An API-key or authentication error.** sartor needs an Anthropic API key for the AI
  writing; it reads one from the `ANTHROPIC_API_KEY` environment variable or a local
  `.api_key` file. If you see an auth error, check that the key is present and valid —
  `docs/install.md` covers the setup.
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
