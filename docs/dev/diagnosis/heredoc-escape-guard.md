# Diagnosis — doubled backslashes in a Bash-tool command lose one backslash before bash runs (item 142)

> **Status:** the collapse is OBSERVED (O1–O4) and reproduced outside Claude Code (O4). The layer
> is located: Git Bash's own parse of its Windows command line. Why the MSYS2 runtime does it is
> inferred, not read from its source (see `## Inferred`).
> **Branch:** `fix/heredoc-escape-guard`

---

## Symptom

Item 142 (`docs/dev/work/items/0142-heredoc-python-escape-corruption-guard.md`): Python
scripts delivered through a Bash heredoc wrote broken files when their text held backslash
escapes. They wrote backspace bytes (`0x08`) where `\b` was meant, and real newlines where
`\n` was meant. It happened at least nine times between 2026-08-05 and 2026-10-07. Once it
silently disabled the docs-lint acronym check (`scripts/doc_lints.py`), and once it put two
backspace bytes into `tests/test_agent_tool_grant_consistency.py`.

---

## Observed

Machine: Windows 11, Claude Code's Bash tool is Git Bash (`MINGW64_NT-10.0-26200 3.6.6`,
`MSYSTEM=MINGW64`, `MSYS` unset), and `.claude/settings.json` has no `env` key. Session
`17250fd2`, 2026-10-07.

### O1 — through the Bash tool, every `\\` arrives as `\`

The Bash tool ran:

```
printf '%s|' 'A\\b' 'B\b' 'C\\\\b' "D\\b"
```

and printed:

```
A\b|B\b|C\\b|D\b|
```

Bash keeps every backslash inside single quotes, so the first and third fields should have
printed `A\\b` and `C\\\\b`. Each doubled run lost exactly half its backslashes, while the
single `\b` came through unchanged.

### O2 — the loss is already in bash's argv, before bash parses anything

In the same call, `tr '\0' ' ' < /proc/$$/cmdline` showed the token written as
`PROBE_X\\y_PROBE` arriving as `PROBE_X\y_PROBE'`. That is bash's own argument vector, before
any quoting or heredoc rule of bash's applies.

### O3 — the PowerShell tool keeps every backslash (control arm)

```
$a = 'A\\b'; $b = 'B\b'; $c = 'C\\\\b'; "{0}|{1}|{2}| lengths {3},{4},{5}" -f $a, $b, $c, $a.Length, $b.Length, $c.Length
```

printed `A\\b|B\b|C\\\\b| lengths 4,3,6`. Nothing collapsed.

### O4 — reproduced without Claude Code: Git Bash's command-line parse, switched off by `MSYS=noglob`

A script written with the Write tool (`repro_collapse.py`, in the session scratchpad) built the
text `printf %s 'X\\b|Y\b|Z\\\\b'` from `chr(92)`. Native Windows Python 3.13.14, run from the
PowerShell tool, then launched `C:/Program Files/Git/usr/bin/bash.exe` three ways. The run
lengths show how many backslashes each run held, against the expected `[2, 1, 4]`:

```
argv-default  rc=0 out='X\\b|Y\\b|Z\\\\b' runs=[1, 1, 2] err=''
argv-noglob   rc=0 out='X\\\\b|Y\\b|Z\\\\\\\\b' runs=[2, 1, 4] err=''
stdin         rc=0 out='X\\\\b|Y\\b|Z\\\\\\\\b' runs=[2, 1, 4] err=''
command line python built: '"C:/Program Files/Git/usr/bin/bash.exe" -c "printf %s \'X\\\\b|Y\\b|Z\\\\\\\\b\'"'
```

(The `out=` values are Python `repr()`, so each real backslash shows as two.)

- **argv-default** is `bash -c <text>` with `MSYS` unset. Every doubled run halved; the single
  one survived.
- **argv-noglob** is the same call with `MSYS=noglob` in the environment. It came through
  intact.
- **stdin** is `bash -s` with the same text on stdin, where no command line carries it. It
  came through intact.
- **The command line Python handed to Windows** still held every backslash
  (`subprocess.list2cmdline`, last line). So the loss happens when bash.exe rebuilds its argv
  from that command line.

### O5 — the recorded incidents: the transcript holds the intended count every time

The transcripts were re-decoded with `json.loads` by `decode_transcripts.py` (session
scratchpad). The decoded string is what the harness received from the model. Line numbers
below are 1-based file lines. The explorer that found them cited them 0-based.

