# Blast radius — b1-stale-template-companions

> **Branch:** `fix/b1-stale-template-companions`
> **Status:** enumeration complete — written before the first production edit.

**Gate status, stated plainly (C-0):** none of the surfaces below is in
`scripts/enforcement/blast_radius.py`'s `GATED` / `GATED_PREFIXES` registry, so
`require-consumer-enumeration` does **not** fire for this branch. This dossier is
written anyway because the change alters a **stored-data shape** — the
`.persona.json` sidecar — and C-10's ordering argument applies whether or not a
hook is watching. It is not a claim that the guard demanded it.

---

## Surface

| File | What changes inside it |
|---|---|
| `docx_to_persona_html.py` | new `skeleton_version()` (cached SHA-256 of the shipped skeleton); the `.persona.json` payload gains a `skeleton_version` key (`:449-452`); the early-return guard at `:438-444` gains a stamp comparison; new public `resolve_companion_html()` entry point. |
| `<stem>.persona.json` (stored data, not tracked) | additive key `skeleton_version`. `layout_fidelity` is untouched in name, type and values. |
| `blueprints/templates.py` | three resolve-then-generate blocks (`:1044-1052`, `:1330-1334`, `:1411-1420`) route through `resolve_companion_html`. No route signature, no auth path, no new route. |
| `generator.py` | one resolve-then-generate block (`:255-264`) routes through `resolve_companion_html`. |

Explicitly **not** changed: `pdf_render.html_template_path_for` stays a pure
resolver (side-effect-free), because `tests/test_pdf_render.py:41-62` asserts
exactly that shape and because a resolver that silently rewrites files is the
trap this dossier's Consumers table exists to avoid.

---

## Enumeration

Every name the surfaces go by, searched tree-wide with `git grep -In` (whole
tree, tracked files, from the repo root). Counts are total matching lines:

```
generate_companion           30
docx_to_persona_html         65
persona\.json                 8
layout_fidelity              14
html_template_path_for       28
resolve_companion_html        0
skeleton_version              0
classic\.html                33
```

Negative results, recorded because they are findings:

- `resolve_companion_html` → **0 hits**: the name is new; no collision anywhere.
- `skeleton_version` → **0 hits**: the sidecar key is new; nothing reads a key by
  that name today, so the addition cannot shadow an existing consumer.
- `persona\.json` → **8 hits, and only 2 are code** (`docx_to_persona_html.py:26`
  prose, `:435` the write). The other 6 are `CHANGELOG.md`, `RELEASE_ARC.md`, the
  two Epic B briefs, and two test assertions. **Nothing in production reads the
  sidecar at all** — this change introduces the first production read of it.
- `git grep -In 'persona\.json' -- static/ templates/` → **0 hits**: the sidecar
  never reaches the frontend, so no JS or Jinja consumer exists to update. (This
  matters because C-10's known limit is that the computed audit covers Python
  import fan-in only; JS/Jinja are curation-only, so the negative had to be
  searched by hand rather than assumed.)

---

## Consumers

