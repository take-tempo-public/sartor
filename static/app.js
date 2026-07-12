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
  loadCandidateRoster();
  setupDropZone();
  document.getElementById('userSelect').addEventListener('change', onUserSelect);
  // Format-check the URL boxes (new-user form + Settings drawer).
  ['newLinkedin', 'newWebsite', 'cfgLinkedin', 'cfgWebsite'].forEach(
    id => _wireUrlField(document.getElementById(id)),
  );
  // F-05: display-name-first new-user form — typing a name auto-derives a
  // username slug until the user edits the username field directly.
  const _newNameEl = document.getElementById('newName');
  if (_newNameEl) _newNameEl.addEventListener('input', _onNewNameInput);
  const _newUsernameEl = document.getElementById('newUsername');
  if (_newUsernameEl) _newUsernameEl.addEventListener('input', _onNewUsernameInput);
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

  // D4 (generation-experience re-architecture, item (b)) — live-render the
  // styled Step-6 preview from whatever's currently typed into the editors,
  // so the visible preview never lags behind what Download would produce.
  // See _wireLiveEditPreview for the mechanics.
  _wireLiveEditPreview('resumePreview', 'resume', 'outputPreviewFrame');
  _wireLiveEditPreview('coverLetterPreview', 'cover_letter', 'coverPreviewFrame');
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

// ---- Candidate roster (Wave 2 recruiter tier, UX review F-08) ----
// A searchable front door layered ON TOP of #userSelect — it never replaces
// the select's mechanics. Selecting a roster card just sets #userSelect's
// value and fires the SAME onUserSelect() every other selection path uses,
// so currentUser semantics are unchanged. Backed by the aggregate
// /api/candidates/roster endpoint (also powers the Pipeline tab below), which
// stays two DB queries regardless of candidate/application count
// (blueprints/users.py:candidate_roster).
let _candidateRoster = [];

async function loadCandidateRoster() {
  const wrap = document.getElementById('candidateRoster');
  const list = document.getElementById('candidateRosterList');
  if (!wrap || !list) return;
  let res;
  try {
    res = await fetch('/api/candidates/roster');
  } catch {
    return; // silent — the plain <select> underneath still works
  }
  if (!res.ok) return;
  const body = await res.json().catch(() => null);
  if (!body || !Array.isArray(body.candidates)) return;
  _candidateRoster = body.candidates;
  // Small rosters (the common job-seeker / small-team case) don't need a
  // searchable surface above the plain <select> — scanning a handful of
  // names in a dropdown is faster than reaching for search. Only show the
  // roster once there are enough candidates that search actually helps.
  wrap.classList.toggle('hidden', _candidateRoster.length < 6);
  _renderCandidateRosterList(_candidateRoster);
}

function _filterCandidateRoster() {
  const q = (document.getElementById('candidateRosterSearch')?.value || '').trim().toLowerCase();
  const filtered = !q ? _candidateRoster : _candidateRoster.filter(c =>
    c.name.toLowerCase().includes(q) || c.username.toLowerCase().includes(q));
  _renderCandidateRosterList(filtered, q);
}

function _renderCandidateRosterList(rows, query) {
  const list = document.getElementById('candidateRosterList');
  if (!list) return;
  _clearChildren(list);
  if (rows.length === 0) {
    _setLoadingPlaceholder(list, query ? 'No candidates match.' : 'No candidates yet.');
    return;
  }
  rows.forEach(c => list.appendChild(_renderCandidateRosterCard(c)));
}

function _renderCandidateRosterCard(c) {
  const card = _el('div', {
    className: 'candidate-roster-card' + (c.username === currentUser ? ' active' : ''),
    id: `roster-card-${c.username}`,
    tabIndex: 0,
  }, [], { role: 'listitem' });
  card.appendChild(_el('div', { className: 'candidate-roster-card-name', textContent: c.name }));
  const latest = c.latest_application;
  card.appendChild(_el('div', {
    className: 'candidate-roster-card-target',
    textContent: latest
      ? `${latest.title}${latest.company ? ' · ' + latest.company : ''}`
      : (c.has_corpus ? 'No applications yet' : 'Not onboarded yet'),
  }));
  const chips = _el('div', { className: 'candidate-roster-card-chips' });
  Object.entries(c.status_counts || {}).forEach(([status, count]) => {
    if (count === 0) return;
    chips.appendChild(_el('span', {
      className: `app-status-chip status-${status}`,
      textContent: `${count} ${status === 'submitted' ? 'no response' : status}`,
    }));
  });
  if (chips.childNodes.length === 0) {
    chips.appendChild(_el('span', { className: 'app-status-chip status-draft', textContent: 'No applications' }));
  }
  card.appendChild(chips);

  const activate = () => {
    const sel = document.getElementById('userSelect');
    if (!sel) return;
    sel.value = c.username;
    onUserSelect();
  };
  card.addEventListener('click', activate);
  card.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
  });
  return card;
}

// ---- Pipeline board (Wave 2 recruiter tier, UX review F-17) ----
// Read-only v1: every candidate's applications, grouped by canonical
// lifecycle status. Same aggregate endpoint as the roster above — one fetch,
// grouped client-side into the five status columns.
const _PIPELINE_STATUSES = ['draft', 'submitted', 'interview', 'rejected', 'withdrawn'];
const _PIPELINE_STATUS_LABELS = {
  draft: 'Draft',
  submitted: 'No response yet',
  interview: 'Got interview',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
};

async function refreshPipeline() {
  const board = document.getElementById('pipelineBoard');
  const countEl = document.getElementById('pipelineCount');
  if (!board) return;
  _setLoadingPlaceholder(board, 'Loading…');
  let res;
  try {
    res = await fetch('/api/candidates/roster');
  } catch {
    _setLoadingPlaceholder(board, 'Network error.');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(board, 'Failed to load the pipeline.');
    return;
  }
  const body = await res.json().catch(() => ({}));
  const apps = Array.isArray(body.applications) ? body.applications : [];
  if (countEl) countEl.textContent = `${apps.length} application${apps.length === 1 ? '' : 's'}`;
  if (apps.length === 0) {
    _setLoadingPlaceholder(board, 'No applications across any candidate yet.');
    return;
  }
  _renderPipelineBoard(apps);
}

function _renderPipelineBoard(apps) {
  const board = document.getElementById('pipelineBoard');
  _clearChildren(board);
  const byStatus = {};
  _PIPELINE_STATUSES.forEach(s => { byStatus[s] = []; });
  apps.forEach(a => { (byStatus[a.status] || (byStatus[a.status] = [])).push(a); });

  _PIPELINE_STATUSES.forEach(status => {
    const rows = byStatus[status] || [];
    const col = _el('div', { className: 'pipeline-column' });
    const header = _el('div', { className: 'pipeline-column-header' });
    header.appendChild(_el('span', {
      className: `app-status-chip status-${status}`,
      textContent: _PIPELINE_STATUS_LABELS[status] || status,
    }));
    header.appendChild(_el('span', { className: 'pipeline-column-count', textContent: String(rows.length) }));
    col.appendChild(header);
    if (rows.length === 0) {
      col.appendChild(_el('div', { className: 'pipeline-empty', textContent: '—' }));
    }
    rows.forEach(a => col.appendChild(_renderPipelineRow(a)));
    board.appendChild(col);
  });
}

function _renderPipelineRow(a) {
  const row = _el('div', { className: 'pipeline-row', tabIndex: 0 }, [], { role: 'listitem' });
  row.appendChild(_el('div', { className: 'pipeline-row-candidate', textContent: a.candidate_name }));
  row.appendChild(_el('div', { className: 'pipeline-row-title', textContent: a.title }));
  if (a.company) {
    row.appendChild(_el('div', { className: 'pipeline-row-company', textContent: a.company }));
  }
  row.appendChild(_el('div', { className: 'pipeline-row-date', textContent: _formatRelativeDate(a.updated_at) }));

  const activate = () => {
    const sel = document.getElementById('userSelect');
    if (!sel) return;
    sel.value = a.candidate_username;
    onUserSelect().then(() => {
      const tailorBtn = document.getElementById('topTabTailor');
      if (tailorBtn) switchTopTab('tailor', tailorBtn);
      // "linking into that candidate+application" (F-17): open the specific
      // application's detail modal, not just the candidate's list.
      // _showApplicationDetail fetches independently, so it doesn't need to
      // wait on the (fire-and-forget) applications-list refresh inside
      // onUserSelect().
      _showApplicationDetail(a.id);
    });
  };
  row.addEventListener('click', activate);
  row.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
  });
  return row;
}

// Reveal the new-user form (don't toggle): hide the "New user" button so the
// only affordance left is the form itself, and focus the name box (F-05:
// display name is the first field now) so the user can start typing
// immediately. Cancel (hideNewUserForm) restores it.
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
  _usernameEditedByUser = false;  // F-05: a fresh form re-arms slug auto-derive
  const n = document.getElementById('newName');
  if (n) n.focus();
  // KW3: the very first user on a fresh install → arm the new-user tour and
  // offer the "import a résumé to start" tip once (no-op for returning users —
  // _maybeFireTourStop gates on the armed flag).
  if (sel && sel.options.length <= 1) _armHelpTour();
  _maybeFireTourStop('tourAddUser', null);
}

// F-05: display-name-first new-user form. Deriving a URL/storage-safe slug
// from a free-typed name client-side, mirrored server-side by
// `_safe_username` (web_infra.py) at account-creation time — this is a
// same-tab convenience only, not the source of truth for validity.
// `_usernameEditedByUser` stops clobbering a deliberate manual edit: once the
// user types directly into the username field, auto-derive backs off for the
// rest of this form session (reset on show/hide).
let _usernameEditedByUser = false;

function _slugify(text) {
  return (text || '')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')  // strip diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
}

function _onNewNameInput() {
  if (_usernameEditedByUser) return;
  const nameEl = document.getElementById('newName');
  const userEl = document.getElementById('newUsername');
  if (!nameEl || !userEl) return;
  userEl.value = _slugify(nameEl.value);
}

function _onNewUsernameInput() {
  _usernameEditedByUser = true;
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
  _usernameEditedByUser = false;  // F-05: re-arm slug auto-derive for next time
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
  loadCandidateRoster();  // the new candidate should appear in the roster too
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
    const userSummary = document.getElementById('panelUserSummary');
    if (userSummary) userSummary.textContent = '';
    hideAllPanels();
    _resetIterationState();
    return;
  }
  // A user is selected → the box now holds data, so allow it to be tucked away.
  // F-23: default it to a compact switcher (collapsed) so it doesn't crowd the
  // wizard; a returning visitor's own toggle choice (persisted) wins instead.
  if (userPanel) userPanel.classList.remove('not-collapsible');
  _applyFoldableDefault('panelUser', true);
  const userSummary = document.getElementById('panelUserSummary');
  if (userSummary) userSummary.textContent = username;
  currentUser = username;
  await loadConfig();
  show('panelApplications');           // prep the Tailor tab's landing panel
  // F-23: default the applications list to a collapsed short summary too — it
  // used to be a full untruncated list sitting above the wizard rail. Persisted
  // the same way as panelUser.
  _applyFoldableDefault('panelApplications', true);
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
  // F-06: explain the jump the moment it happens — a brand-new (or still-empty)
  // user gets routed away from where they clicked, onto Career corpus, with no
  // transition line. Once-ever (cb_help_seen), tour-armed users only, and
  // _maybeFireTourStop already no-ops when another modal is up.
  if (landing === 'corpus') _maybeFireTourStop('tourCorpusLanding', null);
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

// Start a fresh JD tailoring run for the CURRENT user — no browser refresh.
// Clears the in-flight application state (JD text, analysis, clarify,
// composition selections, generated docs, preview) and snaps the wizard back
// to Step 1. The selected user + their corpus are untouched; the next ANALYZE
// opens a brand-new server-side application, so nothing from the prior run
// leaks forward. Fixes the "no way to start over without a browser refresh" gap.
function startNewTailoring() {
  if (!currentUser) { _toast('Select a user first.', true); return; }
  // 1. Clear the Step-1 inputs + analysis view.
  const jd = document.getElementById('jdText');
  if (jd) jd.value = '';
  const ac = document.getElementById('analysisContent');
  if (ac) ac.replaceChildren();
  document.getElementById('analysisPending')?.classList.add('hidden');
  document.getElementById('analysisActions')?.classList.add('hidden');
  const btnA = document.getElementById('btnAnalyze');
  if (btnA) btnA.disabled = false;
  // 2. Reset clarify + iteration/refinement/generated state (existing helpers).
  _resetClarifyUI();
  _resetIterationState();
  // 3. Drop the server handles so forward-gating re-locks Steps 2–6 until the
  //    new JD is analyzed / generated.
  lastContextPath = '';
  lastResumePath = '';
  lastCoverLetterPath = '';
  lastTemplatePath = '';
  _compositionFrozen = false;  // F-09: new run — no approved composition yet
  // 4. Clear the Step-6 preview editor so no stale document lingers (it is a
  //    contenteditable surface read via innerText — see _readEditorText).
  const preview = document.getElementById('resumePreview');
  if (preview) preview.innerText = '';
  // 5. Back to Step 1 (wizardInit resets _wizardStep, re-renders, re-locks).
  wizardInit();
  setStatus('READY');
  _toast('Started a new tailoring run.');
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
  // F-03/F-04 (UX-W1) — needs_onboarding (added to GET config) tells us
  // whether a Candidate DB row exists yet: false once the corpus is
  // authoritative, at which point the flat Skills/Certs/Education fields
  // above are dead controls and the pointer rows take over.
  _applyCorpusModeToSettingsFields(currentConfig.needs_onboarding !== false);
}

// F-03/F-04 (UX-W1, 2026-07-07) — toggle each of the three flat
// Skills/Certifications/Education Settings rows between its live input
// (pre-provision — still the only source of truth) and a labeled pointer
// into the Career-corpus editor (post-provision — corpus is authoritative,
// so the flat field would silently do nothing if left live and editable).
function _applyCorpusModeToSettingsFields(fieldsAreLive) {
  const pairs = [
    ['cfgSkillsFieldRow', 'cfgSkillsCorpusRow'],
    ['cfgCertsFieldRow', 'cfgCertsCorpusRow'],
    ['cfgEducationFieldRow', 'cfgEducationCorpusRow'],
  ];
  pairs.forEach(([fieldRowId, corpusRowId]) => {
    const fieldRow = document.getElementById(fieldRowId);
    const corpusRow = document.getElementById(corpusRowId);
    if (fieldRow) fieldRow.classList.toggle('hidden', !fieldsAreLive);
    if (corpusRow) corpusRow.classList.toggle('hidden', fieldsAreLive);
  });
}

// The pointer rows' "Go to Career corpus →" button: close the Settings
// drawer (via its own dismiss handler, so focus-trap teardown stays
// correct) and switch to the Corpus tab, where the live Skills/Education/
// Certifications editors are.
function _goToCareerCorpusFromSettings() {
  const dismiss = document.querySelector('#settingsDrawer [data-settings-dismiss]');
  if (dismiss) dismiss.click();
  switchTopTab('corpus', document.getElementById('topTabCorpus'));
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
  // dec 4(a) (UX Cohesion Epic) — this is the "scrape/fetch" blocking action
  // the round-2 audit flagged as not clearly signaling "working" the way
  // analyze/generate do: it previously had ONLY the small local
  // #profileFetchStatus text, no app-wide _setBusy banner and no button
  // pending state. It can take a few seconds per URL (network fetch +
  // parse), so it gets the same two-tier treatment as every other
  // long-running action now.
  const btn = document.getElementById('btnFetchProfile');
  _setBtnPending(btn, 'Fetching…');
  _setBusy(true, 'Fetching your profile content');
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
  } finally {
    _setBusy(false);
    _clearBtnPending(btn, 'Fetch profile content');
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
    const skillsFound = data.skills_created || 0;
    // Dropped-role telemetry (fix/output-identity-and-dates): roles the
    // extractor found but couldn't place (missing company or start date) —
    // surfaced instead of silently vanishing from the corpus.
    const dropped = data.experiences_dropped || 0;
    const droppedList = data.dropped_experiences || [];
    const droppedNote = dropped
      ? ` ${dropped} role(s) could not be parsed (missing company or start ` +
        `date) — review and add manually: ` +
        droppedList
          .map(d => d.candidate_inferred_title || d.company || '(untitled)')
          .join(', ') +
        '.'
      : '';

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
              'month/year dates on each role.') +
          droppedNote;
      }
      _toast('No experiences found in résumé', true);
      return;
    }

    setStatus('READY');
    if (out) {
      out.textContent =
        `Added ${made} experience(s), ${merged} merged into existing roles, ` +
        `${altTitles} alternate title(s), ${bullets} bullet(s), ` +
        `${skillsFound} skill(s) — now pending review below.` +
        droppedNote;
    }
    if (dropped) {
      _toast(`Resume ingested — ${dropped} role(s) need manual review`, true);
    } else {
      _toast('Resume ingested into corpus');
    }
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
    _compositionFrozen = false;  // F-09: fresh analysis — nothing frozen yet
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

