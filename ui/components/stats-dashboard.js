/**
 * Stats dashboard: totals, success rate, latency, tokens, agent distribution. Auto-refresh 30s.
 */
(function () {
  const dashboardEl = document.getElementById('stats-dashboard');
  const REFRESH_MS = 30000;
  let refreshTimer = null;

  function render(data) {
    if (!dashboardEl) return;
    if (!data) {
      dashboardEl.innerHTML = '<p class="stats-loading">Loading…</p>';
      return;
    }
    var srNum = Number(data.success_rate);
    var sr = (isNaN(srNum) ? 0 : (srNum * 100).toFixed(1)) + '%';
    var agents = data.agent_distribution || {};
    var agentRows = Object.entries(agents)
      .sort(function (a, b) { return b[1] - a[1]; })
      .slice(0, 10)
      .map(function (e) { return '<tr><td>' + e[0] + '</td><td>' + e[1] + '</td></tr>'; })
      .join('');
    var sentiment = data.sentiment_distribution || {};
    var sentimentRows = Object.entries(sentiment)
      .sort(function (a, b) { return b[1] - a[1]; })
      .map(function (e) { return '<tr><td>' + e[0] + '</td><td>' + e[1] + '</td></tr>'; })
      .join('');
    var totalMessages = data.total_messages ?? 0;
    var totalSessions = data.total_sessions ?? 0;
    var noData = totalMessages === 0 && totalSessions === 0;
    dashboardEl.innerHTML =
      (noData ? '<p class="stats-no-data">No activity yet. Send a message in Chat to see stats.</p>' : '') +
      '<div class="stats-grid">' +
        '<div class="stat-card"><span class="stat-value">' + totalSessions + '</span><span class="stat-label">Sessions</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + totalMessages + '</span><span class="stat-label">Messages</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + sr + '</span><span class="stat-label">Success rate</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + (data.avg_latency_ms ?? 0) + '</span><span class="stat-label">Avg latency (ms)</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + (data.p50_latency_ms ?? 0) + '</span><span class="stat-label">p50 (ms)</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + (data.p95_latency_ms ?? 0) + '</span><span class="stat-label">p95 (ms)</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + (data.p99_latency_ms ?? 0) + '</span><span class="stat-label">p99 (ms)</span></div>' +
        '<div class="stat-card"><span class="stat-value">' + (data.tokens_used ?? 0) + '</span><span class="stat-label">Tokens used</span></div>' +
      '</div>' +
      '<div class="stats-agents">' +
        '<h3 class="stats-subtitle">Agent distribution</h3>' +
        '<table class="stats-table"><thead><tr><th>Agent</th><th>Count</th></tr></thead><tbody>' + (agentRows || '<tr><td colspan="2">No data</td></tr>') + '</tbody></table>' +
      '</div>' +
      '<div class="stats-sentiment">' +
        '<h3 class="stats-subtitle">User sentiment</h3>' +
        '<table class="stats-table"><thead><tr><th>Sentiment</th><th>Count</th></tr></thead><tbody>' + (sentimentRows || '<tr><td colspan="2">No data yet</td></tr>') + '</tbody></table>' +
      '</div>';
  }

  function load() {
    getStats()
      .then(render)
      .catch(function () {
        if (dashboardEl) dashboardEl.innerHTML = '<p>Failed to load stats</p>';
      });
  }

  window.addEventListener('stats-view-show', function () {
    load();
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(load, REFRESH_MS);
  });
  window.addEventListener('stats-view-hide', function () {
    if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  });

  var viewStats = document.getElementById('view-stats');
  if (dashboardEl && viewStats && viewStats.classList.contains('view-active')) {
    load();
    refreshTimer = setInterval(load, REFRESH_MS);
  }
})();
