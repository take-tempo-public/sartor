/* Frontend logic — vanilla JS, fetch API.
   P8 Human Gate: workflow enforces review at two points.

   Naming conventions (docs/RELEASE_CHECKLIST.md A.3):
   - Public functions (called from HTML onclick OR from other modules):
       camelCase, no leading underscore (`loadUsers`, `wizardGoTo`,
       `setStatus`). The onclick handlers in templates/index.html are
       the binding contract.
   - Private helpers (used only within this file):
       _camelCase with a leading underscore (`_wizardRender`,
       `_toSentence`, `_fireRecommendThenCompose`).
   - Documented exceptions still without the underscore for historical
       reasons: `esc`, `show`, `hide`, `hideAllPanels` — heavy internal
       callsites; renaming filed under a future cleanup pass.
   - Constants: UPPER_SNAKE_CASE with a leading underscore for module-
       private (`_ACTIVE_PANEL`, `_WIZARD_PANELS`, `_WIZARD_STEP_LABELS`).
   - DOM-element IDs: camelCase (`statusPill`, `userSelect`,
       `cbStatusbar`).
   - CSS classes referenced from JS: kebab-case (`cb-wordmark`,
       `wizard-step`, `is-active`).
*/

let currentUser = '';
let currentConfig = {};
let lastContextPath = '';
let lastResumePath = '';
let lastCoverLetterPath = '';
let lastResumeFormat = '.docx';
let lastTemplatePath = '';   // path to original .docx for style template
let outputFormat = '.docx';  // user-selected output format
let primaryResume = '';      // currently selected primary resume filename
let refinementHistory = [];  // accumulated refinement instructions, in order
let lastClarifyQuestions = []; // questions returned by the most recent /api/clarify call
// --- Iteration loop state -------------------------------------------------
let currentIteration = 0;          // matches context_set.iteration on the server
let lastGeneratedResume = '';      // frozen copy of the LLM's last resume_content
let lastGeneratedCoverLetter = ''; // frozen copy of the LLM's last cover_letter_content
let lastIterateClarifyQuestions = []; // most recent /api/iterate-clarify questions

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  loadUsers();
  setupDropZone();
  document.getElementById('userSelect').addEventListener('change', onUserSelect);
  document.getElementById('refinementInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submitRefinement(); }
  });

  // callback. top bar — drop a soft shadow once scrolled past 4px. Cheap
  // affordance that says "this bar is anchored above the scroll surface."
  // Idempotent: harmless if #cbTopbar isn't in the DOM.
  const cbBar = document.getElementById('cbTopbar');
  if (cbBar) {
    const onScroll = () => {
      cbBar.classList.toggle('is-scrolled', window.scrollY > 4);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
});

// ---- Users ----
async function loadUsers() {
  const res = await fetch('/api/users');
  const users = await res.json();
  const sel = document.getElementById('userSelect');
  sel.innerHTML = '<option value="">-- Select User --</option>';
  users.forEach(u => {
    const opt = document.createElement('option');
    opt.value = u;
    opt.textContent = u;
    sel.appendChild(opt);
  });
}

function showNewUserForm() {
  document.getElementById('newUserForm').classList.toggle('hidden');
}

async function createUser() {
  const data = {
    username: document.getElementById('newUsername').value.trim(),
    name: document.getElementById('newName').value.trim(),
    email: document.getElementById('newEmail').value.trim(),
    phone: document.getElementById('newPhone').value.trim(),
    linkedin_url: document.getElementById('newLinkedin').value.trim(),
    website_url: document.getElementById('newWebsite').value.trim(),
  };
  if (!data.username) return alert('Username required');

  const res = await fetch('/api/users', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    return alert(err.error || 'Failed to create user');
  }
  document.getElementById('newUserForm').classList.add('hidden');
  await loadUsers();
  document.getElementById('userSelect').value = data.username;
  onUserSelect();
}

async function onUserSelect() {
  const username = document.getElementById('userSelect').value;
  if (!username) {
    currentUser = '';
    hideAllPanels();
    _resetIterationState();
    return;
  }
  currentUser = username;
  await loadConfig();
  show('panelApplications');
  // panelConfig moved to the Settings drawer (Workstream B1.3); no longer
  // a flow panel. loadConfig() still populates the same #cfgX inputs
  // because the drawer hosts them via the same ids.
  _resetIterationState();
  setStatus('READY');
  refreshApplications();
  _loadPersonaOptions();
  wizardInit();
}

// Reset all iteration-loop state. Called when switching users or starting a
// fresh analysis — prevents stale lastGenerated* from gating edit-detection
// against the wrong baseline.
function _resetIterationState() {
  currentIteration = 0;
  lastGeneratedResume = '';
  lastGeneratedCoverLetter = '';
  refinementHistory = [];
  _updateIterationPill();
  // Refinement history UI hides itself when array is empty
  const rh = document.getElementById('refinementHistory');
  if (rh) { rh.classList.add('hidden'); rh.textContent = ''; }
}

// ---- Config ----
async function loadConfig() {
  const res = await fetch(`/api/users/${currentUser}/config`);
  if (!res.ok) return;
  currentConfig = await res.json();
  document.getElementById('cfgName').value = currentConfig.name || '';
  document.getElementById('cfgEmail').value = currentConfig.email || '';
  document.getElementById('cfgPhone').value = currentConfig.phone || '';
  document.getElementById('cfgLinkedin').value = currentConfig.linkedin_url || '';
  document.getElementById('cfgWebsite').value = currentConfig.website_url || '';
  document.getElementById('cfgSkills').value = (currentConfig.skills || []).join(', ');
  document.getElementById('cfgCerts').value = (currentConfig.certifications || []).join(', ');
  document.getElementById('cfgEducation').value = currentConfig.education_summary || '';
  document.getElementById('cfgNotes').value = currentConfig.notes || '';
  document.getElementById('cfgPortfolioUrls').value = (currentConfig.portfolio_urls || []).join('\n');
}

async function saveConfig() {
  const config = {
    name: document.getElementById('cfgName').value,
    email: document.getElementById('cfgEmail').value,
    phone: document.getElementById('cfgPhone').value,
    linkedin_url: document.getElementById('cfgLinkedin').value,
    website_url: document.getElementById('cfgWebsite').value,
    portfolio_urls: document.getElementById('cfgPortfolioUrls').value.split('\n').map(s => s.trim()).filter(Boolean),
    ...(currentConfig.included_resumes !== undefined
      ? { included_resumes: currentConfig.included_resumes }
      : {}),
    skills: document.getElementById('cfgSkills').value.split(',').map(s => s.trim()).filter(Boolean),
    certifications: document.getElementById('cfgCerts').value.split(',').map(s => s.trim()).filter(Boolean),
    education_summary: document.getElementById('cfgEducation').value,
    notes: document.getElementById('cfgNotes').value,
  };
  const res = await fetch(`/api/users/${currentUser}/config`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(config),
  });
  if (res.ok) {
    currentConfig = config;
    setStatus('CONFIG SAVED');
  } else {
    const err = await res.json();
    alert((err.errors || []).join('\n') || 'Failed to save config');
  }
}

// ---- Resume Upload ----
function setupDropZone() {
  const zone = document.getElementById('dropZone');
  const input = document.getElementById('fileInput');
  // Workstream B1 removed the Application-tab Corpus panel; the dropzone
  // now lives in the Career Corpus tab as the inline `+ DROP RESUME`
  // button (a different element id, wired via its own onchange).
  // setupDropZone() is kept as a defensive no-op so an absent #dropZone
  // doesn't throw — that would break the DOMContentLoaded chain, which
  // also wires the userSelect change handler (i.e. "nothing happens
  // when you pick a name").
  if (!zone || !input) return;

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => {
    if (input.files.length) uploadFile(input.files[0]);
  });
}