// F-12: derive the "top 3 actions" deterministically from data already in the
// analyze payload — top missing keywords + top comparison gaps, backfilled from
// the LLM's own suggestions list. No new LLM call; pure client-side selection.
function _topAnalysisActions(a, d) {
  const actions = [];
  const overlap = (d && d.keyword_overlap) || {};
  const missing = overlap.missing_from_resume || [];
  if (missing.length) {
    actions.push(
      'Weave in the top missing keywords where they’re true of your experience: '
      + missing.slice(0, 3).join(', '),
    );
  }
  const gaps = (a.comparison && a.comparison.gaps) || [];
  gaps.slice(0, 2).forEach(g => actions.push(String(g)));
  if (actions.length < 3 && Array.isArray(a.suggestions)) {
    a.suggestions.slice(0, 3 - actions.length).forEach(s => {
      if (s && s.action) actions.push(s.section ? `${s.section}: ${s.action}` : String(s.action));
    });
  }
  return actions.slice(0, 3);
}

// F-12: one-line deterministic verdict — same thresholds as the score-bar
// color (60/35), coverage framing per F-01 (encouragement, not a grade).
function _analysisVerdictLine(pct) {
  if (pct > 60) return 'Strong keyword coverage — your corpus already speaks this job’s language.';
  if (pct > 35) return 'Solid starting point — the actions below are the fastest wins before you compose.';
  return 'Coverage starts low — that’s normal for a first pass. Focus on the actions below.';
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

  // Keyword overlap score (F-01: server-side cleaned universe — company name +
  // JD boilerplate excluded; coverage framing, not a grade)
  const overlap = (d && d.keyword_overlap) || {};
  const score = overlap.match_score || 0;
  const pct = Math.round(score * 100);
  const color = pct > 60 ? 'var(--success)' : pct > 35 ? 'var(--brand)' : 'var(--danger)';
  html += `<div class="analysis-section">
    <h3>JD Keyword Coverage: ${pct}%</h3>
    <div class="score-bar"><div class="score-fill" style="width:${pct}%;background:${color}"></div></div>
    <p class="score-note">Share of the job description's meaningful keywords found in your corpus — the company's name and hiring boilerplate don't count. It matters because it's the same literal-match signal an ATS keyword scan uses to decide whether a human ever sees your résumé. It's coverage, not a grade: 30–50% is typical for a strong match, since multi-word phrases rarely match word-for-word even when your experience genuinely fits. The analysis below is the real fit read.</p>
  </div>`;

  // F-12: short verdict + the top 3 actions lead; the full read is one
  // disclosure away (below) instead of an all-at-once wall.
  const actions = _topAnalysisActions(a, d);
  html += `<div class="analysis-section" id="analysisVerdict">
    <h3>Where to Focus</h3>
    <p class="analysis-verdict-line">${esc(_analysisVerdictLine(pct))}</p>`;
  if (actions.length) {
    html += `<ol class="analysis-top-actions">`;
    actions.forEach(t => { html += `<li>${esc(t)}</li>`; });
    html += `</ol>`;
  } else {
    html += `<p class="analysis-verdict-line">No urgent gaps found — open the full analysis for the complete read, then continue.</p>`;
  }
  html += `</div>`;

  // ATS Warnings — actionable, so they stay above the fold (corpus mode
  // suppresses them server-side; this renders only on the legacy path).
  if (d && d.ats_warnings && d.ats_warnings.length) {
    html += `<div class="analysis-section"><h3>ATS Warnings</h3>`;
    d.ats_warnings.forEach(w => { html += `<div class="warning">${esc(w)}</div>`; });
    html += `</div>`;
  }

  // F-12: everything below is the deep read — collapsed by default behind a
  // native <details> disclosure (keyboard/screen-reader accessible for free).
  html += `<details class="analysis-details" id="analysisDetails"><summary>Show full analysis</summary>`;

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
  (overlap.matched || []).slice(0, 20).forEach(k => { html += `<span class="tag tag-matched">${esc(k)}</span>`; });
  html += `</div></div>`;

  html += `<div class="analysis-section"><h3>Keywords You Could Add</h3><div>`;
  (overlap.missing_from_resume || []).slice(0, 20).forEach(k => { html += `<span class="tag tag-missing">${esc(k)}</span>`; });
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

  html += `</details>`;

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
  _setBusy(true, 'Generating clarifying questions…');
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
  } finally {
    _setBusy(false);
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
    badge.textContent = isScope ? 'Scope' : 'Experience';
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
  // UX fix (feat/ux-busy-states-and-hydration) — this saves answers, then
  // hands off to _fireRecommendThenCompose's real recommend LLM call; before
  // this the only feedback was the status pill, so the app read as frozen.
  // The label switches to "Preparing compose…" once _fireRecommendThenCompose
  // takes over (same overlay element, idempotent re-set — no flicker).
  _setBusy(true, 'Integrating your answers…');

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
      _setBusy(false);
      return reportError('Save answers', data.error || 'Saving answers failed', data.detail);
    }
  } catch (e) {
    if (btnSubmit) btnSubmit.disabled = false;
    _setBusy(false);
    return reportError('Save answers', 'Saving answers request failed', e.message);
  }
  // KW7 / B.8: the route mirrored these answers into candidate memory —
  // sync the panel so the Q&A shows up without a manual refresh.
  refreshMemory();
  await _fireRecommendThenCompose();
  if (btnSubmit) btnSubmit.disabled = false;
  // Belt-and-suspenders: _fireRecommendThenCompose already clears the busy
  // overlay when it fires the recommend call, but it's a no-op (no
  // _composeApplicationId) when there's nothing to recommend against — this
  // guarantees the overlay never sticks in that case.
  _setBusy(false);
}

async function skipClarifications() {
  // UX fix (feat/ux-busy-states-and-hydration) — skip funnels straight into
  // the same recommend call submit does; show the same busy overlay so
  // clicking Skip doesn't read as a no-op while the network call runs.
  _setBusy(true, 'Preparing compose…');
  try {
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
  } finally {
    _setBusy(false);
  }
}

// Workstream B1: fire the recommend call so Compose can default to the
// curated set, then advance the wizard to step 3 (Compose). On recommend
// failure the Compose step falls back to top-5 by score with a toast.
async function _fireRecommendThenCompose() {
  if (_composeApplicationId != null) {
    // UX fix (feat/ux-busy-states-and-hydration) — the recommend call is the
    // real LLM spend in this flow; both submitClarifications and
    // skipClarifications funnel through here, so one wrap covers both.
    _setBusy(true, 'Preparing compose…');
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
    } finally {
      _setBusy(false);
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
  _setBtnPending(gen, 'Generating…');
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
    _clearBtnPending(gen, '+ Generate cover letter');
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

// Refinement scope warning — the in-app modal that replaces the browser-native
// confirm() when /api/validate-refinement flags a note as possibly fact-changing.
// Mirrors _showEditModal's a11y posture (Esc closes, focus trap, focus restored
// to the trigger, backdrop dismiss). Resolves 'proceed' or 'cancel'. It FLAGS,
// never BLOCKS — the user may be correcting a fabricated fact.
function _showRefinementScopeModal(reason, triggerEl) {
  return new Promise((resolve) => {
    const modal = document.getElementById('refinementScopeModal');
    if (!modal) { resolve('cancel'); return; }
    const body = document.getElementById('refinementScopeBody');
    if (body) body.textContent = reason || 'This may change facts rather than just wording.';
    const buttons = Array.from(modal.querySelectorAll('[data-modal-dismiss]'));
    const focusable = modal.querySelectorAll('button[data-modal-dismiss]');

    const cleanup = (action) => {
      modal.classList.add('hidden');
      modal.removeEventListener('keydown', onKey);
      buttons.forEach(b => b.removeEventListener('click', onClick));
      const backdrop = modal.querySelector('.cb-modal-backdrop');
      if (backdrop) backdrop.removeEventListener('click', onClick);
      if (triggerEl && typeof triggerEl.focus === 'function') triggerEl.focus();
      resolve(action || 'cancel');
    };
    const onClick = (e) => {
      cleanup(e.currentTarget?.getAttribute?.('data-modal-dismiss') || 'cancel');
    };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); cleanup('cancel'); return; }
      if (e.key !== 'Tab' || focusable.length === 0) return;
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
    // Default focus on Cancel (the safer default — proceeding may change facts).
    const cancelBtn = document.getElementById('btnRefineCancelScope');
    if (cancelBtn) cancelBtn.focus();
  });
}

// F-07 — generic in-app confirm modal, replacing every browser-native
// confirm() call site (10 sites — retire/delete/merge/accept-all across the
// corpus, applications, and personas surfaces). Mirrors _showEditModal /
// _showRefinementScopeModal's a11y posture (Esc closes, focus trap, backdrop
// dismiss, focus restored to the trigger). Resolves `true` (confirmed) or
// `false` (canceled/dismissed) — call sites read `if (await cbConfirm(...))`.
//   message      — body text; '\n\n' splits into paragraphs (native confirm()
//                  strings used '\n\n' the same way).
//   title        — modal heading (default 'Are you sure?').
//   confirmLabel — confirm button text (default 'Confirm').
//   cancelLabel  — cancel button text (default 'Cancel').
//   danger       — true (default) styles the confirm button destructively
//                  (.cb-bg-danger); false is for high-stakes-but-not-actually-
//                  destructive actions (e.g. accept-all), styled .cb-bg-amber.
//   triggerEl    — element to restore focus to on close.
function cbConfirm(message, {
  title = 'Are you sure?',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = true,
  triggerEl = null,
} = {}) {
  return new Promise((resolve) => {
    const modal = document.getElementById('cbConfirmModal');
    if (!modal) { resolve(false); return; }
    const titleEl = document.getElementById('cbConfirmTitle');
    const bodyEl = document.getElementById('cbConfirmBody');
    const okBtn = document.getElementById('cbConfirmOk');
    const cancelBtn = document.getElementById('cbConfirmCancel');
    if (titleEl) titleEl.textContent = title;
    if (bodyEl) {
      _clearChildren(bodyEl);
      String(message || '').split('\n\n').filter(Boolean).forEach((para) => {
        bodyEl.appendChild(_el('p', { textContent: para, style: 'margin:0 0 10px' }));
      });
    }
    if (okBtn) {
      okBtn.textContent = confirmLabel;
      okBtn.classList.toggle('cb-bg-danger', danger);
      okBtn.classList.toggle('cb-bg-amber', !danger);
    }
    if (cancelBtn) cancelBtn.textContent = cancelLabel;

    const buttons = Array.from(modal.querySelectorAll('[data-modal-dismiss]'));
    const focusable = modal.querySelectorAll('button[data-modal-dismiss]');

    const cleanup = (confirmed) => {
      modal.classList.add('hidden');
      modal.removeEventListener('keydown', onKey);
      buttons.forEach(b => b.removeEventListener('click', onClick));
      const backdrop = modal.querySelector('.cb-modal-backdrop');
      if (backdrop) backdrop.removeEventListener('click', onClick);
      if (triggerEl && typeof triggerEl.focus === 'function') triggerEl.focus();
      resolve(!!confirmed);
    };
    const onClick = (e) => {
      cleanup(e.currentTarget?.getAttribute?.('data-modal-dismiss') === 'confirm');
    };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); cleanup(false); return; }
      if (e.key !== 'Tab' || focusable.length === 0) return;
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
    // Default focus on Cancel — mirrors the native confirm()'s default-safe
    // posture (Enter alone never confirms a destructive action).
    if (cancelBtn) cancelBtn.focus();
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
      + 'your experience lines up. The JD Keyword Coverage percentage at the '
      + 'top measures how much of the job posting’s meaningful vocabulary '
      + 'shows up in your corpus, after cleaning out the company’s name and '
      + 'hiring boilerplate — the same literal-match signal an ATS keyword '
      + 'scan uses to decide whether a human ever sees your résumé. It’s '
      + 'coverage, not a grade: 30–50% is typical for a strong match, since '
      + 'multi-word phrases rarely match word-for-word even when your '
      + 'experience genuinely fits. From here you can answer a few clarifying '
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
      + 'recommended). Click Generate when you’re happy with the look. Note: the '
      + 'preview and PDF paginate identically (same render engine); a .docx '
      + 'download page-breaks the same words through Word instead, so exactly '
      + 'where a page splits can shift slightly there — the content is always '
      + 'the same.',
    tip: 'Step 4 — Template',
  },
  panelGenerate: {
    title: 'Step 5 — Generate',
    body: 'Choose your output format and click Generate. If you saved and '
      + 'continued from Compose, sartor already has your approved composition — '
      + 'clicking Generate just assembles it into the chosen format, instantly '
      + 'and identically every time (no further AI writing, so re-generating '
      + 'the same composition never changes the wording). If you skipped ahead '
      + 'without approving a composition, sartor writes the résumé fresh with '
      + 'an AI call instead, which usually takes about 30–60 seconds.',
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
  // F-06: the post-create tab jump (Tailor → Career corpus) explained in the
  // moment it happens — fired by onUserSelect when smart-landing routes a
  // new/empty-corpus user to the Corpus tab. Once-ever via cb_help_seen.
  tourCorpusLanding: {
    title: 'Let’s build your corpus first',
    body: 'You landed on the Career corpus tab because your profile is empty — '
      + 'sartor tailors résumés from a corpus of your experience, so that’s '
      + 'the one thing to set up first. Import a résumé (fastest) or add an '
      + 'experience by hand; when the corpus is ready, head to Tailor to '
      + 'target a job.',
    tip: 'Why am I on Career corpus?',
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
      copyBtn.textContent = 'Copied ✓';
    } catch {
      // Clipboard API blocked (non-secure context etc.) — fall back to
      // selecting the textarea so the user can Ctrl+C manually.
      if (ta) { ta.focus(); ta.select(); }
      copyBtn.textContent = 'Selected — press Ctrl+C';
    }
    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
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

  // Phase 4 / item (a) — in corpus mode the résumé is a DETERMINISTIC assembly
  // of the Compose-approved composition; there is no résumé-body LLM to re-run
  // wholesale. Instead of a full regenerate, draft ONE scoped item (a sharpened
  // bullet or the summary) and route BACK to Compose with a richer banner that
  // shows the actual proposed change for accept/retire. Legacy (file-based)
  // refine keeps the LLM full regenerate below.
  if (_composeApplicationId != null) {
    await _submitSurgicalRefinement(note);
    return;
  }

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
      const choice = await _showRefinementScopeModal(reason, document.getElementById('btnRefinement'));
      if (choice !== 'proceed') {
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

// Item (a) — the corpus-mode surgical-refinement loop-back. Runs the SAME
// fact-scope check the legacy path uses (a note can still ask for something
// out of scope), then drafts ONE scoped proposal (POST /draft-refinement) and
// stashes both the note AND the proposal (or null, when the model couldn't
// scope one — e.g. a broad "rewrite everything" ask) so Compose's loop-back
// banner can render the ACTUAL change for accept/retire, not just static
// copy. Non-blocking on draft failure: falls back to the generic "adjust it
// yourself" banner rather than stranding the user's refinement ask.
async function _submitSurgicalRefinement(note) {
  const input = document.getElementById('refinementInput');
  const btn = document.getElementById('btnRefinement');
  if (btn) btn.disabled = true;
  try {
    setStatus('CHECKING REFINEMENT SCOPE');
    const checkRes = await fetch('/api/validate-refinement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    });
    const check = await checkRes.json();
    if (!check.valid) {
      const reason = check.reason || 'This may change facts rather than just wording.';
      const choice = await _showRefinementScopeModal(reason, btn);
      if (choice !== 'proceed') {
        setStatus('REFINEMENT CANCELED');
        return;
      }
    }

    setStatus('DRAFTING TARGETED REFINEMENT');
    _setBusy(true, 'Finding the one thing to change');
    let proposal = null;
    if (_composeApplicationId != null) {
      try {
        const res = await fetch(
          `/api/applications/${_composeApplicationId}/draft-refinement`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ context_path: lastContextPath, note }) },
        );
        if (res.ok) proposal = (await res.json()).proposal || null;
      } catch {
        // Non-blocking — falls back to the generic loop-back banner below.
      }
    }

    if (input) input.value = '';
    _composeLoopbackNote = note;
    _composeRefinementProposal = proposal;
    wizardGoTo(3);
    setStatus('BACK TO COMPOSE');
    _announce(proposal
      ? 'A targeted change is ready for your review in Compose.'
      : 'Refinement moved to Compose — adjust your content there, then continue.');
  } catch (e) {
    // A transient failure here (e.g. /api/validate-refinement network error)
    // used to propagate uncaught — the finally block below still reset the
    // busy state, but nothing told the user anything had failed. Mirrors the
    // legacy refine path's catch (above, submitRefinement): surface via
    // reportError, AND leave a visible "NOT EXECUTED" entry in the same
    // refinement history panel both refine paths share. `input` is
    // deliberately left populated (only cleared on success, above) and `btn`
    // is re-enabled in `finally` — together, the retry affordance is simply
    // clicking Refine again with the note still in the box.
    reportError('Refine', 'Refinement request failed', e.message);
    refinementHistory.push({ note, status: 'rejected', reason: 'Request failed: ' + e.message });
    _renderRefinementHistory();
  } finally {
    _setBusy(false);
    if (btn) btn.disabled = false;
  }
}