| Transcript (session) | Line | Shape | Backslashes at the corrupting spot (decoded) | The result that followed |
|---|---|---|---|---|
| `08aa18b5` (2026-10-07) | 799 | `python - <<'EOF'` | 2 before `n` (`"# p\\n"`) | `SyntaxError: unterminated string literal (detected at line 153)` |
| `08aa18b5` | 980 | `cat > …/tooling_md.py <<'PYEOF'` | 2 before `\|`, 5 places | `tooling_md.py:17: SyntaxWarning: invalid escape sequence` |
| `08aa18b5` | 1283 | `cat > …/small_tests.py <<'PYEOF'` | 2 before `b`, `w`, `.`, `b` (`r"\\bhooks/[\\w/-]+\\.sh\\b"`) | `small_tests.py:26: SyntaxWarning: invalid escape sequence` |
| `08aa18b5` | 833 | `grep -n '\\n\|…'` (no heredoc) | 2 before `n` | no error shown: a mis-matching pattern is silent |
| `08aa18b5` | 994 | `grep -c 'Edit\\|Write…'` (no heredoc) | 2 before `\|`, 4 places | no error shown |
| `f0c731c3` (2026-10-01) | 780 | `cat > …/edit_lints2.py <<'PYEOF'` | 2 before `b` (`rf"\\b{acr}s?\\b"`) | no error shown: this is the run that disabled the acronym check |
| `f0c731c3` | 799 | `sed -i 's/\x08/\\b/g'` (the repair, no heredoc) | 2 before `b` | no error shown |
| `f0c731c3` | 2337 | `python - <<'PYEOF'` | 2 before `n`, 4 places | `invalid-syntax: missing closing quote in string literal` (ruff) |
| `f0c731c3` | 2607 | `python - "$S/edit_checker.py" <<'PYEOF'` | 1 and 2 | `AssertionError` (an anchor did not match) |
| `f0c731c3` | 3495 | `python - "$S/write_handoff.py" <<'PYEOF'` | 2 before `n` | `AssertionError: anchor` |

- Python raises `SyntaxWarning: invalid escape sequence` for `\w` or `\|`, never for `\\w` or
  `\\|`. So in rows 980 and 1283 Python itself received one backslash where the decoded command
  had two.
- A `SyntaxError: unterminated string literal` or a `missing closing quote` means a real newline
  sat inside a string literal: `\n` arrived where `\\n` was sent.
- Every heredoc here used a **quoted** delimiter (`<<'EOF'`, `<<'PYEOF'`), which bash does not
  escape-process.
- The 2026-08-05 transcript (`b7fe246e…`) is no longer on disk. That incident is known only from
  the owner's memory note and the old handoff, so it is not counted here.

---

## Falsified

- **"The model emits too few backslashes."** Every decoded transcript command (O5) holds the
  intended two. What the harness received from the model was right.
- **"Bash's heredoc processing eats them."** Every recorded heredoc used a quoted delimiter,
  which bash does not escape-process. Plain single-quoted arguments with no heredoc collapse the
  same way (O1, and O5 rows 833, 994 and 799 of `f0c731c3`). And O2 shows the loss in bash's
  argv, before bash parses.
- **"It is specific to heredoc'd Python."** It is any `\\` anywhere in a Bash-tool command
  (O1, O5's `grep` and `sed` rows). Item 142's filed candidate, "refuse `python -` from a heredoc
  whose body contains a backslash", would have missed three of the ten rows in O5.
- **"The Windows-side launcher drops them."** The command line Python built for bash.exe still
  held every backslash (O4, last line), and the same text on stdin came through intact.

---

## Inferred

- **Why Git Bash does it.** This is from knowledge of the Cygwin/MSYS2 runtime and was not read
  from its source this session. When a native Windows program starts an MSYS2 program, the
  runtime rebuilds `argv` from the Windows command line with its own quoting rules. Those rules
  treat `\\` inside a quoted argument as one escaped backslash. `MSYS=noglob` switches that
  rebuild to plain splitting, which O4 shows works. Claude Code launches the Bash tool's bash as
  a native program (`bash -c "… eval '<command>'"`), so every command passes through this
  rebuild. What would make it known: the runtime's source, or the runtime's own changelog.
- **`MSYS=noglob` as a root-cause fix inside Claude Code** (settings `env`). It worked in O4 but
  was not tested in the harness, and verifying it needs a restarted session. It is filed as its
  own item, not built here (owner decision, 2026-10-07).
- **Hosts other than this one.** Linux and macOS hand bash its argv directly through `execve`,
  with no Windows command line to rebuild, so no collapse is expected there. That has not been
  observed on hypha or the homelab.
- **A separate, unexplained class:** bash refusing a whole command with
  `unexpected EOF while looking for matching '`. It appears in five transcripts. This mechanism
  does not obviously explain it, and it is filed separately.

---

## Falsification

The question was which layer drops the backslash. O4 settles it without Claude Code in the
loop: the same text survives on stdin and with `MSYS=noglob`, and halves through bash.exe's
command line. `tests/test_bash_backslash_collapse.py` pins O4 as a test: Windows-only, skipped
when Git Bash is absent. **If it ever fails, the collapse is gone, and the guard below has lost
its premise.**

---

## The fix

A `bash-dispatcher` guard, `block-doubled-backslash`
(`scripts/enforcement/guards/block_doubled_backslash.py`). On Windows it refuses any Bash-tool
command containing two consecutive backslashes, because the command bash would run is not the
one written. The message gives the ways through: the Write tool and then run by path, the Edit
tool, the PowerShell tool, or `chr(92)`. It allows everything on other platforms (owner
decision, 2026-10-07). The guard sees the intended text: hooks receive the tool input as JSON
on stdin, not through a command line.

---

## Acceptance bar

- Unit and dispatcher tests for the guard pass with `-p no:rerunfailures`, with the block path
  on Windows and the allow path on Linux CI.
- Live, in this session after the wiring lands: a Bash command containing `\\` is refused with
  `BLOCKED (block-doubled-backslash)`, and a command with a single `\` runs.
- `tests/test_bash_backslash_collapse.py` passes on this machine.
