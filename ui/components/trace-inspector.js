/**
 * Trace inspector: read-only list of trace events aligned by turn_index.
 */
function renderTraceInspector(container, traces) {
  if (!traces || traces.length === 0) {
    container.innerHTML = '<section class="trace-inspector"><h2>Trace</h2><p class="muted">No traces yet. Send a message or load a session.</p></section>';
    return;
  }
  let html = '<section class="trace-inspector"><h2>Trace (read-only)</h2>';
  traces.forEach((tr, i) => {
    const idx = tr.turn_index ?? i;
    html += `
      <div class="trace-turn" data-turn-index="${idx}">
        <div class="trace-header">Turn ${idx}</div>
        <div class="trace-meta"><strong>Intent:</strong> ${escapeHtml(tr.intent)} | <strong>Agent:</strong> ${escapeHtml(tr.selected_agent)}</div>
        <div class="trace-latency">Latency: ${tr.latency_ms != null ? tr.latency_ms + " ms" : "—"}</div>
        ${(tr.tool_calls_summary || []).length ? `<div class="trace-tools">${(tr.tool_calls_summary || []).map(t => escapeHtml(t.tool) + (t.success ? " ✓" : " ✗")).join(", ")}</div>` : ""}
        ${(tr.errors || []).length ? `<div class="trace-errors">Errors: ${escapeHtml(tr.errors.join("; "))}</div>` : ""}
        <div class="trace-request-id"><small>request_id: ${escapeHtml(tr.request_id || "")}</small></div>
      </div>
    `;
  });
  html += "</section>";
  container.innerHTML = html;
}

function escapeHtml(s) {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