// The explaining banner shown at the top of Compose after a loop-back. Rendered
// from _composeLoopbackNote (+ _composeRefinementProposal, item (a)) inside
// loadComposition so it survives the auto-recommend re-render cascade;
// dismissing/deciding clears the flags. `data` is the GET /composition payload
// loadComposition just fetched — used to look up the company name + any
// superseded bullet's current text for the proposal card.
function _renderComposeLoopbackBanner(data) {
  const banner = _el('div', { className: 'compose-loopback-banner' });
  const proposal = _composeRefinementProposal;

  if (!proposal) {
    // The plain (pre-item-(a)) loop-back: no scoped proposal came back (e.g.
    // the note asked for a broad rewrite the model correctly declined to
    // scope) — fall back to pointing the user at Compose directly.
    banner.appendChild(_el('div', {
      className: 'compose-loopback-title',
      textContent: 'Adjust your content here, then regenerate',
    }));
    banner.appendChild(_el('div', {
      className: 'compose-loopback-body',
      textContent:
        'Your résumé is assembled from the content you approve here — there is no '
        + 'separate rewrite step. Make your change (bullets, summary, skills) and '
        + 'Save and continue to regenerate.'
        + (_composeLoopbackNote ? ` You asked: “${_composeLoopbackNote}”` : ''),
    }));
    const dismiss = _el('button', {
      className: 'btn-secondary btn-sm compose-loopback-dismiss', textContent: 'Got it',
    });
    dismiss.onclick = () => { _composeLoopbackNote = null; banner.remove(); };
    banner.appendChild(dismiss);
    return banner;
  }

  // Item (a) — a scoped proposal came back: show the ACTUAL change (old text
  // struck through when it supersedes an existing bullet, then the new text)
  // with Accept / Retire, instead of just telling the user to go make it.
  banner.classList.add('compose-loopback-banner-proposal');
  banner.appendChild(_el('div', {
    className: 'compose-loopback-title',
    textContent: 'One targeted change is ready for your review',
  }));
  if (_composeLoopbackNote) {
    banner.appendChild(_el('div', {
      className: 'compose-loopback-body',
      textContent: `You asked: “${_composeLoopbackNote}”`,
    }));
  }

  const card = _el('div', { className: 'compose-loopback-proposal-card' });
  if (proposal.target_kind === 'summary') {
    card.appendChild(_el('div', {
      className: 'loopback-target-label', textContent: 'Positioning summary',
    }));
    const oldText = (data && data.summary && data.summary.drafted_text) || '';
    if (oldText && oldText !== proposal.text) {
      card.appendChild(_el('div', { className: 'loopback-old-text', textContent: oldText }));
    }
    card.appendChild(_el('div', { className: 'loopback-new-text', textContent: proposal.text }));
  } else {
    const exp = (data && data.experiences || []).find(e => e.id === proposal.experience_id);
    card.appendChild(_el('div', {
      className: 'loopback-target-label',
      textContent: `Bullet — ${exp ? exp.company : 'this role'}`,
    }));
    if (proposal.supersedes_bullet_id != null && exp) {
      const oldBullet = (exp.bullets || []).find(b => b.id === proposal.supersedes_bullet_id);
      if (oldBullet) {
        card.appendChild(_el('div', { className: 'loopback-old-text', textContent: oldBullet.text }));
      }
    }
    card.appendChild(_el('div', { className: 'loopback-new-text', textContent: proposal.text }));
  }
  if (proposal.rationale) {
    card.appendChild(_el('div', {
      className: 'loopback-rationale', textContent: proposal.rationale,
    }));
  }
  banner.appendChild(card);

  const actions = _el('div', { className: 'compose-loopback-actions' });
  const accept = _el('button', {
    className: 'btn-secondary btn-sm compose-loopback-accept', textContent: 'Accept',
  });
  accept.onclick = () => {
    _composeRefinementProposal = null;
    _composeLoopbackNote = null;
    _acceptRefinementProposal(proposal);
  };
  const retire = _el('button', {
    className: 'btn-secondary btn-sm compose-loopback-retire', textContent: 'Retire',
  });
  // Retire never reaches the server — nothing was written for a proposal the
  // user hasn't accepted — so this is a pure client-side dismiss.
  retire.onclick = () => { _composeRefinementProposal = null; _composeLoopbackNote = null; banner.remove(); };
  actions.appendChild(accept);
  actions.appendChild(retire);
  banner.appendChild(actions);
  return banner;
}

// Apply an accepted surgical-refinement proposal (item (a)): POST
// /accept-refinement (a pending Bullet folded into the composition +, when it
// supersedes one, that bullet excluded — or the summary override) and reload
// Compose so the change shows immediately. Mirrors _decideGapFill's bg-reload
// bookkeeping (increment before the fetch, decrement in finally).
async function _acceptRefinementProposal(proposal) {
  if (_composeApplicationId == null || !lastContextPath) { loadComposition(); return; }
  _markComposeBgReload(1);
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/accept-refinement`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_path: lastContextPath, proposal }) },
    );
    if (res.ok) { _toast('Change applied.'); loadComposition(); }
    else { _toast('Could not apply the change — please make it manually below.', true); loadComposition(); }
  } catch {
    _toast('Network error applying the change — please make it manually below.', true);
    loadComposition();
  } finally {
    _markComposeBgReload(-1);
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
  // dec 4(b) — undo _setBtnPending's relabel + pulse from the last round
  // too, not just the disabled flag, so a fresh round doesn't show a
  // clickable button still reading "Generating…".
  if (btn) _clearBtnPending(btn, 'Get follow-up questions');
}

async function runIterateClarify() {
  if (!lastContextPath) return;
  if (currentIteration < 1) {
    return alert('Generate the resume at least once before requesting iteration questions.');
  }

  const proceed = await _gateEditsBeforeAction(document.getElementById('btnIterateClarify'));
  if (!proceed) return;

  setStatus('GENERATING QUESTIONS');
  _setBusy(true, 'Generating clarifying questions…');
  const btn = document.getElementById('btnIterateClarify');
  _setBtnPending(btn, 'Generating…');

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
      _clearBtnPending(btn, 'Get follow-up questions');
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
    _clearBtnPending(btn, 'Get follow-up questions');
    reportError('Iteration interview', 'Iteration interview request failed', e.message);
  } finally {
    _setBusy(false);
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
    badge.textContent = kind === 'scope_probe' ? 'Scope'
                       : kind === 'iteration_probe' ? 'Iteration'
                       : 'Experience';
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
      ? `<span class="refinement-badge-rejected">Not executed</span>`
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
// thrown error in fetch / navigation would unwind the await and the
// user would just see a non-responsive button). The disabled-then-
// re-enabled toggle also prevents a second click from racing an
// in-flight fetch.
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

// F-10 (2026-07 UX review) — POST the edited content, then follow the
// server's `download_url` with a plain top-level navigation (a real
// Content-Disposition: attachment response the browser's own download
// manager handles) instead of pulling the file back as a blob and
// synthesizing an <a>.click(). The blob + synthetic-click pattern is what
// Chrome's "multiple automatic downloads" heuristic could silently block on
// the second download in a row without a fresh user gesture — the bug the
// in-app caveat used to document. A location change to an attachment
// response is not a popup and is not subject to that heuristic, and it does
// not unload the current page (the browser recognizes the attachment and
// downloads instead of navigating away). Errors are still caught here (the
// fetch/JSON step) and surfaced via _runDownload's reportError — no silent
// no-op.
async function _downloadEdited(url, payload) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Download failed (${res.status})`);
  }
  const data = await res.json().catch(() => ({}));
  if (!data.download_url) {
    throw new Error('Download failed — the server did not return a file location.');
  }
  window.location.href = data.download_url;
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
// F-23 — the two "ambient" panels that used to crowd the wizard off-screen
// (User selection, Prior applications) persist their collapsed/expanded state
// across reloads, so a returning visitor's own choice sticks instead of
// re-inheriting the collapsed-by-default posture every time. Any manual
// toggle (via _togglePanel) on one of these ids is remembered here; every
// other .cb-panel (wizard step panels, Corpus, etc.) is unaffected.
const _FOLDABLE_PANEL_IDS = ['panelUser', 'panelApplications'];

function _togglePanel(panelId) {
  const panel = document.getElementById(panelId);
  if (!panel || panel.classList.contains('hidden')) return;
  // A panel marked .not-collapsible ignores header clicks (e.g. the User
  // selection box before a user is picked — see onUserSelect).
  if (panel.classList.contains('not-collapsible')) return;
  const isCollapsed = panel.classList.toggle('collapsed');
  const block = document.querySelector(`[data-panel="${panelId}"]`);
  if (block) block.classList.toggle('collapsed', isCollapsed);
  if (_FOLDABLE_PANEL_IDS.includes(panelId)) {
    try {
      localStorage.setItem(`cb_panel_collapsed:${panelId}`, isCollapsed ? '1' : '0');
    } catch { /* storage unavailable (private mode, quota) — state just won't persist */ }
  }
}

