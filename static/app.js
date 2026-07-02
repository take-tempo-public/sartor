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
let outputFormat = '.docx';  // user-selected résumé output format
let coverFormat = '.docx';   // user-selected cover-letter output format (Step 6, independent of the résumé)
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
  // Format-check the URL boxes (new-user form + Settings drawer).
  ['newLinkedin', 'newWebsite', 'cfgLinkedin', 'cfgWebsite'].forEach(
    id => _wireUrlField(document.getElementById(id)),
  );
  document.getElementById('refinementInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submitRefinement(); }
  });

  // sartor. top bar — drop a soft shadow once scrolled past 4px. Cheap
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

  // Sprint 6.5 — inject the in-app help (i)-circles, then maybe auto-open the
  // welcome modal once-ever on first view.
  _initHelp();
  _maybeAutoOpenHelp();
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

// Reveal the new-user form (don't toggle): hide the "New user" button so the
// only affordance left is the form itself, and focus the username box so the
// user can start typing immediately. Cancel (hideNewUserForm) restores it.
function showNewUserForm() {
  document.getElementById('newUserForm').classList.remove('hidden');
  const btn = document.getElementById('btnNewUser');
  if (btn) btn.classList.add('hidden');
  // Clear the dropdown so a previously-picked username doesn't sit stale above
  // the new-user fields (it reads as a heading for the form otherwise). The
  // selection is restored on Cancel (hideNewUserForm). currentUser/panels are
  // intentionally left alone — this is a label fix, not a context teardown.
  const sel = document.getElementById('userSelect');
  if (sel) sel.value = '';
  const u = document.getElementById('newUsername');
  if (u) u.focus();
  // KW3: the very first user on a fresh install → arm the new-user tour and
  // offer the "import a résumé to start" tip once (no-op for returning users —
  // _maybeFireTourStop gates on the armed flag).
  if (sel && sel.options.length <= 1) _armHelpTour();
  _maybeFireTourStop('tourAddUser', null);
}

const _NEW_USER_FIELDS = ['newUsername', 'newName', 'newEmail', 'newPhone', 'newLinkedin', 'newWebsite'];

function hideNewUserForm() {
  document.getElementById('newUserForm').classList.add('hidden');
  const btn = document.getElementById('btnNewUser');
  if (btn) btn.classList.remove('hidden');
  // Restore the dropdown to the active user (showNewUserForm cleared it) so
  // Cancel leaves the picker consistent with the still-loaded context.
  const sel = document.getElementById('userSelect');
  if (sel && currentUser) sel.value = currentUser;
  _NEW_USER_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.value = ''; el.classList.remove('field-invalid'); el.removeAttribute('aria-invalid'); }
  });
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
  for (const [id, label] of [['newLinkedin', 'LinkedIn URL'], ['newWebsite', 'Website URL']]) {
    const el = document.getElementById(id);
    if (!_isPlausibleUrl(el.value)) {
      el.classList.add('field-invalid');
      el.focus();
      return alert(`That ${label} doesn’t look right. Use e.g. linkedin.com/in/you (https:// optional), or leave it blank.`);
    }
  }
  data.linkedin_url = _normalizeUrl(data.linkedin_url);
  data.website_url = _normalizeUrl(data.website_url);

  const res = await fetch('/api/users', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    return alert(err.error || 'Failed to create user');
  }
  hideNewUserForm();  // hide form, clear inputs, restore the "New user" button
  _armHelpTour();     // KW3: a brand-new user → walk them through the first run
  await loadUsers();
  document.getElementById('userSelect').value = data.username;
  onUserSelect();
}

async function onUserSelect() {
  const username = document.getElementById('userSelect').value;
  const userPanel = document.getElementById('panelUser');
  if (!username) {
    currentUser = '';
    // Selection cleared → re-lock the box open so it can't be collapsed shut
    // with no user picked.
    if (userPanel) { userPanel.classList.remove('collapsed'); userPanel.classList.add('not-collapsible'); }
    hideAllPanels();
    _resetIterationState();
    return;
  }
  // A user is selected → the box now holds data, so allow it to be tucked away.
  if (userPanel) userPanel.classList.remove('not-collapsible');
  currentUser = username;
  await loadConfig();
  show('panelApplications');           // prep the Tailor tab's landing panel
  // panelConfig moved to the Settings drawer (Workstream B1.3); no longer
  // a flow panel. loadConfig() still populates the same #cfgX inputs
  // because the drawer hosts them via the same ids.
  // Smart landing (Sprint 6.4 #16/#1 + KW1): empty corpus → onboard on Career
  // corpus; populated corpus → straight to Tailor. switchTopTab('corpus', …)
  // lazy-loads the corpus; switchTopTab('tailor', …) is a no-op when already
  // active but keeps the routing explicit.
  const landing = await _landingTab();
  if (landing === 'corpus') _armHelpTour();  // empty corpus ⇒ new-user onboarding
  _activateTab(landing);
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

// Wordmark / logo click → route home: clear the selected user (onUserSelect's
// no-user branch hides the flow panels, re-locks the picker open, resets
// iteration state) and snap back to the landing tab so "home" is the same view
// a first-time user sees. Routed through _landingTab() — the single source of
// truth for "which tab is home." Because goHome deselects first, _landingTab()
// resolves to 'tailor' (the picker's home, in #tab-tailor), preserving the
// deselected landing view.
function goHome() {
  const sel = document.getElementById('userSelect');
  if (sel) sel.value = '';
  onUserSelect();                       // no-user branch = deselect + landing reset (sync)
  _landingTab().then(name => {
    _activateTab(name);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
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
    linkedin_url: _normalizeUrl(document.getElementById('cfgLinkedin').value),
    website_url: _normalizeUrl(document.getElementById('cfgWebsite').value),
    portfolio_urls: document.getElementById('cfgPortfolioUrls').value.split('\n').map(s => _normalizeUrl(s)).filter(Boolean),
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

// PX-02: opt-in fetch of the saved LinkedIn / website / portfolio URLs. Saves
// the config first (the server route reads the SAVED config), then POSTs to the
// scrape route, which caches the text into Candidate.online_profile_text for the
// LLM to use as context. Best-effort + graceful — never blocks anything.
async function fetchProfileContent() {
  const statusEl = document.getElementById('profileFetchStatus');
  const setMsg = (m) => { if (statusEl) statusEl.textContent = m; };
  setMsg('Saving config…');
  await saveConfig();
  setMsg('Fetching profile content…');
  try {
    const res = await fetch(`/api/users/${currentUser}/profile/fetch`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      setMsg(data.error || 'Fetch failed.');
      return;
    }
    if (data.urls === 0) {
      setMsg('No profile URLs to fetch — add LinkedIn / website / portfolio URLs above.');
    } else if (data.chars === 0) {
      setMsg(`Fetched nothing from ${data.urls} URL(s) — they may be unreachable or blocked.`);
    } else {
      setMsg(`Fetched ${data.chars} characters from ${data.urls} URL(s); the LLM will use it as context.`);
    }
  } catch {
    setMsg('Fetch failed (network error).');
  }
}

// ---- URL field format checking (onboarding + settings) ----
// Tolerant by design: a bare host like "linkedin.com/in/you" is valid. We
// normalize it (prepend https://) on the CLIENT before storing, so the value
// round-trips through validate_config without a "missing scheme" rejection; the
// server's scraper._ensure_scheme re-normalizes defensively at scrape time. We
// only flag input that can't be a URL at all.
const _URL_SCHEME_RE = /^[a-z][a-z0-9+.\-]*:\/\//i;

function _normalizeUrl(value) {
  const v = (value || '').trim();
  if (!v) return '';
  return _URL_SCHEME_RE.test(v) ? v : `https://${v}`;
}

function _isPlausibleUrl(value) {
  const v = (value || '').trim();
  if (!v) return true;  // empty is allowed — these fields are optional
  if (/\s/.test(v)) return false;
  try {
    const u = new URL(_normalizeUrl(v));
    // Require a dotted host — rules out "https://localhost"-style typos while
    // still accepting any real domain the user pastes.
    return !!u.hostname && u.hostname.includes('.');
  } catch {
    return false;
  }
}

// Live validation on a single URL input: red ring + aria-invalid on blur,
// cleared as soon as the user edits. Idempotent + null-safe.
function _wireUrlField(input) {
  if (!input) return;
  input.addEventListener('blur', () => {
    const ok = _isPlausibleUrl(input.value);
    input.classList.toggle('field-invalid', !ok);
    input.setAttribute('aria-invalid', ok ? 'false' : 'true');
  });
  input.addEventListener('input', () => {
    input.classList.remove('field-invalid');
    input.removeAttribute('aria-invalid');
  });
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
  // P2 — persistent busy banner + disable the import control so the user can't
  // re-trigger a second ingest (or wander off) while this ~20-40s call runs.
  _setBusy(true, `Importing ${file.name} and extracting your experience`);
  const ingestInput = document.getElementById('corpusIngestFile');
  if (ingestInput) ingestInput.disabled = true;
  if (out) out.textContent = `Extracting experiences from ${file.name}… (AI, ~$0.02)`;
  try {
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
    const errs = data.errors || [];
    if (!res.ok) {
      if (out) out.textContent = '';
      return reportError(
        'Corpus ingest', data.error || 'Ingest failed', errs.join('; ') || data.detail,
      );
    }
    const made = data.experiences_created || 0;
    const merged = data.experiences_merged || 0;
    const bullets = data.bullets_created || 0;
    const altTitles = data.alternate_titles_created || 0;

    // Honesty: a 2xx with nothing extracted is NOT a success. Tell the user
    // plainly and don't fire the green toast — otherwise the status pill reads
    // "ready" over an empty corpus (the exact "did it do anything?" confusion).
    if (made + merged === 0) {
      setStatus('NO EXPERIENCES FOUND');
      if (out) {
        out.textContent =
          `No experiences could be read from ${file.name}. ` +
          (errs.length
            ? errs.join('; ')
            : 'Make sure it’s a text résumé (not a scanned image) with ' +
              'month/year dates on each role.');
      }
      _toast('No experiences found in résumé', true);
      return;
    }

    setStatus('READY');
    if (out) {
      out.textContent =
        `Added ${made} experience(s), ${merged} merged into existing roles, ` +
        `${altTitles} alternate title(s), ${bullets} bullet(s) — now pending review below.`;
    }
    _toast('Resume ingested into corpus');
    // Render the new cards in place — the user is already on the Career Corpus
    // tab, so a "refetch next visit" flag isn't enough (the old bug: status said
    // ready but the list never updated). refreshCorpus() always refetches and
    // resets _corpusLoadedForUser itself.
    await refreshCorpus();
    // P1 — surface any "possible duplicate roles" the import created (same job,
    // drifted dates/title) so the user can merge or keep separate.
    await refreshMergeSuggestions();
    // KW3: first successful import → explain the corpus + what to do next. The
    // user is on the Career corpus tab, so re-open lives on panelCorpus's (i).
    _maybeFireTourStop('panelCorpus', document.getElementById('help-icon-panelCorpus'));
  } finally {
    _setBusy(false);
    if (ingestInput) ingestInput.disabled = false;
  }
}

function setOutputFormat(fmt, btn) {
  outputFormat = fmt;
  document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// Cover-letter format picker (Step 6, feat/cover-letter-formats). Independent of
// the résumé picker above — scoped to `.cover-format-btn` so the two don't clear
// each other's active state.
function setCoverFormat(fmt, btn) {
  coverFormat = fmt;
  document.querySelectorAll('.cover-format-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ---- Server-Sent Events helper (for streaming routes) ----
//
// EventSource doesn't support POST, and our analyze/generate/clarify
// payloads carry multi-KB JD/context that don't fit a query string. So
// we POST via fetch() and parse the SSE protocol manually off the
// response body. SSE frames are separated by blank lines; within each
// frame the lines are `event: <name>\n` and `data: <json>\n`.
//
// Calls onEvent(eventName, parsedData) for every complete frame.
// Returns when the stream ends or the server closes. Throws on
// network failure (caller's try/catch handles).
async function _consumeSSE(url, body, onEvent) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // Pre-stream error (4xx/409 etc.) — surface the JSON body the way
    // the non-streaming routes do so onboarding-modal / error toasts
    // still work.
    const errBody = await res.json().catch(() => ({}));
    onEvent('http_error', { status: res.status, body: errBody });
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by \n\n. Process all complete frames in
    // the buffer; keep any partial trailing frame for the next read.
    let sep;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (!frame.trim()) continue;
      let eventName = 'message';
      const dataLines = [];
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) eventName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6));
      }
      const raw = dataLines.join('\n');
      let parsed;
      try { parsed = JSON.parse(raw); }
      catch { parsed = raw; }
      onEvent(eventName, parsed);
    }
  }
}

