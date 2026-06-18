// Doc-grounded assistant (Sprint 7.5, feat/doc-assistant).
//
// The client for POST /api/assistant/ask: streams a cited answer off the SSE
// response using the shared _consumeSSE helper in app.js, and reuses the global
// currentUser. Deliberately tiny — retrieval, grounding, and citation all happen
// server-side; this only renders the stream.

// Transport-failure copy: calm, blame-free, actionable, and deliberately DISTINCT
// from the grounded refusal ("I don't have that in my docs.") — a network error
// must never read as "the docs lack it" when the search never ran. Short, because
// it lands in the polite #assistantStatus region and is read aloud.
const ASSISTANT_TRANSPORT_ERR = 'Something went wrong reaching the assistant. Try again in a moment.';

async function askAssistant() {
  const qEl = document.getElementById('assistantQuestion');
  const answerEl = document.getElementById('assistantAnswer');
  const statusEl = document.getElementById('assistantStatus');
  const emptyEl = document.getElementById('assistantEmptyState');
  const btn = document.getElementById('assistantAsk');
  const question = (qEl.value || '').trim();

  // In-voice, non-blocking, and announced via the polite region (the old blocking
  // alert() was neither dismissable nor cleanly read by assistive tech).
  if (!currentUser) { statusEl.textContent = 'Pick a user first, then ask.'; return; }
  if (!question) return;

  const allowDev = document.getElementById('assistantDevMode').checked;
  if (emptyEl) emptyEl.classList.add('hidden');   // first ask retires the empty state
  answerEl.textContent = '';
  // Tokens accumulate SILENTLY in #assistantAnswer (no longer a live region, so no
  // per-chunk screen-reader flood). aria-busy marks it loading; the single terminal
  // announcement goes to #assistantStatus and aria-busy is cleared on EVERY path.
  answerEl.setAttribute('aria-busy', 'true');
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
          answerEl.setAttribute('aria-busy', 'false');
        } else if (eventName === 'error') {
          console.error('assistant stream error:', data && data.error);
          statusEl.textContent = ASSISTANT_TRANSPORT_ERR;
          answerEl.setAttribute('aria-busy', 'false');
        } else if (eventName === 'http_error') {
          console.error('assistant http error:', data && data.status, data && data.body);
          statusEl.textContent = ASSISTANT_TRANSPORT_ERR;
          answerEl.setAttribute('aria-busy', 'false');
        }
      }
    );
  } catch (err) {
    console.error(err);
    statusEl.textContent = ASSISTANT_TRANSPORT_ERR;
    answerEl.setAttribute('aria-busy', 'false');
  } finally {
    btn.disabled = false;
    answerEl.setAttribute('aria-busy', 'false');   // never leave the node stuck busy
  }
}

function _renderAssistantSources(done) {
  if (!done || !Array.isArray(done.citations) || done.citations.length === 0) {
    return 'Answered (no sources cited).';
  }
  // Strip the wiki [[ ]] double-bracket wrapper for a clean, human-readable list
  // (matches the single-bracket inline citation form the avatar now uses); code
  // citations are bare path:line already.
  const uniq = [...new Set(done.citations)].map(c => c.replace(/^\[\[|\]\]$/g, ''));
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
