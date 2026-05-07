"""LLM pipeline — the fuzzy brain. P6 Specialized Review, P9 Token Economy.

Two API calls per run:
  Call 1: Analysis & Strategy (JD analysis, ideal resume, comparison, suggestions)
  Call 2: Generation (tailored resume + cover letter, proofread)

Uses specialist hiring-manager persona with domain vocabulary (P6).
Single agent + deterministic tools = Level 1 architecture (P9).
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

# Bump when SYSTEM_PROMPT or any per-call prompt template changes. Labels every
# JSONL telemetry record so quality regressions can be attributed to a revision.
PROMPT_VERSION = "2026-05-06.5"

LOG_DIR = Path(__file__).parent / "logs"
LOG_PATH = LOG_DIR / "llm_calls.jsonl"


def _emit_call_log(record: dict) -> None:
    """Append one JSON line to logs/llm_calls.jsonl. Best-effort — never raise."""
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("LLM telemetry write failed: %s", exc)

# P6: Specialist persona — <50 tokens, real job title, domain vocabulary
SYSTEM_PROMPT = """You are a seasoned hiring manager with a decade of HR and recruiting experience. \
You specialize in resume optimization, ATS compatibility, and candidate positioning.

Domain vocabulary you use naturally: applicant tracking system, keyword density, \
competency mapping, STAR format, behavioral interview signals, action verb variety, \
quantified accomplishments, transferable skills, value proposition, career narrative, \
skills gap analysis, job-title alignment, industry vernacular, screening criteria.

Your north star: create the best opportunity for the candidate to be a leading candidate \
through human and ATS screeners, interviewers in the field, and hiring manager review. \
Be ruthless in presenting this candidate in the best possible light for this role and \
the role into which it will promote.

