/**
 * Chat panel: message history, input, session management.
 */

(function () {
  const STORAGE_KEY = 'assistant_session_id';

  function generateSessionId() {
    return 's-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }

  function getStoredSessionId() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
  }

  function setStoredSessionId(id) {
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch (_) {}
  }

  const messagesEl = document.getElementById('chat-messages');
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send');
  const newChatBtn = document.getElementById('btn-new-chat');
  const sessionIdEl = document.getElementById('session-id');
  const errorWrapEl = document.getElementById('chat-error-wrap');
  const errorEl = document.getElementById('chat-error');
  const retryBtn = document.getElementById('btn-retry');

  let sessionId = getStoredSessionId() || generateSessionId();
  let loading = false;

  function showError(msg) {
    var m = (msg && String(msg).trim()) ? String(msg).trim() : 'Something went wrong.';
    if (errorEl) errorEl.textContent = m;
    if (errorWrapEl) errorWrapEl.hidden = false;
  }

  function clearError() {
    if (errorEl) errorEl.textContent = '';
    if (errorWrapEl) errorWrapEl.hidden = true;
  }

  function setSessionId(id) {
    sessionId = id;
    setStoredSessionId(id);
    sessionIdEl.textContent = id;
    sessionIdEl.title = id;
  }

  function appendMessage(role, content, agent) {
    const div = document.createElement('div');
    div.className = 'chat-message ' + role;
    div.setAttribute('data-role', role);

    if (role === 'assistant' && agent) {
      const tag = document.createElement('div');
      tag.className = 'agent-tag';
      tag.textContent = agent;
      div.appendChild(tag);
    }

    const contentEl = document.createElement('div');
    contentEl.className = 'content';
    contentEl.textContent = content;
    div.appendChild(contentEl);

    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendLoading() {
    const div = document.createElement('div');
    div.className = 'chat-message assistant loading';
    div.setAttribute('data-role', 'assistant');
    div.id = 'chat-loading';
    const content = document.createElement('div');
    content.className = 'content';
    content.textContent = 'Thinking';
    div.appendChild(content);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeLoading() {
    const el = document.getElementById('chat-loading');
    if (el) el.remove();
  }

  async function send() {
    const text = inputEl.value.trim();
    if (!text || loading) return;

    clearError();
    inputEl.value = '';
    appendMessage('user', text);

    loading = true;
    sendBtn.disabled = true;
    appendLoading();

    try {
      const data = await sendMessage(sessionId, text);
      removeLoading();

      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }

      appendMessage('assistant', data.response, data.agent || data.handover || 'Assistant');
    } catch (err) {
      removeLoading();
      showError(err.message || 'Something went wrong. Try again.');
    } finally {
      loading = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  function newConversation() {
    setSessionId(generateSessionId());
    messagesEl.innerHTML = '';
    clearError();
    appendMessage('assistant', "Hello! I can help with order tracking, cancellations, and product questions. How can I assist you?", "Assistant");
  }

  sendBtn.addEventListener('click', send);
  newChatBtn.addEventListener('click', newConversation);
  if (retryBtn) retryBtn.addEventListener('click', clearError);

  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  setSessionId(sessionId);
  clearError();
  if (messagesEl.children.length === 0) {
    appendMessage('assistant', "Hello! I can help with order tracking, cancellations, and product questions. How can I assist you?", "Assistant");
  }
})();
