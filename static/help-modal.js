// ============================================================================
// Shared help-modal primitive — used by BOTH the wizard (static/app.js) and the
// self-contained diagnostics console (dashboard/templates/dashboard.html).
//
// History: openHelpModal (app.js) and openDashHelp (dashboard.html) were a
// byte-faithful pair; this file is the single extraction (carry-forward ledger
// "Help-opener duplication"). Neither host is an ES module and there is no JS
// build step, so this exposes plain globals on `window`. Authored in ES5 to
// match the dashboard inline JS; app.js may keep ES6 around its wrapper.
//
// LOAD ORDER MATTERS: this must be a classic <script> (no defer/async) that
// runs BEFORE static/app.js and BEFORE the dashboard's inline help IIFE, so the
// globals below exist when those callers run at parse time.
//
// Exposes:
//   window.CB_HELP_SEEN_PREFIX        — the localStorage key prefix.
//   window.cbHelpSeen(id)             — seam read  (storage-safe, false on throw).
//   window.cbMarkHelpSeen(id)         — seam write (storage-safe, no-op on throw).
//   window.cbOpenHelpModal(entry, triggerEl)
//        — opens #helpModal for an ALREADY-RESOLVED { title, body } entry (each
//          page resolves it from its own registry). Esc closes, Tab focus-trap,
//          [data-help-dismiss] click-away, aria-expanded toggle, focus restored
//          to triggerEl (null-safe). No-op if #helpModal or entry is missing.
// ============================================================================
(function () {
  var PREFIX = 'cb_help_seen:';

  // localStorage seam — wrapped so a disabled/throwing store (private mode,
  // quota, file:// origin) never breaks the host. An unreadable store reads as
  // "not seen"; a failed write just means an explainer may re-show (harmless).
  function cbHelpSeen(id) {
    try { return window.localStorage.getItem(PREFIX + id) === '1'; }
    catch (e) { return false; }
  }
  function cbMarkHelpSeen(id) {
    try { window.localStorage.setItem(PREFIX + id, '1'); }
    catch (e) { /* storage unavailable — non-fatal */ }
  }

  // THE reusable opener. `entry` is a resolved { title, body } (the caller looks
  // it up in its own registry). a11y posture is byte-faithful to the original
  // openHelpModal / openDashHelp: Esc closes, Tab focus-trap, backdrop /
  // [data-help-dismiss] click-away, aria-expanded toggle, focus restored to the
  // trigger. triggerEl may be null (the first-view auto-open has no trigger).
  function cbOpenHelpModal(entry, triggerEl) {
    var modal = document.getElementById('helpModal');
    if (!modal || !entry) return;

    var titleEl = document.getElementById('helpModalTitle');
    var bodyEl = document.getElementById('helpModalBody');
    if (titleEl) titleEl.textContent = entry.title;
    if (bodyEl) bodyEl.textContent = entry.body;

    var focusable = modal.querySelectorAll('button');
    var closeBtn = document.getElementById('btnCloseHelp');
    var dismissers = Array.prototype.slice.call(
      modal.querySelectorAll('[data-help-dismiss]')
    );

    function cleanup() {
      modal.classList.add('hidden');
      modal.removeEventListener('keydown', onKey);
      dismissers.forEach(function (b) { b.removeEventListener('click', cleanup); });
      if (triggerEl && typeof triggerEl.setAttribute === 'function') {
        triggerEl.setAttribute('aria-expanded', 'false');
      }
      if (triggerEl && typeof triggerEl.focus === 'function') triggerEl.focus();
    }

    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); cleanup(); return; }
      if (e.key !== 'Tab' || focusable.length === 0) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }

    dismissers.forEach(function (b) { b.addEventListener('click', cleanup); });
    modal.addEventListener('keydown', onKey);
    if (triggerEl && typeof triggerEl.setAttribute === 'function') {
      triggerEl.setAttribute('aria-expanded', 'true');
    }
    modal.classList.remove('hidden');
    if (closeBtn) closeBtn.focus();
  }

  window.CB_HELP_SEEN_PREFIX = PREFIX;
  window.cbHelpSeen = cbHelpSeen;
  window.cbMarkHelpSeen = cbMarkHelpSeen;
  window.cbOpenHelpModal = cbOpenHelpModal;
})();
