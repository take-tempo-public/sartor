<!-- provenance: schema=1 session=19babbc7-54bd-4b7a-890f-6491880aa395 branch=feat/data-root commit=e31fd09 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-16 -->

# Agent handoff — item 145, branch 1 of 3: one data root under `SARTOR_HOME` (`feat/data-root`) → owner's next pick

**Branch to create:** none chosen. The owner picks the next item. Natural follow-ons: item 145's branch 2
(`feat/launcher`, owner questions listed under "What this branch should build"), the remaining
container checks, or the item-164 instrument. Do not start one unprompted.
**Base branch:** `main`

> **This session took item 145 (owner pick, 2026-10-15), cut it into three sequential branches at the
> owner's direction, and did branch 1. The branch is committed (14 commits, 15 with this handoff's
> update) and PR #178 is open. The full gate **passes on a clean checkout of its code and fails in place for
> three tests**, because another session's worktree sits inside this directory (see "What just landed").
> It is NOT merged: the merge is the owner's.**
> - **The change:** `sartor_home.py` (new stdlib-only leaf: `base_dir()` = `SARTOR_HOME` > the repo root
>   in a checkout > the per-user platform dir; `data_path()`); `config._default_base_dir` is now an alias
>   of it. Every user-data writer follows it: `analyzer.py` (log), `db/session.py` (the DB),
>   `preflight.api_key_path` (the key, one resolver for the client, the onboarding CLI, the eval runner,
>   `--setup` and `--doctor`), `onboarding/corpus_import.py`, `evals/{annotation,bootstrap,runner}.py`.
>   Shipped files are no longer looked up under the data root: bundled personas
>   (`_persona_row_location`), the cover-letter shell (`Config.cover_letter_shell`), and a containment
>   recheck. `Dockerfile`: `SARTOR_HOME=/data`, `VOLUME ["/data"]`, a stdlib `HEALTHCHECK`. Docs, wiki,
>   CHANGELOG. Dossier, with the consumer enumeration and every observation:
>   `docs/dev/blast-radius/data-root.md`.
> - **Observed (C-7), one run each unless stated** (dossier `## Observed`, O1–O9):
>   - A fresh interpreter with `SARTOR_HOME` set before import: **12 of 13** probed sites resolved under
>     `C:\Dev\sartor` (log, DB, key, the onboarding dirs, both `ALLOWED_ROOT`s, the runner's log path);
>     **13 of 13** after. `Config().annotation_root` was the only one that already followed it.
>   - **Bundled personas broke outside a checkout.** Under `SARTOR_HOME` the resolver returned `None` and
>     the app logged `Persona template id=1 has invalid path personas/bundled/classic.docx`;
>     `GET /api/personas/<id>/download` answered `404 Persona file missing on disk` (run against `HEAD`
>     in a detached scratch worktree). After: **200, 37,354 bytes**, on the real app.
>   - **Real app under `SARTOR_HOME=<scratch>`** (`python app.py --no-browser`): `/healthz` 200 to the
>     same `urlopen` call the `HEALTHCHECK` uses, DB created under the scratch root, `POST /api/shutdown`
>     202 and **gone in 1.44 s**. The owner's real `logs/llm_calls.jsonl`, `db/resume.sqlite` and
>     `.api_key` had identical size and mtime before and after; the `python.exe` count was back to its
>     start value and the port had no listener.
>   - **The container, built and run locally** (rootful Podman 5.8.3, from a clean `git archive`;
>     dossier O10–O13): `HEALTHCHECK` healthy after 34–35 s; a fresh named `/data` owned by uid 10001;
>     data survived remove-and-recreate **and starting a newer image on the same volume**; Chromium
>     rendered an 8,966-byte PDF as that user; `podman stop` **11.0 s and 11.2 s** with the default
>     signal against **1.3 s and 1.7 s** with SIGINT (exit 0, instance file released), so the image now
>     has `STOPSIGNAL SIGINT`; a read-only root filesystem (writable only `/tmp`, a home tmpfs and
>     `/data`) served every flow tested.
> - **Defects found late, each written down when found** (the first enumeration searched the join it
>   expected and missed siblings; see "Recurrences"):
>   - **The cover-letter preview raised `FileNotFoundError`** under `SARTOR_HOME`: it read the shipped
>     `personas/cover_letter.html` as `PERSONAS_DIR / ...`. Found by re-reading a grep hit, observed
>     before fixing.
>   - **The image did not contain `personas/cover_letter.html` at all**, found only by building it.
>     `.dockerignore`'s `personas/*/` also matches that *file* (Docker strips the trailing slash), so
>     the container's cover-letter preview and PDF failed; this pre-dates the branch. **I had written,
>     in the dossier, this handoff's earlier draft and item 0145, that the file was in the image and
>     that my Dockerfile change would have broken a working preview. That was an untested inference
>     and false; it is retracted in the dossier (O7, O11).** Fixed with `!personas/cover_letter.html`
>     and a derived-set test.
>   - **`preview-edited` answered `404 Template not found` for both document types** after the first
>     fix, because a `_within(path, PERSONAS_DIR)` recheck refuses the packaged directory. Caused by the
>     fix itself; found by a systematic pass over every `PERSONAS_DIR`/`BASE_DIR` use and every resolver
>     caller.
>   - **`analyzer.py`'s "no API key" error still said "at the repo root"**, found by the wiki review step
>     (not by the cite check or the auditor). Fixed, with the page's claim.
>   - **The full gate failed** on the repo's own C-10 audit: `sartor_home.py` has 8 non-test importers,
>     so it must be classified. Now **GATED**, kind `helper`.
> - **Not observed, declared (C-11/C-12):** **rootless Podman** (the machine was rootful, so volume
>   ownership under rootless is untested, and `install.md` still says so); the **CI-built GHCR image** and
>   Docker; the LLM generation path and `sartor --setup` inside the image; no real **wheel** was built or
>   run; the template-preview route (`preview_application_html`) under `SARTOR_HOME` was read, not run.
>   **H2 is observed with its mechanism corrected, and not fixed:** the image's recall index is not built
>   because the base image has no `git` (`FileNotFoundError: 'git'`), not because `.git` is excluded as I
>   first wrote. H3 (`alembic.ini` not in the wheel) and H4 (`personas/cover_letter.html` not in the
>   *wheel*; the image has it now) are unobserved and are branch 2's first instruments.
> - **The wiki-freshness gate is at 64 of its 75-file block threshold.** The scoped wiki pass on this
>   branch does not advance the checkpoint (`3798e2d18a8a`), and this branch's own diff adds
>   wiki-relevant files. A checkpoint-advancing pass is owed **before** the next wiki-relevant branch, or
>   the merge-blocking `scripts/wiki_freshness.py` will trip.
> - **Gate:** PASSED in a clean checkout of `e31fd09`; FAILED in the repo directory on the same commit (three
>   whole-tree tests, caused by another session's linked worktree inside it). Both results, and why, are under
>   "What just landed".

---

## Documents to read before any tool call (in this order)
<!-- verbatim -->

1. `docs/dev/RELEASE_ARC.md` — authoritative branch sequence,
   architectural decisions, and acceptance criteria for v1.0.2 → v1.1.0.
   The durable plan. Do not deviate without user sign-off.
2. `docs/dev/RELEASE_CHECKLIST.md` — what is open, closed,
   and deferred per release. Before proposing anything, check here first.
3. `docs/dev/AGENT_FAILURE_PATTERNS.md` —
   failure patterns to avoid. Read in full before writing any code.
   **§5f ("Guessing the mechanism") is the expensive one — it is why the
   Binding-rules block below exists.**
4. `docs/governance/charter.md` — the binding
   constitution. **C-7 (evidence before mechanism) and C-8 (durable before
   deep) are enforced by hooks, not by your judgment.**
5. `docs/dev/architecture.md` — module map and LLM routing
   boundary. The deterministic / LLM split is load-bearing.
6. `evals/TUNING_LOG.md` — baseline floors and
   prompt change history.
7. **If this branch is a `fix/*`:** its diagnosis dossier at
   `docs/dev/diagnosis/<branch-slug>.md`, if one exists. It is the durable
   evidence record — what was **observed**, what was **falsified** (do not
   re-chase those; each one cost real money to kill), and what is still only
   **inferred**. The `restore-evidence` SessionStart hook replays it into your
   context automatically, including after a compaction.

---

## Where we are in the arc

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging
(owner's 2026-10-02 sequence on item 40).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157) · ~~`fix/console-run-lock-hardening`~~ ✓ (#158) ·
  ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (#159) · ~~`fix/python-direct-hooks-plan-gate`~~ ✓
  (#160) · ~~`fix/heredoc-escape-guard`~~ ✓ (#161) · ~~`fix/bash-tool-transport`~~ ✓ (#162) ·
  ~~`fix/test-reliability`~~ ✓ (#163) · ~~`test/assertion-strength`~~ ✓ (#164) ·
  ~~`fix/frozen-composition-staleness`~~ ✓ (#165) · ~~`fix/regenerate-persistence`~~ ✓ (#166) ·
  ~~`fix/regenerate-keeps-cover-letter`~~ ✓ (#167) · ~~`fix/recurrence-guardrails`~~ ✓ (#168) ·
  ~~`fix/run-row-letter-edit-shadow`~~ ✓ (#169): item 163 closed.
- ~~`feat/confirm-before-overwriting-typed-edits`~~ ✓ (#170): item 170 closed.
- ~~`fix/reorder-networkidle-empty-census`~~ ✓ (#171) · ~~`fix/compose-single-context-parse`~~ ✓
  (#172): item 161 closed · ~~`fix/reorder-networkidle-bound`~~ ✓ (#173): item 30's Phase A;
  **item 30 stays `watching`**.
- ~~`feat/single-instance-and-quit`~~ ✓ (#174): items 146 and 147 closed.
- **`feat/data-root`** ← this branch: **item 145, branch 1 of 3**. Item 145 stays **open**.
- **Next: the owner's pick.** Item 145's branch 2 (`feat/launcher`) and 3 (`feat/pushbuttons`), none
  started, are the natural follow-ons; the container verification and the item-164 instrument are the
  other candidates. Also open: item 7 memory-consolidation apply (Deferred) and the owner-decision items
  (50, 128, 129, 133, 135, 138).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. **Do not start branch 2 or 3 of item 145 on this branch.**

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `feat/data-root`:

| Commit | What |
|---|---|
| `076b029` | **Dossier first** (C-10) plus item 0145's decisions and this session's consumed-ledger file. No production edit. |
| `012635b` | **Instrument first** (C-7): `tests/test_data_root.py`, two strict xfails. Observed 12 of 13 sites ignoring `SARTOR_HOME`, and H1. |
| `9a5099d` | `sartor_home.py`, `config.py` aliases, `py-modules` / mypy / `wiki_relevance` registration, `platformdirs` parity test. |
| `ed2efc7` | Route every user-data writer through it; the key gets one resolver; the **ratchet** `TestNoUnclassifiedFileAnchoredPath`. |
| `add2356` | **Fix H1:** `_persona_row_location` for the resolve, download and preview routes. |
| `917aee0` | `Dockerfile`: `SARTOR_HOME=/data`, `VOLUME`, `HEALTHCHECK`; real-app evidence (dossier O6). |
| `101dc44` | `install.md`, `README.md`, `SECURITY.md`, `CHANGELOG.md`, item 0101's update. |
| `592f8f6` | **Fix:** `Config.cover_letter_shell` / `COVER_LETTER_SHELL`; observed `FileNotFoundError` first (O7). |
| `11a397d` | **Fix:** the `preview-edited` containment recheck accepts the bundled directory (O8). |
| `0318d6e` | Scoped wiki update (4 pages), `analyzer.py`'s error string, a corrected CHANGELOG line. |
| `eb5dc12` | `sartor_home.py` classified **GATED** in `scripts/enforcement/blast_radius.py` (O9). |
| `cf6b90b`, `466105d` | The first handoff, and its correction (another project's plans were generalized out of a public file). |
| `e31fd09` | **Container fixes, found by building and running the image** (O10–O13): `!personas/cover_letter.html` in `.dockerignore`, `STOPSIGNAL SIGINT`, the recall-index claim corrected everywhere, `TestImageShipsItsFiles`. |
| (this commit) | This handoff's update and its `generated` ledger event. Docs only. |

**Verified, with the evidence:**
- **Before / after:** see the callout. The probe is `tests/test_data_root.py` (a subprocess, because the
  constants are fixed at import and the suite's autouse fixtures already redirect two of them).
- **Red-before for the two route fixes:** the cover-letter and `preview-edited` tests were run on the
  code without the fix (O7 shows the traceback; O8 the two `404` bodies). The download test was run
  against `HEAD` in a scratch worktree.
- **The derived-set ratchet** requires the exact set of 10 runtime files that call `Path(__file__)` to
  match a reasoned allow-list, and has a control arm. **Its limit:** it sees `Path(__file__)` only; none
  of the four late finds had one.
- **Wiki:** scoped `/wiki-self-update` on four pages. Cite check 0 violations (after 2 mechanical ones);
  auditor **40 supported / 1 drifted / 5 unsupported** (all five in older text, fixed on the owner's
  say-so); my review made 4 more catches including the stale code string. `docs/wiki/log.md` keeps the
  three signals apart. The checkpoint was **not** advanced; `wiki_freshness` reads 64 of 75.

**Gate:**
- **Passed in a clean checkout, failed in place.** `python -m scripts.gate --result`, run in a **clean
  detached checkout of `e31fd09`** outside the repo directory:
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-16T07:29:06-0700, HEAD e31fd09`
- **In the repo directory the same gate FAILED on the same commit, and `--result` there says so:**
  `gate --result: FAILED -- last run: exit 1, failed step 'pytest -m "not ux" -n auto', finished 2026-10-16T07:07:11-0700, HEAD e31fd09`.
  The three failing tests scan the whole tree: `tests/test_egress_allowlist.py::test_static_egress_allowlist`,
  `tests/test_docstring_coverage_gate.py::test_docstring_coverage_meets_floor` and
  `tests/test_ux_toast_wait_gate.py::test_toast_sites_equal_the_allowlist`. **Another session's locked linked
  worktree, `.claude/worktrees/dependabot-triage-item`, a full copy of the repo with uncommitted work in it,
  now sits inside the scanned tree.** Evidence: all three failure texts list that worktree's paths; in the
  repo's own 64 files **0 of 592** docstrings are missing (404 worktree files carry the 3,008 misses); the
  other 3,484 tests, `ruff`, `ruff format` and `mypy` passed. I did not remove or move that worktree.
  **Until it is gone, a plain `python -m scripts.gate` in this directory fails those three tests**; expect it.
- **Earlier failure:** the first gate run, on `0318d6e`, failed the C-10 classification audit (dossier O9);
  fixed in `eb5dc12`, and a run on `eb5dc12` in place passed (3485 passed, 189 UX passed, 1 xfailed, 1 xpassed).
- **That result is stale for the tip**, because the result binds to HEAD. This handoff's own commit(s)
  (docs plus ledger lines) sit on top of it and change no code or tests. The handoff validation,
  `work_items check`, `doc_lints` and `wiki_cites` were re-run on the tip; the full gate was not. CI re-runs
  on the tip, on a clean checkout, where the worktree does not exist.
- **What the clean run ran** (`GATE_CLEAN_START 07:09:28`, `GATE_CLEAN_DONE exit=0 07:29:06`, the wrapper's
  own markers): **19 min 38 s**. Preflights (hooks path `.githooks`; 4.35 GB free against the 1.00 GB floor),
  `ruff check` clean, `ruff format --check` (420 files) and `mypy .` (436 files) clean;
  `pytest -m "not ux" -n auto` **3487 passed, 8 skipped** (4 m 08 s; +2 over the earlier run, the new
  `TestImageShipsItsFiles` pair); `pytest -m ux` **189 passed, 2 xpassed** (11 m 46 s); `work_items check`
  OK (170 files). **0 `RERUN`, 0 `FAILED`, no rerun-rate alarm.** The stall line read `[ux] networkidle
  pre-drain: 2 stall(s) in 115 reach(es), 32.1 s waiting`: the two deliberate probes and the same 115
  reaches as before, so 0 unintended (item 30: unchanged, still `watching`).
- **The two non-strict xfails moved between runs and I did not investigate:** both XPASSed here; the run on
  `eb5dc12` had one XFAIL and one XPASS (`tests/ux/regression/test_20260708_busy_states_and_chip.py`, whose own
  rationale makes both outcomes legal). This branch does not touch that file or the wizard rail.
- **Wall-clock note:** 14 to 20 minutes across this session's passing runs, 22 last session. Machine load was
  not captured, so do not read any of those numbers as this branch's cost.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 19 / 10 ceiling -- OVER"** — unchanged
by this branch (no item opened or closed; **145 stays open**, in three branches). The owner's drawdown
direction stands: down to 0 if possible, before alpha staging. Still well past the ~8–10
reduction-sprint threshold. Owner-decision items are marked *(owner)*.

`## Open`:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **128** *(owner)*: D1 close-out saw several python3.13 processes started 2026-09-18..25 (~0 MB), not that session's own.
- **129** *(owner)*: Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?
- **130**: Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty.
- **131**: Retire dialog cites a "Show retired" toggle Pipeline lacks; its query drops retired apps.
- **133** *(owner)*: No route, UI or script removes a user. Product decision: wanted, and when?
- **134**: Tuning smoke says ~$0.20 for TWO suite runs; Quality smoke says ~$0.35-0.40 for ONE. At most one is right.
- **135** *(owner)*: Template close-out step 1 says ruff+mypy+pytest (gate runs 6); charter:206 cites step 4 for a step-5 rule.
- **137**: Short review: are the pinned models and call settings (thinking, caching, routing) still the best performance/cost fit?
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link. (This branch added a Quit section to that drawer and no help bubble.)
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Prompts hand bullets to the model as id="b{id}"; the model echoes the handle into prose. Letter date is ungrounded.
- **145**: Owner pre-launch requirement (2026-08-16): stdlib launcher, two backends, per-OS one-click wrappers. **In three sequential branches; branch 1 (`feat/data-root`) is done on this branch, branches 2 (`feat/launcher`) and 3 (`feat/pushbuttons`) are not started.** Owner decisions, the branch 2/3 outlines and this branch's open obligations are in `docs/dev/work/items/0145-launcher-and-per-os-pushbuttons.md` `## Updates`.

`## Blocked` (4): **3**, **5**, **8**, **97**.
`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.
Plus `## Watching` (44, including **30**) and `## Epics` (6) in `BOARD.md`.

Carried from the previous handoff's "declared, not filed" list, still open (**not re-verified this session** unless marked):
- **The simultaneous-launch race** (above, and item 146's resolution): the one open limit of the
  guard this branch built. Owner's call whether it earns an item.
- **Wiki route and blueprint counts are prose, derived by whoever last edited the page.** The
  scribe's counts were wrong twice this pass; the auditor caught one scope word, not the counts.
  Unenforced. A deterministic check (anchored decorator count vs the number in the page) is
  possible and was not built.
- **Reported by subagents, not verified by me** (treat as leads):
  - `blueprints/corpus/__init__.py`'s own docstring sums its routes to 50 where the files hold 54
    (I verified the 54 by an anchored grep; I did not read the docstring).
  - `hardening.py:1780-1785` says the dev server "defaults to `threaded=False`", but Flask's
    `app.run` defaults `threaded=True` (an Explore agent read Flask 3.1.3; I did not re-check).
  - `docs/dev/releasing.md:36-39` still describes a `GATE` step in the publish job that
    `release.yml` no longer has.
  - **For item 145:** `SARTOR_HOME` is not honoured by `analyzer.py:568` `LOG_DIR`,
    `db/session.py:24-25`, `preflight.py:415` or `web_infra/clients.py:34` (`CHANGELOG.md` already
    lists `LOG_DIR`); the `Dockerfile` sets no `SARTOR_HOME`, `VOLUME` or `HEALTHCHECK`;
    `/data` must be writable by uid 10001; `sartor` is already the app wheel's project name and
    console script (`app:main`), so the launcher needs another name or `main` needs verbs
    (inference); in an installed wheel `--setup`'s index build likely writes under
    `site-packages` (inference).
- **A background-run reaper kill left no orphans this time** (listed: only the isidium MCP server
  and the editor's Pyright, neither mine). Known class; memory
  `reference-shared-machine-oom-kills-bg-runs`.
- **The IDE's Pyright again reported stale "not defined / not accessed" hints** between
  consecutive edits; `ruff` and `mypy` were clean each time.
- **`maintainer-lane.md` step 2 still gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`**
  (this handoff's validation used `docs/dev/AGENT_HANDOFF_TEMPLATE.md`); carried from earlier.

Carried from earlier handoffs, **not re-verified this session**:
- the three probe tests (P3, P4, P5) stay in the UX tier until the owner decides (item 30);
- the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5): an owner question;
- whether a cover letter should be regenerable from the shipped screens (item 170's open question);
- `python -I` drops the user site-packages on this machine (Playwright lives there);
- the `isidium` MCP server (two `python.exe -m isidium.store.client.cli mcp`) is not a session's to stop;
- `ruff` is not on the Git Bash PATH here (`python -m ruff` works);
- the sibling window's gap is one sample (1.133 s; diagnosis O8), the 3 s default is a judgment;
- a trunk-time `compacted` row is no longer in `git log`; branch-time rows are (item 165);
- `plan_gate` reports a detached HEAD as `""`, so its `plan-archived` receipt stays in the tracked
  shard there (item 169);
- E1 sees a `lines N-M` reference only when a path is on the same or the preceding line, and E3 is
  word-presence in the file (`scripts/wiki_cites.py` docstring);
- `ALLOWED_LINE_CITES` holds 25 line cites on 8 pages; converting one to a symbol forces the entry down;
- bash-run scripts edit files without the Edit|Write gates seeing them;
- a gap-fill retire, or a drag back to the same position, marks an approval stale without changing
  the résumé; approvals frozen before `fix/frozen-composition-staleness` carry no digest;
- the post-generate announcement still says "Resume and cover letter generated" when no cover
  letter was produced (`static/app.js`, `runGeneration`'s `_announce`);
- `lastCoverLetterPath` is assigned in seven places and read by none (`static/app.js`);
- a stale comment at `db/build_context.py:92`: fold it into any branch that touches that file;
- `scripts/enforcement/blast_radius.py` says `ui_pages/selectors.py` has "14 non-test importers";
  re-derived this session as 14 by the dossier's anchored grep (an earlier session said 15);
- two UX tests hard-code the `#cbConfirm*` ids instead of the `ConfirmModal` selectors
  (`test_20260612_corpus_affordance_polish.py`, `test_20260707_ux_w4_aesthetic.py`);
- the doc-writing skill's evaluation plan has not been run (the owner's call when);
- 32 one-way wiki backlinks (WARN), as counted by an earlier `/wiki-lint`;
- `python scripts/check_docs_projection_fresh.py` reported STALE on a clean tree four sessions ago;
  not re-checked since;
- `sartorEval.run()` returns no handle on its success path (`dashboard.html`);
- `docs/dev/diagnostics.md` cites code by line number, which rots on every edit;
- the derived-set test's `git ls-files` costs 1.8–5.2 s on this machine under 0.5–0.8 GB free;
- transitive wiki relevance is not modelled (`PERFORMANCE_HISTORY.md` → `scripts/perf_baseline.py`);
- `python3` resolution on hypha and the homelab is unchecked; without `python3` on PATH no hook
  starts and the gates fail open (`docs/governance/enforcement.md`);
- `tests/test_plan_approval_scoping.py` takes about 6 minutes locally: split it by `-k` class;
- pre-existing count drift, each deferred in `docs/dev/blast-radius/bash-tool-transport.md`:
  `docs/governance/enforcement.md:29-31` says "8 exist" (14 rules now); `TestBashDispatcher`'s
  docstring names four guards (there are seven); `blast_radius.py`'s `result.py` entry says "10
  non-test importers";
- item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry;
- the threaded UX `live_server` may expose route reads on Windows (inferred, not observed;
  `docs/dev/diagnosis/test-reliability.md` §Inferred);
- `tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt (run 30940947527), not investigated;
- the other routes in `blueprints/applications.py` were not audited for repeated context reads
  (item 161's scope was the GET);
- the wiki auditor found a fact-level error the cite check cannot see (item 161's close-out).
  Brief a scribe's page edit and its audit to the **same** region, and widen the audit to the whole
  bullet or paragraph (`docs/wiki/log.md`, the 2026-10-15 entries).

New this session, declared, not filed (**observed unless marked**):
- **The container was built and run locally, on a rootful machine only.** Unrun: **rootless** Podman
  (ownership of a named volume and of a bind mount), the CI-built GHCR image, Docker, the LLM generation
  path and `sartor --setup` inside the image. `/app` was **not** made root-owned: a read-only rootfs served
  every flow tested, but `install.md` used to recommend `sartor --setup` in the container (it writes under
  `/app/db`) and generation was not run there. **Before any local build run `git ls-files --eol
  Dockerfile`**: this machine's working copy is CRLF, so build from a clean `git archive` as I did, with
  `--format docker`. Everything I created was named `sartor-b1-verify*` and removed, plus the base layer my
  first build pulled; the owner's own containers, volumes and images were untouched. **`podman machine ssh`
  run from the repo drops a file named `NUL` there** (mine was deleted); run it from a scratch directory.
- **H2 is observed (mechanism corrected); H3 and H4 are hypotheses read from code.** H2:
  `scripts/build_vector_index.py:57` `_git` raises `FileNotFoundError: 'git'` because the base image has no
  git, and there is no `.git` in the context either, so installing git alone would not fix it;
  `/app/db/vector_index` holds `model/` only. `install.md`, the CHANGELOG and the Dockerfile header no
  longer say the index is baked. A wheel's `--setup` runs the same step (not run). H3: `alembic.ini` is
  not packaged, and `db/session.py` loads it. H4: `personas/cover_letter.html` is outside every package
  (`pyproject.toml` ships only `personas.bundled`), so a **wheel** does not have it; the image does now.
- **Another session shares this clone.** At 06:55 a linked worktree
  `.claude/worktrees/dependabot-triage-item` (branch `chore/dependabot-triage-item`, locked, at `f01d29e`)
  appeared and `core.hooksPath` became the absolute `C:\Dev\sartor\.githooks`; the gate's hooksPath
  preflight refused. I reset it to `.githooks` on the owner's instruction (that session was stopped and
  waiting). **I did not establish what wrote the absolute path**; seven seconds after the worktree points
  at that session's setup. The setting is per clone, not per worktree, so expect it to recur. `ListAgents`
  showed two other idle sessions (`sartor-e4`, `resume-epic-279-design-pass`); I messaged neither.
- **`platformdirs` has no runtime importer now** (grepped; `config.py` and `sartor_home.py` mention it in
  docstrings only). It is still in `[project.dependencies]` and the parity test needs it, so it moves to
  the dev extra when branch 2 reorganises the dependencies.
- **`sartor_home.py` is now GATED.** Editing it needs a dossier whose `## Consumers` names it, and
  `scripts/enforcement/blast_radius.py` is itself gated.
- **`evals/runner.py` writes results beside the code (`RESULTS_DIR = EVALS_DIR / "results"`) while the
  dashboard reads `PROJECT_ROOT / "evals" / "results"`** (the data root). A mismatch only when
  `SARTOR_HOME` is set on a checkout; it pre-dates this branch; `evals/` is in neither the wheel nor the
  image. Read, not run (dossier `## Deferred`).
- **Read but not run under `SARTOR_HOME`:** `preview_application_html` (`blueprints/templates.py`, the
  `BUNDLED_PERSONAS_DIR` reads at `:1075` and `:1441`) and the `generation.py` callers of the two
  persona resolvers. A real wheel was not run either.
- **`sartor --doctor` reports only `found in .api_key` / `not found`, never the path.** A wheel user whose
  key sat beside the program now sees "not found" and is pointed at `sartor --setup`, which prints where
  it saved the key. Whether `--doctor` should print the path is a small owner/UX call. My CHANGELOG line
  said it did; it was wrong and is corrected.
- **A doc that paraphrases a code string has no check.** `analyzer.py:_NO_CREDENTIAL_DETAIL` was updated
  only because the wiki review step compared a page to it. **Unenforced.**
- **Reported by subagents, not verified by me (leads):** that the sibling project item 0145 refers to has
  no launcher code Sartor could share (an Explore agent's read of that project, deliberately not
  described further here); the status of items 3, 99 and 100 (the same agent's read); the Plan agent's
  questions for branch 2 (PEP 668, bare `sartor` behaviour, a possible C-2 amendment).

---

## Recurrences observed this session → guardrail authored

1. **An enumeration that searched the one join I expected** (C-10). A recurrence of the
   `compose-unawaited-reloads` class (`be48fec` fixed 5 sites, a later grep found 9 more): here
   `BASE_DIR / row.path` was searched, and `PERSONAS_DIR / "cover_letter.html"` (two sites), a
   `_within` recheck that **my first fix broke**, an error string, and a `.dockerignore` rule that hid a
   shipped file from the image turned up afterwards, one at a time. Recognized as the same class when the second site appeared.
   - **Mechanism authored (partial):** `TestNoUnclassifiedFileAnchoredPath` in `tests/test_data_root.py`
     fails closed on an unclassified runtime file that anchors a path on itself, and `TestImageShipsItsFiles`
     fails closed if `.dockerignore` drops a tracked file directly under `personas/` (red on the pre-fix
     file; that directory only). **The first would not have caught any of the five**: none contained
     `Path(__file__)`. Each late find has its own red-before test (`TestBundledPersonaUnderSartorHome`).
   - **For the class itself: none.** "A shipped file looked up under the data root" has no general gate.
     A mechanism would be a whole-suite run under a redirected `SARTOR_HOME`; not built. **Unenforced**,
     stated to the owner here. Memory: `feedback-enumerate-by-class-and-recheck-downstream-guards`.
2. **A subset standing in for the full gate** (second consecutive session; the previous handoff's #4).
   I ran the suites that import the routed modules, not `python -m scripts.gate`, and the gate then
   failed on `test_widely_consumed_modules_are_all_classified`.
   - **The gate failed closed as designed** and named the test. **No new mechanism authored**; stated
     plainly: the lapse is running a subset in place of the definition, and nothing prevents that.
3. **An unsourced assertion written into a doc** (C-12; four instances this session). I wrote, in the
   dossier, an earlier draft of this handoff and item 0145, that `personas/cover_letter.html` was in the
   image because `.dockerignore` "only excludes `personas/*/`"; building the image showed it was not (the
   pattern also matches the file). It was committed in three places before the build and is retracted in
   all of them. My CHANGELOG said
   `sartor --doctor` shows where the key is looked up (it does not); a scribe called `platformdirs` "a
   test pin" (a purpose with no source); I wrote "the one LLM route outside that set" (a universal I had
   not shown). The first was caught by building the image and the rest by the wiki review step or re-reading; none by a
   gate.
   - **No mechanism possible** for prose; the defence is the review step and checking each behavioural
     claim against code before writing it. **Unenforced.**
4. **The interrogative witness paused edits after turns the owner did not type** (item 164's class). It
   paused the first `Edit` in three separate batches, each immediately after a subagent hand-back
   arrived as a turn ("Another Claude session sent a message: ..."), and refused the batch's siblings.
   Re-running the identical calls cleared each time; no hook was bypassed.
   - **Observed:** 3 pauses while 5 scribes and 4 auditors were handing back. **Not established:** whether
     the wiki-skill body turn also armed one; the two are not separable, and the hook writes no
     per-pause receipt (the gap the previous handoff named). Memory
     `reference-subagent-pretooluse-agent-id` said hand-backs "no longer re-arm"; that is now marked
     contradicted. This is more evidence for the previous handoff's recommendation: **reopen 164, the
     instrument first.**
   - **No mechanism authored on this branch**, stated plainly. It needs its own branch and is the
     owner's pick.
5. **A concurrent session changed shared git config** (first sighting for me; related to the
   concurrent-agents worktree memory). The gate's hooksPath preflight (item 150) **failed closed before
   running anything**: an existing mechanism that worked. No new mechanism authored. Not established:
   what wrote the absolute path, and whether it will again (see the "Another session" bullet).
6. **Side-effect files I created while verifying**, both found and removed (first sightings): a file named
   `NUL` in the repo root from `podman machine ssh` (found by `git status`), and an empty `/tmp/__noop`
   from a stray `cat` in one of my own commands. No mechanism; recorded in memory
   (`reference-windows-console-unicode-print-crash`). **Unenforced.**
7. **Wiki scribes made mechanical cite errors** (E1 bare line cites, E4 a removed still-valid cite). The
   deterministic check (`scripts/wiki_cites.py`) existed and **caught both before the auditor spent
   anything**: a mechanism that worked, not a new one.

---

## What this branch should build

**Nothing is queued.** The owner chooses the next item; this handoff does not pick one. Do not expand
beyond what the owner names.

If the owner picks **item 145's branch 2** (`feat/launcher`): read item 0145's `## Updates` first. The
shape is decided: one distribution, `sartor`, stdlib-only core, heavy deps in a `sartor[app]` extra, a
managed venv for `install --native`. The first commit is an **instrument** (does a built wheel ship
`alembic.ini` and `personas/cover_letter.html`? does the image's index build succeed?). Ask the owner
first: the C-2 wording (`docs/governance/charter.md` names "the single-instance probe"; the launcher adds
a loopback shutdown POST and a health read), the PEP 668 fallback for `pip install --user`, whether bare
`sartor` with no runtime runs `up`, and whether `sartor` is free on PyPI. Its end-to-end still depends on
item 3 (nothing is published).

If the owner picks the **remaining container checks**: rootless Podman, the CI-built image, Docker,
generation and `--setup` in the image. The method is in dossier O10–O13: build from a clean `git
archive` with `--format docker`, name everything uniquely, clean up only those names. If the owner
picks the **recall-index fix (H2)**: it needs a no-git path in `scripts/build_vector_index.py` (or git
plus a context with `.git`) and the `Dockerfile`; instrument first.

If the owner picks **reopening item 164**: start with the instrument, not a fix; the evaluation is in
`docs/dev/handoffs/single-instance-and-quit.md` "Recurrences" #5 and this handoff's #4.

If the owner asks what is cheapest: a **checkpoint-advancing wiki pass** (the freshness gate is at 64 of
75), and the *(owner)* items, which need a decision before any branch.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path:
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then confirm with the owner that the PR for `feat/data-root` has
merged. Then ask which item to take. Create that branch off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not code first.**

---

## Binding rules — no discretion (copy verbatim — MANDATORY in every handoff)
<!-- verbatim -->

**These are not heuristics, and your judgment does not decide whether they apply
today.** Each one exists because an agent decided it did not apply, and was
expensively wrong. Read them as prohibitions, not as advice.

**1. Evidence before mechanism (charter C-7). If you did not SEE it, you did not
find it.**
- For a defect you cannot reproduce on demand, **the first commit on this branch
  is the instrument or the reproduction — never the fix.** The
  `require-evidence-before-fix` hook blocks production edits on a `fix/*` branch
  until `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section. There is no escape hatch. `docs/**`, `tests/**` and `*.md` stay
  writable, so the way through is always open: **write down what you saw.**
- **Reading code and finding a plausible mechanism is a HYPOTHESIS.** Put it under
  `## Inferred` and label it as unproven. A fix for a real defect that isn't
  **the** defect still leaves the bug — and plausibility is exactly what makes you
  skip the check.
- **Never scope an instrument to the theory you are testing.** It will confirm
  your theory by hiding its rivals. Capture wider than you think you need.
- **Green CI is not evidence if the test needed a retry.** `pytest-rerunfailures`
  reports a fail-fail-pass as a bare `PASSED` with **no traceback anywhere in the
  log**.
- If you are not certain **from evidence**, say **"I have not verified this"** and
  **stop**. That sentence is always cheaper than the alternative.

**2. Durable before deep (charter C-8). The context window is not a store.**
- Write a hard-won fact — a measurement, a falsified hypothesis, an observed
  artifact — to its durable home **in the turn you learn it.** Not at close-out.
  The pre-close sweep *reconciles*; it must not *discover*.
- **Compaction is an unannounced data-loss event.** After one, reconcile against
  the repo and git — never continue from a summary as though it were the evidence.
- **A thin context is a handoff trigger, not a push-harder trigger.**

**3. Hooks are not obstacles (see `feedback_hook_discipline`).**
- **NEVER** bypass a hook on your own initiative. Never hand-create the file a hook
  checks for. Never skip a step that has no escape hatch. Escape hatches
  (`CLAUDE_ALLOW_MAIN_EDITS=1`, `CLAUDE_CONFIRM_MERGE=1`) are legitimate **only when
  the user explicitly directs their use** — never on your own judgment.
- If a hook blocks you: **surface the hook name and its message, and STOP.**

**4. Do not declare done. Verify done.** "Done" is the *output* of the pre-close
sweep, not an announcement. See the close-out checklist below.

**5. Corrupted input is a blocked gate (charter C-9).** Damaged, truncated, or
fingerprint-mismatched input is a blocked gate — surface it as your **first
output** and **STOP**; never silently reconstruct, however confident the
reconstruction feels. A `blocked` result from
`scripts/verify_doc_template.py --event consumed` on a handoff you're
consuming is exactly this case — three of the four confirmed silent
handoff-corruption events this rule exists for were an agent reconstructing
damaged text instead of saying so (see
`docs/dev/handoff-integrity-design.md` §2).

**6. Enumerate consumers before changing a contract (charter C-10).** Before
implementing any change to a **schema, a shared contract, or a widely-consumed
helper**, enumerate its consumers **grep-complete** — the whole tree, and every
name the thing goes by (symbol, string form, re-export, raw-SQL column, template
selector) — and **decide-and-document each site before the first edit.**
- **The ordering is the mechanism.** An enumeration written afterwards is a
  description of what you did. Written first, it is the thing that tells you the
  change is bigger than you thought.
- **A site you skip deliberately gets a written reason** under `## Deferred`. The
  same site skipped silently is a defect the next person finds.
- **Treat any hand-maintained consumer list as stale until you re-derive it** — it
  rots in *both* directions, naming sites already fixed and omitting sites that
  are not.
- The `require-consumer-enumeration` hook blocks edits to a gated surface (registry:
  `scripts/enforcement/blast_radius.py`) until
  `docs/dev/blast-radius/<branch-slug>.md` has a `## Consumers` section naming that
  surface. There is no escape hatch. That dossier's directory and `tests/**` stay
  writable, so the way through is always open: **write down who consumes it.**

---

## Hard constraints (copy verbatim — do not shorten)
<!-- verbatim -->

- Branch before any code edit (`require-feature-branch` hook enforces this)
- Quality gate before every commit: `ruff check .` + `mypy .` + `pytest`
- Every new Flask route: `_safe_username()` + `_within()` + `secure_filename()`
  — `route-security-lint` hook enforces this on `app.py` edits
- No LLM calls in `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, or `pdf_render.py`
- `PROMPT_VERSION` must bump in the same commit as any prompt change
- New dependency = `pyproject.toml` entry + `CHANGELOG.md` entry
- If a hook blocks you: surface the hook name + error, do not bypass,
  wait for authorization
- Do not merge to `main` without explicit user confirmation
- One branch per session — close, merge, hand off before starting the next
- Capture-before-merge: land ALL of this branch's docs / memory / CHANGELOG /
  RELEASE_ARC-CHECKLIST / tracked-deferred / flaky-test captures **before** the merge.
  Never merge then open a follow-up branch for a one-file doc/memory edit — it
  re-triggers the `--no-ff` `.approved` marker-wipe ceremony. If a small item surfaces
  after you'd otherwise merge, the sweep isn't finished: fold it in and re-gate.

---

## Branch close-out checklist (do in this order before closing the window)
<!-- verbatim -->

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified; **this session's
   own `consumed`-event provenance-ledger file** (`docs/dev/ledger/<session>.jsonl`,
   written on `main` at session start when the incoming handoff pointer was
   consumed) **committed on this branch** — folded into an early commit, never
   left untracked and never given its own dedicated branch/PR (see
   `docs/dev/prov/SPEC.md` §5 step 3); **wiki-relevance check** — if this branch's
   own diff touches any path `scripts/wiki_relevance.py` (`is_wiki_relevant()`)
   classifies as wiki-relevant, run a scoped `/wiki-self-update` against just this
   branch's own diff and commit the wiki edit now, before opening the PR (same
   "committed before merge" discipline as memory/CHANGELOG, never a follow-up PR);
   if the touched file needed no page edit, say so explicitly rather than silently
   skipping the check; **any dev server or
   long-lived background process started this session terminated** before closing the
   window (check with `tasklist`/equivalent — an agent's own orphaned processes are
   exactly the failure mode carry-forward ledger item 20 documents). "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Write the next-agent handoff at `docs/dev/handoffs/<branch-slug>.md` from
   this template (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), stamped per
   `docs/dev/prov/SPEC.md` §1, then validate it:
   `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>`. A
   `failed` result is authoring corruption in the handoff itself — fix the
   file, don't silence the check. **Do this ON THIS BRANCH, BEFORE the
   merge** — this is exactly what the Capture-before-merge hard constraint
   above already requires (the handoff is one of this branch's own docs),
   and `require-feature-branch` blocks writing it on `main` once this
   branch is gone, so there is no compliant way to do this step after
   merging.
3. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean); the handoff file from step 2
   must be committed by this point too (its own commit or folded into this
   one — either way, both must exist before step 4)
4. **Land it through the PR channel — a local `git merge` to `main` is NEVER
   the flow.** `main` carries branch protection requiring a pull request plus
   six passing status checks (`strict: true`), so a local merge is rejected
   outright for a non-admin and, for an admin, silently bypasses those six
   checks. Squash and rebase merges are both disabled on the repo, leaving
   **merge commit** as the only method — deliberately: a squash rewrites SHAs
   and orphans the local commits it replaces (it already produced one zombie
   commit, `9f3c800`, before this was understood). Ask the user to confirm,
   then: `git push -u origin <branch>` → open the PR (`gh pr create`, or hand
   the user the URL) → **wait for the required checks with
   `python -m scripts.ci_wait <n>`** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **`scripts/ci_wait.py` is the single definition of "the PR is green" — never
   hand-roll a watcher, a poll loop, or a `gh pr checks … | jq` one-liner.** It
   exits **0** only when every required check passed *and* no test needed a
   retry; **3 = green-after-retries** (charter C-7 rule 3 — stop and look, do
   not merge on it reflexively), **1** a failing required check plus its log
   tail, **8** the deadline expiring, **2** a wrapper error. Two hand-rolled
   30-minute watches once ran to completion emitting *nothing* while a required
   check was already red — that silence is the failure this replaces.
   **Pushing is outward-facing on a public repo:** state what will become
   public — including any commits already on your local `main` that the remote
   does not have, since they ride along — and get explicit confirmation before
   the first push.
5. Prune the merged branch(es) with the user's OK — **but regenerate the
   pointer FIRST**, because it must cite `main`, and pruning a branch a
   pointer still names leaves the next session with an unresolvable
   reference (a correct C-9 halt, but a wasted first move). After the
   `pull --ff-only` in step 4: generate the one-line pointer with
   `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`). Then prune
   (`git branch -d <branch>`; the remote copy is auto-deleted on merge).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
