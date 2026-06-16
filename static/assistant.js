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