// Step 1 — drop a resume to extract its experiences into the corpus.
// (Workstream E: the legacy primary/supplemental chip selection is gone;
// the DB corpus is the single source of truth.)
async function uploadFile(file) {
  if (!currentUser) return alert('Select a user first');
  const out = document.getElementById('ingestResult');
  const fd = new FormData();
  fd.append('file', file);

  setStatus('INGESTING');
  if (out) out.textContent = `Extracting experiences from ${file.name}… (AI, ~$0.02)`;
  let res;
  try {
    res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/corpus/ingest-resume`,
      { method: 'POST', body: fd },
    );
  } catch (e) {
    return reportError('Corpus ingest', 'Upload request failed', e.message);
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 409 && data.needs_onboarding) {
    setStatus('READY');
    if (out) out.textContent = '';
    return openOnboardingModal(() => uploadFile(file));
  }
  if (!res.ok) {
    if (out) out.textContent = '';
    return reportError('Corpus ingest', data.error || 'Ingest failed', data.detail);
  }
  setStatus('READY');
  const made = data.experiences_created || 0;
  const merged = data.experiences_merged || 0;
  const bullets = data.bullets_created || 0;
  if (out) {
    out.textContent =
      `Added ${made} experience(s), ${merged} merged, ${bullets} bullet(s) — ` +
      `now pending review in the CAREER CORPUS tab.`;
  }
  _toast('Resume ingested into corpus');
  _corpusLoadedForUser = '';  // force corpus tab refetch next visit
}

function setOutputFormat(fmt, btn) {
  outputFormat = fmt;
  document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ---- Analysis (P8 Gate #1) ----
async function runAnalysis() {
  // DB-backed pipeline: the corpus is the source of truth. resume_filename
  // is ignored server-side (Phase C.4); no primary-resume gate anymore.
  const jd = document.getElementById('jdText').value.trim();
  if (!currentUser) return alert('Select a user first');
  if (!jd) return alert('Paste a job description');

  setStatus('ANALYZING');
  document.getElementById('btnAnalyze').disabled = true;
  _resetClarifyUI();
  // Surface the in-flight state inside panelAnalysis: show the pending
  // placeholder, hide the Continue/Skip action row (clicking those
  // mid-flight previously fired "Run ANALYZE first"). The status pill
  // at the top also pulses amber via setStatus('ANALYZING').
  document.getElementById('analysisPending')?.classList.remove('hidden');
  document.getElementById('analysisActions')?.classList.add('hidden');
  document.getElementById('analysisContent').innerHTML = '';
  // Fresh analysis starts a new iteration chain — drop stale baselines so
  // edit-detection doesn't compare the next generation's preview against a
  // prior run's lastGenerated* snapshot.
  _resetIterationState();

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: currentUser,
        job_description: jd,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (_needsOnboarding(res, data)) {
        document.getElementById('btnAnalyze').disabled = false;
        return openOnboardingModal(runAnalysis);
      }
      return reportError('Analyze', data.error || 'Analysis failed', data.detail);
    }
    lastContextPath = data.context_path;
    lastTemplatePath = data.template_path || '';
    _composeApplicationId = data.application_id ?? null;
    _renderAnalysis(data);
    show('panelAnalysis');
    // Reveal the Continue/Skip actions now that the analysis has
    // landed and lastContextPath is populated (so wizardGoTo(2/3)
    // passes _wizardReachable). Hide the in-flight placeholder.
    document.getElementById('analysisPending')?.classList.add('hidden');
    document.getElementById('analysisActions')?.classList.remove('hidden');
    setStatus('ANALYSIS COMPLETE');
    _announce('Analysis complete. Review it, then continue to clarify or skip to compose.');
    // Workstream B1 reorder: recommend no longer fires here. It fires
    // after the user submits or skips clarify (Step 2), so the
    // clarifications can inform the recommendation.
  } catch (e) {
    reportError('Analyze', 'Analysis request failed', e.message);
  } finally {
    document.getElementById('btnAnalyze').disabled = false;
    // Always clear the in-flight placeholder even if analyze errored —
    // leaving "Analyzing…" up after a failure would be misleading. The
    // actions row stays gated on lastContextPath (only the success path
    // above un-hides it).
    document.getElementById('analysisPending')?.classList.add('hidden');
  }
}

function _renderAnalysis(data) {
  const a = data.analysis;
  const d = data.deterministic;
  const el = document.getElementById('analysisContent');

  if (a.parse_error) {
    el.innerHTML = `<div class="warning">LLM returned non-JSON response. Raw output below:</div><pre>${esc(a.raw_response)}</pre>`;
    return;
  }

  let html = '';

  // Keyword overlap score
  const score = d.keyword_overlap.match_score;
  const pct = Math.round(score * 100);
  const color = pct > 60 ? 'var(--success)' : pct > 35 ? 'var(--brand)' : 'var(--danger)';
  html += `<div class="analysis-section">
    <h3>Keyword Match Score: ${pct}%</h3>
    <div class="score-bar"><div class="score-fill" style="width:${pct}%;background:${color}"></div></div>
  </div>`;

  // ATS Warnings
  if (d.ats_warnings.length) {
    html += `<div class="analysis-section"><h3>ATS Warnings</h3>`;
    d.ats_warnings.forEach(w => { html += `<div class="warning">${esc(w)}</div>`; });
    html += `</div>`;
  }

  // Essential Skills
  if (a.essential_skills) {
    html += `<div class="analysis-section"><h3>Essential Skills</h3><div>`;
    a.essential_skills.forEach(s => { html += `<span class="tag tag-skill">${esc(s)}</span>`; });
    html += `</div></div>`;
  }

  // Preferred Skills
  if (a.preferred_skills) {
    html += `<div class="analysis-section"><h3>Preferred Skills</h3><div>`;
    a.preferred_skills.forEach(s => { html += `<span class="tag tag-skill">${esc(s)}</span>`; });
    html += `</div></div>`;
  }

  // Hidden Qualities
  if (a.hidden_qualities) {
    html += `<div class="analysis-section"><h3>Hidden Qualities Sought</h3><ul>`;
    a.hidden_qualities.forEach(q => { html += `<li>${esc(q)}</li>`; });
    html += `</ul></div>`;
  }

  // Keywords matched / missing
  html += `<div class="analysis-section"><h3>Keywords Matched</h3><div>`;
  d.keyword_overlap.matched.slice(0, 20).forEach(k => { html += `<span class="tag tag-matched">${esc(k)}</span>`; });
  html += `</div></div>`;

  html += `<div class="analysis-section"><h3>Keywords Missing From Resume</h3><div>`;
  d.keyword_overlap.missing_from_resume.slice(0, 20).forEach(k => { html += `<span class="tag tag-missing">${esc(k)}</span>`; });
  html += `</div></div>`;

  // Comparison
  if (a.comparison) {
    html += `<div class="analysis-section"><h3>Resume vs. Ideal Comparison</h3>`;
    if (a.comparison.strengths) {
      html += `<p class="analysis-label analysis-label-strengths">Strengths</p><ul>`;
      a.comparison.strengths.forEach(s => { html += `<li>${esc(s)}</li>`; });
      html += `</ul>`;
    }
    if (a.comparison.gaps) {
      html += `<p class="analysis-label analysis-label-gaps">Gaps</p><ul>`;
      a.comparison.gaps.forEach(g => { html += `<li>${esc(g)}</li>`; });
      html += `</ul>`;
    }
    if (a.comparison.title_alignment) {
      html += `<p class="analysis-label analysis-label-title">Title alignment: <span class="analysis-label-detail">${esc(a.comparison.title_alignment)}</span></p>`;
    }
    html += `</div>`;
  }

  // Suggestions
  if (a.suggestions) {
    html += `<div class="analysis-section"><h3>Suggestions</h3>`;
    a.suggestions.forEach(s => {
      html += `<div class="suggestion-card">
        <div class="section-name">${esc(s.section || '')}</div>
        <div class="action">${esc(s.action || '')}</div>
        <div class="rationale">${esc(s.rationale || '')}</div>
      </div>`;
    });
    html += `</div>`;
  }

  // Keyword Placement
  if (a.keyword_placement && a.keyword_placement.length) {
    html += `<div class="analysis-section"><h3>Keyword Placement Suggestions</h3>`;
    a.keyword_placement.forEach(kp => {
      html += `<div class="suggestion-card">
        <div class="section-name">${esc(kp.keyword)}</div>
        <div class="action">${esc(kp.suggested_location)}: ${esc(kp.how)}</div>
      </div>`;
    });
    html += `</div>`;
  }

  // Strategy
  if (a.overall_strategy) {
    html += `<div class="analysis-section"><h3>Overall Strategy</h3><p style="color:var(--brand-hi)">${esc(a.overall_strategy)}</p></div>`;
  }

  el.innerHTML = html;
}

// ---- Clarification (optional interview step between analyze and generate) ----

function _resetClarifyUI() {
  lastClarifyQuestions = [];
  const start = document.getElementById('clarifyStartRow');
  const questions = document.getElementById('clarifyQuestions');
  const actions = document.getElementById('clarifyActions');
  if (start) start.classList.remove('hidden');
  if (questions) {
    questions.textContent = '';
    questions.classList.add('hidden');
  }
  if (actions) actions.classList.add('hidden');
  const btn = document.getElementById('btnClarify');
  if (btn) btn.disabled = false;
}

async function runClarify() {
  if (!lastContextPath) return alert('Run analysis first');
  setStatus('GENERATING QUESTIONS');
  const btn = document.getElementById('btnClarify');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/clarify', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        context_path: lastContextPath,
        username: currentUser,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (btn) btn.disabled = false;
      return reportError('Clarify', data.error || 'Clarification failed', data.detail);
    }
    lastClarifyQuestions = data.questions || [];
    _renderClarifyQuestions(lastClarifyQuestions, data.reasoning || '');
    setStatus('QUESTIONS READY');
    _announce(`${lastClarifyQuestions.length} clarifying question${lastClarifyQuestions.length === 1 ? '' : 's'} ready for review.`);
  } catch (e) {
    if (btn) btn.disabled = false;
    reportError('Clarify', 'Clarification request failed', e.message);
  }
}

// Render clarification questions using safe DOM creation (no innerHTML).
// All LLM-supplied strings (text, target_gap, kind, id) are inserted via
// textContent or attribute setters, which auto-escape and prevent XSS even
// if the model returns content with embedded HTML.
function _renderClarifyQuestions(questions, reasoning) {
  const start = document.getElementById('clarifyStartRow');
  const container = document.getElementById('clarifyQuestions');
  const actions = document.getElementById('clarifyActions');
  if (!container) return;

  container.textContent = '';  // clear

  if (!questions.length) {
    const warn = document.createElement('div');
    warn.className = 'warning';
    warn.textContent = 'No clarifying questions were produced. You can generate directly.';
    container.appendChild(warn);
    container.classList.remove('hidden');
    if (actions) actions.classList.remove('hidden');
    return;
  }

  if (reasoning) {
    const r = document.createElement('div');
    r.className = 'clarify-reasoning';
    r.textContent = reasoning;
    container.appendChild(r);
  }

  questions.forEach((q, idx) => {
    const kind = q.kind || 'experience_probe';
    const isScope = kind === 'scope_probe';
    const wrap = document.createElement('div');
    wrap.className = 'clarify-question';
    wrap.setAttribute('data-qid', q.id || ('q' + (idx + 1)));

    const head = document.createElement('div');
    head.className = 'clarify-question-head';
    const qtext = document.createElement('div');
    qtext.className = 'clarify-question-text';
    qtext.textContent = q.text || '';
    const badge = document.createElement('span');
    badge.className = isScope ? 'clarify-kind-badge scope' : 'clarify-kind-badge';
    badge.textContent = isScope ? 'SCOPE' : 'EXPERIENCE';
    head.appendChild(qtext);
    head.appendChild(badge);
    wrap.appendChild(head);

    if (q.target_gap) {
      const gap = document.createElement('div');
      gap.className = 'clarify-target-gap';
      gap.textContent = 'Gap: ' + q.target_gap;
      wrap.appendChild(gap);
    }

    const ta = document.createElement('textarea');
    ta.className = 'clarify-answer';
    ta.rows = 2;
    ta.placeholder = 'Your answer (optional — leave blank to skip this question)';
    wrap.appendChild(ta);

    container.appendChild(wrap);
  });

  container.classList.remove('hidden');
  if (actions) actions.classList.remove('hidden');
  if (start) start.classList.add('hidden');
}

function _collectClarifyAnswers() {
  const answers = {};
  document.querySelectorAll('#clarifyQuestions .clarify-question').forEach(el => {
    const qid = el.getAttribute('data-qid');
    const ta = el.querySelector('.clarify-answer');
    if (!qid || !ta) return;
    const val = (ta.value || '').trim();
    if (val) answers[qid] = val;
  });
  return answers;
}

// Workstream B1 reorder: submit + skip no longer trigger generate; they
// save clarifications (or clear them), fire the recommend call (so its
// output reflects the clarifications), and advance the wizard to Compose.
async function submitClarifications() {
  if (!lastContextPath) return alert('Run analysis first');

  const answers = _collectClarifyAnswers();
  setStatus('SAVING ANSWERS');
  const btnSubmit = document.getElementById('btnSubmitClarifications');
  if (btnSubmit) btnSubmit.disabled = true;

  try {
    const res = await fetch('/api/answer-clarifications', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        context_path: lastContextPath,
        username: currentUser,
        answers,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (btnSubmit) btnSubmit.disabled = false;
      return reportError('Save answers', data.error || 'Saving answers failed', data.detail);
    }
  } catch (e) {
    if (btnSubmit) btnSubmit.disabled = false;
    return reportError('Save answers', 'Saving answers request failed', e.message);
  }
  await _fireRecommendThenCompose();
  if (btnSubmit) btnSubmit.disabled = false;
}

async function skipClarifications() {
  // No answers submitted — clear any previously saved clarifications so
  // recommend + generate don't pick up stale answers from a prior run.
  if (lastContextPath) {
    try {
      await fetch('/api/answer-clarifications', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          context_path: lastContextPath,
          username: currentUser,
          answers: {},
        }),
      });
    } catch (e) {
      // Non-fatal: continue to recommend + compose regardless.
      console.warn('Failed to clear clarifications on skip:', e);
    }
  }
  await _fireRecommendThenCompose();
}

// Workstream B1: fire the recommend call so Compose can default to the
// curated set, then advance the wizard to step 3 (Compose). On recommend
// failure the Compose step falls back to top-5 by score with a toast.
async function _fireRecommendThenCompose() {
  if (_composeApplicationId != null) {
    try {
      setStatus('RECOMMENDING BULLETS');
      const rec = await fetch(
        `/api/applications/${_composeApplicationId}/recommend`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ context_path: lastContextPath }),
        },
      );
      if (!rec.ok) {
        const err = await rec.json().catch(() => ({}));
        _toast(`Recommend skipped: ${err.error || rec.status} — using top-5 fallback`, true);
      } else {
        setStatus('RECOMMENDATIONS READY');
      }
    } catch (e) {
      _toast(`Recommend skipped: ${e.message} — using top-5 fallback`, true);
    }
  }
  wizardGoTo(3);
}

// ---- Generation (P8 Gate #2) ----
async function runGeneration() {
  if (!lastContextPath) return alert('Run analysis first');

  setStatus('GENERATING');
  document.getElementById('btnGenerate').disabled = true;

  try {
    // refinementHistory holds {note, status} objects — only applied notes
    // count; serializing without filtering would send rejected ones, and
    // template-stringing the object would yield "[object Object]".
    const acceptedNotes = refinementHistory
      .filter(e => e.status === 'applied')
      .map((e, i) => `${i + 1}. ${e.note}`)
      .join('\n');

    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: currentUser,
        context_path: lastContextPath,
        output_format: outputFormat,
        refinement_notes: acceptedNotes,
        persona_template_id: _readSelectedPersonaId(),
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      return reportError('Generate', data.error || 'Generation failed', data.detail);
    }
    lastResumePath = data.resume_path;
    lastCoverLetterPath = data.cover_letter_path;
    lastResumeFormat = data.resume_format || '.docx';
    _selectedPersonaId = data.persona_template_id ?? _readSelectedPersonaId();
    _onGenerationComplete(data);
    _renderOutput(data);
    setStatus('GENERATION COMPLETE');
    _announce(`Iteration ${currentIteration} ready. Resume and cover letter generated.`);
    _wizardAdvanceTo(6);
  } catch (e) {
    reportError('Generate', 'Generation request failed', e.message);
  } finally {
    document.getElementById('btnGenerate').disabled = false;
  }
}

// Update iteration state from a /api/generate response. The backend writes a
// NEW context file each iteration and returns its path — the frontend MUST
// adopt that path so the next refine/iterate-clarify/save-edits call targets
// the latest snapshot, not the parent.
function _onGenerationComplete(data) {
  if (data.context_path) lastContextPath = data.context_path;
  if (typeof data.iteration === 'number') {
    currentIteration = data.iteration;
    _updateIterationPill();
  }
  // Freeze the LLM's output so _detectEdits can diff the live preview against it.
  lastGeneratedResume = data.resume_preview || '';
  lastGeneratedCoverLetter = data.cover_letter_preview || '';
  // A fresh generation supersedes any in-progress iteration interview.
  _resetIterateClarifyUI();
}

function _updateIterationPill() {
  const pill = document.getElementById('iterationPill');
  if (!pill) return;
  if (currentIteration < 1) {
    pill.classList.add('hidden');
    return;
  }
  pill.textContent = `iter ${currentIteration}`;
  pill.classList.remove('hidden');
}

// ---- Edit detection ------------------------------------------------------

// Compare the live preview against the frozen lastGenerated* snapshots.
// Returns {resumeEdited, coverEdited, anyEdited, currentResume, currentCover}.
// The current* fields are the live preview text the caller will send to
// /api/save-edits if the user picks USE EDITS AS BASELINE.
function _detectEdits() {
  const live = (id) => (document.getElementById(id)?.innerText || '').trim();
  const resume = live('resumePreview');
  const cover = live('coverLetterPreview');
  const resumeEdited = !!lastGeneratedResume && resume !== lastGeneratedResume.trim();
  const coverEdited = !!lastGeneratedCoverLetter && cover !== lastGeneratedCoverLetter.trim();
  return {
    resumeEdited, coverEdited,
    anyEdited: resumeEdited || coverEdited,
    currentResume: resume,
    currentCover: cover,
  };
}

// Show the edit-detection modal and resolve with the user's choice:
//   "use"     — adopt the edits as the new baseline (POST /api/save-edits)
//   "discard" — restore preview from lastGenerated* and continue
//   "cancel"  — abort the in-progress action
// Implements a basic focus trap: Esc cancels, Tab/Shift+Tab cycle through
// the three modal buttons, and the recommended action (USE EDITS) is focused
// on open. Focus returns to the trigger button on close (Phase 4 will verify).
function _showEditModal(triggerEl) {
  return new Promise((resolve) => {
    const modal = document.getElementById('editModal');
    if (!modal) { resolve('cancel'); return; }
    const buttons = Array.from(modal.querySelectorAll('[data-modal-dismiss]'));
    const focusable = modal.querySelectorAll('button[data-modal-dismiss]');

    const cleanup = (action) => {
      modal.classList.add('hidden');
      modal.removeEventListener('keydown', onKey);
      buttons.forEach(b => b.removeEventListener('click', onClick));
      const backdrop = modal.querySelector('.lcars-modal-backdrop');
      if (backdrop) backdrop.removeEventListener('click', onClick);
      // Restore focus to the element that opened the modal so keyboard users
      // don't lose their place. Falls back to body when the trigger is gone.
      if (triggerEl && typeof triggerEl.focus === 'function') triggerEl.focus();
      resolve(action || 'cancel');
    };

    const onClick = (e) => {
      const action = e.currentTarget?.getAttribute?.('data-modal-dismiss') || 'cancel';
      cleanup(action);
    };

    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); cleanup('cancel'); return; }
      if (e.key !== 'Tab' || focusable.length === 0) return;
      // Wrap focus within the modal — basic focus trap.
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };

    buttons.forEach(b => b.addEventListener('click', onClick));
    const backdrop = modal.querySelector('.lcars-modal-backdrop');
    if (backdrop) backdrop.addEventListener('click', onClick);
    modal.addEventListener('keydown', onKey);
    modal.classList.remove('hidden');
    // Default focus on the recommended action.
    const useBtn = modal.querySelector('#btnUseEdits');
    if (useBtn) useBtn.focus();
  });
}

// Diagnostics modal — a thin launcher for the /_dashboard blueprint.
// The dashboard is served by this same Flask process, so there is no
// server to "start"; the modal just gives a labelled, keyboard-safe
// entry point. Mirrors _showEditModal's a11y posture (Esc closes,
// focus trap, focus restored to the trigger).
function openDiagnosticsModal() {
  const modal = document.getElementById('diagnosticsModal');
  if (!modal) return;
  const trigger = document.getElementById('diagnosticsPill');
  const focusable = modal.querySelectorAll('a[href], button');

  const cleanup = () => {
    modal.classList.add('hidden');
    modal.removeEventListener('keydown', onKey);
    dismissers.forEach(b => b.removeEventListener('click', cleanup));
    if (trigger && typeof trigger.focus === 'function') trigger.focus();
  };

  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); cleanup(); return; }
    if (e.key !== 'Tab' || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };

  const dismissers = Array.from(modal.querySelectorAll('[data-diag-dismiss]'));
  dismissers.forEach(b => b.addEventListener('click', cleanup));
  modal.addEventListener('keydown', onKey);
  modal.classList.remove('hidden');
  const openBtn = document.getElementById('btnOpenDashboard');
  if (openBtn) openBtn.focus();
}

// ===============================================================
// Workstream B1.3 — Settings drawer (Profile + Diagnostics link)
// ===============================================================

function openSettingsDrawer() {
  const drawer = document.getElementById('settingsDrawer');
  if (!drawer) return;
  const trigger = document.getElementById('settingsPill');
  const focusable = drawer.querySelectorAll(
    'button, input, textarea, select, a[href]',
  );
  const cleanup = () => {
    drawer.classList.add('hidden');
    drawer.removeEventListener('keydown', onKey);
    dismissers.forEach(b => b.removeEventListener('click', cleanup));
    if (trigger && typeof trigger.focus === 'function') trigger.focus();
  };
  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); cleanup(); return; }
    if (e.key !== 'Tab' || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  const dismissers = Array.from(drawer.querySelectorAll('[data-settings-dismiss]'));
  dismissers.forEach(b => b.addEventListener('click', cleanup));
  drawer.addEventListener('keydown', onKey);
  drawer.classList.remove('hidden');
  const first = drawer.querySelector('input, textarea');
  if (first) first.focus();
}

// ===============================================================
// Error reporting — copyable error modal + clickable status pill
// ===============================================================

let _lastError = null;  // { stage, message, detail, ts, user }

// Central error sink. Replaces the old `setStatus('ERROR'); alert(...)`
// pairs: stores the error so the (now clickable) red pill can re-open a
// copyable modal, then surfaces it immediately.
function reportError(stage, message, detail) {
  _lastError = {
    stage: stage || 'Unknown',
    message: message || 'Unknown error',
    detail: detail || '',
    ts: new Date().toISOString(),
    user: currentUser || '(none)',
  };
  setStatus('ERROR');
  openErrorModal();
}

function _formatLastError() {
  if (!_lastError) return 'No error recorded.';
  const e = _lastError;
  let out = `Stage:   ${e.stage}\n`;
  out += `User:    ${e.user}\n`;
  out += `When:    ${e.ts}\n`;
  out += `Message: ${e.message}\n`;
  if (e.detail) out += `\nDetail:\n${e.detail}\n`;
  return out;
}

function openErrorModal() {
  const modal = document.getElementById('errorModal');
  if (!modal) return;
  const ta = document.getElementById('errorModalText');
  if (ta) ta.value = _formatLastError();
  const trigger = document.getElementById('statusPill');
  const focusable = modal.querySelectorAll('button, textarea');

  const cleanup = () => {
    modal.classList.add('hidden');
    modal.removeEventListener('keydown', onKey);
    dismissers.forEach(b => b.removeEventListener('click', cleanup));
    if (copyBtn) copyBtn.removeEventListener('click', onCopy);
    if (trigger && typeof trigger.focus === 'function') trigger.focus();
  };
  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); cleanup(); return; }
    if (e.key !== 'Tab' || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  const onCopy = async () => {
    const text = _formatLastError();
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = 'COPIED ✓';
    } catch {
      // Clipboard API blocked (non-secure context etc.) — fall back to
      // selecting the textarea so the user can Ctrl+C manually.
      if (ta) { ta.focus(); ta.select(); }
      copyBtn.textContent = 'SELECTED — PRESS CTRL+C';
    }
    setTimeout(() => { copyBtn.textContent = 'COPY'; }, 2000);
  };

  const dismissers = Array.from(modal.querySelectorAll('[data-err-dismiss]'));
  const copyBtn = document.getElementById('btnCopyError');
  dismissers.forEach(b => b.addEventListener('click', cleanup));
  if (copyBtn) copyBtn.addEventListener('click', onCopy);
  modal.addEventListener('keydown', onKey);
  modal.classList.remove('hidden');
  if (copyBtn) copyBtn.focus();
}

// ===============================================================
// Legacy-user onboarding bridge (needs_onboarding → import → retry)
// ===============================================================

// True when a DB-backed route reports the selected user has no candidate
// row yet (HTTP 409 + needs_onboarding). Pre-existing config-only users
// (e.g. imported before the DB migration) hit this until imported.
function _needsOnboarding(res, data) {
  return res && res.status === 409 && data && data.needs_onboarding === true;
}

// Opens the onboarding modal. On successful import it closes and calls
// retryFn() so the action the user originally attempted just proceeds.
function openOnboardingModal(retryFn) {
  const modal = document.getElementById('onboardingModal');
  if (!modal) return;
  const nameEl = document.getElementById('onboardingUserName');
  if (nameEl) nameEl.textContent = currentUser || '(no user)';
  const withLlm = document.getElementById('onboardingWithLlm');
  if (withLlm) withLlm.checked = false;
  const statusEl = document.getElementById('onboardingStatus');
  if (statusEl) statusEl.textContent = '';
  const importBtn = document.getElementById('btnRunImport');
  const focusable = modal.querySelectorAll('button, input');

  const cleanup = () => {
    modal.classList.add('hidden');
    modal.removeEventListener('keydown', onKey);
    dismissers.forEach(b => b.removeEventListener('click', cleanup));
    if (importBtn) importBtn.removeEventListener('click', onImport);
  };
  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); cleanup(); return; }
    if (e.key !== 'Tab' || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  const onImport = async () => {
    if (!currentUser) return;
    importBtn.disabled = true;
    if (statusEl) statusEl.textContent = 'Importing… (this can take a moment)';
    try {
      const res = await fetch(
        `/api/users/${encodeURIComponent(currentUser)}/import-legacy`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ with_llm: !!(withLlm && withLlm.checked) }),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (statusEl) statusEl.textContent = '';
        cleanup();
        reportError('Legacy import', data.error || `HTTP ${res.status}`,
          JSON.stringify(data, null, 2));
        return;
      }
      const exp = data.experiences_created || 0;
      const bul = data.bullets_created || 0;
      const clar = data.clarifications_created || 0;
      if (statusEl) {
        statusEl.textContent =
          `Imported: ${exp} experience(s), ${bul} bullet(s), ${clar} clarification(s).`;
      }
      cleanup();
      _toast(`${currentUser} imported into the corpus`);
      if (typeof retryFn === 'function') retryFn();
    } catch (e) {
      if (statusEl) statusEl.textContent = '';
      cleanup();
      reportError('Legacy import', e.message);
    } finally {
      importBtn.disabled = false;
    }
  };

  const dismissers = Array.from(modal.querySelectorAll('[data-onboard-dismiss]'));
  dismissers.forEach(b => b.addEventListener('click', cleanup));
  if (importBtn) importBtn.addEventListener('click', onImport);
  modal.addEventListener('keydown', onKey);
  modal.classList.remove('hidden');
  if (importBtn) importBtn.focus();
}

// Inline placeholder for passive tab refreshes (Corpus / Applications /
// Memory / Personas) when the user isn't onboarded yet. Renders a short
// message + a button that opens the onboarding modal and re-runs the
// tab refresh on success.
function _renderNeedsOnboarding(container, retryFn) {
  if (!container) return;
  _clearChildren(container);
  const wrap = _el('div', { className: 'corpus-empty-experience' });
  wrap.appendChild(_el('div', {
    textContent: `${currentUser} isn't in the career corpus yet.`,
  }));
  const btn = _el('button', {
    className: 'lcars-btn lcars-bg-teal',
    textContent: 'IMPORT INTO CORPUS',
  });
  btn.style.marginTop = '10px';
  btn.onclick = () => openOnboardingModal(retryFn);
  wrap.appendChild(btn);
  container.appendChild(wrap);
}