// ---- Analysis (P8 Gate #1) ----
async function runAnalysis() {
  // DB-backed pipeline: the corpus is the source of truth. resume_filename
  // is ignored server-side (Phase C.4); no primary-resume gate anymore.
  const jd = document.getElementById('jdText').value.trim();
  if (!currentUser) return alert('Select a user first');
  if (!jd) return alert('Paste a job description');

  setStatus('ANALYZING');
  _setBusy(true, 'Analyzing the job description');
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

  // Stream tokens off /api/analyze/stream so the user can see we're alive
  // during the ~90s Sonnet call. The default UI is a spinner + a token
  // counter ("Received N tokens") inside the pending placeholder; a small
  // "Show progress" toggle reveals the raw stream for debugging or the
  // curious. The aria-live="polite" region announces analysis-complete
  // separately, so the spinner-by-default doesn't lose screen-reader signal.
  // On `done` we hide the placeholder and `_renderAnalysis` produces the
  // structured view.
  const pendingEl = document.getElementById('analysisPending');
  if (pendingEl) {
    _clearChildren(pendingEl);
    const status = _el('div', {
      className: 'edit-hint',
      id: 'analysisStreamStatus',
      textContent: 'Analyzing… (~30–60s)',
    });
    status.style.marginBottom = '6px';
    const counter = _el('div', {
      className: 'edit-hint',
      id: 'analysisStreamCounter',
      textContent: 'Received 0 tokens',
    });
    counter.style.opacity = '0.7';
    counter.style.fontSize = '12px';
    counter.style.marginBottom = '8px';
    const toggleBtn = _el('button', {
      id: 'analysisStreamToggle',
      className: 'cb-btn cb-bg-blue',
      textContent: 'Show progress',
    });
    toggleBtn.style.fontSize = '12px';
    toggleBtn.style.padding = '2px 10px';
    toggleBtn.onclick = () => {
      const pre = document.getElementById('analysisStreamPre');
      const btn = document.getElementById('analysisStreamToggle');
      if (!pre || !btn) return;
      const showing = !pre.classList.contains('hidden');
      pre.classList.toggle('hidden', showing);
      btn.textContent = showing ? 'Show progress' : 'Hide progress';
    };
    const streamPre = _el('pre', { id: 'analysisStreamPre', className: 'hidden' });
    streamPre.style.whiteSpace = 'pre-wrap';
    streamPre.style.maxHeight = '320px';
    streamPre.style.overflow = 'auto';
    streamPre.style.fontFamily = 'ui-monospace, Menlo, Consolas, monospace';
    streamPre.style.fontSize = '12px';
    streamPre.style.opacity = '0.9';
    streamPre.style.marginTop = '8px';
    pendingEl.appendChild(status);
    pendingEl.appendChild(counter);
    pendingEl.appendChild(toggleBtn);
    pendingEl.appendChild(streamPre);
  }

  try {
    let finalData = null;
    let httpError = null;
    let streamErr = null;
    let tokenCount = 0;
    await _consumeSSE(
      '/api/analyze/stream',
      { username: currentUser, job_description: jd },
      (eventName, payload) => {
        if (eventName === 'chunk') {
          // Quick coarse "tokens" proxy — Anthropic deltas typically carry
          // 1-4 characters each. We count chunks, not tokens, because we
          // can't see the model's token boundaries from text deltas. The
          // visible label says "tokens" because it's close enough for an
          // alive-indicator and the precise number doesn't matter.
          tokenCount += 1;
          const counterEl = document.getElementById('analysisStreamCounter');
          if (counterEl) counterEl.textContent = `Received ${tokenCount} tokens`;
          // Append to the (hidden by default) raw-stream view so the
          // "Show progress" toggle has something to reveal.
          const pre = document.getElementById('analysisStreamPre');
          if (pre) {
            pre.textContent += payload.text || '';
            if (!pre.classList.contains('hidden')) {
              pre.scrollTop = pre.scrollHeight;
            }
          }
        } else if (eventName === 'retry') {
          const status = document.getElementById('analysisStreamStatus');
          if (status) status.textContent = `Analyzing… (retrying: ${payload.reason})`;
          const pre = document.getElementById('analysisStreamPre');
          if (pre) pre.textContent += `\n\n[retry: ${payload.reason}]\n\n`;
        } else if (eventName === 'phase') {
          // Two-pass analyze emits a phase sentinel before each pass; swap the
          // status label so the user sees concrete progress (extraction is the
          // fast Haiku pass, synthesis is the long Sonnet pass).
          const status = document.getElementById('analysisStreamStatus');
          if (status) {
            const labels = {
              extraction: 'Extracting JD signals… (~10s)',
              synthesis: 'Analyzing positioning… (~50s)',
            };
            status.textContent = labels[payload && payload.phase] || 'Analyzing…';
          }
        } else if (eventName === 'done') {
          finalData = payload;
        } else if (eventName === 'error') {
          streamErr = payload;
        } else if (eventName === 'http_error') {
          httpError = payload;
        }
      },
    );

    if (httpError) {
      const { status, body } = httpError;
      return reportError('Analyze', body.error || 'Analysis failed', body.detail);
    }
    if (streamErr) {
      return reportError('Analyze', streamErr.error || 'Analysis failed', streamErr.detail);
    }
    if (!finalData) {
      return reportError('Analyze', 'Analysis stream ended without a result.');
    }

    lastContextPath = finalData.context_path;
    lastTemplatePath = finalData.template_path || '';
    _composeApplicationId = finalData.application_id ?? null;
    _renderAnalysis(finalData);
    show('panelAnalysis');
    // Reveal the Continue/Skip actions now that the analysis has
    // landed and lastContextPath is populated (so wizardGoTo(2/3)
    // passes _wizardReachable). Hide the in-flight placeholder.
    document.getElementById('analysisPending')?.classList.add('hidden');
    document.getElementById('analysisActions')?.classList.remove('hidden');
    // Re-render the wizard rail so step 2 (now _wizardReachable thanks
    // to lastContextPath) loses its disabled `upcoming` state. Without
    // this, the user has to click the in-flow Continue button to
    // refresh the rail — see the wizard-rail regression note in
    // docs/RELEASE_CHECKLIST.md.
    _wizardRender();
    // KW7: /api/analyze just created the Application row — re-render the
    // applications block so it stops showing the stale pre-analyze state.
    refreshApplications();
    setStatus('ANALYSIS COMPLETE');
    _announce('Analysis complete. Review it, then continue to clarify or skip to compose.');
    // Workstream B1 reorder: recommend no longer fires here. It fires
    // after the user submits or skips clarify (Step 2), so the
    // clarifications can inform the recommendation.
  } catch (e) {
    reportError('Analyze', 'Analysis request failed', e.message);
  } finally {
    _setBusy(false);
    document.getElementById('btnAnalyze').disabled = false;
    // Always clear the in-flight placeholder even if analyze errored —
    // leaving the streamed-tokens view up after a failure would be misleading.
    // The actions row stays gated on lastContextPath (only the success path
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

  // Hidden Qualities — each item is {category, signal} (analyzer 2026-06-01.1+).
  // Fall back to plain-string render for analyses saved before the schema change.
  if (a.hidden_qualities) {
    html += `<div class="analysis-section"><h3>Hidden Qualities Sought</h3><ul>`;
    a.hidden_qualities.forEach(q => {
      if (q && typeof q === 'object') {
        html += `<li><span class="tag tag-skill">${esc(q.category || 'context')}</span> ${esc(q.signal || '')}</li>`;
      } else {
        html += `<li>${esc(q)}</li>`;
      }
    });
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

// Finding #6: the analysis gate already presents the clarify-vs-skip choice
// ("Continue to Clarify →" / "Skip to Compose →"), so re-showing the
// "Get clarifying questions / Skip" row asked the same thing twice. The
// "Continue to Clarify →" CTA now initiates clarification in one action.
// Idempotency guard: if this analysis already produced questions, just show
// them — don't re-spend the /api/clarify LLM call on re-entry (back-nav,
// re-click). _resetClarifyUI() clears lastClarifyQuestions on every fresh
// analysis, so this signal is scoped to the current analysis. The manual
// #clarifyStartRow row still serves a direct rail click into Step 2.
function continueToClarify() {
  wizardGoTo(2);
  if (_wizardStep !== 2) return;            // reachability gate blocked nav
  if (lastClarifyQuestions.length) return;  // already fetched this analysis
  runClarify();
}

async function runClarify() {
  if (!lastContextPath) return alert('Run analysis first');
  setStatus('GENERATING QUESTIONS');
  // Hide the "Get clarifying questions / Skip" row for the duration of the
  // fetch: when runClarify is reached via the "Continue to Clarify →" CTA the
  // row is redundant (finding #6) and would otherwise flash; the pending
  // indicator fills the panel while the LLM call runs. _restore() puts the row
  // back on failure so the user can retry.
  const start = document.getElementById('clarifyStartRow');
  const pending = document.getElementById('clarifyPending');
  if (start) start.classList.add('hidden');
  if (pending) pending.classList.remove('hidden');
  const btn = document.getElementById('btnClarify');
  if (btn) btn.disabled = true;
  const _restore = () => {
    if (pending) pending.classList.add('hidden');
    if (start) start.classList.remove('hidden');
    if (btn) btn.disabled = false;
  };

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
      _restore();
      return reportError('Clarify', data.error || 'Clarification failed', data.detail);
    }
    if (pending) pending.classList.add('hidden');
    lastClarifyQuestions = data.questions || [];
    _renderClarifyQuestions(lastClarifyQuestions, data.reasoning || '');
    setStatus('QUESTIONS READY');
    _announce(`${lastClarifyQuestions.length} clarifying question${lastClarifyQuestions.length === 1 ? '' : 's'} ready for review.`);
  } catch (e) {
    _restore();
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
        merge: true,  // accumulate by id — never drop a prior round's answers
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
  // KW7 / B.8: the route mirrored these answers into candidate memory —
  // sync the panel so the Q&A shows up without a manual refresh.
  refreshMemory();
  await _fireRecommendThenCompose();
  if (btnSubmit) btnSubmit.disabled = false;
}

async function skipClarifications() {
  // No answers submitted — clear any previously saved clarifications so
  // recommend + generate don't pick up stale answers from a prior run.
  // merge:false makes this an explicit whole-map replace (the deliberate
  // "clear" path); submit paths use merge:true to accumulate by id instead.
  if (lastContextPath) {
    try {
      await fetch('/api/answer-clarifications', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          context_path: lastContextPath,
          username: currentUser,
          answers: {},
          merge: false,
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
        // Surface backend's detail field (the recommend route now
        // includes a traceback tail) via reportError so the cause is
        // copyable + the click-to-view path is consistent with other
        // 5xx surfacing. Also fire a quick toast so the user knows
        // the wizard is proceeding without curation.
        _toast(`Recommend failed: ${err.error || rec.status} — using top-5 fallback`, true);
        if (err.detail) {
          reportError('Recommend', err.error || `status ${rec.status}`, err.detail);
        }
        // Pre-fix (2026-05-26): on recommend failure the status pill
        // was left stuck at 'RECOMMENDING BULLETS' until something else
        // set it — the user saw "recommending bullets" on the wizard
        // for the entire rest of the flow including Template + Generate.
        // Reset to READY here so the pill reflects reality.
        setStatus('READY');
      } else {
        setStatus('RECOMMENDATIONS READY');
      }
    } catch (e) {
      _toast(`Recommend skipped: ${e.message} — using top-5 fallback`, true);
      setStatus('READY');
    }
  }
  wizardGoTo(3);
}

// ---- Generation (P8 Gate #2) ----
async function runGeneration() {
  if (!lastContextPath) return alert('Run analysis first');
  _maybeFireTourStop('tourGenerating', null);  // KW3: first Generate click

  setStatus('GENERATING');
  _setBusy(true, 'Generating your tailored résumé');
  document.getElementById('btnGenerate').disabled = true;

  // Build the streaming pending UI — same shape as runAnalysis(): a
  // spinner-style status line, a token counter, and a collapsible
  // "Show progress" toggle that reveals the raw streamed text for
  // debugging or curiosity. Default UI is clean (just status + counter);
  // the raw <pre> starts hidden and only opens on the toggle click.
  const pendingEl = document.getElementById('generatePending');
  if (pendingEl) {
    pendingEl.classList.remove('hidden');
    _clearChildren(pendingEl);
    const status = _el('div', {
      className: 'edit-hint',
      id: 'generateStreamStatus',
      textContent: 'Generating documents… (~30–60s)',
    });
    status.style.marginBottom = '6px';
    const counter = _el('div', {
      className: 'edit-hint',
      id: 'generateStreamCounter',
      textContent: 'Received 0 tokens',
    });
    counter.style.opacity = '0.7';
    counter.style.fontSize = '12px';
    counter.style.marginBottom = '8px';
    const toggleBtn = _el('button', {
      id: 'generateStreamToggle',
      className: 'cb-btn cb-bg-blue',
      textContent: 'Show progress',
    });
    toggleBtn.style.fontSize = '12px';
    toggleBtn.style.padding = '2px 10px';
    toggleBtn.onclick = () => {
      const pre = document.getElementById('generateStreamPre');
      const btn = document.getElementById('generateStreamToggle');
      if (!pre || !btn) return;
      const showing = !pre.classList.contains('hidden');
      pre.classList.toggle('hidden', showing);
      btn.textContent = showing ? 'Show progress' : 'Hide progress';
    };
    const streamPre = _el('pre', { id: 'generateStreamPre', className: 'hidden' });
    streamPre.style.whiteSpace = 'pre-wrap';
    streamPre.style.maxHeight = '320px';
    streamPre.style.overflow = 'auto';
    streamPre.style.fontFamily = 'ui-monospace, Menlo, Consolas, monospace';
    streamPre.style.fontSize = '12px';
    streamPre.style.opacity = '0.9';
    streamPre.style.marginTop = '8px';
    pendingEl.appendChild(status);
    pendingEl.appendChild(counter);
    pendingEl.appendChild(toggleBtn);
    pendingEl.appendChild(streamPre);
  }

  try {
    // refinementHistory holds {note, status} objects — only applied notes
    // count; serializing without filtering would send rejected ones, and
    // template-stringing the object would yield "[object Object]".
    const acceptedNotes = refinementHistory
      .filter(e => e.status === 'applied')
      .map((e, i) => `${i + 1}. ${e.note}`)
      .join('\n');

    let finalData = null;
    let httpError = null;
    let streamErr = null;
    let tokenCount = 0;
    await _consumeSSE(
      '/api/generate/stream',
      {
        username: currentUser,
        context_path: lastContextPath,
        output_format: outputFormat,
        refinement_notes: acceptedNotes,
        persona_template_id: _readSelectedPersonaId(),
        // generate_cover_letter defaults False on the backend (β.5 — cover
        // letter is opt-in via /api/generate-cover-letter); preserved here
        // by omission so we don't widen the request unintentionally.
      },
      (eventName, payload) => {
        if (eventName === 'chunk') {
          // Counting chunks (each delta is 1-4 chars) — close enough for
          // an alive-indicator label that reads "tokens" without the
          // precision of a real tokenizer.
          tokenCount += 1;
          const counterEl = document.getElementById('generateStreamCounter');
          if (counterEl) counterEl.textContent = `Received ${tokenCount} tokens`;
          const pre = document.getElementById('generateStreamPre');
          if (pre) {
            pre.textContent += payload.text || '';
            if (!pre.classList.contains('hidden')) {
              pre.scrollTop = pre.scrollHeight;
            }
          }
        } else if (eventName === 'retry') {
          const status = document.getElementById('generateStreamStatus');
          if (status) status.textContent = `Generating… (retrying: ${payload.reason})`;
          const pre = document.getElementById('generateStreamPre');
          if (pre) pre.textContent += `\n\n[retry: ${payload.reason}]\n\n`;
        } else if (eventName === 'done') {
          finalData = payload;
        } else if (eventName === 'error') {
          streamErr = payload;
        } else if (eventName === 'http_error') {
          httpError = payload;
        }
      },
    );

    if (httpError) {
      return reportError(
        'Generate',
        httpError.body.error || 'Generation failed',
        httpError.body.detail,
      );
    }
    if (streamErr) {
      return reportError('Generate', streamErr.error || 'Generation failed', streamErr.detail);
    }
    if (!finalData) {
      return reportError('Generate', 'Generation stream ended without a result.');
    }

    lastResumePath = finalData.resume_path;
    lastCoverLetterPath = finalData.cover_letter_path;
    lastResumeFormat = finalData.resume_format || '.docx';
    _selectedPersonaId = finalData.persona_template_id ?? _readSelectedPersonaId();
    _onGenerationComplete(finalData);
    _renderOutput(finalData);
    setStatus('GENERATION COMPLETE');
    _announce(`Iteration ${currentIteration} ready. Resume and cover letter generated.`);
    _wizardAdvanceTo(6);
  } catch (e) {
    reportError('Generate', 'Generation request failed', e.message);
  } finally {
    _setBusy(false);
    document.getElementById('btnGenerate').disabled = false;
    // Always hide the pending placeholder — leaving the streamed-tokens
    // view up after success or failure would be misleading.
    document.getElementById('generatePending')?.classList.add('hidden');
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
  // β.5 — toggle the Generate cover letter / Download cover letter
  // affordance based on whether the current generation actually
  // produced a cover letter. /api/generate's default is now résumé-only
  // (with_cover_letter=False), so the Generate button shows after the
  // first résumé generation and swaps for Download once a cover letter
  // exists.
  _updateCoverLetterButtons();
  // Refresh the Step 6 résumé preview once content lands. Post-WYSIWYG the
  // preview route serves the cached last_generated_json_resume from the
  // freshly-saved child context_path, so the styled iframe shows the exact
  // generated content (preview == download). The cover-letter preview
  // refreshes lazily when its tab is shown (see showTab).
  _refreshOutputPreview();
  // KW7: generation updated the application's run data (iteration count,
  // updated_at) — keep the applications block in sync.
  refreshApplications();
}

// β.5 — show "+ Generate cover letter" when no cover letter exists yet,
// "Download cover letter" once one does. Idempotent.
function _updateCoverLetterButtons() {
  const gen = document.getElementById('btnGenerateCover');
  const dl  = document.getElementById('btnDownloadCover');
  if (!gen || !dl) return;
  const haveCoverLetter = (lastGeneratedCoverLetter || '').trim().length > 0;
  gen.classList.toggle('hidden', haveCoverLetter);
  dl.classList.toggle('hidden', !haveCoverLetter);
}

// β.5 — fire the focused /api/generate-cover-letter call. Cheaper than
// re-running /api/generate (no résumé tokens). Reuses the same status-
// pill + edit-detect flow so the cover letter inherits the existing
// refine / iterate / edit-detect affordances.
async function runGenerateCoverLetter() {
  if (!currentUser) return alert('Select a user first');
  if (!lastContextPath) return alert('Generate the résumé first');
  _maybeFireTourStop('tourCoverLetter', null);  // KW3: first cover-letter
  setStatus('GENERATING COVER LETTER');
  _setBusy(true, 'Generating your cover letter');
  const gen = document.getElementById('btnGenerateCover');
  if (gen) gen.disabled = true;
  try {
    const res = await fetch('/api/generate-cover-letter', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: currentUser,
        context_path: lastContextPath,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      return reportError(
        'Cover letter',
        data.error || 'Cover letter generation failed',
        data.detail,
      );
    }
    lastCoverLetterPath = data.cover_letter_path || '';
    lastGeneratedCoverLetter = data.cover_letter_preview || '';
    if (data.context_path) lastContextPath = data.context_path;
    // Populate the editable preview the same way runGeneration →
    // _renderOutput does. downloadCoverLetter reads from
    // #coverLetterPreview so the preview MUST be populated for download
    // to work. B1 (2026-05-26): the separate Rendered view was removed
    // along with the Raw / Rendered toggle.
    const preview = document.getElementById('coverLetterPreview');
    if (preview) preview.textContent = lastGeneratedCoverLetter;
    _updateCoverLetterButtons();
    // Auto-switch to the Cover letter tab so the user lands on the
    // generated content without an extra click. Pre-fix behavior left
    // the user on the Résumé tab and required them to discover the
    // Cover letter tab themselves — bad ux during a wizard flow.
    // showTab('coverLetter') also refreshes the styled CL preview iframe
    // against the freshly-saved context_path.
    showTab('coverLetter');
    setStatus('COVER LETTER READY');
    _announce('Cover letter generated. Download it from Step 6.');
  } catch (e) {
    reportError('Cover letter', 'Cover letter request failed', e.message);
  } finally {
    _setBusy(false);
    if (gen) gen.disabled = false;
  }
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
  // _readEditorText handles hidden-element innerText reads (see helper
  // above downloadResume). Without it, edits to #resumePreview made
  // inside the drawer would not be detected after the drawer closed.
  const resume = (_readEditorText('resumePreview') || '').trim();
  const cover = (_readEditorText('coverLetterPreview') || '').trim();
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
      const backdrop = modal.querySelector('.cb-modal-backdrop');
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
    const backdrop = modal.querySelector('.cb-modal-backdrop');
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

  const openBtn = document.getElementById('btnOpenDashboard');

  const cleanup = () => {
    modal.classList.add('hidden');
    modal.removeEventListener('keydown', onKey);
    dismissers.forEach(b => b.removeEventListener('click', cleanup));
    if (openBtn) openBtn.removeEventListener('click', cleanup);
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
  // Auto-close the modal when the user clicks "Open dashboard" — the
  // link opens /_dashboard in a new tab (target="_blank"), so leaving
  // the modal open afterwards is dead weight. Pre-fix the user had to
  // click Close as a separate action; surfaced 2026-05-26 smoke. The
  // listener fires AFTER the anchor's default action (new-tab open)
  // because we don't preventDefault. cleanup() removes it on close so
  // repeated open/close cycles don't stack handlers.
  if (openBtn) openBtn.addEventListener('click', cleanup);
  modal.classList.remove('hidden');
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
// Sprint 6.5 — reusable in-app help primitive (feat/help-pattern-component)
// ===============================================================
// ONE shared #helpModal whose title/body are swapped per block, plus an
// (i)-circle injected into each registered block's .panel-header that re-opens
// that block's modal, plus an optional inline short-form line. The welcome
// block also auto-opens once-ever on first view (localStorage gate). Per-surface
// copy is just registry keys (no engine change); the KW3 new-user first-run tour
// (feat/education-tailor-corpus-wizard) layers a small once-ever sequence on top
// — see _maybeFireTourStop / _fireWizardTourStop below.
//
// Each entry: { title, body, short?, tip?, welcome? }
//   title   — heading swapped into #helpModalTitle (also the icon's a11y name)
//   body    — canonical "pathfinding" copy swapped into #helpModalBody
//   short   — optional inline short-form, injected atop the block's .panel-body
//   tip     — optional native-tooltip text for the (i) icon (defaults to title)
//   welcome — when true, this block auto-opens once-ever on first view
const _HELP_REGISTRY = {
  // ---- Tailor tab -------------------------------------------------------
  panelUser: {
    title: 'Welcome to sartor',
    body: "sartor tailors your résumé to a specific job from a career corpus "
      + 'it builds out of your past résumés — nothing is locked in a file you '
      + 'hand-edit per application. Select a user to begin, or add a new one to '
      + 'import your first résumé. Every section has an “i” you can click for a '
      + 'quick explanation.',
    short: 'Select a user to begin, or add a new one to import your first résumé.',
    tip: 'About sartor',
    welcome: true,
  },
  panelApplications: {
    title: 'Prior applications',
    body: 'Every résumé you generate is kept here against the job you tailored '
      + 'it for. Reopen one to download it again, or to pick up where you left '
      + 'off and refine it further. Nothing here changes your career corpus.',
    tip: 'Prior applications',
  },

  // ---- Wizard steps (Tailor tab) ---------------------------------------
  panelJD: {
    title: 'Step 1 — Job description',
    body: 'Paste the full text of the job you’re applying for, then click '
      + 'Analyze. sartor reads the posting and weighs it against your career '
      + 'corpus to find the experience that fits this role best. The numbered '
      + 'steps along the top let you move back and forward at any time.',
    tip: 'Step 1 — Job description',
  },
  panelAnalysis: {
    title: 'Step 1 — Analysis',
    body: 'This is sartor’s read of the job — the themes it found and how '
      + 'your experience lines up. From here you can answer a few clarifying '
      + 'questions next (recommended — it usually sharpens the result) or skip '
      + 'straight to composing the résumé.',
    tip: 'Analysis',
  },
  panelClarify: {
    title: 'Step 2 — Clarify',
    body: 'Optional, but worth it. sartor asks a few short questions to draw '
      + 'out real experience your résumé didn’t spell out and to pin down '
      + 'anything vague. Your answers become new candidate bullet points (added '
      + 'to your corpus to accept now or review later) and keep the résumé '
      + 'grounded in fact. Prefer to move on? Click Skip.',
    tip: 'Step 2 — Clarify',
  },
  panelCompose: {
    title: 'Step 3 — Compose',
    body: 'Here’s the résumé sartor proposes for this job: the title it chose '
      + 'for each role and the bullet points it selected and ordered, including '
      + 'any new ones from your clarifying answers. Pin a bullet to force-include '
      + 'it, exclude ones you don’t want, or open “find more” to pull others from '
      + 'your corpus. Edits here affect this application only. Save and continue '
      + 'when it reads right.',
    tip: 'Step 3 — Compose',
  },
  panelTemplate: {
    title: 'Step 4 — Template',
    body: 'Your selected content is loaded — now choose how it looks. Pick a '
      + 'template on the left and the preview shows the pages exactly as they’ll '
      + 'print: same words, different typography and layout. You can also upload '
      + 'your own .docx for sartor to reuse (ATS-safe templates strongly '
      + 'recommended). Click Generate when you’re happy with the look.',
    tip: 'Step 4 — Template',
  },
  panelGenerate: {
    title: 'Step 5 — Generate',
    body: 'Choose your output format and click Generate. sartor writes the '
      + 'final, tailored résumé from the content and template you picked. This '
      + 'usually takes about 30–60 seconds.',
    tip: 'Step 5 — Generate',
  },
  panelOutput: {
    title: 'Step 6 — Preview & download',
    body: 'Here’s your finished résumé. The preview is editable — fix wording in '
      + 'place and those edits are saved as the starting point for your next '
      + 'iteration. Editing here changes the document text only; it does not '
      + 'change your career corpus. Download when you’re ready, and you can also '
      + 'generate an editable cover letter from the same job and résumé.',
    tip: 'Step 6 — Preview & download',
  },

  // ---- Career corpus / Templates / Memory tabs -------------------------
  panelCorpus: {
    title: 'Your career corpus',
    body: 'Your career corpus is the pool of experience sartor draws from when '
      + 'it writes a tailored résumé — the roles and bullet points it built from '
      + 'the résumé you imported. Everything starts as “pending review”: accept '
      + 'items one at a time, by role, or all at once. Reviewing and accepting '
      + 'sharpens future résumés. You can also add experiences by hand, give a '
      + 'role alternate titles, and tag things. When your corpus is ready, head '
      + 'to Tailor to target a specific job.',
    tip: 'Career corpus',
  },
  panelPersonas: {
    title: 'Résumé templates',
    body: 'Templates control how your résumé looks — typography, spacing, and '
      + 'layout — without changing a word of the content. A few ATS-friendly '
      + 'templates ship with the app, and you can upload your own .docx for '
      + 'sartor to reuse as a template. ATS-safe templates are strongly '
      + 'recommended so applicant-tracking systems can read your résumé cleanly.',
    tip: 'Résumé templates',
  },
  panelMemory: {
    title: 'Candidate memory',
    body: 'Candidate memory keeps the questions sartor asked during “Clarify” '
      + 'and the answers you gave, across every application. Answers with '
      + 'concrete numbers and outcomes make the strongest new résumé bullets, so '
      + 'they’re highlighted here. Nothing is shared between users.',
    tip: 'Candidate memory',
  },

  // ---- KW3 first-run tour stops with no panel of their own -------------
  // These fire once at a milestone in the first run; their topic is covered
  // by the nearest section’s (i) for later reference (see _maybeFireTourStop).
  tourAddUser: {
    title: 'Add yourself as a user',
    body: 'Start by importing a résumé — sartor builds your first career '
      + 'corpus from it, so you don’t have to type everything in by hand. An '
      + 'ATS-friendly résumé (plain text, clear month/year dates) works best; '
      + 'sartor does its best with other formats. You can add your name and '
      + 'contact details now or later.',
    tip: 'Adding a user',
  },
  tourGenerating: {
    title: 'Generating your résumé',
    body: 'sartor is writing your tailored résumé now — this usually takes '
      + '30–60 seconds. When it’s done you’ll get a live preview you can edit '
      + 'and download, plus the option to generate a matching, editable cover '
      + 'letter.',
    tip: 'Generating',
  },
  tourCoverLetter: {
    title: 'Your cover letter',
    body: 'sartor drafts a cover letter from the same job and résumé. Like the '
      + 'résumé preview, it’s editable in place — adjust the wording, then '
      + 'download. Generating it again rewrites it from scratch.',
    tip: 'Cover letter',
  },
};

// The localStorage seam and the opener itself now live in the shared
// static/help-modal.js leaf (loaded before this file). These thin wrappers keep
// the in-app call sites + names (_helpSeen / _markHelpSeen / openHelpModal)
// stable while the single implementation is shared with the self-contained
// diagnostics console, which cannot load this file.
function _helpSeen(blockId) { return window.cbHelpSeen(blockId); }
function _markHelpSeen(blockId) { window.cbMarkHelpSeen(blockId); }

// Resolve this page's registry entry, then delegate to the shared opener.
// triggerEl may be null (the first-view auto-open has no trigger). An unknown
// blockId yields undefined → the shared opener no-ops, matching the old guard.
function openHelpModal(blockId, triggerEl) {
  window.cbOpenHelpModal(_HELP_REGISTRY[blockId], triggerEl);
}

// Inject the (i)-circle (+ optional inline short-form) into each registered
// .cb-panel block. Idempotent — re-running never double-injects. Non-panel
// targets are skipped this branch (tab-level help is a later branch).
function _initHelp() {
  Object.keys(_HELP_REGISTRY).forEach((blockId) => {
    const block = document.getElementById(blockId);
    if (!block || !block.classList.contains('cb-panel')) return;
    if (document.getElementById('help-icon-' + blockId)) return;  // already injected
    const entry = _HELP_REGISTRY[blockId];

    const header = block.querySelector('.panel-header');
    if (header) {
      // .has-help-icon keeps the title + icon grouped left and pins the
      // collapse chevron (::after) right; see static/style.css.
      header.classList.add('has-help-icon');
      const icon = _el('button', {
        className: 'help-info',
        id: 'help-icon-' + blockId,
        type: 'button',
        textContent: 'i',
        title: entry.tip || entry.title,
      }, [], {
        'aria-label': 'Help: ' + entry.title,
        'aria-haspopup': 'dialog',
        'aria-controls': 'helpModal',
        'aria-expanded': 'false',
      });
      // stopPropagation so opening help never toggles the panel's collapse.
      icon.onclick = (e) => { e.stopPropagation(); openHelpModal(blockId, icon); };
      header.appendChild(icon);
    }

    if (entry.short) {
      const body = block.querySelector('.panel-body');
      if (body && !document.getElementById('help-inline-' + blockId)) {
        const p = _el('p', {
          className: 'help-inline',
          id: 'help-inline-' + blockId,
          textContent: entry.short,
        });
        body.insertBefore(p, body.firstChild);
        const existing = block.getAttribute('aria-describedby');
        block.setAttribute(
          'aria-describedby',
          existing ? existing + ' help-inline-' + blockId : 'help-inline-' + blockId,
        );
      }
    }
  });
}

// First-view auto-open: the welcome block opens once-ever (localStorage gate).
// Synchronous — no async user-state lookup — so it is race-free and the UX
// suite controls it deterministically via the cb_help_seen flag.
function _maybeAutoOpenHelp() {
  const welcomeId = Object.keys(_HELP_REGISTRY).find(id => _HELP_REGISTRY[id].welcome);
  if (!welcomeId || _helpSeen(welcomeId)) return;
  _markHelpSeen(welcomeId);
  openHelpModal(welcomeId, null);
}

// ---- KW3 first-run tour ------------------------------------------------
// New-users-only guided sequence layered on the help primitive. Each stop is a
// registry entry shown ONCE (the cb_help_seen seam) at a milestone of the first
// run. The only new state is an in-memory "armed" flag: a returning user (an
// existing user with a non-empty corpus) is never armed, so the tour never
// walks them through onboarding again. Stops with a panel are re-openable from
// that panel's (i); the three tour-only stops (tourAddUser / tourGenerating /
// tourCoverLetter) are covered by the nearest section's (i).
let _helpTourArmed = false;
function _armHelpTour() { _helpTourArmed = true; }

// Fire a tour stop once-ever — only while armed and with no modal already open
// (so a stop never stacks on top of the welcome or a prior stop).
function _maybeFireTourStop(stopId, triggerEl) {
  if (!_helpTourArmed) return;
  if (!_HELP_REGISTRY[stopId] || _helpSeen(stopId)) return;
  const modal = document.getElementById('helpModal');
  if (modal && !modal.classList.contains('hidden')) return;
  _markHelpSeen(stopId);
  openHelpModal(stopId, triggerEl || null);
}

// Fire the active wizard step's stop, but only when its panel is actually on
// screen. offsetParent === null ⇒ the panel sits on a hidden top tab (e.g. a
// new user still onboarding on the Career corpus tab) ⇒ don't fire it early.
function _fireWizardTourStop() {
  const panelId = (_WIZARD_PANELS[_wizardStep] || [])[0];
  if (!panelId) return;
  const el = document.getElementById(panelId);
  if (!el || el.offsetParent === null) return;
  _maybeFireTourStop(panelId, document.getElementById('help-icon-' + panelId));
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
// Empty-corpus detection + CTA
// ===============================================================

// True when a DB-backed read reports the selected user has no candidate row
// yet (a brand-new user). Reads signal this via
// `200 + {needs_onboarding:true, <empty>}`. The row self-provisions on the
// first corpus write (résumé upload / add experience), so this is purely an
// empty-state signal — there is no separate import step.
function _needsOnboarding(res, data) {
  return !!(data && data.needs_onboarding === true);
}

// Empty-state CTA for read-only tabs (Memory / Applications / Templates) when
// the user has no corpus material yet. Points them at the Career corpus tab,
// where uploading a résumé / adding an experience both populates the corpus
// and provisions the candidate row.
function _renderCorpusEmptyCTA(container, message) {
  if (!container) return;
  _clearChildren(container);
  const wrap = _el('div', { className: 'corpus-empty-experience' });
  wrap.appendChild(_el('div', { textContent: message || 'Nothing here yet.' }));
  const btn = _el('button', {
    className: 'cb-btn cb-bg-teal',
    textContent: 'Go to Career corpus',
  });
  btn.style.marginTop = '10px';
  btn.onclick = () => switchTopTab('corpus', document.getElementById('topTabCorpus'));
  wrap.appendChild(btn);
  container.appendChild(wrap);
}

// Smart landing (Sprint 6.4 #16/#1 + KW1): which top tab to show for the
// selected user. An empty corpus → 'corpus' (onboard: import a résumé / add an
// experience); a populated corpus → 'tailor' (straight to the application
// workflow). With no user selected (goHome's deselect, initial load) → 'tailor',
// the home of the user picker (#panelUser lives in #tab-tailor).
//
// Side-effect-free on purpose: it must NOT seed `_corpusLoadedForUser` /
// `_corpusExperiences`, or loadCorpusIfReady()'s "already loaded" guard would
// skip the corpus render when we land on the Corpus tab.
async function _landingTab() {
  if (!currentUser) return 'tailor';
  let data;
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/experiences`);
    data = await res.json().catch(() => []);
  } catch {
    return 'tailor';  // network hiccup → safe default (don't strand mid-onboard)
  }
  // Same shape read as refreshCorpus(): bare array on success, or
  // {experiences:[], needs_onboarding:true} for a brand-new user. Both empty
  // forms collapse to length 0.
  const exps = Array.isArray(data) ? data : (data.experiences || []);
  return exps.length === 0 ? 'corpus' : 'tailor';
}

// Activate a top tab by name, looking up its button. Mirrors the inline
// `switchTopTab('x', document.getElementById('topTabX'))` callsites so the
// smart-landing routing reads cleanly.
function _activateTab(name) {
  const ids = { tailor: 'topTabTailor', corpus: 'topTabCorpus',
                personas: 'topTabPersonas', memory: 'topTabMemory' };
  switchTopTab(name, document.getElementById(ids[name] || 'topTabTailor'));
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
    // Walkthrough D1/D2: the styled preview serves the cached JSON Resume, which
    // /api/save-edits just recomputed from the edited markdown — refresh the
    // iframe so the edit shows immediately (no regenerate needed).
    if (edits.resumeEdited) _refreshOutputPreview();
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
      // Walkthrough E4: FLAG, but never BLOCK. Correcting a hallucinated "fact"
      // (e.g. an invented "10 years of…" leap) is exactly what the user needs to
      // do — the scope check must not prevent it. Surface the concern and let the
      // user decide whether to proceed.
      const reason = check.reason || 'This may change facts rather than just wording.';
      const proceed = confirm(
        `Heads up — this looks like it may change facts, not just wording:\n\n`
        + `${reason}\n\nThat's your call. Proceed with this refinement anyway?`,
      );
      if (!proceed) {
        entry.status = 'rejected';
        entry.reason = reason;
        _renderRefinementHistory();
        setStatus('REFINEMENT CANCELED');
        return;
      }
      // User chose to proceed despite the flag — fall through to generate.
    }

    // Step 2: generate with accepted notes only
    entry.status = 'applied';
    _renderRefinementHistory();
    setStatus('REFINING');
    // Walkthrough E1: show the persistent working overlay while the refine
    // regenerates (mirrors runGeneration), not just the status label.
    _setBusy(true, 'Refining your résumé');

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
    _setBusy(false);
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
    // KW5: the section renders below the fold — bring it into view so it's clear
    // something happened (mirrors the wizard-nav / corpus scroll idiom). Fires
    // only after the synchronous render above, covering both the questions and
    // the "no follow-up questions surfaced" branches.
    const iterArea = document.getElementById('iterateClarifyArea');
    if (iterArea) iterArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    // merge:true so the route accumulates these by id into context.clarifications
    // — prior answers (including from the analyze-time clarify) stay intact.
    // This collects ONLY the iterate-round textareas, so a whole-map replace
    // would silently drop the analyze-round answers (KW4).
    const res = await fetch('/api/answer-clarifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        context_path: lastContextPath,
        username: currentUser,
        answers,
        merge: true,
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

  // KW7 / B.8: the route mirrored these answers into candidate memory —
  // sync the panel so the interview Q&A shows up without a manual refresh.
  refreshMemory();
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

  // B1 (2026-05-26): the Raw / Rendered toggle was removed; the raw
  // editor stays hidden in the tab body and surfaces inside the edit
  // drawer (résumé) or as the primary cover-letter surface. No view-
  // mode reset needed anymore.

  // Populate the "What changed?" modal body. Visibility of the
  // #btnViewChanges trigger button is tied to whether either list has
  // content — empty changes_made AND empty proofread_notes means
  // there's nothing to show.
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
  const btnViewChanges = document.getElementById('btnViewChanges');
  if (btnViewChanges) btnViewChanges.classList.toggle('hidden', !changesHtml);

  showTab('resume');
  document.getElementById('refinementArea').classList.remove('hidden');
  document.getElementById('refinementInput').value = '';
}

function showTab(name, clickedBtn) {
  // B1 (2026-05-26): only two output tabs remain — 'resume' and 'coverLetter'.
  // The pre-B1 'changes' tab moved to an info-icon modal next to the
  // download button (openChangesModal). Passing 'changes' is a no-op
  // for backwards safety; callers should use openChangesModal directly.
  if (name === 'changes') {
    openChangesModal();
    return;
  }
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  // Reset all tab-btns' visual + ARIA state in one pass; the matching button
  // is set selected below. Without aria-selected updates, screen readers
  // announce the wrong active tab.
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.remove('active');
    if (b.getAttribute('role') === 'tab') b.setAttribute('aria-selected', 'false');
  });
  const tabId = name === 'coverLetter' ? 'tabCoverLetter' : 'tabResume';
  document.getElementById(tabId).classList.add('active');
  let activeBtn = clickedBtn;
  if (!activeBtn) {
    const btnIndex = name === 'coverLetter' ? 1 : 0;
    const btns = document.querySelectorAll('.tab-btn');
    activeBtn = btns[btnIndex];
  }
  if (activeBtn) {
    activeBtn.classList.add('active');
    if (activeBtn.getAttribute('role') === 'tab') activeBtn.setAttribute('aria-selected', 'true');
  }
  // Refresh the styled cover-letter preview whenever the Cover letter tab
  // becomes active. The route returns a placeholder until a cover letter is
  // generated, so this is safe pre-generation. (The résumé preview refreshes
  // on generation via _onGenerationComplete; the CL preview can't piggyback
  // there because the CL is generated separately, and the tab is hidden when
  // not active so iframes shouldn't load eagerly.)
  if (name === 'coverLetter') {
    _refreshCoverPreview();
  }
}

// "Edit before downloading" drawer for Step 6. Hosts EITHER the résumé
// editor (#resumePreview) or the cover-letter editor (#coverLetterPreview)
// so the raw markdown doesn't compete with the styled iframe for screen
// real estate. We MOVE the existing DOM node in/out of the drawer host
// (rather than cloning) because:
//   - downloadResume()/downloadCoverLetter() + _renderOutput() reference
//     the editors by id; moving (not cloning) keeps that contract intact.
//   - moving preserves the contenteditable state, focus, selection,
//     and any inline event listeners attached.
// Each editor's home parent is captured the first time it's hosted so
// closeEditDrawer can return it cleanly (robust against double-open).
const _EDIT_DRAWER_TARGETS = {
  resume: {
    editorId: 'resumePreview',
    title: 'Edit résumé before downloading',
    hint: 'This is the generated résumé that downloads — the exact content the AI produced for this job. Edit it here, then download. Your edits also become the baseline for the next refine / iterate round.',
  },
  cover: {
    editorId: 'coverLetterPreview',
    title: 'Edit cover letter before downloading',
    hint: 'This is the generated cover letter that downloads — edit it here, then download. Your edits also become the baseline for the next refine / iterate round.',
  },
};
const _editDrawerHome = {};        // editorId -> original parent node
let _editDrawerActiveEditorId = null;

function openEditDrawer(target = 'resume') {
  const cfg = _EDIT_DRAWER_TARGETS[target] || _EDIT_DRAWER_TARGETS.resume;
  const drawer = document.getElementById('editDrawer');
  const host = document.getElementById('editDrawerHost');
  const editor = document.getElementById(cfg.editorId);
  if (!drawer || !host || !editor) return;
  // If a different editor is currently in the drawer, send it home first.
  if (_editDrawerActiveEditorId && _editDrawerActiveEditorId !== cfg.editorId) {
    closeEditDrawer();
  }
  // Capture the home parent once (while the node still lives in its tab body).
  if (!_editDrawerHome[cfg.editorId]) {
    _editDrawerHome[cfg.editorId] = editor.parentNode;
  }
  _editDrawerActiveEditorId = cfg.editorId;
  const title = document.getElementById('editDrawerTitle');
  const hint = document.getElementById('editDrawerHint');
  if (title) title.textContent = cfg.title;
  if (hint) hint.textContent = cfg.hint;
  // Unhide the editor — it lives hidden in the tab body until the drawer
  // opens. The aria-label and contenteditable attributes stay intact.
  editor.classList.remove('hidden');
  host.appendChild(editor);
  drawer.classList.remove('hidden');
  // Defer focus until after the slide-in animation so screen readers
  // announce the drawer + heading first.
  setTimeout(() => editor.focus(), 220);
}

function closeEditDrawer() {
  const drawer = document.getElementById('editDrawer');
  if (!drawer) return;
  drawer.classList.add('hidden');
  const editor = _editDrawerActiveEditorId
    ? document.getElementById(_editDrawerActiveEditorId)
    : null;
  const home = editor ? _editDrawerHome[_editDrawerActiveEditorId] : null;
  if (editor && home) {
    home.appendChild(editor);
    editor.classList.add('hidden');
  }
  _editDrawerActiveEditorId = null;
}

// B1 — "What changed?" info-icon modal. Replaces the pre-B1 Changes tab.
// changesContent's innerHTML is populated by _renderOutput; this just
// shows/hides the modal wrapper.
function openChangesModal() {
  document.getElementById('changesModal')?.classList.remove('hidden');
}

function closeChangesModal() {
  document.getElementById('changesModal')?.classList.add('hidden');
}

// Read an editable preview's text, even when it's display:none.
// innerText is style-aware (per MDN) and returns "" for hidden
// elements; the B1 redesign keeps #resumePreview hidden when the
// edit drawer is closed so a naive innerText read returned empty
// — which silently posted empty content to /api/download-edited
// and broke the résumé download path (round-5 smoke). We restore
// the original hidden state immediately, so the mutation isn't
// visible to the user (no reflow paint in the same JS tick).
function _readEditorText(id) {
  const el = document.getElementById(id);
  if (!el) return '';
  const wasHidden = el.classList.contains('hidden');
  if (wasHidden) el.classList.remove('hidden');
  const text = el.innerText;
  if (wasHidden) el.classList.add('hidden');
  return text;
}

async function downloadResume() {
  const btn = document.getElementById('btnDownloadResume');
  // Diagnostic logging (round 6 smoke, 2026-05-26) — the user reported
  // résumé download still fails after a successful cover-letter
  // download. The console.log shows whether the button click is even
  // firing (rules out CSS pseudo-disabled), the button's actual
  // disabled prop, and the content length we read. With this we can
  // tell which of three things broke: (a) button has stuck disabled
  // state, (b) editor content is empty post-cl-download, or (c)
  // Chrome's "multiple downloads" policy is silently blocking the
  // second download (in which case the address bar would show a
  // small downloads-blocked icon).
  console.log('[download] résumé click; btn.disabled=', btn?.disabled,
              'content len=', _readEditorText('resumePreview')?.length);
  await _runDownload(btn, async () => {
    const content = _readEditorText('resumePreview');
    if (!content || !content.trim()) {
      throw new Error(
        'Cannot read résumé content from the editor — internal: '
        + '#resumePreview is empty. Try regenerating from Step 5.',
      );
    }
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
  });
}

async function downloadCoverLetter() {
  const btn = document.getElementById('btnDownloadCover');
  console.log('[download] cover letter click; btn.disabled=', btn?.disabled,
              'content len=', _readEditorText('coverLetterPreview')?.length);
  await _runDownload(btn, async () => {
    // Use the same helper as downloadResume for symmetry — even though
    // #coverLetterPreview is visible in its tab body today (no drawer
    // for cover letter in B1), B3 may move it behind a drawer too.
    const content = _readEditorText('coverLetterPreview');
    await _downloadEdited('/api/download-edited', {
      username: currentUser,
      content,
      type: 'cover_letter',
      // Honors the dedicated Step-6 cover-letter format picker (independent of
      // the résumé's). persona_template_id lends the persona font: .pdf renders
      // through personas/cover_letter.html, .docx borrows the same CSS family.
      original_format: coverFormat,
      persona_template_id: _selectedPersonaId ?? _readSelectedPersonaId(),
    });
  });
}

// B1 smoke fix (2026-05-26): wrap the download flow so a thrown error
// inside _downloadEdited surfaces to the user (was silent before — the
// thrown error in fetch / blob / click would unwind the await and the
// user would just see a non-responsive button). The disabled-then-
// re-enabled toggle also prevents a second click during the in-flight
// fetch from racing the first one and (on some browsers) tripping the
// "multiple downloads" defense that silently blocks both.
async function _runDownload(btn, doDownload) {
  if (btn) btn.disabled = true;
  try {
    await doDownload();
  } catch (e) {
    reportError('Download', 'Download failed', e && e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function _downloadEdited(url, payload) {
  console.log('[download] fetching', url, 'type=', payload.type);
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  console.log('[download] fetch resolved status=', res.status, 'type=', payload.type);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    console.error('[download] non-ok response', err);
    throw new Error(err.error || `Download failed (${res.status})`);
  }
  // Stream the file as a download.
  const blob = await res.blob();
  console.log('[download] blob size=', blob.size, 'type=', blob.type);
  const disposition = res.headers.get('Content-Disposition') || '';
  const nameMatch = disposition.match(/filename="?([^"]+)"?/);
  const filename = nameMatch ? nameMatch[1] : 'document.docx';
  console.log('[download] resolved filename=', filename);

  // B1 smoke fix (2026-05-26): attach the anchor to the DOM briefly
  // before clicking, and DEFER URL.revokeObjectURL until after the
  // browser has had a chance to read the blob. Pre-fix behavior:
  // detached <a> + immediate revokeObjectURL was fragile across
  // browsers — Chrome on Windows specifically broke subsequent
  // downloads if the user canceled the "Save As" dialog. Both
  // download buttons (résumé AND cover letter) appeared frozen
  // because the leftover state from the first canceled download
  // confused the browser's per-page download-anchor accounting.
  const a = document.createElement('a');
  const objectUrl = URL.createObjectURL(blob);
  a.href = objectUrl;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  console.log('[download] anchor in DOM, about to click; href.length=', objectUrl.length);
  try {
    a.click();
    console.log('[download] a.click() returned; if no save dialog appears, browser policy may be blocking (check address bar for downloads-blocked icon)');
  } finally {
    document.body.removeChild(a);
    // Hold the URL alive long enough for the browser to start the
    // download (or open the Save As dialog). 5 seconds is excessive
    // for a successful read but cheap (one blob URL); the GC will
    // reclaim the blob once revoked.
    setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
  }
  // B.8 Part 1: the user just took a document to go apply with — surface
  // the "Mark submitted" nudge so the outcome funnel starts here, not in a
  // tracker panel they may never revisit.
  _showMarkSubmittedNudge();
}

// Reveal the Step-6 outcome-capture nudge (only when the wizard is bound to
// an application — legacy file-only flows have no row to update).
function _showMarkSubmittedNudge() {
  if (_composeApplicationId == null) return;
  document.getElementById('markSubmittedNudge')?.classList.remove('hidden');
}

// Step-6 nudge click: PUT submitted on the wizard's application, confirm,
// and sync the applications block. Idempotent server-side — sent_at stamps
// only on the first transition.
async function markCurrentApplicationSubmitted() {
  if (_composeApplicationId == null) {
    _toast('No application bound to this wizard run', true);
    return;
  }
  if (await _putApplicationStatus(_composeApplicationId, 'submitted')) {
    document.getElementById('markSubmittedNudge')?.classList.add('hidden');
    _toast('Marked submitted — report the outcome from its Applications card');
    refreshApplications();
  }
}

// B1 (2026-05-26): setViewMode + _renderMarkdown removed along with the
// Raw / Rendered toggle. The styled iframe at the top of the R\u00e9sum\u00e9 tab
// now serves the "Rendered" purpose; the raw editor lives in the
// "Edit before downloading" drawer. Cover letter has no rendered view
// (the markdown IS the document until B3 lands a persona-styled
// preview iframe). If a future step needs markdown\u2192HTML rendering,
// restore `_renderMarkdown` from git history rather than re-inventing.

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
  UPLOADING:                'panelResume',
  ANALYZING:                'panelAnalysis',
  GENERATING:               'panelOutput',
  REFINING:                 'panelOutput',
  // β.5 — focused cover-letter call; same panel as résumé generation.
  'GENERATING COVER LETTER': 'panelOutput',
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
// from the LCARS era; the sartor. chrome uses sentence case.
function _toSentence(s) {
  if (!s) return '';
  const lower = s.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

function setStatus(text) {
  const pill = document.getElementById('statusPill');
  // .cb-status-text is the dedicated label child of the sartor. status
  // pill. The whole pill was migrated from .cb-pill to .cb-status in
  // feat/release-visual-ia, so this element is always present.
  const textEl = pill.querySelector('.cb-status-text');
  if (textEl) textEl.textContent = _toSentence(text);

  // Clear any prior aria-busy state from the previously-active panel so
  // assistive tech stops announcing the panel as busy once work completes.
  document.querySelectorAll('.cb-panel[aria-busy="true"]').forEach(p => {
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
  // bottom status pills; the LCARS-era elbow flash + .cb-block tile
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
  // A panel marked .not-collapsible ignores header clicks (e.g. the User
  // selection box before a user is picked — see onUserSelect).
  if (panel.classList.contains('not-collapsible')) return;
  const isCollapsed = panel.classList.toggle('collapsed');
  const block = document.querySelector(`[data-panel="${panelId}"]`);
  if (block) block.classList.toggle('collapsed', isCollapsed);
}

// Panel-header click toggles the parent .cb-panel between expanded
// and collapsed states (CSS grid-template-rows transition).
document.querySelectorAll('.panel-header').forEach(header => {
  const panel = header.closest('.cb-panel');
  if (panel) header.addEventListener('click', () => _togglePanel(panel.id));
});

// ===============================================================
// Phase D.2 — Top-level tabs + Career Corpus tab
// ===============================================================

let _corpusLoadedForUser = '';
let _corpusExperiences = [];
// P4 — when true, the corpus detail fetch includes retired (is_active=0) titles
// + bullets so the user can review/restore them. Default off: retired items are
// invisible unless this box is ticked.
let _corpusShowRetired = false;

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
  if (name === 'tailor') _fireWizardTourStop();  // KW3: entering the wizard
}

async function loadCorpusIfReady() {
  if (!currentUser) {
    document.getElementById('corpusEmptyHint').textContent =
      'Select a user in the Tailor tab to load their corpus.';
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
  // The onboarding banner refresh fires AFTER _renderCorpusList() (below), not
  // here: its ready/empty decision (Sprint 6.4) reads `_corpusExperiences`,
  // which is still the previous user's value at this point. Both are
  // fire-and-forget — they never block the list load.
  // β.6e — load summary variants alongside experiences. Independent
  // route, independent failure mode — a 5xx on summaries doesn't
  // block the experience list.
  refreshSummaryVariants();
  // B.5 — load the candidate's skills editor alongside; independent route
  // and failure mode (a 5xx on skills doesn't block the experience list).
  refreshSkillsEditor();
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    return;
  }
  if (res.status === 404) {
    _corpusExperiences = [];
    _corpusLoadedForUser = currentUser;
    _renderCorpusList();
    _refreshOnboardingBanner();  // fire-and-forget; fresh emptiness (empty → hides)
    return;
  }
  if (!res.ok) {
    // Surface backend detail (added by list_experiences wrapper).
    const data = await res.json().catch(() => ({}));
    const detail = data.detail || data.error || `status ${res.status}`;
    _setLoadingPlaceholder(list, `Failed to load corpus: ${detail}`);
    return;
  }
  const data = await res.json().catch(() => []);
  // Bare array on success; {experiences:[], needs_onboarding:true} for a
  // brand-new user with no candidate row yet. Treat both as the editable
  // (possibly empty) corpus — the row self-provisions on the first write
  // (résumé import or + ADD EXPERIENCE), so both paths are open immediately.
  _corpusExperiences = Array.isArray(data) ? data : (data.experiences || []);
  _corpusLoadedForUser = currentUser;
  _renderCorpusList();
  _refreshOnboardingBanner();  // fire-and-forget; reads fresh _corpusExperiences
  refreshMergeSuggestions();   // fire-and-forget; hides itself when none found
}

// β.6e — Summary variants editor. Lives at the top of the Career
// Corpus tab; manages the SummaryItem rows the Compose step picks
// from in β.6c. Add / edit / soft-delete; the LLM recommendation +
// per-application pin live in Compose (not here).
async function refreshSummaryVariants() {
  if (!currentUser) return;
  const section = document.getElementById('summaryVariantsSection');
  const listEl  = document.getElementById('summaryVariantsList');
  const hint    = document.getElementById('summaryVariantsEmptyHint');
  if (!section || !listEl) return;
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/summaries`);
  } catch {
    section.style.display = 'none';
    return;
  }
  if (!res.ok) {
    section.style.display = 'none';
    return;
  }
  const body = await res.json();
  const variants = body.summaries || [];
  section.style.display = '';
  _clearChildren(listEl);
  if (variants.length === 0) {
    hint.textContent = 'No summary variants yet. Click + Add variant to '
      + 'create your first positioning summary. Importing a résumé also '
      + 'adds one from its Summary section.';
    return;
  }
  hint.textContent = 'Multiple positioning summaries you can pick from '
    + 'per application. The Compose step recommends the strongest fit '
    + 'for each JD; you can pin a different one there.';
  variants.forEach(v => listEl.appendChild(_renderSummaryVariantRow(v)));
}

function _renderSummaryVariantRow(v) {
  const row = _el('div', { className: 'summary-variant-row' });
  if (v.label) {
    // Make the label itself clickable so users can edit it inline,
    // matching the bullet-row click-to-edit pattern. The dedicated
    // "Rename" button in the row's action area still works (and stays
    // as the primary discoverable affordance with explicit text). The
    // label is also wired as a button via role+tabindex+keyboard handlers
    // so screen-reader and keyboard users have the same access.
    const labelEl = _el('div', {
      className: 'positioning-label',
      textContent: v.label,
      title: 'Click to rename this variant',
    });
    labelEl.style.cursor = 'pointer';
    labelEl.setAttribute('role', 'button');
    labelEl.setAttribute('tabindex', '0');
    labelEl.setAttribute('aria-label', `Rename variant ${v.label}`);
    labelEl.onclick = () => _editSummaryVariantLabel(v.id, v.label);
    labelEl.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        _editSummaryVariantLabel(v.id, v.label);
      }
    };
    row.appendChild(labelEl);
  }
  // Editable text. Save on blur (cheaper than typing-rate writes; also
  // matches the bullet-row inline-edit pattern).
  const ta = _el('textarea', {
    className: 'summary-variant-text',
  });
  ta.value = v.text;
  ta.rows = 3;
  ta.onblur = () => _saveSummaryVariantText(v.id, ta.value, v.text);
  row.appendChild(ta);

  const actions = _el('div', { className: 'summary-variant-actions' });
  const labelBtn = _el('button', {
    className: 'corpus-action-btn',
    textContent: v.label ? 'Rename' : '+ Label',
  });
  labelBtn.onclick = () => _editSummaryVariantLabel(v.id, v.label);
  actions.appendChild(labelBtn);

  const delBtn = _el('button', {
    className: 'corpus-action-btn delete',
    textContent: 'Retire',
    title: 'Soft-retire this variant. Past applications that pinned it '
      + 'still reference it; future Compose steps will skip it.',
  });
  delBtn.onclick = () => _deleteSummaryVariant(v.id);
  actions.appendChild(delBtn);
  row.appendChild(actions);
  return row;
}

async function _saveSummaryVariantText(id, newText, oldText) {
  const trimmed = (newText || '').trim();
  if (!trimmed) {
    _toast('Variant text cannot be empty.', true);
    refreshSummaryVariants();  // restore the original value in the UI
    return;
  }
  if (trimmed === (oldText || '').trim()) return;  // no change
  try {
    const res = await fetch(`/api/summaries/${id}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ text: trimmed }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      _toast(data.error || 'Could not save variant.', true);
      refreshSummaryVariants();
    }
  } catch {
    _toast('Network error saving variant.', true);
    refreshSummaryVariants();
  }
}

async function _editSummaryVariantLabel(id, currentLabel) {
  // Migrated from window.prompt() to openFormModal (2026-05-26) so the
  // visual treatment matches the rest of the app. Blank label clears
  // the label on the server (null in the JSON body) — that flow is
  // preserved by trimming and falling back to null below.
  const values = await openFormModal({
    title: 'Label summary variant',
    subtitle: 'A short tag so you can tell variants apart in the picker.',
    submitLabel: 'Save label',
    fields: [{
      name: 'label',
      label: 'Label',
      type: 'text',
      defaultValue: currentLabel || '',
      placeholder: 'e.g. "AI platform PM", "Design IC"',
    }],
  });
  if (!values) return;  // cancelled
  const trimmed = (values.label || '').trim();
  try {
    const res = await fetch(`/api/summaries/${id}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ label: trimmed || null }),
    });
    if (res.ok) refreshSummaryVariants();
    else _toast('Could not save label.', true);
  } catch {
    _toast('Network error.', true);
  }
}

async function _deleteSummaryVariant(id) {
  if (!confirm('Retire this summary variant?\n\nPast applications that '
               + 'pinned it still reference it; future Compose steps '
               + 'will skip it. You can\'t undo from here.')) return;
  try {
    const res = await fetch(`/api/summaries/${id}`, { method: 'DELETE' });
    if (res.ok) refreshSummaryVariants();
    else _toast('Could not retire variant.', true);
  } catch {
    _toast('Network error.', true);
  }
}

async function openSummaryVariantAdd() {
  if (!currentUser) return;
  // Migrated from a two-prompt chain to openFormModal (2026-05-26).
  // The textarea field gets a sensible-height row count for paragraph-
  // sized summary prose, vs. window.prompt()'s single-line input.
  const values = await openFormModal({
    title: 'Add positioning summary',
    subtitle: 'A reusable positioning paragraph the LLM can pick from. Add label so future picks are recognizable.',
    submitLabel: 'Add variant',
    fields: [
      {
        name: 'text',
        label: 'Summary text',
        type: 'textarea',
        required: true,
        placeholder: 'Paste a positioning paragraph — 2–4 sentences that frame this candidate for a specific kind of role.',
      },
      {
        name: 'label',
        label: 'Label (optional)',
        type: 'text',
        placeholder: 'e.g. "AI platform PM", "Design IC"',
      },
    ],
  });
  if (!values) return;
  const trimmed = (values.text || '').trim();
  if (!trimmed) {
    _toast('Variant text cannot be empty.', true);
    return;
  }
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/summaries`,
      { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          text: trimmed,
          label: (values.label || '').trim() || null,
        }) },
    );
    if (res.ok) refreshSummaryVariants();
    else {
      const data = await res.json().catch(() => ({}));
      _toast(data.error || 'Could not add variant.', true);
    }
  } catch {
    _toast('Network error.', true);
  }
}


// ============================================================
// B.5 (Sprint 6.6) — Skills editor (Career corpus)
// ============================================================
// Candidate-level skill Corpus Items. Add / retire / tag the canonical
// skills, and review (approve / deny) skills the AI proposed from a JD.
// Per-application ordering + pin/drop + recommend/suggest live in Compose.
async function refreshSkillsEditor() {
  if (!currentUser) return;
  const section = document.getElementById('skillsEditorSection');
  const listEl = document.getElementById('skillsEditorList');
  const pendingEl = document.getElementById('skillsEditorPending');
  const hint = document.getElementById('skillsEditorEmptyHint');
  if (!section || !listEl) return;
  let res;
  try {
    res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/skills?include_pending=1`);
  } catch { section.style.display = 'none'; return; }
  if (!res.ok) { section.style.display = 'none'; return; }
  const body = await res.json();
  const all = body.skills || [];
  const pending = all.filter(s => s.is_pending_review);
  const approved = all.filter(s => !s.is_pending_review);
  section.style.display = '';
  _clearChildren(listEl);
  if (pendingEl) _clearChildren(pendingEl);
  if (pendingEl && pending.length) {
    pendingEl.appendChild(_el('div', {
      className: 'edit-hint',
      textContent: `${pending.length} AI-suggested skill${pending.length === 1 ? '' : 's'} to review:`,
    }));
    pending.forEach(s => pendingEl.appendChild(_renderSkillEditorRow(s, true)));
  }
  if (approved.length === 0 && pending.length === 0) {
    hint.textContent = 'No skills yet. Click + Add skill, or import a résumé. '
      + 'The Compose step can also suggest skills your experience shows.';
    return;
  }
  hint.textContent = 'The skills the résumé can surface. The Compose step '
    + 'orders and curates them per job; tailor + AI suggestions live there too.';
  approved.forEach(s => listEl.appendChild(_renderSkillEditorRow(s, false)));
}

function _renderSkillEditorRow(s, isPending) {
  const row = _el('div', { className: 'summary-variant-row skill-editor-row' });
  if (isPending) row.classList.add('skill-pending');
  const head = _el('div', { className: 'skill-editor-head' });
  head.appendChild(_el('span', { className: 'skill-name', textContent: s.name }));
  if (s.category) {
    head.appendChild(_el('span', {
      className: 'skill-category', textContent: ' · ' + s.category,
      style: 'color:var(--fg-2);font-size:0.85em;',
    }));
  }
  row.appendChild(head);

  if (!isPending) {
    const tagWrap = _el('div', {
      className: 'skill-tags', style: 'display:flex;gap:4px;flex-wrap:wrap;margin:4px 0;',
    });
    (s.tags || []).forEach(t => {
      const chip = _el('span', {
        className: 'corpus-row-flag', textContent: t.display_value || t.value,
      });
      const x = _el('button', {
        className: 'tag-remove', textContent: ' ×', title: 'Remove tag',
        style: 'background:none;border:none;cursor:pointer;color:inherit;',
      });
      x.onclick = () => _unlinkSkillTag(s.id, t.id);
      chip.appendChild(x);
      tagWrap.appendChild(chip);
    });
    row.appendChild(tagWrap);
  }

  const actions = _el('div', { className: 'summary-variant-actions' });
  if (isPending) {
    const approve = _el('button', { className: 'corpus-action-btn', textContent: 'Approve' });
    approve.onclick = () => _approveSkill(s.id);
    actions.appendChild(approve);
    const deny = _el('button', { className: 'corpus-action-btn delete', textContent: 'Deny' });
    deny.onclick = () => _denySkill(s.id);
    actions.appendChild(deny);
  } else {
    const tagBtn = _el('button', { className: 'corpus-action-btn', textContent: '+ Tag' });
    tagBtn.onclick = () => _addSkillTag(s.id);
    actions.appendChild(tagBtn);
    const del = _el('button', {
      className: 'corpus-action-btn delete', textContent: 'Retire',
      title: 'Soft-retire this skill. Future Compose steps will skip it.',
    });
    del.onclick = () => _deleteSkillEditor(s.id);
    actions.appendChild(del);
  }
  row.appendChild(actions);
  return row;
}

async function openSkillAdd() {
  if (!currentUser) return;
  const values = await openFormModal({
    title: 'Add skill',
    subtitle: 'A canonical skill the résumé can surface. The Compose step orders + curates per job.',
    submitLabel: 'Add skill',
    fields: [
      { name: 'name', label: 'Skill', type: 'text', required: true, placeholder: 'e.g. Kubernetes' },
      {
        name: 'category', label: 'Category (optional)', type: 'text',
        placeholder: 'language | framework | platform | methodology | domain',
      },
    ],
  });
  if (!values) return;
  const name = (values.name || '').trim();
  if (!name) { _toast('Skill name cannot be empty.', true); return; }
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/skills`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category: (values.category || '').trim() || null }) },
    );
    if (res.ok) refreshSkillsEditor();
    else {
      const d = await res.json().catch(() => ({}));
      _toast(d.error || 'Could not add skill.', true);
    }
  } catch { _toast('Network error.', true); }
}

