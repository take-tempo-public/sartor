# Diagnosis — <one-line symptom>

<!--
  Copy me to docs/dev/diagnosis/<branch-slug>.md, where <branch-slug> is your branch name
  minus the `fix/` prefix. The `require-evidence-before-fix` hook looks for exactly that
  path and will not let you edit production code until `## Observed` below is filled in.

  Copying this file is NOT enough — every placeholder line here is italic, and the gate
  ignores italic lines on purpose. You have to actually write something.

  The one rule that matters: KEEP `## Observed` AND `## Inferred` APART.
  Conflating them is a whole category of expensive failure. An hour spent noticing
  "I have not actually seen this happen" is the cheapest hour in the whole project.
-->

> **Status:** <root cause PROVEN / hypothesis only — say which, plainly>
> **Branch:** `fix/<slug>`

---

## Symptom

_What a user or a test sees. No theory yet — just the complaint._

---

## Observed

<!--
  FACTS WITH ARTIFACTS BEHIND THEM. Nothing in this section may be a deduction.

  Each entry should be something you could hand to a stranger and have them agree with:
  a log line, an HTTP response body, a CI run id, a measurement, a test that fails.
  If you catch yourself writing "so it must be…", stop — that belongs under `## Inferred`.

  (This guidance is inside a comment on purpose: the gate ignores comments and italics, so
  copying this file can never satisfy it. You have to write real content here. Yes, really.)
-->

_(Nothing yet. Instrument first. If you cannot fill this in, you have not looked — and that_
_is the finding, not an obstacle to it.)_

---

## Falsified

<!--
  DEAD ENDS, AND WHAT KILLED EACH ONE. As valuable as what survives: without this list the
  next reader re-chases every one of them, and they are rarely cheap.

  Include your OWN discarded fixes — especially the plausible ones. A fix for a real defect
  that isn't THE defect still leaves the bug, and its plausibility is precisely what made it
  worth shipping at the time.
-->

_(Nothing yet.)_

---

## Inferred

<!--
  THIS IS A HYPOTHESIS. IT IS NOT FACT. Do not build on it until the experiment below has run.

  Say what you think is happening — and then, honestly, why it is still only a guess. Name
  the gap: what would you have to SEE in order to actually know?
-->

_(Nothing yet.)_

---

## Falsification

**The experiment that settles it. Run this BEFORE writing any fix.**

State it so it can fail: a test that **must fail on HEAD**, deterministic, no browser and no
race if you can manage it. Then say, in advance, what each outcome means —

- **If it fails on HEAD:** the hypothesis is confirmed; you may build the fix.
- **If it passes on HEAD:** the hypothesis is **dead**. Stop. Do not fix. Widen the instrument
  and report.

_(Write the experiment here.)_

---

## The fix

_Only after the experiment above has actually failed. Describe the change and why it addresses_
_the mechanism you PROVED, not the one you assumed._

---

## Acceptance bar

_How you will know it is genuinely fixed. Be specific, and be strict: "CI is green" is not a_
_bar if the test needed a retry to get there — `pytest-rerunfailures` reports a fail-fail-pass_
_as a bare `PASSED` with no traceback anywhere in the log._