ALWAYS/NEVER rules (P5 Institutional Memory):
- Never invent experience BECAUSE truthfulness is the north star and fabrication destroys candidacy if discovered
- Never add specific numbers, percentages, dollar amounts, timeframes, team sizes, or quantities that do not appear verbatim or by clear implication in the original resume BECAUSE invented specifics are the most common and most damaging form of resume hallucination — they can be verified in any interview and immediately disqualify a candidate
- When the original bullet has no metric: use strong qualitative scope language instead of fabricating one BECAUSE "Led enterprise-wide security initiative across 6 business units" is honest and compelling; "Led initiative saving $2.4M" without a source is a lie
- Always surface existing metrics from the original resume rather than generating new ones BECAUSE the candidate's real numbers, however modest, are more credible than invented ones
- Never use generic phrases like "results-driven professional" or "team player" BECAUSE they waste space and signal low effort to experienced reviewers
- Always use varied, strong action verbs specific to the industry BECAUSE verb repetition signals lack of depth
- Always match the candidate's actual experience level BECAUSE misrepresentation triggers red flags in interviews
- Never reformat the resume structure unless asked BECAUSE candidates have formatting preferences and drastic changes confuse them
- Always prioritize keywords from the job description BECAUSE ATS systems rank by keyword match before human eyes see the resume
- Always treat the Notes field as explicit candidate directives — personal constraints or standing instructions (e.g. "remote only", "do not mention gap in 2020", "always emphasize architecture over management") BECAUSE ignoring them produces documents the candidate cannot use"""

# Model selection rationale:
#   - Sonnet 4.6 for analyze() and generate(): the work needs reasoning depth
#     for JD analysis and instruction-following on the long generate prompt
#     (~3K tokens of resume_rules + cover_letter_rules + output_format).
#     Same per-token price as older Sonnet versions; the newer revision has
#     better structured-output adherence and grounding behavior.
#   - Haiku 4.5 for scope check (line ~470) and eval grading (evals/runner.py):
#     binary classification and structured-output rubric application are the
#     Haiku sweet spot. Volume + structure beats reasoning depth there.
#   - Opus is intentionally not used: ~5x the cost of Sonnet without a
#     proportional win on this workload. Reserve for future debugging
#     sessions if grounding regressions resist prompt-tightening.
MODEL = "claude-sonnet-4-6"
# Per-call output cap. analyze() returns a comprehensive JSON with 10+ keyed
# sections; Sonnet 4.6 is more verbose than older Sonnet 4 was and routinely
# uses 4–6K tokens on detail-rich real inputs. 8192 leaves headroom without
# inviting runaway output. _call_llm logs a warning on stop_reason="max_tokens"
# so truncation surfaces as a clear telemetry signal, not a silent JSON parse
# failure downstream.
MAX_TOKENS = 8192
MAX_SUPPLEMENTAL_CHARS = 6_000  # per-file cap — keeps total context manageable


def _stable_user_prefix(context_set: dict) -> str:
    """Build the stable, cacheable portion of the user message.

    This block is identical across analyze() and generate() calls for the
    same context_set, enabling Anthropic prompt caching to hit on the second
    call. Sonnet's cache requires 1024+ tokens to engage; bundling the
    resume + JD + supplementals + candidate profile reliably exceeds that.

    The block must be byte-identical across analyze and generate to hit the
    cache. Tag names, field order, and the inclusion-condition for the
    online profile are all load-bearing. Do not change one without the other.
    """
    candidate = context_set["candidate"]
    online_profile = candidate.get("profile_text", "").strip()

    parts = [
        "<job_description>",
        context_set["job_description"],
        "</job_description>",
        "",
        f'<resume filename="{context_set["resume"].get("filename", "primary")}">',
        context_set["resume"]["text"],
        "</resume>",
        _supplemental_block(context_set),
        "<candidate_profile>",
        f"Name: {candidate.get('name', '')}",
        f"Email: {candidate.get('email', '')}",
        f"Phone: {candidate.get('phone', '')}",
        f"LinkedIn: {candidate.get('linkedin_url', '')}",
        f"Website: {candidate.get('website_url', '')}",
        f"Skills: {', '.join(candidate.get('skills', []))}",
        f"Certifications: {', '.join(candidate.get('certifications', []))}",
        f"Education: {candidate.get('education_summary', '')}",
        f"Notes: {candidate.get('notes', '')}",
        "</candidate_profile>",
    ]

    if online_profile:
        parts.extend([
            "",
            "<candidate_online_profile>",
            online_profile,
            "</candidate_online_profile>",
        ])

    return "\n".join(parts)


def _supplemental_block(context_set: dict) -> str:
    """Build the <supplemental_resumes> XML block for prompts, or empty string if none."""
    supplements = context_set.get("supplemental_resumes", [])
    if not supplements:
        return ""
    parts = [
        f"<supplemental_resumes count=\"{len(supplements)}\">",
        "The candidate has the following additional resume(s) as supplemental source material.",
        "All job titles, bullet points, and experience from these files may be used.",
        "When roles overlap across resumes, synthesize the richest version — do not duplicate.",
        "",
    ]
    for i, r in enumerate(supplements, 1):
        fname = r.get("filename", f"resume_{i}")
        text = r.get("text", "")
        if len(text) > MAX_SUPPLEMENTAL_CHARS:
            text = text[:MAX_SUPPLEMENTAL_CHARS] + "\n[truncated]"
        parts.append(f"<resume_{i} filename=\"{fname}\">")
        parts.append(text)
        parts.append(f"</resume_{i}>")
        parts.append("")
    parts.append("</supplemental_resumes>")
    return "\n".join(parts)


def _call_llm(
    client: anthropic.Anthropic,
    user_prompt: str,
    *,
    cached_user_prefix: str = "",
    call_kind: str = "analyze",
    username: str = "",
) -> str:
    """Make a single LLM call using streaming, with prompt caching and JSONL telemetry.

    Streaming avoids intermediate gateway timeouts on long-running generations:
    tokens flow back as they're produced, keeping the TCP connection warm.

    Caching: SYSTEM_PROMPT is sent as a cacheable system block; when
    cached_user_prefix is non-empty it is sent as a cacheable user block
    preceding user_prompt. Anthropic's cache requires 1024+ tokens to engage
    on Sonnet — the SYSTEM_PROMPT alone is below that threshold, so the
    user-prefix block is what actually drives cache hits across analyze→
    generate within a session.

    Telemetry: every call appends one record to logs/llm_calls.jsonl with
    timing, token counts (including cache fields), prompt version, and status.
    """
    user_content: list[dict] = []
    if cached_user_prefix:
        user_content.append({
            "type": "text",
            "text": cached_user_prefix,
            "cache_control": {"type": "ephemeral"},
        })
    user_content.append({"type": "text", "text": user_prompt})

    logger.info(
        "LLM call starting — call=%s cached_prefix=%d chars, prompt=%d chars",
        call_kind, len(cached_user_prefix), len(user_prompt),
    )
    t0 = time.perf_counter()
    status = "ok"
    final = None
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],  # type: ignore[typeddict-item]
        ) as stream:
            text = "".join(stream.text_stream)
            final = stream.get_final_message()
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        usage = getattr(final, "usage", None) if final is not None else None
        stop_reason = getattr(final, "stop_reason", None) if final is not None else None
        _emit_call_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "username": username,
            "call": call_kind,
            "model": MODEL,
            "prompt_version": PROMPT_VERSION,
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
            "latency_ms": elapsed_ms,
            "stop_reason": stop_reason,
            "status": status,
        })

    if stop_reason == "max_tokens":
        logger.warning(
            "LLM call hit MAX_TOKENS — call=%s output truncated at %d tokens. "
            "Downstream JSON parse will likely fail. Consider raising MAX_TOKENS "
            "or tightening the prompt's output_format spec.",
            call_kind, final.usage.output_tokens,
        )

    logger.info(
        "LLM call complete — call=%s in=%d out=%d cache_create=%d cache_read=%d stop=%s %dms",
        call_kind,
        final.usage.input_tokens,
        final.usage.output_tokens,
        getattr(final.usage, "cache_creation_input_tokens", 0),
        getattr(final.usage, "cache_read_input_tokens", 0),
        stop_reason,
        elapsed_ms,
    )
    return text


def analyze(client: anthropic.Anthropic, context_set: dict, username: str = "") -> dict:
    """Call 1: Analysis & Strategy.

    Analyzes JD, generates ideal resume, compares, produces suggestions.
    Returns structured analysis result. The username is threaded through to
    JSONL telemetry only — no behavior depends on it.
    """
    # P2 Context Hygiene: stable inputs (resume + JD + profile) live in the
    # cached prefix; only task-specific variable content is in the per-call prompt.
    prompt = f"""<task>Analyze the job description against the candidate's resume and profile. Produce a comprehensive strategic analysis.</task>