async function _deleteSkillEditor(id) {
  if (!confirm('Retire this skill?\n\nFuture Compose steps will skip it. '
               + 'Past applications that pinned it still reference it.')) return;
  try {
    const res = await fetch(`/api/skills/${id}`, { method: 'DELETE' });
    if (res.ok) refreshSkillsEditor();
    else _toast('Could not retire skill.', true);
  } catch { _toast('Network error.', true); }
}

async function _approveSkill(id) {
  try {
    const res = await fetch(`/api/skills/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_pending_review: false }),
    });
    if (res.ok) refreshSkillsEditor();
    else _toast('Could not approve skill.', true);
  } catch { _toast('Network error.', true); }
}

async function _denySkill(id) {
  try {
    const res = await fetch(`/api/skills/${id}`, { method: 'DELETE' });
    if (res.ok) refreshSkillsEditor();
    else _toast('Could not deny skill.', true);
  } catch { _toast('Network error.', true); }
}

async function _addSkillTag(skillId) {
  const values = await openFormModal({
    title: 'Tag skill',
    subtitle: 'Tags help the matcher reason about this skill.',
    submitLabel: 'Add tag',
    fields: [{ name: 'value', label: 'Tag', type: 'text', required: true, placeholder: 'e.g. cloud, backend' }],
  });
  if (!values) return;
  const value = (values.value || '').trim();
  if (!value) return;
  try {
    const res = await fetch(`/api/skills/${skillId}/tags`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value, kind: 'domain' }),
    });
    if (res.ok) refreshSkillsEditor();
    else _toast('Could not tag skill.', true);
  } catch { _toast('Network error.', true); }
}

async function _unlinkSkillTag(skillId, tagId) {
  try {
    const res = await fetch(`/api/skills/${skillId}/tags/${tagId}`, { method: 'DELETE' });
    if (res.ok) refreshSkillsEditor();
    else _toast('Could not remove tag.', true);
  } catch { _toast('Network error.', true); }
}


// ============================================================
// B.4 (Sprint 6.6) — per-role intro variants editor (Career corpus)
// ============================================================
// Mirrors the candidate summary-variant editor above, scoped to one
// Experience. Variants are managed against /api/experiences/<id>/summaries
// (GET/POST) + /api/experience-summaries/<id> (PUT/DELETE). In Tailor →
// Compose, turning on "Add role intros" lets the user pick one per JD.

function _renderExperienceSummarySection(expId) {
  const section = _el('div', { className: 'exp-summary-variants-section' });
  section.dataset.expId = String(expId);
  const header = _el('div', { className: 'corpus-section-header' });
  header.appendChild(_el('div', {
    className: 'corpus-section-title', textContent: 'Role intro variants',
  }));
  const addBtn = _el('button', {
    className: 'corpus-action-btn', textContent: '+ Add intro',
  });
  addBtn.type = 'button';
  addBtn.onclick = () => openExperienceSummaryAdd(expId);
  header.appendChild(addBtn);
  section.appendChild(header);
  section.appendChild(_el('div', {
    className: 'edit-hint', id: `expSummaryHint-${expId}`, style: 'margin-bottom:8px',
  }));
  section.appendChild(_el('div', {
    className: 'exp-summary-variants-list', id: `expSummaryList-${expId}`,
  }));
  refreshExperienceSummaries(expId);  // async populate
  return section;
}

async function refreshExperienceSummaries(expId) {
  const listEl = document.getElementById(`expSummaryList-${expId}`);
  const hint = document.getElementById(`expSummaryHint-${expId}`);
  if (!listEl) return;
  let res;
  try {
    res = await fetch(`/api/experiences/${expId}/summaries`);
  } catch {
    return;
  }
  if (!res.ok) return;
  const body = await res.json();
  const variants = body.summaries || [];
  _clearChildren(listEl);
  if (hint) {
    hint.textContent = variants.length === 0
      ? 'No role intros yet. Click + Add intro to create a per-role summary '
        + 'line. In Tailor → Compose, turn on “Add role intros” to use one.'
      : 'Per-role intro lines. The Compose step recommends the strongest fit '
        + 'per JD when you turn on “Add role intros”.';
  }
  variants.forEach(v => listEl.appendChild(_renderExperienceSummaryRow(expId, v)));
}

function _renderExperienceSummaryRow(expId, v) {
  const row = _el('div', { className: 'summary-variant-row' });
  if (v.label) {
    const labelEl = _el('div', {
      className: 'positioning-label', textContent: v.label,
      title: 'Click to rename this variant',
    });
    labelEl.style.cursor = 'pointer';
    labelEl.setAttribute('role', 'button');
    labelEl.setAttribute('tabindex', '0');
    labelEl.setAttribute('aria-label', `Rename intro ${v.label}`);
    labelEl.onclick = () => _editExperienceSummaryLabel(expId, v.id, v.label);
    labelEl.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        _editExperienceSummaryLabel(expId, v.id, v.label);
      }
    };
    row.appendChild(labelEl);
  }
  const ta = _el('textarea', { className: 'summary-variant-text' });
  ta.value = v.text;
  ta.rows = 3;
  ta.onblur = () => _saveExperienceSummaryText(expId, v.id, ta.value, v.text);
  row.appendChild(ta);

  const actions = _el('div', { className: 'summary-variant-actions' });
  const labelBtn = _el('button', {
    className: 'corpus-action-btn', textContent: v.label ? 'Rename' : '+ Label',
  });
  labelBtn.onclick = () => _editExperienceSummaryLabel(expId, v.id, v.label);
  actions.appendChild(labelBtn);
  const delBtn = _el('button', {
    className: 'corpus-action-btn delete', textContent: 'Retire',
    title: 'Soft-retire this intro. Past applications that used it still '
      + 'reference it; future Compose steps will skip it.',
  });
  delBtn.onclick = () => _deleteExperienceSummary(expId, v.id);
  actions.appendChild(delBtn);
  row.appendChild(actions);
  return row;
}

async function _saveExperienceSummaryText(expId, id, newText, oldText) {
  const trimmed = (newText || '').trim();
  if (!trimmed) {
    _toast('Intro text cannot be empty.', true);
    refreshExperienceSummaries(expId);
    return;
  }
  if (trimmed === (oldText || '').trim()) return;
  try {
    const res = await fetch(`/api/experience-summaries/${id}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ text: trimmed }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      _toast(data.error || 'Could not save intro.', true);
      refreshExperienceSummaries(expId);
    }
  } catch {
    _toast('Network error saving intro.', true);
    refreshExperienceSummaries(expId);
  }
}