// Apply the persisted collapse choice for a foldable panel, or `defaultCollapsed`
// when nothing is stored yet (first visit). Called once the panel becomes
// relevant (a user is selected) rather than on every render, so it never
// fights a click the user just made in the same flow.
function _applyFoldableDefault(panelId, defaultCollapsed) {
  const panel = document.getElementById(panelId);
  if (!panel || panel.classList.contains('not-collapsible')) return;
  let stored = null;
  try { stored = localStorage.getItem(`cb_panel_collapsed:${panelId}`); } catch { /* ignore */ }
  const collapsed = stored === null ? defaultCollapsed : stored === '1';
  panel.classList.toggle('collapsed', collapsed);
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
  if (name === 'pipeline') refreshPipeline();
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
  // Scroll preservation (feat/ux-busy-states-and-hydration) — every accept /
  // retire / add-experience reloads the whole corpus list, and the
  // "Loading…" placeholder briefly shrinks the page and snaps window scroll
  // back toward the top ("accepting a bullet scrolls me to the top"). Same
  // capture/restore idiom as loadComposition(); see _captureScrollY.
  const _scrollY = _captureScrollY();
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
  // F-04 (UX-W1) — same independent-route/independent-failure-mode pattern
  // for the education + certifications editors.
  refreshEducationEditor();
  refreshCertificationsEditor();
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/experiences`);
  } catch (e) {
    _setLoadingPlaceholder(list, 'Network error.');
    _restoreScrollY(_scrollY);
    return;
  }
  if (res.status === 404) {
    _corpusExperiences = [];
    _corpusLoadedForUser = currentUser;
    _renderCorpusList();
    _refreshOnboardingBanner();  // fire-and-forget; fresh emptiness (empty → hides)
    _restoreScrollY(_scrollY);
    return;
  }
  if (!res.ok) {
    // Surface backend detail (added by list_experiences wrapper).
    const data = await res.json().catch(() => ({}));
    const detail = data.detail || data.error || `status ${res.status}`;
    _setLoadingPlaceholder(list, `Failed to load corpus: ${detail}`);
    _restoreScrollY(_scrollY);
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
  _restoreScrollY(_scrollY);
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
  delBtn.onclick = () => _deleteSummaryVariant(v.id, delBtn);
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

async function _deleteSummaryVariant(id, triggerEl) {
  const ok = await cbConfirm(
    'Past applications that pinned it still reference it; future Compose '
      + "steps will skip it. You can't undo from here.",
    { title: 'Retire this summary variant?', confirmLabel: 'Retire', triggerEl },
  );
  if (!ok) return;
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
  const deniedDetails = document.getElementById('skillsEditorDeniedDetails');
  const deniedSummary = document.getElementById('skillsEditorDeniedSummary');
  const deniedEl = document.getElementById('skillsEditorDenied');
  if (!section || !listEl) return;
  let res;
  try {
    // dec 6 (UX Cohesion Epic) — include_inactive=1 pulls in tombstoned
    // (denied/retired) skills too, so the Denied/retired lane below can
    // offer a Restore (un-deny) action instead of them vanishing forever.
    res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/skills?include_pending=1&include_inactive=1`);
  } catch { section.style.display = 'none'; return; }
  if (!res.ok) { section.style.display = 'none'; return; }
  const body = await res.json();
  const all = body.skills || [];
  const pending = all.filter(s => s.is_pending_review);
  const denied = all.filter(s => !s.is_pending_review && !s.is_active);
  const approved = all.filter(s => !s.is_pending_review && s.is_active);
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
  if (deniedDetails && deniedEl) {
    _clearChildren(deniedEl);
    if (denied.length) {
      deniedDetails.style.display = '';
      if (deniedSummary) deniedSummary.textContent = `Denied / retired skills (${denied.length})`;
      denied.forEach(s => deniedEl.appendChild(_renderDeniedSkillRow(s)));
    } else {
      deniedDetails.style.display = 'none';
    }
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

// dec 6 (UX Cohesion Epic) — a denied (pending suggestion) or retired
// (formerly-approved) skill, tombstoned via DELETE /api/skills/<id>
// (is_active=0, is_pending_review=0). Restore is the un-deny path: PUT
// is_active=true, mirroring the title/bullet "Restore" idiom.
function _renderDeniedSkillRow(s) {
  const row = _el('div', { className: 'summary-variant-row skill-editor-row skill-denied-row' });
  const head = _el('div', { className: 'skill-editor-head' });
  head.appendChild(_renderSkillChip(s.name, s.category));
  if (s.category) {
    head.appendChild(_el('span', {
      className: 'skill-category', textContent: ' · ' + s.category,
      style: 'color:var(--fg-2);font-size:0.85em;',
    }));
  }
  head.appendChild(_el('span', { className: 'corpus-row-flag retired', textContent: 'Denied' }));
  row.appendChild(head);

  const actions = _el('div', { className: 'summary-variant-actions' });
  const restore = _el('button', { className: 'corpus-action-btn', textContent: 'Restore' });
  restore.onclick = async () => {
    try {
      const r = await fetch(`/api/skills/${s.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: true }),
      });
      if (r.ok) { _toast('Skill restored'); refreshSkillsEditor(); }
      else _toast('Could not restore skill.', true);
    } catch { _toast('Network error restoring skill.', true); }
  };
  actions.appendChild(restore);
  row.appendChild(actions);
  return row;
}

// Co4 (round-2 quick win) — corpus-wide "Suggest skills from my corpus",
// wired to the already-built/tested `/skills/suggest-from-corpus` route
// (analyzer.suggest_skills_from_corpus: evidence-only gate, no JD in scope,
// unlike the JD-scoped Compose suggest-skills call). Mirrors the Compose
// "Suggest skills from this JD" button's working-state idiom
// (_fireSuggestSkills): disable + relabel while in flight, restore in a
// finally, refresh the editor on success so the new pending rows render.
async function suggestSkillsFromCorpus() {
  if (!currentUser) return;
  const btn = document.getElementById('btnSuggestSkillsFromCorpus');
  _setBtnPending(btn, 'Suggesting…');
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/skills/suggest-from-corpus`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' } },
    );
    if (res.ok) {
      const body = await res.json().catch(() => ({}));
      const n = (body.proposals || []).length;
      _toast(n ? `${n} skill suggestion${n === 1 ? '' : 's'} to review.` : 'No new grounded skills found.');
      await refreshSkillsEditor();
    } else {
      _toast('Could not suggest skills from your corpus.', true);
    }
  } catch {
    _toast('Network error suggesting skills.', true);
  } finally {
    _clearBtnPending(btn, 'Suggest skills from my corpus');
  }
}

// ============================================================
// dec 3 (G3/Co1, UX Cohesion Epic) — skill iconography.
// ============================================================
// Vendored inline SVG, Phosphor Icons (MIT license, phosphoricons.com),
// "duotone" weight (a 20%-opacity base shape + a full-opacity accent shape,
// both `fill="currentColor"` so a single CSS `color` recolors both layers).
// Source: raw.githubusercontent.com/phosphor-icons/core assets/duotone/.
// See CHANGELOG.md [Unreleased] for the vendoring note.
//
// `category` on a Skill is free-text (no DB CHECK — a human can type
// anything, and the LLM-suggested category isn't constrained either), so
// this is a best-effort keyword match against the five categories the "Add
// skill" modal itself suggests (language | framework | platform |
// methodology | domain), falling back to a neutral generic glyph for
// anything else. The glyph→concept mapping below is the owner-review item
// from the branch report — flag before merge, not a load-bearing contract.
// `Map`, not a plain object — `category` is free-text (see above) and a
// plain-object lookup keyed by an attacker-or-just-weird-influenced string
// like "__proto__"/"constructor" would resolve to Object.prototype instead
// of falling through to the default. `Map` has no such prototype-chain
// lookup surface.
const _SKILL_CATEGORY_ICONS = new Map(Object.entries({
  // language — a code/programming-language glyph.
  code: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
    + '<path d="M240,128l-48,40H64L16,128,64,88H192Z" opacity="0.2"/>'
    + '<path d="M69.12,94.15,28.5,128l40.62,33.85a8,8,0,1,1-10.24,12.29l-48-40a8,8,0,0,1,0-12.29l48-40a8,8,0,0,1,10.24,12.3Zm176,27.7-48-40a8,8,0,1,0-10.24,12.3L227.5,128l-40.62,33.85a8,8,0,1,0,10.24,12.29l48-40a8,8,0,0,0,0-12.29ZM162.73,32.48a8,8,0,0,0-10.25,4.79l-64,176a8,8,0,0,0,4.79,10.26A8.14,8.14,0,0,0,96,224a8,8,0,0,0,7.52-5.27l64-176A8,8,0,0,0,162.73,32.48Z"/></svg>',
  // framework — layered stack (a framework sits in layers atop a language).
  stack: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
    + '<path d="M224,80l-96,56L32,80l96-56Z" opacity="0.2"/>'
    + '<path d="M230.91,172A8,8,0,0,1,228,182.91l-96,56a8,8,0,0,1-8.06,0l-96-56A8,8,0,0,1,36,169.09l92,53.65,92-53.65A8,8,0,0,1,230.91,172ZM220,121.09l-92,53.65L36,121.09A8,8,0,0,0,28,134.91l96,56a8,8,0,0,0,8.06,0l96-56A8,8,0,1,0,220,121.09ZM24,80a8,8,0,0,1,4-6.91l96-56a8,8,0,0,1,8.06,0l96,56a8,8,0,0,1,0,13.82l-96,56a8,8,0,0,1-8.06,0l-96-56A8,8,0,0,1,24,80Zm23.88,0L128,126.74,208.12,80,128,33.26Z"/></svg>',
  // platform — cloud (runtime/infra/OS platforms).
  cloud: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
    + '<path d="M240,128a80,80,0,0,1-80,80H72A56,56,0,1,1,85.92,97.74l0,.1A80,80,0,0,1,240,128Z" opacity="0.2"/>'
    + '<path d="M160,40A88.09,88.09,0,0,0,81.29,88.67,64,64,0,1,0,72,216h88a88,88,0,0,0,0-176Zm0,160H72a48,48,0,0,1,0-96c1.1,0,2.2,0,3.29.11A88,88,0,0,0,72,128a8,8,0,0,0,16,0,72,72,0,1,1,72,72Z"/></svg>',
  // methodology — flow/process arrow.
  'flow-arrow': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
    + '<path d="M80,176a32,32,0,1,1-32-32A32,32,0,0,1,80,176Z" opacity="0.2"/>'
    + '<path d="M245.66,74.34l-32-32a8,8,0,0,0-11.32,11.32L220.69,72H208c-49.33,0-61.05,28.12-71.38,52.92-9.38,22.51-16.92,40.59-49.48,42.84a40,40,0,1,0,.1,16c43.26-2.65,54.34-29.15,64.14-52.69C161.41,107,169.33,88,208,88h12.69l-18.35,18.34a8,8,0,0,0,11.32,11.32l32-32A8,8,0,0,0,245.66,74.34ZM48,200a24,24,0,1,1,24-24A24,24,0,0,1,48,200Z"/></svg>',
  // domain — globe (industry/subject-matter domain knowledge).
  globe: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
    + '<path d="M224,128a96,96,0,1,1-96-96A96,96,0,0,1,224,128Z" opacity="0.2"/>'
    + '<path d="M128,24h0A104,104,0,1,0,232,128,104.12,104.12,0,0,0,128,24Zm88,104a87.61,87.61,0,0,1-3.33,24H174.16a157.44,157.44,0,0,0,0-48h38.51A87.61,87.61,0,0,1,216,128ZM102,168H154a115.11,115.11,0,0,1-26,45A115.27,115.27,0,0,1,102,168Zm-3.9-16a140.84,140.84,0,0,1,0-48h59.88a140.84,140.84,0,0,1,0,48ZM40,128a87.61,87.61,0,0,1,3.33-24H81.84a157.44,157.44,0,0,0,0,48H43.33A87.61,87.61,0,0,1,40,128ZM154,88H102a115.11,115.11,0,0,1,26-45A115.27,115.27,0,0,1,154,88Zm52.33,0H170.71a135.28,135.28,0,0,0-22.3-45.6A88.29,88.29,0,0,1,206.37,88ZM107.59,42.4A135.28,135.28,0,0,0,85.29,88H49.63A88.29,88.29,0,0,1,107.59,42.4ZM49.63,168H85.29a135.28,135.28,0,0,0,22.3,45.6A88.29,88.29,0,0,1,49.63,168Zm98.78,45.6a135.28,135.28,0,0,0,22.3-45.6h35.66A88.29,88.29,0,0,1,148.41,213.6Z"/></svg>',
  // uncategorized / unrecognized — generic capability glyph (gear).
  gear: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">'
    + '<path d="M207.86,123.18l16.78-21a99.14,99.14,0,0,0-10.07-24.29l-26.7-3a81,81,0,0,0-6.81-6.81l-3-26.71a99.43,99.43,0,0,0-24.3-10l-21,16.77a81.59,81.59,0,0,0-9.64,0l-21-16.78A99.14,99.14,0,0,0,77.91,41.43l-3,26.7a81,81,0,0,0-6.81,6.81l-26.71,3a99.43,99.43,0,0,0-10,24.3l16.77,21a81.59,81.59,0,0,0,0,9.64l-16.78,21a99.14,99.14,0,0,0,10.07,24.29l26.7,3a81,81,0,0,0,6.81,6.81l3,26.71a99.43,99.43,0,0,0,24.3,10l21-16.77a81.59,81.59,0,0,0,9.64,0l21,16.78a99.14,99.14,0,0,0,24.29-10.07l3-26.7a81,81,0,0,0,6.81-6.81l26.71-3a99.43,99.43,0,0,0,10-24.3l-16.77-21A81.59,81.59,0,0,0,207.86,123.18ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z" opacity="0.2"/>'
    + '<path d="M128,80a48,48,0,1,0,48,48A48.05,48.05,0,0,0,128,80Zm0,80a32,32,0,1,1,32-32A32,32,0,0,1,128,160Zm88-29.84q.06-2.16,0-4.32l14.92-18.64a8,8,0,0,0,1.48-7.06,107.6,107.6,0,0,0-10.88-26.25,8,8,0,0,0-6-3.93l-23.72-2.64q-1.48-1.56-3-3L186,40.54a8,8,0,0,0-3.94-6,107.29,107.29,0,0,0-26.25-10.86,8,8,0,0,0-7.06,1.48L130.16,40Q128,40,125.84,40L107.2,25.11a8,8,0,0,0-7.06-1.48A107.6,107.6,0,0,0,73.89,34.51a8,8,0,0,0-3.93,6L67.32,64.27q-1.56,1.49-3,3L40.54,70a8,8,0,0,0-6,3.94,107.71,107.71,0,0,0-10.87,26.25,8,8,0,0,0,1.49,7.06L40,125.84Q40,128,40,130.16L25.11,148.8a8,8,0,0,0-1.48,7.06,107.6,107.6,0,0,0,10.88,26.25,8,8,0,0,0,6,3.93l23.72,2.64q1.49,1.56,3,3L70,215.46a8,8,0,0,0,3.94,6,107.71,107.71,0,0,0,26.25,10.87,8,8,0,0,0,7.06-1.49L125.84,216q2.16.06,4.32,0l18.64,14.92a8,8,0,0,0,7.06,1.48,107.21,107.21,0,0,0,26.25-10.88,8,8,0,0,0,3.93-6l2.64-23.72q1.56-1.48,3-3L215.46,186a8,8,0,0,0,6-3.94,107.71,107.71,0,0,0,10.87-26.25,8,8,0,0,0-1.49-7.06Zm-16.1-6.5a73.93,73.93,0,0,1,0,8.68,8,8,0,0,0,1.74,5.48l14.19,17.73a91.57,91.57,0,0,1-6.23,15L187,173.11a8,8,0,0,0-5.1,2.64,74.11,74.11,0,0,1-6.14,6.14,8,8,0,0,0-2.64,5.1l-2.51,22.58a91.32,91.32,0,0,1-15,6.23l-17.74-14.19a8,8,0,0,0-5-1.75h-.48a73.93,73.93,0,0,1-8.68,0,8.06,8.06,0,0,0-5.48,1.74L100.45,215.8a91.57,91.57,0,0,1-15-6.23L82.89,187a8,8,0,0,0-2.64-5.1,74.11,74.11,0,0,1-6.14-6.14,8,8,0,0,0-5.1-2.64L46.43,170.6a91.32,91.32,0,0,1-6.23-15l14.19-17.74a8,8,0,0,0,1.74-5.48,73.93,73.93,0,0,1,0-8.68,8,8,0,0,0-1.74-5.48L40.2,100.45a91.57,91.57,0,0,1,6.23-15L69,82.89a8,8,0,0,0,5.1-2.64,74.11,74.11,0,0,1,6.14-6.14A8,8,0,0,0,82.89,69L85.4,46.43a91.32,91.32,0,0,1,15-6.23l17.74,14.19a8,8,0,0,0,5.48,1.74,73.93,73.93,0,0,1,8.68,0,8.06,8.06,0,0,0,5.48-1.74L155.55,40.2a91.57,91.57,0,0,1,15,6.23L173.11,69a8,8,0,0,0,2.64,5.1,74.11,74.11,0,0,1,6.14,6.14,8,8,0,0,0,5.1,2.64l22.58,2.51a91.32,91.32,0,0,1,6.23,15l-14.19,17.74A8,8,0,0,0,199.87,123.66Z"/></svg>',
}));

// Owner-review glyph→concept mapping (see the module comment above): the
// five categories the "Add skill" modal suggests, each to one Phosphor
// duotone glyph + one existing brand/functional color token. `Map` for the
// same __proto__-key-collision reason as _SKILL_CATEGORY_ICONS above.
const _SKILL_CATEGORY_META = new Map(Object.entries({
  language:    { icon: 'code',       color: 'var(--info)',   soft: 'var(--info-soft)' },
  framework:   { icon: 'stack',      color: 'var(--brand)',  soft: 'var(--brand-soft)' },
  platform:    { icon: 'cloud',      color: 'var(--violet)', soft: 'var(--violet-soft)' },
  methodology: { icon: 'flow-arrow', color: 'var(--success)', soft: 'var(--success-soft)' },
  domain:      { icon: 'globe',      color: 'var(--warning)', soft: 'var(--warning-soft)' },
}));
const _SKILL_CATEGORY_DEFAULT = { icon: 'gear', color: 'var(--fg-2)', soft: 'var(--neutral-soft)' };

function _skillCategoryMeta(category) {
  const key = (category || '').trim().toLowerCase();
  return _SKILL_CATEGORY_META.get(key) || _SKILL_CATEGORY_DEFAULT;
}

// Renders the [glyph-on-colored-background] + [name] chip shared by every
// skill row (Career Corpus editor, Compose skill list, pending-review and
// denied lanes in both). Category-tinted background/border on the chip
// itself (the "colored chips" half of dec 3); the icon badge inside carries
// the "glyph on a colored background" half.
function _renderSkillChip(name, category) {
  const meta = _skillCategoryMeta(category);
  const chip = _el('span', {
    className: 'skill-chip',
    style: `--skill-accent:${meta.color};--skill-accent-soft:${meta.soft};`,
  });
  const badge = _el('span', { className: 'skill-icon-badge' });
  // meta.icon always comes from the fixed _SKILL_CATEGORY_META /
  // _SKILL_CATEGORY_DEFAULT registry above (never from raw user text), and
  // _SKILL_CATEGORY_ICONS is itself a closed, hardcoded set of vendored SVG
  // strings authored in this file — never fetched or attacker-influenced,
  // so this innerHTML assignment has no untrusted-content path.
  badge.innerHTML = _SKILL_CATEGORY_ICONS.get(meta.icon) || '';
  badge.setAttribute('aria-hidden', 'true');
  chip.appendChild(badge);
  chip.appendChild(_el('span', { className: 'skill-name', textContent: name }));
  return chip;
}

function _renderSkillEditorRow(s, isPending) {
  const row = _el('div', { className: 'summary-variant-row skill-editor-row' });
  if (isPending) row.classList.add('skill-pending');
  const head = _el('div', { className: 'skill-editor-head' });
  head.appendChild(_renderSkillChip(s.name, s.category));
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
    del.onclick = () => _deleteSkillEditor(s.id, del);
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

async function _deleteSkillEditor(id, triggerEl) {
  const ok = await cbConfirm(
    'Future Compose steps will skip it. Past applications that pinned it '
      + 'still reference it.',
    { title: 'Retire this skill?', confirmLabel: 'Retire', triggerEl },
  );
  if (!ok) return;
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
// F-04 (UX-W1, 2026-07-07) — Education + Certifications editors (Career corpus)
// ============================================================
// Candidate-level Corpus Items, same row chrome as the Skills editor above
// (.summary-variant-row / .corpus-action-btn), but with no pending-review
// lifecycle — db/models.py's Education/Certification carry no `source` /
// `is_pending_review`; nothing here is LLM-proposed, a human types these
// directly. db/build_context.py already reads both tables (ordered by
// display_order) into the synthesized corpus-mode résumé the analyze/
// generate prompts see; this editor is the missing UI half of that.
//
// Reorder: neither the Skills nor Summary-variant editors above have visible
// reorder controls (their display_order is set once, at insertion), so there
// is no existing corpus-editor reorder affordance to copy. _reorderCorpusRow
// mirrors the Compose bullet-list's keyboard-reorder mechanics instead
// (.reorder-controls/.reorder-btn) scaled down to an immediate swap-and-PUT
// (no debounce — a corpus edit persists right away, unlike Compose autosave).

async function _reorderCorpusRow(row, dir, putUrlFor) {
  const list = row.parentElement;
  if (!list) return;
  const sib = dir < 0 ? row.previousElementSibling : row.nextElementSibling;
  if (!sib) return;  // already at an edge — nothing to do
  const rowId = Number(row.dataset.id);
  const sibId = Number(sib.dataset.id);
  const rowOrder = row.dataset.order;
  const sibOrder = sib.dataset.order;
  if (dir < 0) list.insertBefore(row, sib);
  else list.insertBefore(sib, row);
  try {
    await Promise.all([
      _putJson(putUrlFor(rowId), { display_order: Number(sibOrder) }),
      _putJson(putUrlFor(sibId), { display_order: Number(rowOrder) }),
    ]);
    row.dataset.order = sibOrder;
    sib.dataset.order = rowOrder;
  } catch (e) {
    _toast('Could not reorder: ' + e.message, true);
  }
}

async function refreshEducationEditor() {
  if (!currentUser) return;
  const section = document.getElementById('educationEditorSection');
  const listEl = document.getElementById('educationEditorList');
  const hint = document.getElementById('educationEditorEmptyHint');
  if (!section || !listEl) return;
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/education`);
  } catch { section.style.display = 'none'; return; }
  if (!res.ok) { section.style.display = 'none'; return; }
  const body = await res.json();
  const rows = body.education || [];
  section.style.display = '';
  _clearChildren(listEl);
  if (rows.length === 0) {
    hint.textContent = 'No education yet. Click + Add education, or import a résumé.';
    return;
  }
  hint.textContent = 'Schools and degrees the résumé can surface.';
  rows.forEach((e, i) => listEl.appendChild(_renderEducationRow(e, i === 0, i === rows.length - 1)));
}

function _renderEducationRow(e, isFirst, isLast) {
  const row = _el('div', { className: 'summary-variant-row education-editor-row' });
  row.dataset.id = String(e.id);
  row.dataset.order = String(e.display_order);

  const head = _el('div', { className: 'skill-editor-head' });
  const titleParts = [e.degree, e.institution].filter(Boolean);
  head.appendChild(_el('span', { className: 'skill-name', textContent: titleParts.join(', ') || e.institution }));
  const dateRange = [e.start_date, e.end_date].filter(Boolean).join(' – ');
  if (dateRange) {
    head.appendChild(_el('span', {
      className: 'skill-category', textContent: ' · ' + dateRange,
      style: 'color:var(--fg-2);font-size:0.85em;',
    }));
  }
  row.appendChild(head);
  if (e.field) {
    row.appendChild(_el('div', { className: 'edit-hint', textContent: e.field, style: 'margin:2px 0' }));
  }

  const actions = _el('div', { className: 'summary-variant-actions' });
  const reorder = _el('div', { className: 'reorder-controls' });
  const up = _el('button', { className: 'reorder-btn', textContent: '↑', title: 'Move up' });
  up.type = 'button';
  up.disabled = isFirst;
  up.onclick = () => _reorderCorpusRow(row, -1, id => `/api/education/${id}`);
  const down = _el('button', { className: 'reorder-btn', textContent: '↓', title: 'Move down' });
  down.type = 'button';
  down.disabled = isLast;
  down.onclick = () => _reorderCorpusRow(row, 1, id => `/api/education/${id}`);
  reorder.appendChild(up);
  reorder.appendChild(down);
  actions.appendChild(reorder);

  const editBtn = _el('button', { className: 'corpus-action-btn', textContent: 'Edit' });
  editBtn.onclick = () => openEducationEdit(e);
  actions.appendChild(editBtn);

  const del = _el('button', {
    className: 'corpus-action-btn delete', textContent: 'Retire',
    title: 'Soft-retire this education entry. Future résumés will skip it.',
  });
  del.onclick = () => _deleteEducationEditor(e.id);
  actions.appendChild(del);

  row.appendChild(actions);
  return row;
}

async function openEducationAdd() {
  if (!currentUser) return;
  const values = await openFormModal({
    title: 'Add education',
    subtitle: 'A school or program the résumé can surface.',
    submitLabel: 'Add education',
    fields: [
      { name: 'institution', label: 'Institution', type: 'text', required: true, placeholder: 'e.g. University of Washington' },
      { name: 'degree', label: 'Degree (optional)', type: 'text', placeholder: 'e.g. B.S. Computer Science' },
      { name: 'field', label: 'Field of study (optional)', type: 'text' },
      { name: 'start_date', label: 'Start date (optional)', type: 'text', placeholder: 'YYYY or YYYY-MM' },
      { name: 'end_date', label: 'End date (optional)', type: 'text', placeholder: 'YYYY or YYYY-MM' },
    ],
  });
  if (!values) return;
  const institution = (values.institution || '').trim();
  if (!institution) { _toast('Institution cannot be empty.', true); return; }
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/education`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          institution,
          degree: (values.degree || '').trim() || null,
          field: (values.field || '').trim() || null,
          start_date: (values.start_date || '').trim() || null,
          end_date: (values.end_date || '').trim() || null,
        }) },
    );
    if (res.ok) refreshEducationEditor();
    else {
      const d = await res.json().catch(() => ({}));
      _toast(d.error || 'Could not add education.', true);
    }
  } catch { _toast('Network error.', true); }
}