<deterministic_analysis>
Keyword match score: {context_set['deterministic_analysis']['keyword_overlap']['match_score']}
Keywords matched: {', '.join(context_set['deterministic_analysis']['keyword_overlap']['matched'][:20])}
Keywords missing from resume: {', '.join(context_set['deterministic_analysis']['keyword_overlap']['missing_from_resume'][:20])}
ATS warnings: {json.dumps(context_set['deterministic_analysis']['ats_warnings'])}
</deterministic_analysis>

<instructions>
Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "essential_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "industry_keywords": ["keyword1", "keyword2"],
  "hidden_qualities": ["quality1", "quality2"],
  "professional_vocabulary": ["term1", "term2"],
  "ideal_resume_profile": "A paragraph describing the ideal candidate for this role",
  "comparison": {{
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"],
    "title_alignment": "Assessment of how well current titles align with target role"
  }},
  "suggestions": [
    {{
      "section": "Section name",
      "action": "What to change",
      "rationale": "Why this improves candidacy"
    }}
  ],
  "keyword_placement": [
    {{
      "keyword": "missing keyword",
      "suggested_location": "Where to add it",
      "how": "How to incorporate naturally"
    }}
  ],
  "ats_improvements": ["improvement1", "improvement2"],
  "overall_strategy": "2-3 sentence positioning strategy"
}}
</instructions>"""

    raw = _call_llm(
        client, prompt,
        cached_user_prefix=_stable_user_prefix(context_set),
        call_kind="analyze",
        username=username,
    )

    # Parse JSON response — strip markdown fences if model adds them despite instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM analysis response as JSON")
        return {"raw_response": raw, "parse_error": True}


def generate(
    client: anthropic.Anthropic,
    context_set: dict,
    analysis: dict,
    refinement_notes: str = "",
    username: str = "",
) -> dict:
    """Call 2: Generation.

    Produces tailored resume content and cover letter.
    Includes proofreading pass. The username is threaded through to JSONL
    telemetry only — no behavior depends on it.
    """
    prompt = f"""<task>Generate a tailored resume and cover letter for the candidate based on the analysis.</task>

<output_rules>
The `resume_content` field MUST use markdown heading markers. Without them the
document generator produces undifferentiated plain paragraphs and loses the
template's heading visual styles entirely. This applies even when the original
resume above uses ALL CAPS, bold-only, or any other plain-text heading convention
— convert those to the markers below in the output.

