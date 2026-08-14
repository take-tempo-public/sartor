"""Teeth tests for charter **C-12** — declare the gap, never fill it.

Two mechanisms, each asserted RED-then-GREEN (a gate never shown to reject a bad input is
not evidence of anything — this repo's own standard):

* **M2, the observed-citation floor.** `## Observed` filled with plausible narrative and no
  artifact behind any of it now blocks the production edit. That is the shape items 13, 15
  and 31 shipped under: each filed mechanism was plausible, each became a premise, each was
  wrong.
* **M3, compaction disclosure.** Before this, `restore_evidence()` keyed entirely off a
  `fix/*` dossier, so a compaction on a `feat/*` or `chore/*` branch — i.e. most branches —
  injected **nothing at all**, and the rebuilt context had no way to know it had lost
  anything. `test_compaction_notice_fires_on_a_non_fix_branch` is that exact RED.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.enforcement.adapters import claude_context_hook as ctx
from scripts.enforcement.evidence import has_observed_citation, observed_citations
from scripts.enforcement.guards import require_evidence_before_fix as guard

_REPO_ROOT = Path(__file__).resolve().parent.parent

_UNCITED = """# Diagnosis

## Observed

The compose panel settles before the background volley finishes, and the reload then races
the scroll restore. This happens because the counter is decremented too early, which leaves
the gate open while a request is still in flight.

## Inferred

## Falsified
"""

_CITED = """# Diagnosis

## Observed

CI run 30968745766, ux job log: `test_scroll_spy_attributes_overlapping_refresh_corpus_calls`
failed 2 of 3 attempts. The clear happens at `static/app.js:7036`, before the rAF fires.

## Inferred

## Falsified
"""


class TestM2ObservedCitationFloor:
    def test_uncited_narrative_has_no_citations(self) -> None:
        """Fluent, plausible, and sourced to nothing — the exact failure shape."""
        assert observed_citations(_UNCITED) == 0
        assert not has_observed_citation(_UNCITED)

    def test_a_run_id_or_path_line_counts(self) -> None:
        assert has_observed_citation(_CITED)

    @pytest.mark.parametrize(
        "marker",
        [
            "see https://github.com/x/y/actions/runs/30968745766",
            "run 30968745766 failed",
            "the clear is at static/app.js:7036",
            "tests/test_hardening.py::test_reader_never_observes_a_partial_file failed",
            "reported on PR #99",
            "```\nTimeoutError: Timeout 30000ms exceeded\n```",
        ],
    )
    def test_each_accepted_citation_form(self, marker: str) -> None:
        """Deliberately broad: the point is to reject *unsourced narrative*, not to
        dictate one citation format and make honest authors fight it."""
        text = f"## Observed\n\nSomething was observed, and here is the artifact: {marker}\n"
        assert has_observed_citation(text), marker

    def test_real_repo_dossier_passes(self) -> None:
        """Sanity against the corpus: a real, well-written dossier must not be blocked."""
        dossier = _REPO_ROOT / "docs" / "dev" / "diagnosis" / "ux-scroll-spy-overlapping-refresh.md"
        assert has_observed_citation(dossier.read_text(encoding="utf-8"))


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )


@pytest.fixture
def fix_repo_with_dossier(tmp_path: Path) -> Path:
    """A `fix/*` repo whose dossier's `## Observed` is filled but **uncited**."""
    subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "init", "-q", str(tmp_path)], check=True
    )
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed")
    _git(tmp_path, "checkout", "-q", "-b", "fix/some-bug")
    (tmp_path / "blueprints").mkdir()
    (tmp_path / "blueprints" / "applications.py").write_text("x = 1\n", encoding="utf-8")
    diagnosis = tmp_path / "docs" / "dev" / "diagnosis"
    diagnosis.mkdir(parents=True)
    (diagnosis / "some-bug.md").write_text(_UNCITED, encoding="utf-8")
    return tmp_path


class TestM2BlocksTheEdit:
    def test_uncited_observed_blocks_production_edit(self, fix_repo_with_dossier: Path) -> None:
        """RED: `## Observed` clears the character floor but cites nothing."""
        env = {"CLAUDE_PROJECT_DIR": str(fix_repo_with_dossier)}
        result = guard.decide(str(fix_repo_with_dossier / "blueprints" / "applications.py"), env)
        assert result.blocked
        assert any("cites NOTHING" in m for m in result.messages), result.messages

    def test_adding_a_citation_unblocks(self, fix_repo_with_dossier: Path) -> None:
        """GREEN: the same dossier, with an artifact named."""
        dossier = fix_repo_with_dossier / "docs" / "dev" / "diagnosis" / "some-bug.md"
        dossier.write_text(_CITED, encoding="utf-8")
        env = {"CLAUDE_PROJECT_DIR": str(fix_repo_with_dossier)}
        result = guard.decide(str(fix_repo_with_dossier / "blueprints" / "applications.py"), env)
        assert not result.blocked, result.messages