async function openEducationEdit(e) {
  const values = await openFormModal({
    title: 'Edit education',
    submitLabel: 'Save',
    fields: [
      { name: 'institution', label: 'Institution', type: 'text', required: true, defaultValue: e.institution },
      { name: 'degree', label: 'Degree (optional)', type: 'text', defaultValue: e.degree || '' },
      { name: 'field', label: 'Field of study (optional)', type: 'text', defaultValue: e.field || '' },
      { name: 'start_date', label: 'Start date (optional)', type: 'text', defaultValue: e.start_date || '' },
      { name: 'end_date', label: 'End date (optional)', type: 'text', defaultValue: e.end_date || '' },
    ],
  });
  if (!values) return;
  const institution = (values.institution || '').trim();
  if (!institution) { _toast('Institution cannot be empty.', true); return; }
  try {
    await _putJson(`/api/education/${e.id}`, {
      institution,
      degree: (values.degree || '').trim() || null,
      field: (values.field || '').trim() || null,
      start_date: (values.start_date || '').trim() || null,
      end_date: (values.end_date || '').trim() || null,
    });
    refreshEducationEditor();
  } catch (err) { _toast('Could not save: ' + err.message, true); }
}

async function _deleteEducationEditor(id) {
  if (!confirm('Retire this education entry?\n\nFuture résumés will skip it. '
               + 'You can\'t undo from here.')) return;
  try {
    await _deleteJson(`/api/education/${id}`);
    refreshEducationEditor();
  } catch (e) { _toast('Could not retire: ' + e.message, true); }
}

async function refreshCertificationsEditor() {
  if (!currentUser) return;
  const section = document.getElementById('certificationsEditorSection');
  const listEl = document.getElementById('certificationsEditorList');
  const hint = document.getElementById('certificationsEditorEmptyHint');
  if (!section || !listEl) return;
  let res;
  try {
    res = await fetch(`/api/users/${encodeURIComponent(currentUser)}/certifications`);
  } catch { section.style.display = 'none'; return; }
  if (!res.ok) { section.style.display = 'none'; return; }
  const body = await res.json();
  const rows = body.certifications || [];
  section.style.display = '';
  _clearChildren(listEl);
  if (rows.length === 0) {
    hint.textContent = 'No certifications yet. Click + Add certification, or import a résumé.';
    return;
  }
  hint.textContent = 'Professional certifications the résumé can surface.';
  rows.forEach((c, i) => listEl.appendChild(_renderCertificationRow(c, i === 0, i === rows.length - 1)));
}

function _renderCertificationRow(c, isFirst, isLast) {
  const row = _el('div', { className: 'summary-variant-row certification-editor-row' });
  row.dataset.id = String(c.id);
  row.dataset.order = String(c.display_order);

  const head = _el('div', { className: 'skill-editor-head' });
  head.appendChild(_el('span', { className: 'skill-name', textContent: c.name }));
  if (c.issuer) {
    head.appendChild(_el('span', {
      className: 'skill-category', textContent: ' · ' + c.issuer,
      style: 'color:var(--fg-2);font-size:0.85em;',
    }));
  }
  row.appendChild(head);
  const dateRange = [c.issued, c.expires].filter(Boolean).join(' – ');
  if (dateRange) {
    row.appendChild(_el('div', { className: 'edit-hint', textContent: dateRange, style: 'margin:2px 0' }));
  }

  const actions = _el('div', { className: 'summary-variant-actions' });
  const reorder = _el('div', { className: 'reorder-controls' });
  const up = _el('button', { className: 'reorder-btn', textContent: '↑', title: 'Move up' });
  up.type = 'button';
  up.disabled = isFirst;
  up.onclick = () => _reorderCorpusRow(row, -1, id => `/api/certifications/${id}`);
  const down = _el('button', { className: 'reorder-btn', textContent: '↓', title: 'Move down' });
  down.type = 'button';
  down.disabled = isLast;
  down.onclick = () => _reorderCorpusRow(row, 1, id => `/api/certifications/${id}`);
  reorder.appendChild(up);
  reorder.appendChild(down);
  actions.appendChild(reorder);

  const editBtn = _el('button', { className: 'corpus-action-btn', textContent: 'Edit' });
  editBtn.onclick = () => openCertificationEdit(c);
  actions.appendChild(editBtn);

  const del = _el('button', {
    className: 'corpus-action-btn delete', textContent: 'Retire',
    title: 'Soft-retire this certification. Future résumés will skip it.',
  });
  del.onclick = () => _deleteCertificationEditor(c.id);
  actions.appendChild(del);

  row.appendChild(actions);
  return row;
}

async function openCertificationAdd() {
  if (!currentUser) return;
  const values = await openFormModal({
    title: 'Add certification',
    subtitle: 'A professional certification the résumé can surface.',
    submitLabel: 'Add certification',
    fields: [
      { name: 'name', label: 'Certification', type: 'text', required: true, placeholder: 'e.g. AWS Certified Solutions Architect' },
      { name: 'issuer', label: 'Issuer (optional)', type: 'text' },
      { name: 'issued', label: 'Issued (optional)', type: 'text', placeholder: 'YYYY or YYYY-MM' },
      { name: 'expires', label: 'Expires (optional)', type: 'text', placeholder: 'YYYY or YYYY-MM' },
    ],
  });
  if (!values) return;
  const name = (values.name || '').trim();
  if (!name) { _toast('Certification name cannot be empty.', true); return; }
  try {
    const res = await fetch(
      `/api/users/${encodeURIComponent(currentUser)}/certifications`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          issuer: (values.issuer || '').trim() || null,
          issued: (values.issued || '').trim() || null,
          expires: (values.expires || '').trim() || null,
        }) },
    );
    if (res.ok) refreshCertificationsEditor();
    else {
      const d = await res.json().catch(() => ({}));
      _toast(d.error || 'Could not add certification.', true);
    }
  } catch { _toast('Network error.', true); }
}

async function openCertificationEdit(c) {
  const values = await openFormModal({
    title: 'Edit certification',
    submitLabel: 'Save',
    fields: [
      { name: 'name', label: 'Certification', type: 'text', required: true, defaultValue: c.name },
      { name: 'issuer', label: 'Issuer (optional)', type: 'text', defaultValue: c.issuer || '' },
      { name: 'issued', label: 'Issued (optional)', type: 'text', defaultValue: c.issued || '' },
      { name: 'expires', label: 'Expires (optional)', type: 'text', defaultValue: c.expires || '' },
    ],
  });
  if (!values) return;
  const name = (values.name || '').trim();
  if (!name) { _toast('Certification name cannot be empty.', true); return; }
  try {
    await _putJson(`/api/certifications/${c.id}`, {
      name,
      issuer: (values.issuer || '').trim() || null,
      issued: (values.issued || '').trim() || null,
      expires: (values.expires || '').trim() || null,
    });
    refreshCertificationsEditor();
  } catch (err) { _toast('Could not save: ' + err.message, true); }
}

async function _deleteCertificationEditor(id) {
  if (!confirm('Retire this certification?\n\nFuture résumés will skip it. '
               + 'You can\'t undo from here.')) return;
  try {
    await _deleteJson(`/api/certifications/${id}`);
    refreshCertificationsEditor();
  } catch (e) { _toast('Could not retire: ' + e.message, true); }
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
  delBtn.onclick = () => _deleteExperienceSummary(expId, v.id, delBtn);
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

async function _deleteExperienceSummary(expId, id, triggerEl) {
  const ok = await cbConfirm(
    'Past applications that used it still reference it; future Compose steps '
      + "will skip it. You can't undo from here.",
    { title: 'Retire this role intro?', confirmLabel: 'Retire', triggerEl },
  );
  if (!ok) return;
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
  // Scroll preservation (feat/ux-busy-states-and-hydration) — the owner's
  // "accepting a bullet scrolls me to the top" report traces to THIS reload
  // path: accept/retire/restore call _reloadCorpusCard → here. The card body
  // briefly shrinks to a one-line "Loading…" placeholder mid-reload, which
  // can shift everything below it and clamp window scroll. Same
  // capture/restore idiom as loadComposition() / refreshCorpus().
  const _scrollY = _captureScrollY();
  _setLoadingPlaceholder(body, 'Loading…');
  let res;
  const q = _corpusShowRetired ? '?include_retired=1' : '';
  try {
    res = await fetch(`/api/experiences/${experienceId}${q}`);
  } catch (e) {
    _setLoadingPlaceholder(body, 'Network error.');
    _restoreScrollY(_scrollY);
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(body, 'Failed to load.');
    _restoreScrollY(_scrollY);
    return;
  }
  _renderCorpusDetail(body, await res.json());
  _restoreScrollY(_scrollY);
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
      textContent: 'Accept all pending',
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
  const retire = _el('button', { className: 'cb-btn cb-bg-orange', textContent: 'Soft-retire experience' });
  retire.onclick = () => deleteExperience(expId, retire);
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
  const addBtn = _el('button', { className: 'corpus-action-btn', textContent: '+ Add title' });
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
    textContent: title.is_official ? 'Official' : 'Alt',
  }));
  if (title.is_pending_review) {
    row.appendChild(_el('span', { className: 'corpus-row-flag pending', textContent: 'Pending' }));
  }
  if (retired) {
    row.appendChild(_el('span', { className: 'corpus-row-flag retired', textContent: 'Retired' }));
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
    const restore = _el('button', { className: 'corpus-action-btn', textContent: 'Restore' });
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
    const accept = _el('button', { className: 'corpus-action-btn', textContent: 'Accept' });
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
    const setOfficial = _el('button', { className: 'corpus-action-btn', textContent: 'Set official' });
    setOfficial.onclick = async () => {
      try {
        await _putJson(`/api/experience-titles/${title.id}`, { is_official: true });
        await _reloadCorpusCard(expId);
        _toast('Promoted to official');
      } catch (e) { _toast('Failed: ' + e.message, true); }
    };
    actions.appendChild(setOfficial);
  }
  const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'Retire' });
  del.onclick = async () => {
    const ok = await cbConfirm(
      'It is hidden unless you tick "Show retired", and won’t be used in new résumés.',
      { title: 'Retire this title?', confirmLabel: 'Retire', triggerEl: del },
    );
    if (!ok) return;
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
  const addBtn = _el('button', { className: 'corpus-action-btn', textContent: '+ Add bullet' });
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
    textContent: bullet.has_outcome ? 'Outcome' : 'No outcome',
  });
  flag.title = bullet.has_outcome
    ? 'A numeric outcome was detected (count, %, currency, duration).'
    : 'No measurable outcome — consider adding one.';
  row.appendChild(flag);
  if (bullet.is_pending_review) {
    row.appendChild(_el('span', { className: 'corpus-row-flag pending', textContent: 'Pending' }));
  }
  if (retired) {
    row.appendChild(_el('span', { className: 'corpus-row-flag retired', textContent: 'Retired' }));
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
    const restore = _el('button', { className: 'corpus-action-btn', textContent: 'Restore' });
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
    const accept = _el('button', { className: 'corpus-action-btn', textContent: 'Accept' });
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
  const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'Retire' });
  del.onclick = async () => {
    const ok = await cbConfirm(
      'It is hidden unless you tick "Show retired", and won’t appear in new résumés.',
      { title: 'Retire this bullet?', confirmLabel: 'Retire', triggerEl: del },
    );
    if (!ok) return;
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
    // The collapsed card header (company / title / dates) is rendered from a
    // separate list fetch and doesn't auto-follow this field-level PUT — a
    // company/date edit inside the expanded body used to leave the header
    // showing stale text until a full page reload. Same refresh
    // `_reloadCorpusCard` already uses after title/bullet edits.
    await refreshCorpusSummaryFor(expId);
    _toast(`${field} saved`);
  } catch (e) {
    _toast(`Save failed: ${e.message}`, true);
  }
}

