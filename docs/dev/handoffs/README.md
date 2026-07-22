# Handoffs

One file per branch, frozen once written — never edited after the closing
agent commits it. A correction is a new, explicitly superseding note, not
an edit to the original (append-only history).

- **Filename:** `<branch-slug>.md` (e.g. `feat-handoff-integrity-kit.md`).
- **Content:** built from `docs/dev/AGENT_HANDOFF_TEMPLATE.md`, stamped
  per `docs/dev/prov/SPEC.md` §1, validated with
  `python scripts/verify_doc_template.py <file> docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated ...`
  before commit.
- **The pointer.** The closing agent generates the one line with
  `python scripts/print_handoff_pointer.py docs/dev/handoffs/<branch-slug>.md`
  — never hand-typed — then immediately re-verifies that exact output with
  `python scripts/check_handoff_pointer.py "<output>"` before pasting
  anything. Only then does it go to the user as copyable chat text — path +
  branch + short commit hash — never the file's full content. This is the
  transfer-by-reference fix for the handoff corruption
  `docs/dev/handoff-integrity-design.md` exists to prevent: content that
  must survive verbatim travels as a committed file, not through a
  clipboard. The scripts close a second, separate gap: the pointer
  *line's* hash was hand-typed and unchecked, and was proven fabricated
  once — see `docs/dev/diagnosis/handoff-pointer-verification.md`.
  `print_handoff_pointer.py` fails loudly if the handoff isn't yet
  committed and reachable at HEAD, and reads branch/commit from git
  itself rather than memory; `check_handoff_pointer.py` independently
  confirms the cited commit exists, the doc is present in its tree, and
  the commit is an ancestor of the named branch.
- **Consumption.** The next agent's first action, before reading the
  pointed-to file at all, is `python scripts/check_handoff_pointer.py
  "<pointer line>"` — if that fails, the pointer itself is bad (wrong
  path, branch, or hash) and this is a blocked gate: surface it and stop,
  never guess the "real" values and proceed. Only once that passes does
  it read the file directly (not a chat paste) and run the same doc
  validator with `--event consumed` as the next step. See
  `docs/dev/prov/SPEC.md` §5 for the full workflow and what a `blocked`
  result means.
- **Landing the ledger file the consumption step writes.** `--event
  consumed` writes a new, untracked `docs/dev/ledger/<session>.jsonl` on
  `main`, before any branch exists — nothing else will commit it for
  you. Fold it into the **first commit** of the next branch this session
  creates; do not open a dedicated branch or PR just to land it. If the
  session ends without creating any branch, name the stray file in
  `RELEASE_CHECKLIST.md`'s carry-forward ledger so the next session's
  first branch picks it up instead of it going orphaned again. Full
  rule: `docs/dev/prov/SPEC.md` §5 step 3.

Full schema and rationale: `docs/dev/prov/SPEC.md`. Design record:
`docs/dev/handoff-integrity-design.md`.
