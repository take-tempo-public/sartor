# Diagnosis — the Bash tool's command line: `MSYS=noglob` is no fix (item 157), and Git Bash cuts it at 8,186 characters (item 158)

> **Status:** both mechanisms are OBSERVED at their layer. `MSYS=noglob` breaks every quoted
> command on the harness's real command line (O3). Git Bash cuts a command-line argument to
> 8,186 characters (O4–O6), which explains six of the seven recorded item-158 failures (O7).
> Why the MSYS2 runtime does either is inferred, not read from its source (`## Inferred`).
> **Branch:** `fix/bash-tool-transport`

---

## Symptom

- **Item 157** (`docs/dev/work/items/0157-msys-noglob-root-cause-for-backslash-collapse.md`).
  `MSYS=noglob` stopped Git Bash halving doubled backslashes in item 142's standalone repro
  (`heredoc-escape-guard.md` O4). It was proposed as the root-cause fix, set through
  `.claude/settings.json` `env`, and never tried inside Claude Code.
- **Item 158** (`docs/dev/work/items/0158-bash-unexpected-eof-matching-quote.md`). The Bash tool
  sometimes refused a whole command with
  `unexpected EOF while looking for matching '`, in about six sessions. The cause was unknown.

---

## Observed

Machine: Windows 11. The Bash tool is Git Bash (`MINGW64_NT-10.0-26200 3.6.6-1cdd4371.x86_64`,
`MSYSTEM=MINGW64`, `MSYS` unset), Claude Code `2.1.293`, and native Windows Python 3.13. Session
`5f4fe262`, 2026-10-08. O1–O3 and O7 were first run read-only in plan mode on `main` @ `38cec69`
and re-run on this branch. **In the artifacts below, the user's home directory is written as
`<home>`.**

### O1 — the harness wraps every command as `eval '<cmd>'`, rewriting each `'` as `'"'"'`

Through the Bash tool, `tr '\0' '\n' < /proc/$$/cmdline` printed bash's own argv:

```
/usr/bin/bash
-c
source <home>/.claude/shell-snapshots/snapshot-bash-1791484381942-7e9ft1.sh 2>/dev/null || true && export TEMP='<home>\AppData\Local\Temp' TMP='<home>\AppData\Local\Temp' && shopt -u extglob 2>/dev/null || true && { \builtin unalias -- 'unsetenv'; \builtin unset -f -- 'unsetenv'; } >/dev/null 2>&1 || true && eval ': '"'"'PROBE_SQ'"'"' "PROBE_DQ" PROBE_BS\x; echo "MSYS=${MSYS-unset}"; …' && pwd -P >| <home>/AppData/Local/Temp/claude-786f-cwd
```

### O2 — the raw Windows command line escapes every `"` as `\"`

This includes the `"` the wrapper adds for every `'`. Through the Bash tool,
`powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Process -Filter 'ProcessId=$W').CommandLine"`,
with `W=$(cat /proc/$$/winpid)`, printed the command line Windows holds for that bash:

```
"C:\Program Files\Git\bin\..\usr\bin\bash.exe" -c "source <home>/.claude/shell-snapshots/snapshot-bash-1791484381942-7e9ft1.sh 2>/dev/null || true && export TEMP='<home>\AppData\Local\Temp' TMP='<home>\AppData\Local\Temp' && shopt -u extglob 2>/dev/null || true && { \builtin unalias -- 'unsetenv'; \builtin unset -f -- 'unsetenv'; } >/dev/null 2>&1 || true && eval ': '\"'\"'SQ'\"'\"' \"DQ\" BS\x; W=$(cat /proc/$$/winpid); echo \"winpid=$W\"; powershell.exe -NoProfile -Command \"(Get-CimInstance Win32_Process -Filter '\"'\"'ProcessId=$W'\"'\"').CommandLine\"' < /dev/null && pwd -P >| <home>/AppData/Local/Temp/claude-1ed3-cwd"
```

That is MSVCRT quoting, which `subprocess.list2cmdline` reproduces. The harness added
`< /dev/null` after the eval here but not in O1, whose command carried its own `<` redirect.

### O3 — in the harness's own form, `MSYS=noglob` makes a quoted command unparseable