async function _editExperienceSummaryLabel(expId, id, currentLabel) {
  const values = await openFormModal({
    title: 'Label role intro',
    subtitle: 'A short tag so you can tell intros apart in the picker.',
    submitLabel: 'Save label',
    fields: [{
      name: 'label', label: 'Label', type: 'text',
      defaultValue: currentLabel || '',
      placeholder: 'e.g. "platform-scale framing"',
    }],
  });
  if (!values) return;
  const trimmed = (values.label || '').trim();
  try {
    const res = await fetch(`/api/experience-summaries/${id}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ label: trimmed || null }),
    });
    if (res.ok) refreshExperienceSummaries(expId);
    else _toast('Could not save label.', true);
  } catch {
    _toast('Network error.', true);
  }
}

async function _deleteExperienceSummary(expId, id) {
  if (!confirm('Retire this role intro?\n\nPast applications that used it '
               + 'still reference it; future Compose steps will skip it. '
               + 'You can\'t undo from here.')) return;
  try {
    const res = await fetch(`/api/experience-summaries/${id}`, { method: 'DELETE' });
    if (res.ok) refreshExperienceSummaries(expId);
    else _toast('Could not retire intro.', true);
  } catch {
    _toast('Network error.', true);
  }
}

async function openExperienceSummaryAdd(expId) {
  const values = await openFormModal({
    title: 'Add role intro',
    subtitle: 'A reusable one-line intro for this role the Compose step can pick from.',
    submitLabel: 'Add intro',
    fields: [
      { name: 'text', label: 'Intro text', type: 'textarea', required: true,
        placeholder: 'One or two sentences framing this role — e.g. what you owned and the scale.' },
      { name: 'label', label: 'Label (optional)', type: 'text',
        placeholder: 'e.g. "platform-scale framing"' },
    ],
  });
  if (!values) return;
  const trimmed = (values.text || '').trim();
  if (!trimmed) { _toast('Intro text cannot be empty.', true); return; }
  try {
    const res = await fetch(`/api/experiences/${expId}/summaries`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ text: trimmed, label: (values.label || '').trim() || null }),
    });
    if (res.ok) refreshExperienceSummaries(expId);
    else {
      const data = await res.json().catch(() => ({}));
      _toast(data.error || 'Could not add intro.', true);
    }
  } catch {
    _toast('Network error.', true);
  }
}


function _renderCorpusList() {
  // Wrapped in try/catch with explicit element guards: an earlier
  // screenshot-pass observed _corpusExperiences populated (length 3)
  // but the DOM never receiving .corpus-card elements — a silent
  // throw somewhere between the element lookups and the forEach.
  // Surface any failure to the console so the next reproduction
  // names the culprit directly.
  try {
    const list = document.getElementById('corpusExperienceList');
    const hint = document.getElementById('corpusEmptyHint');
    const toolbar = document.getElementById('corpusToolbar');
    const countEl = document.getElementById('corpusCount');
    if (!list || !hint || !toolbar || !countEl) {
      console.error('[_renderCorpusList] missing required element', {
        list: !!list, hint: !!hint, toolbar: !!toolbar, countEl: !!countEl,
      });
      return;
    }
    toolbar.style.display = '';
    countEl.textContent =
      `${_corpusExperiences.length} experience${_corpusExperiences.length === 1 ? '' : 's'}`;
    _clearChildren(list);
    if (_corpusExperiences.length === 0) {
      hint.textContent = 'No experiences yet. Click + Import résumé to extract '
        + 'your experience from an existing résumé — you review and accept what '
        + 'it finds — or + ADD EXPERIENCE to add one by hand.';
      return;
    }
    hint.textContent = 'Click a card to expand and edit titles + bullets. Saves are inline.';
    _corpusExperiences.forEach((exp, idx) => {
      try {
        list.appendChild(_renderCorpusSummary(exp));
      } catch (e) {
        console.error('[_renderCorpusList] _renderCorpusSummary threw for index', idx, 'exp:', exp, 'err:', e);
      }
    });
  } catch (e) {
    console.error('[_renderCorpusList] threw at top level:', e);
  }
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
  const q = _corpusShowRetired ? '?include_retired=1' : '';
  try {
    res = await fetch(`/api/experiences/${experienceId}${q}`);
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
      className: 'cb-btn cb-bg-teal',
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
  const retire = _el('button', { className: 'cb-btn cb-bg-orange', textContent: 'SOFT-RETIRE EXPERIENCE' });
  retire.onclick = () => deleteExperience(expId);
  btnRow.appendChild(retire);
  body.appendChild(btnRow);
  body.appendChild(_renderTitleSection(expId, exp.titles || []));
  body.appendChild(_renderBulletSection(expId, exp.bullets || []));
  // B.4 — per-role intro variants editor (mirrors the candidate summary-variant
  // editor, scoped to this experience). Loads asynchronously into its list.
  body.appendChild(_renderExperienceSummarySection(expId));
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
  const retired = title.is_active === false;
  const row = _el('div', { className: 'corpus-row' + (retired ? ' retired' : ''), id: `title-row-${title.id}` });
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
  if (retired) {
    row.appendChild(_el('span', { className: 'corpus-row-flag retired', textContent: 'RETIRED' }));
  }
  // Tag chips — Career Corpus parity with the Compose step. Tags
  // already exist on the detail payload via _experience_detail_dict;
  // _renderTagChips wires add/remove inline against the existing
  // /api/experience-titles/<id>/tags endpoints.
  const tagWrap = _el('span', { className: 'tag-chip-wrap' });
  _renderTagChips(tagWrap, 'title', title.id, title.tags || []);
  row.appendChild(tagWrap);
  const actions = _el('div', { className: 'corpus-row-actions' });
  if (retired) {
    const restore = _el('button', { className: 'corpus-action-btn', textContent: 'RESTORE' });
    restore.onclick = async () => {
      try {
        await _putJson(`/api/experience-titles/${title.id}`, { is_active: true });
        await _reloadCorpusCard(expId);
        _toast('Title restored');
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    actions.appendChild(restore);
    row.appendChild(actions);
    return row;
  }
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
  const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'RETIRE' });
  del.onclick = async () => {
    if (!confirm('Retire this title? It is hidden unless you tick "Show retired", and won’t be used in new résumés.')) return;
    try {
      await _deleteJson(`/api/experience-titles/${title.id}`);
      await _reloadCorpusCard(expId);
      await _refreshOnboardingBanner();  // I2: fade the pending banner at 0 pending
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
  const retired = bullet.is_active === false;
  const row = _el('div', { className: 'corpus-row' + (retired ? ' retired' : ''), id: `bullet-row-${bullet.id}` });
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
  if (retired) {
    row.appendChild(_el('span', { className: 'corpus-row-flag retired', textContent: 'RETIRED' }));
  }
  // Tag chips — Career Corpus parity with the Compose step. Tags
  // already ride on the detail payload (_experience_detail_dict),
  // _renderTagChips wires add/remove inline against the existing
  // /api/bullets/<id>/tags endpoints.
  const tagWrap = _el('span', { className: 'tag-chip-wrap' });
  _renderTagChips(tagWrap, 'bullet', bullet.id, bullet.tags || []);
  row.appendChild(tagWrap);
  const actions = _el('div', { className: 'corpus-row-actions' });
  if (retired) {
    const restore = _el('button', { className: 'corpus-action-btn', textContent: 'RESTORE' });
    restore.onclick = async () => {
      try {
        await _putJson(`/api/bullets/${bullet.id}`, { is_active: true });
        await _reloadCorpusCard(expId);
        _toast('Bullet restored');
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    actions.appendChild(restore);
    row.appendChild(actions);
    return row;
  }
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
    if (!confirm('Retire this bullet? It is hidden unless you tick "Show retired", and won’t appear in new résumés.')) return;
    try {
      await _deleteJson(`/api/bullets/${bullet.id}`);
      await _reloadCorpusCard(expId);
      // Walkthrough I2: retiring the last pending bullet must fade the pending
      // banner — accept already refreshed it, retire didn't.
      await _refreshOnboardingBanner();
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

// P4 — global "Show retired" toggle. Re-renders every currently-expanded card
// with (or without) retired titles + bullets. Default off, so retired items are
// never visible unless the user explicitly opts in here.
function toggleCorpusRetired(checked) {
  _corpusShowRetired = !!checked;
  document.querySelectorAll('.corpus-card.expanded').forEach(card => {
    const expId = parseInt(card.dataset.experienceId, 10);
    if (!Number.isNaN(expId)) _loadCorpusDetail(expId);
  });
}

// ---------------------------------------------------------------------------
// P1 — possible-duplicate-roles review (merge suggestions)
// ---------------------------------------------------------------------------

// Fetch + render the "possible duplicate roles" cards. Called after an import
// and on corpus load. Hidden entirely when the server scan finds none.
async function refreshMergeSuggestions() {
  const section = document.getElementById('mergeSuggestionsSection');
  const listEl = document.getElementById('mergeSuggestionsList');
  if (!section || !listEl || !currentUser) return;
  let data;
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/corpus/merge-suggestions`);
    if (!res.ok) { section.classList.add('hidden'); return; }
    data = await res.json();
  } catch {
    section.classList.add('hidden');
    return;
  }
  const suggestions = data.suggestions || [];
  _clearChildren(listEl);
  if (suggestions.length === 0) {
    section.classList.add('hidden');
    return;
  }
  suggestions.forEach(s => listEl.appendChild(_renderMergeSuggestion(s)));
  section.classList.remove('hidden');
}

