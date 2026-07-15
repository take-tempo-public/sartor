# Agent failure patterns to avoid

> **Purpose:** permanent reference for dev agent behavioral discipline.
> These patterns were identified during the v1.0.1 release arc and have
> recurred across sessions. Every agent should read this before writing
> any code.
>
> **Source:** patterns 5a–5e were harvested from the 2026-05-27 v1.0.1
> session retrospective (since retired once captured here); this file is the
> undated, canonical home for them. **5f was added on 2026-07-14** after an
> agent read 5a/5b/5e, judged them inapplicable, and burned a day proving them
> right — which is why 5f is the only one backed by a charter clause (**C-7**)
> and a hook that blocks the edit.
>
> **Companion:** `docs/dev/AGENT_HANDOFF_TEMPLATE.md` requires this file
> be listed in every handoff prompt's "Documents to read" section.

---

## 5a. Diagnostics-as-fix

When a bug couldn't be reproduced from the agent's side, the
default response was "add more logging and ask the user to
retest." This produced commits that increased complexity
without fixing anything, and burned through multiple smoke
cycles (each one costing the user time + their LLM API
credits).

**Discipline:** when you can't reproduce, ASK the user for the
specific data point (log line, response body, screenshot) BEFORE
adding diagnostics. If you must add diagnostics, do it in a
SEPARATE commit and mark it explicitly as "diagnostic only —
will revert."

---

## 5b. Cascading fix attempts

Each round of smoke surfaced new bugs that were treated as
independent issues. In reality many were downstream symptoms of
upstream causes (e.g., paged.js errors caused by personas 500
→ iframe loads bad HTML → paged.js chokes). Fixing downstream
symptoms (sandbox attrs, placeholder HTML) added code without
fixing the root cause.

**Discipline:** when multiple bugs appear simultaneously, ask
"could one of these be causing the others?" before fixing
each independently.

---

## 5c. Security/architecture changes without explicit user sign-off

Added the traceback-in-detail pattern across 6 routes (security
implications), changed iframe sandbox attributes (security
implications), introduced new error-display patterns. All were
defensible in isolation but the user's principle is "no changes
that aren't seen or approved." The agent's pattern of
explaining trade-offs AFTER making the change violates that.

**Discipline:** any change with security, architectural, or
user-visible behavioral implications gets surfaced as a
plan BEFORE the edit, with the user's explicit go-ahead.

---

## 5d. Tool-induced churn

CRLF / heredoc / Edit-vs-Write mistakes produced multiple
commits where the same file was edited 3+ times to land one
intent. Wastes the user's review attention and clutters git
log.

**Discipline:** for non-trivial edits, READ the file, draft the
exact replacement string, then ONE Edit call. Don't iterate
in the file.

---

## 5e. Misplaced confidence

Several rounds ended with "this should fix it; let me know on
re-smoke" only to have the smoke return the same symptom or a
new one. The agent's confidence calibration was wrong.

**Discipline:** state explicitly what evidence supports a fix
working, what could still go wrong, and what to look for in
re-smoke. If the evidence is just "I changed this line,"
expect to be wrong about half the time.

---

## 5f. Guessing the mechanism

**This is the pattern that made the other five binding.** On 2026-07-13 an agent
spent an entire day and ~30% of a weekly token budget on an intermittent CI
flake and shipped **no solution** — because it read the code, found a plausible
mechanism, and fixed *that*. Twice. Without ever instrumenting to see what
actually happened. When it finally added visibility, **the cause printed itself
in a single run**.

The failure is not that it was careless. It is that patterns **5a, 5b and 5e
above already say this**, the agent had read them, and it judged that they did
not apply this time. Its own diagnosis subagent's report literally opened with
*"Step 0 — instrument first (do this before coding a fix)"* and it went straight
to Step 1.

**The trap that makes this so seductive: both wrong fixes were real defects.**
Non-atomic writes really were tearing reads. The missing client guard really was
missing. **Fixing a real defect that isn't THE defect still leaves the bug** —
and the plausibility of the mechanism is exactly what makes you skip the check.
Being right about *a* problem feels identical, from the inside, to being right
about *the* problem.

**Discipline — and this one is no longer advice.** Charter **C-7** makes it
binding and the `require-evidence-before-fix` hook enforces it: on a `fix/*`
branch you cannot edit production code until
`docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed` section.

- **The first commit on the branch is the instrument or the reproduction, never
  the fix.**
- **Never scope the instrument to the hypothesis you are testing.** The agent's
  first traffic dump captured only the two routes it already suspected — and so
  it *hid the actual culprit*. An instrument narrowed to your theory will confirm
  your theory. Capture wider than you think you need.
- **Keep "what I saw" and "what I think is happening" in separate sections, in
  writing.** Not as a formality: the act of trying to fill in `## Observed` is
  what surfaces the fact that you have not actually looked.
- **Green CI is not evidence if the test needed a retry.**
  `pytest-rerunfailures` reports a fail-fail-pass as a bare `PASSED` with no
  traceback anywhere in the log. The test in question had been failing **64% of
  its attempts for 11 runs** behind `--reruns 2`.
- **Say "I have not verified this" out loud, and stop** — rather than narrating a
  mechanism with confidence you have not earned.

Worked example, with every falsified hypothesis and what each cost:
[`diagnosis/compose-summary-draft-settle-hole.md`](diagnosis/compose-summary-draft-settle-hole.md).
