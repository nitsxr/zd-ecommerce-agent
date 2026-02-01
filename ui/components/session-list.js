/**
 * Session list: recent sessions, filter, click to load trace.
 */
(function () {
  const listEl = document.getElementById('session-list');
  const searchEl = document.getElementById('trace-search');
  let sessions = [];
  let selectedId = null;

  function truncate(id, len) {
    if (!id) return '—';
    return id.length <= len ? id : id.slice(0, len) + '…';
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch (_) {
      return iso;
    }
  }

  function render() {
    const q = (searchEl && searchEl.value) ? searchEl.value.trim().toLowerCase() : '';
    const filtered = q
      ? sessions.filter(function (s) { return (s.session_id || '').toLowerCase().includes(q); })
      : sessions;

    if (!listEl) return;
    listEl.innerHTML = '';
    if (filtered.length === 0) {
      listEl.innerHTML = '<p class="session-list-empty">No sessions</p>';
      return;
    }
    filtered.forEach(function (s) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'session-row' + (s.session_id === selectedId ? ' selected' : '');
      row.dataset.sessionId = s.session_id;
      row.innerHTML =
        '<span class="session-row-id">' + truncate(s.session_id, 20) + '</span>' +
        '<span class="session-row-meta">' + (s.message_count || 0) + ' msgs · ' + formatDate(s.updated_at) + '</span>';
      row.addEventListener('click', function () {
        selectedId = s.session_id;
        render();
        window.dispatchEvent(new CustomEvent('trace-session-select', { detail: { sessionId: s.session_id } }));
      });
      listEl.appendChild(row);
    });
  }

  function load() {
    getSessions(100)
      .then(function (data) {
        sessions = data.sessions || [];
        render();
      })
      .catch(function () {
        if (listEl) listEl.innerHTML = '<p class="session-list-empty">Failed to load sessions</p>';
      });
  }

  if (searchEl) searchEl.addEventListener('input', render);
  window.addEventListener('trace-view-show', load);
  if (listEl && document.getElementById('view-trace').classList.contains('view-active')) load();
})();