// Persist the live preview text as the next iteration's baseline.
// Returns true on success, false on failure (caller should abort the chain).
async function _saveEdits(edits) {
  if (!lastContextPath) return false;
  try {
    const res = await fetch('/api/save-edits', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        context_path: lastContextPath,
        username: currentUser,
        edited_resume: edits.resumeEdited ? edits.currentResume : '',
        edited_cover_letter: edits.coverEdited ? edits.currentCover : '',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || 'Saving edits failed');
      return false;
    }
    _announce('Edits saved as baseline for the next iteration.');
    return true;
  } catch (e) {
    alert('Saving edits failed: ' + e.message);
    return false;
  }
}

// Restore the preview from the frozen last-generated snapshots. Used on the
// DISCARD EDITS path so the user's typed changes are visually rolled back
// before the action they triggered (refine / iterate-clarify) proceeds.
function _discardEdits() {
  const r = document.getElementById('resumePreview');
  const c = document.getElementById('coverLetterPreview');
  if (r && lastGeneratedResume) r.innerText = lastGeneratedResume;
  if (c && lastGeneratedCoverLetter) c.innerText = lastGeneratedCoverLetter;
}

// Common gate: if the preview has unsaved edits, prompt the user via the
// modal. Returns true if the action should proceed, false if the user
// canceled. Side effects (save or discard) happen here so callers stay clean.
async function _gateEditsBeforeAction(triggerEl) {
  const edits = _detectEdits();
  if (!edits.anyEdited) return true;

  const choice = await _showEditModal(triggerEl);
  if (choice === 'cancel') return false;
  if (choice === 'discard') { _discardEdits(); return true; }
  if (choice === 'use') {
    const ok = await _saveEdits(edits);
    return ok;
  }
  return false;
}

// ---- Refinement ----
async function submitRefinement() {
  const input = document.getElementById('refinementInput');
  const note = input.value.trim();
  if (!note || !lastContextPath) return;

  // Edit gate: handle in-progress preview edits before the refinement call
  // so the user's typed changes feed the next generation rather than being
  // silently discarded by the regenerate-from-context path.
  const proceed = await _gateEditsBeforeAction(document.getElementById('btnRefinement'));
  if (!proceed) return;

  const entry = { note, status: 'pending' };
  refinementHistory.push(entry);
  _renderRefinementHistory();
  input.value = '';
  document.getElementById('btnRefinement').disabled = true;
  document.getElementById('btnGenerate').disabled = true;

  try {
    // Step 1: scope validation via Haiku
    const checkRes = await fetch('/api/validate-refinement', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ note }),
    });
    const check = await checkRes.json();

    if (!check.valid) {
      entry.status = 'rejected';
      entry.reason = check.reason || 'Outside allowed scope.';
      _renderRefinementHistory();
      setStatus('REFINEMENT REJECTED');
      return;
    }

    // Step 2: generate with accepted notes only
    entry.status = 'applied';
    _renderRefinementHistory();
    setStatus('REFINING');

    const acceptedNotes = refinementHistory
      .filter(e => e.status === 'applied')
      .map((e, i) => `${i + 1}. ${e.note}`)
      .join('\n');

    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: currentUser,
        context_path: lastContextPath,
        output_format: lastResumeFormat,
        refinement_notes: acceptedNotes,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      entry.status = 'rejected';
      entry.reason = data.error || 'Generation failed.';
      _renderRefinementHistory();
      reportError('Refine', data.error || 'Refinement generation failed', data.detail);
      return;
    }
    lastResumePath = data.resume_path;
    lastCoverLetterPath = data.cover_letter_path;
    lastResumeFormat = data.resume_format || lastResumeFormat;
    _onGenerationComplete(data);
    _renderOutput(data);
    setStatus('REFINED');
    _announce(`Iteration ${currentIteration} refined.`);
  } catch (e) {
    entry.status = 'rejected';
    entry.reason = 'Request failed: ' + e.message;
    _renderRefinementHistory();
    reportError('Refine', 'Refinement request failed', e.message);
  } finally {
    document.getElementById('btnRefinement').disabled = false;
    document.getElementById('btnGenerate').disabled = false;
  }
}

// ---- Iteration interview (post-generation clarifying questions) ----------

function _resetIterateClarifyUI() {
  lastIterateClarifyQuestions = [];
  const area = document.getElementById('iterateClarifyArea');
  const questions = document.getElementById('iterateClarifyQuestions');
  const actions = document.getElementById('iterateClarifyActions');
  if (area) area.classList.add('hidden');
  if (questions) questions.textContent = '';
  if (actions) actions.classList.add('hidden');
  const btn = document.getElementById('btnIterateClarify');
  if (btn) btn.disabled = false;
}

async function runIterateClarify() {
  if (!lastContextPath) return;
  if (currentIteration < 1) {
    return alert('Generate the resume at least once before requesting iteration questions.');
  }

  const proceed = await _gateEditsBeforeAction(document.getElementById('btnIterateClarify'));
  if (!proceed) return;

  setStatus('GENERATING QUESTIONS');
  const btn = document.getElementById('btnIterateClarify');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/iterate-clarify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        context_path: lastContextPath,
        username: currentUser,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (btn) btn.disabled = false;
      return reportError('Iteration interview',
        data.error || 'Iteration interview failed', data.detail);
    }
    lastIterateClarifyQuestions = data.questions || [];
    _renderIterateClarifyQuestions(lastIterateClarifyQuestions, data.reasoning || '');
    setStatus('QUESTIONS READY');
    _announce(`${lastIterateClarifyQuestions.length} iteration question${lastIterateClarifyQuestions.length === 1 ? '' : 's'} ready for review.`);
  } catch (e) {
    if (btn) btn.disabled = false;
    reportError('Iteration interview', 'Iteration interview request failed', e.message);
  }
}

// Render iteration-interview questions. Visually distinct from the analyze-
// time clarify panel (different container, different divider label) but uses
// the same per-question markup so screen-reader and keyboard behavior carry
// over. The iteration_probe kind gets its own badge color.
function _renderIterateClarifyQuestions(questions, reasoning) {
  const area = document.getElementById('iterateClarifyArea');
  const container = document.getElementById('iterateClarifyQuestions');
  const actions = document.getElementById('iterateClarifyActions');
  if (!container || !area) return;

  container.textContent = '';

  if (!questions.length) {
    const warn = document.createElement('div');
    warn.className = 'warning';
    warn.textContent = 'No follow-up questions surfaced — the current draft looks healthy on the measured signals.';
    container.appendChild(warn);
    area.classList.remove('hidden');
    if (actions) actions.classList.remove('hidden');
    return;
  }

  if (reasoning) {
    const r = document.createElement('div');
    r.className = 'clarify-reasoning';
    r.textContent = reasoning;
    container.appendChild(r);
  }

  questions.forEach((q, idx) => {
    const kind = q.kind || 'iteration_probe';
    const wrap = document.createElement('div');
    wrap.className = 'clarify-question';
    wrap.setAttribute('data-qid', q.id || ('q' + (idx + 1)));

    const head = document.createElement('div');
    head.className = 'clarify-question-head';
    const qtext = document.createElement('div');
    qtext.className = 'clarify-question-text';
    qtext.textContent = q.text || '';
    const badge = document.createElement('span');
    badge.className = 'clarify-kind-badge';
    if (kind === 'scope_probe') badge.classList.add('scope');
    else if (kind === 'iteration_probe') badge.classList.add('iteration');
    badge.textContent = kind === 'scope_probe' ? 'SCOPE'
                       : kind === 'iteration_probe' ? 'ITERATION'
                       : 'EXPERIENCE';
    head.appendChild(qtext);
    head.appendChild(badge);
    wrap.appendChild(head);

    if (q.target_gap) {
      const gap = document.createElement('div');
      gap.className = 'clarify-target-gap';
      gap.textContent = 'Gap: ' + q.target_gap;
      wrap.appendChild(gap);
    }

    const ta = document.createElement('textarea');
    ta.className = 'clarify-answer';
    ta.rows = 2;
    ta.placeholder = 'Your answer (optional — leave blank to skip this question)';
    wrap.appendChild(ta);

    container.appendChild(wrap);
  });

  area.classList.remove('hidden');
  if (actions) actions.classList.remove('hidden');
}

function _collectIterateClarifyAnswers() {
  const answers = {};
  document.querySelectorAll('#iterateClarifyQuestions .clarify-question').forEach(el => {
    const qid = el.getAttribute('data-qid');
    const ta = el.querySelector('.clarify-answer');
    if (!qid || !ta) return;
    const val = (ta.value || '').trim();
    if (val) answers[qid] = val;
  });
  return answers;
}

async function submitIterateClarificationsAndGenerate() {
  if (!lastContextPath) return;

  const answers = _collectIterateClarifyAnswers();
  const btn = document.getElementById('btnSubmitIterateClarifications');
  if (btn) btn.disabled = true;
  setStatus('SAVING ANSWERS');

  try {
    // The /api/answer-clarifications route merges these into context.clarifications
    // by id — prior answers (including from the analyze-time clarify) stay intact.
    const res = await fetch('/api/answer-clarifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        context_path: lastContextPath,
        username: currentUser,
        answers,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (btn) btn.disabled = false;
      return reportError('Save answers', data.error || 'Saving answers failed', data.detail);
    }
  } catch (e) {
    if (btn) btn.disabled = false;
    return reportError('Save answers', 'Saving answers request failed', e.message);
  }

  // Run a fresh generation against the now-augmented context. The new
  // iteration's <resume> block sees the typed edits AND the new clarifications.
  _resetIterateClarifyUI();
  await runGeneration();
  if (btn) btn.disabled = false;
}

function skipIterateClarifications() {
  // Close the panel; do NOT clear prior context.clarifications — those are
  // accumulated truths, only the new questions get dropped.
  _resetIterateClarifyUI();
  setStatus('READY');
}

function _renderRefinementHistory() {
  const container = document.getElementById('refinementHistory');
  if (!refinementHistory.length) {
    container.classList.add('hidden');
    container.innerHTML = '';
    return;
  }
  container.classList.remove('hidden');
  container.innerHTML = refinementHistory.map((entry, i) => {
    const isRejected = entry.status === 'rejected';
    const badge = isRejected
      ? `<span class="refinement-badge-rejected">NOT EXECUTED</span>`
      : '';
    const reason = isRejected && entry.reason
      ? `<div class="refinement-rejection-reason">${esc(entry.reason)}</div>`
      : '';
    return `<div class="refinement-entry${isRejected ? ' rejected' : ''}">
      <span class="refinement-index">${i + 1}</span>
      <span class="refinement-text">${esc(entry.note)}${badge}</span>
      ${reason}
    </div>`;
  }).join('');
}

function _renderOutput(data) {
  document.getElementById('resumePreview').innerText = data.resume_preview || '';
  document.getElementById('coverLetterPreview').innerText = data.cover_letter_preview || '';
  // Reset view mode to RAW on each generation
  ['resume', 'coverLetter'].forEach(which => {
    const previewId = which === 'resume' ? 'resumePreview' : 'coverLetterPreview';
    const renderedId = which === 'resume' ? 'resumeRendered' : 'coverLetterRendered';
    document.getElementById(previewId).classList.remove('hidden');
    document.getElementById(renderedId).classList.add('hidden');
    const tabId = which === 'resume' ? 'tabResume' : 'tabCoverLetter';
    document.getElementById(tabId).querySelectorAll('.view-btn').forEach((b, i) => {
      b.classList.toggle('active', i === 0);
    });
  });

  let changesHtml = '';
  if (data.changes_made && data.changes_made.length) {
    changesHtml += '<div class="analysis-section"><h3>Changes Made</h3><ul>';
    data.changes_made.forEach(c => { changesHtml += `<li>${esc(c)}</li>`; });
    changesHtml += '</ul></div>';
  }
  if (data.proofread_notes && data.proofread_notes.length) {
    changesHtml += '<div class="analysis-section"><h3>Proofread Notes</h3><ul>';
    data.proofread_notes.forEach(n => { changesHtml += `<li>${esc(n)}</li>`; });
    changesHtml += '</ul></div>';
  }
  document.getElementById('changesContent').innerHTML = changesHtml;
  showTab('resume');
  document.getElementById('refinementArea').classList.remove('hidden');
  document.getElementById('refinementInput').value = '';
}