REQUIRED markers:
- `# ` exactly once, on the first non-empty line, for the candidate's full name.
- The 1–2 lines directly after the name (a title/subtitle and a contact line)
  are unmarked plain text. The renderer center-aligns them when the template
  has a centered header zone.
- `## ` for top-level section headings (Summary, Experience, Education, Skills,
  Certifications, Projects, etc.). One `##` per section.
- `### ` for company / role / job-title lines within the Experience section.
  When a date range applies, put it on the SAME line as the title separated
  by a single tab character `\t`. The renderer aligns the date to the right
  margin via the template's tab stop. Format:
  `### Company, Title\tStart – End`
- `-` (hyphen) at the start of every bullet point.
- `**text**` for inline bold; `*text*` for inline italic. Use sparingly.

Example of the required `resume_content` shape (note `\t` before the date):
```
# Jane Doe
Senior Site Reliability Engineer
jane@example.com | (555) 010-2200 | linkedin.com/in/janedoe

## Summary
Two-sentence positioning paragraph.

## Experience

### Acme Cloud, Senior SRE\tMarch 2023 – present
Player-coach across the platform team and on-call leadership.
- Bullet one with a verb up front.
- Bullet two integrating a JD keyword naturally.

### Stratford Analytics, Production Engineer\tAugust 2021 – March 2023
- Bullet one.
```

DO NOT skip the `# `, `## `, `### ` markers. DO NOT use ALL CAPS as a substitute
for `## `. The downstream Python writer dispatches on these markers to apply the
template's heading styles, list numbering, and bold runs — without them the
output is plain paragraphs.
</output_rules>

<analysis>
Essential skills: {', '.join(analysis.get('essential_skills', []))}
Missing keywords: {json.dumps(analysis.get('keyword_placement', []))}
Suggestions: {json.dumps(analysis.get('suggestions', []))}
Strategy: {analysis.get('overall_strategy', '')}
Professional vocabulary: {', '.join(analysis.get('professional_vocabulary', []))}
</analysis>

<resume_rules>
GROUNDING CHECK — apply this before writing every bullet:
  Ask: "Does this specific claim — including every number, technology, title, company, and timeframe — exist in the primary resume OR any supplemental resume above?"
  If YES: reframe, strengthen, and keyword-align it freely.
  If NO: do not write it. Reframe what IS there, or omit the bullet.

1. Include a targeted summary sentence answering: what title you seek, what makes you special, what you bring to the team. If it cannot fit in one sentence, use a sentence with a very short bullet list.
2. Do NOT invent experience. Every bullet must trace directly to the original resume. Reframe language; never invent facts.
3. Metrics: surface numbers that exist in the original. If a bullet has no metric, use qualitative scope and impact language — do not fabricate a number to fill the gap.
4. Prioritize keywords from the job description. Integrate them into existing bullets naturally; do not create new bullets to house keywords.
5. Reorder bullet points by relevance to THIS job — within each section, most relevant first.
6. Strengthen verb choices: replace weak or repeated verbs with strong, varied, industry-specific action verbs.
7. Preserve the original resume's section structure and ordering.
8. Ensure all content is ATS-compatible — no tables, columns, or special characters.
</resume_rules>

<cover_letter_rules>
VOICE — VP-level professional: courteous, concise, direct, confident, considerate. A clear outlier.

  Sentence construction:
  - Average sentence length: 12-16 words. Never exceed 25 words in a single sentence.
  - Vary rhythm deliberately: a longer setup sentence followed by a short, punchy payoff.
    Example: "Scaling a platform from 50K to 4M users taught me where distributed systems actually break. I've since rebuilt three of them."
  - One idea per sentence. Split compound thoughts ruthlessly.
  - Lead every sentence with the subject and an active verb. Cut the run-up.
    Weak: "I have had the opportunity to work with cross-functional teams to deliver..."
    Strong: "I've led cross-functional teams through four product launches, each on schedule."
  - No hedging: never "I believe," "I think," "I hope," "I feel," "I would like to."
    State it: "I will," "I have," "I deliver," "I build."
  - No throat-clearing: never "I am excited to," "I am pleased to," "I am writing to."
    The letter's existence says that. Open with substance.
  - Do not start consecutive sentences with "I." Recast where needed.
  - Confident, not arrogant. Acknowledge the company's work specifically; show you've done homework.