function _renderMergeSuggestion(s) {
  const card = _el('div', { className: 'merge-suggestion' });
  const fmt = (e) =>
    `${e.company || '(no company)'} · ${e.official_title || '(no title)'}  ` +
    `(${e.start_date} — ${e.end_date || 'current'})`;
  const pair = _el('div', { className: 'merge-suggestion-pair' });
  pair.appendChild(_el('div', { className: 'merge-suggestion-side',
    textContent: fmt(s.exp_in_corpus) + '  — in corpus' }));
  pair.appendChild(_el('div', { className: 'merge-suggestion-side',
    textContent: fmt(s.exp_other) + '  — just imported' }));
  card.appendChild(pair);
  const signals = (s.matched_signals || []).join(', ') || 'similar';
  const n = s.shared_bullet_count || 0;
  card.appendChild(_el('div', { className: 'merge-suggestion-meta',
    textContent: `Match: ${signals} · ${n} shared bullet${n === 1 ? '' : 's'}` }));
  const actions = _el('div', { className: 'merge-suggestion-actions' });
  const merge = _el('button', { className: 'cb-btn cb-bg-teal', textContent: 'Merge into one' });
  merge.onclick = () => _doMerge(s.exp_in_corpus.id, s.exp_other.id);
  const keep = _el('button', { className: 'cb-btn', textContent: 'Keep separate' });
  keep.onclick = () => _dismissMerge(s.exp_a_id, s.exp_b_id);
  actions.appendChild(merge);
  actions.appendChild(keep);
  card.appendChild(actions);
  return card;
}

// Merge the source role into the in-corpus target (which keeps its dates).
async function _doMerge(targetId, sourceId) {
  if (!confirm(
    'Merge these into one role? The extra title becomes an alternate, the ' +
    'bullets combine (duplicates dropped), and the corpus dates are kept.')) return;
  try {
    await _postJson(`/api/experiences/${targetId}/merge`, { source_id: sourceId });
    _toast('Roles merged');
    await refreshCorpus();
    await refreshMergeSuggestions();
  } catch (e) {
    _toast('Merge failed: ' + e.message, true);
  }
}

// Record a "keep separate" decision so the pair stops being suggested.
async function _dismissMerge(expA, expB) {
  try {
    await _postJson(
      `/api/users/${encodeURIComponent(currentUser)}/corpus/merge-suggestions/dismiss`,
      { exp_a_id: expA, exp_b_id: expB });
    await refreshMergeSuggestions();
  } catch (e) {
    _toast('Failed: ' + e.message, true);
  }
}

// P2 — persistent "working…" banner for long actions (ingest / analyze /
// generate). Unlike _toast (2.4s auto-hide), this stays until _setBusy(false),
// so a user who scrolls away still sees the app is busy and not to click around.
function _setBusy(on, label) {
  let bar = document.getElementById('_busyBanner');
  if (on) {
    if (!bar) {
      bar = document.createElement('div');
      bar.id = '_busyBanner';
      bar.className = 'cb-busy-banner';
      bar.setAttribute('role', 'status');
      bar.setAttribute('aria-live', 'polite');
      const dot = document.createElement('span');
      dot.className = 'cb-busy-dot';
      dot.setAttribute('aria-hidden', 'true');
      const text = document.createElement('span');
      text.className = 'cb-busy-text';
      bar.appendChild(dot);
      bar.appendChild(text);
      document.body.appendChild(bar);
    }
    bar.querySelector('.cb-busy-text').textContent =
      (label || 'Working…') + ' — please wait, don’t navigate away.';
    bar.classList.add('show');
    document.body.classList.add('cb-busy');
  } else if (bar) {
    bar.classList.remove('show');
    document.body.classList.remove('cb-busy');
  }
}

async function refreshCorpusSummaryFor(expId) {
  const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
  if (!res.ok) return;
  const body = await res.json().catch(() => []);
  // `/experiences` returns a bare array on success but a needs_onboarding
  // object for un-onboarded users — only treat an array as the list.
  if (!Array.isArray(body)) return;
  _corpusExperiences = body;
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
  if (!confirm('Retire this entire experience? All its bullets become inactive and it drops out of new résumés. You can restore them via "Show retired".')) return;
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
        placeholder: 'YYYY-MM or YYYY', pattern: '\\d{4}(-\\d{2})?' },
      { name: 'end_date',   label: 'End',        type: 'text',
        placeholder: 'YYYY-MM / YYYY (blank = current)', pattern: '\\d{4}(-\\d{2})?' },
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
  if (res.status === 404) {
    _setLoadingPlaceholder(list, 'Candidate not in corpus yet.');
    countEl.textContent = '0 entries';
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load.');
    return;
  }
  const rows = await res.json().catch(() => []);
  if (_needsOnboarding(res, rows)) {
    countEl.textContent = '0 entries';
    _renderCorpusEmptyCTA(list, 'No saved memory yet. Add your résumé in the '
      + 'Career corpus tab to get started.');
    return;
  }
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
      if (res.ok) {
        const body = await res.json().catch(() => []);
        if (Array.isArray(body)) _corpusExperiences = body;
      }
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
  const reviewBtn = document.getElementById('btnReviewNow');
  const acceptBtn = document.getElementById('btnAcceptAllPending');
  const tailorBtn = document.getElementById('btnStartTailoring');
  if (total === 0) {
    // Review finished. Hand the user forward into Tailor only if the corpus
    // actually has material to tailor from (Sprint 6.4); an empty corpus has
    // nothing yet → hide. `_corpusExperiences` is fresh here because callers
    // run this after _renderCorpusList() / a corpus mutation.
    if (_corpusExperiences.length === 0) {
      banner.classList.add('hidden');
      return;
    }
    banner.classList.remove('hidden');
    banner.classList.add('is-ready');
    text.textContent = '✓ Your career corpus is ready.';
    if (reviewBtn) reviewBtn.classList.add('hidden');
    if (acceptBtn) acceptBtn.classList.add('hidden');
    if (tailorBtn) tailorBtn.classList.remove('hidden');
    return;
  }
  banner.classList.remove('hidden', 'is-ready');
  if (reviewBtn) reviewBtn.classList.remove('hidden');
  if (acceptBtn) acceptBtn.classList.remove('hidden');
  if (tailorBtn) tailorBtn.classList.add('hidden');
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

// KW2 — corpus-wide "accept all pending". Clears is_pending_review across
// every role in one click (the per-card ACCEPT ALL PENDING covers by-role).
// Sweeping + high-stakes: accepted items become the source the system scores
// for fit, generates new bullets from, and builds résumés on — so it guards
// behind a sharp confirm even though clearing the flag isn't itself
// destructive.
async function acceptAllPendingCorpus() {
  if (!currentUser) return;
  if (!confirm('Accept every pending item across all roles?\n\n'
      + 'Accepted items become source-of-truth — the system analyzes them for '
      + 'fit, writes new bullets from them, and builds your résumés on them. '
      + 'One bad seed poisons everything downstream. Only accept what you\'ve '
      + 'reviewed and trust.')) return;
  try {
    const r = await _postJson(
      `/api/users/${encodeURIComponent(currentUser)}/accept-all-pending`, {});
    _toast(`Accepted ${r.bullets_accepted} bullet(s) + ${r.titles_accepted} title(s)`);
    await refreshCorpus();            // re-render cards (drops PENDING flags)
    await _refreshOnboardingBanner(); // self-hides at 0 pending
  } catch (e) {
    _toast('Failed: ' + e.message, true);
  }
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
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load duplicates.');
    return;
  }
  const body = await res.json().catch(() => ({}));
  if (_needsOnboarding(res, body)) {
    _setLoadingPlaceholder(list, 'Your corpus is empty — import a résumé or add experiences first.');
    return;
  }
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
      className: 'cb-btn cb-bg-orange', textContent: 'KEEP SELECTED · RETIRE OTHERS',
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

// Walkthrough J1 — retired applications are hidden unless this is on.
let _applicationsShowRetired = false;
function toggleApplicationsRetired(checked) {
  _applicationsShowRetired = !!checked;
  refreshApplications();
}

async function refreshApplications() {
  const list = document.getElementById('applicationsList');
  const countEl = document.getElementById('applicationsCount');
  if (!list) return;
  if (!currentUser) {
    _setLoadingPlaceholder(list, 'Select a user to view their applications.');
    if (countEl) countEl.textContent = '0 applications';
    return;
  }
  // B.8 Part 1: lifecycle filter — server-side via the route's ?status= param
  // (the same query surface the outcome-learning layer uses).
  const statusFilter = document.getElementById('applicationsStatusFilter')?.value || '';
  _setLoadingPlaceholder(list, 'Loading…');
  let res;
  try {
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    if (_applicationsShowRetired) params.set('include_retired', '1');
    const qs = params.toString() ? `?${params.toString()}` : '';
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/applications${qs}`);
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
  const apps = await res.json().catch(() => []);
  if (_needsOnboarding(res, apps)) {
    if (countEl) countEl.textContent = '0 applications';
    _renderCorpusEmptyCTA(list, 'No applications yet. Add your résumé in the '
      + 'Career corpus tab, then analyze a job description.');
    return;
  }
  if (apps.length === 0 && statusFilter) {
    // Distinguish "filtered everything out" from "no applications yet" so
    // the empty-state copy doesn't mislead.
    if (countEl) countEl.textContent = '0 applications';
    _setLoadingPlaceholder(list, 'No applications with this status.');
    return;
  }
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
  const retired = app.is_active === false;
  const card = _el('div', {
    className: 'application-card' + (retired ? ' retired' : ''),
    id: `app-card-${app.id}`,
  });
  const header = _el('div', { className: 'application-card-header' });
  header.appendChild(_el('div', { className: 'application-card-title', textContent: app.title }));
  if (app.company) {
    header.appendChild(_el('div', { className: 'application-card-company', textContent: app.company }));
  }
  card.appendChild(header);

  const meta = _el('div', { className: 'application-card-meta' });
  const chipStatus = app.status || 'draft';
  meta.appendChild(_el('span', {
    className: `app-status-chip status-${chipStatus}`,
    textContent: (chipStatus === 'submitted' ? 'NO RESPONSE' : chipStatus).replace('_', ' ').toUpperCase(),
  }));
  if (retired) {
    meta.appendChild(_el('span', { className: 'app-status-chip status-retired', textContent: 'RETIRED' }));
  }
  const iterText = `${app.iteration_count} iter${app.iteration_count === 1 ? '' : 's'}`;
  meta.appendChild(_el('span', { className: 'application-card-iter', textContent: iterText }));
  if (app.pending_proposals > 0) {
    const badge = _el('span', {
      className: 'application-card-pending',
      textContent: `${app.pending_proposals} to review`,
    });
    badge.title = 'AI-proposed bullets/titles for this application awaiting your review';
    meta.appendChild(badge);
  }
  const outcomeStatuses = new Set(['interview', 'rejected', 'withdrawn']);
  const sentStatuses = new Set(['submitted']);
  let dateLabel;
  if (outcomeStatuses.has(app.status) && app.outcome_at) {
    dateLabel = 'Outcome · ' + _formatRelativeDate(app.outcome_at);
  } else if (sentStatuses.has(app.status) && app.sent_at) {
    dateLabel = 'Sent · ' + _formatRelativeDate(app.sent_at);
  } else {
    dateLabel = _formatRelativeDate(app.updated_at);
  }
  meta.appendChild(_el('span', {
    className: 'application-card-date',
    textContent: dateLabel,
  }));
  card.appendChild(meta);

  // B.8 Part 1 — the status funnel: draft cards offer "Mark submitted"
  // (previously the funnel entry was unreachable — outcome buttons render
  // only on submitted cards, and nothing in the UI ever set submitted).
  // `interview` is terminal: the callback signal this product optimizes for
  // (data-model decision 2026-06-10), so interview/rejected/withdrawn cards
  // get no further actions.
  if (app.status === 'draft') {
    card.appendChild(_statusActionRow(app.id, [
      { label: 'Mark submitted', status: 'submitted' },
    ]));
  } else if (app.status === 'submitted') {
    card.appendChild(_statusActionRow(app.id, [
      { label: 'Got Interview', status: 'interview' },
      { label: 'Got Rejection', status: 'rejected' },
      { label: 'Withdrew', status: 'withdrawn' },
    ]));
  }

  // Walkthrough J1 — retire (hide) a poor/deserted application, or restore one.
  const adminRow = _el('div', { className: 'application-admin-row' });
  if (retired) {
    const restore = _el('button', { className: 'app-admin-btn', textContent: 'Restore' });
    restore.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (await _setApplicationRetired(app.id, false)) refreshApplications();
    });
    adminRow.appendChild(restore);
  } else {
    const retire = _el('button', { className: 'app-admin-btn retire', textContent: 'Retire' });
    retire.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm('Retire this application? It is hidden unless you tick "Show retired". '
        + 'Its iteration history is kept.')) return;
      if (await _setApplicationRetired(app.id, true)) refreshApplications();
    });
    adminRow.appendChild(retire);
  }
  card.appendChild(adminRow);

  card.onclick = () => _showApplicationDetail(app.id);
  return card;
}

// Walkthrough J1 — soft-retire (DELETE) / restore (POST) a prior application.
// Returns true on success so the caller can refresh the list.
async function _setApplicationRetired(appId, retire) {
  try {
    const res = retire
      ? await fetch(`/api/applications/${appId}`, { method: 'DELETE' })
      : await fetch(`/api/applications/${appId}/restore`, { method: 'POST' });
    if (!res.ok) {
      _toast(retire ? 'Retire failed' : 'Restore failed', true);
      return false;
    }
    _toast(retire ? 'Application retired' : 'Application restored');
    return true;
  } catch (e) {
    _toast((retire ? 'Retire' : 'Restore') + ' failed: ' + e.message, true);
    return false;
  }
}

// PUT a lifecycle status for an application; toasts on failure. Shared by
// the card action rows and the Step-6 "mark submitted" nudge (B.8 Part 1).
async function _putApplicationStatus(appId, status) {
  try {
    const res = await fetch(`/api/applications/${appId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      _toast(err.error || 'Failed to update status', true);
      return false;
    }
    return true;
  } catch (e) {
    _toast('Failed to update status: ' + e.message, true);
    return false;
  }
}

