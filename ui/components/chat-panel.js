/**
 * Chat panel: session browser, message input, send.
 */
function renderChatPanel(container, state, onSend, onLoadSession) {
  const sessionId = state.sessionId || "";
  const loading = state.loading || false;
  container.innerHTML = `
    <section class="chat-panel">
      <h2>Session</h2>
      <div class="session-row">
        <input type="text" id="session-id" placeholder="Session ID (e.g. abc123)" value="${escapeHtml(sessionId)}" />
        <button type="button" id="load-session" ${loading ? "disabled" : ""}>Load</button>
      </div>
      <h2>Send message</h2>
      <div class="send-row">
        <input type="text" id="message-input" placeholder="e.g. I want to cancel my order ORD-4567" />
        <button type="button" id="send-btn" ${loading ? "disabled" : ""}>Send</button>
      </div>
      ${state.error ? `<p class="error">${escapeHtml(state.error)}</p>` : ""}
    </section>
  `;
  const sidEl = container.querySelector("#session-id");
  const msgEl = container.querySelector("#message-input");
  container.querySelector("#load-session").addEventListener("click", () => onLoadSession(sidEl.value.trim()));
  container.querySelector("#send-btn").addEventListener("click", () => {
    const msg = msgEl.value.trim();
    if (msg && sidEl.value.trim()) onSend(sidEl.value.trim(), msg);
    msgEl.value = "";
  });
  msgEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const msg = msgEl.value.trim();
      if (msg && sidEl.value.trim()) onSend(sidEl.value.trim(), msg);
      msgEl.value = "";
    }
  });
}

function escapeHtml(s) {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