async function _addTitlePrompt(expId) {
  const result = await openFormModal({
    title: 'Add title',
    subtitle: 'Add an alternate experience title.',
    submitLabel: 'Add title',
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
    title: 'Add bullet',
    subtitle: 'Add a canonical bullet to this experience.',
    submitLabel: 'Add bullet',
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
  merge.onclick = () => _doMerge(s.exp_in_corpus.id, s.exp_other.id, merge);
  const keep = _el('button', { className: 'cb-btn', textContent: 'Keep separate' });
  keep.onclick = () => _dismissMerge(s.exp_a_id, s.exp_b_id);
  actions.appendChild(merge);
  actions.appendChild(keep);
  card.appendChild(actions);
  return card;
}

// Merge the source role into the in-corpus target (which keeps its dates).
async function _doMerge(targetId, sourceId, triggerEl) {
  const ok = await cbConfirm(
    'The extra title becomes an alternate, the bullets combine (duplicates '
      + 'dropped), and the corpus dates are kept.',
    { title: 'Merge these into one role?', confirmLabel: 'Merge', danger: false, triggerEl },
  );
  if (!ok) return;
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

// dec 4(b) (UX Cohesion Epic) — the shared "small button, in flight" idiom:
// disable it, relabel it with a "…"-style pending label, and give it the
// subtle .btn-pending pulse (static/style.css). Several call sites already
// disabled + relabeled by hand (Co2's _fireRecommendSkills fix, the sibling
// _fireSuggestSkills it mirrored) — this centralizes that pattern so the
// pulse ships everywhere consistently instead of being one more manual copy
// per call site. Complements (not replaces) _setBusy: _setBusy is the
// app-wide "don't navigate away" banner for genuinely blocking actions;
// this is the LOCAL affordance on the one button the user actually clicked.
function _setBtnPending(btn, label) {
  if (!btn) return;
  btn.disabled = true;
  btn.classList.add('btn-pending');
  if (label) btn.textContent = label;
}
function _clearBtnPending(btn, label) {
  if (!btn) return;
  btn.disabled = false;
  btn.classList.remove('btn-pending');
  if (label) btn.textContent = label;
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
  const dates = card.querySelector('.corpus-card-dates');
  const meta = card.querySelector('.corpus-card-meta');
  if (company) company.textContent = exp.company;
  if (title) title.textContent = exp.official_title || '(no official title)';
  // Same display convention as _renderCorpusSummary's initial render.
  if (dates) dates.textContent = `${exp.start_date} — ${exp.end_date || 'current'}`;
  if (meta) meta.textContent = `${exp.bullet_count_active} bullets` +
    (exp.bullet_count_pending ? ` · ${exp.bullet_count_pending} pending` : '');
  document.getElementById('corpusCount').textContent =
    `${_corpusExperiences.length} experience${_corpusExperiences.length === 1 ? '' : 's'}`;
}

async function deleteExperience(expId, triggerEl) {
  const ok = await cbConfirm(
    'All its bullets become inactive and it drops out of new résumés. You '
      + 'can restore them via "Show retired".',
    { title: 'Retire this entire experience?', confirmLabel: 'Retire', triggerEl },
  );
  if (!ok) return;
  try {
    const r = await _deleteJson(`/api/experiences/${expId}`);
    _toast(`Retired ${r.retired_bullets} bullet(s)`);
    await refreshCorpus();
  } catch (e) { _toast('Failed: ' + e.message, true); }
}

async function openCorpusAddExperience() {
  const result = await openFormModal({
    title: 'Add experience',
    subtitle: 'New experience for the corpus.',
    submitLabel: 'Add experience',
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

// UX fix (feat/ux-busy-states-and-hydration) — several corpus/compose reloads
// clear a list or card body and rebuild it (loadComposition, refreshCorpus,
// _loadCorpusDetail). The page briefly shrinks to a one-line "Loading…"
// placeholder while that happens, which snaps window scroll back toward the
// top — the "accepting a bullet scrolls me to the top" complaint. Capture the
// scroll position right before the clear, then restore it once the rebuilt
// DOM has landed. Neither the app nor these lists use an internal scroll
// container (verified: .corpus-experience-list has no overflow rule), so
// window scroll is the only position that needs preserving. Restoring the
// same value when nothing moved is a harmless no-op.
function _captureScrollY() { return window.scrollY; }
function _restoreScrollY(y) {
  requestAnimationFrame(() => window.scrollTo(0, y));
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
      className: 'corpus-row-flag outcome', textContent: 'Outcome',
    }));
  }
  if (r.is_promoted_to_bullet) {
    header.appendChild(_el('span', {
      className: 'memory-card-promoted', textContent: 'Promoted',
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
      className: 'corpus-action-btn', textContent: 'Promote to bullet',
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
    title: 'Promote to bullet',
    subtitle: 'Pick which experience this Q&A should become a bullet under.',
    submitLabel: 'Promote',
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
  const ok = await cbConfirm(
    "Accepted items become source-of-truth — the system analyzes them for fit, "
      + 'writes new bullets from them, and builds your résumés on them. One bad '
      + "seed poisons everything downstream. Only accept what you've reviewed and trust.",
    {
      title: 'Accept every pending item across all roles?',
      confirmLabel: 'Accept all',
      danger: false,
      triggerEl: document.getElementById('btnAcceptAllPending'),
    },
  );
  if (!ok) return;
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
          className: 'corpus-row-flag outcome', textContent: 'Outcome',
        }));
      }
      if (b.id === cluster.recommended_keep) {
        meta.appendChild(_el('span', {
          className: 'corpus-row-flag', textContent: 'Recommended',
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

// F-23 — mirror the count into the panel-header summary too, so the
// applications panel still reads as a short summary while it's collapsed.
function _setApplicationsCount(text) {
  const countEl = document.getElementById('applicationsCount');
  const headerEl = document.getElementById('applicationsHeaderCount');
  if (countEl) countEl.textContent = text;
  if (headerEl) headerEl.textContent = text;
}

async function refreshApplications() {
  const list = document.getElementById('applicationsList');
  if (!list) return;
  if (!currentUser) {
    _setLoadingPlaceholder(list, 'Select a user to view their applications.');
    _setApplicationsCount('0 applications');
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
    _setApplicationsCount('0 applications');
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load applications.');
    return;
  }
  const apps = await res.json().catch(() => []);
  if (_needsOnboarding(res, apps)) {
    _setApplicationsCount('0 applications');
    _renderCorpusEmptyCTA(list, 'No applications yet. Add your résumé in the '
      + 'Career corpus tab, then analyze a job description.');
    return;
  }
  if (apps.length === 0 && statusFilter) {
    // Distinguish "filtered everything out" from "no applications yet" so
    // the empty-state copy doesn't mislead.
    _setApplicationsCount('0 applications');
    _setLoadingPlaceholder(list, 'No applications with this status.');
    return;
  }
  _renderApplicationsList(apps);
}

function _renderApplicationsList(apps) {
  const list = document.getElementById('applicationsList');
  _clearChildren(list);
  _setApplicationsCount(`${apps.length} application${apps.length === 1 ? '' : 's'}`);
  if (apps.length === 0) {
    _setLoadingPlaceholder(list, 'No applications yet. Analyze a JD below to start one.');
    return;
  }
  apps.forEach(a => list.appendChild(_renderApplicationCard(a)));
}

// dec 7 (G7, UX Cohesion Epic) — the compact roster card: ONE summary line
// (title/company) + ONE meta line (status · pending-review count · date).
// Everything this card used to render directly — iteration count, the
// status-transition row (Mark submitted / Got interview / …), and the
// retire/restore admin row — moved into the expanded detail modal
// (_showApplicationDetail, already opened on card click below), alongside
// the JD snippet + per-run status that modal now ALSO surfaces for the
// first time. A roster of 10+ applications used to be 10+ small multi-row
// cards each carrying its own button rows; it's now a dense two-line list.
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
    textContent: _toSentence((chipStatus === 'submitted' ? 'no response' : chipStatus).replace('_', ' ')),
  }));
  if (retired) {
    meta.appendChild(_el('span', { className: 'app-status-chip status-retired', textContent: 'Retired' }));
  }
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

  card.onclick = () => _showApplicationDetail(app.id);
  return card;
}

// dec 7 — the status-transition row, now rendered INTO the expanded detail
// modal (#appDetailStatusActions) rather than directly on the compact card.
// Same funnel logic as before (B.8 Part 1): draft → "Mark submitted";
// submitted → the three outcome buttons; interview/rejected/withdrawn is
// terminal (data-model decision 2026-06-10), so no further actions render.
// Re-renders the modal's own detail (not the whole list) on success so the
// modal reflects the new status without a jarring close; refreshApplications()
// still runs so the roster behind it stays in sync.
// `container` is the modal's own #appDetailStatusActions div (already
// carries the .outcome-action-row class in templates/index.html) — this
// populates it in place rather than nesting another wrapper.
function _renderAppDetailStatusActions(container, app) {
  const actions = app.status === 'draft'
    ? [{ label: 'Mark submitted', status: 'submitted' }]
    : app.status === 'submitted'
      ? [
          { label: 'Got Interview', status: 'interview' },
          { label: 'Got Rejection', status: 'rejected' },
          { label: 'Withdrew', status: 'withdrawn' },
        ]
      : [];
  actions.forEach(({ label, status }) => {
    const btn = _el('button', { className: 'outcome-btn', textContent: label });
    btn.addEventListener('click', async () => {
      if (await _putApplicationStatus(app.id, status)) {
        refreshApplications();
        _showApplicationDetail(app.id);
      }
    });
    container.appendChild(btn);
  });
}

// dec 7 — retire/restore, now rendered INTO the expanded detail modal
// (#appDetailAdminRow, already carries .application-admin-row) rather than
// directly on the compact card. Same in-place-populate shape as above.
function _renderAppDetailAdminRow(container, app) {
  const retired = app.is_active === false;
  if (retired) {
    const restore = _el('button', { className: 'app-admin-btn', textContent: 'Restore' });
    restore.addEventListener('click', async () => {
      if (await _setApplicationRetired(app.id, false)) {
        refreshApplications();
        _showApplicationDetail(app.id);
      }
    });
    container.appendChild(restore);
  } else {
    const retire = _el('button', { className: 'app-admin-btn retire', textContent: 'Retire' });
    retire.addEventListener('click', async () => {
      const ok = await cbConfirm(
        'It is hidden unless you tick "Show retired". Its iteration history is kept.',
        { title: 'Retire this application?', confirmLabel: 'Retire', triggerEl: retire },
      );
      if (!ok) return;
      if (await _setApplicationRetired(app.id, true)) {
        refreshApplications();
        _showApplicationDetail(app.id);
      }
    });
    container.appendChild(retire);
  }
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
    textContent: _toSentence(detail.status || 'draft'),
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

  // dec 7 (UX Cohesion Epic) — JD snippet, collapsed by default. New: the
  // roster never surfaced the JD text anywhere before the compact-card
  // redesign moved detail here.
  const jdDetails = document.getElementById('appDetailJDDetails');
  const jdEl = document.getElementById('appDetailJD');
  if (jdDetails && jdEl) {
    _clearChildren(jdEl);
    if (detail.jd_text && detail.jd_text.trim()) {
      jdDetails.style.display = '';
      jdEl.textContent = detail.jd_text;
    } else {
      jdDetails.style.display = 'none';
    }
  }

  // dec 7 — per-run status. ats_roundtrip_status is the closest thing to a
  // "score" this route returns (no separate scoring concept exists on
  // ApplicationRun); shown per iteration alongside what each run produced.
  const scoresEl = document.getElementById('appDetailScores');
  if (scoresEl) {
    _clearChildren(scoresEl);
    (detail.runs || []).forEach(r => {
      const parts = [`Iteration ${r.iteration}`];
      if (r.has_resume) parts.push('résumé');
      if (r.has_cover_letter) parts.push('cover letter');
      if (r.ats_roundtrip_status) parts.push(`ATS: ${r.ats_roundtrip_status}`);
      scoresEl.appendChild(_el('div', {
        className: 'app-detail-score-row',
        textContent: parts.join(' · '),
      }));
    });
  }

  // dec 7 — status-transition + retire/restore actions, moved off the
  // compact card. Rebuilt fresh each open/refresh so they always reflect
  // the CURRENT status/is_active rather than the state at click-time.
  const statusActionsEl = document.getElementById('appDetailStatusActions');
  if (statusActionsEl) {
    _clearChildren(statusActionsEl);
    _renderAppDetailStatusActions(statusActionsEl, detail);
  }
  const adminRowEl = document.getElementById('appDetailAdminRow');
  if (adminRowEl) {
    _clearChildren(adminRowEl);
    _renderAppDetailAdminRow(adminRowEl, detail);
  }

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
  // F-09: conservative reset — the resume payload doesn't say whether this
  // context carries a frozen approved_composition, so Step 5 shows the legacy
  // copy until the user re-freezes via Compose's Save-and-continue. Never
  // claims determinism it can't verify.
  _compositionFrozen = false;
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

  // Full hydration on resume (feat/ux-busy-states-and-hydration, Option A) —
  // the backend now ALWAYS merges the Step-1/2/3 hydration block into the
  // Step-6 resume_state when the context file has it (see
  // blueprints/applications.py::_build_resume_state /
  // _pre_generate_hydration), so back-navigation from a resumed Step 6 shows
  // populated earlier steps instead of blanks. Mirrors
  // _resumeIntoPreGenerateStep's own rendering below, applied to the SAME
  // rs fields, without touching _wizardStep (stays on 6).
  if (rs.analysis) {
    _renderAnalysis({ analysis: rs.analysis, deterministic: rs.deterministic || {} });
    document.getElementById('analysisPending')?.classList.add('hidden');
    document.getElementById('analysisActions')?.classList.remove('hidden');
  }
  if (rs.clarification_questions) {
    lastClarifyQuestions = rs.clarification_questions;
    _renderClarifyQuestions(lastClarifyQuestions, '');
    const answers = rs.clarifications || {};
    document.querySelectorAll('#clarifyQuestions .clarify-question').forEach(el => {
      const qid = el.getAttribute('data-qid');
      const ta = el.querySelector('.clarify-answer');
      if (qid && ta && answers[qid]) ta.value = answers[qid];
    });
  }
  // Compose (Step 3): only hydrate when the saved context actually reached
  // compose (`has_composition` — composition_overrides / llm_recommendations
  // were present), the same gate the backend uses to pick target_step===3 in
  // the pre-generate branch. loadComposition() reads the PERSISTED
  // has_draft/has_gap_fill/has_recommendation flags from the live
  // /composition GET, so its own auto-fire guards apply exactly as they
  // would on a fresh Step-3 arrival — an already-drafted summary or gap-fill
  // never re-fires the cascade, and nothing saved is clobbered. Skipping the
  // call entirely when compose was never reached avoids firing that cascade
  // as a side effect of just viewing a downloaded résumé.
  if (rs.has_composition) loadComposition();

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
    textContent: owned ? 'Yours' : 'Bundled',
  }));
  if (p.is_default) {
    meta.appendChild(_el('span', { className: 'persona-card-default', textContent: 'Default' }));
  }
  meta.appendChild(_el('span', { className: 'persona-card-path', textContent: p.path }));
  card.appendChild(meta);

  const actions = _el('div', { className: 'persona-card-actions' });
  const dl = _el('button', { className: 'corpus-action-btn', textContent: 'Download' });
  dl.onclick = () => window.open(`/api/personas/${p.id}/download`, '_blank');
  actions.appendChild(dl);

  const prev = _el('button', {
    className: 'corpus-action-btn', textContent: 'Open preview',
  });
  prev.onclick = () => _previewPersonaWithResume(p.id, p.name);
  actions.appendChild(prev);

  if (owned) {
    const rename = _el('button', { className: 'corpus-action-btn', textContent: 'Rename' });
    rename.onclick = () => _renamePersona(p.id, p.name);
    actions.appendChild(rename);

    // Wave 2 recruiter tier (UX review F-16) — the smallest honest fix for
    // "house templates are per-candidate": a one-click copy into another
    // candidate's own templates instead of re-uploading the .docx by hand.
    const copyBtn = _el('button', { className: 'corpus-action-btn', textContent: 'Copy to candidate' });
    copyBtn.onclick = () => _copyPersonaToCandidate(p.id, p.name);
    actions.appendChild(copyBtn);

    const del = _el('button', { className: 'corpus-action-btn delete', textContent: 'Delete' });
    del.onclick = () => _deletePersona(p.id, p.name, del);
    actions.appendChild(del);
  }
  card.appendChild(actions);
  return card;
}

