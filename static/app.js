/* Frontend logic — vanilla JS, fetch API.
   P8 Human Gate: workflow enforces review at two points. */

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
  await loadResumes();
  show('panelApplications');
  show('panelConfig');
  show('panelResume');
  show('panelJD');
  hide('panelAnalysis');
  hide('panelOutput');
  _resetIterationState();
  setStatus('READY');
  refreshApplications();
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

async function uploadFile(file) {
  if (!currentUser) return alert('Select a user first');
  const fd = new FormData();
  fd.append('username', currentUser);
  fd.append('file', file);

  setStatus('UPLOADING');
  const res = await fetch('/api/upload', { method: 'POST', body: fd });
  const uploadData = await res.json();
  if (!res.ok) {
    setStatus('ERROR');
    return alert(uploadData.error || 'Upload failed');
  }
  setStatus('UPLOADED');
  // If a whitelist exists, auto-include the new file so it defaults to SOURCE
  if (currentConfig.included_resumes && !currentConfig.included_resumes.includes(uploadData.filename)) {
    currentConfig = Object.assign({}, currentConfig, {
      included_resumes: [...currentConfig.included_resumes, uploadData.filename],
    });
    await fetch(`/api/users/${currentUser}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentConfig),
    });
  }
  await loadResumes();
}

async function loadResumes() {
  const res = await fetch(`/api/users/${currentUser}/resumes`);
  const files = await res.json();
  const list = document.getElementById('resumeList');
  const sel = document.getElementById('resumeSelect');

  list.innerHTML = '';
  sel.innerHTML = '<option value="">-- Select Resume --</option>';

  // Whitelist: null = all included (key absent from config = first use default)
  const includedSet = currentConfig.included_resumes
    ? new Set(currentConfig.included_resumes)
    : null;

  files.forEach(f => {
    const isIncluded = includedSet === null || includedSet.has(f);

    const chip = document.createElement('span');
    chip.className = 'file-chip';
    chip.dataset.filename = f;

    // Left zone: click filename = set as primary resume
    const nameSpan = document.createElement('span');
    nameSpan.textContent = f;
    nameSpan.style.cursor = 'pointer';
    chip.appendChild(nameSpan);

    // Divider between zones
    const divider = document.createElement('span');
    divider.className = 'chip-divider';
    chip.appendChild(divider);

    // Right zone: badge toggles include/exclude
    const badge = document.createElement('span');
    badge.className = 'resume-source-badge' + (isIncluded ? '' : ' excluded');
    badge.textContent = isIncluded ? '✓ SOURCE' : '✗ EXCL';
    badge.title = isIncluded ? 'Click to exclude from source pool' : 'Click to include in source pool';
    chip.appendChild(badge);

    nameSpan.addEventListener('click', () => {
      document.querySelectorAll('.file-chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      sel.value = f;
      _savePrimaryResume(f);
    });

    badge.addEventListener('click', e => {
      e.stopPropagation();
      const nowExcluded = badge.classList.toggle('excluded');
      badge.textContent = nowExcluded ? '✗ EXCL' : '✓ SOURCE';
      badge.title = nowExcluded ? 'Click to include in source pool' : 'Click to exclude from source pool';
      _saveIncludedResumes();
    });

    list.appendChild(chip);

    const opt = document.createElement('option');
    opt.value = f;
    opt.textContent = f;
    sel.appendChild(opt);
  });

  // Auto-select latest resume from config and highlight the chip
  if (currentConfig.latest_resume && files.includes(currentConfig.latest_resume)) {
    sel.value = currentConfig.latest_resume;
    primaryResume = currentConfig.latest_resume;
    list.querySelectorAll('.file-chip').forEach(c => {
      if (c.dataset.filename === currentConfig.latest_resume) c.classList.add('selected');
    });
  }
}

async function _saveIncludedResumes() {
  const included = [];
  document.querySelectorAll('.file-chip').forEach(chip => {
    const badge = chip.querySelector('.resume-source-badge');
    if (badge && !badge.classList.contains('excluded')) {
      included.push(chip.dataset.filename);
    }
  });
  const config = Object.assign({}, currentConfig, { included_resumes: included });
  const res = await fetch(`/api/users/${currentUser}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (res.ok) currentConfig = config;
}

async function _savePrimaryResume(filename) {
  primaryResume = filename;
  const config = Object.assign({}, currentConfig, { latest_resume: filename });
  const res = await fetch(`/api/users/${currentUser}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (res.ok) currentConfig = config;
}

function setOutputFormat(fmt, btn) {
  outputFormat = fmt;
  document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ---- Analysis (P8 Gate #1) ----
async function runAnalysis() {
  const resume = primaryResume || document.getElementById('resumeSelect').value;
  const jd = document.getElementById('jdText').value.trim();
  if (!resume) return alert('Select a primary resume from the Resume Upload panel');
  if (!jd) return alert('Paste a job description');

  setStatus('ANALYZING');
  document.getElementById('btnAnalyze').disabled = true;
  _resetClarifyUI();
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
        resume_filename: resume,
        job_description: jd,
        included_resumes: currentConfig.included_resumes ?? null,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus('ERROR');
      return alert(data.error || 'Analysis failed');
    }
    lastContextPath = data.context_path;
    lastTemplatePath = data.template_path || '';
    renderAnalysis(data);
    show('panelAnalysis');
    setStatus('ANALYSIS COMPLETE');
    _announce('Analysis complete. Review the analysis or skip to generation.');
    document.getElementById('panelAnalysis').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    setStatus('ERROR');
    alert('Analysis failed: ' + e.message);
  } finally {
    document.getElementById('btnAnalyze').disabled = false;
  }
}

function renderAnalysis(data) {
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
  const color = pct > 60 ? 'var(--teal)' : pct > 35 ? 'var(--amber)' : 'var(--red)';
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
      html += `<p style="color:var(--teal);font-size:13px;margin-bottom:4px">STRENGTHS</p><ul>`;
      a.comparison.strengths.forEach(s => { html += `<li>${esc(s)}</li>`; });
      html += `</ul>`;
    }
    if (a.comparison.gaps) {
      html += `<p style="color:var(--red);font-size:13px;margin:8px 0 4px">GAPS</p><ul>`;
      a.comparison.gaps.forEach(g => { html += `<li>${esc(g)}</li>`; });
      html += `</ul>`;
    }
    if (a.comparison.title_alignment) {
      html += `<p style="color:var(--amber);font-size:13px;margin-top:8px">TITLE ALIGNMENT: ${esc(a.comparison.title_alignment)}</p>`;
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
    html += `<div class="analysis-section"><h3>Overall Strategy</h3><p style="color:var(--light)">${esc(a.overall_strategy)}</p></div>`;
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
      setStatus('ERROR');
      if (btn) btn.disabled = false;
      return alert(data.error || 'Clarification failed');
    }
    lastClarifyQuestions = data.questions || [];
    _renderClarifyQuestions(lastClarifyQuestions, data.reasoning || '');
    setStatus('QUESTIONS READY');
    _announce(`${lastClarifyQuestions.length} clarifying question${lastClarifyQuestions.length === 1 ? '' : 's'} ready for review.`);
  } catch (e) {
    setStatus('ERROR');
    if (btn) btn.disabled = false;
    alert('Clarification failed: ' + e.message);
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

async function submitClarificationsAndGenerate() {
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
      setStatus('ERROR');
      if (btnSubmit) btnSubmit.disabled = false;
      return alert(data.error || 'Saving answers failed');
    }
  } catch (e) {
    setStatus('ERROR');
    if (btnSubmit) btnSubmit.disabled = false;
    return alert('Saving answers failed: ' + e.message);
  }

  // Proceed to generate with the now-saved clarifications on disk.
  await runGeneration();
  if (btnSubmit) btnSubmit.disabled = false;
}

async function skipClarifications() {
  // No answers submitted — clear any previously saved clarifications so the
  // generate call doesn't pick up stale answers from a prior run.
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
      // Non-fatal: generate works without this. Log and continue.
      console.warn('Failed to clear clarifications on skip:', e);
    }
  }
  await runGeneration();
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
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus('ERROR');
      return alert(data.error || 'Generation failed');
    }
    lastResumePath = data.resume_path;
    lastCoverLetterPath = data.cover_letter_path;
    lastResumeFormat = data.resume_format || '.docx';
    _onGenerationComplete(data);
    renderOutput(data);
    show('panelOutput');
    setStatus('GENERATION COMPLETE');
    _announce(`Iteration ${currentIteration} ready. Resume and cover letter generated.`);
    document.getElementById('panelOutput').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    setStatus('ERROR');
    alert('Generation failed: ' + e.message);
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
  pill.textContent = `ITER ${currentIteration}`;
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
      setStatus('ERROR');
      return;
    }
    lastResumePath = data.resume_path;
    lastCoverLetterPath = data.cover_letter_path;
    lastResumeFormat = data.resume_format || lastResumeFormat;
    _onGenerationComplete(data);
    renderOutput(data);
    setStatus('REFINED');
    _announce(`Iteration ${currentIteration} refined.`);
  } catch (e) {
    entry.status = 'rejected';
    entry.reason = 'Request failed: ' + e.message;
    _renderRefinementHistory();
    setStatus('ERROR');
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
      setStatus('ERROR');
      if (btn) btn.disabled = false;
      return alert(data.error || 'Iteration interview failed');
    }
    lastIterateClarifyQuestions = data.questions || [];
    _renderIterateClarifyQuestions(lastIterateClarifyQuestions, data.reasoning || '');
    setStatus('QUESTIONS READY');
    _announce(`${lastIterateClarifyQuestions.length} iteration question${lastIterateClarifyQuestions.length === 1 ? '' : 's'} ready for review.`);
  } catch (e) {
    setStatus('ERROR');
    if (btn) btn.disabled = false;
    alert('Iteration interview failed: ' + e.message);
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
      setStatus('ERROR');
      if (btn) btn.disabled = false;
      return alert(data.error || 'Saving answers failed');
    }
  } catch (e) {
    setStatus('ERROR');
    if (btn) btn.disabled = false;
    return alert('Saving answers failed: ' + e.message);
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

function renderOutput(data) {
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
    template_path: lastTemplatePath,
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
  el.classList.remove('hidden', 'collapsed');
  const block = document.querySelector(`[data-panel="${id}"]`);
  if (block) block.classList.remove('hidden', 'collapsed');
}
function hide(id) {
  document.getElementById(id).classList.add('hidden');
  const block = document.querySelector(`[data-panel="${id}"]`);
  if (block) block.classList.add('hidden');
}
function hideAllPanels() {
  ['panelConfig', 'panelResume', 'panelJD', 'panelAnalysis', 'panelOutput'].forEach(hide);
}

// Active states: pill and sidebar block flash together; idle states are solid.
// Maps each active state keyword to the panel whose block should flash.
const _ACTIVE_PANEL = {
  UPLOADING:  'panelResume',
  ANALYZING:  'panelAnalysis',
  GENERATING: 'panelOutput',
  REFINING:   'panelOutput',
};
let _activeBlock = null;  // sidebar block currently flashing; cleared on next call

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

function setStatus(text) {
  const pill = document.getElementById('statusPill');
  pill.textContent = text;

  // Clear previous sidebar flash; re-hide block if its panel never opened (e.g. error)
  if (_activeBlock) {
    _activeBlock.classList.remove('step-active');
    const prevPanel = document.getElementById(_activeBlock.dataset.panel);
    if (prevPanel && prevPanel.classList.contains('hidden')) {
      _activeBlock.classList.add('hidden');
    }
    _activeBlock = null;
  }
  // Clear any prior aria-busy state from the previously-active panel so
  // assistive tech stops announcing the panel as busy once work completes.
  document.querySelectorAll('.lcars-panel[aria-busy="true"]').forEach(p => {
    p.removeAttribute('aria-busy');
  });

  const activeKey = Object.keys(_ACTIVE_PANEL).find(s => text.includes(s));
  const isActive  = !!activeKey;
  const isError   = text.includes('ERROR');

  // Pill: amber + flashing when active, amber solid when idle, red solid on error
  pill.className        = 'lcars-pill' + (isError ? '' : ' lcars-amber') + (isActive ? ' pill-active' : '');
  pill.style.background = isError ? 'var(--red)' : '';
  pill.style.color      = isError ? 'var(--black)' : '';

  // Flash top-bar elbow in sync with pill
  const elbow = document.querySelector('.lcars-elbow-tl');
  if (elbow) elbow.classList.toggle('step-active', isActive);

  // Flash the sidebar block AND mark the active panel aria-busy so screen
  // readers can announce that work is in progress on that section.
  if (isActive) {
    const block = document.querySelector(`[data-panel="${_ACTIVE_PANEL[activeKey]}"]`);
    if (block) {
      block.classList.remove('hidden');
      block.classList.add('step-active');
      _activeBlock = block;
    }
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
function togglePanel(panelId) {
  const panel = document.getElementById(panelId);
  if (!panel || panel.classList.contains('hidden')) return;
  const isCollapsed = panel.classList.toggle('collapsed');
  const block = document.querySelector(`[data-panel="${panelId}"]`);
  if (block) block.classList.toggle('collapsed', isCollapsed);
}

document.querySelectorAll('.lcars-block[data-panel]').forEach(block => {
  block.addEventListener('click', () => togglePanel(block.dataset.panel));
});
document.querySelectorAll('.panel-header').forEach(header => {
  const panel = header.closest('.lcars-panel');
  if (panel) header.addEventListener('click', () => togglePanel(panel.id));
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
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
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
  const title = prompt('Alternate title (e.g. "Director, AI Research"):');
  if (!title) return;
  const makeOfficial = confirm('Mark as the official title? OK = official, Cancel = alternate.');
  try {
    await _postJson(`/api/experiences/${expId}/titles`, { title, is_official: makeOfficial });
    await _reloadCorpusCard(expId);
    _toast('Title added');
  } catch (e) { _toast('Add failed: ' + e.message, true); }
}

async function _addBulletPrompt(expId) {
  const text = prompt('Bullet text:');
  if (!text || !text.trim()) return;
  try {
    await _postJson(`/api/experiences/${expId}/bullets`, { text: text.trim() });
    await _reloadCorpusCard(expId);
    _toast('Bullet added');
  } catch (e) { _toast('Add failed: ' + e.message, true); }
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
  const company = prompt('Company name:');
  if (!company || !company.trim()) return;
  const start = prompt('Start date (YYYY-MM):');
  if (!start || !/^\d{4}-\d{2}$/.test(start)) {
    alert('Start date must be YYYY-MM (e.g. 2023-01)');
    return;
  }
  const end = prompt('End date (YYYY-MM, blank for current):') || '';
  if (end && !/^\d{4}-\d{2}$/.test(end)) {
    alert('End date must be YYYY-MM or blank');
    return;
  }
  const location = prompt('Location (optional):') || '';
  try {
    await _postJson(`/api/users/${encodeURIComponent(currentUser)}/experiences`, {
      company: company.trim(),
      start_date: start,
      end_date: end || null,
      location: location.trim() || null,
    });
    await refreshCorpus();
    _toast('Experience added');
  } catch (e) { _toast('Add failed: ' + e.message, true); }
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
  _clearChildren(document.getElementById('corpusExperienceList'));
  return await _origOnUserSelect.apply(this, arguments);
};

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
