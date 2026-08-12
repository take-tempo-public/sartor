```toml
schema = 1
id = 87
kind = "item"
title = "Interrogative-prompt witness: hook mechanism so a question is answered, not acted on — build before Epic B run 3"
status = "open"
decision_owner = "user"
refs = [
  "docs/dev/handoffs/fix-n1-args-guard-hardening.md",
  "hooks/edit-write-dispatcher.sh",
  ".claude/settings.json",
]
summary = "owner-directed: fail-open witness hooks so a question gets an ANSWER, not action; lands BEFORE the B1a run."
```

**The failure class (third recorded instance 2026-08-12; the owner: "a
recurring issue since before this project existed").** A session with a hot
execution frame treats an interrogative prompt as a work order: it answers,
then unilaterally begins "fixing" something nobody asked about. Prior faces
of the class each got a prose memory (`feedback-answer-before-acting`,
`feedback-dont-announce-and-act-same-breath`) and neither held at the
decisive moment — the same measurement charter C-11 already made about prose
discipline generally. The 2026-08-12 instance: after the
`fix/n1-args-guard-hardening` close-out, the owner asked twice whether the
invoking agent's model was designated in the plan; the session answered,
declared an unrequested "gap" in the just-merged handoff, started editing,
and escalated into a plan ceremony before being interrupted.

**Owner directive (2026-08-12, near-verbatim):** "i wouldn't make it
enforced, but i would enforce your proposal. maybe even a pre-tool-use hook
so before you go editing a file, you check if the prompt was an
interrogative that needs an answer or a question that calls for an action. i
trust that most of the time, you make good decisions when the consideration
is explicit and without momentum. I'd also add, after closeout ritual,
assume a prompt is an interrogative unless obviously not... if i want you to
do something, i'm usually pretty clear about it." And: make it "clean and
enforceable before we start the b epic again."

**The design to implement (two complementary witnesses, both fail-open):**

1. **UserPromptSubmit heuristic** — this hook type sees the prompt text. A
   cheap classifier (trailing "?"; leading token in {is, are, was, should,
   would, could, why, what, when, how, does, do, did, can, whether, who,
   which}) that, on match, INJECTS a non-blocking context reminder before
   any tool runs: the deliverable is the ANSWER; propose follow-on work at
   the end; do not edit. Err toward classifying as interrogative — the
   owner is explicit when action is wanted, so false negatives on
   directives-phrased-as-questions ("can you fix X?") are acceptable and the
   reminder text should say the user's explicit directives override it.
2. **First-Edit/Write-per-turn pause** (the owner's PreToolUse shape) —
   PreToolUse hooks receive tool_input only, NOT the conversation, so this
   cannot classify; it forces the explicit consideration instead: on the
   first Edit/Write of a turn, surface "was the triggering prompt an
   interrogative needing an answer, or a directive calling for action?" as a
   witness. Rate-limit to once per turn/prompt so it never becomes noise.

**Stated limits (C-0/C-11 — label in the implementation, not papered over):**
intent classification is not deterministic; these are WITNESSES that force
the consideration to happen and strip momentum, not gates that prove intent.
Fail-open is deliberate and matches the owner's stated trust in
momentum-free judgment.

**Wiring:** follow the dispatcher pattern (`hooks/edit-write-dispatcher.sh`,
PX-37; one settings.json entry per matcher, logic in
`scripts/enforcement/`). Hook-testing method: byte-correct JSON + throwaway
worktree (see the hook-manual-testing practice used for every prior guard).
Machine-local context: the full incident dossier including the owner's
causal framing lives in this machine's agent memory under the name
`feedback-interrogative-is-not-a-work-order`, and an always-loaded rule
section exists in the gitignored `CLAUDE.local.md`; this item is the
repo-durable home.

**Sequencing (owner-directed):** own branch off `epic/b-render-ats`
(precedent: the pipeline-tooling fixes already ride the epic umbrella), own
session, gate green, ff-merge back into the epic — **BEFORE the Epic B run-3
session (sprint B1a) starts**, so that run's invoking session is already
protected.

## Updates

### 2026-08-12 — filed (owner-directed), sequenced ahead of Epic B run 3

Filed at the close of the `fix/n1-args-guard-hardening` follow-up
conversation. The handoff `docs/dev/handoffs/fix-n1-args-guard-hardening.md`
names this item's branch as the next branch, ahead of
`fix/b1-stale-template-companions`.