function showTab(name, clickedBtn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  // Reset all tab-btns' visual + ARIA state in one pass; the matching button
  // is set selected below. Without aria-selected updates, screen readers
  // announce the wrong active tab.
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.remove('active');
    if (b.getAttribute('role') === 'tab') b.setAttribute('aria-selected', 'false');
  });
  const tabId = name === 'coverLetter' ? 'tabCoverLetter' : name === 'changes' ? 'tabChanges' : 'tabResume';
  document.getElementById(tabId).classList.add('active');
  let activeBtn = clickedBtn;
  if (!activeBtn) {
    const btnIndex = name === 'coverLetter' ? 1 : name === 'changes' ? 2 : 0;
    const btns = document.querySelectorAll('.tab-btn');
    activeBtn = btns[btnIndex];
  }
  if (activeBtn) {
    activeBtn.classList.add('active');
    if (activeBtn.getAttribute('role') === 'tab') activeBtn.setAttribute('aria-selected', 'true');
  }
}

async function downloadResume() {
  const content = document.getElementById('resumePreview').innerText;
  await _downloadEdited('/api/download-edited', {
    username: currentUser,
    content,
    type: 'resume',
    original_format: lastResumeFormat,
    // Workstream C #7: thread the chosen persona so DOWNLOAD honors the
    // template (the legacy template_path was empty in DB mode + gated to
    // RESUMES_DIR, which silently dropped persona templates).
    persona_template_id: _selectedPersonaId ?? _readSelectedPersonaId(),
  });
}

async function downloadCoverLetter() {
  const content = document.getElementById('coverLetterPreview').innerText;
  await _downloadEdited('/api/download-edited', {
    username: currentUser,
    content,
    type: 'cover_letter',
    original_format: lastResumeFormat,
  });
}

async function _downloadEdited(url, payload) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return alert(err.error || 'Download failed');
  }
  // Stream the file as a download
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') || '';
  const nameMatch = disposition.match(/filename="?([^"]+)"?/);
  const filename = nameMatch ? nameMatch[1] : 'document.docx';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Preview view mode (RAW / RENDERED) ----
function setViewMode(mode, which, btn) {
  const previewId = which === 'resume' ? 'resumePreview' : 'coverLetterPreview';
  const renderedId = which === 'resume' ? 'resumeRendered' : 'coverLetterRendered';
  const preview = document.getElementById(previewId);
  const rendered = document.getElementById(renderedId);
  const controls = btn.closest('.view-controls');
  controls.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (mode === 'rendered') {
    rendered.innerHTML = _renderMarkdown(preview.innerText);
    preview.classList.add('hidden');
    rendered.classList.remove('hidden');
  } else {
    preview.classList.remove('hidden');
    rendered.classList.add('hidden');
  }
}

