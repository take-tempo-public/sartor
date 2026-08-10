```toml
schema = 1
id = 49
kind = "item"
status = "watching"
decision_owner = "agent"
title = "Test suite leaves tmp*.html litter in the tracked personas/bundled/ directory"
refs = [
  ".gitignore",
  "personas/bundled/",
  "docx_to_persona_html.py",
]
summary = "A suite run leaves personas/bundled/tmp*.html behind; `git add -A` swept one into a commit before it was caught."
```

Observed 2026-08-05 on `feat/enforcement-first-governance`, directly:

```
$ git commit -a ...
 personas/bundled/tmptdw2spxv.html                  | 75 ++++
```

A 75-line HTML file with a `tempfile`-style random name was committed by a `git add -A`
during close-out. **Caught before push and removed** (`git rm --cached` + amend), so it never
reached `main`.

**Why it was stageable at all.** `.gitignore` ignores `personas/*` and then deliberately
un-ignores the shipped bundled set with `!personas/bundled/**` — that un-ignore is
indiscriminate, so anything a test drops in there becomes stageable. `personas/bundled/` is a
genuinely tracked directory (the bundled `.docx`/`.html`/`.css` templates ship with the
repo), which is what makes this worse than litter in a temp dir: it is litter in a directory
whose contents are *supposed* to be committed.

**Containment landed with this item (charter C-11).** `.gitignore` now carries
`personas/bundled/tmp*`, so git refuses to stage the file. That is a real mechanism, not a
note — but it is **containment, not a fix**: the tests still write there.

## Still open — the actual defect

**Which test writes it, and why into a tracked directory, is NOT diagnosed.** Not
investigated on this branch (governance scope, one branch one item). The obvious suspects are
the persona/template conversion paths (`docx_to_persona_html.py` and the bundled-template
build), but **that is a guess from filenames, not an observation** — do not treat it as a
finding.

Whoever picks this up: the first commit is the instrument, not the fix. `git status` after a
full `pytest -m ux` run will name the files; correlate against the tests that touch
`personas/bundled/`.

**Also worth checking:** whether any *other* tracked directory has the same
un-ignore-everything shape, since the same trap would apply.

## Updates

### 2026-08-05 — filed during feat/enforcement-first-governance (found by hitting it)

First known occurrence — `git log --all -- 'personas/bundled/tmp*'` returns nothing, so no
such file has ever been committed before. Filed `watching` rather than `open`: the
containment holds, and the underlying leak is cosmetic until someone proves otherwise.
