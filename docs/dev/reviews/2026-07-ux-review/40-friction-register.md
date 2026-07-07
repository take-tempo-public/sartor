# 40 — Friction Register

> The consolidated, prioritized list of every friction point found, each with
> the persona(s) it hits, a severity, a **verification verdict** (each claim was
> adversarially checked against the code — see the method note in the
> [README](README.md)), a code anchor where relevant, and a remediation.
>
> **Verdict legend:** `CONFIRMED` — grounded in code/observation as stated.
> `SHARPENED` — the underlying issue is real but the precise framing was
> corrected during verification (the corrected framing is what's written here).
> `OBSERVED` — seen live in the walkthrough (UX judgment, not a code claim).

## Priority index

Severity is impact × likelihood for the affected persona; **P0** = fix before a
public launch, **P1** = high-value polish, **P2** = nice-to-have.

| ID | Friction | Persona | Sev | Verdict |
|---|---|---|---|---|
| F-01 | "Keyword Match Score" deflated by counting company name + generic words as missing | Seeker, Headhunter | P0 | CONFIRMED |
| F-02 | Résumé import doesn't create any skills | Seeker, Headhunter | P0 | CONFIRMED |
| F-11 | Eval harness scores an LLM `generate` path the UI no longer uses | Technical | P0 | SHARPENED |
| F-24 | `install.md` verify step runs pytest/ruff but never installs `[dev]` | Technical | P0 | CONFIRMED |
| F-25 | `install.md` OS walkthroughs skip `sartor --setup` (recall index unbuilt) | Technical | P0 | CONFIRMED |
| F-26 | `pyproject.toml` `py-modules` omits 4 shipped modules (packaging/PyPI) | Technical | P0 | CONFIRMED |
| F-08 | Candidate picker is a flat username `<select>` — no roster/search/status | Headhunter | P1 | CONFIRMED |
| F-12 | Analyze screen is a dense wall with no progressive disclosure | Seeker | P1 | OBSERVED |
| F-03 | Two "skills" homes; the flat profile field goes inert after first import | Seeker | P1 | SHARPENED |
| F-04 | Education/certifications have no corpus panel (flat Settings fields only) | Seeker | P1 | SHARPENED |
| F-15 | Applications show null company / generic title (JD employer not captured) | Seeker, Headhunter | P1 | OBSERVED |
| F-10 | Résumé download can silently fail in Chrome (documented in-app) | Seeker, Headhunter | P1 | OBSERVED |
| F-06d | Dashboard "RELIABILITY 0%" tile shows error rate under a reliability label | Technical | P1 | CONFIRMED |
| F-23 | Wizard sits below the user picker + full applications list on the Tailor tab | Seeker, Headhunter | P1 | CONFIRMED |
| F-21 | README/docs conflate *using* vs *developing* vs *extending* | Technical | P1 | CONFIRMED |
| F-19 | No offline/demo mode — a billed API key is required to see anything | Technical | P1 | OBSERVED |
| F-16 | Personas are per-candidate; a house template must be re-uploaded each time | Headhunter | P1 | CONFIRMED |
| F-17 | No cross-candidate pipeline view | Headhunter | P1 | OBSERVED |
| F-22 | Model-routing docs drifted from code (Sonnet 4.6 → Sonnet 5 / Haiku 4.5) | Technical | P1 | CONFIRMED |
| F-05 | "Username" is the first thing a new user must invent | All | P2 | OBSERVED |
| F-06 | Post-create tab jump (Tailor → Corpus) is unexplained in the moment | Seeker | P2 | OBSERVED |
| F-07 | Native `confirm()` dialogs (10 sites) clash with the custom-modal aesthetic | Seeker, Headhunter | P2 | CONFIRMED |
| F-09 | Deterministic, reproducible Generate is a strength that's never surfaced | Seeker | P2 | SHARPENED |
| F-13 | Compose gap-fill bullets don't read as optional | Seeker | P2 | OBSERVED |
| F-14 | "You edited the preview" gate modal — surprising timing, dense wording | Seeker | P2 | OBSERVED |
| F-18 | Auto-open browser + `FLASK_DEBUG=1` default surprises a dev/container run | Technical | P2 | CONFIRMED |
| F-20 | Documented eval smoke cost (~$0.10) is stale — actual ~$0.37 post-upgrade | Technical | P2 | CONFIRMED |
| F-27 | README doc-polish bundle (Install buried, `git` prereq, jargon, "5 min") | Technical | P2 | CONFIRMED |

---

## P0 — fix before a public launch

### F-01 · The headline "Keyword Match Score" is deflated
**Persona:** job seeker (trust), headhunter (shareability). **Verdict:** CONFIRMED.
Observed live: a strong SRE-to-SRE match scored **18%**, and the "KEYWORDS MISSING
FROM RESUME" set included **"lattice" / "lattice cloud"** (the hiring company's
name) and generic words ("hiring," "drive," "serving"). The keyword-overlap logic
is in `hardening.py:238-245`, where `STOP_WORDS` is only ~65 classic English
function words — **no company-name or JD-boilerplate filtering**. So the employer's
own name and filler count against the candidate, and the most prominent number on
the first gate reads far worse than the true fit.
**Remediation:** (a) strip the hiring company/entities and a JD-boilerplate
stoplist from the keyword universe before scoring; (b) reconsider showing a raw
literal-overlap percentage at all — either weight by the *essential* skills the
analysis already extracts, or reframe the number as "keywords you could add"
rather than a score that implies a grade. This is the single highest-leverage fix.

