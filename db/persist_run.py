"""Persist the LLM's structured generate() output to the corpus DB.

Phase B.3: after `generate()` returns in corpus mode, parse the
`selected_bullets`, `proposed_new_bullets`, and `proposed_experience_titles`
arrays and write them to the audit chain:

- `application_bullet` rows record which bullets were chosen, in what order
- `application_run_title` rows record which title framing was picked per
  experience (via `chosen_title_id`)
- New `bullet` rows are created for `proposed_new_bullets` with
  `is_pending_review=1, source='llm_proposed:<run_id>'`. A `proposal_review`
  row anchors each one with `decision='pending'`.
- New `experience_title` rows are created for `proposed_experience_titles`
  via the same flow.
- `application_run.generated_resume_md` and `generated_cover_letter_md`
  carry the output for the audit trail.
- `iteration_log` records the action.

Every generate of an application reuses ONE run (each iteration's context
carries the same `application_run_id`), so this is called repeatedly on the same
row. The run's `application_bullet` / `application_run_title` rows are therefore
REPLACED by the latest selection, not appended (owner decision D1, item 160 —
appending hit `uq_application_bullet` and rolled the whole persist back); the
per-iteration history lives in the context-file chain. A result with no cover
letter leaves a stored one alone, and a proposal whose text the experience
already has is not re-created. Evidence:
`docs/dev/diagnosis/regenerate-persistence.md`.

ID parsing: the prompt schema uses string prefixes (`e1`, `t10`, `b100`) so
the LLM's output stays self-documenting. This module strips the prefix and
validates the integer maps to a real row that belongs to the right
experience/candidate. Hallucinated IDs are logged and skipped — the
strict-grounding retry is a separate concern (B.3b/B.5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from db.models import (
    ApplicationBullet,
    ApplicationRun,
    ApplicationRunTitle,
    Bullet,
    Experience,
    ExperienceTitle,
    IterationLog,
    ProposalReview,
)

logger = logging.getLogger(__name__)


_VALID_PATTERN_KINDS = frozenset({"xyz", "star", "car", "manual"})


@dataclass
class PersistReport:
    """Summary of what was written; useful for telemetry + smoke output."""

    application_bullets_created: int = 0
    application_run_titles_created: int = 0
    proposed_bullets_created: int = 0
    proposed_titles_created: int = 0
    proposal_reviews_created: int = 0
    bullets_referenced_but_missing: list[int] = field(default_factory=list)
    titles_referenced_but_missing: list[int] = field(default_factory=list)
    experiences_referenced_but_missing: list[int] = field(default_factory=list)
    skipped_due_to_malformed_payload: int = 0
    # A bullet id repeated within one result, or a second title for an experience
    # already titled in it (both would violate the run's unique keys).
    duplicate_selections_skipped: int = 0
    # A proposed bullet whose text its experience already has (e.g. re-proposed by a
    # regenerate) — not re-created, so review never stacks duplicates.
    proposed_bullets_already_present: int = 0


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def persist_corpus_generation(
    session: Session,
    application_run: ApplicationRun,
    generate_result: dict[str, Any],
    candidate_id: int,
) -> PersistReport:
    """Write the LLM's structured output to the corpus audit chain.

    Pre-conditions:
    - `application_run` is the row created by `_run_analysis_corpus_backed`
    - `generate_result` is the dict returned by `analyzer.generate()` with
      corpus-mode fields present (selected_bullets, proposed_new_bullets,
      proposed_experience_titles)
    - `candidate_id` scopes the FK lookups so we don't accept hallucinated
      cross-candidate references

    Caller commits the session. On any per-item validation failure, this
    function logs + records the issue in the report and continues; it never
    aborts the whole persistence. Strict grounding (retry on mismatch) is a
    separate enforcement layer to be added in a follow-up.
    """
    report = PersistReport()

    # Persist the markdown output onto the run row for the audit trail. A résumé-only
    # generate returns "" for the letter; writing that would blank a letter the
    # detached cover-letter route stored (diagnosis O4), so only a real one lands.
    application_run.generated_resume_md = generate_result.get("resume_content")
    cover_letter = generate_result.get("cover_letter_content")
    if cover_letter:
        application_run.generated_cover_letter_md = cover_letter

    selected = generate_result.get("selected_bullets") or []
    _persist_selected_bullets(
        session,
        application_run,
        selected,
        candidate_id,
        report,
    )

    proposed_bullets = generate_result.get("proposed_new_bullets") or []
    _persist_proposed_bullets(
        session,
        application_run,
        proposed_bullets,
        candidate_id,
        report,
    )

    proposed_titles = generate_result.get("proposed_experience_titles") or []
    _persist_proposed_titles(
        session,
        application_run,
        proposed_titles,
        candidate_id,
        report,
    )

    # Iteration_log entry — one row recording this generation. The summary
    # captures the headline counts for the dashboard.
    session.add(
        IterationLog(
            application_run_id=application_run.id,
            action="generate",
            summary=(
                f"selected={report.application_bullets_created} bullets, "
                f"titles={report.application_run_titles_created}, "
                f"proposals={report.proposed_bullets_created}b/{report.proposed_titles_created}t"
            ),
        )
    )
    session.flush()
    return report


def persist_cover_letter_md(
    session: Session,
    application_run: ApplicationRun,
    cover_letter_md: str,
) -> None:
    """Write ONLY `generated_cover_letter_md` onto an existing run row.

    For the detached cover-letter route (`POST /api/generate-cover-letter`),
    which runs *after* the résumé generation has already persisted the run row.
    Unlike `persist_corpus_generation`, this deliberately does NOT touch
    `generated_resume_md` or the bullet/title audit tables — the cover-letter
    result carries no résumé content, so routing it through the full persist
    path would null out the already-saved résumé md. Caller commits.
    """
    application_run.generated_cover_letter_md = cover_letter_md
    session.flush()


# ---------------------------------------------------------------------------
# selected_bullets → application_bullet + application_run_title
# ---------------------------------------------------------------------------


def _persist_selected_bullets(
    session: Session,
    application_run: ApplicationRun,
    selected: list[Any],
    candidate_id: int,
    report: PersistReport,
) -> None:
    """Each entry: {experience_id, chosen_title_id, bullet_ids_in_order}.

    All IDs come as prefixed strings (e.g., "e3", "t12", "b41"). The LLM
    occasionally drops the prefix; both forms are accepted to keep the path
    forgiving — we fail safely on parse errors, not on minor formatting.

    `selected` is typed `list[Any]`, not `list[dict[str, Any]]`, because each
    entry is untrusted LLM JSON — the `isinstance(entry, dict)` guard below is
    live defense against a malformed (non-dict) entry, not dead code.

    The run's existing rows are deleted first (replace, not append — see the
    module docstring); this runs inside the caller's one transaction, so a
    failure rolls back to the previous selection rather than a half-written one.
    Lookups are one `IN` query per kind (experiences, titles, bullets), so the
    statement count doesn't grow with the selection's size. `position` counts
    per experience, so an experience named in two entries continues its order.
    """
    session.query(ApplicationBullet).filter_by(application_run_id=application_run.id).delete()
    session.query(ApplicationRunTitle).filter_by(application_run_id=application_run.id).delete()

    # Parse pass: (experience_id, chosen_title_id | None, [bullet_id, ...]).
    parsed: list[tuple[int, int | None, list[int]]] = []
    for entry in selected:
        if not isinstance(entry, dict):
            report.skipped_due_to_malformed_payload += 1
            continue
        exp_id = _strip_id_prefix(entry.get("experience_id"), "e")
        if exp_id is None:
            report.skipped_due_to_malformed_payload += 1
            continue
        bullet_ids: list[int] = []
        for raw_bid in entry.get("bullet_ids_in_order") or []:
            bullet_id = _strip_id_prefix(raw_bid, "b")
            if bullet_id is None:
                report.skipped_due_to_malformed_payload += 1
                continue
            bullet_ids.append(bullet_id)
        # Chosen title — optional in the schema but the prompt requests it
        parsed.append((exp_id, _strip_id_prefix(entry.get("chosen_title_id"), "t"), bullet_ids))

    owned = _owned_experience_ids(session, candidate_id, {p[0] for p in parsed})
    wanted_titles = {t for e, t, _ in parsed if e in owned and t is not None}
    title_exp: dict[int, int] = (
        {
            tid: eid
            for tid, eid in session.query(ExperienceTitle.id, ExperienceTitle.experience_id)
            .filter(ExperienceTitle.id.in_(wanted_titles))
            .all()
        }
        if wanted_titles
        else {}
    )
    wanted_bullets = {b for e, _, bids in parsed if e in owned for b in bids}
    bullet_exp: dict[int, int] = (
        {
            bid: eid
            for bid, eid in session.query(Bullet.id, Bullet.experience_id)
            .filter(Bullet.id.in_(wanted_bullets))
            .all()
        }
        if wanted_bullets
        else {}
    )

    titled: set[int] = set()
    placed: set[int] = set()
    next_position: dict[int, int] = {}
    for exp_id, chosen_title_id, bullet_ids in parsed:
        # Verify experience belongs to this candidate
        if exp_id not in owned:
            report.experiences_referenced_but_missing.append(exp_id)
            continue

        if chosen_title_id is not None:
            if title_exp.get(chosen_title_id) != exp_id:
                report.titles_referenced_but_missing.append(chosen_title_id)
            elif exp_id in titled:
                report.duplicate_selections_skipped += 1
            else:
                session.add(
                    ApplicationRunTitle(
                        application_run_id=application_run.id,
                        experience_id=exp_id,
                        experience_title_id=chosen_title_id,
                    )
                )
                titled.add(exp_id)
                report.application_run_titles_created += 1

        # Bullets in order; a bullet must belong to THIS experience (which also
        # rejects another candidate's bullet).
        for bullet_id in bullet_ids:
            if bullet_exp.get(bullet_id) != exp_id:
                report.bullets_referenced_but_missing.append(bullet_id)
                continue
            if bullet_id in placed:
                report.duplicate_selections_skipped += 1
                continue
            position = next_position.get(exp_id, 0)
            session.add(
                ApplicationBullet(
                    application_run_id=application_run.id,
                    bullet_id=bullet_id,
                    position=position,
                )
            )
            next_position[exp_id] = position + 1
            placed.add(bullet_id)
            report.application_bullets_created += 1
    session.flush()


# ---------------------------------------------------------------------------
# proposed_new_bullets → bullet (pending) + proposal_review (pending)
# ---------------------------------------------------------------------------


def _persist_proposed_bullets(
    session: Session,
    application_run: ApplicationRun,
    proposals: list[Any],
    candidate_id: int,
    report: PersistReport,
) -> None:
    """Each proposal: {experience_id, text, pattern_kind, rationale}.

    `proposals` is typed `list[Any]`, not `list[dict[str, Any]]`, because each
    entry is untrusted LLM JSON — the `isinstance(entry, dict)` guard below is
    live defense against a malformed (non-dict) entry, not dead code.

    A proposal whose text its experience already has — active, retired, or an
    earlier generate's still-pending proposal — is skipped, the way
    `_persist_proposed_titles` skips a known title. One query loads the
    referenced experiences' bullet texts (which also gives each one's
    display_order base), and all new bullets flush once before their reviews.
    """
    source_value = f"llm_proposed:{application_run.run_id}"

    parsed: list[tuple[int, str, str | None]] = []
    for entry in proposals:
        if not isinstance(entry, dict):
            report.skipped_due_to_malformed_payload += 1
            continue
        exp_id = _strip_id_prefix(entry.get("experience_id"), "e")
        text = (entry.get("text") or "").strip()
        if exp_id is None or not text:
            report.skipped_due_to_malformed_payload += 1
            continue

        pattern_kind: str | None = (entry.get("pattern_kind") or "").strip().lower()
        if pattern_kind not in _VALID_PATTERN_KINDS:
            # Common LLM variants → normalize, else null
            normalized = (pattern_kind or "").replace("-", "").replace("_", "")
            pattern_kind = normalized if normalized in _VALID_PATTERN_KINDS else None
        parsed.append((exp_id, text, pattern_kind))

    owned = _owned_experience_ids(session, candidate_id, {p[0] for p in parsed})
    texts: dict[int, set[str]] = {eid: set() for eid in owned}
    counts: dict[int, int] = dict.fromkeys(owned, 0)
    if owned:
        for eid, existing_text in session.query(Bullet.experience_id, Bullet.text).filter(
            Bullet.experience_id.in_(owned)
        ):
            texts[eid].add(existing_text)
            counts[eid] += 1

    new_bullets: list[Bullet] = []
    for exp_id, text, pattern_kind in parsed:
        if exp_id not in owned:
            report.experiences_referenced_but_missing.append(exp_id)
            continue
        if text in texts[exp_id]:
            report.proposed_bullets_already_present += 1
            continue
        texts[exp_id].add(text)

        new_bullet = Bullet(
            experience_id=exp_id,
            text=text,
            # Use the last display_order in this experience + 1 (best effort)
            display_order=counts[exp_id],
            is_active=1,
            is_pending_review=1,
            source=source_value,
            pattern_kind=pattern_kind,
            has_outcome=0,  # user decides during review; deterministic check would override
        )
        counts[exp_id] += 1
        session.add(new_bullet)
        new_bullets.append(new_bullet)
        report.proposed_bullets_created += 1

    if not new_bullets:
        return
    session.flush()  # need each new_bullet.id for its proposal_review FK
    for new_bullet in new_bullets:
        session.add(
            ProposalReview(
                application_run_id=application_run.id,
                bullet_id=new_bullet.id,
                original_text=new_bullet.text,
                decision="pending",
                llm_critique_json=None,
                user_edited_text=None,
            )
        )
        report.proposal_reviews_created += 1
    session.flush()


# ---------------------------------------------------------------------------
# proposed_experience_titles → experience_title (pending) + proposal_review
# ---------------------------------------------------------------------------


def _persist_proposed_titles(
    session: Session,
    application_run: ApplicationRun,
    proposals: list[Any],
    candidate_id: int,
    report: PersistReport,
) -> None:
    """Each proposal: {experience_id, title, rationale}.

    `proposals` is typed `list[Any]`, not `list[dict[str, Any]]`, because each
    entry is untrusted LLM JSON — the `isinstance(entry, dict)` guard below is
    live defense against a malformed (non-dict) entry, not dead code.
    """
    source_value = f"llm_proposed:{application_run.run_id}"

    for entry in proposals:
        if not isinstance(entry, dict):
            report.skipped_due_to_malformed_payload += 1
            continue
        exp_id = _strip_id_prefix(entry.get("experience_id"), "e")
        title_text = (entry.get("title") or "").strip()
        if exp_id is None or not title_text:
            report.skipped_due_to_malformed_payload += 1
            continue

        experience = (
            session.query(Experience)
            .filter_by(
                id=exp_id,
                candidate_id=candidate_id,
            )
            .first()
        )
        if experience is None:
            report.experiences_referenced_but_missing.append(exp_id)
            continue

        # Don't duplicate: skip if a title with same text already exists on
        # this experience (whether official, alternate, or proposed).
        existing = (
            session.query(ExperienceTitle)
            .filter_by(
                experience_id=experience.id,
                title=title_text,
            )
            .first()
        )
        if existing is not None:
            continue

        new_title = ExperienceTitle(
            experience_id=experience.id,
            title=title_text,
            is_official=0,
            truthful_enough_to_use=0,  # pending review; user promotes if accurate
            is_pending_review=1,
            source=source_value,
            notes=(entry.get("rationale") or "")[:500],
        )
        session.add(new_title)
        session.flush()
        report.proposed_titles_created += 1

        session.add(
            ProposalReview(
                application_run_id=application_run.id,
                experience_title_id=new_title.id,
                original_text=title_text,
                decision="pending",
                llm_critique_json=None,
                user_edited_text=None,
            )
        )
        report.proposal_reviews_created += 1
    session.flush()


# ---------------------------------------------------------------------------
# Helpers: ownership + ID parsing
# ---------------------------------------------------------------------------


def _owned_experience_ids(session: Session, candidate_id: int, exp_ids: set[int]) -> set[int]:
    """The subset of `exp_ids` that belong to `candidate_id` — one query, not one per id."""
    if not exp_ids:
        return set()
    return {
        eid
        for (eid,) in session.query(Experience.id)
        .filter(Experience.candidate_id == candidate_id, Experience.id.in_(exp_ids))
        .all()
    }


def _strip_id_prefix(raw: object, expected_prefix: str) -> int | None:
    """Convert prompt-shaped IDs like 'e3' or 't12' or 'b41' into ints.

    Also accepts bare integers in case the LLM drops the prefix. Returns None
    on any failure (including empty/None input) so callers can record + skip.
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    if value.startswith(expected_prefix) and value[len(expected_prefix) :].isdigit():
        return int(value[len(expected_prefix) :])
    if value.isdigit():
        return int(value)
    return None


__all__ = ["PersistReport", "persist_corpus_generation", "persist_cover_letter_md"]