`transport_probe.py` (session scratchpad, written with the Write tool), section A, builds
`printf '%s|' 'SQ' "DQ" 'A\\b' 'B\b'; echo` from `chr()`. It wraps the command as in O1, quotes
it with `list2cmdline` as in O2, and starts `C:/Program Files/Git/usr/bin/bash.exe` three ways:

```
cmd     : printf '%s|' 'SQ' "DQ" 'A\\b' 'B\b'; echo
cmdline : "C:/Program Files/Git/usr/bin/bash.exe" -c "eval 'printf '\"'\"'%s|'\"'\"' '\"'\"'SQ'\"'\"' \"DQ\" '\"'\"'A\\b'\"'\"' '\"'\"'B\b'\"'\"'; echo'"
default : rc=0 out='SQ|DQ|A\\b|B\\b|' err=''
noglob  : rc=2 out='' err="/usr/bin/bash: -c: line 1: unexpected EOF while looking for matching `''"
stdin   : rc=0 out='SQ|DQ|A\\\\b|B\\b|' err=''
```

(`out=` is Python `repr()`, so each real backslash shows as two.)

- **default** (`MSYS` unset): `A\\b` arrived as `A\b`. This is item 142's halving, now on the
  harness's real command-line form.
- **noglob**: the `-c` script itself no longer parses, rc 2, with item 158's message.
- **stdin**: every backslash survived.
- Item 142's O4 `noglob` arm passed only because its payload put no `"` on the command line.

### O4 — Git Bash cuts a command-line argument to 8,186 characters, silently

`transport_probe.py` section B. Each `-c` script is `echo ${#BASH_EXECUTION_STRING} #` plus
ASCII padding, so it reports the length bash received:

```
sent=  8132 default received=  8132 | noglob received=  8132
sent=  8232 default received=  8186 | noglob received=  8232
sent=  9032 default received=  8186 | noglob received=  9032
sent= 16032 default received=  8186 | noglob received= 16032
sent= 32032 default received=  8186 | noglob received= 32032
largest intact (default): sent 8186 -> received 8186; sent 8187 -> received 8186
```

The cut is silent: rc 0 and nothing on stderr. Under `noglob` there is no cut, but O3 rules
`noglob` out.

### O5 — the 8,186 cap counts characters, not UTF-8 bytes

`transport_probe.py` section C pads with U+2014 (3 bytes in UTF-8) and compares the text received
with the text sent:

```
largest intact: 8186 chars / 24486 UTF-8 bytes (ok=True)
one more pad  : sent 8187 chars / 24489 bytes -> received 8186 chars / 24486 bytes (ok=False)
```

### O6 — inside the harness: a command over the cap is refused, and the wrapper adds 408 characters

Two Bash-tool calls, made before any guard existed. Each starts with
`echo "PROBE-… T=${#BASH_EXECUTION_STRING}"`, followed by lines of balanced `''` pairs. Each `'`
costs 5 wrapped characters (O1).

- **Probe A**, 12 lines of padding, printed:

  ```
  PROBE-A T=7094
  PROBE-A done
  ```