### F-02 · Résumé import creates no skills
**Persona:** job seeker, headhunter. **Verdict:** CONFIRMED. The ingest path
(`blueprints/corpus/curation.py:398-477` → `onboarding` extraction) creates
Experiences, ExperienceTitles, Bullets, and role-intro summary variants — but
never Skill rows. A freshly imported user has an empty Skills section, so the
Compose skills card doesn't appear and skills silently drop out of the tailored
output unless the user notices and adds them by hand.
**Remediation:** extract a skills list during import (the model already reads the
whole résumé) and create pending Skill rows for review, exactly like bullets.

### F-11 · The eval harness measures a generation path the UI doesn't use
**Persona:** technical. **Verdict:** SHARPENED. On the UI happy path the résumé
body is assembled **deterministically** from the frozen composition
(`generation.py:585-603`, `_frozen_composition`). But `evals/runner.py` runs
`analyze → clarify → generate` where `generate` calls `analyzer.generate()` (a
real ~27 s Sonnet call) — i.e. the harness exercises the **fallback/legacy** path,
not the frozen-composition assembly users actually download. The analyze/clarify
signal is still valid; the "generation quality" rubric is measuring something the
primary flow bypasses.
**Remediation:** either add an eval path that drives compose → freeze → assemble
(so the rubric matches shipped output), or document the divergence prominently so
no one over-trusts the generate rubric as a proxy for user-visible quality.

### F-24 · `install.md` verify step needs deps it never installs
**Persona:** technical. **Verdict:** CONFIRMED. `docs/install.md:402-420` tells a
new installer to run `python -m pytest -q` (expecting "1200+ passed") and
`python -m ruff check .` — but the install steps only run `pip install -e .`, not
`pip install -e '.[dev]'`, so pytest/ruff aren't present. The verification step
fails on a clean install.
**Remediation:** add `[dev]` to the install command in the verify section (or gate
the verify step behind it).

### F-25 · OS walkthroughs skip `sartor --setup`
**Persona:** technical. **Verdict:** CONFIRMED. `docs/install.md:73-83` documents
`sartor --setup` as the canonical bootstrap (Chromium for PDF + the semantic-recall
index), but the per-OS walkthroughs don't call it, so a reader who follows an OS
section gets an app whose PDF export and recall assistant are unbuilt.
**Remediation:** make `sartor --setup` an explicit step in every OS path.

### F-26 · `pyproject.toml` omits four shipped modules from the package
**Persona:** technical (and the release gate). **Verdict:** CONFIRMED.
`[tool.setuptools] py-modules` (`pyproject.toml:113`) lists only
`["app","analyzer","config","hardening","generator","parser","scraper"]`, omitting
four top-level deterministic modules that are imported at runtime
(`json_resume`, `corpus_to_json_resume`, `pdf_render`, `docx_to_persona_html`). A
`pip install`ed wheel would be missing them. This is likely the same class of gap
the release workflow's PyPI job is currently (deliberately) failing on.
**Remediation:** add the four modules (or switch to package discovery) and verify a
built wheel imports and runs.