class TestM3CompactionDisclosure:
    def test_no_notice_on_a_normal_startup(self) -> None:
        """Silence when nothing was lost — a hook that greets every session is skipped."""
        assert ctx.compaction_notice({"source": "startup"}) == ""
        assert ctx.compaction_notice({}) == ""

    def test_notice_fires_on_compact_and_names_the_loss(self) -> None:
        notice = ctx.compaction_notice({"source": "compact"})
        assert "INFORMATION WAS LOST" in notice
        assert "C-12" in notice
        assert "reconcile against the" in notice

    def test_compaction_notice_fires_on_a_non_fix_branch(self, tmp_path: Path) -> None:
        """**The RED this mechanism exists for.**

        `restore_evidence()` used to return "" whenever the branch was not `fix/*` or had no
        dossier — so on a `feat/*` branch (this very branch, for one) a compaction injected
        nothing and the rebuilt context could not know it had lost anything.
        """
        payload = {"source": "compact", "cwd": str(tmp_path)}
        replayed = ctx.restore_evidence(payload)
        assert "INFORMATION WAS LOST" in replayed

    def test_receipt_is_written_and_counted(self, tmp_path: Path) -> None:
        """PreCompact cannot reach Claude, so the loss is recorded to disk instead."""
        payload = {"session_id": "sess-1", "cwd": str(tmp_path), "trigger": "auto"}
        assert ctx.record_compaction(payload)
        shard = tmp_path / "docs" / "dev" / "ledger" / "sess-1.jsonl"
        record = json.loads(shard.read_text(encoding="utf-8").strip())
        assert record["event"] == "compacted"
        assert record["trigger"] == "auto"
        assert ctx.compaction_count(payload) == 1

        ctx.record_compaction(payload)
        assert ctx.compaction_count(payload) == 2

    def test_receipt_bytes_are_lf_only(self, tmp_path: Path) -> None:
        """**The RED for the CRLF ledger class (fix/n1-invoker-context-budget).**

        `record_compaction` opened the shard in text mode with no `newline=` argument, so
        on Windows every appended row's `\\n` was translated to CRLF in the WORKING TREE —
        the same post-checkout byte class S3 caught in workflow scripts
        (tests/test_n1_pipeline.py::TestWorkflowWorkingTreeBytes), observed live in real
        shards on 2026-08-13 (twice) and 2026-08-14. `.gitattributes` governs checkout,
        not what a tool writes afterwards.
        """
        payload = {"session_id": "sess-lf", "cwd": str(tmp_path)}
        assert ctx.record_compaction(payload)
        raw = (tmp_path / "docs" / "dev" / "ledger" / "sess-lf.jsonl").read_bytes()
        assert b"\r" not in raw, f"hook-written receipt carries CR bytes: {raw!r}"

    def test_notice_reports_the_running_count(self, tmp_path: Path) -> None:
        payload = {"session_id": "sess-2", "cwd": str(tmp_path), "trigger": "manual"}
        ctx.record_compaction(payload)
        ctx.record_compaction(payload)
        notice = ctx.compaction_notice({**payload, "source": "compact"})
        assert "this session: 2" in notice

    def test_no_session_id_does_not_wedge_the_compaction(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed receipt must never block a compaction — the cure would be worse.

        `CLAUDE_CODE_SESSION_ID` is deleted explicitly rather than assumed absent. The first
        version of this test asserted against the ambient environment and passed or failed
        depending on who ran it — and, worse, `_ledger_shard`'s env fallback meant it could
        have written a receipt into a **real** tracked ledger shard had `CLAUDE_PROJECT_DIR`
        also been set. Same class as the telemetry-redirect trap in
        `tests/conftest.py::_default_llm_log_path`.
        """
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        assert not ctx.record_compaction({"cwd": str(tmp_path)})
        assert ctx.compaction_count({"cwd": str(tmp_path)}) == 0

    def test_session_id_from_the_environment_is_honoured(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The env fallback is deliberate — it mirrors `scripts/verify_doc_template.py`."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-env")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        assert ctx.record_compaction({"cwd": str(tmp_path)})
        assert (tmp_path / "docs" / "dev" / "ledger" / "sess-env.jsonl").is_file()

    def test_record_session_field_matches_the_payload_not_unknown(self, tmp_path: Path) -> None:
        """**The RED this fix exists for (D1).**

        Before this fix, `record_compaction`'s own `record["session"]` field read
        `payload.get("session_id", "unknown")` with no environment fallback — unlike
        `_ledger_shard` three lines above it, which does fall back to
        `CLAUDE_CODE_SESSION_ID`. Every historical row in every ledger shard in this repo
        (52/52, across all sessions) carried `"session": "unknown"` even though the shard
        FILENAME was always correct. This asserts the field inside the row, not just the
        filename.
        """
        payload = {"session_id": "sess-3", "cwd": str(tmp_path)}
        ctx.record_compaction(payload)
        shard = tmp_path / "docs" / "dev" / "ledger" / "sess-3.jsonl"
        record = json.loads(shard.read_text(encoding="utf-8").strip())
        assert record["session"] == "sess-3"

    def test_record_session_field_falls_back_to_the_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same fallback the shard filename already used — now the row's own field agrees."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-env-2")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        ctx.record_compaction({"cwd": str(tmp_path)})
        shard = tmp_path / "docs" / "dev" / "ledger" / "sess-env-2.jsonl"
        record = json.loads(shard.read_text(encoding="utf-8").strip())
        assert record["session"] == "sess-env-2"

    def test_agent_id_and_agent_type_are_captured_when_present(self, tmp_path: Path) -> None:
        """D2: pure enrichment — a subagent's `compacted` row is now attributable.

        `agent_id`/`agent_type` are documented as present in the PreToolUse payload inside a
        subagent (docs/dev/epic-a-chain-design-corrections.md §14.7). This is the first place
        this repo's enforcement code captures either field.
        """
        payload = {
            "session_id": "sess-4",
            "cwd": str(tmp_path),
            "agent_id": "agent-abc123",
            "agent_type": "general-purpose",
        }
        ctx.record_compaction(payload)
        shard = tmp_path / "docs" / "dev" / "ledger" / "sess-4.jsonl"
        record = json.loads(shard.read_text(encoding="utf-8").strip())
        assert record["agent_id"] == "agent-abc123"
        assert record["agent_type"] == "general-purpose"

    def test_agent_id_and_agent_type_are_omitted_not_null_when_absent(self, tmp_path: Path) -> None:
        """A main-session compaction's row stays exactly as it was before this change —
        no `null`-padded keys cluttering the common case."""
        payload = {"session_id": "sess-5", "cwd": str(tmp_path)}
        ctx.record_compaction(payload)
        shard = tmp_path / "docs" / "dev" / "ledger" / "sess-5.jsonl"
        record = json.loads(shard.read_text(encoding="utf-8").strip())
        assert "agent_id" not in record
        assert "agent_type" not in record

    def test_no_threshold_notice_below_the_threshold(self, tmp_path: Path) -> None:
        payload = {"session_id": "sess-6", "cwd": str(tmp_path)}
        for _ in range(ctx._COMPACTION_THRESHOLD - 1):
            ctx.record_compaction(payload)
        assert ctx.compaction_threshold_notice(payload) == ""

    def test_threshold_notice_fires_at_the_threshold_and_is_external_not_self_assessed(
        self, tmp_path: Path
    ) -> None:
        """**The RED this mechanism exists for.** Stop 3 of Epic A falsified an agent's own
        predicted remaining capacity as a reliable handoff trigger — this asserts the notice
        names an external count, not a feeling, as the signal."""
        payload = {"session_id": "sess-7", "cwd": str(tmp_path)}
        for _ in range(ctx._COMPACTION_THRESHOLD):
            ctx.record_compaction(payload)
        notice = ctx.compaction_threshold_notice(payload)
        assert f"{ctx._COMPACTION_THRESHOLD} on record" in notice
        assert "EXTERNAL evidence, not a self-assessment" in notice

    def test_threshold_notice_fires_on_a_fresh_non_compacted_start(self, tmp_path: Path) -> None:
        """Unlike `compaction_notice`, this must NOT require `source == "compact"` — the count
        has to stay visible on an ordinary fresh start within the same session lineage, since
        that is exactly when a hand-off decision is still actionable."""
        payload = {"session_id": "sess-8", "cwd": str(tmp_path)}
        for _ in range(ctx._COMPACTION_THRESHOLD):
            ctx.record_compaction(payload)
        # no "source" key at all -- an ordinary (non-post-compaction) SessionStart
        assert ctx.compaction_threshold_notice(payload) != ""
        assert ctx.compaction_notice(payload) == ""  # the OTHER notice correctly stays silent

    def test_restore_evidence_includes_the_threshold_notice(self, tmp_path: Path) -> None:
        payload = {"session_id": "sess-9", "cwd": str(tmp_path)}
        for _ in range(ctx._COMPACTION_THRESHOLD):
            ctx.record_compaction(payload)
        assert "COMPACTION THRESHOLD" in ctx.restore_evidence(payload)