function _statusActionRow(appId, actions) {
  const row = _el('div', { className: 'outcome-action-row' });
  actions.forEach(({ label, status }) => {
    const btn = _el('button', { className: 'outcome-btn', textContent: label });
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (await _putApplicationStatus(appId, status)) refreshApplications();
    });
    row.appendChild(btn);
  });
  return row;
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

  const modal = document.getElementById('appDetailModal');
  if (!modal) return;

  // Title
  const titleEl = document.getElementById('appDetailModalTitle');
  titleEl.textContent = detail.company
    ? `${detail.title} @ ${detail.company}`
    : detail.title;

  // Status chip
  const metaEl = document.getElementById('appDetailMeta');
  while (metaEl.firstChild) metaEl.removeChild(metaEl.firstChild);
  const chip = _el('span', {
    className: `app-status-chip status-${detail.status}`,
    textContent: (detail.status || 'draft').toUpperCase(),
  });
  const iters = _el('span', {
    style: 'font-size:12px;color:var(--fg-2);margin-left:10px',
    textContent: `${detail.runs.length} iter${detail.runs.length === 1 ? '' : 's'}`,
  });
  metaEl.appendChild(chip);
  metaEl.appendChild(iters);

  // Timestamps
  const tsEl = document.getElementById('appDetailTimestamps');
  while (tsEl.firstChild) tsEl.removeChild(tsEl.firstChild);
  const tsLines = [];
  if (detail.sent_at) tsLines.push(`Submitted: ${_formatRelativeDate(detail.sent_at)}`);
  if (detail.outcome_at) tsLines.push(`Outcome: ${_formatRelativeDate(detail.outcome_at)}`);
  if (tsLines.length) tsEl.textContent = tsLines.join('  ·  ');

  // Notes textarea
  const notesEl = document.getElementById('appDetailNotes');
  notesEl.value = detail.notes || '';

  // Remove any previous blur listener before adding a new one
  const newNotesEl = notesEl.cloneNode(true);
  notesEl.parentNode.replaceChild(newNotesEl, notesEl);
  newNotesEl.value = detail.notes || '';
  newNotesEl.addEventListener('blur', async () => {
    try {
      const r = await fetch(`/api/applications/${applicationId}/notes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: newNotesEl.value }),
      });
      if (r.ok) {
        _toast('Notes saved');
      } else {
        _toast('Failed to save notes', true);
      }
    } catch (e) {
      _toast('Failed to save notes: ' + e.message, true);
    }
  });

  // #24 — editable job title + company. Save-on-blur → PUT /meta, then refresh
  // the applications list so the edited card reflects it. clone-the-node first
  // (like notes) so re-opening the modal doesn't stack blur listeners.
  const _freshInput = (id) => {
    const el = document.getElementById(id);
    const clone = el.cloneNode(true);
    el.parentNode.replaceChild(clone, el);
    return clone;
  };
  const titleInput = _freshInput('appDetailTitle');
  const companyInput = _freshInput('appDetailCompany');
  titleInput.value = detail.title || '';
  companyInput.value = detail.company || '';
  const _saveMeta = async (payload, okMsg) => {
    try {
      const r = await fetch(`/api/applications/${applicationId}/meta`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (r.ok) { _toast(okMsg); refreshApplications(); return true; }
      const err = await r.json().catch(() => ({}));
      _toast(err.error || 'Failed to save', true);
      return false;
    } catch (e) {
      _toast('Failed to save: ' + e.message, true);
      return false;
    }
  };
  titleInput.addEventListener('blur', async () => {
    const v = (titleInput.value || '').trim();
    if (!v) { titleInput.value = detail.title || ''; return; }  // title is required
    if (v === (detail.title || '')) return;
    if (await _saveMeta({ title: v }, 'Title saved')) detail.title = v;
  });
  companyInput.addEventListener('blur', async () => {
    const v = (companyInput.value || '').trim();
    if (v === (detail.company || '')) return;
    if (await _saveMeta({ company: v }, 'Company saved')) detail.company = v || null;
  });

  // Open modal with Escape + close-button wiring
  const closeBtn = document.getElementById('btnCloseAppDetail');
  const backdrop = document.getElementById('appDetailModalBackdrop');
  const resumeBtn = document.getElementById('btnResumeApp');

  const cleanup = () => {
    modal.classList.add('hidden');
    modal.removeEventListener('keydown', onKey);
    if (closeBtn) closeBtn.removeEventListener('click', cleanup);
    if (backdrop) backdrop.removeEventListener('click', cleanup);
    if (resumeBtn) resumeBtn.removeEventListener('click', onResume);
  };
  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); cleanup(); }
  };
  // D.3.1 — "Resume in wizard" rehydrates the wizard at Step 6 from this
  // application's last generated state. Shown only when a run produced a
  // résumé (resume_state.resumable) so analyzed-only applications don't offer
  // a dead button. Close the modal first, then hand off to the wizard.
  const onResume = () => {
    cleanup();
    resumeApplicationIntoWizard(detail);
  };
  if (resumeBtn) {
    const resumable = !!(detail.resume_state && detail.resume_state.resumable);
    resumeBtn.classList.toggle('hidden', !resumable);
    if (resumable) resumeBtn.addEventListener('click', onResume);
  }

  if (closeBtn) closeBtn.addEventListener('click', cleanup);
  if (backdrop) backdrop.addEventListener('click', cleanup);
  modal.addEventListener('keydown', onKey);
  modal.classList.remove('hidden');
  newNotesEl.focus();
}

// D.3.1 + #4 — Resume a prior application into the live wizard at its FURTHEST
// step with data. `detail` is the GET /api/applications/<id> payload; its
// `resume_state` block carries a `target_step` (1/2/3/6) the backend classified
// from the rediscovered context file, plus the per-step payload to rehydrate
// it. Step 6 converges on the exact state a fresh /api/generate produces by
// REUSING _onGenerationComplete + _renderOutput; Steps 1–3 rehydrate the
// analysis panel (+ saved clarify Q&A) from the context file — no LLM re-spend.
function resumeApplicationIntoWizard(detail) {
  const rs = (detail && detail.resume_state) || {};
  if (!rs.resumable) {
    _toast('Nothing to resume yet — analyze a job description first.', true);
    return;
  }
  const targetStep = rs.target_step || 6;

  // Bind the compose/preview routes to this application + reselect the persona
  // so preview iframes + downloads honor the template. lastContextPath enables
  // the Step 2/3 reachability gate (_wizardReachable).
  _composeApplicationId = detail.id;
  const personaSel = document.getElementById('personaSelect');
  if (personaSel && rs.persona_template_id != null) {
    personaSel.value = String(rs.persona_template_id);
  }
  _selectedPersonaId = rs.persona_template_id ?? _readSelectedPersonaId();
  lastContextPath = rs.context_path || '';

  if (targetStep === 6) {
    _resumeIntoStep6(rs);
  } else {
    _resumeIntoPreGenerateStep(rs, targetStep);
  }
}

// Step 6 — a résumé was generated. lastResumePath isn't a real on-disk path
// here — a truthy value satisfies the Step-6 reachability gate; download reads
// the editor content, not this path.
function _resumeIntoStep6(rs) {
  lastResumePath = lastContextPath || 'resumed';
  lastCoverLetterPath = '';
  lastResumeFormat = '.docx';

  // Shape a synthetic generate-response so the shared completion handlers
  // hydrate the editors, freeze the edit-detect baselines, toggle the CL
  // buttons, and refresh the Step-6 preview iframe exactly as a fresh
  // generation would.
  const data = {
    context_path: rs.context_path || '',
    iteration: rs.iteration || 0,
    resume_preview: rs.resume_md || '',
    cover_letter_preview: rs.cover_letter_md || '',
    persona_template_id: rs.persona_template_id ?? null,
    changes_made: [],
    proofread_notes: [],
  };
  _onGenerationComplete(data);
  _renderOutput(data);

  if (_wizardReachable(6)) {
    _wizardAdvanceTo(6);
  } else {
    // Degraded mode — the on-disk context file was cleaned up, so there's no
    // live context_path to gate on. The run WAS generated, so land on Step 6
    // anyway to expose the editors + download; the rail stays gated because
    // iteration + styled preview need a re-generate (toast below).
    _wizardStep = 6;
    _wizardRender();
    _wizardStampHistory(6);  // PX-22: re-entry baseline at the landed step
  }
  setStatus('RESUMED FROM PRIOR APPLICATION');

  if (!rs.context_path) {
    _toast('Saved layout/context for this application is gone — re-generate to '
      + 'restore the styled preview and continue iterating. Your text is intact.',
      true);
  }
}

// Steps 1–3 — no résumé generated yet. Rehydrate Step 1's analysis panel from
// the saved analysis + deterministic blocks (so back-nav has content), then
// land on the furthest step with data. We deliberately DON'T set lastResumePath
// so Step 6 stays gated until the user actually generates.
function _resumeIntoPreGenerateStep(rs, targetStep) {
  // No résumé for this application — clear any generated-output sentinels left
  // by a prior resume/generation so Step 6 stays correctly gated (a stale
  // lastResumePath would otherwise leak another app's output into the rail).
  lastResumePath = '';
  lastCoverLetterPath = '';

  if (rs.analysis) {
    _renderAnalysis({ analysis: rs.analysis, deterministic: rs.deterministic || {} });
    document.getElementById('analysisPending')?.classList.add('hidden');
    document.getElementById('analysisActions')?.classList.remove('hidden');
  }

  if (targetStep === 2) {
    // Render the saved clarify questions WITHOUT re-spending /api/clarify, then
    // pre-fill each textarea from the saved answers (clarifications: {id: text}).
    lastClarifyQuestions = rs.clarification_questions || [];
    _renderClarifyQuestions(lastClarifyQuestions, '');
    const answers = rs.clarifications || {};
    document.querySelectorAll('#clarifyQuestions .clarify-question').forEach(el => {
      const qid = el.getAttribute('data-qid');
      const ta = el.querySelector('.clarify-answer');
      if (qid && ta && answers[qid]) ta.value = answers[qid];
    });
  }

  // Set the step directly (not _wizardAdvanceTo, which only moves forward) so
  // we can land on a lower step than the rail's current position. lastContextPath
  // is set, so steps 2–3 pass _wizardReachable.
  _wizardStep = targetStep;
  _wizardRender();
  if (targetStep === 3) loadComposition();
  _wizardStampHistory(targetStep);  // PX-22: re-entry baseline at the landed step
  setStatus('RESUMED FROM PRIOR APPLICATION');
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
    // Surface backend detail (added by list_bundled_personas wrapper).
    const data = await res.json().catch(() => ({}));
    const detail = data.detail || data.error || `status ${res.status}`;
    _setLoadingPlaceholder(grid, `Failed to load bundled: ${detail}`);
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
    // Surface the backend's detail field when present (added by the
    // 5xx-logging wrapper on list_user_personas in app.py 2026-05-26).
    // Pre-fix this returned a bare "Failed to load." with no clue;
    // now the user sees the exception class so triage is possible
    // without checking the Flask terminal.
    const data = await res.json().catch(() => ({}));
    const detail = data.detail || data.error || `status ${res.status}`;
    _setLoadingPlaceholder(grid, `Failed to load: ${detail}`);
    return;
  }
  const body = await res.json().catch(() => ({}));
  if (_needsOnboarding(res, body)) {
    _renderCorpusEmptyCTA(grid, 'Add your résumé in the Career corpus tab to '
      + 'manage your own templates.');
    return;
  }
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
    className: 'corpus-action-btn', textContent: 'OPEN PREVIEW',
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
  // Migrated from window.prompt() to openFormModal (2026-05-26) for
  // visual consistency with the rest of the corpus / persona editors.
  const values = await openFormModal({
    title: 'Rename persona',
    subtitle: 'The name shown in the template picker. Renames the persona row; does not move the underlying .docx on disk.',
    submitLabel: 'Rename',
    fields: [{
      name: 'name',
      label: 'New name',
      type: 'text',
      required: true,
      defaultValue: currentName,
      placeholder: 'e.g. "Modern One-Column", "Classic With Sidebar"',
    }],
  });
  if (!values) return;
  const next = (values.name || '').trim();
  if (!next || next === currentName) return;
  try {
    await _putJson(`/api/personas/${id}`, { name: next });
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
  _wizardStampHistory(1);  // PX-22: baseline history entry so Back from step 2 lands on step 1
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

function wizardGoTo(step, opts) {
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
  // PX-22: record a history entry for this step change, UNLESS this call is the
  // popstate restore itself (which must not re-push, or Back/Forward would stack).
  if (!(opts && opts.fromHistory)) _wizardPushHistory(step);
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
    // Walkthrough E3: the rail reads as a passive progress bar, so back-nav went
    // unnoticed. A tooltip on reachable steps announces they're clickable.
    const _lbl = btn.querySelector('.wizard-label');
    const _lblText = (_lbl && _lbl.textContent) ? _lbl.textContent : `Step ${s}`;
    if (btn.disabled) btn.removeAttribute('title');
    else btn.title = isActive ? `You're on step ${s}: ${_lblText}`
                              : `Go to step ${s}: ${_lblText}`;
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
  _fireWizardTourStop();  // KW3: first time this step's panel is shown
}

// Advance the rail automatically as the underlying flow completes.
function _wizardAdvanceTo(step) {
  if (step > _wizardStep && _wizardReachable(step)) {
    _wizardStep = step;
    _wizardPushHistory(step);  // PX-22: auto-advance pushes too, so Back unwinds it
  }
  _wizardRender();
}

// ---------------------------------------------------------------------------
// PX-22 — browser Back/Forward traverse wizard steps within the session.
// We push a {wizardStep} history entry on each step change and restore on
// popstate. Scope is deliberately session-only: no address-bar `?step=N` and no
// deep-link-on-load restore, so the forward-gating rule (`_wizardReachable`)
// stays uncoupled from the URL. `_wizardStampHistory` (replaceState) marks a
// re-entry baseline (wizardInit + the resume-from-prior landings) so Back from
// the first step leaves the wizard cleanly instead of restoring a stale step;
// `_wizardPushHistory` (pushState) records a transition.
// ---------------------------------------------------------------------------
function _wizardStampHistory(step) {
  try { history.replaceState({ wizardStep: step }, ''); } catch (e) { /* history unavailable */ }
}

function _wizardPushHistory(step) {
  try {
    // Don't stack a duplicate entry for the step already current — some flows
    // navigate to the same step twice (e.g. Skip-to-Compose runs `wizardGoTo(3)`
    // then skipClarifications → compose again). A duplicate would make one Back
    // press look dead. A real transition (different step) always pushes.
    if (history.state && history.state.wizardStep === step) return;
    history.pushState({ wizardStep: step }, '');
  } catch (e) { /* history unavailable */ }
}

function _onWizardPopState(e) {
  const step = e.state && e.state.wizardStep;
  if (typeof step !== 'number') return;     // pre-wizard entry — let the browser leave the wizard
  if (!_wizardReachable(step)) return;      // context changed; don't force an unreachable step
  wizardGoTo(step, { fromHistory: true });  // restore UI + step side-effects; no re-push
}

window.addEventListener('popstate', _onWizardPopState);

// ===============================================================
// Workstream E — Step 3 Compose (fit-ranked bullets/titles)
// ===============================================================

let _composeApplicationId = null;
// B.4 — whether the "Add role intros" toggle is on for the loaded application.
let _composeUseRoleIntros = false;

async function loadComposition() {
  const list = document.getElementById('composeList');
  if (!list) return;
  // Test-observability settle signal (no product behavior; nothing reads it).
  // Cleared here at entry — BEFORE the /composition fetch opens — so the marker
  // is absent for a render pass's entire in-flight duration, and the auto-
  // recommend re-render cascade (each pass re-enters loadComposition) clears it
  // again every pass. It is re-set only after the final synchronous append
  // below, so a *stably present* marker proves the terminal render was reached.
  // Consumed by ui_pages/wizard_compose.py::_wait_settled (Compose flaky-class fix).
  list.removeAttribute('data-compose-ready');
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
  // β.6c — Positioning card renders first, above the experience cards.
  // Shows the candidate's SummaryItem variants with the recommendation
  // (if any) flagged and the user's pin (if any) marking the chosen one.
  // Auto-fires recommend-summary in the background when there's no
  // recommendation yet and the candidate has 2+ variants.
  const summary = data.summary || {};
  if ((summary.variants || []).length > 0) {
    list.appendChild(_renderPositioningCard(summary));
    if (!summary.has_recommendation && (summary.variants || []).length > 1) {
      _fireRecommendSummary();
    }
  }
  // B.5 — Skills card. Candidate-level (like Positioning), rendered above the
  // experience cards. Surfaces the curated/ordered skills with pin/drop +
  // "Tailor"/"Suggest" actions and a pending-review lane. Auto-fires
  // recommend-skills once when there's no ordering yet and 2+ skills exist.
  const skills = data.skills || {};
  if ((skills.items || []).length > 0 || (skills.pending || []).length > 0) {
    list.appendChild(_renderSkillsCard(skills));
    if (!skills.has_recommendation && (skills.items || []).length > 1) {
      _fireRecommendSkills();
    }
  }
  if (!data.experiences || data.experiences.length === 0) {
    _setLoadingPlaceholder(list, 'No corpus experiences to rank.');
    return;
  }
  // B.4 — "Add role intros" application-level toggle + per-role pickers inside
  // each experience card. The toggle is the explicit opt-in: when off (default)
  // no role intro reaches the résumé and the generate prompt is byte-identical.
  _composeUseRoleIntros = !!data.use_experience_summaries;
  const anyRoleVariants = (data.experiences || []).some(
    e => ((e.summary || {}).variants || []).length > 0);
  if (anyRoleVariants) list.appendChild(_renderRoleIntrosToggle(_composeUseRoleIntros));
  data.experiences.forEach(exp => list.appendChild(_renderComposeCard(exp)));
  if (anyRoleVariants) {
    // Show/hide the per-role pickers + default each opted-in role to the AI's
    // recommendation. Then opportunistically fire the per-role recommend (one
    // Haiku call) only when opted in and a role still lacks one.
    _applyRoleIntros(_composeUseRoleIntros);
    if (_composeUseRoleIntros) _maybeFireRecommendExperienceSummaries();
  }
  // Compose-step inline preview was removed in the 2026-05-25 punch list
  // — it competed for attention with the bullet-curation work and didn't
  // pay for its real estate. The preview lives in Step 4 (Template) and
  // Step 6 (Output) where it's clearly relevant.
  // Terminal render reached — re-set the settle marker cleared at entry (above).
  list.setAttribute('data-compose-ready', '1');
}

// PX-22: load a preview iframe WITHOUT adding a joint session-history entry, so
// the browser Back / Forward buttons traverse wizard steps (see
// _wizardPushHistory) instead of unwinding preview reloads. Setting `frame.src`
// pushes a history entry on every refresh; `contentWindow.location.replace()`
// navigates in place (no entry). The preview iframes are same-origin
// (sandbox="allow-scripts allow-same-origin"), so contentWindow access is
// permitted; the `frame.src` fallback covers a detached frame with no window.
function _loadPreviewFrame(frame, url) {
  if (frame.contentWindow) {
    frame.contentWindow.location.replace(url);
  } else {
    frame.src = url;
  }
}

// β.6 post-review — refresh the Step 6 (Output) résumé preview iframe.
// Shows the styled document the user downloads (post-WYSIWYG: the route
// serves the cached last_generated_json_resume, so preview == download
// content). The raw markdown editor lives behind the "Edit before
// downloading" drawer.
async function _refreshOutputPreview() {
  const block = document.getElementById('outputPreviewBlock');
  const frame = document.getElementById('outputPreviewFrame');
  if (!block || !frame) return;
  if (_composeApplicationId == null) {
    block.classList.add('hidden');
    return;
  }
  const params = new URLSearchParams();
  const sel = _readSelectedPersonaId();
  if (sel != null) params.set('template_id', String(sel));
  if (lastContextPath) params.set('context_path', lastContextPath);
  block.classList.remove('hidden');
  const pageInfo = document.getElementById('outputPreviewPageInfo');
  if (pageInfo) pageInfo.textContent = 'Page — of —';
  _wirePreviewPageCount(frame, 'outputPreviewPageInfo');
  _loadPreviewFrame(frame, `/api/applications/${_composeApplicationId}/preview?${params.toString()}`);
}

// v1.0.5 (Step 6 redesign) — refresh the Step 6 cover-letter preview iframe.
// Renders the generated cover letter through the shared business-letter shell
// styled to the chosen persona's font. The route returns a placeholder until
// a cover letter has been generated, so this is safe to call on tab show even
// before "+ Generate cover letter" is clicked.
async function _refreshCoverPreview() {
  const block = document.getElementById('coverPreviewBlock');
  const frame = document.getElementById('coverPreviewFrame');
  if (!block || !frame) return;
  if (_composeApplicationId == null) {
    block.classList.add('hidden');
    return;
  }
  const params = new URLSearchParams();
  const sel = _readSelectedPersonaId();
  if (sel != null) params.set('template_id', String(sel));
  if (lastContextPath) params.set('context_path', lastContextPath);
  block.classList.remove('hidden');
  const pageInfo = document.getElementById('coverPreviewPageInfo');
  if (pageInfo) pageInfo.textContent = 'Page — of —';
  _wirePreviewPageCount(frame, 'coverPreviewPageInfo');
  _loadPreviewFrame(frame, `/api/applications/${_composeApplicationId}/cover-letter-preview?${params.toString()}`);
}

// β.6c — fire recommend-summary in the background. Idempotent on the
// server (it overwrites llm_summary_recommendation on each call). The
// route returns the same shape as a fresh composition refresh, so we
// reload composition after to surface the recommendation chips.
async function _fireRecommendSummary() {
  if (_composeApplicationId == null || !lastContextPath) return;
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/recommend-summary`,
      { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) {
      // Refresh the composition view so the new recommendation chip
      // shows on the Positioning card. Cheap — no LLM call on this
      // refresh, just a re-read of the persisted JSON.
      loadComposition();
    }
  } catch {
    // Non-blocking — Compose still works without the recommendation.
  }
}

// β.6c — Positioning card. Sits above the experience cards in Step 3.
// One variant chosen per application (either the LLM's recommendation
// or a user pin). Clicking a non-chosen variant pins it; clicking the
// pinned variant unpins (falls back to the recommendation).
function _renderPositioningCard(summary) {
  const card = _el('div', { className: 'compose-experience-card positioning-card' });
  const header = _el('div', { className: 'compose-exp-header' });
  header.appendChild(_el('div', {
    className: 'compose-exp-company', textContent: 'Positioning',
  }));
  card.appendChild(header);

  card.appendChild(_el('div', {
    className: 'edit-hint', style: 'margin-top:4px',
    textContent: 'Which summary variant frames you for this JD. '
      + 'Click a variant to pin it for this application; '
      + 'click the pinned one again to unpin and accept the recommendation.',
  }));

  const variants = summary.variants || [];
  variants.forEach(v => card.appendChild(_renderPositioningVariant(v, summary.chosen_id)));
  return card;
}

function _renderPositioningVariant(v, chosenId) {
  const row = _el('div', { className: 'compose-row positioning-variant' });
  const isChosen = v.id === chosenId;
  if (isChosen) row.classList.add('positioning-chosen');

  const text = _el('div', { className: 'row-text' });
  if (v.label) {
    text.appendChild(_el('div', {
      className: 'positioning-label', textContent: v.label,
    }));
  }
  text.appendChild(_el('div', { className: 'positioning-text', textContent: v.text }));
  row.appendChild(text);

  const meta = _el('div', { className: 'row-meta' });
  if (v.recommended) {
    const chip = _el('span', {
      className: 'corpus-row-flag',
      textContent: 'Recommended',
      style: 'background:var(--brand);color:var(--bg-0);',
    });
    if (v.rationale) chip.title = v.rationale;
    meta.appendChild(chip);
  }
  if (v.pinned) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag',
      textContent: 'Pinned',
      style: 'background:var(--brand-hi);color:var(--bg-0);',
    }));
  }
  if (v.has_outcome) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag outcome', textContent: 'Outcome',
    }));
  }
  row.appendChild(meta);

  // Click handler — pin/unpin via /api/applications/<id>/composition
  row.style.cursor = 'pointer';
  row.onclick = () => _togglePositioningPin(v.id, isChosen && v.pinned);
  return row;
}

// β.6c — toggle pin state. The caller passes the variant id + whether
// it's currently the user-pinned (not just LLM-recommended) variant.
// When already pinned: send pinned_summary_id=null to clear; when not
// pinned: send the id. Refreshes composition after so the chips
// re-render.
async function _togglePositioningPin(summaryId, alreadyPinned) {
  if (_composeApplicationId == null || !lastContextPath) return;
  // Collect the FULL composition state (bullets + bullet_order + title pins +
  // role intros) via the canonical gatherer, then set the summary pin. The
  // POST route rebuilds composition_overrides WHOLESALE, so a partial body
  // silently drops every field it omits — this path used to hand-gather only
  // bullets, which clobbered bullet_order + pinned_title_ids on every summary
  // pin. Routing through _collectCompositionState() fixes that and keeps all
  // override families (incl. B.4 role intros) intact on one save.
  const state = _collectCompositionState();
  state.pinned_summary_id = alreadyPinned ? null : summaryId;
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/composition`,
      { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ context_path: lastContextPath, ...state }) },
    );
    if (res.ok) loadComposition();
  } catch {
    // Non-blocking
  }
}

// ============================================================
// B.5 (Sprint 6.6) — skill curation card (Compose step)
// ============================================================

// Candidate-level Skills card. Shows the curated/ordered skills for this JD
// with pin (force-include) / drop (exclude) / reorder, a "Tailor skills to
// this JD" action (recommend_skills) and a "Suggest skills" action
// (suggest_skills, grounded). Pending suggestions land in a review lane with
// Approve / Deny. State rides along on every composition save via
// _collectSkillState() so a bullet/title save never clobbers it.
function _renderSkillsCard(skills) {
  const card = _el('div', { className: 'compose-experience-card skills-card' });
  const header = _el('div', { className: 'compose-exp-header' });
  header.appendChild(_el('div', {
    className: 'compose-exp-company', textContent: 'Skills',
  }));
  card.appendChild(header);
  card.appendChild(_el('div', {
    className: 'edit-hint', style: 'margin-top:4px',
    textContent: 'Which skills to surface for this JD, in order. '
      + '“Tailor” orders them by relevance; pin to force-keep, drop to hide. '
      + '“Suggest” proposes skills your experience shows that you haven’t added yet.',
  }));

  // Action buttons
  const actions = _el('div', { className: 'skills-actions', style: 'margin:6px 0;display:flex;gap:8px;flex-wrap:wrap;' });
  const tailorBtn = _el('button', {
    className: 'btn-secondary btn-sm', textContent: 'Tailor skills to this JD',
  });
  tailorBtn.onclick = () => _fireRecommendSkills(true);
  actions.appendChild(tailorBtn);
  const suggestBtn = _el('button', {
    className: 'btn-secondary btn-sm', textContent: 'Suggest skills from this JD',
  });
  suggestBtn.onclick = () => _fireSuggestSkills(suggestBtn);
  actions.appendChild(suggestBtn);
  card.appendChild(actions);

  // Ordered list: chosen ids first (effective order), then dropped/unchosen ones.
  const items = skills.items || [];
  const byId = {};
  items.forEach(it => { byId[it.id] = it; });
  const chosen = (skills.chosen_ids || []).filter(id => byId[id]);
  const chosenSet = new Set(chosen);
  const rest = items.filter(it => !chosenSet.has(it.id)).map(it => it.id);
  const orderedIds = chosen.concat(rest);

  const skillList = _el('div', { className: 'compose-skill-list' });
  skillList.dataset.customOrder = 'false';
  orderedIds.forEach(id => skillList.appendChild(_renderSkillRow(byId[id])));
  card.appendChild(skillList);

  // Pending review lane (llm_proposed suggestions awaiting approve/deny).
  const pending = skills.pending || [];
  if (pending.length) {
    const lane = _el('div', { className: 'skills-pending-lane', style: 'margin-top:10px;' });
    lane.appendChild(_el('div', {
      className: 'edit-hint',
      textContent: `${pending.length} suggested skill${pending.length === 1 ? '' : 's'} to review`,
    }));
    pending.forEach(p => lane.appendChild(_renderPendingSkillRow(p)));
    card.appendChild(lane);
  }
  return card;
}

function _renderSkillRow(it) {
  const row = _el('div', { className: 'compose-row compose-skill-row' });
  row._skillState = { id: it.id, pinned: !!it.pinned, excluded: !!it.excluded };
  if (it.excluded) row.classList.add('skill-excluded');

  const text = _el('div', { className: 'row-text' });
  text.appendChild(_el('span', { className: 'skill-name', textContent: it.name }));
  if (it.category) {
    text.appendChild(_el('span', {
      className: 'skill-category', textContent: ' · ' + it.category,
      style: 'color:var(--fg-2);font-size:0.85em;',
    }));
  }
  row.appendChild(text);

  const meta = _el('div', { className: 'row-meta' });
  if (it.recommended) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag', textContent: 'Recommended',
      style: 'background:var(--brand);color:var(--bg-0);',
    }));
  }
  // Pin toggle
  const pinBtn = _el('button', {
    className: 'btn-icon skill-pin', title: 'Pin (always include)',
    textContent: it.pinned ? '📌' : '📍',
  });
  pinBtn.onclick = () => _toggleSkillPin(row);
  meta.appendChild(pinBtn);
  // Drop toggle
  const dropBtn = _el('button', {
    className: 'btn-icon skill-drop', title: it.excluded ? 'Restore' : 'Drop (hide)',
    textContent: it.excluded ? '↩' : '✕',
  });
  dropBtn.onclick = () => _toggleSkillDrop(row);
  meta.appendChild(dropBtn);
  // Reorder up/down
  const upBtn = _el('button', { className: 'btn-icon skill-up', title: 'Move up', textContent: '↑' });
  upBtn.onclick = () => _moveSkillRow(row, -1);
  meta.appendChild(upBtn);
  const downBtn = _el('button', { className: 'btn-icon skill-down', title: 'Move down', textContent: '↓' });
  downBtn.onclick = () => _moveSkillRow(row, 1);
  meta.appendChild(downBtn);

  row.appendChild(meta);
  return row;
}