function _renderMarkdown(text) {
  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const inline = s => esc(s)
    .replace(/\*\*\*([^*\n]+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');
  const lines = text.split('\n');
  let html = '';
  let inList = false;
  for (const raw of lines) {
    const s = raw.trim();
    const isBullet = /^[-*\u2022\u2013\u2014\u00b7\u25c6\u25cf\u25aa]\s/.test(s);
    if (!isBullet && inList) { html += '</ul>'; inList = false; }
    if (!s)               { html += '<br>'; }
    else if (s.startsWith('# '))  { html += `<h1>${inline(s.slice(2))}</h1>`; }
    else if (s.startsWith('## ')) { html += `<h2>${inline(s.slice(3))}</h2>`; }
    else if (s.startsWith('### ')){ html += `<h3>${inline(s.slice(4))}</h3>`; }
    else if (isBullet)  {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${inline(s.replace(/^[-*\u2022\u2013\u2014\u00b7\u25c6\u25cf\u25aa]\s+/,''))}</li>`;
    }
    else { html += `<p>${inline(s)}</p>`; }
  }
  if (inList) html += '</ul>';
  return html;
}

// ---- Helpers ----
function show(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('hidden', 'collapsed');
  const block = document.querySelector(`[data-panel="${id}"]`);
  if (block) block.classList.remove('hidden', 'collapsed');
}
function hide(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add('hidden');
  const block = document.querySelector(`[data-panel="${id}"]`);
  if (block) block.classList.add('hidden');
}
function hideAllPanels() {
  // Workstream B1: panelConfig moved to Settings drawer + panelResume
  // removed; remaining flow panels are listed explicitly + the wizard
  // panels are added so hideAllPanels keeps doing what it advertises.
  [
    'panelApplications',
    'panelJD', 'panelAnalysis', 'panelClarify',
    'panelCompose', 'panelTemplate', 'panelGenerate', 'panelOutput',
  ].forEach(hide);
}

// Active states: pill and sidebar block flash together; idle states are solid.
// Maps each active state keyword to the panel whose block should flash.
const _ACTIVE_PANEL = {
  UPLOADING:  'panelResume',
  ANALYZING:  'panelAnalysis',
  GENERATING: 'panelOutput',
  REFINING:   'panelOutput',
};
// Status communication lives on the topbar + bottom statusbar pills (the
// pulsing-dot is-active state) and the aria-busy attribute on the active
// panel. No DOM tile flash.

// Push a one-shot announcement into the hidden aria-live region. Use only
// for meaningful transitions a screen-reader user wouldn't otherwise notice
// (generation done, questions ready, edits saved, errors). DON'T announce
// every status microstep — aria-live="polite" can drone if over-fed.
//
// We toggle the textContent off-then-on so identical consecutive messages
// re-announce (some screen readers suppress duplicate text).
function _announce(text) {
  const el = document.getElementById('srAnnounce');
  if (!el || !text) return;
  el.textContent = '';
  // Next-tick repopulate so the assistive tech sees a change.
  setTimeout(() => { el.textContent = text; }, 16);
}

// Sentence-case a short status string ('GENERATION COMPLETE' → 'Generation
// complete'). Kept here because every setStatus() call passes ALL CAPS
// from the LCARS era; the callback. chrome uses sentence case.
function _toSentence(s) {
  if (!s) return '';
  const lower = s.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

function setStatus(text) {
  const pill = document.getElementById('statusPill');
  // .cb-status-text is the dedicated label child of the callback. status
  // pill. The whole pill was migrated from .lcars-pill to .cb-status in
  // feat/release-visual-ia, so this element is always present.
  const textEl = pill.querySelector('.cb-status-text');
  if (textEl) textEl.textContent = _toSentence(text);

  // Clear any prior aria-busy state from the previously-active panel so
  // assistive tech stops announcing the panel as busy once work completes.
  document.querySelectorAll('.lcars-panel[aria-busy="true"]').forEach(p => {
    p.removeAttribute('aria-busy');
  });

  const activeKey = Object.keys(_ACTIVE_PANEL).find(s => text.includes(s));
  const isActive  = !!activeKey;
  const isError   = text.includes('ERROR');

  pill.classList.toggle('is-active', isActive);
  pill.classList.toggle('is-error',  isError);

  // Mirror state into the floating bottom status bar so the user gets
  // the same status signal whether their eye is at the top or the bottom
  // of the page during long LLM calls.
  const sbText   = document.getElementById('cbStatusbarText');
  const sbStatus = sbText ? sbText.closest('.cb-statusbar-status') : null;
  if (sbText)   sbText.textContent = _toSentence(text);
  if (sbStatus) {
    sbStatus.classList.toggle('is-active', isActive);
    sbStatus.classList.toggle('is-error',  isError);
  }

  // In error state the pill becomes a button that re-opens the copyable
  // error modal; outside error state it's an inert status indicator.
  if (isError) {
    pill.classList.add('pill-clickable');
    pill.setAttribute('role', 'button');
    pill.setAttribute('tabindex', '0');
    pill.setAttribute('title', 'Click to view / copy the error');
    if (!pill._errBound) {
      pill._errHandler = (ev) => {
        if (ev.type === 'keydown' && ev.key !== 'Enter' && ev.key !== ' ') return;
        if (ev.type === 'keydown') ev.preventDefault();
        if (pill.classList.contains('pill-clickable')) openErrorModal();
      };
      pill.addEventListener('click', pill._errHandler);
      pill.addEventListener('keydown', pill._errHandler);
      pill._errBound = true;
    }
  } else {
    pill.classList.remove('pill-clickable');
    pill.removeAttribute('role');
    pill.removeAttribute('tabindex');
    pill.removeAttribute('title');
  }

  // Mark the active panel aria-busy so screen readers know work is in
  // progress on that section. (Visual feedback lives on the topbar +
  // bottom status pills; the LCARS-era elbow flash + .lcars-block tile
  // flash were retired in feat/release-visual-ia.)
  if (isActive) {
    const activePanel = document.getElementById(_ACTIVE_PANEL[activeKey]);
    if (activePanel) activePanel.setAttribute('aria-busy', 'true');
  }
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ---- Panel collapse / expand ----
function _togglePanel(panelId) {
  const panel = document.getElementById(panelId);
  if (!panel || panel.classList.contains('hidden')) return;
  const isCollapsed = panel.classList.toggle('collapsed');
  const block = document.querySelector(`[data-panel="${panelId}"]`);
  if (block) block.classList.toggle('collapsed', isCollapsed);
}

// Panel-header click toggles the parent .lcars-panel between expanded
// and collapsed states (CSS grid-template-rows transition).
document.querySelectorAll('.panel-header').forEach(header => {
  const panel = header.closest('.lcars-panel');
  if (panel) header.addEventListener('click', () => _togglePanel(panel.id));
});

// ===============================================================
// Phase D.2 — Top-level tabs + Career Corpus tab
// ===============================================================

let _corpusLoadedForUser = '';
let _corpusExperiences = [];

function switchTopTab(name, btn) {
  document.querySelectorAll('.top-tab-btn').forEach(b => {
    b.classList.toggle('active', b === btn);
    b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
  });
  document.querySelectorAll('.top-tab-panel').forEach(p => p.classList.add('hidden'));
  const target = document.getElementById(`tab-${name}`);
  if (target) target.classList.remove('hidden');
  if (name === 'corpus') loadCorpusIfReady();
  if (name === 'personas') _personaTabActivated();
  if (name === 'memory') _memoryTabActivated();
}

async function loadCorpusIfReady() {
  if (!currentUser) {
    document.getElementById('corpusEmptyHint').textContent =
      'Select a user above to load their experiences.';
    document.getElementById('corpusToolbar').style.display = 'none';
    _clearChildren(document.getElementById('corpusExperienceList'));
    _corpusLoadedForUser = '';
    return;
  }
  if (_corpusLoadedForUser === currentUser) return;
  await refreshCorpus();
}

async function refreshCorpus() {
  const list = document.getElementById('corpusExperienceList');
  _setLoadingPlaceholder(list, 'Loading…');
  _refreshOnboardingBanner();  // fire-and-forget; doesn't block list load
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
  }
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    if (_needsOnboarding(res, data)) {
      document.getElementById('corpusToolbar').style.display = 'none';
      _renderNeedsOnboarding(list, refreshCorpus);
      return;
    }
  }
  if (res.status === 404) {
    _clearChildren(list);
    document.getElementById('corpusEmptyHint').textContent =
      'No experiences in the corpus yet for ' + currentUser +
      '. Onboarding extraction populates this on first import.';
    document.getElementById('corpusToolbar').style.display = '';
    _corpusLoadedForUser = currentUser;
    _corpusExperiences = [];
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load corpus.');
    return;
  }
  const data = await res.json();
  _corpusExperiences = data;
  _corpusLoadedForUser = currentUser;
  _renderCorpusList();
}

function _renderCorpusList() {
  const list = document.getElementById('corpusExperienceList');
  const hint = document.getElementById('corpusEmptyHint');
  const toolbar = document.getElementById('corpusToolbar');
  toolbar.style.display = '';
  document.getElementById('corpusCount').textContent =
    `${_corpusExperiences.length} experience${_corpusExperiences.length === 1 ? '' : 's'}`;
  _clearChildren(list);
  if (_corpusExperiences.length === 0) {
    hint.textContent = 'No experiences yet. Click + ADD EXPERIENCE to start, or run onboarding.';
    return;
  }
  hint.textContent = 'Click a card to expand and edit titles + bullets. Saves are inline.';
  _corpusExperiences.forEach(exp => list.appendChild(_renderCorpusSummary(exp)));
}

function _renderCorpusSummary(exp) {
  const card = _el('div', { className: 'corpus-card', id: `corpus-exp-${exp.id}` });
  card.dataset.experienceId = exp.id;
  const header = _el('div', { className: 'corpus-card-header' });
  header.onclick = () => toggleCorpusCard(exp.id);
  header.appendChild(_el('button', { className: 'corpus-card-toggle' }, [], { 'aria-label': 'Expand' }));
  header.appendChild(_el('div', { className: 'corpus-card-company', textContent: exp.company || '(no company)' }));
  header.appendChild(_el('div', { className: 'corpus-card-title', textContent: exp.official_title || '(no official title)' }));
  header.appendChild(_el('div', { className: 'corpus-card-dates', textContent: `${exp.start_date} — ${exp.end_date || 'current'}` }));
  const metaText = `${exp.bullet_count_active} bullets` +
    (exp.bullet_count_pending ? ` · ${exp.bullet_count_pending} pending` : '');
  header.appendChild(_el('div', { className: 'corpus-card-meta', textContent: metaText }));
  card.appendChild(header);
  card.appendChild(_el('div', { className: 'corpus-card-body', id: `corpus-body-${exp.id}` }));
  return card;
}

async function toggleCorpusCard(experienceId) {
  const card = document.getElementById(`corpus-exp-${experienceId}`);
  if (!card) return;
  const willExpand = !card.classList.contains('expanded');
  card.classList.toggle('expanded');
  if (willExpand) await _loadCorpusDetail(experienceId);
}

async function _loadCorpusDetail(experienceId) {
  const body = document.getElementById(`corpus-body-${experienceId}`);
  if (!body) return;
  _setLoadingPlaceholder(body, 'Loading…');
  let res;
  try {
    res = await fetch(`/api/experiences/${experienceId}`);
  } catch (e) {
    _setLoadingPlaceholder(body, 'Network error.');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(body, 'Failed to load.');
    return;
  }
  _renderCorpusDetail(body, await res.json());
}

function _renderCorpusDetail(body, exp) {
  _clearChildren(body);
  const expId = exp.id;
  body.appendChild(_renderExperienceFieldGroup(expId, exp));
  const btnRow = _el('div', { className: 'form-row' });
  const hasPending = (exp.titles || []).some(t => t.is_pending_review) ||
    (exp.bullets || []).some(b => b.is_pending_review);
  if (hasPending) {
    const acceptAll = _el('button', {
      className: 'lcars-btn lcars-bg-teal',
      textContent: 'ACCEPT ALL PENDING',
    });
    acceptAll.onclick = async () => {
      try {
        const r = await _postJson(`/api/experiences/${expId}/accept-all`, {});
        _toast(`Accepted ${r.bullets_accepted} bullet(s) + ${r.titles_accepted} title(s)`);
        await _reloadCorpusCard(expId);
        await _refreshOnboardingBanner();
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    btnRow.appendChild(acceptAll);
  }
  const retire = _el('button', { className: 'lcars-btn lcars-bg-orange', textContent: 'SOFT-RETIRE EXPERIENCE' });
  retire.onclick = () => deleteExperience(expId);
  btnRow.appendChild(retire);
  body.appendChild(btnRow);
  body.appendChild(_renderTitleSection(expId, exp.titles || []));
  body.appendChild(_renderBulletSection(expId, exp.bullets || []));
}

function _renderExperienceFieldGroup(expId, exp) {
  const fg = _el('div', { className: 'corpus-fieldgroup' });
  const fields = [
    { key: 'company',    label: 'Company',         type: 'text',     value: exp.company || '' },
    { key: 'location',   label: 'Location',        type: 'text',     value: exp.location || '' },
    { key: 'start_date', label: 'Start (YYYY-MM)', type: 'text',     value: exp.start_date,
      pattern: '\\d{4}-\\d{2}' },
    { key: 'end_date',   label: 'End (YYYY-MM)',   type: 'text',     value: exp.end_date || '',
      pattern: '\\d{4}-\\d{2}', placeholder: '(blank = current)' },
    { key: 'summary',    label: 'Summary',         type: 'textarea', value: exp.summary || '' },
  ];
  fields.forEach(f => {
    const id = `exp-${expId}-${f.key}`;
    fg.appendChild(_el('label', { textContent: f.label, htmlFor: id }));
    const input = f.type === 'textarea'
      ? _el('textarea', { id, value: f.value })
      : _el('input', { id, type: f.type, value: f.value });
    if (f.type === 'textarea') input.textContent = f.value;
    else input.value = f.value;
    if (f.pattern) input.pattern = f.pattern;
    if (f.placeholder) input.placeholder = f.placeholder;
    input.addEventListener('change', () => _saveExperienceField(expId, f.key, input.value));
    fg.appendChild(input);
  });
  return fg;
}

function _renderTitleSection(expId, titles) {
  const sec = _el('div', { className: 'corpus-section' });
  const header = _el('div', { className: 'corpus-section-header' });
  header.appendChild(_el('div', { className: 'corpus-section-title', textContent: 'Titles' }));
  const addBtn = _el('button', { className: 'corpus-action-btn', textContent: '+ ADD TITLE' });
  addBtn.onclick = () => _addTitlePrompt(expId);
  header.appendChild(addBtn);
  sec.appendChild(header);
  if (titles.length === 0) {
    sec.appendChild(_el('div', { className: 'corpus-empty-experience',
      textContent: 'No titles. Add at least one official title for LLM use.' }));
    return sec;
  }
  titles.forEach(t => sec.appendChild(_renderTitleRow(expId, t)));
  return sec;
}

function _renderTitleRow(expId, title) {
  const row = _el('div', { className: 'corpus-row', id: `title-row-${title.id}` });
  const input = _el('input', { className: 'corpus-row-input', value: title.title });
  input.addEventListener('change', () =>
    _putJson(`/api/experience-titles/${title.id}`, { title: input.value })
      .then(updated => updated && _toast(`Title saved: ${updated.title}`))
      .catch(e => _toast('Save failed: ' + e.message, true))
  );
  row.appendChild(input);
  row.appendChild(_el('span', {
    className: 'corpus-row-flag' + (title.is_official ? ' official' : ''),
    textContent: title.is_official ? 'OFFICIAL' : 'ALT',
  }));
  if (title.is_pending_review) {
    row.appendChild(_el('span', { className: 'corpus-row-flag pending', textContent: 'PENDING' }));
  }
  const actions = _el('div', { className: 'corpus-row-actions' });
  if (title.is_pending_review) {
    const accept = _el('button', { className: 'corpus-action-btn', textContent: 'ACCEPT' });
    accept.onclick = async () => {
      try {
        await _postJson(`/api/experience-titles/${title.id}/accept`, {});
        await _reloadCorpusCard(expId);
        await _refreshOnboardingBanner();
        _toast('Title accepted');
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    actions.appendChild(accept);
  }
  if (!title.is_official) {
    const setOfficial = _el('button', { className: 'corpus-action-btn', textContent: 'SET OFFICIAL' });
    setOfficial.onclick = async () => {
      try {
        await _putJson(`/api/experience-titles/${title.id}`, { is_official: true });
        await _reloadCorpusCard(expId);
        _toast('Promoted to official');
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    actions.appendChild(setOfficial);
  }
  const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'DELETE' });
  del.onclick = async () => {
    if (!confirm('Mark this title non-eligible? Audit row will remain.')) return;
    try {
      await _deleteJson(`/api/experience-titles/${title.id}`);
      await _reloadCorpusCard(expId);
      _toast('Title retired');
    } catch (e) { _toast('Failed: ' + e.message, true); }
  };
  actions.appendChild(del);
  row.appendChild(actions);
  return row;
}

function _renderBulletSection(expId, bullets) {
  const sec = _el('div', { className: 'corpus-section' });
  const header = _el('div', { className: 'corpus-section-header' });
  header.appendChild(_el('div', { className: 'corpus-section-title', textContent: 'Bullets' }));
  const addBtn = _el('button', { className: 'corpus-action-btn', textContent: '+ ADD BULLET' });
  addBtn.onclick = () => _addBulletPrompt(expId);
  header.appendChild(addBtn);
  sec.appendChild(header);
  if (bullets.length === 0) {
    sec.appendChild(_el('div', { className: 'corpus-empty-experience', textContent: 'No active bullets.' }));
    return sec;
  }
  bullets.forEach(b => sec.appendChild(_renderBulletRow(expId, b)));
  return sec;
}

function _renderBulletRow(expId, bullet) {
  const row = _el('div', { className: 'corpus-row', id: `bullet-row-${bullet.id}` });
  const input = _el('textarea', { className: 'corpus-row-input' });
  input.rows = 2;
  input.value = bullet.text;
  input.addEventListener('change', async () => {
    try {
      const updated = await _putJson(`/api/bullets/${bullet.id}`, { text: input.value });
      const fresh = await fetch(`/api/experiences/${expId}`).then(r => r.json());
      const newRow = (fresh.bullets || []).find(b => b.id === bullet.id);
      if (newRow) row.replaceWith(_renderBulletRow(expId, newRow));
      _toast(`Bullet saved${updated.has_outcome ? ' (outcome detected)' : ''}`);
    } catch (e) { _toast('Save failed: ' + e.message, true); }
  });
  row.appendChild(input);
  const flag = _el('span', {
    className: 'corpus-row-flag ' + (bullet.has_outcome ? 'outcome' : 'no-outcome'),
    textContent: bullet.has_outcome ? 'OUTCOME' : 'NO OUTCOME',
  });
  flag.title = bullet.has_outcome
    ? 'A numeric outcome was detected (count, %, currency, duration).'
    : 'No measurable outcome — consider adding one.';
  row.appendChild(flag);
  if (bullet.is_pending_review) {
    row.appendChild(_el('span', { className: 'corpus-row-flag pending', textContent: 'PENDING' }));
  }
  const actions = _el('div', { className: 'corpus-row-actions' });
  if (bullet.is_pending_review) {
    const accept = _el('button', { className: 'corpus-action-btn', textContent: 'ACCEPT' });
    accept.onclick = async () => {
      try {
        await _postJson(`/api/bullets/${bullet.id}/accept`, {});
        await _reloadCorpusCard(expId);
        await _refreshOnboardingBanner();
        _toast('Bullet accepted');
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    actions.appendChild(accept);
  }
  const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'RETIRE' });
  del.onclick = async () => {
    if (!confirm('Soft-retire this bullet? It stays in the audit log but stops appearing in new applications.')) return;
    try {
      await _deleteJson(`/api/bullets/${bullet.id}`);
      await _reloadCorpusCard(expId);
      _toast('Bullet retired');
    } catch (e) { _toast('Failed: ' + e.message, true); }
  };
  actions.appendChild(del);
  row.appendChild(actions);
  return row;
}

async function _saveExperienceField(expId, field, value) {
  const body = {};
  body[field] = value;
  try {
    await _putJson(`/api/experiences/${expId}`, body);
    _toast(`${field} saved`);
  } catch (e) {
    _toast(`Save failed: ${e.message}`, true);
  }
}

async function _addTitlePrompt(expId) {
  const result = await openFormModal({
    title: 'ADD TITLE',
    subtitle: 'Add an alternate experience title.',
    submitLabel: 'ADD TITLE',
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true,
        placeholder: 'e.g. Director, AI Research' },
      { name: 'is_official', label: 'Role', type: 'select',
        options: [
          { value: 'alt', label: 'Alternate framing' },
          { value: 'official', label: 'Official title' },
        ], defaultValue: 'alt' },
    ],
    onSubmit: async (v) => {
      await _postJson(`/api/experiences/${expId}/titles`, {
        title: v.title.trim(),
        is_official: v.is_official === 'official',
      });
    },
  });
  if (!result) return;
  await _reloadCorpusCard(expId);
  _toast('Title added');
}

async function _addBulletPrompt(expId) {
  const result = await openFormModal({
    title: 'ADD BULLET',
    subtitle: 'Add a canonical bullet to this experience.',
    submitLabel: 'ADD BULLET',
    fields: [
      { name: 'text', label: 'Bullet text', type: 'textarea', required: true,
        placeholder: 'e.g. Reduced API latency by 40% by introducing connection pooling.' },
      { name: 'pattern', label: 'Pattern', type: 'select',
        options: [
          { value: '', label: '(none)' },
          { value: 'xyz', label: 'XYZ (accomplished X as measured by Y by doing Z)' },
          { value: 'car', label: 'CAR (challenge, action, result)' },
          { value: 'star', label: 'STAR' },
          { value: 'manual', label: 'Manual' },
        ], defaultValue: '' },
    ],
    onSubmit: async (v) => {
      const body = { text: v.text.trim() };
      if (v.pattern) body.pattern_kind = v.pattern;
      await _postJson(`/api/experiences/${expId}/bullets`, body);
    },
  });
  if (!result) return;
  await _reloadCorpusCard(expId);
  _toast('Bullet added');
}

async function _reloadCorpusCard(expId) {
  await _loadCorpusDetail(expId);
  await refreshCorpusSummaryFor(expId);
}

async function refreshCorpusSummaryFor(expId) {
  const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
  if (!res.ok) return;
  _corpusExperiences = await res.json();
  const exp = _corpusExperiences.find(e => e.id === expId);
  if (!exp) return;
  const card = document.getElementById(`corpus-exp-${expId}`);
  if (!card) return;
  const company = card.querySelector('.corpus-card-company');
  const title = card.querySelector('.corpus-card-title');
  const meta = card.querySelector('.corpus-card-meta');
  if (company) company.textContent = exp.company;
  if (title) title.textContent = exp.official_title || '(no official title)';
  if (meta) meta.textContent = `${exp.bullet_count_active} bullets` +
    (exp.bullet_count_pending ? ` · ${exp.bullet_count_pending} pending` : '');
  document.getElementById('corpusCount').textContent =
    `${_corpusExperiences.length} experience${_corpusExperiences.length === 1 ? '' : 's'}`;
}

async function deleteExperience(expId) {
  if (!confirm('Soft-retire this entire experience? All its bullets become inactive. Audit rows remain.')) return;
  try {
    const r = await _deleteJson(`/api/experiences/${expId}`);
    _toast(`Retired ${r.retired_bullets} bullet(s)`);
    await refreshCorpus();
  } catch (e) { _toast('Failed: ' + e.message, true); }
}

async function openCorpusAddExperience() {
  const result = await openFormModal({
    title: 'ADD EXPERIENCE',
    subtitle: 'New experience for the corpus.',
    submitLabel: 'ADD EXPERIENCE',
    fields: [
      { name: 'company',    label: 'Company',    type: 'text', required: true },
      { name: 'start_date', label: 'Start',      type: 'text', required: true,
        placeholder: 'YYYY-MM', pattern: '\\d{4}-\\d{2}' },
      { name: 'end_date',   label: 'End',        type: 'text',
        placeholder: 'YYYY-MM (blank = current)', pattern: '\\d{4}-\\d{2}' },
      { name: 'location',   label: 'Location',   type: 'text', placeholder: 'Remote / NYC / ...' },
      { name: 'summary',    label: 'Summary',    type: 'textarea',
        placeholder: 'Optional one-line context for this stint.' },
    ],
    onSubmit: async (v) => {
      await _postJson(`/api/users/${encodeURIComponent(currentUser)}/experiences`, {
        company: v.company.trim(),
        start_date: v.start_date,
        end_date: v.end_date || null,
        location: v.location.trim() || null,
        summary: v.summary.trim() || null,
      });
    },
  });
  if (!result) return;
  await refreshCorpus();
  _toast('Experience added');
}

async function _putJson(url, body) {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

async function _postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

async function _deleteJson(url) {
  const res = await fetch(url, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

// Tiny DOM constructor — avoids innerHTML for safety. Props can include
// className, id, textContent, htmlFor, value, type. Children is an array
// of child Nodes appended in order. Attrs is a flat object for ARIA etc.
function _el(tag, props = {}, children = [], attrs = {}) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null) continue;
    if (k === 'htmlFor') node.htmlFor = v;
    else if (k === 'className') node.className = v;
    else if (k === 'textContent') node.textContent = v;
    else if (k === 'id') node.id = v;
    else if (k === 'type') node.type = v;
    else if (k === 'value') node.value = v;
    else node[k] = v;
  }
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  children.forEach(c => node.appendChild(c));
  return node;
}

function _clearChildren(el) {
  if (!el) return;
  while (el.firstChild) el.removeChild(el.firstChild);
}

function _setLoadingPlaceholder(el, msg) {
  _clearChildren(el);
  el.appendChild(_el('div', { className: 'corpus-empty-experience', textContent: msg }));
}

function _toast(msg, isError) {
  let t = document.getElementById('_corpusToast');
  if (!t) {
    t = document.createElement('div');
    t.id = '_corpusToast';
    t.className = 'corpus-toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.toggle('error', !!isError);
  t.classList.add('show');
  clearTimeout(t._hide);
  t._hide = setTimeout(() => t.classList.remove('show'), 2400);
}

// Invalidate the corpus cache when the user changes — pin to onUserSelect.
const _origOnUserSelect = onUserSelect;
onUserSelect = async function() {
  _corpusLoadedForUser = '';
  _corpusExperiences = [];
  _personasLoaded = false;
  _memoryLoaded = false;
  _clearChildren(document.getElementById('corpusExperienceList'));
  return await _origOnUserSelect.apply(this, arguments);
};

// ===============================================================
// Phase D.5 — Candidate Memory tab
// ===============================================================

let _memoryLoaded = false;
let _memoryDebounce = null;

function _memoryTabActivated() {
  if (_memoryLoaded) return;
  _wireMemoryFilters();
  refreshMemory();
}

function _wireMemoryFilters() {
  const search = document.getElementById('memorySearch');
  const kindFilter = document.getElementById('memoryKindFilter');
  const outcomeOnly = document.getElementById('memoryOutcomeOnly');
  const incPromoted = document.getElementById('memoryIncludePromoted');
  if (search && !search._wired) {
    search.addEventListener('input', () => {
      clearTimeout(_memoryDebounce);
      _memoryDebounce = setTimeout(refreshMemory, 250);
    });
    search._wired = true;
  }
  [kindFilter, outcomeOnly, incPromoted].forEach(el => {
    if (el && !el._wired) {
      el.addEventListener('change', refreshMemory);
      el._wired = true;
    }
  });
}

async function refreshMemory() {
  const list = document.getElementById('memoryList');
  const countEl = document.getElementById('memoryCount');
  if (!currentUser) {
    _setLoadingPlaceholder(list, 'Select a user to view memory.');
    countEl.textContent = '0 entries';
    return;
  }
  const params = new URLSearchParams();
  const q = (document.getElementById('memorySearch').value || '').trim();
  if (q) params.set('q', q);
  const kind = document.getElementById('memoryKindFilter').value;
  if (kind) params.set('kind', kind);
  if (document.getElementById('memoryOutcomeOnly').checked) params.set('only_outcome_rich', '1');
  if (document.getElementById('memoryIncludePromoted').checked) params.set('include_promoted', '1');

  _setLoadingPlaceholder(list, 'Loading…');
  let res;
  try {
    res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/clarifications?${params}`,
    );
  } catch {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
  }
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    if (_needsOnboarding(res, data)) {
      countEl.textContent = '0 entries';
      _renderNeedsOnboarding(list, refreshMemory);
      return;
    }
  }
  if (res.status === 404) {
    _setLoadingPlaceholder(list, 'Candidate not in corpus yet.');
    countEl.textContent = '0 entries';
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load.');
    return;
  }
  const rows = await res.json();
  _memoryLoaded = true;
  countEl.textContent = `${rows.length} entr${rows.length === 1 ? 'y' : 'ies'}`;
  _clearChildren(list);
  if (rows.length === 0) {
    _setLoadingPlaceholder(list, 'No matching memory entries.');
    return;
  }
  rows.forEach(r => list.appendChild(_renderMemoryRow(r)));
}

function _renderMemoryRow(r) {
  const card = _el('div', { className: 'memory-card', id: `memory-${r.id}` });

  const header = _el('div', { className: 'memory-card-header' });
  header.appendChild(_el('span', { className: 'memory-card-kind', textContent: r.kind }));
  if (r.outcome_rich) {
    header.appendChild(_el('span', {
      className: 'corpus-row-flag outcome', textContent: 'OUTCOME',
    }));
  }
  if (r.is_promoted_to_bullet) {
    header.appendChild(_el('span', {
      className: 'memory-card-promoted', textContent: 'PROMOTED',
    }));
  }
  if (r.origin_application_title) {
    header.appendChild(_el('span', {
      className: 'memory-card-origin',
      textContent: `from: ${r.origin_application_title}`,
    }));
  }
  header.appendChild(_el('span', {
    className: 'application-card-date',
    textContent: _formatRelativeDate(r.created_at),
  }));
  card.appendChild(header);

  card.appendChild(_el('div', { className: 'memory-card-q', textContent: r.question }));
  card.appendChild(_el('div', { className: 'memory-card-a', textContent: r.answer }));

  if (!r.is_promoted_to_bullet) {
    const actions = _el('div', { className: 'memory-card-actions' });
    const promote = _el('button', {
      className: 'corpus-action-btn', textContent: 'PROMOTE TO BULLET',
    });
    promote.onclick = () => _promoteMemoryRow(r);
    actions.appendChild(promote);
    card.appendChild(actions);
  }
  return card;
}

async function _promoteMemoryRow(r) {
  // Workstream G: real dropdown picker replaces the numbered-prompt UX.
  if (!_corpusExperiences || _corpusExperiences.length === 0) {
    try {
      const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
      if (res.ok) _corpusExperiences = await res.json();
    } catch {}
  }
  if (!_corpusExperiences || _corpusExperiences.length === 0) {
    _toast('No experiences in corpus — add one in CAREER CORPUS first.', true);
    return;
  }
  const expOptions = _corpusExperiences.map(e => ({
    value: String(e.id),
    label: `${e.company} (${e.start_date} — ${e.end_date || 'present'})`,
  }));
  const result = await openFormModal({
    title: 'PROMOTE TO BULLET',
    subtitle: 'Pick which experience this Q&A should become a bullet under.',
    submitLabel: 'PROMOTE',
    fields: [
      { name: 'experience_id', label: 'Experience', type: 'select',
        required: true, options: expOptions,
        defaultValue: expOptions[0].value },
    ],
  });
  if (!result) return;
  const expId = parseInt(result.experience_id, 10);
  try {
    const res = await fetch(`/api/clarifications/${r.id}/promote-to-bullet`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ experience_id: expId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const targetExp = _corpusExperiences.find(e => e.id === expId);
    _toast(`Promoted to bullet on ${targetExp ? targetExp.company : 'experience'}`);
    await refreshMemory();
  } catch (e) {
    _toast('Promote failed: ' + e.message, true);
  }
}

// ===============================================================
// Phase D.6 — Onboarding banner: pending-review counts
// ===============================================================

async function _refreshOnboardingBanner() {
  const banner = document.getElementById('onboardingBanner');
  const text = document.getElementById('onboardingBannerText');
  if (!banner || !text || !currentUser) {
    if (banner) banner.classList.add('hidden');
    return;
  }
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/pending-counts`);
  } catch {
    banner.classList.add('hidden');
    return;
  }
  if (!res.ok) {
    banner.classList.add('hidden');
    return;
  }
  const data = await res.json();
  const total = (data.pending_bullets || 0) + (data.pending_titles || 0);
  if (total === 0) {
    banner.classList.add('hidden');
    return;
  }
  banner.classList.remove('hidden');
  const parts = [];
  if (data.pending_bullets) parts.push(`${data.pending_bullets} bullet${data.pending_bullets === 1 ? '' : 's'}`);
  if (data.pending_titles) parts.push(`${data.pending_titles} title${data.pending_titles === 1 ? '' : 's'}`);
  text.textContent = `${parts.join(' + ')} pending review across ${data.experiences_with_pending} experience${data.experiences_with_pending === 1 ? '' : 's'}`;
}

function scrollToFirstPending() {
  // Find the first experience card with a pending badge in its summary
  // and expand + scroll to it.
  const firstPending = _corpusExperiences.find(e => (e.bullet_count_pending || 0) > 0);
  if (!firstPending) {
    // Fall back: just find the first card with PENDING flag rendered
    const flag = document.querySelector('.corpus-row-flag.pending');
    if (flag) {
      const card = flag.closest('.corpus-card');
      if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    return;
  }
  const card = document.getElementById(`corpus-exp-${firstPending.id}`);
  if (!card) return;
  if (!card.classList.contains('expanded')) toggleCorpusCard(firstPending.id);
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===============================================================
// Workstream B1.2 — Corpus duplicates: find + merge
// ===============================================================

async function loadCorpusDuplicates() {
  const section = document.getElementById('duplicatesSection');
  const list = document.getElementById('duplicatesList');
  if (!currentUser || !section || !list) return;
  section.classList.remove('hidden');
  _setLoadingPlaceholder(list, 'Scanning for near-duplicates…');
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/duplicates`);
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
  }
  if (res.status === 409) {
    _setLoadingPlaceholder(list, 'Candidate not onboarded yet.');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load duplicates.');
    return;
  }
  const body = await res.json();
  _clearChildren(list);
  if (body.cluster_count === 0) {
    _setLoadingPlaceholder(list, 'No near-duplicate clusters found (threshold ' + body.threshold + ').');
    return;
  }
  list.appendChild(_el('div', {
    className: 'edit-hint',
    textContent: `${body.cluster_count} cluster${body.cluster_count === 1 ? '' : 's'} across ${body.experiences.length} experience${body.experiences.length === 1 ? '' : 's'} (threshold ${body.threshold}). Pick one bullet to keep per cluster; the others are soft-retired (audit rows survive).`,
  }));
  body.experiences.forEach(exp => list.appendChild(_renderDuplicateExp(exp)));
}

