# Blast radius: test-reliability

> **Branch:** `fix/test-reliability`
> **Status:** enumeration complete, written before the first edit to `static/app.js`.

---

## Surface

- **`static/app.js`, the notes textarea's blur handler in `_showApplicationDetail`**
  (`:6511-6534`). Today it PUTs `/api/applications/<id>/notes` and toasts `Notes saved` on every
  blur. After the change it does both only when the trimmed text differs from the saved
  `detail.notes`, and it updates `detail.notes` after a successful save. That is the shape the
  title and company handlers below it already have (`:6563-6575`).
- **Unchanged:** the route `update_application_notes` (`blueprints/applications.py:608`), its
  request and response shapes, `_toast`, and the focus call at `:6610`.

The diagnosis behind it is `docs/dev/diagnosis/test-reliability.md`, O5 and O6. The redundant
notes save is what overwrote `Company saved` in item 155.

---

## Enumeration

Every name the behavior goes by, searched over the whole tree (Grep tool; the flake-rate shards
excluded because they are CI log extracts):

```
pattern: appDetailNotes|Notes saved|/notes\b|update_application_notes|newNotesEl|detail\.notes|Failed to save notes
```

Code hits, all listed in `## Consumers` below:
- `static/app.js:6512-6532`, and `:6610`;
- `templates/index.html:1302-1306`;
- `blueprints/applications.py:21`, `:608-609`, `:639`;
- `tests/test_application_routes.py:1204-1246`;
- `tests/ux/regression/test_20260611_prior_app_resume_robustness.py:120-230`.

The other hits are history and prose. None of them depends on the handler's behavior:
- `CHANGELOG*.md` and `docs/dev/RELEASE_ARC.md`;
- `docs/dev/archive/app-blueprints-design.md`, and the handoffs that quote item 155;
- `docs/dev/work/**`;
- this branch's own diagnosis;
- `docs/wiki/pages/route-surface.md:253` (route list only).

Docs describing the save behavior:

```
grep -rniE "notes?[^.]{0,40}(blur|save|saved|autosave)|(blur|save|saved)[^.]{0,40}notes" docs/user docs/wiki README.md templates --include=*.md --include=*.html
templates/index.html:1306:                  placeholder="Add notes (saved on blur)"></textarea>
```

Page-object selectors: `grep -rn "Notes\b\|NOTES" ui_pages/` finds only `selectors.py:369`. That
is the profile-config `#cfgNotes`, a different field. `#appDetailNotes` has no selector, and no
UX test drives the notes textarea.

Other users of the shared toast in the UX tier: `grep -rn "_corpusToast" tests/ux --include=*.py`
found 3 hits. Two are the item-155 test module; the third is
`tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py:62`, which never waits on a notes
toast (`Notes saved` has 0 hits in that file).

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `static/app.js:6519-6534` (notes blur handler) | update | The change itself: skip the PUT and toast when the trimmed value equals `detail.notes \|\| ''`; set `detail.notes` after a successful save. Mirrors `:6563-6575`. |
| 2 | `static/app.js:6512-6518` (initial value, clone-replace) | no change | Still seeds the textarea from `detail.notes`. The new comparison reads the same `detail`. |
| 3 | `static/app.js:6610` (`newNotesEl.focus()` on open) | no change | Focus on open stays. Its blur no longer saves when nothing changed, and that was the defect's trigger (O5). |
| 4 | `templates/index.html:1302-1306` (label, textarea, placeholder "saved on blur") | no change | Still true: a changed note saves on blur. |
| 5 | `blueprints/applications.py:608-631` (`update_application_notes`) | no change | Route untouched. The server still strips the text and stores `None` for blank, so the client's trimmed comparison matches what was stored. |
| 6 | `tests/test_application_routes.py:1204-1246` | no change | Route-level tests; the route is unchanged. |
| 7 | `tests/ux/regression/test_20260611_prior_app_resume_robustness.py` (`_company_round_trip`, P-H1) | update | Item 155's test fix: wait on the PUT `/meta` response instead of the shared toast. P-H1 loses its xfail. |
| 8 | `tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py:62` (`_TOAST`) | no change | Waits on other toasts, never a notes save. |
| 9 | `docs/wiki/pages/route-surface.md:253` | no change | Lists the route, which is unchanged. |

---

## Deferred

- **The toast stays shared.** Every save in the detail modal writes the one `#_corpusToast`, so two
  saves that really both happen (an edited note and an edited company) still leave the later
  response's text on screen. That is correct feedback, since both saved. The test no longer reads
  the toast to learn whether the company saved. Giving each save its own toast would be a
  product change outside item 155.
