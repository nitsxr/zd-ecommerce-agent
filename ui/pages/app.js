/**
 * App: wire chat panel, conversation timeline, trace inspector.
 * Conversation and trace views aligned by turn_index.
 */
(function () {
  const state = {
    sessionId: "",
    turns: [],
    traces: [],
    loading: false,
    error: null,
  };

  const chatRoot = document.getElementById("chat-panel-root");
  const conversationRoot = document.getElementById("conversation-root");
  const traceRoot = document.getElementById("trace-root");

  function setError(msg) {
    state.error = msg;
    state.loading = false;
    render();
  }

  function clearError() {
    state.error = null;
  }

  function loadSession(sessionId) {
    if (!sessionId) return;
    state.sessionId = sessionId;
    state.loading = true;
    clearError();
    render();
    Promise.all([getSessionTurns(sessionId), getSessionTraces(sessionId)])
      .then(([turnsData, tracesData]) => {
        state.turns = turnsData && turnsData.turns ? turnsData.turns : [];
        state.traces = tracesData && tracesData.traces ? tracesData.traces : [];
        state.loading = false;
        render();
      })
      .catch((err) => {
        setError(err.message || "Failed to load session");
      });
  }

  function sendMessage(sessionId, message) {
    state.loading = true;
    clearError();
    render();
    postChat(sessionId, message)
      .then(() => {
        loadSession(sessionId);
      })
      .catch((err) => {
        setError(err.message || "Send failed");
      });
  }

  function render() {
    renderChatPanel(chatRoot, state, sendMessage, loadSession);
    renderConversationTimeline(conversationRoot, state.turns);
    renderTraceInspector(traceRoot, state.traces);
  }

  render();
})();
