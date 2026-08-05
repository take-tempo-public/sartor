# Blast radius — ci-wait-wrapper

> **Branch:** `feat/ci-wait-wrapper`
> **Status:** enumeration complete — written before the first edit to a gated surface.

---

## Surface

One gated surface is edited on this branch:

- **`docs/dev/AGENT_HANDOFF_TEMPLATE.md`** — the **body** of the verbatim section
  `## Branch close-out checklist (do in this order before closing the window)`,
  step 4 only: the phrase "**wait for all required checks to go green**" becomes an
  instruction to run the new `python -m scripts.ci_wait <n>` wrapper. The section's
  **heading text is not changed**, and no other verbatim section is touched.

Changed in the same commit, **not** gated: `AGENTS.md`'s "Branch close-out checklist"
step 4, which is the canonical restatement of the same text.

New, ungated, no existing consumers: `scripts/ci_wait.py`, `tests/test_ci_wait.py`.

---

## Enumeration

Ripgrep over the whole tree (a shelled `grep -rn` was abandoned — it walks
`node_modules/` and `.git/` and timed out at 120 s; `rg` respects the ignore files):

```
rg -l "wait for all required checks"        -> 58 files
rg -l "gh pr merge|gh pr checks"            -> 65 files
rg -l "AGENT_HANDOFF_TEMPLATE"              -> 86 files
```

Partitioned:

| Set | Count | What it is |
|---|---|---|
| `docs/dev/handoffs/*.md` | 56 | historical handoffs that each reproduce the old close-out text |
| `docs/dev/AGENT_HANDOFF_TEMPLATE.md` | 1 | the surface itself |
| `AGENTS.md` | 1 | the canonical restatement |

**Negative results, recorded as findings:**

- **No code globs `docs/dev/handoffs/*.md`.** `rg "handoffs.*glob|glob.*handoffs"` over
  `*.py` returns **0 hits**; the only Python touching that directory is
  `scripts/check_handoff_pointer.py` / `scripts/print_handoff_pointer.py`, both of which
  take **one explicitly-named path** and neither of which reads section bodies. So no
  test or gate re-validates the 56 archived handoffs against the template.
- **`CLAUDE.md` does not restate step 4** — 0 hits for the phrase. It defers to
  `AGENTS.md` via `@AGENTS.md`.
- **`scripts/enforcement/guards/block_merge_to_main.py`** matches
  `\bgit\s+merge(?!-)\b.*\b(?:main|master)\b` against Bash command text. `python -m
  scripts.ci_wait` contains none of those tokens, and the branch name
  `feat/ci-wait-wrapper` contains neither `main` nor `master`, so the new wrapper cannot
  trip the merge guard. No change needed.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `docs/dev/AGENT_HANDOFF_TEMPLATE.md` — close-out §step 4 | **update** | the surface; step 4 names the wrapper |
| 2 | `AGENTS.md` — "Branch close-out checklist" step 4 | **update** | canonical restatement; must not drift from #1, so it moves in the same commit |
| 3 | `scripts/verify_doc_template.py:171-196` (`check_verbatim`) | **no change** | it compares a doc's verbatim body against the template **as it exists at validation time**. No code edit is needed, but this is *the* consumer that makes the change matter — see Deferred |
| 4 | `tests/test_verify_doc_template.py:276-290` (`TestRealTemplate`) | **no change** | asserts the four verbatim **heading titles** only, never their bodies. Editing step 4's text leaves it green — confirmed by reading the assertion, not by running it |
| 5 | 56 × `docs/dev/handoffs/*.md` | **no change (deliberate)** | historical artifacts are never rewritten — see Deferred for the consequence |
| 6 | `scripts/print_handoff_pointer.py`, `scripts/check_handoff_pointer.py` | **no change** | operate on the pointer line (path/branch/commit), never on section bodies |
| 7 | `scripts/wiki_relevance.py` | **no change to the file**, but it **classifies both `AGENTS.md` and `docs/dev/AGENT_HANDOFF_TEMPLATE.md` as wiki-relevant** (`is_wiki_relevant()` → `True`), so this branch owes the close-out scoped `/wiki-self-update` check rather than a silent skip |
| 8 | `scripts/enforcement/blast_radius.py` | **no change** | the registry entry for this surface is already correct; nothing is being added to or removed from the gated set |

---

## Deferred

**The 56 archived handoffs are deliberately not retro-edited.** Consequence, recorded
rather than discovered later:

> Re-running `verify_doc_template.py --event consumed` against a handoff generated
> **before** this commit will now report a verbatim mismatch on the close-out section and
> log `blocked`.

This is acceptable here, and the reason is structural rather than optimistic:

1. The working posture is **strictly serial** (charter W-1 posture; RELEASE_ARC key
   decision 10) — one branch, one session — so at most one handoff is ever in flight.
2. The only handoff in flight was `docs/dev/handoffs/fix-ux-scroll-spy-overlapping-refresh.md`,
   and it was **already consumed at fingerprint `7c5c28c24ff2` at the start of this
   session, before this edit** (ledger: `docs/dev/ledger/b7fe246e-….jsonl`).
3. This branch's own outgoing handoff is generated **after** the template edit, so it is
   written against the new canonical text and validates clean.

Rewriting the archive to match would be the actively worse option: it would rewrite 56
historical records to say something their authors did not write, and it would invalidate
every `generated` fingerprint already on the ledger. Not done, on purpose.

**If the serial posture is ever relaxed**, this becomes a real hazard: a handoff generated
by a concurrent session before the edit and consumed after it would halt that session on a
correct-but-avoidable C-9 block. Flagged here as the tripwire, not tracked as an open item.

---

## Verification

How a missed consumer would surface:

1. `python scripts/verify_doc_template.py docs/dev/handoffs/<this-branch>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated` — the close-out step 2 command.
   If #1 and the handoff disagree by even one character, this **fails loudly** with the
   two sha256 prefixes. This is the exact-set assertion for the surface.
2. `python -m scripts.gate` — runs `tests/test_verify_doc_template.py`, which pins the
   four verbatim heading titles (consumer #4). A heading accidentally renamed while
   editing its body fails there.
3. `AGENTS.md` ↔ template agreement (#2 vs #1) is checked by re-reading both step 4s
   side by side in the same commit's diff; there is no automated cross-check between
   them, which is itself why they are moved together in one commit rather than
   separately. Stated as a known limit, not claimed as enforced.