---

## P1 — high-value polish

### F-08 · The candidate picker doesn't scale
**Persona:** headhunter. **Verdict:** CONFIRMED (`templates/index.html:87-90` — a
plain `<select id="userSelect">` populated by `loadUsers()` at
`static/app.js:73-84`; no search, no per-candidate metadata, no roster view; there
is no second template file). Fine for a job seeker with one profile; a wall for a
recruiter with many candidates.
**Remediation:** a candidate roster surface — searchable, showing target
role/company and pipeline stage per candidate — layered on the existing per-user
model. See the polish plan's "recruiter tier."

### F-12 · The Analyze screen is a firehose
**Persona:** job seeker. **Verdict:** OBSERVED. Everything (score, 4 chip clouds,
strengths/gaps prose, per-experience suggestions, keyword-placement suggestions,
overall strategy) is expanded at once. It's genuinely valuable but overwhelming on
first contact.
**Remediation:** progressive disclosure — lead with a short verdict + the top 3
actions; collapse the deep analysis behind "show details." Pairs with F-01 (fix the
score first, since it's the most prominent element).

### F-03 · Two skills homes, one of them inert
**Persona:** job seeker. **Verdict:** SHARPENED. The Settings→Profile "Skills"
field (`templates/index.html`) is a **one-time seed**: it's imported into corpus
Skill rows on the first analyze (`onboarding/corpus_import.py:178-191`), after
which the **corpus is authoritative** and the flat field no longer affects output.
The drawer still shows it, so a user who edits Skills there later is editing a dead
control.
**Remediation:** either remove the flat Skills field once a corpus exists and point
to the corpus Skills editor, or make it a live view/proxy of the corpus rows.

### F-04 · Education & certifications have no corpus editor
**Persona:** job seeker. **Verdict:** SHARPENED. Backing DB tables exist
(`db/models.py` `Education`/`Certification`) and are read for context, but there is
no corpus panel/CRUD — they're edited only as flat free-text fields in Settings,
away from the corpus, easy to forget.
**Remediation:** surface education/certifications as first-class corpus sections
(like Skills), or at minimum move them next to the corpus with clear labeling.

### F-15 · Applications can't be told apart
**Persona:** job seeker, headhunter. **Verdict:** OBSERVED. New applications show a
**null company** and a generic role title because the JD's employer isn't captured
onto the Application. The tracker's cards look alike.
**Remediation:** extract company + role from the JD at analyze time (the analysis
already parses the posting) and stamp them on the Application; let the user edit.

### F-10 · The last step (downloading) can silently fail
**Persona:** job seeker, headhunter. **Verdict:** OBSERVED (documented in-app). The
Output panel warns that Chrome may block a second download without a fresh gesture
and gives a manual workaround, noting a planned server-side fix.
**Remediation:** ship the server-side download (stream with a `Content-Disposition`
attachment) so the final step is reliable — the app already flags this as future
work.

### F-06d · The "RELIABILITY" tile reads as catastrophic
**Persona:** technical. **Verdict:** CONFIRMED. `dashboard/routes.py:715-756`
computes only `error_rate`/`truncation_rate`; `dashboard/templates/dashboard.html:236-238`
labels the tile "reliability" but renders `error_rate * 100`. So "RELIABILITY 0%"
(5 errors / 3087 calls) actually means ~100% reliable.
**Remediation:** relabel the tile "Error rate," or show `100 − error_rate` under a
"Reliability" label.

### F-23 · The wizard is below the fold on the Tailor tab
**Persona:** job seeker, headhunter. **Verdict:** CONFIRMED. `#panelUser`
(index.html:83) and the full `#panelApplications` list (:129, untruncated at :156)
render before `#wizardRail` (:176) and all step panels. The active step
auto-scrolls into view on each step change, which mitigates the position but not
the ambient panels — the account switcher and full application list still sit above
every step and reappear on scroll-up.
**Remediation:** collapse User Selection to a compact switcher and the applications
list to a short summary while a tailoring session is active, so the wizard owns the
viewport.

### F-21 · Docs blur "use it" / "develop it" / "extend it"
**Persona:** technical. **Verdict:** CONFIRMED. The README presents Claude-Code
slash commands (`/prompt-tune`, `/tune-from-annotations`) as generic developer
tooling (they require the plugin), and `AGENTS.md` claims tool-agnostic
universality while its enforcement is Claude-Code-specific.
**Remediation:** split the README's audiences explicitly — "Use sartor" (job
seeker/recruiter), "Run/self-host it" (operator), "Develop & tune it" (contributor,
with the plugin scoped as Claude-Code-specific).

