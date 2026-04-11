"""LLM pipeline — the fuzzy brain. P6 Specialized Review, P9 Token Economy.

Two API calls per run:
  Call 1: Analysis & Strategy (JD analysis, ideal resume, comparison, suggestions)
  Call 2: Generation (tailored resume + cover letter, proofread)

Uses specialist hiring-manager persona with domain vocabulary (P6).
Single agent + deterministic tools = Level 1 architecture (P9).
"""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

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
- Always prioritize keywords from the job description BECAUSE ATS systems rank by keyword match before human eyes see the resume"""

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


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
        parts.append(f"<resume_{i} filename=\"{fname}\">")
        parts.append(r.get("text", ""))
        parts.append(f"</resume_{i}>")
        parts.append("")
    parts.append("</supplemental_resumes>")
    return "\n".join(parts)


def _call_llm(client: anthropic.Anthropic, user_prompt: str) -> str:
    """Make a single LLM call. P7 Observability: log inputs/outputs."""
    logger.info("LLM call starting — prompt length: %d chars", len(user_prompt))
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text
    logger.info(
        "LLM call complete — input_tokens: %d, output_tokens: %d",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return text


def analyze(client: anthropic.Anthropic, context_set: dict) -> dict:
    """Call 1: Analysis & Strategy.

    Analyzes JD, generates ideal resume, compares, produces suggestions.
    Returns structured analysis result.
    """
    # P2 Context Hygiene: structured prompt, front-load constraints, back-load format
    prompt = f"""<task>Analyze this job description against the candidate's resume and profile. Produce a comprehensive strategic analysis.</task>

<job_description>
{context_set['job_description']}
</job_description>

<candidate_resume filename="{context_set['resume'].get('filename', 'primary')}">
{context_set['resume']['text']}
</candidate_resume>
{_supplemental_block(context_set)}
<candidate_profile>
Name: {context_set['candidate']['name']}
Skills: {', '.join(context_set['candidate'].get('skills', []))}
Certifications: {', '.join(context_set['candidate'].get('certifications', []))}
Education: {context_set['candidate'].get('education_summary', '')}
Notes: {context_set['candidate'].get('notes', '')}
</candidate_profile>

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

    raw = _call_llm(client, prompt)

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


def generate(client: anthropic.Anthropic, context_set: dict, analysis: dict) -> dict:
    """Call 2: Generation.

    Produces tailored resume content and cover letter.
    Includes proofreading pass.
    """
    prompt = f"""<task>Generate a tailored resume and cover letter for this candidate based on the analysis.</task>

<job_description>
{context_set['job_description']}
</job_description>

<original_resume filename="{context_set['resume'].get('filename', 'primary')}">
{context_set['resume']['text']}
</original_resume>
{_supplemental_block(context_set)}
<candidate_profile>
Name: {context_set['candidate']['name']}
Email: {context_set['candidate'].get('email', '')}
Phone: {context_set['candidate'].get('phone', '')}
LinkedIn: {context_set['candidate'].get('linkedin_url', '')}
Website: {context_set['candidate'].get('website_url', '')}
</candidate_profile>

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

<output_format>
Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "resume_content": "The complete tailored resume as plain text with markdown formatting for structure",
  "cover_letter_content": "The complete cover letter as plain text",
  "changes_made": ["change1", "change2"],
  "proofread_notes": ["Any grammar, spelling, or formatting issues found and fixed"]
}}
</output_format>"""

    raw = _call_llm(client, prompt)

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
