# Using the in-app assistant

> **Purpose:** the user-facing explanation of the built-in assistant — what it is, how
> to ask it questions, and what it can and can't answer.
> **Audience:** `user` — no technical background assumed.
> **Grounding:** the assistant pill + modal in `templates/index.html`
> (`#assistantPill`, `#assistantModal`, `#assistantDevMode`) driven by
> `static/assistant.js` (`openAssistantModal`, `askAssistant`); the
> `/api/assistant/ask` route in `blueprints/assistant.py` and
> `analyzer.avatar_answer_streaming` (`AVATAR_SYSTEM_PROMPT`).

---

callback has a built-in assistant — a friendly guide to how the app works and how to use
it. It answers **only from callback's own documentation**, so what it tells you is
grounded, not guessed.

## Asking a question
Click the **magnifier** icon in the top bar to open the assistant, type your question
("How do I tailor a résumé?"), and send. You don't need to pick a user first — its
answers are the same for everyone, and it never reads your private data.

## What it can answer
It draws on these how-to pages and the rest of callback's wiki. If something isn't
documented, it says so plainly — "I don't have that in my docs" — rather than making
something up, and points you to the nearest thing it does cover. Each answer ends with
**numbered sources** you can click to read the original.

## Dev mode
There's a **Dev mode** tick-box for the technically curious: turn it on and the
assistant will also draw on the code and explain how callback is built, not just how to
use it. Leave it off for plain how-to answers.

The assistant is grounded the same way everything callback writes is — see
[[using-callback]].