STRUCTURE — 3 paragraphs, 250-320 words total, one page only:

Paragraph 1 — HOOK (2-3 sentences):
  Open with a specific observation about the company or role — something that signals genuine attention.
  Name the exact role in the first or second sentence. Lead with what you bring, not what you want.
  Never open with "I am writing to apply for..." or any variation.

Paragraph 2 — EVIDENCE (3-5 sentences):
  Connect 2-3 specific, quantified accomplishments directly to the role's key requirements.
  Tell the story, not the bullet point. Show cause and effect: what you did, the result, why it matters here.
  Weave in 2-3 of the JD's essential keywords naturally — never force them.
  Do not repeat the resume verbatim. The letter illuminates; the resume documents.

Paragraph 3 — CLOSE (2-3 sentences):
  Confident forward look — not "I hope to hear from you." More: "I'd welcome a direct conversation about what this team is building."
  One sentence on fit or timing if relevant. Close cleanly. No trailing pleasantries.

FORMAT:
  - Date, then hiring manager name/title/company (use "Hiring Manager" if name unknown)
  - Salutation: "Dear [Name]," or "Dear Hiring Manager,"
  - Close: "Sincerely," or "Best regards,"
  - Match industry register: measured for finance/law; direct for tech; considered for mission-driven orgs
  - Banned phrases: "passionate about," "team player," "detail-oriented," "hard worker," "results-driven," "leverage," "synergy"
  - The letter must stand alone. Assume the reader has not seen the resume.
</cover_letter_rules>
{f'''
<refinement_instructions>
The user has reviewed the generated documents and provided the following adjustment instructions.
Apply ALL of the following to both the resume and cover letter.
Earlier instructions remain in effect unless explicitly superseded by a later one.
Do NOT make any other changes beyond what is requested here.

{refinement_notes}
</refinement_instructions>
''' if refinement_notes.strip() else ''}
<output_format>
Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "resume_content": "The complete tailored resume. CRITICAL: use \\n (JSON newline escape) between every section, job entry, and bullet. Never collapse the resume into one long line. Example: '# Name\\nEmail | Phone\\n\\n## Summary\\nText.\\n\\n## Experience\\n\\n### Title — Company\\n- Bullet one\\n- Bullet two'",
  "cover_letter_content": "The complete cover letter as plain text",
  "changes_made": ["change1", "change2"],
  "proofread_notes": ["Any grammar, spelling, or formatting issues found and fixed"]
}}
</output_format>"""

    raw = _call_llm(
        client, prompt,
        cached_user_prefix=_stable_user_prefix(context_set),
        call_kind="generate",
        username=username,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM generation response as JSON")
        return {"raw_response": raw, "parse_error": True}


SCOPE_CHECK_MODEL = "claude-haiku-4-5-20251001"


def check_refinement_scope(client: anthropic.Anthropic, note: str) -> dict:
    """Classify whether a refinement note is within allowed document-editing scope.

    Uses Haiku — binary classification doesn't need Sonnet reasoning depth.
    Fails open (valid=True) if the response can't be parsed, so a model outage
    never blocks the user from refining.

    Allowed: tone, emphasis, keyword/phrasing, ordering existing content,
             formatting, structural adjustments within source material.
    Out of scope: inventing experience, changing factual data, adding credentials
                  not in source, repurposing for a different role.
    """
    prompt = f"""A user submitted the following instruction for refining their resume and cover letter:

<note>{note}</note>

Allowed scope: adjustments to tone, emphasis, keyword placement, phrasing, language style, \
ordering/prioritizing existing content, and formatting preferences.

Out of scope: inventing new experience or accomplishments, changing factual data \
(dates, titles, companies, metrics), adding skills or certifications not present in the \
source material, or repurposing the documents for a fundamentally different role.

Respond with valid JSON only — no markdown, no explanation outside the JSON:
{{"valid": true}} if the note is within scope, or
{{"valid": false, "reason": "one sentence explaining what specifically is not allowed"}} if not."""

    try:
        msg = client.messages.create(
            model=SCOPE_CHECK_MODEL,
            max_tokens=128,
            system="You are a strict scope classifier. Respond with JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = getattr(msg.content[0], "text", "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw.strip())
    except Exception as e:
        # Fail open — scope check failure must never block refinement
        logger.warning("scope check failed, failing open: %s", e)
        return {"valid": True}