async function _copyPersonaToCandidate(id, name) {
  let users;
  try {
    const res = await fetch('/api/users');
    users = (await res.json()).filter(u => u !== currentUser);
  } catch {
    _toast('Could not load the candidate list.', true);
    return;
  }
  if (users.length === 0) {
    _toast('No other candidates to copy to yet.', true);
    return;
  }
  const result = await openFormModal({
    title: 'Copy to candidate',
    subtitle: `Copy "${name}" into another candidate's own templates. The original is untouched.`,
    submitLabel: 'Copy',
    fields: [{
      name: 'username',
      label: 'Candidate',
      type: 'select',
      options: users.map(u => ({ value: u, label: u })),
    }],
  });
  if (!result) return;
  try {
    const copied = await _postJson(`/api/personas/${id}/copy`, { username: result.username });
    _toast(`Copied to ${result.username}`);
    if (currentUser === result.username) await _loadOwnedPersonas();
    return copied;
  } catch (e) {
    _toast('Copy failed: ' + e.message, true);
  }
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

async function _deletePersona(id, name, triggerEl) {
  const ok = await cbConfirm(
    'The .docx file is removed from disk.',
    { title: `Delete ${name}?`, confirmLabel: 'Delete', triggerEl },
  );
  if (!ok) return;
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
    // companion_warning: the .docx uploaded fine but its live-preview
    // companion (.html/.css) failed to generate — surface it instead of
    // silently previewing as Classic forever (walkthrough residuals item 3).
    const body = await res.json().catch(() => ({}));
    _toast(body.companion_warning ? `Uploaded — ${body.companion_warning}` : 'Uploaded');
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
  // Reveal the "Start new tailoring" action alongside the rail.
  document.getElementById('wizardRailActions')?.classList.remove('hidden');
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
  if (step === 5) _renderGenerateStepCopy();
  // PX-22: record a history entry for this step change, UNLESS this call is the
  // popstate restore itself (which must not re-push, or Back/Forward would stack).
  if (!(opts && opts.fromHistory)) _wizardPushHistory(step);
}

// F-09 (2026-07 UX review) — Step 5's copy is state-aware: honest about which
// path Generate will actually take. When _compositionFrozen is true (Compose's
// Save-and-continue froze an approved_composition this session), the résumé
// body assembles deterministically from that exact content — no résumé-body
// LLM call (generation.py._frozen_composition / _assemble_from_frozen_
// composition). Otherwise (no freeze yet — e.g. the user jumped to Step 5 via
// the rail without going through Compose) Generate still runs the real LLM
// path, so the copy must NOT claim determinism. Toggled on every entry to
// Step 5 (wizardGoTo) so a mid-session freeze/un-freeze is always reflected.
function _renderGenerateStepCopy() {
  const legacy = document.getElementById('generateStepCopyLegacy');
  const frozen = document.getElementById('generateStepCopyFrozen');
  if (legacy) legacy.classList.toggle('hidden', _compositionFrozen);
  if (frozen) frozen.classList.toggle('hidden', !_compositionFrozen);
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
// F-09 (2026-07 UX review) — whether Compose's "Save and continue" froze an
// approved_composition THIS session (career_corpus context + freeze:true
// succeeded — set in saveCompositionThenNext). This is exactly the predicate
// generation.py's _frozen_composition() gates the deterministic-assemble path
// on, so Step 5's copy mirrors it: true only after a real freeze; reset to
// false at each fresh analysis (a legacy/non-corpus context never freezes, so
// it never claims the deterministic-assembly copy). See _renderGenerateStepCopy.
let _compositionFrozen = false;
// Phase 4 — when a refinement loops the user back to Compose (corpus mode has no
// résumé-body LLM to re-run), this holds their note so loadComposition can render
// an explaining banner until dismissed. Null = no pending loop-back.
let _composeLoopbackNote = null;
// Item (a) — the ONE scoped bullet/summary proposal /draft-refinement returned
// for the pending loop-back note, or null when the model couldn't scope one
// (the plain loop-back banner renders instead). Cleared together with
// _composeLoopbackNote on Accept/Retire.
let _composeRefinementProposal = null;
// Generation-experience re-architecture — which application we've already
// auto-fired the summary draft for, so a legitimately-empty draft (no JD facts)
// can't re-loop the Sonnet call on every re-render. Reset when the app changes.
let _draftSummaryFiredForApp = null;
// Phase 3 — which application we've already auto-fired the gap-fill draft for.
// Same latch as the summary: a legitimately-empty draft (no uncovered
// requirements) can't re-loop the Sonnet call on every re-render. The server
// has_gap_fill (key presence) is the durable belt to this session-only latch.
let _gapFillFiredForApp = null;
// feat/regenerate-gap-fill — the current application's durably-retired gap-fill
// proposal keys (composition_overrides.retired_gap_fill_keys), mirrored client-
// side: seeded from the GET response on every loadComposition() pass, pushed to
// optimistically on Retire, and re-sent on every _collectCompositionState() save
// (the wholesale-rebuild clobber invariant — see hardening.ContextSet). The
// server is the durable source of truth (gap-fill-decide writes it directly);
// this mirror only exists so a save between decides doesn't drop it.
let _retiredGapFillKeys = [];
// B.4 — whether the "Add role intros" toggle is on for the loaded application.
let _composeUseRoleIntros = false;

// Test-observability: count of in-flight background reloads that will re-enter
// loadComposition() (auto-cascade draft/recommend + user-action pin/accept/etc).
// Reflected as `data-compose-bg-pending` on #composeList so
// WizardComposePage._wait_settled can gate on "terminal render present AND no
// reload pending" instead of a timing heuristic (the Compose flaky-class fix).
// LOAD-BEARING invariant: each reload-firing call site increments as its FIRST
// synchronous statement (before any await) so the attribute is present before
// loadComposition re-sets `data-compose-ready` at the end of the firing pass —
// a firing pass therefore never looks terminal — and decrements in a `finally`
// so a failed/rejected POST still balances (no stuck attribute → no hang).
// The attribute is ABSENT at zero (the `:not([data-compose-bg-pending])`
// selector depends on that); it is never left as `data-compose-bg-pending="0"`.
let _composeBgReloads = 0;
function _markComposeBgReload(delta) {
  _composeBgReloads = Math.max(0, _composeBgReloads + delta);
  const list = document.getElementById('composeList');
  if (!list) return;
  if (_composeBgReloads > 0) list.setAttribute('data-compose-bg-pending', '1');
  else list.removeAttribute('data-compose-bg-pending');
  // UX fix (feat/ux-busy-states-and-hydration) — the visible counterpart to
  // the test-only attribute above: same counter, same increments/decrements,
  // so the chip and the UX settle gate can never disagree about "is a
  // background reload in flight". Purely presentational — no new state.
  const chip = document.getElementById('composeBgChip');
  if (chip) chip.classList.toggle('hidden', _composeBgReloads === 0);
}

async function loadComposition() {
  const list = document.getElementById('composeList');
  if (!list) return;
  // Scroll preservation (feat/ux-busy-states-and-hydration) — every
  // accept/deny/retire/pin in Compose re-enters this function, which clears
  // + rebuilds #composeList; the transient "Loading…"/error placeholders
  // briefly shrink the page and snap window scroll back toward the top.
  // Capture the position now and restore it (see _restoreScrollY calls
  // below) on every exit path once that path's DOM has landed.
  const _scrollY = _captureScrollY();
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
    _restoreScrollY(_scrollY);
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
    _restoreScrollY(_scrollY);
    return;
  }
  if (!res.ok) {
    _setLoadingPlaceholder(list, 'Failed to load composition.');
    _restoreScrollY(_scrollY);
    return;
  }
  const data = await res.json();
  // feat/regenerate-gap-fill — reseed the durable retired-keys mirror from the
  // server on every load (composition_overrides.retired_gap_fill_keys), so a
  // fresh page load / away-and-back reload starts from the persisted truth
  // rather than whatever this session happened to accumulate.
  _retiredGapFillKeys = Array.isArray(data.retired_gap_fill_keys)
    ? data.retired_gap_fill_keys.slice() : [];
  _clearChildren(list);
  // Phase 4 — a refinement in corpus mode loops back here (no résumé-body LLM to
  // re-run); render an explaining banner from the flag so it survives the
  // auto-recommend re-render cascade until the user dismisses it.
  if (_composeLoopbackNote != null) list.appendChild(_renderComposeLoopbackBanner(data));
  // β.6c — Positioning card renders first, above the experience cards.
  // Shows the candidate's SummaryItem variants with the recommendation
  // (if any) flagged and the user's pin (if any) marking the chosen one.
  // Auto-fires recommend-summary in the background when there's no
  // recommendation yet and the candidate has 2+ variants.
  const summary = data.summary || {};
  // Positioning card is ALWAYS present in Compose — it authors the tailored
  // 2-sentence summary (D2). Renders the editable draft + any saved variants.
  // Always-present also keeps the draft textarea available so it rides along on
  // every composition save (the POST rebuilds overrides wholesale — an absent
  // textarea would drop a persisted draft).
  list.appendChild(_renderPositioningCard(summary));
  // D2 — auto-author the summary once on arrival: draft the 2-sentence
  // positioning paragraph (Sonnet) when none exists yet, else opportunistically
  // recommend a saved variant. One background call per pass so the re-render
  // cascade converges; the draft fires at most once per application.
  // Tracks whether a ctx-writing background call (summary draft/recommend, skills
  // recommend) fires THIS pass. Gap-fill defers until none does, so two routes
  // never read-modify-write the same context file at once (the clobber that would
  // drop summary_text / recommendations).
  let bgDraftFiring = false;
  if (!summary.has_draft && _draftSummaryFiredForApp !== _composeApplicationId) {
    _draftSummaryFiredForApp = _composeApplicationId;
    bgDraftFiring = true;
    _fireDraftSummary(false);
  } else if (!summary.has_recommendation && (summary.variants || []).length > 1) {
    bgDraftFiring = true;
    _fireRecommendSummary();
  }
  // B.5 — Skills card. Candidate-level (like Positioning), rendered above the
  // experience cards. Surfaces the curated/ordered skills with pin/drop +
  // "Tailor"/"Suggest" actions and a pending-review lane. Auto-fires
  // recommend-skills once when there's no ordering yet and 2+ skills exist.
  const skills = data.skills || {};
  if ((skills.items || []).length > 0 || (skills.pending || []).length > 0) {
    list.appendChild(_renderSkillsCard(skills));
    if (!skills.has_recommendation && (skills.items || []).length > 1) {
      bgDraftFiring = true;
      _fireRecommendSkills();
    }
  }
  if (!data.experiences || data.experiences.length === 0) {
    _setLoadingPlaceholder(list, 'No corpus experiences to rank.');
    _restoreScrollY(_scrollY);
    return;
  }
  // B.4 — "Add role intros" application-level toggle + per-role pickers inside
  // each experience card. The toggle is the explicit opt-in: when off (default)
  // no role intro reaches the résumé and the generate prompt is byte-identical.
  _composeUseRoleIntros = !!data.use_experience_summaries;
  const anyRoleVariants = (data.experiences || []).some(
    e => ((e.summary || {}).variants || []).length > 0);
  if (anyRoleVariants) list.appendChild(_renderRoleIntrosToggle(_composeUseRoleIntros));
  // feat/regenerate-gap-fill — the manual Regenerate control for the per-role
  // gap-fill lanes rendered inside each experience card below. Always shown
  // (once experiences exist): a retired proposal never re-auto-drafts (the
  // once-only auto-fire latch), so a stalled zero-suggestion state still needs
  // an explicit way to check again.
  list.appendChild(_renderGapFillControls(data));
  data.experiences.forEach(exp => list.appendChild(_renderComposeCard(exp)));
  // Phase 3 — auto-author gap-fill bullets once on arrival (D2): grounded
  // proposals for JD requirements the corpus doesn't cover. DEFERRED to a pass
  // where no other background draft/recommend is firing (bgDraftFiring), because
  // each does a read-modify-write on the SAME context file — firing gap-fill
  // concurrently would clobber summary_text / recommendations. The convergence
  // cascade fires it a pass later; has_gap_fill (key presence) then flips true
  // (even with zero proposals) so it fires at most once and never re-loops.
  if (!bgDraftFiring && !data.has_gap_fill && _gapFillFiredForApp !== _composeApplicationId) {
    _gapFillFiredForApp = _composeApplicationId;
    _fireDraftGapFill();
  }
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
  _restoreScrollY(_scrollY);
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

// D4 (generation-experience re-architecture, item (b) — "in-app edits ARE
// the document"): wire a debounced live-preview refresh on #resumePreview /
// #coverLetterPreview. Before this, the styled Step-6 iframe only picked up
// an edit AFTER it was explicitly saved (the "Use edits as baseline" gate
// before refine/iterate) — so a typed edit + a straight-to-Download click
// would download the NEW text while the visible preview still showed the
// OLD one. /api/download-edited already reads the editor directly and
// writes nothing; /api/applications/<id>/preview-edited is its preview-side
// twin (content in, rendered HTML out, nothing persisted) — this listener
// is the only caller. The existing edit-detection modal / /api/save-edits
// path (persistence) is untouched: this is purely a display refresh.
const _liveEditPreviewTimers = {};
function _wireLiveEditPreview(editorId, docType, frameId) {
  const editor = document.getElementById(editorId);
  if (!editor) return;
  editor.addEventListener('input', () => {
    if (_composeApplicationId == null) return;
    clearTimeout(_liveEditPreviewTimers[editorId]);
    _liveEditPreviewTimers[editorId] = setTimeout(
      () => _refreshLiveEditPreview(editorId, docType, frameId),
      300,
    );
  });
}

async function _refreshLiveEditPreview(editorId, docType, frameId) {
  if (_composeApplicationId == null) return;
  const content = (_readEditorText(editorId) || '').trim();
  const frame = document.getElementById(frameId);
  if (!content || !frame) return;
  try {
    const body = { content, type: docType };
    const sel = _readSelectedPersonaId();
    if (sel != null) body.template_id = sel;
    const res = await fetch(`/api/applications/${_composeApplicationId}/preview-edited`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) return;  // non-blocking — the last-loaded preview stays up
    const data = await res.json();
    if (typeof data.html !== 'string') return;
    _wirePreviewPageCount(frame, editorId === 'resumePreview' ? 'outputPreviewPageInfo' : 'coverPreviewPageInfo');
    frame.srcdoc = data.html;
  } catch {
    // Non-blocking — this is a display nicety; Download still reads the
    // editor directly and is unaffected by a failed live-preview refresh.
  }
}

// β.6c — fire recommend-summary in the background. Idempotent on the
// server (it overwrites llm_summary_recommendation on each call). The
// route returns the same shape as a fresh composition refresh, so we
// reload composition after to surface the recommendation chips.
async function _fireRecommendSummary() {
  if (_composeApplicationId == null || !lastContextPath) return;
  _markComposeBgReload(1);
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
  } finally {
    _markComposeBgReload(-1);
  }
}

// Generation-experience re-architecture — draft/redraft the 2-sentence
// positioning summary (Sonnet) at Compose, then refresh so the editable draft
// shows. `force` just repaints the placeholder for an explicit Regenerate; the
// route always overwrites composition_overrides.summary_text.
async function _fireDraftSummary(force, btn) {
  if (_composeApplicationId == null || !lastContextPath) return;
  if (force) {
    const el = document.getElementById('composeSummaryDraft');
    if (el) el.placeholder = 'Drafting your summary…';
  }
  // UX fix (feat/ux-busy-states-and-hydration) — the explicit Regenerate
  // click (force=true, `btn` passed) gets visible in-flight feedback on the
  // button itself — same idiom as submitClarifications' btnSubmit.disabled.
  // The silent auto-fire on Compose arrival (force=false, no btn) is
  // unaffected: it already has no button to disable.
  _setBtnPending(btn, 'Regenerating…');
  _markComposeBgReload(1);
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/draft-summary`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) loadComposition();
  } catch {
    // Non-blocking — the user can Regenerate or type their own summary.
  } finally {
    _markComposeBgReload(-1);
    _clearBtnPending(btn, 'Regenerate');
  }
}

// Phase 3 — auto-author gap-fill bullets (Sonnet). Fires once on Compose arrival
// (guarded by _gapFillFiredForApp + the server has_gap_fill flag); reloads so the
// per-role "Suggested for this JD" lanes render.
// feat/regenerate-gap-fill — this same function is ALSO the explicit "Regenerate
// suggestions" trigger (a THIRD context-writing firing path alongside the summary
// draft + skills recommend — serialized through _markComposeBgReload exactly like
// those two). The route always overwrites llm_gap_fill_proposals, filtering out
// anything the user already retired or accepted, so a regenerated draft never
// resurfaces a decided-on proposal. `btn` is the clicked button (present only for
// the explicit trigger); its presence gates in-flight UI feedback + a result
// toast so the silent auto-fire keeps its original non-blocking behavior.
async function _fireDraftGapFill(btn) {
  if (_composeApplicationId == null || !lastContextPath) return;
  _setBtnPending(btn, 'Regenerating…');
  _markComposeBgReload(1);
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/draft-gap-fill`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) {
      if (btn) {
        const body = await res.json().catch(() => ({}));
        const n = (body.proposals || []).length;
        _toast(n
          ? `${n} suggestion${n === 1 ? '' : 's'} to review.`
          : 'No new grounded suggestions found.');
      }
      loadComposition();
    } else if (btn) {
      _toast('Could not regenerate suggestions.', true);
    }
  } catch {
    // Non-blocking on the silent auto-fire — gap-fill is an optional enhancement
    // over the corpus set; the explicit Regenerate surfaces a toast instead.
    if (btn) _toast('Network error regenerating suggestions.', true);
  } finally {
    _markComposeBgReload(-1);
    _clearBtnPending(btn, 'Regenerate suggestions');
  }
}

