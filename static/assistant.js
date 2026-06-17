// Doc-grounded assistant (Sprint 7.5, feat/doc-assistant).
//
// The client for POST /api/assistant/ask: streams a cited answer off the SSE
// response using the shared _consumeSSE helper in app.js, and reuses the global
// currentUser. Deliberately tiny — retrieval, grounding, and citation all happen
// server-side; this only renders the stream.

async function askAssistant() {
  const qEl = document.getElementById('assistantQuestion');
  const answerEl = document.getElementById('assistantAnswer');
  const statusEl = document.getElementById('assistantStatus');
  const btn = document.getElementById('assistantAsk');
  const question = (qEl.value || '').trim();

  if (!currentUser) { alert('Select a user first'); return; }
  if (!question) return;

  const allowDev = document.getElementById('assistantDevMode').checked;
  answerEl.textContent = '';
  statusEl.textContent = 'Thinking…';
  btn.disabled = true;

  try {
    await _consumeSSE(
      '/api/assistant/ask',
      { username: currentUser, question, allow_dev: allowDev },
      (eventName, data) => {
        if (eventName === 'chunk') {
          answerEl.textContent += (data && data.text) ? data.text : '';
          statusEl.textContent = '';
        } else if (eventName === 'done') {
          statusEl.textContent = _renderAssistantSources(data);
        } else if (eventName === 'error') {
          statusEl.textContent = 'Error: ' + ((data && data.error) || 'unknown');
        } else if (eventName === 'http_error') {
          const msg = (data && data.body && data.body.error) || ('HTTP ' + (data && data.status));
          statusEl.textContent = 'Error: ' + msg;
        }
      }
    );
  } catch (err) {
    statusEl.textContent = 'Error: ' + err;
  } finally {
    btn.disabled = false;
  }
}

function _renderAssistantSources(done) {
  if (!done || !Array.isArray(done.citations) || done.citations.length === 0) {
    return 'Answered (no sources cited).';
  }
  const uniq = [...new Set(done.citations)];
  const truncated = done.truncated ? ' · context truncated' : '';
  return 'Sources: ' + uniq.join(', ') + truncated;
}

// Open the assistant modal from the top-bar magnifier (#assistantPill). Mirrors
// openDiagnosticsModal() in app.js for a11y parity — focus-trap over the modal's
// controls, Esc / backdrop / Close all routed through one cleanup(), focus moved
// into the question box on open and restored to the pill on close, plus the pill's
// aria-expanded toggle (it advertises aria-haspopup="dialog"). The .cb-modal CSS
// gives the floating, scrollable overlay; this only wires the open/close behavior.
function openAssistantModal() {
  const modal = document.getElementById('assistantModal');
  if (!modal) return;
  const trigger = document.getElementById('assistantPill');
  const focusable = modal.querySelectorAll('button, input, textarea');

  const cleanup = () => {
    modal.classList.add('hidden');
    modal.removeEventListener('keydown', onKey);
    dismissers.forEach(b => b.removeEventListener('click', cleanup));
    if (trigger && typeof trigger.setAttribute === 'function') {
      trigger.setAttribute('aria-expanded', 'false');
    }
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

  const dismissers = Array.from(modal.querySelectorAll('[data-assistant-dismiss]'));
  dismissers.forEach(b => b.addEventListener('click', cleanup));
  modal.addEventListener('keydown', onKey);
  if (trigger && typeof trigger.setAttribute === 'function') {
    trigger.setAttribute('aria-expanded', 'true');
  }
  modal.classList.remove('hidden');
  const q = document.getElementById('assistantQuestion');
  if (q && typeof q.focus === 'function') q.focus();
}