function _toggleSkillPin(row) {
  const s = row._skillState; if (!s) return;
  s.pinned = !s.pinned;
  if (s.pinned) { s.excluded = false; row.classList.remove('skill-excluded'); }
  const btn = row.querySelector('.skill-pin');
  if (btn) btn.textContent = s.pinned ? '📌' : '📍';
  _scheduleCompositionSave();
}

function _toggleSkillDrop(row) {
  const s = row._skillState; if (!s) return;
  s.excluded = !s.excluded;
  if (s.excluded) { s.pinned = false; }
  row.classList.toggle('skill-excluded', s.excluded);
  const pin = row.querySelector('.skill-pin');
  if (pin) pin.textContent = s.pinned ? '📌' : '📍';
  const drop = row.querySelector('.skill-drop');
  if (drop) { drop.textContent = s.excluded ? '↩' : '✕'; drop.title = s.excluded ? 'Restore' : 'Drop (hide)'; }
  _scheduleCompositionSave();
}

function _moveSkillRow(row, dir) {
  const list = row.closest('.compose-skill-list');
  if (!list) return;
  if (dir < 0 && row.previousElementSibling) {
    list.insertBefore(row, row.previousElementSibling);
  } else if (dir > 0 && row.nextElementSibling) {
    list.insertBefore(row.nextElementSibling, row);
  } else {
    return;
  }
  list.dataset.customOrder = 'true';
  _scheduleCompositionSave();
}

// B.5 — snapshot the skill curation state from the DOM for the composition
// save. pinned/excluded come from each row's _skillState; skill_order is sent
// only when the user explicitly reordered (data-custom-order), mirroring
// bullet_order — so an untouched card keeps the default path byte-identical.
function _collectSkillState() {
  const pinned_skill_ids = [];
  const excluded_skill_ids = [];
  document.querySelectorAll('#composeList .compose-skill-row').forEach(row => {
    const s = row._skillState; if (!s) return;
    if (s.pinned) pinned_skill_ids.push(s.id);
    if (s.excluded) excluded_skill_ids.push(s.id);
  });
  let skill_order = [];
  const list = document.querySelector('#composeList .compose-skill-list');
  if (list && list.dataset.customOrder === 'true') {
    list.querySelectorAll('.compose-skill-row').forEach(row => {
      const s = row._skillState;
      if (s && s.id != null && !s.excluded) skill_order.push(s.id);
    });
  }
  return { pinned_skill_ids, excluded_skill_ids, skill_order };
}

// Fire recommend-skills (Haiku ordering). Idempotent server-side. Reloads
// composition after so the new order + chips render. `explicit` distinguishes a
// user click (always run) from the auto-fire on first load.
async function _fireRecommendSkills(explicit) {
  if (_composeApplicationId == null || !lastContextPath) return;
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/recommend-skills`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) loadComposition();
    else if (explicit) _toast('Could not tailor skills.', true);
  } catch {
    if (explicit) _toast('Network error tailoring skills.', true);
  }
}

// Fire suggest-skills (grounded generator). Proposals land as pending rows;
// reload composition to surface the review lane.
async function _fireSuggestSkills(btn) {
  if (_composeApplicationId == null || !lastContextPath) return;
  if (btn) { btn.disabled = true; btn.textContent = 'Suggesting…'; }
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/suggest-skills`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) {
      const body = await res.json().catch(() => ({}));
      const n = (body.proposals || []).length;
      _toast(n ? `${n} skill suggestion${n === 1 ? '' : 's'} to review.` : 'No new grounded skills found.');
      loadComposition();
    } else {
      _toast('Could not suggest skills.', true);
    }
  } catch {
    _toast('Network error suggesting skills.', true);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Suggest skills from this JD'; }
  }
}

function _renderPendingSkillRow(p) {
  const row = _el('div', { className: 'compose-row pending-skill-row' });
  const text = _el('div', { className: 'row-text' });
  text.appendChild(_el('span', { className: 'skill-name', textContent: p.name }));
  if (p.category) {
    text.appendChild(_el('span', {
      className: 'skill-category', textContent: ' · ' + p.category,
      style: 'color:var(--fg-2);font-size:0.85em;',
    }));
  }
  row.appendChild(text);
  const meta = _el('div', { className: 'row-meta' });
  const approve = _el('button', { className: 'btn-secondary btn-sm', textContent: 'Approve' });
  approve.onclick = () => _reviewPendingSkill(p.id, true);
  meta.appendChild(approve);
  const deny = _el('button', { className: 'btn-secondary btn-sm', textContent: 'Deny' });
  deny.onclick = () => _reviewPendingSkill(p.id, false);
  meta.appendChild(deny);
  row.appendChild(meta);
  return row;
}