function _renderDuplicateExp(exp) {
  const wrap = _el('div', { className: 'compose-experience-card' });
  const header = _el('div', { className: 'compose-exp-header' });
  header.appendChild(_el('div', {
    className: 'compose-exp-company', textContent: exp.company || '(no company)',
  }));
  header.appendChild(_el('div', {
    className: 'compose-exp-dates',
    textContent: `${exp.start_date} — ${exp.end_date || 'current'}`,
  }));
  wrap.appendChild(header);
  exp.clusters.forEach((cluster, ci) => {
    const card = _el('div', { className: 'duplicate-cluster' });
    let keepId = cluster.recommended_keep;
    const groupName = `dup-${exp.id}-${ci}`;
    cluster.bullets.forEach(b => {
      const row = _el('label', { className: 'duplicate-row' });
      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = groupName;
      radio.value = String(b.id);
      if (b.id === keepId) radio.checked = true;
      radio.onchange = () => { keepId = b.id; };
      row.appendChild(radio);
      const meta = _el('span', { className: 'duplicate-meta' });
      if (b.has_outcome) {
        meta.appendChild(_el('span', {
          className: 'corpus-row-flag outcome', textContent: 'OUTCOME',
        }));
      }
      if (b.id === cluster.recommended_keep) {
        meta.appendChild(_el('span', {
          className: 'corpus-row-flag', textContent: 'RECOMMENDED',
        }));
      }
      row.appendChild(meta);
      row.appendChild(_el('span', { className: 'duplicate-text', textContent: b.text }));
      card.appendChild(row);
    });
    const actions = _el('div', { className: 'form-row', style: 'margin-top:8px' });
    const mergeBtn = _el('button', {
      className: 'lcars-btn lcars-bg-orange', textContent: 'KEEP SELECTED · RETIRE OTHERS',
    });
    mergeBtn.onclick = async () => {
      const toRetire = cluster.bullets.filter(b => b.id !== keepId).map(b => b.id);
      mergeBtn.disabled = true;
      try {
        for (const bid of toRetire) {
          await _deleteJson(`/api/bullets/${bid}`);
        }
        _toast(`Retired ${toRetire.length} duplicate bullet(s)`);
        card.style.opacity = '0.4';
        card.style.pointerEvents = 'none';
      } catch (e) {
        _toast('Merge failed: ' + e.message, true);
        mergeBtn.disabled = false;
      }
    };
    actions.appendChild(mergeBtn);
    card.appendChild(actions);
    wrap.appendChild(card);
  });
  return wrap;
}

// ===============================================================
// Phase D.3 — Applications list (within the APPLICATION tab)
// ===============================================================

async function refreshApplications() {
  const list = document.getElementById('applicationsList');
  const countEl = document.getElementById('applicationsCount');
  if (!list) return;
  if (!currentUser) {
    _setLoadingPlaceholder(list, 'Select a user to view their applications.');
    if (countEl) countEl.textContent = '0 applications';
    return;
  }
  _setLoadingPlaceholder(list, 'Loading…');
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/applications`);
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
  }
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    if (_needsOnboarding(res, data)) {
      if (countEl) countEl.textContent = '0 applications';
      _renderNeedsOnboarding(list, refreshApplications);
      return;
    }
  }
  if (res.status === 404) {
    _setLoadingPlaceholder(list, `No applications yet for ${currentUser}. Analyze a JD below to start one.`);
    if (countEl) countEl.textContent = '0 applications';
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load applications.');
    return;
  }
  const apps = await res.json();
  _renderApplicationsList(apps);
}

function _renderApplicationsList(apps) {
  const list = document.getElementById('applicationsList');
  const countEl = document.getElementById('applicationsCount');
  _clearChildren(list);
  if (countEl) countEl.textContent = `${apps.length} application${apps.length === 1 ? '' : 's'}`;
  if (apps.length === 0) {
    _setLoadingPlaceholder(list, 'No applications yet. Analyze a JD below to start one.');
    return;
  }
  apps.forEach(a => list.appendChild(_renderApplicationCard(a)));
}

function _renderApplicationCard(app) {
  const card = _el('div', { className: 'application-card', id: `app-card-${app.id}` });
  const header = _el('div', { className: 'application-card-header' });
  header.appendChild(_el('div', { className: 'application-card-title', textContent: app.title }));
  if (app.company) {
    header.appendChild(_el('div', { className: 'application-card-company', textContent: app.company }));
  }
  card.appendChild(header);

  const meta = _el('div', { className: 'application-card-meta' });
  meta.appendChild(_el('span', {
    className: `app-status-chip status-${app.status}`,
    textContent: (app.status || 'draft').toUpperCase(),
  }));
  const iterText = `${app.iteration_count} iter${app.iteration_count === 1 ? '' : 's'}`;
  meta.appendChild(_el('span', { className: 'application-card-iter', textContent: iterText }));
  if (app.pending_proposals > 0) {
    const badge = _el('span', {
      className: 'application-card-pending',
      textContent: `${app.pending_proposals} pending`,
    });
    badge.title = 'Pending LLM-proposed bullets/titles awaiting your review';
    meta.appendChild(badge);
  }
  meta.appendChild(_el('span', {
    className: 'application-card-date',
    textContent: _formatRelativeDate(app.updated_at),
  }));
  card.appendChild(meta);
  card.onclick = () => _showApplicationDetail(app.id);
  return card;
}

function _formatRelativeDate(iso) {
  if (!iso) return '';
  try {
    const then = new Date(iso);
    const diffMs = Date.now() - then.getTime();
    const diffMin = Math.round(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.round(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.round(diffHr / 24);
    if (diffDay < 30) return `${diffDay}d ago`;
    return then.toISOString().slice(0, 10);
  } catch {
    return iso;
  }
}

async function _showApplicationDetail(applicationId) {
  let res;
  try {
    res = await fetch(`/api/applications/${applicationId}`);
  } catch (e) {
    _toast('Failed to load application: ' + e.message, true);
    return;
  }
  if (!res.ok) {
    _toast('Application not found', true);
    return;
  }
  const detail = await res.json();
  // Lightweight info display in the toast for now — resuming an
  // application into the live editing flow ships in D.3.1.
  const lines = [
    `Title: ${detail.title}`,
    `Status: ${detail.status}`,
    `Iterations: ${detail.runs.length}`,
  ];
  if (detail.runs.length > 0) {
    const last = detail.runs[detail.runs.length - 1];
    lines.push(`Last run: ${last.run_id} (iter ${last.iteration})`);
    if (last.ats_roundtrip_status) lines.push(`ATS check: ${last.ats_roundtrip_status}`);
    if (last.pending_proposals > 0) lines.push(`Pending: ${last.pending_proposals}`);
  }
  _toast(lines.join(' · '));
}

// ===============================================================
// Phase D.4 — Persona Templates tab
// ===============================================================

let _personasLoaded = false;
let _personaUploadLocked = false;

function _personaTabActivated() {
  if (_personasLoaded) return;
  refreshPersonas();
}

async function refreshPersonas() {
  await Promise.all([_loadBundledPersonas(), _loadOwnedPersonas()]);
  _personasLoaded = true;
  // Unlock upload button if a user is selected
  const btn = document.getElementById('btnUploadPersona');
  if (btn) btn.disabled = !currentUser;
}

async function _loadBundledPersonas() {
  const grid = document.getElementById('personaBundledGrid');
  if (!grid) return;
  _setLoadingPlaceholder(grid, 'Loading bundled gallery…');
  let res;
  try {
    res = await fetch('/api/personas/bundled');
  } catch {
    _setLoadingPlaceholder(grid, 'Network error.');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(grid, 'Failed to load bundled.');
    return;
  }
  const rows = await res.json();
  _clearChildren(grid);
  rows.forEach(p => grid.appendChild(_renderPersonaCard(p, /*owned=*/false)));
}

async function _loadOwnedPersonas() {
  const grid = document.getElementById('personaOwnedGrid');
  if (!grid) return;
  if (!currentUser) {
    _setLoadingPlaceholder(grid, 'Select a user to view uploads.');
    return;
  }
  _setLoadingPlaceholder(grid, 'Loading…');
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/personas`);
  } catch {
    _setLoadingPlaceholder(grid, 'Network error.');
    return;
  }
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    if (_needsOnboarding(res, data)) {
      _renderNeedsOnboarding(grid, _loadOwnedPersonas);
      return;
    }
  }
  if (res.status === 404) {
    _setLoadingPlaceholder(grid, 'No DB record for this user yet. Onboarding creates one on first import.');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(grid, 'Failed to load.');
    return;
  }
  const body = await res.json();
  _clearChildren(grid);
  const owned = body.owned || [];
  if (owned.length === 0) {
    _setLoadingPlaceholder(grid, 'No uploaded templates yet. Use UPLOAD below.');
    return;
  }
  owned.forEach(p => grid.appendChild(_renderPersonaCard(p, /*owned=*/true)));
}

function _renderPersonaCard(p, owned) {
  const card = _el('div', { className: 'persona-card', id: `persona-card-${p.id}` });
  const title = _el('div', { className: 'persona-card-name', textContent: p.name });
  card.appendChild(title);
  if (p.description) {
    card.appendChild(_el('div', { className: 'persona-card-desc', textContent: p.description }));
  }
  const meta = _el('div', { className: 'persona-card-meta' });
  meta.appendChild(_el('span', {
    className: 'persona-card-source ' + (owned ? 'owned' : 'bundled'),
    textContent: owned ? 'YOURS' : 'BUNDLED',
  }));
  if (p.is_default) {
    meta.appendChild(_el('span', { className: 'persona-card-default', textContent: 'DEFAULT' }));
  }
  meta.appendChild(_el('span', { className: 'persona-card-path', textContent: p.path }));
  card.appendChild(meta);

  const actions = _el('div', { className: 'persona-card-actions' });
  const dl = _el('button', { className: 'corpus-action-btn', textContent: 'DOWNLOAD' });
  dl.onclick = () => window.open(`/api/personas/${p.id}/download`, '_blank');
  actions.appendChild(dl);

  const prev = _el('button', {
    className: 'corpus-action-btn', textContent: 'PREVIEW WITH MY RESUME',
  });
  prev.onclick = () => _previewPersonaWithResume(p.id, p.name);
  actions.appendChild(prev);

  if (owned) {
    const rename = _el('button', { className: 'corpus-action-btn', textContent: 'RENAME' });
    rename.onclick = () => _renamePersona(p.id, p.name);
    actions.appendChild(rename);

    const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'DELETE' });
    del.onclick = () => _deletePersona(p.id, p.name);
    actions.appendChild(del);
  }
  card.appendChild(actions);
  return card;
}

async function _renamePersona(id, currentName) {
  const next = prompt('New name:', currentName);
  if (!next || next.trim() === currentName) return;
  try {
    await _putJson(`/api/personas/${id}`, { name: next.trim() });
    _toast('Renamed');
    await _loadOwnedPersonas();
  } catch (e) {
    _toast('Rename failed: ' + e.message, true);
  }
}

async function _deletePersona(id, name) {
  if (!confirm(`Delete ${name}? The .docx file is removed from disk.`)) return;
  try {
    await _deleteJson(`/api/personas/${id}`);
    _toast('Deleted');
    await _loadOwnedPersonas();
  } catch (e) {
    _toast('Delete failed: ' + e.message, true);
  }
}

