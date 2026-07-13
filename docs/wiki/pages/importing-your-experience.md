# Importing your experience

> **Purpose:** the user-facing explanation of getting your history into sartor —
> importing a résumé, pulling from your online profiles, and adding experiences by
> hand.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the corpus import control in `templates/index.html` (`#panelCorpus`,
> `#corpusIngestFile`) and the profile-fetch fields in the Settings drawer
> (`#btnFetchProfile`) driven by `static/app.js` (`uploadFile`, `fetchProfileContent`);
> the ingest route `ingest_resume_to_corpus` in `blueprints/corpus/curation.py`
> (parsing via `parser.py`, extraction via the Haiku
> `onboarding.extract_experiences_and_skills`).

---

Everything sartor writes comes from your **[[career-corpus]]** — the pool of your real
experience. There are three ways to fill it.

## Import a résumé
Import a résumé you already have (`.docx`, `.pdf`, or `.md`) and sartor reads it and
extracts your roles, bullet points, **and skills** for you, so you don't start from a
blank page. A clean, **ATS-friendly** résumé — plain text, clear month/year dates —
reads best. Everything it pulls out starts as *pending review*, for you to accept (see
[[career-corpus]]) — including any skills it found in a dedicated Skills/Technologies
section, which now land as pending Skill entries too, so a freshly-imported résumé no
longer leaves your Skills section empty `[synthesis]` (grounded in
[`onboarding/extract_experiences.py`](../../../onboarding/extract_experiences.py)'s
`extract_experiences_and_skills` and `onboarding/corpus_import.py`'s
`_insert_pending_skills`, wired through the same
[`blueprints/corpus/curation.py`](../../../blueprints/corpus/curation.py) ingest route).

After import, sartor scans for roles that look like duplicates — the same job listed
twice with different dates or titles — and shows you a **Possible duplicate roles**
section where you can merge them into one (the extra title becomes an alternate) or
keep them separate. The **Find duplicates** button lets you also manually scan for
near-duplicate bullet points across all your roles `[synthesis]` (grounded in
`static/app.js`'s `refreshMergeSuggestions` called post-import and `loadCorpusDuplicates`
for manual scan, backed by `blueprints/corpus/curation.py`'s `/api/users/<username>/corpus/merge-suggestions` and `/api/users/<username>/duplicates` routes).

## Pull from your online profiles
In **Settings** you can add links to your LinkedIn, website, or portfolio and let
sartor fetch their public text, giving it more of your background to draw on. It reads
what's publicly there — nothing private.

## Add experiences by hand
You can also add roles and bullets yourself, or mix all three. However it gets in, your
corpus is yours and stays on this machine.

See [[using-sartor]] for the whole first run, and [[managing-users]] for setting up a
profile first.
