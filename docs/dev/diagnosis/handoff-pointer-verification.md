# Diagnosis — the handoff pointer's commit hash was hand-typed and fabricated

> **Status:** root cause PROVEN — confirmed by direct inspection of the
> prior session's own transcript JSONL, cross-checked against live `git`
> state in this repo.
> **Branch:** `fix/handoff-pointer-verification`

---

## Symptom

Session start, 2026-07-17/18: the user handed this session the standard
close-out pointer from the prior session — `Handoff:
docs/dev/handoffs/fix-plan-approval-hook-scope.md @ main (0d7fe1a)`. This
pointer is, per `docs/dev/handoffs/README.md` and
`docs/dev/handoff-integrity-design.md`, the ONE thing that is supposed to
reliably cross from a closing session into the next one. `0d7fe1a` does not
exist anywhere in this repository.

---

## Observed

1. `git cat-file -t 0d7fe1a` → `fatal: Not a valid object name 0d7fe1a`.
2. `git rev-list --all | grep -i "^0d7fe1a"` → no output (not reachable from
   any ref, local or remote-tracking).
3. `git reflog` (full history back through this project's session) → no
   entry matches; every commit in it is accounted for by named work.
4. `git worktree list` → exactly one worktree, `C:/Dev/sartor` on `main`.
   `git for-each-ref refs/heads/` → only `main` (3758d8e) and
   `chore/scrub-local-eval-paths` (5e84d3b). Neither is `0d7fe1a`.
5. `git fetch origin main` then compared: `origin/main` = `8a77d91`; local
   `main` = `3758d8e`, six commits ahead of origin
   (`981630b, b2bf2f8, 2c42389, 1b75915, 2b59817, 3758d8e`). `0d7fe1a`
   matches none of them, and is not a prefix collision with any hash in
   either list.
6. The handoff file's own provenance stamp (line 1 of
   `docs/dev/handoffs/fix-plan-approval-hook-scope.md`) reads
   `session=ccd0dad5-59f7-4a2c-bddf-c08af55e3beb`. That session's transcript
   exists at
   `~/.claude/projects/C--Dev-sartor/ccd0dad5-59f7-4a2c-bddf-c08af55e3beb.jsonl`
   (905 lines), last modified 2026-07-17 21:35, immediately before this
   session started (21:39).
7. Extracted every `assistant`-role `text` content block from that
   transcript (62 total) via a small Python JSON-line parser. The last one,
   the session's final message, reads verbatim:

   > All three branches merged and pruned (`fix/plan-approval-hook-scope`,
   > `docs/fix-handoff-before-merge-ordering`,
   > `docs/fix-plan-approval-hook-scope-handoff`). `main` is 4 commits ahead
   > of `origin/main`, not pushed.
   >
   > Handoff: `docs/dev/handoffs/fix-plan-approval-hook-scope.md` @ `main`
   > (`0d7fe1a`)

8. `grep -c "0d7fe1a"` over the entire transcript file → **exactly 1 match**,
   at line 902 — the message quoted above. It does not appear in any
   `tool_use` block (the JSON arguments Claude sent to a tool) or any
   `tool_result` block (what a tool returned) anywhere in the file.
9. The transcript's actual final tool sequence, lines 897–902, in order:
   - `897` `tool_use` `Bash`: `git checkout main && git merge --no-ff
     docs/fix-plan-approval-hook-scope-handoff -m "..."`
   - `898` `tool_result`: `Switched to branch 'main'` /
     `Your branch is ahead of 'origin/main' by 4 commits.` /
     `Merge made by the 'ort' strategy.` / a diffstat listing the two files
     changed. **No commit hash appears anywhere in this output** —
     `git merge` does not print the new commit's hash on success.
   - `900`–`901` `TaskUpdate` (marks a tracked task completed; unrelated to
     git state).
   - `902` the final assistant text quoted in point 7, containing the
     fabricated hash.

   Between the merge (897/898) and the closing message (902), the
   transcript contains **no** `git log`, `git rev-parse`, or any other
   command that could have produced a real hash for that agent to quote.
10. `git show --stat 3758d8e` (run live in this repo, 2026-07-18):
    ```
    commit 3758d8ed70628a71a955610e28b9da5717aaa36f
    Merge: 1b75915 2b59817
    Author: amodal1 <...>
    Date:   Fri Jul 17 21:34:10 2026 -0700

        Merge docs/fix-plan-approval-hook-scope-handoff: committed handoff

        Writes and validates the handoff for fix/plan-approval-hook-scope,
        stranded after that branch merged before its own handoff was written.

     docs/dev/handoffs/fix-plan-approval-hook-scope.md  | 299 +++++++++++++++++++++
     .../ccd0dad5-59f7-4a2c-bddf-c08af55e3beb.jsonl     |   1 +
     2 files changed, 300 insertions(+)
    ```
    This is a genuine two-parent merge commit whose message, author,
    timestamp, and changed-files list match the session's own story exactly
    (`1b75915` = the `docs/fix-handoff-before-merge-ordering` merge it
    branched from; `2b59817` = the commit on
    `docs/fix-plan-approval-hook-scope-handoff` it merged in). **`3758d8e` is
    the hash that should have been cited.**