Six `generate_companion` call sites and every `html_template_path_for` site,
each decided before the first edit.

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `blueprints/templates.py:654` | no change | Upload. Calls `generate_companion(target)` unconditionally on a just-written `.docx`, so the mtime arm already forces generation; the new stamp is written on that same pass. The `None`-means-warning contract (`:654-660`) is preserved because the return type is unchanged. |
| 2 | `blueprints/templates.py:879` | no change | Copy-to-candidate. Same unconditional shape as #1 on a freshly-copied `.docx`. |
| 3 | `blueprints/templates.py:1044-1052` | **update** | `preview_application_html`. Resolve-then-generate: the stale companion exists, so `generate_companion` is never called (diagnosis Fact 5). Routes through `resolve_companion_html`; the bundled-Classic fallback at `:1053-1056` is untouched and still fires on `None`. |
| 4 | `blueprints/templates.py:1330-1334` | **update** | `preview_edited_html`. Same shape, same fallback at `:1335-1338`. |
| 5 | `blueprints/templates.py:1411-1420` | **update** | corpus preview. Same shape, same fallback at `:1421-1424`. |
| 6 | `generator.py:255-264` | **update** | PDF render path. Same shape; the bundled-Classic fallback at `:266-273` is untouched. |
| 7 | `pdf_render.py:59-68` (`html_template_path_for`) | no change | Stays a pure existence resolver. Sites 3-6 stop calling it directly; sites elsewhere and its own tests keep working unchanged. |
| 8 | `pdf_render.py:71-87` (`_register_date_range_global`) | no change | Correct as written — it registers the global; the defect is that stale companions contain no call to it. Its docstring claim at `:80-83` is now true again once companions refresh. |
| 9 | `tests/test_docx_to_persona_html.py:58-113` | **update** | `test_generate_companion_writes_html_css_sidecar:80-81` asserts the sidecar body; the additive key must be asserted, not silently widened. `test_generate_companion_idempotent:102-113` is the "not needlessly regenerated" oracle and must keep passing unchanged. |
| 10 | `tests/test_pdf_render.py:41-62` | no change | Asserts `html_template_path_for`'s pure-resolver behavior, which #7 preserves. If a later refactor makes the resolver side-effecting, these fail — which is the point. |
| 11 | `personas/bundled/*.html` (4 hand-authored companions) | **no change, load-bearing** | These are NOT classic-skeleton clones and have no `.persona.json` (diagnosis Fact 6). `resolve_companion_html` refreshes only when a sidecar is present, so they can never be overwritten. Today they are protected only by the existence check in sites 3-6 — a protection this change removes, which is exactly why the sidecar-presence rule replaces it. Covered by a dedicated regression test. |
| 12 | Stored `<stem>.persona.json` files in user installs | no migration | The key is additive and its absence is precisely the staleness signal. A pre-fix sidecar reads as stale, regenerates once, and gains the key. No reader exists that could break on the extra key (see the `persona\.json` negative above). |

---

## Deferred

**`personas/bundled/*.css` / `*.html` drift is not audited here.** If a bundled
persona's hand-authored companion ever falls behind `classic.html`'s Jinja
contract, this change will not detect it — the sidecar-presence rule
deliberately excludes them, and their maintenance is a hand process. Not chased:
it is a different defect class (hand-authored drift, not stale clones) and B1a's
scope is the imported-template path. Worth a work item; not fixed on this branch.

**The copy-to-candidate path (#2) loses the source persona's hand-authored CSS**
when a bundled house template is copied to a user, because the copy gets a
generated Classic-skeleton companion rather than the bundled one. Pre-existing
behavior, unchanged by this branch, out of B1a's scope. Recorded here so it is a
decision rather than an omission.

---

## Verification

A missed consumer surfaces as one of these, all of which fail loudly:

- **Missed resolution site** — `git grep -n html_template_path_for -- '*.py'`
  after the change must show no remaining resolve-then-generate pair in
  `blueprints/templates.py` or `generator.py`. A site left behind keeps the exact
  bug this branch fixes, on that one route only, which is the silent-partial
  outcome C-10 exists to prevent.
- **Broken sidecar contract** — `tests/test_docx_to_persona_html.py:80-81`
  asserts the sidecar body; an incompatible rewrite of the payload fails there
  rather than in production.
- **Bundled clobber** — `test_resolve_companion_html_does_not_touch_bundled_companions`
  asserts `personas/bundled/modern.html` is byte-identical after a resolve. This
  is the enumeration's highest-value check: row 11 is the consumer a
  grep-for-symbols pass would have missed entirely, because those files are
  consumers by *filesystem adjacency*, not by import.
- **Needless regeneration** — `test_generate_companion_idempotent` plus a new
  resolve-level equivalent assert `mtime_ns` is unchanged on a current
  companion, so a stamp bug that regenerates on every preview fails a test
  instead of quietly re-parsing a `.docx` on every request.
