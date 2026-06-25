# Importing your experience

> **Purpose:** the user-facing explanation of getting your history into callback —
> importing a résumé, pulling from your online profiles, and adding experiences by
> hand.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the corpus import control in `templates/index.html` (`#panelCorpus`,
> `#corpusIngestFile`) and the profile-fetch fields in the Settings drawer
> (`#btnFetchProfile`) driven by `static/app.js` (`uploadFile`, `fetchProfileContent`);
> the ingest route `ingest_resume_to_corpus` in `blueprints/corpus/curation.py`
> (parsing via `parser.py`, extraction via the Haiku `onboarding.extract_experiences`).

---

Everything callback writes comes from your **[[career-corpus]]** — the pool of your real
experience. There are three ways to fill it.

## Import a résumé
Import a résumé you already have (`.docx`, `.pdf`, or `.md`) and callback reads it and
extracts your roles and bullet points for you, so you don't start from a blank page. A
clean, **ATS-friendly** résumé — plain text, clear month/year dates — reads best.
Everything it pulls out starts as *pending review*, for you to accept (see
[[career-corpus]]).

## Pull from your online profiles
In **Settings** you can add links to your LinkedIn, website, or portfolio and let
callback fetch their public text, giving it more of your background to draw on. It reads
what's publicly there — nothing private.

## Add experiences by hand
You can also add roles and bullets yourself, or mix all three. However it gets in, your
corpus is yours and stays on this machine.

See [[using-callback]] for the whole first run, and [[managing-users]] for setting up a
profile first.
