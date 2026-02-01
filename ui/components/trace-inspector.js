/**
 * Trace inspector: show details for selected event.
 */
(function () {
  const inspectorEl = document.getElementById('trace-inspector');

  function formatJson(obj) {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (_) {
      return String(obj);
    }
  }

  function render(event) {
    if (!inspectorEl) return;
    if (!event) {
      inspectorEl.innerHTML = '<p class="inspector-empty">Click an event in the timeline</p>';
      return;
    }
    const ts = event.timestamp ? new Date(event.timestamp).toISOString() : '—';
    const duration = event.duration_ms != null ? event.duration_ms + ' ms' : '—';
    const tokens = event.tokens_used != null ? event.tokens_used : '—';
    const meta = event.metadata && Object.keys(event.metadata).length ? formatJson(event.metadata) : null;
    inspectorEl.innerHTML =
      '<div class="inspector-section">' +
        '<div class="inspector-row"><span class="inspector-label">Type</span><span>' + (event.event_type || '') + '</span></div>' +
        '<div class="inspector-row"><span class="inspector-label">Timestamp</span><span>' + ts + '</span></div>' +
        '<div class="inspector-row"><span class="inspector-label">Duration</span><span>' + duration + '</span></div>' +
        '<div class="inspector-row"><span class="inspector-label">Tokens</span><span>' + tokens + '</span></div>' +
        (event.agent ? '<div class="inspector-row"><span class="inspector-label">Agent</span><span>' + event.agent + '</span></div>' : '') +
        '<div class="inspector-row inspector-action"><span class="inspector-label">Action</span><span>' + (event.action || '') + '</span></div>' +
      '</div>' +
      (meta ? '<div class="inspector-section"><div class="inspector-label">Metadata</div><pre class="inspector-pre">' + meta + '</pre></div>' : '');
  }

  window.addEventListener('trace-event-select', function (e) {
    render(e.detail.event);
  });

  if (inspectorEl) inspectorEl.innerHTML = '<p class="inspector-empty">Click an event in the timeline</p>';
})();
