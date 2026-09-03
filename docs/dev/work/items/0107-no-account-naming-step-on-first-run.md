```toml
schema = 1
id = 107
kind = "item"
title = "First run offers no account-naming step; the account is named after the email address"
status = "open"
decision_owner = "agent"
branches = ["docs/first-run-account-naming-finding"]
refs = ["onboarding/corpus_import.py", "docs/walkthrough.md"]
summary = "No first-run step to name the account; it defaults to the email address while settings shows the real name."
```

**Observed by the owner on a first-run install** (2026-09-02, macOS native install, fresh
data directory).

1. Opening the app for the first time offered **no opportunity to name the account**.
2. A résumé was imported.
3. The account was named after the **email address**.
4. The **name was set correctly in settings** — so the résumé's name field was extracted fine;
   it just wasn't what the account got called.

**Two things wrong, and they're separable.** There is no onboarding step where a user chooses
the account name, and the fallback picks the email address over the name the import already
has in hand. Either could be fixed without the other; both are worth fixing.

**Why the account name matters more than a label.** It is the per-user directory segment
(`configs/<user>`, `resumes/<user>/`, `output/<user>/`), so a user who never chose it ends up
with an email address in their folder paths, visible in Finder and in every generated file's
location. Renaming later is not a settings edit.

**No mechanism claimed.** A grep of `onboarding/corpus_import.py` and `blueprints/corpus/`
turned up no obvious email-to-username derivation, so where the account name is actually
assigned has not been located. **This item records the observation only** — the mechanism is
unknown, not withheld (C-7/C-12). Whoever picks it up should trace the first-run account
creation path before proposing a fix.

**Related.** The onboarding flow is what a first-time user meets before anything else; this
sits alongside item 100's finding that the install path assumes knowledge the user does not
have, and item 105's education-import gap found in the same session.

## Updates

### 2026-09-02 — filed from a live first-run install session

Owner's report, verbatim in substance: never had a chance to name the account; it imported a
résumé and made the account name the email address, though settings had the name set.