async function uploadPersonaFromInput(input) {
  if (_personaUploadLocked) return;
  const file = input.files && input.files[0];
  if (!file) return;
  if (!currentUser) {
    _toast('Select a user before uploading.', true);
    input.value = '';
    return;
  }
  if (!file.name.toLowerCase().endsWith('.docx')) {
    _toast('Only .docx files allowed.', true);
    input.value = '';
    return;
  }
  const name = (document.getElementById('personaUploadName').value || '').trim();
  const fd = new FormData();
  fd.append('file', file);
  if (name) fd.append('name', name);
  _personaUploadLocked = true;
  try {
    const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/personas`, {
      method: 'POST', body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    _toast('Uploaded');
    document.getElementById('personaUploadName').value = '';
    await _loadOwnedPersonas();
  } catch (e) {
    _toast('Upload failed: ' + e.message, true);
  } finally {
    _personaUploadLocked = false;
    input.value = '';
  }
}

// ===============================================================
// Workstream E — Wizard navigation (rail over the existing panels)
// ===============================================================

let _wizardStep = 1;
// Workstream B1 reorder: Job+Analyze → Clarify → Compose → Template → Generate → Download.
// Step 1 spans two panels (JD input + analysis results) because the user
// needs to see the analysis before advancing.
const _WIZARD_PANELS = {
  1: ['panelJD', 'panelAnalysis'],
  2: ['panelClarify'],
  3: ['panelCompose'],
  4: ['panelTemplate'],
  5: ['panelGenerate'],
  6: ['panelOutput'],
};

// Sentence-case labels for the six wizard steps — mirrored into the
// floating bottom statusbar's context line. Kept in JS (not derived from
// DOM) so it survives label edits in the rail without breaking the
// bottom-bar context.
const _WIZARD_STEP_LABELS = {
  1: 'Job + Analyze',
  2: 'Clarify',
  3: 'Compose',
  4: 'Template',
  5: 'Generate',
  6: 'Download',
};

function wizardInit() {
  const rail = document.getElementById('wizardRail');
  if (rail) rail.classList.remove('hidden');
  _wizardStep = 1;
  _wizardRender();
  // Reveal the floating bottom statusbar once the wizard engages.
  const sb = document.getElementById('cbStatusbar');
  if (sb) {
    sb.classList.add('is-visible');
    sb.setAttribute('aria-hidden', 'false');
  }
}

function _wizardReachable(step) {
  // Forward gating after B1 reorder:
  //   Step 1 always reachable; Step 2+ needs a successful analysis;
  //   Step 6 needs a successful generation.
  if (step >= 2 && !lastContextPath) return false;
  if (step >= 6 && !lastResumePath) return false;
  return true;
}

function wizardGoTo(step) {
  if (!_wizardReachable(step)) {
    _toast(step >= 6
      ? 'Generate the documents first.'
      : 'Run ANALYZE first (step 1).', true);
    return;
  }
  _wizardStep = step;
  _wizardRender();
  if (step === 3) loadComposition();
  if (step === 4) _loadTemplatePicker();
}

function wizardNext() { wizardGoTo(Math.min(6, _wizardStep + 1)); }
function wizardBack() { wizardGoTo(Math.max(1, _wizardStep - 1)); }

function _wizardRender() {
  // Show only the active step's panel(s); keep User/Applications/Config
  // visible as ambient context (they aren't wizard steps).
  const stepPanels = new Set(_WIZARD_PANELS[_wizardStep] || []);
  Object.values(_WIZARD_PANELS).flat().forEach(pid => {
    if (stepPanels.has(pid)) show(pid); else hide(pid);
  });
  document.querySelectorAll('.wizard-step').forEach(btn => {
    const s = parseInt(btn.dataset.wstep, 10);
    const isDone     = s < _wizardStep;
    const isActive   = s === _wizardStep;
    const isUpcoming = s > _wizardStep;
    btn.classList.toggle('active', isActive);
    btn.classList.toggle('done', isDone);
    btn.classList.toggle('upcoming', isUpcoming);
    btn.disabled = !_wizardReachable(s);
    // Swap the number for ✓ on done steps; restore the digit otherwise.
    // The original digit is read from data-wstep so we don't need to
    // store it separately. aria-hidden on the glyph keeps SR users on
    // the visible label.
    const num = btn.querySelector('.wizard-num');
    if (num) {
      num.textContent = isDone ? '✓' : btn.dataset.wstep;
      if (isDone) num.setAttribute('aria-hidden', 'true');
      else num.removeAttribute('aria-hidden');
    }
  });
  // Connector ink-trail: done = filled green, active-edge = the connector
  // leading INTO the active step (gradient + sheen sweep), else neutral.
  document.querySelectorAll('.wizard-connector').forEach(c => {
    const n = parseInt(c.dataset.conn, 10);
    c.classList.toggle('done', n < _wizardStep - 1);
    c.classList.toggle('active-edge', n === _wizardStep - 1);
  });
  // Bottom statusbar context: "Step 3 of 6 · Compose"
  const sbStep  = document.getElementById('cbStatusbarStep');
  const sbLabel = document.getElementById('cbStatusbarLabel');
  if (sbStep)  sbStep.textContent  = `Step ${_wizardStep} of 6`;
  if (sbLabel) sbLabel.textContent = _WIZARD_STEP_LABELS[_wizardStep] || '';
  const active = document.getElementById((_WIZARD_PANELS[_wizardStep] || [])[0]);
  if (active) active.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Advance the rail automatically as the underlying flow completes.
function _wizardAdvanceTo(step) {
  if (step > _wizardStep && _wizardReachable(step)) {
    _wizardStep = step;
  }
  _wizardRender();
}

// ===============================================================
// Workstream E — Step 3 Compose (fit-ranked bullets/titles)
// ===============================================================

let _composeApplicationId = null;

async function loadComposition() {
  const list = document.getElementById('composeList');
  if (!list) return;
  _setLoadingPlaceholder(list, 'Scoring corpus against this job…');
  if (_composeApplicationId == null) {
    _setLoadingPlaceholder(list, 'Run ANALYZE first.');
    return;
  }
  let res;
  try {
    res = await fetch(
      `/api/applications/${_composeApplicationId}/composition`
      + `?context_path=${encodeURIComponent(lastContextPath || '')}`,
    );
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load composition.');
    return;
  }
  const data = await res.json();
  _clearChildren(list);
  if (!data.experiences || data.experiences.length === 0) {
    _setLoadingPlaceholder(list, 'No corpus experiences to rank.');
    return;
  }
  data.experiences.forEach(exp => list.appendChild(_renderComposeCard(exp)));
}

// Pick the strongest bullets from a score-sorted list using a quality
// drop-off rule, replacing the prior hard top-5 fallback.
//
//   minKeep: always return at least this many (when available) — the
//            recruiter expects multiple bullets per role, so we don't
//            cut below 3 even if scores are flat.
//   maxKeep: never return more than this — even if all bullets are
//            equally strong, beyond 7 the eye glazes over.
//   ratio:   the drop-off threshold. After minKeep picks, stop once
//            the next pick scores below `ratio × median(picks-so-far)`.
//            0.65 catches obvious step-downs without being trigger-
//            happy on uniformly-strong corpora.
//
// Mirrors the prompt-side "quality over quantity" rule so the fallback
// path and the LLM path have the same shape (3-7 with drop-off).
// Input is expected to be sorted by score descending (the
// /api/applications/<id>/composition route already sorts that way).
function _dropoffPick(bullets, { minKeep = 3, maxKeep = 7, ratio = 0.65 } = {}) {
  if (!bullets || bullets.length === 0) return [];
  const sorted = bullets.slice().sort((a, b) => (b.score || 0) - (a.score || 0));
  const kept = sorted.slice(0, Math.min(minKeep, sorted.length));
  for (let i = minKeep; i < Math.min(sorted.length, maxKeep); i++) {
    const median = kept[Math.floor(kept.length / 2)].score || 0;
    const candidate = sorted[i].score || 0;
    if (median > 0 && candidate < median * ratio) break;
    kept.push(sorted[i]);
  }
  return kept;
}

// Workstream G+I: two-line Compose row, recommended-only by default,
// per-experience drawer for "find more bullets".
function _renderComposeCard(exp) {
  const card = _el('div', { className: 'compose-experience-card' });
  const header = _el('div', { className: 'compose-exp-header' });
  header.appendChild(_el('div', {
    className: 'compose-exp-company',
    textContent: exp.company || '(no company)',
  }));
  header.appendChild(_el('div', {
    className: 'compose-exp-dates',
    textContent: `${exp.start_date} — ${exp.end_date || 'current'}`,
  }));
  card.appendChild(header);

  if (exp.rationale) {
    card.appendChild(_el('div', {
      className: 'compose-exp-rationale', textContent: exp.rationale,
    }));
  }

  // Titles section
  if ((exp.titles || []).length) {
    card.appendChild(_el('div', {
      className: 'compose-exp-section-title', textContent: 'Titles (by fit)',
    }));
    exp.titles.forEach(t => card.appendChild(_renderTitleRow_compose(t)));
  }

  // Bullets split into visible (recommended/pinned/added) + drawer (rest).
  const visible = (exp.bullets || []).filter(
    b => b.recommended || b.pinned || b.added,
  );
  const hidden = (exp.bullets || []).filter(
    b => !(b.recommended || b.pinned || b.added),
  );
  // Fallback when no LLM recommendations exist (call failed or returned
  // empty for this experience): pick 3-7 bullets by score with a
  // drop-off cut so the tail doesn't include obviously weaker picks.
  const fallback = _dropoffPick(hidden, { minKeep: 3, maxKeep: 7, ratio: 0.65 });
  const headerLabel = exp.has_recommendations
    ? `Recommended bullets (${visible.length})`
    : `Top bullets (${visible.length || fallback.length})`;
  card.appendChild(_el('div', {
    className: 'compose-exp-section-title', textContent: headerLabel,
  }));
  let initial = visible;
  if (!exp.has_recommendations && initial.length === 0) {
    initial = fallback;
    initial.forEach(b => b._fallback = true);
  }
  initial.forEach(b => card.appendChild(_renderBulletRow_compose(b)));

  // Drawer: remaining bullets, searchable. v1: client-side filter.
  if (hidden.length > 0) {
    const drawerBullets = initial.length
      ? hidden.filter(b => !initial.includes(b))
      : hidden.slice(fallback.length);  // when fallback consumed the strongest
    if (drawerBullets.length) {
      const toggle = _el('button', {
        className: 'compose-drawer-toggle',
        textContent: `+ FIND MORE BULLETS IN ${exp.company.toUpperCase()} (${drawerBullets.length})`,
      });
      const drawer = _el('div', { className: 'compose-drawer hidden' });
      const toolbar = _el('div', { className: 'compose-drawer-toolbar' });
      const search = _el('input', {
        className: 'compose-drawer-search', type: 'search',
      });
      search.placeholder = 'Search this experience…';
      toolbar.appendChild(search);
      drawer.appendChild(toolbar);
      const rowsHost = _el('div');
      drawer.appendChild(rowsHost);
      drawerBullets.forEach(b => rowsHost.appendChild(_renderBulletRow_compose(b)));
      toggle.onclick = () => {
        drawer.classList.toggle('hidden');
        if (!drawer.classList.contains('hidden')) search.focus();
      };
      search.addEventListener('input', () => {
        const q = search.value.toLowerCase().trim();
        rowsHost.querySelectorAll('.compose-row').forEach(r => {
          const b = r._bulletState;
          const txt = (b.text || '').toLowerCase();
          const tagHits = (b.tags || []).some(
            t => (t.value || '').includes(q) ||
                 (t.display_value || '').toLowerCase().includes(q),
          );
          const match = !q || txt.includes(q) || tagHits;
          r.classList.toggle('hidden', !match);
        });
      });
      card.appendChild(toggle);
      card.appendChild(drawer);
    }
  }
  return card;
}

function _renderTitleRow_compose(t) {
  const row = _el('div', { className: 'compose-row' });
  row.appendChild(_el('span', { className: 'row-text', textContent: t.title }));
  const meta = _el('div', { className: 'row-meta' });
  meta.appendChild(_el('span', {
    className: 'score-chip', textContent: String(Math.round(t.score)),
  }));
  if (t.is_official) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag official', textContent: 'OFFICIAL',
    }));
  }
  const tagWrap = _el('span', { className: 'tag-chip-wrap' });
  _renderTagChips(tagWrap, 'title', t.id, t.tags || []);
  meta.appendChild(tagWrap);
  row.appendChild(meta);
  return row;
}

function _renderBulletRow_compose(b) {
  const row = _el('div', { className: 'compose-row' });
  if (b.recommended) row.classList.add('recommended');
  if (b.pinned)     row.classList.add('pinned');
  if (b.excluded)   row.classList.add('excluded');
  row._bulletState = b;

  row.appendChild(_el('div', { className: 'row-text', textContent: b.text }));

  // Actions (top-right)
  const actions = _el('div', { className: 'row-actions' });
  const pin = _el('button', {
    className: 'corpus-action-btn' + (b.pinned ? ' on' : ''),
    textContent: b.pinned ? 'PINNED' : 'PIN',
  });
  const exc = _el('button', {
    className: 'corpus-action-btn delete' + (b.excluded ? ' on' : ''),
    textContent: b.excluded ? 'EXCLUDED' : 'EXCLUDE',
  });
  // Toggle "add" only for non-recommended bullets reached via drawer;
  // recommended/already-added bullets always count as added.
  const addBtn = _el('button', {
    className: 'corpus-action-btn' + (b.added ? ' on' : ''),
    textContent: b.added ? 'ADDED' : '+ ADD',
  });
  if (b.recommended) addBtn.style.display = 'none';
  pin.onclick = () => {
    b.pinned = !b.pinned;
    if (b.pinned) b.excluded = false;
    _refreshComposeRow(row);
  };
  exc.onclick = () => {
    b.excluded = !b.excluded;
    if (b.excluded) { b.pinned = false; b.added = false; }
    _refreshComposeRow(row);
  };
  addBtn.onclick = () => {
    b.added = !b.added;
    if (b.added) b.excluded = false;
    _refreshComposeRow(row);
  };
  actions.appendChild(pin);
  actions.appendChild(exc);
  if (!b.recommended) actions.appendChild(addBtn);
  row.appendChild(actions);

  // Metadata line (score, outcome, tags)
  const meta = _el('div', { className: 'row-meta' });
  meta.appendChild(_el('span', {
    className: 'score-chip', textContent: String(Math.round(b.score)),
  }));
  if (b.recommended) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag', textContent: 'RECOMMENDED',
      style: 'background:var(--success);color:var(--bg-0);',
    }));
  }
  if (b._fallback) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag',
      textContent: 'Fallback pick',
    }));
  }
  if (b.has_outcome) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag outcome', textContent: 'OUTCOME',
    }));
  }
  if (b.is_pending_review) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag pending', textContent: 'PENDING',
    }));
  }
  const tagWrap = _el('span', { className: 'tag-chip-wrap' });
  _renderTagChips(tagWrap, 'bullet', b.id, b.tags || []);
  meta.appendChild(tagWrap);
  row.appendChild(meta);
  return row;
}

function _refreshComposeRow(row) {
  const b = row._bulletState;
  if (!b) return;
  row.classList.toggle('pinned', !!b.pinned);
  row.classList.toggle('excluded', !!b.excluded);
  const actions = row.querySelector('.row-actions');
  if (!actions) return;
  const btns = actions.querySelectorAll('button');
  if (btns[0]) {
    btns[0].textContent = b.pinned ? 'PINNED' : 'PIN';
    btns[0].classList.toggle('on', !!b.pinned);
  }
  if (btns[1]) {
    btns[1].textContent = b.excluded ? 'EXCLUDED' : 'EXCLUDE';
    btns[1].classList.toggle('on', !!b.excluded);
  }
  if (btns[2]) {
    btns[2].textContent = b.added ? 'ADDED' : '+ ADD';
    btns[2].classList.toggle('on', !!b.added);
  }
}

async function saveCompositionThenNext() {
  if (_composeApplicationId == null) { wizardGoTo(4); return; }
  const pinned = [];
  const excluded = [];
  const added = [];
  document.querySelectorAll('#composeList .compose-row').forEach(row => {
    const b = row._bulletState;
    if (!b) return;
    if (b.pinned) pinned.push(b.id);
    if (b.excluded) excluded.push(b.id);
    if (b.added) added.push(b.id);
  });
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/composition`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context_path: lastContextPath, pinned, excluded, added,
        }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    _toast(`Composition saved (${pinned.length} pinned, ${added.length} added, ${excluded.length} excluded)`);
  } catch (e) {
    _toast('Save failed: ' + e.message, true);
    return;
  }
  wizardGoTo(4);
}

