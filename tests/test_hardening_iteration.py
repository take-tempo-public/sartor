"""Tests for the iteration helpers added in hardening.py.

Covers save_iteration_context: the helper that snapshots a parent context
into a new immutable child file with incremented iteration counter,
parent_context_path link, last_generated_* snapshots, and consumed edits.
"""

import json
from pathlib import Path

from hardening import save_iteration_context


def _seed_parent(tmp_path: Path, iteration: int = 0, extras: dict | None = None) -> tuple[dict, str]:
    """Build a minimal parent context dict and return (context, path_str).

    The parent file is what /api/generate would have loaded — typically the
    analyze output (iteration 0) or a prior iteration's snapshot.
    """
    parent: dict = {
        "timestamp": "2026-05-11T12:00:00",
        "candidate": {"name": "Alice"},
        "resume": {"text": "original resume", "filename": "alice.docx",
                   "format": ".docx", "sections": [], "path": ""},
        "supplemental_resumes": [],
        "job_description": "JD",
        "deterministic_analysis": {
            "jd_keywords": {}, "resume_keywords": {},
            "keyword_overlap": {}, "ats_warnings": [],
        },
        "iteration": iteration,
        "run_id": "abc123",
    }
    if extras:
        parent.update(extras)

    user_dir = tmp_path / "alice"
    user_dir.mkdir()
    parent_path = user_dir / "context_20260511_120000.json"
    parent_path.write_text(json.dumps(parent), encoding="utf-8")
    return parent, str(parent_path)


def test_save_iteration_context_increments_iteration_from_zero(tmp_path):
    parent, parent_path = _seed_parent(tmp_path, iteration=0)

    new_path = save_iteration_context(
        parent_context=parent,
        parent_path=parent_path,
        last_generated_resume="GEN1 resume",
        last_generated_cover_letter="GEN1 letter",
        username="alice",
        base_dir=str(tmp_path),
    )

    saved = json.loads(Path(new_path).read_text(encoding="utf-8"))
    assert saved["iteration"] == 1
    assert saved["parent_context_path"] == parent_path
    assert saved["last_generated_resume"] == "GEN1 resume"
    assert saved["last_generated_cover_letter"] == "GEN1 letter"


def test_save_iteration_context_increments_from_existing_iteration(tmp_path):
    parent, parent_path = _seed_parent(tmp_path, iteration=2)

    new_path = save_iteration_context(
        parent_context=parent, parent_path=parent_path,
        last_generated_resume="r3", last_generated_cover_letter="c3",
        username="alice", base_dir=str(tmp_path),
    )
    saved = json.loads(Path(new_path).read_text(encoding="utf-8"))
    assert saved["iteration"] == 3


def test_save_iteration_context_filename_carries_iter_suffix(tmp_path):
    parent, parent_path = _seed_parent(tmp_path, iteration=0)

    new_path = save_iteration_context(
        parent_context=parent, parent_path=parent_path,
        last_generated_resume="r", last_generated_cover_letter="c",
        username="alice", base_dir=str(tmp_path),
    )
    # Filename must encode the iteration so dashboards can sort/scan visually
    assert "_iter1.json" in Path(new_path).name


def test_save_iteration_context_consumes_edits(tmp_path):
    """edited_resume_text/edited_cover_letter_text must be cleared on the
    child — they fed the prompt that produced this generation; carrying them
    forward would cause double-application on the next iteration."""
    parent, parent_path = _seed_parent(tmp_path, iteration=1, extras={
        "edited_resume_text": "user typed this",
        "edited_cover_letter_text": "user typed letter",
        "last_generated_resume": "prior gen",
        "last_generated_cover_letter": "prior letter",
    })

    new_path = save_iteration_context(
        parent_context=parent, parent_path=parent_path,
        last_generated_resume="new gen", last_generated_cover_letter="new letter",
        username="alice", base_dir=str(tmp_path),
    )

    saved = json.loads(Path(new_path).read_text(encoding="utf-8"))
    assert "edited_resume_text" not in saved
    assert "edited_cover_letter_text" not in saved
    # And the new last_generated_* reflects the just-completed call
    assert saved["last_generated_resume"] == "new gen"


def test_save_iteration_context_appends_iteration_note(tmp_path):
    parent, parent_path = _seed_parent(tmp_path, iteration=0, extras={
        "iteration_notes": [{"timestamp": "earlier", "action": "save_edits",
                              "summary": "user edited resume"}],
    })

    new_path = save_iteration_context(
        parent_context=parent, parent_path=parent_path,
        last_generated_resume="r", last_generated_cover_letter="c",
        username="alice", base_dir=str(tmp_path),
        action="generate", summary="from edited baseline",
    )

    saved = json.loads(Path(new_path).read_text(encoding="utf-8"))
    notes = saved["iteration_notes"]
    assert len(notes) == 2
    # Pre-existing note is preserved
    assert notes[0]["action"] == "save_edits"
    # New note appended last
    assert notes[1]["action"] == "generate"
    assert notes[1]["summary"] == "from edited baseline"
    assert notes[1]["timestamp"]  # not empty


def test_save_iteration_context_preserves_clarifications(tmp_path):
    """Clarifications from prior iterations must accumulate across iterations
    so the LLM continues to see all confirmed candidate truths."""
    parent, parent_path = _seed_parent(tmp_path, iteration=1, extras={
        "clarification_questions": [{"id": "q1", "text": "Q?", "kind": "experience_probe"}],
        "clarifications": {"q1": "Yes, used K8s in prod."},
    })

    new_path = save_iteration_context(
        parent_context=parent, parent_path=parent_path,
        last_generated_resume="r", last_generated_cover_letter="c",
        username="alice", base_dir=str(tmp_path),
    )
    saved = json.loads(Path(new_path).read_text(encoding="utf-8"))
    assert saved["clarifications"] == {"q1": "Yes, used K8s in prod."}
    assert len(saved["clarification_questions"]) == 1


def test_save_iteration_context_does_not_mutate_parent(tmp_path):
    """The helper must deep-copy. If a caller keeps reading the parent dict
    after this call returns, it must observe the original state."""
    parent, parent_path = _seed_parent(tmp_path, iteration=0)
    parent_iteration_before = parent["iteration"]

    save_iteration_context(
        parent_context=parent, parent_path=parent_path,
        last_generated_resume="r", last_generated_cover_letter="c",
        username="alice", base_dir=str(tmp_path),
    )
    assert parent["iteration"] == parent_iteration_before
    assert "last_generated_resume" not in parent