- **Probe B**, 15 lines of padding, ran nothing (no `T=` line) and returned:

  ```
  Exit code 2
  /usr/bin/bash: -c: line 16: unexpected EOF while looking for matching `"'
  ```

`probe_overhead.py` (session scratchpad) read both commands back from this session's transcript:

```
L289 'echo "PROBE-': len=1886 sq=1200 lines=14 wrapped(len+4*sq)=6686
L300 'echo "PROBE-': len=2342 sq=1500 lines=17 wrapped(len+4*sq)=8342
```

- **The harness wrapper adds 7094 − 6686 = 408 characters** on this machine. That figure
  includes the home directory four times and is session-specific in its paths.
- So the longest command that fits here is 8186 − 408 = 7,778 wrapped characters.
- Probe B's wrapped command alone (8,342) exceeds 8,186.

### O7 — the item-158 record: 7 real failures, 6 of them over the cap

`decode_158.py` (session scratchpad) reads every transcript holding the string. That is the six
the item lists, plus the item-142 session and its subagent, plus one workflow subagent the item
does not list. It matches each `tool_result` carrying `unexpected EOF while looking for matching`
to its `tool_use` (`json.loads`). It then checks each Bash command three ways, none of which runs
it:
- as written, `bash -n -s` with the command on stdin;
- through the default transport: O1's wrapper with `printf %s` in place of `eval`, then
  `bash -n` on what arrived;
- through `MSYS=noglob`: `bash -n -c "eval '<cmd>'"`.

Line numbers are 1-based file lines.

| # | Transcript : `tool_use` line | Error in the transcript | len / lines / `'` / longest `\` run / wrapped (len+4·`'`) | As written (`bash -n`, stdin) | Default-transport replay |
|---|---|---|---|---|---|
| 1 | `2b79cef7`:677 | `-c: line 198` EOF `'` | 8538 / 223 / 75 / 2 / 8838 | parses | rc 2, `-c: line 198` EOF `'` |
| 2 | `d3d2e857`:1187 | `eval: line 1` EOF `` ` `` | 152 / 1 / 0 / 1 / 152 | **rc 2, the same error** | intact; still rc 2 |
| 3 | `d3d2e857`:1298 | `-c: line 139` EOF `'` | 11979 / 222 / 41 / 0 / 12143 | parses | rc 2, `-c: line 143` |
| 4 | `dde107cd`:1132 | `-c: line 126` EOF `'` | 9280 / 181 / 57 / 1 / 9508 | parses | rc 2, `-c: line 153` |
| 5 | `f0c731c3`:430 | `-c: line 181` EOF `'` | 7846 / 190 / 58 / 2 / 8078 | parses | rc 0: no cut (`-c` 8,090 long), but `\\s` arrived as `\s` |
| 6 | `ec0ddb33`:227 | `-c: line 164` EOF `'` | 14833 / 323 / 173 / 2 / 15525 | parses | rc 2, `-c: line 167` |
| 12 | `e713dc79` workflow agent `a2fc7baa`:306 | `-c: line 50` EOF `"` | 8452 / 64 / 210 / 0 / 9292 | parses | rc 2, `-c: line 51` |

- **Rows 7–11 are not tool errors.** They are a Read result, an ExitPlanMode result, a Read of
  the board, and two Bash calls by item 142's transcript explorer whose output quoted the string.
- **Rows 1, 3–6 and 12 failed at the outer `-c:` level**, while bash was parsing the wrapper
  itself. All six parse as written. All six exceed the cap once O6's 408-character wrapper is
  added (row 5: 8,078 + 408 = 8,486).
- **The replay's wrapper is shorter than the harness's,** so its cut lands at the same line or
  later, never earlier. Row 5 (8,090 in the replay) stayed under the cap there.
- **Three of the six contain no doubled backslash at all** (rows 3, 4 and 12: longest run 0, 1
  and 0).
- **Row 2 is a different class.** The command was malformed as written:
  `grep -n -i "python\|script\|check_\|```"` opens a backtick command substitution inside double
  quotes. It failed at the inner `eval:` level, and `bash -n` on stdin refuses it identically.
- **The `noglob` arm** gave rc 2 for rows 1, 4, 5, 6 and 12 (and for rows 10 and 11, which parse
  fine as written), and rc 0 for rows 2 and 3. A parse-only check on a mis-split argument shows
  only that the first fragment parsed, so those rc 0 results are not evidence that `noglob`
  carried the command intact. O3 shows it does not.

---

## Falsified

