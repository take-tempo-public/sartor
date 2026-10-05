# The maintainer lane — the owner's session protocol

> **Purpose:** how a session working in the owner's lane starts and closes a branch: taking
> over a handoff, the escape-hatch rules for the plan and merge gates, and the branch close-out
> checklist (pre-close sweep, gate, handoff, PR channel, pointer, prune). Moved out of
> `AGENTS.md` in Epic D sprint D3 (owner decision O-2, 2026-09-28), so outside contributors
> are no longer routed through it.
> **Audience:** `dev` — the owner and every agent session working for the owner in this
> repo. Claude Code sessions load this file automatically: `CLAUDE.md` imports it next to
> `AGENTS.md`. Outside contributors who send a pull request don't need it; they stop at
> [`CONTRIBUTING.md`](../../CONTRIBUTING.md) and the code rules in
> [`AGENTS.md`](../../AGENTS.md).
> **Authoritative for:** the order of the close-out steps and what each one requires. The
> clauses these steps serve live in [`../governance/charter.md`](../governance/charter.md)
> (C-7 to C-12, W-1); the handoff's shape lives in
> [`AGENT_HANDOFF_TEMPLATE.md`](AGENT_HANDOFF_TEMPLATE.md); the provenance stamp and ledger
> schema live in [`prov/SPEC.md`](prov/SPEC.md).

**Binding, not advisory.** Everything here binds a session working in the owner's lane
exactly as `AGENTS.md` binds every agent. It sits in its own file to keep outside contributors
out of it, not to make it optional.

---

## Starting a session from a handoff

A session that receives a handoff pointer line does three things before any other work, in
this order:

1. **Check the pointer:** `python scripts/check_handoff_pointer.py "<pointer line>"`.
2. **Record the consumption:** `python scripts/verify_doc_template.py <handoff>
   AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`, on the handoff the pointer
   names ([`prov/SPEC.md`](prov/SPEC.md) §5 step 2).
3. **Land the ledger file** that step 2 wrote in the first commit of the branch you create
   (close-out step 0 below; SPEC §5 step 3).

If step 1 or step 2 fails, that is the session's first output, and the session stops there
(charter C-9; close-out step 5 below states the rule in full).

---

## Escape hatches and markers

The general rule is in `AGENTS.md` ("Branch before code changes"): an env-var escape hatch is
legitimate only when the user explicitly directs its use, and you never hand-create a file a
hook checks for. In this lane that also covers the plan gate's `.approved` marker: only
`ExitPlanMode` creates it.

**The close-out steps below have no hatch at all.** That includes the pre-close sweep, the
quality gate and the handoff-template step. There is no authorized way to skip them. Follow
each as written, or STOP and surface that you can't. "Good enough" / "approved enough" is not
a call you get to make — quietly downgrading a binding rule to advisory is the failure mode
this section exists to prevent.

---

## Branch close-out checklist

