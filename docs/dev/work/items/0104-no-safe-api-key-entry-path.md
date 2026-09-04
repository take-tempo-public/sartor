```toml
schema = 1
id = 104
kind = "item"
title = "Every documented API-key entry method writes the key into shell history"
status = "closed"
decision_owner = "agent"
branches = [
  "feat/install-onboarding-preflight","docs/container-persistence-guidance"]
refs = ["web_infra/clients.py:47-64", "docs/install.md", "SECURITY.md"]
summary = "Every documented key-entry method puts the key in shell history; --setup should prompt and write .api_key."
resolution = "Built on feat/install-onboarding-preflight (2026-09-03), exactly the fix the item proposed. `sartor --setup` now prompts for the key via getpass when neither ANTHROPIC_API_KEY nor .api_key resolves, and writes .api_key itself through os.open(..., 0o600) so the file is never even briefly world-readable (write_text + a follow-up chmod leaves a window). Three refusals, each tested: never prompts when a key already resolves (--setup is documented idempotent), never on a non-interactive stdin (a container build or CI step would block forever on an unanswerable tty read), and never echoes or logs the key. The prompt runs BEFORE the ~180MB of downloads so a keyless user learns it in the first second. preflight.api_key_path() is the single resolution the writer and the reporter share, and a test asserts it equals what web_infra.clients._get_client actually reads. Docs updated alongside: a 'keep it out of your shell history' section covering the HISTFILE ordering trap and the rotate-if-it-left-your-machine advice, plus all three per-OS key steps rewritten to lead with the prompt. STATED LIMIT (C-0): the 0o600 mode is largely inert on Windows, where the ACL is the real control; _write_api_key does not attempt to set one, and says so in its docstring."
verified_by = [
  "tests/test_setup_api_key.py::TestPromptForApiKey (9 tests incl. test_the_key_is_never_echoed_to_stdout_or_stderr and test_uses_getpass_not_input)",
  "tests/test_setup_api_key.py::TestWriteApiKey::test_file_is_owner_only (POSIX; skips on Windows, which uses ACLs)",
  "tests/test_setup_api_key.py::TestKeyPathAgreement::test_preflight_and_the_app_client_resolve_the_same_file",
]
```

**Found during a live install** (2026-09-02). Every documented way to supply the Anthropic
key puts it in plaintext shell history:

- the container path's `docker run -e ANTHROPIC_API_KEY=sk-ant-...`
- `export ANTHROPIC_API_KEY=sk-ant-...`
- writing the key file with `echo`/`printf` into `.api_key`

Nothing in the docs warns about this or offers a non-echoing alternative. The user
discovered it themselves mid-install and had to be walked through scrubbing
`~/.zsh_history` — including the non-obvious ordering problem that closing the terminal
re-flushes the in-memory history over a scrubbed file, so `unset HISTFILE` has to come first.

**Aggravating context.** This machine was not the key owner's own; a test key ended up both
in history and in `.api_key` on hardware they do not control. The remedy there is key
rotation, but the exposure was avoidable.

**Proposed fix.** `sartor --setup` should prompt for the key when `.api_key` and
`ANTHROPIC_API_KEY` are both absent, read it without echo, and write `.api_key` with mode
600 itself. That removes the exposure and removes a manual step at the same time — the key
file is already the resolution path `web_infra/clients.py:57-64` falls back to.

## Updates

### 2026-09-02 — filed from a live macOS install session

Raised by the user unprompted ("and then clear shell history?"), which is the signal that
the docs should have covered it.
