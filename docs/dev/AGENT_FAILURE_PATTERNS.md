# Agent failure patterns to avoid

> **Purpose:** permanent reference for dev agent behavioral discipline.
> These patterns were identified during the v1.0.1 release arc and have
> recurred across sessions. Every agent should read this before writing
> any code.
>
> **Source:** harvested from `docs/SESSION_HANDOFF_2026-05-27.md §5`,
> which remains the original session record. This file is the undated,
> canonical home for these rules.
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
