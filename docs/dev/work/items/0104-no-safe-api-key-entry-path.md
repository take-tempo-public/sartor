```toml
schema = 1
id = 104
kind = "item"
title = "Every documented API-key entry method writes the key into shell history"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
refs = ["web_infra/clients.py:47-64", "docs/install.md", "SECURITY.md"]
summary = "Every documented key-entry method puts the key in shell history; --setup should prompt and write .api_key."
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