### F-19 · No way to try it without a billed key
**Persona:** technical (and evaluators). **Verdict:** OBSERVED. Every meaningful
action needs a real Anthropic key; the LLM stubs exist only for tests.
**Remediation:** a "demo mode" seeded with a canned analysis/compose/output so a
newcomer can walk the flow before spending — a big adoption lever for an OSS tool.

### F-16 · House templates re-uploaded per candidate · F-17 · No pipeline view
**Persona:** headhunter. **Verdict:** F-16 CONFIRMED (personas are per-user);
F-17 OBSERVED (applications are per selected user; no cross-candidate view). Both
are the boundary of the single-user design, not bugs.
**Remediation:** account-level shared templates; a cross-candidate applications/
pipeline dashboard. Both fit the existing data model. See the polish plan.

### F-22 · Model-routing docs drifted from code
**Persona:** technical. **Verdict:** CONFIRMED. `AGENTS.md:49` (and residual lines
in `docs/architecture.md`) say "Sonnet 4.6 for analyze/clarify/generate," but
`analyzer.py:662-663` uses `claude-sonnet-5` / `claude-haiku-4-5`, analyze is a
two-phase Haiku+Sonnet split, and clarify runs on Haiku. `docs/architecture.md:523-534`
already has the correct wording to copy.
**Remediation:** update the drifted lines; this is a `PROMPT_VERSION`-adjacent
discipline the project already values.

---

## P2 — nice-to-have

- **F-05 · Username as first input.** Let users enter a display name and derive the
  slug; show the slug as secondary.
- **F-06 · Unexplained tab jump after create.** A one-line "Let's build your corpus
  first →" transition would close the gap.
- **F-07 · Native `confirm()` dialogs.** Consistent across ~10 sites
  (`app.js` incl. `:4513`), but they clash with the custom-modal aesthetic; and
  the accept-all one gates a non-destructive action. Migrate high-stakes
  confirmations to the app's own modal; drop the confirm on non-destructive
  bulk-accept.
- **F-09 · Reproducible Generate not surfaced.** Add a line at Generate: "assembled
  exactly from your approved composition — identical every time."
- **F-13 · Gap-fill optionality.** A small "optional — add only what fits" header on
  the gap-fill lane.
- **F-14 · Edit-gate modal.** Trigger it only on a real content edit, and simplify
  the copy.
- **F-18 · Dev-hostile defaults.** Document `--no-browser` / `FLASK_DEBUG=0`
  prominently for headless/container runs.
- **F-20 · Stale eval cost.** Regenerate the "~$0.10" smoke estimate (actual
  ~$0.37 after the Sonnet 5 upgrade) wherever it's quoted.
- **F-27 · README doc-polish bundle.** Add `git` to prerequisites; define the
  "witness metric" where first used; soften architecture.md's "5 minutes"; move (or
  cross-link) Install nearer the top for the technical reader.

---

## What was checked and *not* found to be a problem

Verification also refuted or de-escalated several things a first pass might flag,
which is worth recording so they aren't re-litigated:

- **"Accept all pending does nothing"** — *not a bug.* It's gated behind a native
  `confirm()`; automation cancels the dialog. It works for a human who accepts.
- **A transient "Internal Server Error" in the cover-letter preview** — *not
  reproducible.* It appeared only because the walkthrough navigated away and
  aborted the cover-letter SSE mid-stream; the endpoint cleanly returns the empty
  state afterward.
- **"Resume in wizard loses your work"** — *false.* It correctly restores Step 6
  with the generated résumé and a "Resumed from prior application" badge.
- **Multi-user data leakage** — *none.* Per-candidate corpora are cleanly isolated.
