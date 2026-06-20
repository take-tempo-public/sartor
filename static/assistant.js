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
  const sourcesEl = document.getElementById('assistantSources');
  const btn = document.getElementById('assistantAsk');
  const question = (qEl.value || '').trim();

  // No user gate (7.8c): the assistant's answer is project-global (committed wiki +
  // code), identical for every user, so it's available before any user is selected.
  // The route accepts an empty username and stamps anonymous telemetry.
  if (!question) return;

  const allowDev = document.getElementById('assistantDevMode').checked;
  if (emptyEl) emptyEl.classList.add('hidden');   // first ask retires the empty state
  answerEl.textContent = '';
  if (sourcesEl) sourcesEl.textContent = '';      // clear the prior answer's Sources key
  // Tokens accumulate SILENTLY in #assistantAnswer (no longer a live region, so no
  // per-chunk screen-reader flood). aria-busy marks it loading; the single terminal
  // announcement goes to #assistantStatus and aria-busy is cleared on EVERY path.
  answerEl.setAttribute('aria-busy', 'true');
  statusEl.textContent = 'Thinking…';
  btn.disabled = true;

  try {
    await _consumeSSE(
      '/api/assistant/ask',
      { username: currentUser || '', question, allow_dev: allowDev },
      (eventName, data) => {
        if (eventName === 'chunk') {
          answerEl.textContent += (data && data.text) ? data.text : '';
          statusEl.textContent = '';
        } else if (eventName === 'done') {
          // Re-render the FULL answer once on completion: the server-renumbered text
          // (data.answer) as a constrained markdown subset with clickable [n] cites.
          answerEl.innerHTML = _renderAvatarAnswer(
            (data && typeof data.answer === 'string') ? data.answer : answerEl.textContent,
            data && data.citations
          );
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

// A client-built GitHub blob URL is the ONLY href we ever inject; re-validate the
// prefix the server sent so a malformed/foreign URL can never reach an attribute.
function _safeCiteHref(href) {
  return (typeof href === 'string' && href.indexOf('https://github.com/') === 0) ? href : '';
}

// Re-render the avatar's full answer as a constrained markdown subset (7.8d):
// `inline code`, **bold**, and the numbered [n] citations as clickable GitHub links.
// XSS-safe BY CONSTRUCTION: the answer is escaped FIRST via esc() (app.js), so no raw
// `<`/`>`/`&` from the model or user survives; the only HTML we then introduce is the
// fixed <code>/<strong> tags and an <a> whose href is a server-built, re-validated
// GitHub URL (never model text) and whose link text is the bare number. The body streams
// as plain textContent while loading; this fires once on the `done` event.
function _renderAvatarAnswer(answer, citations) {
  const hrefByN = {};
  (Array.isArray(citations) ? citations : []).forEach(c => {
    const href = c ? _safeCiteHref(c.href) : '';
    if (href) hrefByN[String(c.n)] = href;
  });
  let html = esc(String(answer == null ? '' : answer));
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');        // code first: backticks bound the span
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\[(\d+)\]/g, (m, n) => {
    const href = hrefByN[n];
    return href ? '<a href="' + href + '" target="_blank" rel="noopener">[' + n + ']</a>' : m;
  });
  return html;
}

// Build the numbered, resolving "Sources" key into #assistantSources (7.8d). Each entry
// is "[n] <a>label</a>" linking to the source on GitHub; cited-only, so the footer can't
// overstate grounding. Returns the SHORT announcement for the polite #assistantStatus
// region (the multi-line key would flood a screen reader if announced).
function _renderAssistantSources(done) {
  const box = document.getElementById('assistantSources');
  const cites = (done && Array.isArray(done.citations)) ? done.citations : [];
  if (cites.length === 0) {
    if (box) box.textContent = 'Answered (no sources cited).';
    return 'Answer ready.';
  }
  const parts = cites.map(c => {
    const label = esc(String((c && c.label != null) ? c.label : ''));
    const n = esc(String((c && c.n != null) ? c.n : ''));
    const href = c ? _safeCiteHref(c.href) : '';
    const linked = href ? '<a href="' + href + '" target="_blank" rel="noopener">' + label + '</a>' : label;
    return '[' + n + '] ' + linked;
  });
  const truncated = done.truncated ? ' · context truncated' : '';
  if (box) box.innerHTML = 'Sources: ' + parts.join(' · ') + truncated;
  return 'Answer ready.';
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
