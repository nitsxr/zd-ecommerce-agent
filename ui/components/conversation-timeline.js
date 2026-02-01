/**
 * Conversation timeline: list of turns (user_message, agent, response, handover, tool_calls).
 */
function renderConversationTimeline(container, turns) {
  if (!turns || turns.length === 0) {
    container.innerHTML = '<section class="timeline"><h2>Conversation</h2><p class="muted">No turns yet. Send a message or load a session.</p></section>';
    return;
  }
  let html = '<section class="timeline"><h2>Conversation</h2>';
  turns.forEach((t, i) => {
    html += `
      <div class="turn" data-turn-index="${i}">
        <div class="turn-header">Turn ${i}</div>
        <div class="turn-user"><strong>User:</strong> ${escapeHtml(t.user_message)}</div>
        <div class="turn-agent"><strong>Agent:</strong> ${escapeHtml(t.agent)}</div>
        <div class="turn-response">${escapeHtml(t.response)}</div>
        <div class="turn-handover"><small>${escapeHtml(t.handover)}</small></div>
        ${(t.tool_calls || []).length ? `<div class="turn-tools"><strong>Tools:</strong> ${(t.tool_calls || []).map(tc => escapeHtml(tc.tool)).join(", ")}</div>` : ""}
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