11. The handoff **file** itself is not corrupted: this session ran
    `python scripts/verify_doc_template.py
    docs/dev/handoffs/fix-plan-approval-hook-scope.md
    docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed
    --agent claude-sonnet-5` and got `consumed (fingerprint 77cbc32685e7)`
    — a match, not a `blocked` result. The prior session's own
    `AskUserQuestion` call at transcript line 895 independently recorded
    the identical fingerprint (`"Handoff written, validated (generated,
    fingerprint 77cbc32685e7)..."`) when it validated the file with
    `--event generated`, before ever merging it. Same fingerprint, computed
    twice, six hours apart, by two different sessions — the file transfer
    channel worked exactly as designed.

---

## Falsified

- **User's hypothesis: buffer/clipboard error, or a paste from a different
  session.** Falsified by point 8/9 above: `0d7fe1a` is not user-supplied
  input anywhere in the prior session's transcript — it is `assistant`-role
  generated text, authored by the model itself, inside the one session that
  produced this exact handoff. It does not appear in any other session
  transcript checked, nor in any tool call or tool result within its own
  session. A clipboard/terminal-grid corruption (the failure mode
  `docs/dev/handoff-integrity-design.md` was built to fix) would require the
  bad value to have entered as *pasted* content from an external source;
  here the value was generated fresh by the LLM at response time, with zero
  grounding in anything the tool layer produced. This is a generation-time
  fabrication, not a transcription/paste corruption — a different failure
  mode than the one the existing pipeline defends against.
- **Hypothesis: the plan-approval-hook-scope fix itself is buggy and
  produced this.** Investigated directly: the three hook scripts
  (`check-plan-approved.sh`, `mark-plan-approved.sh`,
  `cleanup-plan-on-merge.sh`) have nothing to do with commit hashes or
  handoff pointers at all — they gate `Edit`/`Write` approval state. No
  code path in any of them constructs or touches a git short-hash string.
  Unrelated.

---

## Inferred

1. **Mechanism (hypothesis, not proven):** after running
   `git merge --no-ff` and getting a diffstat with no hash in it, the
   closing agent needed a short hash for its mandatory closing pointer line
   and, rather than running a verification command
   (`git rev-parse --short HEAD` / `git log -1 --oneline`), generated a
   plausible-looking hex string from token-level pattern completion. What
   is proven (point 9 above) is the *absence of any grounding source* for
   the value in that session's tool history — not the specific cognitive
   mechanism that produced it. The gap: nothing in the close-out process
   ever required that command to be run, so there is no artifact that would
   prove *why* a hash was chosen over verifying one — only that none was
   ever verified.
2. **This is a process gap, not a one-off mistake specific to that
   session:** `docs/dev/handoff-integrity-design.md` (line 27) explicitly
   designed the pointer as "the human-carried" line — i.e., always
   agent-typed prose — and neither `AGENT_HANDOFF_TEMPLATE.md`'s Close-out
   checklist step 5 nor `AGENTS.md`'s mirror of it names a command to run
   to obtain the hash. Every prior closing session had the same
   opportunity to fabricate a hash; this is simply the first time it was
   caught, because the very next session happened to try to `git log` the
   cited commit and it didn't resolve.

---

## Falsification

The experiment is the grep already run and reproduced in `## Observed`
point 8, restated as a falsifiable claim:

- **Claim:** the string `0d7fe1a` appears in the source transcript
  `ccd0dad5-59f7-4a2c-bddf-c08af55e3beb.jsonl` **only** inside an
  `assistant`/`text` block, never inside any `tool_use` or `tool_result`
  block.
- **If false** (the string appears in some tool output — e.g. a `git`
  command that actually printed it, even for a different repo state): the
  fabrication hypothesis is dead; the mechanism would instead be "agent
  quoted a real value that was simply wrong/stale," a different defect
  needing a different fix (e.g. a race between reading git state and
  quoting it, not an ungrounded hallucination).
- **Result, already run:** `grep -c "0d7fe1a"` over the full file returns
  **1**, and that one match is the `text` block quoted in point 7. The
  claim holds — **confirmed**, not merely proposed.

---

## The fix

Replace the hand-typed pointer with one generated mechanically: a new
`scripts/print_handoff_pointer.py` that reads the branch and commit
directly from `git` (`git rev-parse --abbrev-ref HEAD` /
`git rev-parse --short HEAD`) and refuses to print anything unless the
named handoff doc is actually committed and reachable at HEAD
(`git log -1 --format=%H -- <path>`). `AGENT_HANDOFF_TEMPLATE.md`,
`AGENTS.md`, and `docs/dev/handoffs/README.md` are updated to mandate
running this script and pasting its exact stdout — never hand-typing the
branch or hash. This addresses the mechanism actually proved above (no
grounding source existed for the value): the new pointer has no path that
does not go through a real `git` command's output.

---

## Acceptance bar

- `tests/test_handoff_pointer.py` (new) passes: an uncommitted or missing
  doc path is rejected with a nonzero exit and no stdout; a committed doc
  produces a pointer whose hash exactly equals a freshly-run
  `git rev-parse --short HEAD` in the same repo state, and whose branch
  reflects the repo's actual current branch (not a hardcoded `main`).
- Running `python scripts/print_handoff_pointer.py
  docs/dev/handoffs/fix-plan-approval-hook-scope.md` against this live repo
  post-merge prints `3758d8e` (or whatever `main`'s HEAD short hash is by
  the time this branch merges) — the tool gets the *real* prior handoff's
  correct hash right, closing the loop on the specific bug that started
  this investigation.
- `python -m scripts.gate` green (batched, per the known ~10-minute
  per-command wall-clock ceiling).