// Approve (PUT is_pending_review=false → joins the canonical set) or deny
// (DELETE → hard-removes the never-approved suggestion). Reloads composition.
async function _reviewPendingSkill(skillId, approve) {
  try {
    const res = approve
      ? await fetch(`/api/skills/${skillId}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_pending_review: false }) })
      : await fetch(`/api/skills/${skillId}`, { method: 'DELETE' });
    if (res.ok) loadComposition();
    else _toast('Could not update the suggested skill.', true);
  } catch {
    _toast('Network error updating the suggested skill.', true);
  }
}

// ============================================================
// B.4 (Sprint 6.6) — per-role intro picker (Compose step)
// ============================================================

// "Add role intros" application-level toggle. Off by default (opt-in): nothing
// reaches the résumé until the user turns it on. On enable, each role defaults
// to the AI's recommended intro; the user can change or clear per role.
function _renderRoleIntrosToggle(checked) {
  const wrap = _el('div', { className: 'compose-role-intros-toggle' });
  const label = _el('label', { className: 'compose-role-intros-label' });
  const cb = _el('input', { type: 'checkbox', id: 'composeRoleIntrosToggle' });
  cb.checked = !!checked;
  cb.onchange = () => _onRoleIntrosToggle(cb.checked);
  label.appendChild(cb);
  label.appendChild(_el('span', {
    textContent: ' Add role intros — a per-role summary line tailored to this job',
  }));
  wrap.appendChild(label);
  wrap.appendChild(_el('div', {
    className: 'edit-hint',
    textContent: 'Off by default. When on, each role gets the AI’s suggested '
      + 'intro; click another variant to change it, or the chosen one to clear it.',
  }));
  return wrap;
}

async function _onRoleIntrosToggle(checked) {
  _composeUseRoleIntros = checked;
  _applyRoleIntros(checked);
  // Persist immediately so a subsequent recommend reload reads the toggle.
  try {
    await _postComposition(_collectCompositionState());
  } catch (e) {
    _toast('Autosave failed: ' + e.message, true);
  }
  if (checked) _maybeFireRecommendExperienceSummaries();
}

// Show/hide each role's picker for the current toggle state. When on, default
// any undecided role to its recommendation; then re-mark the chosen row.
function _applyRoleIntros(checked) {
  document.querySelectorAll('#composeList .compose-role-intro[data-exp-id]').forEach(sec => {
    sec.classList.toggle('hidden', !checked);
    if (checked
        && (sec.dataset.chosenSummaryId === '' || sec.dataset.chosenSummaryId == null)
        && sec.dataset.recommendedId) {
      sec.dataset.chosenSummaryId = sec.dataset.recommendedId;
    }
    _markRoleIntroChosen(sec);
  });
}

function _markRoleIntroChosen(sec) {
  const raw = sec.dataset.chosenSummaryId;
  const chosen = (raw !== '' && raw != null) ? Number(raw) : null;
  sec.querySelectorAll('.role-intro-variant').forEach(row => {
    const isChosen = chosen != null && chosen > 0 && Number(row.dataset.summaryId) === chosen;
    row.classList.toggle('role-intro-chosen', isChosen);
    _setChosenChip(row, isChosen);
  });
}

function _setChosenChip(row, isChosen) {
  const meta = row.querySelector('.row-meta');
  if (!meta) return;
  const existing = [...meta.querySelectorAll('.corpus-row-flag')]
    .find(c => c.textContent === 'Chosen');
  if (isChosen && !existing) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag', textContent: 'Chosen',
      style: 'background:var(--brand-hi);color:var(--bg-0);',
    }));
  } else if (!isChosen && existing) {
    existing.remove();
  }
}

// Per-role intro picker rendered inside each compose card (hidden unless the
// toggle is on). dataset.recommendedId / chosenSummaryId drive defaulting +
// persistence; show/hide + chosen-marking happen in _applyRoleIntros.
function _renderComposeRoleIntro(exp) {
  const summary = exp.summary || {};
  const variants = summary.variants || [];
  const section = _el('div', { className: 'compose-role-intro hidden' });
  section.dataset.expId = String(exp.id);
  if (summary.recommended_id != null) {
    section.dataset.recommendedId = String(summary.recommended_id);
  }
  section.dataset.chosenSummaryId =
    (summary.chosen_id != null) ? String(summary.chosen_id) : '';

  const header = _el('div', { className: 'compose-exp-section-title' });
  header.appendChild(_el('span', { textContent: 'Role intro' }));
  const addBtn = _el('button', {
    className: 'corpus-action-btn', textContent: '+ Add intro',
  });
  addBtn.type = 'button';
  addBtn.dataset.expId = String(exp.id);
  addBtn.onclick = () => _addComposeRoleIntro(exp.id);
  header.appendChild(addBtn);
  section.appendChild(header);

  if (!variants.length) {
    section.appendChild(_el('div', {
      className: 'compose-empty-experience',
      textContent: 'No intro variants yet — add one to use a per-role summary line.',
    }));
    return section;
  }

  const variantsWrap = _el('div', { className: 'compose-role-intro-variants' });
  variants.forEach(v => variantsWrap.appendChild(_renderRoleIntroVariant(v, exp.id)));
  section.appendChild(variantsWrap);
  return section;
}

function _renderRoleIntroVariant(v, expId) {
  const row = _el('div', { className: 'compose-row role-intro-variant' });
  row.dataset.summaryId = String(v.id);
  const text = _el('div', { className: 'row-text' });
  if (v.label) {
    text.appendChild(_el('div', { className: 'positioning-label', textContent: v.label }));
  }
  text.appendChild(_el('div', { className: 'positioning-text', textContent: v.text }));
  row.appendChild(text);

  const meta = _el('div', { className: 'row-meta' });
  if (v.recommended) {
    const chip = _el('span', {
      className: 'corpus-row-flag', textContent: 'Recommended',
      style: 'background:var(--brand);color:var(--bg-0);',
    });
    if (v.rationale) chip.title = v.rationale;
    meta.appendChild(chip);
  }
  if (v.has_outcome) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag outcome', textContent: 'Outcome',
    }));
  }
  row.appendChild(meta);

  row.style.cursor = 'pointer';
  row.onclick = () => _toggleRoleIntroChoice(expId, v.id);
  return row;
}

// Choose this variant for the role, or clear it (a second click on the chosen
// one) — clearing persists as the sentinel 0 so it isn't re-defaulted on reload.
function _toggleRoleIntroChoice(expId, summaryId) {
  const sec = document.querySelector(
    `#composeList .compose-role-intro[data-exp-id="${expId}"]`);
  if (!sec) return;
  const raw = sec.dataset.chosenSummaryId;
  const cur = (raw !== '' && raw != null) ? Number(raw) : null;
  sec.dataset.chosenSummaryId = (cur === summaryId) ? '0' : String(summaryId);
  _markRoleIntroChosen(sec);
  _scheduleCompositionSave();
}

// Fire the per-role recommend (one batched Haiku call) only when opted in and a
// role with 2+ variants still lacks a recommendation. Reloads composition on
// success so the recommendation chips + defaults surface.
function _maybeFireRecommendExperienceSummaries() {
  let needs = false;
  document.querySelectorAll('#composeList .compose-role-intro[data-exp-id]').forEach(sec => {
    const n = sec.querySelectorAll('.role-intro-variant').length;
    if (n > 1 && !sec.dataset.recommendedId) needs = true;
  });
  if (needs) _fireRecommendExperienceSummaries();
}

async function _fireRecommendExperienceSummaries() {
  if (_composeApplicationId == null || !lastContextPath) return;
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/recommend-experience-summaries`,
      { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) loadComposition();
  } catch {
    // Non-blocking — Compose still works without the recommendation.
  }
}

// Compose-side "+ Add intro": add a variant to this role then reload so it
// appears in the picker. Full variant management lives in the Career corpus.
async function _addComposeRoleIntro(expId) {
  const values = await openFormModal({
    title: 'Add role intro',
    subtitle: 'A one-line intro for this role you can use on a tailored résumé.',
    submitLabel: 'Add intro',
    fields: [
      { name: 'text', label: 'Intro text', type: 'textarea', required: true,
        placeholder: 'One or two sentences framing this role for the target job.' },
      { name: 'label', label: 'Label (optional)', type: 'text',
        placeholder: 'e.g. "platform-scale framing"' },
    ],
  });
  if (!values) return;
  const trimmed = (values.text || '').trim();
  if (!trimmed) { _toast('Intro text cannot be empty.', true); return; }
  try {
    const res = await fetch(`/api/experiences/${expId}/summaries`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ text: trimmed, label: (values.label || '').trim() || null }),
    });
    if (res.ok) loadComposition();
    else {
      const data = await res.json().catch(() => ({}));
      _toast(data.error || 'Could not add intro.', true);
    }
  } catch {
    _toast('Network error.', true);
  }
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

  // Titles section — feat/compose-add-title: per-JD selectable title (radio)
  // + a "+ Add title" affordance that writes a sourced, eligible corpus row.
  const titleHeader = _el('div', { className: 'compose-exp-section-title' });
  titleHeader.appendChild(_el('span', { textContent: 'Title for this résumé' }));
  const addTitleBtn = _el('button', {
    className: 'corpus-action-btn compose-add-title-btn',
    textContent: '+ Add title',
  });
  addTitleBtn.type = 'button';
  addTitleBtn.dataset.expId = String(exp.id);
  addTitleBtn.onclick = () => _addComposeTitlePrompt(exp.id);
  titleHeader.appendChild(addTitleBtn);
  card.appendChild(titleHeader);

  // data-user-pinned tracks whether the selection is an EXPLICIT pin (context
  // already had one, or the user clicked a radio) vs. the default selected
  // state — only explicit pins are sent to the server (mirrors bullet_order's
  // data-custom-order), so an untouched default never persists a pin or busts
  // the analyze→generate cache.
  const titleList = _el('div', { className: 'compose-title-list' });
  titleList.dataset.expId = String(exp.id);
  titleList.dataset.userPinned = (exp.titles || []).some(t => t.pinned) ? 'true' : 'false';
  (exp.titles || []).forEach(t =>
    titleList.appendChild(_renderTitleRow_compose(t, exp.id, exp.chosen_title_id)));
  if (!(exp.titles || []).length) {
    titleList.appendChild(_el('div', {
      className: 'compose-empty-experience',
      textContent: 'No titles yet — add one to use for this résumé.',
    }));
  }
  card.appendChild(titleList);

  // B.4 — per-role intro picker. Hidden unless the "Add role intros" toggle is
  // on. Sits between the title and the bullets (résumé order: heading → intro
  // → bullets).
  card.appendChild(_renderComposeRoleIntro(exp));

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

  // feat/bullet-drag-reorder — one-sentence instruction + an "(i)" depth
  // affordance + a per-experience "Reset to AI ranking". Two load-bearing
  // words in the hint: "AI" (the default order is already intentional) and
  // "shapes" (order isn't cosmetic — it propagates into the generate prompt).
  const orderBar = _el('div', { className: 'compose-order-bar' });
  const hintWrap = _el('div', { className: 'compose-order-hint-wrap' });
  hintWrap.appendChild(_el('span', {
    className: 'compose-order-hint',
    textContent: "Bullets are ranked by sartor's AI by fit to this job. "
      + 'Drag to reorder — your order shapes the final résumé.',
  }));
  const info = _el('button', { className: 'compose-order-info', textContent: 'i' });
  info.type = 'button';
  info.setAttribute('aria-label', 'Why ordering matters');
  info.title = 'Why ordering matters: recruiters scan top-down in seconds, so '
    + 'the first bullet under each role does the work of selling it. And the '
    + 'résumé generator reads bullets in this order — earlier bullets carry '
    + 'more weight when it decides what to keep in a length-limited résumé. '
    + 'Your order is a real lever, not just display.';
  info.onclick = () => _toast(info.title);
  hintWrap.appendChild(info);
  orderBar.appendChild(hintWrap);
  const resetBtn = _el('button', {
    className: 'compose-order-reset', textContent: 'Reset to AI ranking',
  });
  resetBtn.type = 'button';
  orderBar.appendChild(resetBtn);
  card.appendChild(orderBar);

  let initial = visible;
  if (!exp.has_recommendations && initial.length === 0) {
    // fix/compose-order-no-recommendations — when the user saved an explicit
    // order, the GET already returned this experience's bullets in that order
    // (in_custom_order rows first, in the saved sequence). Honor it instead of
    // re-deriving a score sort via _dropoffPick, which silently reverted the
    // on-screen order on reload (the persisted order was always intact; only
    // the render regressed).
    initial = exp.has_custom_order
      ? (exp.bullets || []).filter(b => b.in_custom_order === true)
      : fallback;
    initial.forEach(b => b._fallback = true);
  }

  // Visible (résumé-bound) bullets live in their own container so drag/keyboard
  // reorder and order-serialization are scoped to this set — drawer rows are
  // excluded. data-exp-id keys the saved order; data-custom-order drives Reset.
  const bulletList = _el('div', { className: 'compose-bullet-list' });
  bulletList.dataset.expId = String(exp.id);
  bulletList.dataset.customOrder = exp.has_custom_order ? 'true' : 'false';
  _wireBulletListDnD(bulletList);
  initial.forEach(b => bulletList.appendChild(
    _renderBulletRow_compose(
      b, { draggable: true, expHasCustomOrder: !!exp.has_custom_order },
    ),
  ));
  card.appendChild(bulletList);
  resetBtn.disabled = bulletList.dataset.customOrder !== 'true';
  resetBtn.onclick = () => _resetExperienceOrder(bulletList, resetBtn);

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

function _renderTitleRow_compose(t, expId, chosenTitleId) {
  const row = _el('div', { className: 'compose-row' });
  // feat/compose-add-title — radio selects which eligible title this JD's
  // résumé uses. Checked = the effective title (pin → official → top eligible).
  const radio = _el('input', { className: 'compose-title-radio', type: 'radio' });
  radio.name = `compose-title-${expId}`;
  radio.value = String(t.id);
  radio.dataset.expId = String(expId);
  radio.checked = (t.id === chosenTitleId);
  radio.setAttribute('aria-label', `Use "${t.title}" for this résumé`);
  radio.addEventListener('change', () => {
    if (!radio.checked) return;
    const list = radio.closest('.compose-title-list');
    if (list) list.dataset.userPinned = 'true';
    _scheduleCompositionSave();
  });
  row.appendChild(radio);
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

// feat/compose-add-title — add an alternative title from the Compose step.
// Writes a SOURCED, immediately-eligible corpus row via the existing title
// route (truthful_enough_to_use=true → eligible without being Official), then
// reloads composition so it appears as a selectable option for this résumé.
async function _addComposeTitlePrompt(expId) {
  const result = await openFormModal({
    title: 'ADD TITLE',
    subtitle: 'Add an alternative title for this experience. It joins your '
      + 'career corpus and becomes selectable for this résumé.',
    submitLabel: 'ADD TITLE',
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true,
        placeholder: 'e.g. Director, AI Research' },
    ],
    onSubmit: async (v) => {
      await _postJson(`/api/experiences/${expId}/titles`, {
        title: v.title.trim(),
        truthful_enough_to_use: true,
      });
    },
  });
  if (!result) return;
  await loadComposition();
  _toast('Title added to corpus');
}

function _renderBulletRow_compose(b, opts = {}) {
  const row = _el('div', { className: 'compose-row' });
  if (b.recommended) row.classList.add('recommended');
  if (b.pinned)     row.classList.add('pinned');
  if (b.excluded)   row.classList.add('excluded');
  row._bulletState = b;

  // feat/bullet-drag-reorder — drag affordance on visible (résumé-bound) rows
  // only; drawer rows render without it. The grab handle is the discoverable
  // cue (cursor: grab/grabbing via CSS); the whole row is the drag source.
  if (opts.draggable) {
    row.draggable = true;
    row.classList.add('draggable');
    const handle = _el('span', { className: 'drag-handle', textContent: '≡' });
    handle.setAttribute('aria-hidden', 'true');
    handle.title = 'Drag to reorder';
    row.appendChild(handle);
    row.addEventListener('dragstart', (e) => {
      row.classList.add('dragging');
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = 'move';
        try { e.dataTransfer.setData('text/plain', String(b.id)); } catch (_) {}
      }
    });
    row.addEventListener('dragend', () => row.classList.remove('dragging'));
  }

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
  // Pin/exclude/add now also fire the debounced autosave (the autosave sends
  // the FULL composition state, so these persist alongside bullet_order).
  pin.onclick = () => {
    b.pinned = !b.pinned;
    if (b.pinned) b.excluded = false;
    _refreshComposeRow(row);
    _scheduleCompositionSave();
  };
  exc.onclick = () => {
    b.excluded = !b.excluded;
    if (b.excluded) { b.pinned = false; b.added = false; }
    _refreshComposeRow(row);
    _scheduleCompositionSave();
  };
  addBtn.onclick = () => {
    b.added = !b.added;
    if (b.added) b.excluded = false;
    _refreshComposeRow(row);
    _scheduleCompositionSave();
  };
  actions.appendChild(pin);
  actions.appendChild(exc);
  if (!b.recommended) actions.appendChild(addBtn);
  // feat/bullet-drag-reorder — keyboard reorder path (the a11y floor). Both
  // pointer (drag) and keyboard (these buttons) write the same persistence.
  // Deliberately NOT using deprecated aria-grabbed/aria-dropeffect.
  if (opts.draggable) {
    const reorder = _el('div', { className: 'reorder-controls' });
    const up = _el('button', { className: 'reorder-btn', textContent: '↑' });
    up.type = 'button';
    up.setAttribute('aria-label', 'Move bullet up');
    up.onclick = () => _moveBulletRow(row, -1);
    const down = _el('button', { className: 'reorder-btn', textContent: '↓' });
    down.type = 'button';
    down.setAttribute('aria-label', 'Move bullet down');
    down.onclick = () => _moveBulletRow(row, 1);
    reorder.appendChild(up);
    reorder.appendChild(down);
    actions.appendChild(reorder);
  }
  row.appendChild(actions);

  // Metadata line (score, outcome, tags)
  const meta = _el('div', { className: 'row-meta' });
  meta.appendChild(_el('span', {
    className: 'score-chip', textContent: String(Math.round(b.score)),
  }));
  // feat/bullet-drag-reorder — bullet that post-dates an explicit saved order
  // (e.g. drawer-added later): slotted at the end by the server + flagged here.
  if (opts.expHasCustomOrder && b.in_custom_order === false) {
    row.classList.add('newly-added');
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag newly-added-hint',
      textContent: 'newly added — drag to reposition',
    }));
  }
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
    // Walkthrough D3: edit + approve a proposed bullet INLINE in the tailor flow
    // (both persist straight to the corpus via the same routes the Corpus tab
    // uses), so the user never has to leave Compose to keep a proposed change.
    const editBtn = _el('button', {
      className: 'corpus-action-btn', textContent: 'EDIT',
    });
    editBtn.onclick = () => _editComposeBullet(b, row);
    const approveBtn = _el('button', {
      className: 'corpus-action-btn', textContent: 'APPROVE',
    });
    approveBtn.onclick = async () => {
      try {
        await _postJson(`/api/bullets/${b.id}/accept`, {});
        b.is_pending_review = false;
        meta.querySelector('.corpus-row-flag.pending')?.remove();
        editBtn.remove();
        approveBtn.remove();
        await _refreshOnboardingBanner();
        _toast('Bullet approved — saved to your corpus');
      } catch (e) { _toast('Approve failed: ' + e.message, true); }
    };
    meta.appendChild(editBtn);
    meta.appendChild(approveBtn);
  }
  const tagWrap = _el('span', { className: 'tag-chip-wrap' });
  _renderTagChips(tagWrap, 'bullet', b.id, b.tags || []);
  meta.appendChild(tagWrap);
  row.appendChild(meta);
  return row;
}

// Walkthrough D3 — edit a proposed (pending-review) bullet from the Compose step.
// PUT /api/bullets/<id> persists the new text to the corpus (same route the
// Career Corpus tab uses); the row updates in place. Approval is a separate click.
async function _editComposeBullet(b, row) {
  const result = await openFormModal({
    title: 'EDIT BULLET',
    subtitle: 'Edit this proposed bullet. Your change saves to your career corpus.',
    submitLabel: 'SAVE',
    fields: [
      { name: 'text', label: 'Bullet', type: 'textarea', required: true,
        defaultValue: b.text },
    ],
    onSubmit: async (v) => {
      await _putJson(`/api/bullets/${b.id}`, { text: v.text.trim() });
    },
  });
  if (!result) return;
  b.text = result.text.trim();
  const txt = row.querySelector('.row-text');
  if (txt) txt.textContent = b.text;
  _toast('Bullet saved to corpus');
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

// ============================================================
// feat/bullet-drag-reorder — Compose bullet ordering
// ============================================================
// Persistence shape: composition_overrides.bullet_order =
//   { [experience_id]: [bullet_id, ...] }. Authoritative over the server's
// score sort when present; absent ⇒ AI ranking. Order is collected from the
// .compose-bullet-list DOM containers (drawer rows excluded) and written by a
// debounced autosave that sends the FULL composition state, so it never
// clobbers pins/excludes (the POST route rebuilds composition_overrides).

let _composeSaveTimer = null;

// Snapshot the full current composition state from the DOM: pin/exclude/add
// (all rows) + bullet_order (only experiences flagged data-custom-order).
function _collectCompositionState() {
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
  const bullet_order = {};
  document.querySelectorAll('#composeList .compose-bullet-list').forEach(list => {
    if (list.dataset.customOrder !== 'true') return;
    const expId = list.dataset.expId;
    const ids = [];
    list.querySelectorAll(':scope > .compose-row').forEach(row => {
      const b = row._bulletState;
      if (b && b.id != null) ids.push(b.id);
    });
    if (expId != null && ids.length) bullet_order[expId] = ids;
  });
  // feat/compose-add-title — per-experience title pin. Only collected for cards
  // the user explicitly pinned (data-user-pinned), so an untouched default
  // selection never persists a pin (keeps the default path + generate cache
  // byte-identical, mirroring bullet_order's data-custom-order gate).
  const pinned_title_ids = {};
  document.querySelectorAll('#composeList .compose-title-list').forEach(list => {
    if (list.dataset.userPinned !== 'true') return;
    const expId = list.dataset.expId;
    const checked = list.querySelector('input.compose-title-radio:checked');
    if (expId != null && checked && checked.value) {
      pinned_title_ids[expId] = Number(checked.value);
    }
  });
  return {
    pinned, excluded, added, bullet_order, pinned_title_ids,
    // B.4 — per-role intro toggle + picks ride along on every save so a bullet/
    // title save never clobbers them (the POST rebuilds overrides wholesale).
    ..._collectExperienceSummaryState(),
    // B.5 — skill curation (pin/drop/reorder) likewise rides along on every
    // save so it survives a bullet/title/summary save.
    ..._collectSkillState(),
  };
}

// B.4 — snapshot the "Add role intros" toggle + each role's chosen intro from
// the DOM. data-chosenSummaryId holds a positive id (use that variant), '0'
// (explicitly cleared — no intro for this role), or '' (undecided). Only a
// non-empty value is sent, so an undecided role stays out of the overrides.
function _collectExperienceSummaryState() {
  const toggle = document.getElementById('composeRoleIntrosToggle');
  const use_experience_summaries = !!(toggle && toggle.checked);
  const chosen_experience_summary_ids = {};
  document.querySelectorAll('#composeList .compose-role-intro[data-exp-id]').forEach(sec => {
    const expId = sec.dataset.expId;
    const raw = sec.dataset.chosenSummaryId;
    if (expId != null && raw !== '' && raw != null) {
      chosen_experience_summary_ids[expId] = Number(raw);
    }
  });
  return { use_experience_summaries, chosen_experience_summary_ids };
}

async function _postComposition(state) {
  if (_composeApplicationId == null || !lastContextPath) return false;
  const res = await fetch(
    `/api/applications/${_composeApplicationId}/composition`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context_path: lastContextPath, ...state }),
    },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return true;
}

// Debounced (~300ms) optimistic autosave. The DOM is already updated by the
// caller; on failure we toast and leave the optimistic state in place (the
// next autosave or the Next save retries).
function _scheduleCompositionSave() {
  if (_composeApplicationId == null || !lastContextPath) return;
  if (_composeSaveTimer) clearTimeout(_composeSaveTimer);
  _composeSaveTimer = setTimeout(async () => {
    _composeSaveTimer = null;
    try {
      await _postComposition(_collectCompositionState());
    } catch (e) {
      _toast('Autosave failed: ' + e.message, true);
    }
  }, 300);
}

// Mark an experience's list as user-ordered: enable Reset, clear stale
// "newly added" hints (the user has now placed everything explicitly).
function _markCustomOrder(list) {
  if (!list) return;
  list.dataset.customOrder = 'true';
  const card = list.closest('.compose-experience-card');
  const reset = card && card.querySelector('.compose-order-reset');
  if (reset) reset.disabled = false;
  list.querySelectorAll('.newly-added-hint').forEach(h => h.remove());
  list.querySelectorAll('.compose-row.newly-added').forEach(
    r => r.classList.remove('newly-added'),
  );
}

// Keyboard reorder path: move a row up (-1) or down (+1) within its list.
function _moveBulletRow(row, dir) {
  const list = row.parentElement;
  if (!list || !list.classList.contains('compose-bullet-list')) return;
  if (dir < 0 && row.previousElementSibling) {
    list.insertBefore(row, row.previousElementSibling);
  } else if (dir > 0 && row.nextElementSibling) {
    list.insertBefore(row.nextElementSibling, row);
  } else {
    return;  // already at an edge — nothing changed
  }
  _markCustomOrder(list);
  _scheduleCompositionSave();
}

// HTML5 drag: find the row the dragged element should sit before, by pointer Y.
function _dragAfterElement(list, y) {
  const els = [...list.querySelectorAll(':scope > .compose-row:not(.dragging)')];
  let closest = { offset: -Infinity, element: null };
  for (const child of els) {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) closest = { offset, element: child };
  }
  return closest.element;
}

// Wire a bullet-list container as a drop zone. Reorder is within-experience
// only: a drag whose source row isn't in THIS list is ignored, so a row can't
// jump experiences.
function _wireBulletListDnD(list) {
  list.addEventListener('dragover', (e) => {
    const dragging = list.querySelector('.compose-row.dragging');
    if (!dragging) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    const after = _dragAfterElement(list, e.clientY);
    if (after == null) list.appendChild(dragging);
    else if (after !== dragging) list.insertBefore(dragging, after);
  });
  list.addEventListener('drop', (e) => {
    if (!list.querySelector('.compose-row.dragging')) return;
    e.preventDefault();
    _markCustomOrder(list);
    _scheduleCompositionSave();
  });
}

// "Reset to AI ranking" — restore the server's default order (pinned/
// recommended/added first, then score desc, then id), clear the custom-order
// flag, and persist (omitting this experience from bullet_order).
function _resetExperienceOrder(list, resetBtn) {
  const rows = [...list.querySelectorAll(':scope > .compose-row')];
  rows.sort((a, c) => {
    const ba = a._bulletState || {};
    const bc = c._bulletState || {};
    const ra = (ba.pinned || ba.recommended || ba.added) ? 0 : 1;
    const rc = (bc.pinned || bc.recommended || bc.added) ? 0 : 1;
    if (ra !== rc) return ra - rc;
    const sa = ba.score || 0;
    const sc = bc.score || 0;
    if (sc !== sa) return sc - sa;
    return (ba.id || 0) - (bc.id || 0);
  });
  rows.forEach(r => list.appendChild(r));
  list.dataset.customOrder = 'false';
  if (resetBtn) resetBtn.disabled = true;
  _scheduleCompositionSave();
}

async function saveCompositionThenNext() {
  if (_composeApplicationId == null) { wizardGoTo(4); return; }
  if (_composeSaveTimer) { clearTimeout(_composeSaveTimer); _composeSaveTimer = null; }
  const state = _collectCompositionState();
  try {
    await _postComposition(state);
    _toast(`Composition saved (${state.pinned.length} pinned, ${state.added.length} added, ${state.excluded.length} excluded)`);
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

// _promptAddTag was the original two-prompt() chain for adding a tag
// to a bullet or experience title. Superseded by _openInlineTagComposer
// (Workstream G) which uses an inline composer instead of stacked
// browser prompts; the only "+ tag" button caller (line above this
// block, container.appendChild(add)) now calls _openInlineTagComposer
// directly. Removed 2026-05-26 during the v1.0.1 redesign cleanup pass.

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
    // Surface the backend's detail field (logger.exception wrapper in
    // list_user_personas added the traceback tail so we can see the
    // actual exception here in the dev console too).
    const data = await res.json().catch(() => ({}));
    const detail = data.detail || data.error || `status ${res.status}`;
    if (list) _setLoadingPlaceholder(list, `Failed to load templates: ${detail}`);
    return;
  }
  const body = await res.json().catch(() => ({}));
  // Brand-new user: config exists but no Candidate row yet (the read
  // endpoint now signals this via 200 + needs_onboarding). Mirror
  // _loadOwnedPersonas / refreshApplications and surface the onboarding CTA
  // instead of a misleading "Failed to load templates" error. Return early —
  // the <select> hydration + live-preview kickoff below both assume a
  // populated body.
  if (_needsOnboarding(res, body)) {
    if (list) _renderCorpusEmptyCTA(list, 'Add your résumé in the Career '
      + 'corpus tab to choose a template.');
    return;
  }
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

  // v1.0 Step 4 redesign: stash the full list in state so search +
  // source-filter chips can re-render without re-fetching. Built to
  // handle MANY templates (search becomes load-bearing as the count
  // grows; the chooser column is scroll-isolated).
  _templatePickerState.bundled = body.bundled || [];
  _templatePickerState.owned   = body.owned   || [];

  // Default-select the first bundled card if nothing selected. The
  // selection drives the hidden <select> value AND _selectedPersonaId,
  // both of which downstream code reads.
  if (!sel.value && _templatePickerState.bundled.length) {
    sel.value = String(_templatePickerState.bundled[0].id);
    _selectedPersonaId = _templatePickerState.bundled[0].id;
  }

  _renderTemplatePickList();
  _bindTemplateFilterHandlers();

  // Kick off the live preview for whatever template ended up selected
  // when the picker first hydrates.
  if (sel.value) _refreshLivePreview(parseInt(sel.value, 10));
}

// State for the compact picker (v1.0 redesign). Held module-level so
// search input + source filter chips can re-render against the cached
// fetch without re-hitting /api/users/<u>/personas on every keystroke.
const _templatePickerState = {
  bundled: [],
  owned:   [],
  source:  'all',   // 'all' | 'bundled' | 'owned'
  query:   '',      // search box text (lowercased)
  _bound:  false,   // ensure the search / chip handlers wire once
};

function _renderTemplatePickList() {
  const list = document.getElementById('templatePickList');
  const sel  = document.getElementById('personaSelect');
  const countChip = document.getElementById('templateCountChip');
  if (!list || !sel) return;
  _clearChildren(list);

  const q = _templatePickerState.query;
  const src = _templatePickerState.source;

  const matches = (p) => {
    if (!q) return true;
    const hay = (p.name + ' ' + (p.description || '')).toLowerCase();
    return hay.indexOf(q) !== -1;
  };
  const fromBundled = src === 'owned' ? [] :
    _templatePickerState.bundled.filter(matches);
  const fromOwned = src === 'bundled' ? [] :
    _templatePickerState.owned.filter(matches);
  const total = fromBundled.length + fromOwned.length;
  if (countChip) countChip.textContent = `(${total})`;

  if (total === 0) {
    list.appendChild(_el('div', {
      className: 'template-mini-empty',
      textContent: q ? `No templates match "${q}".` : 'No templates available.',
    }));
    return;
  }

  const renderRow = (p, source) => {
    const isSelected = String(p.id) === sel.value;
    const row = _el('div', {
      className: 'template-mini-row' + (isSelected ? ' selected' : ''),
      id: `tpl-row-${p.id}`,
    });
    row.setAttribute('role', 'option');
    row.setAttribute('aria-selected', isSelected ? 'true' : 'false');
    row.tabIndex = 0;

    const nameRow = _el('div', { className: 'template-mini-name' });
    // The name truncates (…) so a long owned filename can't shove the ATS /
    // MINE badges outside the row (walkthrough B1). Badges stay pinned right.
    nameRow.appendChild(_el('span', { className: 'template-mini-label', textContent: p.name }));
    // ATS-safety badge. All 4 v1.0.0-curated bundled templates are
    // ATS-safe by construction (single column, plain bullets, no
    // tables / icons / sidebars). Owned uploads are marked
    // "unverified" — we can't introspect arbitrary user .docx files
    // for ATS-safety, so we don't claim it.
    const atsLabel = source === 'owned' ? 'ATS · unverified' : 'ATS · safe';
    const atsClass = source === 'owned' ? 'unverified' : 'safe';
    nameRow.appendChild(_el('span', {
      className: 'template-mini-ats ' + atsClass,
      textContent: atsLabel,
    }));
    nameRow.appendChild(_el('span', {
      className: 'template-mini-source ' + (source === 'owned' ? 'owned' : 'bundled'),
      textContent: source === 'owned' ? 'MINE' : 'BUNDLED',
    }));
    row.appendChild(nameRow);

    if (p.description) {
      row.appendChild(_el('div', {
        className: 'template-mini-sub',
        textContent: p.description,
      }));
    }

    const onActivate = () => {
      sel.value = String(p.id);
      _selectedPersonaId = p.id;
      list.querySelectorAll('.template-mini-row').forEach(r => {
        const me = r.id === `tpl-row-${p.id}`;
        r.classList.toggle('selected', me);
        r.setAttribute('aria-selected', me ? 'true' : 'false');
      });
      _refreshLivePreview(p.id);
    };
    row.onclick = onActivate;
    row.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onActivate(); }
    };
    return row;
  };

  fromBundled.forEach(p => list.appendChild(renderRow(p, 'bundled')));
  fromOwned.forEach(p   => list.appendChild(renderRow(p, 'owned')));
}

function _bindTemplateFilterHandlers() {
  if (_templatePickerState._bound) return;
  _templatePickerState._bound = true;

  const search = document.getElementById('templateSearch');
  if (search) {
    search.addEventListener('input', () => {
      _templatePickerState.query = (search.value || '').toLowerCase().trim();
      _renderTemplatePickList();
    });
  }
  document.querySelectorAll('.template-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.template-filter').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      _templatePickerState.source = btn.dataset.source || 'all';
      _renderTemplatePickList();
    });
  });
}

// Step 4 inline upload — reuses /api/users/<u>/personas POST. After a
// successful upload we re-fetch + re-render so the new template
// appears in the chooser without a page reload.
async function uploadTemplateFromTemplateStep(input) {
  if (!input || !input.files || !input.files[0]) return;
  const file = input.files[0];
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
  const btn = document.getElementById('templateUploadBtn');
  if (btn) btn.disabled = true;
  try {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/personas`, {
      method: 'POST', body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    _toast('Template uploaded');
    // Refresh the picker (re-fetches /api/users/<u>/personas).
    await _loadTemplatePicker();
  } catch (e) {
    _toast('Upload failed: ' + e.message, true);
  } finally {
    if (btn) btn.disabled = false;
    input.value = '';
  }
}

// β.4 / β.6 — refresh the embedded live preview iframe for the
// current application + the given template id. Corpus-direct now: the
// route reads Candidate + Experience + Bullet + SummaryItem rows
// straight from the DB and applies composition_overrides from the
// active context file (passed via `context_path`), so the preview
// works BEFORE any /api/generate has run. Idempotent: safe to call on
// step entry, on template-card click, after pin/exclude/add changes,
// and after a generate.
//
// If `_composeApplicationId` is null we fall back to the user-scoped
// preview (`/api/users/<u>/preview`) — covers the "library" flow where
// the user wants to see how their corpus renders without an
// application yet.
async function _refreshLivePreview(templateId) {
  const frame = document.getElementById('livePreviewFrame');
  const empty = document.getElementById('livePreviewEmpty');
  if (!frame) return;

  // v1.0 Step 4 redesign: update toolbar with active template name and
  // reset the page-count display while we load the new iframe.
  const nameSpan = document.getElementById('previewActiveName');
  const pageInfo = document.getElementById('previewPageInfo');
  if (nameSpan) {
    const found = [..._templatePickerState.bundled, ..._templatePickerState.owned]
      .find(p => String(p.id) === String(templateId));
    nameSpan.textContent = found ? found.name : '—';
  }
  if (pageInfo) pageInfo.textContent = 'Page — of —';

  const params = new URLSearchParams();
  if (templateId != null) params.set('template_id', String(templateId));
  // Thread the active context file when present so composition
  // overrides (pin/exclude/add, pinned_summary_id) and LLM
  // recommendations shape the preview output.
  if (typeof lastContextPath === 'string' && lastContextPath) {
    params.set('context_path', lastContextPath);
  }
  const base = (_composeApplicationId != null)
    ? `/api/applications/${_composeApplicationId}/preview`
    : (currentUser ? `/api/users/${encodeURIComponent(currentUser)}/preview` : null);
  if (!base) {
    if (empty) { empty.classList.remove('hidden');
      empty.textContent = 'Select a user (or start an application) to preview.'; }
    frame.classList.add('hidden');
    return;
  }
  const qs = params.toString();
  const url = qs ? `${base}?${qs}` : base;

  // Probe for the only remaining failure mode (no candidate row yet
  // → 409 needs_onboarding) so we surface a clean hint instead of
  // dropping an error blob into the iframe.
  let probe;
  try {
    probe = await fetch(url, { method: 'GET' });
  } catch {
    if (empty) { empty.classList.remove('hidden');
      empty.textContent = 'Could not reach the preview server.'; }
    frame.classList.add('hidden');
    return;
  }
  if (probe.status === 409) {
    if (empty) { empty.classList.remove('hidden');
      empty.textContent = 'Import a résumé first to unlock the live preview.'; }
    frame.classList.add('hidden');
    return;
  }
  if (!probe.ok) {
    if (empty) { empty.classList.remove('hidden');
      empty.textContent = `Preview unavailable (${probe.status}).`; }
    frame.classList.add('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');
  frame.classList.remove('hidden');

  _wirePreviewPageCount(frame, 'previewPageInfo');
  _loadPreviewFrame(frame, url);
}

// Wire a preview iframe's paged.js page-count → a "Page N of M" chip.
// Reused by the Step 4 template preview, the Step 6 résumé output preview,
// and the Step 6 cover-letter preview. The listener persists across src
// swaps; it's installed ONCE per frame (sentinel flag). Messages are routed
// by `ev.source === frame.contentWindow` so multiple preview frames don't
// cross-talk (each iframe posts to window.parent without identifying itself).
// A load-time fallback measures via the iframe's own DOM in case paged.js
// fails to post (e.g., a corrupt vendor file).
function _wirePreviewPageCount(frame, pageInfoId) {
  if (!frame || frame._pageCountHookInstalled) return;
  window.addEventListener('message', (ev) => {
    if (!ev || ev.source !== frame.contentWindow) return;
    if (!ev.data || ev.data.type !== 'pagedjs_rendered') return;
    const pageInfo = document.getElementById(pageInfoId);
    if (!pageInfo) return;
    const n = parseInt(ev.data.pages, 10);
    if (!Number.isFinite(n) || n < 1) return;
    pageInfo.textContent = n === 1 ? 'Page 1 of 1' : `Page 1 of ${n}`;
  });
  frame.addEventListener('load', () => _updatePreviewPageCount(frame, pageInfoId));
  frame._pageCountHookInstalled = true;
}

// Fallback page-count estimator when paged.js doesn't (yet) post a
// count — runs once on iframe load, before paged.js has finished its
// layout pass. Estimates from the iframe's own scrollHeight against
// an 11"×96-DPI Letter page. Paged.js's postMessage will overwrite
// this with the real count usually within 500–1500 ms.
function _updatePreviewPageCount(frame, pageInfoId = 'previewPageInfo') {
  const pageInfo = document.getElementById(pageInfoId);
  if (!pageInfo) return;
  let pages = 1;
  try {
    const doc = frame.contentDocument;
    if (doc && doc.body) {
      const PAGE_PX = 11 * 96;  // Letter height at 96 DPI
      const h = doc.documentElement.scrollHeight || doc.body.scrollHeight;
      pages = Math.max(1, Math.ceil(h / PAGE_PX));
    }
  } catch (e) {
    // contentDocument may be inaccessible briefly during navigation —
    // silently fall through to the safe default of 1.
  }
  pageInfo.textContent = pages === 1 ? `Page 1 of 1` : `~ ${pages} pages`;
}

function _readSelectedPersonaId() {
  const sel = document.getElementById('personaSelect');
  if (!sel || !sel.value) return null;
  const n = parseInt(sel.value, 10);
  return Number.isNaN(n) ? null : n;
}

// β.6 post-review — preview a template against the user's corpus by
// opening the live HTML preview in a new tab. Replaces the legacy
// "stream a .docx preview file" flow per the hands-on review (#1):
// the user asked for a viewable rendering, not a download. The
// corpus-direct route (`/api/users/<u>/preview`) renders without
// requiring any prior /api/generate run.
function _previewPersonaWithResume(personaId, _name) {
  if (!currentUser) { _toast('Select a user first', true); return; }
  const url = `/api/users/${encodeURIComponent(currentUser)}/preview?template_id=${personaId}`;
  window.open(url, '_blank', 'noopener');
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
      const label = _el('label', { htmlFor: id, textContent: f.label });
      if (f.required) {
        // Reusable required-field marker (static/style.css .required-marker):
        // decorative asterisk on the label; aria-required (below) is the real
        // signal assistive tech announces.
        label.appendChild(_el('span', { className: 'required-marker', textContent: '*' }, [], { 'aria-hidden': 'true' }));
      }
      body.appendChild(label);
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
      if (f.required) { input.required = true; input.setAttribute('aria-required', 'true'); }
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