// ===============================================================
// Workstream E — shared tag-chip component (Compose + Career Corpus)
// ===============================================================

function _renderTagChips(container, subjectKind, subjectId, tags) {
  _clearChildren(container);
  (tags || []).forEach(t => {
    const chip = _el('span', { className: 'tag-chip' });
    chip.appendChild(_el('span', { textContent: t.display_value || t.value }));
    const x = _el('button', {
      className: 'tag-chip-x', textContent: '×',
    });
    x.title = 'Remove tag';
    x.onclick = async (e) => {
      e.stopPropagation();
      try {
        await _deleteJson(
          `/api/${subjectKind === 'bullet' ? 'bullets' : 'experience-titles'}`
          + `/${subjectId}/tags/${t.id}`,
        );
        chip.remove();
      } catch (err) { _toast('Remove failed: ' + err.message, true); }
    };
    chip.appendChild(x);
    container.appendChild(chip);
  });
  const add = _el('button', { className: 'tag-chip-add', textContent: '+ tag' });
  add.onclick = () => _openInlineTagComposer(add, subjectKind, subjectId);
  container.appendChild(add);
}

async function _promptAddTag(container, subjectKind, subjectId) {
  const value = prompt('Tag (e.g. "ai", "design-leadership"):');
  if (!value || !value.trim()) return;
  const kind = (prompt('Kind: role | domain | skill | tech', 'skill') || 'skill').trim();
  try {
    const tag = await _postJson(
      `/api/${subjectKind === 'bullet' ? 'bullets' : 'experience-titles'}`
      + `/${subjectId}/tags`,
      { value: value.trim(), kind },
    );
    // Re-render: append the new chip before the add button
    const chip = _el('span', { className: 'tag-chip' });
    chip.appendChild(_el('span', { textContent: tag.display_value || tag.value }));
    const x = _el('button', { className: 'tag-chip-x', textContent: '×' });
    x.onclick = async (e) => {
      e.stopPropagation();
      try {
        await _deleteJson(
          `/api/${subjectKind === 'bullet' ? 'bullets' : 'experience-titles'}`
          + `/${subjectId}/tags/${tag.id}`,
        );
        chip.remove();
      } catch (err) { _toast('Remove failed: ' + err.message, true); }
    };
    chip.appendChild(x);
    const addBtn = container.querySelector('.tag-chip-add');
    container.insertBefore(chip, addBtn);
    _toast('Tag added');
  } catch (e) {
    _toast('Add tag failed: ' + e.message, true);
  }
}

// ===============================================================
// Workstream E — Step 5 persona picker + preview
// ===============================================================

let _selectedPersonaId = null;

async function _loadPersonaOptions() {
  // Kept as a thin wrapper for any callers that still want options
  // populated without the card UI. Workstream B1 introduces the card
  // picker as the primary UX; both share the same hidden <select> as
  // state and the same /api/users/<u>/personas fetch.
  return _loadTemplatePicker();
}

async function _loadTemplatePicker() {
  const sel = document.getElementById('personaSelect');
  const list = document.getElementById('templatePickList');
  if (!sel || !currentUser) return;
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/personas`);
  } catch {
    if (list) _setLoadingPlaceholder(list, 'Failed to load templates.');
    return;
  }
  if (!res.ok) {
    if (list) _setLoadingPlaceholder(list, 'Failed to load templates.');
    return;
  }
  const body = await res.json();
  // Populate the hidden <select> so _readSelectedPersonaId keeps working.
  while (sel.options.length > 1) sel.remove(1);
  const addOpt = (p, group) => {
    const o = document.createElement('option');
    o.value = String(p.id);
    o.textContent = `${group}: ${p.name}`;
    sel.appendChild(o);
  };
  (body.bundled || []).forEach(p => addOpt(p, 'Bundled'));
  (body.owned || []).forEach(p => addOpt(p, 'Yours'));

  // Render cards (Step 4 picker).
  if (!list) return;
  _clearChildren(list);
  const renderCard = (p, source) => {
    const card = _el('div', {
      className: 'persona-card template-pick-card', id: `tpl-card-${p.id}`,
    });
    if (String(p.id) === sel.value) card.classList.add('selected');
    card.appendChild(_el('div', { className: 'persona-card-name', textContent: p.name }));
    if (p.description) {
      card.appendChild(_el('div', { className: 'persona-card-desc', textContent: p.description }));
    }
    const meta = _el('div', { className: 'persona-card-meta' });
    meta.appendChild(_el('span', {
      className: 'persona-card-source ' + (source === 'YOURS' ? 'owned' : 'bundled'),
      textContent: source,
    }));
    card.appendChild(meta);
    const actions = _el('div', { className: 'persona-card-actions' });
    const pickBtn = _el('button', {
      className: 'lcars-btn lcars-bg-teal',
      textContent: String(p.id) === sel.value ? '✓ SELECTED' : 'USE THIS',
    });
    pickBtn.onclick = () => {
      sel.value = String(p.id);
      _selectedPersonaId = p.id;
      list.querySelectorAll('.template-pick-card').forEach(c => {
        c.classList.toggle('selected', c.id === `tpl-card-${p.id}`);
        const btn = c.querySelector('.lcars-btn.lcars-bg-teal');
        if (btn) btn.textContent = (c.id === `tpl-card-${p.id}`) ? '✓ SELECTED' : 'USE THIS';
      });
      // β.4 — re-render live preview with the newly-picked template.
      // No LLM call, no Chromium subprocess; the iframe just swaps
      // src to a URL whose only delta is template_id=<new>.
      _refreshLivePreview(p.id);
    };
    actions.appendChild(pickBtn);
    const preview = _el('button', {
      className: 'corpus-action-btn',
      textContent: 'PREVIEW WITH MY RESUME',
    });
    preview.onclick = () => _previewPersonaWithResume(p.id, p.name);
    actions.appendChild(preview);
    card.appendChild(actions);
    return card;
  };
  (body.bundled || []).forEach(p => list.appendChild(renderCard(p, 'BUNDLED')));
  (body.owned || []).forEach(p => list.appendChild(renderCard(p, 'YOURS')));
  // Default-select the first bundled card if nothing selected.
  if (!sel.value && (body.bundled || []).length) {
    sel.value = String(body.bundled[0].id);
    _selectedPersonaId = body.bundled[0].id;
    const first = document.getElementById(`tpl-card-${body.bundled[0].id}`);
    if (first) {
      first.classList.add('selected');
      const btn = first.querySelector('.lcars-btn.lcars-bg-teal');
      if (btn) btn.textContent = '✓ SELECTED';
    }
  }

  // β.4 — kick off the live preview for whatever template ends up
  // selected. The preview iframe will fetch and render; if no résumé
  // has been generated yet (no JSON Resume sidecar on disk), the
  // route returns 409 and we surface the "generate at least once"
  // hint instead of the frame.
  if (sel.value) _refreshLivePreview(parseInt(sel.value, 10));
}

// β.4 — refresh the embedded live preview iframe for the current
// application + the given template id. Idempotent: safe to call on
// step entry, on template-card click, and after a fresh generate
// (when the sidecar lands).
async function _refreshLivePreview(templateId) {
  const block = document.getElementById('livePreviewBlock');
  const frame = document.getElementById('livePreviewFrame');
  const empty = document.getElementById('livePreviewEmpty');
  if (!block || !frame || !empty) return;
  if (_composeApplicationId == null) {
    block.classList.add('hidden');
    return;
  }
  block.classList.remove('hidden');

  // Probe with HEAD-like GET to detect the 409 (no sidecar yet) case
  // before setting the iframe src — gives us a clean empty-state
  // message instead of an iframe full of JSON error text.
  const url = `/api/applications/${_composeApplicationId}/preview?template_id=${templateId}`;
  let probe;
  try {
    probe = await fetch(url, { method: 'GET' });
  } catch {
    empty.classList.remove('hidden');
    empty.textContent = 'Could not reach the preview server.';
    frame.classList.add('hidden');
    return;
  }
  if (probe.status === 409) {
    // No JSON Resume sidecar yet — user hasn't generated.
    empty.classList.remove('hidden');
    empty.textContent = 'Generate at least once in Step 5 to unlock the live preview.';
    frame.classList.add('hidden');
    return;
  }
  if (!probe.ok) {
    empty.classList.remove('hidden');
    empty.textContent = `Preview unavailable (${probe.status}).`;
    frame.classList.add('hidden');
    return;
  }
  // Happy path — load the URL directly into the iframe.
  empty.classList.add('hidden');
  frame.classList.remove('hidden');
  frame.src = url;
}

function _readSelectedPersonaId() {
  const sel = document.getElementById('personaSelect');
  if (!sel || !sel.value) return null;
  const n = parseInt(sel.value, 10);
  return Number.isNaN(n) ? null : n;
}

async function _previewPersonaWithResume(personaId, name) {
  if (!currentUser) { _toast('Select a user first', true); return; }
  _toast(`Rendering your resume with ${name}…`);
  let res;
  try {
    res = await fetch(`/api/personas/${personaId}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: currentUser }),
    });
  } catch (e) {
    return _toast('Preview failed: ' + e.message, true);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return _toast(err.error || `Preview failed (HTTP ${res.status})`, true);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `preview_${name}.docx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ===============================================================
// Workstream G — generic form modal (replaces prompt() chains)
// ===============================================================

// openFormModal({
//   title, subtitle, submitLabel, fields: [{name,label,type,required,
//     placeholder,options:[{value,label}],defaultValue}], onSubmit(values)
// }) -> Promise that resolves with the entered values or null on cancel.
function openFormModal(opts) {
  return new Promise((resolve) => {
    const modal = document.getElementById('formModal');
    const titleEl = document.getElementById('formModalTitle');
    const subEl = document.getElementById('formModalSubtitle');
    const body = document.getElementById('formModalBody');
    const submit = document.getElementById('formModalSubmit');
    const trigger = document.activeElement;
    if (!modal || !body) { resolve(null); return; }

    titleEl.textContent = opts.title || 'FORM';
    subEl.textContent = opts.subtitle || '';
    submit.textContent = opts.submitLabel || 'SAVE';
    _clearChildren(body);

    const inputs = {};
    (opts.fields || []).forEach(f => {
      const id = `formModal_${f.name}`;
      body.appendChild(_el('label', { htmlFor: id, textContent: f.label }));
      let input;
      if (f.type === 'textarea') {
        input = _el('textarea', { id });
        if (f.defaultValue) input.value = f.defaultValue;
      } else if (f.type === 'select') {
        input = _el('select', { id });
        (f.options || []).forEach(o => {
          const opt = document.createElement('option');
          opt.value = o.value; opt.textContent = o.label;
          if (o.value === f.defaultValue) opt.selected = true;
          input.appendChild(opt);
        });
      } else {
        input = _el('input', { id, type: f.type || 'text' });
        if (f.defaultValue) input.value = f.defaultValue;
      }
      if (f.placeholder) input.placeholder = f.placeholder;
      if (f.required) input.required = true;
      if (f.pattern) input.pattern = f.pattern;
      body.appendChild(input);
      inputs[f.name] = input;
    });
    const errRow = _el('div', { className: 'form-row-error', id: 'formModalError' });
    body.appendChild(errRow);

    const focusable = modal.querySelectorAll('button, input, textarea, select');
    const cleanup = (result) => {
      modal.classList.add('hidden');
      modal.removeEventListener('keydown', onKey);
      submit.onclick = null;
      dismissers.forEach(b => b.removeEventListener('click', onCancel));
      if (trigger && typeof trigger.focus === 'function') trigger.focus();
      resolve(result);
    };
    const onCancel = () => cleanup(null);
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); cleanup(null); return; }
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault(); submit.click(); return;
      }
      if (e.key !== 'Tab' || focusable.length === 0) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    submit.onclick = async () => {
      const vals = {};
      for (const f of opts.fields || []) {
        const v = inputs[f.name].value;
        if (f.required && !String(v || '').trim()) {
          errRow.textContent = `${f.label} is required`;
          inputs[f.name].focus();
          return;
        }
        if (f.pattern && v && !new RegExp(`^${f.pattern}$`).test(v)) {
          errRow.textContent = `${f.label} doesn't match the expected format`;
          inputs[f.name].focus();
          return;
        }
        vals[f.name] = v;
      }
      errRow.textContent = '';
      // Caller can optionally validate / return false to keep modal open
      if (opts.onSubmit) {
        try {
          const ok = await opts.onSubmit(vals);
          if (ok === false) return;  // keep modal open
        } catch (e) {
          errRow.textContent = e.message || 'Save failed';
          return;
        }
      }
      cleanup(vals);
    };

    const dismissers = Array.from(modal.querySelectorAll('[data-form-dismiss]'));
    dismissers.forEach(b => b.addEventListener('click', onCancel));
    modal.addEventListener('keydown', onKey);
    modal.classList.remove('hidden');
    const firstInput = body.querySelector('input,textarea,select');
    if (firstInput) firstInput.focus();
  });
}

// ===============================================================
// Workstream G — inline tag composer (replaces _promptAddTag)
// ===============================================================

let _tagDatalistId = '_tagSuggestList';

async function _ensureTagDatalist() {
  let list = document.getElementById(_tagDatalistId);
  if (!list) {
    list = document.createElement('datalist');
    list.id = _tagDatalistId;
    document.body.appendChild(list);
  }
  if (!currentUser) return list;
  try {
    const r = await fetch(`/api/users/${encodeURIComponent(currentUser)}/tags?limit=100`);
    if (!r.ok) return list;
    const rows = await r.json();
    _clearChildren(list);
    rows.forEach(t => {
      const o = document.createElement('option');
      o.value = t.display_value || t.value;
      list.appendChild(o);
    });
  } catch {}
  return list;
}

function _openInlineTagComposer(addBtn, subjectKind, subjectId) {
  // addBtn is the "+ tag" button; replace it with an inline composer until
  // the user submits or cancels. Datalist auto-fills from /api/users/<u>/tags.
  const parent = addBtn.parentNode;
  if (!parent) return;
  const composer = _el('span', { className: 'tag-composer' });
  const input = _el('input', { type: 'text' });
  input.setAttribute('list', _tagDatalistId);
  input.placeholder = 'tag value';
  const kind = _el('select');
  ['skill', 'role', 'domain', 'tech'].forEach(k => {
    const o = document.createElement('option');
    o.value = k; o.textContent = k;
    kind.appendChild(o);
  });
  const go = _el('button', { className: 'tag-composer-go', textContent: 'ADD' });
  const cancel = _el('button', { className: 'tag-composer-cancel', textContent: '×' });
  composer.appendChild(input); composer.appendChild(kind);
  composer.appendChild(go); composer.appendChild(cancel);
  parent.replaceChild(composer, addBtn);
  _ensureTagDatalist();
  input.focus();

  const restore = () => parent.replaceChild(addBtn, composer);
  cancel.onclick = restore;
  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); restore(); }
    else if (e.key === 'Enter') { e.preventDefault(); go.click(); }
  });
  go.onclick = async () => {
    const v = input.value.trim();
    if (!v) { input.focus(); return; }
    go.disabled = true;
    try {
      const tag = await _postJson(
        `/api/${subjectKind === 'bullet' ? 'bullets' : 'experience-titles'}`
        + `/${subjectId}/tags`,
        { value: v, kind: kind.value },
      );
      const chip = _el('span', { className: 'tag-chip' });
      chip.appendChild(_el('span', { textContent: tag.display_value || tag.value }));
      const x = _el('button', { className: 'tag-chip-x', textContent: '×' });
      x.onclick = async (ev) => {
        ev.stopPropagation();
        try {
          await _deleteJson(
            `/api/${subjectKind === 'bullet' ? 'bullets' : 'experience-titles'}`
            + `/${subjectId}/tags/${tag.id}`,
          );
          chip.remove();
        } catch (err) { _toast('Remove failed: ' + err.message, true); }
      };
      chip.appendChild(x);
      parent.insertBefore(chip, composer);
      restore();
      _toast('Tag added');
    } catch (e) {
      _toast('Add failed: ' + e.message, true);
      go.disabled = false;
    }
  };
}
