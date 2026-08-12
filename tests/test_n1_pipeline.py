"""Structural gate for the N=1 baseline pipeline (work item 84).

Pins `.claude/workflows/n1-baseline.mjs`, `agents/n1-refuter.md`,
`agents/n1-judge.md`, and `docs/dev/n1-baseline-pipeline.md` to the design
they implement (`docs/dev/epic-a-chain-design-corrections.md` sec. 16.4-16.5,
sec. 11.5-11.9) so that any change to the pipeline's load-bearing structure is
a deliberate, reviewed edit to this file.

Scope honesty (C-0, stated in the contract doc's "Stated limits"): the
Workflow-harness API the script targets has zero committed instances in this
repo and the script has NEVER been executed -- these tests certify
self-consistency with the design docs, not harness compatibility. That is
exactly why work item 84 stays `watching` rather than closing on this file
being green (owner decision, 2026-08-11).

Teeth first ("a gate never shown to reject a bad input is not evidence of
anything" -- tests/test_c12_disclosure_gate.py's standard): the JS scanner the
pins depend on is exercised against RED fixtures -- a model-less agent() call,
a call inside a comment, a paren inside a string argument, a forbidden token
in code vs. in a comment -- before it is trusted over the real file.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / ".claude" / "workflows" / "n1-baseline.mjs"
REFUTER_PATH = REPO_ROOT / "agents" / "n1-refuter.md"
JUDGE_PATH = REPO_ROOT / "agents" / "n1-judge.md"
DOC_PATH = REPO_ROOT / "docs" / "dev" / "n1-baseline-pipeline.md"

# The six provenance-ledger event types proposed in sec. 16.5.2.2 and
# explicitly NOT authorized by the owner's sec. 16.7 decision (item 84).
# Their absence from the script is a scope boundary, not a style choice.
UNAUTHORIZED_LEDGER_EVENTS = (
    "burst_started",
    "sprint_judged",
    "flag_raised",
    "coherence_drift_checked",
    "escalated_to_human",
    "ripcord_pulled",
)

# Tokens that would break the Workflow harness's resume contract.
RESUME_BREAKING_TOKENS = ("Date.now(", "Math.random(", "new Date(")

READ_ONLY_GIT_CLAUSE = (
    "You never `git add` / `commit` / `checkout` / `merge` / `push` "
    "or write a file through a shell. Do not work around the boundary."
)


# ---------------------------------------------------------------------------
# The scanner: blank comments and string/template contents so that structural
# scans see only code. Template-literal interpolations (`${...}`) are code and
# stay visible; nesting is handled with an explicit stack.
# ---------------------------------------------------------------------------


def blank_non_code(src: str) -> str:
    """Return src with comment and string/template CONTENTS replaced by
    spaces (newlines preserved), so regex/paren scans only ever see code."""
    out = list(src)
    i = 0
    n = len(src)
    # Stack entries are only ever "template": pushed when an interpolation
    # re-enters code from inside a template literal.
    template_stack: list[str] = []
    brace_depth_stack: list[int] = []

    def blank(idx: int) -> None:
        if out[idx] != "\n":
            out[idx] = " "

    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and src[i] != "\n":
                blank(i)
                i += 1
        elif ch == "/" and nxt == "*":
            blank(i)
            blank(i + 1)
            i += 2
            while i < n and not (src[i] == "*" and i + 1 < n and src[i + 1] == "/"):
                blank(i)
                i += 1
            if i < n:
                blank(i)
                blank(i + 1)
                i += 2
        elif ch in ("'", '"'):
            quote = ch
            i += 1
            while i < n and src[i] != quote:
                if src[i] == "\\":
                    blank(i)
                    i += 1
                if i < n:
                    blank(i)
                    i += 1
            i += 1  # closing quote kept
        elif ch == "`":
            i += 1
            while i < n:
                if src[i] == "\\":
                    blank(i)
                    i += 1
                    if i < n:
                        blank(i)
                        i += 1
                elif src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                    # Interpolation: its contents are CODE. Recurse by
                    # scanning forward for the matching close brace at
                    # depth 0, treating nested templates recursively.
                    template_stack.append("template")
                    brace_depth_stack.append(0)
                    i += 2
                    break
                elif src[i] == "`":
                    i += 1
                    break
                else:
                    blank(i)
                    i += 1
            else:
                break
            # If we broke out via ${, fall through to code scanning; the
            # closing } is detected below via the stack.
            if not template_stack:
                continue
            # Scan code inside the interpolation in the main loop.
            while i < n and template_stack:
                c = src[i]
                cn = src[i + 1] if i + 1 < n else ""
                if c == "{":
                    brace_depth_stack[-1] += 1
                    i += 1
                elif c == "}":
                    if brace_depth_stack[-1] == 0:
                        # end of interpolation: back inside the template
                        template_stack.pop()
                        brace_depth_stack.pop()
                        i += 1
                        # resume blanking template text until ` or next ${
                        while i < n:
                            if src[i] == "\\":
                                blank(i)
                                i += 1
                                if i < n:
                                    blank(i)
                                    i += 1
                            elif src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                                template_stack.append("template")
                                brace_depth_stack.append(0)
                                i += 2
                                break
                            elif src[i] == "`":
                                i += 1
                                break
                            else:
                                blank(i)
                                i += 1
                    else:
                        brace_depth_stack[-1] -= 1
                        i += 1
                elif c == "/" and cn == "/":
                    while i < n and src[i] != "\n":
                        blank(i)
                        i += 1
                elif c in ("'", '"'):
                    q = c
                    i += 1
                    while i < n and src[i] != q:
                        if src[i] == "\\":
                            blank(i)
                            i += 1
                        if i < n:
                            blank(i)
                            i += 1
                    i += 1
                elif c == "`":
                    # nested template inside interpolation: blank its text
                    i += 1
                    while i < n and src[i] != "`":
                        if src[i] == "\\":
                            blank(i)
                            i += 1
                        if i < n:
                            blank(i)
                            i += 1
                    i += 1
                else:
                    i += 1
        else:
            i += 1
    return "".join(out)


def agent_call_spans(src: str) -> list[tuple[int, int]]:
    """(start, end) source spans of every code-context agent(...) call,
    delimited by balanced parens over the blanked source."""
    blanked = blank_non_code(src)
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"\bagent\s*\(", blanked):
        depth = 0
        j = m.end() - 1  # at the opening paren
        while j < len(blanked):
            if blanked[j] == "(":
                depth += 1
            elif blanked[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        spans.append((m.start(), j + 1))
    return spans


def _split(src: str, span: tuple[int, int]) -> tuple[str, str]:
    """(original, blanked) text of one call span."""
    return src[span[0] : span[1]], blank_non_code(src)[span[0] : span[1]]


# ---------------------------------------------------------------------------
# Teeth: the scanner must reject bad input before it is trusted (the
# test_doc_single_home_gate.py red-fixture precedent).
# ---------------------------------------------------------------------------


class TestScannerHasTeeth:
    def test_flags_model_less_call(self) -> None:
        red = "await agent('do the thing', { label: 'x' })\n"
        spans = agent_call_spans(red)
        assert len(spans) == 1
        _, blanked = _split(red, spans[0])
        assert "model:" not in blanked
        assert "agentType:" not in blanked

    def test_ignores_call_inside_comment(self) -> None:
        red = "// await agent('x', { model: 'opus' })\nconst y = 1\n"
        assert agent_call_spans(red) == []

    def test_ignores_call_inside_template_text(self) -> None:
        red = "const p = `never call agent(here) yourself`\n"
        assert agent_call_spans(red) == []

    def test_handles_paren_inside_string_argument(self) -> None:
        red = "await agent('close ) me', { model: 'opus' })\nawait other()\n"
        spans = agent_call_spans(red)
        assert len(spans) == 1
        original, blanked = _split(red, spans[0])
        assert "model:" in blanked
        assert original.endswith("'opus' })")

    def test_sees_call_inside_template_interpolation(self) -> None:
        red = "const p = `count: ${await agent('x', { label: 'y' })}`\n"
        spans = agent_call_spans(red)
        assert len(spans) == 1

    def test_forbidden_token_in_code_is_seen(self) -> None:
        red = "const t = Date.now()\n"
        assert "Date.now(" in blank_non_code(red)

    def test_forbidden_token_in_comment_is_not_flagged(self) -> None:
        red = "// Date.now() is banned here\nconst t = 1\n"
        assert "Date.now(" not in blank_non_code(red)


# ---------------------------------------------------------------------------
# The pins over the real artifacts.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def script_src() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc_src() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


class TestScriptStructure:
    def test_script_exists_with_meta(self, script_src: str) -> None:
        assert SCRIPT_PATH.exists()
        assert "export const meta" in script_src

    def test_phase_calls_match_meta_phases(self, script_src: str) -> None:
        called = set(re.findall(r"phase\('([^']+)'\)", script_src))
        declared = set(re.findall(r"\{ title: '([^']+)',", script_src))
        assert called == {"Implement", "Refute", "Judge", "Close", "Finalize"}
        assert called == declared

    def test_every_agent_call_pins_model_or_agent_type(self, script_src: str) -> None:
        spans = agent_call_spans(script_src)
        # 8 call sites: 2 escalation reviewers, finalize, implementer,
        # refuter, judge, closer, refuter-recheck. Changing this count is a
        # pipeline-structure change -- make it deliberately, here and in the
        # design doc.
        assert len(spans) == 8
        with_model = 0
        with_agent_type = 0
        for span in spans:
            _, blanked = _split(script_src, span)
            has_model = "model:" in blanked
            has_type = "agentType:" in blanked
            assert has_model or has_type, "agent() call without an explicit model pin"
            with_model += int(has_model and not has_type)
            with_agent_type += int(has_type)
        assert with_model == 5
        assert with_agent_type == 3

    def test_agent_type_dispatch_is_bare_names(self, script_src: str) -> None:
        assert script_src.count("agentType: 'n1-refuter'") == 2  # refute + recheck
        assert script_src.count("agentType: 'n1-judge'") == 1
        assert "sartor:n1-" not in script_src  # plugin-namespace dispatch is unattested

    def test_refuter_reads_staged_diff_and_is_told_to_refute(self, script_src: str) -> None:
        assert "git diff --staged" in script_src
        assert "REFUTE" in script_src

    def test_implementer_commits_nothing(self, script_src: str) -> None:
        assert "COMMIT NOTHING" in script_src
        assert "NO EDIT APPROVAL" in script_src

    def test_envelope_cited_in_all_role_prompts(self, script_src: str) -> None:
        # finalize, implementer, refuter, judge, closer, recheck. The two
        # escalation reviewers deliberately get the wider-view brief instead.
        assert script_src.count("${ENVELOPE}") == 6

    def test_gate_string_appears_only_in_ban_context(self, script_src: str) -> None:
        lines = [ln for ln in script_src.splitlines() if "python -m scripts.gate" in ln]
        assert lines, "the ban itself must be present"
        for ln in lines:
            assert ln.lstrip().startswith("//") or "NEVER" in ln, ln

    def test_no_unauthorized_surfaces(self, script_src: str) -> None:
        assert "docs/dev/ledger" not in script_src
        for event in UNAUTHORIZED_LEDGER_EVENTS:
            assert event not in script_src, event

    def test_no_resume_breaking_tokens_in_code(self, script_src: str) -> None:
        blanked = blank_non_code(script_src)
        for token in RESUME_BREAKING_TOKENS:
            assert token not in blanked, token

    def test_halt_point_short_circuits_before_any_reviewer(self, script_src: str) -> None:
        short_circuit = "if (flag.kind === 'halt_point' || flag.kind === 'hook_block') {"
        idx = script_src.index(short_circuit)
        following = script_src[idx : idx + 200]
        assert "return { outcome: 'stop', flag, reviews: [] }" in following
        first_agent_call = agent_call_spans(script_src)[0][0]
        assert idx < first_agent_call, "halt short-circuit must precede every agent() call"

    def test_verbatim_field_passes_through_unmodified(self, script_src: str) -> None:
        assert "${flag.verbatim}" in script_src

    def test_drift_layer_inert_at_n1(self, script_src: str) -> None:
        assert "const N = 1" in script_src
        assert "if (sprint < N - 1) {" in script_src
        assert "driftCheckpoints: []" in script_src

    def test_syntax_via_node(self, script_src: str) -> None:
        """The harness wraps the script body in an async function (top-level
        return/await are harness-legal, plain-ESM-illegal), so the check
        parses the same wrapped form. Verified 2026-08-11 on Node v24: the
        raw file fails on the top-level return; this wrapped form passes."""
        node = shutil.which("node")
        if node is None:
            pytest.skip("node not on PATH")
        wrapped = (
            "async function __harness(){\n"
            + script_src.replace("export const meta", "const meta", 1)
            + "\n}"
        )
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell, source via stdin
            [node, "--input-type=module", "--check"],
            input=wrapped,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_args_normalization_tolerates_a_json_string(self, script_src: str) -> None:
        """`args` arriving as a JSON string must still resolve to real config.

        Not a hypothetical. Observed 2026-08-12 on Epic B run 1: the Workflow
        harness delivered `typeof args === 'string'` even though the caller
        passed an object, contradicting the documented "verbatim" contract
        (probe run wf_733613af-2c5). The old `{ ...defaults, ...(args || {}) }`
        spread turned that string into index-keyed characters, every
        required-arg guard fired, and the pipeline could not be invoked at all
        -- twice, before a single agent spawned.

        Rewritten 2026-08-12 after three adversarial refuters broke the first
        version (appendix of docs/dev/handoffs/epic-b-render-ats.md): the span
        is located in blank_non_code() output so a copy of the block hiding in
        a comment or template literal can never satisfy it; the executed
        snippet is the REAL region -- defaults, normalization, and both
        required-arg guards, nothing hand-supplied; and every arm asserts the
        discriminating error MESSAGE, so deleting the validation guard, the
        Array.isArray check, or the JSON.parse try/catch each fails a specific
        arm.

        Known limit (C-0): whether `args` is even the binding name the harness
        injects cannot be pinned by a unit test; the probes prove it is today.
        """
        node = shutil.which("node")
        if node is None:
            pytest.skip("node not on PATH")

        # Anchor in the BLANKED source (offsets preserved 1:1), then slice the
        # real source at the same span -- per TestScannerHasTeeth, a match in
        # a comment or template literal cannot satisfy these anchors.
        blanked = blank_non_code(script_src)
        start = re.search(r"^const defaults = \{", blanked, re.MULTILINE)
        end = re.search(r"^const report = \{", blanked, re.MULTILINE)
        assert start is not None and end is not None and start.start() < end.start(), (
            "the defaults .. required-arg-guard region is missing from "
            "n1-baseline.mjs -- a JSON-string `args` will silently spread into "
            "index-keyed characters and block invocation"
        )
        assert "rawArgs" in blanked[start.start() : end.start()], (
            "the args-normalization block is gone from the code (not comments) "
            "between `const defaults` and `const report` -- the harness delivers "
            "args as a JSON string (wf_733613af-2c5) and nothing normalizes it"
        )
        region = script_src[start.start() : end.start()]

        def run(args_literal: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(  # noqa: S603 - fixed argv, no shell, source via stdin
                [node, "--input-type=module"],
                input=(
                    f"const args = {args_literal}\n{region}\nconsole.log(JSON.stringify(cfg))\n"
                ),
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

        # The incident shape: a JSON object string must resolve to real config,
        # with the REAL defaults applied.
        as_string = run('\'{"sprintBriefPath":"a.md","epicBriefPath":"b.md"}\'')
        assert as_string.returncode == 0, as_string.stderr
        assert '"sprintBriefPath":"a.md"' in as_string.stdout
        assert '"epicBriefPath":"b.md"' in as_string.stdout
        assert '"stage":"sprint"' in as_string.stdout, "the real defaults must apply"

        # A real object must keep working -- the fix cannot be string-only.
        as_object = run("{ sprintBriefPath: 'a.md', epicBriefPath: 'b.md' }")
        assert as_object.returncode == 0, as_object.stderr
        assert '"sprintBriefPath":"a.md"' in as_object.stdout

        # Empty/absent/null args must reach the REAL required-arg guard, which
        # names what is actually missing (the first version's carve-out threw a
        # misleading "got string" for an empty string instead).
        for literal in ("''", "undefined", "'null'"):
            absent = run(literal)
            assert absent.returncode != 0, f"args={literal} must fail the required-arg guard"
            assert "sprintBriefPath and args.epicBriefPath are required" in absent.stderr, (
                f"args={literal}: expected the required-arg diagnostic, got: {absent.stderr[:200]}"
            )

        # A non-JSON string is a caller error that NAMES args. Deleting the
        # try/catch fails here: the raw SyntaxError carries no such prefix.
        not_json = run("'not json'")
        assert not_json.returncode != 0
        assert "args arrived as a string that is not valid JSON" in not_json.stderr, (
            f"expected the authored wrapper naming args, got: {not_json.stderr[:200]}"
        )

        # An array is rejected BY NAME. Deleting Array.isArray or the whole
        # validation guard fails here: an array that slips the guard spreads
        # index-keyed and dies on the required-arg guard message instead.
        as_array = run('\'["a.md","b.md"]\'')
        assert as_array.returncode != 0
        assert "got array" in as_array.stderr, (
            f"expected the guard to reject an array by name, got: {as_array.stderr[:200]}"
        )

        # The committed form of the wf_af5e441a-faa discriminating signal:
        # finalize without commitMessage must get PAST the args parse and fail
        # on the commitMessage guard, not the args guard.
        finalize = run('\'{"stage":"finalize","sprintBriefPath":"a.md","epicBriefPath":"b.md"}\'')
        assert finalize.returncode != 0
        assert "commitMessage is required" in finalize.stderr, (
            f"expected the finalize guard past the args parse, got: {finalize.stderr[:200]}"
        )


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    body = text.split("---", 2)[1]
    model = re.search(r"^model: (.+)$", body, re.MULTILINE)
    tools = re.findall(r"^  - (\w+)$", body, re.MULTILINE)
    assert model is not None
    return {"model": model.group(1).strip(), "tools": tools}


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class TestRoleFiles:
    @pytest.mark.parametrize(
        ("path", "model"),
        [(REFUTER_PATH, "claude-sonnet-5"), (JUDGE_PATH, "claude-opus-5")],
        ids=["refuter", "judge"],
    )
    def test_frontmatter_pins(self, path: Path, model: str) -> None:
        fm = _frontmatter(path)
        # Frontmatter is the single source of truth for agentType-dispatched
        # models (the script pins model: only on default-type agents).
        assert fm["model"] == model
        assert fm["tools"] == ["Read", "Grep", "Glob", "Bash"]

    @pytest.mark.parametrize("path", [REFUTER_PATH, JUDGE_PATH], ids=["refuter", "judge"])
    def test_read_only_git_clause_present(self, path: Path) -> None:
        text = _normalized(path.read_text(encoding="utf-8"))
        assert _normalized(READ_ONLY_GIT_CLAUSE) in text


class TestRunbookDoc:
    def test_step_six_assertion_verbatim(self, doc_src: str) -> None:
        assert "git diff --quiet" in doc_src
        assert "git status --porcelain --untracked-files=all" in doc_src

    def test_literal_gate_invocation(self, doc_src: str) -> None:
        assert "nohup python -m scripts.gate > gate1.log 2>&1 &" in doc_src
        # The wait is on the gate log's own terminal line, NEVER process-name
        # polling: `tasklist | grep python.exe` matches nothing on this machine
        # (the interpreter is python3.13.exe), so a poll loop exits instantly
        # and a mid-run log reads as finished (observed 2026-08-12, twice).
        assert 'until grep -qE "^gate: (all steps passed|FAILED)" gate1.log' in doc_src
        assert "**never** process-name polling" in doc_src

    def test_preflight_decision_batch_step_present(self, doc_src: str) -> None:
        """Runbook step 0a: one batched preflight question set at kickoff.

        Epic B run 1's overnight window was lost to serial owner questions at
        5-10 minute intervals; the run never started. The chain exists to use
        long uninterrupted windows, so the kickoff discipline is part of the
        contract this file pins.
        """
        assert "Preflight decision batch" in doc_src
        assert "one batch, in one message" in doc_src

    def test_invocation_is_by_script_path(self, doc_src: str) -> None:
        assert "scriptPath: '.claude/workflows/n1-baseline.mjs'" in doc_src

    def test_states_never_run_limit(self, doc_src: str) -> None:
        assert "BUILT, NEVER RUN" in doc_src