**Closing agent, in order:**
0. **Pre-close sweep — run this BEFORE the gate, ON THE BRANCH (never post-merge).** Enumerate the COMPLETE set of close-out obligations and resolve each (or explicitly defer *with the user*) so the session closes **once**, not three times:
   - working changes staged + internally consistent (no dangling refs / links);
   - **memory learnings** from the session written now — doing memory or cleanup *after* the merge (on `main`) gets blocked by `require-feature-branch` + the merge-wiped `~/.claude/plans/.approved` marker, forcing a repeat flag-clear-and-ceremony that steps on the next branch's work; the cheap window is here, pre-merge;
   - every **loose end flagged this session** resolved or explicitly deferred;
   - **trailing "track this" observations** — every note surfaced this session (flaky tests, drift spotted, process friction, follow-on flags, deferred sub-decisions) is **filed durably now** into the **one** Carry-forward ledger in `RELEASE_CHECKLIST.md` (a memory / a PX row may *also* hold detail, but the ledger is the single authoritative home — not scattered per-stream sections joined by pointers); never left to surface after merge as a new one-file branch;
   - **the handoff renders the FULL still-open ledger** — the `Carried-forward observations` section reproduces the *cumulative* still-open subset (every open item, not just this session's), so nothing falls out of attention across handoffs; at **~8–10 open items**, flag a reduction sprint. (Canonical: charter **W-1** "carry-forward discipline".)
   - **branches to prune** identified;
   - **this session's own `consumed`-event provenance-ledger file** (`docs/dev/ledger/<session>.jsonl`, written on `main` at session start when the incoming handoff pointer was consumed) **is committed on this branch** — folded into an early commit, never left untracked and never given its own dedicated branch/PR (see [`prov/SPEC.md`](prov/SPEC.md) §5 step 3);
   - **wiki-relevance check** — if this branch's own diff touches any path `scripts/wiki_relevance.py` (`is_wiki_relevant()`) classifies as wiki-relevant, run a scoped `/wiki-self-update` against just this branch's own diff and **commit the wiki edit now, before opening the PR** — same "committed before merge" discipline as the memory/CHANGELOG items above, never a follow-up PR. If the touched file needed no page edit, say so explicitly (`docs/wiki/log.md`'s existing "verified no-edit" convention) rather than silently skipping the check. Small, incremental, per-branch updates are the expected norm now, not periodic catch-up passes — the merge-blocking `scripts/wiki_freshness.py` gate is the deterministic backstop for anything missed, not the primary mechanism ([`diagnosis/wiki-freshness-relevance-classification.md`](diagnosis/wiki-freshness-relevance-classification.md));
   - **any dev server or long-lived background process started this session terminated**
     before closing the window — an agent's own orphaned processes are exactly the failure
     mode carry-forward ledger item 20 documents (a day-old orphaned `python app.py` caused
     a real test failure in a later, unrelated session); check with `tasklist`/equivalent for
     anything you started that outlived its purpose.
   "Done" is the *output* of this sweep, not a declaration — do not announce completion until it is empty. Declaring progress over verifying completeness manufactures tech debt, repeat close-outs, and eroded trust. In particular, NEVER merge and then open a follow-up branch for a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in before the merge.
1. Quality gate green — `python -m scripts.gate`. [`scripts/gate.py`](../../scripts/gate.py) is the single definition of what it runs, and CI runs the same script. To say a local gate passed, cite `python -m scripts.gate --result`, which checks the run's own result file against the current tree. Don't cite a background-task notification; those have reported `exit 0` for a failed gate.
2. Write the next-agent handoff — **ON THIS BRANCH, BEFORE the merge** (this is exactly what the pre-close sweep's own "fold it in before the merge" rule already requires: the handoff is one of this branch's own docs, and `require-feature-branch` blocks writing it on `main` once this branch is gone, so there is no compliant way to do this step after merging). **READ [`AGENT_HANDOFF_TEMPLATE.md`](AGENT_HANDOFF_TEMPLATE.md) FIRST and reproduce every `<!-- verbatim -->`-marked section (Documents to read, Binding rules, Hard constraints, Close-out checklist) byte-for-byte, dropping none; a handoff written from memory is non-compliant** — as a **committed file** at `docs/dev/handoffs/<branch-slug>.md`, stamped per [`prov/SPEC.md`](prov/SPEC.md) §1 and validated before commit with `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>` (a `failed` result is authoring corruption in the handoff itself — fix the file, don't silence the check).
3. Commit — message records what was done and why (or "no code change — verified" if the branch closed clean); the handoff file from step 2 must be committed by this point too (its own commit or folded into this one — either way, both must exist before step 4).
4. **Land it through the PR channel — a local `git merge` to `main` is NEVER the flow.** `main` carries branch protection requiring a pull request plus six passing status checks (`strict: true`), so a local merge is rejected outright for a non-admin and, for an admin, silently bypasses those six checks. Squash and rebase merges are both disabled on the repo, leaving **merge commit** as the only method — that is deliberate: a squash rewrites SHAs and orphans the local commits it replaces (it already produced one zombie commit, `9f3c800`, before this was understood). Ask the user to confirm, then: `git push -u origin <branch>` → open the PR (`gh pr create`, or hand the user the URL) → **wait for the required checks with `python -m scripts.ci_wait <n>`** → `gh pr merge <n> --merge` (never `--squash`/`--rebase`) → `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected divergence fails loudly instead of silently manufacturing a merge commit. **[`scripts/ci_wait.py`](../../scripts/ci_wait.py) is the single definition of "the PR is green" — never hand-roll a watcher, a poll loop, or a `gh pr checks … | jq` one-liner** (there is no system `jq` on this machine, and `gh pr checks` exits nonzero on failure, so the usual `|| echo '[]'` fallback discards the real output exactly when it matters). It exits **0** only when every required check passed *and* no test needed a retry; **3 = green-after-retries** (charter C-7 rule 3 — stop and look, do not merge on it reflexively), **1** a failing required check plus its `--log-failed` tail, **8** the deadline expiring, **2** a wrapper error. Two hand-rolled 30-minute watches once ran to completion emitting *nothing* while a required check was already red — that silence is the failure this replaces. **Pushing is outward-facing on a public repo:** state what will become public — including any commits already on your local `main` that the remote does not have, since they ride along — and get explicit confirmation before the first push.
5. Prune the merged branch(es) with the user's OK — **but regenerate the pointer FIRST**, because it must cite `main`, and pruning a branch a pointer still names leaves the next session with an unresolvable reference (a correct C-9 halt, but a wasted first move). After the `pull --ff-only` in step 4: generate the one-line pointer with `python scripts/print_handoff_pointer.py docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or commit hash — then immediately verify that exact output with `python scripts/check_handoff_pointer.py "<output>"` before pasting anything: enforce the method, then check the result (a hand-typed hash was proven fabricated once — see [`diagnosis/handoff-pointer-verification.md`](diagnosis/handoff-pointer-verification.md)). Then prune (`git branch -d <branch>`; the remote copy is auto-deleted on merge). Give the user the checked line as copyable chat text, as the **last act** before closing the window — never paste the handoff's full content into chat; that reopens the exact clipboard/terminal-grid corruption channel this flow exists to close (evidence + design: [`handoff-integrity-design.md`](handoff-integrity-design.md); supersedes the prior "handoffs are chat text, never a file" policy for this transfer-channel question specifically). **Binding rule (charter C-9) — corrupted input is a blocked gate:** the next session's FIRST action on receiving a pointer is `python scripts/check_handoff_pointer.py "<pointer line>"`, and only once that passes, `--event consumed` on the handoff file it names; if either one fails (a bad path/branch/hash, structural drift, or a fingerprint mismatch), that is this session's **first output** — surfaced and STOPPED on, never silently reconstructed, regardless of how plausible the reconstruction looks.