// feat/regenerate-gap-fill — the always-visible (once experiences exist) control
// row above the per-role "Suggested for this JD" lanes: a live count of what's
// currently proposed across all roles + the manual Regenerate trigger. Gap-fill
// proposals are drafted in ONE global call (not per-role), so the control lives
// once here rather than duplicated on every card.
function _renderGapFillControls(data) {
  const total = (data.experiences || []).reduce(
    (n, e) => n + (e.gap_fill_proposals || []).length, 0);
  const wrap = _el('div', {
    className: 'gap-fill-controls',
    style: 'margin:6px 0 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;',
  });
  wrap.appendChild(_el('span', { className: 'gap-fill-optional-badge', textContent: 'Optional' }));
  wrap.appendChild(_el('span', {
    className: 'edit-hint',
    textContent: total
      ? `${total} suggested bullet${total === 1 ? '' : 's'} below, across your roles.`
      : 'No open gap-fill suggestions right now.',
  }));
  const regen = _el('button', {
    className: 'btn-secondary btn-sm gap-fill-regen', textContent: 'Regenerate suggestions',
  });
  regen.onclick = () => _fireDraftGapFill(regen);
  wrap.appendChild(regen);
  return wrap;
}

// Retire the drafted summary: clear it locally + persist (the empty value drops
// summary_text from composition_overrides on the wholesale rebuild), so the
// frozen doc falls back to the candidate's saved positioning.
async function _retireDraftSummary() {
  const el = document.getElementById('composeSummaryDraft');
  if (el) { el.value = ''; el.dataset.edited = 'false'; }
  try {
    await _postComposition(_collectCompositionState());
    _toast('Summary draft retired — falls back to your saved positioning.');
  } catch (e) {
    _toast('Retire failed: ' + e.message, true);
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
    textContent: 'Your tailored two-sentence summary for this job. Edit it '
      + 'directly, or Regenerate a fresh draft. It freezes when you continue.',
  }));

  // Generation-experience re-architecture — the drafted 2-sentence positioning
  // summary is the primary content of this card (authored ONCE at Compose).
  // Editable; rides along on every composition save via _collectCompositionState.
  const draft = _el('textarea', { className: 'positioning-draft', id: 'composeSummaryDraft' });
  // a11y: the textarea has only a placeholder + an adjacent hint (no <label for>),
  // which axe flags "Form elements must have labels" — name it explicitly.
  draft.setAttribute('aria-label', 'Tailored two-sentence positioning summary');
  draft.rows = 3;
  draft.value = summary.drafted_text || '';
  draft.placeholder = summary.has_draft ? '' : 'Drafting your summary…';
  draft.dataset.edited = summary.drafted_edited ? 'true' : 'false';
  draft.oninput = () => { draft.dataset.edited = 'true'; _scheduleCompositionSave(); };
  card.appendChild(draft);

  const actions = _el('div', {
    className: 'positioning-draft-actions', style: 'margin-top:6px;display:flex;gap:8px',
  });
  const regen = _el('button', {
    className: 'btn-secondary positioning-draft-regen', textContent: 'Regenerate',
  });
  regen.onclick = () => _fireDraftSummary(true, regen);
  actions.appendChild(regen);
  const retire = _el('button', {
    className: 'btn-secondary positioning-draft-retire', textContent: 'Retire',
  });
  retire.title = 'Clear this draft and fall back to your saved positioning';
  retire.onclick = () => _retireDraftSummary();
  actions.appendChild(retire);
  card.appendChild(actions);

  // Optional: pin one of the candidate's saved SummaryItem variants as the
  // source the next Regenerate reframes from.
  const variants = summary.variants || [];
  if (variants.length > 0) {
    card.appendChild(_el('div', {
      className: 'edit-hint', style: 'margin-top:8px',
      textContent: 'Or pin one of your saved summary variants as the source:',
    }));
    variants.forEach(v => card.appendChild(_renderPositioningVariant(v, summary.chosen_id)));
  }
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
  _markComposeBgReload(1);
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/composition`,
      { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ context_path: lastContextPath, ...state }) },
    );
    if (res.ok) loadComposition();
  } catch {
    // Non-blocking
  } finally {
    _markComposeBgReload(-1);
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
  tailorBtn.onclick = () => _fireRecommendSkills(true, tailorBtn);
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
  // dec 6 (UX Cohesion Epic) — collapsible toggle for the bounded skills
  // list (C2 already bounded it with internal scroll; this adds an actual
  // expand/collapse affordance, shared with the Career Corpus tab's
  // equivalent list via the same .corpus-collapsible wrapper).
  const skillListDetails = _el('details', { className: 'corpus-collapsible', open: true });
  skillListDetails.appendChild(_el('summary', { textContent: `Skills (${orderedIds.length})` }));
  skillListDetails.appendChild(skillList);
  card.appendChild(skillListDetails);

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
  text.appendChild(_renderSkillChip(it.name, it.category));
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
async function _fireRecommendSkills(explicit, btn) {
  if (_composeApplicationId == null || !lastContextPath) return;
  _setBtnPending(btn, 'Tailoring…');
  _markComposeBgReload(1);
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
  } finally {
    _markComposeBgReload(-1);
    _clearBtnPending(btn, 'Tailor skills to this JD');
  }
}

// Fire suggest-skills (grounded generator). Proposals land as pending rows;
// reload composition to surface the review lane.
async function _fireSuggestSkills(btn) {
  if (_composeApplicationId == null || !lastContextPath) return;
  _setBtnPending(btn, 'Suggesting…');
  _markComposeBgReload(1);
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
    _markComposeBgReload(-1);
    _clearBtnPending(btn, 'Suggest skills from this JD');
  }
}

function _renderPendingSkillRow(p) {
  const row = _el('div', { className: 'compose-row pending-skill-row' });
  const text = _el('div', { className: 'row-text' });
  text.appendChild(_renderSkillChip(p.name, p.category));
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
// (DELETE → reversible soft-tombstone, dec 6: is_active=0, never
// hard-deleted, so the name keeps suppressing future re-suggestion and
// Restore can un-deny it from the Career Corpus tab's denied lane).
// Reloads composition.
async function _reviewPendingSkill(skillId, approve) {
  _markComposeBgReload(1);
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
  } finally {
    _markComposeBgReload(-1);
  }
}

// Phase 3 — one "Suggested for this JD" gap-fill proposal row (Accept / Retire).
// Mirrors _renderPendingSkillRow. The proposal is transient text keyed by `key`
// until accepted; accept creates a pending Bullet folded into this application's
// composition, retire drops it.
function _renderGapFillRow(expId, p) {
  const row = _el('div', { className: 'compose-row gap-fill-row' });
  row.dataset.key = p.key;
  const text = _el('div', { className: 'row-text' });
  text.appendChild(_el('span', { className: 'gap-fill-text', textContent: p.text }));
  if (p.requirement) {
    text.appendChild(_el('div', {
      className: 'gap-fill-requirement',
      textContent: 'Covers: ' + p.requirement,
      style: 'color:var(--fg-2);font-size:0.85em;margin-top:2px;',
    }));
  }
  row.appendChild(text);
  const meta = _el('div', { className: 'row-meta' });
  const accept = _el('button', {
    className: 'btn-secondary btn-sm gap-fill-accept', textContent: 'Accept',
  });
  accept.onclick = () => _decideGapFill(p.key, 'accept');
  meta.appendChild(accept);
  const retire = _el('button', {
    className: 'btn-secondary btn-sm gap-fill-retire', textContent: 'Retire',
  });
  retire.onclick = () => _decideGapFill(p.key, 'retire');
  meta.appendChild(retire);
  row.appendChild(meta);
  return row;
}

// Accept (creates a pending Bullet + folds it into this application's composition)
// or retire (drops the transient proposal). Reloads composition on success.
async function _decideGapFill(key, decision) {
  if (_composeApplicationId == null || !lastContextPath) return;
  // feat/regenerate-gap-fill — push the retired key into the local mirror
  // BEFORE the request resolves (optimistic, like the DOM updates other autosave
  // paths make first): the server already durably persists the retire directly,
  // but a debounced _scheduleCompositionSave() that happens to fire in the same
  // window resends _collectCompositionState() regardless, so it must already
  // carry this key to avoid the wholesale-rebuild clobber.
  if (decision === 'retire' && !_retiredGapFillKeys.includes(key)) {
    _retiredGapFillKeys.push(key);
  }
  _markComposeBgReload(1);
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/gap-fill-decide`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_path: lastContextPath, key, decision }) },
    );
    if (res.ok) loadComposition();
    else _toast('Could not update the suggested bullet.', true);
  } catch {
    _toast('Network error updating the suggested bullet.', true);
  } finally {
    _markComposeBgReload(-1);
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
  _markComposeBgReload(1);
  try {
    const res = await fetch(
      `/api/applications/${_composeApplicationId}/recommend-experience-summaries`,
      { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ context_path: lastContextPath }) },
    );
    if (res.ok) loadComposition();
  } catch {
    // Non-blocking — Compose still works without the recommendation.
  } finally {
    _markComposeBgReload(-1);
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
  _markComposeBgReload(1);
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
  } finally {
    _markComposeBgReload(-1);
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

  // Bullets split into visible (recommended/pinned/added/accepted-gap-fill) +
  // drawer (rest). Phase 3 — an accepted gap-fill bullet joins the visible set.
  const visible = (exp.bullets || []).filter(
    b => b.recommended || b.pinned || b.added || b.accepted_generated,
  );
  const hidden = (exp.bullets || []).filter(
    b => !(b.recommended || b.pinned || b.added || b.accepted_generated),
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
        textContent: `+ Find more bullets in ${exp.company} (${drawerBullets.length})`,
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

  // Phase 3 — "Suggested for this JD" gap-fill lane: grounded bullet proposals
  // for JD requirements this résumé doesn't yet cover. Accept → a pending Bullet
  // joins this application's composition; Retire → dropped. Mirrors the Skills
  // pending lane. F-13 (2026-07-07): presentation-only "optional" framing — a
  // subdued badge on the title + the hint leads with "Optional — add only what
  // fits" — so the lane reads as suggestions, not a checklist. Per-item Accept/
  // Retire affordances and the data flow underneath are unchanged.
  const gapFill = exp.gap_fill_proposals || [];
  if (gapFill.length) {
    const lane = _el('div', { className: 'gap-fill-lane' });
    lane.appendChild(_el('div', { className: 'compose-exp-section-title' }, [
      document.createTextNode('Suggested for this JD'),
      _el('span', { className: 'gap-fill-optional-badge', textContent: 'Optional' }),
    ]));
    lane.appendChild(_el('div', {
      className: 'edit-hint',
      textContent: 'Optional — add only what fits. Grounded in your experience; '
        + 'accept to add to this résumé, or retire to drop. Accepted bullets are '
        + 'yours to keep or approve into your corpus later.',
    }));
    gapFill.forEach(p => lane.appendChild(_renderGapFillRow(exp.id, p)));
    card.appendChild(lane);
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
      className: 'corpus-row-flag official', textContent: 'Official',
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
    title: 'Add title',
    subtitle: 'Add an alternative title for this experience. It joins your '
      + 'career corpus and becomes selectable for this résumé.',
    submitLabel: 'Add title',
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
  _markComposeBgReload(1);
  try {
    await loadComposition();
  } finally {
    _markComposeBgReload(-1);
  }
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
    textContent: b.pinned ? 'Pinned' : 'Pin',
  });
  const exc = _el('button', {
    className: 'corpus-action-btn delete' + (b.excluded ? ' on' : ''),
    textContent: b.excluded ? 'Excluded' : 'Exclude',
  });
  // Toggle "add" only for non-recommended bullets reached via drawer;
  // recommended/already-added bullets always count as added.
  const addBtn = _el('button', {
    className: 'corpus-action-btn' + (b.added ? ' on' : ''),
    textContent: b.added ? 'Added' : '+ Add',
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
      className: 'corpus-row-flag', textContent: 'Recommended',
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
      className: 'corpus-row-flag outcome', textContent: 'Outcome',
    }));
  }
  if (b.is_pending_review) {
    meta.appendChild(_el('span', {
      className: 'corpus-row-flag pending', textContent: 'Pending',
    }));
    // Walkthrough D3: edit + approve a proposed bullet INLINE in the tailor flow
    // (both persist straight to the corpus via the same routes the Corpus tab
    // uses), so the user never has to leave Compose to keep a proposed change.
    const editBtn = _el('button', {
      className: 'corpus-action-btn', textContent: 'Edit',
    });
    editBtn.onclick = () => _editComposeBullet(b, row);
    const approveBtn = _el('button', {
      className: 'corpus-action-btn', textContent: 'Approve',
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
    title: 'Edit bullet',
    subtitle: 'Edit this proposed bullet. Your change saves to your career corpus.',
    submitLabel: 'Save',
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
    btns[0].textContent = b.pinned ? 'Pinned' : 'Pin';
    btns[0].classList.toggle('on', !!b.pinned);
  }
  if (btns[1]) {
    btns[1].textContent = b.excluded ? 'Excluded' : 'Exclude';
    btns[1].classList.toggle('on', !!b.excluded);
  }
  if (btns[2]) {
    btns[2].textContent = b.added ? 'Added' : '+ Add';
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
  // Phase 3 — accepted gap-fill bullet ids ride along on EVERY save. The POST
  // rebuilds composition_overrides wholesale (and freezes on continue), so an
  // omitted field would drop the accepted bullet from the composition + the
  // frozen snapshot. The accept route seeds them into ctx; the GET re-surfaces
  // them as b.accepted_generated; this re-sends them so the rebuild preserves them.
  const accepted_generated_bullet_ids = [];
  document.querySelectorAll('#composeList .compose-row').forEach(row => {
    const b = row._bulletState;
    if (!b) return;
    if (b.pinned) pinned.push(b.id);
    if (b.excluded) excluded.push(b.id);
    if (b.added) added.push(b.id);
    if (b.accepted_generated) accepted_generated_bullet_ids.push(b.id);
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
  // Generation-experience re-architecture — the drafted 2-sentence positioning
  // summary rides along on every save (the POST rebuilds overrides wholesale, so
  // a bullet/skill save would otherwise clobber it). Absent card → omit (nothing
  // to preserve yet). An empty value intentionally drops it (Retire).
  const draftEl = document.getElementById('composeSummaryDraft');
  const summaryFields = draftEl
    ? { summary_text: draftEl.value.trim(), summary_text_edited: draftEl.dataset.edited === 'true' }
    : {};
  return {
    pinned, excluded, added, bullet_order, pinned_title_ids,
    accepted_generated_bullet_ids,
    // feat/regenerate-gap-fill — the durable retired-proposal key mirror rides
    // along on every save (the POST rebuilds composition_overrides wholesale, so
    // an omitted field would drop a retiral the moment any OTHER save fires).
    retired_gap_fill_keys: _retiredGapFillKeys.slice(),
    // B.4 — per-role intro toggle + picks ride along on every save so a bullet/
    // title save never clobbers them (the POST rebuilds overrides wholesale).
    ..._collectExperienceSummaryState(),
    // B.5 — skill curation (pin/drop/reorder) likewise rides along on every
    // save so it survives a bullet/title/summary save.
    ..._collectSkillState(),
    ...summaryFields,
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
//
// dec 5 (Co5, UX Cohesion Epic) — this used to be silent on success (only
// the failure path toasted), which the owner flagged as "too quiet": a
// background reload-on-save with no perceptible confirmation reads as
// "did that actually save?". The success path now toasts too, using the
// SAME quiet `_toast()` idiom every other save confirmation in the app
// already uses (Title saved / Bullet restored / etc.) — not a new,
// louder mechanism, just no longer silent.
function _scheduleCompositionSave() {
  if (_composeApplicationId == null || !lastContextPath) return;
  if (_composeSaveTimer) clearTimeout(_composeSaveTimer);
  _composeSaveTimer = setTimeout(async () => {
    _composeSaveTimer = null;
    try {
      await _postComposition(_collectCompositionState());
      _toast('Saved');
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
    // Generation-experience re-architecture — Save-and-continue FREEZES the
    // approved composition (the single content contract downstream renders). The
    // debounced autosave omits `freeze`, so only this explicit action snapshots.
    // F-09: only claim the deterministic-assembly copy when the freeze POST
    // actually landed (_postComposition returns false on its no-app/no-context
    // guard — e.g. a degraded resume with no live context file — and throws on
    // HTTP failure, caught below).
    _compositionFrozen = (await _postComposition({ ...state, freeze: true })) === true;
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
  const add = _el('button', { className: 'tag-chip-add', textContent: '+ Tag' });
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
      textContent: source === 'owned' ? 'Mine' : 'Bundled',
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
    // companion_warning: the .docx uploaded fine but its live-preview
    // companion (.html/.css) failed to generate — surface it instead of
    // silently previewing as Classic forever (walkthrough residuals item 3).
    const body = await res.json().catch(() => ({}));
    _toast(body.companion_warning ? `Template uploaded — ${body.companion_warning}` : 'Template uploaded');
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

    titleEl.textContent = opts.title || 'Form';
    subEl.textContent = opts.subtitle || '';
    submit.textContent = opts.submitLabel || 'Save';
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
  const go = _el('button', { className: 'tag-composer-go', textContent: 'Add' });
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