- **"`MSYS=noglob` is the root-cause fix for item 142"** (item 157's premise). On the harness's
  real command line it turns any command containing a quote into a bash syntax error (O3). Set
  in `.claude/settings.json`, it would break nearly every Bash-tool call. The earlier standalone
  success (item 142 O4) used a payload with no `"`.
- **"Item 158 is item 142's halving."** Three of the six over-cap failures contain no doubled
  backslash (O7). Halving changes backslash counts; these commands were cut.
- **"Item 158 is the Windows command-line length limit."** The cut is at 8,186 characters (O4).
  Windows allows 32,767, and a 32,032-character argument reached bash intact under `noglob`.
- **"Item 158 is one mechanism."** Row 2 (O7) is a malformed command that bash refuses on stdin
  too. It is not transport.

---

## Inferred

- **Why the runtime cuts at 8,186, and why `noglob` changes quoting.** This is from knowledge of
  the Cygwin/MSYS2 runtime, not read from its source.
  - When a native program starts an MSYS2 program, the runtime rebuilds `argv` from the Windows
    command line. In the default (glob) mode it passes each quoted argument through `glob()`.
  - `glob()`'s backslash unescape would explain the halving.
  - A pattern buffer of about 8K characters would explain the cut. 8,186 is 8,192 − 6.
  - `MSYS=noglob` skips `glob()`, which is why the halving and the cut both vanish. It also
    seems to take a splitter that does not honour `\"` as an escaped quote, so the first `\"`
    ends the argument.
  - What would make it known: the runtime's `build_argv`/`globify`/`glob` source.
- **A cut that leaves balanced quotes could run a truncated command** instead of failing loudly.
  For example, a cut just after `'"'"` closes the outer quoting. Not observed: every recorded
  cut failed to parse.
- **Hosts other than this one.** Linux and macOS start bash through `execve`, with no Windows
  command line to rebuild, so no cut is expected there. Not observed on hypha or the homelab.
- **Characters outside the Basic Multilingual Plane** may count as two toward the cap, if the
  runtime counts UTF-16 units. Not measured; O5 used U+2014.

---

## Falsification

The question for item 157 was whether `MSYS=noglob` carries the harness's command intact. O3
answers no, on the exact command-line form Windows holds (O2).

The question for item 158 was whether the refused commands were broken before or after transport.
O7 answers it per command:
- six parse on stdin and fail only through the command line;
- the command line cuts at 8,186 (O4);
- the harness refuses a padded command just past that cap with the same error (O6).

`tests/test_bash_backslash_collapse.py` pins O3 and O4 alongside item 142's halving. It is
Windows-only and skipped without Git Bash. **If the cut test ever fails, the cap has moved, and
the guard below must be re-measured.**

---

## The fix

A `bash-dispatcher` guard, `block-long-bash-command`
(`scripts/enforcement/guards/block_long_bash_command.py`). The owner chose a new, separate
guard on 2026-10-08.
- On Windows it refuses a Bash-tool command whose wrapped length (`len + 4 × '`) exceeds
  `BUDGET = CUT − RESERVE`, which is 8,186 − 1,024 = 7,162.
- The reserve stands for the harness's own wrapper. O6 measured 408; the rest is headroom for
  longer home and temp paths.
- The way through is to write the script with the Write tool and run it by path.
- It allows everything on other platforms.
- The cost is O(n) `len` and `count` in the existing dispatcher process, with no subprocess.
- `tests/test_bash_backslash_collapse.py` takes `CUT` from the guard, so a guard constant that
  drifts from the measured runtime fails on Windows.

Item 157 is closed as falsified, on the standalone evidence (owner decision, 2026-10-08).
`.claude/settings.json` does not change. The `block_doubled_backslash.py` docstring, which said
`noglob` would remove that guard's premise, now says it breaks quoting.

**Live, in this session, right after the wiring landed (2026-10-08):**

- **LIVE-1.** The same padding as probe B (O6) was refused before bash saw it:

  ```
  PreToolUse:Bash hook error: [python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" bash-dispatcher]: BLOCKED (block-long-bash-command): this command is 8,340 characters once the Bash tool wraps it (every ' counts as 5), over the 7,162 budget. …
  ```

- **LIVE-2.** `echo "LIVE-2 short command runs, T=${#BASH_EXECUTION_STRING}"` ran and printed
  `LIVE-2 short command runs, T=469`. That command is 61 characters with no `'`, so the wrapper
  added 469 − 61 = 408 characters. This confirms O6's figure from a second, independent command.
- **LIVE-3.** `printf '%s\n' 'LIVE-3 A\\b'` is still refused by the other guard:
  `BLOCKED (block-doubled-backslash): this command contains `\\`. …`

---

## Acceptance bar

- `tests/test_bash_backslash_collapse.py` passes on this machine with `-p no:rerunfailures`. It
  covers the halving, stdin, `noglob` on the simple form, `noglob` breaking the harness form, and
  the 8,186 cut.
- The guard's unit and dispatcher tests pass, with the block path on Windows and the allow path
  on Linux CI.
- Live, in this session after the wiring lands:
  - an over-budget command is refused with `BLOCKED (block-long-bash-command)`;
  - a short command runs;
  - a command containing `\\` is still refused by `block-doubled-backslash`.
