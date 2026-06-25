"""DB-backed equivalent of `hardening.build_context_set`.

Phase B.1 contract: produce a ContextSet whose SHAPE matches the file-based
output exactly, so existing prompts (analyze, generate, clarify) work
unchanged. Only the data sourcing differs. Phase B.2 will change the prompt
structure itself (`<career_corpus>` block).

Also creates the `application` + `application_run` rows that anchor the
new audit chain, so subsequent phases can grow into them.

Synthesized resume text is reconstructed from active experiences + bullets
grouped by source provenance. The result reads like a real resume to the
LLM but is a deterministic projection from DB state, not the user's
original file text. supplemental_resumes is empty in DB-backed mode — the
unified corpus carries every framing already.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from analyzer import PROMPT_VERSION
from db.models import (
    Application,
    ApplicationRun,
    Bullet,
    Candidate,
    Certification,
    Education,
    Experience,
    ExperienceTitle,
    Skill,
)
from hardening import (
    ContextSet,
    CorpusBullet,
    CorpusEligibleTitle,
    CorpusExperience,
    check_ats_format,
    compute_keyword_overlap,
    extract_keywords,
)

logger = logging.getLogger(__name__)


def build_context_set_from_db(
    session: Session,
    *,
    candidate_username: str,
    jd_text: str,
    run_id: str,
    jd_url: str | None = None,
    application_title: str | None = None,
) -> tuple[ContextSet, Application, ApplicationRun]:
    """Construct a ContextSet from DB rows + create the application/run anchor.

    Returns (context_set, application_row, application_run_row). The caller
    is responsible for committing the session. The application_run carries
    `corpus_snapshot_json` populated by `_select_corpus_snapshot()` so future
    iterations of this application reuse the same bullet/title ID set.

    Behavior matches `build_context_set` in shape: the returned ContextSet
    has the same TypedDict keys with equivalent semantics. Differences:
    - `resume.text` is synthesized from DB bullets, not file-parsed
    - `resume.format` is "md" (the synthesized text uses markdown)
    - `resume.path` is "" (no file backs the synthetic text)
    - `supplemental_resumes` is always [] in DB-backed mode
    """
    candidate = session.query(Candidate).filter_by(username=candidate_username).first()
    if candidate is None:
        raise ValueError(f"No candidate with username={candidate_username!r}")

    experiences = list(
        session.execute(
            select(Experience)
            .where(Experience.candidate_id == candidate.id)
            .order_by(Experience.start_date.desc(), Experience.id)
        ).scalars()
    )
    skills = [
        s.name
        for s in session.execute(
            select(Skill).where(Skill.candidate_id == candidate.id).order_by(Skill.name)
        ).scalars()
    ]
    certifications = [
        c.name
        for c in session.execute(
            select(Certification)
            .where(Certification.candidate_id == candidate.id)
            .order_by(Certification.display_order, Certification.id)
        ).scalars()
    ]
    educations = list(
        session.execute(
            select(Education)
            .where(Education.candidate_id == candidate.id)
            .order_by(Education.display_order, Education.id)
        ).scalars()
    )

    resume_text = _synthesize_resume_markdown(
        experiences=experiences,
        skills=skills,
        certifications=certifications,
        educations=educations,
        candidate=candidate,
    )

    jd_keywords = extract_keywords(jd_text)
    resume_keywords = extract_keywords(resume_text)
    overlap = compute_keyword_overlap(resume_keywords, jd_keywords)
    ats_warnings = check_ats_format({"text": resume_text, "sections": []})

    jd_fingerprint = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()[:16]
    application = Application(
        candidate_id=candidate.id,
        title=application_title or _infer_application_title(jd_text),
        jd_text=jd_text,
        jd_url=jd_url,
        jd_fingerprint=jd_fingerprint,
        status="draft",
    )
    session.add(application)
    session.flush()

    snapshot = _select_corpus_snapshot(
        experiences,
        set(jd_keywords.get("keywords", {}).keys()),
    )

    application_run = ApplicationRun(
        application_id=application.id,
        iteration=0,
        parent_run_id=None,
        run_id=run_id,
        prompt_version=PROMPT_VERSION,
        persona_template_id=None,
        corpus_snapshot_json=snapshot,
    )
    session.add(application_run)
    session.flush()

    education_summary = _summarize_educations(educations)
    profile_text = candidate.profile_text or ""

    career_corpus = _build_career_corpus_payload(experiences)

    context_set: ContextSet = {
        "timestamp": application_run.created_at,
        "candidate": {
            "name": candidate.name or "",
            "email": candidate.email or "",
            "phone": candidate.phone or "",
            "linkedin_url": candidate.linkedin_url or "",
            "website_url": candidate.website_url or "",
            "skills": skills,
            "certifications": certifications,
            "education_summary": education_summary,
            "notes": candidate.notes or "",
            "profile_text": profile_text,
            # PX-02: cached opt-in profile/website/portfolio scrape. Rides the
            # saved context_set and is NOT mutated by _apply_chosen_summary, so
            # the analyze↔generate prefix stays byte-identical within an iteration.
            "online_profile_text": candidate.online_profile_text or "",
        },
        "resume": {
            "format": "md",
            "sections": [],
            "text": resume_text,
            "filename": f"<corpus snapshot {run_id}>",
            "path": "",
        },
        "supplemental_resumes": [],
        "job_description": jd_text,
        "deterministic_analysis": {
            "jd_keywords": jd_keywords,
            "resume_keywords": resume_keywords,
            "keyword_overlap": overlap,
            "ats_warnings": ats_warnings,
        },
        "run_id": run_id,
        "career_corpus": career_corpus,
    }
    return context_set, application, application_run


def eligible_titles_for(exp: Experience) -> list[CorpusEligibleTitle]:
    """Eligible titles for one experience, in snapshot order.

    Eligible = ``is_official=1 OR truthful_enough_to_use=1`` (the same filter the
    Compose GET and the generate snapshot use). Ordered official-first then by id.
    The single source of truth for the corpus snapshot's title set: reused by the
    analyze-time payload build (`_build_career_corpus_payload`) and the
    composition-save re-sync in `app.py`, so the two can never drift.
    """
    eligible: list[CorpusEligibleTitle] = [
        {"id": t.id, "title": t.title, "is_official": bool(t.is_official)}
        for t in exp.titles
        if t.is_official or t.truthful_enough_to_use
    ]
    eligible.sort(key=lambda t: (not t["is_official"], t["id"]))
    return eligible


def _build_career_corpus_payload(experiences: list[Experience]) -> list[CorpusExperience]:
    """Build the structured corpus the LLM consumes in the new prompt shape.

    Each experience carries:
    - id, company, location, dates
    - eligible_titles: every is_official=1 OR truthful_enough_to_use=1 title
      (so the LLM can pick the right framing per JD)
    - bullets: active bullets with id, text, tags, has_outcome, source

    Pending-review titles and bullets are INCLUDED so a freshly-imported user
    can use the pipeline before reviewing. Phase D's review UI will enforce
    review before "first real application" if needed.
    """
    payload: list[CorpusExperience] = []
    for exp in experiences:
        eligible_titles = eligible_titles_for(exp)

        bullets: list[CorpusBullet] = []
        for b in sorted(exp.bullets, key=lambda x: x.display_order):
            if not b.is_active:
                continue
            bullets.append(
                {
                    "id": b.id,
                    "text": b.text,
                    "tags": [],  # Phase B.2 doesn't surface tags yet; B.3 adds the join
                    "has_outcome": bool(b.has_outcome),
                    "source": b.source,
                }
            )

        payload.append(
            {
                "id": exp.id,
                "company": exp.company,
                "location": exp.location or "",
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "eligible_titles": eligible_titles,
                "bullets": bullets,
            }
        )
    return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthesize_resume_markdown(
    *,
    experiences: list[Experience],
    skills: list[str],
    certifications: list[str],
    educations: list[Education],
    candidate: Candidate,
) -> str:
    """Reconstruct a markdown resume from DB rows.

    Layout mirrors what the prompt expects (#/##/### headings + `-` bullets):
    a single combined resume capturing every active experience + bullet.
    Pending-review bullets are INCLUDED so a freshly-imported user can run
    the pipeline immediately — review state is a UI concern, not a
    pipeline-gating one.
    """
    parts: list[str] = []
    if candidate.name:
        parts.append(f"# {candidate.name}")
    contact_bits = [
        candidate.email or "",
        candidate.phone or "",
        candidate.linkedin_url or "",
        candidate.website_url or "",
    ]
    contact = " · ".join(b for b in contact_bits if b)
    if contact:
        parts.append(contact)
    parts.append("")
    parts.append("## Experience")

    for exp in experiences:
        official = _pick_official_title(exp.titles)
        active_bullets = sorted(
            (b for b in exp.bullets if b.is_active),
            key=lambda b: b.display_order,
        )
        if not official and not active_bullets:
            continue

        date_range = f"{exp.start_date} — {exp.end_date or 'Present'}"
        location = exp.location or ""
        title_part = official or "(role)"
        header = f"### {exp.company}, {title_part}"
        if location:
            header += f" — {location}"
        header += f" {date_range}"
        parts.append("")
        parts.append(header)
        for b in active_bullets:
            parts.append(f"- {b.text}")

    if skills:
        parts.append("")
        parts.append("## Skills")
        parts.append(", ".join(skills))

    if educations:
        parts.append("")
        parts.append("## Education")
        for ed in educations:
            line = ed.institution
            if ed.degree:
                line = f"{ed.degree}, {line}"
            date_part = " — ".join(d for d in (ed.start_date, ed.end_date) if d)
            if date_part:
                line += f" ({date_part})"
            parts.append(f"- {line}")

    if certifications:
        parts.append("")
        parts.append("## Certifications")
        for c in certifications:
            parts.append(f"- {c}")

    return "\n".join(parts)


def _pick_official_title(titles: Iterable[ExperienceTitle]) -> str:
    """Return the official title; failing that the first truthful-enough one; failing that ``""``."""
    for t in titles:
        if t.is_official:
            return t.title
    for t in titles:
        if t.truthful_enough_to_use:
            return t.title
    return ""


def _summarize_educations(educations: list[Education]) -> str:
    """Build a one-line summary matching the legacy `config.education_summary` shape so downstream code keeps working.

    Downstream code reads this as a single string.
    """
    if not educations:
        return ""
    return "; ".join(ed.institution for ed in educations)


_WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z+#.-]{1,}\b")


def _tokenize(text: str) -> set[str]:
    """Lowercase word set for overlap scoring (same shape as extract_keywords)."""
    return {w for w in _WORD_RE.findall((text or "").lower()) if len(w) > 2}


def score_corpus_bullet(
    text: str,
    has_outcome: bool,
    tag_values: list[str],
    jd_kw: set[str],
    essential: set[str] | None = None,
) -> float:
    """Score one bullet's fit against a JD deterministically (P1 hardening — no LLM).

    Higher = better fit. Used by the iteration-0 pre-filter AND
    the Compose-step composition endpoint so ranking is consistent.

    - essential-skill word overlap is weighted highest (2.0)
    - JD-keyword word overlap (1.0)
    - tag overlap vs JD ∪ essential, splitting hyphenated tags (1.5/tag)
    - measurable-outcome bonus (1.5)
    """
    essential = essential or set()
    toks = _tokenize(text)
    jd_overlap = len(toks & jd_kw)
    ess_overlap = len(toks & essential)
    tag_target = jd_kw | essential
    tag_hits = 0
    for tv in tag_values:
        parts = {p for p in (tv or "").lower().split("-") if len(p) > 2}
        if parts & tag_target:
            tag_hits += 1
    return 2.0 * ess_overlap + 1.0 * jd_overlap + 1.5 * tag_hits + (1.5 if has_outcome else 0.0)


def _bullet_tag_values(bullet: Bullet) -> list[str]:
    """Normalized tag values linked to a bullet (empty if none)."""
    out: list[str] = []
    for link in getattr(bullet, "tag_links", []) or []:
        tag = getattr(link, "tag", None)
        if tag is not None and tag.value:
            out.append(tag.value)
    return out


def _select_corpus_snapshot(
    experiences: list[Experience],
    jd_kw: set[str] | None = None,
    top_n: int = 30,
) -> str:
    """Pick the bullet/title ID set this application iteration will see.

    Workstream B: deterministic JD-aware pre-filter. Per experience, keep
    the top-N active bullets by `score_corpus_bullet` (tie-break on
    display_order for stability so the snapshot — and thus the cached
    prompt prefix — is reproducible). All eligible titles are kept (small
    set; the official title must never be dropped). When `jd_kw` is None
    (no JD context) every active bullet is kept, preserving prior behavior.
    """
    bullet_ids: list[int] = []
    title_ids: list[int] = []
    for exp in experiences:
        active = [b for b in exp.bullets if b.is_active]
        if jd_kw is None:
            chosen = sorted(active, key=lambda b: b.display_order)
        else:
            scored = sorted(
                active,
                key=lambda b: (
                    -score_corpus_bullet(
                        b.text,
                        bool(b.has_outcome),
                        _bullet_tag_values(b),
                        jd_kw,
                    ),
                    b.display_order,
                ),
            )
            chosen = scored[:top_n]
        bullet_ids.extend(b.id for b in chosen)
        for t in exp.titles:
            if t.is_official or t.truthful_enough_to_use:
                title_ids.append(t.id)
    return json.dumps({"bullet_ids": bullet_ids, "experience_title_ids": title_ids})


def _infer_application_title(jd_text: str) -> str:
    """Best-effort short label for the application card.

    Picks the first non-empty line up to 80 chars. The user can rename via
    the Applications tab (Phase D).
    """
    for line in jd_text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:80]
    return "Untitled application"


__all__ = ["build_context_set_from_db", "eligible_titles_for"]
