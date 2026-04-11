/* Frontend logic — vanilla JS, fetch API.
   P8 Human Gate: workflow enforces review at two points. */

let currentUser = '';
let currentConfig = {};
let lastContextPath = '';
let lastResumePath = '';
let lastCoverLetterPath = '';
let lastResumeFormat = '.docx';

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  loadUsers();
  setupDropZone();
  document.getElementById('userSelect').addEventListener('change', onUserSelect);
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
    return;
  }
  currentUser = username;
  await loadConfig();
  await loadResumes();
  show('panelConfig');
  show('panelResume');
  show('panelJD');
  hide('panelAnalysis');
  hide('panelOutput');
  setStatus('READY');
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
}

async function saveConfig() {
  const config = {
    name: document.getElementById('cfgName').value,
    email: document.getElementById('cfgEmail').value,
    phone: document.getElementById('cfgPhone').value,
    linkedin_url: document.getElementById('cfgLinkedin').value,
    website_url: document.getElementById('cfgWebsite').value,
    portfolio_urls: currentConfig.portfolio_urls || [],
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
  if (!res.ok) {
    const err = await res.json();
    setStatus('ERROR');
    return alert(err.error || 'Upload failed');
  }
  setStatus('UPLOADED');
  await loadResumes();
}

async function loadResumes() {
  const res = await fetch(`/api/users/${currentUser}/resumes`);
  const files = await res.json();
  const list = document.getElementById('resumeList');
  const sel = document.getElementById('resumeSelect');

  list.innerHTML = '';
  sel.innerHTML = '<option value="">-- Select Resume --</option>';

  files.forEach(f => {
    const chip = document.createElement('span');
    chip.className = 'file-chip';

    const nameSpan = document.createElement('span');
    nameSpan.textContent = f;
    chip.appendChild(nameSpan);

    const badge = document.createElement('span');
    badge.className = 'resume-source-badge';
    badge.textContent = 'SOURCE';
    chip.appendChild(badge);

    chip.onclick = () => {
      document.querySelectorAll('.file-chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      sel.value = f;
    };
    list.appendChild(chip);

    const opt = document.createElement('option');
    opt.value = f;
    opt.textContent = f;
    sel.appendChild(opt);
  });

  // Auto-select latest resume from config and highlight the chip
  if (currentConfig.latest_resume && files.includes(currentConfig.latest_resume)) {
    sel.value = currentConfig.latest_resume;
    list.querySelectorAll('.file-chip').forEach(c => {
      if (c.querySelector('span').textContent === currentConfig.latest_resume) {
        c.classList.add('selected');
      }
    });
  }
}

// ---- Analysis (P8 Gate #1) ----
async function runAnalysis() {
  const resume = document.getElementById('resumeSelect').value;
  const jd = document.getElementById('jdText').value.trim();
  if (!resume) return alert('Select a resume');
  if (!jd) return alert('Paste a job description');

  setStatus('ANALYZING');
  document.getElementById('btnAnalyze').disabled = true;

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: currentUser,
        resume_filename: resume,
        job_description: jd,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus('ERROR');
      return alert(data.error || 'Analysis failed');
    }
    lastContextPath = data.context_path;
    renderAnalysis(data);
    show('panelAnalysis');
    setStatus('ANALYSIS COMPLETE');
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

// ---- Generation (P8 Gate #2) ----
async function runGeneration() {
  if (!lastContextPath) return alert('Run analysis first');

  setStatus('GENERATING');
  document.getElementById('btnGenerate').disabled = true;

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: currentUser,
        context_path: lastContextPath,
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
    renderOutput(data);
    show('panelOutput');
    setStatus('GENERATION COMPLETE');
    document.getElementById('panelOutput').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    setStatus('ERROR');
    alert('Generation failed: ' + e.message);
  } finally {
    document.getElementById('btnGenerate').disabled = false;
  }
}

function renderOutput(data) {
  document.getElementById('resumePreview').innerText = data.resume_preview || '';
  document.getElementById('coverLetterPreview').innerText = data.cover_letter_preview || '';

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
}

function showTab(name, clickedBtn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const tabId = name === 'coverLetter' ? 'tabCoverLetter' : name === 'changes' ? 'tabChanges' : 'tabResume';
  document.getElementById(tabId).classList.add('active');
  // Activate button: use the passed reference, or find by tab name
  if (clickedBtn) {
    clickedBtn.classList.add('active');
  } else {
    const btnIndex = name === 'coverLetter' ? 1 : name === 'changes' ? 2 : 0;
    const btns = document.querySelectorAll('.tab-btn');
    if (btns[btnIndex]) btns[btnIndex].classList.add('active');
  }
}

async function downloadResume() {
  const content = document.getElementById('resumePreview').innerText;
  await _downloadEdited('/api/download-edited', {
    username: currentUser,
    content,
    type: 'resume',
    original_format: lastResumeFormat,
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

// ---- Helpers ----
function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }
function hideAllPanels() {
  ['panelConfig', 'panelResume', 'panelJD', 'panelAnalysis', 'panelOutput'].forEach(hide);
}

function setStatus(text) {
  const pill = document.getElementById('statusPill');
  pill.textContent = text;
  if (text.includes('ANALYZING') || text.includes('GENERATING') || text.includes('UPLOADING')) {
    pill.className = 'lcars-pill lcars-amber loading';
  } else if (text.includes('ERROR')) {
    pill.className = 'lcars-pill';
    pill.style.background = 'var(--red)';
    pill.style.color = 'var(--black)';
  } else {
    pill.className = 'lcars-pill lcars-amber';
    pill.style.background = '';
    pill.style.color = '';
  }
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
