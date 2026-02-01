/**
 * Trace timeline: vertical list of events, color-coded by type/agent.
 */
(function () {
  const timelineEl = document.getElementById('trace-timeline');
  const EVENT_COLORS = {
    request_received: 'var(--accent)',
    memory_analysis: '#a371f7',
    routing_decision: '#79c0ff',
    agent_called: '#7ee787',
    tool_called: '#d2a8ff',
    response_sent: '#79c0ff',
    error: 'var(--error-text)',
  };

  function formatTime(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString();
    } catch (_) {
      return String(iso);
    }
  }

  function renderEvent(event, index) {
    const div = document.createElement('div');
    div.className = 'timeline-event';
    div.dataset.index = index;
    const color = EVENT_COLORS[event.event_type] || 'var(--text-muted)';
    const agent = event.agent || '—';
    const duration = event.duration_ms != null ? event.duration_ms + ' ms' : '';
    const tokens = event.tokens_used != null ? event.tokens_used + ' tokens' : '';
    div.innerHTML =
      '<span class="timeline-event-dot" style="background:' + color + '"></span>' +
      '<div class="timeline-event-body">' +
        '<span class="timeline-event-type">' + (event.event_type || '') + '</span>' +
        (agent !== '—' ? ' <span class="timeline-event-agent">' + agent + '</span>' : '') +
        '<div class="timeline-event-action">' + (event.action || '') + '</div>' +
        (duration || tokens ? '<div class="timeline-event-meta">' + [duration, tokens].filter(Boolean).join(' · ') + '</div>' : '') +
      '</div>';
    div.addEventListener('click', function () {
      document.querySelectorAll('.timeline-event.selected').forEach(function (e) { e.classList.remove('selected'); });
      div.classList.add('selected');
      window.dispatchEvent(new CustomEvent('trace-event-select', { detail: { event: event, index: index } }));
    });
    return div;
  }

  function render(events) {
    if (!timelineEl) return;
    timelineEl.innerHTML = '';
    if (!events || events.length === 0) {
      timelineEl.innerHTML = '<p class="timeline-empty">Select a session to view trace</p>';
      return;
    }
    events.forEach(function (ev, i) {
      timelineEl.appendChild(renderEvent(ev, i));
    });
  }

  window.addEventListener('trace-session-select', function (e) {
    const sessionId = e.detail.sessionId;
    getTrace(sessionId)
      .then(function (data) {
        render(data.events || []);
      })
      .catch(function () {
        render([]);
      });
  });
})();
